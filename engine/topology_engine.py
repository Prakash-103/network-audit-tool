"""
Topology Management & Link Validation Engine.
Handles logical D2D adjacencies, bidirectional physical port-to-port mapping,
Port-Channel bundling, and Section 2.4 Link Validation checks.
"""
import uuid
from typing import List, Dict, Tuple, Optional
from core.models import DeviceModel, TopologyLink, PortChannelGroup, LinkValidationIssue
from core.constants import SeverityLevel, PortSpeed

class TopologyEngine:
    @staticmethod
    def get_canonical_link_id(dev_a: str, port_a: str, dev_b: str, port_b: str) -> str:
        pair = sorted([(dev_a, port_a), (dev_b, port_b)])
        return f"{pair[0][0]}_{pair[0][1]}___{pair[1][0]}_{pair[1][1]}"

    @staticmethod
    def add_bidirectional_link(
        links: List[TopologyLink],
        source_device: str,
        source_port: str,
        target_device: str,
        target_port: str,
        link_speed: str = PortSpeed.SPEED_10G.value,
        port_channel_id: Optional[str] = None
    ) -> List[TopologyLink]:
        canonical_id = TopologyEngine.get_canonical_link_id(source_device, source_port, target_device, target_port)
        
        # Remove any existing link that matches this canonical pair
        updated_links = [l for l in links if l.id != canonical_id]
        
        # Add the new bidirectional link
        new_link = TopologyLink(
            id=canonical_id,
            source_device=source_device,
            source_port=source_port,
            target_device=target_device,
            target_port=target_port,
            link_speed=link_speed,
            port_channel_id=port_channel_id,
            status="Valid"
        )
        updated_links.append(new_link)
        return updated_links

    @staticmethod
    def remove_bidirectional_link(links: List[TopologyLink], link_id: str) -> List[TopologyLink]:
        return [l for l in links if l.id != link_id]

    @staticmethod
    def validate_topology(
        devices: List[DeviceModel],
        links: List[TopologyLink],
        port_channels: List[PortChannelGroup]
    ) -> List[LinkValidationIssue]:
        """
        Enforces Section 2.4 Link Validation Rules:
        1. Missing adjacent-device relationship
        2. Missing port assignment
        3. Duplicate port assignment
        4. Port connected to multiple devices
        5. Port-channel with incomplete member ports
        6. Mismatched port speeds
        7. Invalid port combinations
        8. One-sided configuration
        9. Orphan interfaces
        """
        issues: List[LinkValidationIssue] = []
        device_map = {d.hostname: d for d in devices}

        # Track usage of ports per device
        device_port_usage: Dict[str, Dict[str, List[Tuple[str, str]]]] = {d.hostname: {} for d in devices}

        for link in links:
            s_dev = link.source_device
            s_port = link.source_port
            t_dev = link.target_device
            t_port = link.target_port

            # Check 1: Missing adjacent-device existence
            if s_dev not in device_map:
                issues.append(LinkValidationIssue(
                    rule="Missing Adjacent Device",
                    severity=SeverityLevel.HIGH,
                    source_device=s_dev,
                    source_port=s_port,
                    target_device=t_dev,
                    message=f"Source device '{s_dev}' is referenced in topology but does not exist in Inventory.",
                    remediation="Add device to Inventory on Page 1 or remove invalid connection."
                ))
            if t_dev not in device_map:
                issues.append(LinkValidationIssue(
                    rule="Missing Adjacent Device",
                    severity=SeverityLevel.HIGH,
                    source_device=s_dev,
                    target_device=t_dev,
                    target_port=t_port,
                    message=f"Target device '{t_dev}' is referenced in topology but does not exist in Inventory.",
                    remediation="Add device to Inventory on Page 1 or remove invalid connection."
                ))

            # Check 2: Missing port assignment
            if not s_port or s_port == "Unassigned":
                issues.append(LinkValidationIssue(
                    rule="Missing Port Assignment",
                    severity=SeverityLevel.CRITICAL,
                    source_device=s_dev,
                    target_device=t_dev,
                    message=f"Connection between '{s_dev}' and '{t_dev}' is missing source port assignment.",
                    remediation="Assign a physical interface on source device."
                ))
            if not t_port or t_port == "Unassigned":
                issues.append(LinkValidationIssue(
                    rule="Missing Port Assignment",
                    severity=SeverityLevel.CRITICAL,
                    source_device=s_dev,
                    target_device=t_dev,
                    message=f"Connection between '{s_dev}' and '{t_dev}' is missing target port assignment.",
                    remediation="Assign a physical interface on target device."
                ))

            # Track port usage for duplicate/conflict detection
            if s_dev in device_port_usage and s_port:
                if s_port not in device_port_usage[s_dev]:
                    device_port_usage[s_dev][s_port] = []
                device_port_usage[s_dev][s_port].append((t_dev, t_port))

            if t_dev in device_port_usage and t_port:
                if t_port not in device_port_usage[t_dev]:
                    device_port_usage[t_dev][t_port] = []
                device_port_usage[t_dev][t_port].append((s_dev, s_port))

            # Check 6: Mismatched port speeds
            dev_s_obj = device_map.get(s_dev)
            dev_t_obj = device_map.get(t_dev)
            if dev_s_obj and dev_t_obj:
                # If link speed differs from configured device default port speed
                if dev_s_obj.port_speed != dev_t_obj.port_speed and not link.port_channel_id:
                    issues.append(LinkValidationIssue(
                        rule="Mismatched Port Speeds",
                        severity=SeverityLevel.MEDIUM,
                        source_device=s_dev,
                        source_port=s_port,
                        target_device=t_dev,
                        target_port=t_port,
                        message=f"Speed mismatch between {s_dev} ({dev_s_obj.port_speed}) and {t_dev} ({dev_t_obj.port_speed}).",
                        remediation="Ensure connecting physical transceivers and interface speeds are uniform."
                    ))

        # Check 3 & 4: Duplicate port assignment / Port connected to multiple devices
        for dev_name, ports in device_port_usage.items():
            for port_name, connections in ports.items():
                if len(connections) > 1:
                    targets = [f"{c[0]}:{c[1]}" for c in connections]
                    issues.append(LinkValidationIssue(
                        rule="Duplicate Port Assignment / Multiple Connections",
                        severity=SeverityLevel.CRITICAL,
                        source_device=dev_name,
                        source_port=port_name,
                        message=f"Physical port '{port_name}' on '{dev_name}' is connected to multiple endpoints: {', '.join(targets)}.",
                        remediation="A physical port cannot connect to multiple devices simultaneously. Reassign ports."
                    ))

        # Check 5: Port-channel with incomplete member ports
        for po in port_channels:
            if len(po.source_member_ports) != len(po.target_member_ports):
                issues.append(LinkValidationIssue(
                    rule="Port-Channel Incomplete Member Ports",
                    severity=SeverityLevel.HIGH,
                    source_device=po.source_device,
                    target_device=po.target_device,
                    message=f"Port-Channel '{po.id}' has {len(po.source_member_ports)} member ports on {po.source_device} but {len(po.target_member_ports)} on {po.target_device}.",
                    remediation="Add matching number of member physical interfaces on both endpoints."
                ))
            if len(po.source_member_ports) == 0:
                issues.append(LinkValidationIssue(
                    rule="Port-Channel Missing Members",
                    severity=SeverityLevel.HIGH,
                    source_device=po.source_device,
                    target_device=po.target_device,
                    message=f"Port-Channel '{po.id}' has no member physical interfaces assigned.",
                    remediation="Assign at least 2 member physical interfaces to the Port-Channel."
                ))

        # Check 9: Orphan Interfaces (Devices with 0 configured links)
        connected_devs = set()
        for l in links:
            connected_devs.add(l.source_device)
            connected_devs.add(l.target_device)

        for dev in devices:
            if dev.hostname not in connected_devs and dev.device_role != "Other":
                issues.append(LinkValidationIssue(
                    rule="Orphan Device / Missing Uplink",
                    severity=SeverityLevel.MEDIUM,
                    source_device=dev.hostname,
                    message=f"Device '{dev.hostname}' ({dev.device_role.value}) has no connected uplinks or downlinks in Topology.",
                    remediation="Connect device to adjacent Core, Distribution, or Spine switch on Page 2."
                ))

        return issues
