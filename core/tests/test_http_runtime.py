"""Real HTTP regression tests. All writes use a disposable database and project."""
import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request


class HTTPRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        env = dict(os.environ, KRISHNA_DB=str(cls.root / "core.db"),
                   KRISHNA_HOST="127.0.0.1", KRISHNA_PORT=str(cls.port),
                   KRISHNA_ALLOW_ACTIONS="0")
        cls.log = (cls.root / "server.log").open("w")
        cls.proc = subprocess.Popen([sys.executable, "-m", "krishna_core.server"],
            cwd=Path(__file__).resolve().parents[1], env=env,
            stdout=cls.log, stderr=cls.log)
        for _ in range(100):
            try:
                if cls.call("/health")[0] == 200: break
            except OSError: time.sleep(.1)
        else:
            cls.log.flush()
            details=""
            try:details=(cls.root/"server.log").read_text(encoding="utf-8",errors="replace")[-6000:]
            except OSError:pass
            raise RuntimeError("test Core failed to start\n"+details)
        cls.call("/api/projects/register", {"name":"KRISHNA", "root":str(cls.root), "privacy":"local_only"})

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.log.close()
        cls.temp.cleanup()

    @classmethod
    def call(cls, path, data=None, headers=None):
        request = urllib.request.Request(f"http://127.0.0.1:{cls.port}"+path,
            data=None if data is None else json.dumps(data).encode(),
            headers={"Content-Type":"application/json", **(headers or {})})
        try: response = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as error: response = error
        with response:
            body = response.read()
            return response.status, json.loads(body) if "json" in response.headers.get("Content-Type", "") else body

    def test_read_endpoints(self):
        for path in ("/health", "/api/status", "/api/dashboard", "/api/capabilities",
                     "/api/projects", "/api/plugins", "/api/specialists", "/api/specialist-teams", "/api/resources",
                     "/api/tasks", "/api/core/state", "/api/core/neural-state",
                     "/api/project-graph", "/api/recovery/ladder", "/api/incidents",
                     "/api/garuda/status", "/api/commitments", "/api/autonomy/status", "/api/gyan-bhandar",
                     "/api/gyan-bhandar/pending", "/api/gyan-bhandar/inventory?project=KRISHNA", "/api/software-factory/workers/status",
                     "/api/narad/status", "/api/narad/workflows", "/api/narad/history", "/api/narad/connections", "/api/narad/dead-letters", "/api/narad/scheduler", "/api/intelligence/status",
                     "/api/brahmagyan/status", "/api/brahmagyan/council", "/api/brahmagyan/missions", "/api/brahmagyan/curiosity",
                     "/api/runtime/integrity", "/api/runtime/audit", "/api/requirements", "/api/garudanetra/sessions", "/api/ui-guardian/registry",
                     "/api/vision/status", "/api/voice/status", "/api/avatar/status", "/api/avatar/performance", "/api/remote/status", "/api/resilience/status", "/api/wearables",
                     "/api/models/gateways", "/api/secure-vault/status", "/api/mobile/pair/pending"):
            with self.subTest(path=path): self.assertEqual(self.call(path)[0], 200)

    def test_requirements_search_contract(self):
        code,d=self.call("/api/requirements?q=mobile")
        self.assertEqual(code,200)
        self.assertGreater(d["count"],0)
        self.assertTrue(any("mobile" in (x.get("group","")+x.get("title","")+x.get("requirement","")).lower() for x in d["matches"]))

    def test_ui_guardian_registry_lifecycle(self):
        code,item=self.call("/api/ui-guardian/register",{"name":"HTTP UI","project":"KRISHNA","url":"http://127.0.0.1:8766","state":"candidate"})
        self.assertEqual(code,201)
        self.assertEqual(self.call("/api/ui-guardian/transition",{"entry_id":item["id"],"target":"stable","verified":True})[0],403)
        self.assertEqual(self.call("/api/ui-guardian/transition",{"entry_id":item["id"],"target":"rejected","verified":False})[0],200)

    def test_garudanetra_live_routes_fail_closed(self):
        self.assertEqual(self.call("/api/garudanetra/session")[0],400)
        self.assertEqual(self.call("/api/garudanetra/frame?id=missing")[0],404)
        self.assertEqual(self.call("/api/garudanetra/session/start",{"project":"KRISHNA","url":"file:///tmp/x"})[0],400)
        self.assertEqual(self.call("/api/garudanetra/session/control",{"session_id":"missing","action":"pause"})[0],404)

    def test_protected_project_role_is_read_only(self):
        protected=self.root/"protected";protected.mkdir(exist_ok=True)
        code,row=self.call("/api/projects/register",{"name":"PROTECTED-TEST","root":str(protected),"privacy":"local_only","role":"protected","allowed_actions":["edit"]})
        self.assertEqual(code,200);self.assertEqual(row["role"],"protected")
        projects=self.call("/api/projects")[1]["projects"]
        self.assertEqual(next(x for x in projects if x["name"]=="PROTECTED-TEST")["role"],"protected")

    def test_remote_voice_vision_resilience_contracts(self):
        self.assertEqual(self.call("/api/remote/status")[1]["mode"],"private-network-only")
        voice=self.call("/api/voice/status")[1]
        self.assertEqual(voice["language"],"or-IN");self.assertEqual(voice["wake"]["wake_word"],"Krishna")
        vision=self.call("/api/vision/status")[1];self.assertTrue(vision["local"])
        resilience=self.call("/api/resilience/status")[1]
        self.assertIn("worker_supervisor",resilience);self.assertIn("model_memory",resilience)

    def test_wearable_registration_is_unverified_until_explicit_verify(self):
        code,row=self.call("/api/wearables/register",{"name":"HTTP headset","kind":"headset","capabilities":["bluetooth_audio","microphone"]})
        self.assertEqual(code,201);self.assertFalse(row["verified"])
        self.assertEqual(self.call("/api/wearables/verify",{"device_id":row["id"],"capabilities":["bluetooth_audio","microphone"]})[0],400)
        code,row=self.call("/api/wearables/verify",{"device_id":row["id"],"capabilities":["bluetooth_audio","microphone"],"evidence":"HTTP acceptance hardware evidence"})
        self.assertEqual(code,200);self.assertTrue(row["verified"])

    def test_garudanetra_persistent_mode_requires_approval(self):
        code,_=self.call("/api/garudanetra/session/start",{"project":"KRISHNA","url":"http://127.0.0.1:%d/"%self.port,"mode":"persistent_workspace"})
        self.assertEqual(code,403)

    def test_avatar_preview_is_real_webp(self):
        code, body = self.call("/api/avatar360")
        self.assertEqual(code, 200)
        self.assertEqual(body[:4], b"RIFF")
        self.assertEqual(body[8:12], b"WEBP")

    def test_avatar_character_bible_is_canonical_and_cross_surface(self):
        code,status=self.call("/api/avatar/status")
        self.assertEqual(code,200)
        self.assertEqual(status["character_bible"],"character-bible-v1")
        self.assertIn("FLUTE",status["states"])
        self.assertIn("DHYAN",status["states"])
        code,bible=self.call("/api/avatar/performance")
        self.assertEqual(code,200)
        self.assertEqual(bible["version"],"character-bible-v1")
        for state in ("LISTENING","THINKING","SPEAKING","WISDOM","PLAYFUL","PROTECTION","FLUTE","DHYAN","SLEEPING","WAKING"):
            self.assertIn(state,bible["states"])
        self.assertEqual(bible["visual_identity"]["priority"],"face-first")
        self.assertIn("pc",bible["surface_contract"])
        self.assertIn("mobile",bible["surface_contract"])
        self.assertIn("glass",bible["surface_contract"])
        dashboard=self.call("/api/dashboard")[1]
        self.assertIn(dashboard["avatar_state"],bible["states"])
        self.assertEqual(dashboard["avatar_character_bible"],"character-bible-v1")

    def test_favicon_probe_never_creates_browser_404_noise(self):
        code, body = self.call("/favicon.ico")
        self.assertEqual(code, 204)
        self.assertEqual(body, b"")

    def test_json_shape_and_empty_message(self):
        for data in ([], "text", 3, {"message":[]}, {"message":""}):
            with self.subTest(data=data): self.assertEqual(self.call("/api/core/chat", data)[0], 400)

    def test_cross_origin_request_cannot_mutate(self):
        self.assertEqual(self.call("/api/chats/create", {"project":"KRISHNA"},
            {"Origin":"https://untrusted.example"})[0], 403)
        self.assertEqual(self.call("/api/chats", headers={"Origin":"null"})[0], 403)
        self.assertEqual(self.call("/api/chats", headers={"Origin":f"http://127.0.0.1:{self.port}"})[0], 200)

    def test_mobile_spoof_does_not_mark_connected(self):
        before = self.call("/api/mobile/connection")[1]
        self.call("/api/status", headers={"X-Krishna-Device":"forged-device"})
        after = self.call("/api/mobile/connection")[1]
        self.assertEqual(before["requests"], after["requests"])
        self.assertNotEqual(after["device"], "forged-device")

    def test_post_routing_ignores_query_string(self):
        code,row=self.call("/api/mobile/pair/request?source=mobile",{"device_id":"query-route-phone","name":"Query route"})
        self.assertEqual(code,200)
        self.assertEqual(row["device_id"],"query-route-phone")

    def test_pairing_resume_and_invalid_cursor(self):
        pending = self.call("/api/mobile/pair/request", {"device_id":"test-phone"})[1]
        paired = self.call("/api/mobile/pair/approve", {"request_id":pending["request_id"]})[1]
        headers={"X-Krishna-Device":"test-phone", "Authorization":"Device "+paired["token"]}
        self.assertEqual(self.call("/api/mobile/resume")[0], 401)
        self.assertEqual(self.call("/api/mobile/resume", headers=headers)[0], 200)
        self.assertEqual(self.call("/api/mobile/resume?after=bad", headers=headers)[0], 400)
        self.assertTrue(self.call("/api/mobile/connection")[1]["connected"])
        self.assertEqual(self.call("/api/mobile/control", {"action":"shell"}, headers)[0], 403)
        for denied in ("filesystem","credentials","trading"):
            with self.subTest(denied=denied):
                self.assertEqual(self.call("/api/mobile/control", {"action":denied}, headers)[0], 403)

    def test_zero_code_pairing_uses_client_hash_without_returning_secret(self):
        import hashlib
        token="http-client-held-credential"
        digest=hashlib.sha256(token.encode()).hexdigest()
        code,pending=self.call("/api/mobile/pair/request",{"device_id":"zero-code-phone","name":"HTTP phone","credential_sha256":digest})
        self.assertEqual(code,200);self.assertNotIn("credential_sha256",pending)
        listed=self.call("/api/mobile/pair/pending")[1]["pending"]
        self.assertTrue(any(x["device_id"]=="zero-code-phone" and x["credential_proposed"] for x in listed))
        code,approved=self.call("/api/mobile/pair/approve",{"request_id":pending["request_id"]})
        self.assertEqual(code,200);self.assertNotIn("token",approved)
        headers={"X-Krishna-Device":"zero-code-phone","Authorization":"Device "+token}
        self.assertEqual(self.call("/api/mobile/resume",headers=headers)[0],200)

    def test_specialist_team_plan_keeps_krishna_authority(self):
        code,d=self.call("/api/specialist-teams/plan",{"project":"KRISHNA","task":"Fix frontend UI and verify responsive layout"})
        self.assertEqual(code,200)
        roles={x["role"] for x in d["roles"]}
        self.assertIn("frontend",roles);self.assertIn("testing",roles);self.assertIn("critic",roles);self.assertIn("verifier",roles)
        self.assertEqual(d["authority"],"KRISHNA")
        self.assertFalse(d["live_mutation_allowed"])

    def test_commitment_autonomy_is_explicit_and_allowlisted(self):
        self.assertEqual(self.call("/api/commitments/create",{"project":"KRISHNA","title":"unsafe","autonomy":{"enabled":True,"operation":"shell"}})[0],403)
        code,row=self.call("/api/commitments/create",{"project":"KRISHNA","title":"safe inspect","detail":{"goal":"inspect KRISHNA"},"autonomy":{"enabled":True,"operation":"investigate","interval_seconds":3600}})
        self.assertEqual(code,201)
        self.assertTrue(row["detail"]["autonomy"]["enabled"])
        status=self.call("/api/autonomy/status")[1]
        self.assertIn("investigate",status["safe_operations"])
        self.assertIn(row["commitment_id"],status["eligible"])
        self.assertEqual(self.call("/api/commitments/update",{"commitment_id":row["commitment_id"],"status":"cancelled","detail":row["detail"]})[0],200)

    def test_chats_and_attachment_lifecycle(self):
        code, chat = self.call("/api/chats/create", {"project":"KRISHNA", "title":"HTTP test"})
        self.assertEqual(code, 200)
        cid=chat["chat_id"]
        self.assertEqual(self.call("/api/chats/rename", {"chat_id":cid,"title":"Renamed"})[0],200)
        self.assertEqual(self.call("/api/attachments", {"chat_id":cid,"name":"note.txt",
            "data_b64":base64.b64encode(b"isolated test").decode(),"content_type":"text/plain"})[0],201)
        self.assertEqual(len(self.call("/api/attachments?chat_id="+cid)[1]["attachments"]),1)
        self.assertEqual(self.call("/api/chats/delete", {"chat_id":cid})[0],200)
        self.assertFalse(any(x["chat_id"]==cid for x in self.call("/api/chats")[1]["chats"]))

    def test_attachment_directory_escape_rejected(self):
        self.assertEqual(self.call("/api/attachments?chat_id=../../")[0],400)

    def test_unknown_promotion_and_action_are_blocked(self):
        self.assertIn(self.call("/api/work/promotion/apply", {"promotion_token":"unknown","approved":True})[0],(403,404,409))
        self.assertEqual(self.call("/api/work/run", {"project":"KRISHNA","goal":"test","action":"unknown","approved":True})[0],403)
        self.assertFalse(self.call("/api/capabilities")[1]["mutating_actions_enabled"])

    def test_gyan_typed_supersession_approval(self):
        code,p=self.call("/api/gyan-bhandar/propose",{"project":"KRISHNA","topic":"HTTP memory","lesson":"first","memory_kind":"semantic","provenance":{"source":"http"}})
        self.assertEqual(code,202)
        code,d=self.call("/api/gyan-bhandar/decide",{"approval_id":p["approval_id"],"approved":True})
        self.assertEqual(code,200); fp=d["learning"]["fingerprint"]
        code,p2=self.call("/api/gyan-bhandar/supersede",{"project":"KRISHNA","fingerprint":fp,"topic":"HTTP memory","lesson":"second","memory_kind":"semantic","provenance":{"reason":"new evidence"}})
        self.assertEqual(code,202)
        self.assertEqual(self.call("/api/gyan-bhandar/decide",{"approval_id":p2["approval_id"],"approved":True})[0],200)
        rows=self.call("/api/gyan-bhandar?project=KRISHNA&include_superseded=1")[1]["learnings"]
        self.assertTrue(any(x["status"]=="superseded" for x in rows))
        inv=self.call("/api/gyan-bhandar/inventory?project=KRISHNA")[1]
        self.assertGreaterEqual(inv["kinds"]["semantic"]["superseded"],1)

    def test_brahmagyan_deep_mission_is_action_native_and_not_instant_truth(self):
        code,status=self.call("/api/brahmagyan/status")
        self.assertEqual(code,200)
        self.assertEqual(status["name"],"BRAHMAGYAN")
        self.assertEqual(status["council"]["running_processes"],0)
        self.assertEqual(status["maturity_levels"][0]["code"],"L0")
        self.assertEqual(status["maturity_levels"][-1]["code"],"L8")
        code,receipt=self.call("/api/action-bus/dispatch",{
            "action":"brahmagyan.mission.create","project":"KRISHNA",
            "payload":{"project":"KRISHNA","topic":"Deep test knowledge","question":"What evidence supports this?","target_level":"L8"}
        })
        self.assertEqual(code,200)
        self.assertEqual(receipt["status"],"completed")
        mission=receipt["result"]
        self.assertEqual(mission["maturity"],"L0")
        self.assertEqual(mission["target_level"],"L8")
        self.assertIn("verify_sources",mission["deep_learning_loop"])
        self.assertIn("gautama",mission["review_flow"])
        self.assertIn("veda-vyasa",mission["review_flow"])

    def test_narad_workflow_lifecycle(self):
        code,w=self.call("/api/narad/workflows/create",{"name":"http-safe","trigger":{"type":"manual"},"steps":[{"action":"publish_event","topic":"http.test"}]})
        self.assertEqual(code,201); wid=w["id"]
        self.assertEqual(self.call("/api/narad/workflows/execute",{"workflow_id":wid})[0],409)
        self.assertEqual(self.call("/api/narad/workflows/promote",{"workflow_id":wid,"state":"sandbox"})[0],200)
        self.assertEqual(self.call("/api/narad/workflows/execute",{"workflow_id":wid})[0],200)
        self.assertEqual(self.call("/api/narad/workflows/promote",{"workflow_id":wid,"state":"stable"})[0],403)
        self.assertEqual(self.call("/api/narad/workflows/promote",{"workflow_id":wid,"state":"verified","verified":True})[0],200)
        self.assertEqual(self.call("/api/narad/workflows/promote",{"workflow_id":wid,"state":"stable","verified":True})[0],200)
        self.assertTrue(self.call("/api/narad/history")[1]["history"])

    def test_narad_webhook_and_connection_reference_contract(self):
        code,ref=self.call("/api/narad/connections/register",{"name":"HTTP n8n","provider":"n8n","env_var":"KRISHNA_HTTP_N8N_TOKEN"})
        self.assertEqual(code,201)
        self.assertEqual(ref["env_var"],"KRISHNA_HTTP_N8N_TOKEN")
        self.assertNotIn("secret",json.dumps(ref).lower())
        conns=self.call("/api/narad/connections")[1]["connections"]
        self.assertTrue(any(x["id"]==ref["id"] for x in conns))

        code,w=self.call("/api/narad/workflows/create",{"name":"incoming-http","trigger":{"type":"webhook"},"steps":[{"action":"publish_event","topic":"http.webhook"}]})
        self.assertEqual(code,201);wid=w["id"]
        self.assertEqual(self.call("/api/narad/workflows/promote",{"workflow_id":wid,"state":"sandbox"})[0],200)
        self.assertEqual(self.call("/api/narad/workflows/promote",{"workflow_id":wid,"state":"verified","verified":True})[0],200)
        self.assertEqual(self.call("/api/narad/workflows/promote",{"workflow_id":wid,"state":"stable","verified":True})[0],200)
        code,hook=self.call("/api/narad/webhooks/provision",{"workflow_id":wid})
        self.assertEqual(code,201)
        self.assertEqual(self.call(hook["path"],{"hello":"world"})[0],200)
        self.assertEqual(self.call("/api/narad/webhook/wrong",{"hello":"world"})[0],403)

    def test_narad_dead_letter_is_visible(self):
        code,w=self.call("/api/narad/workflows/create",{"name":"bad-action","trigger":{"type":"manual"},"steps":[{"action":"not_supported"}]})
        self.assertEqual(code,201);wid=w["id"]
        self.assertEqual(self.call("/api/narad/workflows/promote",{"workflow_id":wid,"state":"sandbox"})[0],200)
        self.assertEqual(self.call("/api/narad/workflows/execute",{"workflow_id":wid})[0],409)
        letters=self.call("/api/narad/dead-letters")[1]["dead_letters"]
        self.assertTrue(any(x["workflow_id"]==wid for x in letters))

    def test_plugin_lifecycle(self):
        code, plugin=self.call("/api/plugins/add", {"name":"Isolated test plugin","kind":"custom","enabled":False})
        self.assertEqual(code,200)
        self.assertEqual(self.call("/api/plugins/enable", {"id":plugin["id"],"enabled":True})[0],200)
        self.assertEqual(self.call("/api/plugins/enable", {"id":plugin["id"],"enabled":False})[0],200)
        self.assertEqual(self.call("/api/plugins/remove", {"id":plugin["id"]})[0],200)


if __name__ == "__main__": unittest.main()


class NaradHttpContractTests(unittest.TestCase):
    def test_server_exposes_narad_routes(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/"krishna_core"/"server.py").read_text(encoding="utf-8")
        for route in ("/api/narad/status","/api/narad/workflows","/api/narad/history",
                      "/api/narad/workflows/create","/api/narad/workflows/promote",
                      "/api/narad/workflows/execute","/api/narad/connections/register","/api/narad/connections",
                      "/api/narad/dead-letters","/api/narad/dead-letters/retry","/api/narad/webhooks/provision",
                      "/api/narad/scheduler","/api/narad/scheduler/tick","/api/intelligence/status"):
            self.assertIn(route,source)
