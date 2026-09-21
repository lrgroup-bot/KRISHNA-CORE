from __future__ import annotations
import time
class BenchmarkLab:
    def run(self,name,cases,runner):
        results=[]; start=time.perf_counter()
        for i,case in enumerate(cases or []):
            try:
                out=runner(case); ok=bool(out.get('ok',out is not False)) if isinstance(out,dict) else bool(out)
                results.append({"case":i+1,"passed":ok,"result":out})
            except Exception as exc: results.append({"case":i+1,"passed":False,"error":f"{type(exc).__name__}: {exc}"})
        passed=sum(1 for x in results if x['passed']); total=len(results)
        return {"name":name,"passed":total>0 and passed==total,"passed_cases":passed,"total_cases":total,"pass_rate":(passed/total if total else 0.0),"duration_ms":int((time.perf_counter()-start)*1000),"results":results}
