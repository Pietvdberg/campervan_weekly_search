import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from campervan_search import rdw_lookup as rdw


class RdwTests(unittest.TestCase):
    def response(self, rows):
        return {
            "status": "ok",
            "records": rows,
            "source": "https://example.test/rdw",
        }

    def test_unknown_plate_is_failure(self):
        with patch.object(rdw, "fetch", return_value=self.response([])):
            self.assertEqual(rdw.lookup("AB-123-C")["status"], "error")

    def test_catalogue_failure_is_not_complete_success(self):
        def fetch(dataset, value):
            if dataset == "vehicle":
                return self.response([{"kenteken": value}])
            if dataset == "defects":
                return self.response(
                    [
                        {
                            "gebrek_identificatie": "123",
                            "meld_datum_door_keuringsinstantie": None,
                        }
                    ]
                )
            return {"status": "error", "error": "HTTP 503"}

        with patch.object(rdw, "fetch", side_effect=fetch):
            result = rdw.lookup("AB123C")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["defect_catalogue_errors"][0]["code"], "123")
        self.assertIsNone(
            result["apk_defect_summary"]["entries"][0]["inspection_date"]
        )

    def test_empty_catalogue_is_failure(self):
        def fetch(dataset, value):
            return self.response(
                [{"kenteken": value}]
                if dataset == "vehicle"
                else (
                    [{"gebrek_identificatie": "123"}]
                    if dataset == "defects"
                    else []
                )
            )

        with patch.object(rdw, "fetch", side_effect=fetch):
            self.assertEqual(rdw.lookup("AB123C")["status"], "error")

    def test_no_recorded_defects_is_valid(self):
        with patch.object(
            rdw,
            "fetch",
            side_effect=[
                self.response([{"kenteken": "AB123C"}]),
                self.response([]),
            ],
        ):
            self.assertEqual(rdw.lookup("AB123C")["status"], "ok")

    def test_malformed_mismatched_and_capped_responses_fail(self):
        for rows in (
            [1],
            [{"kenteken": "ZZ999Z"}],
            [{"kenteken": "AB123C"}] * 1000,
        ):
            with (
                self.subTest(rows_count=len(rows)),
                patch.object(
                    rdw, "urlopen", return_value=io.StringIO(json.dumps(rows))
                ),
            ):
                self.assertEqual(
                    rdw.fetch("vehicle", "AB123C", attempts=1)["status"],
                    "error",
                )

    def test_request_file_preserves_all_lines_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "plates.txt"
            output = Path(folder) / "results.json"
            source.write_text("AB-123-C\nZZ-999-Z, AB123C\tXY123Z\n")
            with (
                patch(
                    "sys.argv",
                    [
                        "rdw_lookup.py",
                        "--input",
                        str(source),
                        "--output",
                        str(output),
                    ],
                ),
                patch.object(
                    rdw,
                    "lookup",
                    side_effect=lambda p: {"status": "ok", "kenteken": p},
                ) as lookup,
            ):
                self.assertEqual(rdw.main(), 0)
            self.assertEqual(
                [call.args[0] for call in lookup.call_args_list],
                ["AB123C", "ZZ999Z", "XY123Z"],
            )
            self.assertEqual(len(json.loads(output.read_text())["results"]), 3)

    def test_invalid_request_is_validated_before_network(self):
        with (
            patch("sys.argv", ["rdw_lookup.py", "AB123C", "invalid"]),
            patch.object(rdw, "lookup") as lookup,
            patch("sys.stderr", new_callable=io.StringIO),
        ):
            with self.assertRaises(SystemExit):
                rdw.main()
            lookup.assert_not_called()

    def test_partial_results_exit_nonzero_and_preserve_output(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "results.json"
            with (
                patch(
                    "sys.argv",
                    [
                        "rdw_lookup.py",
                        "AB123C",
                        "ZZ999Z",
                        "--output",
                        str(output),
                    ],
                ),
                patch.object(
                    rdw,
                    "lookup",
                    side_effect=[{"status": "ok"}, {"status": "error"}],
                ),
            ):
                self.assertEqual(rdw.main(), 1)
            self.assertEqual(len(json.loads(output.read_text())["results"]), 2)
