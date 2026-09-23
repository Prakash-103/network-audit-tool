import os
import re
import json
import zipfile
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from core.collector.validator import CommandValidator

import tempfile

def _resolve_base_files_dir() -> str:
    is_serverless = any(os.getenv(v) for v in [
        "VERCEL", "VERCEL_ENV", "NETLIFY", "NETLIFY_DEV",
        "AWS_LAMBDA_FUNCTION_NAME", "LAMBDA_TASK_ROOT", "AWS_EXECUTION_ENV"
    ])
    if is_serverless:
        tmp_dir = os.path.join(tempfile.gettempdir(), "files")
        try:
            os.makedirs(tmp_dir, exist_ok=True)
            return tmp_dir
        except Exception:
            pass

    local_dir = os.path.join(os.getcwd(), "files")
    try:
        os.makedirs(local_dir, exist_ok=True)
        return local_dir
    except (OSError, PermissionError):
        tmp_dir = os.path.join(tempfile.gettempdir(), "files")
        try:
            os.makedirs(tmp_dir, exist_ok=True)
            return tmp_dir
        except Exception:
            return local_dir

BASE_FILES_DIR = _resolve_base_files_dir()

def get_timezone_aware_now(client_timezone: Optional[str] = None) -> datetime:
    if client_timezone:
        try:
            import zoneinfo
            return datetime.now(zoneinfo.ZoneInfo(client_timezone))
        except Exception:
            pass
    return datetime.now()

class LogWriter:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or _resolve_base_files_dir()
        try:
            os.makedirs(self.base_dir, exist_ok=True)
        except Exception:
            # Fallback to temp directory if read-only filesystem
            self.base_dir = os.path.join(tempfile.gettempdir(), "files")
            try:
                os.makedirs(self.base_dir, exist_ok=True)
            except Exception:
                pass

    def _sanitize_path_component(self, name: str) -> str:
        if not name:
            return "default"
        clean = re.sub(r'[<>:"/\\|?*]', '_', name.strip())
        return re.sub(r'\s+', '_', clean)

    def get_device_dir(self, company: str, building: str, device_name: str, date_str: Optional[str] = None, client_timezone: Optional[str] = None) -> str:
        """
        Constructs the hierarchical path:
        files/<companyname>/<building>/<date>/<device>/
        """
        if date_str is None:
            date_str = get_timezone_aware_now(client_timezone).strftime("%Y%m%d")

        comp_clean = self._sanitize_path_component(company)
        bldg_clean = self._sanitize_path_component(building)
        dev_clean = self._sanitize_path_component(device_name)

        device_dir = os.path.join(self.base_dir, comp_clean, bldg_clean, date_str, dev_clean)
        try:
            os.makedirs(device_dir, exist_ok=True)
        except Exception:
            # Fallback to system temp folder
            fallback_dir = os.path.join(tempfile.gettempdir(), "files", comp_clean, bldg_clean, date_str, dev_clean)
            try:
                os.makedirs(fallback_dir, exist_ok=True)
                device_dir = fallback_dir
            except Exception:
                pass
        return device_dir

    def save_command_output(
        self,
        company: str,
        building: str,
        device_name: str,
        command_executed: str,
        output: str,
        timestamp_dt: Optional[datetime] = None,
        client_timezone: Optional[str] = None
    ) -> str:
        """
        Saves command output to:
        files/<companyname>/<building>/<date>/<device>/sh_(cmd)_HHMMSS.cfg
        """
        if timestamp_dt is None:
            timestamp_dt = get_timezone_aware_now(client_timezone)

        date_str = timestamp_dt.strftime("%Y%m%d")
        time_str = timestamp_dt.strftime("%H%M%S")

        device_dir = self.get_device_dir(company, building, device_name, date_str, client_timezone=client_timezone)
        clean_cmd_name = CommandValidator.sanitize_filename_cmd(command_executed)

        filename = f"{clean_cmd_name}_{time_str}.cfg"
        filepath = os.path.join(device_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8", errors="replace") as f:
                f.write(output)
        except Exception:
            # If filesystem write fails on serverless, write to /tmp or return virtual path
            try:
                alt_dir = os.path.join(tempfile.gettempdir(), "files")
                os.makedirs(alt_dir, exist_ok=True)
                filepath = os.path.join(alt_dir, filename)
                with open(filepath, "w", encoding="utf-8", errors="replace") as f:
                    f.write(output)
            except Exception:
                return f"files/{self._sanitize_path_component(company)}/{self._sanitize_path_component(building)}/{date_str}/{self._sanitize_path_component(device_name)}/{filename}"

        return filepath

    def create_zip_archive(self, identifier: str = "all", target_device: Optional[str] = None) -> str:
        """
        Creates a ZIP archive containing the collected logs for download.
        """
        zip_filename = f"audit_logs_{identifier}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join(self.base_dir, zip_filename)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.base_dir):
                for file in files:
                    if not file.endswith('.zip'):
                        full_path = os.path.join(root, file)
                        if target_device:
                            if target_device.lower() not in full_path.lower():
                                continue
                        arcname = os.path.relpath(full_path, self.base_dir)
                        zipf.write(full_path, arcname)

        return zip_path
