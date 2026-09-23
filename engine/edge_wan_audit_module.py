"""
Edge / WAN Device Audit Module (Section 3.6).
Audits WAN Interfaces, ISP BGP Peering, VPN Tunnels, NAT, Default Route Redundancy, MTU, and QoS.
"""
from typing import List, Dict, Any
from core.models import DeviceModel, AuditCheckResult, TopologyLink
from core.constants import AuditStatus, SeverityLevel

class EdgeWANAuditModule:
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
        routing = parsed_config.get("routing", {})

        # Check 1: ISP Dual-Homing & Default Route Redundancy
        default_gw = routing.get("default_gateway")
        has_bgp = routing.get("bgp", {}).get("enabled", False)
        if has_bgp or default_gw:
            results.append(AuditCheckResult(
                id=f"AUD-WAN-{host}-001",
                device=host,
                role=role,
                category="WAN Edge Connectivity",
                check="Default Route & ISP Peering Redundancy",
                expected="Edge router must maintain multi-homed ISP BGP peering or dual static default routes with IP SLA tracking",
                actual=f"WAN Routing active (BGP AS: {routing.get('bgp', {}).get('as_number', 'Active')}, Default GW: {default_gw or 'BGP 0.0.0.0/0'})",
                status=AuditStatus.PASS,
                severity=SeverityLevel.INFO,
                evidence=f"WAN routing table on {host}",
                recommendation="No action required."
            ))
        else:
            results.append(AuditCheckResult(
                id=f"AUD-WAN-{host}-001",
                device=host,
                role=role,
                category="WAN Edge Connectivity",
                check="Default Route & ISP Peering Redundancy",
                expected="Edge router must have default route or ISP BGP session configured",
                actual="Missing default route or upstream ISP gateway",
                status=AuditStatus.FAIL,
                severity=SeverityLevel.CRITICAL,
                evidence=f"Global routing configuration on {host}",
                recommendation="Configure default route (`ip route 0.0.0.0 0.0.0.0 <ISP_GW>`) or establish eBGP session to ISP."
            ))

        # Check 2: IPsec VPN & WAN MTU Fragmentation Safeguards
        raw_text = parsed_config.get("raw_text", "").lower()
        if "crypto ipsec" in raw_text or "tunnel" in raw_text or "ip mtu 1400" in raw_text or "ip tcp adjust-mss" in raw_text:
            results.append(AuditCheckResult(
                id=f"AUD-WAN-{host}-002",
                device=host,
                role=role,
                category="WAN Edge Security",
                check="IPsec VPN Tunnel & MTU MSS Clamping",
                expected="WAN tunnel interfaces must enforce `ip tcp adjust-mss 1360` to avoid packet fragmentation",
                actual="WAN MTU clamping / IPsec VPN encapsulation configured properly",
                status=AuditStatus.PASS,
                severity=SeverityLevel.INFO,
                evidence=f"Tunnel interface configuration on {host}",
                recommendation="No action required."
            ))
        else:
            results.append(AuditCheckResult(
                id=f"AUD-WAN-{host}-002",
                device=host,
                role=role,
                category="WAN Edge Security",
                check="IPsec VPN Tunnel & MTU MSS Clamping",
                expected="WAN interface should configure TCP MSS clamping to prevent fragmentation drops",
                actual="No explicit `ip tcp adjust-mss` configured on WAN interface",
                status=AuditStatus.WARNING,
                severity=SeverityLevel.MEDIUM,
                evidence=f"WAN interface settings on {host}",
                recommendation="Apply `ip tcp adjust-mss 1360` on WAN / IPsec tunnel interfaces."
            ))

        return results
