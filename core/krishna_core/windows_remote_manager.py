"""Authorized Windows remote-management policy facade.

This intentionally does not embed pentesting shells. A transport adapter may
perform inventory/service operations only after scope and approval checks.
"""
from __future__ import annotations

class WindowsRemoteManager:
    READ_ONLY=frozenset({"inventory","health","service_status"})
    MUTATING=frozenset({"restart_service","start_service","stop_service"})
    def authorize(self,operation,*,owned_or_authorized=False,approved=False):
        op=str(operation or "").strip().lower()
        if op not in self.READ_ONLY|self.MUTATING:
            return {"allowed":False,"reason":"operation_not_supported"}
        if not owned_or_authorized:
            return {"allowed":False,"reason":"target_not_explicitly_authorized"}
        if op in self.MUTATING and not approved:
            return {"allowed":False,"reason":"owner_approval_required"}
        return {"allowed":True,"reason":"authorized","operation":op}
    def plan(self,host,operation,**policy):
        verdict=self.authorize(operation,**policy)
        return {"host":str(host),"operation":str(operation),"executed":False,
                "transport":"winrm_adapter_required","policy":verdict}
