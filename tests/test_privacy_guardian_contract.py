from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]


class PrivacyGuardianArchitectureContracts(unittest.TestCase):
    def test_privacy_guardian_is_internal_to_kabach_and_not_main_menu(self):
        requirements=json.loads((ROOT/"core"/"requirements"/"krishna_chat_requirements.json").read_text(encoding="utf-8"))
        kabach=next(x for x in requirements["groups"] if x["id"]=="kabach")
        text=" ".join(kabach["requirements"]).lower()
        self.assertIn("privacy",text)
        self.assertIn("internal",text)
        self.assertIn("main menu",text)

        web=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8")
        # Do not introduce a dedicated permanent nav item for this internal capability.
        self.assertNotIn('data-page="privacy-guardian"',web)
        self.assertNotIn('>Privacy Guardian</button>',web)

    def test_privacy_routes_and_shared_actions_exist(self):
        server=(ROOT/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8")
        orchestrator=(ROOT/"core"/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        for route in (
            "/api/kabach/privacy/status",
            "/api/kabach/privacy/history",
            "/api/kabach/privacy/metrics",
            "/api/kabach/privacy/audit",
            "/api/kabach/privacy/clean-url",
            "/api/kabach/privacy/baseline",
            "/api/kabach/privacy/compare",
            "/api/kabach/privacy/release-gate",
        ):
            self.assertIn(route,server)
        for action in (
            "kabach.privacy.audit",
            "kabach.privacy.clean_url",
            "kabach.privacy.baseline.save",
            "kabach.privacy.baseline.compare",
            "kabach.privacy.release_gate",
        ):
            self.assertIn(action,orchestrator)

    def test_restrictive_privacy_tools_are_adapters_not_embedded_dependencies(self):
        doc=(ROOT/"docs"/"KABACH_PRIVACY_GUARDIAN.md").read_text(encoding="utf-8")
        mobile=(ROOT/"core"/"krishna_core"/"privacy_guardian"/"mobile.py").read_text(encoding="utf-8")
        guardian=(ROOT/"core"/"krishna_core"/"privacy_guardian"/"guardian.py").read_text(encoding="utf-8")
        self.assertIn("MobSF remains an independent GPL service",mobile)
        self.assertIn("OpenWPM research mode",doc)
        self.assertIn("external adapter only",guardian)
        self.assertNotIn("import mobsf",mobile.lower())
        self.assertNotIn("import openwpm",guardian.lower())

    def test_privacy_external_probe_is_disabled_by_default_and_no_third_party_ip_service_is_hardcoded(self):
        network=(ROOT/"core"/"krishna_core"/"privacy_guardian"/"network.py").read_text(encoding="utf-8")
        self.assertIn("KRISHNA_PRIVACY_PROBE_URL",network)
        self.assertIn("disabled unless explicitly configured",network)
        for forbidden in ("api.ipify.org","ifconfig.me","ipinfo.io","icanhazip.com","browserleaks.com"):
            self.assertNotIn(forbidden,network.lower())

    def test_ci_has_real_browser_and_real_apk_privacy_gates(self):
        core_ci=(ROOT/".github"/"workflows"/"test-core.yml").read_text(encoding="utf-8")
        mobile_ci=(ROOT/".github"/"workflows"/"build-mobile-v3.yml").read_text(encoding="utf-8")
        self.assertIn("privacy-browser-e2e",core_ci)
        self.assertIn("playwright install chromium",core_ci)
        self.assertIn("KRISHNA_PRIVACY_BROWSER_E2E",core_ci)
        self.assertIn("KABACH real APK privacy gate",mobile_ci)
        self.assertIn("basic_apk_privacy_audit",mobile_ci)
        self.assertIn("KABACH_MOBILE_PRIVACY_GATE_OK",mobile_ci)

    def test_runtime_acceptance_keeps_evidence_on_e_drive(self):
        script=(ROOT/"scripts"/"CHECK_KABACH_PRIVACY.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('E:\\Krishna-The GOD',script)
        self.assertIn("Assert-EPath",script)
        self.assertIn("state\\privacy",script)
        self.assertIn("External network",script)
        self.assertIn("Mobile dynamic",script)


if __name__=="__main__":
    unittest.main()
