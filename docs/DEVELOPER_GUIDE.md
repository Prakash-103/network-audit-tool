# Enterprise Network Infrastructure Audit Tool — Developer & Extensibility Guide

## 1. Development Environment Setup

### Prerequisites
- **Python 3.10+** (Tested on Python 3.10, 3.11, 3.12, 3.13)
- **Git**

### Installation Steps
```bash
# 1. Clone the repository
git clone https://github.com/Prakash-103/network-audit-tool.git
cd network-audit-tool

# 2. Create and activate a virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start local development server
python app.py
# Or run with uvicorn directly:
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```
Open your browser at `http://127.0.0.1:8000` to interact with the web dashboard.

---

## 2. Project Directory Structure

```text
NW_audit_tool/
├── app.py                     # Clean FastAPI application bootstrap & router orchestrator
├── api/                       # API Routers & Request/Response Schemas
│   ├── schemas.py             # Consolidated Pydantic V2 request & response schemas
│   └── routers/               # Modular FastAPI Domain APIRouters
│       ├── __init__.py        # Router aggregator
│       ├── state.py           # State & enterprise preset endpoints (/api/state)
│       ├── devices.py         # Device inventory & configuration logs (/api/devices)
│       ├── topology.py        # Links, Port-Channels & graph validation (/api/topology)
│       ├── projects.py        # Blank project setup & saved workbooks (/api/project)
│       ├── reports.py         # Excel & Executive Report exports (/api/export)
│       ├── catalog.py         # Vendor & scenario catalog studio (/api/catalog)
│       └── audit.py           # Audit run, tasks, SSE stream & normalized JSON (/api/audit)
├── services/                  # Business Logic & Application Services
│   ├── state_service.py       # Global Single Source of Truth state manager
│   └── preset_service.py      # Multi-tier enterprise topology preset generator
├── core/                      # Domain Models, Constants & Live Automation
│   ├── constants.py           # Enums: Roles, Functions, Severities, Statuses
│   ├── models.py              # Pydantic V2 core state & entity models
│   └── collector/             # Stage 3 Live Automation Engine
│       ├── audit_trigger_runner.py  # Automation orchestrator & async queue manager
│       ├── simulation_engine.py     # Deterministic multi-vendor CLI simulator
│       ├── validator.py             # Automated output inspection & pattern matcher
│       ├── log_writer.py            # Hierarchical disk logging & ZIP packaging
│       └── adapters/                # Network device connection adapters
├── engine/                    # Rule, Validation & Normalization Engines
│   ├── audit_normalizer.py    # Canonical Single Source of Truth Normalizer
│   ├── audit_orchestrator.py  # Full 3-stage audit pipeline orchestration
│   ├── topology_engine.py     # Section 2.4 link validation & multi-tier layout
│   ├── catalog_manager.py     # Catalog persistence & profile management
│   ├── protocol_catalog.py    # 60+ protocol checks with vendor CLI commands
│   ├── severity_engine.py     # Health score & risk evaluation algorithms
│   ├── l2_audit_module.py     # Layer 2 switching, VLAN, STP rules
│   ├── l3_audit_module.py     # Layer 3 routing (OSPF/BGP), gateway rules
│   ├── firewall_audit_module.py # Firewall, ACL, NAT, state-tracking rules
│   ├── wireless_audit_module.py # Wireless, SSID, WLC, 802.1X rules
│   ├── edge_wan_audit_module.py # Edge/WAN, IPsec, BFD, SD-WAN rules
│   └── connectivity_audit_module.py # Management plane, NTP, SNMP, Syslog, AAA
├── parsers/                   # Text & Configuration Parsers
│   ├── config_parser.py       # Configuration parser for Cisco, Juniper, Arista, Fortinet
│   ├── command_parser.py      # Operational CLI log parser
│   └── lifecycle_parser.py    # Hardware lifecycle & vulnerability checks
├── reporting/                 # Formal Deliverable Generators
│   ├── docx_generator.py      # Publication-grade Word (.docx) executive report generator
│   ├── excel_generator.py     # Multi-sheet Excel workbook generator & importer
│   └── executive_report.py    # 6-page formal executive management report generator
├── static/                    # Frontend Web Assets
│   ├── css/style.css          # Glassmorphic dark-mode styling & animations
│   └── js/                    # Modular Frontend JavaScript
│       ├── app.js             # Main coordinator & entrypoint
│       └── modules/           # Domain-focused client controllers
│           ├── state.js       # Global state, stage switcher & presets
│           ├── inventory.js   # Device inventory table & modal controls
│           ├── topology.js    # Canvas diagram, links, port-channels & tiering
│           ├── project.js     # Blank file setup, Excel export/import & saved files
│           ├── audit.js       # Device audit matrix, task status & evidence notes
│           ├── live_trigger.js # Live automated audit trigger & SSE progress listener
│           └── catalog.js     # Vendor & scenario catalog studio
├── templates/                 # Jinja2 HTML Templates
│   ├── index.html             # Master workbench layout orchestrator
│   ├── executive_report.html  # 6-page white-background executive report template
│   └── components/            # Modular Template Partials
├── tests/                     # Automated Test Suites (20 Passing Tests)
│   ├── test_audit_engine.py   # Full audit engine unit & integration tests
│   ├── test_executive_report.py # 1:1 data consistency & schema validation tests
│   ├── test_portchannel_api.py # Port-Channel & link validation API tests
│   ├── test_catalog_manager.py # Vendor & scenario catalog tests
│   ├── test_ui_catalog_sync.py # Dynamic catalog UI synchronization tests
│   ├── test_audit_priority_timezone.py # Priority & timezone ordering tests
│   └── test_stage3_trigger.py # Live audit automation & simulation tests
├── docs/                      # Comprehensive Technical Documentation
│   ├── README.md              # Documentation index and architecture overview
│   ├── ARCHITECTURE.md        # System Architecture & Layered Design
│   ├── WORKFLOW.md            # End-to-End Audit & Execution Workflows
│   ├── DEVELOPER_GUIDE.md     # Developer Setup, API Reference & Extensibility
│   ├── audit-methodology.md   # 4-stage audit lifecycle & scoring methodology
│   ├── supported-devices.md   # Multi-vendor matrix & platform definitions
│   ├── threat-model.md        # STRIDE security & risk analysis
│   ├── data-privacy.md        # Zero-telemetry & local data retention policy
│   └── authorized-use.md      # Authorization policy & legal disclaimers
├── requirements.txt           # Python dependency manifest
└── zenquix_BLRCC002_Audit_Evidence.xlsx # Default enterprise preset workbook
```

