from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo


class GitaGyan:
    """Local-first Bhagavad Gita daily learning runtime for KRISHNA.

    Canonical scripture data is immutable and bundled separately from generated
    teaching material. Generated Odia/Hindi explanations are cached as derived
    learning aids and are never written back into the canonical verse corpus.
    """

    VERSION = "gita-gyan-v1"
    SUPPORTED_LANGUAGES = {"or": "Odia", "hi": "Hindi"}
    LANGUAGE_ALIASES = {
        "or": "or", "odia": "or", "oriya": "or", "ଓଡ଼ିଆ": "or", "ଓଡିଆ": "or",
        "hi": "hi", "hindi": "hi", "हिंदी": "hi", "हिन्दी": "hi",
    }

    def __init__(self, state_root: str | Path, catalog_path: str | Path | None = None, explainer=None):
        self.state_root = Path(state_root)
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.catalog_path = Path(catalog_path or (Path(__file__).resolve().parent / "data" / "bhagavad_gita_public_domain.json"))
        self.progress_path = self.state_root / "progress.json"
        self.explanation_root = self.state_root / "explanations"
        self.explanation_root.mkdir(parents=True, exist_ok=True)
        self.explainer = explainer
        self._lock = threading.RLock()
        self.load_error = None
        self.catalog = self._load_catalog()
        self.verses = list(self.catalog["verses"])
        self._by_id = {str(row["id"]): row for row in self.verses}
        self._by_ref = {(int(row["chapter"]), int(row["verse"])): row for row in self.verses}
        self._order = {str(row["id"]): idx + 1 for idx, row in enumerate(self.verses)}
        self.state = self._load_progress()

    @staticmethod
    def _atomic_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def _load_catalog(self) -> dict:
        if not self.catalog_path.is_file():
            raise FileNotFoundError(f"Bhagavad Gita catalog not found: {self.catalog_path}")
        raw = json.loads(self.catalog_path.read_text(encoding="utf-8-sig"))
        if not isinstance(raw, dict) or not isinstance(raw.get("verses"), list) or not raw["verses"]:
            raise ValueError("Bhagavad Gita catalog is invalid")
        required = {"id", "chapter", "verse", "sanskrit", "transliteration", "english"}
        seen = set()
        verses = []
        for item in raw["verses"]:
            if not isinstance(item, dict) or not required.issubset(item):
                raise ValueError("Bhagavad Gita catalog verse entry is invalid")
            vid = str(item["id"]).strip()
            ref = (int(item["chapter"]), int(item["verse"]))
            if not vid or vid in seen:
                raise ValueError("Bhagavad Gita catalog contains duplicate/blank verse id")
            seen.add(vid)
            verses.append({
                "id": vid,
                "chapter": ref[0],
                "verse": ref[1],
                "sanskrit": str(item["sanskrit"]).strip(),
                "transliteration": str(item["transliteration"]).strip(),
                "english": str(item["english"]).strip(),
                "translator": str(item.get("translator") or raw.get("primary_translator") or "").strip(),
            })
        verses.sort(key=lambda row: (row["chapter"], row["verse"]))
        out = dict(raw)
        out["verses"] = verses
        return out

    def _default_state(self) -> dict:
        default_language = self._normalize_language(os.getenv("KRISHNA_GITA_LANGUAGE", "or"))
        return {
            "schema": 1,
            "preferred_language": default_language,
            "last_date": None,
            "last_id": None,
            "last_order": 0,
            "cycle": 1,
            "delivered": [],
            "understood": {},
            "questions": [],
            "reviewed": {},
            "updated_at": time.time(),
        }

    def _load_progress(self) -> dict:
        if not self.progress_path.exists():
            return self._default_state()
        try:
            raw = json.loads(self.progress_path.read_text(encoding="utf-8-sig"))
            if not isinstance(raw, dict) or int(raw.get("schema", 0)) != 1:
                raise ValueError("unsupported GITA-GYAN progress schema")
            base = self._default_state()
            base.update(raw)
            base["preferred_language"] = self._normalize_language(base.get("preferred_language"))
            base["delivered"] = [x for x in list(base.get("delivered") or []) if x in self._by_id]
            base["understood"] = {
                str(k): dict(v) for k, v in dict(base.get("understood") or {}).items()
                if str(k) in self._by_id and isinstance(v, dict)
            }
            base["questions"] = [x for x in list(base.get("questions") or []) if isinstance(x, dict)][-500:]
            base["reviewed"] = {
                str(k): float(v) for k, v in dict(base.get("reviewed") or {}).items()
                if str(k) in self._by_id
            }
            self.load_error = None
            return base
        except Exception as exc:
            self.load_error = f"{type(exc).__name__}: {exc}"
            return self._default_state()

    def _healthy(self) -> None:
        if self.load_error:
            raise RuntimeError("GITA-GYAN progress state is unreadable; refusing to overwrite it: " + self.load_error)

    def _save(self) -> None:
        self._healthy()
        self.state["updated_at"] = time.time()
        self._atomic_json(self.progress_path, self.state)

    @classmethod
    def _normalize_language(cls, value) -> str:
        key = str(value or "or").strip().lower()
        if key in cls.LANGUAGE_ALIASES:
            return cls.LANGUAGE_ALIASES[key]
        raise ValueError("GITA-GYAN language must be Odia/or or Hindi/hi")

    @staticmethod
    def _truthy(value, default=False) -> bool:
        if value is None:
            return bool(default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on", "deep"}

    @staticmethod
    def _date_string(value=None) -> str:
        if value is None:
            return date.today().isoformat()
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return date.fromisoformat(str(value)).isoformat()

    def set_language(self, language: str) -> dict:
        lang = self._normalize_language(language)
        with self._lock:
            self._healthy()
            self.state["preferred_language"] = lang
            self._save()
        return {"preferred_language": lang, "name": self.SUPPORTED_LANGUAGES[lang]}

    def _choose_next(self) -> dict:
        delivered = set(self.state.get("delivered") or [])
        for row in self.verses:
            if row["id"] not in delivered:
                return row
        self.state["cycle"] = int(self.state.get("cycle") or 1) + 1
        self.state["delivered"] = []
        return self.verses[0]

    def verse(self, chapter: int, verse: int, language=None, deep=False) -> dict:
        try:
            row = self._by_ref[(int(chapter), int(verse))]
        except (KeyError, TypeError, ValueError):
            raise KeyError(f"Bhagavad Gita verse not found: {chapter}.{verse}")
        return self.lesson_for_id(row["id"], language=language, deep=deep)

    def lesson_for_id(self, verse_id: str, language=None, deep=False) -> dict:
        vid = str(verse_id or "").strip().upper()
        if vid not in self._by_id:
            raise KeyError("Bhagavad Gita verse not found")
        lang = self._normalize_language(language or self.state.get("preferred_language") or "or")
        row = self._by_id[vid]
        lesson = {
            "id": row["id"],
            "chapter": row["chapter"],
            "verse": row["verse"],
            "order": self._order[row["id"]],
            "sanskrit": row["sanskrit"],
            "transliteration": row["transliteration"],
            "public_domain_english": row["english"],
            "translator": row.get("translator"),
            "language": lang,
            "language_name": self.SUPPORTED_LANGUAGES[lang],
            "avatar_state": "WISDOM",
            "canonical_text": True,
            "canonical_text_mutable": False,
            "commentary_is_derived": True,
            "source": {
                "repository": self.catalog.get("source_repository"),
                "source": self.catalog.get("source"),
                "license": self.catalog.get("license"),
                "edition_note": self.catalog.get("edition_note"),
            },
        }
        lesson["explanation"] = self._explanation(row, lang) if self._truthy(deep) else None
        return lesson

    def daily_lesson(self, language=None, deep=True, for_date=None, advance=False) -> dict:
        lang = self._normalize_language(language or self.state.get("preferred_language") or "or")
        day = self._date_string(for_date)
        with self._lock:
            self._healthy()
            if not advance and self.state.get("last_date") == day and self.state.get("last_id") in self._by_id:
                row = self._by_id[self.state["last_id"]]
            else:
                row = self._choose_next()
                if row["id"] not in self.state["delivered"]:
                    self.state["delivered"].append(row["id"])
                self.state["last_date"] = day
                self.state["last_id"] = row["id"]
                self.state["last_order"] = self._order[row["id"]]
                self.state["preferred_language"] = lang
                self._save()
        lesson = self.lesson_for_id(row["id"], language=lang, deep=deep)
        lesson["daily"] = True
        lesson["date"] = day
        lesson["cycle"] = int(self.state.get("cycle") or 1)
        return lesson

    @staticmethod
    def _extract_json(text: str) -> dict:
        raw = str(text or "").strip()
        fence = chr(96) * 3
        if raw.startswith(fence):
            lines = raw.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip().startswith(fence):
                lines = lines[:-1]
            raw = "\n".join(lines).strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("local explainer did not return a JSON object")
        value = json.loads(raw[start:end + 1])
        if not isinstance(value, dict):
            raise ValueError("local explainer JSON root must be an object")
        return value

    def _explanation_prompt(self, row: dict, lang: str) -> str:
        language_name = self.SUPPORTED_LANGUAGES[lang]
        return (
            "You are KRISHNA GITA-GYAN, a careful Bhagavad Gita study teacher. "
            f"Explain the supplied verse in natural {language_name}. "
            "The Sanskrit and supplied public-domain English translation are source material; never alter or invent the Sanskrit. "
            "Keep canonical text separate from interpretation. Do not claim a named philosophical school teaches something unless a source for that school is supplied. "
            "You may present clearly labelled textual, devotional, action-oriented, and contemplative lenses as interpretive lenses, not as exclusive truth. "
            "Do not give fatalistic advice; explain karma-yoga as compatible with planning, responsibility, and learning from outcomes when relevant. "
            "Return ONLY valid JSON with keys: literal_meaning, context, deep_explanation, practical_application, reflection_question, perspectives. "
            "perspectives must be a JSON array of objects with keys label and explanation. "
            f"\nVERSE ID: {row['id']}\nSANSKRIT:\n{row['sanskrit']}"
            f"\nTRANSLITERATION:\n{row['transliteration']}"
            f"\nPUBLIC-DOMAIN ENGLISH ({row.get('translator') or 'translator'}):\n{row['english']}"
        )

    def _fallback_explanation(self, row: dict, lang: str, error: str) -> dict:
        message = (
            "ସ୍ଥାନୀୟ ଗଭୀର ବ୍ୟାଖ୍ୟା ମଡେଲ୍ ଏବେ ଉପଲବ୍ଧ ନାହିଁ। ସଂସ୍କୃତ ଶ୍ଲୋକ ଓ ସାର୍ବଜନିକ-ଡୋମେନ୍ ଇଂରାଜୀ ଅର୍ଥ ଉପଲବ୍ଧ ଅଛି।"
            if lang == "or" else
            "स्थानीय गहन व्याख्या मॉडल अभी उपलब्ध नहीं है। संस्कृत श्लोक और सार्वजनिक-डोमेन अंग्रेज़ी अर्थ उपलब्ध हैं।"
        )
        return {
            "language": lang,
            "literal_meaning": row["english"],
            "literal_meaning_language": "en",
            "context": message,
            "deep_explanation": "",
            "practical_application": "",
            "reflection_question": "",
            "perspectives": [],
            "degraded": True,
            "error": error,
            "source_boundary": "canonical Sanskrit/public-domain translation remain available; derived explanation unavailable",
        }

    def _explanation(self, row: dict, lang: str) -> dict:
        cache = self.explanation_root / f"{row['id']}.{lang}.json"
        if cache.is_file():
            try:
                value = json.loads(cache.read_text(encoding="utf-8-sig"))
                if isinstance(value, dict) and value.get("verse_id") == row["id"] and value.get("language") == lang:
                    return value
            except Exception:
                pass
        if not self.explainer:
            return self._fallback_explanation(row, lang, "local explainer is not configured")
        try:
            raw = self.explainer(self._explanation_prompt(row, lang))
            value = self._extract_json(raw)
            perspectives = value.get("perspectives")
            if not isinstance(perspectives, list):
                perspectives = []
            clean = {
                "verse_id": row["id"],
                "language": lang,
                "literal_meaning": str(value.get("literal_meaning") or "").strip(),
                "context": str(value.get("context") or "").strip(),
                "deep_explanation": str(value.get("deep_explanation") or "").strip(),
                "practical_application": str(value.get("practical_application") or "").strip(),
                "reflection_question": str(value.get("reflection_question") or "").strip(),
                "perspectives": [
                    {"label": str(x.get("label") or "").strip(), "explanation": str(x.get("explanation") or "").strip()}
                    for x in perspectives if isinstance(x, dict)
                    if str(x.get("label") or "").strip() or str(x.get("explanation") or "").strip()
                ][:8],
                "degraded": False,
                "generated_at": time.time(),
                "source_boundary": "derived teaching aid; canonical Sanskrit is stored separately and unchanged",
            }
            if not clean["literal_meaning"] or not clean["deep_explanation"]:
                raise ValueError("local explainer returned incomplete teaching JSON")
            self._atomic_json(cache, clean)
            return clean
        except Exception as exc:
            return self._fallback_explanation(row, lang, f"{type(exc).__name__}: {exc}")

    def mark_understood(self, verse_id: str, understood=True, note=None) -> dict:
        vid = str(verse_id or "").strip().upper()
        if vid not in self._by_id:
            raise KeyError("Bhagavad Gita verse not found")
        with self._lock:
            self._healthy()
            self.state["understood"][vid] = {
                "understood": bool(understood),
                "note": str(note or "").strip()[:4000],
                "at": time.time(),
            }
            self._save()
            return dict(self.state["understood"][vid], verse_id=vid)

    def add_question(self, verse_id: str, question: str) -> dict:
        vid = str(verse_id or "").strip().upper()
        q = str(question or "").strip()
        if vid not in self._by_id:
            raise KeyError("Bhagavad Gita verse not found")
        if not q:
            raise ValueError("question is required")
        row = {"verse_id": vid, "question": q[:8000], "at": time.time()}
        with self._lock:
            self._healthy()
            self.state["questions"].append(row)
            self.state["questions"] = self.state["questions"][-500:]
            self._save()
        return row

    def revision(self, language=None, limit=7, deep=False) -> dict:
        lang = self._normalize_language(language or self.state.get("preferred_language") or "or")
        try:
            n = max(1, min(int(limit), 30))
        except (TypeError, ValueError):
            raise ValueError("revision limit must be an integer")
        delivered = [vid for vid in self.state.get("delivered") or [] if vid in self._by_id]
        selected = list(reversed(delivered[-n:]))
        now = time.time()
        lessons = [self.lesson_for_id(vid, language=lang, deep=deep) for vid in selected]
        with self._lock:
            if selected:
                self._healthy()
                for vid in selected:
                    self.state["reviewed"][vid] = now
                self._save()
        return {
            "language": lang,
            "count": len(lessons),
            "lessons": lessons,
            "reflection": "Recall the Sanskrit idea first, then explain it in your own words before reading KRISHNA's explanation.",
        }

    def progress(self) -> dict:
        delivered = list(self.state.get("delivered") or [])
        understood = dict(self.state.get("understood") or {})
        understood_true = sum(1 for row in understood.values() if row.get("understood"))
        total = len(self.verses)
        return {
            "preferred_language": self.state.get("preferred_language"),
            "last_date": self.state.get("last_date"),
            "last_id": self.state.get("last_id"),
            "cycle": int(self.state.get("cycle") or 1),
            "delivered_count": len(delivered),
            "understood_count": understood_true,
            "question_count": len(self.state.get("questions") or []),
            "total_verses_in_bundled_edition": total,
            "delivery_percent": round((len(delivered) / total) * 100, 2) if total else 0.0,
            "load_error": self.load_error,
        }

    def status(self) -> dict:
        chapters = sorted({int(x["chapter"]) for x in self.verses})
        return {
            "module": "GITA-GYAN",
            "version": self.VERSION,
            "mode": "local-first",
            "verses_loaded": len(self.verses),
            "chapters": chapters,
            "languages": dict(self.SUPPORTED_LANGUAGES),
            "preferred_language": self.state.get("preferred_language"),
            "canonical_scripture_separate_from_commentary": True,
            "generated_commentary_cached_locally": True,
            "named_tradition_attribution_requires_source": True,
            "avatar_state": "WISDOM",
            "source": {
                "repository": self.catalog.get("source_repository"),
                "source": self.catalog.get("source"),
                "license": self.catalog.get("license"),
                "primary_translator": self.catalog.get("primary_translator"),
                "edition_note": self.catalog.get("edition_note"),
            },
            "progress": self.progress(),
        }

    def interpret_command(self, text: str, language=None) -> dict:
        raw = str(text or "").strip()
        if not raw:
            raise ValueError("command text is required")
        low = raw.lower()
        lang = self._normalize_language(language or self.state.get("preferred_language") or "or")
        if any(token in low for token in ("odia", "oriya")) or "ଓଡ" in raw:
            lang = "or"
        if "hindi" in low or "हिं" in raw:
            lang = "hi"
        deep = any(token in low for token in ("deep", "deeply", "detail", "ଗଭୀର", "विस्तार", "गहर"))
        revision = any(token in low for token in ("revise", "revision", "yesterday", "previous", "ପୁଣି", "पुनर", "दोहरा"))
        chapter_match = re.search(r"(?:chapter|adhyay|अध्याय)\s*(\d{1,2})", low)
        verse_match = re.search(r"(?:verse|sloka|shloka|श्लोक)\s*(\d{1,3})", low)
        if chapter_match and verse_match:
            return {
                "intent": "verse",
                "chapter": int(chapter_match.group(1)),
                "verse": int(verse_match.group(1)),
                "language": lang,
                "deep": deep,
            }
        if revision:
            return {"intent": "revision", "language": lang, "deep": deep}
        return {"intent": "daily", "language": lang, "deep": True}


class GitaDailyScheduler:
    """Small in-process once-per-local-day trigger for GITA-GYAN."""

    def __init__(
        self,
        callback,
        daily_time="07:30",
        timezone_name="Asia/Kolkata",
        poll_seconds=30,
        enabled=True,
    ):
        self.callback = callback
        self.daily_time = self._validate_time(daily_time)
        self.timezone_name = str(timezone_name or "Asia/Kolkata")
        self.timezone = ZoneInfo(self.timezone_name)
        self.poll_seconds = max(5, int(poll_seconds))
        self.enabled = bool(enabled)
        self.last_run_date = None
        self.last_run_at = None
        self.last_result = None
        self.last_error = None
        self.run_count = 0
        self._thread = None
        self._stop = threading.Event()

    @staticmethod
    def _validate_time(value) -> str:
        raw = str(value or "").strip()
        match = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", raw)
        if not match:
            raise ValueError("KRISHNA_GITA_DAILY_TIME must be HH:MM in 24-hour format")
        return raw

    def run_due(self, now=None) -> dict:
        if not self.enabled:
            return {"status": "disabled"}
        current = now
        if current is None:
            current = datetime.now(self.timezone)
        elif current.tzinfo is None:
            current = current.replace(tzinfo=self.timezone)
        else:
            current = current.astimezone(self.timezone)
        day = current.date().isoformat()
        if self.last_run_date == day:
            return {"status": "already_ran", "date": day}
        hour, minute = [int(x) for x in self.daily_time.split(":")]
        if (current.hour, current.minute) < (hour, minute):
            return {"status": "not_due", "date": day, "daily_time": self.daily_time}
        try:
            result = self.callback()
            self.last_run_date = day
            self.last_run_at = current.isoformat()
            self.last_result = result
            self.last_error = None
            self.run_count += 1
            return {"status": "completed", "date": day, "result": result}
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            return {"status": "failed", "date": day, "error": self.last_error}

    def _loop(self):
        while not self._stop.wait(self.poll_seconds):
            self.run_due()

    def start(self):
        if not self.enabled:
            return self.status()
        if self._thread and self._thread.is_alive():
            return self.status()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="krishna-gita-daily", daemon=True)
        self._thread.start()
        self.run_due()
        return self.status()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        return self.status()

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "running": bool(self._thread and self._thread.is_alive()),
            "daily_time": self.daily_time,
            "timezone": self.timezone_name,
            "poll_seconds": self.poll_seconds,
            "last_run_date": self.last_run_date,
            "last_run_at": self.last_run_at,
            "run_count": self.run_count,
            "last_error": self.last_error,
        }
