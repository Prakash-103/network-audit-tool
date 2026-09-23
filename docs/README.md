# 📖 Enterprise Network Infrastructure Audit Platform — Documentation Hub

Welcome to the technical documentation hub for the **Enterprise Network Infrastructure Audit Platform**. This directory contains comprehensive architectural specifications, procedural workflows, developer guides, security analyses, and operational policies governing the platform.

---

## 🧭 Documentation Index

| Document | Primary Audience | Key Contents |
| :--- | :--- | :--- |
| [System Architecture](file:///d:/Zenquix/NW_audit_tool/docs/ARCHITECTURE.md) | Architects, Tech Leads | Layered architecture, domain controllers, `AuditNormalizer` Single Source of Truth, Pydantic V2 data contracts, and subsystem deep dives. |
| [Audit Methodology](file:///d:/Zenquix/NW_audit_tool/docs/audit-methodology.md) | Lead Auditors, Compliance | 4-Stage audit lifecycle, Checks vs Findings vs Recommendations hierarchy, 5 canonical categories, severity standards, and mathematical compliance formulas. |
| [Developer Guide](file:///d:/Zenquix/NW_audit_tool/docs/DEVELOPER_GUIDE.md) | Developers, DevOps | Project directory tree, full REST API reference, `/api/audit/normalized` endpoint, adding audit rules, and running the 20-test test suite. |
| [Workflow & Sequence](file:///d:/Zenquix/NW_audit_tool/docs/WORKFLOW.md) | Engineers, Operators | End-to-end Mermaid sequence diagrams, live execution workflows, on-the-fly CLI retry mechanism, and deliverables generation. |
| [Supported Devices Matrix](file:///d:/Zenquix/NW_audit_tool/docs/supported-devices.md) | Network Engineers | Multi-vendor platform definitions (Cisco, Arista, Juniper, Palo Alto, Fortinet, Aruba, Huawei, MikroTik, Dell, Check Point), port prefix rules, and Catalog Studio guide. |
| [Threat Model (STRIDE)](file:///d:/Zenquix/NW_audit_tool/docs/threat-model.md) | Security Auditors, CISOs | STRIDE-based risk assessment, Zero-Storage Ephemeral RAM credentials, MITM safeguards, command injection defense, and SSRF prevention. |
| [Data Privacy Policy](file:///d:/Zenquix/NW_audit_tool/docs/data-privacy.md) | Compliance, SecOps | Zero-telemetry declaration, air-gapped operational model, local data retention controls, and sensitive secret scrubbing. |
| [Authorized Use Policy](file:///d:/Zenquix/NW_audit_tool/docs/authorized-use.md) | Legal, Operators | Mandatory authorization requirements, maintainer disclaimer of liability, and acceptable enterprise audit scenarios. |

---

## 🏛️ Core Architectural Foundations

### 1. Normalized Audit Engine (`AuditNormalizer`) as Single Source of Truth
The platform eliminates data discrepancy risks by channeling all audit task evaluations through a centralized intermediate normalizer: [`engine/audit_normalizer.py`](file:///d:/Zenquix/NW_audit_tool/engine/audit_normalizer.py).
- **Guaranteed 1:1 Consistency**: The live audit web console, programmatic API endpoint (`GET /api/audit/normalized`), and executive management reports share the exact same mathematical dataset.
- **Strict Data Hierarchy**:
  $$\text{Checks (Total Executed)} \;\longrightarrow\; \text{Findings (Non-PASS Only)} \;\longrightarrow\; \text{Recommendations (Action Items)}$$
  If 27 checks execute with 26 passes and 1 warning, the system reports **27 total checks, 26 passes, 1 warning, 0 failures, 96.3% compliance, exactly 1 finding, and exactly 1 prioritized recommendation**. No findings are fabricated when checks pass.

### 2. Five Canonical Audit Categories
Every vendor-specific testcase and protocol scenario is deterministically classified into one of five standard enterprise categories:
1. **Security**: AAA/TACACS+, SSHv2 enforcement, SNMPv3 privacy, management-plane ACLs, firewall zone traversal.
2. **Availability**: Spanning Tree root placement, dynamic LACP Port-Channels, FHRP default gateway redundancy, BFD link probing.
3. **Configuration**: VLAN database consistency, interface IP addressing, subnet masking, hostname and MTU alignment.
4. **Network Services**: NTP stratum synchronization, remote syslog redundancy, DNS resolution, DHCP snooping.
5. **Performance**: Interface duplex/speed negotiation, CRC error counters, hardware health, and environmental baselines.

### 3. Objective Category Compliance Percentage
$$\text{Category Compliance \%} = \left( \frac{\text{Passed Checks}}{\text{Total Executed Checks}} \right) \times 100$$
Each category calculates compliance based strictly on evaluated checks without arbitrary baseline floors or placeholder estimates.

### 4. Full Audit Evidence Traceability
Every finding presented in executive deliverables maintains transparent provenance linking it back to:
- **Target Device Hostname & Role**
- **Canonical Category & Check ID**
- **Exact Multi-Vendor CLI Command Executed**
- **Verified Factual Observation & Technical Impact**
- **Actionable Remediation Directive**

---

## 📊 Enterprise Deliverables Overview

The platform compiles two primary audit deliverables driven directly from the normalized dataset:

### Deliverable 1: 6-Page Formal Executive Management Report (Word .docx / HTML / PDF / Markdown)
Designed specifically for CIOs, CTOs, and Infrastructure Leadership, rendered on a clean, professional white background with 1:1 mathematical data consistency:
- **Page 1 — Executive Summary & Dashboard**: 5 KPI summary cards (`Audited Devices`, `Executed Checks`, `Passed Checks`, `Warnings`, `Compliance Rate %`), overall status badge, and an actionable priority plan derived strictly from verified findings.
- **Page 2 — Infrastructure Scope & Domain Classification**: Hardware inventory summary, facility distribution, and Table 03 domain compliance table displaying evaluated checks, pass/fail counts, and calculated compliance percentages.
- **Page 3 — Top Critical & High Risk Findings**: Granular finding cards detailing device hostname, category, Check ID, verification CLI command, factual observation, potential business impact, and recommended remediation.
- **Page 4 — Security Posture & Availability Matrix**: Evidence-based validation of management-plane controls alongside live protocol redundancy statuses.
- **Page 5 — Fleet Health & Multi-Facility Assessment**: Per-device health distribution, approved OS/firmware baseline alignment, and facility risk concentration.
- **Page 6 — Recommendations Roadmap & Evidence Traceability**: Prioritized 3-horizon engineering roadmap coupled with the **Audit Evidence Traceability Sample** table.

*Downloadable as Microsoft Word (`/api/export/executive/docx`), accessible in the web dashboard, via `/api/export/executive/html` (print-optimized for 1-click PDF), programmatically at `/api/audit/normalized`, or as Markdown at `/api/export/executive/md`.*

### Deliverable 2: Multi-Tab Excel Audit Evidence Workbook (`.xlsx`)
A formatted multi-sheet Excel workbook (`Audit_Evidence_Workbook.xlsx`) containing:
1. **Device Inventory Tab**: Complete device attributes, hardware models, serial numbers, and management IPs.
2. **Link Connections Tab**: Inter-switch link mapping, speeds, duplex, and port-channel memberships.
3. **Audit Status & Evidence Tab**: Granular test execution results, CLI verification commands, status (`PASS` / `FAIL` / `WARNING`), and sanitized output notes.

---

## 🔒 Security, Privacy & Zero-Storage Guarantees

- **Zero-Storage Ephemeral Credentials**: Device passwords, enable secrets, and private keys reside exclusively in temporary RAM during Stage 3 Netmiko live verification and are scrubbed immediately upon session completion. Zero disk persistence, zero database logging.
- **Sensitive Data Sanitization**: Configuration show command outputs pass through automated sanitizers masking passwords, SNMP communities, and pre-shared keys with `[REDACTED-SECRET]`.
- **Zero Telemetry Commitment**: The application collects **zero telemetry, analytics, or crash reports**, and operates completely air-gapped without phoning home. See [docs/data-privacy.md](file:///d:/Zenquix/NW_audit_tool/docs/data-privacy.md).
- **Authorized Use Notice**: Designed strictly for authorized compliance and security assessments. See [docs/authorized-use.md](file:///d:/Zenquix/NW_audit_tool/docs/authorized-use.md).
