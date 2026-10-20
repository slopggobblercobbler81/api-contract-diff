"""CLI interface for api-contract-diff."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .differ import diff_files
from .reporters import Colors, format_console, format_json, format_markdown


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="api-contract-diff",
        description="Fast developer CLI and library to compare OpenAPI/Swagger specs and detect breaking changes.",
    )
    parser.add_argument("old_spec", help="Path to base/original OpenAPI or Swagger specification (JSON/YAML)")
    parser.add_argument("new_spec", help="Path to updated/modified OpenAPI or Swagger specification (JSON/YAML)")

    parser.add_argument(
        "-f",
        "--format",
        choices=["console", "markdown", "json"],
        default="console",
        help="Report output format (default: console)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Write report output to specified file path instead of stdout",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include non-breaking and informational changes in report (default for markdown/json)",
    )
    parser.add_argument(
        "--fail-on-breaking",
        dest="fail_on_breaking",
        action="store_true",
        default=True,
        help="Exit with non-zero exit code (1) if breaking changes are detected (default: enabled)",
    )
    parser.add_argument(
        "--no-fail",
        dest="fail_on_breaking",
        action="store_false",
        help="Do not exit with code 1 when breaking changes are detected",
    )
    parser.add_argument(
        "--ignore-path",
        action="append",
        default=[],
        help="Regex pattern to ignore matching endpoint paths (can be repeated)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color codes in console output",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.no_color:
        Colors.disable()

    try:
        report = diff_files(
            args.old_spec,
            args.new_spec,
            ignore_path_patterns=args.ignore_path,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    # Render formatted output
    include_all = args.all or args.format in ("markdown", "json")
    if args.format == "json":
        rendered = format_json(report)
    elif args.format == "markdown":
        rendered = format_markdown(report, include_non_breaking=include_all)
    else:
        rendered = format_console(report, include_non_breaking=include_all)

    # Write output
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(rendered)
            print(f"Contract diff report written to: {args.output}")
        except IOError as e:
            print(f"Error writing to output file: {e}", file=sys.stderr)
            return 2
    else:
        try:
            sys.stdout.write(rendered)
            if not rendered.endswith("\n"):
                sys.stdout.write("\n")
        except UnicodeEncodeError:
            safe_text = rendered.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8")
            sys.stdout.write(safe_text)
            if not safe_text.endswith("\n"):
                sys.stdout.write("\n")

    if report.has_breaking_changes and args.fail_on_breaking:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
