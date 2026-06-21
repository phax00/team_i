import unittest

import streamlit_app as app


DATASET = "Detailed Graph"


class NormalizationAndValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph_path = str(app.GRAPH_OPTIONS[DATASET])
        cls.graph_payload = app.load_graph(cls.graph_path)
        cls.indexes = app.build_indexes(cls.graph_path)

    def person_node(self, name):
        for node in self.indexes["nodes_by_id"].values():
            if node.get("label") == "Person" and node.get("name") == name:
                return node
        raise AssertionError(f"Missing person node {name}")

    def test_query_normalization_keeps_technical_terms(self):
        self.assertEqual("who knows azure", app.expand_query("who knows azure"))
        self.assertEqual("who knows erp", app.expand_query("who knows erp"))
        self.assertEqual("who has skill python", app.expand_query("who has skill python"))
        self.assertEqual("who works with api", app.expand_query("who works with api"))

    def test_query_normalization_fixes_common_structure_typos(self):
        self.assertEqual("who works with people", app.expand_query("who works woth people"))
        self.assertEqual("where are they based", app.expand_query("where are thez based"))
        self.assertEqual("what is petra location", app.expand_query("what is petra localitz"))

    def test_display_query_term_formats_short_technical_terms_as_uppercase(self):
        self.assertEqual("ERP", app.display_query_term("erp"))
        self.assertEqual("API", app.display_query_term("api"))
        self.assertEqual("Azure", app.display_query_term("azure"))

    def test_llm_validator_allows_people_present_in_evidence(self):
        filip = self.person_node("Filip Hruby")
        evidence = {
            "top_nodes": [filip],
            "related_nodes": [filip],
            "relationships": [],
        }

        is_valid, reason = app.validate_llm_answer(
            "Filip Hruby is relevant here.",
            "who knows azure",
            evidence,
            self.indexes,
        )

        self.assertTrue(is_valid, reason)

    def test_llm_validator_rejects_known_person_outside_evidence(self):
        filip = self.person_node("Filip Hruby")
        evidence = {
            "top_nodes": [filip],
            "related_nodes": [filip],
            "relationships": [],
        }

        is_valid, reason = app.validate_llm_answer(
            "John Smith and Eva Kralikova are responsible.",
            "who knows azure",
            evidence,
            self.indexes,
        )

        self.assertFalse(is_valid)
        self.assertIn("Eva Kralikova", reason)

    def test_llm_validator_rejects_new_capitalized_entity_not_in_graph(self):
        evidence = {
            "top_nodes": [],
            "related_nodes": [],
            "relationships": [],
        }

        is_valid, reason = app.validate_llm_answer(
            "Jane Doe owns the system.",
            "who owns the system",
            evidence,
            self.indexes,
        )

        self.assertFalse(is_valid)
        self.assertIn("Jane Doe", reason)

    def test_followup_resolution_replaces_pronouns_for_person_focus(self):
        resolved = app.resolve_followup_question(
            "who works with her",
            {"label": "Person", "name": "Petra Novakova"},
        )

        self.assertEqual("who works with Petra Novakova", resolved)


if __name__ == "__main__":
    unittest.main()
