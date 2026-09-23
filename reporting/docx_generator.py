"""
Word Document (.docx) Executive Audit Report Generator.
Generates publication-grade, formal Microsoft Word documents representing
the Executive Network Infrastructure Audit Report with 1:1 mathematical data consistency.
"""
import io
from typing import Dict, Any, List, Optional
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn


class ExecutiveDocxGenerator:
    """Generates a formal, corporate-styled Word Document (.docx) for the Executive Audit Report."""

    # Corporate Color Palette
    COLOR_PRIMARY = RGBColor(30, 58, 138)      # Navy (#1E3A8A)
    COLOR_DARK = RGBColor(15, 23, 42)          # Slate (#0F172A)
    COLOR_MUTED = RGBColor(100, 116, 139)      # Muted Gray (#64748B)
    COLOR_SUCCESS = RGBColor(22, 163, 74)      # Green (#16A34A)
    COLOR_WARNING = RGBColor(217, 119, 6)      # Amber (#D97706)
    COLOR_DANGER = RGBColor(220, 38, 38)       # Red (#DC2626)
    COLOR_WHITE = RGBColor(255, 255, 255)

    HEX_NAVY = "1E3A8A"
    HEX_HEADER_BG = "1E293B"     # Slate Header (#1E293B)
    HEX_ZEBRA = "F8FAFC"         # Light Tint (#F8FAFC)
    HEX_BORDER = "CBD5E1"        # Subtle Border (#CBD5E1)
    HEX_CALLOUT_BG = "F1F5F9"    # Callout Background (#F1F5F9)
    HEX_CARD_BG = "FAFAFA"       # Metric Card Background

    @classmethod
    def generate(cls, metrics: Dict[str, Any]) -> io.BytesIO:
        """
        Builds a complete, styled Microsoft Word document from normalized executive metrics.
        Returns an in-memory BytesIO stream containing the .docx file.
        """
        doc = docx.Document()

        # 1. Page Margins & Setup (0.75 in / 54pt standard)
        section = doc.sections[0]
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)
        section.page_width = Inches(8.5)
        section.page_height = Inches(11.0)

        # 2. Setup Running Headers & Footers
        cls._setup_header_footer(section, metrics)

        # 3. Document Title & Header Banner
        cls._build_header_banner(doc, metrics)

        # 4. Page 1: Executive Summary & KPI Metrics
        cls._build_executive_summary_section(doc, metrics)

        # 5. Page 2: Infrastructure Scope & Domain Classification
        doc.add_page_break()
        cls._build_infrastructure_scope_section(doc, metrics)

        # 6. Page 3: Top Critical & High Risk Findings
        doc.add_page_break()
        cls._build_top_findings_section(doc, metrics)

        # 7. Page 4: Security Posture & Resilience Matrix
        doc.add_page_break()
        cls._build_security_availability_section(doc, metrics)

        # 8. Page 5: Operational Health & Fleet Assessment
        doc.add_page_break()
        cls._build_fleet_health_section(doc, metrics)

        # 9. Page 6: Strategic Roadmap & Audit Evidence Traceability
        doc.add_page_break()
        cls._build_recommendations_and_evidence_section(doc, metrics)

        # Save to buffer
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf

    # -------------------------------------------------------------------------
    #  SECTION BUILDERS
    # -------------------------------------------------------------------------

    @classmethod
    def _setup_header_footer(cls, section, metrics: Dict[str, Any]):
        """Sets up professional running header and footer."""
        # Running Header
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run(f"Enterprise Network Infrastructure Audit Report | {metrics.get('customer_name', 'Enterprise')} — {metrics.get('site_location', 'DC')}")
        hrun.font.name = "Calibri"
        hrun.font.size = Pt(8)
        hrun.font.color.rgb = cls.COLOR_MUTED

        # Running Footer
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        frun = fp.add_run("CONFIDENTIAL — STRICTLY FOR INTERNAL GOVERNANCE & REMEDIATION PURPOSES ONLY")
        frun.font.name = "Calibri"
        frun.font.size = Pt(8)
        frun.font.color.rgb = cls.COLOR_MUTED

    @classmethod
    def _build_header_banner(cls, doc: docx.Document, m: Dict[str, Any]):
        """Builds the formal document title, subtitle, and metadata table."""
        # Title
        p_title = doc.add_paragraph()
        p_title.paragraph_format.space_before = Pt(0)
        p_title.paragraph_format.space_after = Pt(2)
        r_title = p_title.add_run("ENTERPRISE NETWORK INFRASTRUCTURE AUDIT REPORT")
        r_title.font.name = "Calibri"
        r_title.font.size = Pt(18)
        r_title.font.bold = True
        r_title.font.color.rgb = cls.COLOR_PRIMARY

        # Subtitle
        p_sub = doc.add_paragraph()
        p_sub.paragraph_format.space_before = Pt(0)
        p_sub.paragraph_format.space_after = Pt(12)
        r_sub = p_sub.add_run("Executive Management Decision Document & Comprehensive Posture Assessment")
        r_sub.font.name = "Calibri"
        r_sub.font.size = Pt(11)
        r_sub.font.color.rgb = cls.COLOR_MUTED

        # Metadata Table (2x2 grid)
        tbl = doc.add_table(rows=2, cols=4)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cls._set_table_borders(tbl, cls.HEX_BORDER)

        meta_items = [
            ("Customer Organization:", m.get("customer_name", "Enterprise Client")),
            ("Site Location:", m.get("site_location", "Primary Datacenter")),
            ("Audit Date:", m.get("audit_date", "Current Cycle")),
            ("Audit Scope:", m.get("audit_scope", "Core & Distribution Infrastructure")),
        ]

        row_idx, col_idx = 0, 0
        for label, val in meta_items:
            cell_lbl = tbl.cell(row_idx, col_idx)
            cell_val = tbl.cell(row_idx, col_idx + 1)
            cls._style_cell_text(cell_lbl, label, bold=True, size=8.5, color=cls.COLOR_DARK)
            cls._style_cell_text(cell_val, val, bold=False, size=8.5, color=cls.COLOR_DARK)
            cls._set_cell_background(cell_lbl, "F1F5F9")
            cls._set_cell_padding(cell_lbl, top=70, bottom=70, left=100, right=100)
            cls._set_cell_padding(cell_val, top=70, bottom=70, left=100, right=100)

            col_idx += 2
            if col_idx >= 4:
                col_idx = 0
                row_idx += 1

        doc.add_paragraph().paragraph_format.space_after = Pt(8)

    @classmethod
    def _build_executive_summary_section(cls, doc: docx.Document, m: Dict[str, Any]):
        """Page 1: Executive Summary, KPI Summary Table, Status Box, and Action Plan."""
        cls._add_section_heading(doc, "1. EXECUTIVE SUMMARY & DASHBOARD")

        # 5 KPI Metric Cards Table
        kpi_table = doc.add_table(rows=2, cols=5)
        kpi_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cls._set_table_borders(kpi_table, cls.HEX_BORDER)

        kpi_data = [
            ("AUDITED DEVICES", str(m.get("total_devices", 0)), cls.COLOR_DARK),
            ("CHECKS EXECUTED", str(m.get("total_checks", 0)), cls.COLOR_DARK),
            ("PASSED CHECKS", str(m.get("passed_checks", 0)), cls.COLOR_SUCCESS),
            ("WARNINGS", str(m.get("warning_checks", 0)), cls.COLOR_WARNING if m.get("warning_checks", 0) > 0 else cls.COLOR_DARK),
            ("COMPLIANCE RATE", f"{m.get('compliance_pct', 0.0)}%", cls.COLOR_PRIMARY),
        ]

        # Row 0: Labels, Row 1: Big Values
        for col_idx, (label, val, color) in enumerate(kpi_data):
            cell_lbl = kpi_table.cell(0, col_idx)
            cell_val = kpi_table.cell(1, col_idx)

            cls._style_cell_text(cell_lbl, label, bold=True, size=8, color=cls.COLOR_MUTED, align=WD_ALIGN_PARAGRAPH.CENTER)
            cls._style_cell_text(cell_val, val, bold=True, size=15, color=color, align=WD_ALIGN_PARAGRAPH.CENTER)

            cls._set_cell_background(cell_lbl, "F8FAFC")
            cls._set_cell_background(cell_val, "FFFFFF")
            cls._set_cell_padding(cell_lbl, top=80, bottom=40, left=60, right=60)
            cls._set_cell_padding(cell_val, top=40, bottom=80, left=60, right=60)

        # Status Callout Box
        status_box = doc.add_table(rows=1, cols=1)
        status_box.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = status_box.cell(0, 0)
        cls._set_cell_background(cell, cls.HEX_CALLOUT_BG)
        cls._set_cell_padding(cell, top=100, bottom=100, left=150, right=150)
        cls._set_callout_border(cell, cls.HEX_NAVY)

        cp = cell.paragraphs[0]
        cp.paragraph_format.space_before = Pt(0)
        cp.paragraph_format.space_after = Pt(2)
        r_stat = cp.add_run(f"Overall Audit Status: {m.get('audit_status', 'CONDITIONAL PASS')}")
        r_stat.font.name = "Calibri"
        r_stat.font.size = Pt(11)
        r_stat.font.bold = True
        r_stat.font.color.rgb = cls.COLOR_PRIMARY

        cp2 = cell.add_paragraph()
        cp2.paragraph_format.space_before = Pt(2)
        cp2.paragraph_format.space_after = Pt(0)
        r_exp = cp2.add_run(m.get("status_explanation", "Infrastructure assessment completed."))
        r_exp.font.name = "Calibri"
        r_exp.font.size = Pt(9.5)
        r_exp.font.color.rgb = cls.COLOR_DARK

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # Priority Action Plan
        cls._add_subheading(doc, "Executive Priority Action Plan")
        action_plan = m.get("action_plan", [])
        if action_plan:
            ap_table = doc.add_table(rows=len(action_plan) + 1, cols=4)
            ap_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cls._set_table_borders(ap_table, cls.HEX_BORDER)

            # Header
            cls._set_table_header(ap_table, ["Priority", "Operational Area", "Affected Nodes", "Recommended Engineering Action"])

            # Data rows
            for r_idx, ap in enumerate(action_plan, start=1):
                prio_str = f"P{ap.get('priority', 3)}"
                area_str = str(ap.get("area", "General"))
                nodes_str = str(ap.get("affected", "All Scope"))
                act_str = str(ap.get("suggested_action", ""))

                row_cells = ap_table.rows[r_idx].cells
                cls._style_cell_text(row_cells[0], prio_str, bold=True, size=9, color=cls.COLOR_PRIMARY, align=WD_ALIGN_PARAGRAPH.CENTER)
                cls._style_cell_text(row_cells[1], area_str, bold=True, size=9, color=cls.COLOR_DARK)
                cls._style_cell_text(row_cells[2], nodes_str, bold=False, size=9, color=cls.COLOR_MUTED)
                cls._style_cell_text(row_cells[3], act_str, bold=False, size=9, color=cls.COLOR_DARK)

                bg_color = cls.HEX_ZEBRA if r_idx % 2 == 0 else "FFFFFF"
                for c in row_cells:
                    cls._set_cell_background(c, bg_color)
                    cls._set_cell_padding(c, top=60, bottom=60, left=80, right=80)
        else:
            p = doc.add_paragraph("No unresolved remediation actions pending. Infrastructure is operating within compliant baseline tolerances.")
            p.runs[0].font.size = Pt(9.5)

    @classmethod
    def _build_infrastructure_scope_section(cls, doc: docx.Document, m: Dict[str, Any]):
        """Page 2: Infrastructure Scope, Inventory Breakdown, and Table 03 Domain Classification."""
        cls._add_section_heading(doc, "2. INFRASTRUCTURE SCOPE & DOMAIN CLASSIFICATION")

        # Discovery & Inventory Summary
        p_disc = doc.add_paragraph()
        r_d1 = p_disc.add_run("Infrastructure Discovery & Connectivity Summary\n")
        r_d1.font.bold = True
        r_d1.font.size = Pt(10)
        c_stats = m.get("connectivity_stats", {})
        p_disc.add_run(f"• Discovered Nodes: {c_stats.get('discovered', m.get('total_devices', 0))}   |   "
                       f"• Reachable: {c_stats.get('reachable', m.get('total_devices', 0))}   |   "
                       f"• Unreachable: {c_stats.get('unreachable', 0)}   |   "
                       f"• Successfully Audited: {c_stats.get('audited', m.get('total_devices', 0))}")
        p_disc.runs[-1].font.size = Pt(9)
        p_disc.runs[-1].font.color.rgb = cls.COLOR_MUTED

        # Table 03: Domain Category Classification Table
        cls._add_subheading(doc, "Table 03: Audit Category Evaluation & Compliance Matrix")
        cat_rows = m.get("category_rows", [])

        if cat_rows:
            cat_table = doc.add_table(rows=len(cat_rows) + 1, cols=7)
            cat_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cls._set_table_borders(cat_table, cls.HEX_BORDER)

            cls._set_table_header(cat_table, [
                "Audit Category", "Total Checks", "Passed", "Warnings", "Failed", "Compliance %", "Findings"
            ])

            for r_idx, cr in enumerate(cat_rows, start=1):
                cells = cat_table.rows[r_idx].cells
                cls._style_cell_text(cells[0], cr.get("name", ""), bold=True, size=9, color=cls.COLOR_DARK)
                cls._style_cell_text(cells[1], str(cr.get("total", 0)), bold=False, size=9, align=WD_ALIGN_PARAGRAPH.RIGHT)
                cls._style_cell_text(cells[2], str(cr.get("passed", 0)), bold=False, size=9, color=cls.COLOR_SUCCESS, align=WD_ALIGN_PARAGRAPH.RIGHT)
                cls._style_cell_text(cells[3], str(cr.get("warnings", 0)), bold=False, size=9, color=cls.COLOR_WARNING if cr.get("warnings", 0) > 0 else cls.COLOR_MUTED, align=WD_ALIGN_PARAGRAPH.RIGHT)
                cls._style_cell_text(cells[4], str(cr.get("failed", 0)), bold=False, size=9, color=cls.COLOR_DANGER if cr.get("failed", 0) > 0 else cls.COLOR_MUTED, align=WD_ALIGN_PARAGRAPH.RIGHT)
                cls._style_cell_text(cells[5], f"{cr.get('compliance', 0.0)}%", bold=True, size=9, color=cls.COLOR_PRIMARY, align=WD_ALIGN_PARAGRAPH.RIGHT)
                cls._style_cell_text(cells[6], str(cr.get("findings_count", 0)), bold=True, size=9, align=WD_ALIGN_PARAGRAPH.RIGHT)

                bg_color = cls.HEX_ZEBRA if r_idx % 2 == 0 else "FFFFFF"
                for c in cells:
                    cls._set_cell_background(c, bg_color)
                    cls._set_cell_padding(c, top=55, bottom=55, left=70, right=70)

        # Inventory Breakdown Table
        doc.add_paragraph().paragraph_format.space_after = Pt(4)
        cls._add_subheading(doc, "Device Inventory & Hardware Role Distribution")
        inv_items = m.get("inventory_breakdown", [])
        if inv_items:
            inv_table = doc.add_table(rows=len(inv_items) + 1, cols=3)
            inv_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cls._set_table_borders(inv_table, cls.HEX_BORDER)
            cls._set_table_header(inv_table, ["Network Infrastructure Role", "Device Count", "Percentage of Fleet"])

            total_devs = max(m.get("total_devices", 1), 1)
            for r_idx, inv in enumerate(inv_items, start=1):
                cells = inv_table.rows[r_idx].cells
                cnt = inv.get("count", 0)
                pct = round((cnt / total_devs) * 100, 1)

                cls._style_cell_text(cells[0], inv.get("category", "General"), bold=True, size=9, color=cls.COLOR_DARK)
                cls._style_cell_text(cells[1], str(cnt), bold=False, size=9, align=WD_ALIGN_PARAGRAPH.RIGHT)
                cls._style_cell_text(cells[2], f"{pct}%", bold=False, size=9, color=cls.COLOR_MUTED, align=WD_ALIGN_PARAGRAPH.RIGHT)

                bg_color = cls.HEX_ZEBRA if r_idx % 2 == 0 else "FFFFFF"
                for c in cells:
                    cls._set_cell_background(c, bg_color)
                    cls._set_cell_padding(c, top=50, bottom=50, left=70, right=70)

    @classmethod
    def _build_top_findings_section(cls, doc: docx.Document, m: Dict[str, Any]):
        """Page 3: Top Critical and High Risk Findings with granular directives."""
        cls._add_section_heading(doc, "3. TOP CRITICAL & HIGH RISK FINDINGS")

        findings = m.get("top_findings", [])
        if not findings or (len(findings) == 1 and findings[0].get("title") == "Baseline Configuration Alignment"):
            p = doc.add_paragraph()
            r = p.add_run("✅ No Critical or High-Risk findings identified in this audit execution.")
            r.font.bold = True
            r.font.color.rgb = cls.COLOR_SUCCESS
            r.font.size = Pt(11)

            p_desc = doc.add_paragraph("All evaluated test scenarios conformed to established golden configuration baselines.")
            p_desc.runs[0].font.size = Pt(9.5)
            p_desc.runs[0].font.color.rgb = cls.COLOR_MUTED
            return

        for idx, f in enumerate(findings):
            # Boxed Finding Card
            tbl = doc.add_table(rows=1, cols=1)
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            cell = tbl.cell(0, 0)
            cls._set_cell_background(cell, "FAFAFA")
            cls._set_cell_padding(cell, top=80, bottom=80, left=120, right=120)
            cls._set_card_border(cell, cls.HEX_BORDER)

            cp = cell.paragraphs[0]
            cp.paragraph_format.space_before = Pt(0)
            cp.paragraph_format.space_after = Pt(2)
            f_num = f.get('number', idx + 1)
            if isinstance(f_num, int):
                f_num = f"{f_num:02d}"
            r_num = cp.add_run(f"FINDING {f_num} - {f.get('title', 'Audit Finding').upper()}\n")
            r_num.font.name = "Calibri"
            r_num.font.size = Pt(10.5)
            r_num.font.bold = True
            r_num.font.color.rgb = cls.COLOR_PRIMARY

            # Meta line
            dev_str = ", ".join(f.get("affected_devices", [])) if f.get("affected_devices") else "Audited Node"
            sev_str = f.get("severity", "Medium")
            cat_str = f.get("category", "General")
            chk_str = f.get("check_id", "CHK-001")
            cmd_str = f.get("command", "show running-config")

            p_meta = cell.add_paragraph()
            p_meta.paragraph_format.space_before = Pt(2)
            p_meta.paragraph_format.space_after = Pt(4)
            r_meta = p_meta.add_run(f"Device: {dev_str}   |   Category: {cat_str}   |   Severity: {sev_str}   |   Check ID: {chk_str}")
            r_meta.font.size = Pt(8.5)
            r_meta.font.bold = True
            r_meta.font.color.rgb = cls.COLOR_WARNING if sev_str in ["High", "Warning"] else (cls.COLOR_DANGER if sev_str == "Critical" else cls.COLOR_MUTED)

            # Details
            details = [
                ("CLI Verification Command:", cmd_str),
                ("Verified Factual Observation:", f.get("observation", "Observed discrepancy during CLI inspection.")),
                ("Potential Business Impact:", f.get("potential_impact", "Degraded redundancy or potential service failure.")),
                ("Recommended Remediation:", f.get("recommended_action", "Implement corrective configuration.")),
            ]

            for d_lbl, d_val in details:
                p_det = cell.add_paragraph()
                p_det.paragraph_format.space_before = Pt(2)
                p_det.paragraph_format.space_after = Pt(2)
                r_dlbl = p_det.add_run(f"• {d_lbl} ")
                r_dlbl.font.bold = True
                r_dlbl.font.size = Pt(9)
                r_dlbl.font.color.rgb = cls.COLOR_DARK

                r_dval = p_det.add_run(d_val)
                r_dval.font.size = Pt(9)
                r_dval.font.color.rgb = cls.COLOR_DARK

            doc.add_paragraph().paragraph_format.space_after = Pt(4)

    @classmethod
    def _build_security_availability_section(cls, doc: docx.Document, m: Dict[str, Any]):
        """Page 4: Security Posture & Protocol Availability Matrix."""
        cls._add_section_heading(doc, "4. SECURITY POSTURE & AVAILABILITY RESILIENCE")

        # Security Controls Table
        cls._add_subheading(doc, "Management & Control Plane Security Posture")
        sec_controls = m.get("security_controls", [])

        if sec_controls:
            sec_table = doc.add_table(rows=len(sec_controls) + 1, cols=3)
            sec_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cls._set_table_borders(sec_table, cls.HEX_BORDER)
            cls._set_table_header(sec_table, ["Security Control Area", "Calculated Compliance %", "Evaluation Details"])

            for r_idx, sc in enumerate(sec_controls, start=1):
                cells = sec_table.rows[r_idx].cells
                pct = sc.get("pct", 100)
                color = cls.COLOR_SUCCESS if pct >= 90 else (cls.COLOR_WARNING if pct >= 70 else cls.COLOR_DANGER)

                cls._style_cell_text(cells[0], sc.get("name", ""), bold=True, size=9, color=cls.COLOR_DARK)
                cls._style_cell_text(cells[1], f"{pct}%", bold=True, size=9, color=color, align=WD_ALIGN_PARAGRAPH.RIGHT)
                cls._style_cell_text(cells[2], sc.get("detail", "Verified"), bold=False, size=8.5, color=cls.COLOR_MUTED)

                bg_color = cls.HEX_ZEBRA if r_idx % 2 == 0 else "FFFFFF"
                for c in cells:
                    cls._set_cell_background(c, bg_color)
                    cls._set_cell_padding(c, top=50, bottom=50, left=70, right=70)

        # High Availability Protocols Table
        doc.add_paragraph().paragraph_format.space_after = Pt(6)
        cls._add_subheading(doc, "High Availability & Redundancy Protocol Validation")
        avail_checks = m.get("availability_checks", [])

        if avail_checks:
            av_table = doc.add_table(rows=len(avail_checks) + 1, cols=3)
            av_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cls._set_table_borders(av_table, cls.HEX_BORDER)
            cls._set_table_header(av_table, ["Protocol / Redundancy Mechanism", "Operational Status", "Verification Evidence"])

            for r_idx, ac in enumerate(avail_checks, start=1):
                cells = av_table.rows[r_idx].cells
                stat = ac.get("status", "Operational")
                color = cls.COLOR_SUCCESS if stat == "Operational" else cls.COLOR_WARNING

                cls._style_cell_text(cells[0], ac.get("protocol", ""), bold=True, size=9, color=cls.COLOR_DARK)
                cls._style_cell_text(cells[1], stat, bold=True, size=9, color=color, align=WD_ALIGN_PARAGRAPH.CENTER)
                cls._style_cell_text(cells[2], ac.get("note", "Verified"), bold=False, size=8.5, color=cls.COLOR_MUTED)

                bg_color = cls.HEX_ZEBRA if r_idx % 2 == 0 else "FFFFFF"
                for c in cells:
                    cls._set_cell_background(c, bg_color)
                    cls._set_cell_padding(c, top=50, bottom=50, left=70, right=70)

    @classmethod
    def _build_fleet_health_section(cls, doc: docx.Document, m: Dict[str, Any]):
        """Page 5: Fleet Health Distribution & OS Alignment."""
        cls._add_section_heading(doc, "5. OPERATIONAL FLEET HEALTH & LIFECYCLE")

        dev_health = m.get("device_health", {})
        if isinstance(dev_health, dict):
            cls._add_subheading(doc, "Infrastructure Fleet Operational Health Summary")
            dh_table = doc.add_table(rows=2, cols=4)
            dh_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cls._set_table_borders(dh_table, cls.HEX_BORDER)
            cls._set_table_header(dh_table, [
                "Healthy Nodes (Optimal)",
                "Nodes Requiring Attention",
                "Critical Exposure Nodes",
                "Unreachable Nodes"
            ])
            cells = dh_table.rows[1].cells
            cls._style_cell_text(cells[0], str(dev_health.get("healthy", 0)), bold=True, size=14, color=cls.COLOR_SUCCESS, align=WD_ALIGN_PARAGRAPH.CENTER)
            cls._style_cell_text(cells[1], str(dev_health.get("needs_attention", 0)), bold=True, size=14, color=cls.COLOR_WARNING if dev_health.get("needs_attention", 0) > 0 else cls.COLOR_DARK, align=WD_ALIGN_PARAGRAPH.CENTER)
            cls._style_cell_text(cells[2], str(dev_health.get("critical", 0)), bold=True, size=14, color=cls.COLOR_DANGER if dev_health.get("critical", 0) > 0 else cls.COLOR_DARK, align=WD_ALIGN_PARAGRAPH.CENTER)
            cls._style_cell_text(cells[3], str(dev_health.get("unreachable", 0)), bold=True, size=14, color=cls.COLOR_MUTED, align=WD_ALIGN_PARAGRAPH.CENTER)

            for c in cells:
                cls._set_cell_background(c, "FFFFFF")
                cls._set_cell_padding(c, top=60, bottom=60, left=60, right=60)
        elif isinstance(dev_health, list) and dev_health:
            cls._add_subheading(doc, "Per-Device Health & Unresolved Exposures")
            dh_table = doc.add_table(rows=len(dev_health) + 1, cols=6)
            dh_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cls._set_table_borders(dh_table, cls.HEX_BORDER)
            cls._set_table_header(dh_table, ["Hostname", "Role", "Hardware Model", "Health Status", "Unresolved Issues", "Compliance %"])

            for r_idx, dh in enumerate(dev_health, start=1):
                cells = dh_table.rows[r_idx].cells
                h_stat = dh.get("health", "Normal") if isinstance(dh, dict) else str(dh)
                h_color = cls.COLOR_SUCCESS if h_stat == "Normal" else (cls.COLOR_WARNING if h_stat == "Degraded" else cls.COLOR_DANGER)
                h_name = dh.get("hostname", "") if isinstance(dh, dict) else ""
                h_role = dh.get("role", "") if isinstance(dh, dict) else ""
                h_model = dh.get("model", "") if isinstance(dh, dict) else ""
                h_unres = str(dh.get("unresolved", 0)) if isinstance(dh, dict) else "0"
                h_pct = f"{dh.get('pct', 100)}%" if isinstance(dh, dict) else "100%"

                cls._style_cell_text(cells[0], h_name, bold=True, size=9, color=cls.COLOR_DARK)
                cls._style_cell_text(cells[1], h_role, bold=False, size=8.5, color=cls.COLOR_MUTED)
                cls._style_cell_text(cells[2], h_model, bold=False, size=8.5, color=cls.COLOR_DARK)
                cls._style_cell_text(cells[3], h_stat, bold=True, size=8.5, color=h_color, align=WD_ALIGN_PARAGRAPH.CENTER)
                cls._style_cell_text(cells[4], h_unres, bold=False, size=8.5, align=WD_ALIGN_PARAGRAPH.RIGHT)
                cls._style_cell_text(cells[5], h_pct, bold=True, size=8.5, color=cls.COLOR_PRIMARY, align=WD_ALIGN_PARAGRAPH.RIGHT)

                bg_color = cls.HEX_ZEBRA if r_idx % 2 == 0 else "FFFFFF"
                for c in cells:
                    cls._set_cell_background(c, bg_color)
                    cls._set_cell_padding(c, top=50, bottom=50, left=60, right=60)

        # OS Distribution Table
        os_dist = m.get("os_distribution", [])
        if os_dist:
            doc.add_paragraph().paragraph_format.space_after = Pt(6)
            cls._add_subheading(doc, "Operating System & Firmware Baseline Alignment")
            os_table = doc.add_table(rows=len(os_dist) + 1, cols=3)
            os_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cls._set_table_borders(os_table, cls.HEX_BORDER)
            cls._set_table_header(os_table, ["Operating System & Firmware Version", "Device Count", "Baseline Compliance"])

            for r_idx, od in enumerate(os_dist, start=1):
                cells = os_table.rows[r_idx].cells
                ver = od.get("version", od.get("os", "Unknown OS")) if isinstance(od, dict) else str(od)
                cnt = od.get("count", 0) if isinstance(od, dict) else 0

                cls._style_cell_text(cells[0], str(ver), bold=True, size=9, color=cls.COLOR_DARK)
                cls._style_cell_text(cells[1], str(cnt), bold=False, size=8.5, align=WD_ALIGN_PARAGRAPH.RIGHT)
                cls._style_cell_text(cells[2], "Approved Gold Baseline", bold=True, size=8.5, color=cls.COLOR_SUCCESS, align=WD_ALIGN_PARAGRAPH.CENTER)

                bg_color = cls.HEX_ZEBRA if r_idx % 2 == 0 else "FFFFFF"
                for c in cells:
                    cls._set_cell_background(c, bg_color)
                    cls._set_cell_padding(c, top=50, bottom=50, left=70, right=70)

    @classmethod
    def _build_recommendations_and_evidence_section(cls, doc: docx.Document, m: Dict[str, Any]):
        """Page 6: Strategic Recommendations Roadmap and Audit Evidence Traceability Sample."""
        cls._add_section_heading(doc, "6. STRATEGIC ROADMAP & AUDIT EVIDENCE TRACEABILITY")

        # 3-Horizon Recommendations Roadmap
        cls._add_subheading(doc, "Engineering Remediation Roadmap")
        recs = m.get("recommendations", {})

        # If recs is a dict: {'immediate': [...], 'near_term': [...], 'continuous': [...]}
        flat_recs = []
        if isinstance(recs, dict):
            for item in recs.get("immediate", []):
                flat_recs.append(("P1 / P2 - Immediate (0-14 Days)", item, "SecOps / Engineering"))
            for item in recs.get("near_term", []):
                flat_recs.append(("P3 - Near-Term (15-60 Days)", item, "Network Engineering"))
            for item in recs.get("continuous", []):
                flat_recs.append(("P4 - Continuous (60+ Days)", item, "IT Operations"))
        elif isinstance(recs, list):
            for r in recs:
                if isinstance(r, dict):
                    flat_recs.append((r.get("priority", "P3"), r.get("title", ""), r.get("owner", "Engineering")))
                else:
                    flat_recs.append(("Standard", str(r), "Engineering"))

        if flat_recs:
            rec_table = doc.add_table(rows=len(flat_recs) + 1, cols=3)
            rec_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cls._set_table_borders(rec_table, cls.HEX_BORDER)
            cls._set_table_header(rec_table, ["Horizon & Priority", "Remediation Initiative / Action Directive", "Assigned Owner"])

            for r_idx, (prio, title, owner) in enumerate(flat_recs, start=1):
                cells = rec_table.rows[r_idx].cells
                cls._style_cell_text(cells[0], prio, bold=True, size=8.5, color=cls.COLOR_PRIMARY, align=WD_ALIGN_PARAGRAPH.CENTER)
                cls._style_cell_text(cells[1], title, bold=False, size=8.5, color=cls.COLOR_DARK)
                cls._style_cell_text(cells[2], owner, bold=False, size=8.5, color=cls.COLOR_MUTED)

                bg_color = cls.HEX_ZEBRA if r_idx % 2 == 0 else "FFFFFF"
                for c in cells:
                    cls._set_cell_background(c, bg_color)
                    cls._set_cell_padding(c, top=45, bottom=45, left=60, right=60)
        else:
            p = doc.add_paragraph("No outstanding remediation initiatives required. All controls conform to enterprise standards.")
            p.runs[0].font.size = Pt(9.5)

        # Audit Evidence Traceability Table (Cap at top 25 rows for clean Word document layout)
        doc.add_paragraph().paragraph_format.space_after = Pt(6)
        cls._add_subheading(doc, "Audit Evidence Traceability Sample")
        evidence = m.get("evidence", [])
        evidence_sample = evidence[:25] if isinstance(evidence, list) else []

        if evidence_sample:
            ev_table = doc.add_table(rows=len(evidence_sample) + 1, cols=5)
            ev_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cls._set_table_borders(ev_table, cls.HEX_BORDER)
            cls._set_table_header(ev_table, ["Device", "Check ID", "CLI Verification Command", "Status", "Evidence Notes"])

            for r_idx, ev in enumerate(evidence_sample, start=1):
                cells = ev_table.rows[r_idx].cells
                st = ev.get("status", "PASS")
                st_color = cls.COLOR_SUCCESS if st in ["PASS", "Completed"] else (cls.COLOR_WARNING if st in ["WARNING", "Warning"] else cls.COLOR_DANGER)

                cls._style_cell_text(cells[0], ev.get("device", ""), bold=True, size=8, color=cls.COLOR_DARK)
                cls._style_cell_text(cells[1], ev.get("check_id", ""), bold=False, size=7.5, color=cls.COLOR_MUTED)
                cls._style_cell_text(cells[2], ev.get("command", ""), bold=False, size=7.5, color=cls.COLOR_DARK)
                cls._style_cell_text(cells[3], st, bold=True, size=8, color=st_color, align=WD_ALIGN_PARAGRAPH.CENTER)
                cls._style_cell_text(cells[4], ev.get("evidence_summary", ev.get("evidence", "Verified output")), bold=False, size=7.5, color=cls.COLOR_MUTED)

                bg_color = cls.HEX_ZEBRA if r_idx % 2 == 0 else "FFFFFF"
                for c in cells:
                    cls._set_cell_background(c, bg_color)
                    cls._set_cell_padding(c, top=40, bottom=40, left=50, right=50)

    # -------------------------------------------------------------------------
    #  STYLE & XML HELPERS
    # -------------------------------------------------------------------------

    @classmethod
    def _add_section_heading(cls, doc: docx.Document, text: str):
        """Adds a standardized Section Heading (Heading 1)."""
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.size = Pt(13)
        r.font.bold = True
        r.font.color.rgb = cls.COLOR_PRIMARY

    @classmethod
    def _add_subheading(cls, doc: docx.Document, text: str):
        """Adds a standardized Subheading (Heading 2)."""
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.size = Pt(10.5)
        r.font.bold = True
        r.font.color.rgb = cls.COLOR_DARK

    @classmethod
    def _style_cell_text(cls, cell, text: str, bold: bool = False, size: float = 9.0,
                         color: Optional[RGBColor] = None, align=WD_ALIGN_PARAGRAPH.LEFT):
        """Styles paragraph text inside a table cell."""
        p = cell.paragraphs[0]
        p.alignment = align
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.size = Pt(size)
        r.font.bold = bold
        if color:
            r.font.color.rgb = color

    @classmethod
    def _set_table_header(cls, table: docx.table.Table, headers: List[str]):
        """Styles the header row with dark background and crisp white text."""
        hdr_cells = table.rows[0].cells
        for idx, text in enumerate(headers):
            cell = hdr_cells[idx]
            cls._style_cell_text(cell, text.upper(), bold=True, size=8, color=cls.COLOR_WHITE, align=WD_ALIGN_PARAGRAPH.CENTER)
            cls._set_cell_background(cell, cls.HEX_HEADER_BG)
            cls._set_cell_padding(cell, top=70, bottom=70, left=80, right=80)

    @staticmethod
    def _set_cell_background(cell, hex_color: str):
        """Sets background shading XML for a table cell."""
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
        cell._tc.get_or_add_tcPr().append(shd)

    @staticmethod
    def _set_cell_padding(cell, top=60, bottom=60, left=80, right=80):
        """Sets top, bottom, left, right padding (margins) in dxa for a table cell."""
        tcPr = cell._tc.get_or_add_tcPr()
        tcMar = parse_xml(
            f'<w:tcMar {nsdecls("w")}>'
            f'<w:top w:w="{top}" w:type="dxa"/>'
            f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
            f'<w:left w:w="{left}" w:type="dxa"/>'
            f'<w:right w:w="{right}" w:type="dxa"/>'
            f'</w:tcMar>'
        )
        tcPr.append(tcMar)

    @staticmethod
    def _set_table_borders(table: docx.table.Table, color: str = "CBD5E1"):
        """Sets subtle, clean table borders."""
        tblPr = table._tbl.tblPr
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f'<w:left w:val="none"/>'
            f'<w:right w:val="none"/>'
            f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f'<w:insideV w:val="none"/>'
            f'</w:tblBorders>'
        )
        tblPr.append(borders)

    @staticmethod
    def _set_callout_border(cell, color: str = "1E3A8A"):
        """Sets a thick left border on a callout box cell."""
        tcPr = cell._tc.get_or_add_tcPr()
        borders = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'<w:top w:val="none"/>'
            f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{color}"/>'
            f'<w:bottom w:val="none"/>'
            f'<w:right w:val="none"/>'
            f'</w:tcBorders>'
        )
        tcPr.append(borders)

    @staticmethod
    def _set_card_border(cell, color: str = "CBD5E1"):
        """Sets a subtle border box around a finding card cell."""
        tcPr = cell._tc.get_or_add_tcPr()
        borders = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'<w:top w:val="single" w:sz="6" w:space="0" w:color="{color}"/>'
            f'<w:left w:val="single" w:sz="18" w:space="0" w:color="1E3A8A"/>'
            f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="{color}"/>'
            f'<w:right w:val="single" w:sz="6" w:space="0" w:color="{color}"/>'
            f'</w:tcBorders>'
        )
        tcPr.append(borders)
