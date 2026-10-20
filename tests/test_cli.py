"""Unit tests for the CLI entry point."""

import json
import os
import tempfile
import unittest
from api_contract_diff.cli import main


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.spec_v1 = os.path.join(self.tmpdir.name, "v1.json")
        self.spec_v2_breaking = os.path.join(self.tmpdir.name, "v2_breaking.json")
        self.spec_v2_compat = os.path.join(self.tmpdir.name, "v2_compat.json")

        v1 = {
            "openapi": "3.0.0",
            "info": {"title": "Users API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {"200": {"description": "OK"}}
                    }
                }
            },
        }

        v2_breaking = {
            "openapi": "3.0.0",
            "info": {"title": "Users API", "version": "2.0.0"},
            "paths": {
                # /users removed
                "/accounts": {
                    "get": {
                        "responses": {"200": {"description": "OK"}}
                    }
                }
            },
        }

        v2_compat = {
            "openapi": "3.0.0",
            "info": {"title": "Users API", "version": "1.1.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {"200": {"description": "OK"}}
                    }
                },
                "/users/search": {
                    "get": {
                        "responses": {"200": {"description": "OK"}}
                    }
                },
            },
        }

        with open(self.spec_v1, "w") as f:
            json.dump(v1, f)
        with open(self.spec_v2_breaking, "w") as f:
            json.dump(v2_breaking, f)
        with open(self.spec_v2_compat, "w") as f:
            json.dump(v2_compat, f)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_version_flag(self):
        with self.assertRaises(SystemExit) as cm:
            main(["--version"])
        self.assertEqual(cm.exception.code, 0)

    def test_cli_breaking_exit_code_1(self):
        # Default fail-on-breaking should return 1
        code = main([self.spec_v1, self.spec_v2_breaking])
        self.assertEqual(code, 1)

    def test_cli_compatible_exit_code_0(self):
        # Compatible addition should return 0
        code = main([self.spec_v1, self.spec_v2_compat])
        self.assertEqual(code, 0)

    def test_cli_no_fail_flag(self):
        # With --no-fail, should return 0 even with breaking changes
        code = main([self.spec_v1, self.spec_v2_breaking, "--no-fail"])
        self.assertEqual(code, 0)

    def test_cli_formats_and_output_file(self):
        out_md = os.path.join(self.tmpdir.name, "diff.md")
        out_json = os.path.join(self.tmpdir.name, "diff.json")

        code_md = main([self.spec_v1, self.spec_v2_compat, "-f", "markdown", "-o", out_md])
        self.assertEqual(code_md, 0)
        self.assertTrue(os.path.exists(out_md))
        with open(out_md, "r", encoding="utf-8") as f:
            self.assertIn("# 📑 API Contract Diff Report", f.read())

        code_json = main([self.spec_v1, self.spec_v2_compat, "-f", "json", "-o", out_json])
        self.assertEqual(code_json, 0)
        self.assertTrue(os.path.exists(out_json))
        with open(out_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertFalse(data["has_breaking_changes"])

    def test_cli_error_file_not_found(self):
        code = main(["missing_old.json", "missing_new.json"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
