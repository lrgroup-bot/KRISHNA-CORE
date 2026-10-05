from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
JS = ROOT / "app" / "spatial-ui" / "public" / "operational-dashboard.js"
CSS = ROOT / "app" / "spatial-ui" / "public" / "operational-dashboard.css"
PREVIEW = ROOT / "app" / "spatial-ui" / "public" / "operational-preview.html"
LEGACY = ROOT / "app" / "spatial-ui" / "public" / "legacy-dashboard.html"

SYSTEM_IDS = (
    "krishna", "brahma", "sudarshan", "hawkeye", "kabach", "garuda",
    "garudanetra", "narad", "brahmagyan", "gyan", "rishi", "amcc",
    "suryadev", "chandradev", "mrityunjaya", "ui_guardian", "developer",
    "specialists", "perfection", "vishvakarma",
)


def _read(path):
    return path.read_text(encoding="utf-8")


def test_operational_overlay_covers_every_upper_system():
    js = _read(JS)
    for system_id in SYSTEM_IDS:
        assert f"{system_id}:{{" in js, system_id
    assert "chandradev:{" in js
    assert "amcc:{" in js
    assert "hawkeye:{" in js


def test_owner_dashboard_uses_plain_operational_sections():
    js = _read(JS)
    for label in ("WORKING NOW", "DONE", "NEXT", "OWNER APPROVAL", "LAST ACTIVITY"):
        assert label in js
    assert "Technical details (only when needed)" in js
    assert "No separate detailed telemetry endpoint" in js


def test_status_semantics_do_not_call_idle_an_error():
    js = _read(JS)
    css = _read(CSS)
    assert "['idle','ready','landed','stopped',''].includes(s)) return 'ready'" in js
    assert "attention:'op-attention'" in js
    assert ".orbitDot.idle{background:var(--op-amber)!important" in css
    assert ".godLight.op-attention{background:var(--op-red)!important" in css


def test_progress_is_only_shown_when_runtime_reports_progress():
    js = _read(JS)
    assert "function realProgress(data)" in js
    assert "progress_percent" in js
    assert "completion_percent" in js
    assert "wrap.hidden=pct===null" in js
    assert "50% complete" not in js


def test_sudarshan_composer_is_command_first():
    js = _read(JS)
    for label in ("file", "plugin", "project", "investigate", "research"):
        assert f"label.includes('{label}')" in js
    assert "Tell KRISHNA what you want done" in js
    assert "Run command through Sudarshan" in js
    assert "No system may bypass Sudarshan" in js


def test_upper_buttons_have_visible_letters_and_3d_depth():
    js = _read(JS)
    css = _read(CSS)
    assert "mark:'CH'" in js
    assert "mark:'AM'" in js
    assert "mark:'HW'" in js
    assert "perspective(220px)" in css
    assert "box-shadow:" in css
    assert ".miniGodName" in css


def test_preview_is_same_origin_and_keeps_stable_dashboard_untouched():
    preview = _read(PREVIEW)
    assert LEGACY.is_file()
    assert 'src="/spatial/legacy-dashboard.html"' in preview
    assert "/spatial/operational-dashboard.css" in preview
    assert "/spatial/operational-dashboard.js" in preview
    assert "stable dashboard is preserved" in preview.lower()
