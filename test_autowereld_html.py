import unittest
from xml.etree import ElementTree
from autowereld_html import html_to_xml

class HtmlToXmlTests(unittest.TestCase):
    def test_realistic_relative_and_absolute_adverts(self):
        base="https://www.autowereld.nl/rss/peugeot/boxer/"
        page='<html><a href="/peugeot/boxer/l2h2-43922209/details.html">Peugeot Boxer L2H2</a><script>"https://www.autowereld.nl/ford/transit/airco-43913528/details.html"</script></html>'
        xml,stats=html_to_xml(page,base)
        links=[n.text for n in ElementTree.fromstring(xml).findall(".//item/link")]
        self.assertEqual(len(links),2)
        self.assertTrue(stats["conversion_usable"])
    def test_block_page_is_empty(self):
        xml,stats=html_to_xml("<html><title>Access unavailable</title></html>","https://www.autowereld.nl/rss/peugeot/boxer/")
        self.assertFalse(stats["conversion_usable"])
        self.assertEqual(ElementTree.fromstring(xml).findall(".//item"),[])
    def test_other_host_and_catalog_rejected(self):
        page='<a href="https://other.example/peugeot/boxer/l2h2-43922209/details.html">Boxer</a><a href="/peugeot/boxer/">Boxer</a>'
        xml,stats=html_to_xml(page,"https://www.autowereld.nl/peugeot/boxer/")
        self.assertEqual(stats["verified_advert_links"],0)
    def test_no_generic_text_invented(self):
        xml,stats=html_to_xml("<p>Peugeot Boxer L2H2 2018 € 7000</p>","https://www.autowereld.nl/")
        self.assertFalse(stats["conversion_usable"])
if __name__=="__main__":
    unittest.main()
