from __future__ import annotations

"""Engineering research programs for persistent scientist/Shishya specialties."""

def multi_objective_design_score(*, performance,reliability,reusability,manufacturability,
                                 safety,material_cost,manufacturing_cost,maintenance,
                                 complexity,mass):
    benefits=(performance,reliability,reusability,manufacturability,safety)
    costs=(material_cost,manufacturing_cost,maintenance,complexity,mass)
    b=sum(max(0,min(1,float(x))) for x in benefits)/len(benefits)
    c=sum(max(0,min(1,float(x))) for x in costs)/len(costs)
    return round(.7*b+.3*(1-c),6)

def engineering_research_program(parent_rishi,specialty):
    return {
        "parent_rishi":str(parent_rishi).lower(),"specialty":str(specialty),
        "continuous_loop":[
            "requirements","prior_art","failure_history","physics_model","candidate_design",
            "simulation","independent_replication","manufacturability","cost_model",
            "safety_reliability_review","contradiction_review","rishi_review","brahma_qc","learn",
        ],
        "optimization":{
            "maximize":["performance","reliability","reusability","manufacturability","safety"],
            "minimize":["material_cost","manufacturing_cost","maintenance","part_count","complexity","mass","waste"],
            "selection":"pareto_frontier; never optimize cost alone",
        },
        "readiness_policy":"track scientist maturity separately from technology TRL 1-9",
        "physical_test_policy":"simulation/review may be autonomous; hazardous physical testing requires applicable facility, safety and human authorization gates",
        "failure_policy":"negative results and rejected hypotheses are retained as useful evidence",
    }

ROCKET_PROGRAM=engineering_research_program("marichi","rocket propulsion and engine engineering")
