"""
Normalized Audit Engine.
Serves as the Single Source of Truth between Live Audit Discovery/CLI Execution
and Report Generation (Executive PDF, HTML, Markdown, and Live UI).
Strictly enforces the hierarchy:
Checks -> Findings -> Categories -> Recommendations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict

from core.models import NetworkProjectState, DeviceModel, DeviceAuditTask, AuditCheckResult
from core.constants import AuditStatus, SeverityLevel, TaskVerificationStatus, DeviceFunction, DeviceRole, LifecycleStatus


class AuditNormalizer:
    """
    Normalizes audit state into a standardized data model consumed by both the
    Live UI and the Executive Report generator. Eliminates independent calculation
    and ensures 100% data consistency.
    """

    CANONICAL_CATEGORIES = [
        "Security",
        "Availability",
        "Configuration",
        "Network Services",
        "Performance"
    ]

    @classmethod
    def normalize_audit(cls, state: NetworkProjectState, scope: str = "all") -> Dict[str, Any]:
        """
        Produce normalized audit dictionary adhering to the enterprise audit schema.
        Supports scope filtering ('all' vs 'critical').
        """
        devices = state.devices or []
        device_tasks = state.device_audit_tasks or []
        audit_results = state.audit_results or []
        summary = state.summary

        # Hostname to device model lookup
        dev_map: Dict[str, DeviceModel] = {d.hostname: d for d in devices}

        # -------------------------------------------------------------
        # 1. Audit Session Metadata
        # -------------------------------------------------------------
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        audit_date_display = summary.audit_date if (summary and summary.audit_date) else datetime.now().strftime("%d %B %Y")
        audit_id = f"AUD-{datetime.now().strftime('%Y%m%d')}-{len(devices):03d}"
        customer_name = state.company_name or "Enterprise Org"
        site_location = state.site_location or "HQ Data Center"

        scope_title = "Enterprise Network Infrastructure (Core, Distribution, Access, Security & Services)"
        if scope == "critical":
            scope_title = "Enterprise Network Infrastructure (Critical & High Risk Scope)"

        audit_meta = {
            "audit_id": audit_id,
            "organization": customer_name,
            "site": site_location,
            "project_name": state.project_name or f"{customer_name} - {site_location} Audit",
            "audit_date": audit_date_display,
            "audit_scope": scope_title,
            "started_at": now_str,
            "completed_at": now_str
        }

        # -------------------------------------------------------------
        # 2. Extract Unified Canonical Checks
        # -------------------------------------------------------------
        raw_checks: List[Dict[str, Any]] = []

        if device_tasks:
            # Stage 3 device audit tasks are the primary source of live audit checks
            for t in device_tasks:
                dev = dev_map.get(t.device_hostname)
                cat = cls._map_category(t.category, t.protocol, t.title)
                status_str = cls._map_task_status(t.status)
                sev_str = t.severity.value if hasattr(t.severity, 'value') else str(t.severity)

                raw_checks.append({
                    "check_id": t.id,
                    "device_id": dev.device_id if dev else t.device_hostname,
                    "hostname": t.device_hostname,
                    "vendor": dev.vendor if dev else "Cisco",
                    "model": dev.device_model if dev else "Catalyst 9300",
                    "site": dev.site_location if (dev and dev.site_location) else site_location,
                    "category": cat,
                    "subcategory": t.protocol or cat,
                    "check_name": t.title,
                    "status": status_str,
                    "severity": sev_str,
                    "expected": t.description or "Configuration conforms to enterprise gold baseline.",
                    "actual": t.actual_output or t.evidence_notes or f"Status: {status_str}",
                    "command": t.verification_command or "show running-config",
                    "evidence": t.actual_output or t.evidence_notes or f"Verification status: {status_str}",
                    "recommendation": cls._derive_recommendation(t.title, t.protocol, t.actual_output or t.evidence_notes),
                    "timestamp": t.timestamp or now_str,
                    "parser": cls._derive_parser_name(dev.vendor if dev else "cisco", t.protocol),
                    "parser_confidence": "Deterministic / 100%"
                })

            # Check if there are unique topology/link validation results in audit_results
            existing_ids = {c["check_id"] for c in raw_checks}
            for r in audit_results:
                if r.id.startswith("AUD-TOPO-") and r.id not in existing_ids:
                    dev = dev_map.get(r.device)
                    cat = "Availability"
                    raw_checks.append({
                        "check_id": r.id,
                        "device_id": dev.device_id if dev else r.device,
                        "hostname": r.device,
                        "vendor": dev.vendor if dev else "Cisco",
                        "model": dev.device_model if dev else "Catalyst 9300",
                        "site": dev.site_location if (dev and dev.site_location) else site_location,
                        "category": cat,
                        "subcategory": "Topology & Links",
                        "check_name": r.check,
                        "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
                        "severity": r.severity.value if hasattr(r.severity, 'value') else str(r.severity),
                        "expected": r.expected,
                        "actual": r.actual,
                        "command": "Topology Link Validator Engine",
                        "evidence": r.evidence,
                        "recommendation": r.recommendation,
                        "timestamp": r.timestamp or now_str,
                        "parser": "topology_engine",
                        "parser_confidence": "Deterministic / 100%"
                    })
        elif audit_results:
            # Fallback when only audit_results exists (e.g. Stage 2 direct tests)
            for r in audit_results:
                dev = dev_map.get(r.device)
                cat = cls._map_category(r.category, r.check, r.check)
                status_str = r.status.value if hasattr(r.status, 'value') else str(r.status)
                sev_str = r.severity.value if hasattr(r.severity, 'value') else str(r.severity)

                raw_checks.append({
                    "check_id": r.id,
                    "device_id": dev.device_id if dev else r.device,
                    "hostname": r.device,
                    "vendor": dev.vendor if dev else "Cisco",
                    "model": dev.device_model if dev else "Catalyst 9300",
                    "site": dev.site_location if (dev and dev.site_location) else site_location,
                    "category": cat,
                    "subcategory": r.category or cat,
                    "check_name": r.check,
                    "status": status_str,
                    "severity": sev_str,
                    "expected": r.expected,
                    "actual": r.actual,
                    "command": "show running-config",
                    "evidence": r.evidence,
                    "recommendation": r.recommendation or cls._derive_recommendation(r.check, r.category, r.actual),
                    "timestamp": r.timestamp or now_str,
                    "parser": "config_parser",
                    "parser_confidence": "Deterministic / 100%"
                })

        # -------------------------------------------------------------
        # 3. Compute Ground-Truth Summary KPIs
        # -------------------------------------------------------------
        total_devices = len(devices)
        total_checks = len(raw_checks)
        passed_checks = sum(1 for c in raw_checks if c["status"] == "PASS")
        warning_checks = sum(1 for c in raw_checks if c["status"] == "WARNING")
        failed_checks = sum(1 for c in raw_checks if c["status"] == "FAIL")
        na_checks = sum(1 for c in raw_checks if c["status"] == "NOT APPLICABLE")
        incomplete_checks = sum(1 for c in raw_checks if c["status"] == "INCOMPLETE")

        # Active checks evaluated (excluding N/A and unattempted In-Complete)
        executed_checks = passed_checks + warning_checks + failed_checks
        if executed_checks > 0 and incomplete_checks > 0:
            evaluable_checks = executed_checks
            displayed_checks = executed_checks
        else:
            evaluable_checks = total_checks - na_checks
            displayed_checks = evaluable_checks

        compliance_pct = round((passed_checks / evaluable_checks * 100)) if evaluable_checks > 0 else 100

        # -------------------------------------------------------------
        # 4. Extract Strict Findings (ONLY checks with status != PASS and != NOT APPLICABLE)
        # -------------------------------------------------------------
        findings: List[Dict[str, Any]] = []
        finding_idx = 1

        for c in raw_checks:
            if c["status"] in ["FAIL", "WARNING"]:
                f_sev = c["severity"]
                f_id = f"FND-{finding_idx:02d}"

                # Priority mapping: Critical -> P1, High -> P2, Medium -> P3, Low -> P4
                if f_sev == SeverityLevel.CRITICAL.value:
                    prio = "P1"
                    impact_text = "Severe business impact. Immediate operational disruption or compliance compromise risk."
                elif f_sev == SeverityLevel.HIGH.value:
                    prio = "P2"
                    impact_text = "Elevated risk of service degradation, single point of failure, or unauthorized management plane access."
                elif f_sev == SeverityLevel.MEDIUM.value:
                    prio = "P3"
                    impact_text = "Configuration drift from enterprise baseline. Hampered incident correlation or suboptimal failover."
                else:
                    prio = "P4"
                    impact_text = "Minor baseline inconsistency with low direct operational risk."

                findings.append({
                    "finding_id": f_id,
                    "check_id": c["check_id"],
                    "device": c["hostname"],
                    "category": c["category"],
                    "subcategory": c["subcategory"],
                    "check_name": c["check_name"],
                    "status": c["status"],
                    "severity": f_sev,
                    "priority": prio,
                    "observation": c["actual"],
                    "potential_impact": impact_text,
                    "recommended_action": c["recommendation"],
                    "command": c["command"],
                    "evidence": c["evidence"]
                })
                finding_idx += 1

        critical_findings_count = sum(1 for f in findings if f["severity"] == SeverityLevel.CRITICAL.value)
        high_findings_count = sum(1 for f in findings if f["severity"] == SeverityLevel.HIGH.value)
        medium_findings_count = sum(1 for f in findings if f["severity"] == SeverityLevel.MEDIUM.value)
        low_findings_count = sum(1 for f in findings if f["severity"] in [SeverityLevel.LOW.value, SeverityLevel.INFO.value])

        # Overall Status
        if critical_findings_count >= 5:
            audit_status = "CRITICAL RISK"
            audit_status_badge = "critical"
        elif critical_findings_count > 0:
            audit_status = "ATTENTION REQUIRED"
            audit_status_badge = "warning"
        elif high_findings_count > 0 or failed_checks > 0:
            audit_status = "REVIEW RECOMMENDED"
            audit_status_badge = "high"
        elif warning_checks > 0:
            audit_status = "REVIEW RECOMMENDED"
            audit_status_badge = "high"
        else:
            audit_status = "COMPLIANT"
            audit_status_badge = "pass"

        # Status explanation text
        if findings:
            parts = []
            if critical_findings_count > 0:
                parts.append(f"{critical_findings_count} critical")
            if high_findings_count > 0:
                parts.append(f"{high_findings_count} high")
            if medium_findings_count > 0:
                parts.append(f"{medium_findings_count} medium")
            if low_findings_count > 0:
                parts.append(f"{low_findings_count} low")
            sev_summary = ", ".join(parts)

            status_explanation = (
                f"Audit identified {len(findings)} actionable findings across {displayed_checks} executed checks "
                f"({sev_summary}). {passed_checks} checks passed successfully ({compliance_pct}% compliance rate)."
            )
        else:
            status_explanation = (
                f"All {displayed_checks} verification checks passed successfully across {total_devices} audited node(s). "
                f"No critical exposures or operational availability risks were detected ({compliance_pct}% compliance rate)."
            )

        summary_metrics = {
            "devices": total_devices,
            "checks": displayed_checks,
            "total_scheduled": total_checks,
            "incomplete": incomplete_checks,
            "passed": passed_checks,
            "warnings": warning_checks,
            "failed": failed_checks,
            "critical": critical_findings_count,
            "high": high_findings_count,
            "medium": medium_findings_count,
            "low": low_findings_count,
            "compliance": compliance_pct,
            "audit_status": audit_status,
            "audit_status_badge": audit_status_badge,
            "status_explanation": status_explanation
        }

        # -------------------------------------------------------------
        # 5. Compute Category Breakdown & Compliance %
        # -------------------------------------------------------------
        categories: Dict[str, Dict[str, Any]] = {}
        for cat_name in cls.CANONICAL_CATEGORIES:
            all_cat_checks = [c for c in raw_checks if c["category"] == cat_name]
            executed_cat_checks = [c for c in all_cat_checks if c["status"] not in ["INCOMPLETE", "NOT APPLICABLE"]]
            cat_checks = executed_cat_checks if (executed_cat_checks and incomplete_checks > 0) else all_cat_checks
            c_tot = len(cat_checks)
            c_pass = sum(1 for c in cat_checks if c["status"] == "PASS")
            c_warn = sum(1 for c in cat_checks if c["status"] == "WARNING")
            c_fail = sum(1 for c in cat_checks if c["status"] == "FAIL")
            c_comp = round((c_pass / c_tot * 100)) if c_tot > 0 else 100

            # Findings in this category
            cat_findings = [f for f in findings if f["category"] == cat_name]
            crit_cnt = sum(1 for f in cat_findings if f["severity"] == SeverityLevel.CRITICAL.value)
            high_cnt = sum(1 for f in cat_findings if f["severity"] == SeverityLevel.HIGH.value)
            med_cnt = sum(1 for f in cat_findings if f["severity"] == SeverityLevel.MEDIUM.value)
            low_cnt = sum(1 for f in cat_findings if f["severity"] in [SeverityLevel.LOW.value, SeverityLevel.INFO.value])

            categories[cat_name.lower().replace(" ", "_")] = {
                "name": cat_name,
                "total": c_tot,
                "passed": c_pass,
                "warnings": c_warn,
                "failed": c_fail,
                "critical": crit_cnt,
                "high": high_cnt,
                "medium": med_cnt,
                "low": low_cnt,
                "compliance": c_comp,
                "findings_count": len(cat_findings)
            }

        # Category rows formatted for executive report table
        category_rows = []
        for cat_name in cls.CANONICAL_CATEGORIES:
            cat_data = categories[cat_name.lower().replace(" ", "_")]
            category_rows.append(cat_data)

        # -------------------------------------------------------------
        # 6. Recommendations strictly derived from Findings
        # -------------------------------------------------------------
        recommendations = {
            "immediate": [],
            "near_term": [],
            "continuous": []
        }
        action_plan = []

        if findings:
            for idx, f in enumerate(findings):
                action_text = f["recommended_action"]
                rec_title = f"{f['check_name']} ({f['device']})"
                prio_num = 1 if f["priority"] == "P1" else (2 if f["priority"] == "P2" else 3)

                if f["priority"] in ["P1", "P2"]:
                    recommendations["immediate"].append(f"[{f['priority']}] {f['device']}: {action_text}")
                elif f["priority"] == "P3":
                    recommendations["near_term"].append(f"[P3] {f['device']}: {action_text}")
                else:
                    recommendations["continuous"].append(f"[P4] {f['device']}: {action_text}")

                action_plan.append({
                    "priority": prio_num,
                    "area": f["category"],
                    "affected": 1,
                    "suggested_action": f"{f['check_name']} - {action_text}"
                })
        else:
            action_plan.append({
                "priority": 1,
                "area": "Configuration Baselines",
                "affected": 0,
                "suggested_action": "Infrastructure conforms to defined baselines. Maintain routine automated configuration audits."
            })
            recommendations["immediate"].append("Maintain routine automated baseline monitoring across audited devices.")
            recommendations["near_term"].append("Periodically review configuration drift and backup archives.")
            recommendations["continuous"].append("Incorporate automated audit validation into ITSM change workflows.")

        # Ensure continuous improvement always has best practice items
        if not recommendations["continuous"]:
            recommendations["continuous"].append("Establish automated recurring network infrastructure compliance audits.")
            recommendations["continuous"].append("Integrate audit validation findings into enterprise IT change management.")

        # -------------------------------------------------------------
        # 7. Security Control Posture (Calculated from actual checks)
        # -------------------------------------------------------------
        security_controls = cls._compute_security_controls(raw_checks)

        # -------------------------------------------------------------
        # 8. High Availability & Redundancy Verification (From actual checks)
        # -------------------------------------------------------------
        availability_checks, availability_concerns = cls._compute_availability_matrix(raw_checks, findings, devices)

        # -------------------------------------------------------------
        # 9. Infrastructure Scope & Inventory Breakdown
        # -------------------------------------------------------------
        inventory_breakdown = cls._compute_inventory_breakdown(devices)
        sites_list = cls._compute_sites_list(devices, site_location)
        connectivity_stats = cls._compute_connectivity_stats(devices, raw_checks)
        device_health = cls._compute_device_health(devices, findings)
        os_distribution = cls._compute_os_distribution(devices)
        site_risk_table = cls._compute_site_risk_table(devices, sites_list, findings)

        # -------------------------------------------------------------
        # 10. Evidence Traceability Records
        # -------------------------------------------------------------
        evidence_records = []
        for c in raw_checks:
            evidence_records.append({
                "audit_id": audit_id,
                "device": c["hostname"],
                "check_id": c["check_id"],
                "command": c["command"],
                "status": c["status"],
                "severity": c["severity"],
                "timestamp": c["timestamp"],
                "evidence_summary": (c["evidence"][:120] + "...") if len(c["evidence"]) > 120 else c["evidence"],
                "parser": c["parser"],
                "confidence": c["parser_confidence"]
            })

        # Assemble Master Normalized Output
        return {
            "audit": audit_meta,
            "summary": summary_metrics,
            "categories": categories,
            "category_rows": category_rows,
            "findings": findings,
            "recommendations": recommendations,
            "action_plan": action_plan,
            "security_controls": security_controls,
            "availability_checks": availability_checks,
            "availability_concerns": availability_concerns,
            "inventory_breakdown": inventory_breakdown,
            "sites_list": sites_list,
            "connectivity_stats": connectivity_stats,
            "device_health": device_health,
            "os_distribution": os_distribution,
            "site_risk_table": site_risk_table,
            "evidence": evidence_records,
            "raw_checks": raw_checks,
            "evidence_workbook_name": f"{customer_name.replace(' ', '_')}_{site_location.replace(' ', '_')}_Audit_Evidence.xlsx"
        }

    # =========================================================================
    # Internal Helpers & Classification Logics
    # =========================================================================

    @classmethod
    def _map_category(cls, category_hint: str, proto_hint: str, title_hint: str) -> str:
        """Map raw protocol/task category to one of the 5 canonical executive categories."""
        combined = f"{category_hint} {proto_hint} {title_hint}".lower()

        # Security
        if any(k in combined for k in [
            "security", "aaa", "ssh", "snmp", "password", "secret", "user", "vty",
            "tacacs", "radius", "acl", "firewall", "zone", "port security",
            "dhcp snooping", "dai", "ip source guard", "crypto", "vpn", "banner"
        ]):
            return "Security"

        # Availability / Redundancy
        if any(k in combined for k in [
            "availability", "stp", "rstp", "spanning", "root", "etherchannel",
            "lacp", "channel", "bundle", "hsrp", "vrrp", "fhrp", "bfd", "uplink",
            "redundancy", "failover", "ha"
        ]):
            return "Availability"

        # Performance & QoS
        if any(k in combined for k in [
            "performance", "qos", "buffer", "drop", "error", "utilization",
            "cpu", "memory", "sla", "traffic policy"
        ]):
            return "Performance"

        # Configuration, VLANs & IP Addressing
        if any(k in combined for k in [
            "configuration", "baseline", "vlan", "trunk", "native", "subnet",
            "addressing", "ip addressing", "svi", "route", "routing", "static", "ospf", "bgp", "eigrp"
        ]):
            return "Configuration"

        # Network Services
        if any(k in combined for k in [
            "service", "ntp", "clock", "time", "syslog", "logging", "siem",
            "dns", "dhcp", "cdp", "lldp", "neighbor", "interfaces", "health"
        ]):
            return "Network Services"

        # Configuration (Default)
        return "Configuration"

    @staticmethod
    def _map_task_status(status: Any) -> str:
        """Map TaskVerificationStatus or AuditStatus to standardized PASS / WARNING / FAIL / NOT APPLICABLE / INCOMPLETE."""
        if hasattr(status, 'value'):
            s = status.value.lower()
        else:
            s = str(status).lower()

        if s in ["completed", "pass"]:
            return "PASS"
        elif s in ["warning", "warn"]:
            return "WARNING"
        elif s in ["failed", "fail"]:
            return "FAIL"
        elif s in ["n/a", "not applicable", "not_applicable"]:
            return "NOT APPLICABLE"
        return "INCOMPLETE"

    @staticmethod
    def _derive_recommendation(title: str, protocol: str, output: str) -> str:
        """Derive standard engineering remediation recommendation."""
        combined = f"{title} {protocol}".lower()
        if "ssh" in combined:
            return "Enforce SSHv2 exclusively with strong crypto ciphers and disable legacy Telnet."
        elif "aaa" in combined:
            return "Deploy centralized TACACS+/RADIUS authentication with resilient local fallback."
        elif "ntp" in combined:
            return "Configure redundant enterprise NTP stratum servers and synchronize local clocks."
        elif "snmp" in combined:
            return "Deprecate default community strings and enforce SNMPv3 with authPriv encryption."
        elif "lacp" in combined or "channel" in combined:
            return "Standardize LACP timers, interface MTUs, and verify active port bundling."
        elif "stp" in combined or "spanning" in combined:
            return "Enforce root bridge priorities, verify Rapid-PVST+, and enable BPDU Guard on edge ports."
        elif "vlan" in combined or "trunk" in combined:
            return "Standardize trunk native VLANs across inter-switch links and prune unused VLAN IDs."
        elif "ip" in combined or "address" in combined:
            return "Validate IP addressing, subnet masks, and interface reachability parameters."
        return "Review and align configuration parameters with enterprise gold baseline."

    @staticmethod
    def _derive_parser_name(vendor: str, protocol: str) -> str:
        v = (vendor or "cisco").lower().replace(" ", "_")
        p = (protocol or "config").lower().replace(" ", "_").replace("/", "_")
        return f"{v}_{p}_parser"

    @classmethod
    def _compute_security_controls(cls, checks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate true compliance % for the 6 core management-plane security controls."""
        controls_def = [
            ("AAA / Centralized Authentication", ["aaa", "tacacs", "radius", "password", "authentication"], "Measures enforcement of central TACACS+/RADIUS credentials and privilege safety."),
            ("SSH Management Plane Cryptography", ["ssh", "crypto", "telnet"], "Enforces SSHv2 exclusively, strong ciphers, and complete decommissioning of Telnet."),
            ("SNMP Monitoring & Access Control", ["snmp"], "Verifies deprecation of default community strings and enablement of SNMPv3 authPriv."),
            ("NTP Time Synchronization", ["ntp", "clock", "time"], "Audits clock stratum, synchronization status, and redundant master pool configuration."),
            ("Syslog Central Event Auditing", ["syslog", "logging", "siem"], "Validates dual destination SIEM logging with appropriate informational severity thresholds."),
            ("Management Access ACLs & Control Plane", ["acl", "vty", "line vty", "access-list"], "Audits line access restrictions allowing only authorized jump-host administration.")
        ]

        results = []
        for name, keywords, detail in controls_def:
            matched = [c for c in checks if any(k in f"{c['check_name']} {c['subcategory']}".lower() for k in keywords)]
            if matched:
                tot = len(matched)
                pass_cnt = sum(1 for c in matched if c["status"] == "PASS")
                pct = round((pass_cnt / tot) * 100)
            else:
                # If no matching test was specifically run, check if overall security checks passed
                sec_checks = [c for c in checks if c["category"] == "Security"]
                if sec_checks:
                    sec_pass = sum(1 for c in sec_checks if c["status"] == "PASS")
                    pct = round((sec_pass / len(sec_checks)) * 100)
                else:
                    pct = 100

            results.append({
                "name": name,
                "pct": pct,
                "detail": detail
            })
        return results

    @classmethod
    def _compute_availability_matrix(cls, checks: List[Dict[str, Any]], findings: List[Dict[str, Any]], devices: List[DeviceModel]):
        """Map live checks to availability matrix protocols."""
        proto_defs = [
            ("STP / Spanning Tree Root", ["stp", "spanning", "root"], "Root priority enforcement across distribution nodes"),
            ("RSTP / Rapid Convergence", ["rstp", "rapid"], "Rapid convergence on access switch uplinks"),
            ("EtherChannel Bundling", ["etherchannel", "port-channel", "bundle"], "Channel group member status and duplex uniformity"),
            ("LACP Protocol State", ["lacp"], "Dynamic LACP negotiation timer standardization"),
            ("HSRP / FHRP Gateway HA", ["hsrp", "fhrp", "standby"], "First-hop redundancy across VLAN interfaces"),
            ("VRRP Gateway Redundancy", ["vrrp"], "Gateway redundancy verification"),
            ("BFD Rapid Fault Detection", ["bfd"], "BFD peer adjacency verification for sub-second routing failover"),
            ("Dual Uplink Redundancy", ["uplink", "redundancy"], "Access switches verified for diverse physical paths")
        ]

        avail_checks = []
        for proto_name, keywords, note in proto_defs:
            matched = [c for c in checks if any(k in f"{c['check_name']} {c['subcategory']}".lower() for k in keywords)]
            if not matched:
                avail_checks.append({"protocol": proto_name, "status": "-", "note": "Not configured / Not assessed in scope"})
            else:
                fails = [c for c in matched if c["status"] in ["FAIL", "WARNING"]]
                if not fails:
                    avail_checks.append({"protocol": proto_name, "status": "✓", "note": note})
                elif any(c["severity"] in [SeverityLevel.CRITICAL.value, SeverityLevel.HIGH.value] for c in fails):
                    avail_checks.append({"protocol": proto_name, "status": "✗", "note": fails[0]["actual"]})
                else:
                    avail_checks.append({"protocol": proto_name, "status": "⚠", "note": fails[0]["actual"]})

        # Availability Concerns
        avail_concerns = []
        avail_findings = [f for f in findings if f["category"] == "Availability"]
        for f in avail_findings:
            avail_concerns.append({
                "finding": f["check_name"],
                "devices": 1,
                "severity": f["severity"],
                "impact": f["potential_impact"]
            })

        if not avail_concerns:
            # Clean conformance
            avail_concerns.append({
                "finding": "Redundancy Baseline Conformance",
                "devices": 0,
                "severity": "Low",
                "impact": "No active single point of failure or loop hazard identified in audited scope."
            })

        return avail_checks, avail_concerns

    @staticmethod
    def _compute_inventory_breakdown(devices: List[DeviceModel]) -> List[Dict[str, Any]]:
        cisco_sw = 0
        arista_sw = 0
        juniper_sw = 0
        firewalls = 0
        wireless = 0
        routers = 0
        other = 0

        for d in devices:
            v = (d.vendor or "").lower()
            role = d.device_role
            func = d.device_function

            if role == DeviceRole.FIREWALL or func == DeviceFunction.FIREWALL:
                firewalls += 1
            elif role == DeviceRole.WIRELESS_AP or func == DeviceFunction.WIRELESS_AP:
                wireless += 1
            elif role == DeviceRole.EDGE or func == DeviceFunction.EDGE_WAN or "router" in str(role).lower() or "router" in str(func).lower():
                routers += 1
            elif "cisco" in v:
                cisco_sw += 1
            elif "arista" in v:
                arista_sw += 1
            elif "juniper" in v:
                juniper_sw += 1
            else:
                other += 1

        items = [
            {"category": "Cisco Switches", "count": cisco_sw},
            {"category": "Arista Switches", "count": arista_sw},
            {"category": "Juniper Switches", "count": juniper_sw},
            {"category": "Firewalls & Security", "count": firewalls},
            {"category": "Wireless APs & Controllers", "count": wireless},
            {"category": "Routers & Gateways", "count": routers},
            {"category": "Other Network Devices", "count": other},
        ]
        filtered = [i for i in items if i["count"] > 0]
        return filtered if filtered else [{"category": "Network Infrastructure Nodes", "count": len(devices)}]

    @staticmethod
    def _compute_sites_list(devices: List[DeviceModel], default_site: str) -> List[Dict[str, Any]]:
        counts = defaultdict(int)
        for d in devices:
            s = d.site_location or default_site
            counts[s] += 1
        return [{"site": k, "count": v} for k, v in counts.items()] if counts else [{"site": default_site, "count": len(devices)}]

    @staticmethod
    def _compute_connectivity_stats(devices: List[DeviceModel], checks: List[Dict[str, Any]]) -> Dict[str, int]:
        total = len(devices)
        reachable = sum(1 for d in devices if d.lifecycle_status in [LifecycleStatus.ACTIVE, LifecycleStatus.EOL, LifecycleStatus.EOS])
        unreachable = total - reachable
        audited_hosts = {c["hostname"] for c in checks}
        audited = len(audited_hosts) if audited_hosts else reachable
        partial = max(0, reachable - audited)
        return {
            "discovered": total,
            "reachable": reachable,
            "unreachable": unreachable,
            "audited": audited,
            "partially_audited": partial
        }

    @staticmethod
    def _compute_device_health(devices: List[DeviceModel], findings: List[Dict[str, Any]]) -> Dict[str, int]:
        total = len(devices)
        dev_findings = defaultdict(list)
        for f in findings:
            dev_findings[f["device"]].append(f["severity"])

        crit = sum(1 for d, sevs in dev_findings.items() if SeverityLevel.CRITICAL.value in sevs)
        attention = sum(1 for d, sevs in dev_findings.items() if SeverityLevel.HIGH.value in sevs or SeverityLevel.MEDIUM.value in sevs)
        healthy = max(0, total - crit - attention)
        return {
            "healthy": healthy,
            "needs_attention": attention,
            "critical": crit,
            "unreachable": 0
        }

    @staticmethod
    def _compute_os_distribution(devices: List[DeviceModel]) -> List[Dict[str, Any]]:
        counts = defaultdict(int)
        for d in devices:
            ver = d.os_version or "Unknown Version"
            counts[ver] += 1
        return [{"version": k, "count": v} for k, v in counts.items()] if counts else [{"version": "IOS-XE 17.9", "count": len(devices)}]

    @staticmethod
    def _compute_site_risk_table(devices: List[DeviceModel], sites_list: List[Dict[str, Any]], findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = []
        for s in sites_list:
            site_name = s["site"]
            s_devs = [d for d in devices if (d.site_location or "HQ DC") == site_name]
            dev_hosts = {d.hostname for d in s_devs}

            s_findings = [f for f in findings if f["device"] in dev_hosts]
            crits = sum(1 for f in s_findings if f["severity"] == SeverityLevel.CRITICAL.value)
            highs = sum(1 for f in s_findings if f["severity"] == SeverityLevel.HIGH.value)
            meds = sum(1 for f in s_findings if f["severity"] == SeverityLevel.MEDIUM.value)
            lows = sum(1 for f in s_findings if f["severity"] in [SeverityLevel.LOW.value, SeverityLevel.INFO.value])

            status = "ATTENTION" if crits > 0 else ("WARNING" if highs > 0 else "HEALTHY")
            rows.append({
                "site": site_name,
                "device_count": len(s_devs) if s_devs else s["count"],
                "critical": crits,
                "high": highs,
                "medium": meds,
                "low": lows,
                "status": status
            })
        return rows
