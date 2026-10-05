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
            raise RuntimeError(f"patch anchor missing in {path}: {old[:120]!r}")
    if text!=original:
        p.write_text(text,encoding="utf-8")
        print(f"patched {path}")
    else:
        print(f"already patched {path}")


patch(Path("core/krishna_core/shared_action_bus.py"),[
("""    def __init__(self,event_bus,policy,audit:Callable|None=None,permission_resolver:Callable|None=None,\n                 history_limit=500,idempotency_db_path=None):\n        self.event_bus=event_bus\n        self.policy=policy\n        self.audit=audit\n        self.permission_resolver=permission_resolver\n""",
"""    def __init__(self,event_bus,policy,audit:Callable|None=None,permission_resolver:Callable|None=None,\n                 history_limit=500,idempotency_db_path=None,authority_gate=None):\n        self.event_bus=event_bus\n        self.policy=policy\n        self.audit=audit\n        self.permission_resolver=permission_resolver\n        self.authority_gate=authority_gate\n"""),
("""    def dispatch(self,action,payload=None,*,project=\"KRISHNA\",source=\"pc\",actor=\"owner\",\n                 approved=False,permissions=(),idempotency_key=None)->dict:\n""",
"""    def dispatch(self,action,payload=None,*,project=\"KRISHNA\",source=\"pc\",actor=\"owner\",\n                 approved=False,permissions=(),idempotency_key=None,authority_lease=None)->dict:\n"""),
("""            \"action_id\":action_id,\"action\":name,\"project\":project,\"source\":source,\"actor\":actor,\n            \"approved\":bool(approved),\"permissions\":list(permissions or []),\n            \"payload\":self._safe_payload(payload),\"created_at\":self._now(),\n""",
"""            \"action_id\":action_id,\"action\":name,\"project\":project,\"source\":source,\"actor\":actor,\n            \"approved\":False,\"permissions\":list(permissions or []),\n            \"payload\":self._safe_payload(payload),\"created_at\":self._now(),\n"""),
("""        # Low-risk state mutations can be marked mutating for audit without forcing\n        # an approval dialog. PolicyKernel approval is invoked when this action's\n        # contract explicitly requires approval.\n        decision=self.policy.action(name,mutating=bool(spec.requires_approval),approved=bool(approved))\n""",
"""        # A caller-supplied boolean is intent, never executable authority.  When\n        # KRISHNA is configured with the persistent authority gate, any action whose\n        # contract requires approval (or any caller attempting to assert approval)\n        # must present a one-time lease bound to this exact action envelope.\n        effective_approved=bool(approved) if self.authority_gate is None else False\n        authority_receipt=None\n        if self.authority_gate is not None and (spec.requires_approval or bool(approved) or authority_lease):\n            try:\n                authority_receipt=self.authority_gate.consume(\n                    authority_lease,action=name,payload=payload,project=project,source=source,actor=actor,\n                )\n                effective_approved=True\n            except PermissionError as exc:\n                row={**envelope,\"status\":\"blocked\",\"reason\":str(exc),\"spec\":spec.as_dict()}\n                self._record(row);self._publish(\"action.blocked\",row)\n                raise\n        envelope[\"approved\"]=effective_approved\n        if authority_receipt:\n            envelope[\"authority\"]={\n                \"lease_id\":authority_receipt.get(\"lease_id\"),\n                \"scope_fingerprint\":authority_receipt.get(\"scope_fingerprint\"),\n                \"approved_by\":authority_receipt.get(\"approved_by\"),\n            }\n        context={**envelope,\"spec\":spec.as_dict()}\n        # Low-risk state mutations can be marked mutating for audit without forcing\n        # an approval dialog. PolicyKernel approval is invoked when this action's\n        # contract explicitly requires approval.\n        decision=self.policy.action(name,mutating=bool(spec.requires_approval),approved=effective_approved)\n"""),
("""    def rollback(self,action_id,*,source=\"pc\",actor=\"owner\",approved=False)->dict:\n""",
"""    def rollback(self,action_id,*,source=\"pc\",actor=\"owner\",approved=False,authority_lease=None)->dict:\n"""),
("""        if not approved:\n            raise PermissionError(\"rollback requires explicit approval\")\n        return self.dispatch(\n            spec_name,{\"original_action\":original},project=original.get(\"project\") or \"KRISHNA\",\n            source=source,actor=actor,approved=True,\n            idempotency_key=f\"rollback:{action_id}\",\n        )\n""",
"""        if self.authority_gate is None and not approved:\n            raise PermissionError(\"rollback requires explicit approval\")\n        return self.dispatch(\n            spec_name,{\"original_action\":original},project=original.get(\"project\") or \"KRISHNA\",\n            source=source,actor=actor,approved=approved,authority_lease=authority_lease,\n            idempotency_key=f\"rollback:{action_id}\",\n        )\n"""),
("""            \"durable_idempotency\":self._idempotency_store is not None,\n            \"actions\":self.list(),\n""",
"""            \"durable_idempotency\":self._idempotency_store is not None,\n            \"authority_lease\":self.authority_gate.status() if self.authority_gate is not None else {\"configured\":False},\n            \"actions\":self.list(),\n"""),
])

