"""Data models for API contract changes and diff reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ChangeSeverity(str, Enum):
    BREAKING = "BREAKING"
    NON_BREAKING = "NON_BREAKING"
    INFO = "INFO"


class ChangeCategory(str, Enum):
    ENDPOINT = "ENDPOINT"
    PARAMETER = "PARAMETER"
    REQUEST_BODY = "REQUEST_BODY"
    RESPONSE = "RESPONSE"
    SCHEMA = "SCHEMA"
    SECURITY = "SECURITY"


@dataclass
class ApiChange:
    severity: ChangeSeverity
    category: ChangeCategory
    path: str
    method: Optional[str]
    message: str
    details: Optional[str] = None
    old_value: Any = None
    new_value: Any = None

    @property
    def is_breaking(self) -> bool:
        return self.severity == ChangeSeverity.BREAKING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "path": self.path,
            "method": self.method.upper() if self.method else None,
            "message": self.message,
            "details": self.details,
            "old_value": self.old_value,
            "new_value": self.new_value,
        }


@dataclass
class DiffReport:
    old_spec_title: str
    new_spec_title: str
    old_version: str
    new_version: str
    changes: List[ApiChange] = field(default_factory=list)

    @property
    def breaking_changes(self) -> List[ApiChange]:
        return [c for c in self.changes if c.severity == ChangeSeverity.BREAKING]

    @property
    def non_breaking_changes(self) -> List[ApiChange]:
        return [c for c in self.changes if c.severity == ChangeSeverity.NON_BREAKING]

    @property
    def info_changes(self) -> List[ApiChange]:
        return [c for c in self.changes if c.severity == ChangeSeverity.INFO]

    @property
    def has_breaking_changes(self) -> bool:
        return any(c.is_breaking for c in self.changes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "old_spec": {
                "title": self.old_spec_title,
                "version": self.old_version,
            },
            "new_spec": {
                "title": self.new_spec_title,
                "version": self.new_version,
            },
            "summary": {
                "total": len(self.changes),
                "breaking": len(self.breaking_changes),
                "non_breaking": len(self.non_breaking_changes),
                "info": len(self.info_changes),
            },
            "has_breaking_changes": self.has_breaking_changes,
            "changes": [c.to_dict() for c in self.changes],
        }
