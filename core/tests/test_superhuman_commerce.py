import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.application_security import ApplicationSecurityLoop
from krishna_core.node_registry import NodeRegistry
from krishna_core.node_execution import TrustedNodeExecutor
from krishna_core.gmail_triage import GmailTriage
from krishna_core.github_pr_review import GitHubPRReviewer
from krishna_core.manibhadra_commerce import ManibhadraCommerce
from krishna_core.marketplace_adapters import MarketplaceAdapterRegistry
from krishna_core.narad.providers import NaradProviderHub
from krishna_core.narad.runtime import NaradRuntime
from krishna_core.automation_bus import AutomationBus
from krishna_core.plugin_runtime import PluginRegistry
from krishna_core.skill_compiler import SkillCompiler
from krishna_core.superhuman_operator import SuperhumanOperatorPolicy
from krishna_core.social_channels import SocialChannelRegistry
from krishna_core.workflow_recording import WorkflowRecorder
from krishna_core.windows_worker_sandbox import WindowsWorkerSandbox


class SuperhumanCommerceTests(unittest.TestCase):
    def test_superhuman_policy_keeps_irreversible_actions_owner_gated(self):
        p=SuperhumanOperatorPolicy({"trash":True})
        self.assertTrue(p.decide("read")["allowed"])
        self.assertFalse(p.decide("permanent_delete")["allowed"])
        self.assertTrue(p.decide("permanent_delete",approved=True)["allowed"])
        self.assertFalse(p.decide("trash",confidence=0.90)["allowed"])
        self.assertTrue(p.decide("trash",confidence=0.999)["allowed"])

    def test_gmail_triage_is_conservative_about_delete(self):
        t=GmailTriage()
        v=t.classify({"subject":"Lottery winner","body":"claim your prize now"})
        self.assertEqual(v["category"],"spam")
        self.assertNotEqual(v["recommended_action"],"trash")
        m=t.classify({},{"category":"spam","confidence":0.999,"reasons":["model"]})
        self.assertEqual(m["recommended_action"],"trash")
        self.assertTrue(m["requires_owner_approval"])

    def test_manibhadra_marketplace_seo_guardrails(self):
        m=ManibhadraCommerce()
        plan=m.listing_plan("amazon",{"name":"Steel Water Bottle","brand":"LRS","features":["Leak resistant","1 litre"]},
                            ["steel bottle","best","cheapest","water bottle"])
        self.assertLessEqual(len(plan["title"]),75)
        self.assertNotIn("best",plan["search_terms"])
        self.assertNotIn("cheapest",plan["search_terms"])
        self.assertTrue(plan["publish_requires_owner_approval"])
        offer=m.supplier_offer("Steel Water Bottle",seller_name="Supplier")
        self.assertTrue(offer["requires_owner_approval_to_send"])

    def test_marketplace_registry_tells_api_truth(self):
        r=MarketplaceAdapterRegistry()
        self.assertEqual(r.get("amazon","listing_put")["mode"],"official_api")
        self.assertTrue(r.get("amazon","listing_put")["approval_required"])
        self.assertEqual(r.get("meesho","seller_portal_write")["mode"],"authorized_browser")

    def test_compute_node_reuses_canonical_trusted_registry(self):
        with tempfile.TemporaryDirectory() as td:
            f=NodeRegistry(Path(td)/"nodes.json")
            with self.assertRaises(PermissionError):
                f.enroll("Mac Worker","0123456789abcdef",approved=False)
            node=f.enroll("Mac Worker","0123456789abcdef",approved=True)
            with self.assertRaises(PermissionError):
                f.configure_execution(node.id,platform="macos",capabilities=["build"],approved=False)
            f.configure_execution(node.id,platform="macos",capabilities=["build","render"],endpoint="ssh://builder@mac.local",workspace_root="/srv/krishna",approved=True)
            f.heartbeat(node.id)
            self.assertEqual(f.select("build")["id"],node.id)
            executor=TrustedNodeExecutor(f)
            with patch("krishna_core.node_execution.shutil.which",return_value="/usr/bin/ssh"):
                plan=executor.plan("build",["python3","-m","unittest"],"macos")
            self.assertTrue(plan["ready"])
            self.assertEqual(plan["target"],"builder@mac.local")
            self.assertEqual(plan["workspace_root"],"/srv/krishna")

    def test_record_to_skill_is_candidate_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            rec=WorkflowRecorder(root/"recordings",SkillCompiler(root/"skills"))
            s=rec.start("Android smoke","KRISHNA")
            rec.append(s["session_id"],"open","Android Studio")
            rec.append(s["session_id"],"screenshot","emulator")
            out=rec.finish(s["session_id"])
            self.assertEqual(out["skill_candidate"]["status"],"candidate")

    def test_pr_reviewer_blocks_failed_checks_and_high_security(self):
        r=GitHubPRReviewer()
        out=r.review({"title":"x","body":"intent"},[{"filename":"a.py","changes":5}],
                     [{"conclusion":"failure"}],[{"severity":"high","rule":"secret"}])
        self.assertFalse(out["accepted"])
        self.assertFalse(out["auto_merge"])

    def test_application_security_loop_is_candidate_only(self):
        a=ApplicationSecurityLoop()
        plan=a.reproduction_plan({"rule":"python_eval"},Path.cwd())
        self.assertFalse(plan["live_target_allowed"])
        self.assertFalse(plan["network_external_target_allowed"])

    def test_windows_sandbox_never_claims_ready_before_bootstrap(self):
        with tempfile.TemporaryDirectory() as td:
            s=WindowsWorkerSandbox(td)
            plan=s.plan(Path(td)/"worktree","worker-1")
            self.assertFalse(plan["ready"])
            self.assertEqual(plan["provider"],"openai-codex-windows-sandbox")
            self.assertIn("setup_command",plan)

    def test_curated_plugin_catalog_contains_requested_integrations(self):
        with tempfile.TemporaryDirectory() as td:
            r=PluginRegistry(td)
            by_id={x["id"]:x for x in r.list()}
            for pid in ("gmail","google-drive","agentmarkup","windsurf","blackbox-ai","amazon-sp-api","flipkart-seller","meesho-seller","metricool","windsor-ai","shopify","semrush","agentmail","superhuman-mail"):
                self.assertIn(pid,by_id)
            self.assertTrue(by_id["agentmarkup"]["free"])
            self.assertFalse(by_id["blackbox-ai"]["free"])
            self.assertFalse(by_id["blackbox-ai"]["enabled"])

    def test_social_registry_separates_direct_and_connector_channels(self):
        s=SocialChannelRegistry()
        self.assertEqual(s.get("whatsapp")["mode"],"narad_direct")
        self.assertEqual(s.get("instagram")["mode"],"connector_required")
        self.assertIn("publish",s.get("instagram")["mutating"])

    def test_narad_registers_gmail_read_and_trash_operations(self):
        n=NaradRuntime(None,AutomationBus())
        ops={(x["provider"],x["operation"]):x for x in n.connectors.list()}
        self.assertFalse(ops[("gmail","list_messages")]["mutating"])
        self.assertTrue(ops[("gmail","trash_message")]["mutating"])

    def test_gmail_provider_list_and_trash_use_official_api_shapes(self):
        hub=NaradProviderHub()
        with patch("krishna_core.narad.providers._json_request") as req:
            req.return_value={"status":200,"ok":True,"data":{}}
            hub.send("gmail","list_messages",{"q":"is:unread","max_results":25},{"Authorization":"Bearer x"})
            args,kwargs=req.call_args
            self.assertIn("gmail.googleapis.com/gmail/v1/users/me/messages?",args[0])
            self.assertEqual(kwargs["method"],"GET")
        with patch("krishna_core.narad.providers._json_request") as req:
            req.return_value={"status":200,"ok":True,"data":{}}
            hub.send("gmail","trash_message",{"message_id":"abc"},{"Authorization":"Bearer x"})
            args,kwargs=req.call_args
            self.assertTrue(args[0].endswith("/abc/trash"))
            self.assertEqual(kwargs["body"],{})


class IntegrationContractTests(unittest.TestCase):
    def test_orchestrator_exposes_superhuman_and_manibhadra_actions(self):
        root=Path(__file__).resolve().parents[2]
        text=(root/"core"/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        for action in (
            "superhuman.status","social.channels.status","social.channel","gmail.triage","manibhadra.status","manibhadra.research",
            "manibhadra.evaluate","manibhadra.supplier_offer","manibhadra.listing_plan",
            "marketplace.capabilities","compute.nodes.status","compute.nodes.configure","compute.nodes.plan","compute.nodes.run",
            "workflow.record.start","workflow.record.finish","github.pr.review",
            "application.security.threat_model","windows.sandbox.status","windows.sandbox.setup_plan","windows.sandbox.plan","windows.sandbox.run",
        ):
            self.assertIn(f'"{action}"',text)


if __name__=="__main__":
    unittest.main()
