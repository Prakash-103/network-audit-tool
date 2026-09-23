# Data Privacy & Telemetry Policy

The **Enterprise Network Infrastructure Audit Platform** respects the strict confidentiality of corporate infrastructure data.

---

## 1. Zero-Telemetry Commitment

> [!IMPORTANT]
> **This project does NOT collect telemetry, analytics, usage statistics, device fingerprints, or crash reports, and NEVER transmits client network data to external servers or project maintainers.**

- **No Remote Phone-Home**: There are zero tracking beacons, analytics scripts, or background telemetry connections in this software.
- **No Third-Party Cloud Dependencies**: The application operates completely air-gapped or on-premises. All REST API calls and UI state management execute locally between the user's browser and the local FastAPI server instance.

---

## 2. Infrastructure Data Collected Locally

During an audit session, the platform processes the following technical infrastructure attributes strictly on the local host:

| Data Type | Description | Local Storage Location |
| :--- | :--- | :--- |
| **Inventory Attributes** | Device ID, Hostname, Management IP, Vendor, Model, OS Version, Serial Number, Role | `project_state` in-memory / local JSON |
| **Topology Data** | CDP/LLDP neighbors, Port-Channels, VLAN tags, STP topology | RAM / temporary audit session |
| **Verification Output** | Raw `show` command CLI output retrieved via Netmiko | Local file system (`collected_logs/`) |
| **Audit Findings** | Pass/Fail status, deviation descriptions, remediation guidance | Local Excel export (`Audit_Evidence_Workbook.xlsx`) |

---

## 3. Data Retention & Deletion Controls

- **Audit Evidence Excel Workbooks**: Generated workbooks are saved directly to the operator's designated directory. They are never synchronized to external repositories.
- **Collected CLI Logs**: Device output text files stored in `collected_logs/` can be deleted at any time by the operator or cleared via the UI reset endpoint.
- **Credential Ephemerality**: Device passwords and authentication keys are kept exclusively in volatile memory for the duration of the audit execution session and are immediately erased. They are never written to disk, database, or cookies.
