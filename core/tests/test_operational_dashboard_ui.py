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
    assert "window.KRISHNA_OPERATIONAL_UI" in js
    assert "2026.10-spatial-command-os-v1" in js


def test_owner_dashboard_uses_one_plain_operational_grammar():
    js = _read(JS)
    for label in (
        "WHAT THIS SYSTEM DOES",
        "WORKING NOW",
        "PROGRESS",
        "COMPLETED RECENTLY",
        "PROBLEMS",
        "NEEDS PARTHA",
        "NEXT",
        "RECENT HISTORY",
        "Advanced / evidence",
    ):
        assert label in js
    assert "No separate detailed telemetry endpoint" in js
    assert "OWNER VIEW · READ ONLY" in js


def test_status_semantics_do_not_call_idle_an_error():
    js = _read(JS)
    css = _read(CSS)
    assert "['idle','ready','landed','stopped',''].includes(s)) return 'ready'" in js
    assert "ready:'IDLE'" in js
    assert "healing:'HEALING'" in js
    assert "attention:'BLOCKED'" in js
    assert ".orbitDot.idle{background:var(--op-gold)!important" in css
    assert ".godLight.op-healing" in css
    assert ".godLight.op-attention,.godLight.status-red{background:var(--op-red)!important" in css


def test_progress_never_fabricates_a_percentage():
    js = _read(JS)
    assert "function realProgress(data)" in js
    assert "progress_percent" in js
    assert "completion_percent" in js
    assert "No percentage reported by this system" in js
    assert "50% complete" not in js
    assert "pct+'%'" in js


def test_sudarshan_composer_is_command_first():
    js = _read(JS)
    css = _read(CSS)
    assert "button.dataset.opHidden='true'" in js
    assert ".composeFoot .tools{display:none!important}" in css
    assert "Tell KRISHNA what you want done" in js
    assert "Run command through Sudarshan" in js
    assert "Mutating and external actions remain behind Sudarshan" in js


def test_upper_buttons_have_visible_letters_state_and_3d_depth():
    js = _read(JS)
    css = _read(CSS)
    assert "mark:'CH'" in js
    assert "mark:'AM'" in js
    assert "mark:'HW'" in js
    assert "perspective(260px)" in css
    assert "box-shadow:" in css
    assert ".miniGodName" in css
    assert ".miniGodState" in css
    assert "clip:auto!important" in css


def test_home_command_deck_summarizes_system_state():
    js = _read(JS)
    css = _read(CSS)
    assert "KRISHNA SPATIAL COMMAND OS" in js
    assert "One command. Verified execution." in js
    assert "opCountWorking" in js
    assert "opCountIdle" in js
    assert "opCountHealing" in js
    assert "opCountAttention" in js
    assert ".opHomeDeck" in css


def test_preview_is_same_origin_and_keeps_verified_dashboard_untouched():
    preview = _read(PREVIEW)
    assert LEGACY.is_file()
    assert 'src="/spatial/legacy-dashboard.html"' in preview
    assert "/spatial/operational-dashboard.css" in preview
    assert "/spatial/operational-dashboard.js" in preview
    assert "verified dashboard is preserved" in preview.lower()
    assert "has not been promoted" in preview.lower()
