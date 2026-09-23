# Network Infrastructure Audit Methodology

This document outlines the systematic, four-stage audit methodology employed by the **Enterprise Network Infrastructure Audit Platform**.

---

## The Four-Stage Audit Lifecycle

```text
  ┌────────────────────────────────────────────────────────┐
  │  Stage 1: Multi-Vendor Inventory & Platform Profiling  │
  │  Device Discovery, Roles, Hardware Models, OS Versions │
  └──────────────────────────┬─────────────────────────────┘
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │  Stage 2: Protocol Catalog & Topology Evaluation      │
  │  Layer 2 Switching, L3 Routing, STP, Port-Channels     │
  └──────────────────────────┬─────────────────────────────┘
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │  Stage 3: Zero-Storage Ephemeral CLI Verification      │
  │  Live Multi-Vendor 'show' Execution via Netmiko SSH   │
  └──────────────────────────┬─────────────────────────────┘
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │  Stage 4: Normalized Audit & Publication Deliverables  │
  │  Single Source of Truth, 6-Page PDF & Excel Evidence   │
  └────────────────────────────────────────────────────────┘
```

---

## Stage Breakdown

### Stage 1: Multi-Vendor Inventory & Platform Profiling
- **Device Discovery & Classification**: Ingests network devices with attributes: Device ID, Hostname, Management IP Address, Hardware Vendor, Model, Operating System Version, Serial Number, Physical Port Count, and Port Speed.
- **Role & Function Categorization**: Classifies devices by Network Role (`Core`, `Distribution`, `Access`, `Spine`, `Leaf`, `Firewall`, `Edge`, `Wireless AP`) and Functional Layer (`L2`, `L3`, `L2/L3`, `Firewall`, `Edge/WAN`).
- **Port Interface Prefix Resolution**: Dynamically maps vendor-appropriate interface naming (`GigabitEthernet1/0/`, `Ethernet`, `ge-0/0/`, `port`, `1/1/`, `10GE1/0/`).

### Stage 2: Protocol Catalog & Topology Evaluation
- **Modular Test Scenario Matching**: Applies the code-independent protocol catalog (`config/test_scenarios.json`) based strictly on device roles.
- **Audit Domain Checklists**:
  1. **Device Health & Baseline**: Hardware power supplies, fan status, CPU/RAM utilization, NTP synchronization, syslog logging, AAA authentication.
  2. **Interface & Physical Layer**: Admin/oper status, MTU consistency, CRC/FCS error rate, duplex and speed negotiation.
  3. **Layer 2 Switching**: VLAN ID consistency, trunk pruning, Native VLAN security, 802.1D/802.1w/802.1s Spanning Tree Root Bridge placement.
  4. **Layer 3 Routing**: OSPF Area 0 backbone integrity, neighbor adjacencies, dead/hello timers, BGP AS peering, Route Reflector validation.
  5. **Gateway Redundancy (FHRP)**: HSRP / VRRP priority alignment with STP Root Bridge to prevent asymmetric routing.
  6. **Security & Firewalls**: Zone traversal, interface ACLs, drop counters, HA synchronization.
  7. **Wireless Infrastructure**: Controller associations, AP RF channel assignments, 5GHz/2.4GHz band utilization.

### Stage 3: Zero-Storage Ephemeral CLI Verification
- **Targeted Command Resolution**: Dynamically resolves the vendor-specific CLI verification command for each test scenario and target vendor.
- **Ephemeral RAM Execution**: Operator provides credentials (username, password, enable secret) at execution time. Credentials reside strictly in temporary RAM and are scrubbed immediately upon job completion.
- **Controlled Concurrency**: Multi-threaded execution pool (`MAX_CONCURRENT_SSH_WORKERS = 5`) prevents CPU spikes on target network devices.
- **Real-Time Streaming**: Live execution logs and status transitions (`Completed`, `Failed`, `Warning`) stream to the operator interface via Server-Sent Events (SSE).

