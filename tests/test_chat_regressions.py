import unittest

import streamlit_app as app


DATASET = "Detailed Graph"


class ChatRegressionTests(unittest.TestCase):
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

    def assertContainsAll(self, text, expected_items):
        lowered = text.casefold()
        for item in expected_items:
            self.assertIn(item.casefold(), lowered, msg=f"Missing expected text: {item}")

    def assertGraphOnly(self, backend, trace):
        self.assertEqual("Graph Search", backend)
        self.assertEqual("None", trace["internal_model_use"])

    def test_cto_missing_role_suggests_related_technical_roles(self):
        answer, evidence, backend, _, trace = self.ask("who is cto")

        self.assertGraphOnly(backend, trace)
        self.assertIn("could not find the exact title", answer.casefold())
        self.assertContainsAll(answer, ["IT Director / Head of IT", "Filip Hruby"])
        self.assertTrue(evidence["top_nodes"])

    def test_cdo_missing_role_does_not_invent_result(self):
        answer, evidence, backend, _, trace = self.ask("who is cdo")

        self.assertGraphOnly(backend, trace)
        self.assertIn("could not find", answer.casefold())
        self.assertNotIn("Chief Data Officer is", answer)
        self.assertEqual([], evidence["top_nodes"])

    def test_head_of_it_identity_uses_alias(self):
        answer, evidence, backend, _, trace = self.ask("who is head of it")

        self.assertGraphOnly(backend, trace)
        self.assertContainsAll(answer, ["Filip Hruby", "IT Director / Head of IT"])
        self.assertTrue(any(node.get("name") == "Filip Hruby" for node in evidence["top_nodes"]))

    def test_reporting_down_for_coo(self):
        answer, evidence, backend, _, trace = self.ask("who reports to coo")

        self.assertGraphOnly(backend, trace)
        self.assertContainsAll(answer, ["Jozef Polak", "Katarina Urban", "Martin Pospisil", "Eva Kralikova"])
        self.assertTrue(any(rel["type"] == "REPORTS_TO" for rel in evidence["relationships"]))

    def test_person_location_for_daniel_matches_country_membership(self):
        daniel_answer, _, backend, _, trace = self.ask("where does daniel richter work")
        slovakia_answer, _, _, _, _ = self.ask("who works in slovakia")

        self.assertGraphOnly(backend, trace)
        self.assertContainsAll(daniel_answer, ["Daniel Richter", "Bratislava", "Slovakia"])
        self.assertIn("Daniel Richter", slovakia_answer)

    def test_unknown_country_lists_available_countries_and_sites(self):
        answer, _, backend, query_state, trace = self.ask("who works in germany")

        self.assertGraphOnly(backend, trace)
        self.assertIn("could not find", answer.casefold())
        self.assertContainsAll(answer, ["Austria", "Czech Republic", "Slovakia", "Wien HQ"])
        self.assertEqual("membership", query_state["kind"])

    def test_czechia_alias_maps_to_czech_republic(self):
        answer, _, backend, query_state, trace = self.ask("who works in czechia")

        self.assertGraphOnly(backend, trace)
        self.assertIn("Klara Novak", answer)
        self.assertIn("Czech Republic", answer)
        self.assertEqual("Czech Republic", query_state["target"])

    def test_location_listing_returns_all_sites_not_short_preview(self):
        answer, evidence, backend, _, trace = self.ask("list all locations")

        self.assertGraphOnly(backend, trace)
        self.assertContainsAll(answer, ["Banska Bystrica", "Bratislava", "Bucharest", "Landgraaf", "Oberwart", "Warszawa", "Wien HQ"])
        self.assertGreaterEqual(len(evidence["top_nodes"]), 20)

    def test_people_keyword_api_returns_all_expected_matches_and_reasons(self):
        answer, evidence, backend, query_state, trace = self.ask("who works with api")

        self.assertGraphOnly(backend, trace)
        self.assertContainsAll(answer, ["Nina Havel", "Erik Sykora", "David Mraz"])
        self.assertContainsAll(answer, ["API design", "FastAPI", "API integrations"])
        self.assertEqual(["Nina Havel", "Erik Sykora", "David Mraz"], query_state["shown_people"])
        self.assertTrue(any(rel["type"] == "HAS_SKILL" for rel in evidence["relationships"]))

    def test_why_followup_explains_previous_people_keyword_answer(self):
        _, first_evidence, _, first_state, _ = self.ask("who works with api")
        answer, _, backend, state, trace = self.ask("why", last_query_state=first_state, last_evidence=first_evidence)

        self.assertGraphOnly(backend, trace)
        self.assertEqual(first_state, state)
        self.assertContainsAll(answer, ["Nina Havel", "Erik Sykora", "David Mraz", "API design", "FastAPI", "API integrations"])

    def test_person_concept_detects_skill_without_requiring_exact_wording(self):
        answer, evidence, backend, _, trace = self.ask("does david know api integration")

        self.assertGraphOnly(backend, trace)
        self.assertContainsAll(answer, ["David Mraz", "API integrations"])
        self.assertTrue(any(rel["type"] == "HAS_SKILL" for rel in evidence["relationships"]))

    def test_relationship_path_shared_site(self):
        answer, evidence, backend, state, trace = self.ask("are veronika and lucia connected?")

        self.assertGraphOnly(backend, trace)
        self.assertContainsAll(answer, ["Veronika Duda", "Lucia Benesova", "Banska Bystrica"])
        self.assertEqual("relationship_pair", state["kind"])
        self.assertTrue(evidence["relationships"])

    def test_relationship_path_shared_manager(self):
        answer, evidence, backend, state, trace = self.ask("is petra and filip connected somehow")

        self.assertGraphOnly(backend, trace)
        self.assertContainsAll(answer, ["Petra Novakova", "Filip Hruby", "Lukas Steiner"])
        self.assertEqual("relationship_pair", state["kind"])
        self.assertTrue(any(rel["type"] == "REPORTS_TO" for rel in evidence["relationships"]))

    def test_typo_in_name_returns_safe_close_match_instead_of_bad_graph_result(self):
        answer, _, backend, query_state, trace = self.ask("who works with úetra")

        self.assertGraphOnly(backend, trace)
        self.assertContainsAll(answer, ["could not find the exact person or role", "Petra Novakova", "HR Director"])
        self.assertNotIn("Multi-site", answer)
        self.assertEqual("pending_suggestion", query_state["kind"])
        self.assertEqual("Petra Novakova", query_state["suggested_name"])

    def test_structural_typo_woth_is_corrected(self):
        self.assertEqual("who works with people", app.expand_query("who works woth people"))

        answer, _, backend, query_state, trace = self.ask("who works woth people")

        self.assertGraphOnly(backend, trace)
        self.assertIn("Petra Novakova", answer)
        self.assertEqual("people", query_state["target"])


if __name__ == "__main__":
    unittest.main()
