"""BRAHMAGYAN research protocol for auditory entrainment, embodiment and OBE reports.

No frequency is encoded as an astral-projection mechanism. Competing explanations are tested.
Human experimentation requires informed consent and appropriate safety/ethics review.
"""
PROGRAM={
 "program_id":"brahmagyan.auditory-embodiment.v1",
 "question":"Which measurable auditory, sleep-state, vestibular and multisensory variables change EEG, cognition, embodiment or reported OBE-like experiences?",
 "claim_status":"open_research_question",
 "astral_projection_proven":False,
 "variables":{
  "auditory":["binaural","monaural","isochronic","music/noise control","silence control"],
  "beat_hz":[3,4,6,8,9,10,12,15,20,40],
  "measurements":["EEG spectral power","EEG connectivity/coherence","behavioral attention","memory","calm/focus","body ownership","self-location","agency","sleep stage"],
  "mechanisms":["auditory beat perception","entrainment hypothesis","expectancy/placebo","relaxation/arousal","multisensory integration","vestibular-proprioceptive mismatch","sleep/lucid-dream transition"],
 },
 "evidence_rules":["randomized/blinded controls where feasible","pre-register outcome and frequency","separate subjective report from EEG","record null results","independent replication","do not infer non-local consciousness from subjective OBE report"],
 "safety":["no unsupervised electrical/magnetic brain stimulation","no seizure-provocation experiments","human studies require consent and appropriate ethics/safety review"],
 "seed_evidence":[
  {"pmid":"37205669","finding":"2023 systematic review found binaural-beat EEG entrainment results inconsistent"},
  {"pmid":"42349368","finding":"2026 theta binaural-beat review found low-certainty/heterogeneous evidence; some cognition signals"},
  {"pmid":"41920802","finding":"2026 brief 6 Hz study reported increased calmness/focus"},
  {"pmid":"41937954","finding":"2026 embodiment EEG review found central-parietal alpha reduction most recurrent; theta evidence sparse/contradictory"},
  {"pmid":"40540759","finding":"2025 OBE scoping review found heterogeneous triggers and competing explanatory hypotheses"}
 ]
}

def research_plan():
 return {**PROGRAM,"promotion_rule":"results remain evidence/candidates until BRAHMA and knowledge-law gates pass"}
