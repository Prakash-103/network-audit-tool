"""
FastAPI Server for Enterprise Network Infrastructure Audit Application.
Maintains Single Source of Truth across Inventory, Topology, and Dynamic Audit Engine.
"""
import io
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request, HTTPException, Query, File, UploadFile
from fastapi.responses import HTMLResponse, FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.models import (
    NetworkProjectState, DeviceModel, TopologyLink, PortChannelGroup, LinkValidationIssue, DeviceAuditTask
)
from core.constants import DeviceFunction, DeviceRole, PortSpeed, LifecycleStatus, SeverityLevel, AuditStatus, TaskVerificationStatus
from engine.topology_engine import TopologyEngine
from engine.audit_orchestrator import AuditOrchestrator
from engine.catalog_manager import CatalogManager
from reporting.excel_generator import ExcelWorkbookGenerator, ExcelWorkbookImporter
from reporting.executive_report import ExecutiveReportGenerator
from engine.audit_normalizer import AuditNormalizer

from core.collector.models import Stage3TriggerRequest, Stage3RetryTaskRequest, EphemeralCredentials
from core.collector.audit_trigger_runner import AuditTriggerRunner

app = FastAPI(title="Enterprise Network Infrastructure Audit Application", version="3.0")


BASE_DIR = Path(__file__).resolve().parent
if not (BASE_DIR / "templates").exists() and (BASE_DIR.parent / "templates").exists():
    BASE_DIR = BASE_DIR.parent

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Global In-Memory Single Source of Truth
project_state = NetworkProjectState(project_name="zenquix - BLRCC002 Audit")

