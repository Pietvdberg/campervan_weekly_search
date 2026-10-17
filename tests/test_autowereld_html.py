import unittest
from xml.etree import ElementTree

from campervan_search.autowereld_html import html_to_xml


class HtmlToXmlTests(unittest.TestCase):
    def test_response_identity_distinguishes_real_rss_from_fallback(self):
        from campervan_search.autowereld_html import response_identity

        rss = (
            "<rss><channel><item><link>https://www.autowereld"
            ".nl/peugeot/boxer/l2h2-43922209/details.html</li"
            "nk></item></channel></rss>"
        )
        fallback = (
            "<html><head><title>Service unavailable</title></head><body>Try"
            " again</body></html>"
        )
        actual = response_identity(rss, "application/rss+xml")
        blocked = response_identity(fallback, "text/html")
        self.assertEqual(actual["response_class"], "actual_rss")
        self.assertTrue(actual["has_rss_items"])
        self.assertTrue(actual["contains_vehicle_detail_url"])
        self.assertEqual(blocked["response_class"], "html_no_links")
        self.assertEqual(blocked["html_title"], "Service unavailable")
        self.assertFalse(blocked["contains_vehicle_detail_url"])
        self.assertNotEqual(actual["sha256_prefix"], blocked["sha256_prefix"])

    def test_response_identity_does_not_expose_html_body(self):
        from campervan_search.autowereld_html import response_identity

        doc = (
            "<html><title>Fallback</title><p>private diagnostic"
            " token</p></html>"
        )
        item = response_identity(doc, "text/html")
        self.assertNotIn("private diagnostic token", str(item))
        self.assertEqual(len(item["sha256_prefix"]), 16)

    def test_realistic_relative_and_absolute_adverts(self):
        base = "https://www.autowereld.nl/rss/peugeot/boxer/"
        page = (
            '<html><a href="/peugeot/boxer/l2h2-43922209/'
            'details.html">Peugeot Boxer '
            'L2H2</a><script>"https://www.autowereld.nl/f'
            'ord/transit/airco-43913528/details.html"</sc'
            "ript></html>"
        )
        xml, stats = html_to_xml(page, base)
        links = [
            n.text for n in ElementTree.fromstring(xml).findall(".//item/link")
        ]
        self.assertEqual(len(links), 2)
        self.assertTrue(stats["conversion_usable"])

    def test_block_page_is_empty(self):
        xml, stats = html_to_xml(
            "<html><title>Access unavailable</title></html>",
            "https://www.autowereld.nl/rss/peugeot/boxer/",
        )
        self.assertFalse(stats["conversion_usable"])
        self.assertEqual(ElementTree.fromstring(xml).findall(".//item"), [])

    def test_other_host_and_catalog_rejected(self):
        page = (
            '<a href="https://other.example/peugeot/boxer'
            '/l2h2-43922209/details.html">Boxer</a><a '
            'href="/peugeot/boxer/">Boxer</a>'
        )
        xml, stats = html_to_xml(
            page, "https://www.autowereld.nl/peugeot/boxer/"
        )
        self.assertEqual(stats["verified_advert_links"], 0)

    def test_no_generic_text_invented(self):
        xml, stats = html_to_xml(
            "<p>Peugeot Boxer L2H2 2018 € 7000</p>",
            "https://www.autowereld.nl/",
        )
        self.assertFalse(stats["conversion_usable"])


if __name__ == "__main__":
    unittest.main()
