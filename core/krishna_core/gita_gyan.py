from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Callable, Iterable


class GitaGyan:
    """Daily Bhagavad Gita learning runtime for KRISHNA.

    Canonical Sanskrit stays separate from generated commentary. The runtime is
    offline-first and ships with a provenance-pinned conventional 700-verse corpus.
    Runtime overrides live under KRISHNA state and never rewrite bundled scripture.
    """

    VERSION = "gita-gyan-v2"
    EXPECTED_VERSE_COUNT = 700
    CHAPTER_VERSE_COUNTS = (
        47, 72, 43, 42, 29, 47, 30, 28, 34,
        42, 55, 20, 34, 27, 20, 24, 28, 78,
    )
    VERSE_NUMBERING = (
        "conventional 700-verse recension; source editions may include an additional "
        "opening question in chapter 13 and total 701"
    )
    LANGUAGES = {"or": "odia", "hi": "hindi", "en": "english"}
    BUNDLED_FILENAME = "bhagavad_gita_700.json"

    SEED = (
        {
            "chapter": 2,
            "verse": 47,
            "sanskrit": "कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।\nमा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि॥",
            "transliteration": "karmaṇy-evādhikāras te mā phaleṣu kadācana; mā karma-phala-hetur bhūr mā te saṅgo 'stv akarmaṇi",
            "summary_en": "Focus on responsible action without making attachment to outcomes the basis of action or inaction.",
        },
    )

    def __init__(self, state_root: str | Path, corpus_path: str | Path | None = None):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.progress_path = self.root / "progress.json"
        self.override_path = self.root / "bhagavad_gita.override.json"
        self.bundled_corpus_path = Path(__file__).resolve().parent / "data" / self.BUNDLED_FILENAME
        self._explicit_corpus = Path(corpus_path) if corpus_path else None

        if self._explicit_corpus is not None:
            self.corpus_path = self._explicit_corpus
        elif self.override_path.is_file():
            self.corpus_path = self.override_path
        elif self.bundled_corpus_path.is_file():
            self.corpus_path = self.bundled_corpus_path
        else:
            self.corpus_path = self.root / "bhagavad_gita.fallback.json"
            self._seed_if_missing()

    def _seed_if_missing(self) -> None:
        if not self.corpus_path.exists():
            self.corpus_path.write_text(
                json.dumps(list(self.SEED), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def _read_payload(self) -> tuple[dict, list]:
        try:
            raw_bytes = self.corpus_path.read_bytes()
            raw = json.loads(raw_bytes.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"gita corpus unavailable: {exc}") from exc

        if isinstance(raw, list):
            return {
                "schema_version": "legacy-array",
                "provenance": {},
                "sha256": hashlib.sha256(raw_bytes).hexdigest(),
            }, raw
        if not isinstance(raw, dict) or not isinstance(raw.get("verses"), list):
            raise RuntimeError("gita corpus must be a JSON array or an object with a verses array")

        meta = {k: v for k, v in raw.items() if k != "verses"}
        meta["sha256"] = hashlib.sha256(raw_bytes).hexdigest()
        return meta, raw["verses"]

    def _load_corpus(self) -> list[dict]:
        _meta, raw = self._read_payload()
        records = []
        seen = set()
        for row in raw:
            if not isinstance(row, dict):
                continue
            try:
                chapter, verse = int(row["chapter"]), int(row["verse"])
            except (KeyError, TypeError, ValueError):
                continue
            if not (1 <= chapter <= 18):
                continue
            max_verse = self.CHAPTER_VERSE_COUNTS[chapter - 1]
            if not (1 <= verse <= max_verse):
                continue
            sanskrit = str(row.get("sanskrit") or "").strip()
            if not sanskrit:
                continue
            key = (chapter, verse)
            if key in seen:
                continue
            seen.add(key)
            item = dict(row)
            item["chapter"] = chapter
            item["verse"] = verse
            item["sanskrit"] = sanskrit
            records.append(item)
        return sorted(records, key=lambda x: (x["chapter"], x["verse"]))

    def _integrity(self, corpus: list[dict]) -> dict:
        counts = {chapter: 0 for chapter in range(1, 19)}
        keys = set()
        for row in corpus:
            counts[row["chapter"]] += 1
            keys.add((row["chapter"], row["verse"]))
        expected = {
            chapter: self.CHAPTER_VERSE_COUNTS[chapter - 1]
            for chapter in range(1, 19)
        }
        chapter_counts_match = counts == expected
        complete = (
            len(corpus) == self.EXPECTED_VERSE_COUNT
            and len(keys) == self.EXPECTED_VERSE_COUNT
            and chapter_counts_match
        )
        return {
            "complete": complete,
            "verse_count": len(corpus),
            "unique_reference_count": len(keys),
            "chapter_counts": counts,
            "expected_chapter_counts": expected,
            "chapter_counts_match": chapter_counts_match,
        }

    def _load_progress(self) -> dict:
        if not self.progress_path.exists():
            return {"completed": [], "last_date": None, "preferred_language": "or"}
        try:
            data = json.loads(self.progress_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        data.setdefault("completed", [])
        data.setdefault("last_date", None)
        data.setdefault("preferred_language", "or")
        return data

    def _save_progress(self, data: dict) -> None:
        tmp = self.progress_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.progress_path)

    @staticmethod
    def _key(row: dict) -> str:
        return f'{int(row["chapter"])}.{int(row["verse"])}'

    def is_completed(self, chapter: int, verse: int) -> bool:
        key=f"{int(chapter)}.{int(verse)}"
        return key in {str(x) for x in (self._load_progress().get("completed") or [])}

    def mark_completed(self, chapter: int, verse: int, language: str | None = None) -> dict:
        row=self.verse(int(chapter),int(verse))
        key=self._key(row)
        progress=self._load_progress()
        completed=[str(x) for x in progress.get("completed") or []]
        if key not in completed:
            completed.append(key)
        progress["completed"]=completed
        progress["last_key"]=key
        if language:
            lang=str(language).strip().lower()
            if lang not in self.LANGUAGES:
                raise ValueError("language must be one of: or, hi, en")
            progress["preferred_language"]=lang
        self._save_progress(progress)
        return {
            "reference":key,
            "completed":True,
            "completed_count":len(set(completed)),
        }

    def status(self) -> dict:
        meta, _raw = self._read_payload()
        corpus = self._load_corpus()
        integrity = self._integrity(corpus)
        progress = self._load_progress()
        provenance = dict(meta.get("provenance") or {})
        return {
            "version": self.VERSION,
            "available_verses": len(corpus),
            "expected_verses": self.EXPECTED_VERSE_COUNT,
            "verse_numbering": self.VERSE_NUMBERING,
            "corpus_complete": integrity["complete"],
            "integrity": integrity,
            "corpus_path": str(self.corpus_path),
            "corpus_mode": (
                "explicit" if self._explicit_corpus is not None
                else "runtime_override" if self.corpus_path == self.override_path
                else "bundled" if self.corpus_path == self.bundled_corpus_path
                else "fallback_seed"
            ),
            "corpus_sha256": meta.get("sha256"),
            "schema_version": meta.get("schema_version"),
            "recension": meta.get("recension"),
            "provenance": provenance,
            "completed_count": len(set(progress["completed"])),
            "preferred_language": progress["preferred_language"],
            "last_date": progress["last_date"],
            "languages": dict(self.LANGUAGES),
            "offline_first": True,
            "commentary_is_separate_from_scripture": True,
        }

    def import_corpus(self, records: Iterable[dict]) -> dict:
        normalized = []
        for row in records:
            if not isinstance(row, dict):
                raise ValueError("each corpus item must be an object")
            normalized.append(dict(row))

        destination = self._explicit_corpus or self.override_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.corpus_path = destination
        corpus = self._load_corpus()
        integrity = self._integrity(corpus)
        return {
            "imported": len(corpus),
            "complete": integrity["complete"],
            "integrity": integrity,
            "destination": str(destination),
        }

    def clear_runtime_override(self) -> dict:
        if self._explicit_corpus is not None:
            raise RuntimeError("explicit corpus paths are controlled by the caller")
        if self.override_path.exists():
            self.override_path.unlink()
        if self.bundled_corpus_path.is_file():
            self.corpus_path = self.bundled_corpus_path
        else:
            self.corpus_path = self.root / "bhagavad_gita.fallback.json"
            self._seed_if_missing()
        return self.status()

    def verse(self, chapter: int, verse: int) -> dict:
        chapter, verse = int(chapter), int(verse)
        for row in self._load_corpus():
            if row["chapter"] == chapter and row["verse"] == verse:
                return dict(row)
        raise KeyError(f"Bhagavad Gita {chapter}.{verse} is not present in the local corpus")

    def _next_row(self, on_date: date | None = None) -> dict:
        corpus = self._load_corpus()
        if not corpus:
            raise RuntimeError("gita corpus is empty")
        progress = self._load_progress()
        today = (on_date or date.today()).isoformat()
        completed = set(str(x) for x in progress.get("completed") or [])
        if progress.get("last_date") == today and progress.get("last_key"):
            for row in corpus:
                if self._key(row) == progress["last_key"]:
                    return dict(row)
        for row in corpus:
            if self._key(row) not in completed:
                return dict(row)
        return dict(corpus[0])

    def lesson_prompt(self, row: dict, language: str = "or", depth: str = "deep") -> str:
        lang = str(language or "or").strip().lower()
        if lang not in self.LANGUAGES:
            raise ValueError("language must be one of: or, hi, en")
        depth = str(depth or "deep").strip().lower()
        if depth not in {"brief", "deep"}:
            raise ValueError("depth must be brief or deep")
        return f"""You are KRISHNA's GITA-GYAN teacher speaking to Partha.
Explain Bhagavad Gita {row['chapter']}.{row['verse']} in natural {self.LANGUAGES[lang]}.
Canonical Sanskrit (do not modify it):
{row['sanskrit']}

Transliteration:
{row.get('transliteration','')}

Trusted short summary:
{row.get('summary_en','')}

Rules:
- Never alter or invent the Sanskrit verse.
- Clearly separate literal meaning, deeper interpretation, and practical application.
- Explain important Sanskrit terms when useful.
- Do not present one philosophical school as the only possible interpretation when traditions differ.
- Do not claim supernatural certainty or that a personal life event has one divinely mandated answer.
- Preserve Partha's agency.
- Depth: {depth}.
- End with one short reflective question.
"""

    def daily_lesson(
        self,
        language: str | None = None,
        depth: str = "deep",
        explain: Callable[[str], str] | None = None,
        on_date: date | None = None,
        mark_complete: bool = True,
    ) -> dict:
        progress = self._load_progress()
        lang = str(language or progress.get("preferred_language") or "or").strip().lower()
        if lang not in self.LANGUAGES:
            raise ValueError("language must be one of: or, hi, en")
        row = self._next_row(on_date)
        prompt = self.lesson_prompt(row, lang, depth)
        explanation = None
        if explain is not None:
            explanation = str(explain(prompt) or "").strip() or None

        today = (on_date or date.today()).isoformat()
        key = self._key(row)
        if mark_complete:
            completed = [str(x) for x in progress.get("completed") or []]
            if key not in completed:
                completed.append(key)
            progress.update({
                "completed": completed,
                "last_date": today,
                "last_key": key,
                "preferred_language": lang,
            })
            self._save_progress(progress)

        status = self.status()
        return {
            "reference": f"Bhagavad Gita {key}",
            "chapter": row["chapter"],
            "verse": row["verse"],
            "sanskrit": row["sanskrit"],
            "transliteration": row.get("transliteration"),
            "trusted_summary_en": row.get("summary_en"),
            "source": row.get("source"),
            "language": lang,
            "depth": depth,
            "explanation": explanation,
            "speech_text": explanation or row["sanskrit"],
            "avatar_state": "WISDOM",
            "avatar_activity": "wisdom",
            "reflection_enabled": True,
            "marked_complete": bool(mark_complete),
            "corpus_complete": status["corpus_complete"],
            "corpus_sha256": status["corpus_sha256"],
        }

    def revise(self, limit: int = 7) -> list[dict]:
        limit = max(1, min(30, int(limit)))
        progress = self._load_progress()
        completed = list(dict.fromkeys(str(x) for x in progress.get("completed") or []))
        wanted = set(completed[-limit:])
        return [
            {
                "reference": f"Bhagavad Gita {self._key(row)}",
                "chapter": row["chapter"],
                "verse": row["verse"],
                "sanskrit": row["sanskrit"],
                "transliteration": row.get("transliteration"),
                "trusted_summary_en": row.get("summary_en"),
                "source": row.get("source"),
            }
            for row in self._load_corpus()
            if self._key(row) in wanted
        ]
