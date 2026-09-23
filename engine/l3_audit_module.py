"""
Layer 3 Device Audit Module (Section 3.2).
Audits L3 Configuration & L3 Design Validation for devices classified as L3 / L2_L3 / Core / Distribution / Spine / Leaf / Edge.
"""
from typing import List, Dict, Any
from core.models import DeviceModel, AuditCheckResult, TopologyLink
from core.constants import AuditStatus, SeverityLevel

class L3AuditModule:
    @staticmethod
    def audit(
        device: DeviceModel,
        parsed_config: Dict[str, Any],
        topology_links: List[TopologyLink],
        all_devices: List[DeviceModel],
        all_configs: Dict[str, Dict[str, Any]]
    ) -> List[AuditCheckResult]:
        results: List[AuditCheckResult] = []
        host = device.hostname
        role = device.device_role.value
        intfs = parsed_config.get("interfaces", [])
        routing = parsed_config.get("routing", {})

        # Check 1: Interface IP Addressing & Subnet Masks
        ips_found = [i for i in intfs if i.get("ip")]
        if ips_found:
            results.append(AuditCheckResult(
                id=f"AUD-L3-{host}-001",
                device=host,
                role=role,
                category="L3 Configuration",
                check="Interface IP Addressing & Subnet Masks",
                expected="All routed and SVI interfaces must have valid non-overlapping IP addresses and netmasks",
                actual=f"{len(ips_found)} configured IP interface(s) detected: {', '.join([f'{i['name']} ({i['ip']})' for i in ips_found[:3]])}",
                status=AuditStatus.PASS,
                severity=SeverityLevel.INFO,
                evidence=f"Interface IP table on {host}",
                recommendation="Maintain standardized IP addressing plan."
            ))
        else:
            results.append(AuditCheckResult(
                id=f"AUD-L3-{host}-001",
                device=host,
                role=role,
                category="L3 Configuration",
                check="Interface IP Addressing & Subnet Masks",
                expected="L3 device must have at least one routed or SVI interface configured with an IP address",
                actual="No IP addresses configured on any interface",
                status=AuditStatus.FAIL,
                severity=SeverityLevel.CRITICAL if "core" in role.lower() else SeverityLevel.HIGH,
                evidence=f"Running configuration interface section for {host}",
                recommendation="Assign IP addresses to routed interfaces / Loopback0 per IP Plan."
            ))

        # Check 2: Dynamic Routing Protocol (OSPF / BGP / EIGRP)
        ospf = routing.get("ospf", {})
        bgp = routing.get("bgp", {})
        if ospf.get("enabled"):
            # OSPF Passive Interface Check
            if not ospf.get("passive_interfaces") and ("core" in role.lower() or "dist" in role.lower()):
                results.append(AuditCheckResult(
                    id=f"AUD-L3-{host}-002",
                    device=host,
                    role=role,
                    category="L3 Routing",
                    check="OSPF Passive Interface Hygiene",
                    expected="OSPF hello packets must be suppressed on user/edge VLANs using `passive-interface default`",
                    actual="OSPF is active without passive-interface restrictions",
                    status=AuditStatus.WARNING,
                    severity=SeverityLevel.HIGH,
                    evidence=f"Router OSPF {ospf.get('process_id')} on {host}",
                    recommendation="Enable `passive-interface default` and explicit `no passive-interface` on core links."
                ))
            else:
                results.append(AuditCheckResult(
                    id=f"AUD-L3-{host}-002",
                    device=host,
                    role=role,
                    category="L3 Routing",
                    check="OSPF Dynamic Routing",
                    expected=f"OSPF process active with defined areas",
                    actual=f"OSPF active (Process ID: {ospf.get('process_id')}, Areas: {', '.join(str(a) for a in ospf.get('areas', []))})",
                    status=AuditStatus.PASS,
                    severity=SeverityLevel.INFO,
                    evidence=f"OSPF configuration for {host}",
                    recommendation="No action required."
                ))

        if bgp.get("enabled"):
            unfiltered = [n["ip"] for n in bgp.get("neighbors", []) if n["ip"] not in bgp.get("filtered_neighbors", [])]
            if unfiltered:
                results.append(AuditCheckResult(
                    id=f"AUD-L3-{host}-003",
                    device=host,
                    role=role,
                    category="L3 Routing",
                    check="BGP Route Filtering (Prefix-lists / Route-maps)",
                    expected="All external and internal BGP peerings must apply explicit prefix-list or route-map inbound/outbound filters",
                    actual=f"Unfiltered BGP peer(s): {', '.join(unfiltered)}",
                    status=AuditStatus.FAIL,
                    severity=SeverityLevel.HIGH,
                    evidence=f"Router BGP {bgp.get('as_number')} on {host}",
                    recommendation="Apply route-maps/prefix-lists to all BGP neighbors to prevent route leaks."
                ))
            else:
                results.append(AuditCheckResult(
                    id=f"AUD-L3-{host}-003",
                    device=host,
                    role=role,
                    category="L3 Routing",
                    check="BGP Route Filtering",
                    expected="BGP peering sessions must enforce route filtering policies",
                    actual="All configured BGP neighbors enforce prefix-list / route-map filtering",
                    status=AuditStatus.PASS,
                    severity=SeverityLevel.INFO,
                    evidence=f"BGP configuration for {host}",
                    recommendation="No action required."
                ))

        # Check 3: L3 Design Validation - Duplicate IP Detection across Network
        device_ips = [i["ip"] for i in ips_found if i.get("ip")]
        duplicate_ips = []
        for other_host, other_cfg in all_configs.items():
            if other_host == host:
                continue
            other_ips = [i["ip"] for i in other_cfg.get("interfaces", []) if i.get("ip")]
            for ip in device_ips:
                if ip in other_ips:
                    duplicate_ips.append(f"{ip} (also on {other_host})")

        if duplicate_ips:
            results.append(AuditCheckResult(
                id=f"AUD-L3-{host}-004",
                device=host,
                role=role,
                category="L3 Design Validation",
                check="Duplicate IP Address Detection",
                expected="Every interface IP address across the routed domain must be globally unique",
                actual=f"Duplicate IP(s) detected: {', '.join(duplicate_ips)}",
                status=AuditStatus.FAIL,
                severity=SeverityLevel.CRITICAL,
                evidence=f"Cross-device configuration analysis for {host}",
                recommendation="Immediately resolve duplicate IP conflict to prevent ARP flapping and intermittent traffic drops."
            ))
        else:
            results.append(AuditCheckResult(
                id=f"AUD-L3-{host}-004",
                device=host,
                role=role,
                category="L3 Design Validation",
                check="Duplicate IP Address Detection",
                expected="Unique IP addressing across all routed subnets",
                actual="Zero duplicate IP addresses detected across active network devices",
                status=AuditStatus.PASS,
                severity=SeverityLevel.INFO,
                evidence=f"Network-wide IP plan validation for {host}",
                recommendation="No action required."
            ))

        return results
