from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREVIEW = (ROOT / "app" / "spatial-ui" / "src" / "LegacyKrishnaPreview.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "app" / "spatial-ui" / "public" / "krishna-command-core.css").read_text(encoding="utf-8")
JS = (ROOT / "app" / "spatial-ui" / "public" / "krishna-command-core.js").read_text(encoding="utf-8")


def test_command_core_is_loaded_after_display_fit():
    assert "krishna-command-core.css" in PREVIEW
    assert "krishna-command-core.js" in PREVIEW
    assert PREVIEW.index("krishna-display-fit.css") < PREVIEW.index("krishna-command-core.css")
    assert PREVIEW.index("krishna-display-fit.js") < PREVIEW.index("krishna-command-core.js")


def test_sidebar_recovers_live_data_and_never_stays_blank_offline():
    assert "fetchJson('/api/projects')" in JS
    assert "fetchJson('/api/chats')" in JS
    assert "window.refreshSidebarData" in JS
    assert "Core offline · projects will appear automatically" in JS
    assert "Core offline · chat history will appear automatically" in JS
    assert "No projects yet · use + to create one" in JS
    assert "No chats yet · use + to start Sudarshan" in JS


def test_active_navigation_is_reconciled_from_real_view_state():
    assert "document.body.dataset.view" in JS
    assert "button.classList.toggle('active', active)" in JS
    assert "button.setAttribute('aria-current', 'page')" in JS
    assert "kbNavLR" in JS and "kbNavBrahmand" in JS


def test_cinematic_surface_has_live_hud_and_ai_motion():
    assert "krishnaCommandHud" in JS
    assert "KRISHNA CORE" in JS
    assert "ACTIVE CHAMBER" in JS
    assert "kcRingTiltA" in CSS
    assert "kcOrbitA" in CSS
    assert "kcConversationSweep" in CSS
    assert "--kc-cyan:#4ee7ff" in CSS
    assert "--kc-gold:#f5ca68" in CSS


def test_cinematic_motion_respects_reduced_motion():
    assert "@media(prefers-reduced-motion:reduce)" in CSS


def test_sidebar_action_controls_remain_visible():
    assert ".chatMore" in CSS
    assert ".projectBranchMore" in CSS
    assert "font-size:17px" in CSS
