import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.router import ModelRouter
from krishna_core.vision_adapter import VisionAdapter
from krishna_core.model_router import ModelRouter as LegacyModelRouter


class QwenPcMobilePolicyIntegrationTests(unittest.TestCase):
    def test_automatic_defaults_remain_non_qwen(self):
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

    def test_pc_qwen_can_be_explicitly_enabled_by_environment(self):
        with patch.dict(os.environ, {
            "KRISHNA_LOCAL_MODEL":"qwen3.5:4b",
            "KRISHNA_LOCAL_FALLBACK_MODELS":"qwen2.5:3b,qwen2.5vl:7b",
        }, clear=True):
            candidates=ModelRouter.local_model_candidates()
        self.assertEqual(candidates[0], "qwen3.5:4b")
        self.assertIn("qwen2.5:3b", candidates)
        self.assertIn("qwen2.5vl:7b", candidates)

    def test_router_uses_explicit_pc_qwen(self):
        router=ModelRouter()
        seen=[]
        router._ollama_generate=lambda model,prompt: seen.append((model,prompt)) or "ok"
        self.assertEqual(router.local("hello", "qwen3.5:4b"), "ok")
        self.assertEqual(seen, [("qwen3.5:4b","hello")])

    def test_qwen_is_not_automatic_when_default_environment_is_used(self):
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

    def test_hawkeye_pc_vision_can_explicitly_use_qwen(self):
        with patch.dict(os.environ, {
            "KRISHNA_VISION_MODEL":"qwen2.5vl:7b",
            "KRISHNA_VISION_FALLBACK_MODELS":"gemma3:4b",
            "KRISHNA_FAST_VISION_MODEL":"qwen3.5:4b",
            "KRISHNA_FAST_VISION_FALLBACK_MODELS":"gemma3:4b",
        }, clear=True):
            adapter=VisionAdapter()
        self.assertEqual(adapter.model, "qwen2.5vl:7b")
        self.assertEqual(adapter.fast_model, "qwen3.5:4b")
        self.assertIn("qwen2.5vl:7b", adapter.candidates("detailed"))
        self.assertIn("qwen3.5:4b", adapter.candidates("fast"))

    def test_legacy_pc_router_can_explicitly_use_qwen(self):
        with patch.dict(os.environ, {
            "KRISHNA_OLLAMA_MODEL":"qwen3.5:4b",
            "KRISHNA_OLLAMA_FALLBACK_MODELS":"qwen2.5:3b,qwen2.5vl:7b",
        }, clear=True):
            router=LegacyModelRouter()
        models=[p.model for p in router.providers if p.name.startswith("ollama")]
        self.assertEqual(models[0], "qwen3.5:4b")
        self.assertIn("qwen2.5:3b", models)
        self.assertIn("qwen2.5vl:7b", models)

    def test_pc_qwen_installer_is_explicit_opt_in_only(self):
        root=Path(__file__).resolve().parents[2]
        script=(root/"scripts"/"INSTALL_KRISHNA_QWEN35.ps1").read_text(encoding="utf-8")
        self.assertIn("PC-only Qwen is permitted", script)
        self.assertIn("[switch]$Pull", script)
        self.assertIn(" pull $Model", script)
        self.assertNotIn("Qwen is disabled by owner policy", script)

    def test_manual_stop_script_never_deletes_models(self):
        root=Path(__file__).resolve().parents[2]
        script=(root/"scripts"/"STOP_KRISHNA_QWEN.ps1").read_text(encoding="utf-8")
        self.assertIn(" stop $model", script)
        self.assertIn("Installed model files were not deleted", script)
        self.assertNotIn("ollama rm", script.lower())

    def test_env_defaults_remain_non_qwen(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/".env.example").read_text(encoding="utf-8")
        self.assertNotIn("qwen", text.lower())
        self.assertIn("KRISHNA_LOCAL_MODEL=gemma3:4b", text)
        self.assertIn("KRISHNA_VISION_MODEL=gemma3:4b", text)

    def test_canonical_deploy_preserves_pc_qwen(self):
        root=Path(__file__).resolve().parents[2]
        text=(root/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8")
        self.assertNotIn("& powershell -NoProfile -ExecutionPolicy Bypass -File $qwenStopScript", text)
        self.assertNotIn("QWEN STOP POLICY FAILED", text)
        self.assertIn("PC QWEN POLICY", text)

    def test_mobile_is_explicitly_qwen_free(self):
        root=Path(__file__).resolve().parents[2]
        manifest=json.loads((root/"mobile_v3"/"CANONICAL_RUNTIME.json").read_text(encoding="utf-8"))
        policy=manifest["model_policy"]
        self.assertTrue(policy["pc_qwen_allowed"])
        self.assertFalse(policy["mobile_qwen_allowed"])
        self.assertFalse(policy["mobile_qwen_dependency"])
        self.assertEqual(policy["mobile_cloud_mode"], "verified-free-only")

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
