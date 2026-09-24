from __future__ import annotations

import math
import re
import wave
from pathlib import Path


class GitaLipSyncPlanner:
    """Language-aware fallback viseme planner for Gita speech.

    This planner creates deterministic Oculus-style viseme timing commands. It is
    intentionally labelled ESTIMATED until a real forced aligner + production
    facial rig is verified. When a PCM WAV is available, its measured duration is
    used so mouth motion spans the actual audio rather than an unrelated estimate.
    """

    VERSION = "gita-lipsync-v1"
    VISEMES = ("sil","PP","FF","TH","DD","kk","CH","SS","nn","RR","aa","E","ih","oh","ou")
    LANGUAGES = ("sa","or","hi","en")

    DEVANAGARI_VOWELS = {
        "अ":"aa","आ":"aa","ा":"aa","इ":"ih","ि":"ih","ई":"E","ी":"E",
        "उ":"ou","ु":"ou","ऊ":"ou","ू":"ou","ऋ":"RR","ृ":"RR","ए":"E","े":"E",
        "ऐ":"E","ै":"E","ओ":"oh","ो":"oh","औ":"ou","ौ":"ou",
    }
    ODIA_VOWELS = {
        "ଅ":"aa","ଆ":"aa","ା":"aa","ଇ":"ih","ି":"ih","ଈ":"E","ୀ":"E",
        "ଉ":"ou","ୁ":"ou","ଊ":"ou","ୂ":"ou","ଋ":"RR","ୃ":"RR","ଏ":"E","େ":"E",
        "ଐ":"E","ୈ":"E","ଓ":"oh","ୋ":"oh","ଔ":"ou","ୌ":"ou",
    }
    DEVANAGARI_CONSONANTS = {
        **{x:"kk" for x in "कखगघङ"},
        **{x:"CH" for x in "चछजझञ"},
        **{x:"DD" for x in "टठडढणतथदध"},
        **{x:"nn" for x in "नम"},
        **{x:"PP" for x in "पबभ"},
        "फ":"FF","व":"FF",
        **{x:"RR" for x in "यरल"},
        **{x:"SS" for x in "शषसह"},
    }
    ODIA_CONSONANTS = {
        **{x:"kk" for x in "କଖଗଘଙ"},
        **{x:"CH" for x in "ଚଛଜଝଞ"},
        **{x:"DD" for x in "ଟଠଡଢଣତଥଦଧ"},
        **{x:"nn" for x in "ନମ"},
        **{x:"PP" for x in "ପବଭ"},
        "ଫ":"FF","ଵ":"FF","ୱ":"FF",
        **{x:"RR" for x in "ଯୟରଲଳ"},
        **{x:"SS" for x in "ଶଷସହ"},
    }

    @classmethod
    def _latin_viseme(cls, token: str) -> str:
        value=token.lower()
        if re.search(r"[bmp]",value):return "PP"
        if re.search(r"[fv]",value):return "FF"
        if "th" in value:return "TH"
        if re.search(r"[td]",value):return "DD"
        if re.search(r"[kg]",value):return "kk"
        if re.search(r"(ch|j|sh|zh)",value):return "CH"
        if re.search(r"[sz]",value):return "SS"
        if re.search(r"[nl]",value):return "nn"
        if re.search(r"[r]",value):return "RR"
        if re.search(r"(oo|u|w)",value):return "ou"
        if re.search(r"(o)",value):return "oh"
        if re.search(r"(ee|e)",value):return "E"
        if re.search(r"(i|y)",value):return "ih"
        if re.search(r"[a]",value):return "aa"
        return "sil"

    @classmethod
    def _units(cls,text: str,language: str) -> list[tuple[str,str]]:
        raw=str(text or "")
        if not raw.strip():return []
        units=[]
        if language in {"sa","hi"}:
            vowels=cls.DEVANAGARI_VOWELS; consonants=cls.DEVANAGARI_CONSONANTS
            for ch in raw:
                if ch in vowels:units.append((ch,vowels[ch]))
                elif ch in consonants:units.append((ch,consonants[ch]))
                elif ch.isspace() or ch in "।॥,.;:!?-":units.append((ch,"sil"))
        elif language=="or":
            vowels=cls.ODIA_VOWELS; consonants=cls.ODIA_CONSONANTS
            for ch in raw:
                if ch in vowels:units.append((ch,vowels[ch]))
                elif ch in consonants:units.append((ch,consonants[ch]))
                elif ch.isspace() or ch in ",.;:!?-।॥":units.append((ch,"sil"))
        else:
            for token in re.findall(r"[A-Za-z']+|\s+|[^A-Za-z\s]+",raw):
                units.append((token,"sil" if token.isspace() else cls._latin_viseme(token)))
        # Collapse long runs of identical visemes while retaining natural silences.
        compact=[]
        for grapheme,viseme in units:
            if compact and compact[-1][1]==viseme and viseme!="sil":
                compact[-1]=(compact[-1][0]+grapheme,viseme)
            elif compact and compact[-1][1]=="sil" and viseme=="sil":
                compact[-1]=(compact[-1][0]+grapheme,"sil")
            else:
                compact.append((grapheme,viseme))
        return compact

    @staticmethod
    def _wav_duration(path: str|Path|None) -> float|None:
        if not path:return None
        p=Path(path)
        if not p.is_file() or p.suffix.lower()!=".wav":return None
        try:
            with wave.open(str(p),"rb") as wav:
                rate=wav.getframerate(); frames=wav.getnframes()
                return (frames/rate) if rate else None
        except (wave.Error,OSError):
            return None

    @classmethod
    def plan(cls,text: str,language: str,audio_path: str|Path|None=None) -> dict:
        lang=str(language or "").strip().lower()
        if lang not in cls.LANGUAGES:
            raise ValueError("lip-sync language must be one of: sa, or, hi, en")
        units=cls._units(text,lang)
        if not units:
            raise ValueError("lip-sync text is required")
        measured=cls._wav_duration(audio_path)
        if measured and measured>0.08:
            duration=measured
            timing_source="wav_duration_distributed"
        else:
            # Conservative speaking-time estimate; Sanskrit recitation is slower.
            per_unit=0.145 if lang=="sa" else (0.12 if lang in {"or","hi"} else 0.105)
            duration=max(0.35,min(60.0,len(units)*per_unit))
            timing_source="text_estimate"
        weights=[0.55 if v=="sil" else 1.0 for _,v in units]
        total=sum(weights) or 1.0
        t=0.0;events=[]
        for index,((grapheme,viseme),weight) in enumerate(zip(units,weights)):
            span=duration*(weight/total)
            start=t;end=duration if index==len(units)-1 else min(duration,t+span)
            events.append({
                "index":index,
                "grapheme":grapheme,
                "viseme":viseme,
                "start_ms":round(start*1000),
                "end_ms":round(end*1000),
            })
            t=end
        return {
            "version":cls.VERSION,
            "language":lang,
            "duration_ms":round(duration*1000),
            "timing_source":timing_source,
            "viseme_set":"Oculus-15-compatible",
            "events":events,
            "verified":False,
            "verification_status":"ESTIMATED_NOT_VERIFIED",
            "verification_note":"Requires audio forced-alignment and a verified production facial rig before exact lip-sync may be claimed.",
        }

    @classmethod
    def status(cls) -> dict:
        return {
            "version":cls.VERSION,
            "languages":list(cls.LANGUAGES),
            "visemes":list(cls.VISEMES),
            "audio_duration_aware":True,
            "forced_alignment_verified":False,
            "production_rig_verified":False,
            "status":"ESTIMATED_NOT_VERIFIED",
        }