patch(Path("core/krishna_core/sudarshan_control.py"),[
("""    def action(self,action,payload=None,*,project=\"KRISHNA\",source=\"pc\",actor=\"sudarshan\",\n               approved=False,permissions=(),idempotency_key=None,evidence=None,checks=None):\n        receipt=self.action_bus.dispatch(\n            action,payload,project=project,source=source,actor=actor,\n            approved=approved,permissions=permissions,idempotency_key=idempotency_key,\n        )\n""",
"""    def action(self,action,payload=None,*,project=\"KRISHNA\",source=\"pc\",actor=\"sudarshan\",\n               approved=False,permissions=(),idempotency_key=None,authority_lease=None,evidence=None,checks=None):\n        receipt=self.action_bus.dispatch(\n            action,payload,project=project,source=source,actor=actor,\n            approved=approved,permissions=permissions,idempotency_key=idempotency_key,\n            authority_lease=authority_lease,\n        )\n"""),
("""    def job(self,action,payload=None,*,project=\"KRISHNA\",actor=\"sudarshan-job\",\n            permissions=(),approved=False,idempotency_key=None,evidence=None,checks=None):\n        row=self.jobs.submit(\n            action,payload,project=project,actor=actor,permissions=permissions,\n            approved=approved,idempotency_key=idempotency_key,\n        )\n""",
"""    def job(self,action,payload=None,*,project=\"KRISHNA\",actor=\"sudarshan-job\",\n            permissions=(),approved=False,idempotency_key=None,authority_lease=None,evidence=None,checks=None):\n        row=self.jobs.submit(\n            action,payload,project=project,actor=actor,permissions=permissions,\n            approved=approved,idempotency_key=idempotency_key,authority_lease=authority_lease,\n        )\n"""),
("""            \"policy\":\"delegated capabilities enter through permissioned actions/jobs and leave through independent verification\",\n""",
"""            \"policy\":\"delegated capabilities enter through permissioned actions/jobs, consequential execution requires scoped authority leases, and results leave through independent verification\",\n"""),
])

patch(Path("core/krishna_core/job_runtime.py"),[
("""    def submit(self,action,payload=None,*,project=\"KRISHNA\",actor=\"job-runtime\",\n               permissions=(),approved=False,idempotency_key=None,mission_id=None,\n               max_retries=2,resource_budget=None):\n""",
"""    def submit(self,action,payload=None,*,project=\"KRISHNA\",actor=\"job-runtime\",\n               permissions=(),approved=False,idempotency_key=None,authority_lease=None,mission_id=None,\n               max_retries=2,resource_budget=None):\n"""),
("""                approved=approved,permissions=permissions,\n                idempotency_key=idempotency_key or (f\"mission:{mission_id}\" if mission_id else \"job:\"+task_id),\n""",
"""                approved=approved,permissions=permissions,authority_lease=authority_lease,\n                idempotency_key=idempotency_key or (f\"mission:{mission_id}\" if mission_id else \"job:\"+task_id),\n"""),
])

patch(Path("core/krishna_core/orchestrator.py"),[
("""from .auth_handoff import AuthenticationHandoffGate\n""",
"""from .auth_handoff import AuthenticationHandoffGate\nfrom .authority_lease import AuthorityLeaseGate\n"""),
("""        runtime_state = Path(self.db_path).resolve().parent / \".krishna_state\"\n        self.project_brain = ProjectBrain(self.memory,runtime_state / \"project-brain\")\n""",
"""        runtime_state = Path(self.db_path).resolve().parent / \".krishna_state\"\n        self.authority = AuthorityLeaseGate(runtime_state / \"authority\", audit=self.memory.audit, initially_locked=True)\n        self.project_brain = ProjectBrain(self.memory,runtime_state / \"project-brain\")\n"""),
("""        self.action_bus = SharedActionBus(\n            self.lifecycle_bus,self.agi.policy,audit=self.memory.audit,\n            permission_resolver=self.permissions.authorize,\n            idempotency_db_path=self.db_path,\n        )\n""",
"""        self.action_bus = SharedActionBus(\n            self.lifecycle_bus,self.agi.policy,audit=self.memory.audit,\n            permission_resolver=self.permissions.authorize,\n            idempotency_db_path=self.db_path,authority_gate=self.authority,\n        )\n"""),
("""    def dispatch_action(self,action,payload=None,project=\"KRISHNA\",source=\"pc\",actor=\"owner\",\n                        approved=False,permissions=(),idempotency_key=None):\n        return self.sudarshan.action(\n            action,payload,project=project,source=source,actor=actor,approved=approved,\n            permissions=permissions,idempotency_key=idempotency_key,\n        )\n""",
"""    def dispatch_action(self,action,payload=None,project=\"KRISHNA\",source=\"pc\",actor=\"owner\",\n                        approved=False,permissions=(),idempotency_key=None,authority_lease=None):\n        return self.sudarshan.action(\n            action,payload,project=project,source=source,actor=actor,approved=approved,\n            permissions=permissions,idempotency_key=idempotency_key,authority_lease=authority_lease,\n        )\n"""),
])