### Stage 4: Normalized Audit & Publication Deliverables
Stage 4 bridges operational CLI execution with executive governance through the **Normalized Audit Engine (`AuditNormalizer`)**:
- **Single Source of Truth (SSOT)**: Ingests all executed checks and generates canonical `NormalizedAudit` records, guaranteeing **100% mathematical consistency** across all views.
- **Strict Data Hierarchy**:
  - **Audit Checks**: Every evaluated test case across devices (e.g., 27 checks).
  - **Audit Findings**: Identified **only** when a check status is `FAIL` or `WARNING` (e.g., 1 finding). When all checks pass, findings count is strictly 0.
  - **Recommendations**: Remediation action items derived directly and exclusively from verified findings.
- **Five Canonical Audit Categories**:
  1. **Security**: Identity management, SSHv2, SNMPv3, management ACLs, firewall traversal.
  2. **Availability**: Spanning tree root placement, LACP link redundancy, FHRP failover, BFD health probing.
  3. **Configuration**: VLAN database, IP addressing, subnet masking, hostname consistency.
  4. **Network Services**: NTP clock synchronization, remote syslog redundancy, DNS, DHCP snooping.
  5. **Performance**: Interface MTU alignment, duplex speed negotiation, CRC error counters, hardware health.
- **True Mathematical Compliance Formula**:
  $$\text{Category Compliance \%} = \left( \frac{\text{Passed Checks}}{\text{Total Executed Checks}} \right) \times 100$$
- **Dual Publication Deliverables**:
  1. **Deliverable 1: 6-Page Formal Executive Management Report**:
     - *Page 1*: Executive Summary, 5 KPI cards, overall status badge, and prioritized action plan.
     - *Page 2*: Infrastructure scope, site breakdown, and Table 03 domain compliance table.
     - *Page 3*: Detailed finding cards with Check ID, command, observation, business impact, and remediation.
     - *Page 4*: Evidence-backed security posture controls and live protocol redundancy statuses.
     - *Page 5*: Fleet health distribution and approved OS baseline alignment.
     - *Page 6*: Prioritized recommendations roadmap and **Audit Evidence Traceability Sample** table.
  2. **Deliverable 2: Multi-Tab Excel Evidence Workbook (`.xlsx`)**:
     - *Device Inventory Tab*: Hardware models, serials, management IPs, and lifecycle statuses.
     - *Link Connections Tab*: Inter-switch physical links, speeds, and Port-Channel memberships.
     - *Audit Status & Evidence Tab*: Complete test execution records, CLI commands, Pass/Fail statuses, and sanitized evidence outputs.

---

## Finding Severity & Classification Standards

| Severity | Definition | Remediation Window |
| :--- | :--- | :--- |
| **Critical** | Major outage risk, complete loss of redundancy, unauthenticated boundary access, or routing blackhole. | Immediate (0–24 hours) |
| **High** | Sub-optimal redundancy, active STP loops, misaligned FHRP/STP roots, or high interface CRC errors. | Urgent (1–3 business days) |
| **Medium** | Missing port descriptions, unsynchronized NTP clock, VLAN naming deviations, or degraded Port-Channel link. | Standard Maintenance (1–2 weeks) |
| **Low** | Cosmetic discrepancies, minor logging verbosity variations, or non-impacting configuration drift. | Next scheduled audit cycle |

### Status Classifications
- **PASS**: Verification check satisfied; configuration complies with golden enterprise standards.
- **FAIL**: Discrepancy or violation identified; formal finding and remediation recommendation logged.
- **WARNING**: Incomplete or sub-optimal configuration; potential risk under failure conditions.
- **NOT APPLICABLE**: Scenario excluded based on device role (e.g. Wireless AP checks on a Core router).

---

## Evidence Traceability Standard

Every audit finding must maintain unbroken provenance back to operational CLI evidence:

| Finding Attribute | Purpose & Source |
| :--- | :--- |
| **Device Hostname** | Identifies the physical/virtual asset inspected. |
| **Category** | Canonical audit classification (`Security`, `Availability`, `Configuration`, `Network Services`, `Performance`). |
| **Check ID** | Unique test identifier (e.g. `TASK-05-LACP`). |
| **Verification Command** | Exact multi-vendor CLI inspection command executed (e.g. `show etherchannel summary`). |
| **Verified Observation** | Factual output extracted from target device (e.g. `Po1 operational; Po2 member Gi1/0/2 suspended`). |
| **Potential Impact** | Technical and operational risk under degraded or failure conditions. |
| **Remediation Directive** | Actionable engineering command or procedure required to achieve compliance. |
