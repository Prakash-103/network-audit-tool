"""
Multi-Vendor Configuration Parser for L2/L3 Switches, Routers, Firewalls, and Wireless APs.
Supports Cisco IOS/NX-OS, Arista EOS, Juniper JunOS, Fortinet FortiOS, Palo Alto PAN-OS, ArubaOS.
"""
import re
from typing import Dict, Any, List

class MultiVendorConfigParser:
    @staticmethod
    def detect_vendor_and_os(content: str) -> tuple[str, str]:
        content_lower = content.lower()
        if "arista" in content_lower or "eos" in content_lower:
            return "Arista", "EOS"
        elif "juniper" in content_lower or "junos" in content_lower:
            return "Juniper", "JunOS"
        elif "palo alto" in content_lower or "pan-os" in content_lower or "panos" in content_lower:
            return "Palo Alto", "PAN-OS"
        elif "fortinet" in content_lower or "fortigate" in content_lower or "fortios" in content_lower:
            return "Fortinet", "FortiOS"
        elif "aruba" in content_lower or "arubaos" in content_lower:
            return "Aruba", "ArubaOS"
        elif "nx-os" in content_lower or "nexus" in content_lower:
            return "Cisco", "NX-OS"
        elif "cisco" in content_lower or "ios-xe" in content_lower or "version 1" in content_lower or "version 15" in content_lower or "version 16" in content_lower or "hostname" in content_lower:
            return "Cisco", "IOS-XE"
        return "Unknown", "Unknown"

    @staticmethod
    def parse_config(content: str, filename: str = "config.txt") -> Dict[str, Any]:
        vendor, os_type = MultiVendorConfigParser.detect_vendor_and_os(content)
        
        hostname = "UNKNOWN_HOST"
        hostname_match = re.search(r'^\s*hostname\s+["\']?([^\s"\']+)["\']?', content, re.MULTILINE | re.IGNORECASE)
        if not hostname_match:
            hostname_match = re.search(r'^\s*set system host-name\s+([^\s]+)', content, re.MULTILINE)
        if not hostname_match:
            hostname_match = re.search(r'^\s*sysname\s+([^\s]+)', content, re.MULTILINE)
        if hostname_match:
            hostname = hostname_match.group(1).strip()
        else:
            clean_name = filename.split('.')[0].replace('_config', '').replace('-config', '')
            if clean_name and clean_name.lower() != "config":
                hostname = clean_name.upper()

        parsed_data = {
            "hostname": hostname,
            "vendor": vendor,
            "os_type": os_type,
            "interfaces": [],
            "vlans": [],
            "port_channels": {},
            "stp": {
                "mode": "Unknown",
                "root_bridge": False,
                "portfast_enabled": False,
                "bpdu_guard_enabled": False,
                "root_guard_enabled": False,
                "loop_guard_enabled": False
            },
            "routing": {
                "default_gateway": None,
                "static_routes": [],
                "ospf": {"enabled": False, "process_id": None, "router_id": None, "areas": [], "passive_interfaces": []},
                "bgp": {"enabled": False, "as_number": None, "neighbors": [], "filtered_neighbors": []},
                "eigrp": {"enabled": False, "as_number": None}
            },
            "ha": {
                "hsrp": [],
                "vrrp": [],
                "vpc": {"enabled": False, "domain": None},
                "ha_sync_status": "Synced"
            },
            "wireless": {
                "ssids": [],
                "controller_ip": None,
                "radios_2ghz_active": False,
                "radios_5ghz_active": False,
                "channel_width": "20MHz",
                "wpa3_enabled": False
            },
            "firewall": {
                "zones": [],
                "policies": [],
                "nat_rules": [],
                "acls": [],
                "ha_peer": None
            },
            "security": {
                "aaa_enabled": False,
                "tacacs_radius": False,
                "ssh_enabled": False,
                "telnet_enabled": False,
                "snmp_v2c": False,
                "snmp_v3": False,
                "ntp_servers": [],
                "logging_servers": [],
                "secret_encrypted": False,
                "acls_configured": False
            },
            "raw_text": content
        }

        # Parse Interfaces
        intf_blocks = re.findall(r'(?:interface|set interfaces)\s+([^\n\r]+)([\s\S]*?)(?=(?:interface|set interfaces|\Z|line|router|vlan))', content, re.IGNORECASE)
        for name, block in intf_blocks:
            intf_name = name.strip()
            ip_match = re.search(r'ip address\s+([0-9.]+)\s+([0-9.]+)', block, re.IGNORECASE)
            ip_addr = ip_match.group(1) if ip_match else None
            mask = ip_match.group(2) if ip_match else None
            
            is_trunk = "mode trunk" in block.lower() or "portmode trunk" in block.lower()
            is_access = "mode access" in block.lower()
            
            native_vlan = 1
            native_match = re.search(r'switchport trunk native vlan\s+(\d+)', block, re.IGNORECASE)
            if native_match:
                native_vlan = int(native_match.group(1))

            allowed_match = re.search(r'switchport trunk allowed vlan\s+([0-9,-]+|all)', block, re.IGNORECASE)
            allowed_vlans = allowed_match.group(1) if allowed_match else "all"

            portfast = "spanning-tree portfast" in block.lower() or "port-type edge" in block.lower()
            bpduguard = "bpduguard enable" in block.lower() or "bpdu-guard enable" in block.lower()

            # Port channel membership
            po_match = re.search(r'channel-group\s+(\d+)', block, re.IGNORECASE)
            po_id = f"Po{po_match.group(1)}" if po_match else None
            if po_id:
                if po_id not in parsed_data["port_channels"]:
                    parsed_data["port_channels"][po_id] = []
                parsed_data["port_channels"][po_id].append(intf_name)

            parsed_data["interfaces"].append({
                "name": intf_name,
                "ip": ip_addr,
                "mask": mask,
                "is_trunk": is_trunk,
                "is_access": is_access,
                "native_vlan": native_vlan,
                "allowed_vlans": allowed_vlans,
                "portfast": portfast,
                "bpduguard": bpduguard,
                "port_channel": po_id,
                "shutdown": "shutdown" in block.lower() and "no shutdown" not in block.lower()
            })

        # Parse VLANs
        vlan_ids = set(re.findall(r'vlan\s+(\d+)', content, re.IGNORECASE))
        parsed_data["vlans"] = sorted([int(v) for v in vlan_ids if int(v) <= 4094])

        # Parse STP
        if "spanning-tree mode rapid-pvst" in content.lower():
            parsed_data["stp"]["mode"] = "Rapid-PVST+"
        elif "spanning-tree mode mst" in content.lower():
            parsed_data["stp"]["mode"] = "MST"
        elif "spanning-tree mode pvst" in content.lower():
            parsed_data["stp"]["mode"] = "PVST+"
        elif "spanning-tree" in content.lower():
            parsed_data["stp"]["mode"] = "STP-Enabled"
        
        parsed_data["stp"]["portfast_enabled"] = "spanning-tree portfast default" in content.lower() or any(i["portfast"] for i in parsed_data["interfaces"])
        parsed_data["stp"]["bpdu_guard_enabled"] = "spanning-tree portfast bpduguard default" in content.lower() or any(i["bpduguard"] for i in parsed_data["interfaces"])
        parsed_data["stp"]["root_bridge"] = "spanning-tree vlan" in content.lower() and "priority 0" in content.lower() or "root primary" in content.lower()

        # Parse Default Gateway
        gw_match = re.search(r'ip default-gateway\s+([0-9.]+)', content, re.IGNORECASE)
        if gw_match:
            parsed_data["routing"]["default_gateway"] = gw_match.group(1)

        # Parse OSPF
        if "router ospf" in content.lower():
            parsed_data["routing"]["ospf"]["enabled"] = True
            ospf_match = re.search(r'router ospf\s+(\d+)', content, re.IGNORECASE)
            if ospf_match:
                parsed_data["routing"]["ospf"]["process_id"] = ospf_match.group(1)
            areas = set(re.findall(r'area\s+(\d+|\d+\.\d+\.\d+\.\d+)', content, re.IGNORECASE))
            parsed_data["routing"]["ospf"]["areas"] = list(areas)
            passives = re.findall(r'passive-interface\s+([^\n\r]+)', content, re.IGNORECASE)
            parsed_data["routing"]["ospf"]["passive_interfaces"] = [p.strip() for p in passives]

        # Parse BGP
        if "router bgp" in content.lower():
            parsed_data["routing"]["bgp"]["enabled"] = True
            bgp_match = re.search(r'router bgp\s+(\d+)', content, re.IGNORECASE)
            if bgp_match:
                parsed_data["routing"]["bgp"]["as_number"] = bgp_match.group(1)
            neighbors = re.findall(r'neighbor\s+([0-9.]+)\s+remote-as\s+(\d+)', content, re.IGNORECASE)
            parsed_data["routing"]["bgp"]["neighbors"] = [{"ip": n[0], "as": n[1]} for n in neighbors]
            # Check route-maps/prefix-lists on neighbors
            filtered = re.findall(r'neighbor\s+([0-9.]+)\s+(?:route-map|prefix-list)', content, re.IGNORECASE)
            parsed_data["routing"]["bgp"]["filtered_neighbors"] = list(set(filtered))

        # Parse HA
        if "standby " in content.lower():
            parsed_data["ha"]["hsrp"].append("HSRP Configured")
        if "vrrp " in content.lower():
            parsed_data["ha"]["vrrp"].append("VRRP Configured")
        if "vpc domain" in content.lower():
            parsed_data["ha"]["vpc"]["enabled"] = True

        # Parse Wireless (SSIDs, Controller, WPA3)
        ssids = re.findall(r'ssid\s+["\']?([^"\n\r]+)["\']?', content, re.IGNORECASE)
        parsed_data["wireless"]["ssids"] = list(set(ssids))
        wlc_match = re.search(r'(?:controller|wlc|capwap)\s+(?:ip\s+)?([0-9.]+)', content, re.IGNORECASE)
        if wlc_match:
            parsed_data["wireless"]["controller_ip"] = wlc_match.group(1)
        if "dot11 24ghz" in content.lower() or "radio 2.4" in content.lower() or "wlan" in content.lower():
            parsed_data["wireless"]["radios_2ghz_active"] = True
        if "dot11 5ghz" in content.lower() or "radio 5" in content.lower() or "wlan" in content.lower():
            parsed_data["wireless"]["radios_5ghz_active"] = True
        if "wpa3" in content.lower() or "sae" in content.lower():
            parsed_data["wireless"]["wpa3_enabled"] = True

        # Parse Firewall (Zones, Policies, NAT)
        zones = re.findall(r'zone\s+([^\s\n\r]+)', content, re.IGNORECASE)
        parsed_data["firewall"]["zones"] = list(set(zones))
        policies = re.findall(r'(?:security-policy|firewall policy|access-list [^\n]+ permit)', content, re.IGNORECASE)
        parsed_data["firewall"]["policies"] = policies
        if "nat " in content.lower() or "ip nat " in content.lower():
            parsed_data["firewall"]["nat_rules"].append("NAT Configured")

        # Parse Security Settings
        if "aaa new-model" in content.lower() or "aaa group server" in content.lower():
            parsed_data["security"]["aaa_enabled"] = True
        if "tacacs" in content.lower() or "radius" in content.lower():
            parsed_data["security"]["tacacs_radius"] = True
        if "transport input ssh" in content.lower() or "ip ssh version 2" in content.lower():
            parsed_data["security"]["ssh_enabled"] = True
        if "transport input telnet" in content.lower() or "transport input all" in content.lower():
            parsed_data["security"]["telnet_enabled"] = True
        if "snmp-server community" in content.lower():
            parsed_data["security"]["snmp_v2c"] = True
        if "snmp-server user" in content.lower() or "snmp-server group" in content.lower():
            parsed_data["security"]["snmp_v3"] = True

        ntps = re.findall(r'ntp server\s+([^\s\n\r]+)', content, re.IGNORECASE)
        parsed_data["security"]["ntp_servers"] = ntps

        loggings = re.findall(r'logging (?:host\s+)?([^\s\n\r]+)', content, re.IGNORECASE)
        parsed_data["security"]["logging_servers"] = [l for l in loggings if l.lower() not in ["buffered", "console", "monitor", "on"]]

        if "service password-encryption" in content.lower() or "enable secret" in content.lower():
            parsed_data["security"]["secret_encrypted"] = True

        return parsed_data
