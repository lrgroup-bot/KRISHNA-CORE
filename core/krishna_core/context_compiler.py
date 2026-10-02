from __future__ import annotations
class ContextCompiler:
    """Build bounded engineering context from deterministic project truth."""
    def compile(self,task,*,code_index,truth_graph=None,requirements=(),failures=(),max_nodes=40):
        q=str(task or "");matches=[n for n in code_index.get("nodes",[]) if any(t.lower() in (n["name"]+" "+n["file"]).lower() for t in q.split() if len(t)>2)]
        return {"task":q,"code":matches[:max_nodes],"requirements":list(requirements)[:20],"failures":list(failures)[-10:],"truth":truth_graph.trace(requirements[0]) if truth_graph and requirements else None,"index_digest":code_index.get("digest")}
