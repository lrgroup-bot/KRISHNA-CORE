import tempfile
import unittest
from krishna_core.garuda_repair_workflow import GarudaRepairWorkflow

class RepairWorkflowTests(unittest.TestCase):
    def test_authorized_draft_and_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            app=GarudaRepairWorkflow(root)
            kw=dict(device_id="laptop-1",device_kind="windows",category="thermal",
                    symptom="Fan spins at full speed",paired=True,evidence_refs=("photo:1",))
            first=app.open_case(**kw)
            second=app.open_case(**kw)
            self.assertEqual(first["case_id"],second["case_id"])
            self.assertFalse(first["repair_authorized"])
            self.assertFalse(first["knowledge_verified"])
            self.assertTrue(first["diagnostic_plan"]["actions"])
    def test_reject_unpaired(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(PermissionError):
                GarudaRepairWorkflow(root).open_case(device_id="pc-1",device_kind="windows",
                     category="software",symptom="Application cannot start")
    def test_original_guide(self):
        with tempfile.TemporaryDirectory() as root:
            result=GarudaRepairWorkflow(root).create_original_guide(
                model="Laptop X",title="Check external cooling vents",difficulty="easy",
                minutes=10,steps=[{"title":"Inspect","instruction":"Observe external vents without opening the case"}])
            self.assertEqual(result["status"],"draft")
    def test_reference_offline_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            result=GarudaRepairWorkflow(root).module_summary(device_model="Laptop X",module="fan")
            self.assertEqual(result["reference_error"],"provider_not_configured")
if __name__=="__main__":
    unittest.main()
