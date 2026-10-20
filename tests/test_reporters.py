"""Unit tests for console, Markdown, and JSON reporters."""

import json
import unittest
from api_contract_diff.models import ApiChange, ChangeCategory, ChangeSeverity, DiffReport
from api_contract_diff.reporters import Colors, format_console, format_json, format_markdown


class TestReporters(unittest.TestCase):
    def setUp(self):
        self.report = DiffReport(
            old_spec_title="Payment API",
            new_spec_title="Payment API v2",
            old_version="1.0.0",
            new_version="2.0.0",
            changes=[
                ApiChange(
                    severity=ChangeSeverity.BREAKING,
                    category=ChangeCategory.ENDPOINT,
                    path="/v1/charge",
                    method="POST",
                    message="Operation 'POST /v1/charge' was removed",
                    details="Clients using v1 charges will fail",
                ),
                ApiChange(
                    severity=ChangeSeverity.NON_BREAKING,
                    category=ChangeCategory.ENDPOINT,
                    path="/v2/charge",
                    method="POST",
                    message="New operation 'POST /v2/charge' added",
                ),
                ApiChange(
                    severity=ChangeSeverity.INFO,
                    category=ChangeCategory.ENDPOINT,
                    path="/v1/refund",
                    method="POST",
                    message="Operation 'POST /v1/refund' has been marked as deprecated",
                ),
            ],
        )

    def test_colors_disable(self):
        Colors.disable()
        self.assertEqual(Colors.RED, "")

    def test_format_console(self):
        out = format_console(self.report)
        self.assertIn("Payment API", out)
        self.assertIn("[BREAKING CHANGES] (1)", out)
        self.assertIn("/v1/charge", out)
        self.assertIn("[NON-BREAKING CHANGES] (1)", out)

    def test_format_markdown(self):
        md = format_markdown(self.report)
        self.assertIn("# 📑 API Contract Diff Report", md)
        self.assertIn("| ❌ **BREAKING** |", md)
        self.assertIn("`/v1/charge`", md)
        self.assertIn("`ENDPOINT`", md)

    def test_format_json(self):
        json_str = format_json(self.report)
        data = json.loads(json_str)
        self.assertTrue(data["has_breaking_changes"])
        self.assertEqual(data["summary"]["breaking"], 1)
        self.assertEqual(data["summary"]["non_breaking"], 1)
        self.assertEqual(len(data["changes"]), 3)


if __name__ == "__main__":
    unittest.main()
