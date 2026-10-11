from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "app" / "spatial-ui" / "public" / "krishna-display-fit.css").read_text(encoding="utf-8")
JS = (ROOT / "app" / "spatial-ui" / "public" / "krishna-display-fit.js").read_text(encoding="utf-8")
PREVIEW = (ROOT / "app" / "spatial-ui" / "src" / "LegacyKrishnaPreview.tsx").read_text(encoding="utf-8")


def test_display_fit_layer_is_loaded_last():
    assert "krishna-display-fit-style" in PREVIEW
    assert "krishna-display-fit-script" in PREVIEW
    assert PREVIEW.index("krishna-owner-corrections-style") < PREVIEW.index("krishna-display-fit-style")
    assert PREVIEW.index("krishna-apple-shell-script") < PREVIEW.index("krishna-display-fit-script")


def test_desktop_readability_is_not_tiny():
    assert "--rail:clamp(260px,18vw,360px)" in CSS
    assert "font-size:14px!important" in CSS
    assert "font-size:13px!important" in CSS
    assert "@media(min-width:1800px)" in CSS
    assert "@media(max-width:1450px)" in CSS


def test_krishna_has_lightweight_compositor_motion():
    assert "krishnaHeroFloat60" in CSS
    assert "krishnaOmBreath60" in CSS
    assert "will-change:transform" in CSS
    assert "@media(prefers-reduced-motion:reduce)" in CSS


def test_sudarshan_and_composer_cannot_leak_to_other_views():
    assert 'body:not([data-view="sudarshan"]) #sudarshan' in CSS
    assert 'body:not([data-view="sudarshan"]) .composerWrap' in CSS
    assert 'body:not([data-view="sudarshan"]) #liveWork' in CSS
    assert "sudarshan?.classList.remove('active')" in JS
    assert "composer.hidden = true" in JS
    assert "liveWork.hidden = true" in JS
    assert "main?.classList.remove('liveSplit')" in JS


def test_sudarshan_chat_is_centered_when_active():
    assert 'body[data-view="sudarshan"] #sudarshan .holoRail' in CSS
    assert "display:none!important" in CSS
    assert "width:min(100%,1080px)!important" in CSS
    assert "width:min(100%,980px)!important" in CSS


def test_real_browser_split_is_50_50_inside_sudarshan():
    assert 'body[data-view="sudarshan"] .main.liveSplit #sudarshan' in CSS
    assert "width:50%!important" in CSS
    assert "margin-right:50%!important" in CSS
    assert 'body[data-view="sudarshan"] #liveWork:not([hidden])' in CSS