def get_enterprise_preset() -> NetworkProjectState:
    excel_path = BASE_DIR / "zenquix_BLRCC002_Audit_Evidence.xlsx"
    if not excel_path.exists() and (BASE_DIR.parent / "zenquix_BLRCC002_Audit_Evidence.xlsx").exists():
        excel_path = BASE_DIR.parent / "zenquix_BLRCC002_Audit_Evidence.xlsx"

    if excel_path.exists():
        try:
            with open(excel_path, "rb") as f:
                content = f.read()
            parsed_state = ExcelWorkbookImporter.parse_workbook(content)
            return AuditOrchestrator.run_full_audit(parsed_state)
        except Exception as e:
            print(f"Warning: Failed to load {excel_path}: {e}")

    # Indestructible embedded preset with all 12 devices, 25 links, and 5 port channels
    preset_devices = [
        DeviceModel(
            device_id="DEV-1", hostname="FW-01", company_name="zenquix", vendor="Palo Alto",
            device_model="paloalto", os_version="PAN-OS 10.2", device_function=DeviceFunction.FIREWALL,
            device_role=DeviceRole.FIREWALL, num_ports=24, port_type="GigabitEthernet",
            port_speed=PortSpeed.SPEED_100G.value, management_ip="10.254.1.10", site_location="BLRCC002",
            serial_number="SN-9823412", lifecycle_status=LifecycleStatus.ACTIVE
        ),
        DeviceModel(
            device_id="DEV-2", hostname="FW-02", company_name="zenquix", vendor="Palo Alto",
            device_model="paloalto", os_version="PAN-OS 10.2", device_function=DeviceFunction.FIREWALL,
            device_role=DeviceRole.FIREWALL, num_ports=24, port_type="GigabitEthernet",
            port_speed=PortSpeed.SPEED_100G.value, management_ip="10.254.1.11", site_location="BLRCC002",
            serial_number="SN-9823413", lifecycle_status=LifecycleStatus.ACTIVE
        ),
        DeviceModel(
            device_id="DEV-3", hostname="CORE-01", company_name="zenquix", vendor="Cisco",
            device_model="Catalyst 9300", os_version="IOS-XE 17.9", device_function=DeviceFunction.L2_L3,
            device_role=DeviceRole.CORE, num_ports=48, port_type="GigabitEthernet",
            port_speed=PortSpeed.SPEED_100G.value, management_ip="10.254.1.12", site_location="BLRCC002",
            serial_number="SN-9823414", lifecycle_status=LifecycleStatus.EOL
        ),
        DeviceModel(
            device_id="DEV-4", hostname="CORE-02", company_name="zenquix", vendor="Cisco",
            device_model="Catalyst 9300", os_version="IOS-XE 17.9", device_function=DeviceFunction.L2_L3,
            device_role=DeviceRole.CORE, num_ports=48, port_type="GigabitEthernet",
            port_speed=PortSpeed.SPEED_100G.value, management_ip="10.254.1.13", site_location="BLRCC002",
            serial_number="SN-9823415", lifecycle_status=LifecycleStatus.EOL
        ),
        DeviceModel(
            device_id="DEV-5", hostname="ACC-01", company_name="zenquix", vendor="Cisco",
            device_model="Catalyst 9300", os_version="IOS-XE 17.9.4a", device_function=DeviceFunction.L2,
            device_role=DeviceRole.ACCESS, num_ports=24, port_type="GigabitEthernet",
            port_speed=PortSpeed.SPEED_10G.value, management_ip="10.254.1.14", site_location="BLRCC002",
            serial_number="SN-9823416", lifecycle_status=LifecycleStatus.ACTIVE
        ),
        DeviceModel(
            device_id="DEV-6", hostname="ACC-02", company_name="zenquix", vendor="Cisco",
            device_model="Catalyst 9300", os_version="IOS-XE 17.9.4a", device_function=DeviceFunction.L2,
            device_role=DeviceRole.ACCESS, num_ports=24, port_type="GigabitEthernet",
            port_speed=PortSpeed.SPEED_10G.value, management_ip="10.254.1.15", site_location="BLRCC002",
            serial_number="SN-9823417", lifecycle_status=LifecycleStatus.ACTIVE
        ),
        DeviceModel(
            device_id="DEV-7", hostname="ACC-03", company_name="zenquix", vendor="Cisco",
            device_model="Catalyst 9300", os_version="IOS-XE 17.9.4a", device_function=DeviceFunction.L2,
            device_role=DeviceRole.ACCESS, num_ports=24, port_type="GigabitEthernet",
            port_speed=PortSpeed.SPEED_10G.value, management_ip="10.254.1.16", site_location="BLRCC002",
            serial_number="SN-9823418", lifecycle_status=LifecycleStatus.ACTIVE
        ),
        DeviceModel(
            device_id="DEV-8", hostname="ACC-04", company_name="zenquix", vendor="Cisco",
            device_model="Catalyst 9300", os_version="IOS-XE 17.9.4a", device_function=DeviceFunction.L2,
            device_role=DeviceRole.ACCESS, num_ports=24, port_type="GigabitEthernet",
            port_speed=PortSpeed.SPEED_10G.value, management_ip="10.254.1.17", site_location="BLRCC002",
            serial_number="SN-9823419", lifecycle_status=LifecycleStatus.ACTIVE
        ),
        DeviceModel(
            device_id="DEV-9", hostname="AP-01", company_name="zenquix", vendor="Aruba",
            device_model="aruba", os_version="ArubaOS 10.6.0.2", device_function=DeviceFunction.WIRELESS_AP,
            device_role=DeviceRole.WIRELESS_AP, num_ports=2, port_type="GigabitEthernet",
            port_speed=PortSpeed.SPEED_10G.value, management_ip="10.254.1.18", site_location="BLRCC002",
            serial_number="SN-9823420", lifecycle_status=LifecycleStatus.ACTIVE
        ),
        DeviceModel(
            device_id="DEV-10", hostname="AP-02", company_name="zenquix", vendor="Aruba",
            device_model="aruba", os_version="ArubaOS 10.6.0.2", device_function=DeviceFunction.WIRELESS_AP,
            device_role=DeviceRole.WIRELESS_AP, num_ports=2, port_type="GigabitEthernet",
            port_speed=PortSpeed.SPEED_10G.value, management_ip="10.254.1.19", site_location="BLRCC002",
            serial_number="SN-9823421", lifecycle_status=LifecycleStatus.ACTIVE
        ),
        DeviceModel(
            device_id="DEV-11", hostname="AP-03", company_name="zenquix", vendor="Aruba",
            device_model="aruba", os_version="ArubaOS 10.6.0.2", device_function=DeviceFunction.WIRELESS_AP,
            device_role=DeviceRole.WIRELESS_AP, num_ports=2, port_type="GigabitEthernet",
            port_speed=PortSpeed.SPEED_10G.value, management_ip="10.254.1.20", site_location="BLRCC002",
            serial_number="SN-9823422", lifecycle_status=LifecycleStatus.ACTIVE
        ),
        DeviceModel(
            device_id="DEV-12", hostname="AP-04", company_name="zenquix", vendor="Aruba",
            device_model="aruba", os_version="ArubaOS 10.6.0.2", device_function=DeviceFunction.WIRELESS_AP,
            device_role=DeviceRole.WIRELESS_AP, num_ports=2, port_type="GigabitEthernet",
            port_speed=PortSpeed.SPEED_10G.value, management_ip="10.254.1.21", site_location="BLRCC002",
            serial_number="SN-9823423", lifecycle_status=LifecycleStatus.ACTIVE
        )
    ]

    preset_links = [
        TopologyLink(id="FW-01_Port1___FW-02_Port1", source_device="FW-01", source_port="Port1", target_device="FW-02", target_port="Port1", link_speed="40G", port_channel_id="Po10"),
        TopologyLink(id="FW-01_Port2___FW-02_Port2", source_device="FW-01", source_port="Port2", target_device="FW-02", target_port="Port2", link_speed="40G", port_channel_id="Po10"),
        TopologyLink(id="FW-01_Port3___CORE-01_GigabitEthernet1/0/1", source_device="FW-01", source_port="Port3", target_device="CORE-01", target_port="GigabitEthernet1/0/1", link_speed="40G", port_channel_id="Po11"),
        TopologyLink(id="FW-01_Port4___CORE-01_GigabitEthernet1/0/2", source_device="FW-01", source_port="Port4", target_device="CORE-01", target_port="GigabitEthernet1/0/2", link_speed="40G", port_channel_id="Po11"),
        TopologyLink(id="FW-01_Port5___CORE-02_GigabitEthernet1/0/1", source_device="FW-01", source_port="Port5", target_device="CORE-02", target_port="GigabitEthernet1/0/1", link_speed="40G", port_channel_id="Po12"),
        TopologyLink(id="FW-01_Port6___CORE-02_GigabitEthernet1/0/2", source_device="FW-01", source_port="Port6", target_device="CORE-02", target_port="GigabitEthernet1/0/2", link_speed="40G", port_channel_id="Po12"),
        TopologyLink(id="FW-02_Port3___CORE-01_GigabitEthernet1/0/3", source_device="FW-02", source_port="Port3", target_device="CORE-01", target_port="GigabitEthernet1/0/3", link_speed="40G", port_channel_id="Po13"),
        TopologyLink(id="FW-02_Port4___CORE-01_GigabitEthernet1/0/4", source_device="FW-02", source_port="Port4", target_device="CORE-01", target_port="GigabitEthernet1/0/4", link_speed="40G", port_channel_id="Po13"),
        TopologyLink(id="FW-02_Port5___CORE-02_GigabitEthernet1/0/3", source_device="FW-02", source_port="Port5", target_device="CORE-02", target_port="GigabitEthernet1/0/3", link_speed="40G", port_channel_id="Po14"),
        TopologyLink(id="FW-02_Port6___CORE-02_GigabitEthernet1/0/4", source_device="FW-02", source_port="Port6", target_device="CORE-02", target_port="GigabitEthernet1/0/4", link_speed="40G", port_channel_id="Po14"),
        TopologyLink(id="CORE-01_GigabitEthernet1/0/5___ACC-01_GigabitEthernet1/0/1", source_device="CORE-01", source_port="GigabitEthernet1/0/5", target_device="ACC-01", target_port="GigabitEthernet1/0/1", link_speed="10G"),
        TopologyLink(id="CORE-01_GigabitEthernet1/0/6___ACC-02_GigabitEthernet1/0/1", source_device="CORE-01", source_port="GigabitEthernet1/0/6", target_device="ACC-02", target_port="GigabitEthernet1/0/1", link_speed="10G"),
        TopologyLink(id="CORE-01_GigabitEthernet1/0/7___ACC-03_GigabitEthernet1/0/1", source_device="CORE-01", source_port="GigabitEthernet1/0/7", target_device="ACC-03", target_port="GigabitEthernet1/0/1", link_speed="10G"),
        TopologyLink(id="CORE-01_GigabitEthernet1/0/8___ACC-04_GigabitEthernet1/0/1", source_device="CORE-01", source_port="GigabitEthernet1/0/8", target_device="ACC-04", target_port="GigabitEthernet1/0/1", link_speed="10G"),
        TopologyLink(id="CORE-02_GigabitEthernet1/0/5___ACC-01_GigabitEthernet1/0/2", source_device="CORE-02", source_port="GigabitEthernet1/0/5", target_device="ACC-01", target_port="GigabitEthernet1/0/2", link_speed="10G"),
        TopologyLink(id="CORE-02_GigabitEthernet1/0/6___ACC-02_GigabitEthernet1/0/2", source_device="CORE-02", source_port="GigabitEthernet1/0/6", target_device="ACC-02", target_port="GigabitEthernet1/0/2", link_speed="10G"),
        TopologyLink(id="CORE-02_GigabitEthernet1/0/7___ACC-03_GigabitEthernet1/0/2", source_device="CORE-02", source_port="GigabitEthernet1/0/7", target_device="ACC-03", target_port="GigabitEthernet1/0/2", link_speed="10G"),
        TopologyLink(id="CORE-02_GigabitEthernet1/0/8___ACC-04_GigabitEthernet1/0/2", source_device="CORE-02", source_port="GigabitEthernet1/0/8", target_device="ACC-04", target_port="GigabitEthernet1/0/2", link_speed="10G"),
        TopologyLink(id="ACC-01_GigabitEthernet1/0/3___AP-01_Port1", source_device="ACC-01", source_port="GigabitEthernet1/0/3", target_device="AP-01", target_port="Port1", link_speed="10G"),
        TopologyLink(id="ACC-02_GigabitEthernet1/0/3___AP-02_Port1", source_device="ACC-02", source_port="GigabitEthernet1/0/3", target_device="AP-02", target_port="Port1", link_speed="10G"),
        TopologyLink(id="ACC-02_GigabitEthernet1/0/4___AP-01_Port2", source_device="ACC-02", source_port="GigabitEthernet1/0/4", target_device="AP-01", target_port="Port2", link_speed="10G"),
        TopologyLink(id="ACC-03_GigabitEthernet1/0/3___AP-03_Port1", source_device="ACC-03", source_port="GigabitEthernet1/0/3", target_device="AP-03", target_port="Port1", link_speed="10G"),
        TopologyLink(id="ACC-03_GigabitEthernet1/0/4___AP-04_Port1", source_device="ACC-03", source_port="GigabitEthernet1/0/4", target_device="AP-04", target_port="Port1", link_speed="10G"),
        TopologyLink(id="ACC-04_GigabitEthernet1/0/3___AP-03_Port2", source_device="ACC-04", source_port="GigabitEthernet1/0/3", target_device="AP-03", target_port="Port2", link_speed="10G"),
        TopologyLink(id="ACC-04_GigabitEthernet1/0/4___AP-04_Port2", source_device="ACC-04", source_port="GigabitEthernet1/0/4", target_device="AP-04", target_port="Port2", link_speed="10G")
    ]

    preset_pos = [
        PortChannelGroup(id="Po10", source_device="FW-01", target_device="FW-02", source_member_ports=["Port1", "Port2"], target_member_ports=["Port1", "Port2"], protocol="LACP", status="Operational"),
        PortChannelGroup(id="Po11", source_device="FW-01", target_device="CORE-01", source_member_ports=["Port3", "Port4"], target_member_ports=["GigabitEthernet1/0/1", "GigabitEthernet1/0/2"], protocol="LACP", status="Operational"),
        PortChannelGroup(id="Po12", source_device="FW-01", target_device="CORE-02", source_member_ports=["Port5", "Port6"], target_member_ports=["GigabitEthernet1/0/1", "GigabitEthernet1/0/2"], protocol="LACP", status="Operational"),
        PortChannelGroup(id="Po13", source_device="FW-02", target_device="CORE-01", source_member_ports=["Port3", "Port4"], target_member_ports=["GigabitEthernet1/0/3", "GigabitEthernet1/0/4"], protocol="LACP", status="Operational"),
        PortChannelGroup(id="Po14", source_device="FW-02", target_device="CORE-02", source_member_ports=["Port5", "Port6"], target_member_ports=["GigabitEthernet1/0/3", "GigabitEthernet1/0/4"], protocol="LACP", status="Operational")
    ]

    state = NetworkProjectState(
        project_name="zenquix - BLRCC002 Audit",
        company_name="zenquix",
        site_location="BLRCC002",
        devices=preset_devices,
        topology_links=preset_links,
        port_channels=preset_pos
    )
    return AuditOrchestrator.run_full_audit(state)

