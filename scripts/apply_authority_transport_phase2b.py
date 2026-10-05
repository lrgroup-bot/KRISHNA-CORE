from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def patch(path, replacements):
    p=ROOT/path
    text=p.read_text(encoding="utf-8")
    original=text
    for old,new in replacements:
        if old in text:
            text=text.replace(old,new)
        elif new not in text:
            raise RuntimeError(f"patch anchor missing in {path}: {old[:140]!r}")
    if text != original:
        p.write_text(text,encoding="utf-8")
        print(f"patched {path}")
    else:
        print(f"already patched {path}")


patch(Path("core/krishna_core/agent_runtime.py"),[
("""    def dispatch(self,agent_id,action,payload=None,*,project=\"KRISHNA\",approved=False,idempotency_key=None):\n""",
 """    def dispatch(self,agent_id,action,payload=None,*,project=\"KRISHNA\",approved=False,idempotency_key=None,authority_lease=None):\n"""),
("""                approved=approved,permissions=item.permissions,idempotency_key=idempotency_key,\n""",
 """                approved=approved,permissions=item.permissions,idempotency_key=idempotency_key,authority_lease=authority_lease,\n"""),
("""            approved=approved,permissions=item.permissions,idempotency_key=idempotency_key,\n""",
 """            approved=approved,permissions=item.permissions,idempotency_key=idempotency_key,authority_lease=authority_lease,\n"""),
])

patch(Path("core/krishna_core/dispatch_runtime.py"),[
("""    def dispatch(self,target,action,payload=None,*,project=\"KRISHNA\",actor=\"owner\",\n                 agent_id=None,permissions=(),approved=False,idempotency_key=None):\n""",
 """    def dispatch(self,target,action,payload=None,*,project=\"KRISHNA\",actor=\"owner\",\n                 agent_id=None,permissions=(),approved=False,idempotency_key=None,authority_lease=None):\n"""),
("""                    permissions=permissions,approved=approved,idempotency_key=idempotency_key,\n""",
 """                    permissions=permissions,approved=approved,idempotency_key=idempotency_key,authority_lease=authority_lease,\n"""),
("""                permissions=permissions,approved=approved,idempotency_key=idempotency_key,\n""",
 """                permissions=permissions,approved=approved,idempotency_key=idempotency_key,authority_lease=authority_lease,\n"""),
("""                agent_id,action,payload,project=project,approved=approved,\n                idempotency_key=idempotency_key,\n""",
 """                agent_id,action,payload,project=project,approved=approved,\n                idempotency_key=idempotency_key,authority_lease=authority_lease,\n"""),
("""                approved=approved,idempotency_key=idempotency_key,\n""",
 """                approved=approved,idempotency_key=idempotency_key,authority_lease=authority_lease,\n"""),
])

patch(Path("core/krishna_core/protocol_gateway.py"),[
("""    def mcp_call(self,tool_name,args=None,*,principal=\"mcp-client\",project=\"KRISHNA\",\n                 permissions=(),approved=False,request_id=None):\n""",
 """    def mcp_call(self,tool_name,args=None,*,principal=\"mcp-client\",project=\"KRISHNA\",\n                 permissions=(),approved=False,request_id=None,authority_lease=None):\n"""),
("""                permissions=permissions,approved=approved,idempotency_key=request_id,\n""",
 """                permissions=permissions,approved=approved,idempotency_key=request_id,authority_lease=authority_lease,\n"""),
("""            permissions=permissions,approved=approved,idempotency_key=request_id,\n""",
 """            permissions=permissions,approved=approved,idempotency_key=request_id,authority_lease=authority_lease,\n"""),
("""                approved=bool(msg.get(\"approved\",False)),\n                idempotency_key=str(msg.get(\"request_id\") or \"\").strip() or None,\n""",
 """                approved=bool(msg.get(\"approved\",False)),\n                idempotency_key=str(msg.get(\"request_id\") or \"\").strip() or None,\n                authority_lease=msg.get(\"authority_lease\"),\n"""),
("""                permissions=msg.get(\"permissions\") or [],approved=bool(msg.get(\"approved\",False)),\n                idempotency_key=str(msg.get(\"request_id\") or \"\").strip() or None,\n""",
 """                permissions=msg.get(\"permissions\") or [],approved=bool(msg.get(\"approved\",False)),\n                idempotency_key=str(msg.get(\"request_id\") or \"\").strip() or None,\n                authority_lease=msg.get(\"authority_lease\"),\n"""),
])

