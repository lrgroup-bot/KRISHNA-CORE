from __future__ import annotations
class ProjectTruthGraph:
    """Evidence graph joining requirements, architecture, code, tests and runtime receipts."""
    def __init__(self):self.nodes={};self.edges=[]
    def add(self,node_id,kind,**data):
        self.nodes[str(node_id)]={"id":str(node_id),"kind":str(kind),**data};return self.nodes[str(node_id)]
    def link(self,source,target,relation,evidence=None):
        if source not in self.nodes or target not in self.nodes:raise KeyError("truth graph endpoints must exist")
        row={"source":source,"target":target,"relation":relation,"evidence":list(evidence or [])};self.edges.append(row);return row
    def trace(self,node_id):
        seen={str(node_id)};front=list(seen)
        while front:
            x=front.pop(0)
            for e in self.edges:
                if e["source"]==x and e["target"] not in seen:seen.add(e["target"]);front.append(e["target"])
                if e["target"]==x and e["source"] not in seen:seen.add(e["source"]);front.append(e["source"])
        return {"nodes":[self.nodes[x] for x in seen if x in self.nodes],"edges":[e for e in self.edges if e["source"] in seen and e["target"] in seen]}
    def requirement_status(self,requirement_id):
        g=self.trace(requirement_id);kinds={n["kind"] for n in g["nodes"]}
        return {"requirement":requirement_id,"implemented":"code" in kinds,"tested":"test" in kinds,"runtime_verified":"runtime_evidence" in kinds,"complete":{"code","test","runtime_evidence"}.issubset(kinds)}
