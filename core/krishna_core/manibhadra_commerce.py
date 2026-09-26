from __future__ import annotations

from dataclasses import dataclass,asdict
from typing import Any
import re

PROHIBITED_SEO_WORDS={"best","cheapest","amazing","guaranteed","number 1","#1"}


@dataclass(frozen=True)
class CommerceOpportunity:
    product:str
    score:float
    demand:float
    margin:float
    competition:float
    return_risk:float
    reasons:tuple[str,...]
    def as_dict(self):
        row=asdict(self);row["reasons"]=list(self.reasons);return row


class ManibhadraCommerce:
    """KRISHNA commerce specialist: product research -> supplier -> listing -> sale.

    No fake reviews, fake ratings, trademark abuse, scraping bypasses or platform
    policy evasion. External commitments and marketplace writes require approval.
    """

    PLATFORM_CAPABILITIES={
        "amazon":{
            "mode":"official_api",
            "adapter":"Amazon SP-API",
            "listing_api":True,"orders_api":True,"inventory_api":True,
            "title_max_2026":75,"item_highlights_max_2026":125,
        },
        "flipkart":{
            "mode":"official_api",
            "adapter":"Flipkart Marketplace Seller API v3",
            "listing_api":True,"orders_api":True,"inventory_api":True,
        },
        "meesho":{
            "mode":"browser_assisted_until_verified_api",
            "adapter":"Garudanetra/authorized seller portal",
            "listing_api":False,"orders_api":False,"inventory_api":False,
        },
        "alibaba":{
            "mode":"research_ready_waiting_for_connection",
            "adapter":"Alibaba.com Open API / Seller Central after owner connection",
            "market_type":"B2B_wholesale_global",
            "listing_api":True,"orders_api":True,"rfq":True,
            "connection_required_for_writes":True,
            "paid_membership_may_be_required":True,
            "selling_enabled_under_zero_spend":False,
            "research_enabled_under_zero_spend":True,
        },
    }

    def evaluate(self,product:str,*,demand:float,margin:float,competition:float,return_risk:float)->dict[str,Any]:
        vals=[float(x) for x in (demand,margin,competition,return_risk)]
        if any(x<0 or x>1 for x in vals):raise ValueError("signals must be between 0 and 1")
        score=0.35*vals[0]+0.35*vals[1]+0.20*(1-vals[2])+0.10*(1-vals[3])
        reasons=[]
        if demand>=0.7:reasons.append("strong demand")
        if margin>=0.3:reasons.append("healthy margin")
        if competition>=0.8:reasons.append("high competition")
        if return_risk>=0.4:reasons.append("return risk")
        return CommerceOpportunity(product,round(score,4),*vals,tuple(reasons)).as_dict()

    def supplier_offer(self,product:str,*,seller_name:str="",commission_percent:float|None=None)->dict:
        commission="" if commission_percent is None else f" Proposed commission: {float(commission_percent):g}%."
        text=(
            f"I represent a sales channel for {product}. With your permission, I can market and sell the product "
            f"through approved marketplaces. You remain responsible for accurate product information, stock and "
            f"delivery to the confirmed customer address; I will handle listing optimization, demand generation "
            f"and customer/order coordination under agreed terms.{commission}"
        )
        return {"product":product,"supplier":seller_name or None,"proposal":text,"requires_owner_approval_to_send":True}

    @staticmethod
    def _clean_keywords(keywords):
        out=[]
        for raw in keywords or []:
            word=" ".join(str(raw).strip().lower().split())
            if not word or word in PROHIBITED_SEO_WORDS:continue
            if word not in out:out.append(word)
        return out

    def listing_plan(self,platform:str,product:dict,keywords:list[str]|None=None)->dict:
        p=str(platform or "").strip().lower()
        if p not in self.PLATFORM_CAPABILITIES:raise ValueError("unsupported marketplace")
        name=str(product.get("name") or "").strip()
        if not name:raise ValueError("product name is required")
        brand=str(product.get("brand") or "").strip()
        features=[str(x).strip() for x in product.get("features") or [] if str(x).strip()]
        keys=self._clean_keywords(keywords)
        base=" ".join(x for x in (brand,name) if x).strip()
        if p=="amazon":
            title=base[:75].rstrip()
            highlight="; ".join(features)[:125].rstrip()
            search_terms=" ".join(keys)[:249].strip()
            return {
                "platform":p,"title":title,"item_highlights":highlight,"search_terms":search_terms,
                "rules":{"title_max":75,"item_highlights_max":125,"subjective_claims":False},
                "publish_requires_owner_approval":True,
            }
        return {
            "platform":p,"title":base,"features":features,"keywords":keys,
            "mode":self.PLATFORM_CAPABILITIES[p]["mode"],
            "publish_requires_owner_approval":True,
        }

    def zero_spend_strategy(self):
        return {
            "mode":"RECEIVE_ONLY",
            "allowed":[
                "affiliate/referral commissions",
                "finder fees",
                "supplier-paid fulfillment/reseller commissions",
                "free organic social traffic",
                "free SEO",
                "free self-hosted storefront on existing hardware",
                "free marketplace/research channels with no seller fee or paid membership",
            ],
            "blocked":[
                "inventory purchase","supplier prepayment","paid ads","paid boosts","paid leads",
                "seller memberships","listing fees","subscriptions","paid APIs","paid hosting",
                "courier/shipping payment","domain purchase","software credits",
            ],
            "owner_approval_can_override":False,
        }

    def status(self):
        return {
            "name":"MANIBHADRA","role":"commerce/sourcing/marketplace specialist",
            "platforms":self.PLATFORM_CAPABILITIES,
            "forbidden":["fake reviews","fake ratings","trademark stuffing","platform policy evasion","unauthorized price/order changes"],
            "external_commitments_require_owner_approval":True,
            "zero_spend":self.zero_spend_strategy(),
        }
