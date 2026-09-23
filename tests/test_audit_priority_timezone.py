import unittest
from datetime import datetime
import zoneinfo
from core.models import DeviceModel, DeviceRole, DeviceFunction, NetworkProjectState
from core.collector.models import EphemeralCredentials
from core.constants import AuditProtocol
from engine.protocol_catalog import ProtocolCatalogEngine
from core.collector.log_writer import get_timezone_aware_now, LogWriter
from core.collector.simulation_engine import DeviceSimulationEngine
from core.collector.audit_trigger_runner import AuditTriggerRunner

class TestAuditPriorityAndTimezone(unittest.TestCase):
    def setUp(self):
        self.device = DeviceModel(
            device_id="dev-c3850",
            hostname="CORE-SW-01",
            management_ip="10.254.1.1",
            device_role=DeviceRole.CORE,
            device_function=DeviceFunction.L3,
            vendor="Cisco",
            device_model="WS-C3850-48P"
        )

    def test_running_config_priority_one(self):
        protocols = ProtocolCatalogEngine.get_applicable_protocols(self.device)
        self.assertEqual(protocols[0], AuditProtocol.RUNNING_CONFIG)

        tasks = ProtocolCatalogEngine.generate_audit_tasks(self.device)
        self.assertTrue(len(tasks) > 0)
        first_task = tasks[0]
        self.assertEqual(first_task.protocol, AuditProtocol.RUNNING_CONFIG.value)
        self.assertEqual(first_task.verification_command, "show running-config")
        self.assertIn("Priority 1 Baseline", first_task.condition)

    def test_browser_regional_timezone(self):
        tokyo_dt = get_timezone_aware_now("Asia/Tokyo")
        ny_dt = get_timezone_aware_now("America/New_York")
        self.assertIsNotNone(tokyo_dt.tzinfo)
        self.assertIsNotNone(ny_dt.tzinfo)
        self.assertEqual(tokyo_dt.tzinfo.key, "Asia/Tokyo")
        self.assertEqual(ny_dt.tzinfo.key, "America/New_York")

    def test_simulation_engine_running_config(self):
        output = DeviceSimulationEngine.generate_cli_output(
            "Cisco", "WS-C3850-48P", "CORE-SW-01", "show running-config", "10.254.1.1"
        )
        self.assertIn("hostname CORE-SW-01", output)
        self.assertIn("interface GigabitEthernet1/0/1", output)

    def test_retry_task_command(self):
        tasks = ProtocolCatalogEngine.generate_audit_tasks(self.device)
        state = NetworkProjectState(
            project_id="proj-test",
            project_name="Test Audit",
            company_name="Zenquix Corp",
            site_location="HQ-Bldg1",
            devices=[self.device],
            device_audit_tasks=tasks
        )
        runner = AuditTriggerRunner()
        first_task = tasks[0]

        result = runner.retry_task_command(
            task_id=first_task.id,
            new_command="show running-config",
            credentials=EphemeralCredentials(username="admin", password="password123"),
            project_state=state,
            client_timezone="Asia/Kolkata"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "Completed")
        self.assertIn("CORE-SW-01", state.raw_configs)
        self.assertIn("hostname CORE-SW-01", state.raw_configs["CORE-SW-01"])

if __name__ == "__main__":
    unittest.main()
