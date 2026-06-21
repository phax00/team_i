import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INDEX_HTML = DOCS / "index.html"
APP_JS = DOCS / "app.js"
STYLES_CSS = DOCS / "styles.css"
CORE_GRAPH = DOCS / "data" / "knowledge_graph_core_normalized.json"
DETAILED_GRAPH = DOCS / "data" / "knowledge_graph_school_mvp_normalized.json"


class VisualizerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index_html = INDEX_HTML.read_text(encoding="utf-8")
        cls.app_js = APP_JS.read_text(encoding="utf-8")
        cls.styles_css = STYLES_CSS.read_text(encoding="utf-8")
        cls.core = json.loads(CORE_GRAPH.read_text(encoding="utf-8"))
        cls.detailed = json.loads(DETAILED_GRAPH.read_text(encoding="utf-8"))

    def test_visualizer_entry_files_exist_and_are_linked(self):
        self.assertTrue(INDEX_HTML.exists())
        self.assertTrue(APP_JS.exists())
        self.assertTrue(STYLES_CSS.exists())
        self.assertRegex(self.index_html, r'src="\./app\.js(?:\?[^"]*)?"')
        self.assertRegex(self.index_html, r'href="\./styles\.css(?:\?[^"]*)?"')

    def test_visualizer_default_dataset_is_detailed_graph(self):
        self.assertRegex(self.app_js, r"datasetKey:\s*[\"']school[\"']")
        self.assertRegex(
            self.index_html,
            r'<button class="chip active" data-dataset="school">Detailed Graph</button>',
        )
        self.assertRegex(
            self.index_html,
            r'<button class="chip" data-dataset="core">Basic Graph</button>',
        )

    def test_visualizer_dataset_urls_match_existing_assets(self):
        self.assertIn("./data/knowledge_graph_core_normalized.json", self.app_js)
        self.assertIn("./data/knowledge_graph_school_mvp_normalized.json", self.app_js)
        self.assertEqual(568, len(self.core["nodes"]))
        self.assertEqual(746, len(self.core["relationships"]))
        self.assertEqual(678, len(self.detailed["nodes"]))
        self.assertEqual(1103, len(self.detailed["relationships"]))

    def test_visualizer_required_dom_hooks_are_present(self):
        required_ids = [
            "dataset-row",
            "preset-row",
            "graph-network",
            "graph-network-wrap",
            "stat-nodes",
            "stat-relationships",
            "stat-rendered-nodes",
            "stat-rendered-relationships",
            "selection-details",
            "details-body",
        ]
        for element_id in required_ids:
            self.assertIn(f'id="{element_id}"', self.index_html, msg=f"Missing DOM hook #{element_id}")
        self.assertIn('class="panel details-panel"', self.index_html)

    def test_visualizer_presets_cover_core_user_views(self):
        for preset in ["org", "skills", "job", "activity", "full"]:
            self.assertRegex(self.index_html, rf'data-preset="{preset}"')
            self.assertRegex(self.app_js, rf"{preset}:\s*\{{")

        self.assertIn("HAS_ROLE", self.app_js)
        self.assertIn("HAS_SKILL", self.app_js)
        self.assertIn("KNOWS_SYSTEM", self.app_js)
        self.assertIn("WORKED_ON_TICKET", self.app_js)

    def test_graph_assets_have_visualizer_required_fields(self):
        for graph in [self.core, self.detailed]:
            for node in graph["nodes"]:
                self.assertIn("id", node)
                self.assertIn("label", node)
                self.assertIn("name", node)
            for relationship in graph["relationships"]:
                self.assertIn("start", relationship)
                self.assertIn("end", relationship)
                self.assertIn("type", relationship)

    def test_visualizer_styles_keep_controls_rounded_and_scrollbar_customized(self):
        self.assertIn("border-radius", self.styles_css)
        self.assertIn("scrollbar", self.styles_css.casefold())
        self.assertIn(".filters-panel", self.styles_css)
        self.assertIn(".graph-stage", self.styles_css)

    def test_no_empty_default_graph_regression_markers(self):
        self.assertNotRegex(self.app_js, r"datasetKey:\s*[\"']core[\"']")
        self.assertNotIn("Org View - 0 nodes - 0 relationships", self.index_html)


if __name__ == "__main__":
    unittest.main()
