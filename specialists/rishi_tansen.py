"""Rishi Tansen — KRISHNA/BRAHMAGYAN music research specialist.

Canonical owner: KRISHNA / BRAHMAGYAN.
Consumers such as LR Songs receive task-scoped dossiers/receipts only.
"""
from dataclasses import dataclass, asdict
from typing import Iterable

RISHI_TANSEN = {
    "id": "rishi-tansen",
    "name": "Rishi Tansen",
    "owner": "KRISHNA",
    "knowledge_home": "BRAHMAGYAN",
    "role": "MUSIC_RESEARCH_AND_KNOWLEDGE_RISHI",
    "languages": ["hi", "or"],
    "research": {
        "discovery": "WEB_ONLY",
        "reasoning_router": "KRISHNA_FREE_ROUTER",
        "external_content": "DATA_ONLY_UNTIL_VERIFIED",
        "paid_fallback": False,
        "provenance_required": True,
    },
    "domains": [
        "audience_interest", "lyrics_prosody", "hindi_pronunciation",
        "odia_pronunciation", "melody", "raga", "taal_rhythm",
        "composition", "instrumentation", "arrangement", "vocal_performance",
        "music_history", "contemporary_production", "mix_master",
    ],
    "restrictions": {
        "copy_protected_lyrics": False,
        "copy_protected_melody": False,
        "clone_famous_singer_voice": False,
        "production_execution": False,
    },
}

@dataclass(frozen=True)
class TansenResearchRequest:
    project_id: str
    subject: str
    language: str
    audience: str
    questions: tuple[str, ...]

def create_research_request(project_id: str, subject: str, language: str,
                            audience: str, questions: Iterable[str]):
    if language not in RISHI_TANSEN["languages"]:
        raise ValueError("LR Songs Tansen research is Hindi/Odia only")
    qs = tuple(q.strip() for q in questions if q and q.strip())
    if not project_id or not subject or not audience or not qs:
        raise ValueError("Tansen research request incomplete")
    req = TansenResearchRequest(project_id, subject, language, audience, qs)
    return {
        "schema": "krishna.rishi.tansen.request.v1",
        "rishi": RISHI_TANSEN["id"],
        "request": asdict(req),
        "route": "KRISHNA_FREE_ROUTER",
        "mode": "WEB_ONLY",
        "provenance_required": True,
        "production_authority": False,
    }

def issue_verified_dossier(request: dict, findings: list, source_refs: list,
                           verification_receipt: str):
    if request.get("rishi") != RISHI_TANSEN["id"]:
        raise ValueError("wrong Rishi")
    if not findings or not source_refs or not verification_receipt:
        raise ValueError("verified evidence required")
    return {
        "schema": "krishna.rishi.tansen.dossier.v1",
        "project_id": request["request"]["project_id"],
        "rishi": RISHI_TANSEN["id"],
        "findings": findings,
        "source_refs": source_refs,
        "verification_receipt": verification_receipt,
        "knowledge_home": "BRAHMAGYAN",
        "consumer_payload": "TASK_SCOPED_DOSSIER",
        "production_authority": False,
    }
