"""
Lifecycle EOL/EOS Knowledge Base and Evaluator.
"""
from typing import Tuple

EOL_DATABASE = {
    "ws-c3750g": {"status": "End-of-Life (Critical)", "risk": "High"},
    "ws-c2960-24tt-l": {"status": "End-of-Life (Critical)", "risk": "High"},
    "c9300-48u": {"status": "Active / Supported", "risk": "Low"},
    "c9500-24q": {"status": "Active / Supported", "risk": "Low"},
    "nexus 7000": {"status": "End-of-Support Approaching", "risk": "Medium"},
    "nexus 9300": {"status": "Active / Supported", "risk": "Low"},
    "dcs-7050sx-64": {"status": "End-of-Life Approaching", "risk": "Medium"},
    "dcs-7280sr": {"status": "Active / Supported", "risk": "Low"},
    "srx300": {"status": "Active / Supported", "risk": "Low"},
    "fortigate 100f": {"status": "Active / Supported", "risk": "Low"},
    "pa-3220": {"status": "Active / Supported", "risk": "Low"},
    "ap-515": {"status": "Active / Supported", "risk": "Low"}
}

class LifecycleEvaluator:
    @staticmethod
    def evaluate(model: str, os_version: str) -> Tuple[str, str]:
        hw_status = "Active / Supported"
        sw_status = "Active / Supported"

        model_clean = model.lower().strip()
        os_clean = os_version.lower().strip()

        for key, info in EOL_DATABASE.items():
            if key in model_clean:
                hw_status = info["status"]

        if any(v in os_clean for v in ["12.2", "15.0", "4.20", "6.2"]):
            sw_status = "End-of-Support OS (Upgrade Recommended)"

        return hw_status, sw_status
