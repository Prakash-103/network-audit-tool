from abc import ABC, abstractmethod
from typing import Tuple, Optional
from core.collector.models import EphemeralCredentials

class BaseDeviceAdapter(ABC):
    def __init__(self, hostname: str, ip_address: str, port: int, vendor: str, model: str, credentials: EphemeralCredentials, timeout: int = 30):
        self.hostname = hostname
        self.ip_address = ip_address
        self.port = port
        self.vendor = vendor
        self.model = model
        self.credentials = credentials
        self.timeout = timeout
        self.is_connected = False

    @abstractmethod
    def connect(self) -> Tuple[bool, Optional[str]]:
        pass

    @abstractmethod
    def execute_command(self, command: str) -> Tuple[bool, str, Optional[str]]:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass
