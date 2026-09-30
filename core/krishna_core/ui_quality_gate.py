from __future__ import annotations
class UIQualityGate:
 REQUIRED=("desktop","mobile","functional","accessibility","console","network","performance")
 @classmethod
 def judge(cls,evidence):
  missing=[x for x in cls.REQUIRED if x not in evidence]
  failed=[x for x in cls.REQUIRED if x in evidence and not bool(evidence[x])]
  return {"passed":not missing and not failed,"missing":missing,"failed":failed,
          "package_allowed":not missing and not failed}
