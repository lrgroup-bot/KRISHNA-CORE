from __future__ import annotations

from .contracts import LEGACY_ACTION_MAP,RetryPolicy,WorkflowNode


class WorkflowGraph:
    """Small n8n-inspired DAG contract without importing the n8n runtime."""

    TARGETS={"action","job"}

    def __init__(self,steps):
        self.nodes=self._normalize(steps)
        self.by_id={x.id:x for x in self.nodes}
        self.order=self._topological_order()

    @classmethod
    def _normalize(cls,steps):
        if not isinstance(steps,list) or not steps:
            raise ValueError("workflow requires at least one step")
        rows=[];seen=set();previous=None
        for idx,raw in enumerate(steps,1):
            if not isinstance(raw,dict):raise ValueError("workflow step must be an object")
            node_id=str(raw.get("id") or f"step-{idx}").strip()
            if not node_id or node_id in seen:raise ValueError("workflow step ids must be unique")
            seen.add(node_id)
            action=str(raw.get("action") or "").strip()
            action=LEGACY_ACTION_MAP.get(action,action)
            if not action:raise ValueError(f"{node_id}: action is required")
            dispatch=str(raw.get("dispatch") or "action").strip().lower()
            if dispatch not in cls.TARGETS:raise ValueError(f"{node_id}: dispatch must be action or job")
            explicit="depends_on" in raw
            deps=raw.get("depends_on") or []
            if isinstance(deps,str):deps=[deps]
            deps=tuple(str(x).strip() for x in deps if str(x).strip())
            if not explicit and previous:deps=(previous,)
            payload=dict(raw.get("payload") or {})
            # Preserve legacy NARAD fields as action payload.
            for key in ("topic","provider","url","operation","credential_ref"):
                if key in raw and key not in payload:payload[key]=raw.get(key)
            retry=RetryPolicy.from_value(raw.get("retry"))
            rows.append(WorkflowNode(
                node_id,action,dispatch,deps,payload,retry,bool(raw.get("continue_on_error",False)),
            ))
            previous=node_id
        ids={x.id for x in rows}
        for node in rows:
            missing=[x for x in node.depends_on if x not in ids]
            if missing:raise ValueError(f"{node.id}: missing dependency {missing[0]}")
            if node.id in node.depends_on:raise ValueError(f"{node.id}: self dependency is not allowed")
        return rows

    def _topological_order(self):
        incoming={n.id:set(n.depends_on) for n in self.nodes}
        outgoing={n.id:set() for n in self.nodes}
        for node in self.nodes:
            for dep in node.depends_on:outgoing[dep].add(node.id)
        ready=[n.id for n in self.nodes if not incoming[n.id]]
        order=[]
        while ready:
            current=ready.pop(0);order.append(current)
            for child in sorted(outgoing[current]):
                incoming[child].discard(current)
                if not incoming[child] and child not in ready and child not in order:ready.append(child)
        if len(order)!=len(self.nodes):raise ValueError("workflow graph contains a cycle")
        return order

    def normalized_steps(self):return [self.by_id[x].as_dict() for x in self.order]
