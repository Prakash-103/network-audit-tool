"""
Executive Audit Report Generator.
Produces Decision-Ready Management Executive Report in HTML and Markdown.
Adheres to the 5 Core Questions framework:
What did we audit? -> What did we find? -> How serious is it? -> What business areas are affected? -> What should happen next?
"""
import io
from typing import Dict, Any, List
from core.models import NetworkProjectState
from engine.audit_normalizer import AuditNormalizer
from reporting.docx_generator import ExecutiveDocxGenerator


class ExecutiveReportGenerator:
    """Aggregates and formats audit results into a high-level executive management decision document."""

    @staticmethod
    def compile_executive_metrics(state: NetworkProjectState, scope: str = "all") -> Dict[str, Any]:
        """
        Computes all metrics, classifications, risk distributions, security posture %,
        availability checks, and action plans required for the Executive Report.

        All data is normalized through AuditNormalizer to ensure exact data-consistency
        with the Live Audit Screen. Supports scope filtering ('all' vs 'critical').
        """
        norm = AuditNormalizer.normalize_audit(state, scope=scope)

        # Build top findings for executive presentation (up to top 5)
        top_findings = []
        for idx, f in enumerate(norm["findings"]):
            top_findings.append({
                "number": f"{idx + 1:02d}",
                "title": f["check_name"],
                "affected_count": 1,
                "affected_devices": [f["device"]],
                "category": f["category"],
                "severity": f["severity"],
                "observation": f["observation"],
                "potential_impact": f["potential_impact"],
                "recommended_action": f["recommended_action"],
                "command": f["command"],
                "evidence": f["evidence"],
                "check_id": f["check_id"]
            })
            if idx >= 4:
                break

        if not top_findings:
            top_findings.append({
                "number": "01",
                "title": "Baseline Configuration Alignment",
                "affected_count": 0,
                "affected_devices": [],
                "category": "Configuration",
                "severity": "Low",
                "observation": "Audited infrastructure conforms to defined gold master baseline policies.",
                "potential_impact": "No immediate operational or security impact identified.",
                "recommended_action": "Maintain routine automated configuration drift monitoring.",
                "command": "show running-config",
                "evidence": "All evaluated configuration checks passed.",
                "check_id": "CHK-BASE-001"
            })

        # Scope and methodology data
        audit_scope_data = {
            "sites_count": len(norm["sites_list"]),
            "devices_discovered": norm["summary"]["devices"],
            "devices_audited": norm["connectivity_stats"]["audited"],
            "checks_executed": norm["summary"]["checks"],
            "checks_passed": norm["summary"]["passed"],
            "checks_failed": norm["summary"]["failed"],
            "warnings_count": norm["summary"]["warnings"],
            "compliance_pct": norm["summary"]["compliance"],
            "data_sources": [
                "SSH CLI Execution",
                "RESTful APIs (where applicable)",
                "Device Hardware Inventory",
                "Running Configuration Analysis",
                "Neighbor Protocol Tables (CDP / LLDP)",
                "Interface Operational Statistics"
            ],
            "audit_categories": [
                "Device Health & Hardware Inventory",
                "Interface Diagnostics & Physical Link Health",
                "VLAN Architecture & 802.1Q Trunking",
                "Spanning Tree Protocol (STP) Topology",
                "Layer 3 Routing & Neighbor Adjacencies",
                "Control Plane & Infrastructure Security",
                "AAA Authentication & Authorization",
                "SNMP Monitoring & Syslog Architecture",
                "NTP Time Synchronization",
                "Port-Channel & Link Aggregation Redundancy"
            ],
            "lifecycle_stages": [
                "Detected", "Reviewed", "Acknowledged", "Remediation Planned",
                "Remediated", "Revalidated", "Closed"
            ],
            "open_findings": {
                "critical": norm["summary"]["critical"],
                "high": norm["summary"]["high"],
                "medium": norm["summary"]["medium"],
                "low": norm["summary"]["low"],
                "new_findings": len(norm["findings"]),
                "resolved": norm["summary"]["passed"]
            }
        }

        return {
            "customer_name": norm["audit"]["organization"],
            "site_location": norm["audit"]["site"],
            "audit_date": norm["audit"]["audit_date"],
            "audit_scope": norm["audit"]["audit_scope"],
            "total_devices": norm["summary"]["devices"],
            "passed_checks": norm["summary"]["passed"],
            "warning_checks": norm["summary"]["warnings"],
            "failed_checks": norm["summary"]["failed"],
            "total_checks": norm["summary"]["checks"],
            "compliance_pct": norm["summary"]["compliance"],
            "critical_findings_count": norm["summary"]["critical"],
            "high_findings_count": norm["summary"]["high"],
            "medium_findings_count": norm["summary"]["medium"],
            "low_findings_count": norm["summary"]["low"],
            "audit_status": norm["summary"]["audit_status"],
            "audit_status_badge": norm["summary"]["audit_status_badge"],
            "status_explanation": norm["summary"]["status_explanation"],
            "inventory_breakdown": norm["inventory_breakdown"],
            "sites_list": norm["sites_list"],
            "connectivity_stats": norm["connectivity_stats"],
            "category_rows": norm["category_rows"],
            "categories": norm["categories"],
            "findings": norm["findings"],
            "top_findings": top_findings,
            "security_controls": norm["security_controls"],
            "availability_checks": norm["availability_checks"],
            "availability_concerns": norm["availability_concerns"],
            "device_health": norm["device_health"],
            "os_distribution": norm["os_distribution"],
            "site_risk_table": norm["site_risk_table"],
            "action_plan": norm["action_plan"],
            "audit_scope_data": audit_scope_data,
            "recommendations": norm["recommendations"],
            "evidence": norm["evidence"],
            "evidence_workbook_name": norm["evidence_workbook_name"],
            "normalized_json": norm
        }

    @staticmethod
    def _categorize_check(check_name: str, check_cat: str) -> str:
        """Classify a check into one of the 5 canonical executive categories (backwards compatible)."""
        return AuditNormalizer._map_category(check_cat, check_name, check_name)

    @staticmethod
    def generate_markdown(state: NetworkProjectState, scope: str = "all") -> str:
        """Generates a complete decision-ready executive report in GitHub-flavored Markdown."""
        m = ExecutiveReportGenerator.compile_executive_metrics(state, scope=scope)

        # Inventory text
        inv_lines = "\n".join([f"* **{item['category']}:** {item['count']}" for item in m["inventory_breakdown"]])
        site_lines = "\n".join([f"* **{item['site']}:** {item['count']} devices" for item in m["sites_list"]])

        # Categories table
        cat_table = "| Category | Total Checks | Passed | Warnings | Failed | Compliance % | Findings |\n| --- | ---: | ---: | ---: | ---: | ---: | ---: |\n"
        for c in m["category_rows"]:
            cat_table += f"| {c['name']} | {c['total']} | {c['passed']} | {c['warnings']} | {c['failed']} | **{c['compliance']}%** | {c['findings_count']} |\n"

        # Action plan table
        ap_table = "| Priority | Operational Area | Affected Nodes | Suggested Action |\n| :---: | --- | :---: | --- |\n"
        for ap in m["action_plan"]:
            ap_table += f"| **P{ap['priority']}** | {ap['area']} | {ap['affected']} | {ap['suggested_action']} |\n"

        # Top findings text
        tf_text = ""
        for tf in m["top_findings"]:
            tf_text += f"""### {tf['number']} — {tf['title']}
* **Affected Nodes:** {tf['affected_count']} ({', '.join(tf['affected_devices'][:4]) if tf['affected_devices'] else 'All Scope'})
* **Category:** {tf['category']} | **Severity:** {tf['severity']} | **Check ID:** `{tf.get('check_id', 'CHK-001')}`
* **Verification Command:** `{tf.get('command', 'show running-config')}`

> **Observation:** {tf['observation']}  
> **Potential Impact:** {tf['potential_impact']}  
> **Recommended Action:** {tf['recommended_action']}

---
"""

        # Security controls table
        sec_table = "| Security Control | Compliance % | Evaluation Scope |\n| --- | :---: | --- |\n"
        for sc in m["security_controls"]:
            sec_table += f"| {sc['name']} | **{sc['pct']}%** | {sc['detail']} |\n"

        # Availability checks table
        avail_table = "| Resilience Check | Status | Verification Note |\n| --- | :---: | --- |\n"
        for ac in m["availability_checks"]:
            avail_table += f"| {ac['protocol']} | **{ac['status']}** | {ac['note']} |\n"

        report = f"""# ENTERPRISE NETWORK INFRASTRUCTURE AUDIT REPORT
## Executive Management Decision Document

**Customer:** {m['customer_name']}  
**Site Location:** {m['site_location']}  
**Audit Date:** {m['audit_date']}  
**Audit Scope:** {m['audit_scope']}  

---

## 1. EXECUTIVE SUMMARY & DASHBOARD

| Total Nodes Assessed | Verification Checks Executed | Passed Checks | Warnings | Failed | Compliance Rate |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **{m['total_devices']}** | **{m['total_checks']}** | **{m['passed_checks']}** | **{m['warning_checks']}** | **{m['failed_checks']}** | **{m['compliance_pct']}%** |

### Overall Audit Status: **{m['audit_status']}**
> {m['status_explanation']}

### Executive Action Plan
{ap_table}

---

## 2. INFRASTRUCTURE AT A GLANCE & CATEGORY BREAKDOWN

### Hardware Inventory Breakdown
{inv_lines}
* **Total Discovered Nodes:** {m['total_devices']}

### Site Distribution
{site_lines}

### Connectivity & Verification Coverage
* **Discovered Nodes:** {m['connectivity_stats']['discovered']}
* **Reachable Nodes:** {m['connectivity_stats']['reachable']}
* **Unreachable Nodes:** {m['connectivity_stats']['unreachable']}
* **Successfully Audited:** {m['connectivity_stats']['audited']}
* **Partially Audited:** {m['connectivity_stats']['partially_audited']}

### Domain Category Classification
{cat_table}

---

## 3. TOP CRITICAL & HIGH RISK FINDINGS

{tf_text}

---

## 4. SECURITY POSTURE & CONTROL PLANE COMPLIANCE

{sec_table}

---

## 5. NETWORK AVAILABILITY & RESILIENCE

{avail_table}

---

## 6. INFRASTRUCTURE OPERATIONAL HEALTH & FIRMWARE

* **Healthy Nodes:** {m['device_health']['healthy']}
* **Nodes Requiring Attention:** {m['device_health']['needs_attention']}
* **Critical Exposure Nodes:** {m['device_health']['critical']}
* **Unreachable Nodes:** {m['device_health']['unreachable']}

### OS & Firmware Distribution
{"".join([f"* **{item['version']}:** {item['count']} devices\n" for item in m["os_distribution"]])}

---

## 7. STRATEGIC & OPERATIONAL RECOMMENDATIONS

### Immediate Review (0 – 14 Days)
{"".join([f"1. {rec}\n" for rec in m["recommendations"]["immediate"]])}

### Near-Term Remediation (15 – 60 Days)
{"".join([f"1. {rec}\n" for rec in m["recommendations"]["near_term"]])}

### Continuous Improvement (60+ Days)
{"".join([f"1. {rec}\n" for rec in m["recommendations"]["continuous"]])}

---

## 8. AUDIT SCOPE, METHODOLOGY & EVIDENCE TRACEABILITY

* **Total Audited Nodes:** {m['total_devices']}
* **Total Execution Checks:** {m['total_checks']} ({m['passed_checks']} Passed, {m['failed_checks']} Failed, {m['warning_checks']} Warnings)
* **Overall Compliance:** **{m['compliance_pct']}%**
* **Traceable Evidence Workbook:** `{m['evidence_workbook_name']}`
* **Finding Lifecycle Model:** `Detected → Reviewed → Acknowledged → Remediation Planned → Remediated → Revalidated → Closed`
"""
        return report

    @staticmethod
    def generate_docx(state: NetworkProjectState, scope: str = "all") -> io.BytesIO:
        """
        Generates a publication-grade Microsoft Word (.docx) executive report
        with 1:1 mathematical data consistency via AuditNormalizer.
        """
        metrics = ExecutiveReportGenerator.compile_executive_metrics(state, scope=scope)
        return ExecutiveDocxGenerator.generate(metrics)
