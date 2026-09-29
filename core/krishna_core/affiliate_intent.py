from __future__ import annotations

from dataclasses import dataclass,asdict
from typing import Any
from urllib.parse import urlparse,parse_qsl,urlencode,urlunparse
import re

DISCLOSURE="Affiliate link — we may earn a commission if you buy through this link."


@dataclass(frozen=True)
class IntentSignal:
    source:str
    text:str
    public_or_consented:bool
    kind:str="text"
    def as_dict(self):return asdict(self)


class AffiliateIntentEngine:
    """Public/consented intent -> product -> compliant referral-link plan.

    It never reads private browsing/watch history without explicit user authorization.
    It does not hide affiliate tracking or bypass marketplace channel rules.
    """

    CHANNELS={
        "amazon":{
            "allowed":{"approved_website","approved_social","approved_mobile_app"},
            "blocked_default":{"email","whatsapp","direct_message","offline","sms"},
            "disclosure_required":True,
            "generator":"tagged_url_or_official_link_tool",
        },
        "flipkart":{
            "allowed":{"approved_website","approved_mobile_app"},
            "blocked_default":{"email","whatsapp","direct_message","offline","sms"},
            "disclosure_required":True,
            "generator":"official_affiliate_deep_link",
        },
        "alibaba":{
            "allowed":{"approved_website","approved_social"},
            "blocked_default":{"email","whatsapp","direct_message","offline","sms"},
            "disclosure_required":True,
            "generator":"verified_affiliate_or_campaign_link_after_connection",
        },
    }

    def intent_summary(self,signals:list[dict[str,Any]])->dict[str,Any]:
        accepted=[];rejected=[]
        for row in signals or []:
            sig=IntentSignal(
                str(row.get("source") or "unknown"),
                str(row.get("text") or "").strip(),
                bool(row.get("public_or_consented",False)),
                str(row.get("kind") or "text"),
            )
            if not sig.text:continue
            if not sig.public_or_consented:
                rejected.append({**sig.as_dict(),"reason":"private/unconsented signal"})
            else:
                accepted.append(sig.as_dict())
        words=[]
        for row in accepted:
            for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}",row["text"].lower()):
                if token not in {"the","and","for","with","that","this","want","need","looking"}:
                    words.append(token)
        freq={}
        for w in words:freq[w]=freq.get(w,0)+1
        top=sorted(freq.items(),key=lambda x:(-x[1],x[0]))[:20]
        return {
            "accepted_signals":accepted,
            "rejected_signals":rejected,
            "keywords":[x[0] for x in top],
            "ready_for_product_match":bool(accepted),
            "privacy_rule":"public or explicitly consented signals only",
        }

    def channel_policy(self,provider:str,channel:str,*,account_override:bool=False)->dict[str,Any]:
        p=str(provider or "").strip().lower();c=str(channel or "").strip().lower()
        if p not in self.CHANNELS:raise ValueError("unsupported affiliate provider")
        spec=self.CHANNELS[p]
        allowed=c in spec["allowed"]
        if c in spec["blocked_default"] and account_override:
            allowed=True
        return {
            "provider":p,"channel":c,"allowed":allowed,
            "account_specific_override_used":bool(account_override and c in spec["blocked_default"]),
            "disclosure_required":spec["disclosure_required"],
            "generator":spec["generator"],
            "reason":"approved channel" if allowed else "channel blocked by default until program/account rules explicitly allow it",
        }

    @staticmethod
    def amazon_special_link(product_url:str,tracking_id:str)->str:
        url=str(product_url or "").strip();tag=str(tracking_id or "").strip()
        if not url or not tag:raise ValueError("product_url and tracking_id are required")
        parsed=urlparse(url)
        host=(parsed.hostname or "").lower()
        if host not in {"amazon.in","www.amazon.in"} and not host.endswith(".amazon.in"):
            raise ValueError("Amazon India affiliate link must target amazon.in")
        if not re.fullmatch(r"[A-Za-z0-9_-]{2,64}",tag):
            raise ValueError("invalid tracking_id")
        query=dict(parse_qsl(parsed.query,keep_blank_values=True));query["tag"]=tag
        return urlunparse((parsed.scheme or "https",parsed.netloc,parsed.path,parsed.params,urlencode(query),parsed.fragment))

    def referral_plan(
        self,*,provider:str,channel:str,product_name:str,product_url:str="",
        tracking_id:str="",official_deep_link:str="",account_override:bool=False,
        estimated_price:float|None=None,commission_rate:float|None=None,
    )->dict[str,Any]:
        policy=self.channel_policy(provider,channel,account_override=account_override)
        if not policy["allowed"]:
            return {
                "ready":False,"provider":provider,"channel":channel,"product":product_name,
                "policy":policy,"reason":"distribution channel not permitted by current policy",
                "connection_state":"WAITING_FOR_CONNECTION_OR_CHANNEL_APPROVAL",
            }
        p=str(provider).lower()
        link=""
        if p=="amazon":
            if not tracking_id:
                return {"ready":False,"provider":p,"product":product_name,"policy":policy,
                        "reason":"Amazon tracking ID is not connected","connection_state":"WAITING_FOR_CONNECTION"}
            link=self.amazon_special_link(product_url,tracking_id)
        else:
            link=str(official_deep_link or "").strip()
            if not link:
                return {"ready":False,"provider":p,"product":product_name,"policy":policy,
                        "reason":"official affiliate/deep link must be generated after account connection",
                        "connection_state":"WAITING_FOR_CONNECTION"}
        commission=None
        if estimated_price is not None and commission_rate is not None:
            price=float(estimated_price);rate=float(commission_rate)
            if price>=0 and 0<=rate<=1:commission=round(price*rate,2)
        return {
            "ready":True,"provider":p,"channel":channel,"product":product_name,
            "link":link,"disclosure":DISCLOSURE,"estimated_commission":commission,
            "policy":policy,"connection_state":"CONNECTED_LINK_READY",
            "send_or_publish_requires_superhuman_policy":True,
        }

    def status(self):
        return {
            "component":"MANIBHADRA Affiliate Intent Engine",
            "channels":self.CHANNELS,
            "connection_state":"WAITING_FOR_CONNECTION",
            "private_browsing_history_monitoring":False,
            "public_or_consented_interest_signals":True,
            "affiliate_disclosure_required":True,
        }