patch(Path("core/krishna_core/orchestrator.py"),[
("""    def rollback_dispatched_action(self,action_id,source=\"pc\",actor=\"owner\",approved=False):\n        return self.action_bus.rollback(action_id,source=source,actor=actor,approved=approved)\n""",
 """    def rollback_dispatched_action(self,action_id,source=\"pc\",actor=\"owner\",approved=False,authority_lease=None):\n        return self.action_bus.rollback(action_id,source=source,actor=actor,approved=approved,authority_lease=authority_lease)\n"""),
("""    def run_managed_goal(self, project, goal, action_name=None, components=None, approved=False, amcc_signals=None):\n""",
 """    def run_managed_goal(self, project, goal, action_name=None, components=None, approved=False, amcc_signals=None, authority_lease=None):\n"""),
("""            project=project, source=\"pc\", actor=\"work-console\", approved=approved,\n""",
 """            project=project, source=\"pc\", actor=\"work-console\", approved=approved, authority_lease=authority_lease,\n"""),
("""    def promote_candidate(self, token, approved=False):\n""",
 """    def promote_candidate(self, token, approved=False, authority_lease=None):\n"""),
("""            project=project,source=\"pc\",actor=\"promotion-manager\",approved=approved,\n""",
 """            project=project,source=\"pc\",actor=\"promotion-manager\",approved=approved,authority_lease=authority_lease,\n"""),
("""                \"auto_apply\":True,\n                \"max_rounds\":2,\n""",
 """                \"auto_apply\":False,\n                \"max_rounds\":2,\n"""),
("""            actor=\"mrityunjay\",\n            approved=True,\n""",
 """            actor=\"mrityunjay\",\n            approved=False,\n"""),
("""                \"auto_apply\":bool(payload.get(\"auto_apply\",True)),\n""",
 """                \"auto_apply\":bool(payload.get(\"auto_apply\",False)),\n"""),
("""            if not token or not bool(payload.get(\"auto_apply\",True)):\n                wrapped[\"status\"]=result.get(\"status\") or \"incomplete\"\n                return wrapped\n\n            apply_payload={\n""",
 """            if not token or not bool(payload.get(\"auto_apply\",False)):\n                wrapped[\"status\"]=result.get(\"status\") or \"incomplete\"\n                return wrapped\n            if not bool(context.get(\"approved\",False)):\n                raise PermissionError(\"MRITYUNJAY live auto-apply requires a scoped owner authority lease\")\n\n            apply_payload={\n"""),
])

