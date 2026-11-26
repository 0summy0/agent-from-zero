import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_4_2_browser_use",
    ROOT / "chapters" / "stage4-orchestration" / "browser_use.py",
)
browser_use = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(browser_use)


def test_chapter_module_imports():
    assert browser_use.CHAPTER_ID == "4.2-browser-use"
    assert callable(browser_use.run_minimal_path)


def test_extracts_title_visible_text_and_links():
    page = browser_use.parse_html(
        """<!doctype html><html><head><title> Local &amp; stable </title></head>
        <body><h1>Hello <em>world</em></h1><p>First paragraph.</p>
        <p>Second <a href="local://docs">Read <strong>docs</strong></a>.</p>
        <script>invisibleScript()</script><style>.invisible {}</style>
        <div hidden />invisibleAttribute<noscript>invisibleFallback</noscript>
        </body></html>"""
    )
    assert page["title"] == "Local & stable"
    assert page["text"] == "Hello world First paragraph. Second Read docs."
    assert page["links"] == [{"text": "Read docs", "href": "local://docs"}]
    assert "invisible" not in page["text"]


def test_builtin_homepage_has_expected_navigation():
    browser = browser_use.BrowserTool()
    home = browser.open_page(browser_use.HOME_URL)
    assert browser.current_url() == browser_use.HOME_URL
    assert home["title"] == "Agent From Zero - Home"
    assert [link["text"] for link in home["links"]] == ["Documentation", "Contact"]


def test_click_link_navigates_by_visible_text():
    browser = browser_use.BrowserTool()
    browser.open_page(browser_use.HOME_URL)
    docs = browser.click_link("  documentation ")
    assert browser.current_url() == browser_use.DOCS_URL
    assert docs["title"] == "Agent From Zero - Documentation"
    assert "Observe the page" in docs["text"]
    contact = browser.click_link("Contact")
    assert browser.current_url() == browser_use.CONTACT_URL
    assert contact["title"] == "Agent From Zero - Contact"
    browser.click_link("Home")
    assert browser.current_url() == browser_use.HOME_URL


def test_unknown_link_is_rejected_without_changing_page():
    browser = browser_use.BrowserTool()
    browser.open_page(browser_use.HOME_URL)
    with pytest.raises(ValueError, match="unknown link text"):
        browser.click_link("Delete account")
    assert browser.current_url() == browser_use.HOME_URL
    assert browser.open_page(browser_use.HOME_URL)["title"] == "Agent From Zero - Home"


def test_click_requires_an_open_page():
    with pytest.raises(ValueError, match="open a page"):
        browser_use.BrowserTool().click_link("Documentation")


def test_external_or_unknown_pages_are_rejected():
    browser = browser_use.BrowserTool()
    for url in ("https://example.com", "local://missing"):
        with pytest.raises(ValueError, match="unknown local page"):
            browser.open_page(url)
    assert browser.current_url() is None


def test_page_isolation_between_instances():
    first = browser_use.BrowserTool()
    second = browser_use.BrowserTool()
    first.open_page(browser_use.HOME_URL)
    first.click_link("Documentation")
    assert first.current_url() == browser_use.DOCS_URL
    assert second.current_url() is None
    second.open_page(browser_use.CONTACT_URL)
    assert first.current_url() == browser_use.DOCS_URL
    assert second.current_url() == browser_use.CONTACT_URL


def test_snapshots_do_not_expose_mutable_page_state():
    browser = browser_use.BrowserTool()
    snapshot = browser.open_page(browser_use.HOME_URL)
    snapshot["links"].clear()
    snapshot["title"] = "Changed by caller"
    fresh = browser.open_page(browser_use.HOME_URL)
    assert fresh["title"] == "Agent From Zero - Home"
    assert len(fresh["links"]) == 2


def test_minimal_path_is_serializable_and_deterministic():
    first = browser_use.run_minimal_path()
    second = browser_use.run_minimal_path()
    assert first == second
    assert json.loads(json.dumps(first, ensure_ascii=False)) == first
    assert first["chapter"] == browser_use.CHAPTER_ID
    assert first["url"] == browser_use.DOCS_URL
    assert first["title"] == "Agent From Zero - Documentation"
    assert "Observe the page" in first["text_summary"]
    assert len(first["text_summary"]) <= 160


def test_main_prints_json(capsys):
    browser_use.main()
    output = capsys.readouterr().out
    assert json.loads(output) == browser_use.run_minimal_path()
