from krishna_core.commerce_expansion_adapters import CommerceExpansionAdapterRegistry


def test_provider_inventory_is_explicit():
    reg=CommerceExpansionAdapterRegistry()
    assert set(reg.providers())=={
        "ondc","ebay","etsy","google_merchant","google_search_console",
        "pinterest","medusa","ucp",
    }


def test_ondc_registry_and_participant_readiness_are_fail_closed():
    reg=CommerceExpansionAdapterRegistry()
    lookup=reg.plan("ondc","registry_lookup",{"environment":"prod","domain":"ONDC:RET10"})
    assert lookup["method"]=="POST"
    assert lookup["url"]=="https://prod.registry.ondc.org/v2.0/lookup"
    assert lookup["external_write"] is False
    readiness=reg.plan("ondc","participant_readiness",{})
    assert readiness["ready"] is False
    assert "Ed25519 signing keys" in readiness["requirements"]


def test_ondc_buyer_search_requires_real_network_participant_connection():
    out=CommerceExpansionAdapterRegistry().plan(
        "ondc","buyer_search",
        {"domain":"ONDC:RET10","context":{"action":"search"},"message":{"intent":{}}},
    )
    assert out["url"]=="https://prod.gateway.ondc.org/search"
    assert out["requires_connection"] is True
    assert out["external_write"] is True
    assert any("registration" in note for note in out["notes"])


def test_ebay_publish_is_blocked_by_zero_spend_until_fee_path_is_verified_free():
    reg=CommerceExpansionAdapterRegistry()
    item=reg.plan("ebay","inventory_item_put",{"sku":"SKU 1","body":{"availability":{}}})
    assert "/inventory_item/SKU%201" in item["url"]
    assert item["zero_spend_allowed"] is True
    publish=reg.plan("ebay","offer_publish",{"offer_id":"OFFER-1"})
    assert publish["external_write"] is True
    assert publish["zero_spend_allowed"] is False


def test_etsy_listing_write_is_researchable_but_not_zero_spend_executable():
    reg=CommerceExpansionAdapterRegistry()
    read=reg.plan("etsy","listings_get",{"shop_id":"123"})
    assert read["external_write"] is False
    draft=reg.plan("etsy","draft_listing_create",{"shop_id":"123","body":{"title":"Test"}})
    assert draft["url"].endswith("/shops/123/listings")
    assert draft["zero_spend_allowed"] is False


def test_google_merchant_free_listing_request_contract():
    out=CommerceExpansionAdapterRegistry().plan(
        "google_merchant","product_insert",
        {"account_id":"123","data_source":"accounts/123/dataSources/456","body":{"offerId":"sku-1"}},
    )
    assert out["url"].startswith("https://merchantapi.googleapis.com/products/v1/accounts/123/productInputs:insert?")
    assert out["external_write"] is True
    assert out["zero_spend_allowed"] is True
    assert "https://www.googleapis.com/auth/content" in out["required_scopes"]


def test_search_console_is_read_only():
    out=CommerceExpansionAdapterRegistry().plan(
        "google_search_console","search_analytics_query",
        {"site_url":"https://example.com/","body":{"startDate":"2026-09-01","endDate":"2026-09-25"}},
    )
    assert out["method"]=="POST"
    assert out["external_write"] is False
    assert "/searchAnalytics/query" in out["url"]
    assert "webmasters.readonly" in out["required_scopes"][0]


def test_pinterest_catalogs_exclude_paid_ads():
    reg=CommerceExpansionAdapterRegistry()
    feed=reg.plan("pinterest","feed_create",{"body":{"name":"Products"}})
    assert feed["url"]=="https://api.pinterest.com/v5/catalogs/feeds"
    assert feed["zero_spend_allowed"] is True
    try:
        reg.plan("pinterest","campaign_create",{})
    except ValueError:
        pass
    else:
        raise AssertionError("Pinterest paid-ad operation was unexpectedly exposed")


def test_medusa_defaults_to_local_self_hosted_and_remote_requires_owner_authority():
    reg=CommerceExpansionAdapterRegistry()
    local=reg.plan("medusa","store_products",{})
    assert local["url"]=="http://127.0.0.1:9000/store/products"
    assert local["requires_connection"] is False
    try:
        reg.plan("medusa","admin_products",{"base_url":"https://commerce.example.com"})
    except PermissionError:
        pass
    else:
        raise AssertionError("remote Medusa access was not owner-gated")


def test_ucp_discovery_and_profile_template_never_authorize_payment():
    reg=CommerceExpansionAdapterRegistry()
    discover=reg.plan("ucp","discover",{"business_url":"https://shop.example.com"})
    assert discover["url"]=="https://shop.example.com/.well-known/ucp"
    profile=reg.plan("ucp","merchant_profile_template",{"endpoint":"https://shop.example.com/mcp"})
    assert profile["external_write"] is False
    assert "deterministic" in profile["checkout_rule"]
    assert "no outgoing-payment authority" in profile["checkout_rule"]
