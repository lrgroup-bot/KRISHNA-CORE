from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

READ_ONLY={"read","search","summarize","classify","draft","analyze","recommend","preview"}
HIGH_IMPACT={
    "send","reply","publish","post","delete","trash","bulk_message","price_change",
    "ad_spend","refund","cancel_order","account_setting","security_setting","supplier_commitment",
}
NEVER_UNATTENDED={"permanent_delete","credential_change","ownership_transfer"}
NEVER_ALLOWED_SPEND={
    "payment","bank_transfer","purchase","purchase_inventory","supplier_prepay","supplier_deposit",
    "subscription","membership","seller_membership","paid_api","api_credit","credit_purchase",
    "ad_spend","boost","sponsor","paid_lead","listing_fee","platform_fee_payment",
    "shipping_payment","courier_payment","domain_purchase","hosting_purchase","software_purchase",
    "bid_payment","commission_payment",
}


@dataclass(frozen=True)
class OperatorDecision:
    operation:str
    allowed:bool
    requires_owner_approval:bool
    reason:str
    risk:str
    def as_dict(self): return asdict(self)


class SuperhumanOperatorPolicy:
    """Owner-first action policy for email/social/commerce delegation."""

    def __init__(self, approved_automation:dict[str,bool]|None=None):
        self.approved_automation={str(k):bool(v) for k,v in (approved_automation or {}).items()}

    def decide(self,operation:str,*,approved:bool=False,confidence:float|None=None)->dict[str,Any]:
        op=str(operation or "").strip().lower()
        if not op: raise ValueError("operation is required")
        if op in READ_ONLY:
            return OperatorDecision(op,True,False,"read/draft/analysis operation","low").as_dict()
        if op in NEVER_ALLOWED_SPEND:
            return OperatorDecision(op,False,False,"zero-spend policy forbids outgoing money even with approval","critical").as_dict()
        if op in NEVER_UNATTENDED:
            return OperatorDecision(op,bool(approved),True,"irreversible/sensitive action requires owner approval","critical").as_dict()
        if op in HIGH_IMPACT:
            preapproved=self.approved_automation.get(op,False)
            if preapproved and op=="trash" and confidence is not None and float(confidence)>=0.995:
                return OperatorDecision(op,True,False,"owner pre-approved high-confidence trash automation","medium").as_dict()
            return OperatorDecision(op,bool(approved),True,"external or state-changing action requires owner approval","high").as_dict()
        return OperatorDecision(op,bool(approved),True,"unknown mutation defaults to owner approval","high").as_dict()

    def status(self):
        return {
            "component":"KRISHNA Superhuman Operator Policy",
            "owner_controlled":True,
            "read_draft_without_prompt":sorted(READ_ONLY),
            "approval_required":sorted(HIGH_IMPACT),
            "never_unattended":sorted(NEVER_UNATTENDED),
            "never_allowed_spend":sorted(NEVER_ALLOWED_SPEND),
            "zero_spend":True,
            "approved_automation":dict(self.approved_automation),
        }
