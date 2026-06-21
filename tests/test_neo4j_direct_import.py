import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "neo4j" / "import_graph_to_neo4j.py"
DETAILED_GRAPH = ROOT / "docs" / "data" / "knowledge_graph_school_mvp_normalized.json"


def load_importer_module():
    spec = importlib.util.spec_from_file_location("skillwiki_neo4j_importer", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Neo4jDirectImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.importer = load_importer_module()
        cls.graph = json.loads(DETAILED_GRAPH.read_text(encoding="utf-8"))

    def test_detailed_graph_validates_for_direct_import(self):
        summary = self.importer.validate_graph(self.graph)

        self.assertEqual(678, summary["nodes"])
        self.assertEqual(1103, summary["relationships"])
        self.assertEqual(15, summary["labels"])
        self.assertEqual(28, summary["relationship_types"])

    def test_node_rows_preserve_labels_and_properties(self):
        grouped = self.importer.prepare_node_rows(self.graph["nodes"])

        self.assertIn("Person", grouped)
        self.assertEqual(32, len(grouped["Person"]))
        self.assertIn("id", grouped["Person"][0])
        self.assertIn("properties", grouped["Person"][0])

    def test_relationship_rows_preserve_types_and_endpoints(self):
        grouped = self.importer.prepare_relationship_rows(self.graph["relationships"])

        self.assertIn("REPORTS_TO", grouped)
        self.assertEqual(31, len(grouped["REPORTS_TO"]))
        self.assertIn("start_id", grouped["REPORTS_TO"][0])
        self.assertIn("end_id", grouped["REPORTS_TO"][0])
        self.assertIn("import_key", grouped["REPORTS_TO"][0])

    def test_parallel_relationships_receive_distinct_stable_import_keys(self):
        grouped = self.importer.prepare_relationship_rows(self.graph["relationships"])
        python_edges = [
            row
            for row in grouped["HAS_SKILL"]
            if row["start_id"] == "Person:david-mraz"
            and row["end_id"] == "Skill:python"
        ]

        self.assertEqual(2, len(python_edges))
        self.assertEqual(2, len({row["import_key"] for row in python_edges}))
        self.assertEqual(
            {"person_specific", "github_activity"},
            {row["properties"]["source"] for row in python_edges},
        )

    def test_nested_properties_are_serialized_for_neo4j(self):
        self.assertEqual('{"a": 1}', self.importer.normalize_property({"a": 1}))
        self.assertEqual(["A", "B"], self.importer.normalize_property(["A", "B"]))

    def test_invalid_dynamic_token_is_rejected(self):
        with self.assertRaises(ValueError):
            self.importer.sanitize_token("Person`) MATCH (n) DELETE n //", "label")

    def test_replace_requires_explicit_confirmation(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--dataset",
                "detailed",
                "--dry-run",
                "--replace",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("--replace requires --confirm-replace", result.stderr)

    def test_dry_run_validates_without_neo4j_connection(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--dataset", "detailed", "--dry-run"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, msg=result.stderr)
        self.assertIn("678 nodes", result.stdout)
        self.assertIn("1103 relationships", result.stdout)
        self.assertIn("Neo4j was not modified", result.stdout)


if __name__ == "__main__":
    unittest.main()
