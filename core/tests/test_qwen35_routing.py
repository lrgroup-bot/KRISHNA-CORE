import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.router import ModelRouter
from krishna_core.vision_adapter import VisionAdapter
from krishna_core.model_router import ModelRouter as LegacyModelRouter


class QwenPcMobilePolicyIntegrationTests(unittest.TestCase):
    def test_pc_general_and_coding_candidates_are_qwen_free(self):
        with patch.dict(os.environ, {}, clear=True):
            general=ModelRouter.local_model_candidates()
            coding=ModelRouter.local_model_candidates("coding")
        self.assertEqual(general[0],"gemma3:4b")
        self.assertEqual(coding[0],"gemma3:4b")
        self.assertTrue(all(not x.lower().startswith("qwen") for x in general+coding))

    def test_router_filters_qwen_even_if_env_requests_it(self):
        with patch.dict(os.environ, {
            "KRISHNA_LOCAL_MODEL":"qwen3.5:4b",
            "KRISHNA_LOCAL_FALLBACK_MODELS":"qwen2.5:3b,gemma3:4b",
        }, clear=True):
            self.assertEqual(ModelRouter.local_model_candidates()[0],"gemma3:4b")
            self.assertTrue(all(not x.lower().startswith("qwen") for x in ModelRouter.local_model_candidates()))

    def test_hawkeye_profiles_are_qwen_free(self):
        with patch.dict(os.environ, {}, clear=True):
            adapter=VisionAdapter()
        self.assertEqual(adapter.model,"gemma3:4b")
        self.assertEqual(adapter.fast_model,"gemma3:4b")
        self.assertTrue(all(not x.lower().startswith("qwen") for x in adapter.candidates("detailed")+adapter.candidates("fast")))

    def test_hawkeye_filters_qwen_from_env(self):
        with patch.dict(os.environ, {
            "KRISHNA_VISION_MODEL":"qwen2.5vl:7b",
            "KRISHNA_FAST_VISION_MODEL":"qwen3.5:4b",
        }, clear=True):
            adapter=VisionAdapter()
        self.assertEqual(adapter.model,"gemma3:4b")
        self.assertEqual(adapter.fast_model,"gemma3:4b")

    def test_legacy_pc_router_respects_owner_qwen_disable_policy(self):
        with patch.dict(os.environ, {}, clear=True):
            router=LegacyModelRouter()
        models=[p.model for p in router.providers if p.name.startswith("ollama")]
        self.assertEqual(models[0],"gemma3:4b")
        self.assertTrue(all(not str(model).lower().startswith("qwen") for model in models))

    def test_env_defaults_are_qwen_free(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/".env.example").read_text(encoding="utf-8").lower()
        self.assertNotIn("=qwen",text)
        self.assertIn("krishna_local_model=gemma3:4b",text)

    def test_mobile_manifest_records_global_qwen_disable(self):
        root=Path(__file__).resolve().parents[2]
        manifest=json.loads((root/"mobile_v3"/"CANONICAL_RUNTIME.json").read_text(encoding="utf-8"))
        policy=manifest["model_policy"]
        self.assertFalse(policy["pc_qwen_allowed"])
        self.assertFalse(policy["pc_qwen_default_role_assigned"])
        self.assertFalse(policy["mobile_qwen_allowed"])
        self.assertFalse(policy["mobile_qwen_dependency"])
        for value in policy["pc_roles"].values():
            self.assertFalse(str(value).lower().startswith("qwen"))
        for values in policy["pc_fallbacks"].values():
            self.assertTrue(all(not str(x).lower().startswith("qwen") for x in values))
        self.assertFalse(policy["automatic_paid_fallback"])

    def test_manual_stop_script_never_deletes_models(self):
        root=Path(__file__).resolve().parents[2]
        script=(root/"scripts"/"STOP_KRISHNA_QWEN.ps1").read_text(encoding="utf-8")
        self.assertIn(" stop $model",script)
        self.assertIn("Installed model files were not deleted",script)
        self.assertNotIn("ollama rm",script.lower())

    def test_hawkeye_server_keeps_existing_fast_and_detailed_contracts(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/"krishna_core"/"server.py").read_text(encoding="utf-8")
        self.assertIn('vision=_vision.analyze_bytes(raw,content_type,prompt,mode="fast")',text)
        self.assertGreaterEqual(text.count('vision=_vision.analyze_bytes(raw,content_type,prompt,mode="detailed")'),3)

if __name__=="__main__":
    unittest.main()