patch(Path("core/krishna_core/server.py"),[
("""        if path == \"/health\":\n""",
"""        if path == \"/api/authority/status\":\n            return self._json(200,orch.authority.status())\n        if path == \"/health\":\n"""),
("""        except Exception as exc:\n            return self._json(400, {\"error\": f\"invalid json: {exc}\"})\n\n        if post_path == \"/api/hawkeye/ruview/wifi/connect\":\n""",
"""        except Exception as exc:\n            return self._json(400, {\"error\": f\"invalid json: {exc}\"})\n\n        if post_path == \"/api/authority/lease/request\":\n            if self.client_address[0] not in (\"127.0.0.1\",\"::1\"):\n                return self._json(403,{\"error\":\"authority leases may be requested only on the KRISHNA PC\"})\n            action=str(data.get(\"action\") or \"\").strip()\n            if not action:return self._json(400,{\"error\":\"action is required\"})\n            if action not in {x.get(\"name\") for x in orch.action_bus.list()}:\n                return self._json(404,{\"error\":\"shared action not registered\"})\n            try:\n                row=orch.authority.request(\n                    action=action,payload=data.get(\"payload\") or {},\n                    project=str(data.get(\"project\") or \"KRISHNA\"),\n                    source=str(data.get(\"source\") or \"pc\"),actor=str(data.get(\"actor\") or \"owner\"),\n                    reason=str(data.get(\"reason\") or \"\"),ttl_seconds=data.get(\"ttl_seconds\"),\n                )\n                return self._json(201,row)\n            except (ValueError,RuntimeError) as exc:return self._json(400,{\"error\":str(exc)})\n\n        if post_path == \"/api/authority/lease/decide\":\n            if self.client_address[0] not in (\"127.0.0.1\",\"::1\"):\n                return self._json(403,{\"error\":\"authority decisions must be made on the KRISHNA PC\"})\n            lease_id=str(data.get(\"lease_id\") or \"\").strip()\n            if not lease_id:return self._json(400,{\"error\":\"lease_id is required\"})\n            try:return self._json(200,orch.authority.decide(lease_id,approved=bool(data.get(\"approved\",False)),approved_by=\"Partha\"))\n            except KeyError:return self._json(404,{\"error\":\"authority lease not found\"})\n            except (ValueError,PermissionError,RuntimeError) as exc:return self._json(409,{\"error\":str(exc)})\n\n        if post_path == \"/api/authority/kill-switch/engage\":\n            if self.client_address[0] not in (\"127.0.0.1\",\"::1\"):\n                return self._json(403,{\"error\":\"kill switch is local-owner only\"})\n            return self._json(200,orch.authority.engage_kill_switch(str(data.get(\"reason\") or \"owner safety lock\")))\n\n        if post_path == \"/api/authority/kill-switch/disarm\":\n            if self.client_address[0] not in (\"127.0.0.1\",\"::1\"):\n                return self._json(403,{\"error\":\"kill switch is local-owner only\"})\n            if str(data.get(\"confirm\") or \"\") != \"PARTHA_DISARM_KRISHNA\":\n                return self._json(403,{\"error\":\"explicit Partha disarm confirmation required\"})\n            return self._json(200,orch.authority.disarm_kill_switch(approved_by=\"Partha\",reason=str(data.get(\"reason\") or \"controlled readiness test\")))\n\n        if post_path == \"/api/hawkeye/ruview/wifi/connect\":\n"""),
("""                    approved=bool(data.get(\"approved\",False)),\n""",
"""                    approved=bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\"),\n"""),
])

print("Authority Lease Phase 2 source patch complete")
