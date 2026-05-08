"""Analysis routes for orchestrating compliance checks and rendering results."""

import os

from fasthtml.common import (
    A,
    Details,
    Div,
    Form,
    Option,
    P,
    Summary,
    Request,
    Span,
    Table,
    Tbody,
    Td,
    Th,
    Thead,
    Title,
    Tr,
)
from monsterui.all import H1, Container

from app.components.layout import DashboardLayout
from app.components.ui import (
    Alert,
    AlertT,
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    Checkbox,
    CountTableItemSpec,
    FormLabel,
    ItemsCountDataTable,
    Label,
    Select,
    SubmitButton,
)
from app.modules.orchestrator import BIMGuard_App
from app.services.documents_service import DocumentService
from app.services.projects_service import ProjectsService

_bim_guard_app = BIMGuard_App()
_projects_service = ProjectsService()
_documents_service = DocumentService()

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def _band_badge(band: str):
    colours = {
        "Critical": "bg-red-600 text-white",
        "High": "bg-orange-500 text-white",
        "Medium": "bg-yellow-400 text-black",
        "Low": "bg-green-600 text-white",
    }
    return Span(
        band,
        cls=f"inline-block px-2 py-0.5 rounded text-xs font-semibold {colours.get(band, 'bg-gray-400 text-white')}",
    )


def _compliance_card(results, cost_impact, issue_stats, is_demo, project_id, error):
    """Build the corrosion compliance results card for the analysis results page."""
    if error:
        return Card(
            CardHeader(CardTitle("Corrosion Compliance — GC-001 / CC-001")),
            CardContent(P(f"Compliance engine error: {error}", cls="text-sm text-destructive")),
        )

    if not results:
        return None

    bands = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for r in results:
        b = r.get("risk_band", "Low")
        if b in bands:
            bands[b] += 1

    badge_row = Div(
        *[
            Div(
                _band_badge(b),
                Span(f" {bands[b]}", cls="text-sm font-medium ml-1"),
                cls="flex items-center",
            )
            for b in ("Critical", "High", "Medium", "Low")
        ],
        cls="flex items-center gap-4 flex-wrap",
    )

    cost_line = (
        P(
            f"Estimated remediation: £{cost_impact.total_cost_gbp:,.0f}  |  "
            f"Programme impact: {cost_impact.total_days} days",
            cls="text-sm text-muted-foreground mt-2",
        )
        if cost_impact
        else ""
    )

    tracker_line = (
        P(
            f"Issue history: {issue_stats.get('new', 0)} new, "
            f"{issue_stats.get('updated', 0)} updated, "
            f"{issue_stats.get('resolved', 0)} resolved.",
            cls="text-xs text-muted-foreground mt-1",
        )
        if issue_stats
        else ""
    )

    demo_notice = (
        Alert(
            "No IFC file found — showing synthetic demo data (25 representative MEP elements).",
            cls=AlertT.info if hasattr(AlertT, "info") else "",
        )
        if is_demo
        else ""
    )

    flagged = [r for r in results if r.get("risk_band", "Low") != "Low"]

    if flagged:
        header_cells = [
            Th(h, cls="px-3 py-2 text-left text-xs font-semibold text-muted-foreground bg-muted")
            for h in ("Element", "Floor", "Material", "Band", "Score", "Required Action")
        ]
        data_rows = []
        for r in flagged[:20]:
            data_rows.append(
                Tr(
                    Td(r.get("name", "—")[:40], cls="px-3 py-2 text-sm"),
                    Td(r.get("floor", "—"), cls="px-3 py-2 text-sm"),
                    Td(r.get("material_a", "—")[:22], cls="px-3 py-2 text-sm"),
                    Td(_band_badge(r.get("risk_band", "Low")), cls="px-3 py-2"),
                    Td(f"{r.get('overall_score', 0):.3f}", cls="px-3 py-2 text-sm font-mono"),
                    Td(r.get("action", "—")[:70], cls="px-3 py-2 text-xs"),
                    cls="border-b border-muted last:border-0",
                )
            )
        if len(flagged) > 20:
            data_rows.append(
                Tr(
                    Td(
                        f"… and {len(flagged) - 20} more flagged elements",
                        cls="px-3 py-2 text-xs text-muted-foreground italic",
                        colspan="6",
                    )
                )
            )
        results_table = Div(
            Table(
                Thead(Tr(*header_cells)),
                Tbody(*data_rows),
                cls="w-full text-sm",
            ),
            cls="overflow-auto mt-4 border rounded-md",
        )
    else:
        results_table = P(
            "No elements flagged at Medium risk or above.",
            cls="text-sm text-muted-foreground mt-3",
        )

    bcf_btn = (
        Div(
            A(
                "Download BCF Report",
                href=f"/reports/bcf/{project_id}",
                cls="inline-block mt-4 px-4 py-2 bg-primary text-primary-foreground text-sm rounded-md hover:opacity-90",
            ),
        )
        if project_id
        else ""
    )

    return Card(
        CardHeader(CardTitle("Corrosion Compliance — GC-001 / CC-001")),
        CardContent(
            demo_notice,
            badge_row,
            cost_line,
            tracker_line,
            results_table,
            bcf_btn,
        ),
    )


