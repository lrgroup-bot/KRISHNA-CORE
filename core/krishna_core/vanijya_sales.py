from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
import re
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
        "Find legitimate public or consented prospects that match the product and ideal customer profile.",
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
        "Determine need, authority, budget/ability, timing, fit, objections, and next action without fabricating facts.",
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
        "Translate the customer's stated problem into an evidence-grounded product or service recommendation.",
        ("crm.read", "catalog.read", "research.read", "communications.draft"),
    ),
    SalesAgent(
        "proposal-pricing",
        "Proposal & Pricing Specialist",
        "proposal and exact-price preparation",
        "Prepare scope, quotation, exact receivable amount, terms, and assumptions from approved catalogue/pricing data.",
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

    Vāṇijya owns go-to-market and sales execution, while MANIBHADRA owns the
    commerce/product catalogue and opportunity supply. External actions are
    fail-closed until an approved connector is connected. Payment requests are
    receive-only; Vāṇijya never performs payouts or outgoing money movement.
    """

    SCHEMA = "krishna.vanijya.sales.v1"
    ALLOWED_CHANNELS = {"gmail", "email", "whatsapp"}
    BLOCKED_CONTACT_HINTS = {
        "do not contact",
        "do not call",
        "unsubscribe",
        "stop",
        "opt out",
        "opt-out",
        "no marketing",
    }

    def __init__(self):
        self.id = "rishi-vanijya"
        self.display_name = "Rishi Vāṇijya"
        self.title = "Independent Sales & Marketing Head"
        self.owner = "KRISHNA"
        self.product_source = "MANIBHADRA"

    @staticmethod
    def _money(value) -> Decimal:
        try:
            amount = Decimal(str(value)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("invalid amount")
        if amount <= 0:
            raise ValueError("amount must be greater than zero")
        return amount

    def status(self) -> dict:
        return {
            "schema": self.SCHEMA,
            "id": self.id,
            "name": self.display_name,
            "title": self.title,
            "independent": True,
            "reports_to": self.owner,
            "asks_manibhadra_for_products": True,
            "product_source": self.product_source,
            "mission": "market approved products/services, convert legitimate demand into sales, and grow received revenue",
            "team": [agent.as_dict() for agent in PERMANENT_TEAM],
            "money_policy": {
                "receive_only": True,
                "outgoing_spend": False,
                "payouts": False,
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
        }

    def hr_request(self, requirement: str, *, reason: str = "", temporary: bool = True) -> dict:
        """Create a bounded HR request; this does not silently instantiate an agent."""
        req = str(requirement or "").strip()
        if not req:
            raise ValueError("worker requirement is required")
        return {
            "schema": "krishna.hr.worker-request.v1",
            "request_id": _id("hr"),
            "requested_by": self.id,
            "department": "sales_marketing",
            "requirement": req[:500],
            "reason": str(reason or "")[:1000],
            "employment": "temporary_shishya" if temporary else "permanent_specialist",
            "must_inherit": [
                "zero_spend",
                "receive_only",
                "public_or_consented_contact_only",
                "honor_opt_out",
                "no_deception",
                "no_secret_exfiltration",
                "external_connector_fail_closed",
            ],
            "status": "REQUESTED",
            "created_at": _now(),
        }

    def ask_manibhadra(self, *, objective: str = "find products or services worth marketing now") -> dict:
        return {
            "schema": "krishna.vanijya.manibhadra-request.v1",
            "from": self.id,
            "to": "manibhadra",
            "objective": str(objective or "").strip()[:1000],
            "need": [
                "approved product/service records",
                "target customer profile",
                "sale price or commission economics",
                "allowed geographies/channels",
                "evidence for product claims",
                "availability or fulfilment constraints",
            ],
            "zero_spend": True,
            "created_at": _now(),
        }

    @classmethod
    def outreach_decision(cls, lead: dict, *, channel: str, connector_state: str) -> dict:
        channel = str(channel or "").strip().lower()
        state = str(connector_state or "").strip().upper()
        contact_text = " ".join(
            str(lead.get(k) or "") for k in ("consent", "notes", "last_message", "tags")
        ).lower()
        opted_out = any(x in contact_text for x in cls.BLOCKED_CONTACT_HINTS)
        public_or_consented = bool(
            lead.get("consented")
            or lead.get("inbound")
            or lead.get("public_business_contact")
            or lead.get("existing_customer")
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

    @staticmethod
    def upi_payment_request(
        *,
        payee_vpa: str,
        payee_name: str,
        amount,
        invoice_id: str,
        note: str = "",
    ) -> dict:
        """Build an exact-amount receive-only UPI intent URI.

        Payment remains PENDING until a trusted PSP/bank verification event is
        supplied. A screenshot, browser/app return, or customer assertion is not
        sufficient proof of payment.
        """
        vpa = str(payee_vpa or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{2,}@[A-Za-z0-9.-]{2,}", vpa):
            raise ValueError("configured merchant/payee UPI VPA is required")
        name = str(payee_name or "").strip()
        if not name:
            raise ValueError("payee name is required")
        invoice = str(invoice_id or "").strip()
        if not invoice:
            raise ValueError("invoice_id is required")
        exact = VanijyaSalesHead._money(amount)
        params = {
            "pa": vpa,
            "pn": name,
            "am": f"{exact:.2f}",
            "cu": "INR",
            "tn": (str(note or "").strip() or f"Invoice {invoice}")[:80],
        }
        return {
            "schema": "krishna.vanijya.payment-request.v1",
            "invoice_id": invoice,
            "amount": float(exact),
            "currency": "INR",
            "upi_uri": "upi://pay?" + urlencode(params),
            "qr_payload": "upi://pay?" + urlencode(params),
            "status": "PENDING",
            "receive_only": True,
            "verification_required": True,
            "created_at": _now(),
        }

    @staticmethod
    def verify_payment(
        request: dict,
        evidence: dict,
    ) -> dict:
        """Accept only authenticated provider/bank evidence for PAID state."""
        invoice = str(request.get("invoice_id") or "")
        expected = VanijyaSalesHead._money(request.get("amount"))
        provider = str(evidence.get("provider") or "").strip()
        verified = bool(evidence.get("signature_verified") or evidence.get("bank_verified"))
        status = str(evidence.get("status") or "").strip().upper()
        evidence_invoice = str(evidence.get("invoice_id") or "")
        txid = str(evidence.get("transaction_id") or evidence.get("utr") or "").strip()
        try:
            received = VanijyaSalesHead._money(evidence.get("amount"))
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
        return {
            "invoice_id": invoice,
            "status": "PAID" if paid else "PENDING",
            "paid": paid,
            "provider": provider,
            "transaction_id": txid if paid else "",
            "amount": float(expected),
            "reasons": reasons,
            "verified_at": _now() if paid else None,
        }
