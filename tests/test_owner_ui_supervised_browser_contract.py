from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app" / "spatial-ui" / "public" / "krishna-owner-corrections.js").read_text(encoding="utf-8")
CSS = (ROOT / "app" / "spatial-ui" / "public" / "krishna-owner-corrections.css").read_text(encoding="utf-8")
WEB = (ROOT / "core" / "web_validation.html").read_text(encoding="utf-8")
SERVER = (ROOT / "core" / "krishna_core" / "server.py").read_text(encoding="utf-8")


def test_sudarshan_browser_uses_canonical_livework_split():
    assert "toggleLiveWork" in JS
    assert "kb-real-browser-split" in JS
    assert "#liveWork" in CSS
    assert "width:50%!important" in CSS
    assert ".main.liveSplit #sudarshan" in CSS
    assert "#kbBrowserDrawer" in CSS
    assert "display:none!important" in CSS


def test_live_browser_frame_is_real_garudanetra_frame():
    assert 'id="liveWork"' in WEB
    assert 'id="garudaFrame"' in WEB
    assert "/api/garudanetra/frame" in SERVER
    assert "frame_info" in SERVER


def test_chat_and_project_overflow_actions_remain_available():
    assert "openChatActionMenu" in WEB
    assert "openProjectActionMenu" in WEB
    assert "chat.rename" in WEB
    assert "chat.delete" in WEB
    assert "chat.move" in WEB
    assert "Rename" in WEB
    assert "Pin" in WEB
    assert "Share" in WEB
    assert "Delete" in WEB
    assert "button.textContent = '⋯'" in JS
    assert ".chatMore" in CSS
    assert ".projectBranchMore" in CSS
    assert "opacity:1!important" in CSS


def test_chatgpt_and_claude_are_supervised_web_plugins():
    assert "ChatGPT Free" in JS
    assert "Claude Free" in JS
    assert "https://chatgpt.com/" in JS
    assert "https://claude.ai/" in JS
    assert "SUPERVISED WEB" in JS
    assert "Open in Sudarshan" in JS
    assert "/api/plugins/add" in JS
    assert "startGarudanetraBrowser" in JS
    assert "₹0 API spend" in JS
