from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREVIEW = (ROOT / "app" / "spatial-ui" / "src" / "LegacyKrishnaPreview.tsx").read_text(encoding="utf-8")
ENHANCEMENTS = (ROOT / "app" / "spatial-ui" / "public" / "krishna-owner-enhancements.js").read_text(encoding="utf-8")
CORRECTIONS = (ROOT / "app" / "spatial-ui" / "public" / "krishna-owner-corrections.js").read_text(encoding="utf-8")
APPLE = (ROOT / "app" / "spatial-ui" / "public" / "krishna-apple-shell.js").read_text(encoding="utf-8")


def test_preview_loader_cannot_wait_for_retired_browser_drawer():
    wait_block = PREVIEW.split("const waitForOwnerDom", 1)[1].split("void (async () =>", 1)[0]
    assert "kbBrowserDrawer" not in wait_block
    assert "setState('ready')" in PREVIEW
    optional_load = "await loadOptional('krishna-owner-enhancements-script'"
    assert optional_load in PREVIEW
    assert PREVIEW.index("setState('ready')") < PREVIEW.index(optional_load)
    assert "script.remove()" in PREVIEW
    assert "timed out after" in PREVIEW


def test_overflow_button_repairs_are_idempotent():
    guard = "if (button.textContent !== '⋯') button.textContent = '⋯';"
    assert guard in ENHANCEMENTS
    assert guard in CORRECTIONS


def test_plugin_fallback_repair_does_not_rebuild_same_dom_forever():
    assert "wantedIds.join('|') === existingIds.join('|')" in CORRECTIONS
    assert "existing.forEach((node) => node.remove())" in CORRECTIONS
    assert CORRECTIONS.index("wantedIds.join('|') === existingIds.join('|')") < CORRECTIONS.index("existing.forEach((node) => node.remove())")


def test_flow_repair_is_signature_guarded():
    assert "kbFlowSignature" in ENHANCEMENTS
    assert "qsa('.kb-flow-drop', svg).length === paths.length * 3" in ENHANCEMENTS


def test_premium_shell_brand_repair_is_idempotent():
    assert "small && small.textContent !== wanted" in APPLE
    assert "__KRISHNA_APPLE_SHELL__" in APPLE


def test_duplicate_browser_drawer_is_removed_not_used():
    assert "$('kbBrowserDrawer')?.remove();" in CORRECTIONS
    assert "#liveWork" in (ROOT / "app" / "spatial-ui" / "public" / "krishna-owner-corrections.css").read_text(encoding="utf-8")


def test_home_cosmos_is_forced_to_static_low_load_during_boot():
    assert "loadBrahmandMainLowLoad" in PREVIEW
    assert "query !== '(prefers-reduced-motion: reduce)'" in PREVIEW
    assert "if (property === 'matches') return true" in PREVIEW
    assert "finally" in PREVIEW and "win.matchMedia = originalMatchMedia" in PREVIEW
    assert "await loadBrahmandMainLowLoad()" in PREVIEW
