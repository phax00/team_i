import unittest

import streamlit_app as app


DATASET = "Detailed Graph"


class GoldenQuestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph_path = str(app.GRAPH_OPTIONS[DATASET])
        cls.graph_payload = app.load_graph(cls.graph_path)
        cls.indexes = app.build_indexes(cls.graph_path)

    def ask(self, question, last_query_state=None, last_evidence=None):
        return app.answer_question(
            question=question,
            dataset_name=DATASET,
            graph_payload=self.graph_payload,
            indexes=self.indexes,
            gemini_model_name="",
            ollama_model_name="",
            ollama_host="",
            conversation_focus=None,
            recent_messages=None,
            last_query_state=last_query_state,
            last_evidence=last_evidence,
        )

    def assertAnswerContains(self, question, expected, forbidden=None):
        answer, _evidence, backend, _query_state, trace = self.ask(question)

        self.assertEqual("Graph Search", backend)
        for item in expected:
            self.assertIn(item.casefold(), answer.casefold(), msg=f"Question {question!r} missed {item!r}")
        for item in forbidden or []:
            self.assertNotIn(item.casefold(), answer.casefold(), msg=f"Question {question!r} should not include {item!r}")
        self.assertNotIn("I could not find a confident match", answer)
        self.assertEqual("None", trace["internal_model_use"])
        return answer

    def test_who_knows_erp_golden_answer(self):
        self.assertAnswerContains(
            "who knows erp",
            expected=["Lukas Steiner", "Filip Hruby", "Zuzana Balaz", "ERP"],
            forbidden=["no people are currently linked to it"],
        )

    def test_who_knows_python_golden_answer_matches_current_graph_links(self):
        self.assertAnswerContains(
            "who knows python",
            expected=["David Mraz", "Python"],
            forbidden=["John Smith", "Nina Havel currently knows `Python`"],
        )

    def test_who_works_in_slovakia_golden_answer(self):
        self.assertAnswerContains(
            "who works in slovakia",
            expected=["Jozef Polak", "Lucia Benesova", "Daniel Richter", "Alena Kralova", "Slovakia"],
            forbidden=["Showing"],
        )

    def test_where_is_petra_based_golden_answer(self):
        self.assertAnswerContains(
            "where is petra based",
            expected=["Petra Novakova", "Group / Multi-site"],
            forbidden=["holds the HR Director"],
        )

    def test_who_is_cio_golden_answer(self):
        self.assertAnswerContains(
            "who is cio",
            expected=["could not find", "IT Director / Head of IT", "Filip Hruby"],
            forbidden=["John Smith", "Chief Information Officer is"],
        )

    def test_who_works_with_api_golden_answer(self):
        self.assertAnswerContains(
            "who works with api",
            expected=["Erik Sykora", "Nina Havel", "David Mraz"],
            forbidden=["could not find"],
        )

    def test_petra_and_filip_relationship_golden_answer(self):
        self.assertAnswerContains(
            "are petra and filip connected through lukas",
            expected=["Petra Novakova", "Filip Hruby", "Lukas Steiner"],
            forbidden=["master data governance"],
        )

    def test_hr_location_followup_golden_answer(self):
        first_answer, first_evidence, _backend, first_query_state, _trace = self.ask("who works in hr")
        self.assertIn("Petra Novakova", first_answer)
        self.assertIn("Manuela Kovacova", first_answer)
        self.assertIn("Ioana Marinescu", first_answer)

        followup_answer, _evidence, backend, _query_state, trace = self.ask(
            "where are they based",
            last_query_state=first_query_state,
            last_evidence=first_evidence,
        )

        self.assertEqual("Graph Search", backend)
        self.assertIn("Petra Novakova", followup_answer)
        self.assertIn("Manuela Kovacova", followup_answer)
        self.assertIn("Ioana Marinescu", followup_answer)
        self.assertIn("Bucharest", followup_answer)
        self.assertIn("Follow-up group location", trace["resolution_mode"])


if __name__ == "__main__":
    unittest.main()
