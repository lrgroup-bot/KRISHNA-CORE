import os
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.router import ModelRouter
from krishna_core.vision_adapter import VisionAdapter
from krishna_core.model_router import ModelRouter as LegacyModelRouter


class QwenStopPolicyIntegrationTests(unittest.TestCase):
    def test_primary_and_fallback_order_is_non_qwen(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                ModelRouter.local_model_candidates(),
                [
                    "gemma3:4b",
                    "granite3.3:2b",
                    "smollm2:1.7b",
                    "llama3.2:1b",
                    "deepseek-r1:1.5b",
                ],
            )

    def test_qwen_environment_cannot_reenable_router(self):
        with patch.dict(os.environ, {
            "KRISHNA_LOCAL_MODEL":"qwen3.5:4b",
            "KRISHNA_LOCAL_FALLBACK_MODELS":"qwen2.5:3b,qwen2.5vl:7b",
        }, clear=True):
            candidates=ModelRouter.local_model_candidates()
        self.assertTrue(candidates)
        self.assertFalse(any("qwen" in x.lower() for x in candidates))

    def test_router_selects_non_qwen_when_only_qwen_and_gemma_are_installed(self):
        router=ModelRouter()
        router._probe_json=lambda *_: (True, {
            "models":[
                {"name":"qwen3.5:4b"},
                {"name":"qwen2.5vl:7b"},
                {"name":"gemma3:4b"},
            ]
        })
        with patch.dict(os.environ, {}, clear=True):
            status=router.local_model_status()
        self.assertTrue(status["available"])
        self.assertEqual(status["selected_model"], "gemma3:4b")

    def test_explicit_qwen_is_blocked_before_ollama(self):
        router=ModelRouter()
        router._ollama_generate=lambda *args,**kwargs: self.fail("Qwen reached Ollama")
        with self.assertRaisesRegex(RuntimeError, "disabled by owner policy"):
            router.local("hello", "qwen3.5:4b")

    def test_hawkeye_vision_is_non_qwen_and_qwen_env_is_ignored(self):
        with patch.dict(os.environ, {
            "KRISHNA_VISION_MODEL":"qwen2.5vl:7b",
            "KRISHNA_VISION_FALLBACK_MODELS":"qwen3.5:4b",
            "KRISHNA_FAST_VISION_MODEL":"qwen3.5:4b",
            "KRISHNA_FAST_VISION_FALLBACK_MODELS":"qwen2.5vl:7b",
        }, clear=True):
            adapter=VisionAdapter()
        self.assertEqual(adapter.model, "gemma3:4b")
        self.assertEqual(adapter.fast_model, "gemma3:4b")
        self.assertFalse(any("qwen" in x.lower() for x in adapter.candidates("detailed")))
        self.assertFalse(any("qwen" in x.lower() for x in adapter.candidates("fast")))

    def test_legacy_router_is_non_qwen_even_with_qwen_env(self):
        with patch.dict(os.environ, {
            "KRISHNA_OLLAMA_MODEL":"qwen3.5:4b",
            "KRISHNA_OLLAMA_FALLBACK_MODELS":"qwen2.5:3b,qwen2.5vl:7b",
        }, clear=True):
            router=LegacyModelRouter()
        models=[p.model for p in router.providers if p.name.startswith("ollama")]
        self.assertTrue(models)
        self.assertEqual(models[0], "gemma3:4b")
        self.assertFalse(any("qwen" in str(x).lower() for x in models))

    def test_legacy_qwen_installer_is_fail_closed(self):
        root=Path(__file__).resolve().parents[2]
        script=(root/"scripts"/"INSTALL_KRISHNA_QWEN35.ps1").read_text(encoding="utf-8")
        self.assertIn("Qwen is disabled by owner policy", script)
        self.assertNotIn("ollama pull", script.lower())

    def test_stop_script_stops_without_deleting_models(self):
        root=Path(__file__).resolve().parents[2]
        script=(root/"scripts"/"STOP_KRISHNA_QWEN.ps1").read_text(encoding="utf-8")
        self.assertIn(" stop $model", script)
        self.assertIn("Installed model files were not deleted", script)
        self.assertNotIn("ollama rm", script.lower())

    def test_env_example_has_no_qwen_defaults(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/".env.example").read_text(encoding="utf-8")
        self.assertNotIn("qwen", text.lower())
        self.assertIn("KRISHNA_LOCAL_MODEL=gemma3:4b", text)
        self.assertIn("KRISHNA_VISION_MODEL=gemma3:4b", text)

    def test_canonical_deploy_runs_qwen_stop_policy(self):
        root=Path(__file__).resolve().parents[2]
        text=(root/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8")
        self.assertIn("STOP_KRISHNA_QWEN.ps1", text)
        self.assertIn("QWEN STOP POLICY FAILED", text)

    def test_hawkeye_server_uses_fast_only_for_ordinary_live_frames(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/"krishna_core"/"server.py").read_text(encoding="utf-8")
        self.assertIn('vision=_vision.analyze_bytes(raw,content_type,prompt,mode="fast")',text)
        self.assertGreaterEqual(
            text.count('vision=_vision.analyze_bytes(raw,content_type,prompt,mode="detailed")'),
            3,
        )


if __name__=="__main__":
    unittest.main()
