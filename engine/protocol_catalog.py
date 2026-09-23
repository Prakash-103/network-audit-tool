"""
Protocol Catalog & Device-Type Test Matrix Engine.
Implements device-type driven audit test suites, multi-vendor CLI verification commands,
and dynamic protocol detection per HLD/LLD & configuration rules.
"""
from typing import List, Dict, Any, Optional
from core.models import DeviceModel, DeviceAuditTask, TopologyLink
from core.constants import DeviceFunction, DeviceRole, TaskVerificationStatus, SeverityLevel, AuditProtocol
from engine.catalog_manager import CatalogManager

class ProtocolCatalogEngine:
    """
    Generates device-type specific audit checklists and verification commands.
    Supports dynamic test scenario feeding and multi-vendor CLI catalogs.
    """

    @staticmethod
    def get_cli_command(vendor: str, protocol: str, test_key: str, device: DeviceModel) -> str:
        """
        Return the vendor-specific verification CLI command for a given protocol and test.
        First attempts lookup in modular CatalogManager, then uses internal fallback matrix.
        """
        # 0. Check modular CatalogManager first
        modular_cmd = CatalogManager.get_vendor_cli_command(test_key, vendor)
        if modular_cmd and modular_cmd != "show running-config":
            return modular_cmd

        # Check by protocol name in modular catalog
        proto_str = protocol.value if hasattr(protocol, 'value') else str(protocol)
        for s in CatalogManager.get_scenarios():
            if s.get("protocol", "").lower() == proto_str.lower() or s.get("id", "").lower() == test_key.lower():
                cmd = CatalogManager.get_vendor_cli_command(s.get("id", ""), vendor)
                if cmd and cmd != "show running-config":
                    return cmd

        v = (vendor or "Cisco").lower()

        # 0. Native Running Configuration Backup (Priority 1)
        if protocol == AuditProtocol.RUNNING_CONFIG or test_key == "Running_Config_Backup":
            if "juniper" in v:
                return "show configuration"
            elif "palo" in v:
                return "show config running"
            elif "fortinet" in v:
                return "show full-configuration"
            elif "arista" in v:
                return "show running-config"
            elif "gwn" in v or "grandstream" in v:
                m = (device.device_model or "").lower()
                if "ap" in m or "76" in m:
                    return "cat /etc/config/wireless; show running-config"
                return "show running-config"
            elif "sophos" in v:
                return "system diagnostics show version"
            elif "aruba" in v:
                return "show running-config"
            return "show running-config"

        # 1. Device Health & Baseline
        if protocol == AuditProtocol.BASIC_HEALTH:
            if "palo" in v:
                return "show system info; show system resources; show ntp; show admins"
            elif "arista" in v:
                return "show version; show environment all; show ntp status; show processes top"
            elif "juniper" in v:
                return "show version; show chassis environment; show ntp associations"
            elif "fortinet" in v:
                return "get system status; get system performance status; get system ntp"
            elif "aruba" in v:
                return "show system; show version; show environment; show ap database"
            return "show version; show environment all; show processes cpu; show ntp status; show logging"

        # 2. Interfaces
        elif protocol == AuditProtocol.INTERFACES:
            if "palo" in v:
                return "show interface all; show interface counters"
            elif "arista" in v:
                return "show interfaces status; show interfaces counters errors"
            elif "juniper" in v:
                return "show interfaces terse; show interfaces extensive"
            elif "fortinet" in v:
                return "get hardware nic; diagnose hardware deviceinfo nic"
            elif "aruba" in v:
                return "show interface brief; show ap status"
            return "show interfaces status; show interfaces counters errors; show interfaces description"

        # 3. CDP
        elif protocol == AuditProtocol.CDP:
            if "arista" in v:
                return "show cdp neighbors detail"
            elif "juniper" in v:
                return "show cdp neighbor"
            return "show cdp neighbors detail"

        # 4. LLDP
        elif protocol == AuditProtocol.LLDP:
            if "arista" in v:
                return "show lldp neighbors detail"
            elif "juniper" in v:
                return "show lldp neighbors"
            elif "palo" in v:
                return "show lldp neighbors"
            return "show lldp neighbors detail"

        # 5. VLAN
        elif protocol == AuditProtocol.VLAN:
            if "arista" in v:
                return "show vlan; show vlan summary"
            elif "juniper" in v:
                return "show vlans extensive"
            return "show vlan brief; show vlan summary"

        # 6. Access Port
        elif protocol == AuditProtocol.ACCESS_PORT:
            if "arista" in v:
                return "show interfaces switchport | grep -E 'Access|Mode'"
            return "show interfaces status | include access; show spanning-tree summary"

        # 7. Trunk
        elif protocol == AuditProtocol.TRUNK:
            if "arista" in v:
                return "show interfaces trunk"
            elif "juniper" in v:
                return "show ethernet-switching interfaces"
            return "show interfaces trunk"

        # 8. STP
        elif protocol == AuditProtocol.STP:
            if "arista" in v:
                return "show spanning-tree; show spanning-tree root"
            elif "juniper" in v:
                return "show spanning-tree bridge; show spanning-tree interface"
            return "show spanning-tree summary; show spanning-tree detail | include is the root"

        # 9. EtherChannel / LACP
        elif protocol == AuditProtocol.ETHERCHANNEL:
            if "arista" in v:
                return "show port-channel summary; show lacp neighbor"
            elif "juniper" in v:
                return "show lacp interfaces"
            return "show etherchannel summary; show lacp neighbor"

        # 10. Port Security & Layer 2 Security
        elif protocol in [AuditProtocol.PORT_SECURITY, AuditProtocol.DHCP_SNOOPING, AuditProtocol.DAI, AuditProtocol.IP_SOURCE_GUARD]:
            if "arista" in v:
                return "show mac security; show dhcp snooping binding"
            return "show port-security; show ip dhcp snooping binding; show ip arp inspection vlan"

        # 11. SVI & Routed Interfaces
        elif protocol == AuditProtocol.SVI:
            if "arista" in v:
                return "show ip interface brief | include Vlan"
            return "show ip interface brief | include Vlan; show ip route connected"

        # 12. Static Routing
        elif protocol == AuditProtocol.STATIC_ROUTING:
            if "arista" in v:
                return "show ip route static"
            elif "juniper" in v:
                return "show route protocol static"
            elif "palo" in v:
                return "show routing route type static"
            return "show ip route static; show ip route summary"

        # 13. OSPF
        elif protocol == AuditProtocol.OSPF:
            if "arista" in v:
                return "show ip ospf neighbor; show ip ospf interface brief; show ip route ospf"
            elif "juniper" in v:
                return "show ospf neighbor; show ospf interface; show route protocol ospf"
            elif "palo" in v:
                return "show routing protocol ospf neighbor; show routing protocol ospf area"
            return "show ip ospf neighbor; show ip ospf interface brief; show ip route ospf"

        # 14. BGP
        elif protocol == AuditProtocol.BGP:
            if "arista" in v:
                return "show ip bgp summary; show ip bgp neighbors; show ip route bgp"
            elif "juniper" in v:
                return "show bgp summary; show bgp neighbor"
            elif "palo" in v:
                return "show routing protocol bgp summary; show routing protocol bgp peer"
            return "show ip bgp summary; show ip bgp neighbors; show ip route bgp"

        # 15. EIGRP
        elif protocol == AuditProtocol.EIGRP:
            return "show ip eigrp neighbors; show ip eigrp interfaces; show ip route eigrp"

        # 16. HSRP / VRRP (FHRP)
        elif protocol in [AuditProtocol.HSRP, AuditProtocol.VRRP]:
            if "arista" in v:
                return "show vrrp; show vrrp detail"
            elif "juniper" in v:
                return "show vrrp extensive"
            return "show standby brief; show standby neighbors; show vrrp brief"

        # 17. BFD
        elif protocol == AuditProtocol.BFD:
            if "arista" in v:
                return "show bfd peers"
            elif "juniper" in v:
                return "show bfd session"
            return "show bfd neighbors detail"

        # 18. VRF
        elif protocol == AuditProtocol.VRF:
            if "arista" in v:
                return "show vrf"
            elif "juniper" in v:
                return "show routing-instances"
            return "show vrf detail; show ip route vrf *"

        # 19. QoS & ACL
        elif protocol in [AuditProtocol.QOS, AuditProtocol.ACL]:
            if "arista" in v:
                return "show qos maps; show ip access-lists"
            return "show policy-map interface; show ip access-lists"

        # 20. NAT & VPN
        elif protocol in [AuditProtocol.NAT, AuditProtocol.VPN]:
            if "palo" in v:
                return "show running nat-rule; show vpn ipsec-sa; show vpn ike-sa"
            elif "fortinet" in v:
                return "get router info routing-table all; get vpn ipsec tunnel summary"
            return "show ip nat translations; show crypto ikev2 sa; show crypto ipsec sa"

        # 21. Firewall Specific (Policies, Zones, HA)
        elif protocol in [AuditProtocol.FIREWALL_POLICY, AuditProtocol.FIREWALL_ZONES, AuditProtocol.FIREWALL_HA]:
            if "palo" in v:
                return "show running security-rule; show zones; show high-availability all"
            elif "fortinet" in v:
                return "show firewall policy; show system ha; get system ha status"
            return "show running security-rule; show zones; show high-availability all"

        # 22. Wireless (WLC & AP)
        elif protocol in [AuditProtocol.WIRELESS_WLC, AuditProtocol.WIRELESS_AP, AuditProtocol.WIRELESS_SSID, AuditProtocol.WIRELESS_RF]:
            if "aruba" in v:
                return "show ap database; show wlan summary; show ap radio-summary"
            return "show ap summary; show wlan summary; show ap dot11 5ghz summary; show ap dot11 24ghz summary"

        # 23. WAN / SD-WAN Edge
        elif protocol in [AuditProtocol.WAN_UNDERLAY, AuditProtocol.WAN_SLA]:
            if "cisco" in v:
                return "show sdwan control connections; show sdwan bfd sessions; show sdwan app-route sla-summary"
            return "show ip interface brief; show bfd neighbors; show ip sla statistics"

        # 24. Management Security
        elif protocol == AuditProtocol.MANAGEMENT_SECURITY:
            if "palo" in v:
                return "show admins; show ntp; show snmp info; show system services"
            elif "arista" in v:
                return "show aaa; show ssh; show ntp status; show snmp"
            return "show line vty 0 4; show aaa servers; show ntp status; show snmp group"

        return "show running-config"

    @staticmethod
    def detect_device_classification(device: DeviceModel) -> str:
        """
        Classifies a device into one of the 9 core device types:
        L2 Switch, L3 Switch, Router, Firewall, WLC, Wireless AP, WAN Edge, VPN Gateway, Load Balancer.
        """
        func = device.device_function
        role = device.device_role
        m = (device.device_model or "").lower()
        v = (device.vendor or "").lower()

        if func == DeviceFunction.FIREWALL or role == DeviceRole.FIREWALL or "palo" in v or "fortinet" in v:
            return "Firewall"
        if func == DeviceFunction.WIRELESS_AP or role == DeviceRole.WIRELESS_AP:
            return "Wireless AP"
        if "wlc" in m or "controller" in m:
            return "Wireless Controller"
        if func == DeviceFunction.EDGE_WAN or role == DeviceRole.EDGE or "isr" in m or "asr" in m:
            return "WAN Edge"
        if func == DeviceFunction.L3 or role in [DeviceRole.CORE, DeviceRole.SPINE]:
            return "L3 Switch"
        if func == DeviceFunction.L2_L3 or role in [DeviceRole.DISTRIBUTION, DeviceRole.LEAF]:
            return "L3 Switch"
        if func == DeviceFunction.L2 or role == DeviceRole.ACCESS:
            return "L2 Switch"
        return "L2 Switch"

    @classmethod
    def get_applicable_protocols(cls, device: DeviceModel, config: Dict[str, Any] = None) -> List[AuditProtocol]:
        """
        Returns the ordered list of applicable protocols for the given device classification and configuration.
        """
        dev_type = cls.detect_device_classification(device)
        protocols = [AuditProtocol.RUNNING_CONFIG, AuditProtocol.BASIC_HEALTH, AuditProtocol.INTERFACES, AuditProtocol.MANAGEMENT_SECURITY]

        if dev_type == "L2 Switch":
            protocols.extend([
                AuditProtocol.CDP,
                AuditProtocol.LLDP,
                AuditProtocol.VLAN,
                AuditProtocol.ACCESS_PORT,
                AuditProtocol.TRUNK,
                AuditProtocol.STP,
                AuditProtocol.ETHERCHANNEL,
                AuditProtocol.PORT_SECURITY,
                AuditProtocol.DHCP_SNOOPING,
                AuditProtocol.DAI,
                AuditProtocol.IP_SOURCE_GUARD,
                AuditProtocol.ACL
            ])
        elif dev_type == "L3 Switch":
            protocols.extend([
                AuditProtocol.CDP,
                AuditProtocol.LLDP,
                AuditProtocol.VLAN,
                AuditProtocol.ACCESS_PORT,
                AuditProtocol.TRUNK,
                AuditProtocol.STP,
                AuditProtocol.ETHERCHANNEL,
                AuditProtocol.PORT_SECURITY,
                AuditProtocol.DHCP_SNOOPING,
                AuditProtocol.DAI,
                AuditProtocol.SVI,
                AuditProtocol.STATIC_ROUTING,
                AuditProtocol.OSPF,
                AuditProtocol.BGP,
                AuditProtocol.EIGRP,
                AuditProtocol.HSRP,
                AuditProtocol.VRRP,
                AuditProtocol.BFD,
                AuditProtocol.VRF,
                AuditProtocol.QOS,
                AuditProtocol.ACL
            ])
        elif dev_type == "Router":
            protocols.extend([
                AuditProtocol.CDP,
                AuditProtocol.LLDP,
                AuditProtocol.STATIC_ROUTING,
                AuditProtocol.OSPF,
                AuditProtocol.BGP,
                AuditProtocol.EIGRP,
                AuditProtocol.ISIS,
                AuditProtocol.HSRP,
                AuditProtocol.VRRP,
                AuditProtocol.VRF,
                AuditProtocol.BFD,
                AuditProtocol.MPLS,
                AuditProtocol.QOS,
                AuditProtocol.ACL,
                AuditProtocol.NAT,
                AuditProtocol.VPN
            ])
        elif dev_type == "Firewall":
            protocols.extend([
                AuditProtocol.FIREWALL_ZONES,
                AuditProtocol.FIREWALL_POLICY,
                AuditProtocol.NAT,
                AuditProtocol.STATIC_ROUTING,
                AuditProtocol.OSPF,
                AuditProtocol.BGP,
                AuditProtocol.VPN,
                AuditProtocol.FIREWALL_HA,
                AuditProtocol.ACL
            ])
        elif dev_type == "Wireless Controller":
            protocols.extend([
                AuditProtocol.WIRELESS_WLC,
                AuditProtocol.WIRELESS_AP,
                AuditProtocol.WIRELESS_SSID,
                AuditProtocol.WIRELESS_RF,
                AuditProtocol.VLAN,
                AuditProtocol.ACL,
                AuditProtocol.QOS
            ])
        elif dev_type == "Wireless AP":
            protocols.extend([
                AuditProtocol.WIRELESS_AP,
                AuditProtocol.WIRELESS_SSID,
                AuditProtocol.WIRELESS_RF,
                AuditProtocol.VLAN,
                AuditProtocol.LLDP
            ])
        elif dev_type == "WAN Edge":
            protocols.extend([
                AuditProtocol.WAN_UNDERLAY,
                AuditProtocol.WAN_SLA,
                AuditProtocol.BFD,
                AuditProtocol.OSPF,
                AuditProtocol.BGP,
                AuditProtocol.STATIC_ROUTING,
                AuditProtocol.VPN,
                AuditProtocol.NAT,
                AuditProtocol.QOS,
                AuditProtocol.ACL
            ])

        return protocols

    @classmethod
    def generate_audit_tasks(
        cls,
        device: DeviceModel,
        config: Dict[str, Any] = None,
        links: List[TopologyLink] = None,
        existing_tasks: List[DeviceAuditTask] = None
    ) -> List[DeviceAuditTask]:
        """
        Generates the list of interactive To-Do audit tasks for this device based on its classification.
        Preserves existing task statuses and engineer notes if already set.
        """
        existing_map = {t.id: t for t in (existing_tasks or []) if t.device_hostname == device.hostname}
        dev_type = cls.detect_device_classification(device)
        vendor = device.vendor or "Cisco"
        protocols = cls.get_applicable_protocols(device, config)
        tasks: List[DeviceAuditTask] = []

        task_definitions = {
            AuditProtocol.RUNNING_CONFIG: [
                ("Running_Config_Backup", "Device Running Configuration Backup",
                 "Capture and archive a full running-configuration backup and baseline snapshot prior to audit verification.",
                 "Always Applicable (Priority 1 Baseline)", SeverityLevel.CRITICAL)
            ],
            AuditProtocol.BASIC_HEALTH: [
                ("Health_Baseline", "Device Platform, OS Version & Environmental Health",
                 "Verify hardware model, OS version compliance, uptime, CPU/Memory utilization, power supplies, and fan status.",
                 "Always Applicable", SeverityLevel.HIGH),
                ("Health_Management", "Management Protocol Synchronization (NTP, DNS, Syslog, SNMP)",
                 "Validate NTP clock synchronization, primary/secondary DNS servers, remote syslog logging, and SNMP trap communities.",
                 "Always Applicable", SeverityLevel.MEDIUM)
            ],
            AuditProtocol.INTERFACES: [
                ("Interface_Status", "Physical Interface Operational State & Speed/Duplex",
                 "Verify admin/operational status, auto-negotiation, port speed, MTU consistency, and interface descriptions.",
                 "Connected Ports Active", SeverityLevel.CRITICAL),
                ("Interface_Errors", "Interface Counter Errors, Drops & CRC Health",
                 "Verify absence of alignment errors, FCS/CRC error increments, packet discards, collisions, and err-disabled states.",
                 "All Interfaces", SeverityLevel.HIGH)
            ],
            AuditProtocol.CDP: [
                ("CDP_Neighbors", "CDP Neighbor Adjacency & Expected Peer Topology Match",
                 "Verify CDP neighbor table against physical topology design. Ensure local interface, remote interface, and device platform consistency.",
                 "CDP Enabled / Expected", SeverityLevel.MEDIUM)
            ],
            AuditProtocol.LLDP: [
                ("LLDP_Neighbors", "LLDP Neighbor Chassis ID & Port Information",
                 "Validate multi-vendor LLDP neighbor table, system capabilities, and remote management address consistency.",
                 "LLDP Enabled / Expected", SeverityLevel.MEDIUM)
            ],
            AuditProtocol.VLAN: [
                ("VLAN_Consistency", "VLAN Database, Active VLAN IDs & Name Consistency",
                 "Verify standard VLANs (Data, Voice, Management, Native), ensure active state, and validate cross-switch VLAN consistency.",
                 "VLAN Configured", SeverityLevel.HIGH)
            ],
            AuditProtocol.ACCESS_PORT: [
                ("Access_VLAN_Mapping", "Access Port VLAN Assignment & PortFast Enforcement",
                 "Ensure edge ports are mapped to correct access VLAN, voice VLAN enabled where applicable, and Spanning-Tree PortFast is active.",
                 "Interface Mode = Access", SeverityLevel.HIGH)
            ],
            AuditProtocol.TRUNK: [
                ("Trunk_Integrity", "802.1Q Trunk Status, Native VLAN & Allowed VLAN List",
                 "Verify trunk operational state, consistent native VLAN (non-default VLAN 1), and explicit allowed VLAN filtering on inter-switch uplinks.",
                 "Interface Mode = Trunk", SeverityLevel.CRITICAL)
            ],
            AuditProtocol.STP: [
                ("STP_Topology", "Spanning-Tree Protocol Mode, Root Bridge & Guard Protection",
                 "Verify STP mode (Rapid-PVST/MST), designated Root Bridge priorities, blocking ports, and BPDU Guard/Root Guard on edge interfaces.",
                 "STP Active", SeverityLevel.CRITICAL)
            ],
            AuditProtocol.ETHERCHANNEL: [
                ("LACP_Bundling", "EtherChannel Port-Channel Bundling & LACP Negotiation",
                 "Validate member port aggregation, active LACP negotiation, duplex/speed/VLAN consistency across bundled physical links.",
                 "Port-Channel Configured", SeverityLevel.HIGH)
            ],
            AuditProtocol.PORT_SECURITY: [
                ("Port_Security_Audit", "Port Security MAC Limiting & Violation Actions",
                 "Verify maximum allowable MAC addresses, sticky learning, and shutdown/restrict violation mode on untrusted edge access interfaces.",
                 "L2 Security Feature Configured", SeverityLevel.MEDIUM)
            ],
            AuditProtocol.DHCP_SNOOPING: [
                ("DHCP_Snooping_DAI", "DHCP Snooping & Dynamic ARP Inspection (DAI) Binding",
                 "Validate trusted vs untrusted uplink interfaces, active DHCP snooping binding table, and DAI rate limiting against ARP spoofing.",
                 "DHCP Snooping / DAI Enabled", SeverityLevel.HIGH)
            ],
            AuditProtocol.SVI: [
                ("SVI_Gateways", "Switch Virtual Interface (SVI) Gateway IP & Subnetting",
                 "Verify SVI operational status (up/up), IP address assignment, correct prefix lengths, and absence of IP conflicts or overlap.",
                 "SVI Configured", SeverityLevel.CRITICAL)
            ],
            AuditProtocol.STATIC_ROUTING: [
                ("Static_Routes", "Static & Default Route Reachability and Tracking",
                 "Verify default gateway route (0.0.0.0/0), next-hop recursive resolution, and IP SLA route tracking for gateway failover.",
                 "Static Routing Configured", SeverityLevel.HIGH)
            ],
            AuditProtocol.OSPF: [
                ("OSPF_Adjacencies", "OSPF Neighbor Adjacencies, Router-ID & Area Consistency",
                 "Verify OSPF process ID, unique Router-IDs, Full neighbor adjacencies, timer synchronization (Hello/Dead), and passive interfaces.",
                 "OSPF Routing Configured", SeverityLevel.CRITICAL),
                ("OSPF_Route_Table", "OSPF Inter-Area & External Route Learning",
                 "Confirm expected internal O/O IA routes and external E1/E2 prefixes are actively populated in the routing table.",
                 "OSPF Routing Configured", SeverityLevel.HIGH)
            ],
            AuditProtocol.BGP: [
                ("BGP_Sessions", "BGP Peer Session State, AS Numbers & Prefix Exchange",
                 "Verify BGP Established state, local/remote AS numbers, update-source loopback, route-maps, and prefix advertised/received counts.",
                 "BGP Peering Configured", SeverityLevel.CRITICAL)
            ],
            AuditProtocol.EIGRP: [
                ("EIGRP_Neighbors", "EIGRP Neighbor Adjacencies & K-Value Compatibility",
                 "Verify Autonomous System number, neighbor table status, passive interfaces, and metric/successor convergence.",
                 "EIGRP Configured", SeverityLevel.HIGH)
            ],
            AuditProtocol.HSRP: [
                ("FHRP_Redundancy", "HSRP / VRRP Virtual IP, Priority & Preemption Verification",
                 "Validate active/standby router roles, Virtual IP (VIP) consistency, priority decrements on uplink failure, and preemption settings.",
                 "FHRP Configured", SeverityLevel.CRITICAL)
            ],
            AuditProtocol.BFD: [
                ("BFD_Fast_Failover", "Bidirectional Forwarding Detection (BFD) Session Health",
                 "Verify sub-second BFD peer session status, detection multipliers, and protocol associations (OSPF/BGP/Static).",
                 "BFD Configured", SeverityLevel.HIGH)
            ],
            AuditProtocol.VRF: [
                ("VRF_Isolation", "VRF Route Distinguishers, Route Targets & Route Isolation",
                 "Verify interface VRF bindings, segregated routing tables, and controlled route leaking policies across management/corporate domains.",
                 "VRF Configured", SeverityLevel.HIGH)
            ],
            AuditProtocol.QOS: [
                ("QoS_Policies", "Quality of Service (QoS) Queuing, DSCP/CoS & Policing",
                 "Validate class-maps, policy-map attachments on WAN/uplink interfaces, DSCP trust boundaries, and absence of excessive tail drops.",
                 "QoS Configured", SeverityLevel.MEDIUM)
            ],
            AuditProtocol.ACL: [
                ("ACL_Enforcement", "Access Control List (ACL) Rule Sequence & Logging",
                 "Verify ACL placement on interfaces, ingress/egress filtering, implicit deny logging, and absence of shadowed/redundant ACEs.",
                 "ACL Configured", SeverityLevel.HIGH)
            ],
            AuditProtocol.FIREWALL_ZONES: [
                ("FW_Security_Zones", "Firewall Security Zones & Interface Membership",
                 "Verify Inside, Outside, DMZ zone assignments, virtual router bindings, and intra/inter-zone default block policies.",
                 "Firewall Classified", SeverityLevel.CRITICAL)
            ],
            AuditProtocol.FIREWALL_POLICY: [
                ("FW_Security_Rules", "Firewall Security Rule Base & Any/Any Mitigation",
                 "Audit active firewall rules, source/destination zone constraints, application-ID inspection, and verify no overly broad Any/Any rules.",
                 "Firewall Rules Configured", SeverityLevel.CRITICAL)
            ],
            AuditProtocol.NAT: [
                ("FW_NAT_Policies", "Network Address Translation (NAT) Rules & IP Pools",
                 "Verify Source/Destination NAT policies, PAT overload IP pools, static 1:1 server mappings, and hit counts.",
                 "NAT Configured", SeverityLevel.HIGH)
            ],
            AuditProtocol.VPN: [
                ("VPN_Tunnels", "IPsec / SSL VPN Tunnel Phase 1 & Phase 2 SAs",
                 "Verify IKEv2 / IPsec proposal encryption (AES-256/GCM), DH groups, tunnel operational status, and crypto throughput.",
                 "VPN Configured", SeverityLevel.CRITICAL)
            ],
            AuditProtocol.FIREWALL_HA: [
                ("FW_HA_Sync", "Firewall High Availability Active/Passive & Session Sync",
                 "Verify HA control/data link heartbeats, configuration synchronization, state table replication, and split-brain safeguards.",
                 "Firewall HA Configured", SeverityLevel.CRITICAL)
            ],
            AuditProtocol.WIRELESS_WLC: [
                ("WLC_Health", "Wireless Controller License, AP Capacity & Redundancy",
                 "Verify WLC HA SSO state, maximum AP license capacity, CPU/Memory thresholds, and centralized mobility groups.",
                 "WLC Classified", SeverityLevel.CRITICAL)
            ],
            AuditProtocol.WIRELESS_AP: [
                ("AP_Join_Status", "AP Controller Registration, AP Group & Site Tagging",
                 "Verify AP CAPWAP join state, correct primary/secondary controller IP, AP group assignment, and physical floor location tag.",
                 "Wireless AP Classified", SeverityLevel.CRITICAL)
            ],
            AuditProtocol.WIRELESS_SSID: [
                ("WLAN_SSID_Security", "SSID Broadcast, 802.1X / WPA3 Security & VLAN Mapping",
                 "Validate corporate/guest SSID broadcast, WPA3-Enterprise / RADIUS authentication, and client VLAN subnet assignments.",
                 "SSID Configured", SeverityLevel.HIGH)
            ],
            AuditProtocol.WIRELESS_RF: [
                ("RF_Radio_Channels", "Radio Spectrum (2.4/5/6 GHz), Auto-Channel & Tx Power",
                 "Audit DFS channels, transmit power levels, channel width (20/40/80 MHz), interference/noise floor, and clean Air metrics.",
                 "Wireless Radio Active", SeverityLevel.HIGH)
            ],
            AuditProtocol.WAN_UNDERLAY: [
                ("WAN_Overlay_Tunnels", "WAN Underlay Transport & Overlay Control Connections",
                 "Verify dual ISP internet/MPLS underlay reachability, IPsec overlay tunnel encryption, and control plane peering.",
                 "WAN Edge Classified", SeverityLevel.CRITICAL)
            ],
            AuditProtocol.WAN_SLA: [
                ("WAN_Application_SLA", "WAN Application-Aware SLA Tracking (Loss/Latency/Jitter)",
                 "Validate real-time link latency, jitter, packet loss metrics, and automated application route steering failover.",
                 "WAN Edge Classified", SeverityLevel.HIGH)
            ],
            AuditProtocol.MANAGEMENT_SECURITY: [
                ("Mgmt_Access_Hardening", "Management Plane Hardening (SSH Only, AAA, VTY ACL)",
                 "Confirm Telnet/HTTP disabled, SSHv2 enforced, TACACS+/RADIUS authentication active, and VTY access filtered by management ACL.",
                 "Always Applicable", SeverityLevel.HIGH)
            ]
        }

        for proto in protocols:
            defs = task_definitions.get(proto, [])
            for test_key, title, desc, cond, sev in defs:
                task_id = f"TASK-{device.hostname}-{proto.value.replace(' ', '_').replace('/', '_')}-{test_key}"
                cli_cmd = cls.get_cli_command(vendor, proto, test_key, device)

                # Check if existing task has status/notes
                existing = existing_map.get(task_id)
                status = existing.status if existing else TaskVerificationStatus.INCOMPLETE
                notes = existing.evidence_notes if existing else ""
                output = existing.actual_output if existing else ""

                tasks.append(DeviceAuditTask(
                    id=task_id,
                    device_hostname=device.hostname,
                    device_role=device.device_role.value,
                    protocol=proto.value,
                    category=cls.get_category_for_protocol(proto),
                    title=title,
                    description=desc,
                    condition=cond,
                    verification_command=cli_cmd,
                    status=status,
                    actual_output=output,
                    evidence_notes=notes,
                    severity=sev
                ))

        # Include any custom/modular test scenarios from CatalogManager strictly based on device role
        existing_task_keys = {t.id for t in tasks}
        existing_titles = {t.title.lower().strip() for t in tasks}
        dev_role_str = device.device_role.value if hasattr(device.device_role, "value") else str(device.device_role)
        applicable_proto_names = {p.value.lower() for p in protocols} | {p.name.lower() for p in protocols}

        for scenario in CatalogManager.get_scenarios():
            s_id = scenario.get("id", "")
            s_proto = scenario.get("protocol", "Custom")
            s_cat = scenario.get("category", "Custom Audit Domain")
            s_title = scenario.get("title", s_id)
            s_desc = scenario.get("description", "")
            s_cond = scenario.get("condition", "Custom Policy")
            s_roles = scenario.get("roles")

            # 1. Strict Role-based validation: only add scenario if device role is in allowed roles
            if s_roles:
                if not any(r.lower() == dev_role_str.lower() for r in s_roles):
                    continue  # Skip scenario: device role not in allowed roles!
            else:
                # Protocol-based check against applicable protocols for this device
                s_proto_norm = s_proto.lower().strip().replace(" ", "_")
                if not any(p_name in s_proto_norm or s_proto_norm in p_name for p_name in applicable_proto_names):
                    continue

            # 2. Avoid duplicating existing tests already generated by task_definitions
            if s_title.lower().strip() in existing_titles:
                # Update verification command if CatalogManager provides a vendor-specific one
                for existing_task in tasks:
                    if existing_task.title.lower().strip() == s_title.lower().strip():
                        custom_cli = CatalogManager.get_vendor_cli_command(s_id, vendor)
                        if custom_cli and custom_cli != "show running-config":
                            existing_task.verification_command = custom_cli
                continue

            s_sev_str = scenario.get("severity", "Medium")
            s_sev = SeverityLevel.CRITICAL if s_sev_str.lower() == "critical" else (
                SeverityLevel.HIGH if s_sev_str.lower() == "high" else (
                    SeverityLevel.LOW if s_sev_str.lower() == "low" else SeverityLevel.MEDIUM
                )
            )
            task_id = f"TASK-{device.hostname}-{s_id}"
            if task_id not in existing_task_keys:
                cli_cmd = CatalogManager.get_vendor_cli_command(s_id, vendor)
                existing = existing_map.get(task_id)
                status = existing.status if existing else TaskVerificationStatus.INCOMPLETE
                notes = existing.evidence_notes if existing else ""
                output = existing.actual_output if existing else ""

                tasks.append(DeviceAuditTask(
                    id=task_id,
                    device_hostname=device.hostname,
                    device_role=device.device_role.value,
                    protocol=s_proto,
                    category=s_cat,
                    title=s_title,
                    description=s_desc,
                    condition=s_cond,
                    verification_command=cli_cmd,
                    status=status,
                    actual_output=output,
                    evidence_notes=notes,
                    severity=s_sev
                ))

        return tasks

    @staticmethod
    def get_category_for_protocol(proto: AuditProtocol) -> str:
        if proto == AuditProtocol.RUNNING_CONFIG:
            return "Configuration & Baseline"
        if proto in [AuditProtocol.BASIC_HEALTH, AuditProtocol.MANAGEMENT_SECURITY]:
            return "Baseline & Device Health"
        if proto in [AuditProtocol.INTERFACES, AuditProtocol.CDP, AuditProtocol.LLDP]:
            return "Interface & Neighbor Discovery"
        if proto in [AuditProtocol.VLAN, AuditProtocol.ACCESS_PORT, AuditProtocol.TRUNK, AuditProtocol.STP, AuditProtocol.ETHERCHANNEL]:
            return "Layer 2 Switching & STP"
        if proto in [AuditProtocol.PORT_SECURITY, AuditProtocol.DHCP_SNOOPING, AuditProtocol.DAI, AuditProtocol.IP_SOURCE_GUARD]:
            return "Layer 2 Infrastructure Security"
        if proto in [AuditProtocol.SVI, AuditProtocol.STATIC_ROUTING, AuditProtocol.OSPF, AuditProtocol.BGP, AuditProtocol.EIGRP, AuditProtocol.ISIS, AuditProtocol.HSRP, AuditProtocol.VRRP, AuditProtocol.BFD, AuditProtocol.VRF]:
            return "Layer 3 Routing & Redundancy"
        if proto in [AuditProtocol.FIREWALL_ZONES, AuditProtocol.FIREWALL_POLICY, AuditProtocol.NAT, AuditProtocol.FIREWALL_HA]:
            return "Firewall & Perimeter Security"
        if proto in [AuditProtocol.WIRELESS_WLC, AuditProtocol.WIRELESS_AP, AuditProtocol.WIRELESS_SSID, AuditProtocol.WIRELESS_RF]:
            return "Wireless Infrastructure & RF"
        if proto in [AuditProtocol.WAN_UNDERLAY, AuditProtocol.WAN_SLA, AuditProtocol.MPLS, AuditProtocol.VPN, AuditProtocol.QOS, AuditProtocol.ACL]:
            return "WAN, Overlay & Traffic Policy"
        return "General Infrastructure"
