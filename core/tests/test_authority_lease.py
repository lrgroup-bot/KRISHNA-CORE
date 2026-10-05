import json
import tempfile
import unittest
from pathlib import Path

from krishna_core.authority_lease import AuthorityLeaseGate


class _Clock:
    def __init__(self, value=1000.0):
        self.value=float(value)
    def __call__(self):
        return self.value
    def advance(self, seconds):
        self.value += float(seconds)


class AuthorityLeaseGateTests(unittest.TestCase):
    def make_gate(self, *, locked=False, ttl=30, clock=None, root=None):
        if root is None:
            root=Path(tempfile.mkdtemp(prefix="krishna-authority-"))
        return AuthorityLeaseGate(root, ttl_seconds=ttl, clock=clock, initially_locked=locked)

    def approved_lease(self, gate, *, payload=None, action="desktop.rpa.run", source="pc", actor="owner"):
        row=gate.request(action=action,payload=payload or {"workflow":"safe"},project="KRISHNA",source=source,actor=actor)
        gate.decide(row["lease_id"],approved=True,approved_by="Partha")
        return row["lease_id"]

    def test_default_runtime_state_is_fail_closed(self):
        gate=self.make_gate(locked=True)
        self.assertTrue(gate.status()["kill_switch_engaged"])
        lease=self.approved_lease(gate)
        with self.assertRaises(PermissionError):
            gate.consume(lease,action="desktop.rpa.run",payload={"workflow":"safe"},project="KRISHNA",source="pc",actor="owner")

    def test_exact_scope_is_one_time_and_replay_resistant(self):
        gate=self.make_gate(locked=False)
        payload={"workflow":"safe","variables":{"x":1}}
        lease=self.approved_lease(gate,payload=payload)
        first=gate.consume(lease,action="desktop.rpa.run",payload=payload,project="KRISHNA",source="pc",actor="owner")
        self.assertTrue(first["allowed"])
        with self.assertRaises(PermissionError):
            gate.consume(lease,action="desktop.rpa.run",payload=payload,project="KRISHNA",source="pc",actor="owner")

    def test_payload_change_is_rejected_without_consuming_grant(self):
        gate=self.make_gate(locked=False)
        original={"amount":100,"target":"A"}
        lease=self.approved_lease(gate,payload=original,action="transfer")
        with self.assertRaises(PermissionError):
            gate.consume(lease,action="transfer",payload={"amount":101,"target":"A"},project="KRISHNA",source="pc",actor="owner")
        self.assertEqual(gate.get(lease)["status"],"APPROVED")
        good=gate.consume(lease,action="transfer",payload=original,project="KRISHNA",source="pc",actor="owner")
        self.assertTrue(good["allowed"])

    def test_action_project_source_and_actor_are_bound(self):
        gate=self.make_gate(locked=False)
        payload={"id":"x"}
        for key, override in (
            ("action", {"action":"publish"}),
            ("project", {"project":"OTHER"}),
            ("source", {"source":"agent"}),
            ("actor", {"actor":"forged-ui"}),
        ):
            lease=self.approved_lease(gate,payload=payload,action="delete",source="pc",actor="owner")
            args={"action":"delete","payload":payload,"project":"KRISHNA","source":"pc","actor":"owner"}
            args.update(override)
            with self.assertRaises(PermissionError,msg=key):
                gate.consume(lease,**args)
            self.assertEqual(gate.get(lease)["status"],"APPROVED")

    def test_expired_lease_is_rejected(self):
        clock=_Clock()
        gate=self.make_gate(locked=False,ttl=5,clock=clock)
        lease=self.approved_lease(gate,payload={"x":1},action="publish")
        clock.advance(6)
        with self.assertRaises(PermissionError):
            gate.consume(lease,action="publish",payload={"x":1},project="KRISHNA",source="pc",actor="owner")
        self.assertEqual(gate.get(lease)["status"],"EXPIRED")

    def test_denied_lease_never_executes(self):
        gate=self.make_gate(locked=False)
        row=gate.request(action="delete",payload={"id":1},project="KRISHNA",source="pc",actor="owner")
        gate.decide(row["lease_id"],approved=False,approved_by="Partha")
        with self.assertRaises(PermissionError):
            gate.consume(row["lease_id"],action="delete",payload={"id":1},project="KRISHNA",source="pc",actor="owner")

    def test_kill_switch_revokes_live_leases_and_survives_restart(self):
        root=Path(tempfile.mkdtemp(prefix="krishna-authority-restart-"))
        gate=self.make_gate(locked=False,root=root)
        lease=self.approved_lease(gate,payload={"x":1},action="publish")
        gate.engage_kill_switch("operator emergency stop")
        self.assertEqual(gate.get(lease)["status"],"REVOKED")
        restarted=AuthorityLeaseGate(root, initially_locked=False)
        self.assertTrue(restarted.status()["kill_switch_engaged"])
        with self.assertRaises(PermissionError):
            restarted.consume(lease,action="publish",payload={"x":1},project="KRISHNA",source="pc",actor="owner")

    def test_corrupt_state_fails_closed(self):
        root=Path(tempfile.mkdtemp(prefix="krishna-authority-corrupt-"))
        gate=self.make_gate(locked=False,root=root)
        gate.path.write_text("{broken",encoding="utf-8")
        with self.assertRaises(RuntimeError):
            gate.status()


if __name__ == "__main__":
    unittest.main()
