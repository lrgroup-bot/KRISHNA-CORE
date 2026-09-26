from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
import urllib.parse
import uuid


VANIJYA_RISHI_ID = "vanijya"
VANIJYA_HEAD_NAME = "Rishi Vanijya"

PIPELINE = (
    "prospecting",
    "contact",
    "qualification",
    "discovery",
    "solution",
    "proposal",
    "negotiation",
    "payment_pending",
    "closed_won",
    "closed_lost",
)

TRUSTED_PAYMENT_SOURCES = frozenset({
    "bank_api",
    "bank_statement_api",
    "payment_gateway_webhook",
    "psp_api",
    "upi_acquirer_webhook",
    "upi_psp_status_api",
})

UNTRUSTED_PAYMENT_SOURCES = frozenset({
    "customer_claim",
    "customer_message",
    "screenshot",
    "image",
    "browser_redirect",
    "client_callback",
    "manual_text",
})

ALLOWED_CONTACT_BASES = frozenset({
    "customer_inquiry",
    "existing_customer",
    "public_business_contact_for_relevant_b2b",
    "contractual_service_contact",
})


@dataclass(frozen=True)
class SalesAgentRole:
    id: str
    name: str
    responsibility: str
    stage: str
    handoff_to: tuple[str, ...]

    def as_dict(self):
        row = asdict(self)
        row["handoff_to"] = list(self.handoff_to)
        return row


SALES_TEAM = (
    SalesAgentRole(
        "lead-researcher",
        "Lead Researcher",
        "Find public or consented prospect/account opportunities that match an approved product or service.",
        "prospecting",
        ("sdr-calling-shishya", "lead-qualifier"),
    ),
    SalesAgentRole(
        "sdr-calling-shishya",
        "SDR / Calling Shishya",
        "Handle first permitted contact, inbound enquiries and appointment setting without spam or deception.",
        "contact",
        ("lead-qualifier",),
    ),
    SalesAgentRole(
        "lead-qualifier",
        "Lead Qualifier",
        "Verify need, fit, intent, authority, timing and permitted contact basis before advancing a lead.",
        "qualification",
        ("account-executive",),
    ),
    SalesAgentRole(
        "account-executive",
        "Account Executive",
        "Own discovery, the commercial relationship and coordination of the opportunity through the sales cycle.",
        "discovery",
        ("solution-consultant", "proposal-pricing-specialist"),
    ),
    SalesAgentRole(
        "solution-consultant",
        "Solution Consultant",
        "Understand the customer's problem and match only capabilities/products that are actually available.",
        "solution",
        ("proposal-pricing-specialist",),
    ),
    SalesAgentRole(
        "proposal-pricing-specialist",
        "Proposal & Pricing Specialist",
        "Prepare truthful scope, quotation and commercial proposals from approved product/pricing information.",
        "proposal",
        ("negotiator-deal-closer",),
    ),
    SalesAgentRole(
        "negotiator-deal-closer",
        "Negotiator / Deal Closer",
        "Handle objections and negotiate within approved boundaries, then obtain valid order/contract/payment intent.",
        "negotiation",
        ("customer-relationship-manager",),
    ),
    SalesAgentRole(
        "customer-relationship-manager",
        "Customer Relationship Manager",
        "Manage post-sale follow-up, repeat sales, cross-sell, upsell and referrals without misleading the customer.",
        "relationship",
        (),
    ),
)

TEAM_BY_ID = {row.id: row for row in SALES_TEAM}


