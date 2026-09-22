from __future__ import annotations

POLICY_DECISIONS=("ALLOW","DENY","ASK_OWNER","ALLOW_READ_ONLY","ALLOW_SANDBOXED")

class PermissionRuntime:
    """Central capability and contextual policy engine for KRISHNA actions."""

    MOBILE_BASE=frozenset({
        "chat.read","chat.write","project.message","project.create","status.read",
    })

    @staticmethod
    def _risk(value):
        value=str(value or "low").strip().lower()
        return value if value in {"low","medium","high","critical"} else "medium"

    def decide(self,*,agent="owner",project="KRISHNA",tool="",path="",operation="read",
               risk="low",mission=None,execution_profile="FAST",source="pc",approved=False,sandboxed=False):
        source=str(source or "pc").lower();operation=str(operation or "read").lower()
        risk=self._risk(risk);profile=str(execution_profile or "FAST").upper()
        mutating=operation not in {"read","inspect","list","status","verify","search"}
        if source not in {"pc","system","mobile","agent","job","mcp","a2a"}:
            return {"decision":"DENY","reason":"unknown source","risk":risk}
        if source=="mobile" and risk in {"high","critical"} and mutating:
            return {"decision":"ASK_OWNER","reason":"consequential mobile mutation requires owner approval","risk":risk}
        if risk=="critical" and mutating and not approved:
            return {"decision":"ASK_OWNER","reason":"critical mutation requires explicit owner approval","risk":risk}
        if profile=="PRO" and mutating and sandboxed:
            return {"decision":"ALLOW_SANDBOXED","reason":"PRO mutation constrained to sandbox/worktree","risk":risk}
        if profile=="FAST" and risk=="high" and mutating:
            return {"decision":"ASK_OWNER","reason":"high-risk mutation cannot use FAST path","risk":risk}
        if operation in {"read","inspect","list","status","verify","search"}:
            return {"decision":"ALLOW_READ_ONLY","reason":"read-only operation","risk":risk}
        return {"decision":"ALLOW","reason":"capability/policy checks permit operation","risk":risk}

    def authorize(self,spec,context):
        source=str(context.get("source") or "pc").lower()
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
            "decisions":list(POLICY_DECISIONS),
            "local_owner_sources":["pc","system"],
            "mobile_capabilities":sorted(self.MOBILE_BASE),
            "delegated_sources":["agent","job","mcp","a2a"],
            "policy_inputs":["agent","project","tool","path","operation","risk","mission","execution_profile"],
            "policy":"delegated callers receive only explicitly presented capabilities; consequential actions can require owner approval or sandboxing",
        }
