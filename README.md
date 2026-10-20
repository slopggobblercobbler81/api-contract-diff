# 📑 api-contract-diff

[![CI](https://github.com/slopggobblercobbler81/api-contract-diff/actions/workflows/ci.yml/badge.svg)](https://github.com/slopggobblercobbler81/api-contract-diff/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> Fast developer CLI and library to compare OpenAPI/Swagger v2/v3 specifications, detect breaking API changes, and generate clean Markdown, JSON, and terminal reports for CI/CD gates.

---

## ✨ Features

- ⚡ **OpenAPI 3.x & Swagger 2.0 Support**: Seamlessly compares OpenAPI 3.0, 3.1, and Swagger 2.0 specs in JSON or YAML.
- 🚨 **Deep Semantic Breaking Change Detection**:
  - Removed endpoints or HTTP methods.
  - Newly added required query/header/path parameters.
  - Parameter optionality changes (`optional` ➔ `required`).
  - Parameter or payload data type mutations.
  - Request body requirement changes and removed media types.
  - Removed response status codes (`200`, `201`, `default`).
  - Removed properties in response payloads or added required fields in request payloads.
  - Added authentication requirements to public endpoints.
- 📝 **Multiple Rich Report Formats**:
  - **Console**: Clean, colorized terminal summary with breakdown by category.
  - **Markdown**: Formatted tables, badges, and summaries perfect for GitHub PR comments.
  - **JSON**: Machine-readable payload for CI pipeline automation and custom dashboards.
- 🚦 **CI/CD Quality Gate Ready**: Exits with code `1` when breaking changes are detected to automatically block breaking PRs.
- 🔄 **Cycle-Safe `$ref` Resolution**: Recursively resolves internal JSON pointers and `$ref` schemas without infinite loops.
- 🐍 **Standalone CLI & Python SDK**: Use directly from terminal or import as a Python library.

---

## 🚀 Installation

### Via pip
```bash
pip install api-contract-diff
```

### From source
```bash
git clone https://github.com/slopggobblercobbler81/api-contract-diff.git
cd api-contract-diff
pip install -e .
```

### Standalone (Zero-Install)
```bash
python -m api_contract_diff --help
```

---

## 🛠️ CLI Quickstart

### Compare two API specifications

```bash
# Basic console diff
api-contract-diff old_api.json new_api.json

# Include non-breaking changes and documentation updates
api-contract-diff old_api.yaml new_api.yaml --all

# Generate Markdown report for GitHub PR
api-contract-diff v1.json v2.json --format markdown -o breaking-changes.md

# Machine-readable JSON output
api-contract-diff v1.json v2.json --format json -o diff.json

# Ignore internal or deprecated path patterns
api-contract-diff v1.json v2.json --ignore-path "^/internal/" --ignore-path "^/admin/"

# Inspect without failing the build (exit code 0)
api-contract-diff v1.json v2.json --no-fail
```

---

## 📊 Sample Output

### Terminal Console Output
```text
API Contract Diff Report
  Old Spec: Petstore API (v1.0.0)
  New Spec: Petstore API (v2.0.0)
-----------------------------------------------------------------
Summary: 3 Breaking | 2 Non-Breaking | 0 Info

[BREAKING CHANGES] (3):
  * [GET] /pets
    Category: PARAMETER
    Change:   Added required parameter 'orgId' (query)
    Impact:   Existing clients that do not send this parameter will fail

  * [POST] /pets
    Category: SCHEMA
    Change:   Added required property 'species' in request body (application/json)
    Impact:   Clients not sending this field will be rejected

  * [DELETE] /pets/{petId}
    Category: ENDPOINT
    Change:   Operation 'DELETE /pets/{petId}' was removed

[NON-BREAKING CHANGES] (2):
  * [GET] /pets
    Category: PARAMETER
    Change:   Added optional parameter 'sort' (query)

  * [GET] /pets/search
    Category: ENDPOINT
    Change:   New endpoint 'GET /pets/search' added
```

---

## 🔍 Breaking Change Classification Matrix

| Component | Change | Classification |
|---|---|---|
| **Endpoint** | Removed path or HTTP method | 🔴 **BREAKING** |
| **Endpoint** | Added new path or HTTP method | 🟢 **NON-BREAKING** |
| **Endpoint** | Operation marked deprecated | ℹ️ **INFO** |
| **Parameter** | Added required parameter | 🔴 **BREAKING** |
| **Parameter** | Added optional parameter | 🟢 **NON-BREAKING** |
| **Parameter** | Changed parameter from optional to required | 🔴 **BREAKING** |
| **Parameter** | Changed parameter from required to optional | 🟢 **NON-BREAKING** |
| **Parameter** | Changed parameter data type | 🔴 **BREAKING** |
| **Parameter** | Removed parameter | 🔴 **BREAKING** |
| **Request Body** | Added required request body | 🔴 **BREAKING** |
| **Request Body** | Added optional request body | 🟢 **NON-BREAKING** |
| **Request Body** | Removed supported media type (e.g. `application/json`) | 🔴 **BREAKING** |
| **Request Body** | Added required property to request body schema | 🔴 **BREAKING** |
| **Request Body** | Removed property from request body schema | 🔴 **BREAKING** |
| **Response** | Removed successful response code (e.g., `200`, `201`) | 🔴 **BREAKING** |
| **Response** | Added response status code | 🟢 **NON-BREAKING** |
| **Response** | Removed property from response body schema | 🔴 **BREAKING** |
| **Response** | Added property to response body schema | 🟢 **NON-BREAKING** |
| **Security** | Added authentication requirement to previously public endpoint | 🔴 **BREAKING** |
| **Security** | Removed authentication requirement | 🟢 **NON-BREAKING** |

---

## 🤖 GitHub Actions CI/CD Integration

Block pull requests that introduce breaking API changes:

```yaml
name: API Contract Guard

on:
  pull_request:
    paths:
      - 'openapi/**'

jobs:
  check-breaking-changes:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout PR branch
        uses: actions/checkout@v4
        with:
          path: current

      - name: Checkout base branch
        uses: actions/checkout@v4
        with:
          ref: ${{ github.base_ref }}
          path: base

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install api-contract-diff
        run: pip install api-contract-diff

      - name: Run contract diff
        run: |
          api-contract-diff base/openapi/spec.yaml current/openapi/spec.yaml --format markdown -o pr-report.md

      - name: Comment PR
        if: always()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            if (fs.existsSync('pr-report.md')) {
              const body = fs.readFileSync('pr-report.md', 'utf8');
              github.rest.issues.createComment({
                issue_number: context.issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                body: body
              });
            }
```

---

## 🐍 Python Library API

```python
from api_contract_diff import diff_files, diff_specs

# Compare from files
report = diff_files("v1.json", "v2.json")

print(f"Has breaking changes: {report.has_breaking_changes}")
for change in report.breaking_changes:
    print(f"[{change.method}] {change.path}: {change.message}")

# Compare dictionaries directly
spec_a = {"openapi": "3.0.0", "paths": {}}
spec_b = {"openapi": "3.0.0", "paths": {}}
report = diff_specs(spec_a, spec_b)
```

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more details.
