"""Governed project ingress for external project channels.

LR Technology is a customer/product interface. It submits an approved, versioned
project specification to Sudarshan. Sudarshan orchestrates the project, while
KRISHNA remains the authority boundary for permissions, policy, resources and
consequential actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ProjectIngress:
    project_id: str
    spec_version: str
    source: str
    customer_approved: bool
    specification: Mapping[str, Any]


class SudarshanProjectIngress:
    ALLOWED_SOURCES = frozenset({"owner", "krishna", "lr-technology"})

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def accept(self, ingress: ProjectIngress):
        source = str(ingress.source or "").strip().lower()
        if source not in self.ALLOWED_SOURCES:
            return {"state": "BLOCKED_SOURCE", "owner": "Sudarshan", "source": source}
        if source == "lr-technology" and not ingress.customer_approved:
            return {
                "state": "BLOCKED_CUSTOMER_APPROVAL",
                "owner": "Sudarshan",
                "project": ingress.project_id,
            }
        if not str(ingress.spec_version or "").strip():
            return {"state": "BLOCKED_SPEC_VERSION", "owner": "Sudarshan"}
        if not isinstance(ingress.specification, Mapping) or not ingress.specification:
            return {"state": "BLOCKED_SPECIFICATION", "owner": "Sudarshan"}

        context = dict(ingress.specification)
        context["project_spec_version"] = ingress.spec_version
        context["project_ingress_source"] = source
        context["customer_approved"] = bool(ingress.customer_approved)
        result = self.orchestrator.start(ingress.project_id, context)
        result["ingress"] = {
            "source": source,
            "spec_version": ingress.spec_version,
            "customer_approved": bool(ingress.customer_approved),
        }
        result["authority"] = "KRISHNA"
        result["orchestration"] = "Sudarshan"
        return result

    @staticmethod
    def authority_request(project_id, capability, *, reason="", permissions=()):
        """Create a request envelope; this never grants authority itself."""
        return {
            "project": project_id,
            "requested_by": "Sudarshan",
            "authority": "KRISHNA",
            "capability": str(capability),
            "reason": str(reason),
            "permissions": list(permissions),
            "approved": False,
        }
