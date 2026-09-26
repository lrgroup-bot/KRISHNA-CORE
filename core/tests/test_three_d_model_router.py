import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.three_d_model_router import ThreeDModelRouter
from krishna_core.zero_spend_policy import ZeroSpendPolicy


class ThreeDModelRouterTests(unittest.TestCase):
    def setUp(self):
        self.router=ThreeDModelRouter(zero_spend=ZeroSpendPolicy())

    def _workers(self, root, names):
        env={}
        for provider_id,env_name in names:
            path=Path(root)/f"{provider_id}.worker"
            path.write_text("worker",encoding="utf-8")
            env[env_name]=str(path)
        return env

    def test_catalog_contains_researched_free_pipeline_and_paid_block(self):
        ids={x["provider_id"] for x in self.router.catalog(vram_gb=24)}
        for expected in {
            "blender","instant-meshes","openfacefx","triposr","triposg","partcrafter",
            "hunyuan3d-2mini","stable-fast-3d","spar3d","unirig","skintokens",
            "puppeteer","anytop","anigen","pixal3d","trellis2",
            "tripo-p2-free-credit","tripo-h31-free-credit","tripo-paid-api",
        }:
            self.assertIn(expected,ids)

        paid=self.router.provider_status("tripo-paid-api",vram_gb=24)
        self.assertFalse(paid["automatic_eligible"])
        self.assertFalse(paid["spend_ok"])
        self.assertTrue(any("zero-spend" in x.lower() or "sending money" in x.lower() or "paid" in x.lower() for x in paid["blockers"]))

    def test_cloud_free_credit_providers_never_auto_run(self):
        for provider_id in ("tripo-p2-free-credit","tripo-h31-free-credit"):
            row=self.router.provider_status(provider_id,vram_gb=24)
            self.assertFalse(row["automatic_eligible"])
            self.assertFalse(row["spend_ok"])
            self.assertIn("test-only"," ".join(row["blockers"]).lower())

    def test_four_gb_hardware_blocks_heavy_generation_and_rigging(self):
        with tempfile.TemporaryDirectory() as td:
            env=self._workers(td,[
                ("blender","KRISHNA_BLENDER_CMD"),
                ("instant-meshes","KRISHNA_INSTANT_MESHES_CMD"),
                ("openfacefx","KRISHNA_OPENFACEFX_CMD"),
                ("triposr","KRISHNA_TRIPOSR_CMD"),
                ("unirig","KRISHNA_UNIRIG_CMD"),
            ])
            with patch.dict(os.environ,env,clear=False):
                plan=self.router.plan(vram_gb=4,include_parts=False,include_animation=False)
        self.assertTrue(plan["current_low_vram_mode"])
        self.assertIsNone(plan["stages"]["generation"])
        self.assertIsNone(plan["stages"]["rigging"])
        self.assertEqual(plan["stages"]["retopology"]["provider_id"],"instant-meshes")
        self.assertEqual(plan["stages"]["face"]["provider_id"],"openfacefx")
        self.assertEqual(plan["stages"]["pipeline"]["provider_id"],"blender")
        self.assertIn("generation",plan["missing_stages"])
        self.assertIn("rigging",plan["missing_stages"])

    def test_eight_gb_node_selects_free_generation_retopo_and_unirig(self):
        with tempfile.TemporaryDirectory() as td:
            env=self._workers(td,[
                ("blender","KRISHNA_BLENDER_CMD"),
                ("triposg","KRISHNA_TRIPOSG_CMD"),
                ("partcrafter","KRISHNA_PARTCRAFTER_CMD"),
                ("instant-meshes","KRISHNA_INSTANT_MESHES_CMD"),
                ("unirig","KRISHNA_UNIRIG_CMD"),
                ("puppeteer","KRISHNA_PUPPETEER_CMD"),
                ("openfacefx","KRISHNA_OPENFACEFX_CMD"),
            ])
            with patch.dict(os.environ,env,clear=False):
                plan=self.router.plan(vram_gb=8)
        self.assertTrue(plan["ready"])
        self.assertEqual(plan["stages"]["generation"]["provider_id"],"triposg")
        self.assertEqual(plan["stages"]["parts"]["provider_id"],"partcrafter")
        self.assertEqual(plan["stages"]["rigging"]["provider_id"],"unirig")
        self.assertEqual(plan["stages"]["animation"]["provider_id"],"puppeteer")

    def test_fourteen_gb_prefers_skintokens_when_configured(self):
        with tempfile.TemporaryDirectory() as td:
            env=self._workers(td,[
                ("blender","KRISHNA_BLENDER_CMD"),
                ("triposg","KRISHNA_TRIPOSG_CMD"),
                ("instant-meshes","KRISHNA_INSTANT_MESHES_CMD"),
                ("unirig","KRISHNA_UNIRIG_CMD"),
                ("skintokens","KRISHNA_SKINTOKENS_CMD"),
                ("puppeteer","KRISHNA_PUPPETEER_CMD"),
                ("openfacefx","KRISHNA_OPENFACEFX_CMD"),
            ])
            with patch.dict(os.environ,env,clear=False):
                plan=self.router.plan(vram_gb=14,include_parts=False)
        self.assertEqual(plan["stages"]["rigging"]["provider_id"],"skintokens")

    def test_twenty_four_gb_prefers_pixal3d_when_configured(self):
        with tempfile.TemporaryDirectory() as td:
            env=self._workers(td,[
                ("blender","KRISHNA_BLENDER_CMD"),
                ("pixal3d","KRISHNA_PIXAL3D_CMD"),
                ("instant-meshes","KRISHNA_INSTANT_MESHES_CMD"),
                ("skintokens","KRISHNA_SKINTOKENS_CMD"),
                ("puppeteer","KRISHNA_PUPPETEER_CMD"),
                ("openfacefx","KRISHNA_OPENFACEFX_CMD"),
            ])
            with patch.dict(os.environ,env,clear=False):
                plan=self.router.plan(vram_gb=24,include_parts=False)
        self.assertEqual(plan["stages"]["generation"]["provider_id"],"pixal3d")
        self.assertEqual(plan["stages"]["rigging"]["provider_id"],"skintokens")

    def test_anigen_remains_license_restricted_for_commercial_use(self):
        row=self.router.provider_status("anigen",vram_gb=24)
        self.assertIn("non-commercial",row["commercial_use"].lower())

    def test_status_never_marks_paid_or_free_credit_cloud_as_automatic(self):
        status=self.router.status()
        automatic=set(status["automatic_eligible"])
        self.assertNotIn("tripo-paid-api",automatic)
        self.assertNotIn("tripo-p2-free-credit",automatic)
        self.assertNotIn("tripo-h31-free-credit",automatic)


if __name__=="__main__":
    unittest.main()
