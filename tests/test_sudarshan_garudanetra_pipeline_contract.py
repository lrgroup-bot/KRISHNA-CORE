from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "app" / "spatial-ui" / "public"
LAYOUT = (PUBLIC / "krishna-layout-guard.css").read_text(encoding="utf-8")
ENHANCE = (PUBLIC / "krishna-owner-enhancements.js").read_text(encoding="utf-8")
BRAHMAND = (PUBLIC / "krishna-brahmand-main.js").read_text(encoding="utf-8")
WEB = (ROOT / "core" / "web_validation.html").read_text(encoding="utf-8")


def test_sudarshan_is_full_canvas_and_messages_scroll_inside_it():
    assert 'body[data-view="sudarshan"] #sudarshan.chatView.active' in LAYOUT
    assert 'inset:0!important' in LAYOUT
    assert 'width:100%!important' in LAYOUT
    assert 'height:100%!important' in LAYOUT
    assert 'body[data-view="sudarshan"] #messages' in LAYOUT
    assert 'overflow-y:auto!important' in LAYOUT
    assert 'body:not([data-view="sudarshan"]) #sudarshan' in LAYOUT


def test_garudanetra_uses_canonical_live_work_and_exact_split():
    assert 'id="liveWork" class="liveWork"' in WEB
    assert 'id="garudaFrame" class="garudaFrame"' in WEB
    assert 'function toggleLiveWork(force)' in WEB
    assert 'body[data-view="sudarshan"] #liveWork:not([hidden])' in LAYOUT
    assert 'width:50%!important' in LAYOUT
    assert '#liveWork.expanded:not([hidden])' in LAYOUT
    assert 'width:100%!important' in LAYOUT
    assert '.main.liveSplit #sudarshan' in LAYOUT
    assert 'right:50%!important' in LAYOUT


def test_pipeline_state_is_derived_from_live_backend_truth():
    assert "fetch('/api/status'" in BRAHMAND
    assert "fetch('/api/tasks?limit=500'" in BRAHMAND
    assert 'nodeState(def)' in BRAHMAND
    assert 'await Promise.all([...ids].filter((id)=>node(id)?.endpoint).map(probe))' in BRAHMAND
    assert "fetchJson('/health')" in ENHANCE
    assert "fetchJson('/api/status')" in ENHANCE
    assert "fetchJson('/api/tasks?limit=500')" in ENHANCE
    assert "fetchJson('/api/garudanetra/fabric')" in ENHANCE
    assert "dataset.kbPipelineBackend = coreOnline ? 'online' : 'offline'" in ENHANCE


def test_pipeline_flow_is_paused_when_backend_truth_is_offline():
    assert 'data-kb-pipeline-backend="offline"' in LAYOUT
    assert '#kbGraphSvg .kb-flow-drop' in LAYOUT
    assert "dataset.kbPipelineBackend !== 'online'" in ENHANCE
    assert "path.kb-edge.active,path.kb-edge.green" in ENHANCE
    assert 'animateMotion' in ENHANCE
    assert 'repeatCount' in ENHANCE


def test_garudanetra_health_is_monitored_with_pipeline_truth():
    assert "const garudaReady = garuda.status === 'fulfilled'" in ENHANCE
    assert "browserToggle.dataset.garudanetraStatus = garudaReady ? 'ready' : 'offline'" in ENHANCE
    assert "liveState.textContent = 'BACKEND OFFLINE'" in ENHANCE
