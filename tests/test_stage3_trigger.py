import os
import sys
import shutil
import unittest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.models import (
    NetworkProjectState, DeviceModel, DeviceAuditTask, TaskVerificationStatus
)
from core.collector.models import (
    EphemeralCredentials, Stage3TriggerRequest, Stage3RetryTaskRequest
)
from core.collector.log_writer import LogWriter
from core.collector.audit_trigger_runner import AuditTriggerRunner
from core.collector.validator import CommandValidator

class MockDeviceAdapter:
    def __init__(self, hostname, ip_address, port, vendor, model, credentials, timeout=30):
        self.hostname = hostname
        self.ip_address = ip_address
        self.port = port
        self.vendor = vendor
        self.model = model
        self.credentials = credentials
        self.timeout = timeout
        self.is_connected = False

    def connect(self):
        self.is_connected = True
        return True, None

    def execute_command(self, command: str):
        if "invalid_cmd" in command:
            return False, "% Invalid input detected at '^' marker.", "Syntax Error"
        elif "fixed_cmd" in command:
            return True, f"Mock output for {command} on {self.hostname}: OK", None
        elif "show system info" in command:
            return True, f"Palo Alto PAN-OS 10.2 System Info for {self.hostname}", None
        else:
            return True, f"Standard output for {command} on {self.hostname}", None

    def disconnect(self):
        self.is_connected = False

class TestStage3Trigger(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(os.getcwd(), "test_stage3_files")
        self.runner = AuditTriggerRunner()
        self.runner.log_writer = LogWriter(base_dir=self.test_dir)

        # Mock adapters
        import core.collector.audit_trigger_runner
        self.orig_ssh = core.collector.audit_trigger_runner.SSHDeviceAdapter
        self.orig_rest = core.collector.audit_trigger_runner.RestAPIDeviceAdapter
        core.collector.audit_trigger_runner.SSHDeviceAdapter = MockDeviceAdapter
        core.collector.audit_trigger_runner.RestAPIDeviceAdapter = MockDeviceAdapter

    def tearDown(self):
        import core.collector.audit_trigger_runner
        core.collector.audit_trigger_runner.SSHDeviceAdapter = self.orig_ssh
        core.collector.audit_trigger_runner.RestAPIDeviceAdapter = self.orig_rest
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_log_writer_exact_path_format(self):
        fixed_time = datetime(2026, 9, 2, 11, 30, 45)
        path = self.runner.log_writer.save_command_output(
            company="zenquix",
            building="BLRCC002",
            device_name="FW-01",
            command_executed="show system info",
            output="Mock PAN-OS output",
            timestamp_dt=fixed_time
        )
        # Expected format: files/<companyname>/<building>/<date>/<device>/sh_(cmd)_HHMMSS.cfg
        expected_part = os.path.join("zenquix", "BLRCC002", "20260902", "FW-01", "sh_system_info_113045.cfg")
        self.assertIn(expected_part, path)
        self.assertTrue(os.path.exists(path))

    def test_single_click_trigger_all_devices(self):
        state = NetworkProjectState(project_name="Test Project", company_name="zenquix")
        dev1 = DeviceModel(
            device_id="dev-1",
            hostname="FW-01",
            company_name="zenquix",
            site_location="BLRCC002",
            vendor="Palo Alto",
            device_model="paloalto",
            management_ip="10.254.1.10"
        )
        dev2 = DeviceModel(
            device_id="dev-2",
            hostname="CORE-01",
            company_name="zenquix",
            site_location="BLRCC002",
            vendor="Cisco",
            device_model="Catalyst 3850",
            management_ip="10.254.1.1"
        )
        state.devices = [dev1, dev2]

        task1 = DeviceAuditTask(
            id="task-1",
            device_hostname="FW-01",
            device_role="FIREWALL",
            protocol="Basic Health",
            category="Device Health & Baseline",
            title="System Info",
            description="Verify platform",
            verification_command="show system info",
            status=TaskVerificationStatus.INCOMPLETE
        )
        task2 = DeviceAuditTask(
            id="task-2",
            device_hostname="CORE-01",
            device_role="CORE",
            protocol="Basic Health",
            category="Device Health & Baseline",
            title="Version Info",
            description="Verify version",
            verification_command="show version",
            status=TaskVerificationStatus.INCOMPLETE
        )
        state.device_audit_tasks = [task1, task2]

        req = Stage3TriggerRequest(
            scope="all",
            credentials=EphemeralCredentials(username="admin", password="SecretPassword123!")
        )

        job_id = self.runner.trigger_audit(req, state)
        self.assertTrue(bool(job_id))

        # Wait briefly for thread execution
        import time
        for _ in range(20):
            if self.runner.jobs[job_id]["status"] == "COMPLETED":
                break
            time.sleep(0.1)

        self.assertEqual(self.runner.jobs[job_id]["status"], "COMPLETED")
        self.assertEqual(task1.status, TaskVerificationStatus.COMPLETED)
        self.assertEqual(task2.status, TaskVerificationStatus.COMPLETED)
        self.assertGreater(len(task1.actual_output), 0)

        # Check output files generated in test_stage3_files/zenquix/BLRCC002/
        today = datetime.now().strftime("%Y%m%d")
        fw_folder = os.path.join(self.test_dir, "zenquix", "BLRCC002", today, "FW-01")
        self.assertTrue(os.path.exists(fw_folder))
        cfg_files = [f for f in os.listdir(fw_folder) if f.endswith(".cfg")]
        self.assertGreaterEqual(len(cfg_files), 1)

    def test_error_handling_and_interactive_retry(self):
        state = NetworkProjectState(project_name="Test Project", company_name="zenquix")
        dev1 = DeviceModel(
            device_id="dev-1",
            hostname="FW-01",
            company_name="zenquix",
            site_location="BLRCC002",
            vendor="Palo Alto",
            device_model="paloalto",
            management_ip="10.254.1.10"
        )
        state.devices = [dev1]

        # A task with an invalid command that will fail
        task1 = DeviceAuditTask(
            id="task-fail-1",
            device_hostname="FW-01",
            device_role="FIREWALL",
            protocol="Static Routing",
            category="Layer 3 Routing",
            title="Routing Table",
            description="Verify routes",
            verification_command="invalid_cmd test",
            status=TaskVerificationStatus.INCOMPLETE
        )
        state.device_audit_tasks = [task1]

        req = Stage3TriggerRequest(
            scope="device",
            hostname="FW-01",
            credentials=EphemeralCredentials(username="admin", password="Pass123!")
        )

        job_id = self.runner.trigger_audit(req, state)
        import time
        for _ in range(20):
            if self.runner.jobs[job_id]["status"] == "COMPLETED":
                break
            time.sleep(0.1)

        # Should be marked FAILED due to invalid_cmd
        self.assertEqual(task1.status, TaskVerificationStatus.FAILED)
        self.assertTrue("SYNTAX_ERROR" in task1.evidence_notes or "Command error" in task1.evidence_notes)

        # Now simulate user editing the command on the UI and clicking Retry!

        retry_creds = EphemeralCredentials(username="admin", password="Pass123!")
        retry_res = self.runner.retry_task_command(
            task_id="task-fail-1",
            new_command="fixed_cmd show routing",
            credentials=retry_creds,
            project_state=state
        )

        self.assertTrue(retry_res["success"])
        self.assertEqual(retry_res["status"], "Completed")
        self.assertEqual(task1.status, TaskVerificationStatus.COMPLETED)
        self.assertEqual(task1.verification_command, "fixed_cmd show routing")
        self.assertIn("fixed_cmd", task1.actual_output)

if __name__ == "__main__":
    unittest.main()
