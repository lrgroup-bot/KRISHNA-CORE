from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "app" / "spatial-ui"
LOADER = (UI / "src" / "LegacyKrishnaPreview.tsx").read_text(encoding="utf-8")
CSS = (UI / "public" / "krishna-layout-guard.css").read_text(encoding="utf-8")
WEB = (ROOT / "core" / "web_validation.html").read_text(encoding="utf-8")


def test_layout_guard_loads_after_visual_layers():
    assert "krishna-layout-guard.css" in LOADER
    assert LOADER.index("krishna-layout-guard.css") > LOADER.index("krishna-live-feed-richtext.css")


def test_sidebar_is_compact_on_desktop():
    assert "--rail:clamp(208px,12vw,232px)" in CSS
    assert "--rail:232px" in CSS
    assert "--rail:208px" in CSS


def test_composer_is_positioned_inside_main_not_offset_twice():
    assert '<div class="composerWrap">' in WEB
    assert "position:absolute!important" in CSS
    assert "left:0!important" in CSS
    assert "body[data-view=\"sudarshan\"] .composerWrap" in CSS


def test_garudanetra_is_exactly_half_of_main_on_desktop():
    assert "#liveWork:not([hidden])" in CSS
    assert "position:absolute!important" in CSS
    assert "width:50%!important" in CSS
    assert ".main.liveSplit #sudarshan" in CSS
    assert "right:50%!important" in CSS


def test_garudanetra_expand_control_still_works():
    assert "#liveWork.expanded:not([hidden])" in CSS
    assert "width:100%!important" in CSS


def test_chat_and_project_overflow_buttons_are_always_visible():
    assert ".chatMore" in CSS
    assert ".projectBranchMore" in CSS
    assert "opacity:1!important" in CSS
    assert "visibility:visible!important" in CSS


def test_60hz_motion_prefers_compositor_friendly_properties():
    assert "krishnaOmCompositorBreath" in CSS
    assert "will-change:transform,opacity" in CSS
    assert "backdrop-filter:blur(14px)" in CSS
    assert "contain:layout paint" in CSS
