# Multi-Vendor Platform Support Matrix

The **Enterprise Network Infrastructure Audit Platform** supports code-independent platform definitions, port naming prefix rules, and CLI verification command mappings for major networking vendors.

---

## Vendor Support Matrix

| Vendor | Primary Operating Systems | Port Interface Prefix | Supported Hardware Models / Platforms | Verification Driver |
| :--- | :--- | :--- | :--- | :--- |
| **Cisco Systems** | IOS-XE (17.x), IOS (15.x), NX-OS (9.x) | `GigabitEthernet1/0/` | Catalyst 9300, 9500, 9200, 9600, Nexus 9000, 7000, 5000, ISR 4451-X, ISR 4331, ASR 1001-X, Catalyst 9800 WLC | `cisco_ios`, `cisco_xe`, `cisco_nxos` |
| **Arista Networks** | EOS (4.2x–4.3x) | `Ethernet` | DCS-7050SX3, DCS-7280R3, DCS-7060CX, DCS-7150S, DCS-7010T | `arista_eos` |
| **Juniper Networks** | Junos (21.x–23.x) | `ge-0/0/`, `xe-0/0/` | QFX5100, QFX5200, EX4300, EX3400, MX204, MX480, SRX345, SRX1500 | `juniper_junos` |
| **Palo Alto Networks** | PAN-OS (10.x–11.x) | `Port` | PA-440, PA-850, PA-3220, PA-5220, PA-5450, PA-VM | `paloalto_panos` |
| **Fortinet** | FortiOS (7.x) | `port` | FortiGate-60F, 100F, 200F, 600E, 1000D, FortiGate-VM | `fortinet` |
| **Aruba / HPE** | AOS-CX (10.x), ProCurve | `1/1/` | CX 6300, CX 6400, CX 8320, CX 8325, CX 8400, CX 10000, Aruba 2930F, Aruba 3810M, 7210 Controller, AP-535 | `aruba_osswitch`, `hp_comware` |
| **Huawei Enterprise** | VRP (V200R019+) | `10GE1/0/` | CloudEngine 6800, S5735, S6730, CloudEngine 12800, NetEngine AR6000 | `huawei` |
| **MikroTik** | RouterOS (v6, v7) | `ether` | Cloud Router Switch (CRS326, CRS328, CRS354), Cloud Core Router (CCR1036, CCR2004, CCR2116) | `mikrotik_routeros` |
| **Dell Technologies** | OS10 (10.5+) | `ethernet1/1/` | PowerSwitch S4148F-ON, S5248F-ON, S5224F-ON, Z9264F-ON | `dell_os10` |
| **Check Point** | Gaia (R81.x) | `eth` | Quantum 3600, Quantum 6600, Quantum 16000, Quantum Maestro, CloudGuard | `checkpoint_gaia` |

---

## Adding Custom Hardware Platforms & Port Rules

You do **not** need to modify application source code to add new hardware models or vendors:
1. Navigate to **⚙️ Modular Test Scenario & Vendor Platform Studio** in the application interface.
2. Select the **🏢 Vendor & Platform Profiles** tab.
3. Click **➕ Add Vendor Profile**.
4. Configure:
   - **Vendor Short Name**: Identifier used in test scenario mappings (e.g. `Extreme`, `Brocade`).
   - **Display Name**: Human-readable label (e.g. `Extreme Networks Enterprise`).
   - **Default OS**: Recommended baseline operating system version.
   - **Port Interface Prefix**: Prefix used when auto-generating device ports (e.g. `1:` or `slot1/`).
   - **Supported Platforms / Hardware Models**: Comma-separated list of hardware models.
   - **Supported Port Speeds**: Comma-separated list of interface speeds (`1G, 10G, 25G, 40G, 100G`).
5. Save the profile. The new vendor and its hardware models/port speeds will immediately be available in the **Add Network Device** modal and in all testcase CLI command fields.
