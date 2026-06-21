import json
import unittest
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_GRAPH = ROOT / "docs" / "data" / "knowledge_graph_core_normalized.json"
DETAILED_GRAPH = ROOT / "docs" / "data" / "knowledge_graph_school_mvp_normalized.json"


class GraphIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(CORE_GRAPH.read_text(encoding="utf-8"))
        cls.detailed = json.loads(DETAILED_GRAPH.read_text(encoding="utf-8"))
        cls.nodes = cls.detailed["nodes"]
        cls.relationships = cls.detailed["relationships"]
        cls.by_id = {node["id"]: node for node in cls.nodes}
        cls.rels_by_start = defaultdict(list)
        cls.rels_by_end = defaultdict(list)
        for rel in cls.relationships:
            cls.rels_by_start[rel["start"]].append(rel)
            cls.rels_by_end[rel["end"]].append(rel)

    def nodes_by_label(self, label):
        return [node for node in self.nodes if node.get("label") == label]

    def test_graph_sizes_match_expected_mvp_scale(self):
        self.assertEqual(568, len(self.core["nodes"]))
        self.assertEqual(746, len(self.core["relationships"]))
        self.assertEqual(678, len(self.detailed["nodes"]))
        self.assertEqual(1103, len(self.detailed["relationships"]))

    def test_node_ids_are_unique_and_named(self):
        ids = [node["id"] for node in self.nodes]
        self.assertEqual(len(ids), len(set(ids)))

        unnamed = [
            node["id"]
            for node in self.nodes
            if node.get("label") in {"Person", "Role", "Team", "Department", "Site", "Country", "Skill", "System"}
            and not str(node.get("name", "")).strip()
        ]
        self.assertEqual([], unnamed)

    def test_relationship_endpoints_exist(self):
        missing = [
            rel
            for rel in self.relationships
            if rel.get("start") not in self.by_id or rel.get("end") not in self.by_id
        ]
        self.assertEqual([], missing)

    def test_expected_labels_and_relationship_types_exist(self):
        label_counts = Counter(node.get("label") for node in self.nodes)
        relationship_types = {rel["type"] for rel in self.relationships}

        for label in ["Person", "Role", "JobDescription", "Team", "Department", "Site", "Country", "Skill", "System", "Topic"]:
            self.assertGreater(label_counts[label], 0, msg=f"Missing node label {label}")

        for rel_type in [
            "HAS_ROLE",
            "REPORTS_TO",
            "MEMBER_OF",
            "AT_SITE",
            "LOCATED_IN",
            "HAS_SKILL",
            "KNOWS_SYSTEM",
            "OWNS_TOPIC",
            "LINKED_TO_JD",
        ]:
            self.assertIn(rel_type, relationship_types)

    def test_each_person_has_core_organizational_context(self):
        people_without_role = []
        people_without_team = []
        people_without_site = []

        for person in self.nodes_by_label("Person"):
            rel_types = {rel["type"] for rel in self.rels_by_start[person["id"]]}
            if "HAS_ROLE" not in rel_types:
                people_without_role.append(person["name"])
            if "MEMBER_OF" not in rel_types:
                people_without_team.append(person["name"])
            if "AT_SITE" not in rel_types:
                people_without_site.append(person["name"])

        self.assertEqual([], people_without_role)
        self.assertEqual([], people_without_team)
        self.assertEqual([], people_without_site)

    def test_every_person_has_country_or_explicit_multi_site_context(self):
        missing_location_context = []

        for person in self.nodes_by_label("Person"):
            has_direct_country = any(rel["type"] == "LOCATED_IN" for rel in self.rels_by_start[person["id"]])
            site_ids = [rel["end"] for rel in self.rels_by_start[person["id"]] if rel["type"] == "AT_SITE"]
            has_site_country = any(
                any(site_rel["type"] == "IN_COUNTRY" for site_rel in self.rels_by_start[site_id])
                for site_id in site_ids
            )
            site_names = [self.by_id[site_id].get("name", "") for site_id in site_ids]
            person_location_context = str(person.get("location_context", ""))
            has_multi_site_context = any(
                marker.lower() in f"{person_location_context} {' '.join(site_names)}".lower()
                for marker in ["multi-site", "group", "enterprise", "all production sites"]
            )
            if not has_direct_country and not has_site_country and not has_multi_site_context:
                missing_location_context.append(person["name"])

        self.assertEqual([], missing_location_context)

    def test_business_critical_entities_are_present(self):
        names_by_label = defaultdict(set)
        for node in self.nodes:
            names_by_label[node.get("label")].add(node.get("name"))

        self.assertIn("Eva Kralikova", names_by_label["Person"])
        self.assertIn("Filip Hruby", names_by_label["Person"])
        self.assertIn("Petra Novakova", names_by_label["Person"])
        self.assertIn("Chief Operating Officer", names_by_label["Role"])
        self.assertIn("IT Director / Head of IT", names_by_label["Role"])
        self.assertIn("Human Resources", names_by_label["Department"])
        self.assertIn("Slovakia", names_by_label["Country"])
        self.assertIn("ERP", names_by_label["System"])
        self.assertIn("Python", names_by_label["Skill"])

    def test_erp_system_has_people_and_empty_erp_skill_does_not_drive_system_answer(self):
        erp_system = next(node for node in self.nodes if node.get("label") == "System" and node.get("name") == "ERP")
        erp_system_people = [
            self.by_id[rel["start"]]["name"]
            for rel in self.rels_by_end[erp_system["id"]]
            if rel["type"] == "KNOWS_SYSTEM" and self.by_id[rel["start"]].get("label") == "Person"
        ]

        self.assertGreaterEqual(len(erp_system_people), 9)
        self.assertIn("Filip Hruby", erp_system_people)
        self.assertIn("Zuzana Balaz", erp_system_people)


if __name__ == "__main__":
    unittest.main()
