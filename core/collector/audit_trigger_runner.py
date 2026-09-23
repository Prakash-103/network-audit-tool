import os
import time
import uuid
import queue
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.models import NetworkProjectState, DeviceModel, DeviceAuditTask, TaskVerificationStatus
from core.collector.models import EphemeralCredentials, Stage3TriggerRequest
from core.collector.validator import CommandValidator
from core.collector.adapters.ssh_adapter import SSHDeviceAdapter
from core.collector.adapters.rest_adapter import RestAPIDeviceAdapter
from core.collector.log_writer import LogWriter

logger = logging.getLogger("AuditTriggerRunner")

class AuditTriggerRunner:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AuditTriggerRunner, cls).__new__(cls)
            cls._instance._init_runner()
        return cls._instance

    def __init__(self):
        # Ensure attributes exist even if instantiated without __new__ hook
        if not hasattr(self, "_initialized") or not self._initialized:
            self._init_runner()

    def _init_runner(self):
        self.log_writer = LogWriter()
        self.job_queues: Dict[str, queue.Queue] = {}
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self._initialized = True

    def emit_event(self, job_id: str, event_type: str, data: Dict[str, Any]):
        if not hasattr(self, "job_queues"):
            self.job_queues = {}
        if job_id in self.job_queues:
            payload = {
                "event": event_type,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "data": data
            }
            self.job_queues[job_id].put(payload)

    def _get_client_now(self, client_timezone: Optional[str] = None) -> datetime:
        if client_timezone:
            try:
                import zoneinfo
                return datetime.now(zoneinfo.ZoneInfo(client_timezone))
            except Exception:
                pass
        return datetime.now()

    def trigger_audit(self, req: Stage3TriggerRequest, project_state: NetworkProjectState) -> str:
        if not hasattr(self, "job_queues"):
            self.job_queues = {}
        if not hasattr(self, "jobs"):
            self.jobs = {}

        now_dt = self._get_client_now(req.client_timezone)
        job_id = str(uuid.uuid4())[:8]
        self.job_queues[job_id] = queue.Queue()

        # Determine target devices
        if req.scope == "all":
            target_devices = list(project_state.devices)
        elif req.scope in ["device", "section"] and req.hostname:
            target_devices = [d for d in project_state.devices if d.hostname.lower() == req.hostname.lower()]
        elif req.scope == "task" and req.task_id:
            task = next((t for t in project_state.device_audit_tasks if t.id == req.task_id), None)
            if task:
                target_devices = [d for d in project_state.devices if d.hostname.lower() == task.device_hostname.lower()]
            else:
                target_devices = []
        else:
            target_devices = list(project_state.devices)

        if not target_devices:
            raise ValueError("No matching devices found for audit trigger.")

        self.jobs[job_id] = {
            "job_id": job_id,
            "status": "RUNNING",
            "scope": req.scope,
            "started_at": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "completed_at": None,
            "total_devices": len(target_devices),
            "completed_devices": 0,
            "total_tasks_executed": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
            "log_files": [],
            "client_timezone": req.client_timezone
        }

        is_serverless = (
            req.project_state is not None or
            any(os.getenv(v) for v in [
                "VERCEL", "VERCEL_ENV", "NETLIFY", "NETLIFY_DEV",
                "AWS_LAMBDA_FUNCTION_NAME", "LAMBDA_TASK_ROOT", "AWS_EXECUTION_ENV"
            ])
        )
        if is_serverless:
            # Execute synchronously so AWS Lambda / Netlify / Vercel does not freeze worker threads
            self._run_audit_job(
                job_id,
                target_devices,
                req,
                project_state
            )
        else:
            # Run in thread pool for asynchronous background streaming
            executor = ThreadPoolExecutor(max_workers=req.max_workers, thread_name_prefix=f"audit-trigger-{job_id}")
            executor.submit(
                self._run_audit_job,
                job_id,
                target_devices,
                req,
                project_state
            )

        return job_id

    def _run_audit_job(
        self,
        job_id: str,
        devices: List[DeviceModel],
        req: Stage3TriggerRequest,
        project_state: NetworkProjectState
    ):
        start_t = time.time()
        self.emit_event(job_id, "JOB_STARTED", {
            "job_id": job_id,
            "total_devices": len(devices),
            "scope": req.scope,
            "message": f"Starting live audit command execution across {len(devices)} device(s)..."
        })

        creds = req.credentials
        pool = ThreadPoolExecutor(max_workers=min(len(devices), 8))

        try:
            device_futures = []
            for dev in devices:
                f = pool.submit(self._execute_device_audit, job_id, dev, req, project_state, creds)
                device_futures.append(f)

            for future in as_completed(device_futures):
                try:
                    res = future.result()
                    self.jobs[job_id]["completed_devices"] += 1
                    self.jobs[job_id]["total_tasks_executed"] += res["total_tasks"]
                    self.jobs[job_id]["tasks_succeeded"] += res["succeeded"]
                    self.jobs[job_id]["tasks_failed"] += res["failed"]
                    self.jobs[job_id]["log_files"].extend(res["log_files"])
                except Exception as e:
                    logger.error(f"Error in device audit thread: {e}")

        except Exception as fatal_err:
            # Emit JOB_FAILED so frontend can handle gracefully instead of hanging
            logger.error(f"Fatal error in audit job {job_id}: {fatal_err}")
            self.jobs[job_id]["status"] = "FAILED"
            self.jobs[job_id]["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.emit_event(job_id, "JOB_FAILED", {
                "job_id": job_id,
                "error": str(fatal_err),
                "message": f"Audit job failed unexpectedly: {fatal_err}"
            })
            return

        finally:
            pool.shutdown(wait=False)

            # Ephemeral credentials memory purge
            try:
                creds.password = None
                creds.ssh_key = None
                creds.api_token = None
                creds.secret = None
                del creds
            except Exception:
                pass

            # Recompute summary task metrics in project_state
            if project_state.summary:
                total = len(project_state.device_audit_tasks)
                completed = sum(1 for t in project_state.device_audit_tasks if t.status in [
                    TaskVerificationStatus.COMPLETED, TaskVerificationStatus.NOT_APPLICABLE, TaskVerificationStatus.WARNING
                ])
                project_state.summary.total_tasks = total
                project_state.summary.completed_tasks = completed
                project_state.summary.incomplete_tasks = total - completed

        duration = round(time.time() - start_t, 2)
        self.jobs[job_id]["status"] = "COMPLETED"
        self.jobs[job_id]["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.emit_event(job_id, "JOB_COMPLETED", {
            "job_id": job_id,
            "duration_seconds": duration,
            "tasks_succeeded": self.jobs[job_id]["tasks_succeeded"],
            "tasks_failed": self.jobs[job_id]["tasks_failed"],
            "total_files": len(self.jobs[job_id]["log_files"]),
            "message": f"Audit execution finished in {duration}s. {self.jobs[job_id]['tasks_succeeded']} tasks verified, {self.jobs[job_id]['tasks_failed']} failed."
        })

    def _execute_device_audit(
        self,
        job_id: str,
        device: DeviceModel,
        req: Stage3TriggerRequest,
        project_state: NetworkProjectState,
        credentials: EphemeralCredentials
    ) -> Dict[str, Any]:
        # Filter tasks for this device
        dev_tasks = [t for t in project_state.device_audit_tasks if t.device_hostname == device.hostname]
        
        if req.scope == "section" and req.section_category:
            dev_tasks = [t for t in dev_tasks if t.category.lower() == req.section_category.lower()]
        elif req.scope == "task" and req.task_id:
            dev_tasks = [t for t in dev_tasks if t.id == req.task_id]

        summary = {
            "device": device.hostname,
            "total_tasks": len(dev_tasks),
            "succeeded": 0,
            "failed": 0,
            "log_files": []
        }

        self.emit_event(job_id, "DEVICE_STARTED", {
            "hostname": device.hostname,
            "ip_address": device.management_ip,
            "vendor": device.vendor,
            "total_tasks": len(dev_tasks)
        })

        # Connect adapter
        is_rest = "meraki" in device.vendor.lower() or "rest" in device.device_model.lower()
        if is_rest:
            adapter = RestAPIDeviceAdapter(
                hostname=device.hostname,
                ip_address=device.management_ip,
                port=443,
                vendor=device.vendor,
                model=device.device_model,
                credentials=credentials,
                timeout=req.timeout_seconds
            )
        else:
            adapter = SSHDeviceAdapter(
                hostname=device.hostname,
                ip_address=device.management_ip,
                port=22,
                vendor=device.vendor,
                model=device.device_model,
                credentials=credentials,
                timeout=req.timeout_seconds
            )

        connected, conn_err = adapter.connect()
        if not connected:
            err_class = "CONNECTION_FAILED"
            err_detail = conn_err or "Unknown connection failure"
            # Mark all tasks as failed due to connection error
            for t in dev_tasks:
                t.status = TaskVerificationStatus.FAILED
                t.actual_output = f"Connection failed to {device.management_ip}: {err_detail}"
                t.evidence_notes = f"Device unreachable or auth failed: {err_detail}"
                t.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                summary["failed"] += 1
                self.emit_event(job_id, "TASK_FAILED", {
                    "task_id": t.id,
                    "hostname": device.hostname,
                    "title": t.title,
                    "error": err_detail,
                    "error_class": err_class,
                    "failed_command": "(connection)",
                    "evidence_notes": t.evidence_notes
                })
            self.emit_event(job_id, "DEVICE_FAILED", {
                "hostname": device.hostname,
                "error": err_detail,
                "error_class": err_class,
                "message": f"Could not connect to {device.hostname} ({device.management_ip}): {err_detail}"
            })
            return summary

        # ── Role-based Command & Task Filtering ──────────────────────────────────
        # Strictly execute commands ONLY applicable to this device's role/classification
        from engine.protocol_catalog import ProtocolCatalogEngine
        applicable_protocols = ProtocolCatalogEngine.get_applicable_protocols(device)
        applicable_proto_values = {p.value.lower() for p in applicable_protocols}
        applicable_proto_names = {p.name.lower() for p in applicable_protocols}
        dev_role_val = device.device_role.value.lower() if hasattr(device.device_role, "value") else str(device.device_role).lower()

        tasks_to_execute = []
        for t in dev_tasks:
            p_low = t.protocol.lower().strip()
            # Verify protocol compatibility against device role
            is_valid_role = (
                p_low in applicable_proto_values or
                p_low.replace(" ", "_") in applicable_proto_names or
                t.device_role.lower().strip() == dev_role_val
            )
            # Enforce mutual exclusivity for security/wireless/switching domains
            if "firewall" not in dev_role_val and "firewall" in p_low:
                is_valid_role = False
            if "wireless" not in dev_role_val and "wireless" in p_low:
                is_valid_role = False
            if dev_role_val == "access" and p_low in ["ospf", "bgp", "eigrp", "isis", "hsrp", "vrrp", "bfd"]:
                is_valid_role = False

            if is_valid_role:
                tasks_to_execute.append(t)
            else:
                # Mark non-applicable task as N/A and do not run on device
                t.status = TaskVerificationStatus.NOT_APPLICABLE
                t.evidence_notes = f"N/A: Command/protocol not applicable for {device.device_role.value} role."

        dev_tasks = tasks_to_execute

        # ── Native Running Configuration Backup executes FIRST as Priority 1 ────
        def _task_sort_key(t: DeviceAuditTask) -> int:
            t_cmd = t.verification_command.lower()
            t_proto = t.protocol.lower()
            if "running config" in t_proto or "running-config" in t_cmd or "show configuration" in t_cmd or "show full-configuration" in t_cmd:
                return 0
            return 1

        dev_tasks.sort(key=_task_sort_key)

        # ── Command Execution De-duplication Cache (per device trigger run) ──────
        # Caches executed commands on this device so identical show commands are NOT repeated
        cmd_cache: Dict[str, Tuple[bool, str, Optional[str], str]] = {}

        try:
            for task in dev_tasks:
                now_dt = self._get_client_now(req.client_timezone)
                now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

                self.emit_event(job_id, "TASK_RUNNING", {
                    "task_id": task.id,
                    "hostname": device.hostname,
                    "title": task.title,
                    "command": task.verification_command
                })

                # Sub-commands separated by ';'
                sub_commands = [c.strip() for c in task.verification_command.split(";") if c.strip()]
                all_outputs = []
                cmd_evals = []

                for sub_cmd in sub_commands:
                    # De-duplication: reuse output if command already executed on this device during this trigger
                    if sub_cmd in cmd_cache:
                        cmd_ok, raw_out, cmd_err, saved_path = cmd_cache[sub_cmd]
                    else:
                        cmd_ok, raw_out, cmd_err = adapter.execute_command(sub_cmd)
                        save_output = raw_out if raw_out else (cmd_err or "(no output)")
                        saved_path = self.log_writer.save_command_output(
                            company=device.company_name or project_state.company_name or "zenquix",
                            building=device.site_location or "BLRCC002",
                            device_name=device.hostname,
                            command_executed=sub_cmd,
                            output=save_output,
                            timestamp_dt=now_dt,
                            client_timezone=req.client_timezone
                        )
                        cmd_cache[sub_cmd] = (cmd_ok, raw_out, cmd_err, saved_path)

                    if saved_path not in summary["log_files"]:
                        summary["log_files"].append(saved_path)

                    save_output = raw_out if raw_out else (cmd_err or "(no output)")
                    all_outputs.append(f"--- [ {sub_cmd} ] ---\n{save_output}")

                    # Validate output with vendor-aware patterns
                    is_valid, detected_class, err_snip = CommandValidator.is_valid_output(
                        raw_out,
                        vendor=device.vendor
                    )

                    # Classify single command outcome
                    is_empty = (not raw_out or not raw_out.strip() or detected_class == "EMPTY_OUTPUT")
                    is_error = (not cmd_ok) or (not is_valid and not is_empty)
                    is_passed = cmd_ok and is_valid and not is_empty

                    cmd_evals.append({
                        "cmd": sub_cmd,
                        "cmd_ok": cmd_ok,
                        "is_valid": is_valid,
                        "is_passed": is_passed,
                        "is_empty": is_empty,
                        "is_error": is_error,
                        "err_class": detected_class,
                        "err_snip": err_snip or cmd_err
                    })

                task.actual_output = "\n\n".join(all_outputs)
                task.timestamp = now_str

                # If this is the native running-config backup, store in project_state raw_configs
                if "running config" in task.protocol.lower() or "running-config" in task.verification_command.lower() or "configuration" in task.verification_command.lower():
                    if hasattr(project_state, "raw_configs") and task.actual_output:
                        project_state.raw_configs[device.hostname] = task.actual_output

                # ── Output Evaluation & Status Classification ──────────────────────
                # 1. Output is NONE / EMPTY on the entire task -> Mark stage as N/A
                if all(c["is_empty"] for c in cmd_evals):
                    task.status = TaskVerificationStatus.NOT_APPLICABLE
                    task.evidence_notes = f"N/A: No output returned from device (feature/protocol unconfigured or empty table) at {task.timestamp}."
                    summary["succeeded"] += 1
                    self.emit_event(job_id, "TASK_COMPLETED", {
                        "task_id": task.id,
                        "hostname": device.hostname,
                        "title": task.title,
                        "status": "N/A",
                        "command": task.verification_command,
                        "evidence_notes": task.evidence_notes
                    })

                # 2. All commands PASSED and VALID -> Mark stage as Completed
                elif all(c["is_passed"] for c in cmd_evals):
                    task.status = TaskVerificationStatus.COMPLETED
                    task.evidence_notes = f"Verified successfully via live execution at {task.timestamp}."
                    summary["succeeded"] += 1
                    self.emit_event(job_id, "TASK_COMPLETED", {
                        "task_id": task.id,
                        "hostname": device.hostname,
                        "title": task.title,
                        "status": "Completed",
                        "command": task.verification_command,
                        "evidence_notes": task.evidence_notes
                    })

                # 3. All commands returned ERROR / INVALID COMMAND -> Mark stage as Failed
                elif all(c["is_error"] for c in cmd_evals):
                    first_err = next((c for c in cmd_evals if c["is_error"]), cmd_evals[0])
                    err_class = first_err["err_class"] or "CLI_ERROR"
                    err_msg = first_err["err_snip"] or "Command execution failed validation."
                    failed_cmd = first_err["cmd"]
                    task.status = TaskVerificationStatus.FAILED
                    task.evidence_notes = f"[{err_class}] Command error on '{failed_cmd}': {err_msg}"
                    summary["failed"] += 1
                    self.emit_event(job_id, "TASK_FAILED", {
                        "task_id": task.id,
                        "hostname": device.hostname,
                        "title": task.title,
                        "status": "Failed",
                        "error": err_msg,
                        "error_class": err_class,
                        "failed_command": failed_cmd,
                        "evidence_notes": task.evidence_notes
                    })

                # 4. Partially works (some passed, some failed or not passed) -> Mark stage as Warning
                else:
                    passed_cmds = [c["cmd"] for c in cmd_evals if c["is_passed"]]
                    failed_cmds = [c["cmd"] for c in cmd_evals if not c["is_passed"]]
                    first_err = next((c for c in cmd_evals if c["is_error"]), None)
                    err_class = first_err["err_class"] if first_err else "PARTIAL_EXECUTION"
                    failed_str = ", ".join(f"'{c}'" for c in failed_cmds)
                    passed_str = ", ".join(f"'{c}'" for c in passed_cmds) if passed_cmds else "None"
                    task.status = TaskVerificationStatus.WARNING
                    task.evidence_notes = f"Warning: {failed_str} not passed or executed. Passed: {passed_str} at {task.timestamp}."
                    summary["succeeded"] += 1
                    self.emit_event(job_id, "TASK_COMPLETED", {
                        "task_id": task.id,
                        "hostname": device.hostname,
                        "title": task.title,
                        "status": "Warning",
                        "command": task.verification_command,
                        "error_class": err_class,
                        "failed_command": failed_cmds[0] if failed_cmds else "",
                        "evidence_notes": task.evidence_notes
                    })

        finally:
            adapter.disconnect()

        return summary

    def retry_task_command(
        self,
        task_id: str,
        new_command: str,
        credentials: EphemeralCredentials,
        project_state: NetworkProjectState,
        client_timezone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Live interactive test and update of a custom command for a specific task.
        """
        now_dt = self._get_client_now(client_timezone)
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

        task = next((t for t in project_state.device_audit_tasks if t.id == task_id), None)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found."}

        device = next((d for d in project_state.devices if d.hostname.lower() == task.device_hostname.lower()), None)
        if not device:
            return {"success": False, "error": f"Device {task.device_hostname} not found."}

        is_rest = "meraki" in device.vendor.lower() or "rest" in device.device_model.lower()
        if is_rest:
            adapter = RestAPIDeviceAdapter(
                hostname=device.hostname,
                ip_address=device.management_ip,
                port=443,
                vendor=device.vendor,
                model=device.device_model,
                credentials=credentials,
                timeout=25
            )
        else:
            adapter = SSHDeviceAdapter(
                hostname=device.hostname,
                ip_address=device.management_ip,
                port=22,
                vendor=device.vendor,
                model=device.device_model,
                credentials=credentials,
                timeout=25
            )

        connected, conn_err = adapter.connect()
        if not connected:
            return {"success": False, "error": f"Connection failed: {conn_err}"}

        try:
            sub_commands = [c.strip() for c in new_command.split(";") if c.strip()]
            all_outputs = []
            cmd_evals = []
            saved_path = ""

            for sub_cmd in sub_commands:
                ok, raw_out, err = adapter.execute_command(sub_cmd)
                is_valid, err_class, err_snip = CommandValidator.is_valid_output(
                    raw_out,
                    vendor=device.vendor
                )
                save_output = raw_out if raw_out else (err or "(no output received)")
                saved_path = self.log_writer.save_command_output(
                    company=device.company_name or project_state.company_name or "zenquix",
                    building=device.site_location or "BLRCC002",
                    device_name=device.hostname,
                    command_executed=sub_cmd,
                    output=save_output,
                    timestamp_dt=now_dt,
                    client_timezone=client_timezone
                )
                all_outputs.append(f"--- [ {sub_cmd} ] ---\n{save_output}")

                is_empty = (not raw_out or not raw_out.strip() or err_class == "EMPTY_OUTPUT")
                is_error = (not ok) or (not is_valid and not is_empty)
                is_passed = ok and is_valid and not is_empty

                cmd_evals.append({
                    "cmd": sub_cmd,
                    "ok": ok,
                    "is_valid": is_valid,
                    "is_passed": is_passed,
                    "is_empty": is_empty,
                    "is_error": is_error,
                    "err_class": err_class,
                    "err_snip": err_snip or err
                })

            task.verification_command = new_command
            task.actual_output = "\n\n".join(all_outputs)
            task.timestamp = now_str

            # Update raw_configs if retrying the running-config backup task
            if "running config" in task.protocol.lower() or "running-config" in task.verification_command.lower() or "configuration" in task.verification_command.lower():
                if hasattr(project_state, "raw_configs") and task.actual_output:
                    project_state.raw_configs[device.hostname] = task.actual_output

            if all(c["is_empty"] for c in cmd_evals):
                task.status = TaskVerificationStatus.NOT_APPLICABLE
                task.evidence_notes = f"N/A: No output received from device at {task.timestamp}."
                status_str = "N/A"
                success = True
                ret_err = None
                ret_err_class = None
            elif all(c["is_passed"] for c in cmd_evals):
                task.status = TaskVerificationStatus.COMPLETED
                task.evidence_notes = f"Updated and verified successfully via UI retry at {task.timestamp}."
                status_str = "Completed"
                success = True
                ret_err = None
                ret_err_class = None
            elif all(c["is_error"] for c in cmd_evals):
                first_err = next((c for c in cmd_evals if c["is_error"]), cmd_evals[0])
                ret_err_class = first_err["err_class"] or "EXEC_ERROR"
                ret_err = first_err["err_snip"] or "Output failed validation"
                task.status = TaskVerificationStatus.FAILED
                task.evidence_notes = f"[{ret_err_class}] Retry error on '{first_err['cmd']}': {ret_err}"
                status_str = "Failed"
                success = False
            else:
                passed_cmds = [c["cmd"] for c in cmd_evals if c["is_passed"]]
                failed_cmds = [c["cmd"] for c in cmd_evals if not c["is_passed"]]
                task.status = TaskVerificationStatus.WARNING
                task.evidence_notes = f"Warning: ({', '.join(failed_cmds)}) not passed or executed. Passed: ({', '.join(passed_cmds)}) at {task.timestamp}."
                status_str = "Warning"
                success = True
                ret_err = None
                ret_err_class = None

            # Recompute summary metrics
            if project_state.summary:
                total = len(project_state.device_audit_tasks)
                completed = sum(1 for t in project_state.device_audit_tasks if t.status in [
                    TaskVerificationStatus.COMPLETED, TaskVerificationStatus.NOT_APPLICABLE, TaskVerificationStatus.WARNING
                ])
                project_state.summary.total_tasks = total
                project_state.summary.completed_tasks = completed
                project_state.summary.incomplete_tasks = total - completed

            return {
                "success": success,
                "task_id": task_id,
                "status": status_str,
                "new_command": new_command,
                "output": task.actual_output,
                "saved_file": saved_path,
                "evidence_notes": task.evidence_notes,
                "error_class": ret_err_class,
                "error": ret_err
            }

        finally:
            adapter.disconnect()
            try:
                credentials.password = None
                credentials.ssh_key = None
                credentials.api_token = None
                credentials.secret = None
                del credentials
            except Exception:
                pass

