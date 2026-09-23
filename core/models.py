"""
Pydantic Data Models for Network Infrastructure Audit Application.
Maintains a single source of truth across Inventory, Topology, and Audit stages.
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from core.constants import (
    DeviceFunction, DeviceRole, AuditStatus, SeverityLevel, LifecycleStatus, PortSpeed, PortType, TaskVerificationStatus
)

class DeviceModel(BaseModel):
    device_id: str
    hostname: str
    company_name: str = "Enterprise Org"
    vendor: str = "Cisco"
    device_model: str = "Catalyst 9300"
    os_version: str = "IOS-XE 17.9"
    device_function: DeviceFunction = DeviceFunction.L2_L3
    device_role: DeviceRole = DeviceRole.ACCESS
    num_ports: int = 24
    port_type: str = PortType.GIGABIT_ETHERNET.value
    port_speed: str = PortSpeed.SPEED_1G.value
    management_ip: str = "192.168.1.1"
    site_location: str = "HQ Data Center"
    serial_number: str = "SN-100001"
    lifecycle_status: LifecycleStatus = LifecycleStatus.ACTIVE
    ports: List[str] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if not self.ports:
            # Generate default ports dynamically based on Vendor Catalog
            from engine.catalog_manager import CatalogManager
            prefix = CatalogManager.get_vendor_port_prefix(self.vendor)
            self.ports = [f"{prefix}{i}" for i in range(1, self.num_ports + 1)]

class TopologyLink(BaseModel):
    id: str
    source_device: str
    source_port: str
    target_device: str
    target_port: str
    link_speed: str = PortSpeed.SPEED_10G.value
    port_channel_id: Optional[str] = None
    status: str = "Valid"

class PortChannelGroup(BaseModel):
    id: str  # e.g., Po10
    source_device: str
    target_device: str
    source_member_ports: List[str] = Field(default_factory=list)
    target_member_ports: List[str] = Field(default_factory=list)
    protocol: str = "LACP"
    status: str = "Operational"

class LinkValidationIssue(BaseModel):
    rule: str
    severity: SeverityLevel
    source_device: str
    source_port: Optional[str] = None
    target_device: Optional[str] = None
    target_port: Optional[str] = None
    message: str
    remediation: str

class DeviceAuditTask(BaseModel):
    id: str
    device_hostname: str
    device_role: str
    protocol: str  # e.g., "CDP", "OSPF", "VLAN", "STP", "Interfaces", etc.
    category: str  # e.g., "Layer 2 Switching", "Layer 3 Routing", "Security"
    title: str  # e.g., "CDP Neighbor Consistency & Verification"
    description: str
    condition: str = "Always Applicable"
    verification_command: str  # vendor specific show command e.g. "show cdp neighbors detail"
    status: TaskVerificationStatus = TaskVerificationStatus.INCOMPLETE
    actual_output: str = ""
    evidence_notes: str = ""
    severity: SeverityLevel = SeverityLevel.MEDIUM
    timestamp: str = ""

class AuditCheckResult(BaseModel):
    id: str
    device: str
    role: str
    category: str
    check: str
    expected: str
    actual: str
    status: AuditStatus
    severity: SeverityLevel
    evidence: str
    recommendation: str
    timestamp: str = ""

class AuditSummaryMetrics(BaseModel):
    client_name: str = "Enterprise Network Design"
    audit_date: str = ""
    total_devices: int = 0
    total_links: int = 0
    total_port_channels: int = 0
    health_score: int = 100
    overall_risk: SeverityLevel = SeverityLevel.LOW
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0
    na_checks: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    incomplete_tasks: int = 0
    domain_coverage: Dict[str, str] = Field(default_factory=dict)

class NetworkProjectState(BaseModel):
    project_name: str = "Enterprise Infrastructure Audit"
    company_name: str = "Enterprise Org"
    site_location: str = "HQ Data Center"
    devices: List[DeviceModel] = Field(default_factory=list)
    topology_links: List[TopologyLink] = Field(default_factory=list)
    port_channels: List[PortChannelGroup] = Field(default_factory=list)
    validation_issues: List[LinkValidationIssue] = Field(default_factory=list)
    device_audit_tasks: List[DeviceAuditTask] = Field(default_factory=list)
    audit_results: List[AuditCheckResult] = Field(default_factory=list)
    summary: Optional[AuditSummaryMetrics] = None
    raw_configs: Dict[str, str] = Field(default_factory=dict)  # hostname -> config content
    operational_logs: Dict[str, str] = Field(default_factory=dict)  # hostname -> show output
