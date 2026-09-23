"""
Test Suite for Modular Catalog Manager & Dynamic Test Scenarios.
Validates vendor profile CRUD, port prefix generation, test scenario management,
and multi-vendor CLI verification command resolution.
"""
import unittest
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.catalog_manager import CatalogManager
from engine.protocol_catalog import ProtocolCatalogEngine
from core.models import DeviceModel
from core.constants import DeviceFunction, DeviceRole

class TestCatalogManager(unittest.TestCase):
    def setUp(self):
        CatalogManager.initialize()

    def test_vendor_catalog_loading(self):
        vendors = CatalogManager.get_vendors()
        self.assertGreater(len(vendors), 0)
        vendor_names = [v["name"] for v in vendors]
        self.assertIn("Cisco", vendor_names)
        self.assertIn("Juniper", vendor_names)
        self.assertIn("Arista", vendor_names)
        self.assertIn("Palo Alto", vendor_names)

    def test_dynamic_port_prefix_generation(self):
        cisco_dev = DeviceModel(
            device_id="TEST-01", hostname="TEST-SW01", vendor="Cisco", num_ports=4
        )
        self.assertEqual(cisco_dev.ports, ["GigabitEthernet1/0/1", "GigabitEthernet1/0/2", "GigabitEthernet1/0/3", "GigabitEthernet1/0/4"])

        arista_dev = DeviceModel(
            device_id="TEST-02", hostname="TEST-LEAF01", vendor="Arista", num_ports=2
        )
        self.assertEqual(arista_dev.ports, ["Ethernet1", "Ethernet2"])

        huawei_dev = DeviceModel(
            device_id="TEST-03", hostname="TEST-CORE01", vendor="Huawei", num_ports=2
        )
        self.assertEqual(huawei_dev.ports, ["10GE1/0/1", "10GE1/0/2"])

    def test_add_and_delete_vendor(self):
        custom_vendor = {
            "name": "AcmeNet",
            "display_name": "Acme Enterprise Networks",
            "platforms": ["Acme-Switch-100", "Acme-Router-200"],
            "default_os_version": "AcmeOS 1.0",
            "port_prefix": "ge-1/",
            "default_port_type": "GigabitEthernet",
            "supported_speeds": ["1G", "10G"]
        }
        CatalogManager.add_or_update_vendor(custom_vendor)
        v = CatalogManager.get_vendor("AcmeNet")
        self.assertIsNotNone(v)
        self.assertEqual(v["port_prefix"], "ge-1/")

        # Test that existing scenarios now include AcmeNet in their vendor_commands
        scenarios = CatalogManager.get_scenarios()
        self.assertGreater(len(scenarios), 0)
        for s in scenarios:
            self.assertIn("AcmeNet", s.get("vendor_commands", {}))

        # Test device port creation with new vendor
        dev = DeviceModel(device_id="ACME-01", hostname="ACME-SW", vendor="AcmeNet", num_ports=3)
        self.assertEqual(dev.ports, ["ge-1/1", "ge-1/2", "ge-1/3"])

        # Delete vendor
        CatalogManager.delete_vendor("AcmeNet")
        self.assertIsNone(CatalogManager.get_vendor("AcmeNet"))

    def test_test_scenario_management_and_cli_commands(self):
        # Create a custom test scenario
        custom_scenario = {
            "id": "TS-TEST-BGP-ROUTE-REFLECTOR",
            "protocol": "BGP",
            "category": "Layer 3 Routing",
            "title": "BGP Route Reflector Cluster & Client Status",
            "description": "Verify BGP Route-Reflector cluster ID and advertised client reflection rules.",
            "condition": "BGP Configured",
            "severity": "Critical",
            "vendor_commands": {
                "Cisco": "show ip bgp cluster-ids; show ip bgp update-group",
                "Juniper": "show bgp group route-reflector",
                "Arista": "show ip bgp summary | grep RR",
                "Default": "show ip bgp"
            }
        }
        CatalogManager.add_or_update_scenario(custom_scenario)

        # Test CLI command resolution for different vendors
        cisco_cmd = CatalogManager.get_vendor_cli_command("TS-TEST-BGP-ROUTE-REFLECTOR", "Cisco")
        self.assertEqual(cisco_cmd, "show ip bgp cluster-ids; show ip bgp update-group")

        juniper_cmd = CatalogManager.get_vendor_cli_command("TS-TEST-BGP-ROUTE-REFLECTOR", "Juniper")
        self.assertEqual(juniper_cmd, "show bgp group route-reflector")

        unknown_cmd = CatalogManager.get_vendor_cli_command("TS-TEST-BGP-ROUTE-REFLECTOR", "GenericVendor")
        self.assertEqual(unknown_cmd, "show ip bgp")

        # Verify ProtocolCatalogEngine generates task for this custom scenario
        dev = DeviceModel(device_id="D-01", hostname="CORE-BGP-01", vendor="Cisco", device_role=DeviceRole.CORE)
        tasks = ProtocolCatalogEngine.generate_audit_tasks(dev)
        task_ids = [t.id for t in tasks]
        self.assertIn("TASK-CORE-BGP-01-TS-TEST-BGP-ROUTE-REFLECTOR", task_ids)

        # Clean up
        CatalogManager.delete_scenario("TS-TEST-BGP-ROUTE-REFLECTOR")

if __name__ == "__main__":
    unittest.main()
