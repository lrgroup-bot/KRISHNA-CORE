import unittest

from krishna_core.commerce_expansion_adapters import CommerceExpansionAdapterRegistry


class CommerceExpansionAdapterTests(unittest.TestCase):
    def test_provider_inventory_is_explicit(self):
        self.assertEqual(set(CommerceExpansionAdapterRegistry().providers()),{
            "ondc","ebay","etsy","google_merchant","google_search_console",
            "pinterest","medusa","ucp",
        })

    def test_ondc_registry_and_participant_readiness_are_fail_closed(self):
        reg=CommerceExpansionAdapterRegistry()
        lookup=reg.plan("ondc","registry_lookup",{"environment":"prod","domain":"ONDC:RET10"})
        self.assertEqual(lookup["method"],"POST")
        self.assertEqual(lookup["url"],"https://prod.registry.ondc.org/v2.0/lookup")
        self.assertFalse(lookup["external_write"])
        readiness=reg.plan("ondc","participant_readiness",{})
        self.assertFalse(readiness["ready"])
        self.assertIn("Ed25519 signing keys",readiness["requirements"])

    def test_ondc_buyer_search_requires_real_network_participant_connection(self):
        out=CommerceExpansionAdapterRegistry().plan(
            "ondc","buyer_search",
            {"domain":"ONDC:RET10","context":{"action":"search"},"message":{"intent":{}}},
        )
        self.assertEqual(out["url"],"https://prod.gateway.ondc.org/search")
        self.assertTrue(out["requires_connection"])
        self.assertTrue(out["external_write"])
        self.assertTrue(any("registration" in note for note in out["notes"]))

    def test_ebay_publish_is_blocked_by_zero_spend_until_fee_path_is_verified_free(self):
        reg=CommerceExpansionAdapterRegistry()
        item=reg.plan("ebay","inventory_item_put",{"sku":"SKU 1","body":{"availability":{}}})
        self.assertIn("/inventory_item/SKU%201",item["url"])
        self.assertTrue(item["zero_spend_allowed"])
        publish=reg.plan("ebay","offer_publish",{"offer_id":"OFFER-1"})
        self.assertTrue(publish["external_write"])
        self.assertFalse(publish["zero_spend_allowed"])

    def test_etsy_listing_write_is_not_zero_spend_executable(self):
        reg=CommerceExpansionAdapterRegistry()
        self.assertFalse(reg.plan("etsy","listings_get",{"shop_id":"123"})["external_write"])
        draft=reg.plan("etsy","draft_listing_create",{"shop_id":"123","body":{"title":"Test"}})
        self.assertTrue(draft["url"].endswith("/shops/123/listings"))
        self.assertFalse(draft["zero_spend_allowed"])

    def test_google_merchant_free_listing_request_contract(self):
        out=CommerceExpansionAdapterRegistry().plan(
            "google_merchant","product_insert",
            {"account_id":"123","data_source":"accounts/123/dataSources/456","body":{"offerId":"sku-1"}},
        )
        self.assertTrue(out["url"].startswith("https://merchantapi.googleapis.com/products/v1/accounts/123/productInputs:insert?"))
        self.assertTrue(out["external_write"])
        self.assertTrue(out["zero_spend_allowed"])
        self.assertIn("https://www.googleapis.com/auth/content",out["required_scopes"])

    def test_search_console_is_read_only(self):
        out=CommerceExpansionAdapterRegistry().plan(
            "google_search_console","search_analytics_query",
            {"site_url":"https://example.com/","body":{"startDate":"2026-09-01","endDate":"2026-09-25"}},
        )
        self.assertEqual(out["method"],"POST")
        self.assertFalse(out["external_write"])
        self.assertIn("/searchAnalytics/query",out["url"])
        self.assertIn("webmasters.readonly",out["required_scopes"][0])

    def test_pinterest_catalogs_exclude_paid_ads(self):
        reg=CommerceExpansionAdapterRegistry()
        feed=reg.plan("pinterest","feed_create",{"body":{"name":"Products"}})
        self.assertEqual(feed["url"],"https://api.pinterest.com/v5/catalogs/feeds")
        self.assertTrue(feed["zero_spend_allowed"])
        with self.assertRaises(ValueError):
            reg.plan("pinterest","campaign_create",{})

    def test_medusa_defaults_local_and_remote_requires_owner_authority(self):
        reg=CommerceExpansionAdapterRegistry()
        local=reg.plan("medusa","store_products",{})
        self.assertEqual(local["url"],"http://127.0.0.1:9000/store/products")
        self.assertFalse(local["requires_connection"])
        with self.assertRaises(PermissionError):
            reg.plan("medusa","admin_products",{"base_url":"https://commerce.example.com"})

    def test_ucp_discovery_and_profile_template_never_authorize_payment(self):
        reg=CommerceExpansionAdapterRegistry()
        discover=reg.plan("ucp","discover",{"business_url":"https://shop.example.com"})
        self.assertEqual(discover["url"],"https://shop.example.com/.well-known/ucp")
        profile=reg.plan("ucp","merchant_profile_template",{"endpoint":"https://shop.example.com/mcp"})
        self.assertFalse(profile["external_write"])
        self.assertIn("deterministic",profile["checkout_rule"])
        self.assertIn("no outgoing-payment authority",profile["checkout_rule"])


if __name__=="__main__":
    unittest.main()
