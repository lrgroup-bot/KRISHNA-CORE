from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class SimulationRequest:
    simulation_id: str
    objective: str
    evidence_refs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    personas: tuple[dict[str, Any], ...] = ()
    scenarios: tuple[dict[str, Any], ...] = ()
    rounds: int = 3
    seed: int = 0
    company_id: str | None = None
    mode: str = "counterfactual"

@dataclass(frozen=True)
class SimulationPolicy:
    sandbox_only: bool = True
    writes_to_real_systems: bool = False
    may_spend: bool = False
    may_publish: bool = False
    may_sign: bool = False
    may_deploy: bool = False
    label: str = "SIMULATION_NOT_TRUTH"

def simulation_packet(request: SimulationRequest, policy: SimulationPolicy = SimulationPolicy()):
    if not request.simulation_id or not request.objective:
        raise ValueError("simulation identity and objective required")
    if request.rounds < 1 or request.rounds > 100:
        raise ValueError("rounds must be between 1 and 100")
    return {"simulation_id": request.simulation_id, "objective": request.objective,
            "company_id": request.company_id, "evidence_refs": list(dict.fromkeys(request.evidence_refs)),
            "assumptions": list(request.assumptions), "personas": list(request.personas),
            "scenarios": list(request.scenarios), "rounds": request.rounds, "seed": request.seed,
            "mode": request.mode, "policy": policy.__dict__, "status": "planned"}