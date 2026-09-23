# Project Governance

This document describes how the **Enterprise Network Infrastructure Audit Platform** open-source project is governed, how decisions are made, and how contributors can become maintainers.

---

## 1. Roles and Responsibilities

### Project Lead / Benevolent Dictator for Life (BDFL)
- **Current Lead**: Prakash N ([@Prakash-103](https://github.com/Prakash-103))
- **Responsibilities**: Sets the high-level technical vision, roadmap priorities, architectural standards, and makes final determinations when consensus cannot be reached.

### Maintainers
- Maintainers are active contributors with write access to the repository.
- **Responsibilities**:
  - Review and merge pull requests.
  - Triage reported issues and feature proposals.
  - Oversee CI/CD stability, test coverage, and documentation accuracy.
  - Participate in security vulnerability remediation.

### Contributors
- Anyone who submits pull requests, files issues, improves documentation, or contributes new vendor profiles and audit scenarios.

---

## 2. Decision-Making Process

We strive for consensus among active maintainers:
1. **Minor Fixes & Documentation**: Approved and merged by any single maintainer after automated CI passes.
2. **Architecture, Schema, or Protocol Catalog Changes**: Require review and approval by at least two maintainers, including the Project Lead.
3. **Dispute Resolution**: If maintainers disagree on an architectural approach, the Project Lead provides the final decision based on alignment with the project's core design tenets (deterministic parsing, zero-storage credential hygiene, enterprise adoption).

---

## 3. Release Lifecycle & Semantic Versioning

The project follows [Semantic Versioning 2.0.0](https://semver.org/):
- **MAJOR (`X.y.z`)**: Incompatible API changes, breaking modifications to protocol catalog schemas, or breaking export formats.
- **MINOR (`x.Y.z`)**: New functionality, additional hardware vendor profiles, new audit domain checklists, and non-breaking features.
- **PATCH (`x.y.Z`)**: Backwards-compatible bug fixes, security patches, and documentation improvements.

---

## 4. Becoming a Maintainer

Active contributors who demonstrate technical competence, constructive collaboration, and consistent adherence to security and code quality standards may be nominated as maintainers by an existing maintainer. Maintainership requires unanimous agreement among existing maintainers.
