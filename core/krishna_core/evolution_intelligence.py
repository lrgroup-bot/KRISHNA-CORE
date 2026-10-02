from __future__ import annotations
class EvolutionIntelligence:
    def compare(self,before,after):
        bn={n["id"] for n in before.get("nodes",[])};an={n["id"] for n in after.get("nodes",[])}
        be={(e["source"],e["target"],e["kind"]) for e in before.get("edges",[])};ae={(e["source"],e["target"],e["kind"]) for e in after.get("edges",[])}
        return {"symbols_added":sorted(an-bn),"symbols_removed":sorted(bn-an),"dependencies_added":sorted(ae-be),"dependencies_removed":sorted(be-ae)}
    def test_gaps(self,index,critical_files=()):
        tests=set(index.get("test_files",[]));critical=set(critical_files)
        return {"critical_files":sorted(critical),"test_files":sorted(tests),"uncovered_candidates":sorted(critical) if not tests else [],"heuristic":True}
