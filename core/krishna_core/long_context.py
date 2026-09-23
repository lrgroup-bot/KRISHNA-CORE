from __future__ import annotations

"""KRISHNA long-context reliability, retrieval and bounded recursive-context tools.

The module is deliberately dependency-light. Model execution is injected by the
caller so tests remain deterministic and the production orchestrator can enforce
local-only/privacy routing.
"""

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import math
import re
import threading
import time
from typing import Callable, Iterable


_WORD = re.compile(r"[a-z0-9][a-z0-9_+.-]{1,}", re.I)


def _terms(value: str) -> list[str]:
    return [x.lower() for x in _WORD.findall(str(value or "")) if len(x) > 1]


def _ngrams(value: str, n: int = 3) -> set[str]:
    text = re.sub(r"\s+", " ", str(value or "").lower()).strip()
    if not text:
        return set()
    if len(text) <= n:
        return {text}
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def _cosine(a: Iterable[float], b: Iterable[float]) -> float:
    av = list(a)
    bv = list(b)
    if not av or not bv or len(av) != len(bv):
        return 0.0
    dot = sum(x * y for x, y in zip(av, bv))
    na = math.sqrt(sum(x * x for x in av))
    nb = math.sqrt(sum(x * x for x in bv))
    return dot / (na * nb) if na and nb else 0.0


class HybridRAG:
    """Project-scoped hybrid retrieval behind Gyan-Bhandar.

    Retrieval combines lexical overlap, fuzzy character similarity, optional dense
    embeddings, verification/confidence signals and ContextGovernor selection.
    Gyan-Bhandar remains the canonical memory authority.
    """

    def __init__(self, gyan, context_governor, embedder: Callable[[str], list[float]] | None = None):
        self.gyan = gyan
        self.context = context_governor
        self.embedder = embedder

    @staticmethod
    def _lexical_score(query: str, text: str) -> float:
        q = _terms(query)
        d = _terms(text)
        if not q or not d:
            return 0.0
        qs, ds = set(q), set(d)
        overlap = len(qs & ds)
        return overlap / max(1, len(qs))

    @staticmethod
    def _fuzzy_score(query: str, text: str) -> float:
        q = _ngrams(query)
        d = _ngrams(text)
        if not q or not d:
            return 0.0
        return len(q & d) / max(1, len(q | d))

    def query(
        self,
        project: str,
        query: str,
        *,
        limit: int = 12,
        candidate_limit: int = 200,
        verified_only: bool = False,
        memory_kind: str | None = None,
    ) -> dict:
        rows = self.gyan.recall(
            project, None, max(limit, candidate_limit), verified_only, memory_kind, False
        )
        query_vec = None
        if self.embedder:
            try:
                query_vec = self.embedder(query)
            except Exception:
                query_vec = None

        scored = []
        for row in rows:
            text = f"{row.get('topic', '')}\n{row.get('lesson', '')}"
            lexical = self._lexical_score(query, text)
            fuzzy = self._fuzzy_score(query, text)
            dense = 0.0
            dense_ok = False
            if query_vec is not None:
                try:
                    dense = _cosine(query_vec, self.embedder(text))
                    dense_ok = True
                except Exception:
                    dense = 0.0
            verified = row.get("status") == "verified"
            confidence = max(0.0, min(float(row.get("confidence") or 0.0), 1.0))
            relevance = 0.56 * lexical + 0.18 * fuzzy + 0.16 * dense
            relevance += 0.07 if verified else 0.0
            relevance += 0.03 * confidence
            scored.append(
                {
                    **row,
                    "retrieval": {
                        "score": round(relevance, 6),
                        "lexical": round(lexical, 6),
                        "fuzzy": round(fuzzy, 6),
                        "dense": round(dense, 6),
                        "dense_used": dense_ok,
                    },
                }
            )

        scored.sort(
            key=lambda x: (
                x["retrieval"]["score"],
                x.get("status") == "verified",
                float(x.get("confidence") or 0.0),
            ),
            reverse=True,
        )
        candidates = scored[: max(limit * 4, limit)]
        governed = self.context.select(
            [
                {
                    "text": (
                        f"[{x.get('status', 'candidate').upper()}]"
                        f"[{x.get('memory_kind', 'semantic')}] "
                        f"{x.get('topic')}: {x.get('lesson')}"
                    ),
                    "verified": x.get("status") == "verified",
                    "score": x["retrieval"]["score"],
                    "fingerprint": x.get("fingerprint"),
                    "source": x.get("source"),
                    "provenance": x.get("provenance") or {},
                    "retrieval": x["retrieval"],
                }
                for x in candidates
            ]
        )
        governed = governed[:limit]
        return {
            "project": project,
            "query": query,
            "mode": "hybrid_dense" if query_vec is not None else "hybrid_lexical_fuzzy",
            "candidate_count": len(rows),
            "count": len(governed),
            "items": governed,
            "policy": "project-scoped retrieval; verified/confident evidence is preferred but relevance remains explicit",
        }


