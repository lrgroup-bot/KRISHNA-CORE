from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode
import json
import re
import shutil
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass(frozen=True)
class SalesAgent:
    id: str
    name: str
    role: str
    mission: str
    permissions: tuple[str, ...]
    external_write: bool = False

    def as_dict(self) -> dict:
        row = asdict(self)
        row["permissions"] = list(self.permissions)
        return row


PERMANENT_TEAM = (
    SalesAgent(
        "lead-researcher",
        "Lead Researcher",
        "market and prospect research",
        "Find legitimate public or consented prospects that match the approved product and ideal customer profile.",
        ("web.read", "crm.read", "crm.write"),
    ),
    SalesAgent(
        "sdr-caller",
        "SDR / Calling Shishya",
        "first contact and appointment setting",
        "Contact eligible prospects through connected approved channels, respect opt-outs, and create qualified conversations.",
        ("crm.read", "crm.write", "communications.draft", "communications.send"),
        True,
    ),
    SalesAgent(
        "lead-qualifier",
        "Lead Qualifier",
        "qualification",
        "Determine need, authority, ability/budget, timing, fit, objections, and next action without fabricating facts.",
        ("crm.read", "crm.write", "communications.draft"),
    ),
    SalesAgent(
        "account-executive",
        "Account Executive",
        "opportunity ownership",
        "Own the sales opportunity from discovery through commercial close and coordinate internal specialists.",
        ("crm.read", "crm.write", "communications.draft", "communications.send"),
        True,
    ),
    SalesAgent(
        "solution-consultant",
        "Solution Consultant",
        "solution discovery and matching",
        "Translate the customer's stated problem into an evidence-grounded approved product or service recommendation.",
        ("crm.read", "catalog.read", "research.read", "communications.draft"),
    ),
    SalesAgent(
        "proposal-pricing",
        "Proposal & Pricing Specialist",
        "proposal and exact-price preparation",
        "Prepare scope, quotation, exact receivable amount, terms, and assumptions only from approved catalogue/pricing data.",
        ("crm.read", "catalog.read", "proposal.write"),
    ),
    SalesAgent(
        "deal-closer",
        "Negotiator / Deal Closer",
        "objection handling and negotiation",
        "Handle objections and negotiate within approved commercial boundaries; escalate exceptions instead of inventing authority.",
        ("crm.read", "crm.write", "communications.draft", "communications.send"),
        True,
    ),
    SalesAgent(
        "relationship-manager",
        "Customer Relationship Manager",
        "follow-up and account growth",
        "Maintain post-proposal and post-sale follow-up, referrals, repeat sales, upsell and cross-sell using consented channels.",
        ("crm.read", "crm.write", "communications.draft", "communications.send"),
        True,
    ),
)


