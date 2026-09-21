from __future__ import annotations


class SudarshanControlPlane:
    """Permissioned execution/verification gate for every delegated KRISHNA capability.

    Sudarshan is not a second orchestrator. It wraps the canonical Shared Action Bus
    and JobRuntime, then forces every delegated result through the independent critic.
    """

    def __init__(self,action_bus,jobs,critic,audit=None):
        self.action_bus=action_bus
        self.jobs=jobs
        self.critic=critic
        self.audit=audit

    @staticmethod
    def _receipt_checks(receipt):
        status=str(receipt.get("status") or "").lower()
        checks=[{
            "name":"action_receipt",
            "status":"PASS" if status=="completed" else "FAIL",
            "passed":status=="completed",
            "detail":f"action={receipt.get('action')} status={receipt.get('status')}",
        }]
        result=receipt.get("result")
        if isinstance(result,dict):
            extra=result.get("_verification") or result.get("verification_checks") or []
            if isinstance(extra,list):
                for row in extra:
                    if isinstance(row,dict):
                        checks.append(dict(row))
        return checks

    def verify_receipt(self,receipt,evidence=None,checks=None):
        rows=list(checks or self._receipt_checks(receipt))
        verdict=self.critic.judge(rows,evidence or [])
        if self.audit:
            try:
                self.audit(
                    receipt.get("action_id") or "sudarshan-verification",
                    "verified" if verdict.get("passed") else "rejected",
                    f"{receipt.get('action')}:{verdict.get('status')}:{verdict.get('reason')}",
                )
            except Exception:
                pass
        return verdict

    def action(self,action,payload=None,*,project="KRISHNA",source="pc",actor="sudarshan",
               approved=False,permissions=(),idempotency_key=None,evidence=None,checks=None):
        receipt=self.action_bus.dispatch(
            action,payload,project=project,source=source,actor=actor,
            approved=approved,permissions=permissions,idempotency_key=idempotency_key,
        )
        verdict=self.verify_receipt(receipt,evidence=evidence,checks=checks)
        receipt["verification"]=verdict
        receipt["verified"]=bool(verdict.get("passed"))
        if not receipt["verified"]:
            raise RuntimeError("independent verifier rejected action result: "+str(verdict.get("reason")))
        return receipt

    def job(self,action,payload=None,*,project="KRISHNA",actor="sudarshan-job",
            permissions=(),approved=False,idempotency_key=None,evidence=None,checks=None):
        row=self.jobs.submit(
            action,payload,project=project,actor=actor,permissions=permissions,
            approved=approved,idempotency_key=idempotency_key,
        )
        receipt=row["action"]
        verdict=self.verify_receipt(receipt,evidence=evidence,checks=checks)
        receipt["verification"]=verdict
        receipt["verified"]=bool(verdict.get("passed"))
        row["verification"]=verdict
        row["verified"]=bool(verdict.get("passed"))
        if not row["verified"]:
            raise RuntimeError("independent verifier rejected job result: "+str(verdict.get("reason")))
        return row

    def verify_workflow(self,node_runs,evidence=None):
        checks=[]
        for row in node_runs or []:
            verdict=row.get("verification") or {}
            passed=bool(verdict.get("passed"))
            checks.append({
                "name":"node:"+str(row.get("node_id") or "unknown"),
                "status":"PASS" if passed else "FAIL",
                "passed":passed,
                "detail":str(verdict.get("reason") or row.get("status") or ""),
            })
        return self.critic.judge(checks,evidence or [])

    def status(self):
        return {
            "owner":"Sudarshan Control Plane",
            "entry":"Shared Action Bus / JobRuntime",
            "exit":"IndependentCriticVerifier",
            "policy":"delegated capabilities enter through permissioned actions/jobs and leave through independent verification",
        }
