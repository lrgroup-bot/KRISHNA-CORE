from __future__ import annotations
from collections import defaultdict
class CompetenceFeedback:
    def summarize(self,receipts):
        stats=defaultdict(lambda:{"attempts":0,"passed":0})
        for r in receipts:
            key=f"{r.get('agent','unknown')}::{r.get('domain','general')}";stats[key]["attempts"]+=1;stats[key]["passed"]+=int(bool(r.get("passed")))
        out={}
        for k,v in stats.items():out[k]={**v,"success_rate":round(v["passed"]/v["attempts"],4) if v["attempts"] else 0}
        return out
    def weaknesses(self,receipts,threshold=.75,min_attempts=3):
        s=self.summarize(receipts);return {k:v for k,v in s.items() if v["attempts"]>=min_attempts and v["success_rate"]<threshold}
