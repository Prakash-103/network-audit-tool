"""
Layer 2 Device Audit Module (Section 3.3).
Audits Switching, VLANs, Spanning-Tree (Rapid-PVST+/MST), BPDU Guard, Native VLAN security, and L2 Design Validation.
"""
from typing import List, Dict, Any
from core.models import DeviceModel, AuditCheckResult, TopologyLink
from core.constants import AuditStatus, SeverityLevel

class L2AuditModule:
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
        stp = parsed_config.get("stp", {})
        vlans = parsed_config.get("vlans", [])

        # Check 1: Spanning Tree Protocol (STP) Mode
        stp_mode = stp.get("mode", "Unknown")
        if stp_mode in ["Rapid-PVST+", "MST"]:
            results.append(AuditCheckResult(
                id=f"AUD-L2-{host}-001",
                device=host,
                role=role,
                category="L2 Switching",
                check="Spanning-Tree Protocol Mode",
                expected="Rapid-PVST+ or MST required for sub-second failure convergence",
                actual=f"Spanning-Tree mode is {stp_mode}",
                status=AuditStatus.PASS,
                severity=SeverityLevel.INFO,
                evidence=f"STP configuration on {host}",
                recommendation="No action required."
            ))
        else:
            results.append(AuditCheckResult(
                id=f"AUD-L2-{host}-001",
                device=host,
                role=role,
                category="L2 Switching",
                check="Spanning-Tree Protocol Mode",
                expected="Rapid-PVST+ or MST required for sub-second failure convergence",
                actual=f"Legacy or unverified STP mode: {stp_mode}",
                status=AuditStatus.WARNING,
                severity=SeverityLevel.HIGH if "core" in role.lower() else SeverityLevel.MEDIUM,
                evidence=f"Global STP configuration on {host}",
                recommendation="Migrate STP mode to `spanning-tree mode rapid-pvst`."
            ))

        # Check 2: BPDU Guard on Edge Ports
        bpdu_guard = stp.get("bpdu_guard_enabled", False)
        edge_ports = [i for i in intfs if i.get("portfast")]
        if bpdu_guard or all(i.get("bpduguard") for i in edge_ports):
            results.append(AuditCheckResult(
                id=f"AUD-L2-{host}-002",
                device=host,
                role=role,
                category="L2 Switching",
                check="STP BPDU Guard Enforcement",
                expected="BPDU Guard must be active globally or on all edge PortFast access ports",
                actual="BPDU Guard is enabled and protecting edge interfaces",
                status=AuditStatus.PASS,
                severity=SeverityLevel.INFO,
                evidence=f"STP BPDU Guard policy on {host}",
                recommendation="No action required."
            ))
        else:
            results.append(AuditCheckResult(
                id=f"AUD-L2-{host}-002",
                device=host,
                role=role,
                category="L2 Switching",
                check="STP BPDU Guard Enforcement",
                expected="BPDU Guard must be active globally or on all edge PortFast access ports",
                actual="BPDU Guard is disabled on edge access interfaces",
                status=AuditStatus.FAIL,
                severity=SeverityLevel.HIGH,
                evidence=f"PortFast / BPDU Guard configuration on {host}",
                recommendation="Configure global `spanning-tree portfast bpduguard default` to prevent unauthorized switch attachments."
            ))

        # Check 3: Native VLAN 1 Security on 802.1Q Trunks
        trunks = [i for i in intfs if i.get("is_trunk")]
        trunks_with_vlan1 = [i["name"] for i in trunks if i.get("native_vlan") == 1]
        if trunks_with_vlan1:
            results.append(AuditCheckResult(
                id=f"AUD-L2-{host}-003",
                device=host,
                role=role,
                category="L2 Switching",
                check="802.1Q Trunk Native VLAN Tagging & ID",
                expected="Native VLAN must be explicitly changed from default VLAN 1 to a non-routable ID (e.g. VLAN 999)",
                actual=f"Default VLAN 1 used as native VLAN on trunks: {', '.join(trunks_with_vlan1)}",
                status=AuditStatus.WARNING,
                severity=SeverityLevel.MEDIUM,
                evidence=f"Trunk configuration for {host}",
                recommendation="Change native VLAN on trunks using `switchport trunk native vlan 999` to prevent VLAN hopping attacks."
            ))
        else:
            results.append(AuditCheckResult(
                id=f"AUD-L2-{host}-003",
                device=host,
                role=role,
                category="L2 Switching",
                check="802.1Q Trunk Native VLAN Tagging & ID",
                expected="Native VLAN changed from default VLAN 1",
                actual=f"Native VLAN security policy enforced on all {len(trunks)} trunk(s)",
                status=AuditStatus.PASS,
                severity=SeverityLevel.INFO,
                evidence=f"Trunk interface configs on {host}",
                recommendation="No action required."
            ))

        # Check 4: L2 Design Validation - Neighbor VLAN Consistency across Trunks
        # Find adjacent devices via topology links
        neighbor_vlan_mismatches = []
        for link in topology_links:
            peer_host = link.target_device if link.source_device == host else link.source_device if link.target_device == host else None
            if peer_host and peer_host in all_configs:
                peer_vlans = all_configs[peer_host].get("vlans", [])
                missing_on_peer = set(vlans) - set(peer_vlans)
                if missing_on_peer and len(vlans) > 0 and len(peer_vlans) > 0:
                    neighbor_vlan_mismatches.append(f"VLAN(s) {list(missing_on_peer)} present on {host} but missing on {peer_host}")

        if neighbor_vlan_mismatches:
            results.append(AuditCheckResult(
                id=f"AUD-L2-{host}-004",
                device=host,
                role=role,
                category="L2 Design Validation",
                check="VLAN Database Consistency with Neighbor Switches",
                expected="All connecting trunk peer switches must have consistent active VLAN databases",
                actual=f"VLAN inconsistency: {'; '.join(neighbor_vlan_mismatches[:2])}",
                status=AuditStatus.WARNING,
                severity=SeverityLevel.HIGH,
                evidence=f"Topology link trunk peer analysis for {host}",
                recommendation="Synchronize VLAN database definitions across all adjacent switching nodes."
            ))
        else:
            results.append(AuditCheckResult(
                id=f"AUD-L2-{host}-004",
                device=host,
                role=role,
                category="L2 Design Validation",
                check="VLAN Database Consistency with Neighbor Switches",
                expected="Consistent VLAN databases between connected switches",
                actual="VLAN definitions are consistent with connected neighbor switches",
                status=AuditStatus.PASS,
                severity=SeverityLevel.INFO,
                evidence=f"Cross-switch VLAN comparison for {host}",
                recommendation="No action required."
            ))

        return results
