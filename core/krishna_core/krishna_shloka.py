from __future__ import annotations

import json
import os
import random
import re
from pathlib import Path
from typing import Callable


class KrishnaShlokaOrchestrator:
    """Canonical Gita conversation coordinator.

    Retrieval is always from GitaGyan. Performance comes from GitaPerformanceEngine.
    Generated explanation is kept separate from canonical Sanskrit and source data.
    """

    VERSION = "krishna-shloka-orchestrator-v1"

    SITUATION_VERSES = {
        "confusion": (2, 7),
        "courage": (2, 14),
        "work": (2, 47),
        "results": (2, 47),
        "failure": (2, 48),
        "mind": (6, 26),
        "meditation": (6, 26),
        "self": (6, 5),
        "devotion": (9, 22),
        "offering": (9, 26),
        "fear": (2, 20),
        "change": (2, 13),
        "choice": (18, 63),
        "agency": (18, 63),
    }

    KEYWORD_GROUPS = {
        "confusion": ("confused", "confusion", "don't know", "dont know", "bujhi paruni", "ବୁଝି", "ଦ୍ୱନ୍ଦ୍ୱ", "उलझ", "समझ नहीं"),
        "courage": ("courage", "brave", "fear", "afraid", "ଭୟ", "ସାହସ", "डर", "हिम्मत"),
        "work": ("work", "job", "result", "outcome", "କାମ", "ଫଳ", "काम", "फल"),
        "mind": ("mind", "focus", "attention", "ମନ", "ଧ୍ୟାନ", "मन", "ध्यान"),
        "devotion": ("devotion", "bhakti", "ଭକ୍ତି", "भक्ति"),
        "change": ("change", "loss", "death", "ପରିବର୍ତ୍ତନ", "ମୃତ୍ୟୁ", "बदल", "मृत्यु"),
        "choice": ("choice", "decision", "decide", "ନିଷ୍ପତ୍ତି", "निर्णय"),
    }

    def __init__(self, gita, performance, state_path: str | Path):
        self.gita = gita
        self.performance = performance
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def _state(self) -> dict:
        if not self.state_path.is_file():
            return {"last_reference": None}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {"last_reference": None}
        except (OSError, json.JSONDecodeError):
            return {"last_reference": None}

    def _save_state(self, **changes) -> None:
        state = self._state()
        state.update(changes)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.state_path)

    @staticmethod
    def _lang(message: str, default: str = "or") -> str:
        text = str(message or "").lower()
        if any(x in text for x in ("hindi", "हिंदी", "हिन्दी")):
            return "hi"
        if any(x in text for x in ("english", "in english")):
            return "en"
        if any(x in text for x in ("odia", "oriya", "ଓଡ଼ିଆ", "ଓଡିଆ")):
            return "or"
        return default

    @staticmethod
    def _depth(message: str, default: str = "deep") -> str:
        text = str(message or "").lower()
        return "brief" if any(x in text for x in ("brief", "short", "ଛୋଟ", "संक्षेप")) else default

    def _explain(self, row: dict, language: str, depth: str,
                 explain: Callable[[str], str] | None) -> str | None:
        if explain is None:
            return None
        prompt = self.gita.lesson_prompt(row, language, depth)
        out = str(explain(prompt) or "").strip()
        return out or None

    def verse(self, chapter: int, verse: int, *, language: str = "or",
              depth: str = "deep", explain: Callable[[str], str] | None = None) -> dict:
        row = self.gita.verse(chapter, verse)
        performance = self.performance.record(chapter, verse)
        explanation = self._explain(row, language, depth, explain)
        ref = f"{int(chapter)}.{int(verse)}"
        self._save_state(last_reference=ref)
        partha_line = {
            "or": "ପାର୍ଥ, ଏବେ ଏହାର ଅର୍ଥକୁ ଶାନ୍ତ ଭାବରେ ଦେଖିବା।",
            "hi": "पार्थ, अब इसका अर्थ शांत मन से समझते हैं।",
            "en": "Partha, now consider its meaning calmly.",
        }[language]
        return {
            "reference": f"Bhagavad Gita {ref}",
            "chapter": int(chapter),
            "verse": int(verse),
            "sanskrit": row["sanskrit"],
            "transliteration": row.get("transliteration"),
            "source": row.get("source"),
            "language": language,
            "depth": depth,
            "generated_explanation": explanation,
            "performance": performance,
            "partha_line": partha_line,
            "speech_segments": [
                {
                    "kind": "shloka",
                    "mode": "SHLOKA_RECITATION",
                    "language": "sa",
                    "text": row["sanskrit"],
                    "timing_profile": performance["recitation_profile"],
                },
                {
                    "kind": "explanation",
                    "mode": "GITA_EXPLANATION",
                    "language": language,
                    "text": explanation,
                    "timing_profile": performance["pause_profile"],
                },
                {
                    "kind": "partha",
                    "mode": "KRISHNA_TO_PARTHA",
                    "language": language,
                    "text": partha_line,
                },
            ],
            "canonical_sanskrit_unchanged": True,
            "generated_commentary_separate": True,
        }

    def chapter(self, chapter: int, *, include_performance: bool = True) -> dict:
        c = int(chapter)
        if not 1 <= c <= 18:
            raise ValueError("chapter must be between 1 and 18")
        rows = [row for row in self.gita._load_corpus() if row["chapter"] == c]
        items = []
        for row in rows:
            item = {
                "chapter": c,
                "verse": row["verse"],
                "verse_id": f"{c}.{row['verse']}",
                "sanskrit": row["sanskrit"],
                "transliteration": row.get("transliteration"),
                "source": row.get("source"),
            }
            if include_performance:
                item["performance"] = self.performance.record(c, row["verse"])
            items.append(item)
        return {
            "chapter": c,
            "verse_count": len(items),
            "expected_verse_count": self.gita.CHAPTER_VERSE_COUNTS[c - 1],
            "items": items,
            "sequential_recitation": True,
        }

    def search(self, query: str, *, limit: int = 10) -> dict:
        q = " ".join(str(query or "").lower().split())
        if not q:
            raise ValueError("query is required")
        limit = max(1, min(50, int(limit)))
        tokens = [x for x in re.split(r"[^\w\u0900-\u097f\u0b00-\u0b7f]+", q) if len(x) > 1]
        scored = []
        for row in self.gita._load_corpus():
            perf = self.performance.record(row["chapter"], row["verse"])
            hay = " ".join([
                perf["theme"],
                " ".join(perf["secondary_themes"]),
                str(row.get("transliteration") or ""),
                str(row.get("summary_en") or ""),
            ]).lower()
            score = sum(3 if token in perf["theme"].lower() else 1 for token in tokens if token in hay)
            if score:
                scored.append((score, row["chapter"], row["verse"], perf))
        scored.sort(key=lambda x: (-x[0], x[1], x[2]))
        items = []
        for score, c, v, perf in scored[:limit]:
            row = self.gita.verse(c, v)
            items.append({
                "reference": f"Bhagavad Gita {c}.{v}",
                "chapter": c,
                "verse": v,
                "sanskrit": row["sanskrit"],
                "transliteration": row.get("transliteration"),
                "theme": perf["theme"],
                "score": score,
                "performance": perf,
            })
        return {"query": query, "count": len(items), "items": items, "mode": "offline_theme_search"}

    def situation(self, message: str, *, language: str = "or",
                  depth: str = "deep", explain: Callable[[str], str] | None = None) -> dict:
        text = " ".join(str(message or "").lower().split())
        category = None
        for name, words in self.KEYWORD_GROUPS.items():
            if any(word in text for word in words):
                category = name
                break
        if category is None:
            category = "confusion"
        ref = self.SITUATION_VERSES[category]
        out = self.verse(*ref, language=language, depth=depth, explain=explain)
        out["selection"] = {
            "mode": "situation_based_verified_reference",
            "category": category,
            "reason": f"KRISHNA maps the request to the curated '{category}' theme; this is guidance, not a claim of divine certainty.",
        }
        return out

    def random_verified(self, *, language: str = "or", depth: str = "deep",
                        explain: Callable[[str], str] | None = None) -> dict:
        rows = self.gita._load_corpus()
        row = random.SystemRandom().choice(rows)
        out = self.verse(row["chapter"], row["verse"], language=language, depth=depth, explain=explain)
        out["selection"] = {"mode": "random_verified_verse"}
        return out

    def adjacent(self, delta: int, *, language: str = "or", depth: str = "deep",
                 explain: Callable[[str], str] | None = None) -> dict:
        rows = self.gita._load_corpus()
        refs = [(row["chapter"], row["verse"]) for row in rows]
        last = str(self._state().get("last_reference") or "")
        try:
            c, v = [int(x) for x in last.split(".", 1)]
            index = refs.index((c, v))
        except (ValueError, TypeError):
            index = 0
        target = refs[max(0, min(len(refs) - 1, index + int(delta)))]
        return self.verse(*target, language=language, depth=depth, explain=explain)

    def parse_request(self, message: str, *, explain: Callable[[str], str] | None = None) -> dict:
        raw = str(message or "").strip()
        text = " ".join(raw.lower().split())
        language = self._lang(raw)
        depth = self._depth(raw)

        exact = re.search(r"(?<!\d)(1[0-8]|[1-9])\s*[\.:/-]\s*(\d{1,3})(?!\d)", text)
        if exact:
            return self.verse(int(exact.group(1)), int(exact.group(2)), language=language, depth=depth, explain=explain)

        chapter_match = re.search(r"(?:chapter|adhyaya|अध्याय|ଅଧ୍ୟାୟ)\s*(1[0-8]|[1-9])", text)
        if chapter_match and any(x in text for x in ("recite", "say", "chapter", "kuha", "କୁହ", "सुन")):
            return self.chapter(int(chapter_match.group(1)))

        if any(x in text for x in ("next verse", "next shloka", "next sloka", "ପରବର୍ତ୍ତୀ", "अगला")):
            return self.adjacent(1, language=language, depth=depth, explain=explain)
        if any(x in text for x in ("previous verse", "previous shloka", "previous sloka", "ପୂର୍ବ", "पिछला")):
            return self.adjacent(-1, language=language, depth=depth, explain=explain)
        if any(x in text for x in ("random verse", "random shloka", "random sloka")):
            return self.random_verified(language=language, depth=depth, explain=explain)

        for category, words in self.KEYWORD_GROUPS.items():
            if any(word in text for word in words):
                return self.situation(raw, language=language, depth=depth, explain=explain)

        query = re.sub(r"\b(?:krishna|gita|geeta|shloka|sloka|explain|say|tell me|what does|about)\b", " ", text)
        query = " ".join(query.split())
        results = self.search(query or "self knowledge", limit=5)
        if results["items"]:
            first = results["items"][0]
            out = self.verse(first["chapter"], first["verse"], language=language, depth=depth, explain=explain)
            out["selection"] = {
                "mode": "theme_search",
                "query": query,
                "reason": "Selected from deterministic offline theme metadata.",
            }
            return out
        return self.situation(raw, language=language, depth=depth, explain=explain)