---

## 3. REST API Specification

### State & Enterprise Presets (`api/routers/state.py`)
| Method | Endpoint | Description | Request Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/state` | Retrieve current active `NetworkProjectState` | - |
| `GET` | `/api/presets/enterprise` | Reset workspace state to enterprise topology preset | - |

### Inventory & Device Management (`api/routers/devices.py`)
| Method | Endpoint | Description | Request Body |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/devices` | Add new device to inventory & recompute audit | `DeviceModel` JSON |
| `PUT` | `/api/devices/{device_id}` | Update device attributes, update links & re-audit | `DeviceModel` JSON |
| `DELETE` | `/api/devices/{device_id}` | Remove device, purge attached links & re-audit | - |
| `GET` | `/api/devices/{device_id}/config_logs` | Retrieve device raw configuration and CLI logs | - |
| `POST` | `/api/devices/{device_id}/config_logs` | Upload/update device raw config and CLI logs | `ConfigLogsRequest` JSON |

### Topology & Link Management (`api/routers/topology.py`)
| Method | Endpoint | Description | Request Body |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/topology/link` | Create 1-to-1 links or port-channel member links | `LinkRequest` JSON |
| `DELETE` | `/api/topology/link` | Delete bidirectional topology link | Query `link_id` |
| `PUT` | `/api/topology/portchannel/{po_id}` | Create / update Port-Channel bundle | `PortChannelEditRequest` JSON |
| `DELETE` | `/api/topology/portchannel/{po_id}` | Delete Port-Channel bundle and unbind links | - |
| `GET` | `/api/topology/validate` | Run real-time Section 2.4 link validation checks | - |

### Project Lifecycle & Workspace Files (`api/routers/projects.py`)
| Method | Endpoint | Description | Request Body |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/project/new` | Initialize blank audit project with conflict check | `NewProjectRequest` JSON |
| `GET` | `/api/project/saved-files` | List saved `.xlsx` files in workspace directory | - |
| `POST` | `/api/project/load-file` | Load and restore project from saved workbook | `LoadFileRequest` JSON |

