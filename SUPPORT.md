# Support Guidelines

Thank you for using the **Enterprise Network Infrastructure Audit Platform**! Here is how to obtain support, report issues, and collaborate with the community.

---

## 1. Getting Help

### Community Discussions & Questions
If you have questions about:
- How to configure custom multi-vendor port prefixes
- How to write regex patterns for new device show commands
- Deployment architectures behind corporate reverse proxies
- Best practices for scheduled audit runs

Please use **GitHub Discussions** rather than filing an issue. This keeps the issue tracker dedicated to actionable bugs and feature proposals.

---

## 2. Reporting Bugs & Issues

If you encountered a bug, unexpected audit failure, or parser error:
1. Search existing [GitHub Issues](https://github.com/Prakash-103/network-audit-tool/issues) to verify it hasn't already been reported or resolved.
2. Open a new issue using our structured **Bug Report** template.
3. Include:
   - Target vendor and operating system version (e.g. `Cisco Catalyst 9300 / IOS-XE 17.9`).
   - Audit test scenario ID where the failure occurred (e.g. `TS-HEALTH-01`).
   - Python version and runtime environment (Windows, Linux, Docker).
   - Sanitized command output or stack trace (ensure **all passwords, IP spaces, and secrets are scrubbed**).

---

## 3. Requesting New Vendors & Features

If you need support for an additional network vendor (e.g. Brocade, Allied Telesis, SonicWall) or audit domain:
- Open a **Feature / Vendor Support Request** issue detailing the hardware model, default OS, and standard CLI `show` verification commands.
- Better yet: consider contributing the vendor profile directly via a Pull Request (see [CONTRIBUTING.md](file:///d:/Zenquix/NW_audit_tool/CONTRIBUTING.md)).

---

## 4. Security Vulnerabilities

> [!CAUTION]
> Do NOT file public GitHub issues for security vulnerabilities or credential leakage concerns.

Please follow the private disclosure process documented in [SECURITY.md](file:///d:/Zenquix/NW_audit_tool/SECURITY.md).
