# Threat Model for Network Infrastructure Audit Platform

This document details the threat analysis and mitigation architecture for the **Enterprise Network Infrastructure Audit Platform** using the **STRIDE** methodology (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege).

---

## System Overview & Trust Boundaries

```text
       [ Network Engineer / Auditor ]
                     │  HTTPS / Web UI & REST API
                     ▼
          ┌─────────────────────┐
          │  Audit Application   │ ◄── [Trust Boundary 1: Web Interface]
          │   (FastAPI/Uvicorn) │
          └──────────┬──────────┘
                     │  Netmiko / Paramiko SSHv2 (Volatile RAM Credentials)
                     ▼
  ┌────────────────────────────────────────────────────────┐
  │ [Trust Boundary 2: Network Management Infrastructure]   │
  │                                                        │
  │   [Cisco Switch]    [Arista Leaf]    [Juniper Router]  │
  │   [FortiGate FW]    [Palo Alto FW]   [Aruba Controller]│
  └────────────────────────────────────────────────────────┘
```

---

## STRIDE Threat Matrix & Technical Mitigations

| Threat Category | Identified Attack Vector | Impact | Technical Mitigation in Architecture |
| :--- | :--- | :--- | :--- |
| **Spoofing (Identity)** | Unauthorized actor connects to network devices impersonating the audit server. | Rogue device commands; false audit evidence. | Outbound SSH connects exclusively from the auditor's whitelisted IP address; devices enforce strict management ACLs and key-based authentication. |
| **Tampering (Data Integrity)** | Man-in-the-Middle (MITM) modifies CLI show command output or audit rule catalogs. | Falsified compliance status; undetected vulnerabilities. | SSHv2 strong encryption and host-key validation; audit rules and test scenario catalogs are stored in validated configuration files with schema enforcement. |
| **Repudiation** | Operator claims an audit was triggered by an unauthorized party. | Inability to audit security incident timeline. | Event timestamping recorded in audit execution logs; zero credential retention ensures only authorized operators with active credentials can initiate jobs. |
| **Information Disclosure** | Device passwords, SNMP community strings, or topology IP schemes leak through logs. | Exposure of internal network secrets and compromise. | **Zero-Storage Ephemeral RAM**: credentials never touch disk. Automated regex sanitization strips `password`, `secret`, and `community` strings before generating Excel workbooks. |
| **Denial of Service (DoS)** | Excessive concurrent SSH audit sessions exhaust target device CPU/VTY lines. | Network device management unresponsiveness. | Built-in concurrency rate limiter (`MAX_CONCURRENT_SSH_WORKERS = 5`); sequential per-device execution; timeout thresholds per command (30s maximum). |
| **Elevation of Privilege** | An attacker injects destructive CLI write commands (`write erase`, `reload`) into show command fields. | Network disruption or configuration destruction. | **Strict Read-Only Command Enforcement**: CLI verification commands in Catalog Studio are strictly validated for inspection verbs (`show`, `display`, `get`, `check`). Config-mode commands (`configure terminal`, `set`, `delete`) are rejected. |

---

## Specific Attack Vectors & Architectural Defenses

### 1. Command Injection Mitigation
- **Risk**: A user inputs arbitrary shell or device commands in test scenario fields.
- **Defense**: All commands dispatched via Netmiko run through `send_command()` which executes within the device's operational mode (exec/view). Semicolon-separated commands are parsed and validated against whitelisted operational verification patterns.

### 2. Server-Side Request Forgery (SSRF)
- **Risk**: An attacker supplies malicious Management IP addresses (e.g. AWS metadata endpoint `169.254.169.254` or internal services).
- **Defense**: IP addresses in device inventory are validated against strict IPv4/IPv6 CIDR format rules. Subnet isolation ensures outbound traffic routes only to designated device management networks.

### 3. Supply-Chain & Dependency Poisoning
- **Risk**: Compromised upstream PyPI package executes malicious code during audit.
- **Defense**: Pinned dependency version ranges in `requirements.txt`; machine-readable SBOM (`sbom/sbom.spdx.json`); weekly automated security alerts via Dependabot; GitHub Actions CI validation across multiple Python runtimes.