### Device Audit, Tasks & Normalization (`api/routers/audit.py`)
| Method | Endpoint | Description | Request Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/audit/normalized` | **Retrieve canonical Normalized Audit JSON (SSOT)** | - |
| `POST` | `/api/audit/run` | Trigger full 3-Stage audit pipeline calculation | Query `target_device` (opt) |
| `GET` | `/api/audit/device/{hostname}/tasks` | Retrieve all audit tasks for a specific device | - |
| `POST` | `/api/audit/task/{task_id}/status` | Update task verification status & evidence notes | `TaskStatusUpdateRequest` JSON |
| `POST` | `/api/audit/tasks/batch_update` | Batch update tasks by hostname/protocol filter | `BatchTaskUpdateRequest` JSON |
| `GET` | `/api/audit/matrix_summary` | Get consolidated protocol compliance matrix | - |

### Live Automation & Telemetry (`api/routers/audit.py`)
| Method | Endpoint | Description | Request Body |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/audit/trigger` | Trigger live automated CLI execution across scope | `Stage3TriggerRequest` JSON |
| `GET` | `/api/audit/stream/{job_id}` | Server-Sent Events (SSE) progress & log stream | - |
| `POST` | `/api/audit/task/{task_id}/retry` | On-the-fly custom command re-test for failed task | `Stage3RetryTaskRequest` JSON |
| `GET` | `/api/audit/download_files/{target}` | Download ZIP archive of raw collected `.cfg` files | - |

### Deliverable Reports & Data Ingestion (`api/routers/reports.py`)
| Method | Endpoint | Description | Returns |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/export/executive/metrics` | Summary metrics derived from `AuditNormalizer` | JSON metrics |
| `GET` | `/api/export/executive/docx` | Download publication-grade 6-page executive report in Word | Binary `.docx` file |
| `GET` | `/api/export/executive/html` | Render publication-grade 6-page executive report | HTML Web Page (Print PDF ready) |
| `GET` | `/api/export/executive/md` | Generate executive report in Markdown format | Markdown `.md` text |
| `POST` | `/api/export/excel` | Export Excel evidence workbook with client state | Binary `.xlsx` file |
| `GET` | `/api/export/excel` | Export Excel evidence workbook with server state | Binary `.xlsx` file |
| `POST` | `/api/import/excel` | Ingest 3-sheet Excel workbook & update state | `NetworkProjectState` JSON |

### Catalog Studio Management (`api/routers/catalog.py`)
| Method | Endpoint | Description | Request Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/catalog/vendors` | Retrieve all vendor platform profiles | - |
| `POST` | `/api/catalog/vendors` | Add or update vendor platform profile | Vendor profile dict |
| `DELETE` | `/api/catalog/vendors/{name}` | Delete vendor platform profile | - |
| `GET` | `/api/catalog/scenarios` | Retrieve all modular test scenarios | - |
| `POST` | `/api/catalog/scenarios` | Add or update test scenario | Scenario dict |
| `DELETE` | `/api/catalog/scenarios/{id}` | Delete test scenario | - |
| `POST` | `/api/catalog/scenarios/import` | Bulk import scenarios from JSON file | UploadFile (`.json`) |
| `GET` | `/api/catalog/scenarios/export` | Export scenarios catalog as JSON | Downloadable `.json` |
| `POST` | `/api/catalog/vendors/import` | Bulk import vendor profiles from JSON file | UploadFile (`.json`) |
| `GET` | `/api/catalog/vendors/export` | Export vendor catalog as JSON | Downloadable `.json` |
| `POST` | `/api/catalog/reset` | Reset catalogs to factory presets | - |

---

## 4. How to Extend the Audit Engine

