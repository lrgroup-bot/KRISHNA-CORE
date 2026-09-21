from __future__ import annotations


class PermissionRuntime:
    """Central capability check for Shared Action Bus principals."""

    MOBILE_BASE=frozenset({
        "chat.read","chat.write","project.message","project.create","status.read",
    })

    def authorize(self,spec,context):
        source=str(context.get("source") or "pc").lower()
        actor=str(context.get("actor") or "owner")
        required=set(spec.permissions)
        presented=set(str(x) for x in (context.get("permissions") or []))

        if source in {"pc","system"}:
            return True,"local owner/runtime authority"

        if source=="mobile":
            effective=presented & set(self.MOBILE_BASE)
            if not required.issubset(effective):
                return False,"mobile capability denied: "+",".join(sorted(required-effective))
            return True,"paired mobile capability contract"

        if source in {"agent","job","mcp","a2a"}:
            if not required.issubset(presented):
                return False,f"{source} missing capability: "+",".join(sorted(required-presented))
            return True,f"{source} capability contract"

        return False,f"unknown action source: {source}"

    def status(self):
        return {
            "owner":"KRISHNA Permission Runtime",
            "local_owner_sources":["pc","system"],
            "mobile_capabilities":sorted(self.MOBILE_BASE),
            "delegated_sources":["agent","job","mcp","a2a"],
            "policy":"delegated callers receive only explicitly presented capabilities; action spec remains authoritative",
        }