def _rule_validation_card(rule_validations: list[dict], analysis_theme: str):
    """Build the Module 3 rule validation card for the analysis results page."""
    if not rule_validations:
        return Card(
            CardHeader(CardTitle(f"Rule Validation — Module 3 ({analysis_theme})")),
            CardContent(
                P(
                    f"No {analysis_theme} rules found in the library. "
                    "Go to Library → Rule Extraction Studio to extract and save rules first.",
                    cls="text-sm text-muted-foreground",
                )
            ),
        )

    present = sum(1 for r in rule_validations if r["status"] == "present")
    not_found = len(rule_validations) - present

    summary = Div(
        Div(
            Span(str(len(rule_validations)), cls="text-2xl font-bold"),
            Span(" rules checked", cls="text-sm text-muted-foreground ml-1"),
            cls="flex items-baseline",
        ),
        Div(
            Span(
                f"{present} matched",
                cls="inline-block px-2 py-0.5 rounded text-xs font-semibold bg-green-100 text-green-800 mr-2",
            ),
            Span(
                f"{not_found} no elements",
                cls="inline-block px-2 py-0.5 rounded text-xs font-semibold bg-yellow-100 text-yellow-800",
            ),
            cls="mt-1",
        ),
        cls="mb-4",
    )

    header_cells = [
        Th(h, cls="px-3 py-2 text-left text-xs font-semibold text-muted-foreground bg-muted")
        for h in ("Reference", "Description", "Target IFC Class", "Elements in Model", "Status")
    ]

    def _status_badge(status: str, count: int):
        if status == "present":
            return Span(
                f"✓ {count} found",
                cls="inline-block px-2 py-0.5 rounded text-xs font-semibold bg-green-100 text-green-800",
            )
        return Span(
            "No elements",
            cls="inline-block px-2 py-0.5 rounded text-xs font-semibold bg-yellow-100 text-yellow-800",
        )

    data_rows = []
    for r in rule_validations:
        data_rows.append(
            Tr(
                Td(r.get("reference", "—"), cls="px-3 py-2 text-xs font-mono"),
                Td(
                    r.get("description", "")[:80]
                    + ("…" if len(r.get("description", "")) > 80 else ""),
                    cls="px-3 py-2 text-sm",
                ),
                Td(r.get("target_ifc_class", "—"), cls="px-3 py-2 text-xs font-mono text-blue-700"),
                Td(str(r.get("element_count", 0)), cls="px-3 py-2 text-sm text-center"),
                Td(_status_badge(r["status"], r["element_count"]), cls="px-3 py-2"),
                cls="border-b border-muted last:border-0",
            )
        )

    return Card(
        CardHeader(
            Div(
                CardTitle(f"Rule Validation — Module 3 ({analysis_theme})"),
                P(
                    "Each library rule is checked against the IFC model. "
                    "'No elements' means that IFC class is absent from this model.",
                    cls="text-xs text-muted-foreground mt-0.5",
                ),
            )
        ),
        CardContent(
            summary,
            Div(
                Table(
                    Thead(Tr(*header_cells)),
                    Tbody(*data_rows),
                    cls="w-full text-sm",
                ),
                cls="overflow-auto border rounded-md",
            ),
        ),
    )


