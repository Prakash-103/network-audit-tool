"""
Catalog Manager Engine.
Provides modular, code-independent management of Vendor Platform profiles,
Port interface naming rules, and dynamic Audit Test Scenarios with multi-vendor CLI verification commands.
"""
import json
import os
import sys
from typing import List, Dict, Any, Optional

# Base directory resolution (works in local dev and serverless Vercel)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
VENDOR_CATALOG_FILE = os.path.join(CONFIG_DIR, "vendor_catalog.json")
TEST_SCENARIOS_FILE = os.path.join(CONFIG_DIR, "test_scenarios.json")

# Fallback default vendor catalog if files cannot be read
DEFAULT_VENDOR_CATALOG = {
    "vendors": [
        {
            "name": "Cisco",
            "display_name": "Cisco Systems",
            "platforms": ["Catalyst 9300", "Catalyst 9500", "Catalyst 9200", "Nexus 9000", "ISR 4451-X"],
            "default_os_version": "IOS-XE 17.9",
            "port_prefix": "GigabitEthernet1/0/",
            "default_port_type": "GigabitEthernet",
            "supported_speeds": ["1G", "10G", "25G", "40G", "100G", "400G"],
            "cli_prompt_suffix": "#"
        },
        {
            "name": "Arista",
            "display_name": "Arista Networks",
            "platforms": ["DCS-7050SX3", "DCS-7280R3", "DCS-7060CX", "DCS-7150S"],
            "default_os_version": "EOS 4.28",
            "port_prefix": "Ethernet",
            "default_port_type": "Ethernet",
            "supported_speeds": ["1G", "10G", "25G", "40G", "100G", "400G"],
            "cli_prompt_suffix": "#"
        },
        {
            "name": "Juniper",
            "display_name": "Juniper Networks",
            "platforms": ["QFX5100", "QFX5200", "EX4300", "EX3400", "MX204", "SRX345"],
            "default_os_version": "Junos 21.4R1",
            "port_prefix": "ge-0/0/",
            "default_port_type": "GigabitEthernet",
            "supported_speeds": ["1G", "10G", "25G", "40G", "100G"],
            "cli_prompt_suffix": ">"
        },
        {
            "name": "Palo Alto",
            "display_name": "Palo Alto Networks",
            "platforms": ["PA-3220", "PA-5220", "PA-850", "PA-440", "PA-1410"],
            "default_os_version": "PAN-OS 10.2",
            "port_prefix": "Port",
            "default_port_type": "GigabitEthernet",
            "supported_speeds": ["1G", "10G", "40G", "100G"],
            "cli_prompt_suffix": ">"
        },
        {
            "name": "Fortinet",
            "display_name": "Fortinet FortiGate",
            "platforms": ["FortiGate 100F", "FortiGate 200F", "FortiGate 60F", "FortiGate 600E"],
            "default_os_version": "FortiOS 7.2",
            "port_prefix": "port",
            "default_port_type": "GigabitEthernet",
            "supported_speeds": ["1G", "10G", "25G", "40G", "100G"],
            "cli_prompt_suffix": "#"
        },
        {
            "name": "Aruba",
            "display_name": "Aruba / HPE",
            "platforms": ["CX 6300", "CX 8325", "AP-515", "AP-535", "7210 Mobility Controller"],
            "default_os_version": "AOS-CX 10.10",
            "port_prefix": "1/1/",
            "default_port_type": "GigabitEthernet",
            "supported_speeds": ["1G", "10G", "25G", "40G", "100G"],
            "cli_prompt_suffix": "#"
        },
        {
            "name": "Huawei",
            "display_name": "Huawei Enterprise",
            "platforms": ["CloudEngine 6800", "S5735", "AR6140 Router", "USG6600 Firewall"],
            "default_os_version": "VRP V200R019",
            "port_prefix": "10GE1/0/",
            "default_port_type": "10GE",
            "supported_speeds": ["1G", "10G", "25G", "40G", "100G"],
            "cli_prompt_suffix": ">"
        }
    ]
}


