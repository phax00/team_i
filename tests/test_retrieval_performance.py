import time
import unittest

import streamlit_app as app


DATASET = "Detailed Graph"


class RetrievalPerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph_path = str(app.GRAPH_OPTIONS[DATASET])
        cls.graph_payload = app.load_graph(cls.graph_path)
        cls.indexes = app.build_indexes(cls.graph_path)

    def answer(self, question):
        return app.answer_question(
            question=question,
            dataset_name=DATASET,
            graph_payload=self.graph_payload,
            indexes=self.indexes,
            gemini_model_name="",
            ollama_model_name="",
            ollama_host="",
        )

    def test_index_contains_expected_scale(self):
        nodes = self.graph_payload["nodes"]
        relationships = self.graph_payload["relationships"]

        self.assertGreaterEqual(len(nodes), 650)
        self.assertGreaterEqual(len(relationships), 1000)

    def test_index_build_time_is_reasonable_for_mvp_graph(self):
        start = time.perf_counter()
        indexes = app.build_indexes(self.graph_path)
        elapsed = time.perf_counter() - start

        self.assertIn("nodes_by_id", indexes)
        self.assertLess(elapsed, 5.0, msg=f"Index build took too long: {elapsed:.3f}s")

    def test_common_graph_queries_run_without_model_and_under_budget(self):
        questions = [
            "who is coo",
            "who works in slovakia",
            "who knows erp",
            "who has skill python",
            "who is petras boss",
            "where does daniel richter work",
            "who works with data",
            "list all roles",
            "tell me everything about filip",
        ]

        start = time.perf_counter()
        answers = [self.answer(question) for question in questions]
        elapsed = time.perf_counter() - start

        for answer, _, backend, _, trace in answers:
            self.assertTrue(answer.strip())
            self.assertEqual("Graph Search", backend)
            self.assertEqual("None", trace["internal_model_use"])

        self.assertLess(elapsed, 8.0, msg=f"Common graph query batch took too long: {elapsed:.3f}s")


if __name__ == "__main__":
    unittest.main()
