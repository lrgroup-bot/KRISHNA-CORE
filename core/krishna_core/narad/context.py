from __future__ import annotations

import re


_REF=re.compile(r"\$\{([a-zA-Z0-9_.-]+)\}")


def _lookup(path,state):
    cur=state
    for part in str(path).split("."):
        if isinstance(cur,dict) and part in cur:cur=cur[part]
        elif isinstance(cur,list) and part.isdigit() and int(part)<len(cur):cur=cur[int(part)]
        else:raise KeyError(path)
    return cur


def resolve_value(value,state):
    if isinstance(value,dict):return {k:resolve_value(v,state) for k,v in value.items()}
    if isinstance(value,list):return [resolve_value(v,state) for v in value]
    if not isinstance(value,str):return value
    full=_REF.fullmatch(value.strip())
    if full:return _lookup(full.group(1),state)
    def repl(match):
        found=_lookup(match.group(1),state)
        return str(found)
    return _REF.sub(repl,value)


def build_node_payload(node_payload,workflow_input,node_outputs):
    state={"input":dict(workflow_input or {}),"nodes":dict(node_outputs or {})}
    return resolve_value(dict(node_payload or {}),state)
