"""
Master Audit Pipeline Orchestrator for 3-Stage Network Infrastructure Audit.
Orchestrates Dynamic Role & Function Audits, Link Validation, and 3-Way Delta Verification.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.models import (
    NetworkProjectState, DeviceModel, TopologyLink, PortChannelGroup,
    AuditCheckResult, AuditSummaryMetrics
)
from core.constants import DeviceFunction, DeviceRole, AuditStatus, SeverityLevel, TaskVerificationStatus, ROLE_AUDIT_DISPLAY_MAP
from parsers.config_parser import MultiVendorConfigParser
from parsers.command_parser import CommandOutputParser
from engine.topology_engine import TopologyEngine
from engine.l3_audit_module import L3AuditModule
from engine.l2_audit_module import L2AuditModule
from engine.wireless_audit_module import WirelessAuditModule
from engine.firewall_audit_module import FirewallAuditModule
from engine.edge_wan_audit_module import EdgeWANAuditModule
from engine.connectivity_audit_module import ConnectivityAuditModule
from engine.severity_engine import SeverityEngine
from engine.protocol_catalog import ProtocolCatalogEngine

class AuditOrchestrator:
    @staticmethod
    def run_full_audit(state: NetworkProjectState, target_device_id: Optional[str] = None) -> NetworkProjectState:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Run Link Validation Engine on Page 2 Topology
        state.validation_issues = TopologyEngine.validate_topology(
            devices=state.devices,
            links=state.topology_links,
            port_channels=state.port_channels
        )

        # 2. Parse Raw Configurations & Command Outputs per device
        parsed_configs: Dict[str, Dict[str, Any]] = {}
        parsed_command_outputs: Dict[str, Dict[str, Any]] = {}

        for dev in state.devices:
            raw_cfg = state.raw_configs.get(dev.hostname, "")
            parsed_configs[dev.hostname] = MultiVendorConfigParser.parse_config(raw_cfg, f"{dev.hostname}_config.txt")

            raw_cmd = state.operational_logs.get(dev.hostname, "")
            parsed_command_outputs[dev.hostname] = {
                "cdp_neighbors": CommandOutputParser.parse_cdp_lldp(raw_cmd),
                "interface_errors": CommandOutputParser.parse_interfaces_errors(raw_cmd),
                "port_channels": CommandOutputParser.parse_port_channels(raw_cmd),
                "ospf_neighbors": CommandOutputParser.parse_ospf_neighbors(raw_cmd),
                "bgp_peers": CommandOutputParser.parse_bgp_summary(raw_cmd)
            }

        # 3. Execute Dynamic Function & Role Audits
        all_results: List[AuditCheckResult] = []
        target_devices = state.devices if not target_device_id else [d for d in state.devices if d.device_id == target_device_id or d.hostname == target_device_id]

        for dev in target_devices:
            host = dev.hostname
            func = dev.device_function
            role = dev.device_role
            cfg = parsed_configs.get(host, {})
            cmd_out = parsed_command_outputs.get(host, {})

            # L3 Audit (if function is L3, L2_L3, or role is Core/Distribution/Spine/Leaf/Edge)
            if func in [DeviceFunction.L3, DeviceFunction.L2_L3] or role in [DeviceRole.CORE, DeviceRole.DISTRIBUTION, DeviceRole.SPINE, DeviceRole.LEAF, DeviceRole.EDGE]:
                all_results.extend(L3AuditModule.audit(dev, cfg, state.topology_links, state.devices, parsed_configs))

            # L2 Audit (if function is L2, L2_L3, or role is Access/Distribution/Leaf)
            if func in [DeviceFunction.L2, DeviceFunction.L2_L3] or role in [DeviceRole.ACCESS, DeviceRole.DISTRIBUTION, DeviceRole.LEAF]:
                all_results.extend(L2AuditModule.audit(dev, cfg, state.topology_links, state.devices, parsed_configs))

            # Wireless AP Audit
            if func == DeviceFunction.WIRELESS_AP or role == DeviceRole.WIRELESS_AP:
                all_results.extend(WirelessAuditModule.audit(dev, cfg, state.topology_links, state.devices, parsed_configs))

            # Firewall Audit
            if func == DeviceFunction.FIREWALL or role == DeviceRole.FIREWALL:
                all_results.extend(FirewallAuditModule.audit(dev, cfg, state.topology_links, state.devices, parsed_configs))

            # Edge / WAN Audit
            if func == DeviceFunction.EDGE_WAN or role == DeviceRole.EDGE:
                all_results.extend(EdgeWANAuditModule.audit(dev, cfg, state.topology_links, state.devices, parsed_configs))

            # Connectivity & Port-Channel Audit (All Devices)
            all_results.extend(ConnectivityAuditModule.audit(dev, state.topology_links, state.port_channels, cmd_out, cfg))

        # Add Link Validation Issues directly to findings
        for issue in state.validation_issues:
            all_results.append(AuditCheckResult(
                id=f"AUD-TOPO-{issue.source_device}-{issue.rule.replace(' ', '_')}",
                device=issue.source_device,
                role=next((d.device_role.value for d in state.devices if d.hostname == issue.source_device), "Network Node"),
                category="Topology & Link Integrity",
                check=issue.rule,
                expected="Clean bidirectional port connectivity with zero link errors",
                actual=issue.message,
                status=AuditStatus.FAIL if issue.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH] else AuditStatus.WARNING,
                severity=issue.severity,
                evidence="Page 2 Topology Validation Engine",
                recommendation=issue.remediation,
                timestamp=now_str
            ))

        # Update timestamps
        for r in all_results:
            if not r.timestamp:
                r.timestamp = now_str

        state.audit_results = all_results

        # 4. Synchronize Stage 3: Device Audit Tasks via Protocol Catalog Engine
        # Preserve user-updated statuses/notes from existing tasks
        all_audit_tasks = []
        active_hostnames = {d.hostname for d in state.devices}
        for dev in state.devices:
            cfg = parsed_configs.get(dev.hostname, {})
            existing_for_dev = [t for t in state.device_audit_tasks if t.device_hostname == dev.hostname]
            tasks = ProtocolCatalogEngine.generate_audit_tasks(
                device=dev,
                config=cfg,
                links=state.topology_links,
                existing_tasks=existing_for_dev
            )
            all_audit_tasks.extend(tasks)
        state.device_audit_tasks = all_audit_tasks

        # 5. Compute Health Score & Domain Summary Metrics
        score, overall_risk = SeverityEngine.calculate_health_score(all_results)
        
        pass_cnt = sum(1 for r in all_results if r.status == AuditStatus.PASS)
        fail_cnt = sum(1 for r in all_results if r.status == AuditStatus.FAIL)
        warn_cnt = sum(1 for r in all_results if r.status == AuditStatus.WARNING)
        na_cnt = sum(1 for r in all_results if r.status == AuditStatus.NOT_APPLICABLE)

        # Task completion metrics
        total_tasks = len(state.device_audit_tasks)
        completed_tasks = sum(1 for t in state.device_audit_tasks if t.status in [
            TaskVerificationStatus.COMPLETED, TaskVerificationStatus.NOT_APPLICABLE, TaskVerificationStatus.WARNING
        ])
        incomplete_tasks = total_tasks - completed_tasks

        # Domain coverage
        domains = ["L3 & Routing", "L2 & Switching", "Topology & Links", "Wireless RF", "Firewall & Security", "Connectivity"]
        coverage = {}
        for d in domains:
            d_results = [r for r in all_results if any(k.lower() in r.category.lower() for k in d.split(" & "))]
            if not d_results:
                coverage[d] = "NOT ASSESSED"
            elif any(r.status == AuditStatus.FAIL for r in d_results):
                coverage[d] = "FAIL"
            elif any(r.status == AuditStatus.WARNING for r in d_results):
                coverage[d] = "WARNING"
            else:
                coverage[d] = "PASS"

        state.summary = AuditSummaryMetrics(
            client_name=state.project_name,
            audit_date=now_str,
            total_devices=len(state.devices),
            total_links=len(state.topology_links),
            total_port_channels=len(state.port_channels),
            health_score=score,
            overall_risk=overall_risk,
            total_checks=len(all_results),
            passed_checks=pass_cnt,
            failed_checks=fail_cnt,
            warning_checks=warn_cnt,
            na_checks=na_cnt,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            incomplete_tasks=incomplete_tasks,
            domain_coverage=coverage
        )

        return state
