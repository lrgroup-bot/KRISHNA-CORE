import json
import tempfile
import unittest
from pathlib import Path

from krishna_core.suryadev import SuryadevAgent
from krishna_core.chandradev import ChandradevQC
from krishna_core.external_observer_bridge import ExternalObserverBridge
from krishna_core.auth_handoff import AuthenticationHandoffGate
from krishna_core.node_registry import NodeRegistry


class BrahmaStub:
    def __init__(self):
        self.calls = []

    def intake(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "decision_id": "brahma-1",
            "lead_rishi": "gautama",
            "team": ["gautama", "bharadvaja"],
            "recorded_finding": {"finding_id": "rishi-1"},
        }


class UIReviewerStub:
    def review(self, screenshots, deterministic_context=None, required=False):
        return {
            "available": True,
            "required": required,
            "passed": False,
            "issues": [{
                "kind": "low_grade_input",
                "detail": "Text box hierarchy is weak and the control looks unfinished.",
                "severity": "warning",
                "confidence": 0.91,
                "image": "screen.png",
            }],
            "material_issues": [],
            "reviews": [],
        }


class MemoryStub:
    def __init__(self):
        self.rows = []

    def audit(self, action, status, details):
        self.rows.append((action, status, details))


class SuryadevChandradevTests(unittest.TestCase):
    def test_suryadev_creates_ui_jobs_and_routes_distilled_findings(self):
        with tempfile.TemporaryDirectory() as td:
            brahma = BrahmaStub()
            agent = SuryadevAgent(
                Path(td) / "surya",
                brahma=brahma,
                ui_reviewer=UIReviewerStub(),
                memory=MemoryStub(),
            )
            jobs = agent.project_ui_audit_jobs([
                {"name": "KRISHNA", "url": "http://127.0.0.1:8766"},
                {"name": "KUBER", "url": "http://127.0.0.1:8080"},
            ])
            self.assertEqual(len(jobs), 2)
            self.assertEqual(jobs[0]["kind"], "project_ui_audit")
            self.assertFalse(jobs[0]["workspace_policy"]["send_raw_media_to_krishna"])

            ui = agent.review_ui([{"path": "not-present.png"}], required=False)
            self.assertEqual(ui["agent"], "SURYDEV")
            self.assertEqual(len(ui["change_requests"]), 1)

            packet = agent.distilled_finding(
                job_id=jobs[0]["job_id"],
                project="KRISHNA",
                topic="Control Room UI",
                finding="Primary input control lacks visual hierarchy and should be retested after refinement.",
                modality="multimodal",
                evidence=[{
                    "source_ref": "external-session:1",
                    "source_type": "screen",
                    "sha256": "a" * 64,
                    "note": "Observed during live UI test.",
                }],
                confidence=0.86,
                timestamps=["00:01:12"],
                source_ref="external-session:1",
            )
            routed = agent.route_finding(packet)
            self.assertTrue(routed["routed"])
            self.assertEqual(routed["lead_rishi"], "gautama")
            self.assertEqual(len(brahma.calls), 1)
            self.assertEqual(brahma.calls[0]["provenance"]["source_agent"], "suryadev")
            self.assertFalse(brahma.calls[0]["provenance"]["raw_media_transferred"])

    def test_suryadev_rejects_raw_media_in_finding_packet(self):
        with tempfile.TemporaryDirectory() as td:
            agent = SuryadevAgent(Path(td))
            with self.assertRaises(ValueError):
                agent.distilled_finding(
                    job_id="SURYA-1",
                    project="KRISHNA",
                    topic="video",
                    finding="candidate",
                    evidence=[{"raw_video": "secret.mp4"}],
                )

    def test_chandradev_forces_debate_when_brahma_and_suryadev_disagree(self):
        with tempfile.TemporaryDirectory() as td:
            qc = ChandradevQC(Path(td), memory=MemoryStub())
            row = qc.review(
                project="KRISHNA",
                deterministic_passed=True,
                suryadev_review={"passed": False, "issues": [{"detail": "poor textbox"}]},
                brahma_review={"candidate_passed": True, "reasons": []},
                camera_observation={"issues": []},
            )
            self.assertEqual(row["state"], "DEBATE_REQUIRED")
            self.assertTrue(row["debate_required"])
            self.assertEqual(row["debate"]["participants"], ["chandradev", "brahma"])

            resolved = qc.resolve_debate(
                row["qc_id"],
                resolution="RETEST_REQUIRED",
                chandradev_position="Visible UI issue still needs correction.",
                brahma_position="Knowledge/evidence checks pass but UI should be retested.",
                notes="Return to tester after textbox refinement.",
            )
            self.assertEqual(resolved["state"], "RETEST_REQUIRED")
            self.assertFalse(resolved["debate_required"])
            self.assertEqual(resolved["debate"]["status"], "CLOSED")

    def test_chandradev_cannot_override_failed_deterministic_test(self):
        with tempfile.TemporaryDirectory() as td:
            qc = ChandradevQC(Path(td))
            row = qc.review(
                deterministic_passed=False,
                suryadev_review={"passed": True},
                brahma_review={"candidate_passed": True},
                camera_observation={"issues": []},
            )
            self.assertEqual(row["state"], "BLOCKED")
            self.assertFalse(row["debate_required"])

    def test_external_bridge_requires_trusted_capability_and_validates_usb(self):
        with tempfile.TemporaryDirectory() as td:
            registry = NodeRegistry(Path(td) / "nodes.json")
            node = registry.enroll(
                "Research Laptop",
                "0123456789abcdef0123456789abcdef",
                role="observer",
                approved=True,
            )
            registry.configure_execution(
                node.id,
                platform="windows",
                capabilities=["suryadev.worker", "suryadev.screen_read"],
                endpoint="https://192.168.1.50:8771",
                workspace_root="E:/Suryadev",
                approved=True,
            )
            bridge = ExternalObserverBridge(Path(td) / "bridge", registry)
            env = bridge.envelope(
                agent="suryadev",
                node_id=node.id,
                payload={"job_id": "SURYA-1", "kind": "video_research"},
                transport="usb",
            )
            out = bridge.export_usb(env, Path(td) / "usb")
            imported = bridge.import_usb(out["packet"], out["manifest"])
            self.assertTrue(imported["validation"]["valid"])
            self.assertEqual(imported["validation"]["agent"], "suryadev")

            target = bridge.lan_target(agent="suryadev", node_id=node.id)
            self.assertTrue(target["ready"])
            self.assertEqual(target["endpoint"], "https://192.168.1.50:8771")

    def test_node_registry_accepts_dedicated_qc_role(self):
        with tempfile.TemporaryDirectory() as td:
            registry = NodeRegistry(Path(td) / "nodes.json")
            node = registry.enroll(
                "QC Laptop",
                "fedcba9876543210fedcba9876543210",
                role="qc",
                approved=True,
            )
            self.assertEqual(node.role, "qc")

    def test_auth_handoff_requires_explicit_owner_permission_and_is_one_time(self):
        with tempfile.TemporaryDirectory() as td:
            gate = AuthenticationHandoffGate(Path(td) / "auth", memory=MemoryStub(), ttl_seconds=600)
            req = gate.request(
                agent="suryadev",
                job_id="SURYA-123",
                origin="https://example.com/login",
                method="mfa",
                reason="Site requires owner authentication",
                checkpoint_ref="login-step-2",
            )
            self.assertEqual(req["status"], "OWNER_APPROVAL_REQUIRED")
            self.assertEqual(gate.status()["pending"], 1)

            with self.assertRaises(PermissionError):
                gate.consume(
                    req["request_id"],
                    agent="suryadev",
                    job_id="SURYA-123",
                    origin="https://example.com/login",
                    method="mfa",
                )

            approved = gate.decide(req["request_id"], approved=True, approved_by="owner")
            self.assertEqual(approved["status"], "APPROVED")

            grant = gate.consume(
                req["request_id"],
                agent="suryadev",
                job_id="SURYA-123",
                origin="https://example.com/login",
                method="mfa",
            )
            self.assertTrue(grant["allowed"])
            self.assertEqual(grant["action"], "HUMAN_HANDOFF_ALLOWED")
            self.assertFalse(grant["credential_capture"])
            self.assertFalse(grant["captcha_solving"])
            self.assertFalse(grant["liveness_spoofing"])

            with self.assertRaises(PermissionError):
                gate.consume(
                    req["request_id"],
                    agent="suryadev",
                    job_id="SURYA-123",
                    origin="https://example.com/login",
                    method="mfa",
                )

    def test_auth_handoff_is_scope_bound_and_can_be_denied(self):
        with tempfile.TemporaryDirectory() as td:
            gate = AuthenticationHandoffGate(Path(td) / "auth")
            req = gate.request(
                agent="chandradev",
                job_id="CHANDRA-1",
                origin="https://example.com",
                method="liveness",
            )
            gate.decide(req["request_id"], approved=True)
            with self.assertRaises(PermissionError):
                gate.consume(
                    req["request_id"],
                    agent="chandradev",
                    job_id="CHANDRA-1",
                    origin="https://other.example.com",
                    method="liveness",
                )

            req2 = gate.request(
                agent="suryadev",
                job_id="SURYA-2",
                origin="https://example.com",
                method="captcha",
            )
            denied = gate.decide(req2["request_id"], approved=False)
            self.assertEqual(denied["status"], "DENIED")
            with self.assertRaises(PermissionError):
                gate.consume(
                    req2["request_id"],
                    agent="suryadev",
                    job_id="SURYA-2",
                    origin="https://example.com",
                    method="captcha",
                )


if __name__ == "__main__":
    unittest.main()
