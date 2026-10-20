"""Unit tests for OpenAPI contract diffing logic and breaking change detection."""

import unittest
from api_contract_diff.differ import diff_specs, diff_files
from api_contract_diff.models import ChangeCategory, ChangeSeverity


class TestContractDiffer(unittest.TestCase):
    def test_identical_specs(self):
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "App API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {"200": {"description": "OK"}}
                    }
                }
            },
        }
        report = diff_specs(spec, spec)
        self.assertFalse(report.has_breaking_changes)
        self.assertEqual(len(report.changes), 0)

    def test_removed_endpoint(self):
        old_spec = {
            "paths": {
                "/users": {"get": {"responses": {"200": {"description": "OK"}}}},
                "/orders": {"get": {"responses": {"200": {"description": "OK"}}}},
            }
        }
        new_spec = {
            "paths": {
                "/users": {"get": {"responses": {"200": {"description": "OK"}}}},
            }
        }
        report = diff_specs(old_spec, new_spec)
        self.assertTrue(report.has_breaking_changes)
        breaking = report.breaking_changes
        self.assertEqual(len(breaking), 1)
        self.assertEqual(breaking[0].category, ChangeCategory.ENDPOINT)
        self.assertIn("/orders", breaking[0].path)

    def test_added_endpoint(self):
        old_spec = {"paths": {}}
        new_spec = {
            "paths": {
                "/health": {"get": {"responses": {"200": {"description": "OK"}}}}
            }
        }
        report = diff_specs(old_spec, new_spec)
        self.assertFalse(report.has_breaking_changes)
        non_breaking = report.non_breaking_changes
        self.assertEqual(len(non_breaking), 1)
        self.assertEqual(non_breaking[0].severity, ChangeSeverity.NON_BREAKING)

    def test_operation_deprecation(self):
        old_spec = {"paths": {"/items": {"get": {"deprecated": False}}}}
        new_spec = {"paths": {"/items": {"get": {"deprecated": True}}}}
        report = diff_specs(old_spec, new_spec)
        self.assertFalse(report.has_breaking_changes)
        info = report.info_changes
        self.assertEqual(len(info), 1)
        self.assertIn("deprecated", info[0].message)

    def test_added_required_vs_optional_parameter(self):
        old_spec = {"paths": {"/search": {"get": {"parameters": []}}}}
        new_spec_req = {
            "paths": {
                "/search": {
                    "get": {
                        "parameters": [
                            {"name": "query", "in": "query", "required": True, "schema": {"type": "string"}}
                        ]
                    }
                }
            }
        }
        report_req = diff_specs(old_spec, new_spec_req)
        self.assertTrue(report_req.has_breaking_changes)
        self.assertEqual(report_req.breaking_changes[0].category, ChangeCategory.PARAMETER)

        new_spec_opt = {
            "paths": {
                "/search": {
                    "get": {
                        "parameters": [
                            {"name": "page", "in": "query", "required": False, "schema": {"type": "integer"}}
                        ]
                    }
                }
            }
        }
        report_opt = diff_specs(old_spec, new_spec_opt)
        self.assertFalse(report_opt.has_breaking_changes)
        self.assertEqual(len(report_opt.non_breaking_changes), 1)

    def test_parameter_optional_to_required(self):
        old_spec = {
            "paths": {
                "/items": {
                    "get": {
                        "parameters": [{"name": "filter", "in": "query", "required": False}]
                    }
                }
            }
        }
        new_spec = {
            "paths": {
                "/items": {
                    "get": {
                        "parameters": [{"name": "filter", "in": "query", "required": True}]
                    }
                }
            }
        }
        report = diff_specs(old_spec, new_spec)
        self.assertTrue(report.has_breaking_changes)
        self.assertIn("optional to required", report.breaking_changes[0].message)

    def test_parameter_required_to_optional(self):
        old_spec = {
            "paths": {
                "/items": {
                    "get": {
                        "parameters": [{"name": "filter", "in": "query", "required": True}]
                    }
                }
            }
        }
        new_spec = {
            "paths": {
                "/items": {
                    "get": {
                        "parameters": [{"name": "filter", "in": "query", "required": False}]
                    }
                }
            }
        }
        report = diff_specs(old_spec, new_spec)
        self.assertFalse(report.has_breaking_changes)
        self.assertEqual(len(report.non_breaking_changes), 1)

    def test_parameter_type_changed(self):
        old_spec = {
            "paths": {
                "/users/{id}": {
                    "get": {
                        "parameters": [
                            {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                        ]
                    }
                }
            }
        }
        new_spec = {
            "paths": {
                "/users/{id}": {
                    "get": {
                        "parameters": [
                            {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                        ]
                    }
                }
            }
        }
        report = diff_specs(old_spec, new_spec)
        self.assertTrue(report.has_breaking_changes)
        self.assertEqual(report.breaking_changes[0].category, ChangeCategory.SCHEMA)

    def test_parameter_removed(self):
        old_spec = {
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [{"name": "limit", "in": "query", "required": False}]
                    }
                }
            }
        }
        new_spec = {"paths": {"/users": {"get": {"parameters": []}}}}
        report = diff_specs(old_spec, new_spec)
        self.assertTrue(report.has_breaking_changes)
        self.assertEqual(report.breaking_changes[0].category, ChangeCategory.PARAMETER)

    def test_request_body_property_changes(self):
        old_spec = {
            "paths": {
                "/login": {
                    "post": {
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "username": {"type": "string"},
                                            "password": {"type": "string"},
                                        },
                                        "required": ["username", "password"],
                                    }
                                }
                            },
                        }
                    }
                }
            }
        }
        # Added required property 'otp'
        new_spec = {
            "paths": {
                "/login": {
                    "post": {
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "username": {"type": "string"},
                                            "password": {"type": "string"},
                                            "otp": {"type": "string"},
                                        },
                                        "required": ["username", "password", "otp"],
                                    }
                                }
                            },
                        }
                    }
                }
            }
        }
        report = diff_specs(old_spec, new_spec)
        self.assertTrue(report.has_breaking_changes)
        self.assertIn("otp", report.breaking_changes[0].message)

    def test_request_body_media_types(self):
        old_spec = {
            "paths": {
                "/upload": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {"schema": {"type": "object"}},
                                "multipart/form-data": {"schema": {"type": "object"}},
                            }
                        }
                    }
                }
            }
        }
        new_spec = {
            "paths": {
                "/upload": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {"schema": {"type": "object"}},
                            }
                        }
                    }
                }
            }
        }
        report = diff_specs(old_spec, new_spec)
        self.assertTrue(report.has_breaking_changes)
        self.assertIn("multipart/form-data", report.breaking_changes[0].message)

    def test_removed_response_code(self):
        old_spec = {
            "paths": {
                "/data": {
                    "get": {
                        "responses": {
                            "200": {"description": "OK"},
                            "404": {"description": "Not Found"},
                        }
                    }
                }
            }
        }
        new_spec = {
            "paths": {
                "/data": {
                    "get": {
                        "responses": {
                            "404": {"description": "Not Found"},
                        }
                    }
                }
            }
        }
        report = diff_specs(old_spec, new_spec)
        self.assertTrue(report.has_breaking_changes)
        self.assertIn("200", report.breaking_changes[0].message)

    def test_removed_response_property(self):
        old_spec = {
            "paths": {
                "/user": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "email": {"type": "string"},
                                            },
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        new_spec = {
            "paths": {
                "/user": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                            },
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        report = diff_specs(old_spec, new_spec)
        self.assertTrue(report.has_breaking_changes)
        self.assertIn("email", report.breaking_changes[0].message)

    def test_array_item_schema_diff(self):
        old_spec = {
            "paths": {
                "/tags": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        new_spec = {
            "paths": {
                "/tags": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {"type": "integer"},
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        report = diff_specs(old_spec, new_spec)
        self.assertTrue(report.has_breaking_changes)
        self.assertIn("Changed data type", report.breaking_changes[0].message)

    def test_enum_changes(self):
        old_spec = {
            "paths": {
                "/orders": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string", "enum": ["pending", "paid", "cancelled"]}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        # Removed 'cancelled' from allowed enum in request body
        new_spec = {
            "paths": {
                "/orders": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string", "enum": ["pending", "paid"]}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        report = diff_specs(old_spec, new_spec)
        self.assertTrue(report.has_breaking_changes)
        self.assertIn("cancelled", report.breaking_changes[0].message)

    def test_added_security_requirement(self):
        old_spec = {"paths": {"/public": {"get": {"security": []}}}}
        new_spec = {"paths": {"/public": {"get": {"security": [{"BearerAuth": []}]}}}}
        report = diff_specs(old_spec, new_spec)
        self.assertTrue(report.has_breaking_changes)
        self.assertEqual(report.breaking_changes[0].category, ChangeCategory.SECURITY)

    def test_ignore_path_patterns(self):
        old_spec = {
            "paths": {
                "/internal/metrics": {"get": {}},
                "/api/v1/users": {"get": {}},
            }
        }
        new_spec = {"paths": {}}
        report = diff_specs(old_spec, new_spec, ignore_path_patterns=[r"^/internal/"])
        breaking_paths = [c.path for c in report.breaking_changes]
        self.assertNotIn("/internal/metrics", breaking_paths)
        self.assertIn("/api/v1/users", breaking_paths)


if __name__ == "__main__":
    unittest.main()
