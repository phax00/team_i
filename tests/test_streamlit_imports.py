import importlib
import unittest


class StreamlitImportSmokeTests(unittest.TestCase):
    def test_main_streamlit_app_imports_and_exposes_expected_api(self):
        app = importlib.import_module("streamlit_app")

        for attribute in [
            "answer_question",
            "build_indexes",
            "load_graph",
            "provider_chain",
            "skillwiki_brand_html",
            "skillwiki_logo_src",
            "main",
        ]:
            self.assertTrue(hasattr(app, attribute), msg=f"streamlit_app is missing {attribute}")

    def test_clean_streamlit_app_imports_and_exposes_expected_api(self):
        clean_app = importlib.import_module("streamlit_app_clean")

        for attribute in [
            "build_sidebar",
            "clean_brand_html",
            "clean_logo_src",
            "render_message",
            "main",
        ]:
            self.assertTrue(hasattr(clean_app, attribute), msg=f"streamlit_app_clean is missing {attribute}")

    def test_main_brand_helper_returns_safe_html(self):
        app = importlib.import_module("streamlit_app")
        brand_html = app.skillwiki_brand_html(compact=True)

        self.assertIn("Skill", brand_html)
        self.assertIn("Wiki", brand_html)
        self.assertIn("<img", brand_html)
        self.assertIn("data:image/", brand_html)
        self.assertNotIn("</div>\n    </div>", brand_html)

    def test_clean_brand_helper_returns_safe_html(self):
        clean_app = importlib.import_module("streamlit_app_clean")
        brand_html = clean_app.clean_brand_html(compact=True)

        self.assertIn("Skill", brand_html)
        self.assertIn("Wiki", brand_html)
        self.assertIn("<img", brand_html)
        self.assertIn("data:image/", brand_html)
        self.assertNotIn("</div>\n    </div>", brand_html)

    def test_clean_and_main_apps_share_graph_options(self):
        app = importlib.import_module("streamlit_app")
        clean_app = importlib.import_module("streamlit_app_clean")

        self.assertTrue(hasattr(clean_app, "core"))
        self.assertIs(clean_app.core, app)
        self.assertIn("Basic Graph", app.GRAPH_OPTIONS)
        self.assertIn("Detailed Graph", app.GRAPH_OPTIONS)


if __name__ == "__main__":
    unittest.main()
