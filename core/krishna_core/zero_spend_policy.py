from __future__ import annotations

from dataclasses import dataclass,asdict
from typing import Any


ZERO_SPEND_FORBIDDEN={
    "payment","bank_transfer","purchase","purchase_inventory","supplier_prepay","supplier_deposit",
    "subscription","membership","seller_membership","paid_api","api_credit","credit_purchase",
    "ad_spend","boost","sponsor","paid_lead","listing_fee","platform_fee_payment",
    "shipping_payment","courier_payment","domain_purchase","hosting_purchase","software_purchase",
    "refund_from_our_funds","bid_payment","commission_payment",
}

RECEIVE_ONLY_ALLOWED={
    "affiliate_commission","referral_fee","customer_payment","seller_payout","marketplace_payout",
    "supplier_commission","finder_fee","service_fee_received","royalty_received",
}


@dataclass(frozen=True)
class MoneyDecision:
    operation:str
    allowed:bool
    direction:str
    reason:str
    hard_block:bool
    def as_dict(self):return asdict(self)


class ZeroSpendPolicy:
    """KRISHNA owner money policy: receive revenue; never initiate spend.

    This is intentionally stricter than an approval gate. Owner approval does not
    override it. A future policy change must be an explicit source-level/config
    change, not a normal action approval.
    """

    def __init__(self):
        self.enabled=True

    def decide(self,operation:str,*,amount:float|None=None,currency:str="INR")->dict[str,Any]:
        op=str(operation or "").strip().lower()
        if not op:raise ValueError("operation is required")
        if amount is not None and float(amount)<0:raise ValueError("amount cannot be negative")
        if op in ZERO_SPEND_FORBIDDEN:
            return MoneyDecision(op,False,"outgoing","zero-spend policy forbids sending money",True).as_dict()
        if op in RECEIVE_ONLY_ALLOWED:
            return MoneyDecision(op,True,"incoming","revenue receipt is permitted",False).as_dict()
        return MoneyDecision(op,False,"unknown","unknown money movement is blocked by default",True).as_dict()

    def plugin_allowed(self,plugin:dict)->dict[str,Any]:
        free=bool(plugin.get("free",False))
        return {
            "plugin_id":plugin.get("id"),
            "allowed":free,
            "reason":"free-only plugin/service" if free else "paid/non-free plugin blocked by zero-spend policy",
            "hard_block":not free,
        }

    def business_model_allowed(self,model:str,*,upfront_cost:float=0.0,recurring_cost:float=0.0,inventory_cost:float=0.0,ad_spend:float=0.0)->dict[str,Any]:
        costs={
            "upfront_cost":float(upfront_cost),
            "recurring_cost":float(recurring_cost),
            "inventory_cost":float(inventory_cost),
            "ad_spend":float(ad_spend),
        }
        allowed=all(v<=0 for v in costs.values())
        return {
            "model":str(model),
            "allowed":allowed,
            "costs":costs,
            "required_structure":"affiliate/referral/commission, supplier-funded fulfillment, or free self-hosted channel",
            "reason":"zero cash outflow" if allowed else "business model requires outgoing spend",
        }

    def status(self):
        return {
            "component":"KRISHNA Zero Spend Policy",
            "enabled":True,
            "rule":"receive money; never send money",
            "currency_agnostic":True,
            "owner_approval_can_override":False,
            "forbidden_operations":sorted(ZERO_SPEND_FORBIDDEN),
            "allowed_inflows":sorted(RECEIVE_ONLY_ALLOWED),
            "platform_fee_deducted_from_proceeds":"blocked by default until explicitly treated as non-outgoing by a future policy change",
        }
