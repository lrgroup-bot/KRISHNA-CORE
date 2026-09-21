from __future__ import annotations


class JobRuntime:
    """Durable job receipts over TaskLedger; execution still goes through the Action Bus."""

    def __init__(self,task_ledger,action_bus):
        self.task_ledger=task_ledger
        self.action_bus=action_bus

    def submit(self,action,payload=None,*,project="KRISHNA",actor="job-runtime",
               permissions=(),approved=False,idempotency_key=None):
        task=self.task_ledger.create(project,f"action:{action}")
        job_id=task["task_id"]
        self.task_ledger.update(job_id,"running","dispatch",{
            "action":action,"actor":actor,"source":"job","mutation_performed":False,
        })
        try:
            receipt=self.action_bus.dispatch(
                action,payload,project=project,source="job",actor=actor,
                approved=approved,permissions=permissions,
                idempotency_key=idempotency_key or ("job:"+job_id),
            )
            self.task_ledger.update(job_id,"completed","complete",{
                "action":action,"action_id":receipt["action_id"],
                "action_status":receipt["status"],
                "mutation_performed":bool((receipt.get("spec") or {}).get("mutating")),
            })
            return {"job_id":job_id,"status":"completed","action":receipt}
        except Exception as exc:
            self.task_ledger.update(job_id,"failed","dispatch",{
                "action":action,"error":f"{type(exc).__name__}: {exc}",
                "mutation_performed":False,
            })
            raise

    def get(self,job_id):
        return self.task_ledger.get(job_id)

    def list(self,project=None,limit=100):
        return self.task_ledger.list_tasks(project,limit)

    def status(self):
        return {
            "owner":"KRISHNA Job Runtime",
            "mode":"durable-inline",
            "active":self.task_ledger.active(),
            "authority":"Shared Action Bus",
        }
