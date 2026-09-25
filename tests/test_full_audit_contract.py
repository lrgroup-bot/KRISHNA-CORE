from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FullAuditContractTests(unittest.TestCase):
    def test_master_audit_continues_after_phase_failure(self):
        text = (ROOT / "scripts" / "AUDIT_KRISHNA_FULL.ps1").read_text(encoding="utf-8")
        start = text.index("function Step")
        end = text.index("$env:PYTHONPATH", start)
        step = text[start:end]

        self.assertIn('status="FAIL"', step)
        self.assertIn("AUDIT STEP FAILED:", step)
        self.assertIn("return", step)
        self.assertNotIn("\n    throw\n", step)

    def test_master_audit_builds_spatial_frontend_and_preflights_self_heal(self):
        text = (ROOT / "scripts" / "AUDIT_KRISHNA_FULL.ps1").read_text(encoding="utf-8")
        self.assertIn('Step "SPATIAL FRONTEND BUILD"', text)
        self.assertIn("npm run build", text)
        self.assertIn('Step "SELF-HEAL CONTRACT PREFLIGHT"', text)
        self.assertIn("tests.test_self_heal", text)
        self.assertIn("tests.test_shared_action_bus", text)
        self.assertIn("tests.test_promotion_runtime", text)

    def test_master_audit_still_fails_release_after_collecting_results(self):
        text = (ROOT / "scripts" / "AUDIT_KRISHNA_FULL.ps1").read_text(encoding="utf-8")
        self.assertIn('fail=@($rows|Where-Object{$_.status -eq "FAIL"}).Count', text)
        self.assertIn('if($summary.fail){exit 2}else{exit 0}', text)


if __name__ == "__main__":
    unittest.main()
