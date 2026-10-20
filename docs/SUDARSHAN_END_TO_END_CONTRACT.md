# Sudarshan End-to-End Project Contract

## Authority
KRISHNA is the root system authority. Sudarshan is the project control, orchestration, and independent verification plane. Sudarshan may request capabilities and permissions from KRISHNA but cannot grant itself authority or bypass KRISHNA policy.

## Approved project ingress
Two canonical ingress paths are supported:

1. Owner/User -> KRISHNA intent -> Sudarshan.
2. Customer -> LR Technology -> customer-approved, versioned Project Specification Package -> Sudarshan -> KRISHNA authority gate.

LR Technology is the customer/product interface. It does not directly command KRISHNA, Rishis, specialists, workers, models, security controls, spending, deployment, or infrastructure. Normal LR Technology project communication terminates at Sudarshan.

After ingress, the canonical execution path is:
Sudarshan -> project bootstrap/load -> discovery/baseline -> Project Brain reconciliation -> task/dependency plan -> KRISHNA authority requests as required -> specialist/Rishi knowledge routing -> team assembly -> implementation -> build/run -> automated and specialist QA -> independent Sudarshan verification -> repair/retest loop -> phase completion -> final acceptance -> deploy -> post-deploy runtime verification -> learning/provenance review -> Gyan-Bhandar/Project Memory -> verified release package.

For LR Technology projects, the verified release package returns:
Sudarshan -> LR Technology -> customer UAT/delivery.

Design work additionally requires Vishvakarma consultation and mandatory design gates. New ideas enter through Idea Intake and Project Delta, never as an untracked code mutation.

A project MUST NOT be reported complete solely because source code exists or tests passed. Deployment and actual runtime verification are distinct completion gates. When physical/runtime access is unavailable, status remains POST_DEPLOY_VERIFY or BLOCKED rather than VERIFIED_COMPLETE.
