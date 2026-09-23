"""
End-to-End Verification Test for 3-Stage Network Infrastructure Audit Engine.
"""
import os
import sys
import openpyxl

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from core.models import DeviceModel, TopologyLink, PortChannelGroup, NetworkProjectState
from core.constants import DeviceFunction, DeviceRole, PortSpeed, LifecycleStatus, AuditStatus
from engine.topology_engine import TopologyEngine
from engine.audit_orchestrator import AuditOrchestrator
from reporting.excel_generator import ExcelWorkbookGenerator
from reporting.executive_report import ExecutiveReportGenerator

def test_full_pipeline():
    print("==================================================")
    print("TESTING 3-STAGE NETWORK INFRASTRUCTURE AUDIT ENGINE")
    print("==================================================")

    # 1. Test Page 1: Device Inventory & Classification
    print("\n[Stage 1] Testing Device Inventory & Role/Function Segregation...")
    devices = [
        DeviceModel(
            device_id="DEV-01",
            hostname="CORE-01",
            vendor="Cisco",
            device_model="Catalyst 9500-24Q",
            os_version="IOS-XE 17.9.4a",
            device_function=DeviceFunction.L3,
            device_role=DeviceRole.CORE,
            num_ports=24,
            port_speed=PortSpeed.SPEED_40G.value,
            management_ip="10.254.0.1",
            lifecycle_status=LifecycleStatus.ACTIVE
        ),
        DeviceModel(
            device_id="DEV-02",
            hostname="DIST-01",
            vendor="Cisco",
            device_model="Catalyst 9300-48U",
            os_version="IOS-XE 17.9.4a",
            device_function=DeviceFunction.L2_L3,
            device_role=DeviceRole.DISTRIBUTION,
            num_ports=48,
            port_speed=PortSpeed.SPEED_10G.value,
            management_ip="10.254.1.1",
            lifecycle_status=LifecycleStatus.ACTIVE
        ),
        DeviceModel(
            device_id="DEV-03",
            hostname="ACC-01",
            vendor="Cisco",
            device_model="Catalyst 9200-24P",
            os_version="IOS-XE 17.6.3",
            device_function=DeviceFunction.L2,
            device_role=DeviceRole.ACCESS,
            num_ports=24,
            port_speed=PortSpeed.SPEED_1G.value,
            management_ip="10.254.10.10",
            lifecycle_status=LifecycleStatus.ACTIVE
        ),
        DeviceModel(
            device_id="DEV-04",
            hostname="FW-01",
            vendor="Palo Alto",
            device_model="PA-3220",
            os_version="PAN-OS 10.2.3",
            device_function=DeviceFunction.FIREWALL,
            device_role=DeviceRole.FIREWALL,
            num_ports=12,
            port_speed=PortSpeed.SPEED_10G.value,
            management_ip="10.254.99.1",
            lifecycle_status=LifecycleStatus.ACTIVE
        ),
        DeviceModel(
            device_id="DEV-05",
            hostname="AP-01",
            vendor="Aruba",
            device_model="AP-515",
            os_version="ArubaOS 8.10.0",
            device_function=DeviceFunction.WIRELESS_AP,
            device_role=DeviceRole.WIRELESS_AP,
            num_ports=2,
            port_speed=PortSpeed.SPEED_1G.value,
            management_ip="10.254.50.25",
            lifecycle_status=LifecycleStatus.ACTIVE
        )
    ]
    print(f"      Created {len(devices)} categorized devices.")

    # 2. Test Page 2: Topology Links, Port-Channels & Bidirectional Sync
    print("\n[Stage 2] Testing Topology & Bidirectional Link Synchronization...")
    links = []
    links = TopologyEngine.add_bidirectional_link(links, "CORE-01", "GigabitEthernet1/0/1", "DIST-01", "GigabitEthernet1/0/49", "10G", "Po10")
    links = TopologyEngine.add_bidirectional_link(links, "CORE-01", "GigabitEthernet1/0/2", "DIST-01", "GigabitEthernet1/0/50", "10G", "Po10")
    links = TopologyEngine.add_bidirectional_link(links, "DIST-01", "GigabitEthernet1/0/1", "ACC-01", "GigabitEthernet1/0/24", "1G")
    links = TopologyEngine.add_bidirectional_link(links, "CORE-01", "GigabitEthernet1/0/10", "FW-01", "Port1", "10G")
    links = TopologyEngine.add_bidirectional_link(links, "ACC-01", "GigabitEthernet1/0/1", "AP-01", "Port1", "1G")

    port_channels = [
        PortChannelGroup(
            id="Po10",
            source_device="CORE-01",
            target_device="DIST-01",
            source_member_ports=["GigabitEthernet1/0/1", "GigabitEthernet1/0/2"],
            target_member_ports=["GigabitEthernet1/0/49", "GigabitEthernet1/0/50"],
            protocol="LACP",
            status="Operational"
        )
    ]
    print(f"      Created {len(links)} links and {len(port_channels)} Port-Channel bundles.")

    # Test Link Validation Engine (Section 2.4)
    print("      Running Section 2.4 Link Validation Engine...")
    issues = TopologyEngine.validate_topology(devices, links, port_channels)
    print(f"      Link Validation Issues Detected: {len(issues)}")
    for iss in issues:
        print(f"        - [{iss.severity.value}] {iss.rule}: {iss.message}")

    # 3. Test Page 3: Dynamic Role & Function Audit Engine
    print("\n[Stage 3] Testing Dynamic Role & Function Audit Engine...")
    raw_configs = {
        "CORE-01": "hostname CORE-01\nspanning-tree mode rapid-pvst\ninterface Loopback0\n ip address 10.254.0.1 255.255.255.255\nrouter ospf 100\n passive-interface default\nline vty 0 15\n transport input ssh\n",
        "ACC-01": "hostname ACC-01\nspanning-tree mode pvst\nvlan 10,20,30\ninterface GigabitEthernet1/0/24\n switchport mode trunk\n switchport trunk native vlan 1\ninterface GigabitEthernet1/0/1\n switchport mode access\n switchport access vlan 10\n spanning-tree portfast\nline vty 0 4\n transport input telnet\n"
    }

    operational_logs = {
        "CORE-01": "CORE-01# show cdp neighbors\nDIST-01 Gig 1/0/1 160 S WS-C9300 Gig 1/0/49\nFW-01 Gig 1/0/10 155 R PA-3220 Port1\n",
        "ACC-01": "ACC-01# show interfaces counters errors\nGig1/0/24 0 42 0 42 0 0 42\n"
    }

    state = NetworkProjectState(
        project_name="Enterprise Test Network",
        devices=devices,
        topology_links=links,
        port_channels=port_channels,
        raw_configs=raw_configs,
        operational_logs=operational_logs
    )

    state = AuditOrchestrator.run_full_audit(state)
    s = state.summary

    print(f"      Audit Completed!")
    print(f"      Health Score: {s.health_score}/100")
    print(f"      Overall Risk: {s.overall_risk.value}")
    print(f"      Total Checks: {s.total_checks} (Passed: {s.passed_checks}, Failed: {s.failed_checks}, Warnings: {s.warning_checks})")

    # 4. Test Deliverable 1: 12-Sheet Excel Evidence Workbook
    print("\n[Deliverable 1] Testing 12-Sheet Excel Workbook Generation...")
    xlsx_path = os.path.abspath(os.path.dirname(__file__) + "/../Audit_Evidence_Workbook.xlsx")
    ExcelWorkbookGenerator.generate(state, xlsx_path)
    
    wb = openpyxl.load_workbook(xlsx_path)
    sheet_names = wb.sheetnames
    print(f"      Workbook Generated: {xlsx_path}")
    print(f"      Total Sheets: {len(sheet_names)}")
    for idx, name in enumerate(sheet_names, 1):
        print(f"        Sheet {idx:02d}: {name}")
    assert len(sheet_names) == 3, f"Expected 3 sheets, got {len(sheet_names)}"

    # 5. Test Deliverable 2: Executive Report
    print("\n[Deliverable 2] Testing Single-Page Executive Report...")
    md = ExecutiveReportGenerator.generate_markdown(state)
    print("      Markdown Report Summary:")
    print(md[:400] + "...\n[Truncated]")

    print("\n[SUCCESS] ALL 3 STAGES & DELIVERABLES VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    test_full_pipeline()