### 4.1 Adding a New Audit Rule
To add a new audit check to a domain module (e.g. `L3AuditModule`):
1. Open [`engine/l3_audit_module.py`](file:///d:/Zenquix/NW_audit_tool/engine/l3_audit_module.py).
2. Create a check method or add to `audit_device()`:
```python
# Example: BGP Max-Prefix Safeguard Rule
def _check_bgp_max_prefix(device: DeviceModel, raw_config: str) -> Optional[AuditCheckResult]:
    has_bgp = "router bgp" in raw_config.lower()
    if not has_bgp:
        return None
    
    has_max_prefix = "maximum-prefix" in raw_config.lower()
    return AuditCheckResult(
        id=f"CHK-BGP-MAXPFX-{device.hostname}",
        device=device.hostname,
        role=device.device_role.value,
        category="Layer 3 Routing",
        check="BGP Peer Maximum-Prefix Safeguard",
        expected="neighbor <ip> maximum-prefix configured to prevent route leaks",
        actual="Configured" if has_max_prefix else "Missing maximum-prefix statement",
        status=AuditStatus.PASSED if has_max_prefix else AuditStatus.WARNING,
        severity=SeverityLevel.MEDIUM,
        evidence="Found 'maximum-prefix' in BGP stanza" if has_max_prefix else "No prefix limits applied to BGP neighbors",
        recommendation="Apply 'neighbor <ip> maximum-prefix <limit>' on all eBGP peer sessions to safeguard routing memory."
    )
```

---

### 4.2 Adding a New Protocol Check to the Protocol Catalog
1. Open [`engine/protocol_catalog.py`](file:///d:/Zenquix/NW_audit_tool/engine/protocol_catalog.py).
2. Add a new entry to `PROTOCOL_REGISTRY` under the target category:
```python
{
    "protocol": "BFD",
    "category": "High Availability",
    "title": "Bidirectional Forwarding Detection (BFD) Health Probing",
    "description": "Verify BFD sub-second link failure detection is enabled on critical routing peers.",
    "roles": [DeviceRole.CORE, DeviceRole.EDGE_WAN, DeviceRole.DISTRIBUTION],
    "vendor_commands": {
        "cisco": "show bfd neighbors detail",
        "juniper": "show bfd session extensive",
        "arista": "show bfd peers"
    },
    "severity": SeverityLevel.HIGH,
    "condition": "When dynamic routing is enabled across physical links"
}
```

---

### 4.3 Customizing Category Normalization Rules
Category mapping is governed centrally by `AuditNormalizer._map_category()` in [`engine/audit_normalizer.py`](file:///d:/Zenquix/NW_audit_tool/engine/audit_normalizer.py). It normalizes checks into the 5 canonical categories:
- `Security`
- `Availability`
- `Configuration`
- `Network Services`
- `Performance`

When adding new checks, ensure specific configuration terms (e.g. `subnet`, `addressing`, `vlan`) take precedence over generic `interfaces` keywords to prevent misclassification.

---

## 5. Testing & Quality Assurance

Run the automated test suite using Python's standard unittest runner:

```bash
# Run all 22 automated tests
python -m unittest discover tests

# Or run specific test modules:
python -m unittest tests/test_executive_report.py
python -m unittest tests/test_audit_engine.py
python -m unittest tests/test_portchannel_api.py
python -m unittest tests/test_catalog_manager.py
python -m unittest tests/test_ui_catalog_sync.py
python -m unittest tests/test_audit_priority_timezone.py
python -m unittest tests/test_stage3_trigger.py
```

### Verified Test Suites:
- `test_executive_report.py`: Validates 1:1 mathematical data consistency (e.g. 27 executed checks with 1 warning yield exactly 96.3% compliance, 1 finding, and 1 recommendation), Normalized Audit JSON schema, and zero findings when all checks pass.
- `test_audit_engine.py`: Full 3-stage pipeline calculation, risk metrics, and deliverable export.
- `test_portchannel_api.py`: 1-to-1 links, port-channel bundling, validation rules, and backward-compatible app exports.
- `test_catalog_manager.py`: Vendor catalog and test scenario CRUD, persistence, and factory reset.
- `test_ui_catalog_sync.py`: Dynamic vendor synchronization across UI modals and scenarios.
- `test_audit_priority_timezone.py`: Priority 1 baseline checks and client timezone timestamping.
- `test_stage3_trigger.py`: Multi-scope execution runner, simulation engine, SSH credential handling, on-the-fly retry, and `.cfg` log packaging.

---

## 6. Coding Standards & Best Practices
1. **Strong Typing**: Use Pydantic V2 models (`core/models.py`, `api/schemas.py`) and Python type annotations for all data contracts.
2. **Single Source of Truth**: All reporting and API consumers must consume `AuditNormalizer.normalize_audit(state)` rather than implementing independent classification heuristics.
3. **Strict Hierarchy**: Never fabricate findings when checks pass; findings exist only when `check.status != PASS`.
4. **Deterministic Outputs**: Ensure sorting and ordering of devices, links, and checks remain predictable across Excel and report generation.
5. **Actionable Error Responses**: Always return clean `HTTPException` exceptions with detailed descriptions for duplicate names, missing links, or invalid parameters.
