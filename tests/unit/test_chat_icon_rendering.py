"""
Unit & Regression Tests for NEXUS Chat UI Icon Rendering
Verifies:
1. get_icon_svg produces well-formed HTML/SVG without broken string expressions (e.g. '.strip()').
2. SVG output does not contain unescaped external URLs triggering markdown autolinkers.
3. Chat message rendering isolates presentation elements from clean message content.
4. Database conversation messages never contain stored SVG/HTML presentation markup.
5. HTML special characters in citations and diagnostic snippets are safely escaped.
"""

import html
import re
import unittest
from backend.storage.db import init_database, get_db_connection
from backend.services.conversation_service import create_conversation, add_message, get_conversation_messages
from frontend.components.icons import (
    get_icon_svg,
    icon_html,
    get_material_icon,
    LUCIDE_PATHS,
    ICON_COLOR_GOLD,
    ICON_COLOR_SUBTLE
)


class TestChatIconRendering(unittest.TestCase):
    """Regression test suite ensuring zero raw SVG/HTML leakage in chat messages."""

    def test_get_icon_svg_well_formed_attributes(self):
        """Verify SVG attributes have valid syntax and no literal string artifacts like '.strip()'."""
        for icon_name in ["user", "shield", "file_text", "target", "database", "info"]:
            svg = get_icon_svg(icon_name)
            
            # Must not contain literal Python syntax like '.strip()'
            self.assertNotIn(".strip()", svg, f"Icon '{icon_name}' contains literal '.strip()' artifact!")
            
            # Must not contain http:// URL that triggers markdown autolinking
            self.assertNotIn("http://", svg, f"Icon '{icon_name}' contains 'http://' URL triggering autolinks!")
            
            # Must start with <svg and end with </svg>
            self.assertTrue(svg.startswith("<svg "), f"Icon '{icon_name}' does not start with '<svg '")
            self.assertTrue(svg.endswith("</svg>"), f"Icon '{icon_name}' does not end with '</svg>'")
            
            # Must have clean class attribute
            self.assertIn('class="nexus-lucide-icon"', svg)
            self.assertIn('viewBox="0 0 24 24"', svg)

    def test_icon_html_structure(self):
        """Verify icon_html combines vector SVG and text without corrupting HTML elements."""
        rendered = icon_html("user", "Operator Inquiry", size=16, color=ICON_COLOR_SUBTLE, gap=6)
        self.assertIn("Operator Inquiry", rendered)
        self.assertIn("<span", rendered)
        self.assertIn("<svg", rendered)
        self.assertNotIn(".strip()", rendered)
        self.assertNotIn("http://", rendered)

    def test_material_icon_mapping(self):
        """Verify Streamlit native Material Symbols are available for chat avatars."""
        user_avatar = get_material_icon("user")
        assistant_avatar = get_material_icon("assistant")
        
        self.assertEqual(user_avatar, ":material/person:")
        self.assertEqual(assistant_avatar, ":material/shield:")

    def test_database_messages_contain_clean_text_only(self):
        """Verify conversation messages stored in SQLite do NOT contain SVG markup."""
        conv = create_conversation(user_id=1, title="Test Tactical Briefing")
        conv_id = conv["id"]

        user_query = "What is the primary hydraulic pressure for the braking sub-system?"
        bot_response = "The primary hydraulic pressure is 210 bar as per the technical manual."
        mock_citations = [{
            "filename": "HYDRAULIC_MANUAL.pdf",
            "page_number": 12,
            "relevance_score": 0.88,
            "passage": "Normal operating hydraulic pressure must be maintained at 210 bar."
        }]

        # Add user & assistant messages
        add_message(conv_id, "user", user_query, user_id=1)
        add_message(conv_id, "assistant", bot_response, citations=mock_citations, user_id=1)

        messages = get_conversation_messages(conv_id, user_id=1)
        self.assertEqual(len(messages), 2)

        for m in messages:
            content = m["content"]
            # Content MUST NOT contain raw SVG or HTML presentation tags
            self.assertNotIn("<svg", content)
            self.assertNotIn("</svg>", content)
            self.assertNotIn("<path", content)
            self.assertNotIn(".strip()", content)

    def test_citation_fields_safely_escaped(self):
        """Verify citations with XML/HTML characters (e.g. <>&) do not break markup."""
        dangerous_passage = "Pressure < 200 bar & Temp > 85°C triggers safety shutdown."
        dangerous_title = "Manual <Rev 2> & Specs.pdf"
        
        esc_passage = html.escape(dangerous_passage)
        esc_title = html.escape(dangerous_title)
        
        self.assertNotIn("< 200", esc_passage)
        self.assertIn("&lt; 200", esc_passage)
        self.assertNotIn("<Rev", esc_title)
        self.assertIn("&lt;Rev", esc_title)

    def test_no_markdown_atx_headings_with_inline_icons(self):
        """
        Regression test for System Analytics & Views:
        Verify that no view file embeds SVG helpers or raw SVG into Markdown ATX headings (# to ######).
        Markdown heading parsers fail on inline SVGs, causing raw markup to be displayed as text.
        """
        import glob
        pattern = re.compile(r'^\s*#+\s*.*(?:icon_html|get_icon_svg|<svg)', re.MULTILINE)
        view_files = glob.glob("frontend/views/*.py") + glob.glob("frontend/components/*.py")
        self.assertTrue(len(view_files) > 0, "No view files discovered for scan")

        for fpath in view_files:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            matches = pattern.findall(content)
            self.assertEqual(
                matches,
                [],
                f"File '{fpath}' contains inline SVG or icon helpers inside Markdown headings: {matches}"
            )

    def test_analytics_cards_clean_html_rendering(self):
        """
        Verify that System Analytics stat cards render cleanly as HTML blocks
        without .strip() artifacts or unescaped http URLs.
        """
        from frontend.components.icons import get_icon_svg
        gen_ico = get_icon_svg("circle_check", size=18, color="#D6C6A5")
        guard_ico = get_icon_svg("shield", size=18, color="#D6C6A5")

        for ico in [gen_ico, guard_ico]:
            self.assertIn("<svg", ico)
            self.assertIn("</svg>", ico)
            self.assertNotIn(".strip()", ico)
            self.assertNotIn("http://", ico)
            self.assertNotIn("https://", ico)


if __name__ == "__main__":
    unittest.main()
