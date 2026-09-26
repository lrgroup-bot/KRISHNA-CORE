from __future__ import annotations

from dataclasses import dataclass,asdict
import re

CATEGORIES=("needs_reply","updates","promotions","sales","spam","phishing","other")


@dataclass(frozen=True)
class MailVerdict:
    category:str
    confidence:float
    reasons:tuple[str,...]
    recommended_action:str
    requires_owner_approval:bool
    def as_dict(self):
        row=asdict(self);row["reasons"]=list(self.reasons);return row


class GmailTriage:
    """Fast Jev-style mailbox decision layer.

    Heuristics are only a cheap first pass. A local/free model may replace the
    verdict, but destructive actions remain governed by SuperhumanOperatorPolicy.
    """

    SPAM_PATTERNS=(
        r"(?i)guaranteeds+income",r"(?i)cryptos+giveaway",r"(?i)claims+yours+prize",
        r"(?i)urgents+wire",r"(?i)lotterys+winner",r"(?i)buys+followers",
    )
    PHISH_PATTERNS=(
        r"(?i)verifys+yours+account",r"(?i)passwords+expires",r"(?i)unusuals+login",
        r"(?i)confirms+yours+credentials",
    )

    def classify(self,message:dict,model_verdict:dict|None=None)->dict:
        if model_verdict:
            cat=str(model_verdict.get("category") or "").lower()
            conf=float(model_verdict.get("confidence") or 0)
            if cat in CATEGORIES and 0<=conf<=1:
                action="trash" if cat=="spam" and conf>=0.995 else ("quarantine" if cat in {"spam","phishing"} else "keep")
                return MailVerdict(cat,conf,tuple(model_verdict.get("reasons") or ["model verdict"]),action,action=="trash").as_dict()
        subject=str(message.get("subject") or "")
        sender=str(message.get("from") or "")
        body=str(message.get("snippet") or message.get("body") or "")
        text=" ".join((subject,sender,body))
        reasons=[]
        for p in self.PHISH_PATTERNS:
            if re.search(p,text):
                reasons.append("phishing phrase matched")
        if reasons:
            return MailVerdict("phishing",0.98,tuple(reasons),"quarantine",False).as_dict()
        spam=sum(bool(re.search(p,text)) for p in self.SPAM_PATTERNS)
        if spam:
            return MailVerdict("spam",min(0.99,0.90+spam*0.03),("spam pattern matched",),"quarantine",False).as_dict()
        low=text.lower()
        if any(x in low for x in ("newsletter","unsubscribe","offer","coupon","sale ends")):
            return MailVerdict("promotions",0.86,("promotion/newsletter signal",),"archive_or_label",False).as_dict()
        if any(x in low for x in ("quotation","quote","purchase order","pricing","demo","partnership","customer")):
            return MailVerdict("sales",0.84,("commercial intent signal",),"review",False).as_dict()
        if "?" in body or any(x in low for x in ("please reply","let me know","can you","could you")):
            return MailVerdict("needs_reply",0.82,("reply-request signal",),"draft_reply",False).as_dict()
        if any(x in low for x in ("receipt","shipped","delivered","status update","notification")):
            return MailVerdict("updates",0.82,("transaction/update signal",),"label",False).as_dict()
        return MailVerdict("other",0.55,("no strong signal",),"keep",False).as_dict()

    def batch(self,messages,model_verdicts=None):
        verdicts=model_verdicts or {}
        return [{"message_id":str(m.get("id") or ""),"verdict":self.classify(m,verdicts.get(str(m.get("id") or "")))} for m in messages]
