"""Public-business research normalization.

Collection is delegated to approved providers/APIs. This module stores only
public business facts and does not harvest personal/private credentials.
"""
from __future__ import annotations

class BusinessResearch:
    ALLOWED=("name","category","address","website","public_phone","public_email","latitude","longitude","source")
    def normalize(self,row):
        row=dict(row or {})
        return {k:row.get(k) for k in self.ALLOWED if row.get(k) not in (None,"")}
    def batch(self,rows):
        clean=[self.normalize(x) for x in rows]
        clean=[x for x in clean if x.get("name")]
        return {"businesses":clean,"count":len(clean),"personal_data_harvesting":False,
                "credential_collection":False}
