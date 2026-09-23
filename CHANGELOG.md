# Changelog

All notable changes to the **Enterprise Network Infrastructure Audit Platform** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.3.0] - 2026-09-23

### Added
- **Normalized Audit Engine (`AuditNormalizer`)**: Centralized intermediate normalization engine (`engine/audit_normalizer.py`) establishing a definitive **Single Source of Truth (SSOT)** across the entire application.
- **1:1 Mathematical Consistency Guarantee**: Ensures identical metrics between the live audit screen, normalized JSON API, and executive report (e.g., 27 executed checks with 26 passes and 1 warning yield exactly 96.3% compliance, 1 finding, and 1 recommendation).
- **Strict Hierarchy: Checks $\to$ Findings $\to$ Recommendations**: Enforces that findings are created **strictly** when `check.status != PASS`. Eliminates phantom exposures, false-positive findings when checks pass, and artificial action items.
- **Publication-Grade 6-Page Executive Management Report**:
  - Rebuilt template (`templates/executive_report.html`) with clean, high-contrast, professional white background optimized for 1-click print-to-PDF.
  - Page 1: 5 KPI summary cards (`Audited Devices`, `Executed Checks`, `Passed Checks`, `Warnings`, `Compliance Rate %`), overall status badge, and an actionable priority plan derived strictly from verified findings.
  - Page 2: Infrastructure scope breakdown and Table 03 domain compliance table displaying evaluated checks, pass/fail counts, and calculated compliance percentages.
  - Page 3: Actionable engineering finding cards with Device Hostname, Category, Check ID, Verification Command, Observation, Potential Impact, and Remediation.
  - Page 4: Evidence-backed security posture controls and live protocol redundancy statuses (eliminating hardcoded placeholder warnings).
  - Page 5: Fleet health distribution and approved OS baseline alignment.
  - Page 6: Prioritized recommendations roadmap and **Audit Evidence Traceability Sample** table.
- **Downloadable Word Document (.docx) Export**: Built dedicated `ExecutiveDocxGenerator` (`reporting/docx_generator.py`) and API endpoint `GET /api/export/executive/docx` enabling 1-click download of the complete 6-page Executive Report as a formal, corporate-styled Microsoft Word (.docx) document with verified KPI metrics, domain compliance tables, finding blocks, and evidence traceability.
- **Audit Evidence Traceability Standard**: Links every finding directly to its target device, Check ID, verification CLI command, and raw evidence output notes.
- **Canonical Five Audit Categories**: Unified classification across `Security`, `Availability`, `Configuration`, `Network Services`, and `Performance` with explicit precedence rules.
- **Normalized Audit API Endpoint**: Added `GET /api/audit/normalized` delivering canonical `NormalizedAudit` JSON.
- **Central Documentation Hub**: Added comprehensive documentation index at `docs/README.md`.
- **Expanded Test Suite**: Added 1:1 mathematical data consistency tests, schema validation, and zero-finding guarantees (`tests/test_executive_report.py`), bringing the test suite to 20 passing tests.

### Changed
- Refactored `reporting/executive_report.py` to consume `AuditNormalizer.normalize_audit(state)` as the sole source of truth for HTML, print PDF, and Markdown exports.
- Synchronized `/api/export/executive/metrics` with `AuditNormalizer` summary metrics.
- Updated `docs/ARCHITECTURE.md`, `docs/audit-methodology.md`, `docs/DEVELOPER_GUIDE.md`, and `docs/WORKFLOW.md` to reflect the Normalized Audit Architecture.

---

## [0.2.0] - 2026-09-23

### Added
- **Catalog Studio Tab Reordering**: Vendor & Platform Profiles tab is now positioned first and active by default; Test Scenarios & CLI Commands is second.
- **Dynamic Vendor CLI Verification Fields**: Test scenario add/edit modal now dynamically renders CLI verification command input fields for all configured vendors in the catalog.
- **Automatic Scenario Vendor Synchronization**: Adding or importing a new vendor profile in Catalog Studio automatically synchronizes all test scenarios in the catalog to include command entries for the new vendor.
- **Add Device Hardware Model Dropdown**: Hardware Model in the Add Device modal is now a dynamic dropdown populated with the selected vendor's catalog platforms, with support for custom models.
- **Add Device Port Speed from Catalog**: Port Speed options in Add Device are now dynamically populated based on the vendor's supported speeds configured in the catalog.

### Changed
- Refactored `CatalogManager.add_or_update_vendor` and `CatalogManager.delete_vendor` to maintain atomic synchronization between vendor profiles and scenario verification commands.
- Enhanced test suite with dynamic catalog and UI synchronization unit tests (`tests/test_ui_catalog_sync.py`).

---

## [0.1.0] - 2026-09-20

### Added
- Initial release of the Enterprise Network Infrastructure Audit Platform.
- Four-stage audit workflow: Device Inventory, Topology/Protocol Catalog, Live Stage 3 CLI verification, and Stage 4 Excel evidence generation.
- Support for 10 hardware vendors (Cisco, Arista, Juniper, Palo Alto, Fortinet, Aruba, Huawei, Mikrotik, Dell, CheckPoint).
- Zero-Storage Ephemeral Security architecture for Netmiko SSH credentials.
- Multi-tab Excel audit evidence export (`Audit_Evidence_Workbook.xlsx`).
