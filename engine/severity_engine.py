"""
Context-Aware Severity and Risk Score Calculator.
"""
from typing import List
from core.models import AuditCheckResult
from core.constants import AuditStatus, SeverityLevel

class SeverityEngine:
    @staticmethod
    def calculate_health_score(results: List[AuditCheckResult]) -> tuple[int, SeverityLevel]:
        if not results:
            return 100, SeverityLevel.LOW

        crit_count = sum(1 for r in results if r.status == AuditStatus.FAIL and r.severity == SeverityLevel.CRITICAL)
        high_count = sum(1 for r in results if r.status == AuditStatus.FAIL and r.severity == SeverityLevel.HIGH)
        med_count = sum(1 for r in results if r.status in [AuditStatus.FAIL, AuditStatus.WARNING] and r.severity == SeverityLevel.MEDIUM)
        low_count = sum(1 for r in results if r.status in [AuditStatus.FAIL, AuditStatus.WARNING] and r.severity == SeverityLevel.LOW)

        deductions = (crit_count * 25) + (high_count * 15) + (med_count * 8) + (low_count * 3)
        score = max(0, 100 - deductions)

        if crit_count > 0 or score < 50:
            overall_risk = SeverityLevel.CRITICAL
        elif high_count > 0 or score < 75:
            overall_risk = SeverityLevel.HIGH
        elif med_count > 0 or score < 90:
            overall_risk = SeverityLevel.MEDIUM
        else:
            overall_risk = SeverityLevel.LOW

        return score, overall_risk
