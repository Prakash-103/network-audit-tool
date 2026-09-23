# Open Source Public Release Pre-Flight Checklist

Before making this repository public on GitHub, complete and verify every item on this checklist to ensure intellectual property clarity, credential hygiene, and legal compliance.

---

## 1. Legal, Employer & IP Clearance

- [ ] **Ownership & Employment Verification**: Confirm that you have explicit, written authorization from your employer or company to open-source this code under the Apache License 2.0.
- [ ] **Proprietary Code Audit**: Confirm that no proprietary frameworks, internal company APIs, or internal tooling libraries are included.
- [ ] **Customer Data Scrub**: Verify that zero customer names, client site names, real corporate IP spaces, or actual production hostnames exist in the repository or commit history.
- [ ] **License Consistency**: Confirm that `LICENSE` is set to Apache 2.0 with the correct copyright header (`Copyright 2026 Prakash N`).
- [ ] **NOTICE File**: Confirm that `NOTICE` and `THIRD-PARTY-NOTICES.md` accurately attribute all direct and indirect dependencies.
- [ ] **Trademark Compliance**: Review `TRADEMARKS.md` to ensure no vendor trademarks (Cisco, Arista, etc.) imply official endorsement.

---

## 2. Secrets, Credentials & Git History Hygiene

- [ ] **Source Code Secret Scan**: Search for hardcoded passwords, tokens, API keys, or enable secrets using tools like `trufflehog` or `gitleaks`:
  ```bash
  gitleaks detect --source . --verbose
  ```
- [ ] **Git Commit History Scan**: Verify that secrets were not committed in past commits (deleting a secret from HEAD is insufficient if it exists in Git history).
- [ ] **Dotenv & Key Files**: Ensure `.env`, `.env.*` (except `.env.example`), `*.key`, and `*.pem` are excluded in `.gitignore`.
- [ ] **Evidence & Log Files**: Verify that `collected_logs/` and `*.xlsx` evidence workbooks are not tracked in Git.

---

## 3. Security, Supply Chain & Threat Modeling

- [ ] **Vulnerability Reporting Policy**: Confirm that `SECURITY.md` accurately describes reporting procedures and private advisory links.
- [ ] **Threat Model**: Ensure `docs/threat-model.md` accurately reflects current architecture.
- [ ] **Authorized Use Disclaimer**: Confirm `docs/authorized-use.md` is present and prominently linked.
- [ ] **Data Privacy & Telemetry**: Confirm `docs/data-privacy.md` accurately states zero telemetry collection.
- [ ] **SBOM Verification**: Verify `sbom/sbom.spdx.json` matches current `requirements.txt` packages and versions.
- [ ] **Dependency Audit**: Run safety / pip-audit on dependencies:
  ```bash
  pip install pip-audit && pip-audit -r requirements.txt
  ```

---

## 4. Code Quality, Tests & CI Automation

- [ ] **Automated Tests Passing**: Confirm 100% test pass rate across all suites:
  ```bash
  python -m unittest discover tests
  ```
- [ ] **GitHub Actions CI**: Verify `.github/workflows/ci.yml` is enabled and passing on Ubuntu and Windows.
- [ ] **Dependabot Configured**: Ensure `.github/dependabot.yml` is active for automated dependency vulnerability monitoring.
- [ ] **Issue & PR Templates**: Verify `.github/ISSUE_TEMPLATE/` and `.github/pull_request_template.md` are present.
- [ ] **Linting & Formatting**: Ensure code adheres to PEP 8 standards with no syntax or import errors.

---

## 5. Documentation & Public Presentation

- [ ] **README Polish**: Verify `README.md` contains clear architectural diagrams, feature list, quick start commands, and links to documentation.
- [ ] **Audit Methodology**: Confirm `docs/audit-methodology.md` accurately explains the 4-stage audit workflow.
- [ ] **Supported Devices Matrix**: Confirm `docs/supported-devices.md` matches active catalog platforms.
- [ ] **Contributing Guide**: Ensure `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md` are clearly linked.
- [ ] **Governance & Roadmap**: Review `GOVERNANCE.md` and `ROADMAP.md` for accuracy.
- [ ] **Release Tagging**: Tag the initial public release using semantic versioning (e.g. `v0.2.0` or `v1.0.0`):
  ```bash
  git tag -a v0.2.0 -m "Release v0.2.0 - Modular Studio & Multi-Vendor Audit"
  git push origin v0.2.0
  ```
- [ ] **Release Notes Published**: Create GitHub Release with release notes matching `CHANGELOG.md`.
