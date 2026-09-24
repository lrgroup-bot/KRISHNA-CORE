from __future__ import annotations

"""Provider-neutral text -> viseme timing planner for KRISHNA speech.

This module produces deterministic fallback timing for Sanskrit, Odia, Hindi and
English. It does not claim acoustic alignment. When a verified audio aligner is
available, its timings should replace these estimates while preserving the same
Oculus-style viseme contract.
"""

import re
from dataclasses import dataclass, asdict


OCULUS_VISEMES = (
    "sil", "PP", "FF", "TH", "DD", "kk", "CH", "SS",
    "nn", "RR", "aa", "E", "ih", "oh", "ou",
)

OCULUS_MORPH_TARGETS = {
    "sil": "viseme_sil",
    "PP": "viseme_PP",
    "FF": "viseme_FF",
    "TH": "viseme_TH",
    "DD": "viseme_DD",
    "kk": "viseme_kk",
    "CH": "viseme_CH",
    "SS": "viseme_SS",
    "nn": "viseme_nn",
    "RR": "viseme_RR",
    "aa": "viseme_aa",
    "E": "viseme_E",
    "ih": "viseme_I",
    "oh": "viseme_O",
    "ou": "viseme_U",
}


@dataclass(frozen=True)
class VisemeEvent:
    viseme: str
    morph_target: str
    start_ms: int
    end_ms: int
    token: str
    confidence: str = "estimated"


class KrishnaLipSyncPlanner:
    VERSION = "krishna-lipsync-v1"
    LANGUAGES = {"sa": "sanskrit", "or": "odia", "hi": "hindi", "en": "english"}

    # Deliberately conservative character-to-mouth-shape mapping. This is a
    # renderer contract, not a linguistic claim about exact phonetics.
    DEVANAGARI = {
        **{c: "aa" for c in "अआा"},
        **{c: "ih" for c in "इईिीऋृ"},
        **{c: "ou" for c in "उऊुू"},
        **{c: "E" for c in "एऐेै"},
        **{c: "oh" for c in "ओऔोौ"},
        **{c: "kk" for c in "कखगघङ"},
        **{c: "CH" for c in "चछजझञ"},
        **{c: "DD" for c in "टठडढणतथदध"},
        **{c: "nn" for c in "नम"},
        **{c: "PP" for c in "पबभ"},
        "फ": "FF",
        **{c: "RR" for c in "यरलव"},
        **{c: "SS" for c in "शषसह"},
    }
    ODIA = {
        **{c: "aa" for c in "ଅଆା"},
        **{c: "ih" for c in "ଇଈିୀଋୃ"},
        **{c: "ou" for c in "ଉଊୁୂ"},
        **{c: "E" for c in "ଏଐେୈ"},
        **{c: "oh" for c in "ଓଔୋୌ"},
        **{c: "kk" for c in "କଖଗଘଙ"},
        **{c: "CH" for c in "ଚଛଜଝଞ"},
        **{c: "DD" for c in "ଟଠଡଢଣତଥଦଧ"},
        **{c: "nn" for c in "ନମ"},
        **{c: "PP" for c in "ପବଭ"},
        "ଫ": "FF",
        **{c: "RR" for c in "ୟରଲୱଵ"},
        **{c: "SS" for c in "ଶଷସହ"},
    }

    @classmethod
    def status(cls) -> dict:
        return {
            "version": cls.VERSION,
            "languages": dict(cls.LANGUAGES),
            "visemes": list(OCULUS_VISEMES),
            "morph_targets": dict(OCULUS_MORPH_TARGETS),
            "timing": "deterministic_estimate",
            "acoustic_alignment_verified": False,
            "requires_audio_alignment_for_production": True,
            "requires_morph_targets": True,
            "truth_note": (
                "Estimated timings are suitable for fallback animation planning; "
                "production lip-sync remains unverified until aligned against real audio "
                "and rendered on a GLB with verified viseme morph targets."
            ),
        }

    @staticmethod
    def _duration(viseme: str, mode: str) -> int:
        base = 105 if mode == "SHLOKA_RECITATION" else 82
        if viseme in {"aa", "E", "ih", "oh", "ou"}:
            base += 45
        if mode == "SHLOKA_RECITATION":
            base += 20
        return base

    @classmethod
    def _english_viseme(cls, token: str) -> str:
        t = token.lower()
        if not t:
            return "sil"
        if t.startswith(("th",)):
            return "TH"
        if t.startswith(("ch", "sh", "j")):
            return "CH"
        if t.startswith(("ph", "f", "v")):
            return "FF"
        if t.startswith(("p", "b", "m")):
            return "PP"
        if t.startswith(("k", "g", "q", "c")):
            return "kk"
        if t.startswith(("t", "d")):
            return "DD"
        if t.startswith(("n",)):
            return "nn"
        if t.startswith(("r", "l", "w", "y")):
            return "RR"
        if t.startswith(("s", "z", "x", "h")):
            return "SS"
        if t.startswith(("oo", "u")):
            return "ou"
        if t.startswith(("o",)):
            return "oh"
        if t.startswith(("e", "ai", "ay")):
            return "E"
        if t.startswith(("i", "y")):
            return "ih"
        return "aa"

    @classmethod
    def _tokens(cls, text: str, language: str):
        if language == "en":
            return re.findall(r"[A-Za-z]+|\d+|[^\s]", text)
        # Indic scripts are handled per visible code point. Marks inherit their
        # own mapped mouth shape where useful; punctuation becomes silence.
        return [c for c in text if not c.isspace()]

    @classmethod
    def _viseme_for(cls, token: str, language: str) -> str:
        if re.fullmatch(r"[\s\.,;:!?।॥\-–—()\[\]{}'\"]+", token):
            return "sil"
        if language in {"sa", "hi"}:
            return cls.DEVANAGARI.get(token, "sil" if not token.isalnum() else "aa")
        if language == "or":
            return cls.ODIA.get(token, "sil" if not token.isalnum() else "aa")
        return cls._english_viseme(token)

    @classmethod
    def plan(cls, text: str, language: str, mode: str = "GITA_EXPLANATION") -> dict:
        language = str(language or "").strip().lower()
        if language not in cls.LANGUAGES:
            raise ValueError("language must be one of: sa, or, hi, en")
        mode = str(mode or "GITA_EXPLANATION").strip().upper()
        value = str(text or "").strip()
        if not value:
            return {
                **cls.status(),
                "language": language,
                "mode": mode,
                "text": "",
                "duration_ms": 0,
                "events": [],
            }

        events = []
        cursor = 0
        for token in cls._tokens(value, language):
            viseme = cls._viseme_for(token, language)
            duration = 115 if viseme == "sil" else cls._duration(viseme, mode)
            event = VisemeEvent(viseme, OCULUS_MORPH_TARGETS[viseme], cursor, cursor + duration, token)
            events.append(asdict(event))
            cursor += duration

        # End in a neutral mouth state so consecutive speech segments can
        # transition cleanly.
        events.append(asdict(VisemeEvent("sil", OCULUS_MORPH_TARGETS["sil"], cursor, cursor + 90, "")))
        cursor += 90
        return {
            **cls.status(),
            "language": language,
            "mode": mode,
            "text": value,
            "duration_ms": cursor,
            "events": events,
        }
