# Enterprise SAP Data Pipeline

> A zero-dependency Python pipeline that validates and classifies business entity records before SAP integration.

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Table of Contents

1. [Description](#description)
2. [Key Features](#key-features)
3. [Tech Stack](#tech-stack)
4. [Requirements](#requirements)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Usage / Quick Start](#usage--quick-start)
8. [Public API](#public-api)
9. [Project Structure](#project-structure)
10. [Testing](#testing)
11. [Roadmap](#roadmap)
12. [Contributing](#contributing)
13. [Contact / Author](#contact--author)
14. [License](#license)

---

## Description

Enterprise SAP Data Pipeline is a lightweight Python script that automates the pre-processing of business entity records before they are uploaded to SAP systems. It validates VAT IDs (with full support for Polish NIP format) and email addresses, then routes each record to a success CSV for clean import or an error CSV for manual review. All pipeline events are written to a rotating log file with simultaneous console output.

The pipeline requires no third-party packages — only the Python standard library.

---

## Key Features

- **VAT ID validation** — strict regex check for Polish NIP (`PL` + 10 digits); non-empty check for all other countries
- **Email validation** — RFC-style regex pattern covering common address formats
- **Domestic / International classification** — automatic `group` field (`DOMESTIC` / `INTERNATIONAL`) added to every processed record
- **Dual-output CSV export** — clean records to `processed_success.csv`, rejected records with failure reason to `processed_errors.csv`
- **Rotating log file** — 5 MB cap, 5 backup archives, mirrored to stdout
- **Zero external dependencies** — standard library only (`json`, `csv`, `re`, `logging`, `pathlib`)
- **Auto-bootstrap** — creates `.gitignore`, `data/`, and `logs/` directories, and generates sample input data on first run

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.8+ |
| Validation | `re` (standard library) |
| I/O | `json`, `csv`, `pathlib` (standard library) |
| Logging | `logging`, `RotatingFileHandler` (standard library) |

---

## Requirements

- Python **3.8** or higher
- No third-party packages — see [`requirements.txt`](requirements.txt)

---

## Installation

```bash
# Clone the repository
git clone https://github.com/eryks23/Enterprise-SAP-Data-Pipeline.git
cd Enterprise-SAP-Data-Pipeline

# (Optional) Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

No `pip install` step is required — all dependencies ship with Python.

---

## Configuration

There are no environment variables or `.env` files. All paths are resolved relative to the script location using `pathlib`.

| Path constant | Description | Default |
|--------------|-------------|---------|
| `DATA_DIR` | Input and output CSV files | `<project_root>/data/` |
| `LOG_DIR` | Rotating log files | `<project_root>/logs/` |

Both directories are created automatically if they do not exist.

To use a custom input filename, pass it to the constructor:

```python
integrator = SAPIntegrator(input_filename="my_records.json")
```

---

## Usage / Quick Start

### 1. Prepare input data

Place a JSON file at `data/input_data.json`. The file must be a JSON array of objects.

| Field | Type | Description |
|-------|------|-------------|
| `vat_id` | `string` \| `null` | VAT / NIP number |
| `country` | `string` | ISO 3166-1 alpha-2 country code |
| `email` | `string` | Contact email address |

**`data/input_data.json`:**

```json
[
    {"vat_id": "PL1234567890", "country": "PL", "email": "contact@company.pl"},
    {"vat_id": "DE123456789",  "country": "DE", "email": "info@firma.de"},
    {"vat_id": null,           "country": "PL", "email": "broken@vat.pl"}
]
```

> **Note:** If `data/input_data.json` is missing, the pipeline generates a 3-record sample file automatically and continues processing.

### 2. Run the pipeline

```bash
python sap_integrator.py
```

### 3. Inspect the output

**`data/processed_success.csv`** — valid records ready for SAP import:

```
country,email,group,vat_id
PL,contact@company.pl,DOMESTIC,PL1234567890
DE,info@firma.de,INTERNATIONAL,DE123456789
```

**`data/processed_errors.csv`** — rejected records with the failure reason:

```
country,email,error_reason,group,vat_id
PL,broken@vat.pl,Validation failed (VAT/Email),DOMESTIC,
```

**`logs/sap_process.log`** — run summary (also printed to stdout):

```
2026-05-04 20:05:10,414 - INFO - Starting SAP Data Pre-processing pipeline...
2026-05-04 20:05:10,414 - INFO - Loaded 3 records from data source
2026-05-04 20:05:10,414 - INFO - File saved successfully: processed_success.csv
2026-05-04 20:05:10,414 - INFO - File saved successfully: processed_errors.csv
2026-05-04 20:05:10,414 - INFO - Process finished. Success: 2, Failures: 1
```

---

## Public API

Import `SAPIntegrator` to embed the pipeline in a larger workflow:

```python
from sap_integrator import SAPIntegrator
```

---

### `class SAPIntegrator`

Main processing class. Call `run()` for a full end-to-end execution, or invoke individual methods for custom orchestration.

---

#### `__init__(self, input_filename: str = "input_data.json")`

Initialises path constants and triggers `.gitignore` bootstrap.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_filename` | `str` | `"input_data.json"` | Filename within `data/` directory |

---

#### `load_data(self) -> None`

Reads `data/<input_filename>` and populates `self.data`. Logs an error and returns silently if the file is missing or the JSON is malformed.

---

#### `validate_vat(self, vat_id: Any, country: str) -> bool`

Validates a VAT ID against country-specific rules.

| Parameter | Description |
|-----------|-------------|
| `vat_id` | Raw VAT string (may be `None`) |
| `country` | ISO 3166-1 alpha-2 country code |

**Returns** `True` if valid, `False` otherwise.

| Country | Rule |
|---------|------|
| `PL` | Must match `^PL\d{10}$` |
| Any other | Must be a non-empty string |

**Example:**

```python
integrator = SAPIntegrator()
integrator.validate_vat("PL1234567890", "PL")   # True
integrator.validate_vat("ABC12345",     "PL")   # False
integrator.validate_vat("DE123456789",  "DE")   # True
integrator.validate_vat(None,           "PL")   # False
```

---

#### `validate_email(self, email: Any) -> bool`

Validates an email address using a standard regex pattern.

| Parameter | Description |
|-----------|-------------|
| `email` | Raw email string (may be `None`) |

**Returns** `True` if valid, `False` otherwise.

**Example:**

```python
integrator.validate_email("user@example.com")   # True
integrator.validate_email("invalid-email")       # False
integrator.validate_email(None)                  # False
```

---

#### `process_data(self) -> None`

Iterates `self.data`, validates each record, appends a `group` field, and routes the record to either `self.valid_data` or `self.error_log`.

---

#### `run(self) -> None`

Orchestrates the full pipeline:

```
load_data() → process_data() → write processed_success.csv → write processed_errors.csv → log summary
```

**Minimal usage example:**

```python
from sap_integrator import SAPIntegrator

integrator = SAPIntegrator(input_filename="my_records.json")
integrator.run()

print(f"Valid:  {len(integrator.valid_data)}")
print(f"Errors: {len(integrator.error_log)}")
```

---

## Project Structure

```
Enterprise-SAP-Data-Pipeline/
├── sap_integrator.py           # Main pipeline class and CLI entry point
├── requirements.txt            # Dependency manifest (stdlib only)
├── .gitignore                  # Auto-generated on first run
├── LICENSE
├── README.md
│
├── data/                       # Auto-created by the pipeline
│   ├── input_data.json         # Input records (auto-generated if missing)
│   ├── processed_success.csv   # Valid records ready for SAP import
│   └── processed_errors.csv    # Rejected records with error_reason
│
└── logs/                       # Auto-created by the pipeline
    └── sap_process.log         # Rotating log (max 5 MB × 5 backups)
```

> `data/` and `logs/` are added to `.gitignore` automatically on first run to prevent accidental commits of sensitive business data.

---

## Testing

The project currently has no automated test suite. To run a manual smoke test:

```bash
# 1. Remove any existing input data to trigger auto-generation
rm -f data/input_data.json

# 2. Run the pipeline
python sap_integrator.py

# 3. Verify output
cat data/processed_success.csv   # Should contain PL1234567890
cat data/processed_errors.csv    # Should contain the 2 invalid records
cat logs/sap_process.log         # Should show: Success: 1, Failures: 2
```

To exercise the validator methods in isolation:

```python
from sap_integrator import SAPIntegrator

s = SAPIntegrator()

# VAT validation
assert s.validate_vat("PL1234567890", "PL") is True
assert s.validate_vat("PL123",        "PL") is False
assert s.validate_vat("ANYTHING",     "DE") is True
assert s.validate_vat(None,           "PL") is False

# Email validation
assert s.validate_email("user@example.com") is True
assert s.validate_email("not-an-email")     is False
assert s.validate_email(None)               is False

print("All assertions passed.")
```

Contributions that add a `pytest`-based test suite are welcome — see [Contributing](#contributing).

---

## Roadmap

- [ ] Extend VAT validation to additional EU countries (currently only `PL` has regex enforcement)
- [ ] Add `pytest` test suite for `validate_vat` and `validate_email`
- [ ] Support configurable input/output paths via CLI arguments (`argparse`)
- [ ] Add a `--dry-run` flag: validate records without writing output files
- [ ] Support additional input formats (CSV, Excel)

---

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature-name`.
3. Commit your changes with a clear message: `git commit -m "Add: DE VAT validation regex"`.
4. Push to your fork: `git push origin feature/your-feature-name`.
5. Open a Pull Request against `main`.

Please keep changes focused — one feature or bug fix per PR. For significant changes, open an issue first to discuss the approach.

---

## Contact / Author

- **GitHub:** [eryks23](https://github.com/eryks23)
- **Repository:** [https://github.com/eryks23/Enterprise-SAP-Data-Pipeline](https://github.com/eryks23/Enterprise-SAP-Data-Pipeline)

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
