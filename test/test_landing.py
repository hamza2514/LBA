import re

from streamlit.testing.v1 import AppTest

from core import landing_art as art
from core import landing_sections as sections


def test_compact_removes_indentation_and_blank_lines():
    out = sections.compact("<div>\n    <p>a</p>\n\n    <p>b</p>\n</div>")
    assert "\n" not in out and out == "<div> <p>a</p> <p>b</p> </div>"


def test_every_section_is_markdown_safe_html():
    for html in (sections.nav(), sections.hero_copy(), sections.scene(), sections.why(), sections.how(),
                 sections.features(), sections.band(None), sections.footer()):
        assert "\n" not in html and not re.search(r"\s{4,}", html)


def test_request_access_only_appears_with_a_contact_email():
    assert "Request access" not in sections.band(None)
    assert 'mailto:ops@example.com' in sections.band("ops@example.com")


def test_line_balance_matches_the_documented_definition():
    assert art.line_balance([50, 100]) == 75
    assert art.line_balance(art.SAMPLE_AFTER) > art.line_balance(art.SAMPLE_BEFORE)


def test_charts_are_valid_svg_roots():
    for svg in (art.bar_chart(art.SAMPLE_BEFORE, art.SAMPLE_TAKT), art.skill_grid(), art.factory_scene(), art.jeans()):
        assert svg.startswith("<svg") and svg.endswith("</svg>")


def _landing_app():
    from core import landing
    landing.render()


def test_sign_in_form_renders_and_rejects_bad_credentials(monkeypatch):
    from core import auth
    monkeypatch.setattr(auth, "needs_setup", lambda: False)
    monkeypatch.setattr(auth, "authenticate", lambda u, p: None)
    at = AppTest.from_function(_landing_app).run()
    assert not at.exception
    assert [t.label for t in at.text_input] == ["Username", "Password"]
    at.text_input[0].set_value("x")
    at.text_input[1].set_value("y")
    at.button[0].click().run()
    assert at.error[0].value == "Wrong username or password."


def test_first_run_shows_administrator_setup(monkeypatch):
    from core import auth
    monkeypatch.setattr(auth, "needs_setup", lambda: True)
    at = AppTest.from_function(_landing_app).run()
    assert not at.exception
    assert len(at.text_input) == 4
