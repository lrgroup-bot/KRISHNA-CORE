import unittest

from krishna_core.affiliate_intent import AffiliateIntentEngine
from krishna_core.manibhadra_commerce import ManibhadraCommerce
from krishna_core.marketplace_adapters import MarketplaceAdapterRegistry
from krishna_core.plugin_runtime import PluginRegistry
import tempfile


class AffiliateIntentTests(unittest.TestCase):
    def test_private_unconsented_signal_is_rejected(self):
        e=AffiliateIntentEngine()
        out=e.intent_summary([
            {"source":"public-post","text":"Looking for a smartwatch under 5000","public_or_consented":True},
            {"source":"private-history","text":"secret browsing history","public_or_consented":False},
        ])
        self.assertTrue(out["ready_for_product_match"])
        self.assertEqual(len(out["accepted_signals"]),1)
        self.assertEqual(len(out["rejected_signals"]),1)
        self.assertIn("smartwatch",out["keywords"])

    def test_amazon_exact_tagged_link_waits_for_tracking_id(self):
        e=AffiliateIntentEngine()
        waiting=e.referral_plan(
            provider="amazon",channel="approved_social",product_name="Watch",
            product_url="https://www.amazon.in/dp/ABC123"
        )
        self.assertFalse(waiting["ready"])
        self.assertEqual(waiting["connection_state"],"WAITING_FOR_CONNECTION")
        ready=e.referral_plan(
            provider="amazon",channel="approved_social",product_name="Watch",
            product_url="https://www.amazon.in/dp/ABC123",tracking_id="mytag-21",
            estimated_price=1000,commission_rate=0.05,
        )
        self.assertTrue(ready["ready"])
        self.assertIn("tag=mytag-21",ready["link"])
        self.assertEqual(ready["estimated_commission"],50.0)
        self.assertIn("commission",ready["disclosure"].lower())

    def test_amazon_blocks_unapproved_direct_message_by_default(self):
        e=AffiliateIntentEngine()
        out=e.referral_plan(
            provider="amazon",channel="whatsapp",product_name="Watch",
            product_url="https://www.amazon.in/dp/ABC123",tracking_id="mytag-21",
        )
        self.assertFalse(out["ready"])
        self.assertIn("not permitted",out["reason"])

    def test_flipkart_requires_official_deep_link(self):
        e=AffiliateIntentEngine()
        out=e.referral_plan(provider="flipkart",channel="approved_website",product_name="Shoes")
        self.assertFalse(out["ready"])
        self.assertEqual(out["connection_state"],"WAITING_FOR_CONNECTION")
        out=e.referral_plan(
            provider="flipkart",channel="approved_website",product_name="Shoes",
            official_deep_link="https://affiliate.flipkart.example/deep-link"
        )
        self.assertTrue(out["ready"])

    def test_alibaba_is_global_b2b_and_waiting_for_connection(self):
        m=ManibhadraCommerce()
        s=m.status()
        self.assertEqual(s["platforms"]["alibaba"]["market_type"],"B2B_wholesale_global")
        self.assertTrue(s["platforms"]["alibaba"]["connection_required_for_writes"])
        r=MarketplaceAdapterRegistry()
        self.assertEqual(r.get("alibaba","product_research")["mode"],"public_research")
        self.assertTrue(r.get("alibaba","listing_put")["approval_required"])

    def test_pending_connectors_are_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            p=PluginRegistry(td)
            rows={x["id"]:x for x in p.list()}
            for pid in ("alibaba-global","amazon-associates","flipkart-affiliate"):
                self.assertIn(pid,rows)
                self.assertFalse(rows[pid]["enabled"])


if __name__=="__main__":
    unittest.main()
