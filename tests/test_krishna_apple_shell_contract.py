from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL_CSS = (ROOT / "app" / "spatial-ui" / "public" / "krishna-apple-shell.css").read_text(encoding="utf-8")
SHELL_JS = (ROOT / "app" / "spatial-ui" / "public" / "krishna-apple-shell.js").read_text(encoding="utf-8")
PREVIEW = (ROOT / "app" / "spatial-ui" / "src" / "LegacyKrishnaPreview.tsx").read_text(encoding="utf-8")
PREFLIGHT = (ROOT / "app" / "spatial-ui" / "public" / "krishna-brahmand-preflight.js").read_text(encoding="utf-8")


def test_premium_shell_and_functional_priority_are_both_preserved():
    assert "krishna-apple-shell.css" in PREVIEW
    assert "krishna-apple-shell.js" in PREVIEW
    # Behavior corrections execute before premium JS so the shell can layer its
    # presentation, but functional CSS is linked last so cosmetics cannot hide
    # controls or break the canonical browser split.
    assert PREVIEW.index("krishna-owner-corrections.js") < PREVIEW.index("krishna-apple-shell.js")
    shell_style = "ensureStyle('krishna-apple-shell-style'"
    correction_style = "ensureStyle('krishna-owner-corrections-style'"
    assert PREVIEW.index(shell_style) < PREVIEW.index(correction_style)


def test_sidebar_is_product_navigation_not_dense_dashboard():
    for token in (
        "--rail:272px",
        ".sidebarWorkspace",
        ".appleSectionLabel",
        ".apple-section-collapsed",
        ".chatSearchWrap",
        "#kbOwnerLoad",
        "#kbMobileCard",
    ):
        assert token in SHELL_CSS
    assert "LOCAL INTELLIGENCE SYSTEM" in SHELL_JS
    assert "addSectionToggle('projects', 'PROJECTS')" in SHELL_JS
    assert "addSectionToggle('chats', 'CHATS')" in SHELL_JS


def test_home_uses_premium_centered_product_hero():
    for token in (
        ".appleHeroEyebrow",
        ".appleHeroTitle",
        ".appleHeroSubtitle",
        ".appleHeroActions",
        "#assistantOm",
        "Quiet power. Clear control.",
    ):
        assert token in SHELL_CSS or token in SHELL_JS
    assert "Open Sudarshan" in SHELL_JS
    assert "Explore Brahmand" in SHELL_JS


def test_disconnected_state_is_compact_not_full_width_banner():
    assert "#notice" in SHELL_CSS
    assert "width:max-content" in SHELL_CSS
    assert "border-radius:999px" in SHELL_CSS


def test_real_garudanetra_split_remains_half_screen():
    assert ".liveWork" in SHELL_CSS
    assert "width:50%" in SHELL_CSS
    assert ".main.liveSplit>.view" in SHELL_CSS
    assert "margin-right:50%" in SHELL_CSS
    assert ".main.liveSplit .composerWrap" in SHELL_CSS
    assert "right:50%" in SHELL_CSS


def test_preflight_requires_canonical_browser_not_retired_drawer():
    assert "Sudarshan canonical Garudanetra browser ready" in PREFLIGHT
    assert "has('#liveWork')" in PREFLIGHT
    assert "has('#garudaFrame')" in PREFLIGHT
    assert "retired duplicate browser drawer absent" in PREFLIGHT
    assert "!has('#kbBrowserDrawer')" in PREFLIGHT
