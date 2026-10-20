"""Report formatters for terminal console, Markdown, and JSON."""

from __future__ import annotations

import json
from typing import List

from .models import ApiChange, ChangeSeverity, DiffReport


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"

    @classmethod
    def disable(cls):
        cls.RESET = ""
        cls.BOLD = ""
        cls.RED = ""
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.BLUE = ""
        cls.MAGENTA = ""
        cls.CYAN = ""
        cls.GRAY = ""


def format_console(report: DiffReport, include_non_breaking: bool = True) -> str:
    lines: List[str] = []
    lines.append(f"{Colors.BOLD}API Contract Diff Report{Colors.RESET}")
    lines.append(f"  Old Spec: {Colors.CYAN}{report.old_spec_title} (v{report.old_version}){Colors.RESET}")
    lines.append(f"  New Spec: {Colors.CYAN}{report.new_spec_title} (v{report.new_version}){Colors.RESET}")
    lines.append("-" * 65)

    breaking = report.breaking_changes
    non_breaking = report.non_breaking_changes
    info = report.info_changes

    summary_color = Colors.RED if report.has_breaking_changes else Colors.GREEN
    lines.append(
        f"{summary_color}{Colors.BOLD}Summary:{Colors.RESET} "
        f"{Colors.RED}{len(breaking)} Breaking{Colors.RESET} | "
        f"{Colors.GREEN}{len(non_breaking)} Non-Breaking{Colors.RESET} | "
        f"{Colors.BLUE}{len(info)} Info{Colors.RESET}"
    )
    lines.append("")

    if not report.changes:
        lines.append(f"{Colors.GREEN}[IN SYNC]{Colors.RESET} Specifications are identical. No API changes detected.")
        return "\n".join(lines)

    if breaking:
        lines.append(f"{Colors.RED}{Colors.BOLD}[BREAKING CHANGES] ({len(breaking)}):{Colors.RESET}")
        for c in breaking:
            method_str = f"[{c.method.upper()}] " if c.method else ""
            lines.append(f"  {Colors.RED}* {Colors.BOLD}{method_str}{c.path}{Colors.RESET}")
            lines.append(f"    Category: {Colors.MAGENTA}{c.category.value}{Colors.RESET}")
            lines.append(f"    Change:   {Colors.YELLOW}{c.message}{Colors.RESET}")
            if c.details:
                lines.append(f"    Impact:   {Colors.GRAY}{c.details}{Colors.RESET}")
            lines.append("")

    if include_non_breaking:
        if non_breaking:
            lines.append(f"{Colors.GREEN}{Colors.BOLD}[NON-BREAKING CHANGES] ({len(non_breaking)}):{Colors.RESET}")
            for c in non_breaking:
                method_str = f"[{c.method.upper()}] " if c.method else ""
                lines.append(f"  {Colors.GREEN}* {Colors.BOLD}{method_str}{c.path}{Colors.RESET}")
                lines.append(f"    Category: {Colors.MAGENTA}{c.category.value}{Colors.RESET}")
                lines.append(f"    Change:   {Colors.GRAY}{c.message}{Colors.RESET}")
                lines.append("")

        if info:
            lines.append(f"{Colors.BLUE}{Colors.BOLD}[INFORMATIONAL CHANGES] ({len(info)}):{Colors.RESET}")
            for c in info:
                method_str = f"[{c.method.upper()}] " if c.method else ""
                lines.append(f"  {Colors.BLUE}* {Colors.BOLD}{method_str}{c.path}{Colors.RESET}")
                lines.append(f"    Change: {Colors.GRAY}{c.message}{Colors.RESET}")
                lines.append("")

    return "\n".join(lines)


def format_markdown(report: DiffReport, include_non_breaking: bool = True) -> str:
    lines: List[str] = [
        "# 📑 API Contract Diff Report",
        "",
        f"- **Base Specification**: `{report.old_spec_title}` (v{report.old_version})",
        f"- **Updated Specification**: `{report.new_spec_title}` (v{report.new_version})",
        "",
        "## 📊 Summary",
        "",
        "| Status | Breaking | Non-Breaking | Info | Total Changes |",
        "|---|---|---|---|---|",
    ]

    status_badge = "❌ **BREAKING**" if report.has_breaking_changes else "✅ **COMPATIBLE**"
    lines.append(
        f"| {status_badge} | **{len(report.breaking_changes)}** | {len(report.non_breaking_changes)} | {len(report.info_changes)} | {len(report.changes)} |"
    )
    lines.append("")

    if report.breaking_changes:
        lines.append("## 🚨 Breaking Changes")
        lines.append("")
        lines.append("| Method | Path | Category | Description |")
        lines.append("|---|---|---|---|")
        for c in report.breaking_changes:
            m = f"`{c.method.upper()}`" if c.method else "-"
            lines.append(f"| {m} | `{c.path}` | `{c.category.value}` | {c.message} |")
        lines.append("")

    if include_non_breaking:
        if report.non_breaking_changes:
            lines.append("## ✨ Non-Breaking / Additive Changes")
            lines.append("")
            lines.append("| Method | Path | Category | Description |")
            lines.append("|---|---|---|---|")
            for c in report.non_breaking_changes:
                m = f"`{c.method.upper()}`" if c.method else "-"
                lines.append(f"| {m} | `{c.path}` | `{c.category.value}` | {c.message} |")
            lines.append("")

        if report.info_changes:
            lines.append("## ℹ️ Informational Changes")
            lines.append("")
            lines.append("| Method | Path | Description |")
            lines.append("|---|---|---|")
            for c in report.info_changes:
                m = f"`{c.method.upper()}`" if c.method else "-"
                lines.append(f"| {m} | `{c.path}` | {c.message} |")
            lines.append("")

    lines.append("---")
    lines.append("*Generated by [api-contract-diff](https://github.com/slopggobblercobbler81/api-contract-diff)*")
    return "\n".join(lines) + "\n"


def format_json(report: DiffReport) -> str:
    return json.dumps(report.to_dict(), indent=2) + "\n"
