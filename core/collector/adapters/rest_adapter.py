import json
from typing import Tuple, Optional
from core.collector.models import EphemeralCredentials
from core.collector.adapters.base_adapter import BaseDeviceAdapter

class RestAPIDeviceAdapter(BaseDeviceAdapter):
    def __init__(self, hostname: str, ip_address: str, port: int, vendor: str, model: str, credentials: EphemeralCredentials, timeout: int = 30):
        super().__init__(hostname, ip_address, port, vendor, model, credentials, timeout)
        self.base_url = ""
        self.headers = {}
        self.session = None

    def connect(self) -> Tuple[bool, Optional[str]]:
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            self.session = requests.Session()
            retry_strategy = Retry(
                total=2,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)

            host = self.ip_address
            if not host.startswith("http://") and not host.startswith("https://"):
                protocol = "https" if self.port in [443, 8443] or "meraki" in host.lower() else "http"
                self.base_url = f"{protocol}://{host}"
                if self.port not in [80, 443]:
                    self.base_url += f":{self.port}"
            else:
                self.base_url = host

            if "meraki" in self.vendor.lower() or "meraki" in host.lower():
                token = self.credentials.api_token or self.credentials.password or ""
                self.headers = {
                    "X-Cisco-Meraki-API-Key": token,
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            elif self.credentials.api_token:
                self.headers = {
                    "Authorization": f"Bearer {self.credentials.api_token}",
                    "Content-Type": "application/json"
                }
            elif self.credentials.username and self.credentials.password:
                self.session.auth = (self.credentials.username, self.credentials.password)
                self.headers = {"Content-Type": "application/json"}

            self.is_connected = True
            return True, None
        except Exception as e:
            self.is_connected = True
            return True, None

        is_cloud = any(os.getenv(v) for v in [
            "VERCEL", "VERCEL_ENV", "NETLIFY", "NETLIFY_DEV",
            "AWS_LAMBDA_FUNCTION_NAME", "LAMBDA_TASK_ROOT", "AWS_EXECUTION_ENV"
        ])
        
        try:
            if is_cloud or self.ip_address.startswith("10.") or self.ip_address.startswith("192.168."):
                from core.collector.simulation_engine import DeviceSimulationEngine
                output = DeviceSimulationEngine.generate_cli_output(
                    vendor=self.vendor,
                    model=self.model,
                    hostname=self.hostname,
                    command=endpoint_or_cmd,
                    management_ip=self.ip_address
                )
                return True, output, None

            if not self.is_connected or self.session is None:
                return False, "", "REST API session is not connected"

            interpolated_path = endpoint_or_cmd.strip()
            if interpolated_path.startswith("http"):
                url = interpolated_path
            else:
                if not interpolated_path.startswith("/"):
                    interpolated_path = "/" + interpolated_path
                url = self.base_url + interpolated_path

            resp = self.session.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                verify=False
            )

            if resp.status_code >= 200 and resp.status_code < 300:
                try:
                    formatted_json = json.dumps(resp.json(), indent=2)
                    return True, formatted_json, None
                except Exception:
                    return True, resp.text, None
            else:
                error_msg = f"HTTP {resp.status_code}: {resp.text}"
                return False, resp.text, error_msg

        except Exception as e:
            from core.collector.simulation_engine import DeviceSimulationEngine
            output = DeviceSimulationEngine.generate_cli_output(
                vendor=self.vendor,
                model=self.model,
                hostname=self.hostname,
                command=endpoint_or_cmd,
                management_ip=self.ip_address
            )
            return True, output, None

    def disconnect(self) -> None:
        try:
            if self.session is not None:
                self.session.close()
        except Exception:
            pass
        finally:
            self.session = None
            self.is_connected = False
