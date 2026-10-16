"""BRAHMAGYAN-owned external engineering intake and lab research planning.

This adapter does not browse, execute experiments, promote claims, or create
independent learning authority. All execution remains SUDARSHAN-gated.
"""
from __future__ import annotations

from .external_learning_ledger import ExternalLearningLedger


class BrahmagyanLearningBridge:
    def __init__(self, brahmagyan, ledger: ExternalLearningLedger):
        self.brahmagyan = brahmagyan
        self.ledger = ledger

    def capture_source(self, *, source_url, source_revision, license_id,
                       summary, evidence):
        return self.ledger.capture(
            source_url=source_url, source_revision=source_revision,
            license_id=license_id, summary=summary, evidence=evidence)

    def propose_research(self, lesson_id, *, project="KRISHNA",
                         question=None, shishya_count=4):
        """Create an L0 BRAHMAGYAN mission and bounded research plan.

        Approved ledger entries only; ledger approval is *not* GYAN approval.
        No claims are advanced or promoted here.
        """
        lesson = self.ledger.get(lesson_id)
        if lesson["status"] != "approved":
            raise PermissionError("external source is not approved for BRAHMAGYAN intake")
        if isinstance(shishya_count, bool) or not isinstance(shishya_count, int):
            raise ValueError("invalid shishya count")
        shishya_count = max(1, min(shishya_count, 8))
        topic = lesson["summary"][:240]
        mission = self.brahmagyan.create_mission(
            project=project, topic=topic,
            question=question or f"Reproduce and challenge: {topic}",
            knowledge_track="engineering", target_level="L6")
        mission_id = mission["mission_id"]
        perspectives = self.brahmagyan.perspective_plan(mission_id, limit=5)
        shishyas = self.brahmagyan.shishya_plan(
            mission_id, count=shishya_count,
            specialties=[
                "Primary-source and license verification",
                "Independent contradiction and failure analysis",
                "Reproducible software experiment design",
                "Cross-project applicability and regression planning",
            ])
        self.brahmagyan.add_questions(mission_id, [
            f"Confirm provenance and license for {lesson['source_url']} at {lesson['source_revision']}.",
            "Design a reproducible sandbox experiment and define a negative control.",
            "Identify failure modes, conflicting evidence, and performance costs.",
            "Do not promote to trusted GYAN without Gautama/Vyasa and owner approval.",
        ])
        return {
            "mission_id": mission_id,
            "lesson_id": lesson_id,
            "authority": "BRAHMAGYAN",
            "maturity": "L0",
            "source_url": lesson["source_url"],
            "source_revision": lesson["source_revision"],
            "perspectives": perspectives,
            "shishya_plan": shishyas,
            "execution_authority": "SUDARSHAN",
            "experiment_execution": "not_started",
            "gyan_promotion": "not_requested",
        }
