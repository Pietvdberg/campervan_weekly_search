import unittest
from unittest.mock import Mock

from camper_pipeline import evaluate


class InputValidationTests(unittest.TestCase):
    def test_bad_batch_is_rejected_before_lookup(self):
        from test_camper_pipeline import ScreeningTests
        lookup = Mock()
        for bad in (None, [], {"candidates": {}}, {"candidates": [ScreeningTests().example(), "bad"]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                evaluate(bad, lookup)
        lookup.assert_not_called()

    def test_truthy_strings_cannot_be_check_evidence(self):
        with self.assertRaisesRegex(ValueError, "checks"):
            evaluate({"candidates": [{"checks": {"high_roof": "yes"}}]})

    def test_nonfinite_or_nonnumeric_amounts_rejected(self):
        for value in (float("nan"), float("inf"), -1, "5000", True):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "price_incl_vat"):
                evaluate({"candidates": [{"price_incl_vat": value}]})
