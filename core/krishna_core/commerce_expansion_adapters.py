from __future__ import annotations

from dataclasses import dataclass, asdict
from urllib.parse import quote, urlencode


@dataclass(frozen=True)
class RequestPlan:
    provider: str
    operation: str
    method: str
    url: str
    body: dict | None
    required_scopes: tuple[str,...]
    requires_connection: bool
    external_write: bool
    zero_spend_allowed: bool
    notes: tuple[str,...]=()

    def as_dict(self):
        row=asdict(self)
        row["required_scopes"]=list(self.required_scopes)
        row["notes"]=list(self.notes)
        return row


class CommerceExpansionAdapterRegistry:
    """Concrete request contracts for the future-commerce modules.

    This class deliberately plans requests only. Credentials are never stored
    here and network execution must go through an approved connector/provider
    runtime. A plan is not proof that an account, seller profile or network
    participant registration exists.
    """

    def providers(self):
        return (
            "ondc","ebay","etsy","google_merchant","google_search_console",
            "pinterest","medusa","ucp",
        )

    @staticmethod
    def _required(value,name):
        text=str(value or "").strip()
        if not text:
            raise ValueError(f"{name} is required")
        return text

    def plan(self,provider:str,operation:str,payload:dict|None=None)->dict:
        p=str(provider or "").strip().lower()
        op=str(operation or "").strip().lower()
        row=dict(payload or {})
        if p=="ondc":return self._ondc(op,row)
        if p=="ebay":return self._ebay(op,row)
        if p=="etsy":return self._etsy(op,row)
        if p=="google_merchant":return self._merchant(op,row)
        if p=="google_search_console":return self._search_console(op,row)
        if p=="pinterest":return self._pinterest(op,row)
        if p=="medusa":return self._medusa(op,row)
        if p=="ucp":return self._ucp(op,row)
        raise ValueError("unsupported commerce expansion provider")

    def _ondc(self,op,row):
        if op=="registry_lookup":
            env=str(row.get("environment") or "prod").strip().lower()
            if env not in {"preprod","prod"}:raise ValueError("ONDC environment must be preprod or prod")
            host="https://preprod.registry.ondc.org" if env=="preprod" else "https://prod.registry.ondc.org"
            return RequestPlan(
                "ondc",op,"POST",host+"/v2.0/lookup",
                {
                    "country":str(row.get("country") or "IND"),
                    "domain":self._required(row.get("domain"),"domain"),
                },
                (),False,False,True,
                ("Official ONDC registry v2 lookup.","Signed Authorization may be required by current registry policy."),
            ).as_dict()
        if op=="buyer_search":
            # Production ONDC gateway search is a signed network-participant operation.
            domain=self._required(row.get("domain"),"domain")
            context=dict(row.get("context") or {})
            message=dict(row.get("message") or {})
            return RequestPlan(
                "ondc",op,"POST","https://prod.gateway.ondc.org/search",
                {"context":{**context,"domain":context.get("domain") or domain},"message":message},
                (),True,True,True,
                ("Requires valid ONDC Network Participant registration, subscriber identity and protocol signing.",
                 "Plan only; do not fabricate registry membership or signing keys."),
            ).as_dict()
        if op=="participant_readiness":
            return {
                "provider":"ondc","operation":op,"external_write":False,"zero_spend_allowed":True,
                "requirements":[
                    "ONDC portal/network-participant onboarding",
                    "registered subscriber_id / FQDN","valid SSL certificate",
                    "Ed25519 signing keys","X25519 encryption keys",
                    "/on_subscribe callback","registry lookup verification",
                    "domain-specific ONDC protocol conformance",
                ],
                "ready":False,
                "reason":"readiness becomes true only after real registration and conformance evidence are supplied",
            }
        raise ValueError("unsupported ONDC operation")

    def _ebay(self,op,row):
        base="https://api.ebay.com/sell/inventory/v1"
        scope=("https://api.ebay.com/oauth/api_scope/sell.inventory",)
        if op=="inventory_item_put":
            sku=quote(self._required(row.get("sku"),"sku"),safe="")
            return RequestPlan("ebay",op,"PUT",f"{base}/inventory_item/{sku}",dict(row.get("body") or {}),scope,True,True,True,
                ("Official eBay Sell Inventory API.","Seller must satisfy eBay business-policy and inventory-location prerequisites.")).as_dict()
        if op=="offer_create":
            return RequestPlan("ebay",op,"POST",f"{base}/offer",dict(row.get("body") or {}),scope,True,True,True,
                ("Creates an unpublished eBay offer.","Publishing may create marketplace fees; check exact seller economics before publish.")).as_dict()
        if op=="offer_publish":
            offer=quote(self._required(row.get("offer_id"),"offer_id"),safe="")
            return RequestPlan("ebay",op,"POST",f"{base}/offer/{offer}/publish",None,scope,True,True,False,
                ("Live listing publication can incur marketplace fees and is blocked by KRISHNA zero-spend until the exact fee path is verified as zero outgoing spend.")).as_dict()
        if op=="inventory_get":
            sku=quote(self._required(row.get("sku"),"sku"),safe="")
            return RequestPlan("ebay",op,"GET",f"{base}/inventory_item/{sku}",None,scope,True,False,True).as_dict()
        raise ValueError("unsupported eBay operation")

    def _etsy(self,op,row):
        base="https://api.etsy.com/v3/application"
        shop=quote(self._required(row.get("shop_id"),"shop_id"),safe="")
        if op=="listings_get":
            return RequestPlan("etsy",op,"GET",f"{base}/shops/{shop}/listings/active",None,("listings_r",),True,False,True).as_dict()
        if op=="draft_listing_create":
            return RequestPlan(
                "etsy",op,"POST",f"{base}/shops/{shop}/listings",dict(row.get("body") or {}),
                ("listings_w",),True,True,False,
                ("Official Etsy Open API v3 createDraftListing route.",
                 "Etsy selling/listing fee paths are treated as outgoing spend; automatic listing writes remain blocked under zero-spend."),
            ).as_dict()
        raise ValueError("unsupported Etsy operation")

    def _merchant(self,op,row):
        account=quote(self._required(row.get("account_id"),"account_id"),safe="")
        base=f"https://merchantapi.googleapis.com/products/v1/accounts/{account}"
        scope=("https://www.googleapis.com/auth/content",)
        if op=="products_list":
            return RequestPlan("google_merchant",op,"GET",f"{base}/products",None,scope,True,False,True,
                ("Official Google Merchant Products API.","Use processed product status/issues to verify free-listing eligibility.")).as_dict()
        if op=="product_insert":
            source=self._required(row.get("data_source"),"data_source")
            q=urlencode({"dataSource":source})
            return RequestPlan("google_merchant",op,"POST",f"{base}/productInputs:insert?{q}",dict(row.get("body") or {}),scope,True,True,True,
                ("Requires an API-type Merchant data source.","KRISHNA permits only free-listing use; paid Shopping Ads remain disabled.")).as_dict()
        if op=="data_source_create":
            return RequestPlan("google_merchant",op,"POST",f"{base}/dataSources",dict(row.get("body") or {}),scope,True,True,True,
                ("Create only for a verified owned Merchant Center account and free-listings path.")).as_dict()
        raise ValueError("unsupported Google Merchant operation")

    def _search_console(self,op,row):
        if op!="search_analytics_query":
            raise ValueError("unsupported Search Console operation")
        site=self._required(row.get("site_url"),"site_url")
        return RequestPlan(
            "google_search_console",op,"POST",
            "https://www.googleapis.com/webmasters/v3/sites/"+quote(site,safe="")+"/searchAnalytics/query",
            dict(row.get("body") or {}),
            ("https://www.googleapis.com/auth/webmasters.readonly",),
            True,False,True,
            ("Read-only Search Console analytics for an owned/authorized property.",),
        ).as_dict()

    def _pinterest(self,op,row):
        base="https://api.pinterest.com/v5"
        scopes=("catalogs:read","catalogs:write")
        if op=="catalogs_list":
            return RequestPlan("pinterest",op,"GET",f"{base}/catalogs",None,("catalogs:read",),True,False,True).as_dict()
        if op=="feeds_list":
            return RequestPlan("pinterest",op,"GET",f"{base}/catalogs/feeds",None,("catalogs:read",),True,False,True).as_dict()
        if op=="feed_create":
            return RequestPlan("pinterest",op,"POST",f"{base}/catalogs/feeds",dict(row.get("body") or {}),scopes,True,True,True,
                ("Organic catalog management only.","Pinterest ad/campaign endpoints are intentionally excluded under zero-spend.")).as_dict()
        if op=="items_batch":
            return RequestPlan("pinterest",op,"POST",f"{base}/catalogs/items/batch",dict(row.get("body") or {}),scopes,True,True,True,
                ("Near-real-time catalog updates; organic shopping only.","Business account/domain requirements must already be satisfied.")).as_dict()
        raise ValueError("unsupported Pinterest operation")

    def _medusa(self,op,row):
        root=str(row.get("base_url") or "http://127.0.0.1:9000").rstrip("/")
        if not (root.startswith("http://127.0.0.1") or root.startswith("http://localhost") or bool(row.get("owner_authorized_remote"))):
            raise PermissionError("remote Medusa host requires explicit owner authorization")
        if op=="store_products":
            return RequestPlan("medusa",op,"GET",root+"/store/products",None,(),False,False,True,
                ("Medusa v2 Store API.",)).as_dict()
        if op=="admin_products":
            return RequestPlan("medusa",op,"GET",root+"/admin/products",None,(),True,False,True,
                ("Medusa v2 Admin API; admin authentication is required.",)).as_dict()
        if op=="admin_product_create":
            return RequestPlan("medusa",op,"POST",root+"/admin/products",dict(row.get("body") or {}),(),True,True,True,
                ("Local/self-hosted commerce-core write only; no paid hosting purchase authority.",)).as_dict()
        raise ValueError("unsupported Medusa operation")

    def _ucp(self,op,row):
        business=str(row.get("business_url") or "").rstrip("/")
        if op=="discover":
            business=self._required(business,"business_url")
            return RequestPlan("ucp",op,"GET",business+"/.well-known/ucp",None,(),False,False,True,
                ("UCP profile discovery only.",)).as_dict()
        if op=="merchant_profile_template":
            endpoint=self._required(row.get("endpoint"),"endpoint")
            return {
                "provider":"ucp","operation":op,"external_write":False,"zero_spend_allowed":True,
                "profile":{
                    "ucp":{
                        "version":str(row.get("version") or "2026-08-25"),
                        "services":{
                            "dev.ucp.shopping":[{
                                "version":str(row.get("version") or "2026-08-25"),
                                "transport":"mcp",
                                "endpoint":endpoint,
                            }]
                        },
                        "capabilities":{
                            "dev.ucp.shopping.catalog.search":[{
                                "version":str(row.get("version") or "2026-08-25"),
                            }]
                        },
                    }
                },
                "checkout_rule":"agents may assist, but order placement/payment must hand off to a trusted deterministic user-facing checkout; KRISHNA has no outgoing-payment authority",
            }
        raise ValueError("unsupported UCP operation")
