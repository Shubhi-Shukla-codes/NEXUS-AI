"""
NEXUS Frontend UI & Application Shell Unit Tests
Validates theme color tokens, logo rendering, view module imports, and layout integrity.
"""

import sys
import unittest
from pathlib import Path

# Ensure root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestFrontendFoundation(unittest.TestCase):
    """Test suite for Phase 1 UI components, views, and styling."""

    def test_theme_css_exists_and_contains_color_tokens(self):
        """Verify theme.css exists and defines the tactical camouflage color palette."""
        css_path = PROJECT_ROOT / "frontend" / "styles" / "theme.css"
        self.assertTrue(css_path.is_file(), f"Missing theme CSS at: {css_path}")
        
        content = css_path.read_text(encoding="utf-8")
        required_tokens = [
            "--olive-drab: #556B2F",
            "--army-green: #4B5320",
            "--deep-tactical: #26382B",
            "--khaki: #C3B091",
            "--sand-beige: #D6C6A5",
            "--off-white: #F4F2E9",
            "--charcoal: #202820",
            "--muted-gold: #B49A5A",
        ]
        for token in required_tokens:
            self.assertIn(
                token,
                content,
                f"Required tactical color token not defined in CSS: {token}"
            )

    def test_logo_generation_all_sizes(self):
        """Verify vector logo generator works across all required responsive sizes."""
        from frontend.components.logo import get_nexus_logo_svg

        # Test icon size
        icon_svg = get_nexus_logo_svg(size="icon")
        self.assertIn("<svg", icon_svg)
        self.assertIn("viewBox", icon_svg)

        # Test favicon size
        fav_svg = get_nexus_logo_svg(size="favicon")
        self.assertIn('width="32"', fav_svg)

        # Test sidebar size
        sidebar_html = get_nexus_logo_svg(size="sidebar")
        self.assertIn("NEXUS", sidebar_html)
        self.assertIn("INTELLIGENCE", sidebar_html)

        # Test full wordmark
        full_html = get_nexus_logo_svg(size="full")
        self.assertIn("NE", full_html)
        self.assertIn("X", full_html)
        self.assertIn("US", full_html)
        self.assertIn("OFFLINE-FIRST", full_html)

    def test_view_modules_importability(self):
        """Ensure all required views import without errors."""
        import frontend.views.dashboard as v_dash
        import frontend.views.chat as v_chat
        import frontend.views.repository as v_repo
        import frontend.views.ingest as v_ingest
        import frontend.views.analytics as v_anal
        import frontend.views.settings as v_sett
        import frontend.views.login as v_login

        self.assertTrue(callable(v_dash.render_dashboard_view))
        self.assertTrue(callable(v_chat.render_chat_view))
        self.assertTrue(callable(v_repo.render_repository_view))
        self.assertTrue(callable(v_ingest.render_ingest_view))
        self.assertTrue(callable(v_anal.render_analytics_view))
        self.assertTrue(callable(v_sett.render_settings_view))
        self.assertTrue(callable(v_login.render_login_view))

    def test_components_importability(self):
        """Ensure reusable header, sidebar, and cards import cleanly."""
        import frontend.components.header as c_head
        import frontend.components.sidebar as c_side
        import frontend.components.citation_card as c_cite
        import frontend.components.document_card as c_doc

        self.assertTrue(callable(c_head.render_header))
        self.assertTrue(callable(c_side.render_sidebar))
        self.assertTrue(callable(c_cite.render_citation_card))
        self.assertTrue(callable(c_cite.render_citations_list))
        self.assertTrue(callable(c_doc.render_document_card))

    def test_app_entrypoint_exists(self):
        """Verify app.py master entry point exists and defines main function."""
        import app
        self.assertTrue(callable(app.main))


if __name__ == "__main__":
    unittest.main()
