# Project Roadmap

This document outlines the strategic technical roadmap for the **Enterprise Network Infrastructure Audit Platform**. Priorities are guided by community feedback, enterprise compliance standards, and operational requirements.

---

## Current Release: v0.3.0 (Active)

- [x] **Normalized Audit Architecture (`AuditNormalizer`)**: Canonical Single Source of Truth (`engine/audit_normalizer.py`) ensuring zero divergence across views.
- [x] **1:1 Mathematical Consistency Guarantee**: Identical check counts, pass/fail metrics, and compliance percentages across the live audit dashboard, normalized JSON API (`/api/audit/normalized`), and executive reports.
- [x] **Strict Hierarchy (Checks $\to$ Findings $\to$ Recommendations)**: Findings generated strictly when `status != PASS`, eliminating artificial risk inflation and phantom exposures.
- [x] **Publication-Grade 6-Page Executive Management Report**: Formal white-background executive document designed for CIOs and CTOs, print-optimized for 1-click PDF generation.
- [x] **Audit Evidence Traceability Standard**: Granular lineage linking every finding to its Device Hostname, Check ID, verification CLI command, and raw evidence output.
- [x] **Five Canonical Audit Categories**: Standardized classification (`Security`, `Availability`, `Configuration`, `Network Services`, `Performance`) with true mathematical compliance percentages.
- [x] **Central Documentation Hub**: Dedicated technical documentation entrypoint at `docs/README.md`.
- [x] **Modular Test Scenario & Vendor Platform Studio**: Code-independent management of hardware vendors, platforms, port prefixes, and test scenarios.
- [x] **Dynamic Vendor Verification Linkage**: Automatic synchronization of testcase CLI command fields across all configured vendors.
- [x] **Zero-Storage Ephemeral Credentials**: RAM-only credential execution for Stage 3 Netmiko live verification sessions.

---

## Phase 1: Near-Term Priorities (v0.4.0)

- [ ] **Docker & Containerized Deployment**: Production-ready `Dockerfile` and `docker-compose.yml` with multi-stage build optimization and non-root execution.
- [ ] **TextFSM & ntc-templates Integration**: Supplementary structured parsing for complex multi-vendor routing tables and interface statistics.
- [ ] **Scheduled & Recurring Audit Crons**: Headless CLI trigger mode (`--cron`) allowing scheduled audits with email or webhook dispatch.
- [ ] **Enhanced Secret Scrubbing Engine**: Extended regex filters to automatically sanitize BGP MD5 keys, TACACS/RADIUS shared secrets, and IPsec crypto keys.

---

## Phase 2: Mid-Term Enhancements (v0.5.0)

- [ ] **API-Based Device Adapters**:
  - Arista eAPI integration (JSON-RPC over HTTPS).
  - Cisco RESTCONF / NETCONF transport alternatives alongside Netmiko SSH.
  - Palo Alto XML API connector.
- [ ] **Automated CIS Benchmark Mapping**: Tagging test scenarios with specific CIS Network Device Benchmark and NIST SP 800-53 controls.
- [ ] **Comparative Audit Diffing**: Compare baseline audit workbooks against subsequent runs to instantly visualize configuration drift and newly introduced risks.

---

## Phase 3: Long-Term Enterprise Vision (v1.0.0+)

- [ ] **Multi-Cloud Hybrid Network Auditing**: Audit adapters for cloud transit gateways, AWS VPC route tables, Azure Virtual WAN, and Google Cloud VPCs.
- [ ] **Enterprise RBAC & OIDC/SAML SSO**: Integration with corporate identity providers (Okta, Keycloak, Microsoft Entra ID).
- [ ] **Automated Remediation Playbooks**: Export verified remediation steps as Ansible playbooks or Terraform HCL definitions.
