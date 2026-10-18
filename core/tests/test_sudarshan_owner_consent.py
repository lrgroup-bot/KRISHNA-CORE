import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from krishna_core.sudarshan_owner_consent import OwnerConsent

OBSERVE = "sudarshan.research.observe"
MISSION = "sudarshan.research.mission"

class OwnerConsentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"runtime.sqlite"
        self.gate=OwnerConsent("fe"*32,self.path)
        self.payload={"project_id":"p","engine":"REA","spec":{"target":"sample"}}
    def test_valid_exact_scope_consumes_once(self):
        proof=self.gate.issue(OBSERVE,"p",self.payload)
        self.assertTrue(self.gate.consume(proof,OBSERVE,"p",self.payload))
        with self.assertRaises(PermissionError):
            self.gate.consume(proof,OBSERVE,"p",self.payload)
    def test_replay_blocked_after_restart(self):
        proof=self.gate.issue(OBSERVE,"p",self.payload)
        self.gate.consume(proof,OBSERVE,"p",self.payload)
        restarted=OwnerConsent("fe"*32,self.path)
        with self.assertRaises(PermissionError):
            restarted.consume(proof,OBSERVE,"p",self.payload)
    def test_changed_payload_denied(self):
        proof=self.gate.issue(OBSERVE,"p",self.payload)
        with self.assertRaises(PermissionError):
            self.gate.consume(proof,OBSERVE,"p",{**self.payload,"engine":"MiroFish"})
    def test_project_and_action_bound(self):
        proof=self.gate.issue(OBSERVE,"p",self.payload)
        for action,project in ((MISSION,"p"),(OBSERVE,"other")):
            with self.assertRaises(PermissionError):
                self.gate.consume(proof,action,project,self.payload)
    def test_tampered_invalid_and_missing_tokens_denied(self):
        proof=self.gate.issue(OBSERVE,"p",self.payload)
        for value in (None, "", "bogus", "a.b", proof[:-3]+"abc", "!!"+"."+"!!"):
            with self.assertRaises(PermissionError, msg=str(value)):
                self.gate.consume(value,OBSERVE,"p",self.payload)
    def test_expiry_and_future_issue_denied(self):
        with patch("krishna_core.sudarshan_owner_consent.time.time",return_value=10000):
            proof=self.gate.issue(OBSERVE,"p",self.payload,ttl_seconds=1)
        with patch("krishna_core.sudarshan_owner_consent.time.time",return_value=10002):
            with self.assertRaises(PermissionError):
                self.gate.consume(proof,OBSERVE,"p",self.payload)
    def test_unsafe_config_rejected(self):
        with self.assertRaises(ValueError):
            OwnerConsent("0"*64,self.path)
        with self.assertRaises(ValueError):
            self.gate.issue(OBSERVE,"p",self.payload,ttl_seconds=301)
        with self.assertRaises(ValueError):
            self.gate.issue("deploy.production","p",self.payload)
    def test_owner_token_not_bound_into_payload_digest(self):
        proof=self.gate.issue(OBSERVE,"p",self.payload)
        self.assertTrue(self.gate.consume(
            proof,OBSERVE,"p",{**self.payload,"owner_token":proof}))
    def test_wrong_key_denied(self):
        proof=self.gate.issue(OBSERVE,"p",self.payload)
        other=OwnerConsent("ab"*32,self.path)
        with self.assertRaises(PermissionError):
            other.consume(proof,OBSERVE,"p",self.payload)

if __name__=="__main__":
    unittest.main()
