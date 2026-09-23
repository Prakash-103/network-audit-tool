"""
Unit tests for the 10-Page Management Executive Report Generator.
Verifies metrics aggregation, decision-document formatting, security posture %, and template rendering.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.models import DeviceModel, NetworkProjectState, AuditCheckResult, AuditSummaryMetrics
from core.constants import DeviceFunction, DeviceRole, PortSpeed, LifecycleStatus, AuditStatus, SeverityLevel
from reporting.executive_report import ExecutiveReportGenerator

class TestExecutiveReportGenerator(unittest.TestCase):

    def setUp(self):
        self.devices = [
            DeviceModel(
                device_id="DEV-01", hostname="CORE-01", vendor="Cisco", device_model="Catalyst 9500",
                os_version="IOS-XE 17.9.4a", device_function=DeviceFunction.L3, device_role=DeviceRole.CORE,
                num_ports=24, port_speed=PortSpeed.SPEED_40G.value, management_ip="10.1.1.1", site_location="Chennai DC"
            ),
            DeviceModel(
                device_id="DEV-02", hostname="DIST-01", vendor="Cisco", device_model="Catalyst 9300",
                os_version="IOS-XE 17.9.4a", device_function=DeviceFunction.L2_L3, device_role=DeviceRole.DISTRIBUTION,
                num_ports=48, port_speed=PortSpeed.SPEED_10G.value, management_ip="10.1.2.1", site_location="Chennai DC"
            ),
            DeviceModel(
                device_id="DEV-03", hostname="ACC-01", vendor="Arista", device_model="7050TX",
                os_version="EOS 4.28.1F", device_function=DeviceFunction.L2, device_role=DeviceRole.ACCESS,
                num_ports=48, port_speed=PortSpeed.SPEED_10G.value, management_ip="10.1.3.1", site_location="Bangalore DC"
            ),
            DeviceModel(
                device_id="DEV-04", hostname="FW-01", vendor="Palo Alto", device_model="PA-3220",
                os_version="PAN-OS 10.2.3", device_function=DeviceFunction.FIREWALL, device_role=DeviceRole.FIREWALL,
                num_ports=12, port_speed=PortSpeed.SPEED_10G.value, management_ip="10.1.99.1", site_location="Chennai DC"
            ),
            DeviceModel(
                device_id="DEV-05", hostname="AP-01", vendor="Aruba", device_model="AP-515",
                os_version="ArubaOS 10.6.0.2", device_function=DeviceFunction.WIRELESS_AP, device_role=DeviceRole.WIRELESS_AP,
                num_ports=2, port_speed=PortSpeed.SPEED_1G.value, management_ip="10.1.50.1", site_location="Bangalore DC"
            )
        ]

        self.audit_results = [
            AuditCheckResult(
                id="CHK-01", device="CORE-01", role="Core", category="Security",
                check="SSH Management Plane Version", expected="SSH version 2", actual="SSH version 1 detected on VTY lines",
                status=AuditStatus.FAIL, severity=SeverityLevel.CRITICAL, evidence="show ip ssh",
                recommendation="Enforce SSHv2 and disable SSHv1"
            ),
            AuditCheckResult(
                id="CHK-02", device="DIST-01", role="Distribution", category="Availability",
                check="LACP Link Aggregation", expected="LACP Active", actual="Port-channel 10 member interface suspended",
                status=AuditStatus.WARNING, severity=SeverityLevel.HIGH, evidence="show etherchannel summary",
                recommendation="Validate port-channel configuration and member link speeds"
            ),
            AuditCheckResult(
                id="CHK-03", device="ACC-01", role="Access", category="Network Services",
                check="NTP Clock Synchronization", expected="NTP Synced", actual="NTP not configured",
                status=AuditStatus.WARNING, severity=SeverityLevel.MEDIUM, evidence="show ntp status",
                recommendation="Configure redundant NTP servers"
            ),
            AuditCheckResult(
                id="CHK-04", device="FW-01", role="Firewall", category="Security",
                check="AAA Authentication", expected="TACACS+ enabled", actual="TACACS+ configured and verified",
                status=AuditStatus.PASS, severity=SeverityLevel.LOW, evidence="show running-config aaa",
                recommendation="None"
            )
        ]

        self.state = NetworkProjectState(
            project_name="Enterprise Infrastructure Audit",
            company_name="ABC Corporation",
            site_location="Chennai Data Center",
            devices=self.devices,
            audit_results=self.audit_results,
            summary=AuditSummaryMetrics(
                client_name="ABC Corporation",
                audit_date="23 September 2026",
                total_devices=5,
                health_score=78,
                passed_checks=1,
                failed_checks=1,
                warning_checks=2,
                total_checks=4
            )
        )

    def test_compile_executive_metrics_structure(self):
        metrics = ExecutiveReportGenerator.compile_executive_metrics(self.state)

        # 1. Header & General Scope
        self.assertEqual(metrics["customer_name"], "ABC Corporation")
        self.assertEqual(metrics["site_location"], "Chennai Data Center")
        self.assertIn("Infrastructure", metrics["audit_scope"])

        # 2. Status & Context (Must NOT be just an arbitrary score)
        self.assertEqual(metrics["audit_status"], "ATTENTION REQUIRED")
        self.assertEqual(metrics["critical_findings_count"], 1)
        self.assertEqual(metrics["high_findings_count"], 1)
        self.assertIn("Audit identified 3 actionable findings across 4 executed checks", metrics["status_explanation"])

        # 3. Infrastructure Inventory at a glance
        self.assertEqual(metrics["total_devices"], 5)
        categories = [item["category"] for item in metrics["inventory_breakdown"]]
        self.assertIn("Cisco Switches", categories)
        self.assertIn("Arista Switches", categories)
        self.assertIn("Firewalls & Security", categories)

        # 4. Key Findings by Category
        cat_names = [row["name"] for row in metrics["category_rows"]]
        self.assertIn("Security", cat_names)
        self.assertIn("Availability", cat_names)
        self.assertIn("Network Services", cat_names)

        # 5. Top Findings with Business Impact
        self.assertTrue(len(metrics["top_findings"]) > 0)
        top_f = metrics["top_findings"][0]
        self.assertIn("observation", top_f)
        self.assertIn("potential_impact", top_f)
        self.assertIn("recommended_action", top_f)

        # 6. Security Posture Controls
        sec_names = [sc["name"] for sc in metrics["security_controls"]]
        self.assertTrue(any("AAA" in n for n in sec_names))
        self.assertTrue(any("SSH" in n for n in sec_names))

        # 7. Action Plan derived from actual findings
        self.assertEqual(len(metrics["action_plan"]), len(metrics["findings"]))
        self.assertEqual(metrics["action_plan"][0]["priority"], 1)

    def test_generate_markdown_report(self):
        md = ExecutiveReportGenerator.generate_markdown(self.state)
        self.assertIn("ENTERPRISE NETWORK INFRASTRUCTURE AUDIT REPORT", md)
        self.assertIn("ABC Corporation", md)
        self.assertIn("ATTENTION REQUIRED", md)
        self.assertIn("EXECUTIVE SUMMARY & DASHBOARD", md)
        self.assertIn("INFRASTRUCTURE AT A GLANCE", md)
        self.assertIn("TOP CRITICAL & HIGH RISK FINDINGS", md)
        self.assertIn("SECURITY POSTURE & CONTROL PLANE COMPLIANCE", md)

    def test_html_endpoint_rendering(self):
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        response = client.get("/api/export/executive/html")
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn("Enterprise Network Infrastructure", html)
        self.assertIn("EXECUTIVE SUMMARY", html)
        self.assertIn("INFRASTRUCTURE AT A GLANCE", html)
        self.assertIn("TOP FINDINGS", html)
        self.assertIn("SECURITY POSTURE", html)

    def test_normalized_audit_json_schema(self):
        from engine.audit_normalizer import AuditNormalizer
        norm = AuditNormalizer.normalize_audit(self.state)

        # Top-level required keys
        required_keys = [
            "audit", "summary", "categories", "category_rows", "findings",
            "recommendations", "action_plan", "security_controls",
            "availability_checks", "inventory_breakdown", "sites_list",
            "connectivity_stats", "evidence", "evidence_workbook_name"
        ]
        for key in required_keys:
            self.assertIn(key, norm, f"Missing required normalized key: {key}")

        # Summary KPIs
        summary = norm["summary"]
        self.assertEqual(summary["devices"], 5)
        self.assertEqual(summary["checks"], 4)
        self.assertEqual(summary["passed"], 1)
        self.assertEqual(summary["warnings"], 2)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["compliance"], 25)

    def test_data_consistency_27_checks_1_warning(self):
        """
        Verify the exact scenario reported by the user:
        1 Device, 27 total checks executed in Stage 3:
        26 PASS, 1 WARNING, 0 FAIL -> 96% compliance, exactly 1 finding, exactly 1 recommendation.
        """
        from core.models import DeviceAuditTask
        from core.constants import TaskVerificationStatus
        from engine.audit_normalizer import AuditNormalizer

        single_dev = DeviceModel(
            device_id="DEV-001", hostname="CORE-SW01", vendor="Cisco", device_model="Catalyst 9300",
            os_version="IOS-XE 17.9", device_function=DeviceFunction.L3, device_role=DeviceRole.CORE,
            num_ports=48, port_speed=PortSpeed.SPEED_10G.value, management_ip="10.254.1.1", site_location="HQ Primary Lead"
        )

        # Generate 27 tasks: 26 Completed, 1 Warning (IP Addressing)
        tasks = []
        protocols = [
            ("Running Config", "Configuration", "Running Configuration Baseline"),
            ("Device Health", "Baseline & Health", "System Resource & CPU Utilization"),
            ("Interfaces", "Interfaces", "Interface Operational Status & Errors"),
            ("Management Security", "Security", "SSH Management Cryptography"),
            ("Management Security", "Security", "AAA Centralized Authentication"),
            ("Management Security", "Security", "SNMP Access Control"),
            ("Management Security", "Security", "NTP Time Synchronization"),
            ("Management Security", "Security", "Syslog SIEM Auditing"),
            ("Management Security", "Security", "Management Access VTY ACL"),
            ("CDP", "Network Services", "CDP Neighbor Consistency"),
            ("LLDP", "Network Services", "LLDP Neighbor Verification"),
            ("VLAN", "Configuration", "VLAN Database & SVI Allocation"),
            ("Access Port", "Configuration", "Access Port Security & FastEthernet"),
            ("Trunk", "Configuration", "Trunk Native VLAN & Pruning"),
            ("STP", "Availability", "Spanning Tree Root Priority"),
            ("EtherChannel", "Availability", "EtherChannel / LACP Bundling"),
            ("Port Security", "Security", "Port Security Enforcement"),
            ("DHCP Snooping", "Security", "DHCP Snooping & Trust State"),
            ("DAI", "Security", "Dynamic ARP Inspection Validation"),
            ("SVI", "Configuration", "SVI Interface Addressing"),
            ("Static Routing", "Routing", "Static Route Null Routing"),
            ("OSPF", "Routing", "OSPF Adjacencies & Area 0"),
            ("BGP", "Routing", "BGP Peering Sessions"),
            ("HSRP", "Availability", "HSRP / FHRP Gateway VIP"),
            ("BFD", "Availability", "BFD Peer Rapid Detection"),
            ("QoS", "Performance", "QoS Trust & Queue Drop Statistics"),
            ("Interfaces", "Configuration", "Interface IP Addressing & Subnet Masks")  # The 1 warning
        ]
        self.assertEqual(len(protocols), 27)

        for idx, (proto, cat, title) in enumerate(protocols):
            if idx == 26:
                # 27th check: Warning on Interface IP Addressing
                t_status = TaskVerificationStatus.WARNING
                t_sev = SeverityLevel.HIGH
                t_out = "Warning: Subnet overlap detected on Vlan10 (10.1.1.0/24)"
            else:
                t_status = TaskVerificationStatus.COMPLETED
                t_sev = SeverityLevel.LOW
                t_out = "Verified. Configuration aligns with gold baseline."

            tasks.append(DeviceAuditTask(
                id=f"TASK-CORE-SW01-{idx:02d}",
                device_hostname="CORE-SW01",
                device_role="Core",
                protocol=proto,
                category=cat,
                title=title,
                description="Test description",
                verification_command="show running-config",
                status=t_status,
                actual_output=t_out,
                severity=t_sev
            ))

        live_state = NetworkProjectState(
            project_name="Acme Corp - HQ Primary Lead Audit",
            company_name="Acme Corp",
            site_location="HQ Primary Lead",
            devices=[single_dev],
            device_audit_tasks=tasks
        )

        norm = AuditNormalizer.normalize_audit(live_state)
        metrics = ExecutiveReportGenerator.compile_executive_metrics(live_state)

        # 1. Main KPI Verification
        self.assertEqual(metrics["total_devices"], 1)
        self.assertEqual(metrics["total_checks"], 27)
        self.assertEqual(metrics["passed_checks"], 26)
        self.assertEqual(metrics["warning_checks"], 1)
        self.assertEqual(metrics["failed_checks"], 0)
        self.assertEqual(metrics["compliance_pct"], 96)  # 26/27 = 96.3% -> 96%

        # 2. Strict Findings Distinction
        # Exactly 1 finding because 26 checks passed and 1 had a warning!
        self.assertEqual(len(metrics["findings"]), 1)
        self.assertEqual(metrics["findings"][0]["check_name"], "Interface IP Addressing & Subnet Masks")
        self.assertEqual(metrics["findings"][0]["status"], "WARNING")
        self.assertEqual(metrics["findings"][0]["severity"], "High")

        # 3. Recommendations derived strictly from findings
        self.assertEqual(len(metrics["action_plan"]), 1)
        self.assertEqual(metrics["action_plan"][0]["area"], "Configuration")

        # 4. Security Posture Controls calculation
        for sc in metrics["security_controls"]:
            # All security checks passed! Should be 100%, never hardcoded 10%!
            self.assertEqual(sc["pct"], 100, f"Security control {sc['name']} should be 100% compliant")

        # 5. Availability checks status
        stp_check = next(ac for ac in metrics["availability_checks"] if "STP" in ac["protocol"])
        self.assertEqual(stp_check["status"], "✓")

    def test_zero_findings_when_all_checks_pass(self):
        """Verify that when 100% of checks pass, zero findings are fabricated."""
        from core.models import DeviceAuditTask
        from core.constants import TaskVerificationStatus
        from engine.audit_normalizer import AuditNormalizer

        single_dev = DeviceModel(
            device_id="DEV-001", hostname="CORE-SW01", vendor="Cisco", device_model="Catalyst 9300",
            os_version="IOS-XE 17.9", device_function=DeviceFunction.L3, device_role=DeviceRole.CORE,
            num_ports=48, port_speed=PortSpeed.SPEED_10G.value, management_ip="10.254.1.1", site_location="HQ Primary Lead"
        )

        tasks = [
            DeviceAuditTask(
                id=f"TASK-PASS-{i}",
                device_hostname="CORE-SW01",
                device_role="Core",
                protocol="STP",
                category="Availability",
                title=f"Check {i}",
                description="Conforms to standard",
                verification_command="show running-config",
                status=TaskVerificationStatus.COMPLETED
            ) for i in range(10)
        ]

        clean_state = NetworkProjectState(
            company_name="Acme Corp",
            devices=[single_dev],
            device_audit_tasks=tasks
        )

        norm = AuditNormalizer.normalize_audit(clean_state)
        self.assertEqual(norm["summary"]["checks"], 10)
        self.assertEqual(norm["summary"]["passed"], 10)
        self.assertEqual(norm["summary"]["warnings"], 0)
        self.assertEqual(norm["summary"]["failed"], 0)
        self.assertEqual(norm["summary"]["compliance"], 100)
        self.assertEqual(len(norm["findings"]), 0)
        self.assertEqual(norm["summary"]["audit_status"], "COMPLIANT")

    def test_generate_docx_report(self):
        buf = ExecutiveReportGenerator.generate_docx(self.state)
        self.assertIsNotNone(buf)
        raw_bytes = buf.getvalue()
        self.assertGreater(len(raw_bytes), 1000)
        # Verify it's a valid zip/docx archive starting with PK\x03\x04
        self.assertTrue(raw_bytes.startswith(b"PK\x03\x04"))

    def test_docx_endpoint_download(self):
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        response = client.get("/api/export/executive/docx")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("content-type"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        self.assertIn("attachment", response.headers.get("content-disposition", ""))
        self.assertIn(".docx", response.headers.get("content-disposition", ""))
    def test_partial_task_execution_executed_checks_kpi(self):
        """
        Verify that when an audit has unexecuted incomplete tasks in the queue (e.g. 222 total tasks,
        32 executed [22 PASS, 10 WARNING], 190 INCOMPLETE), executed checks is 32 and compliance is
        69% (22/32), NOT deflated to 10% (22/222).
        """
        from core.models import DeviceAuditTask
        from core.constants import TaskVerificationStatus
        from engine.audit_normalizer import AuditNormalizer

        single_dev = DeviceModel(
            device_id="DEV-001", hostname="CORE-SW01", vendor="Cisco", device_model="Catalyst 9300",
            os_version="IOS-XE 17.9", device_function=DeviceFunction.L3, device_role=DeviceRole.CORE,
            num_ports=48, port_speed=PortSpeed.SPEED_10G.value, management_ip="10.254.1.1", site_location="HQ Primary Lead"
        )

        tasks = []
        # 22 Passed tasks
        for i in range(22):
            tasks.append(DeviceAuditTask(
                id=f"TASK-PASS-{i+1:03d}", device_hostname="CORE-SW01", device_role="Core", category="Security",
                protocol="SSH", title=f"Security Baseline Check {i+1}", description="Gold baseline",
                verification_command="show running-config", actual_output="Configured correctly",
                evidence_notes="OK", status=TaskVerificationStatus.COMPLETED, severity=SeverityLevel.LOW
            ))
        # 10 Warning tasks
        for i in range(10):
            tasks.append(DeviceAuditTask(
                id=f"TASK-WARN-{i+1:03d}", device_hostname="CORE-SW01", device_role="Core", category="Availability",
                protocol="STP", title=f"Spanning Tree Root Priority Check {i+1}", description="Gold baseline",
                verification_command="show spanning-tree", actual_output="Bridge priority is default 32768",
                evidence_notes="Warning", status=TaskVerificationStatus.WARNING, severity=SeverityLevel.HIGH
            ))
        # 190 Incomplete queued tasks
        for i in range(190):
            tasks.append(DeviceAuditTask(
                id=f"TASK-INC-{i+1:03d}", device_hostname="CORE-SW01", device_role="Core", category="Performance",
                protocol="QoS", title=f"Buffer Queuing Check {i+1}", description="Gold baseline",
                verification_command="show policy-map", actual_output="",
                evidence_notes="", status=TaskVerificationStatus.INCOMPLETE, severity=SeverityLevel.MEDIUM
            ))

        partial_state = NetworkProjectState(
            project_name="Partial Execution Audit",
            company_name="Zenquix",
            site_location="BLRCC002",
            devices=[single_dev],
            device_audit_tasks=tasks,
            audit_results=[]
        )

        norm = AuditNormalizer.normalize_audit(partial_state)
        summary = norm["summary"]

        self.assertEqual(summary["total_scheduled"], 222)
        self.assertEqual(summary["incomplete"], 190)
        self.assertEqual(summary["passed"], 22)
        self.assertEqual(summary["warnings"], 10)
        self.assertEqual(summary["failed"], 0)
        # Executed checks must be 32, NOT 222!
        self.assertEqual(summary["checks"], 32)
        # Compliance must be 22 / 32 = 69%, NOT 22 / 222 = 10%!
        self.assertEqual(summary["compliance"], 69)

    def test_html_endpoint_download_attachment(self):
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        response = client.get("/api/export/executive/html?download=1")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers.get("content-disposition", ""))
        self.assertIn(".html", response.headers.get("content-disposition", ""))
        self.assertIn("<!DOCTYPE html>", response.text)

    def test_scope_filtering_critical(self):
        from engine.audit_normalizer import AuditNormalizer
        norm_all = AuditNormalizer.normalize_audit(self.state, scope="all")
        self.assertIn("Enterprise Network Infrastructure", norm_all["audit"]["audit_scope"])

        norm_crit = AuditNormalizer.normalize_audit(self.state, scope="critical")
        self.assertIn("Critical & High Risk Scope", norm_crit["audit"]["audit_scope"])

    def test_md_preview_endpoint(self):
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        response = client.get("/api/export/executive/md/preview?scope=all")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("Markdown Deliverable Preview", response.text)
        self.assertIn("rawMarkdownText", response.text)

    def test_md_download_endpoint(self):
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        response = client.get("/api/export/executive/md?download=1&scope=critical")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/markdown", response.headers.get("content-type", ""))
        self.assertIn("attachment", response.headers.get("content-disposition", ""))
        self.assertIn(".md", response.headers.get("content-disposition", ""))


if __name__ == "__main__":
    unittest.main()
