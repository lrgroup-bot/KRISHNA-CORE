import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.router import ModelRouter
from krishna_core.vision_adapter import VisionAdapter
from krishna_core.model_router import ModelRouter as LegacyModelRouter


class QwenPcMobilePolicyIntegrationTests(unittest.TestCase):
    def test_general_pc_defaults_use_qwen35_with_local_fallbacks(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                ModelRouter.local_model_candidates(),
                [
                    "qwen3.5:4b",
                    "gemma3:4b",
                    "granite3.3:2b",
                    "smollm2:1.7b",
                    "llama3.2:1b",
                    "deepseek-r1:1.5b",
                    "qwen2.5:3b",
                ],
            )

    def test_coding_pc_defaults_use_qwen25_coder(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                ModelRouter.local_model_candidates("coding"),
                [
                    "qwen2.5-coder:7b",
                    "qwen3.5:4b",
                    "gemma3:4b",
                    "granite3.3:2b",
                ],
            )
            self.assertEqual(
                ModelRouter.local_model_candidates("implementation")[0],
                "qwen2.5-coder:7b",
            )

    def test_general_router_selects_qwen35_when_installed(self):
        router=ModelRouter()
        router._probe_json=lambda *_: (True, {
            "models":[
                {"name":"qwen3.5:4b"},
                {"name":"gemma3:4b"},
                {"name":"qwen2.5vl:7b"},
            ]
        })
        with patch.dict(os.environ, {}, clear=True):
            status=router.local_model_status()
        self.assertTrue(status["available"])
        self.assertEqual(status["task"], "general")
        self.assertEqual(status["selected_model"], "qwen3.5:4b")

    def test_coding_router_selects_qwen25_coder_when_installed(self):
        router=ModelRouter()
        router._probe_json=lambda *_: (True, {
            "models":[
                {"name":"qwen2.5-coder:7b"},
                {"name":"qwen3.5:4b"},
                {"name":"gemma3:4b"},
            ]
        })
        with patch.dict(os.environ, {}, clear=True):
            status=router.local_model_status("coding")
        self.assertTrue(status["available"])
        self.assertEqual(status["task"], "coding")
        self.assertEqual(status["selected_model"], "qwen2.5-coder:7b")

    def test_coding_route_prioritizes_coder(self):
        router=ModelRouter()
        router._probe_json=lambda *_: (True, {
            "models":[{"name":"qwen2.5-coder:7b"},{"name":"qwen3.5:4b"}]
        })
        seen=[]
        def ask(provider,*_args,**_kwargs):
            seen.append(provider)
            if provider=="ollama-model:qwen2.5-coder:7b":
                return "coder-ok"
            raise RuntimeError("unexpected provider")
        router._governed_ask=ask
        with patch.dict(os.environ, {}, clear=True):
            out=router.route("repair this code",privacy="local_only",task="implementation")
        self.assertEqual(out["model"], "qwen2.5-coder:7b")
        self.assertEqual(out["task"], "coding")
        self.assertEqual(seen[0], "ollama-model:qwen2.5-coder:7b")

    def test_role_status_keeps_mobile_qwen_free_and_paid_cloud_off(self):
        router=ModelRouter()
        router._probe_json=lambda *_: (True, {
            "models":[
                {"name":"qwen3.5:4b"},
                {"name":"qwen2.5-coder:7b"},
                {"name":"gemma3:4b"},
            ]
        })
        with patch.dict(os.environ, {}, clear=True):
            status=router.role_status()
        self.assertEqual(status["pc"]["general"]["selected_model"], "qwen3.5:4b")
        self.assertEqual(status["pc"]["coding"]["selected_model"], "qwen2.5-coder:7b")
        self.assertFalse(status["mobile"]["qwen_runtime"])
        self.assertFalse(status["cloud"]["automatic_paid_fallback"])
        self.assertEqual(status["cloud"]["coding"][0], "openrouter-free:coding")

    def test_hawkeye_pc_vision_defaults_are_specialized(self):
        with patch.dict(os.environ, {}, clear=True):
            adapter=VisionAdapter()
        self.assertEqual(adapter.model, "qwen2.5vl:7b")
        self.assertEqual(adapter.fallback_models, ["qwen3.5:4b","gemma3:4b"])
        self.assertEqual(adapter.fast_model, "qwen3.5:4b")
        self.assertEqual(adapter.fast_fallback_models, ["gemma3:4b","qwen2.5vl:7b"])

    def test_hawkeye_status_selects_detailed_and_fast_models_by_role(self):
        with patch.dict(os.environ, {}, clear=True):
            adapter=VisionAdapter()
        adapter._installed_models=lambda: (
            ["qwen3.5:4b","qwen2.5vl:7b","gemma3:4b"],
            {"qwen3.5:4b","qwen2.5vl:7b","gemma3:4b"},
        )
        detailed=adapter.status("detailed")
        fast=adapter.status("fast")
        self.assertEqual(detailed["selected_model"], "qwen2.5vl:7b")
        self.assertEqual(fast["selected_model"], "qwen3.5:4b")

    def test_legacy_pc_router_uses_qwen35_primary(self):
        with patch.dict(os.environ, {}, clear=True):
            router=LegacyModelRouter()
        models=[p.model for p in router.providers if p.name.startswith("ollama")]
        self.assertEqual(models[0], "qwen3.5:4b")
        self.assertIn("gemma3:4b", models)
        self.assertIn("qwen2.5:3b", models)

    def test_pc_qwen_installer_never_makes_mobile_depend_on_qwen(self):
        root=Path(__file__).resolve().parents[2]
        script=(root/"scripts"/"INSTALL_KRISHNA_QWEN35.ps1").read_text(encoding="utf-8")
        self.assertIn("Qwen is role-assigned on the KRISHNA PC", script)
        self.assertIn("[switch]$Pull", script)
        self.assertIn(" pull $Model", script)
        self.assertIn("Mobile remains Qwen-free", script)

    def test_manual_stop_script_never_deletes_models(self):
        root=Path(__file__).resolve().parents[2]
        script=(root/"scripts"/"STOP_KRISHNA_QWEN.ps1").read_text(encoding="utf-8")
        self.assertIn(" stop $model", script)
        self.assertIn("Installed model files were not deleted", script)
        self.assertNotIn("ollama rm", script.lower())

    def test_env_records_pc_task_roles_and_hawkeye_roles(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/".env.example").read_text(encoding="utf-8")
        self.assertIn("KRISHNA_LOCAL_MODEL=qwen3.5:4b", text)
        self.assertIn("KRISHNA_CODING_MODEL=qwen2.5-coder:7b", text)
        self.assertIn("KRISHNA_VISION_MODEL=qwen2.5vl:7b", text)
        self.assertIn("KRISHNA_FAST_VISION_MODEL=qwen3.5:4b", text)
        self.assertIn("gemma3:4b", text)

    def test_canonical_deploy_preserves_pc_qwen(self):
        root=Path(__file__).resolve().parents[2]
        text=(root/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8")
        self.assertNotIn("& powershell -NoProfile -ExecutionPolicy Bypass -File $qwenStopScript", text)
        self.assertNotIn("QWEN STOP POLICY FAILED", text)
        self.assertIn("role-assigned PC models preserved", text)

    def test_mobile_is_explicitly_qwen_free_with_pc_role_assignments(self):
        root=Path(__file__).resolve().parents[2]
        manifest=json.loads((root/"mobile_v3"/"CANONICAL_RUNTIME.json").read_text(encoding="utf-8"))
        policy=manifest["model_policy"]
        self.assertTrue(policy["pc_qwen_allowed"])
        self.assertTrue(policy["pc_qwen_default_role_assigned"])
        self.assertFalse(policy["mobile_qwen_allowed"])
        self.assertFalse(policy["mobile_qwen_dependency"])
        self.assertEqual(policy["mobile_cloud_mode"], "verified-free-only")
        self.assertEqual(policy["pc_roles"]["general"], "qwen3.5:4b")
        self.assertEqual(policy["pc_roles"]["coding"], "qwen2.5-coder:7b")
        self.assertEqual(policy["pc_roles"]["hawkeye_detailed"], "qwen2.5vl:7b")
        self.assertFalse(policy["automatic_paid_fallback"])

    def test_hawkeye_server_uses_fast_only_for_ordinary_live_frames(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/"krishna_core"/"server.py").read_text(encoding="utf-8")
        self.assertIn('vision=_vision.analyze_bytes(raw,content_type,prompt,mode="fast")',text)
        self.assertGreaterEqual(
            text.count('vision=_vision.analyze_bytes(raw,content_type,prompt,mode="detailed")'),
            3,
        )
        self.assertIn('if path == "/api/models/roles":', text)
        self.assertIn('roles["mobile"]["qwen_runtime"]=False', text)


if __name__=="__main__":
    unittest.main()
