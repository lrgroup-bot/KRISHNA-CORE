from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Callable, Iterable


class GitaGyan:
    """Daily Bhagavad Gita learning runtime for KRISHNA.

    Canonical Sanskrit stays separate from generated commentary. The runtime is
    offline-first: it uses a local corpus when available and never treats model
    commentary as scripture text.
    """

    VERSION = "gita-gyan-v1"
    EXPECTED_VERSE_COUNT = 700
    CHAPTER_VERSE_COUNTS = (
        47, 72, 43, 42, 29, 47, 30, 28, 34,
        42, 55, 20, 34, 27, 20, 24, 28, 78,
    )
    VERSE_NUMBERING = "700-verse recension; some editions include an additional opening verse in chapter 13 and total 701"
    LANGUAGES = {"or": "odia", "hi": "hindi", "en": "english"}

    SEED = (
        {
            "chapter": 2,
            "verse": 47,
            "sanskrit": "कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।\nमा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि॥",
            "transliteration": "karmaṇy-evādhikāras te mā phaleṣu kadācana; mā karma-phala-hetur bhūr mā te saṅgo 'stv akarmaṇi",
            "summary_en": "Focus on responsible action without making attachment to outcomes the basis of action or inaction.",
        },
        {
            "chapter": 2,
            "verse": 48,
            "sanskrit": "योगस्थः कुरु कर्माणि सङ्गं त्यक्त्वा धनञ्जय।\nसिद्ध्यसिद्ध्योः समो भूत्वा समत्वं योग उच्यते॥",
            "transliteration": "yoga-sthaḥ kuru karmāṇi saṅgaṁ tyaktvā dhanañjaya; siddhy-asiddhyoḥ samo bhūtvā samatvaṁ yoga ucyate",
            "summary_en": "Act with steadiness, giving up attachment and maintaining balance in success and failure.",
        },
        {
            "chapter": 4,
            "verse": 7,
            "sanskrit": "यदा यदा हि धर्मस्य ग्लानिर्भवति भारत।\nअभ्युत्थानमधर्मस्य तदात्मानं सृजाम्यहम्॥",
            "transliteration": "yadā yadā hi dharmasya glānir bhavati bhārata; abhyutthānam adharmasya tadātmānaṁ sṛjāmy aham",
            "summary_en": "The verse describes divine manifestation when dharma declines and adharma rises.",
        },
        {
            "chapter": 4,
            "verse": 8,
            "sanskrit": "परित्राणाय साधूनां विनाशाय च दुष्कृताम्।\nधर्मसंस्थापनार्थाय सम्भवामि युगे युगे॥",
            "transliteration": "paritrāṇāya sādhūnāṁ vināśāya ca duṣkṛtām; dharma-saṁsthāpanārthāya sambhavāmi yuge yuge",
            "summary_en": "The verse speaks of protecting the good, restraining wrongdoing, and re-establishing dharma.",
        },
        {
            "chapter": 6,
            "verse": 5,
            "sanskrit": "उद्धरेदात्मनात्मानं नात्मानमवसादयेत्।\nआत्मैव ह्यात्मनो बन्धुरात्मैव रिपुरात्मनः॥",
            "transliteration": "uddhared ātmanātmānaṁ nātmānam avasādayet; ātmaiva hy ātmano bandhur ātmaiva ripur ātmanaḥ",
            "summary_en": "One should elevate oneself rather than degrade oneself; the mind/self can become one's ally or obstacle.",
        },
        {
            "chapter": 18,
            "verse": 63,
            "sanskrit": "इति ते ज्ञानमाख्यातं गुह्याद्गुह्यतरं मया।\nविमृश्यैतदशेषेण यथेच्छसि तथा कुरु॥",
            "transliteration": "iti te jñānam ākhyātaṁ guhyād guhyataraṁ mayā; vimṛśyaitad aśeṣeṇa yathecchasi tathā kuru",
            "summary_en": "After teaching, Krishna asks the listener to reflect fully and then choose how to act.",
        },
    )

    def __init__(self, state_root: str | Path, corpus_path: str | Path | None = None):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.progress_path = self.root / "progress.json"
        self.corpus_path = Path(corpus_path) if corpus_path else self.root / "bhagavad_gita.json"
        self._seed_if_missing()

    def _seed_if_missing(self) -> None:
        if not self.corpus_path.exists():
            self.corpus_path.write_text(
                json.dumps(list(self.SEED), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def _load_corpus(self) -> list[dict]:
        try:
            raw = json.loads(self.corpus_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"gita corpus unavailable: {exc}") from exc
        if not isinstance(raw, list):
            raise RuntimeError("gita corpus must be a JSON array")
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

    def status(self) -> dict:
        corpus = self._load_corpus()
        progress = self._load_progress()
        return {
            "version": self.VERSION,
            "available_verses": len(corpus),
            "expected_verses": self.EXPECTED_VERSE_COUNT,
            "verse_numbering": self.VERSE_NUMBERING,
            "corpus_complete": len(corpus) == self.EXPECTED_VERSE_COUNT,
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
        self.corpus_path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        corpus = self._load_corpus()
        return {"imported": len(corpus), "complete": len(corpus) == self.EXPECTED_VERSE_COUNT}

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

        return {
            "reference": f"Bhagavad Gita {key}",
            "chapter": row["chapter"],
            "verse": row["verse"],
            "sanskrit": row["sanskrit"],
            "transliteration": row.get("transliteration"),
            "trusted_summary_en": row.get("summary_en"),
            "language": lang,
            "depth": depth,
            "explanation": explanation,
            "speech_text": explanation or row["sanskrit"],
            "avatar_state": "WISDOM",
            "avatar_activity": "wisdom",
            "reflection_enabled": True,
            "marked_complete": bool(mark_complete),
            "corpus_complete": self.status()["corpus_complete"],
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
            }
            for row in self._load_corpus()
            if self._key(row) in wanted
        ]
