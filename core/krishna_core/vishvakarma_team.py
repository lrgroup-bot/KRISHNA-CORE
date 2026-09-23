"""Sudarshan design team: a liaison consults Vishvakarma, workers execute, verifier gates."""
from dataclasses import dataclass
@dataclass(frozen=True)
class TeamRole:
 name:str; responsibility:str
TEAM=(
 TeamRole("Vishvakarma Liaison","retrieve relevant Rishi Vishvakarma knowledge and translate it into project guidance"),
 TeamRole("UX Architect","flows, information architecture and interaction states"),
 TeamRole("Visual Designer","visual language, typography, spacing and hierarchy"),
 TeamRole("Design System Engineer","tokens, components and consistency"),
 TeamRole("Responsive Accessibility Engineer","responsive behavior, keyboard and accessibility"),
 TeamRole("Implementation Worker","implement approved design specification"),
 TeamRole("Browser QA","Playwright-led functional browser verification"),
 TeamRole("Visual QA","render comparison and design-drift detection"),
 TeamRole("Sudarshan Verifier","independent final acceptance and repair routing"),
)
class VishvakarmaTeam:
 def brief(self,task_type,findings):
  if not findings:raise RuntimeError("Vishvakarma Liaison must consult Vishvakarma before team dispatch")
  return {"task_type":task_type,"consulted":"Rishi Vishvakarma","liaison":"Vishvakarma Liaison","knowledge":findings,"team":[r.name for r in TEAM]}
 def handoff(self,brief,design_spec):
  if brief.get("consulted")!="Rishi Vishvakarma":raise RuntimeError("missing Vishvakarma consultation")
  if not design_spec:raise RuntimeError("design specification required")
  return {"ready":True,"design_spec":design_spec,"workers":[r.name for r in TEAM[1:-1]],"verifier":"Sudarshan Verifier"}
