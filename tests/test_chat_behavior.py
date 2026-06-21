import unittest

import streamlit_app as app


DATASET = "Detailed Graph"


class ChatBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph_path = str(app.GRAPH_OPTIONS[DATASET])
        cls.graph_payload = app.load_graph(cls.graph_path)
        cls.indexes = app.build_indexes(cls.graph_path)

    def ask(self, question, last_query_state=None, last_evidence=None):
        answer, evidence, backend, query_state, trace = app.answer_question(
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
        return answer, evidence, backend, query_state, trace

    def assertContainsAll(self, text, expected_items):
        lowered = text.casefold()
        for item in expected_items:
            self.assertIn(item.casefold(), lowered, msg=f"Missing expected text: {item}")

    def test_identity_coo_returns_graph_person(self):
        answer, _, backend, _, trace = self.ask("who is coo")

        self.assertEqual("Graph Search", backend)
        self.assertIn("Eva Kralikova", answer)
        self.assertIn("Chief Operating Officer", answer)
        self.assertIn("identity", trace["resolution_mode"].casefold())

    def test_missing_cio_does_not_hallucinate_john_smith(self):
        answer, _, backend, _, _ = self.ask("who cio")

        self.assertEqual("Graph Search", backend)
        self.assertNotIn("John Smith", answer)
        self.assertNotIn("Chief Information Officer is John Smith", answer)
        self.assertTrue(
            "could not find" in answer.casefold()
            or "close related role" in answer.casefold()
            or "IT Director / Head of IT" in answer
        )

    def test_reporting_up_for_petra(self):
        answer, _, backend, _, _ = self.ask("who is petras boss")

        self.assertEqual("Graph Search", backend)
        self.assertIn("Petra Novakova", answer)
        self.assertIn("Lukas Steiner", answer)
        self.assertIn("Chief Financial Officer", answer)

    def test_country_membership_returns_all_slovakia_people(self):
        answer, _, backend, query_state, _ = self.ask("who works in slovakia")

        self.assertEqual("Graph Search", backend)
        self.assertNotIn("Showing", answer)
        self.assertContainsAll(
            answer,
            [
                "Jozef Polak",
                "Michal Hronec",
                "Lucia Benesova",
                "Andrej Varga",
                "Nina Havel",
                "Erik Sykora",
                "Barbora Klinec",
                "David Mraz",
                "Roman Kolar",
                "Katarina Urban",
                "Veronika Duda",
                "Manuela Kovacova",
                "Daniel Richter",
                "Alena Kralova",
            ],
        )
        self.assertEqual("membership", query_state["kind"])

    def test_group_location_followup_uses_previous_membership_group(self):
        first_answer, first_evidence, _, first_state, _ = self.ask("who works in hr")
        answer, _, backend, query_state, _ = self.ask(
            "where are they based?",
            last_query_state=first_state,
            last_evidence=first_evidence,
        )

        self.assertIn("Petra Novakova", first_answer)
        self.assertEqual("Graph Search", backend)
        self.assertContainsAll(answer, ["Petra Novakova", "Manuela Kovacova", "Ioana Marinescu"])
        self.assertContainsAll(answer, ["Banska Bystrica", "Bucharest"])
        self.assertEqual("person_location", query_state["kind"])

    def test_erp_system_skill_ambiguity_prefers_system_with_people(self):
        answer, _, backend, _, _ = self.ask("who knows erp")

        self.assertEqual("Graph Search", backend)
        self.assertNotIn("no people are currently linked", answer.casefold())
        self.assertContainsAll(
            answer,
            [
                "Lukas Steiner",
                "Filip Hruby",
                "Marek Sramek",
                "Tomas Benes",
                "Nina Havel",
                "Roman Kolar",
                "Martin Pospisil",
                "Veronika Duda",
                "Zuzana Balaz",
            ],
        )

    def test_azure_typo_correction_does_not_rewrite_to_are_or_sharepoint(self):
        self.assertEqual("who knows azure", app.expand_query("who knows azure"))

        answer, _, backend, _, _ = self.ask("who knows azure")

        self.assertEqual("Graph Search", backend)
        self.assertIn("Filip Hruby", answer)
        self.assertIn("Azure", answer)
        self.assertNotIn("SharePoint", answer)

    def test_python_skill_query_returns_all_linked_people(self):
        answer, _, backend, _, _ = self.ask("who has skill python")

        self.assertEqual("Graph Search", backend)
        self.assertContainsAll(
            answer,
            ["David Mraz", "Erik Sykora", "Nina Havel", "Barbora Klinec", "Filip Hruby", "Roman Kolar"],
        )

    def test_person_summary_is_not_truncated_to_only_few_skills(self):
        answer, _, backend, _, _ = self.ask("tell me everything about filip")

        self.assertEqual("Graph Search", backend)
        self.assertContainsAll(answer, ["Apache Airflow", "Python", "Workflow orchestration"])
        self.assertContainsAll(answer, ["Azure", "ERP", "identity management"])

    def test_greeting_does_not_fall_back_to_graph_matches(self):
        answer, _, backend, _, trace = self.ask("hi")

        self.assertEqual("Graph Search", backend)
        self.assertIn("Hi, I'm SkillWiki", answer)
        self.assertNotIn("strongest graph matches", answer.casefold())
        self.assertIn("greeting", trace["resolution_mode"].casefold())


if __name__ == "__main__":
    unittest.main()