class CatalogManager:
    """
    Singleton-style manager for Vendor & Test Scenario catalogs.
    """
    _vendor_catalog: Optional[Dict[str, Any]] = None
    _test_scenarios: Optional[Dict[str, Any]] = None

    @classmethod
    def initialize(cls) -> None:
        """Load catalogs from disk or set defaults."""
        cls.load_vendor_catalog()
        cls.load_test_scenarios()

    # ---------------------------------------------------------
    # Vendor Catalog Management
    # ---------------------------------------------------------
    @classmethod
    def load_vendor_catalog(cls) -> Dict[str, Any]:
        """Load vendor catalog from config/vendor_catalog.json."""
        if os.path.exists(VENDOR_CATALOG_FILE):
            try:
                with open(VENDOR_CATALOG_FILE, "r", encoding="utf-8") as f:
                    cls._vendor_catalog = json.load(f)
                    return cls._vendor_catalog
            except Exception as e:
                print(f"[CatalogManager] Warning: Failed to parse {VENDOR_CATALOG_FILE}: {e}")

        cls._vendor_catalog = json.loads(json.dumps(DEFAULT_VENDOR_CATALOG))
        return cls._vendor_catalog

    @classmethod
    def get_vendor_catalog(cls) -> Dict[str, Any]:
        if cls._vendor_catalog is None:
            return cls.load_vendor_catalog()
        return cls._vendor_catalog

    @classmethod
    def save_vendor_catalog(cls, data: Dict[str, Any]) -> bool:
        """Persist vendor catalog to disk."""
        cls._vendor_catalog = data
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(VENDOR_CATALOG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"[CatalogManager] Notice: Could not write {VENDOR_CATALOG_FILE} (e.g. read-only env): {e}")
            return False

    @classmethod
    def get_vendors(cls) -> List[Dict[str, Any]]:
        return cls.get_vendor_catalog().get("vendors", [])

    @classmethod
    def get_vendor(cls, vendor_name: str) -> Optional[Dict[str, Any]]:
        target = (vendor_name or "").lower().strip()
        for v in cls.get_vendors():
            if v.get("name", "").lower() == target or v.get("display_name", "").lower() == target:
                return v
        return None

    @classmethod
    def get_vendor_port_prefix(cls, vendor_name: str) -> str:
        """Returns port interface prefix for auto-generating interface names."""
        v = cls.get_vendor(vendor_name)
        if v and v.get("port_prefix"):
            return v["port_prefix"]
        
        # Fallback keyword match
        v_low = (vendor_name or "").lower()
        if "arista" in v_low:
            return "Ethernet"
        elif "juniper" in v_low:
            return "ge-0/0/"
        elif "cisco" in v_low:
            return "GigabitEthernet1/0/"
        elif "fortinet" in v_low:
            return "port"
        elif "aruba" in v_low:
            return "1/1/"
        elif "huawei" in v_low:
            return "10GE1/0/"
        elif "mikrotik" in v_low:
            return "ether"
        elif "dell" in v_low:
            return "ethernet1/1/"
        return "Port"

    @classmethod
    def add_or_update_vendor(cls, vendor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new vendor or update existing one."""
        catalog = cls.get_vendor_catalog()
        vendors = catalog.setdefault("vendors", [])
        v_name = vendor_data.get("name", "").strip()
        if not v_name:
            raise ValueError("Vendor 'name' is required.")

        updated = False
        for i, existing in enumerate(vendors):
            if existing.get("name", "").lower() == v_name.lower():
                vendors[i] = {**existing, **vendor_data}
                updated = True
                break

        if not updated:
            vendors.append(vendor_data)

        cls.save_vendor_catalog(catalog)

        # Synchronize test scenarios to ensure testcase fields exist for this vendor
        scenarios_catalog = cls.get_test_scenarios_catalog()
        scenarios = scenarios_catalog.get("scenarios", [])
        scenarios_modified = False
        for scen in scenarios:
            v_cmds = scen.setdefault("vendor_commands", {})
            has_vendor = any(k.lower() == v_name.lower() for k in v_cmds.keys())
            if not has_vendor:
                default_cmd = v_cmds.get("Default", "show running-config")
                v_cmds[v_name] = default_cmd
                scenarios_modified = True

        if scenarios_modified:
            cls.save_test_scenarios(scenarios_catalog)

        return vendor_data

    @classmethod
    def delete_vendor(cls, vendor_name: str) -> bool:
        """Delete a vendor from catalog."""
        catalog = cls.get_vendor_catalog()
        vendors = catalog.get("vendors", [])
        v_name = vendor_name.lower().strip()
        initial_len = len(vendors)
        catalog["vendors"] = [v for v in vendors if v.get("name", "").lower() != v_name]
        
        if len(catalog["vendors"]) < initial_len:
            cls.save_vendor_catalog(catalog)
            # Also remove deleted vendor from test scenarios
            scenarios_catalog = cls.get_test_scenarios_catalog()
            scenarios = scenarios_catalog.get("scenarios", [])
            scen_modified = False
            for scen in scenarios:
                v_cmds = scen.get("vendor_commands", {})
                matching_keys = [k for k in v_cmds.keys() if k.lower() == v_name]
                for k in matching_keys:
                    del v_cmds[k]
                    scen_modified = True
            if scen_modified:
                cls.save_test_scenarios(scenarios_catalog)
            return True
        return False

    # ---------------------------------------------------------
    # Test Scenario Management
    # ---------------------------------------------------------
    @classmethod
    def load_test_scenarios(cls) -> Dict[str, Any]:
        """Load test scenarios from config/test_scenarios.json."""
        if os.path.exists(TEST_SCENARIOS_FILE):
            try:
                with open(TEST_SCENARIOS_FILE, "r", encoding="utf-8") as f:
                    cls._test_scenarios = json.load(f)
                    return cls._test_scenarios
            except Exception as e:
                print(f"[CatalogManager] Warning: Failed to parse {TEST_SCENARIOS_FILE}: {e}")

        cls._test_scenarios = {"scenarios": []}
        return cls._test_scenarios

    @classmethod
    def get_test_scenarios_catalog(cls) -> Dict[str, Any]:
        if cls._test_scenarios is None:
            return cls.load_test_scenarios()
        return cls._test_scenarios

    @classmethod
    def save_test_scenarios(cls, data: Dict[str, Any]) -> bool:
        """Persist test scenarios to disk."""
        cls._test_scenarios = data
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(TEST_SCENARIOS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"[CatalogManager] Notice: Could not write {TEST_SCENARIOS_FILE} (e.g. read-only env): {e}")
            return False

    @classmethod
    def get_scenarios(cls) -> List[Dict[str, Any]]:
        return cls.get_test_scenarios_catalog().get("scenarios", [])

    @classmethod
    def get_scenario(cls, scenario_id: str) -> Optional[Dict[str, Any]]:
        s_id = (scenario_id or "").lower().strip()
        for s in cls.get_scenarios():
            if s.get("id", "").lower() == s_id:
                return s
        return None

    @classmethod
    def get_vendor_cli_command(cls, scenario_id: str, vendor: str) -> str:
        """
        Dynamically lookup the vendor CLI verification command for a scenario.
        Falls back to 'Default' or generic show running-config.
        """
        scenario = cls.get_scenario(scenario_id)
        if not scenario:
            return "show running-config"

        commands = scenario.get("vendor_commands", {})
        v_low = (vendor or "Cisco").lower()

        # Check exact key match
        for k, cmd in commands.items():
            if k.lower() == v_low:
                return cmd

        # Check partial keyword match (e.g. "palo", "juniper", "cisco")
        for k, cmd in commands.items():
            if k.lower() in v_low or v_low in k.lower():
                return cmd

        # Fallback to Default or first command
        if "Default" in commands:
            return commands["Default"]
        elif commands:
            return next(iter(commands.values()))
        return "show running-config"

    @classmethod
    def add_or_update_scenario(cls, scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add or update a test scenario."""
        catalog = cls.get_test_scenarios_catalog()
        scenarios = catalog.setdefault("scenarios", [])
        s_id = scenario_data.get("id", "").strip()
        if not s_id:
            # Auto-generate ID if missing
            s_id = f"TS-{len(scenarios) + 1:03d}"
            scenario_data["id"] = s_id

        updated = False
        for i, existing in enumerate(scenarios):
            if existing.get("id", "").lower() == s_id.lower():
                scenarios[i] = {**existing, **scenario_data}
                updated = True
                break

        if not updated:
            scenarios.append(scenario_data)

        cls.save_test_scenarios(catalog)
        return scenario_data

    @classmethod
    def delete_scenario(cls, scenario_id: str) -> bool:
        """Delete a scenario by ID."""
        catalog = cls.get_test_scenarios_catalog()
        scenarios = catalog.get("scenarios", [])
        s_id = scenario_id.lower().strip()
        initial_len = len(scenarios)
        catalog["scenarios"] = [s for s in scenarios if s.get("id", "").lower() != s_id]
        
        if len(catalog["scenarios"]) < initial_len:
            cls.save_test_scenarios(catalog)
            return True
        return False

    @classmethod
    def reset_to_defaults(cls) -> None:
        """Reset catalogs to factory presets."""
        cls.save_vendor_catalog(DEFAULT_VENDOR_CATALOG)
        cls.load_test_scenarios()


# Auto-initialize on import
CatalogManager.initialize()
