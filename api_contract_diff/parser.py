"""Parser and normalizer for OpenAPI 3.x and Swagger 2.0 specifications."""

from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict, Optional, Set


class SpecParseError(Exception):
    """Raised when an API specification cannot be parsed or loaded."""


def load_spec_file(file_path: str) -> Dict[str, Any]:
    """Load an OpenAPI/Swagger spec from a JSON or YAML file."""
    if not os.path.exists(file_path):
        raise SpecParseError(f"Specification file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    return parse_spec_content(content, file_path)


def parse_spec_content(content: str, filename: str = "") -> Dict[str, Any]:
    """Parse JSON or YAML spec content."""
    content_stripped = content.strip()

    # Try JSON first
    if content_stripped.startswith("{") or filename.endswith(".json"):
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            if filename.endswith(".json"):
                raise SpecParseError(f"Failed to parse JSON specification: {e}")

    # Try YAML
    try:
        import yaml
        data = yaml.safe_load(content)
        if isinstance(data, dict):
            return data
        raise SpecParseError("Parsed content is not a valid specification dictionary")
    except ImportError:
        # Fallback to json if yaml not installed
        try:
            return json.loads(content)
        except Exception:
            raise SpecParseError(
                "PyYAML is not installed and content is not valid JSON. Install pyyaml: pip install pyyaml"
            )
    except Exception as e:
        raise SpecParseError(f"Failed to parse specification: {e}")


class SpecNormalizer:
    """Resolves $refs and normalizes Swagger 2.0 / OpenAPI 3.x specs to a unified structure."""

    def __init__(self, root_spec: Dict[str, Any]):
        self.root = copy.deepcopy(root_spec)
        self.is_swagger2 = self.root.get("swagger", "").startswith("2.")
        self.is_openapi3 = self.root.get("openapi", "").startswith("3.")

    def resolve_ref(self, ref_str: str, visited: Optional[Set[str]] = None) -> Any:
        """Resolve an internal JSON pointer reference like #/components/schemas/Pet."""
        if visited is None:
            visited = set()

        if ref_str in visited:
            # Handle recursive/circular references gracefully
            return {"type": "object", "description": f"Circular ref to {ref_str}"}

        visited.add(ref_str)

        if not ref_str.startswith("#/"):
            # External references are not inlined, return placeholder
            return {"$ref": ref_str}

        parts = ref_str[2:].split("/")
        curr = self.root
        for part in parts:
            part = part.replace("~1", "/").replace("~0", "~")
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            else:
                return {"$ref": ref_str}

        # If resolved object itself has a $ref, resolve transitively
        if isinstance(curr, dict) and "$ref" in curr:
            return self.resolve_ref(curr["$ref"], visited)

        return copy.deepcopy(curr)

    def inline_refs(self, node: Any, depth: int = 0, max_depth: int = 20) -> Any:
        """Recursively inline internal $refs with cycle prevention."""
        if depth > max_depth:
            return node

        if isinstance(node, dict):
            if "$ref" in node and isinstance(node["$ref"], str) and node["$ref"].startswith("#/"):
                resolved = self.resolve_ref(node["$ref"])
                return self.inline_refs(resolved, depth + 1, max_depth)
            return {k: self.inline_refs(v, depth + 1, max_depth) for k, v in node.items()}
        elif isinstance(node, list):
            return [self.inline_refs(item, depth + 1, max_depth) for item in node]
        return node

    def normalize(self) -> Dict[str, Any]:
        """Produce a normalized OpenAPI 3.x-like representation."""
        spec = copy.deepcopy(self.root)
        spec = self.inline_refs(spec)

        paths = spec.get("paths", {})
        normalized_paths: Dict[str, Any] = {}

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            norm_path_item: Dict[str, Any] = {}
            path_parameters = path_item.get("parameters", [])

            for method in ("get", "post", "put", "delete", "patch", "options", "head", "trace"):
                if method not in path_item:
                    continue

                operation = copy.deepcopy(path_item[method])
                # Merge path-level parameters with operation parameters
                op_params = operation.get("parameters", [])
                combined_params = self._merge_parameters(path_parameters, op_params)

                # Normalize Swagger 2.0 body param to requestBody
                if self.is_swagger2:
                    body_param = None
                    other_params = []
                    for p in combined_params:
                        if p.get("in") == "body":
                            body_param = p
                        else:
                            other_params = append_non_body(other_params, p)
                    combined_params = other_params

                    if body_param and "requestBody" not in operation:
                        operation["requestBody"] = {
                            "required": body_param.get("required", False),
                            "description": body_param.get("description", ""),
                            "content": {
                                "application/json": {
                                    "schema": body_param.get("schema", {})
                                }
                            },
                        }

                    # Normalize Swagger 2.0 responses
                    responses = operation.get("responses", {})
                    norm_responses = {}
                    for code, resp in responses.items():
                        if isinstance(resp, dict):
                            r = copy.deepcopy(resp)
                            if "schema" in r and "content" not in r:
                                r["content"] = {
                                    "application/json": {
                                        "schema": r.pop("schema")
                                    }
                                }
                            norm_responses[str(code)] = r
                        else:
                            norm_responses[str(code)] = resp
                    operation["responses"] = norm_responses

                operation["parameters"] = combined_params
                norm_path_item[method] = operation

            normalized_paths[path] = norm_path_item

        spec["paths"] = normalized_paths
        return spec

    def _merge_parameters(self, path_params: list, op_params: list) -> list:
        param_map = {}
        for p in path_params:
            if isinstance(p, dict) and "name" in p and "in" in p:
                param_map[(p["name"], p["in"])] = p
        for p in op_params:
            if isinstance(p, dict) and "name" in p and "in" in p:
                param_map[(p["name"], p["in"])] = p
        return list(param_map.values())


def append_non_body(param_list: list, param: dict) -> list:
    param_list.append(param)
    return param_list
