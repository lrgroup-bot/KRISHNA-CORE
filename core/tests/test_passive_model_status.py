from types import SimpleNamespace

import pytest

from krishna_core.hawkeye_free_cloud import HawkeyeFreeCloudFabric
import krishna_core.vision_adapter as vision_module


class _PassiveOpenRouter:
    CACHE_SECONDS = 300

    def __init__(self):
        self.live_status_calls = 0

    def profile(self):
        return {"id": "openrouter-free", "name": "OpenRouter Free"}

    def _read_cache(self):
        return {"fetched_at": 1.0, "models": [{"id": "cached/free"}]}

    def status(self, refresh=False):
        self.live_status_calls += 1
        raise AssertionError("passive HAWKEYE status must not delegate to OpenRouter live status")


class _DirectFree:
    def status(self, refresh=False):
        return {"configured": False, "refresh": bool(refresh)}


class _Gateway:
    def list(self):
        return {"profiles": []}


class _Gemini:
    def status(self):
        return {"configured": False}


def test_hawkeye_passive_status_is_cache_only_and_never_calls_openrouter_status():
    openrouter = _PassiveOpenRouter()
    fabric = HawkeyeFreeCloudFabric(openrouter, _DirectFree(), _Gateway(), _Gemini())

    status = fabric.status(refresh=False)

    assert openrouter.live_status_calls == 0
    provider = status["providers"]["openrouter_zero_cost"]
    assert provider["status_mode"] == "passive-cache-only"
    assert provider["network_refresh"] is False
    assert provider["catalog"]["cached"] is True
    assert provider["catalog"]["stale"] is True


def test_hawkeye_explicit_refresh_still_delegates_to_provider():
    class RefreshOpenRouter(_PassiveOpenRouter):
        def status(self, refresh=False):
            self.live_status_calls += 1
            return {"configured": True, "refresh": bool(refresh)}

    openrouter = RefreshOpenRouter()
    fabric = HawkeyeFreeCloudFabric(openrouter, _DirectFree(), _Gateway(), _Gemini())

    status = fabric.status(refresh=True)

    assert openrouter.live_status_calls == 1
    assert status["providers"]["openrouter_zero_cost"]["refresh"] is True


def test_disabled_vision_status_never_opens_an_ollama_socket(monkeypatch):
    monkeypatch.setattr(
        vision_module,
        "settings",
        SimpleNamespace(ollama_enabled=False, ollama_url="disabled://krishna-ollama"),
    )

    def forbidden_urlopen(*args, **kwargs):
        raise AssertionError("disabled KRISHNA vision attempted network I/O")

    monkeypatch.setattr(vision_module.urllib.request, "urlopen", forbidden_urlopen)
    adapter = vision_module.VisionAdapter()

    status = adapter.status("fast")

    assert status["available"] is False
    assert status["service_available"] is False
    assert status["owner_enabled"] is False
    assert "disabled by owner policy" in status["error"]

    with pytest.raises(PermissionError, match="disabled by owner policy"):
        adapter.analyze_bytes(b"image", "image/jpeg", "inspect", mode="fast")
