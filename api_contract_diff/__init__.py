"""api-contract-diff: Fast OpenAPI & Swagger contract diff and breaking change detector."""

__version__ = "1.0.0"

from .differ import ApiContractDiffer, diff_files, diff_specs
from .models import ApiChange, ChangeCategory, ChangeSeverity, DiffReport
from .parser import SpecNormalizer, SpecParseError, load_spec_file, parse_spec_content
from .reporters import format_console, format_json, format_markdown

__all__ = [
    "__version__",
    "ApiContractDiffer",
    "diff_specs",
    "diff_files",
    "ApiChange",
    "ChangeCategory",
    "ChangeSeverity",
    "DiffReport",
    "SpecNormalizer",
    "SpecParseError",
    "load_spec_file",
    "parse_spec_content",
    "format_console",
    "format_markdown",
    "format_json",
]
