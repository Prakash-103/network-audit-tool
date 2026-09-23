"""
Verification script for Catalog Studio and Add Device fixes.
"""
import unittest
import os
import json
import re
from fastapi.testclient import TestClient

from app import app
from engine.catalog_manager import CatalogManager

class TestCatalogAndAddDeviceFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        CatalogManager.initialize()

    def test_catalog_html_structure(self):
        """Verify HTML changes: tabs order, dynamic modalVendorCmdsList, and devModelSelect."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # 1. Verify Vendor tab is first and Scenario tab is second
        vendors_pos = html.find('id="tabBtnVendors"')
        scenarios_pos = html.find('id="tabBtnScenarios"')
        self.assertNotEqual(vendors_pos, -1, "tabBtnVendors must be in HTML")
        self.assertNotEqual(scenarios_pos, -1, "tabBtnScenarios must be in HTML")
        self.assertLess(vendors_pos, scenarios_pos, "tabBtnVendors must precede tabBtnScenarios")

        # Verify active class on tabBtnVendors by default
        self.assertIn('class="catalog-tab-btn active" id="tabBtnVendors"', html)

        # 2. Verify dynamic container for vendor commands
        self.assertIn('id="modalVendorCmdsList"', html)
        # Verify hardcoded vendor input IDs are removed from HTML
        self.assertNotIn('id="modalCmdCisco"', html)
        self.assertNotIn('id="modalCmdArista"', html)

        # 3. Verify Hardware Model is a select dropdown in Add Device
        self.assertIn('id="devModelSelect"', html)
        self.assertIn('id="devModelCustomInput"', html)
        # Verify old text input devModelInput is replaced
        self.assertNotIn('id="devModelInput"', html)

    def test_vendor_addition_syncs_to_all_scenarios(self):
        """Verify requirement: if vendor added, make sure testcase fields for vendors also included for that vendor."""
        # Add a custom vendor
        new_vendor = {
            "name": "ExtremeNet",
            "display_name": "Extreme Networks",
            "platforms": ["ExtremeSwitch-X440", "ExtremeSwitch-X670"],
            "default_os_version": "ExtremeXOS 31.5",
            "port_prefix": "1:",
            "default_port_type": "GigabitEthernet",
            "supported_speeds": ["10G", "40G", "100G"]
        }
        res = self.client.post("/api/catalog/vendors", json=new_vendor)
        self.assertEqual(res.status_code, 200)

        # Verify all scenarios now have ExtremeNet in their vendor_commands
        scenarios_res = self.client.get("/api/catalog/scenarios")
        self.assertEqual(scenarios_res.status_code, 200)
        data = scenarios_res.json()
        scenarios = data.get("scenarios", [])
        self.assertGreater(len(scenarios), 0)

        for s in scenarios:
            v_cmds = s.get("vendor_commands", {})
            self.assertIn("ExtremeNet", v_cmds, f"Scenario {s['id']} should include ExtremeNet")
            # Should have fallen back to default show command or non-empty string
            self.assertTrue(len(v_cmds["ExtremeNet"]) > 0)

        # Clean up vendor
        del_res = self.client.delete("/api/catalog/vendors/ExtremeNet")
        self.assertEqual(del_res.status_code, 200)

    def test_device_creation_with_catalog_model_and_speed(self):
        """Verify adding a device with hardware model and speed works as expected."""
        dev_payload = {
            "device_id": "TEST-DEV-SPEED-01",
            "hostname": "EDGE-SW99",
            "company_name": "zenquix",
            "vendor": "Aruba",
            "device_model": "CX 6300",
            "os_version": "AOS-CX 10.10",
            "device_function": "L2/L3",
            "device_role": "Access",
            "num_ports": 24,
            "port_speed": "10G",
            "management_ip": "10.254.99.1",
            "site_location": "BLRCC002",
            "serial_number": "SN-TEST-ARUBA-01",
            "lifecycle_status": "Active"
        }
        res = self.client.post("/api/devices", json=dev_payload)
        self.assertEqual(res.status_code, 200)
        state = res.json()
        devs = state.get("devices", [])
        created = next((d for d in devs if d.get("device_id") == "TEST-DEV-SPEED-01"), None)
        self.assertIsNotNone(created)
        self.assertEqual(created.get("device_model"), "CX 6300")
        self.assertEqual(created.get("port_speed"), "10G")
        self.assertEqual(created.get("vendor"), "Aruba")

        # Clean up created device
        self.client.delete("/api/devices/TEST-DEV-SPEED-01")

if __name__ == "__main__":
    unittest.main()