def _rule_compliance_card(
    compliance_results: list[dict], summary: dict, error: str | None, analysis_theme: str
):
    """Module 4 rule compliance card — shows PASS/FAIL per rule with element details."""
    title = f"Rule Compliance Check — Module 4 ({analysis_theme})"

    if error:
        return Card(
            CardHeader(CardTitle(title)),
            CardContent(P(f"Compliance check error: {error}", cls="text-sm text-destructive")),
        )

    if not compliance_results:
        return None

    total = summary.get("total_rules", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    missing = summary.get("missing_data", 0)
    no_elem = summary.get("no_elements", 0)
    rate = summary.get("pass_rate", 0)
    mand_f = summary.get("mandatory_failed", 0)

    # Colour the pass-rate pill
    rate_cls = (
        "bg-green-100 text-green-800"
        if rate >= 80
        else "bg-yellow-100 text-yellow-800"
        if rate >= 50
        else "bg-red-100 text-red-800"
    )

    summary_bar = Div(
        Span(
            f"{rate:.0f}% pass rate",
            cls=f"inline-block px-3 py-1 rounded-full text-sm font-semibold {rate_cls} mr-3",
        ),
        Span(f"✓ {passed} passed", cls="text-xs text-green-700 mr-2"),
        Span(f"✗ {failed} failed", cls="text-xs text-red-700 mr-2"),
        Span(f"~ {missing} missing data", cls="text-xs text-yellow-700 mr-2") if missing else "",
        Span(f"○ {no_elem} no elements", cls="text-xs text-muted-foreground") if no_elem else "",
        Span(f"  ⚠ {mand_f} mandatory failures", cls="text-xs text-red-600 font-semibold ml-2")
        if mand_f
        else "",
        cls="flex flex-wrap items-center gap-1 mb-4",
    )

    _STATUS_CLS = {
        "PASS": "bg-green-100 text-green-800",
        "FAIL": "bg-red-100 text-red-800",
        "MISSING_DATA": "bg-yellow-100 text-yellow-800",
        "PARTIAL": "bg-orange-100 text-orange-800",
        "NO_ELEMENTS": "bg-gray-100 text-gray-600",
    }

    header_cells = [
        Th(h, cls="px-3 py-2 text-left text-xs font-semibold text-muted-foreground bg-muted")
        for h in ("Ref", "Description", "Target", "Property", "Rule", "Status", "Pass/Fail/Miss")
    ]

    rows = []
    for r in compliance_results:
        op = r.get("operator", "")
        if op == "between":
            rule_str = f"between {r.get('value_min')}–{r.get('value_max')} {r.get('unit', '')}"
        elif op == "exists":
            rule_str = "exists"
        else:
            rule_str = f"{op} {r.get('check_value', '')} {r.get('unit', '')}".strip()

        status = r.get("status", "")
        s_cls = _STATUS_CLS.get(status, "bg-gray-100 text-gray-600")

        counts = Span(
            f"{r.get('pass_count', 0)} / {r.get('fail_count', 0)} / {r.get('missing_count', 0)}",
            cls="font-mono text-xs",
        )

        # Collapsible failure details
        failures = r.get("failures", [])
        fail_detail = ""
        if failures:
            fail_rows = [
                Tr(
                    Td(f.get("element_name", "")[:40], cls="px-2 py-1 text-xs font-mono"),
                    Td(str(f.get("actual", "")), cls="px-2 py-1 text-xs"),
                    Td(f.get("reason", ""), cls="px-2 py-1 text-xs text-red-700"),
                )
                for f in failures[:20]
            ]
            fail_detail = Details(
                Summary(
                    f"{len(failures)} failing element(s)", cls="text-xs text-red-600 cursor-pointer"
                ),
                Div(
                    Table(
                        Thead(
                            Tr(
                                Th("Element", cls="px-2 py-1 text-xs bg-muted"),
                                Th("Actual", cls="px-2 py-1 text-xs bg-muted"),
                                Th("Reason", cls="px-2 py-1 text-xs bg-muted"),
                            )
                        ),
                        Tbody(*fail_rows),
                        cls="w-full text-xs border rounded mt-1",
                    ),
                    cls="max-h-48 overflow-y-auto",
                ),
            )

        rows.append(
            Tr(
                Td(r.get("rule_ref", "—"), cls="px-3 py-2 text-xs font-mono"),
                Td(
                    Div(
                        (r.get("rule_desc", "") or "")[:70]
                        + ("…" if len(r.get("rule_desc", "") or "") > 70 else ""),
                        fail_detail,
                    ),
                    cls="px-3 py-2 text-xs",
                ),
                Td(r.get("target", "—"), cls="px-3 py-2 text-xs font-mono text-blue-700"),
                Td(r.get("property_name", ""), cls="px-3 py-2 text-xs font-mono"),
                Td(rule_str, cls="px-3 py-2 text-xs font-mono"),
                Td(
                    Span(
                        status,
                        cls=f"inline-block px-1.5 py-0.5 rounded text-xs font-semibold {s_cls}",
                    ),
                    cls="px-3 py-2",
                ),
                Td(counts, cls="px-3 py-2"),
                cls="border-b border-muted last:border-0",
            )
        )

    csv_btn = A(
        "Download CSV",
        href="/reports/compliance-csv",
        cls="inline-block px-3 py-1.5 rounded text-xs font-medium bg-slate-800 text-white hover:bg-slate-600 mt-3",
    )

    return Card(
        CardHeader(
            Div(
                CardTitle(title),
                P(
                    "Full property-level compliance check against every rule in the library.",
                    cls="text-xs text-muted-foreground mt-0.5",
                ),
            )
        ),
        CardContent(
            summary_bar,
            Div(
                Table(Thead(Tr(*header_cells)), Tbody(*rows), cls="w-full text-sm"),
                cls="overflow-auto border rounded-md",
            ),
            csv_btn,
        ),
    )


# Module-level cache for CSV export (populated in analysis_run_post)
_last_compliance_results: list[dict] = []


def setup_routes(rt):
    """Register analysis workflow routes."""

    @rt("/analysis/run")
    def analysis_run():
        projects = _projects_service.list_projects()
        documents = _documents_service.list_documents()

        project_options = [
            Option("— select a project —", value="", disabled=True, selected=True)
        ] + [Option(p.get("name", f"Project {p['id']}"), value=str(p["id"])) for p in projects]

        doc_checkboxes = []
        for doc in documents:
            doc_checkboxes.append(
                Div(
                    Checkbox(
                        id=f"doc_{doc['id']}",
                        name="document_ids",
                        value=str(doc["id"]),
                        cls="mr-2",
                    ),
                    Label(
                        doc.get("filename", f"Document {doc['id']}"),
                        for_=f"doc_{doc['id']}",
                        cls="text-sm cursor-pointer",
                    ),
                    cls="flex items-center gap-1",
                )
            )

        if not doc_checkboxes:
            doc_checkboxes = [P("No documents uploaded yet.", cls="text-sm text-muted-foreground")]

        return Title("Run Analysis - BIM Guard"), DashboardLayout(
            Container(
                Div(
                    Card(
                        CardHeader(CardTitle("Select Inputs")),
                        CardContent(
                            Form(
                                Div(
                                    Div(
                                        FormLabel("Project (IFC Model)", fr="project_id"),
                                        Select(
                                            *project_options,
                                            id="project_id",
                                            name="project_id",
                                            required=True,
                                        ),
                                    ),
                                    Div(
                                        FormLabel("Analysis Theme", fr="analysis_theme"),
                                        Select(
                                            Option("Architecture", value="Architecture", selected=True),
                                            Option("MEP", value="MEP"),
                                            id="analysis_theme",
                                            name="analysis_theme",
                                            required=True,
                                        ),
                                    ),
                                    Div(
                                        FormLabel("Documents"),
                                        Div(
                                            *doc_checkboxes,
                                            cls="space-y-2 border rounded-md p-3 bg-muted/30",
                                        ),
                                    ),
                                    Div(
                                        FormLabel("Count Options"),
                                        Div(
                                            Div(
                                                Checkbox(
                                                    id="include_openings",
                                                    name="include_openings",
                                                    value="1",
                                                    checked=True,
                                                    cls="mr-2",
                                                ),
                                                Label(
                                                    "Include openings (IfcOpeningElement)",
                                                    for_="include_openings",
                                                    cls="text-sm cursor-pointer",
                                                ),
                                                cls="flex items-center gap-1",
                                            ),
                                            Div(
                                                Checkbox(
                                                    id="include_spaces",
                                                    name="include_spaces",
                                                    value="1",
                                                    checked=True,
                                                    cls="mr-2",
                                                ),
                                                Label(
                                                    "Include spaces (IfcSpace)",
                                                    for_="include_spaces",
                                                    cls="text-sm cursor-pointer",
                                                ),
                                                cls="flex items-center gap-1",
                                            ),
                                            Div(
                                                Checkbox(
                                                    id="include_type_definitions",
                                                    name="include_type_definitions",
                                                    value="1",
                                                    cls="mr-2",
                                                ),
                                                Label(
                                                    "Include type definitions (IfcElementType)",
                                                    for_="include_type_definitions",
                                                    cls="text-sm cursor-pointer",
                                                ),
                                                cls="flex items-center gap-1",
                                            ),
                                            cls="space-y-2 border rounded-md p-3 bg-muted/30",
                                        ),
                                    ),
                                    Div(
                                        SubmitButton(
                                            "Run Analysis",
                                            variant="primary",
                                        ),
                                        Div(
                                            P(
                                                "Running analysis…",
                                                cls="text-sm text-muted-foreground",
                                            ),
                                            id="run-spinner",
                                            cls="htmx-indicator",
                                            style="display:none",
                                        ),
                                        cls="flex items-center gap-4",
                                    ),
                                ),
                                hx_post="/analysis/results",
                                hx_target="#analysis-results",
                                hx_swap="innerHTML",
                                hx_indicator="#run-spinner",
                            ),
                        ),
                    ),
                    Div(id="analysis-results"),
                )
            )
        )

    @rt("/analysis/results", methods=["POST"])
    async def analysis_run_post(req: Request):
        form = await req.form()
        project_id_raw = form.get("project_id") or ""
        if not project_id_raw:
            return Alert("Please select a project.", cls=AlertT.error)
        try:
            project_id = int(project_id_raw)
        except ValueError:
            return Alert("Invalid project selection.", cls=AlertT.error)

        doc_ids = [int(v) for v in form.getlist("document_ids") if v]
        analysis_theme = (form.get("analysis_theme") or "Architecture").strip()
        include_openings = bool(form.get("include_openings"))
        include_spaces = bool(form.get("include_spaces"))
        include_type_definitions = bool(form.get("include_type_definitions"))
        result = _bim_guard_app.orchestrate_workflow(
            project_id,
            doc_ids,
            analysis_theme=analysis_theme,
            include_openings=include_openings,
            include_spaces=include_spaces,
            include_type_definitions=include_type_definitions,
        )

        if "error" in result:
            return Alert(result["error"], cls=AlertT.error)

        project = result["project"]
        selected_theme = result.get("analysis_theme", "Architecture")
        ifc_count = result["ifc_element_count"]
        ifc_type_counts = result.get("ifc_type_counts") or {}
        ifc_totals = result.get("ifc_totals") or {}
        ifc_error = result["ifc_error"]

        # IFC summary card
        if ifc_error:
            ifc_detail = P(f"IFC parsing error: {ifc_error}", cls="text-sm text-destructive")
        elif not _projects_service.resolve_ifc_file(project_id):
            ifc_detail = P(
                "No IFC file attached to this project.",
                cls="text-sm text-muted-foreground",
            )
        else:
            filters = ifc_totals.get("filters") or {}
            deltas = ifc_totals.get("excluded_or_added") or {}
            counts_table = ItemsCountDataTable(
                [
                    CountTableItemSpec(
                        label="Built Elements",
                        total=int(ifc_totals.get("built_elements", ifc_count)),
                        subtotal=int(ifc_totals.get("built_elements", ifc_count)),
                        note="Schema-aware building entities",
                    ),
                    CountTableItemSpec(
                        label="All Physical Elements",
                        total=int(ifc_totals.get("all_physical_elements", 0)),
                        subtotal=int(ifc_totals.get("adjusted_physical_elements", ifc_count)),
                        note="Based on IfcElement",
                    ),
                    CountTableItemSpec(
                        label="All Products",
                        total=int(ifc_totals.get("all_products", 0)),
                        subtotal=int(ifc_totals.get("adjusted_products", 0)),
                        note="Based on IfcProduct",
                    ),
                ],
                caption="Built, physical, and product item counts",
                options_summary=(
                    "Options: "
                    f"openings={'on' if filters.get('include_openings', True) else 'off'} "
                    f"(count: {deltas.get('openings', 0)}), "
                    f"spaces={'on' if filters.get('include_spaces', True) else 'off'} "
                    f"(count: {deltas.get('spaces', 0)}), "
                    f"type defs={'on' if filters.get('include_type_definitions', False) else 'off'} "
                    f"(count: {deltas.get('type_definitions', 0)})."
                ),
                built_type_breakdown=ifc_type_counts,
            )

            ifc_detail = Div(
                counts_table,
                cls="space-y-1",
            )

        doc_cards = []
        for doc in result["documents"]:
            doc_cards.append(
                Card(
                    CardHeader(CardTitle(doc["filename"] or "Untitled document")),
                    CardContent(
                        P(
                            f"{doc['section_count']} text sections extracted.",
                            cls="text-sm text-muted-foreground",
                        )
                    ),
                )
            )

        compliance_card = _compliance_card(
            results=result.get("compliance_results", []),
            cost_impact=result.get("cost_impact"),
            issue_stats=result.get("issue_stats", {}),
            is_demo=result.get("compliance_is_demo", False),
            project_id=result.get("bcf_project_id"),
            error=result.get("compliance_error"),
        )

        rule_validation_card = _rule_validation_card(
            result.get("rule_validations", []), selected_theme
        )

        rc = result.get("rule_compliance", [])
        rc_summary = result.get("rule_compliance_summary", {})
        rc_error = result.get("rule_compliance_error")

        # Cache for CSV download
        global _last_compliance_results
        _last_compliance_results = rc

        rule_compliance_card = _rule_compliance_card(rc, rc_summary, rc_error, selected_theme)

        sections = [
            Card(
                CardHeader(CardTitle(f"{project.get('name', 'Project')} — {selected_theme} Theme")),
                CardContent(ifc_detail),
            ),
            *(doc_cards or [P("No documents selected.", cls="text-sm text-muted-foreground")]),
            rule_validation_card,
        ]
        if rule_compliance_card:
            sections.append(rule_compliance_card)
        if selected_theme == "MEP" and compliance_card:
            sections.append(compliance_card)

        return Div(*sections, cls="space-y-4")

    @rt("/reports/compliance-csv")
    def compliance_csv_download():
        """Download the last rule compliance check as a CSV file."""
        from starlette.responses import Response as StarletteResponse
        from app.modules.module5_reporter import Module5_Reporter

        csv_content = Module5_Reporter().generate_csv_summary(_last_compliance_results)
        return StarletteResponse(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="compliance_results.csv"'},
        )

    @rt("/reports/bcf/{project_id}")
    def bcf_download(project_id: int):
        from starlette.responses import Response as StarletteResponse

        bcf_file = os.path.join(_DATA_DIR, f"compliance_project_{project_id}.bcf")
        if not os.path.exists(bcf_file):
            return Alert(
                "BCF file not found. Run the analysis first to generate the report.",
                cls=AlertT.error,
            )
        with open(bcf_file, "rb") as fh:
            bcf_bytes = fh.read()
        return StarletteResponse(
            content=bcf_bytes,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="compliance_project_{project_id}.bcf"'
                )
            },
        )

    @rt("/reports")
    def reports():
        return Title("Reports - BIM Guard"), DashboardLayout(
            Container(
                Div(
                    H1("Reports", cls="text-3xl font-bold mb-4 tracking-tight"),
                    P(
                        "Reports will be available once the compliance pipeline is implemented.",
                        cls="text-muted-foreground mb-6",
                    ),
                    Card(
                        CardHeader(CardTitle("Coming Soon")),
                        CardContent(
                            P(
                                "Add report filters, history, and export actions here.",
                                cls="text-sm text-muted-foreground",
                            )
                        ),
                    ),
                    cls="container mx-auto py-6",
                )
            )
        )
