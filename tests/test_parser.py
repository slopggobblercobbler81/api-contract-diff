"""Unit tests for OpenAPI and Swagger parser & normalizer."""

import json
import os
import tempfile
import unittest
from api_contract_diff.parser import (
    SpecNormalizer,
    SpecParseError,
    load_spec_file,
    parse_spec_content,
)


class TestParser(unittest.TestCase):
    def test_parse_json(self):
        spec_str = json.dumps({"openapi": "3.0.0", "info": {"title": "Test API", "version": "1.0.0"}})
        parsed = parse_spec_content(spec_str, "spec.json")
        self.assertEqual(parsed["info"]["title"], "Test API")

    def test_parse_yaml(self):
        yaml_str = """
openapi: 3.0.0
info:
  title: YAML API
  version: 2.0.0
paths: {}
"""
        parsed = parse_spec_content(yaml_str, "spec.yaml")
        self.assertEqual(parsed["info"]["title"], "YAML API")

    def test_invalid_json(self):
        with self.assertRaises(SpecParseError):
            parse_spec_content("{broken json", "spec.json")

    def test_file_not_found(self):
        with self.assertRaises(SpecParseError):
            load_spec_file("nonexistent_file.yaml")

    def test_ref_resolution_and_cycle(self):
        spec = {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "friend": {"$ref": "#/components/schemas/User"},
                        },
                    }
                }
            },
            "paths": {
                "/users/{id}": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/User"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
        }
        normalizer = SpecNormalizer(spec)
        normalized = normalizer.normalize()
        schema = normalized["paths"]["/users/{id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        self.assertEqual(schema["type"], "object")
        self.assertIn("id", schema["properties"])
        # Circular reference resolved gracefully without infinite loop
        self.assertEqual(schema["properties"]["friend"]["type"], "object")

    def test_swagger2_normalization(self):
        swagger2 = {
            "swagger": "2.0",
            "info": {"title": "Petstore", "version": "1.0"},
            "paths": {
                "/pets": {
                    "post": {
                        "parameters": [
                            {
                                "name": "body",
                                "in": "body",
                                "required": True,
                                "schema": {"type": "object", "properties": {"name": {"type": "string"}}},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Success",
                                "schema": {"type": "array"},
                            }
                        },
                    }
                }
            },
        }
        normalizer = SpecNormalizer(swagger2)
        norm = normalizer.normalize()
        op = norm["paths"]["/pets"]["post"]

        # Swagger 2 body param converted to requestBody
        self.assertIn("requestBody", op)
        self.assertTrue(op["requestBody"]["required"])
        self.assertIn("application/json", op["requestBody"]["content"])

        # Swagger 2 responses normalized to content map
        self.assertIn("application/json", op["responses"]["200"]["content"])


if __name__ == "__main__":
    unittest.main()
