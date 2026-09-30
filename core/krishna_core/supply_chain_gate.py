from __future__ import annotations
class SupplyChainGate:
 """Release metadata gate for hash/SBOM/provenance/attestation evidence."""
 REQUIRED=("source_commit","sha256","sbom","provenance","attestation")
 @classmethod
 def verify(cls,receipt):
  missing=[x for x in cls.REQUIRED if not receipt.get(x)]
  return {"passed":not missing,"missing":missing,"install_allowed":not missing}
