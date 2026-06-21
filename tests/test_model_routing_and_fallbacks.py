import unittest
from unittest.mock import patch

import streamlit_app as app


DATASET = "Detailed Graph"


class ModelRoutingAndFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph_path = str(app.GRAPH_OPTIONS[DATASET])
        cls.graph_payload = app.load_graph(cls.graph_path)
        cls.indexes = app.build_indexes(cls.graph_path)

    def ask(self, question, gemini_model_name="", ollama_model_name="", ollama_host=""):
        return app.answer_question(
            question=question,
            dataset_name=DATASET,
            graph_payload=self.graph_payload,
            indexes=self.indexes,
            gemini_model_name=gemini_model_name,
            ollama_model_name=ollama_model_name,
            ollama_host=ollama_host,
            conversation_focus=None,
            recent_messages=None,
            last_query_state=None,
            last_evidence=None,
        )

    def test_provider_chain_graph_only_when_model_assistance_is_off(self):
        self.assertEqual(["search"], app.provider_chain("local", False, True, True))
        self.assertEqual(["search"], app.provider_chain("cloud", False, True, True))

    def test_provider_chain_prefers_ollama_for_local_runtime(self):
        self.assertEqual(["ollama", "search"], app.provider_chain("local", True, True, True))
        self.assertEqual(["search"], app.provider_chain("local", True, False, True))

    def test_provider_chain_prefers_gemini_for_cloud_runtime_only_when_ready(self):
        self.assertEqual(["gemini", "search"], app.provider_chain("cloud", True, False, True))
        self.assertEqual(["search"], app.provider_chain("cloud", True, False, False))

    @patch("streamlit_app.call_ollama")
    @patch("streamlit_app.is_ollama_available", return_value=True)
    def test_local_model_path_uses_ollama_before_graph_search(self, _available, call_ollama):
        call_ollama.return_value = "The retrieved graph evidence describes company strategy ownership."

        answer, _evidence, backend, _query_state, trace = self.ask(
            "company strategy ownership",
            ollama_model_name="llama3.2",
            ollama_host="http://127.0.0.1:11434",
        )

        self.assertEqual("Ollama", backend)
        self.assertGreaterEqual(call_ollama.call_count, 1)
        self.assertIn("LLM answer over retrieved graph context", trace["resolution_mode"])
        self.assertIn("company strategy", answer.casefold())

    @patch("streamlit_app.call_gemini")
    @patch("streamlit_app.get_api_key", return_value="fake-key")
    @patch("streamlit_app.is_ollama_available", return_value=False)
    def test_cloud_model_path_uses_gemini_when_enabled_and_ready(self, _available, _api_key, call_gemini):
        call_gemini.return_value = "The retrieved graph evidence describes company strategy ownership."

        with patch("streamlit_app.st.session_state", {}), patch("streamlit_app.detect_runtime_mode", return_value="cloud"):
            answer, _evidence, backend, _query_state, trace = self.ask(
                "company strategy ownership",
                gemini_model_name=app.DEFAULT_GEMINI_MODEL,
            )

        self.assertEqual("Gemini", backend)
        self.assertGreaterEqual(call_gemini.call_count, 1)
        self.assertIn("LLM answer over retrieved graph context", trace["resolution_mode"])
        self.assertIn("company strategy", answer.casefold())

    @patch("streamlit_app.call_gemini", side_effect=TimeoutError("Gemini timed out"))
    @patch("streamlit_app.get_api_key", return_value="fake-key")
    @patch("streamlit_app.is_ollama_available", return_value=False)
    def test_model_timeout_falls_back_to_graph_search(self, _available, _api_key, call_gemini):
        with patch("streamlit_app.st.session_state", {}), patch("streamlit_app.detect_runtime_mode", return_value="cloud"):
            answer, evidence, backend, _query_state, trace = self.ask(
                "company strategy ownership",
                gemini_model_name=app.DEFAULT_GEMINI_MODEL,
            )

        self.assertEqual("Graph Search", backend)
        self.assertGreaterEqual(call_gemini.call_count, 1)
        self.assertTrue(evidence["top_nodes"])
        self.assertIn("timeout", trace["resolution_mode"].casefold())
        self.assertIn("Gemini", trace["internal_model_use"])
        self.assertIn("timed out", trace["internal_model_use"])
        self.assertIn("company strategy", answer.casefold())

    @patch("streamlit_app.call_gemini", side_effect=RuntimeError("429 quota exceeded"))
    @patch("streamlit_app.get_api_key", return_value="fake-key")
    @patch("streamlit_app.is_ollama_available", return_value=False)
    def test_gemini_quota_error_disables_gemini_and_uses_graph_search(self, _available, _api_key, call_gemini):
        session_state = {}
        with patch("streamlit_app.st.session_state", session_state), patch("streamlit_app.detect_runtime_mode", return_value="cloud"):
            answer, evidence, backend, _query_state, trace = self.ask(
                "company strategy ownership",
                gemini_model_name=app.DEFAULT_GEMINI_MODEL,
            )

        self.assertEqual("Graph Search", backend)
        self.assertGreaterEqual(call_gemini.call_count, 1)
        self.assertTrue(evidence["top_nodes"])
        self.assertTrue(session_state.get("gemini_model_disabled", False))
        self.assertIn("Graph-only fallback", trace["resolution_mode"])
        self.assertIn("company strategy", answer.casefold())

    @patch("streamlit_app.call_gemini", return_value="John Smith is the CIO.")
    @patch("streamlit_app.get_api_key", return_value="fake-key")
    @patch("streamlit_app.is_ollama_available", return_value=False)
    def test_unsupported_model_answer_is_rejected_by_validator(self, _available, _api_key, _call_gemini):
        with patch("streamlit_app.st.session_state", {}), patch("streamlit_app.detect_runtime_mode", return_value="cloud"):
            answer, _evidence, backend, _query_state, trace = self.ask(
                "company strategy ownership",
                gemini_model_name=app.DEFAULT_GEMINI_MODEL,
            )

        self.assertEqual("Graph Search", backend)
        self.assertNotIn("John Smith is the CIO", answer)
        self.assertIn("Validator fallback", trace["resolution_mode"])
        self.assertIn("unsupported", trace["validation"].casefold())


if __name__ == "__main__":
    unittest.main()
