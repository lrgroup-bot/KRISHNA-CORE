from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, asdict
from itertools import combinations
from typing import Dict, Iterable, List, Set, Tuple
import math
import threading


@dataclass(frozen=True)
class ProjectNode:
    name: str
    kind: str
    metadata: dict


class ProjectGraph:
    """Thread-safe lightweight dependency/relationship graph for KRISHNA projects.

    This remains the canonical in-process project graph. Impact and history
    intelligence are deliberately methods on this graph rather than a second
    graph/database so KRISHNA has one architecture source of truth.
    """

    def __init__(self):
        self._nodes: Dict[str, ProjectNode] = {}
        self._edges: Dict[str, Set[Tuple[str, str]]] = {}
        self._lock = threading.RLock()

    def upsert_node(self, name: str, kind: str = "component", metadata: dict | None = None) -> None:
        with self._lock:
            self._nodes[name] = ProjectNode(name=name, kind=kind, metadata=metadata or {})

    def link(self, source: str, target: str, relation: str = "depends_on") -> None:
        with self._lock:
            self._edges.setdefault(source, set()).add((relation, target))

    def neighbors(self, name: str) -> List[dict]:
        with self._lock:
            return [
                {"relation": rel, "target": target}
                for rel, target in sorted(self._edges.get(name, set()))
            ]

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "nodes": [asdict(v) for _, v in sorted(self._nodes.items())],
                "edges": [
                    {"source": src, "relation": rel, "target": target}
                    for src, pairs in sorted(self._edges.items())
                    for rel, target in sorted(pairs)
                ],
            }

    def relevant(self, seeds: List[str], depth: int = 2) -> dict:
        with self._lock:
            seen = set(seeds)
            frontier = list(seeds)
            for _ in range(max(depth, 0)):
                nxt = []
                for node in frontier:
                    for _, target in self._edges.get(node, set()):
                        if target not in seen:
                            seen.add(target)
                            nxt.append(target)
                    for src, pairs in self._edges.items():
                        if any(target == node for _, target in pairs) and src not in seen:
                            seen.add(src)
                            nxt.append(src)
                frontier = nxt
            return {
                "nodes": [asdict(self._nodes[n]) for n in sorted(seen) if n in self._nodes],
                "edges": [
                    {"source": src, "relation": rel, "target": target}
                    for src, pairs in self._edges.items()
                    for rel, target in pairs
                    if src in seen and target in seen
                ],
            }

    def impact(self, seeds: Iterable[str], depth: int = 4) -> dict:
        """Rank nodes that can be affected by changing *seeds*.

        Dependency edges are stored as source -> target ("source depends on
        target"), therefore blast radius walks the graph in reverse. Every
        result includes the concrete dependency path that justifies it; KRISHNA
        never invents an impact edge. Test nodes are identified separately so
        verification can select relevant tests without scanning the whole repo.
        """
        with self._lock:
            seed_list = sorted({str(x) for x in seeds if str(x)})
            reverse: Dict[str, List[Tuple[str, str]]] = {}
            for source, pairs in self._edges.items():
                for relation, target in pairs:
                    reverse.setdefault(target, []).append((source, relation))

            queue = deque((seed, 0, [seed], []) for seed in seed_list)
            best: dict[str, dict] = {}
            while queue:
                node, distance, path, evidence = queue.popleft()
                if distance >= max(0, int(depth)):
                    continue
                for dependent, relation in sorted(reverse.get(node, [])):
                    next_distance = distance + 1
                    edge = {"source": dependent, "relation": relation, "target": node}
                    next_path = path + [dependent]
                    next_evidence = evidence + [edge]
                    current = best.get(dependent)
                    if current is not None and current["distance"] <= next_distance:
                        continue
                    best[dependent] = {
                        "name": dependent,
                        "distance": next_distance,
                        "path": next_path,
                        "evidence": next_evidence,
                    }
                    queue.append((dependent, next_distance, next_path, next_evidence))

            for seed in seed_list:
                best.pop(seed, None)

            impacted = []
            tests = []
            for name, row in best.items():
                node = self._nodes.get(name)
                kind = node.kind if node else "unknown"
                metadata = dict(node.metadata) if node else {}
                inbound = len(reverse.get(name, []))
                outbound = len(self._edges.get(name, set()))
                score = (1.0 / row["distance"]) + 0.05 * (inbound + outbound)
                item = {
                    **row,
                    "kind": kind,
                    "metadata": metadata,
                    "score": round(score, 6),
                }
                is_test = kind.lower() in {"test", "tests"} or bool(metadata.get("test"))
                (tests if is_test else impacted).append(item)

            order = lambda x: (-x["score"], x["distance"], x["name"])
            impacted.sort(key=order)
            tests.sort(key=order)
            return {
                "seeds": seed_list,
                "depth": max(0, int(depth)),
                "impacted": impacted,
                "tests": tests,
                "impact_count": len(impacted),
                "test_count": len(tests),
                "evidence_policy": "proven graph edges only; missing relationships remain unknown",
            }

    def change_hotspots(self, commits: Iterable[Iterable[str]], limit: int = 50) -> dict:
        """Score files/components that repeatedly change with other files.

        The caller supplies commit file-sets from the existing Git/history
        boundary. No Git command is executed here. The score combines observed
        churn, observed co-change partners and current static graph degree.
        Counts and partners are returned as evidence so the score is auditable.
        """
        with self._lock:
            churn: Counter[str] = Counter()
            pairs: Counter[Tuple[str, str]] = Counter()
            commit_count = 0
            for raw in commits:
                files = sorted({str(x) for x in raw if str(x)})
                if not files:
                    continue
                commit_count += 1
                churn.update(files)
                pairs.update(combinations(files, 2))

            partners: dict[str, Counter[str]] = {}
            for (left, right), count in pairs.items():
                partners.setdefault(left, Counter())[right] += count
                partners.setdefault(right, Counter())[left] += count

            rows = []
            for name, changes in churn.items():
                co = partners.get(name, Counter())
                co_weight = sum(co.values())
                static_degree = len(self._edges.get(name, set()))
                static_degree += sum(
                    1 for values in self._edges.values()
                    if any(target == name for _, target in values)
                )
                # Native KRISHNA score: history is primary; static degree only
                # increases priority modestly. Raw evidence remains visible.
                score = changes * (1.0 + math.log1p(co_weight) + 0.25 * math.log1p(static_degree))
                rows.append({
                    "name": name,
                    "score": round(score, 6),
                    "changes": changes,
                    "cochange_weight": co_weight,
                    "cochange_partners": [
                        {"name": partner, "count": count}
                        for partner, count in co.most_common(10)
                    ],
                    "static_degree": static_degree,
                })
            rows.sort(key=lambda x: (-x["score"], -x["changes"], x["name"]))
            return {
                "commit_count": commit_count,
                "hotspots": rows[:max(0, int(limit))],
                "method": "KRISHNA native churn + co-change evidence + modest static-degree weighting",
                "mutated": False,
            }
