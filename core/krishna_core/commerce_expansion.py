from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CommerceExpansion:
    id: str
    name: str
    category: str
    research: bool
    external_write: bool
    zero_spend_status: str
    connection_required: bool
    owner: str
    notes: tuple[str, ...]

    def as_dict(self):
        row=asdict(self);row["notes"]=list(self.notes);return row


EXPANSIONS=(
    CommerceExpansion(
        "ondc","ONDC Buyer / Seller Integration","marketplace",True,True,
        "READY_FOR_RESEARCH__WRITES_WAIT_FOR_VERIFIED_FREE_CONNECTION",True,"MANIBHADRA",
        ("use official ONDC participant/network contracts only",
         "do not claim seller/buyer network access until credentials and participant status are verified",
         "any route requiring fees remains blocked by zero-spend policy")),
    CommerceExpansion(
        "ebay","eBay Worldwide Seller Integration","marketplace",True,True,
        "READY_FOR_RESEARCH__WRITES_WAIT_FOR_CONNECTION",True,"MANIBHADRA",
        ("prefer official eBay APIs","marketplace listing/order writes require connected seller authority",
         "fees or paid seller services are not automatically authorized")),
    CommerceExpansion(
        "etsy","Etsy International Selling","marketplace",True,True,
        "RESEARCH_ONLY_WHILE_LISTING_FEES_OR_OTHER_SPEND_APPLY",True,"MANIBHADRA",
        ("research is allowed","listing or transaction paths that require outgoing fees remain blocked",
         "do not bypass Etsy platform rules or fees")),
    CommerceExpansion(
        "google_merchant_free","Google Merchant Free Listings","discovery",True,True,
        "FREE_ROUTE_CANDIDATE__WAIT_FOR_CONNECTION",True,"MANIBHADRA",
        ("use Google Merchant official feeds/APIs","free listings may be used when account eligibility is verified",
         "paid Shopping ads remain disabled")),
    CommerceExpansion(
        "google_search_console","Google Search Console","analytics",True,False,
        "FREE_READ_ROUTE__WAIT_FOR_CONNECTION",True,"MANIBHADRA",
        ("read owned-site search performance only","no credential material leaves local secret storage")),
    CommerceExpansion(
        "pinterest_shopping","Pinterest Organic Shopping","social_commerce",True,True,
        "ORGANIC_FREE_ROUTE_CANDIDATE__WAIT_FOR_CONNECTION",True,"VANIJYA",
        ("use owned/authorized business account and official interfaces",
         "paid promotion remains disabled")),
    CommerceExpansion(
        "organic_social","Free / Organic Social Commerce","social_commerce",True,True,
        "ZERO_SPEND_ROUTE",True,"VANIJYA",
        ("all external sends route through NARAD","honor consent, channel policy and opt-outs",
         "no paid boosts, ads, purchased leads or spam")),
    CommerceExpansion(
        "supplier_funded_dropshipping","Supplier-Funded Dropshipping","fulfilment",True,True,
        "ALLOWED_ONLY_IF_NO_OUTGOING_MONEY",True,"MANIBHADRA",
        ("no inventory purchase, supplier advance or deposit",
         "supplier must fund/absorb fulfilment where model requires zero outgoing spend",
         "customer and supplier terms must be truthful and documented")),
    CommerceExpansion(
        "b2b_rfq","B2B RFQ Matching","b2b",True,True,
        "ZERO_SPEND_RESEARCH_AND_CONSENTED_OUTREACH",True,"VANIJYA",
        ("GARUDA performs public research","VANIJYA handles qualified outreach",
         "marketplace writes require official connected access")),
    CommerceExpansion(
        "importer_distributor_discovery","Global Importer / Distributor Discovery","b2b",True,False,
        "ZERO_SPEND_PUBLIC_RESEARCH",False,"GARUDA",
        ("use public and lawful sources","do not bypass login walls or platform anti-scraping controls",
         "contact details must have a legitimate public-business or consent basis")),
    CommerceExpansion(
        "ai_commerce_ucp","AI-Commerce / UCP Readiness","protocol",True,True,
        "ADAPTER_ONLY_UNTIL_PROTOCOL_AND_COUNTERPARTY_VERIFIED",True,"MANIBHADRA",
        ("machine-readable product/service catalogue may be prepared",
         "agent-commerce writes/payments stay disabled until verified protocol, authority and zero-spend compatibility",
         "no autonomous stablecoin, x402 or other outgoing payment execution")),
    CommerceExpansion(
        "medusa","Self-Hosted Medusa Commerce Core","storefront",True,True,
        "LOCAL_SELF_HOSTED_CANDIDATE__NO_PAID_HOSTING",False,"MANIBHADRA",
        ("use as an open-source commerce-core candidate","local/self-hosted testing is allowed",
         "domain, hosting or paid service purchase remains blocked")),
)


class CommerceExpansionRegistry:
    def list(self):
        return [x.as_dict() for x in EXPANSIONS]

    def get(self, expansion_id: str):
        key=str(expansion_id or "").strip().lower()
        for row in EXPANSIONS:
            if row.id==key:return row.as_dict()
        raise KeyError(key)

    def plan(self, expansion_id: str, *, connected: bool=False, free_verified: bool=False):
        row=self.get(expansion_id)
        blockers=[]
        if row["connection_required"] and not connected:
            blockers.append("WAITING_FOR_CONNECTION")
        if row["external_write"] and not free_verified:
            blockers.append("FREE_ROUTE_NOT_VERIFIED")
        if "RESEARCH_ONLY" in row["zero_spend_status"]:
            blockers.append("OUTGOING_COST_PATH_BLOCKED")
        return {
            "module":row,
            "research_allowed":bool(row["research"]),
            "external_write_allowed":bool(row["external_write"] and connected and free_verified and "RESEARCH_ONLY" not in row["zero_spend_status"]),
            "blockers":blockers,
            "zero_spend":True,
            "paid_fallback":False,
        }

    def status(self):
        return {
            "schema":"krishna.manibhadra.commerce-expansion.v1",
            "count":len(EXPANSIONS),
            "modules":self.list(),
            "zero_spend":True,
            "paid_fallback":False,
        }
