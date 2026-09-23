from __future__ import annotations

"""Optional local GNN training adapter.

KRISHNA does not claim a trainable production GNN architecture by default. The
adapter verifies backend/data readiness and accepts an explicitly supplied local
trainer callable when an experiment defines a validated schema and training
procedure.
"""


class LocalGNNTrainer:
    def __init__(self,backend,dataset):
        self.backend=backend
        self.dataset=dataset

    def readiness(self,min_examples=50):
        examples=self.dataset.load()
        count=len(examples)
        return {
            "backend_available":bool(self.backend.available()),
            "verified_examples":count,
            "minimum_examples":max(1,int(min_examples)),
            "ready":bool(self.backend.available()) and count>=max(1,int(min_examples)),
            "training_adapter_required":True,
        }

    def train(self,min_examples=50,*,trainer=None,schema=None):
        state=self.readiness(min_examples)
        if not state["ready"]:
            raise RuntimeError("GNN training prerequisites not satisfied")
        if trainer is None:
            return {
                **state,
                "trained":False,
                "status":"ADAPTER_REQUIRED",
                "reason":"no validated local GNN trainer/schema was supplied",
                "production_claim":False,
            }
        if not callable(trainer):
            raise TypeError("trainer must be callable")
        if not isinstance(schema,dict) or not schema:
            raise ValueError("validated dataset/model schema is required")
        examples=self.dataset.load()
        result=trainer(examples,schema)
        if not isinstance(result,dict):
            raise RuntimeError("GNN trainer must return a result dictionary")
        return {
            **state,
            "trained":bool(result.get("trained",False)),
            "status":"TRAINED_CANDIDATE" if result.get("trained") else "TRAINING_FAILED",
            "result":result,
            "production_claim":False,
            "verification_required":True,
        }