class VanijyaSalesHead:
    """Independent KRISHNA Sales & Marketing Head.

    VANIJYA owns market-to-revenue orchestration. MANIBHADRA remains product and
    commerce source-of-truth, NARAD remains the connector/workflow executor and
    NARADA Legal remains the legal/compliance authority.
    """

    def __init__(self, crm, manibhadra, zero_spend, operator_policy):
        self.crm = crm
        self.manibhadra = manibhadra
        self.zero_spend = zero_spend
        self.operator_policy = operator_policy
        self.worker_runtime = None

    def bind_worker_runtime(self, worker_runtime):
        self.worker_runtime = worker_runtime
        return self.status()

    def team(self):
        return [row.as_dict() for row in SALES_TEAM]

    def status(self):
        return {
            "component": "Rishi Vanijya Sales & Marketing Head",
            "rishi_id": VANIJYA_RISHI_ID,
            "display_name": VANIJYA_HEAD_NAME,
            "independent_in_krishna": True,
            "reports_to": "KRISHNA",
            "mission": "market approved products/services, sell truthfully, close valid deals and grow received revenue",
            "product_source_of_truth": "MANIBHADRA",
            "external_communications_executor": "NARAD",
            "legal_compliance_advisor": "NARADA Legal",
            "worker_provisioning": "KRISHNA HR / bounded Shishya runtime",
            "team": self.team(),
            "pipeline": list(PIPELINE),
            "money_policy": "receive only; never send money",
            "payment_rule": "never mark paid from QR/link creation, screenshot, customer claim or browser callback",
            "campaign_rule": "new campaigns ask MANIBHADRA for current product/service opportunity first",
            "autonomous_external_sales": (
                "only inside an owner-authorized verified Stable workflow, with connected accounts, "
                "valid contact basis, suppression/opt-out enforcement and NARADA Legal/provider permission"
            ),
            "worker_runtime_bound": self.worker_runtime is not None,
        }

    @staticmethod
    def _role(role_id: str):
        key = str(role_id or "").strip().lower()
        if key not in TEAM_BY_ID:
            raise KeyError(key)
        return TEAM_BY_ID[key]

    def hr_plan(self, requirement: str, *, role_ids=None, requested_count: int = 1):
        task = str(requirement or "").strip()
        if not task:
            raise ValueError("requirement is required")
        selected = list(role_ids or ["lead-researcher"])
        count = max(1, min(int(requested_count or 1), 8))
        requests = []
        for role_id in selected:
            role = self._role(role_id)
            requests.append({
                "requested_count": count,
                "role": role.id,
                "role_name": role.name,
                "manager": "rishi:vanijya",
                "parent_rishi": VANIJYA_RISHI_ID,
                "specialty": role.responsibility,
                "task": task,
                "allow_sub_shishyas": False,
                "max_children_per_worker": 0,
                "retire_after_handover": True,
                "reason": "Rishi Vanijya requested bounded sales/marketing manpower for a defined requirement",
            })
        return {
            "head": VANIJYA_HEAD_NAME,
            "hr_action": "create bounded workers for the requirement, preserve findings and retire temporary identities after handover",
            "requests": requests,
        }

    def execute_hr_plan(
        self,
        project: str,
        requirement: str,
        *,
        role_ids=None,
        requested_count: int = 1,
        privacy: str = "local_only",
    ):
        if self.worker_runtime is None:
            raise RuntimeError("VANIJYA worker runtime is not bound")
        plan = self.hr_plan(requirement, role_ids=role_ids, requested_count=requested_count)
        batches = []
        for request in plan["requests"]:
            batches.append(self.worker_runtime.execute(
                str(project or "KRISHNA"),
                request,
                "Rishi Vanijya sales/marketing mission: " + str(requirement),
                str(privacy or "local_only"),
            ))
        return {
            "head": VANIJYA_HEAD_NAME,
            "project": str(project or "KRISHNA"),
            "requirement": str(requirement),
            "worker_batches": batches,
            "all_workers_retire_after_handover": True,
        }

    def product_request(self, category: str = ""):
        category = str(category or "").strip()
        return {
            "from": VANIJYA_HEAD_NAME,
            "to": "MANIBHADRA",
            "required_before_new_campaign": True,
            "category": category or "best current zero-spend sellable product/service opportunity",
            "request": (
                "Find a lawful zero-spend product/service opportunity with evidence for demand, target customer, "
                "positioning, approved price/commission path, competition, fulfilment responsibility and realistic "
                "received-revenue path. Do not authorize purchases or paid promotion."
            ),
            "next_action": "manibhadra.research",
        }

    def marketing_plan(self, product: dict, *, objective: str = "generate qualified leads"):
        row = dict(product or {})
        name = str(row.get("name") or row.get("product") or "").strip()
        if not name:
            raise ValueError("product name is required")
        return {
            "head": VANIJYA_HEAD_NAME,
            "product": name,
            "objective": str(objective or "generate qualified leads"),
            "paid_media": False,
            "channels": [
                "owned website/SEO/content",
                "organic social content",
                "inbound email replies",
                "permissioned email outreach",
                "permissioned/inbound WhatsApp",
                "public relevant B2B prospect research",
                "partner/referral routes allowed by program rules",
            ],
            "sequence": [
                "confirm MANIBHADRA product truth and selling path",
                "define ideal customer and problem",
                "research public/consented lead sources",
                "create truthful value proposition",
                "publish organic/owned demand content where authorized",
                "qualify inbound or permitted B2B leads",
                "route qualified leads to Account Executive",
                "measure lead-to-opportunity and opportunity-to-revenue conversion",
            ],
            "prohibitions": [
                "paid advertising under zero-spend mode",
                "bought lead lists",
                "mass unsolicited messaging",
                "fabricated claims/testimonials/scarcity",
                "contacting suppressed/opted-out recipients",
            ],
            "legal_review": "NARADA Legal before automated promotional campaigns in each target jurisdiction/channel",
        }

    @staticmethod
    def qualify_lead(lead: dict):
        lead = dict(lead or {})
        score = max(0, min(int(lead.get("score") or lead.get("intent_score") or 0), 100))
        requirement = str(lead.get("intent") or lead.get("requirement") or "").strip()
        reachable = bool(lead.get("email") or lead.get("phone") or lead.get("channel_address"))
        basis = str(lead.get("contact_basis") or "").strip().lower()
        consented = bool(lead.get("consented") or lead.get("opt_in"))
        inbound = bool(lead.get("inbound"))
        suppressed = bool(lead.get("opted_out") or lead.get("suppressed") or lead.get("do_not_contact"))
        permission_ok = not suppressed and (consented or inbound or basis in ALLOWED_CONTACT_BASES)
        reasons = []
        if not requirement:
            reasons.append("customer requirement is not known")
        if not reachable:
            reasons.append("no reachable contact channel")
        if suppressed:
            reasons.append("recipient is suppressed/opted out/do-not-contact")
        elif not permission_ok:
            reasons.append("no verified contact basis; legal/channel review required before outreach")
        if score < 25:
            reasons.append("intent score is low")
        qualified = bool(requirement and reachable and permission_ok and score >= 25)
        return {
            "qualified": qualified,
            "score": score,
            "permission_ok": permission_ok,
            "suppressed": suppressed,
            "reasons": reasons or ["requirement, reachability, contact basis and minimum intent are present"],
            "next_role": "account-executive" if qualified else "lead-qualifier",
            "stage": "discovery" if qualified else "qualification",
        }

    @staticmethod
    def outreach_plan(channel: str, contact: dict, *, purpose: str, body: str, subject: str = ""):
        channel = str(channel or "").strip().lower()
        contact = dict(contact or {})
        purpose = str(purpose or "").strip()
        body = str(body or "").strip()
        if not purpose or not body:
            raise ValueError("purpose and body are required")
        if channel not in {"gmail", "email", "whatsapp"}:
            raise ValueError("VANIJYA currently supports Gmail/email and WhatsApp plans")

        suppressed = bool(contact.get("opted_out") or contact.get("suppressed") or contact.get("do_not_contact"))
        consented = bool(contact.get("consented") or contact.get("opt_in"))
        inbound = bool(contact.get("inbound") or contact.get("reply_to_existing_thread"))
        basis = str(contact.get("contact_basis") or "").strip().lower()
        permitted_basis = basis in ALLOWED_CONTACT_BASES
        permission_ok = not suppressed and (consented or inbound or permitted_basis)

        # Promotional WhatsApp is intentionally stricter: a public business phone
        # number alone is not enough to enter an automatic WhatsApp send workflow.
        if channel == "whatsapp" and not (consented or inbound):
            permission_ok = False

        provider = "gmail" if channel in {"gmail", "email"} else "whatsapp"
        address = str(contact.get("email") if provider == "gmail" else contact.get("phone") or contact.get("to") or "").strip()
        operation = "send_email" if provider == "gmail" else "send_message"
        payload = {"to": address, "text": body}
        if provider == "gmail":
            payload["subject"] = str(subject or purpose).strip()

        return {
            "channel": provider,
            "recipient": address,
            "purpose": purpose,
            "suppressed": suppressed,
            "contact_permission": permission_ok,
            "legal_gate": "NARADA Legal review required for current jurisdiction/campaign/channel rules",
            "provider_policy_gate": True,
            "opt_out_must_be_honored": True,
            "provider_action": {
                "action": "narad.provider_send",
                "provider": provider,
                "operation": operation,
                "payload": payload,
            },
            "can_enter_automatic_send_workflow": bool(address and permission_ok),
            "reason": (
                "permitted contact basis present and recipient is not suppressed"
                if address and permission_ok
                else "recipient/address/contact permission is missing, suppressed or insufficient for this channel"
            ),
        }

    @staticmethod
    def inbound_reply_plan(message: dict):
        msg = dict(message or {})
        text = str(msg.get("text") or msg.get("body") or msg.get("snippet") or "").strip()
        low = text.lower()
        if not text:
            return {"intent": "unknown", "next_role": "lead-qualifier", "next_action": "request readable reply content"}
        if any(x in low for x in ("stop", "unsubscribe", "remove me", "do not contact", "don't contact")):
            return {
                "intent": "opt_out",
                "next_role": "lead-qualifier",
                "next_action": "suppress recipient immediately and stop promotional follow-up",
                "must_not_sell": True,
            }
        if any(x in low for x in ("price", "quotation", "quote", "cost", "how much")):
            return {"intent": "pricing", "next_role": "proposal-pricing-specialist", "next_action": "prepare approved-price proposal"}
        if any(x in low for x in ("demo", "details", "specification", "feature", "requirement")):
            return {"intent": "solution_interest", "next_role": "solution-consultant", "next_action": "continue discovery and solution fit"}
        if any(x in low for x in ("buy", "order", "proceed", "purchase", "send payment", "payment link")):
            return {"intent": "purchase_intent", "next_role": "negotiator-deal-closer", "next_action": "confirm order terms then create exact payment request"}
        return {"intent": "needs_review", "next_role": "account-executive", "next_action": "continue customer conversation"}

    def crm_snapshot(self):
        return self.crm.dashboard()

    def save_lead(self, lead: dict):
        return self.crm.upsert_lead(dict(lead or {}))

    def save_deal(self, deal: dict):
        return self.crm.upsert_deal(dict(deal or {}))

    @staticmethod
    def pipeline_next(stage: str, *, payment_verified: bool = False):
        stage = str(stage or "").strip().lower()
        if stage not in PIPELINE:
            raise ValueError("unsupported VANIJYA pipeline stage")
        if stage == "closed_won":
            return {"stage": stage, "next": "customer-relationship-manager"}
        if stage == "closed_lost":
            return {"stage": stage, "next": "archive_and_learn"}
        if stage == "payment_pending":
            return {
                "stage": "closed_won" if payment_verified else "payment_pending",
                "next": "customer-relationship-manager" if payment_verified else "verify_payment_from_trusted_source",
            }
        idx = PIPELINE.index(stage)
        return {"stage": stage, "next": PIPELINE[min(idx + 1, len(PIPELINE) - 1)]}

    @staticmethod
    def _money_amount(amount):
        try:
            value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("valid amount is required") from exc
        if value <= 0:
            raise ValueError("amount must be positive")
        return value

    def payment_request(self, *, payee_vpa: str, payee_name: str, amount, order_ref: str, note: str = ""):
        value = self._money_amount(amount)
        money = self.zero_spend.decide("customer_payment", amount=float(value), currency="INR")
        if not money.get("allowed"):
            raise PermissionError("zero-spend policy did not permit incoming customer payment")

        vpa = str(payee_vpa or "").strip()
        name = str(payee_name or "").strip()
        ref = str(order_ref or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{2,256}@[A-Za-z0-9.-]{2,64}", vpa):
            raise ValueError("valid payee UPI VPA is required")
        if not name:
            raise ValueError("payee_name is required")
        if not ref:
            raise ValueError("order_ref is required")

        params = {
            "pa": vpa,
            "pn": name,
            "tr": ref,
            "tn": str(note or ("Payment for " + ref)).strip()[:80],
            "am": format(value, ".2f"),
            "cu": "INR",
        }
        uri = "upi://pay?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        return {
            "payment_request_id": "VAN-" + uuid.uuid4().hex[:16].upper(),
            "order_ref": ref,
            "amount": format(value, ".2f"),
            "currency": "INR",
            "upi_uri": uri,
            "payment_link": uri,
            "qr_payload": uri,
            "qr_instruction": "Render qr_payload as a QR locally/client-side; QR creation itself is not payment proof.",
            "share_text": f"Please pay INR {format(value, '.2f')} for {ref} using the UPI QR/link.",
            "status": "pending_unverified",
            "money_policy": money,
            "verification_required": True,
            "trusted_verification_sources": sorted(TRUSTED_PAYMENT_SOURCES),
        }

    @staticmethod
    def verify_payment(evidence: dict, *, expected_amount=None, expected_order_ref: str = ""):
        evidence = dict(evidence or {})
        source = str(evidence.get("source") or "").strip().lower()
        status = str(evidence.get("status") or "").strip().lower()

        if source in UNTRUSTED_PAYMENT_SOURCES or source not in TRUSTED_PAYMENT_SOURCES:
            return {
                "verified": False,
                "status": "unverified",
                "reason": "evidence is not from a trusted server-side bank/PSP/acquirer/gateway source",
                "source": source or "unknown",
            }
        if status not in {"success", "paid", "captured", "completed"}:
            return {
                "verified": False,
                "status": status or "unknown",
                "reason": "trusted source did not report a successful terminal payment state",
                "source": source,
            }

        if expected_amount is not None:
            try:
                expected = Decimal(str(expected_amount)).quantize(Decimal("0.01"))
                actual = Decimal(str(evidence.get("amount"))).quantize(Decimal("0.01"))
            except (InvalidOperation, TypeError, ValueError):
                return {"verified": False, "status": "unverified", "reason": "payment amount is missing/invalid", "source": source}
            if actual != expected:
                return {
                    "verified": False,
                    "status": "amount_mismatch",
                    "reason": f"received amount {actual} does not match expected {expected}",
                    "source": source,
                }

        expected_ref = str(expected_order_ref or "").strip()
        actual_ref = str(evidence.get("order_ref") or evidence.get("reference") or "").strip()
        if expected_ref and actual_ref != expected_ref:
            return {
                "verified": False,
                "status": "reference_mismatch",
                "reason": "payment reference does not match the expected order",
                "source": source,
            }

        transaction_id = str(evidence.get("transaction_id") or evidence.get("utr") or evidence.get("rrn") or "").strip()
        if not transaction_id:
            return {
                "verified": False,
                "status": "unverified",
                "reason": "trusted payment success lacks transaction/UTR/RRN identifier",
                "source": source,
            }

        return {
            "verified": True,
            "status": "paid_verified",
            "source": source,
            "transaction_id": transaction_id,
            "amount": str(evidence.get("amount") or ""),
            "order_ref": actual_ref,
            "next_stage": "closed_won",
        }

    def automation_blueprint(self):
        return {
            "owner": VANIJYA_HEAD_NAME,
            "product_loop": [
                "ask MANIBHADRA for a product/service opportunity",
                "build zero-spend marketing plan",
                "research only public/consented prospect sources",
                "create and score CRM lead",
                "qualify contact basis and buyer intent",
                "contact through a connected NARAD provider inside an authorized Stable workflow",
                "read inbound reply and route it to the appropriate sales role",
                "run discovery, solution, proposal and negotiation",
                "generate exact-amount UPI request after customer agrees",
                "verify payment from trusted server-side evidence",
                "mark closed-won only after verified payment",
                "hand customer to Customer Relationship Manager",
            ],
            "never": [
                "mass unsolicited spam",
                "buy leads or paid media under zero-spend mode",
                "invent product capabilities, price, testimonials or customer claims",
                "ignore opt-out/suppression",
                "send outgoing money",
                "mark payment complete from screenshot/customer claim/QR generation",
                "bypass NARADA Legal or provider policy",
            ],
        }
