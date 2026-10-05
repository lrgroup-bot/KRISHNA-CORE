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
            known_seeds = [name for name in seed_list if name in self._nodes]
            unknown_seeds = [name for name in seed_list if name not in self._nodes]
            graph_nodes = set(self._nodes)
            referenced_nodes = set(self._edges)
            referenced_nodes.update(
                target for pairs in self._edges.values() for _, target in pairs
            )
            dangling_nodes = sorted(referenced_nodes - graph_nodes)
            total_referenced = len(referenced_nodes)
            classified_ratio = (
                (total_referenced - len(dangling_nodes)) / total_referenced
                if total_referenced else 1.0
            )
            seed_ratio = len(known_seeds) / len(seed_list) if seed_list else 0.0
            confidence = seed_ratio * classified_ratio
            if unknown_seeds:
                confidence_label = "INSUFFICIENT"
            elif dangling_nodes:
                confidence_label = "PARTIAL"
            else:
                confidence_label = "GRAPH_COMPLETE_FOR_KNOWN_EDGES"
            return {
                "seeds": seed_list,
                "known_seeds": known_seeds,
                "unknown_seeds": unknown_seeds,
                "depth": max(0, int(depth)),
                "impacted": impacted,
                "tests": tests,
                "impact_count": len(impacted),
                "test_count": len(tests),
                "graph_evidence": {
                    "referenced_nodes": total_referenced,
                    "registered_nodes": len(graph_nodes),
                    "dangling_nodes": dangling_nodes,
                    "classified_ratio": round(classified_ratio, 6),
                },
                "confidence": round(confidence, 6),
                "confidence_label": confidence_label,
                "safe_to_claim_no_impact": (
                    not unknown_seeds and not dangling_nodes and not impacted
                ),
                "evidence_policy": (
                    "proven graph edges only; zero discovered impact is not proof of safety "
                    "when seeds or referenced nodes are unknown"
                ),
            }


    def cycles(self, relations: Iterable[str] | None = None) -> dict:
        """Return deterministic dependency cycles with edge evidence."""
        with self._lock:
            allowed = None if relations is None else {str(x) for x in relations}
            adjacency: Dict[str, List[Tuple[str, str]]] = {}
            for source, pairs in self._edges.items():
                for relation, target in pairs:
                    if allowed is None or relation in allowed:
                        adjacency.setdefault(source, []).append((relation, target))

            found: dict[tuple[str, ...], dict] = {}
            visiting: list[str] = []
            active: set[str] = set()
            visited: set[str] = set()

            def canonical(nodes: list[str]) -> tuple[str, ...]:
                body = nodes[:-1]
                rotations = [tuple(body[i:] + body[:i]) for i in range(len(body))]
                return min(rotations)

            def walk(node: str):
                if node in visited:
                    return
                active.add(node); visiting.append(node)
                for relation, target in sorted(adjacency.get(node, [])):
                    if target in active:
                        start = visiting.index(target)
                        cycle_nodes = visiting[start:] + [target]
                        key = canonical(cycle_nodes)
                        edges = []
                        for left, right in zip(cycle_nodes, cycle_nodes[1:]):
                            rel = next(
                                rel for rel, candidate in sorted(adjacency.get(left, []))
                                if candidate == right
                            )
                            edges.append({"source": left, "relation": rel, "target": right})
                        found[key] = {"nodes": cycle_nodes, "edges": edges}
                    elif target not in visited:
                        walk(target)
                visiting.pop(); active.discard(node); visited.add(node)

            nodes = set(adjacency)
            nodes.update(target for pairs in adjacency.values() for _, target in pairs)
            for node in sorted(nodes):
                walk(node)
            rows = [found[key] for key in sorted(found)]
            return {
                "cycle_count": len(rows),
                "cycles": rows,
                "relations": sorted(allowed) if allowed is not None else None,
                "passed": not rows,
                "evidence_policy": "reported cycles require a closed path of proven graph edges",
            }

    def check_architecture_rules(self, rules: Iterable[dict]) -> dict:
        """Evaluate explicit dependency-boundary rules against proven graph edges.

        Supported rules:
        - deny: source_kind/source_prefix -> target_kind/target_prefix
        - allow_only: matching sources may depend only on listed target kinds/prefixes

        Unknown nodes are not silently classified; they are reported separately.
        """
        with self._lock:
            normalized = [dict(rule) for rule in rules]
            violations = []
            unknown_edges = []

            def matches(node: ProjectNode | None, name: str, rule: dict, side: str) -> bool:
                kind = rule.get(f"{side}_kind")
                prefix = rule.get(f"{side}_prefix")
                if kind is not None and (node is None or node.kind != str(kind)):
                    return False
                if prefix is not None and not name.startswith(str(prefix)):
                    return False
                return kind is not None or prefix is not None

            for source, pairs in sorted(self._edges.items()):
                source_node = self._nodes.get(source)
                for relation, target in sorted(pairs):
                    target_node = self._nodes.get(target)
                    edge = {"source": source, "relation": relation, "target": target}
                    if source_node is None or target_node is None:
                        unknown_edges.append({
                            **edge,
                            "missing_nodes": [
                                name for name, node in ((source, source_node), (target, target_node))
                                if node is None
                            ],
                        })
                    for index, rule in enumerate(normalized):
                        mode = str(rule.get("mode") or "deny").lower()
                        if not matches(source_node, source, rule, "source"):
                            continue
                        if mode == "deny":
                            if matches(target_node, target, rule, "target"):
                                violations.append({
                                    "rule_index": index,
                                    "rule": rule,
                                    "edge": edge,
                                    "reason": "forbidden_dependency",
                                })
                        elif mode == "allow_only":
                            allowed_kinds = {str(x) for x in rule.get("target_kinds") or []}
                            allowed_prefixes = tuple(str(x) for x in rule.get("target_prefixes") or [])
                            allowed = (
                                (target_node is not None and target_node.kind in allowed_kinds)
                                or (bool(allowed_prefixes) and target.startswith(allowed_prefixes))
                            )
                            if not allowed:
                                violations.append({
                                    "rule_index": index,
                                    "rule": rule,
                                    "edge": edge,
                                    "reason": "dependency_outside_allowlist",
                                })
                        else:
                            raise ValueError(f"unsupported architecture rule mode: {mode}")

            return {
                "passed": not violations and not unknown_edges,
                "rule_count": len(normalized),
                "violations": violations,
                "violation_count": len(violations),
                "unknown_edges": unknown_edges,
                "unknown_edge_count": len(unknown_edges),
                "policy": "fail closed: violations and unclassified graph edges require review",
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
