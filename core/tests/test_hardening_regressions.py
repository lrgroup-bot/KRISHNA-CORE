import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from krishna_core.development_operator import DevelopmentOperator
from krishna_core.promotion_runtime import PromotionRuntime
from krishna_core.promotion_manager import PromotionManager
from krishna_core.attachments import AttachmentStore
from krishna_core.plugin_executor import PluginExecutor
from krishna_core.plugin_runtime import PluginRegistry
from krishna_core.realtime_session import RealtimeSessionStore
from krishna_core.model_gateway import ModelGatewayRegistry
from krishna_core.remote_access import PrivateRemotePolicy
from krishna_core.kabach import KabachAgent


class _Browser:
    pass


class HardeningRegressionTests(unittest.TestCase):
    def test_clean_git_status_is_really_clean(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            subprocess.run(["git","init"],cwd=root,check=True,capture_output=True)
            subprocess.run(["git","config","user.email","krishna@example.invalid"],cwd=root,check=True)
            subprocess.run(["git","config","user.name","KRISHNA Test"],cwd=root,check=True)
            (root/"a.txt").write_text("x",encoding="utf-8")
            subprocess.run(["git","add","a.txt"],cwd=root,check=True)
            subprocess.run(["git","commit","-m","init"],cwd=root,check=True,capture_output=True)
            out=DevelopmentOperator(_Browser()).git_snapshot(root)
            self.assertTrue(out["ok"])
            self.assertTrue(out["clean"])
            self.assertEqual(out["status"],"")

    def test_promotion_runtime_rejects_escape_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            shadow=root/"shadow"; working=root/"working"
            shadow.mkdir();working.mkdir()
            (root/"outside.txt").write_text("secret",encoding="utf-8")
            with self.assertRaises(ValueError):
                PromotionRuntime().promote(shadow,working,["../outside.txt"],verified=True)

    def test_realtime_store_hashes_device_filename_and_fails_closed_on_corruption(self):
        with tempfile.TemporaryDirectory() as td:
            store=RealtimeSessionStore(td)
            device="android/../../primary"
            event=store.publish(device,"hello",{"ok":True},idempotency_key="k1")
            self.assertEqual(event["seq"],1)
            path=store._path(device)
            self.assertTrue(path.is_file())
            self.assertNotIn("android",path.name)
            self.assertNotIn("..",path.name)
            path.write_text("{bad-json",encoding="utf-8")
            with self.assertRaises(RuntimeError):
                store.after(device,0)

    def test_attachment_payload_integrity_is_verified(self):
        import base64
        with tempfile.TemporaryDirectory() as td:
            store=AttachmentStore(td)
            chat="11111111-1111-4111-8111-111111111111"
            item=store.save(chat,"evidence.txt",base64.b64encode(b"trusted").decode(),"text/plain")
            row,path=store.resolve(chat,item["attachment_id"])
            path.write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                store.read(chat,item["attachment_id"])

    def test_plugin_endpoint_blocks_metadata_and_public_cleartext(self):
        for url in ("http://169.254.169.254/latest/meta-data/","http://metadata.google.internal/"):
            with self.assertRaises(PermissionError):
                PluginExecutor._endpoint(url)
        with self.assertRaises(PermissionError):
            PluginExecutor._endpoint("http://8.8.8.8/")
        self.assertEqual(PluginExecutor._endpoint("http://127.0.0.1:8766/").hostname,"127.0.0.1")

    def test_corrupt_plugin_registry_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            state=Path(td)
            (state/"plugins.json").write_text("{broken",encoding="utf-8")
            with self.assertRaises(RuntimeError):
                PluginRegistry(state)

    def test_promotion_manager_project_name_cannot_escape_backup_root(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);live=root/"live";candidate=root/"candidate";backups=root/"backups"
            live.mkdir();candidate.mkdir()
            (live/"a.txt").write_text("old",encoding="utf-8")
            (candidate/"a.txt").write_text("new",encoding="utf-8")
            out=PromotionManager(backups).promote("../../escape",live,candidate,lambda _:{"verified":True})
            backup=Path(out["backup"]).resolve()
            backup.relative_to(backups.resolve())
            self.assertEqual((live/"a.txt").read_text(encoding="utf-8"),"new")

    def test_kabach_egress_resolves_dns_before_allowing(self):
        class Memory:
            def audit(self,*_args):pass
        k=KabachAgent(Memory())
        fake=[(2,1,6,"",("169.254.169.254",443))]
        with patch("krishna_core.kabach.socket.getaddrinfo",return_value=fake):
            out=k.inspect_egress("https://metadata-alias.example/x",allowed_domains=["metadata-alias.example"])
        self.assertFalse(out["allowed"])
        self.assertIn("private_or_reserved_ip",out["evidence"])

    def test_testing_lead_traversal_is_non_destructive_by_default(self):
        source=(Path(__file__).resolve().parents[1]/"krishna_core"/"browser_operator.py").read_text(encoding="utf-8")
        self.assertIn('"consequential_control"',source)
        self.assertIn('wait_until="domcontentloaded"',source)
        self.assertNotIn('page.goto(url,wait_until="networkidle")',source)

    def test_corrupt_model_gateway_registry_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"gateways.json"
            path.write_text("{broken",encoding="utf-8")
            reg=ModelGatewayRegistry(path)
            with self.assertRaises(RuntimeError):
                reg.register("x","https://127.0.0.1","m","secret")

    def test_model_gateway_blocks_link_local_metadata_targets(self):
        with self.assertRaises(PermissionError):
            ModelGatewayRegistry._validate_url("https://169.254.169.254")
        with self.assertRaises(PermissionError):
            ModelGatewayRegistry._validate_url("https://[fe80::1]")

    def test_remote_policy_matches_documented_lan_ranges(self):
        p=PrivateRemotePolicy()
        self.assertTrue(p.allowed("192.168.1.20"))
        self.assertTrue(p.allowed("10.1.2.3"))
        self.assertTrue(p.allowed("172.16.1.2"))
        self.assertTrue(p.allowed("fd00::20"))
        self.assertFalse(p.allowed("192.0.2.10"))
        self.assertFalse(p.allowed("8.8.8.8"))

    def test_realtime_store_migrates_legacy_session_without_deleting_it(self):
        with tempfile.TemporaryDirectory() as td:
            store=RealtimeSessionStore(td)
            device="android-primary"
            legacy=store._legacy_path(device)
            legacy.write_text(json.dumps({"next_seq":2,"events":[{"id":"x","seq":1,"type":"old","payload":{},"ts":1}],"seen":{}}),encoding="utf-8")
            rows=store.after(device,0)
            self.assertEqual(rows[0]["type"],"old")
            self.assertTrue(store._path(device).is_file())
            self.assertTrue(legacy.is_file())


if __name__=="__main__":
    unittest.main()
