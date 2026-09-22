from __future__ import annotations


class JobRuntime:
    """Durable queued jobs over KRISHNA Mission Engine + Shared Action Bus.

    The queue is authoritative. submit() preserves the historical synchronous API,
    but execution first passes through durable enqueue -> claim -> ACK/failed state.
    """

    def __init__(self,task_ledger,action_bus,missions=None,queue=None,budgets=None,event_bus=None):
        self.task_ledger=task_ledger
        self.action_bus=action_bus
        self.missions=missions
        self.queue=queue
        self.budgets=budgets
        self.event_bus=event_bus
        self.worker_id="job-runtime:inline"

    def _emit(self,topic,payload):
        if not self.event_bus:return
        try:self.event_bus.publish(topic,payload,source="job-runtime")
        except Exception:pass

    def submit(self,action,payload=None,*,project="KRISHNA",actor="job-runtime",
               permissions=(),approved=False,idempotency_key=None,mission_id=None,
               max_retries=2,resource_budget=None):
        task=self.task_ledger.create(project,f"action:{action}")
        task_id=task["task_id"]
        mission=None
        if self.missions:
            if mission_id:
                mission=self.missions.get(mission_id)
                if not mission:raise KeyError(f"mission not found: {mission_id}")
            else:
                mission=self.missions.create(
                    f"action:{action}",project_id=project,required_tools=[action],
                    permission_profile="job",resource_budget=resource_budget or {},
                    metadata={"compat_task_id":task_id,"actor":actor},
                )
            mission_id=mission["mission_id"]
            if self.budgets:self.budgets.configure(mission_id,resource_budget or mission.get("resource_budget") or {})
            self.missions.transition(mission_id,"RUNNING",current_step="queue_dispatch",progress=.1)
            self.missions.checkpoint(mission_id,"job_enqueued",{"action":action,"compat_task_id":task_id})

        self.task_ledger.update(task_id,"running","dispatch",{
            "action":action,"actor":actor,"source":"job","mutation_performed":False,
            "mission_id":mission_id,
        })

        queue_row=None
        if self.queue:
            queue_row=self.queue.enqueue(
                action,payload,mission_id=mission_id,project=project,actor=actor,
                permissions=permissions,approved=approved,
                idempotency_key=idempotency_key or (f"mission:{mission_id}" if mission_id else "job:"+task_id),
                max_retries=max_retries,
            )
            queue_row=self.queue.claim(self.worker_id,queue_row["queue_id"])
            if not queue_row:raise RuntimeError("durable queue claim failed")

        try:
            if self.budgets and mission_id:
                self.budgets.consume(mission_id,"tool_calls",1)
                self.budgets.assert_allowed(mission_id)
            receipt=self.action_bus.dispatch(
                action,payload,project=project,source="job",actor=actor,
                approved=approved,permissions=permissions,
                idempotency_key=idempotency_key or (f"mission:{mission_id}" if mission_id else "job:"+task_id),
            )
            if self.queue and queue_row:self.queue.ack(queue_row["queue_id"],receipt,worker_id=self.worker_id)
            self.task_ledger.update(task_id,"completed","complete",{
                "action":action,"action_id":receipt["action_id"],
                "action_status":receipt["status"],
                "mutation_performed":bool((receipt.get("spec") or {}).get("mutating")),
                "mission_id":mission_id,"queue_id":queue_row["queue_id"] if queue_row else None,
            })
            if self.missions and mission_id:
                self.missions.checkpoint(mission_id,"action_completed",{"action_id":receipt["action_id"],"status":receipt["status"]})
                self.missions.transition(mission_id,"VERIFYING",current_step="sudarshan_verification",progress=.9)
            return {"job_id":task_id,"mission_id":mission_id,
                    "queue_id":queue_row["queue_id"] if queue_row else None,
                    "status":"completed","action":receipt}
        except Exception as exc:
            if self.queue and queue_row:
                try:self.queue.fail(queue_row["queue_id"],f"{type(exc).__name__}: {exc}",requeue=False,worker_id=self.worker_id)
                except Exception:pass
            self.task_ledger.update(task_id,"failed","dispatch",{
                "action":action,"error":f"{type(exc).__name__}: {exc}",
                "mutation_performed":False,"mission_id":mission_id,
                "queue_id":queue_row["queue_id"] if queue_row else None,
            })
            if self.missions and mission_id:
                try:
                    self.missions.increment_retry(mission_id,f"{type(exc).__name__}: {exc}")
                    self.missions.transition(mission_id,"FAILED",current_step="dispatch_failed",
                                             error=f"{type(exc).__name__}: {exc}")
                except Exception:pass
            raise

    def mark_verified(self,mission_id,passed,reason=""):
        if not self.missions or not mission_id:return None
        if passed:
            if self.queue and not self.queue.mission_drained(mission_id):
                return self.missions.transition(mission_id,"WAITING",current_step="queue_not_drained",
                                                verification_status="pending")
            return self.missions.transition(mission_id,"COMPLETED",current_step="complete",progress=1.0,
                                            verification_status="passed",
                                            metadata_patch={"verification_reason":str(reason)})
        return self.missions.transition(mission_id,"FAILED",current_step="verification_failed",
                                        verification_status="failed",error=str(reason))

    def recover_startup(self):
        out={"queue":[],"missions":[]}
        if self.queue:out["queue"]=self.queue.recover_stale_processing(force=True)
        if self.missions:out["missions"]=self.missions.recover_interrupted()
        self._emit("MISSION_RECOVERY_SCAN",{"queue":len(out["queue"]),"missions":len(out["missions"])})
        return out

    def get(self,job_id):
        return self.task_ledger.get(job_id)

    def list(self,project=None,limit=100):
        return self.task_ledger.list_tasks(project,limit)

    def status(self):
        return {
            "owner":"KRISHNA Job Runtime",
            "mode":"durable-queue-inline-worker",
            "active":self.task_ledger.active(),
            "queue":self.queue.status() if self.queue else None,
            "missions":self.missions.status() if self.missions else None,
            "authority":"Shared Action Bus + durable backend queue",
        }
