from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path


class AvatarAgeProfile:
    """Local-only daily age progression for KRISHNA's private child-likeness avatar.

    The source face remains private owner data. This controller never uploads,
    regenerates, or overwrites the source GLB. It emits deterministic daily age
    targets that a verified local renderer may later apply using age morphs or
    approved age-stage assets while preserving identity.
    """

    VERSION = "avatar-age-profile-v1"

    def __init__(self, state_root: str | Path):
        root = Path(state_root).resolve()
        self.path = root / "avatar" / "age-profile.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({
                "schema": self.VERSION,
                "baseline_date": date.today().isoformat(),
                "growth_rate_days_per_day": 1.0,
                "base_visual_age_years": None,
                "identity_mode": "private_child_likeness",
                "identity_lock": True,
                "cloud_upload_allowed": False,
            })

    def _read(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        baseline = str(data.get("baseline_date") or date.today().isoformat())
        try:
            date.fromisoformat(baseline)
        except ValueError:
            baseline = date.today().isoformat()
        try:
            rate = max(0.0, float(data.get("growth_rate_days_per_day", 1.0)))
        except (TypeError, ValueError):
            rate = 1.0
        base = data.get("base_visual_age_years")
        try:
            base = None if base in (None, "") else max(0.0, float(base))
        except (TypeError, ValueError):
            base = None
        return {
            "schema": self.VERSION,
            "baseline_date": baseline,
            "growth_rate_days_per_day": rate,
            "base_visual_age_years": base,
            "identity_mode": "private_child_likeness",
            "identity_lock": True,
            "cloud_upload_allowed": False,
        }

    def _write(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def configure(self, *, baseline_date: str | None = None,
                  base_visual_age_years: float | None = None,
                  growth_rate_days_per_day: float = 1.0) -> dict:
        current = self._read()
        if baseline_date:
            date.fromisoformat(str(baseline_date))
            current["baseline_date"] = str(baseline_date)
        if base_visual_age_years is not None:
            current["base_visual_age_years"] = max(0.0, float(base_visual_age_years))
        current["growth_rate_days_per_day"] = max(0.0, float(growth_rate_days_per_day))
        self._write(current)
        return self.status()

    def status(self, as_of: str | date | None = None) -> dict:
        data = self._read()
        if as_of is None:
            now = date.today()
        elif isinstance(as_of, date):
            now = as_of
        else:
            now = date.fromisoformat(str(as_of))
        baseline = date.fromisoformat(data["baseline_date"])
        real_days = max(0, (now - baseline).days)
        visual_days = real_days * data["growth_rate_days_per_day"]
        years = visual_days / 365.2425
        base = data["base_visual_age_years"]
        display_age = (base + years) if base is not None else None
        year_fraction = years - int(years)
        return {
            "version": self.VERSION,
            "configured": True,
            "baseline_date": data["baseline_date"],
            "as_of": now.isoformat(),
            "real_days_elapsed": real_days,
            "visual_age_offset_days": round(visual_days, 4),
            "visual_age_offset_years": round(years, 6),
            "base_visual_age_years": base,
            "display_visual_age_years": round(display_age, 6) if display_age is not None else None,
            "year_stage": int(years),
            "blend_to_next_year": round(year_fraction, 6),
            "daily_progression": True,
            "identity_mode": data["identity_mode"],
            "identity_lock": True,
            "source_face_policy": "private owner child avatar remains the identity anchor",
            "cloud_upload_allowed": False,
            "renderer_ready": False,
            "renderer_requirement": (
                "verified local identity-preserving age morphs or approved age-stage assets; "
                "current controller changes age targets only and never fabricates face geometry"
            ),
        }
