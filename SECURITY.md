# Security Policy

The **Enterprise Network Infrastructure Audit Platform** is designed for deployment in sensitive enterprise environments. Security, credential hygiene, and least-privilege operations are foundational architectural requirements.

---

## Supported Versions

Security updates and vulnerability patches are actively maintained for the following versions:

| Version | Supported | Status |
| :--- | :--- | :--- |
| **v1.0.x** | :white_check_mark: Yes | Current Stable Release |
| **v0.2.x** | :white_check_mark: Yes | Maintenance / Security Backports |
| **< v0.2.0** | :x: No | Unsupported |

---

## Reporting a Vulnerability

We take all security vulnerabilities seriously. If you discover a potential vulnerability, please **do not open a public issue**. Public disclosure before a fix is available puts networks at risk.

### Preferred Reporting Method
Report vulnerabilities privately using **GitHub Private Vulnerability Reporting**:
1. Navigate to the **Security** tab of the repository on GitHub.
2. Select **Advisories** and click **Report a vulnerability**.
3. Provide detailed steps to reproduce, impact assessment, and any affected configurations.

### Response Timeframes & SLAs
- **Initial Acknowledgement**: Within 48 hours.
- **Triage & Severity Assessment**: Within 5 business days.
- **Patch Development & Advisory Disclosure**: Coordinated disclosure within 30 to 90 days depending on severity.

---

## Security Architecture & Core Principles

### 1. Zero-Storage Ephemeral Credentials
- **Volatile RAM Only**: Device administrative credentials (username, password, enable secret, SSH private keys) provided for Stage 3 Live Verification audits are held strictly in temporary process RAM during the execution lifetime of that job.
- **Zero Disk Persistence**: Credentials are **never** written to SQLite/database storage, configuration JSON files, local caches, browser cookies, or local storage.
- **Immediate RAM Erasure**: Immediately upon completion (or cancellation) of the Netmiko SSH session, credential objects are overwritten and dereferenced in memory.
- **Zero Logging**: Device passwords and secrets are strictly excluded from application log streams, audit trails, and debug files.

### 2. Transport Layer Security & SSH Hardening
- **Encrypted Shell Access**: Live audit verification uses Netmiko/Paramiko over SSHv2. Insecure plaintext Telnet is strongly discouraged and disabled by default.
- **Host Key Verification**: System administrators should configure known_hosts verification in production deployments.
- **Ciphers & MACs**: Avoid legacy deprecated ciphers (such as `des`, `3des-cbc`, or `diffie-hellman-group1-sha1`).

### 3. Output Sanitization & Evidence Redaction
- **Regex Secret Scrubbing**: Device configurations retrieved during audits (`show running-config`, `show startup-config`) pass through deterministic regex sanitizers before being written into Excel workbooks or stored evidence logs.
- **Password Hashes & Pre-Shared Keys**: Passwords, SNMP community strings (`snmp-server community`), BGP MD5 secrets, and IPsec preshared keys (`pre-shared-key`) are masked with `[REDACTED-SECRET]`.

### 4. Least-Privilege Recommended Access
We strongly recommend configuring dedicated read-only network administrator accounts for audit tooling:
- **Cisco IOS/IOS-XE**: Privilege level 15 read-only view or custom parser view (`parser view AUDIT_VIEW` allowing only `show` commands).
- **Arista EOS**: Role-based access control with `read-only` command rules.
- **Juniper Junos**: Custom login class with `view` permission only.

---

## Security Best Practices for Operators

1. **Localhost Binding**: By default, bind the application daemon to `127.0.0.1` (`HOST=127.0.0.1`) behind a reverse proxy (Nginx, Traefik, Caddy) enforcing TLS with corporate SSO/OIDC authentication.
2. **Firewall & Jump Host Control**: Restrict outbound SSH access from the audit server strictly to target device management IP subnets.
3. **Environment Isolation**: Deploy within a hardened Linux container or dedicated management VLAN.