# Initialize project with default enterprise preset
project_state = get_enterprise_preset()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/state")
async def get_state():
    global project_state
    return project_state

@app.get("/api/presets/enterprise")
async def load_enterprise_preset():
    global project_state
    project_state = get_enterprise_preset()
    return project_state

@app.post("/api/devices")
async def add_device(device: DeviceModel):
    global project_state
    # Uniqueness validations
    if any(d.device_id.lower() == device.device_id.lower() for d in project_state.devices):
        raise HTTPException(status_code=400, detail=f"Device ID '{device.device_id}' already exists. Please use a unique Device ID.")
    
    if any(d.hostname.lower() == device.hostname.lower() for d in project_state.devices):
        raise HTTPException(status_code=400, detail=f"Hostname '{device.hostname}' already exists. Hostnames must be unique.")

    if any(d.management_ip.strip() == device.management_ip.strip() for d in project_state.devices):
        existing_dev = next(d for d in project_state.devices if d.management_ip.strip() == device.management_ip.strip())
        raise HTTPException(status_code=400, detail=f"Management IP '{device.management_ip}' is already assigned to {existing_dev.hostname} ({existing_dev.device_id}). IP addresses must be unique.")

    if any(d.serial_number.strip().lower() == device.serial_number.strip().lower() for d in project_state.devices):
        existing_dev = next(d for d in project_state.devices if d.serial_number.strip().lower() == device.serial_number.strip().lower())
        raise HTTPException(status_code=400, detail=f"Serial Number '{device.serial_number}' is already assigned to {existing_dev.hostname} ({existing_dev.device_id}). Serial numbers must be unique.")

    project_state.devices.append(device)
    project_state = AuditOrchestrator.run_full_audit(project_state)
    return project_state

