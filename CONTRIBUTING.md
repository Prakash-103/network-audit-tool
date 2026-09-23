# Contributing to the Enterprise Network Infrastructure Audit Platform

Thank you for your interest in contributing to the **Enterprise Network Infrastructure Audit Platform**! We welcome contributions from network automation engineers, security auditors, and software developers.

By contributing to this project, you agree that your contributions are licensed under the [Apache License 2.0](file:///d:/Zenquix/NW_audit_tool/LICENSE) and adhere to our [Code of Conduct](file:///d:/Zenquix/NW_audit_tool/CODE_OF_CONDUCT.md).

---

## Development Environment Setup

### Prerequisites
- **Python 3.10+** (tested on 3.10, 3.11, and 3.12)
- **Git**
- A modern web browser (Chrome, Firefox, Safari, Edge)

### Installation
```bash
# Clone the repository
git clone https://github.com/Prakash-103/network-audit-tool.git
cd network-audit-tool

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Running the Application Locally
```bash
# Launch the local development server with auto-reload
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## Running the Automated Test Suite

Before submitting any code changes, ensure all unit and integration tests pass cleanly:

```bash
# Run the complete test suite
python -m unittest discover tests

# Or run specific test modules
python -m unittest tests/test_catalog_manager.py
python -m unittest tests/test_ui_catalog_sync.py
python -m unittest tests/test_audit_engine.py
```

---

## How to Contribute

### 1. Adding a New Hardware Vendor or Model
You can contribute new hardware vendors or platforms in two ways:
- **Code-Independent (Preferred)**: Open **Catalog Studio** in the UI, create or edit the Vendor Profile, and export the resulting JSON.
- **Via Configuration File**: Add the vendor definition directly to [config/vendor_catalog.json](file:///d:/Zenquix/NW_audit_tool/config/vendor_catalog.json):
  ```json
  {
    "name": "VendorShortName",
    "display_name": "Full Vendor Name",
    "default_os_version": "v1.0",
    "port_prefix": "ge-0/0/",
    "platforms": ["Model-100", "Model-200"],
    "supported_speeds": ["1G", "10G", "25G"]
  }
  ```

### 2. Adding or Enhancing Audit Test Scenarios
To contribute audit test scenarios (e.g. BGP EVPN verification, VXLAN, MACsec, 802.1X):
- Edit [config/test_scenarios.json](file:///d:/Zenquix/NW_audit_tool/config/test_scenarios.json).
- Provide vendor-specific `show` commands for all major platforms (Cisco, Arista, Juniper, etc.) and a generic `Default` fallback.
- Specify clear, actionable remediation guidance in the `recommendation` field.

### 3. Adding CLI Parsers or Sanitizers
Deterministic CLI parsing routines reside in `parsers/`. We adhere strictly to:
- **Deterministic Parsing**: Routine CLI inspection uses deterministic regex or TextFSM patterns rather than non-deterministic LLM inference.
- **Sensitive Data Redaction**: Ensure any parser handling credential or secret output masks strings matching `password`, `secret`, `hash`, or `community`.

---

## Pull Request Guidelines

1. **Create a Topic Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Commit Hygiene**:
   - Write clear, imperative commit messages (e.g. `feat: add Aruba AOS-CX EVPN audit scenario`, `fix: sanitize BGP MD5 passwords in evidence logs`).
   - Reference relevant issue numbers.
3. **Never Commit Secrets or Customer Data**:
   - Ensure test fixtures contain **only dummy data** (e.g., `10.254.1.0/24`, `SN-0000000`, `Acme Corp`).
   - Run `git diff` before committing to verify no credentials, customer configurations, or sensitive IP spaces are included.
4. **Submit Your Pull Request**:
   - Open a PR against `main`. Fill in the PR template completely and ensure GitHub Actions CI passes.
