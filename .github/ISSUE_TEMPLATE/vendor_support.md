---
name: Vendor / Hardware Platform Support
about: Request support or CLI verification commands for a network hardware vendor
title: '[VENDOR] Support for '
labels: vendor-support
assignees: ''
---

**Vendor Identification**
- Vendor Name: [e.g. Brocade, Extreme, Allied Telesis, SonicWall]
- Operating System & Versions: [e.g. Fabric OS 9.x, ExtremeXOS 31.x]
- Primary Device Types: [e.g. Access Switch, Core Chassis, Security Gateway]

**Interface Naming & Port Prefixes**
- Standard Interface Naming Format: [e.g. `1/1/`, `ge-0/0/`, `10GE1/0/`, `ether1`]
- Supported Port Speeds: [e.g. `1G, 10G, 25G, 40G, 100G`]

**Key CLI Verification Commands (`show` commands)**
Please provide operational inspection commands for:
- Device Health / Version: [e.g. `display version; display environment`]
- Interface Operational Status: [e.g. `display interface brief`]
- VLAN & Switching: [e.g. `display vlan`]
- Spanning Tree: [e.g. `display stp brief`]
- Routing (OSPF/BGP): [e.g. `display ospf peer brief`]

**Netmiko Device Type (if known)**
- Netmiko driver name: [e.g. `extreme_exos`, `brocade_fastiron`, `generic_termserver`]

**Sample CLI Output (Sanitized)**
Provide sample outputs for testing parsers. Ensure all passwords, real IP addresses, and customer names are removed.