@app.put("/api/devices/{device_id}")
async def update_device(device_id: str, device: DeviceModel):
    global project_state
    idx = next((i for i, d in enumerate(project_state.devices) if d.device_id == device_id or d.hostname == device_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Check uniqueness excluding self
    other_devices = [d for i, d in enumerate(project_state.devices) if i != idx]

    if any(d.device_id.lower() == device.device_id.lower() for d in other_devices):
        raise HTTPException(status_code=400, detail=f"Device ID '{device.device_id}' already exists.")

    if any(d.hostname.lower() == device.hostname.lower() for d in other_devices):
        raise HTTPException(status_code=400, detail=f"Hostname '{device.hostname}' already exists. Hostnames must be unique.")

    if any(d.management_ip.strip() == device.management_ip.strip() for d in other_devices):
        existing_dev = next(d for d in other_devices if d.management_ip.strip() == device.management_ip.strip())
        raise HTTPException(status_code=400, detail=f"Management IP '{device.management_ip}' is already assigned to {existing_dev.hostname}. IP addresses must be unique.")

    if any(d.serial_number.strip().lower() == device.serial_number.strip().lower() for d in other_devices):
        existing_dev = next(d for d in other_devices if d.serial_number.strip().lower() == device.serial_number.strip().lower())
        raise HTTPException(status_code=400, detail=f"Serial Number '{device.serial_number}' is already assigned to {existing_dev.hostname}. Serial numbers must be unique.")

    old_hostname = project_state.devices[idx].hostname
    project_state.devices[idx] = device

    # If hostname changed, update topology links, port-channels, configs, and logs
    if old_hostname != device.hostname:
        for l in project_state.topology_links:
            if l.source_device == old_hostname:
                l.source_device = device.hostname
            if l.target_device == old_hostname:
                l.target_device = device.hostname

        for po in project_state.port_channels:
            if po.source_device == old_hostname:
                po.source_device = device.hostname
            if po.target_device == old_hostname:
                po.target_device = device.hostname

        if old_hostname in project_state.raw_configs:
            project_state.raw_configs[device.hostname] = project_state.raw_configs.pop(old_hostname)
        if old_hostname in project_state.operational_logs:
            project_state.operational_logs[device.hostname] = project_state.operational_logs.pop(old_hostname)

    project_state = AuditOrchestrator.run_full_audit(project_state)
    return project_state

@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: str):
    global project_state
    target_dev = next((d for d in project_state.devices if d.device_id == device_id or d.hostname == device_id), None)
    if not target_dev:
        raise HTTPException(status_code=404, detail="Device not found")

    host = target_dev.hostname
    # Remove device
    project_state.devices = [d for d in project_state.devices if d.device_id != device_id and d.hostname != host]
    # Remove associated links
    project_state.topology_links = [l for l in project_state.topology_links if l.source_device != host and l.target_device != host]
    # Remove associated port-channels
    project_state.port_channels = [po for po in project_state.port_channels if po.source_device != host and po.target_device != host]
    # Remove configs and operational logs
    project_state.raw_configs.pop(host, None)
    project_state.operational_logs.pop(host, None)
    
    project_state = AuditOrchestrator.run_full_audit(project_state)
    return project_state

class ConfigLogsRequest(BaseModel):
    raw_config: str = ""
    operational_logs: str = ""

@app.get("/api/devices/{device_id}/config_logs")
async def get_device_config_logs(device_id: str):
    global project_state
    dev = next((d for d in project_state.devices if d.device_id == device_id or d.hostname == device_id), None)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return {
        "device_id": dev.device_id,
        "hostname": dev.hostname,
        "raw_config": project_state.raw_configs.get(dev.hostname, ""),
        "operational_logs": project_state.operational_logs.get(dev.hostname, "")
    }

@app.post("/api/devices/{device_id}/config_logs")
async def update_device_config_logs(device_id: str, req: ConfigLogsRequest):
    global project_state
    dev = next((d for d in project_state.devices if d.device_id == device_id or d.hostname == device_id), None)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    
    project_state.raw_configs[dev.hostname] = req.raw_config
    project_state.operational_logs[dev.hostname] = req.operational_logs
    project_state = AuditOrchestrator.run_full_audit(project_state)
    return project_state

class PortChannelEditRequest(BaseModel):
    id: str
    source_device: str
    target_device: str
    source_member_ports: list[str]
    target_member_ports: list[str]
    protocol: str = "LACP"
    status: str = "Operational"

@app.put("/api/topology/portchannel/{po_id}")
async def update_port_channel(po_id: str, req: PortChannelEditRequest):
    global project_state
    idx = next((i for i, po in enumerate(project_state.port_channels) if po.id == po_id), None)
    if idx is None:
        po_group = PortChannelGroup(
            id=req.id,
            source_device=req.source_device,
            target_device=req.target_device,
            source_member_ports=req.source_member_ports,
            target_member_ports=req.target_member_ports,
            protocol=req.protocol,
            status=req.status
        )
        project_state.port_channels.append(po_group)
    else:
        project_state.port_channels[idx].source_member_ports = req.source_member_ports
        project_state.port_channels[idx].target_member_ports = req.target_member_ports
        project_state.port_channels[idx].protocol = req.protocol
        project_state.port_channels[idx].status = req.status

    project_state = AuditOrchestrator.run_full_audit(project_state)
    return project_state

@app.delete("/api/topology/portchannel/{po_id}")
async def delete_port_channel(po_id: str):
    global project_state
    # Remove port-channel assignment from links
    for l in project_state.topology_links:
        if l.port_channel_id == po_id:
            l.port_channel_id = None
            
    # Delete port-channel group
    project_state.port_channels = [po for po in project_state.port_channels if po.id != po_id]
    project_state = AuditOrchestrator.run_full_audit(project_state)
    return project_state

class LinkRequest(BaseModel):
    source_device: str
    source_port: Optional[str] = None
    source_ports: Optional[list[str]] = None
    target_device: str
    target_port: Optional[str] = None
    target_ports: Optional[list[str]] = None
    link_speed: str = PortSpeed.SPEED_10G.value
    port_channel_id: Optional[str] = None

@app.post("/api/topology/link")
async def add_link(req: LinkRequest):
    global project_state
    
    # Resolve source and target port lists
    src_ports = req.source_ports if req.source_ports is not None else ([req.source_port] if req.source_port else [])
    tgt_ports = req.target_ports if req.target_ports is not None else ([req.target_port] if req.target_port else [])

    if len(src_ports) == 0 or len(tgt_ports) == 0:
        raise HTTPException(status_code=400, detail="Source and Target ports must be selected.")
    if len(src_ports) != len(tgt_ports):
        raise HTTPException(
            status_code=400,
            detail=f"Source ports count ({len(src_ports)}) must match target ports count ({len(tgt_ports)}) for 1-to-1 connection mapping."
        )

    for sp, tp in zip(src_ports, tgt_ports):
        project_state.topology_links = TopologyEngine.add_bidirectional_link(
            links=project_state.topology_links,
            source_device=req.source_device,
            source_port=sp,
            target_device=req.target_device,
            target_port=tp,
            link_speed=req.link_speed,
            port_channel_id=req.port_channel_id
        )

    # If Port-Channel specified, update port channels table
    if req.port_channel_id:
        po_group = next((po for po in project_state.port_channels if po.id == req.port_channel_id), None)
        if not po_group:
            po_group = PortChannelGroup(
                id=req.port_channel_id,
                source_device=req.source_device,
                target_device=req.target_device,
                source_member_ports=list(src_ports),
                target_member_ports=list(tgt_ports),
                protocol="LACP",
                status="Operational"
            )
            project_state.port_channels.append(po_group)
        else:
            for sp in src_ports:
                if sp not in po_group.source_member_ports:
                    po_group.source_member_ports.append(sp)
            for tp in tgt_ports:
                if tp not in po_group.target_member_ports:
                    po_group.target_member_ports.append(tp)

    project_state = AuditOrchestrator.run_full_audit(project_state)
    return project_state

@app.delete("/api/topology/link")
async def delete_link(link_id: str = Query(...)):
    global project_state
    project_state.topology_links = TopologyEngine.remove_bidirectional_link(project_state.topology_links, link_id)
    project_state = AuditOrchestrator.run_full_audit(project_state)
    return project_state

@app.get("/api/topology/validate")
async def validate_topology():
    global project_state
    issues = TopologyEngine.validate_topology(
        devices=project_state.devices,
        links=project_state.topology_links,
        port_channels=project_state.port_channels
    )
    project_state.validation_issues = issues
    return {"issues": issues}

@app.post("/api/audit/run")
async def run_audit(target_device: Optional[str] = None):
    global project_state
    project_state = AuditOrchestrator.run_full_audit(project_state, target_device)
    return project_state

class NewProjectRequest(BaseModel):
    company_name: str = "Enterprise Org"
    site_location: str = "HQ Data Center"
    project_name: str = "Enterprise Infrastructure Audit"

@app.post("/api/project/new")
async def create_new_project(req: NewProjectRequest):
    global project_state
    
    # Calculate corresponding workbook file name
    comp = (req.company_name or "Enterprise").strip()
    site = (req.site_location or "Site").strip()
    safe_comp = "".join(c if c.isalnum() else "_" for c in comp).strip("_")
    safe_site = "".join(c if c.isalnum() else "_" for c in site).strip("_")
    if not safe_comp:
        safe_comp = "Enterprise"
    if not safe_site:
        safe_site = "Site"
        
    target_filename = f"{safe_comp}_{safe_site}_Audit_Evidence.xlsx"
    target_path = BASE_DIR / target_filename
    
    # Check if a file with the same name already exists in workspace
    if target_path.exists():
        raise HTTPException(
            status_code=409,
            detail=f'A project file with the name "{target_filename}" already exists for {comp} ({site}). Please use a different company name or site location, or load the existing file.'
        )
    
    # Also check against current active project name if devices exist
    if project_state and project_state.devices:
        cur_comp = (project_state.company_name or "").strip().lower()
        cur_site = (project_state.site_location or "").strip().lower()
        if cur_comp == comp.lower() and cur_site == site.lower():
            raise HTTPException(
                status_code=409,
                detail=f'A project is already active for {comp} ({site}). Please specify a distinct company name or site location.'
            )

    state = NetworkProjectState(
        project_name=req.project_name,
        company_name=req.company_name,
        site_location=req.site_location,
        devices=[],
        topology_links=[],
        port_channels=[],
        raw_configs={},
        operational_logs={}
    )
    project_state = AuditOrchestrator.run_full_audit(state)
    return project_state

@app.get("/api/project/saved-files")
async def list_saved_files():
    """List all .xlsx workbook files in the project root directory as loadable past work."""
    import os
    from datetime import datetime as dt
    xlsx_files = []
    for f in sorted(BASE_DIR.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = f.stat()
        xlsx_files.append({
            "filename": f.name,
            "size_kb": round(stat.st_size / 1024, 1),
            "modified": dt.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return {"files": xlsx_files}

class LoadFileRequest(BaseModel):
    filename: str

@app.post("/api/project/load-file")
async def load_saved_file(req: LoadFileRequest):
    """Load a previously saved .xlsx workbook file by filename."""
    global project_state
    safe_name = Path(req.filename).name  # prevent path traversal
    file_path = BASE_DIR / safe_name
    if not file_path.exists() or not safe_name.endswith(".xlsx"):
        raise HTTPException(status_code=404, detail=f"File not found: {safe_name}")
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        imported_state = ExcelWorkbookImporter.parse_workbook(content)
        
        # If imported state doesn't have custom company/site but filename does (e.g., Company_Site_Audit_Evidence.xlsx)
        raw_name = safe_name.replace("_Audit_Evidence.xlsx", "").replace(".xlsx", "")
        parts = [p for p in raw_name.split("_") if p]
        if parts:
            if not imported_state.company_name or imported_state.company_name in ["Imported Infrastructure Audit", "Enterprise Org"]:
                imported_state.company_name = parts[0]
            if not imported_state.site_location or imported_state.site_location in ["HQ Data Center", "HQ DC"]:
                imported_state.site_location = parts[1] if len(parts) > 1 else parts[0]
            imported_state.project_name = f"{imported_state.company_name} - {imported_state.site_location} Audit"

        project_state = AuditOrchestrator.run_full_audit(imported_state)
        return project_state
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load file: {str(e)}")

def parse_client_state(payload: Optional[Dict[str, Any]] = None) -> NetworkProjectState:
    global project_state
    if not payload or not isinstance(payload, dict):
        return project_state
    try:
        return NetworkProjectState.model_validate(payload)
    except Exception:
        try:
            # Normalize devices and enums if needed
            dev_list = []
            for d in payload.get("devices", []):
                if isinstance(d, dict):
                    d_copy = dict(d)
                    df = str(d_copy.get("device_function", "L2"))
                    if "L3" in df and "L2" not in df:
                        d_copy["device_function"] = "L3"
                    elif "L2" in df and "L3" not in df:
                        d_copy["device_function"] = "L2"
                    elif "Firewall" in df or "FW" in df:
                        d_copy["device_function"] = "Firewall"
                    elif "AP" in df or "Wireless" in df:
                        d_copy["device_function"] = "Wireless AP"
                    elif "Edge" in df or "WAN" in df:
                        d_copy["device_function"] = "Edge/WAN"
                    dev_list.append(DeviceModel.model_validate(d_copy))
                elif isinstance(d, DeviceModel):
                    dev_list.append(d)

            link_list = [TopologyLink.model_validate(l) if isinstance(l, dict) else l for l in payload.get("topology_links", [])]
            po_list = [PortChannelGroup.model_validate(p) if isinstance(p, dict) else p for p in payload.get("port_channels", [])]
            task_list = [DeviceAuditTask.model_validate(t) if isinstance(t, dict) else t for t in payload.get("device_audit_tasks", [])]

            return NetworkProjectState(
                project_name=payload.get("project_name", "Enterprise Audit"),
                company_name=payload.get("company_name", "Enterprise"),
                site_location=payload.get("site_location", "HQ Data Center"),
                devices=dev_list,
                topology_links=link_list,
                port_channels=po_list,
                device_audit_tasks=task_list
            )
        except Exception:
            return project_state


def _generate_excel_response(payload: Optional[Dict[str, Any]] = None):
    global project_state
    target_state = parse_client_state(payload) if payload else project_state

    comp = (target_state.devices[0].company_name if (target_state.devices and target_state.devices[0].company_name) else target_state.company_name or "Enterprise").strip()
    site = (target_state.devices[0].site_location if (target_state.devices and target_state.devices[0].site_location) else target_state.site_location or "HQ_DC").strip()

    safe_comp = "".join(c if c.isalnum() else "_" for c in comp).strip("_")
    safe_site = "".join(c if c.isalnum() else "_" for c in site).strip("_")

    if not safe_comp:
        safe_comp = "Enterprise"
    if not safe_site:
        safe_site = "Site"

    download_filename = f"{safe_comp}_{safe_site}_Audit_Evidence.xlsx"

    buf = io.BytesIO()
    ExcelWorkbookGenerator.generate(target_state, buf)
    buf.seek(0)
    file_bytes = buf.getvalue()
    try:
        saved_file_path = BASE_DIR / download_filename
        with open(saved_file_path, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        print(f"Warning: could not save local copy to {download_filename}: {e}")

    return Response(
        content=file_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{download_filename}"'}
    )

@app.post("/api/export/excel")
async def export_excel_post(request: Request):
    """Export evidence workbook using the client's active state payload."""
    try:
        body = await request.json()
    except Exception:
        body = None
    return _generate_excel_response(body)

@app.get("/api/export/excel")
async def export_excel_get():
    """Export evidence workbook using the server's current state."""
    return _generate_excel_response(None)

@app.post("/api/import/excel")
async def import_excel(file: UploadFile = File(...)):
    """
    Import an entire 3-sheet Excel workbook (.xlsx), parse all devices, links, port-channels,
    and audit task states, and update the global project state.
    """
    global project_state
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a valid .xlsx Excel workbook.")

    try:
        content = await file.read()
        imported_state = ExcelWorkbookImporter.parse_workbook(content)
        
        # If imported state doesn't have custom company/site but filename does (e.g., Company_Site_Audit_Evidence.xlsx)
        raw_name = Path(file.filename).name.replace("_Audit_Evidence.xlsx", "").replace(".xlsx", "")
        parts = [p for p in raw_name.split("_") if p]
        if parts:
            if not imported_state.company_name or imported_state.company_name in ["Imported Infrastructure Audit", "Enterprise Org"]:
                imported_state.company_name = parts[0]
            if not imported_state.site_location or imported_state.site_location in ["HQ Data Center", "HQ DC"]:
                imported_state.site_location = parts[1] if len(parts) > 1 else parts[0]
            imported_state.project_name = f"{imported_state.company_name} - {imported_state.site_location} Audit"

        # Run full audit pipeline to sync protocol tasks and compute summary health metrics
        project_state = AuditOrchestrator.run_full_audit(imported_state)
        return project_state
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import Excel workbook: {str(e)}")

@app.get("/api/export/executive/html", response_class=HTMLResponse)
async def export_executive_html(request: Request, scope: str = "all", download: bool = False):
    global project_state
    metrics = ExecutiveReportGenerator.compile_executive_metrics(project_state, scope=scope)
    crit_findings = [r for r in project_state.audit_results if r.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH] and r.status in [AuditStatus.FAIL, AuditStatus.WARNING]]
    recs_p1 = [r for r in crit_findings if r.severity == SeverityLevel.CRITICAL]
    recs_p2 = [r for r in crit_findings if r.severity == SeverityLevel.HIGH]

    context = {
        "request": request,
        "state": project_state,
        "metrics": metrics,
        "crit_findings": crit_findings,
        "recs_p1": recs_p1,
        "recs_p2": recs_p2
    }

    if download:
        company = project_state.company_name or "Enterprise"
        site = project_state.site_location or "Network"
        filename = f"{company}_{site}_Executive_Report.html".replace(" ", "_")
        html_str = templates.get_template("executive_report.html").render(context)
        return Response(
            content=html_str,
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    return templates.TemplateResponse(request=request, name="executive_report.html", context=context)

@app.get("/api/export/executive/md")
async def export_executive_md(scope: str = "all", download: bool = False):
    global project_state
    md = ExecutiveReportGenerator.generate_markdown(project_state, scope=scope)
    headers = {}
    if download:
        company = project_state.company_name or "Enterprise"
        site = project_state.site_location or "Network"
        filename = f"{company}_{site}_Executive_Report.md".replace(" ", "_")
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return Response(content=md, media_type="text/markdown", headers=headers)

@app.get("/api/export/executive/md/preview", response_class=HTMLResponse)
async def export_executive_md_preview(request: Request, scope: str = "all"):
    """
    Rich interactive Markdown deliverable visualizer for the Enterprise Report modal.
    Serves full rendered document view + raw markdown source with copy & download controls.
    """
    global project_state
    md_text = ExecutiveReportGenerator.generate_markdown(project_state, scope=scope)
    company = project_state.company_name or "Enterprise"
    site = project_state.site_location or "Network"
    return templates.TemplateResponse(
        request=request,
        name="markdown_preview.html",
        context={
            "request": request,
            "md_text": md_text,
            "scope": scope,
            "company": company,
            "site": site,
            "char_count": len(md_text),
            "line_count": len(md_text.splitlines()),
            "word_count": len(md_text.split()),
        }
    )

@app.get("/api/export/executive/docx")
async def export_executive_docx(scope: str = "all"):
    """
    Download publication-grade Microsoft Word (.docx) Executive Audit Report
    with 1:1 mathematical data consistency via AuditNormalizer.
    """
    global project_state
    docx_io = ExecutiveReportGenerator.generate_docx(project_state, scope=scope)
    company = project_state.company_name or "Enterprise"
    site = project_state.site_location or "Network"
    filename = f"{company}_{site}_Executive_Report.docx".replace(" ", "_")
    return Response(
        content=docx_io.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.get("/api/export/executive/metrics")
async def get_executive_metrics(scope: str = "all"):
    global project_state
    return ExecutiveReportGenerator.compile_executive_metrics(project_state, scope=scope)

@app.get("/api/audit/normalized")
async def get_normalized_audit(scope: str = "all"):
    """Return the canonical Normalized Audit JSON representing the Single Source of Truth."""
    global project_state
    return AuditNormalizer.normalize_audit(project_state, scope=scope)


# ==========================================================================
#  STAGE 3: DEVICE AUDIT & PROTOCOL VERIFICATION API ENDPOINTS
# ==========================================================================

@app.get("/api/audit/device/{hostname}/tasks")
async def get_device_audit_tasks(hostname: str):
    """Return all audit tasks and protocol metadata for a specific device."""
    global project_state
    dev = next((d for d in project_state.devices if d.hostname == hostname), None)
    if not dev:
        raise HTTPException(status_code=404, detail=f"Device '{hostname}' not found in inventory")

    tasks = [t for t in project_state.device_audit_tasks if t.device_hostname == hostname]

    # Group by category for frontend
    categories = {}
    for t in tasks:
        cat = t.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(t.model_dump())

    # Protocol summary
    protocols = list({t.protocol for t in tasks})
    total = len(tasks)
    completed = sum(1 for t in tasks if t.status in [TaskVerificationStatus.COMPLETED, TaskVerificationStatus.NOT_APPLICABLE, TaskVerificationStatus.WARNING])
    failed = sum(1 for t in tasks if t.status == TaskVerificationStatus.FAILED)
    warnings = sum(1 for t in tasks if t.status == TaskVerificationStatus.WARNING)
    incomplete = sum(1 for t in tasks if t.status == TaskVerificationStatus.INCOMPLETE)

    from engine.protocol_catalog import ProtocolCatalogEngine
    dev_classification = ProtocolCatalogEngine.detect_device_classification(dev)

    return {
        "hostname": hostname,
        "device_classification": dev_classification,
        "vendor": dev.vendor,
        "device_model": dev.device_model,
        "os_version": dev.os_version,
        "device_role": dev.device_role.value,
        "device_function": dev.device_function.value,
        "management_ip": dev.management_ip,
        "protocols": protocols,
        "total_tasks": total,
        "completed_tasks": completed,
        "failed_tasks": failed,
        "warning_tasks": warnings,
        "incomplete_tasks": incomplete,
        "categories": categories,
        "tasks": [t.model_dump() for t in tasks]
    }


class TaskStatusUpdateRequest(BaseModel):
    status: str  # "In-Complete", "Completed", "Warning", "Failed", "N/A"
    evidence_notes: str = ""
    actual_output: str = ""


@app.post("/api/audit/task/{task_id}/status")
async def update_task_status(task_id: str, req: TaskStatusUpdateRequest):
    """Update an individual audit task's verification status and evidence."""
    global project_state

    task = next((t for t in project_state.device_audit_tasks if t.id == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail=f"Audit task '{task_id}' not found")

    # Map status string to enum
    status_map = {
        "In-Complete": TaskVerificationStatus.INCOMPLETE,
        "Completed": TaskVerificationStatus.COMPLETED,
        "Warning": TaskVerificationStatus.WARNING,
        "Failed": TaskVerificationStatus.FAILED,
        "N/A": TaskVerificationStatus.NOT_APPLICABLE
    }
    new_status = status_map.get(req.status)
    if not new_status:
        raise HTTPException(status_code=400, detail=f"Invalid status: '{req.status}'. Must be one of: {list(status_map.keys())}")

    task.status = new_status
    if req.evidence_notes:
        task.evidence_notes = req.evidence_notes
    if req.actual_output:
        task.actual_output = req.actual_output
    task.timestamp = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Recompute summary task metrics
    if project_state.summary:
        total = len(project_state.device_audit_tasks)
        completed = sum(1 for t in project_state.device_audit_tasks if t.status in [
            TaskVerificationStatus.COMPLETED, TaskVerificationStatus.NOT_APPLICABLE, TaskVerificationStatus.WARNING
        ])
        project_state.summary.total_tasks = total
        project_state.summary.completed_tasks = completed
        project_state.summary.incomplete_tasks = total - completed

    return {"status": "updated", "task": task.model_dump()}


class BatchTaskUpdateRequest(BaseModel):
    hostname: Optional[str] = None
    protocol: Optional[str] = None
    status: str = "Completed"


@app.post("/api/audit/tasks/batch_update")
async def batch_update_tasks(req: BatchTaskUpdateRequest):
    """Batch update verification status for all tasks matching a hostname and/or protocol filter."""
    global project_state

    status_map = {
        "In-Complete": TaskVerificationStatus.INCOMPLETE,
        "Completed": TaskVerificationStatus.COMPLETED,
        "Warning": TaskVerificationStatus.WARNING,
        "Failed": TaskVerificationStatus.FAILED,
        "N/A": TaskVerificationStatus.NOT_APPLICABLE
    }
    new_status = status_map.get(req.status)
    if not new_status:
        raise HTTPException(status_code=400, detail=f"Invalid status: '{req.status}'")

    updated_count = 0
    now_str = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for task in project_state.device_audit_tasks:
        match = True
        if req.hostname and task.device_hostname != req.hostname:
            match = False
        if req.protocol and task.protocol != req.protocol:
            match = False
        if match:
            task.status = new_status
            task.timestamp = now_str
            updated_count += 1

    # Recompute summary task metrics
    if project_state.summary:
        total = len(project_state.device_audit_tasks)
        completed = sum(1 for t in project_state.device_audit_tasks if t.status in [
            TaskVerificationStatus.COMPLETED, TaskVerificationStatus.NOT_APPLICABLE, TaskVerificationStatus.WARNING
        ])
        project_state.summary.total_tasks = total
        project_state.summary.completed_tasks = completed
        project_state.summary.incomplete_tasks = total - completed

    return {"status": "batch_updated", "updated_count": updated_count}


@app.get("/api/audit/matrix_summary")
async def get_audit_matrix_summary():
    """Return consolidated protocol verification matrix across all devices."""
    global project_state

    from engine.protocol_catalog import ProtocolCatalogEngine

    matrix = []
    for dev in project_state.devices:
        dev_tasks = [t for t in project_state.device_audit_tasks if t.device_hostname == dev.hostname]
        classification = ProtocolCatalogEngine.detect_device_classification(dev)

        # Per-protocol status
        protocols = {}
        for task in dev_tasks:
            proto = task.protocol
            if proto not in protocols:
                protocols[proto] = {"total": 0, "completed": 0, "failed": 0, "warning": 0, "incomplete": 0, "na": 0}
            protocols[proto]["total"] += 1
            if task.status == TaskVerificationStatus.COMPLETED:
                protocols[proto]["completed"] += 1
            elif task.status == TaskVerificationStatus.FAILED:
                protocols[proto]["failed"] += 1
            elif task.status == TaskVerificationStatus.WARNING:
                protocols[proto]["warning"] += 1
            elif task.status == TaskVerificationStatus.NOT_APPLICABLE:
                protocols[proto]["na"] += 1
            else:
                protocols[proto]["incomplete"] += 1

        total = len(dev_tasks)
        completed = sum(1 for t in dev_tasks if t.status in [
            TaskVerificationStatus.COMPLETED, TaskVerificationStatus.NOT_APPLICABLE, TaskVerificationStatus.WARNING
        ])
        failed = sum(1 for t in dev_tasks if t.status == TaskVerificationStatus.FAILED)
        warnings = sum(1 for t in dev_tasks if t.status == TaskVerificationStatus.WARNING)

        # Overall device status
        if total == 0:
            device_status = "No Tasks"
        elif failed > 0:
            device_status = "Failed"
        elif completed == total:
            device_status = "Verified"
        else:
            device_status = "In Progress"

        matrix.append({
            "hostname": dev.hostname,
            "vendor": dev.vendor,
            "device_model": dev.device_model,
            "device_role": dev.device_role.value,
            "device_function": dev.device_function.value,
            "classification": classification,
            "management_ip": dev.management_ip,
            "total_tasks": total,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "warning_tasks": warnings,
            "incomplete_tasks": sum(1 for t in dev_tasks if t.status == TaskVerificationStatus.INCOMPLETE),
            "completion_pct": round((completed / total * 100) if total > 0 else 0, 1),
            "device_status": device_status,
            "protocols": protocols
        })

    return {
        "matrix": matrix,
        "summary": project_state.summary.model_dump() if project_state.summary else None
    }


# =========================================================
# Modular Vendor & Test Scenario Catalog Studio Endpoints
# =========================================================

@app.get("/api/catalog/vendors")
async def get_vendor_catalog():
    """Retrieve all modular vendor profiles."""
    return CatalogManager.get_vendor_catalog()


@app.post("/api/catalog/vendors")
async def save_vendor_profile(vendor_data: dict):
    """Add or update a vendor profile in the catalog."""
    try:
        updated = CatalogManager.add_or_update_vendor(vendor_data)
        return {"status": "success", "vendor": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/catalog/vendors/{vendor_name}")
async def delete_vendor_profile(vendor_name: str):
    """Delete a vendor profile from the catalog."""
    success = CatalogManager.delete_vendor(vendor_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Vendor '{vendor_name}' not found.")
    return {"status": "success", "message": f"Vendor '{vendor_name}' deleted."}


@app.get("/api/catalog/scenarios")
async def get_test_scenarios():
    """Retrieve all modular audit test scenarios with multi-vendor CLI commands."""
    return CatalogManager.get_test_scenarios_catalog()


@app.post("/api/catalog/scenarios")
async def save_test_scenario(scenario_data: dict):
    """Add or update a test scenario in the catalog."""
    try:
        updated = CatalogManager.add_or_update_scenario(scenario_data)
        # Re-run audit to synchronize tasks
        global project_state
        project_state = AuditOrchestrator.run_full_audit(project_state)
        return {"status": "success", "scenario": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/catalog/scenarios/{scenario_id}")
async def delete_test_scenario(scenario_id: str):
    """Delete a test scenario from the catalog."""
    success = CatalogManager.delete_scenario(scenario_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")
    # Re-run audit to synchronize tasks
    global project_state
    project_state = AuditOrchestrator.run_full_audit(project_state)
    return {"status": "success", "message": f"Scenario '{scenario_id}' deleted."}


@app.post("/api/catalog/scenarios/import")
async def import_scenarios_json(file: UploadFile = File(...)):
    """Bulk import test scenarios from a JSON file."""
    try:
        content = await file.read()
        import json
        data = json.loads(content.decode("utf-8"))
        if isinstance(data, list):
            data = {"scenarios": data}
        elif "scenarios" not in data:
            raise ValueError("JSON must contain a 'scenarios' list.")
        
        CatalogManager.save_test_scenarios(data)
        global project_state
        project_state = AuditOrchestrator.run_full_audit(project_state)
        return {"status": "success", "total_scenarios": len(data["scenarios"])}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import scenarios JSON: {str(e)}")


@app.get("/api/catalog/scenarios/export")
async def export_scenarios_json():
    """Export the current test scenarios catalog as a JSON file."""
    import json
    data = CatalogManager.get_test_scenarios_catalog()
    content_str = json.dumps(data, indent=2)
    return Response(
        content=content_str,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="test_scenarios_catalog.json"'}
    )


@app.post("/api/catalog/vendors/import")
async def import_vendors_json(file: UploadFile = File(...)):
    """Bulk import vendor platform profiles from a JSON file."""
    try:
        content = await file.read()
        import json
        data = json.loads(content.decode("utf-8"))
        if isinstance(data, list):
            data = {"vendors": data}
        elif "vendors" not in data:
            raise ValueError("JSON must contain a 'vendors' list.")
        
        CatalogManager.save_vendor_catalog(data)
        return {"status": "success", "total_vendors": len(data["vendors"])}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import vendor catalog JSON: {str(e)}")


@app.get("/api/catalog/vendors/export")
async def export_vendors_json():
    """Export the current vendor platform catalog as a JSON file."""
    import json
    data = CatalogManager.get_vendor_catalog()
    content_str = json.dumps(data, indent=2)
    return Response(
        content=content_str,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="vendor_platform_catalog.json"'}
    )


@app.post("/api/catalog/reset")
async def reset_catalog_defaults():
    """Reset both vendor and scenario catalogs to default presets."""
    CatalogManager.reset_to_defaults()
    global project_state
    project_state = AuditOrchestrator.run_full_audit(project_state)
    return {"status": "success", "message": "Catalogs reset to factory presets."}


# =========================================================================
# STAGE 3: LIVE AUDIT TRIGGER & INTERACTIVE RETRY ENDPOINTS
# =========================================================================

@app.post("/api/audit/trigger")
async def trigger_stage3_audit(req: Stage3TriggerRequest):
    """
    Trigger live automated audit command execution in Stage 3:
    - scope="all": Runs across all devices
    - scope="device": Runs for a specific device (hostname)
    - scope="section": Runs for a specific section/category on a device
    - scope="task": Runs for a single task
    Output files saved to files/<company>/<building>/<date>/<device>/sh_(cmd)_HHMMSS.cfg.
    """
    global project_state
    try:
        active_state = parse_client_state(req.project_state) if req.project_state else project_state
        project_state = active_state

        runner = AuditTriggerRunner()
        job_id = runner.trigger_audit(req, active_state)
        job_data = runner.jobs.get(job_id, {})
        is_completed = (job_data.get("status") in ["COMPLETED", "FAILED"])
        return {
            "status": "completed" if is_completed else "started",
            "job_id": job_id,
            "scope": req.scope,
            "tasks_succeeded": job_data.get("tasks_succeeded", 0),
            "tasks_failed": job_data.get("tasks_failed", 0),
            "total_files": len(job_data.get("log_files", [])),
            "log_files": job_data.get("log_files", []),
            "stream_url": f"/api/audit/stream/{job_id}",
            "project_state": active_state.dict()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/stream/{job_id}")
async def stream_audit_progress(job_id: str):
    """
    Server-Sent Events (SSE) streaming real-time task progress to the UI.
    """
    runner = AuditTriggerRunner()
    if not hasattr(runner, "job_queues") or job_id not in runner.job_queues:
        raise HTTPException(status_code=404, detail="Audit job not found.")

    import asyncio
    import json

    async def event_generator():
        event_queue = runner.job_queues[job_id]
        while True:
            try:
                if not event_queue.empty():
                    event_data = event_queue.get_nowait()
                    yield f"data: {json.dumps(event_data)}\n\n"
                    if event_data.get("event") in ["JOB_COMPLETED", "JOB_FAILED"]:
                        break
                else:
                    await asyncio.sleep(0.15)
                    job_info = runner.jobs.get(job_id)
                    if job_info and job_info.get("status") in ["COMPLETED", "FAILED"] and event_queue.empty():
                        break
            except Exception:
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/audit/task/{task_id}/retry")
async def retry_audit_task(task_id: str, req: Stage3RetryTaskRequest):
    """
    Live on-the-fly execution and test of an updated/custom command for a failed task.
    Updates the task command, executes on the device, updates status to Completed if passed,
    and saves output to files/<company>/<building>/<date>/<device>/sh_(cmd)_HHMMSS.cfg.
    """
    global project_state
    active_state = parse_client_state(req.project_state) if req.project_state else project_state
    project_state = active_state

    runner = AuditTriggerRunner()
    result = runner.retry_task_command(
        task_id=task_id,
        new_command=req.new_command,
        credentials=req.credentials,
        project_state=active_state,
        client_timezone=req.client_timezone
    )
    if not result.get("success"):
        # Always return 400 if the command failed so frontend knows to show error
        err_msg = result.get("error") or "Command failed validation on device."
        err_class = result.get("error_class", "EXEC_ERROR")
        raise HTTPException(
            status_code=400,
            detail={
                "error": err_msg,
                "error_class": err_class,
                "task_id": task_id,
                "output": result.get("output", ""),
                "saved_file": result.get("saved_file", ""),
                "project_state": active_state.dict()
            }
        )
    result["project_state"] = active_state.dict()
    return result


@app.get("/api/audit/download_files/{target}")
async def download_audit_files(target: str = "all"):
    """
    Download a ZIP archive of raw collected .cfg files from files/ folder.
    target can be 'all' or a specific device hostname.
    """
    import os
    runner = AuditTriggerRunner()
    target_dev = None if target.lower() == "all" else target
    zip_path = runner.log_writer.create_zip_archive(identifier=target, target_device=target_dev)

    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="No log archive available.")

    filename = os.path.basename(zip_path)
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=filename
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)


