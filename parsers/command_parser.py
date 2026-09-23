"""
Operational Command Output Parser for CDP/LLDP, Link Stats/Errors, Port-Channels, Routing Neighbors, and HA.
"""
import re
from typing import Dict, Any, List

class CommandOutputParser:
    @staticmethod
    def parse_cdp_lldp(output: str) -> List[Dict[str, str]]:
        neighbors = []
        lines = output.splitlines()
        for line in lines:
            # Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID
            m = re.search(r'^([a-zA-Z0-9.\-_]+)\s+([a-zA-Z0-9/\.]+)\s+\d+\s+[\s\w]*?\s+([a-zA-Z0-9/\.\-]+)?\s*([a-zA-Z0-9/\.]+)?$', line.strip())
            if m and not line.startswith("Device ID") and not line.startswith("Capability"):
                neighbors.append({
                    "neighbor_device": m.group(1),
                    "local_interface": m.group(2),
                    "remote_interface": m.group(4) if m.group(4) else "Unknown"
                })
        return neighbors

    @staticmethod
    def parse_interfaces_errors(output: str) -> List[Dict[str, Any]]:
        errors = []
        blocks = re.findall(r'([a-zA-Z0-9/\.\-]+)\s+is\s+(up|down).*?([\s\S]*?)(?=[a-zA-Z0-9/\.\-]+\s+is\s+(?:up|down)|\Z)', output, re.IGNORECASE)
        for name, status, body in blocks:
            crc = 0
            input_errors = 0
            output_errors = 0
            
            crc_m = re.search(r'(\d+)\s+CRC', body, re.IGNORECASE)
            if crc_m:
                crc = int(crc_m.group(1))
                
            in_err_m = re.search(r'(\d+)\s+input errors', body, re.IGNORECASE)
            if in_err_m:
                input_errors = int(in_err_m.group(1))

            out_err_m = re.search(r'(\d+)\s+output errors', body, re.IGNORECASE)
            if out_err_m:
                output_errors = int(out_err_m.group(1))

            if crc > 0 or input_errors > 0 or output_errors > 0:
                errors.append({
                    "interface": name,
                    "status": status,
                    "crc_errors": crc,
                    "input_errors": input_errors,
                    "output_errors": output_errors
                })
        return errors

    @staticmethod
    def parse_port_channels(output: str) -> List[Dict[str, Any]]:
        channels = []
        # Parse show etherchannel summary
        lines = output.splitlines()
        for line in lines:
            # Group  Port-channel  Protocol    Ports
            # 10     Po10(SU)         LACP      Eth1/1(P) Eth1/2(P)
            m = re.search(r'^\s*(\d+)\s+(Po\d+)\(([A-Z]+)\)\s+([A-Z]+)\s+(.+)$', line)
            if m:
                status_flags = m.group(3)
                members = re.findall(r'([a-zA-Z0-9/\.\-]+)\(([A-Z]+)\)', m.group(5))
                channels.append({
                    "group": m.group(1),
                    "port_channel": m.group(2),
                    "is_operational": "U" in status_flags,  # U = in use
                    "protocol": m.group(4),
                    "members": [{"port": port, "state": flag, "is_bundled": "P" in flag or "b" in flag} for port, flag in members]
                })
        return channels

    @staticmethod
    def parse_ospf_neighbors(output: str) -> List[Dict[str, str]]:
        neighbors = []
        lines = output.splitlines()
        for line in lines:
            m = re.search(r'^([0-9.]+)\s+(\d+)\s+([A-Z/]+)\s+[0-9:]+\s+([0-9.]+)\s+([a-zA-Z0-9/\.]+)', line.strip())
            if m and not line.startswith("Neighbor ID"):
                neighbors.append({
                    "neighbor_id": m.group(1),
                    "priority": m.group(2),
                    "state": m.group(3),
                    "address": m.group(4),
                    "interface": m.group(5)
                })
        return neighbors

    @staticmethod
    def parse_bgp_summary(output: str) -> List[Dict[str, str]]:
        peers = []
        lines = output.splitlines()
        for line in lines:
            m = re.search(r'^([0-9.]+)\s+\d+\s+(\d+)\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+([0-9a-zA-Z:]+)\s+(\d+|Active|Idle|Established)', line.strip())
            if m and not line.startswith("Neighbor"):
                peers.append({
                    "neighbor": m.group(1),
                    "remote_as": m.group(2),
                    "uptime": m.group(3),
                    "state_pfx": m.group(4)
                })
        return peers
