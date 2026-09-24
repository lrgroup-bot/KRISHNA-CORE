import os
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.router import ModelRouter
from krishna_core.vision_adapter import VisionAdapter
from krishna_core.model_router import ModelRouter as LegacyModelRouter


class Qwen35RoutingTests(unittest.TestCase):
    def test_primary_qwen35_and_old_qwen_fallback_order(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                ModelRouter.local_model_candidates(),
                ["qwen3.5:4b", "qwen2.5:3b", "qwen2.5vl:7b"],
            )

    def test_router_selects_qwen35_when_installed(self):
        router=ModelRouter()
        router._probe_json=lambda *_: (True, {
            "models":[
                {"name":"qwen2.5:3b"},
                {"name":"qwen3.5:4b"},
                {"name":"qwen2.5vl:7b"},
            ]
        })
        with patch.dict(os.environ, {}, clear=True):
            status=router.local_model_status()
        self.assertTrue(status["available"])
        self.assertEqual(status["selected_model"], "qwen3.5:4b")
        self.assertEqual(status["fallback_models"], ["qwen2.5:3b", "qwen2.5vl:7b"])

    def test_router_falls_back_without_deleting_old_qwen(self):
        router=ModelRouter()
        router._probe_json=lambda *_: (True, {"models":[{"name":"qwen2.5:3b"}]})
        called=[]
        router._ollama_generate=lambda model,prompt: called.append((model,prompt)) or "ok"
        with patch.dict(os.environ, {}, clear=True):
            out=router.local("hello")
        self.assertEqual(out, "ok")
        self.assertEqual(called, [("qwen2.5:3b","hello")])

    def test_hawkeye_vision_defaults_to_qwen35_with_qwen25vl_fallback(self):
        with patch.dict(os.environ, {}, clear=True):
            adapter=VisionAdapter()
        self.assertEqual(adapter.model, "qwen3.5:4b")
        self.assertEqual(adapter.fallback_models, ["qwen2.5vl:7b"])

    def test_legacy_router_uses_same_qwen_order(self):
        with patch.dict(os.environ, {}, clear=True):
            router=LegacyModelRouter()
        names=[(p.name,p.model) for p in router.providers[:3]]
        self.assertEqual(names,[
            ("ollama","qwen3.5:4b"),
            ("ollama-model:qwen2.5:3b","qwen2.5:3b"),
            ("ollama-model:qwen2.5vl:7b","qwen2.5vl:7b"),
        ])

    def test_install_script_never_removes_old_models(self):
        root=Path(__file__).resolve().parents[2]
        script=(root/"scripts"/"INSTALL_KRISHNA_QWEN35.ps1").read_text(encoding="utf-8")
        self.assertIn("qwen3.5:4b",script)
        self.assertIn("OLLAMA_MODELS",script)
        self.assertNotIn("ollama rm",script.lower())

    def test_env_example_records_primary_and_vision_fallback(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/".env.example").read_text(encoding="utf-8")
        self.assertIn("KRISHNA_LOCAL_MODEL=qwen3.5:4b",text)
        self.assertIn("KRISHNA_LOCAL_FALLBACK_MODELS=qwen2.5:3b,qwen2.5vl:7b",text)
        self.assertIn("KRISHNA_VISION_MODEL=qwen3.5:4b",text)
        self.assertIn("KRISHNA_VISION_FALLBACK_MODELS=qwen2.5vl:7b",text)


if __name__=="__main__":
    unittest.main()
