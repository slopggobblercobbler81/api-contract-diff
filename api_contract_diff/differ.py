"""OpenAPI / Swagger Contract Diff Engine with breaking change detection."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from .models import ApiChange, ChangeCategory, ChangeSeverity, DiffReport
from .parser import SpecNormalizer, load_spec_file, parse_spec_content


class ApiContractDiffer:
    """Calculates semantic and breaking changes between two API specifications."""

    def __init__(
        self,
        old_spec: Dict[str, Any],
        new_spec: Dict[str, Any],
        ignore_path_patterns: Optional[List[str]] = None,
    ):
        self.old_normalizer = SpecNormalizer(old_spec)
        self.new_normalizer = SpecNormalizer(new_spec)
        self.old_spec = self.old_normalizer.normalize()
        self.new_spec = self.new_normalizer.normalize()
        self.ignore_patterns = [re.compile(p) for p in (ignore_path_patterns or [])]

    def _is_ignored(self, path: str) -> bool:
        return any(pattern.search(path) for pattern in self.ignore_patterns)

    def diff(self) -> DiffReport:
        changes: List[ApiChange] = []

        old_info = self.old_spec.get("info", {})
        new_info = self.new_spec.get("info", {})
        old_title = old_info.get("title", "Old API")
        new_title = new_info.get("title", "New API")
        old_ver = old_info.get("version", "1.0.0")
        new_ver = new_info.get("version", "1.0.0")

        old_paths = self.old_spec.get("paths", {})
        new_paths = self.new_spec.get("paths", {})

        all_paths = set(old_paths.keys()) | set(new_paths.keys())

        for path in sorted(all_paths):
            if self._is_ignored(path):
                continue

            # Path completely removed
            if path in old_paths and path not in new_paths:
                for method in old_paths[path].keys():
                    changes.append(
                        ApiChange(
                            severity=ChangeSeverity.BREAKING,
                            category=ChangeCategory.ENDPOINT,
                            path=path,
                            method=method,
                            message=f"Endpoint '{method.upper()} {path}' was removed",
                            old_value=path,
                            new_value=None,
                        )
                    )
                continue

            # Path completely added
            if path not in old_paths and path in new_paths:
                for method in new_paths[path].keys():
                    changes.append(
                        ApiChange(
                            severity=ChangeSeverity.NON_BREAKING,
                            category=ChangeCategory.ENDPOINT,
                            path=path,
                            method=method,
                            message=f"New endpoint '{method.upper()} {path}' added",
                            old_value=None,
                            new_value=path,
                        )
                    )
                continue

            # Path exists in both - compare methods
            old_methods = old_paths[path]
            new_methods = new_paths[path]

            all_methods = set(old_methods.keys()) | set(new_methods.keys())
            for method in sorted(all_methods):
                if method in old_methods and method not in new_methods:
                    changes.append(
                        ApiChange(
                            severity=ChangeSeverity.BREAKING,
                            category=ChangeCategory.ENDPOINT,
                            path=path,
                            method=method,
                            message=f"Operation '{method.upper()} {path}' was removed",
                            old_value=method.upper(),
                            new_value=None,
                        )
                    )
                elif method not in old_methods and method in new_methods:
                    changes.append(
                        ApiChange(
                            severity=ChangeSeverity.NON_BREAKING,
                            category=ChangeCategory.ENDPOINT,
                            path=path,
                            method=method,
                            message=f"New operation '{method.upper()} {path}' added",
                            old_value=None,
                            new_value=method.upper(),
                        )
                    )
                else:
                    # Operation in both - compare operation details
                    changes.extend(
                        self._diff_operation(
                            path, method, old_methods[method], new_methods[method]
                        )
                    )

        return DiffReport(
            old_spec_title=old_title,
            new_spec_title=new_title,
            old_version=old_ver,
            new_version=new_ver,
            changes=changes,
        )

    def _diff_operation(
        self, path: str, method: str, old_op: Dict[str, Any], new_op: Dict[str, Any]
    ) -> List[ApiChange]:
        changes: List[ApiChange] = []

        # Deprecation check
        old_dep = bool(old_op.get("deprecated", False))
        new_dep = bool(new_op.get("deprecated", False))
        if not old_dep and new_dep:
            changes.append(
                ApiChange(
                    severity=ChangeSeverity.INFO,
                    category=ChangeCategory.ENDPOINT,
                    path=path,
                    method=method,
                    message=f"Operation '{method.upper()} {path}' has been marked as deprecated",
                )
            )

        # 1. Compare parameters
        changes.extend(
            self._diff_parameters(
                path, method, old_op.get("parameters", []), new_op.get("parameters", [])
            )
        )

        # 2. Compare request bodies
        changes.extend(
            self._diff_request_body(
                path, method, old_op.get("requestBody"), new_op.get("requestBody")
            )
        )

        # 3. Compare responses
        changes.extend(
            self._diff_responses(
                path, method, old_op.get("responses", {}), new_op.get("responses", {})
            )
        )

        # 4. Compare security
        changes.extend(
            self._diff_security(
                path, method, old_op.get("security"), new_op.get("security")
            )
        )

        return changes

    def _diff_parameters(
        self, path: str, method: str, old_params: List[Dict[str, Any]], new_params: List[Dict[str, Any]]
    ) -> List[ApiChange]:
        changes: List[ApiChange] = []
        old_map = {(p.get("name"), p.get("in")): p for p in old_params if isinstance(p, dict)}
        new_map = {(p.get("name"), p.get("in")): p for p in new_params if isinstance(p, dict)}

        # Check removed parameters
        for (name, loc), old_p in old_map.items():
            if (name, loc) not in new_map:
                changes.append(
                    ApiChange(
                        severity=ChangeSeverity.BREAKING,
                        category=ChangeCategory.PARAMETER,
                        path=path,
                        method=method,
                        message=f"Removed parameter '{name}' ({loc})",
                        old_value=old_p,
                        new_value=None,
                    )
                )

        # Check added parameters
        for (name, loc), new_p in new_map.items():
            if (name, loc) not in old_map:
                is_req = bool(new_p.get("required", False))
                if is_req:
                    changes.append(
                        ApiChange(
                            severity=ChangeSeverity.BREAKING,
                            category=ChangeCategory.PARAMETER,
                            path=path,
                            method=method,
                            message=f"Added required parameter '{name}' ({loc})",
                            details="Existing clients that do not send this parameter will fail",
                            old_value=None,
                            new_value=new_p,
                        )
                    )
                else:
                    changes.append(
                        ApiChange(
                            severity=ChangeSeverity.NON_BREAKING,
                            category=ChangeCategory.PARAMETER,
                            path=path,
                            method=method,
                            message=f"Added optional parameter '{name}' ({loc})",
                            old_value=None,
                            new_value=new_p,
                        )
                    )

        # Check common parameters
        for (name, loc) in set(old_map.keys()) & set(new_map.keys()):
            old_p = old_map[(name, loc)]
            new_p = new_map[(name, loc)]

            # Check required change
            old_req = bool(old_p.get("required", False))
            new_req = bool(new_p.get("required", False))
            if not old_req and new_req:
                changes.append(
                    ApiChange(
                        severity=ChangeSeverity.BREAKING,
                        category=ChangeCategory.PARAMETER,
                        path=path,
                        method=method,
                        message=f"Parameter '{name}' ({loc}) changed from optional to required",
                        old_value="optional",
                        new_value="required",
                    )
                )
            elif old_req and not new_req:
                changes.append(
                    ApiChange(
                        severity=ChangeSeverity.NON_BREAKING,
                        category=ChangeCategory.PARAMETER,
                        path=path,
                        method=method,
                        message=f"Parameter '{name}' ({loc}) changed from required to optional",
                        old_value="required",
                        new_value="optional",
                    )
                )

            # Check schema / type
            old_schema = old_p.get("schema") or old_p
            new_schema = new_p.get("schema") or new_p
            changes.extend(
                self._diff_schema(
                    path,
                    method,
                    f"parameter '{name}'",
                    old_schema,
                    new_schema,
                    is_request=True,
                )
            )

        return changes

    def _diff_request_body(
        self,
        path: str,
        method: str,
        old_body: Optional[Dict[str, Any]],
        new_body: Optional[Dict[str, Any]],
    ) -> List[ApiChange]:
        changes: List[ApiChange] = []

        if old_body and not new_body:
            changes.append(
                ApiChange(
                    severity=ChangeSeverity.BREAKING,
                    category=ChangeCategory.REQUEST_BODY,
                    path=path,
                    method=method,
                    message="Request body was removed",
                )
            )
            return changes

        if not old_body and new_body:
            is_req = bool(new_body.get("required", False))
            if is_req:
                changes.append(
                    ApiChange(
                        severity=ChangeSeverity.BREAKING,
                        category=ChangeCategory.REQUEST_BODY,
                        path=path,
                        method=method,
                        message="Added required request body to previously bodiless operation",
                    )
                )
            else:
                changes.append(
                    ApiChange(
                        severity=ChangeSeverity.NON_BREAKING,
                        category=ChangeCategory.REQUEST_BODY,
                        path=path,
                        method=method,
                        message="Added optional request body",
                    )
                )
            return changes

        if old_body and new_body:
            old_req = bool(old_body.get("required", False))
            new_req = bool(new_body.get("required", False))
            if not old_req and new_req:
                changes.append(
                    ApiChange(
                        severity=ChangeSeverity.BREAKING,
                        category=ChangeCategory.REQUEST_BODY,
                        path=path,
                        method=method,
                        message="Request body changed from optional to required",
                    )
                )
            elif old_req and not new_req:
                changes.append(
                    ApiChange(
                        severity=ChangeSeverity.NON_BREAKING,
                        category=ChangeCategory.REQUEST_BODY,
                        path=path,
                        method=method,
                        message="Request body changed from required to optional",
                    )
                )

            old_content = old_body.get("content", {})
            new_content = new_body.get("content", {})

            # Removed media types
            for mt in old_content.keys():
                if mt not in new_content:
                    changes.append(
                        ApiChange(
                            severity=ChangeSeverity.BREAKING,
                            category=ChangeCategory.REQUEST_BODY,
                            path=path,
                            method=method,
                            message=f"Removed supported request body media type '{mt}'",
                        )
                    )

            # Added media types
            for mt in new_content.keys():
                if mt not in old_content:
                    changes.append(
                        ApiChange(
                            severity=ChangeSeverity.NON_BREAKING,
                            category=ChangeCategory.REQUEST_BODY,
                            path=path,
                            method=method,
                            message=f"Added supported request body media type '{mt}'",
                        )
                    )

            # Compare common media type schemas
            for mt in set(old_content.keys()) & set(new_content.keys()):
                old_s = old_content[mt].get("schema", {})
                new_s = new_content[mt].get("schema", {})
                changes.extend(
                    self._diff_schema(
                        path,
                        method,
                        f"request body ({mt})",
                        old_s,
                        new_s,
                        is_request=True,
                    )
                )

        return changes

    def _diff_responses(
        self,
        path: str,
        method: str,
        old_responses: Dict[str, Any],
        new_responses: Dict[str, Any],
    ) -> List[ApiChange]:
        changes: List[ApiChange] = []

        # Removed response codes
        for code in old_responses.keys():
            if code not in new_responses:
                # Removing 2xx or default is breaking
                is_breaking = code.startswith("2") or code == "default"
                changes.append(
                    ApiChange(
                        severity=ChangeSeverity.BREAKING if is_breaking else ChangeSeverity.NON_BREAKING,
                        category=ChangeCategory.RESPONSE,
                        path=path,
                        method=method,
                        message=f"Removed response status code '{code}'",
                        old_value=code,
                        new_value=None,
                    )
                )

        # Added response codes
        for code in new_responses.keys():
            if code not in old_responses:
                changes.append(
                    ApiChange(
                        severity=ChangeSeverity.NON_BREAKING,
                        category=ChangeCategory.RESPONSE,
                        path=path,
                        method=method,
                        message=f"Added new response status code '{code}'",
                        old_value=None,
                        new_value=code,
                    )
                )

        # Common response codes
        for code in set(old_responses.keys()) & set(new_responses.keys()):
            old_r = old_responses[code]
            new_r = new_responses[code]
            if not isinstance(old_r, dict) or not isinstance(new_r, dict):
                continue

            old_content = old_r.get("content", {})
            new_content = new_r.get("content", {})

            for mt in old_content.keys():
                if mt not in new_content:
                    changes.append(
                        ApiChange(
                            severity=ChangeSeverity.BREAKING,
                            category=ChangeCategory.RESPONSE,
                            path=path,
                            method=method,
                            message=f"Removed response media type '{mt}' from status code {code}",
                        )
                    )

            for mt in set(old_content.keys()) & set(new_content.keys()):
                old_s = old_content[mt].get("schema", {})
                new_s = new_content[mt].get("schema", {})
                changes.extend(
                    self._diff_schema(
                        path,
                        method,
                        f"response {code} ({mt})",
                        old_s,
                        new_s,
                        is_request=False,
                    )
                )

        return changes

    def _diff_schema(
        self,
        path: str,
        method: str,
        location: str,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        is_request: bool,
        property_path: str = "",
    ) -> List[ApiChange]:
        """Deeply compare schemas with direction-aware breaking rules.
        
        In request bodies:
          - Adding a required property is BREAKING.
          - Removing a property is BREAKING (server stops accepting it).
          - Adding an optional property is NON_BREAKING.
          - Widening types is NON_BREAKING.
          - Narrowing types is BREAKING.
        In response bodies:
          - Removing a property is BREAKING (clients expecting it break!).
          - Changing type is BREAKING.
          - Adding a property is NON_BREAKING (backward-compatible clients ignore extra fields).
        """
        changes: List[ApiChange] = []
        if not isinstance(old_schema, dict) or not isinstance(new_schema, dict):
            return changes

        prop_label = f"{location}{' -> ' + property_path if property_path else ''}"

        # 1. Compare types
        old_type = old_schema.get("type")
        new_type = new_schema.get("type")
        if old_type and new_type and old_type != new_type:
            changes.append(
                ApiChange(
                    severity=ChangeSeverity.BREAKING,
                    category=ChangeCategory.SCHEMA,
                    path=path,
                    method=method,
                    message=f"Changed data type in {prop_label} from '{old_type}' to '{new_type}'",
                    old_value=old_type,
                    new_value=new_type,
                )
            )

        # 2. Compare enum values
        old_enum = old_schema.get("enum")
        new_enum = new_schema.get("enum")
        if old_enum is not None and new_enum is not None:
            removed_enums = set(map(str, old_enum)) - set(map(str, new_enum))
            added_enums = set(map(str, new_enum)) - set(map(str, old_enum))

            if is_request:
                # In request: removing allowed enum is BREAKING
                if removed_enums:
                    changes.append(
                        ApiChange(
                            severity=ChangeSeverity.BREAKING,
                            category=ChangeCategory.SCHEMA,
                            path=path,
                            method=method,
                            message=f"Removed allowed enum values in {prop_label}: {sorted(list(removed_enums))}",
                        )
                    )
            else:
                # In response: adding an unexpected enum might break strict client deserializers
                if added_enums:
                    changes.append(
                        ApiChange(
                            severity=ChangeSeverity.NON_BREAKING,
                            category=ChangeCategory.SCHEMA,
                            path=path,
                            method=method,
                            message=f"Added new enum values in response {prop_label}: {sorted(list(added_enums))}",
                        )
                    )

        # 3. Compare object properties
        old_props = old_schema.get("properties", {})
        new_props = new_schema.get("properties", {})

        if isinstance(old_props, dict) and isinstance(new_props, dict):
            old_req_raw = old_schema.get("required", [])
            old_req = set(old_req_raw) if isinstance(old_req_raw, list) else set()
            new_req_raw = new_schema.get("required", [])
            new_req = set(new_req_raw) if isinstance(new_req_raw, list) else set()

            # Removed properties
            for p_name in old_props.keys():
                if p_name not in new_props:
                    curr_prop_path = f"{property_path}.{p_name}" if property_path else p_name
                    # Removing property in response is BREAKING for clients relying on it
                    # Removing property in request is BREAKING (field no longer accepted)
                    changes.append(
                        ApiChange(
                            severity=ChangeSeverity.BREAKING,
                            category=ChangeCategory.SCHEMA,
                            path=path,
                            method=method,
                            message=f"Removed property '{curr_prop_path}' in {location}",
                        )
                    )

            # Added properties
            for p_name in new_props.keys():
                if p_name not in old_props:
                    curr_prop_path = f"{property_path}.{p_name}" if property_path else p_name
                    is_p_req = p_name in new_req
                    if is_request:
                        if is_p_req:
                            changes.append(
                                ApiChange(
                                    severity=ChangeSeverity.BREAKING,
                                    category=ChangeCategory.SCHEMA,
                                    path=path,
                                    method=method,
                                    message=f"Added required property '{curr_prop_path}' in {location}",
                                    details="Clients not sending this field will be rejected",
                                )
                            )
                        else:
                            changes.append(
                                ApiChange(
                                    severity=ChangeSeverity.NON_BREAKING,
                                    category=ChangeCategory.SCHEMA,
                                    path=path,
                                    method=method,
                                    message=f"Added optional property '{curr_prop_path}' in {location}",
                                )
                            )
                    else:
                        # In response, adding a property is typically non-breaking (additive)
                        changes.append(
                            ApiChange(
                                severity=ChangeSeverity.NON_BREAKING,
                                category=ChangeCategory.SCHEMA,
                                path=path,
                                method=method,
                                message=f"Added property '{curr_prop_path}' in response {location}",
                            )
                        )

            # Common properties - recursive comparison
            for p_name in set(old_props.keys()) & set(new_props.keys()):
                curr_prop_path = f"{property_path}.{p_name}" if property_path else p_name

                # Check required status change
                was_req = p_name in old_req
                now_req = p_name in new_req
                if is_request and not was_req and now_req:
                    changes.append(
                        ApiChange(
                            severity=ChangeSeverity.BREAKING,
                            category=ChangeCategory.SCHEMA,
                            path=path,
                            method=method,
                            message=f"Property '{curr_prop_path}' in {location} changed from optional to required",
                        )
                    )

                changes.extend(
                    self._diff_schema(
                        path,
                        method,
                        location,
                        old_props[p_name],
                        new_props[p_name],
                        is_request,
                        curr_prop_path,
                    )
                )

        # 4. Compare array items
        if old_schema.get("type") == "array" and new_schema.get("type") == "array":
            old_items = old_schema.get("items", {})
            new_items = new_schema.get("items", {})
            changes.extend(
                self._diff_schema(
                    path,
                    method,
                    location,
                    old_items,
                    new_items,
                    is_request,
                    f"{property_path}[]" if property_path else "[]",
                )
            )

        return changes

    def _diff_security(
        self,
        path: str,
        method: str,
        old_sec: Optional[List[Any]],
        new_sec: Optional[List[Any]],
    ) -> List[ApiChange]:
        changes: List[ApiChange] = []
        old_has_sec = bool(old_sec)
        new_has_sec = bool(new_sec)

        if not old_has_sec and new_has_sec:
            changes.append(
                ApiChange(
                    severity=ChangeSeverity.BREAKING,
                    category=ChangeCategory.SECURITY,
                    path=path,
                    method=method,
                    message=f"Added authentication requirement to previously public endpoint '{method.upper()} {path}'",
                )
            )
        elif old_has_sec and not new_has_sec:
            changes.append(
                ApiChange(
                    severity=ChangeSeverity.NON_BREAKING,
                    category=ChangeCategory.SECURITY,
                    path=path,
                    method=method,
                    message=f"Removed authentication requirement from '{method.upper()} {path}'",
                )
            )

        return changes


def diff_specs(
    old_spec: Dict[str, Any],
    new_spec: Dict[str, Any],
    ignore_path_patterns: Optional[List[str]] = None,
) -> DiffReport:
    """Convenience functional interface to compute API contract difference."""
    differ = ApiContractDiffer(old_spec, new_spec, ignore_path_patterns=ignore_path_patterns)
    return differ.diff()


def diff_files(
    old_file_path: str,
    new_file_path: str,
    ignore_path_patterns: Optional[List[str]] = None,
) -> DiffReport:
    """Compute API contract diff between two spec file paths."""
    old_spec = load_spec_file(old_file_path)
    new_spec = load_spec_file(new_file_path)
    return diff_specs(old_spec, new_spec, ignore_path_patterns=ignore_path_patterns)
