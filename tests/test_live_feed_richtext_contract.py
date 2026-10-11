from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "app" / "spatial-ui"
LOADER = (UI / "src" / "LegacyKrishnaPreview.tsx").read_text(encoding="utf-8")
JS = (UI / "public" / "krishna-live-feed-richtext.js").read_text(encoding="utf-8")
CSS = (UI / "public" / "krishna-live-feed-richtext.css").read_text(encoding="utf-8")


def test_live_feed_is_loaded_by_preview():
    assert "krishna-live-feed-richtext.css" in LOADER
    assert "krishna-live-feed-richtext.js" in LOADER
    assert "__KRISHNA_LIVE_FEED_RICHTEXT__" in LOADER


def test_feed_uses_real_dashboard_telemetry():
    assert "fetch('/api/dashboard'" in JS
    assert "current_activity" in JS
    assert "payload?.recent" in JS
    assert "LIVE INTELLIGENCE FEED" in JS
    assert "CORE OFFLINE" in JS
    assert "setInterval(() => { void refreshFeed(); }, 2000)" in JS


def test_rich_text_supports_markdown_code_and_tables_without_raw_html_input():
    assert "markdownToHtml" in JS
    assert "kc-code-block" in JS
    assert "kc-table-wrap" in JS
    assert "safeUrl" in JS
    assert "escapeHtml" in JS
    assert "window.addMsg" in JS
    assert "upgradeExistingMessages" in JS


def test_rich_text_and_feed_are_visually_present():
    assert ".kc-live-feed" in CSS
    assert ".kc-feed-row" in CSS
    assert ".kc-rich-text" in CSS
    assert ".kc-code-block" in CSS
    assert ".kc-table-wrap" in CSS
