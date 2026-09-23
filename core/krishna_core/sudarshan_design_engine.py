from __future__ import annotations

"""Sudarshan design planning, design-genome, drift and acceptance contracts."""

from dataclasses import dataclass
from pathlib import Path
import json
import time


@dataclass(frozen=True)
class DesignJob:
    kind: str
    reference_image: bool = False
    existing_ui: bool = False
    agentic_browser: bool = False


class SkillRouter:
    def select(self, job: DesignJob):
        kind = str(job.kind or "").strip().lower()
        skills = []
        if kind in {"frontend", "ui", "ux", "mobile", "mobile-ui", "dashboard", "web-design", "component"}:
            skills += ["web-design", "taste-skill"]
        if job.existing_ui:
            skills += ["redesign-existing-projects"]
        if job.reference_image:
            skills += ["image-to-code"]
        skills += ["playwright-cli"]
        if job.agentic_browser:
            skills += ["stagehand"]
        return list(dict.fromkeys(skills))


class DesignGenome:
    SCHEMA = "krishna.design-genome.v1"
    SECTIONS = ("identity", "color", "typography", "geometry", "depth", "motion", "components")

    def __init__(self, **values):
        self.data = {"schema": self.SCHEMA}
        for section in self.SECTIONS:
            value = values.get(section) or {}
            if not isinstance(value, dict):
                raise ValueError(f"design genome section {section} must be an object")
            self.data[section] = dict(value)

    def save(self, path):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(target)


class DesignDrift:
    @staticmethod
    def _flatten(value, prefix=""):
        if not isinstance(value, dict):
            return {prefix or "$": value}
        out = {}
        for key, item in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(item, dict):
                out.update(DesignDrift._flatten(item, name))
            else:
                out[name] = item
        return out

    def compare(self, expected: dict, actual: dict):
        left = self._flatten(dict(expected or {}))
        right = self._flatten(dict(actual or {}))
        keys = sorted(set(left) | set(right))
        diff = {
            key: {"expected": left.get(key), "actual": right.get(key)}
            for key in keys if left.get(key) != right.get(key)
        }
        return {"pass": not diff, "differences": diff, "difference_count": len(diff)}


class AcceptanceGovernor:
    REQUIRED = (
        "functional", "visual", "responsive", "accessibility", "keyboard",
        "loading", "error", "empty", "console", "performance", "security",
    )

    def evaluate(self, checks: dict):
        checks = dict(checks or {})
        failed = [name for name in self.REQUIRED if checks.get(name) is not True]
        return {
            "verified": not failed,
            "failed": failed,
            "owner": "Sudarshan",
            "required": list(self.REQUIRED),
        }


class SudarshanDesignEngine:
    VERSION = "sudarshan-design-v2"

    def __init__(self, root):
        self.root = Path(root)
        self.router = SkillRouter()
        self.drift = DesignDrift()
        self.acceptance = AcceptanceGovernor()

    def plan(self, job: DesignJob):
        return {
            "owner": "Sudarshan",
            "version": self.VERSION,
            "skills": self.router.select(job),
            "krishna_context": "summary-only",
            "vishvakarma_required": True,
            "created_at": time.time(),
        }

    def status(self):
        return {
            "component": "Sudarshan Design Engine",
            "version": self.VERSION,
            "skills": ["web-design", "taste-skill", "redesign-existing-projects", "image-to-code", "playwright-cli", "stagehand"],
            "acceptance_gates": list(self.acceptance.REQUIRED),
            "design_genome_schema": DesignGenome.SCHEMA,
            "ready": True,
        }