@dataclass
class RecursiveBudget:
    max_depth: int = 3
    max_calls: int = 12
    chunk_chars: int = 6000
    top_k: int = 4

    def normalized(self) -> "RecursiveBudget":
        return RecursiveBudget(
            max_depth=max(1, min(int(self.max_depth), 8)),
            max_calls=max(1, min(int(self.max_calls), 64)),
            chunk_chars=max(1000, min(int(self.chunk_chars), 32000)),
            top_k=max(1, min(int(self.top_k), 12)),
        )


class RecursiveContextEngine:
    """Bounded RLM-style context exploration.

    Large context remains outside the worker model. KRISHNA selects promising
    regions, asks bounded sub-calls, then synthesizes evidence. No unbounded
    recursion, no hidden filesystem/tool authority, and cycle fingerprints stop
    duplicate work.
    """

    def __init__(self):
        self.last_run = None

    @staticmethod
    def _chunks(text: str, chunk_chars: int) -> list[dict]:
        raw = str(text or "")
        if not raw:
            return []
        chunks = []
        total = max(1, len(raw))
        start = 0
        index = 0
        while start < len(raw):
            end = min(len(raw), start + chunk_chars)
            # Prefer paragraph/newline boundary when reasonably close.
            if end < len(raw):
                boundary = raw.rfind("\n", start + chunk_chars // 2, end)
                if boundary > start:
                    end = boundary + 1
            piece = raw[start:end]
            chunks.append(
                {
                    "index": index,
                    "start": start,
                    "end": end,
                    "position": round(start / total, 6),
                    "text": piece,
                }
            )
            index += 1
            start = end
        return chunks

    @staticmethod
    def _score(question: str, text: str) -> float:
        q = set(_terms(question))
        d = set(_terms(text))
        lexical = len(q & d) / max(1, len(q)) if q and d else 0.0
        qg = _ngrams(question)
        dg = _ngrams(text)
        fuzzy = len(qg & dg) / max(1, len(qg | dg)) if qg and dg else 0.0
        return 0.8 * lexical + 0.2 * fuzzy

    def solve(
        self,
        question: str,
        context: str,
        worker: Callable[[str], str],
        *,
        budget: RecursiveBudget | None = None,
    ) -> dict:
        b = (budget or RecursiveBudget()).normalized()
        state = {"calls": 0, "visited": set(), "evidence": []}

        def call(prompt: str) -> str:
            if state["calls"] >= b.max_calls:
                return "[BUDGET_EXHAUSTED]"
            digest = hashlib.sha256(prompt.encode("utf-8", "ignore")).hexdigest()
            if digest in state["visited"]:
                return "[DUPLICATE_CALL_BLOCKED]"
            state["visited"].add(digest)
            state["calls"] += 1
            return str(worker(prompt) or "")

        def explore(text: str, depth: int) -> str:
            if depth >= b.max_depth or len(text) <= b.chunk_chars:
                prompt = (
                    "Answer the question using only the supplied context. "
                    "If unsupported, say INSUFFICIENT_EVIDENCE.\n\n"
                    f"QUESTION:\n{question}\n\nCONTEXT:\n{text}"
                )
                answer = call(prompt)
                state["evidence"].append(
                    {"depth": depth, "chars": len(text), "answer": answer[:4000]}
                )
                return answer

            chunks = self._chunks(text, b.chunk_chars)
            ranked = sorted(
                ((self._score(question, x["text"]), x) for x in chunks),
                key=lambda pair: pair[0],
                reverse=True,
            )[: b.top_k]
            partials = []
            for score, chunk in ranked:
                if state["calls"] >= b.max_calls:
                    break
                answer = explore(chunk["text"], depth + 1)
                partials.append(
                    f"[chunk={chunk['index']} position={chunk['position']} score={score:.4f}]\n{answer}"
                )
            if not partials:
                return "INSUFFICIENT_EVIDENCE"
            if state["calls"] >= b.max_calls:
                return "\n\n".join(partials)
            synthesis = call(
                "Synthesize a final answer from these bounded sub-results. "
                "Do not invent facts not present in the sub-results.\n\n"
                f"QUESTION:\n{question}\n\nSUB_RESULTS:\n" + "\n\n".join(partials)
            )
            return synthesis

        answer = explore(str(context or ""), 0)
        out = {
            "question": question,
            "answer": answer,
            "calls": state["calls"],
            "max_calls": b.max_calls,
            "max_depth": b.max_depth,
            "chunk_chars": b.chunk_chars,
            "evidence": state["evidence"],
            "cycle_guard_entries": len(state["visited"]),
            "bounded": state["calls"] <= b.max_calls,
        }
        self.last_run = out
        return out


class LongContextLab:
    """Needle, lost-in-the-middle and context-rot benchmark generator."""

    VERSION = "long-context-lab-v1"

    @staticmethod
    def _filler(chars: int) -> str:
        sentence = (
            "KRISHNA benchmark filler records ordinary telemetry, project notes, "
            "verification history and unrelated observations. "
        )
        repeats = max(1, chars // len(sentence) + 2)
        return (sentence * repeats)[:chars]

    @classmethod
    def needle_case(cls, context_chars: int, position: float, case_id: str) -> dict:
        size = max(1000, int(context_chars))
        pos = max(0.0, min(float(position), 1.0))
        token = "KRN-" + hashlib.sha256(
            f"{size}:{pos:.6f}:{case_id}".encode("utf-8")
        ).hexdigest()[:20].upper()
        needle = f"\nCRITICAL TEST FACT: KRISHNA verification code is {token}.\n"
        filler_chars = max(0, size - len(needle))
        before_len = int(filler_chars * pos)
        after_len = filler_chars - before_len
        context = cls._filler(before_len) + needle + cls._filler(after_len)
        prompt = (
            "Read the complete context. Return only the KRISHNA verification code.\n\n"
            f"CONTEXT:\n{context}\n\nQUESTION: What is the KRISHNA verification code?"
        )
        return {
            "id": case_id,
            "context_chars": len(context),
            "position": pos,
            "token": token,
            "prompt": prompt,
        }

    def needle_matrix(
        self,
        runner: Callable[[str], str],
        *,
        context_sizes: Iterable[int] = (4000, 8000, 16000, 32000),
        positions: Iterable[float] = (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0),
    ) -> dict:
        results = []
        for size in context_sizes:
            for position in positions:
                case_id = f"niah-{size}-{int(float(position) * 100):03d}"
                case = self.needle_case(int(size), float(position), case_id)
                started = time.perf_counter()
                try:
                    output = str(runner(case["prompt"]) or "")
                    error = None
                except Exception as exc:
                    output = ""
                    error = f"{type(exc).__name__}: {exc}"
                elapsed = int((time.perf_counter() - started) * 1000)
                passed = case["token"].lower() in output.lower()
                results.append(
                    {
                        "case": case_id,
                        "context_chars": case["context_chars"],
                        "position": case["position"],
                        "passed": passed,
                        "latency_ms": elapsed,
                        "output_excerpt": output[:300],
                        "error": error,
                    }
                )
        return self._summarize(results)

    @staticmethod
    def _summarize(results: list[dict]) -> dict:
        total = len(results)
        passed = sum(1 for x in results if x.get("passed"))
        by_size = {}
        by_position = {}
        for row in results:
            by_size.setdefault(str(row["context_chars"]), []).append(row)
            bucket = f"{int(round(float(row['position']) * 100)):03d}%"
            by_position.setdefault(bucket, []).append(row)

        def rates(groups):
            return {
                key: round(sum(1 for x in rows if x.get("passed")) / max(1, len(rows)), 4)
                for key, rows in groups.items()
            }

        size_rates = rates(by_size)
        position_rates = rates(by_position)
        middle = [
            x for x in results if 0.40 <= float(x.get("position") or 0.0) <= 0.60
        ]
        edges = [
            x
            for x in results
            if float(x.get("position") or 0.0) <= 0.10
            or float(x.get("position") or 0.0) >= 0.90
        ]
        middle_rate = (
            sum(1 for x in middle if x.get("passed")) / len(middle) if middle else 0.0
        )
        edge_rate = (
            sum(1 for x in edges if x.get("passed")) / len(edges) if edges else 0.0
        )
        smallest_key = min(by_size, key=lambda x: int(x)) if by_size else None
        largest_key = max(by_size, key=lambda x: int(x)) if by_size else None
        smallest = size_rates.get(smallest_key, 0.0) if smallest_key else 0.0
        largest = size_rates.get(largest_key, 0.0) if largest_key else 0.0
        return {
            "version": LongContextLab.VERSION,
            "passed": total > 0 and passed == total,
            "passed_cases": passed,
            "total_cases": total,
            "pass_rate": round(passed / total, 4) if total else 0.0,
            "by_context_chars": size_rates,
            "by_position": position_rates,
            "lost_in_middle": {
                "edge_pass_rate": round(edge_rate, 4),
                "middle_pass_rate": round(middle_rate, 4),
                "middle_gap": round(edge_rate - middle_rate, 4),
            },
            "context_rot": {
                "smallest_context_pass_rate": round(smallest, 4),
                "largest_context_pass_rate": round(largest, 4),
                "degradation": round(smallest - largest, 4),
            },
            "results": results,
        }


class WeeklyLongContextScheduler:
    """Persistent seven-day scheduler for the model-backed NIAH regression."""

    def __init__(
        self,
        state_root: str | Path,
        run_suite: Callable[[], dict],
        interval_seconds: int = 7 * 24 * 60 * 60,
        poll_seconds: int = 3600,
    ):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "weekly-long-context.json"
        self.run_suite = run_suite
        self.interval_seconds = max(24 * 60 * 60, int(interval_seconds))
        self.poll_seconds = max(300, int(poll_seconds))
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.RLock()
        self.state = {
            "version": 1,
            "last_run_at": None,
            "next_run_at": time.time() + self.interval_seconds,
            "last_result": None,
            "last_error": None,
            "run_count": 0,
        }
        self._load()

    def _load(self):
        if not self.path.is_file():
            self._save()
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self.state.update(raw)
        except Exception as exc:
            self.state["last_error"] = f"state_load:{type(exc).__name__}: {exc}"

    def _save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def due(self, now: float | None = None) -> bool:
        current = float(now or time.time())
        return current >= float(self.state.get("next_run_at") or 0.0)

    def run_once(self, force: bool = False) -> dict:
        with self._lock:
            now = time.time()
            if not force and not self.due(now):
                return {
                    "status": "not_due",
                    "next_run_at": self.state.get("next_run_at"),
                }
            try:
                result = self.run_suite()
                self.state["last_result"] = result
                self.state["last_error"] = None
                status = "completed"
            except Exception as exc:
                result = None
                self.state["last_error"] = f"{type(exc).__name__}: {exc}"
                status = "error"
            self.state["last_run_at"] = now
            skipped = isinstance(result, dict) and str(result.get("status") or "").startswith("skipped")
            retry_soon = status == "error" or skipped
            self.state["next_run_at"] = now + (self.poll_seconds if retry_soon else self.interval_seconds)
            self.state["run_count"] = int(self.state.get("run_count") or 0) + 1
            self._save()
            return {
                "status": status,
                "last_run_at": now,
                "next_run_at": self.state["next_run_at"],
                "result": result,
                "error": self.state.get("last_error"),
            }

    def start(self) -> dict:
        if self._thread and self._thread.is_alive():
            return self.status()
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="krishna-long-context-weekly", daemon=True
        )
        self._thread.start()
        return self.status()

    def stop(self) -> dict:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        return self.status()

    def _loop(self):
        while not self._stop.is_set():
            if self.due():
                self.run_once()
            if self._stop.wait(self.poll_seconds):
                break

    def status(self) -> dict:
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "interval_seconds": self.interval_seconds,
            "poll_seconds": self.poll_seconds,
            **self.state,
            "policy": "weekly model-backed NIAH runs through KRISHNA local-only routing",
        }
