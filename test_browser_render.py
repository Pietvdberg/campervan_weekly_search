import unittest
from unittest.mock import patch
from browser_render import render

class BrowserGuardTests(unittest.TestCase):
    def test_http_rejected_before_browser_import(self):
        with self.assertRaises(ValueError):
            render("http://www.marktplaats.nl/v/auto-s/bestelauto-s/m12345")
    def test_untrusted_domain_rejected(self):
        with self.assertRaises(ValueError):
            render("https://attacker.example/vehicles")
    def test_lookalike_hostname_rejected(self):
        with self.assertRaises(ValueError):
            render("https://marktplaats.nl.attacker.example/van")
if __name__=="__main__": unittest.main()
