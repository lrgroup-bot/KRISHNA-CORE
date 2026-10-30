"""Offline connection-first protocol tests with the actual Core catalogue."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "standalone" / "suryadev"))
from krishna_core.suryadev import SuryadevAgent
from krishna_core.suryadev_plan_delivery import approved_plan
from krishna_core.suryadev_tls_runtime import allowed_method_path
from suryadev_connection_bootstrap import ConnectionBootstrap, install_plan, canonical
from suryadev_dashboard_worker import DashboardWorkerControl


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.local = self.root / "local"
        self.local.mkdir()
        self.agent = SuryadevAgent(self.root / "core", clock=lambda: 1000)
        self.device = "suryadev-test"
        self.config = {"device_id": self.device, "fingerprint": "a" * 64}
        self.calls = []

    def transport(self, config, path, payload):
        self.calls.append(path)
        if path.endswith("heartbeat"):
            self.assertFalse((self.local / "learning-plan.json").exists())
            return self.agent.device_heartbeat(payload, authenticated=True)
        self.assertEqual(path, "/api/suryadev/learning-plan/request")
        return approved_plan(self.agent, self.device)

    def bootstrap(self):
        with patch("suryadev_connection_bootstrap.load_config", return_value=self.config):
            return ConnectionBootstrap(self.local, "unused", transport=self.transport, clock=lambda: 1000)

    def catalogue(self):
        self.agent.mission_backlog.catalogue.write_text(json.dumps({
            "schema": "krishna.suryadev.approved-curriculum.v1",
            "allowed_source_hosts": ["docs.python.org"],
            "missions": [{"id": "python", "topic": "Python reference",
                          "approved_urls": ["https://docs.python.org/3/"]}]}), encoding="utf-8")

    def test_connect_then_wait_then_receive_without_placeholder(self):
        client = self.bootstrap()
        self.assertIsNone(client.tick())
        self.assertFalse((self.local / "learning-plan.json").exists())
        ack = json.loads((self.local / "krishna-fleet-heartbeat-ack.json").read_text())
        self.assertTrue(ack["authenticated_core_reply"])
        self.assertFalse(self.agent.device_status(self.device)["learning_green"])
        self.catalogue()
        target = client.tick()
        self.assertEqual(json.loads(target.read_text())["approved_urls"], ["https://docs.python.org/3/"])
        self.assertEqual(len(list((self.local / "core-plan-evidence").glob("*.json"))), 1)
        self.assertEqual(self.calls[:2], ["/api/suryadev/device/heartbeat", "/api/suryadev/learning-plan/request"])

    def test_no_plan_delivery_before_authenticated_fresh_heartbeat(self):
        self.catalogue()
        with self.assertRaises(KeyError):
            approved_plan(self.agent, self.device)
        self.agent.device_heartbeat({"device_id": self.device}, authenticated=False)
        with self.assertRaises(PermissionError):
            approved_plan(self.agent, self.device)
        self.agent.device_heartbeat({"device_id": self.device}, authenticated=True)
        self.agent.clock = lambda: 1200
        with self.assertRaises(PermissionError):
            approved_plan(self.agent, self.device)

    def test_auth_failure_does_not_request_or_write_plan(self):
        client = self.bootstrap()
        client.transport = lambda *args: {"accepted": False, "device_id": self.device}
        with self.assertRaises(ValueError):
            client.tick()
        self.assertEqual(list(self.local.iterdir()), [])

    def test_invalid_or_widened_delivery_never_published(self):
        self.catalogue()
        self.agent.device_heartbeat({"device_id": self.device}, authenticated=True)
        good = approved_plan(self.agent, self.device)
        for mutation in ("digest", "identity", "empty", "approval", "delegation", "quota"):
            reply = copy.deepcopy(good)
            if mutation == "digest": reply["sha256"] = "0" * 64
            if mutation == "identity": reply["device_id"] = "suryadev-other"
            if mutation == "empty": reply["plan"]["approved_urls"] = []
            if mutation == "approval": reply["approval"]["missions"][0]["approved_urls"] = ["https://evil.example/"]
            if mutation == "delegation": reply["plan"]["paired_core_host_delegation"] = True
            if mutation == "quota": reply["plan"]["max_queued"] = 1000
            if mutation != "digest":
                reply["sha256"] = hashlib.sha256(canonical({k:v for k,v in reply.items() if k != "sha256"})).hexdigest()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                install_plan(self.local, self.config, reply)
            self.assertFalse((self.local / "learning-plan.json").exists())

    def test_existing_owner_file_is_never_overwritten(self):
        self.catalogue()
        self.agent.device_heartbeat({"device_id": self.device}, authenticated=True)
        target = self.local / "learning-plan.json"
        target.write_text("owner data")
        with self.assertRaises(FileExistsError):
            install_plan(self.local, self.config, approved_plan(self.agent, self.device))
        self.assertEqual(target.read_text(), "owner data")

    def test_dashboard_can_boot_paired_worker_without_plan(self):
        folder = Path(__file__).resolve().parents[2] / "standalone" / "suryadev"
        ctl = DashboardWorkerControl(self.local, folder)
        self.addCleanup(ctl.close)
        with patch.object(ctl, "core_pairing", return_value={"configured":True,"ready":True}), patch(
                "suryadev_dashboard_worker.subprocess.Popen") as spawn:
            result = ctl.start(model="collector")
        self.assertFalse(result["approved_plan_loaded"])
        self.assertIn("--fleet-mode", spawn.call_args.args[0])
        self.assertNotIn("--plan", spawn.call_args.args[0])
        self.assertFalse((self.local / "learning-plan.json").exists())

    def test_new_protocol_is_explicitly_tls_allowed(self):
        self.assertTrue(allowed_method_path("POST", "/api/suryadev/learning-plan/request"))
        self.assertFalse(allowed_method_path("GET", "/api/suryadev/learning-plan/request"))

    def test_real_pinned_tls_rejects_bad_pin_and_token_then_delivers_plan(self):
        from datetime import datetime, timedelta, timezone
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import ssl
        import threading
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.x509.oid import NameOID
        except ImportError:
            self.skipTest("optional cryptography required for ephemeral TLS fixture")
        from krishna_core.device_pairing import DevicePairingStore
        from suryadev_krishna_mission import post_core
        self.catalogue()
        agent = self.agent
        pairing = DevicePairingStore(self.root / "test-pairing")
        credential = "test-only-credential-" + "x" * 48
        pending = pairing.request(self.device, "fixture", hashlib.sha256(credential.encode()).hexdigest())
        pairing.approve(pending["request_id"])
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "bootstrap fixture")])
        now = datetime.now(timezone.utc)
        certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(hours=1))
            .sign(key, hashes.SHA256()))
        cert = self.root / "test-cert.pem"
        secret = self.root / "test-key.pem"
        cert.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        secret.write_bytes(key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append(self.path)
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                device = self.headers.get("X-Krishna-Device", "")
                token = self.headers.get("Authorization", "").removeprefix("Device ")
                if not pairing.verify(device, token):
                    status, result = 401, {"error": "paired device required"}
                elif device != data.get("device_id"):
                    status, result = 403, {"error": "identity mismatch"}
                elif self.path.endswith("heartbeat"):
                    status, result = 200, agent.device_heartbeat(data, authenticated=True)
                else:
                    try:
                        status, result = 200, approved_plan(agent, device)
                    except (KeyError, PermissionError):
                        status, result = 403, {"error": "heartbeat required"}
                raw = json.dumps(result).encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, secret)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            config = {**self.config, "host":"127.0.0.1", "port":server.server_port,
                      "credential":credential,
                      "fingerprint":hashlib.sha256(certificate.public_bytes(serialization.Encoding.DER)).hexdigest()}
            with self.assertRaises(ssl.SSLError):
                post_core({**config,"fingerprint":"0"*64}, "/api/suryadev/device/heartbeat", {})
            self.assertEqual(requests, [])  # no token-bearing HTTP request before pin verification
            with self.assertRaisesRegex(RuntimeError, "401"):
                post_core({**config,"credential":"wrong"}, "/api/suryadev/device/heartbeat", {})
            with self.assertRaisesRegex(RuntimeError, "403"):
                post_core(config, "/api/suryadev/learning-plan/request", {"device_id":self.device})
            with patch("suryadev_connection_bootstrap.load_config", return_value=config):
                client = ConnectionBootstrap(self.local, "unused", transport=post_core)
            self.assertTrue(client.tick().is_file())
            self.assertEqual(requests[-2:], ["/api/suryadev/device/heartbeat", "/api/suryadev/learning-plan/request"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
