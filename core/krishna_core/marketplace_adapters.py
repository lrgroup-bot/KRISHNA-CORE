from __future__ import annotations

from dataclasses import dataclass,asdict


@dataclass(frozen=True)
class MarketplaceOperation:
    provider:str
    operation:str
    mutating:bool
    approval_required:bool
    auth:str
    mode:str
    def as_dict(self):return asdict(self)


class MarketplaceAdapterRegistry:
    """Marketplace capability truth; no credential or browser bypasses."""

    def __init__(self):
        self._items={}
        for row in (
            MarketplaceOperation("amazon","catalog_search",False,False,"sp_api_oauth","official_api"),
            MarketplaceOperation("amazon","listing_get",False,False,"sp_api_oauth","official_api"),
            MarketplaceOperation("amazon","listing_put",True,True,"sp_api_oauth","official_api"),
            MarketplaceOperation("amazon","order_search",False,False,"sp_api_oauth","official_api"),
            MarketplaceOperation("amazon","shipment_confirm",True,True,"sp_api_oauth","official_api"),
            MarketplaceOperation("flipkart","listing_get",False,False,"oauth","official_api"),
            MarketplaceOperation("flipkart","listing_create",True,True,"oauth","official_api"),
            MarketplaceOperation("flipkart","listing_update",True,True,"oauth","official_api"),
            MarketplaceOperation("flipkart","inventory_update",True,True,"oauth","official_api"),
            MarketplaceOperation("flipkart","orders_search",False,False,"oauth","official_api"),
            MarketplaceOperation("meesho","seller_portal_read",False,False,"owner_session","authorized_browser"),
            MarketplaceOperation("meesho","seller_portal_write",True,True,"owner_session","authorized_browser"),
            MarketplaceOperation("alibaba","product_research",False,False,"none","public_research"),
            MarketplaceOperation("alibaba","rfq_research",False,False,"none","public_research"),
            MarketplaceOperation("alibaba","listing_get",False,False,"alibaba_open_api_oauth","official_api_after_connection"),
            MarketplaceOperation("alibaba","listing_put",True,True,"alibaba_open_api_oauth","official_api_after_connection"),
            MarketplaceOperation("alibaba","order_search",False,False,"alibaba_open_api_oauth","official_api_after_connection"),
            MarketplaceOperation("alibaba","rfq_reply",True,True,"seller_account","seller_portal_or_verified_api"),
        ):
            self._items[(row.provider,row.operation)]=row

    def get(self,provider,operation):
        key=(str(provider).lower().strip(),str(operation).lower().strip())
        if key not in self._items:raise KeyError("marketplace operation not registered")
        return self._items[key].as_dict()

    def list(self):return [self._items[k].as_dict() for k in sorted(self._items)]