patch(Path("core/krishna_core/server.py"),[
("""            try:return self._json(200,orch.authority.decide(lease_id,approved=bool(data.get(\"approved\",False)),approved_by=\"Partha\"))\n""",
 """            if bool(data.get(\"approved\",False)) and str(data.get(\"confirm\") or \"\") != \"PARTHA_APPROVE_LEASE\":\n                return self._json(403,{\"error\":\"explicit Partha lease approval confirmation required\"})\n            try:return self._json(200,orch.authority.decide(lease_id,approved=bool(data.get(\"approved\",False)),approved_by=\"Partha\"))\n"""),
("""                    approved=bool(data.get(\"approved\",False)),permissions=(\"mobile.test\",\"device.control\"),\n""",
 """                    approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\"),permissions=(\"mobile.test\",\"device.control\"),\n"""),
("""                    approved=bool(data.get(\"approved\",False)),permissions=(\"desktop.control\",),\n""",
 """                    approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\"),permissions=(\"desktop.control\",),\n"""),
("""receipt=orch.dispatch_action(\"garudanetra.start\",payload,project=project,source=\"pc\",actor=\"legacy-http\",approved=bool(data.get(\"persistent_approved\",False)))""",
 """receipt=orch.dispatch_action(\"garudanetra.start\",payload,project=project,source=\"pc\",actor=\"legacy-http\",approved=bool(data.get(\"persistent_approved\",False)),authority_lease=data.get(\"authority_lease\"))"""),
("""receipt=orch.dispatch_action(\"garudanetra.replay\",{\"session_id\":sid,\"steps\":steps},project=\"KRISHNA\",source=\"pc\",actor=\"legacy-http\",approved=bool(data.get(\"approved\",False)))""",
 """receipt=orch.dispatch_action(\"garudanetra.replay\",{\"session_id\":sid,\"steps\":steps},project=\"KRISHNA\",source=\"pc\",actor=\"legacy-http\",approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\"))"""),
("""receipt=orch.dispatch_action(\"narad.dead_letter.retry\",{\"letter_id\":letter_id},source=\"pc\",actor=\"legacy-http\",approved=bool(data.get(\"approved\",False)))""",
 """receipt=orch.dispatch_action(\"narad.dead_letter.retry\",{\"letter_id\":letter_id},source=\"pc\",actor=\"legacy-http\",approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\"))"""),
("""receipt=orch.dispatch_action(\"narad.checkpoint.resume\",{\"run_id\":run_id},source=\"pc\",actor=\"legacy-http\",approved=bool(data.get(\"approved\",False)))""",
 """receipt=orch.dispatch_action(\"narad.checkpoint.resume\",{\"run_id\":run_id},source=\"pc\",actor=\"legacy-http\",approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\"))"""),
("""receipt=orch.dispatch_action(\"narad.workflow.promote\",{\"workflow_id\":wid,\"state\":state,\"verified\":bool(data.get(\"verified\",False))},source=\"pc\",actor=\"legacy-http\",approved=bool(data.get(\"approved\",False)))""",
 """receipt=orch.dispatch_action(\"narad.workflow.promote\",{\"workflow_id\":wid,\"state\":state,\"verified\":bool(data.get(\"verified\",False))},source=\"pc\",actor=\"legacy-http\",approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\"))"""),
("""receipt=orch.dispatch_action(\"narad.workflow.execute\",{\"workflow_id\":wid,\"context\":data.get(\"context\") or {}},source=\"pc\",actor=\"legacy-http\",approved=bool(data.get(\"approved\",False)))""",
 """receipt=orch.dispatch_action(\"narad.workflow.execute\",{\"workflow_id\":wid,\"context\":data.get(\"context\") or {}},source=\"pc\",actor=\"legacy-http\",approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\"))"""),
("""                    approved=bool(data.get(\"approved\",False)),permissions=(\"plugin.write\",),\n""",
 """                    approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\"),permissions=(\"plugin.write\",),\n"""),
("""            try:return self._json(200,orch.rollback_dispatched_action(action_id,source=\"pc\",actor=\"ui\",approved=bool(data.get(\"approved\",False))))\n""",
 """            try:return self._json(200,orch.rollback_dispatched_action(action_id,source=\"pc\",actor=\"ui\",approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\")))\n"""),
("""                permissions=data.get(\"permissions\") or [],approved=bool(data.get(\"approved\",False)),\n                request_id=str(data.get(\"request_id\") or \"\").strip() or None,\n""",
 """                permissions=data.get(\"permissions\") or [],approved=bool(data.get(\"approved\",False)),\n                request_id=str(data.get(\"request_id\") or \"\").strip() or None,authority_lease=data.get(\"authority_lease\"),\n"""),
("""                    approved=bool(data.get(\"approved\",False)),permissions=(\"plugin.execute\",\"network.external\"),\n""",
 """                    approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\"),permissions=(\"plugin.execute\",\"network.external\"),\n"""),
("""                    approved=bool(data.get(\"approved\",False)),permissions=(\"memory.admin\",),\n""",
 """                    approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\"),permissions=(\"memory.admin\",),\n"""),
("""                    approved=bool(data.get(\"approved\",False)),permissions=(\"memory.admin\",\"filesystem.write\"),\n""",
 """                    approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\"),permissions=(\"memory.admin\",\"filesystem.write\"),\n"""),
("""                    approved=bool(data.get(\"approved\",False)),permissions=(\"memory.admin\",\"memory.write\"),\n""",
 """                    approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\"),permissions=(\"memory.admin\",\"memory.write\"),\n"""),
("""                    approved=bool(data.get(\"approved\", False)),\n                    amcc_signals=data.get(\"amcc\") or {},\n""",
 """                    approved=bool(data.get(\"approved\", False)),\n                    amcc_signals=data.get(\"amcc\") or {},authority_lease=data.get(\"authority_lease\"),\n"""),
("""live=orch.promote_candidate(token,approved=True)""",
 """live=orch.promote_candidate(token,approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\"))"""),
("""try: return self._json(200,orch.promote_candidate(token,approved=bool(data.get(\"approved\",False))))""",
 """try: return self._json(200,orch.promote_candidate(token,approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\")))"""),
])

print("Authority transport Phase 2B patch complete")