class VanijyaSalesHead:
    """Independent Sales & Marketing Head for KRISHNA.

    Vāṇijya owns go-to-market and sales execution. MANIBHADRA remains the
    commerce/product/catalogue/opportunity authority. NARAD remains the external
    communications connector path. External writes fail closed until the real
    connector is connected and the contact basis is permitted.

    Payment collection is receive-only. Vāṇijya can create exact-amount UPI
    intents/QR payloads but can mark a payment PAID only from authenticated
    provider/bank evidence matching invoice, amount and transaction reference.
    """

    SCHEMA = "krishna.vanijya.sales.v2"
    ALLOWED_CHANNELS = {"gmail", "email", "whatsapp"}
    BLOCKED_CONTACT_HINTS = {
        "do not contact", "do not call", "unsubscribe", "stop", "opt out",
        "opt-out", "no marketing", "remove me", "don't message", "dont message",
    }
    SALES_STAGES = (
        "prospect", "contacted", "qualified", "discovery", "solution",
        "proposal", "negotiation", "payment_pending", "won", "lost", "nurture",
    )

    def __init__(self, state_path: str | Path | None = None, *, crm=None, message_store=None):
        self.id = "rishi-vanijya"
        self.display_name = "Rishi Vāṇijya"
        self.title = "Independent Sales & Marketing Head"
        self.owner = "KRISHNA"
        self.product_source = "MANIBHADRA"
        self.crm = crm
        self.message_store = message_store
        self.path = Path(state_path).resolve() if state_path else None
        self.backup = self.path.with_suffix(self.path.suffix + ".bak") if self.path else None
        self._state = self._load()

    def _blank(self) -> dict:
        return {
            "schema": self.SCHEMA,
            "updated_at": _now(),
            "campaigns": [],
            "conversations": [],
            "quotes": [],
            "payments": [],
            "workers": [],
            "hr_requests": [],
            "product_assignments": [],
            "opt_outs": [],
            "activities": [],
            "settings": {
                "zero_spend": True,
                "receive_only": True,
                "auto_sales": True,
                "auto_paid_acquisition": False,
                "contact_basis": "public_business_or_consented_or_inbound_or_existing_customer",
                "external_connector_fail_closed": True,
                "payment_verification": "trusted_psp_or_bank_only",
            },
        }

    def _load(self) -> dict:
        if not self.path:
            return self._blank()
        if not self.path.exists():
            data = self._blank()
            self._write(data, make_backup=False)
            return data
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("schema") != self.SCHEMA:
                raise ValueError("Vanijya state schema mismatch")
            return data
        except Exception as exc:
            if self.backup and self.backup.exists():
                data = json.loads(self.backup.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("schema") == self.SCHEMA:
                    self._write(data, make_backup=False)
                    return data
            raise RuntimeError(f"VANIJYA state unreadable: {type(exc).__name__}: {exc}") from exc

    def _write(self, data: dict, *, make_backup: bool = True) -> dict:
        data = dict(data)
        data["schema"] = self.SCHEMA
        data["updated_at"] = _now()
        self._state = data
        if not self.path:
            return data
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        if make_backup and self.path.exists() and self.backup:
            try:
                shutil.copy2(self.path, self.backup)
            except OSError:
                pass
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)
        return data

    def _activity(self, kind: str, title: str, detail: str = "", record_id: str = "") -> None:
        self._state["activities"].insert(0, {
            "id": _id("vact"), "time": _now(), "kind": str(kind)[:80],
            "title": str(title)[:240], "detail": str(detail)[:1200],
            "record_id": str(record_id)[:120],
        })
        del self._state["activities"][500:]

    @staticmethod
    def _money(value) -> Decimal:
        try:
            amount = Decimal(str(value)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("invalid amount")
        if amount <= 0:
            raise ValueError("amount must be greater than zero")
        return amount

    @staticmethod
    def _bounded_score(value) -> float:
        try:
            return max(0.0, min(100.0, float(value or 0)))
        except (TypeError, ValueError):
            return 0.0

    def health(self) -> dict:
        try:
            data = self._load() if self.path else self._state
            return {
                "ok": True, "component": "Rishi Vanijya Sales Runtime",
                "schema": data.get("schema"), "updated_at": data.get("updated_at"),
                "backup": bool(self.backup and self.backup.exists()),
            }
        except Exception as exc:
            return {
                "ok": False, "component": "Rishi Vanijya Sales Runtime",
                "error": f"{type(exc).__name__}: {exc}",
                "backup": bool(self.backup and self.backup.exists()),
            }

    def status(self) -> dict:
        data = self._state
        active_campaigns = [x for x in data["campaigns"] if x.get("status") == "active"]
        open_conversations = [x for x in data["conversations"] if x.get("status") not in {"won", "lost", "opted_out"}]
        pending_payments = [x for x in data["payments"] if x.get("status") == "PENDING"]
        won_payments = [x for x in data["payments"] if x.get("status") == "PAID"]
        return {
            "schema": self.SCHEMA,
            "id": self.id,
            "name": self.display_name,
            "title": self.title,
            "independent": True,
            "reports_to": self.owner,
            "asks_manibhadra_for_products": True,
            "product_source": self.product_source,
            "communications_owner": "NARAD",
            "mission": "market approved products/services, convert legitimate demand into sales, and grow received revenue",
            "team": [agent.as_dict() for agent in PERMANENT_TEAM],
            "temporary_workers": list(data["workers"]),
            "counts": {
                "campaigns": len(data["campaigns"]),
                "active_campaigns": len(active_campaigns),
                "conversations": len(data["conversations"]),
                "open_conversations": len(open_conversations),
                "quotes": len(data["quotes"]),
                "payments": len(data["payments"]),
                "pending_payments": len(pending_payments),
                "paid_payments": len(won_payments),
                "hr_requests": len(data["hr_requests"]),
            },
            "money_policy": {
                "receive_only": True,
                "outgoing_spend": False,
                "payouts": False,
                "paid_ads": False,
                "paid_leads": False,
                "payment_confirmation": "trusted-provider-or-bank-evidence-only",
            },
            "outreach_policy": {
                "public_or_consented_business_contact_only": True,
                "honor_opt_outs": True,
                "bulk_spam": False,
                "deception": False,
                "fake_identity": False,
                "connected_channels_required": True,
            },
            "health": self.health(),
        }

    def dashboard(self) -> dict:
        status = self.status()
        return {
            "schema": "krishna.vanijya.dashboard.v1",
            "status": status,
            "campaigns": list(self._state["campaigns"][-30:]),
            "conversations": list(self._state["conversations"][-50:]),
            "quotes": list(self._state["quotes"][-30:]),
            "payments": list(self._state["payments"][-30:]),
            "hr_requests": list(self._state["hr_requests"][-30:]),
            "workers": list(self._state["workers"][-30:]),
            "activities": list(self._state["activities"][:50]),
            "product_assignments": list(self._state["product_assignments"][-50:]),
        }

    def hr_request(self, requirement: str, *, reason: str = "", temporary: bool = True) -> dict:
        req = str(requirement or "").strip()
        if not req:
            raise ValueError("worker requirement is required")
        row = {
            "schema": "krishna.hr.worker-request.v1",
            "request_id": _id("hr"),
            "requested_by": self.id,
            "department": "sales_marketing",
            "requirement": req[:500],
            "reason": str(reason or "")[:1000],
            "employment": "temporary_shishya" if temporary else "permanent_specialist",
            "must_inherit": [
                "zero_spend", "receive_only", "public_or_consented_contact_only",
                "honor_opt_out", "no_deception", "no_secret_exfiltration",
                "external_connector_fail_closed",
            ],
            "status": "REQUESTED",
            "created_at": _now(),
        }
        self._state["hr_requests"].append(row)
        self._activity("hr", "Sales worker requested", req, row["request_id"])
        self._write(self._state)
        return dict(row)

    def hr_create_bot(self, request_id: str, *, name: str = "", skills=None) -> dict:
        req = next((x for x in self._state["hr_requests"] if x.get("request_id") == str(request_id)), None)
        if not req:
            raise KeyError("HR request not found")
        if req.get("status") not in {"REQUESTED", "APPROVED"}:
            raise RuntimeError("HR request is not creatable")
        worker = {
            "id": _id("salesbot"),
            "name": str(name or req["requirement"]).strip()[:160],
            "department": "sales_marketing",
            "reports_to": self.id,
            "employment": req["employment"],
            "skills": [str(x)[:100] for x in (skills or [])][:30],
            "mission": req["requirement"],
            "guardrails": list(req["must_inherit"]),
            "status": "READY",
            "created_at": _now(),
        }
        req["status"] = "FULFILLED"
        req["worker_id"] = worker["id"]
        req["fulfilled_at"] = _now()
        self._state["workers"].append(worker)
        self._activity("hr", "Sales bot created", worker["name"], worker["id"])
        self._write(self._state)
        return dict(worker)

    def hr_retire_bot(self, worker_id: str, *, outcome: str = "", lessons=None) -> dict:
        worker = next((x for x in self._state["workers"] if x.get("id") == str(worker_id)), None)
        if not worker:
            raise KeyError("sales worker not found")
        worker["status"] = "RETIRED"
        worker["retired_at"] = _now()
        worker["outcome"] = str(outcome or "")[:2000]
        worker["lessons"] = [str(x)[:500] for x in (lessons or [])][:50]
        self._activity("hr", "Sales bot retired", worker["name"], worker["id"])
        self._write(self._state)
        return dict(worker)

    def ask_manibhadra(self, *, objective: str = "find products or services worth marketing now") -> dict:
        return {
            "schema": "krishna.vanijya.manibhadra-request.v1",
            "from": self.id,
            "to": "manibhadra",
            "objective": str(objective or "").strip()[:1000],
            "need": [
                "approved product/service records", "target customer profile",
                "sale price or commission economics", "allowed geographies/channels",
                "evidence for product claims", "availability or fulfilment constraints",
            ],
            "zero_spend": True,
            "created_at": _now(),
        }

    def sync_manibhadra_products(self) -> dict:
        if self.crm is None:
            return {"synced": 0, "products": [], "reason": "crm_not_bound"}
        records = self.crm.records()
        products = list(records.get("products") or [])
        existing = {x.get("product_id"): x for x in self._state["product_assignments"]}
        added = 0
        for product in products:
            pid = str(product.get("id") or "").strip()
            if not pid:
                continue
            row = existing.get(pid)
            if row is None:
                row = {
                    "id": _id("product_assignment"),
                    "product_id": pid,
                    "product_name": str(product.get("name") or ""),
                    "status": "READY_TO_MARKET" if str(product.get("status") or "").lower() not in {"blocked", "disabled"} else "BLOCKED",
                    "sale_price": product.get("sale_price", 0),
                    "source": product.get("source", ""),
                    "url": product.get("url", ""),
                    "assigned_at": _now(),
                }
                self._state["product_assignments"].append(row)
                existing[pid] = row
                added += 1
            else:
                row["product_name"] = str(product.get("name") or row.get("product_name") or "")
                row["sale_price"] = product.get("sale_price", row.get("sale_price", 0))
                row["source"] = product.get("source", row.get("source", ""))
                row["url"] = product.get("url", row.get("url", ""))
        if added:
            self._activity("product", "MANIBHADRA products synced", f"{added} new product assignments")
            self._write(self._state)
        return {"synced": added, "products": list(self._state["product_assignments"])}

    def create_campaign(
        self, product: dict, *, name: str = "", objective: str = "",
        channels=None, audience: str = "", geography: str = "",
    ) -> dict:
        product = dict(product or {})
        product_name = str(product.get("name") or "").strip()
        if not product_name:
            raise ValueError("approved product/service name is required")
        selected = [str(x).strip().lower() for x in (channels or ["gmail", "whatsapp"]) if str(x).strip()]
        if any(x not in self.ALLOWED_CHANNELS for x in selected):
            raise ValueError("campaign contains unsupported channel")
        row = {
            "id": _id("campaign"),
            "name": str(name or f"{product_name} sales campaign")[:180],
            "product_id": str(product.get("id") or ""),
            "product_name": product_name,
            "product_url": str(product.get("url") or ""),
            "sale_price": product.get("sale_price", 0),
            "objective": str(objective or "generate legitimate qualified sales")[:1000],
            "audience": str(audience or "")[:1000],
            "geography": str(geography or "")[:300],
            "channels": selected,
            "acquisition_cost_limit": 0,
            "paid_ads": False,
            "paid_leads": False,
            "status": "active",
            "created_at": _now(),
        }
        self._state["campaigns"].append(row)
        self._activity("campaign", "Sales campaign created", row["name"], row["id"])
        self._write(self._state)
        return dict(row)

    @classmethod
    def outreach_decision(cls, lead: dict, *, channel: str, connector_state: str) -> dict:
        channel = str(channel or "").strip().lower()
        state = str(connector_state or "").strip().upper()
        contact_text = " ".join(str(lead.get(k) or "") for k in ("consent", "notes", "last_message", "tags")).lower()
        opted_out = any(x in contact_text for x in cls.BLOCKED_CONTACT_HINTS) or bool(lead.get("opted_out"))
        public_or_consented = bool(
            lead.get("consented") or lead.get("inbound") or lead.get("public_business_contact") or lead.get("existing_customer")
        )
        reasons = []
        if channel not in cls.ALLOWED_CHANNELS:
            reasons.append("channel_not_approved")
        if state != "CONNECTED":
            reasons.append("connector_not_connected")
        if opted_out:
            reasons.append("opted_out")
        if not public_or_consented:
            reasons.append("no_public_or_consented_contact_basis")
        return {
            "allowed": not reasons,
            "channel": channel,
            "reasons": reasons,
            "requires_identity_and_offer_truth": True,
            "requires_unsubscribe_or_stop_handling": True,
        }

    def qualify_lead(self, lead: dict, signals: dict | None = None) -> dict:
        lead = dict(lead or {})
        signals = dict(signals or {})
        need = self._bounded_score(signals.get("need", lead.get("score", 0)))
        authority = self._bounded_score(signals.get("authority", 0))
        timing = self._bounded_score(signals.get("timing", 0))
        fit = self._bounded_score(signals.get("fit", 0))
        engagement = self._bounded_score(signals.get("engagement", 0))
        score = round(need * .30 + fit * .25 + engagement * .20 + timing * .15 + authority * .10, 1)
        qualified = score >= 60 and need >= 50 and fit >= 50
        return {
            "lead_id": str(lead.get("id") or ""),
            "score": score,
            "qualified": qualified,
            "stage": "qualified" if qualified else "nurture",
            "signals": {
                "need": need, "authority": authority, "timing": timing,
                "fit": fit, "engagement": engagement,
            },
            "next_agent": "account-executive" if qualified else "relationship-manager",
            "next_action": "discovery" if qualified else "consented_nurture",
        }

    @staticmethod
    def _reply_intent(text: str) -> str:
        low = str(text or "").lower()
        if any(x in low for x in ("unsubscribe", "stop", "do not contact", "remove me", "don't message", "dont message")):
            return "opt_out"
        if any(x in low for x in ("price", "cost", "quote", "quotation", "how much", "rate")):
            return "pricing"
        if any(x in low for x in ("yes", "interested", "demo", "meeting", "call me", "let's talk", "lets talk")):
            return "positive"
        if any(x in low for x in ("not interested", "no thanks", "no thank", "don't need", "dont need")):
            return "negative"
        if any(x in low for x in ("problem", "issue", "need", "require", "looking for", "want")):
            return "requirement"
        if "?" in low:
            return "question"
        return "unknown"

    def ingest_reply(
        self, *, lead_id: str, provider: str, text: str, thread_ref: str = "",
        sender: str = "", metadata: dict | None = None,
    ) -> dict:
        intent = self._reply_intent(text)
        row = {
            "id": _id("conv"),
            "lead_id": str(lead_id or ""),
            "provider": str(provider or "").strip().lower(),
            "thread_ref": str(thread_ref or "")[:240],
            "sender": str(sender or "")[:240],
            "direction": "inbound",
            "text": str(text or "")[:20000],
            "intent": intent,
            "status": "opted_out" if intent == "opt_out" else "open",
            "metadata": dict(metadata or {}),
            "created_at": _now(),
        }
        self._state["conversations"].append(row)
        if intent == "opt_out":
            self._state["opt_outs"].append({
                "lead_id": row["lead_id"], "provider": row["provider"],
                "sender": row["sender"], "at": _now(), "source": "customer_reply",
            })
        if self.message_store is not None:
            try:
                self.message_store.add(
                    direction="inbox", provider=row["provider"], text=row["text"],
                    thread_ref=row["thread_ref"], sender=row["sender"],
                    metadata={"vanijya": True, "lead_id": row["lead_id"], "intent": intent},
                )
            except Exception:
                pass
        self._activity("reply", f"Customer reply · {intent}", row["sender"] or row["lead_id"], row["id"])
        self._write(self._state)
        return {**dict(row), "next": self.reply_plan(row)}

    def reply_plan(self, reply: dict) -> dict:
        intent = str(reply.get("intent") or self._reply_intent(reply.get("text") or ""))
        mapping = {
            "opt_out": ("relationship-manager", "stop_contact", "Acknowledge the opt-out if needed and do not send further marketing."),
            "pricing": ("proposal-pricing", "prepare_quote", "Prepare an exact truthful quote from MANIBHADRA catalogue pricing."),
            "positive": ("account-executive", "discovery", "Continue discovery and confirm requirement, timing and decision process."),
            "negative": ("relationship-manager", "close_or_nurture", "Respect the response; do not pressure. Keep only if future contact is consented."),
            "requirement": ("solution-consultant", "match_solution", "Map the stated requirement to an approved product/service and evidence."),
            "question": ("solution-consultant", "answer_truthfully", "Answer from verified product facts; research unknown facts before replying."),
            "unknown": ("lead-qualifier", "clarify", "Ask one concise question to understand the customer's requirement."),
        }
        agent, action, guidance = mapping.get(intent, mapping["unknown"])
        return {"intent": intent, "agent": agent, "action": action, "guidance": guidance}

    def plan_outbound(
        self, *, lead: dict, channel: str, connector_state: str,
        text: str, subject: str = "", thread_ref: str = "", purpose: str = "sales",
    ) -> dict:
        decision = self.outreach_decision(lead, channel=channel, connector_state=connector_state)
        row = {
            "id": _id("conv"),
            "lead_id": str(lead.get("id") or ""),
            "provider": str(channel or "").strip().lower(),
            "direction": "outbound",
            "subject": str(subject or "")[:500],
            "text": str(text or "")[:20000],
            "thread_ref": str(thread_ref or "")[:240],
            "purpose": str(purpose or "sales")[:100],
            "status": "queued" if decision["allowed"] else "blocked",
            "decision": decision,
            "created_at": _now(),
        }
        if not row["text"].strip():
            raise ValueError("outbound message text is required")
        self._state["conversations"].append(row)
        if self.message_store is not None:
            try:
                self.message_store.add(
                    direction="outbox", provider=row["provider"], text=row["text"],
                    state="queued" if decision["allowed"] else "draft",
                    thread_ref=row["thread_ref"],
                    recipients=[str(lead.get("email") or lead.get("phone") or "")],
                    metadata={
                        "vanijya": True, "lead_id": row["lead_id"],
                        "subject": row["subject"], "purpose": row["purpose"],
                        "blocked": not decision["allowed"],
                    },
                )
            except Exception:
                pass
        self._activity("outreach", "Outbound sales message planned", row["provider"], row["id"])
        self._write(self._state)
        return dict(row)

    def provider_payload(self, outbound: dict, lead: dict) -> dict:
        provider = str(outbound.get("provider") or "").lower()
        if provider in {"gmail", "email"}:
            to = str(lead.get("email") or "").strip()
            if not to:
                raise ValueError("lead email is required")
            return {
                "provider": "gmail",
                "operation": "send_email",
                "payload": {
                    "to": to,
                    "subject": str(outbound.get("subject") or "Information from our team"),
                    "text": str(outbound.get("text") or ""),
                    "thread_id": str(outbound.get("thread_ref") or ""),
                },
            }
        if provider == "whatsapp":
            to = str(lead.get("phone") or "").strip()
            if not to:
                raise ValueError("lead phone is required")
            return {
                "provider": "whatsapp",
                "operation": "send_message",
                "payload": {"to": to, "text": str(outbound.get("text") or "")},
            }
        raise ValueError("unsupported outbound provider")

    def quote(
        self, *, lead_id: str, product: dict, quantity: int = 1,
        deal_id: str = "", notes: str = "", approved_discount_percent: float = 0.0,
    ) -> dict:
        quantity = max(1, int(quantity or 1))
        product = dict(product or {})
        unit = self._money(product.get("sale_price"))
        discount = max(0.0, min(100.0, float(approved_discount_percent or 0)))
        max_discount = max(0.0, min(100.0, float(product.get("approved_discount_percent") or 0)))
        if discount > max_discount:
            raise PermissionError("discount exceeds approved product pricing authority")
        subtotal = unit * quantity
        final = (subtotal * (Decimal("1") - Decimal(str(discount)) / Decimal("100"))).quantize(Decimal("0.01"))
        row = {
            "id": _id("quote"),
            "quote_number": "VQ-" + uuid.uuid4().hex[:10].upper(),
            "lead_id": str(lead_id or ""),
            "deal_id": str(deal_id or ""),
            "product_id": str(product.get("id") or ""),
            "product_name": str(product.get("name") or ""),
            "quantity": quantity,
            "unit_price": float(unit),
            "subtotal": float(subtotal),
            "discount_percent": discount,
            "amount_due": float(final),
            "currency": "INR",
            "notes": str(notes or "")[:2000],
            "truth_source": "MANIBHADRA product record",
            "status": "OPEN",
            "created_at": _now(),
        }
        if not row["product_name"]:
            raise ValueError("product name is required")
        self._state["quotes"].append(row)
        self._activity("quote", "Quote created", f"{row['quote_number']} · ₹{row['amount_due']:.2f}", row["id"])
        self._write(self._state)
        return dict(row)

    def upi_payment_request(
        self, *, payee_vpa: str, payee_name: str, amount,
        invoice_id: str, note: str = "", deal_id: str = "", lead_id: str = "",
    ) -> dict:
        vpa = str(payee_vpa or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{2,}@[A-Za-z0-9.-]{2,}", vpa):
            raise ValueError("configured merchant/payee UPI VPA is required")
        name = str(payee_name or "").strip()
        if not name:
            raise ValueError("payee name is required")
        invoice = str(invoice_id or "").strip()
        if not invoice:
            raise ValueError("invoice_id is required")
        exact = self._money(amount)
        params = {
            "pa": vpa, "pn": name, "am": f"{exact:.2f}", "cu": "INR",
            "tn": (str(note or "").strip() or f"Invoice {invoice}")[:80],
        }
        uri = "upi://pay?" + urlencode(params)
        row = {
            "schema": "krishna.vanijya.payment-request.v1",
            "id": _id("payment"),
            "invoice_id": invoice,
            "deal_id": str(deal_id or ""),
            "lead_id": str(lead_id or ""),
            "amount": float(exact),
            "currency": "INR",
            "upi_uri": uri,
            "qr_payload": uri,
            "status": "PENDING",
            "receive_only": True,
            "verification_required": True,
            "created_at": _now(),
        }
        self._state["payments"].append(row)
        self._activity("payment", "Payment request created", f"{invoice} · ₹{float(exact):.2f}", row["id"])
        self._write(self._state)
        return dict(row)

    def verify_payment(self, request: dict, evidence: dict) -> dict:
        invoice = str(request.get("invoice_id") or "")
        expected = self._money(request.get("amount"))
        provider = str(evidence.get("provider") or "").strip()
        verified = bool(evidence.get("signature_verified") or evidence.get("bank_verified"))
        status = str(evidence.get("status") or "").strip().upper()
        evidence_invoice = str(evidence.get("invoice_id") or "")
        txid = str(evidence.get("transaction_id") or evidence.get("utr") or "").strip()
        try:
            received = self._money(evidence.get("amount"))
        except ValueError:
            received = Decimal("0")
        reasons = []
        if not provider:
            reasons.append("provider_missing")
        if not verified:
            reasons.append("unverified_evidence")
        if status not in {"SUCCESS", "CAPTURED", "PAID"}:
            reasons.append("provider_status_not_paid")
        if invoice and evidence_invoice and invoice != evidence_invoice:
            reasons.append("invoice_mismatch")
        if received != expected:
            reasons.append("amount_mismatch")
        if not txid:
            reasons.append("transaction_reference_missing")
        paid = not reasons
        result = {
            "invoice_id": invoice,
            "status": "PAID" if paid else "PENDING",
            "paid": paid,
            "provider": provider,
            "transaction_id": txid if paid else "",
            "amount": float(expected),
            "reasons": reasons,
            "verified_at": _now() if paid else None,
        }
        if paid:
            for row in self._state["payments"]:
                if row.get("invoice_id") == invoice and float(row.get("amount") or 0) == float(expected):
                    row.update(result)
                    if row.get("deal_id") and self.crm is not None:
                        try:
                            self.crm.move_deal(str(row["deal_id"]), "won")
                        except Exception:
                            pass
                    break
            self._activity("payment", "Payment verified", f"{invoice} · {provider}", txid)
            self._write(self._state)
        return result

    def autopilot_plan(self) -> dict:
        """Build the next bounded autonomous sales workload.

        This planner may update local VANIJYA product assignments, but it does not
        perform an external send or spend money. External communication is handed
        to NARAD and remains subject to connector, consent and workflow gates.
        """
        sync=self.sync_manibhadra_products()
        request=self.ask_manibhadra(
            objective=(
                "Review current commerce state and identify any new or improved product/service "
                "Vāṇijya should market using zero-spend routes, with target customer, price/commission "
                "economics, truthful claims, geography, fulfilment constraints and channel rules."
            )
        )
        records=self.crm.records() if self.crm is not None else {
            "products":[],"leads":[],"deals":[],"tasks":[],
        }
        products=list(records.get("products") or [])
        leads=list(records.get("leads") or [])
        deals=list(records.get("deals") or [])
        tasks=list(records.get("tasks") or [])
        ready_products=[
            x for x in products
            if str(x.get("status") or "research").lower() not in {"blocked","disabled","paused"}
        ]
        queue=[]
        if not ready_products:
            queue.append({
                "agent":"lead-researcher",
                "priority":100,
                "action":"WAIT_FOR_MANIBHADRA_PRODUCT",
                "reason":"No approved marketable product/service exists.",
            })
        elif not leads:
            queue.append({
                "agent":"lead-researcher",
                "priority":95,
                "action":"FIND_TARGET_PROSPECTS",
                "product_id":ready_products[0].get("id"),
                "reason":"A product is ready but there are no buyer leads yet.",
            })
        for lead in leads:
            if str(lead.get("stage") or "new").lower() in {"won","lost"}:
                continue
            queue.append({
                "agent":"lead-qualifier",
                "priority":85 if float(lead.get("score") or 0)>=70 else 65,
                "action":"QUALIFY_OR_FOLLOW_UP",
                "lead_id":lead.get("id"),
                "reason":lead.get("next_action") or "Lead requires qualification/follow-up.",
            })
        stage_agent={
            "new":"lead-qualifier",
            "qualified":"account-executive",
            "contacted":"account-executive",
            "proposal":"proposal-pricing",
            "negotiation":"deal-closer",
        }
        for deal in deals:
            stage=str(deal.get("stage") or "new").lower()
            if stage in {"won","lost"}:
                continue
            queue.append({
                "agent":stage_agent.get(stage,"account-executive"),
                "priority":90 if stage in {"proposal","negotiation"} else 75,
                "action":"ADVANCE_DEAL",
                "deal_id":deal.get("id"),
                "stage":stage,
                "reason":deal.get("next_action") or "Deal requires a next action.",
            })
        for task in tasks:
            if str(task.get("status") or "open").lower()=="open":
                queue.append({
                    "agent":"relationship-manager",
                    "priority":80 if str(task.get("priority") or "").lower()=="high" else 60,
                    "action":"FOLLOW_UP_TASK",
                    "task_id":task.get("id"),
                    "reason":task.get("title") or "Open follow-up task.",
                })
        queue.sort(key=lambda x:(-int(x.get("priority") or 0),str(x.get("agent") or "")))
        return {
            "schema":"krishna.vanijya.autopilot-plan.v1",
            "status":"READY" if ready_products else "NEEDS_PRODUCT",
            "manibhadra_request":request,
            "product_sync":sync,
            "ready_product_count":len(ready_products),
            "lead_count":len(leads),
            "deal_count":len(deals),
            "agent_queue":queue[:100],
            "external_send_performed":False,
            "spend_performed":False,
            "communications_via":"NARAD",
            "zero_spend":True,
            "created_at":_now(),
        }

    def sales_cycle(self, *, product: dict | None = None) -> dict:
        product = dict(product or {})
        if not product and self.crm is not None:
            products = list((self.crm.records() or {}).get("products") or [])
            ready = [x for x in products if str(x.get("status") or "research").lower() not in {"blocked", "disabled"}]
            product = ready[0] if ready else {}
        if not product:
            return {
                "status": "NEEDS_PRODUCT",
                "next": self.ask_manibhadra(objective="provide the next approved product/service Vāṇijya should market"),
            }
        return {
            "status": "READY",
            "product": {
                "id": product.get("id"), "name": product.get("name"),
                "sale_price": product.get("sale_price"), "source": product.get("source"),
                "url": product.get("url"),
            },
            "workflow": [
                {"agent": "lead-researcher", "action": "find legitimate target prospects"},
                {"agent": "sdr-caller", "action": "make first contact through approved connected channels"},
                {"agent": "lead-qualifier", "action": "qualify need, fit, timing and decision process"},
                {"agent": "account-executive", "action": "own discovery and opportunity"},
                {"agent": "solution-consultant", "action": "match requirement to verified product/service facts"},
                {"agent": "proposal-pricing", "action": "prepare truthful exact quote"},
                {"agent": "deal-closer", "action": "handle objections and negotiate within approved authority"},
                {"agent": "relationship-manager", "action": "follow through payment, repeat business and referrals"},
            ],
            "zero_spend": True,
            "paid_acquisition": False,
            "communications_via": "NARAD",
        }
