from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class DeviceInventoryItem(BaseModel):
    id: str
    company: str = "Zenquix Enterprise"
    site: str = "BLRCC002_Bangalore"
    device_name: str
    ip_address: str
    port: int = 22
    vendor: str
    model: str
    adapter_type: str = "ssh" # "ssh" or "rest_api"
    command_template: Optional[str] = None
    extra_params: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)

class EphemeralCredentials(BaseModel):
    auth_type: str = "password" # "password", "key", "api_token"
    username: Optional[str] = None
    password: Optional[str] = None
    secret: Optional[str] = None # Enable password if needed
    ssh_key: Optional[str] = None
    passphrase: Optional[str] = None
    api_token: Optional[str] = None

class CommandItem(BaseModel):
    name: str
    primary: str
    fallbacks: List[str] = Field(default_factory=list)
    description: str = ""
    category: str = "general"

class CommandTemplate(BaseModel):
    vendor: str
    model: str
    adapter_type: str = "ssh"
    device_type: str = "generic_termserver"
    error_patterns: List[str] = Field(default_factory=list)
    commands: List[CommandItem] = Field(default_factory=list)

class Stage3TriggerRequest(BaseModel):
    scope: str = "all" # "all", "device", "section", "task"
    hostname: Optional[str] = None
    section_category: Optional[str] = None
    task_id: Optional[str] = None
    credentials: EphemeralCredentials
    max_workers: int = 4
    timeout_seconds: int = 35
    project_state: Optional[Dict[str, Any]] = None
    client_timezone: Optional[str] = None

class Stage3RetryTaskRequest(BaseModel):
    task_id: str
    new_command: str
    credentials: EphemeralCredentials
    project_state: Optional[Dict[str, Any]] = None
    client_timezone: Optional[str] = None

class CommandResult(BaseModel):
    command_name: str
    command_executed: str
    status: str # "SUCCESS", "FAILED", "FALLBACK_SUCCESS", "SKIPPED"
    output: str = ""
    error_message: Optional[str] = None
    is_fallback: bool = False
    saved_filepath: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
