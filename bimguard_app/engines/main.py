"""
BIMGUARD AI — FastHTML Application
main.py

Automated BIM corrosion and spatial compliance checker.
Built with FastHTML + MonsterUI + IfcOpenShell.

Run:
  uv run uvicorn main:app
  or
  python main.py
"""

import io
import sys
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from fasthtml.common import *
from monsterui.all import *

# ── ENGINE IMPORTS ────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
try:
    from demo_data import DEMO_ELEMENTS, get_summary, run_demo_compliance

    DEMO_AVAILABLE = True
except ImportError:
    DEMO_AVAILABLE = False

try:
    import ifcopenshell

    IFC_AVAILABLE = True
except ImportError:
    IFC_AVAILABLE = False

# ── APP SETUP ─────────────────────────────────────────────────────────────────
app, rt = fast_app(
    hdrs=Theme.blue.headers(),
    live=True,
)

# In-memory session store (replace with FastLite SQLite for production)
_session: dict = {}

# ── COLOUR HELPERS ────────────────────────────────────────────────────────────
BAND_COLOURS = {
    "Critical": "bg-red-600 text-white",
    "High": "bg-orange-500 text-white",
    "Medium": "bg-yellow-500 text-white",
    "Low": "bg-green-600 text-white",
}


def band_badge(band: str):
    return Span(
        band, cls=f"px-2 py-0.5 rounded text-xs font-bold {BAND_COLOURS.get(band, 'bg-gray-300')}"
    )


def mech_badge(mech: str):
    colours = {
        "GC-001 Galvanic": "bg-blue-100 text-blue-800",
        "CC-001 Crevice": "bg-purple-100 text-purple-800",
        "MC-001 MIC": "bg-teal-100 text-teal-800",
    }
    return Span(
        mech, cls=f"px-2 py-0.5 rounded text-xs font-semibold {colours.get(mech, 'bg-gray-100')}"
    )


# ── NAV ───────────────────────────────────────────────────────────────────────
def nav():
    return NavBar(
        A("BIMGUARD AI", href="/", cls="font-bold text-lg text-white"),
        A("Run Check", href="/compliance", cls="text-white hover:text-blue-200 text-sm"),
        A("Results", href="/results", cls="text-white hover:text-blue-200 text-sm"),
        A("BCF Issues", href="/issues", cls="text-white hover:text-blue-200 text-sm"),
        A("Cost Impact", href="/cost", cls="text-white hover:text-blue-200 text-sm"),
        cls="bg-blue-900 px-6 py-3 flex items-center gap-6 shadow-md",
    )


def page_wrap(*content, title="BIMGUARD AI"):
    return Titled(
        title,
        nav(),
        Div(*content, cls="max-w-7xl mx-auto px-6 py-8"),
    )


# ── HOME / DASHBOARD ──────────────────────────────────────────────────────────
@rt("/")
def get():
    results = _session.get("results", [])
    summary = get_summary(results) if results else None

    hero = Div(
        Div(
            H1("BIMGUARD AI", cls="text-4xl font-bold text-white"),
            P(
                "Automated BIM Corrosion & Spatial Compliance Checker",
                cls="text-blue-200 text-lg mt-1",
            ),
            P("OpenBIM · IFC ISO 16739-1 · BCF 2.1 · ISO 19650", cls="text-blue-300 text-sm mt-1"),
            cls="flex-1",
        ),
        Div(
            A(
                "Run Compliance Check →",
                href="/compliance",
                cls="bg-cyan-500 hover:bg-cyan-400 text-white font-bold px-6 py-3 rounded-lg text-sm",
            ),
            cls="flex items-center",
        ),
        cls="bg-blue-900 rounded-xl p-8 flex items-center gap-6 mb-8",
    )

    # Pipeline phases
    phases = [
        ("1", "Spatial Filter", "C-to-C spacing\nvs minimum", "bg-blue-800"),
        ("2", "Halo Envelope", "LOD 350 support\nreservation", "bg-blue-700"),
        ("3", "Galvanic Gate", "GC-001 material\ncompatibility", "bg-teal-700"),
        ("3", "Crevice Gate", "CC-001 CCT\nadequacy", "bg-teal-600"),
        ("3", "MIC Gate", "MC-001 dead-leg\nstagnation", "bg-teal-500"),
        ("4", "Resolution Hierarchy", "Who moves,\nhow far, cost", "bg-amber-700"),
        ("5", "Executive Report", "BCF + ISO 19650\n+ cost avoid", "bg-cyan-700"),
    ]
    pipeline = Div(
        H2("Five-Phase Compliance Pipeline", cls="text-lg font-bold text-gray-700 mb-4"),
        Div(
            *[
                Div(
                    Div(
                        p[0],
                        cls=f"w-8 h-8 rounded {p[3]} text-white text-sm font-bold flex items-center justify-center flex-shrink-0",
                    ),
                    Div(
                        P(p[1], cls="font-semibold text-gray-800 text-sm leading-tight"),
                        P(p[2], cls="text-xs text-gray-500 mt-0.5 whitespace-pre-line"),
                        cls="ml-3",
                    ),
                    cls="flex items-start p-3 bg-white rounded-lg border border-gray-100 shadow-sm",
                )
                for p in phases
            ],
            cls="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4",
        ),
        cls="bg-gray-50 rounded-xl p-6 mb-8",
    )

    # Stats (if run)
    if summary:
        stats_section = Div(
            H2("Last Run Results", cls="text-lg font-bold text-gray-700 mb-4"),
            Div(
                _stat_card("Elements checked", summary["total"], "blue"),
                _stat_card("Issues flagged", summary["issues"], "red"),
                _stat_card("Critical", summary["bands"]["Critical"], "red"),
                _stat_card("High", summary["bands"]["High"], "orange"),
                _stat_card("Medium", summary["bands"]["Medium"], "yellow"),
                _stat_card("Cost avoidance", f"£{summary['cost_avoidance']:,}", "green"),
                cls="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4",
            ),
            Div(
                A(
                    "View Results →",
                    href="/results",
                    cls="text-blue-600 hover:text-blue-800 text-sm font-semibold",
                ),
                A(
                    "View BCF Issues →",
                    href="/issues",
                    cls="text-blue-600 hover:text-blue-800 text-sm font-semibold ml-6",
                ),
                A(
                    "View Cost Impact →",
                    href="/cost",
                    cls="text-blue-600 hover:text-blue-800 text-sm font-semibold ml-6",
                ),
                cls="mt-4",
            ),
            cls="bg-white rounded-xl p-6 border border-gray-200 mb-8",
        )
    else:
        stats_section = Div(
            P(
                "No compliance check has been run yet. ",
                A(
                    "Run a demo check →",
                    href="/compliance",
                    cls="text-blue-600 font-semibold hover:underline",
                ),
                cls="text-gray-500 text-sm",
            ),
            cls="bg-gray-50 rounded-xl p-6 border border-dashed border-gray-300 mb-8 text-center",
        )

    # Key finding callout
    finding = Div(
        H2("The defining finding", cls="text-base font-bold text-white mb-2"),
        P(
            "SS316 stainless steel flanges in a pool plant room",
            cls="text-cyan-200 font-semibold mb-1",
        ),
        Div(
            Div(
                Span("GC-001 Galvanic", cls="text-green-300 font-bold text-sm"),
                Span(" 0.00 → Low", cls="text-white text-xl font-bold block mt-1"),
                P(
                    "SS316 is the most noble grade — no galvanic risk",
                    cls="text-blue-200 text-xs mt-1",
                ),
                cls="bg-blue-900 rounded-lg p-4 flex-1",
            ),
            Div(
                Span("CC-001 Crevice", cls="text-red-300 font-bold text-sm"),
                Span(" 0.89 → Critical", cls="text-white text-xl font-bold block mt-1"),
                P(
                    "CCT +10°C exceeded — pool temp 35°C — crevice attack active",
                    cls="text-blue-200 text-xs mt-1",
                ),
                cls="bg-red-900 rounded-lg p-4 flex-1",
            ),
            cls="flex gap-4 mt-3",
        ),
        P(
            "A galvanic-only tool classifies this as safe. BIMGUARD AI correctly identifies it as Critical.",
            cls="text-cyan-100 text-sm mt-3 italic",
        ),
        cls="bg-blue-900 rounded-xl p-6",
    )

    return page_wrap(hero, pipeline, stats_section, finding, title="BIMGUARD AI — Dashboard")


def _stat_card(label, value, colour="blue"):
    colours = {
        "blue": "border-blue-200 bg-blue-50",
        "red": "border-red-200 bg-red-50",
        "orange": "border-orange-200 bg-orange-50",
        "yellow": "border-yellow-200 bg-yellow-50",
        "green": "border-green-200 bg-green-50",
    }
    text_colours = {
        "blue": "text-blue-700",
        "red": "text-red-700",
        "orange": "text-orange-700",
        "yellow": "text-yellow-700",
        "green": "text-green-700",
    }
    return Div(
        P(str(value), cls=f"text-2xl font-bold {text_colours.get(colour, 'text-gray-700')}"),
        P(label, cls="text-xs text-gray-500 mt-1"),
        cls=f"rounded-lg border p-4 {colours.get(colour, 'border-gray-200 bg-gray-50')}",
    )


# ── COMPLIANCE CHECK PAGE ─────────────────────────────────────────────────────
@rt("/compliance")
def get():
    demo_card = Card(
        CardHeader(CardTitle("Run Synthetic Demo")),
        CardBody(
            P(
                "25 pre-configured MEP elements representing a typical commercial building plant room. "
                "Covers pool plant, fire suppression, domestic water, chilled water, and process services.",
                cls="text-sm text-gray-600 mb-4",
            ),
            Div(
                Span("✓ GC-001 Galvanic engine", cls="text-xs text-green-700"),
                Span("✓ CC-001 Crevice engine", cls="text-xs text-green-700 ml-4"),
                Span("✓ MC-001 MIC engine", cls="text-xs text-green-700 ml-4"),
                cls="mb-4",
            ),
            Button(
                "Run 25-element demo →",
                hx_post="/compliance/demo",
                hx_target="#run-status",
                hx_swap="innerHTML",
                hx_indicator="#spinner",
                cls="bg-blue-900 hover:bg-blue-800 text-white font-semibold px-6 py-2 rounded-lg text-sm",
            ),
        ),
        cls="mb-6",
    )

    ifc_card = Card(
        CardHeader(CardTitle("Upload IFC File")),
        CardBody(
            P(
                "Upload an IFC 2x3 or IFC4 file exported from any BIM authoring tool. "
                "The parser reads Pset_MaterialCommon, Pset_PipeSegmentOccurrence, "
                "Pset_CoveringCommon, and IfcZone for environment classification.",
                cls="text-sm text-gray-600 mb-4",
            ),
            Form(
                Div(
                    Input(
                        type="file",
                        name="ifc_file",
                        accept=".ifc",
                        cls="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100",
                    ),
                    cls="mb-4",
                ),
                Button(
                    "Upload and run check →",
                    type="submit",
                    cls="bg-teal-700 hover:bg-teal-600 text-white font-semibold px-6 py-2 rounded-lg text-sm"
                    + ("" if IFC_AVAILABLE else " opacity-50 cursor-not-allowed"),
                    disabled=not IFC_AVAILABLE,
                ),
                hx_post="/compliance/upload",
                hx_target="#run-status",
                hx_swap="innerHTML",
                hx_encoding="multipart/form-data",
            ),
            P(
                "⚠ ifcopenshell not installed — IFC upload disabled. Run: pip install ifcopenshell",
                cls="text-xs text-amber-600 mt-2",
            )
            if not IFC_AVAILABLE
            else "",
        ),
        cls="mb-6",
    )

    status_area = Div(
        Div(cls="htmx-indicator text-sm text-blue-600 mb-2", id="spinner"), id="run-status"
    )

    return page_wrap(
        H1("Run Compliance Check", cls="text-2xl font-bold text-gray-800 mb-6"),
        demo_card,
        ifc_card,
        status_area,
        title="BIMGUARD AI — Run Check",
    )


@rt("/compliance/demo")
def post():
    results = run_demo_compliance()
    _session["results"] = results
    _session["source"] = "synthetic_demo"
    summary = get_summary(results)
    issues = [r for r in results if r["combined_band"] != "Low"]
    return Div(
        Div(
            Span("✓", cls="text-green-600 font-bold text-lg mr-2"),
            Span(
                f"Demo compliance check complete — {len(results)} elements assessed",
                cls="font-semibold text-gray-800",
            ),
            cls="flex items-center mb-4",
        ),
        Div(
            _stat_card("Total elements", summary["total"], "blue"),
            _stat_card("Issues flagged", summary["issues"], "red"),
            _stat_card("Critical", summary["bands"]["Critical"], "red"),
            _stat_card("High", summary["bands"]["High"], "orange"),
            _stat_card("Est. cost", f"£{summary['cost']:,}", "yellow"),
            _stat_card("Cost avoidance", f"£{summary['cost_avoidance']:,}", "green"),
            cls="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-4",
        ),
        Div(
            A(
                "View full results →",
                href="/results",
                cls="bg-blue-900 text-white font-semibold px-4 py-2 rounded-lg text-sm hover:bg-blue-800 mr-3",
            ),
            A(
                "View BCF issues →",
                href="/issues",
                cls="bg-teal-700 text-white font-semibold px-4 py-2 rounded-lg text-sm hover:bg-teal-600 mr-3",
            ),
            A(
                "View cost impact →",
                href="/cost",
                cls="bg-amber-700 text-white font-semibold px-4 py-2 rounded-lg text-sm hover:bg-amber-600",
            ),
        ),
        cls="bg-green-50 border border-green-200 rounded-xl p-5",
    )


@rt("/compliance/upload")
async def post(req):
    if not IFC_AVAILABLE:
        return P("ifcopenshell not installed — IFC upload not available.", cls="text-red-600")
    form = await req.form()
    ifc_file = form.get("ifc_file")
    if not ifc_file or not ifc_file.filename:
        return P("No file selected.", cls="text-red-600")
    try:
        content = await ifc_file.read()
        tmp = Path(f"/tmp/bimguard_{uuid.uuid4().hex}.ifc")
        tmp.write_bytes(content)
        model = ifcopenshell.open(str(tmp))
        tmp.unlink()
        elements = _parse_ifc_elements(model)
        if not elements:
            return P(
                "No IfcPipeSegment or IfcPipeFitting elements found in this IFC model. "
                "Ensure the model contains MEP services with Pset_MaterialCommon populated.",
                cls="text-amber-600 text-sm",
            )
        results = _run_engines_on_ifc(elements)
        _session["results"] = results
        _session["source"] = ifc_file.filename
        summary = get_summary(results)
        return Div(
            Span(
                f"✓ IFC file '{ifc_file.filename}' processed — {len(elements)} elements found",
                cls="font-semibold text-green-700 block mb-3",
            ),
            Div(
                _stat_card("Total", summary["total"], "blue"),
                _stat_card("Issues", summary["issues"], "red"),
                _stat_card("Critical", summary["bands"]["Critical"], "red"),
                _stat_card("Cost", f"£{summary['cost']:,}", "yellow"),
                cls="grid grid-cols-4 gap-3 mb-3",
            ),
            A(
                "View results →",
                href="/results",
                cls="bg-blue-900 text-white font-semibold px-4 py-2 rounded text-sm",
            ),
            cls="bg-green-50 border border-green-200 rounded-xl p-5",
        )
    except Exception as e:
        return P(f"Error processing IFC file: {str(e)}", cls="text-red-600 text-sm")


# ── RESULTS PAGE ──────────────────────────────────────────────────────────────
@rt("/results")
def get(filter: str = "all"):
    results = _session.get("results", [])
    source = _session.get("source", "No data")

    if not results:
        return page_wrap(
            H1("Results", cls="text-2xl font-bold text-gray-800 mb-4"),
            P(
                "No compliance check has been run yet. ",
                A("Run a check →", href="/compliance", cls="text-blue-600 font-semibold"),
                cls="text-gray-500",
            ),
            title="BIMGUARD AI — Results",
        )

    summary = get_summary(results)

    # Filter buttons
    filters = Div(
        *[
            A(
                f,
                href=f"/results?filter={f.lower()}",
                cls="px-3 py-1 rounded text-sm font-semibold mr-2 "
                + (
                    "bg-blue-900 text-white"
                    if filter == f.lower() or (filter == "all" and f == "All")
                    else "bg-gray-100 text-gray-700 hover:bg-gray-200"
                ),
            )
            for f in ["All", "Critical", "High", "Medium", "Low"]
        ],
        cls="mb-4 flex flex-wrap",
    )

    # Filter results
    show = (
        results if filter == "all" else [r for r in results if r["combined_band"].lower() == filter]
    )

    # Summary row
    summary_row = Div(
        _stat_card("Total", summary["total"], "blue"),
        _stat_card("Critical", summary["bands"]["Critical"], "red"),
        _stat_card("High", summary["bands"]["High"], "orange"),
        _stat_card("Medium", summary["bands"]["Medium"], "yellow"),
        _stat_card("Low", summary["bands"]["Low"], "green"),
        _stat_card("Cost avoidance", f"£{summary['cost_avoidance']:,}", "green"),
        cls="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6",
    )

    # Results table
    tbl = Div(
        Table(
            Thead(
                Tr(
                    *[
                        Th(
                            h,
                            cls="text-xs font-semibold text-gray-500 uppercase px-3 py-2 bg-gray-50 text-left",
                        )
                        for h in [
                            "ID",
                            "Service",
                            "Floor",
                            "Material",
                            "Combined",
                            "GC-001",
                            "CC-001",
                            "MC-001",
                            "Primary mechanism",
                        ]
                    ]
                )
            ),
            Tbody(
                *[
                    Tr(
                        Td(r["id"], cls="px-3 py-2 text-xs text-gray-600 font-mono"),
                        Td(r["service"], cls="px-3 py-2 text-xs text-gray-700"),
                        Td(r["floor"], cls="px-3 py-2 text-xs text-gray-500"),
                        Td(r.get("mat_a", ""), cls="px-3 py-2 text-xs text-gray-500"),
                        Td(band_badge(r["combined_band"]), cls="px-3 py-2"),
                        Td(f"{r['gc_score']:.2f}", cls="px-3 py-2 text-xs text-gray-600"),
                        Td(f"{r['cc_score']:.2f}", cls="px-3 py-2 text-xs text-gray-600"),
                        Td(f"{r['mc_score']:.2f}", cls="px-3 py-2 text-xs text-gray-600"),
                        Td(mech_badge(r["primary_mechanism"]), cls="px-3 py-2"),
                        cls="border-t border-gray-100 hover:bg-gray-50",
                    )
                    for r in show
                ]
            ),
            cls="w-full text-sm",
        ),
        cls="bg-white rounded-xl border border-gray-200 overflow-auto",
    )

    # CSV export
    export = Div(
        A(
            "Export CSV →",
            href="/results/csv",
            cls="text-blue-600 text-sm font-semibold hover:underline",
        ),
        P(f"Source: {source}", cls="text-xs text-gray-400 ml-4 inline"),
        cls="mt-4",
    )

    return page_wrap(
        H1("Compliance Results", cls="text-2xl font-bold text-gray-800 mb-4"),
        summary_row,
        filters,
        tbl,
        export,
        title="BIMGUARD AI — Results",
    )


@rt("/results/csv")
def get():
    results = _session.get("results", [])
    if not results:
        return P("No results.")
    lines = [
        "ID,Service,Floor,Zone,Material,CombinedBand,CombinedScore,GC_Score,GC_Band,CC_Score,CC_Band,MC_Score,MC_Band,PrimaryMechanism"
    ]
    for r in results:
        lines.append(
            f"{r['id']},{r['service']},{r['floor']},{r['zone']},{r.get('mat_a', '')},{r['combined_band']},{r['combined_score']},{r['gc_score']},{r['gc_band']},{r['cc_score']},{r['cc_band']},{r['mc_score']},{r['mc_band']},{r['primary_mechanism']}"
        )
    csv_content = "\n".join(lines)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bimguard_results.csv"},
    )


# ── BCF ISSUES PAGE ───────────────────────────────────────────────────────────
@rt("/issues")
def get():
    results = _session.get("results", [])
    issues = [r for r in results if r["combined_band"] != "Low"]

    if not issues:
        return page_wrap(
            H1("BCF Issues", cls="text-2xl font-bold text-gray-800 mb-4"),
            P(
                "No issues found. " if results else "No compliance check has been run yet. ",
                A("Run a check →", href="/compliance", cls="text-blue-600 font-semibold"),
                cls="text-gray-500",
            ),
            title="BIMGUARD AI — BCF Issues",
        )

    def issue_card(r):
        band = r["combined_band"]
        border_colours = {
            "Critical": "border-red-400",
            "High": "border-orange-400",
            "Medium": "border-yellow-400",
        }
        return Div(
            Div(
                Div(
                    band_badge(band), mech_badge(r["primary_mechanism"]), cls="flex gap-2 flex-wrap"
                ),
                P(f"Score: {r['combined_score']:.3f}", cls="text-xs text-gray-500 mt-1"),
                cls="flex-1",
            ),
            Div(
                P(r["id"], cls="font-mono text-xs text-gray-700 font-bold"),
                P(
                    f"{r['service']} · {r['floor']} · {r['zone']}",
                    cls="text-xs text-gray-500 mt-0.5",
                ),
                P(f"Material: {r.get('mat_a', '—')}", cls="text-xs text-gray-400 mt-0.5"),
                cls="flex-1",
            ),
            Div(
                P(f"GC: {r['gc_score']:.2f}", cls="text-xs text-gray-500"),
                P(f"CC: {r['cc_score']:.2f}", cls="text-xs text-gray-500"),
                P(f"MC: {r['mc_score']:.2f}", cls="text-xs text-gray-500"),
                cls="text-right",
            ),
            cls=f"flex items-center gap-4 p-4 border-l-4 {border_colours.get(band, 'border-gray-300')} bg-white rounded-lg border border-gray-100 shadow-sm mb-3",
        )

    critical = [r for r in issues if r["combined_band"] == "Critical"]
    high = [r for r in issues if r["combined_band"] == "High"]
    medium = [r for r in issues if r["combined_band"] == "Medium"]

    return page_wrap(
        Div(
            H1("BCF Issue Manager", cls="text-2xl font-bold text-gray-800"),
            Div(
                A(
                    "Download BCF 2.1 →",
                    href="/issues/bcf",
                    cls="bg-blue-900 text-white font-semibold px-4 py-2 rounded-lg text-sm hover:bg-blue-800",
                ),
                cls="ml-auto",
            ),
            cls="flex items-center mb-6",
        ),
        Div(
            _stat_card("Total issues", len(issues), "red"),
            _stat_card("Critical", len(critical), "red"),
            _stat_card("High", len(high), "orange"),
            _stat_card("Medium", len(medium), "yellow"),
            cls="grid grid-cols-4 gap-3 mb-6",
        ),
        H2("Critical", cls="text-base font-bold text-red-700 mb-3") if critical else "",
        *[issue_card(r) for r in critical],
        H2("High", cls="text-base font-bold text-orange-700 mb-3 mt-4") if high else "",
        *[issue_card(r) for r in high],
        H2("Medium", cls="text-base font-bold text-yellow-700 mb-3 mt-4") if medium else "",
        *[issue_card(r) for r in medium],
        title="BIMGUARD AI — BCF Issues",
    )


@rt("/issues/bcf")
def get():
    results = _session.get("results", [])
    issues = [r for r in results if r["combined_band"] != "Low"]
    if not issues:
        return P("No issues to export.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in issues:
            iid = str(uuid.uuid4())
            cost = {"Critical": 8800, "High": 5000, "Medium": 2200}.get(r["combined_band"], 0)
            markup = f"""<?xml version="1.0" encoding="utf-8"?>
<Markup>
  <Topic Guid="{iid}" TopicType="Issue" TopicStatus="Open">
    <Title>BIMGUARD AI — {r["combined_band"]} — {r["id"]} — {r["primary_mechanism"]}</Title>
    <Priority>{r["combined_band"]}</Priority>
    <CreationDate>{datetime.utcnow().isoformat()}Z</CreationDate>
    <CreationAuthor>BIMGUARD AI v1.0.0</CreationAuthor>
    <AssignedTo>Mechanical Engineer</AssignedTo>
    <Description>
Element: {r["id"]} | Service: {r["service"]} | Floor: {r["floor"]} | Zone: {r["zone"]}
Material: {r.get("mat_a", "—")}
Combined Score: {r["combined_score"]} | Band: {r["combined_band"]}
GC-001: {r["gc_score"]:.3f} ({r["gc_band"]}) | CC-001: {r["cc_score"]:.3f} ({r["cc_band"]}) | MC-001: {r["mc_score"]:.3f} ({r["mc_band"]})
Primary mechanism: {r["primary_mechanism"]}
Estimated remediation cost: £{cost:,}
    </Description>
    <Components>
      <Component IfcGuid="{r["id"]}" Selected="true" Visible="true"/>
    </Components>
  </Topic>
</Markup>"""
            zf.writestr(f"{iid}/markup.bcf", markup)
    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=BIMGUARD_BCF_Issues.bcf.zip"},
    )


# ── COST IMPACT PAGE ──────────────────────────────────────────────────────────
@rt("/cost")
def get():
    results = _session.get("results", [])
    if not results:
        return page_wrap(
            H1("Cost Impact", cls="text-2xl font-bold text-gray-800 mb-4"),
            P(
                "No compliance check has been run yet. ",
                A("Run a check →", href="/compliance", cls="text-blue-600 font-semibold"),
                cls="text-gray-500",
            ),
            title="BIMGUARD AI — Cost Impact",
        )

    unit_costs = {"Critical": 8800, "High": 5000, "Medium": 2200, "Low": 0}
    unit_days = {"Critical": 5, "High": 3, "Medium": 2, "Low": 0}

    total_cost = sum(unit_costs.get(r["combined_band"], 0) for r in results)
    total_days = sum(unit_days.get(r["combined_band"], 0) for r in results)
    avoidance = total_cost * 5
    field_equiv = total_cost * 6

    issues = [r for r in results if r["combined_band"] != "Low"]

    # Cost by band
    by_band = {b: {"count": 0, "cost": 0, "days": 0} for b in ["Critical", "High", "Medium"]}
    by_mech = {
        "GC-001 Galvanic": {"count": 0, "cost": 0},
        "CC-001 Crevice": {"count": 0, "cost": 0},
        "MC-001 MIC": {"count": 0, "cost": 0},
    }
    for r in issues:
        b = r["combined_band"]
        if b in by_band:
            by_band[b]["count"] += 1
            by_band[b]["cost"] += unit_costs[b]
            by_band[b]["days"] += unit_days[b]
        m = r["primary_mechanism"]
        if m in by_mech:
            by_mech[m]["count"] += 1
            by_mech[m]["cost"] += unit_costs.get(b, 0)

    # Header stats
    header_stats = Div(
        Div(
            P(f"£{total_cost:,}", cls="text-3xl font-bold text-red-700"),
            P("Design-stage remediation cost", cls="text-xs text-gray-500 mt-1"),
            cls="bg-red-50 border border-red-200 rounded-xl p-5",
        ),
        Div(
            P(f"£{field_equiv:,}", cls="text-3xl font-bold text-orange-700"),
            P("Field-stage equivalent (6× multiplier)", cls="text-xs text-gray-500 mt-1"),
            cls="bg-orange-50 border border-orange-200 rounded-xl p-5",
        ),
        Div(
            P(f"£{avoidance:,}", cls="text-3xl font-bold text-green-700"),
            P("Cost avoidance (field − design stage)", cls="text-xs text-gray-500 mt-1"),
            cls="bg-green-50 border border-green-200 rounded-xl p-5",
        ),
        Div(
            P(f"{total_days} days", cls="text-3xl font-bold text-blue-700"),
            P("Total programme delay avoided", cls="text-xs text-gray-500 mt-1"),
            cls="bg-blue-50 border border-blue-200 rounded-xl p-5",
        ),
        cls="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8",
    )

    # By band table
    band_tbl = Div(
        H2("Breakdown by risk band", cls="text-base font-bold text-gray-700 mb-3"),
        Table(
            Thead(
                Tr(
                    *[
                        Th(
                            h,
                            cls="text-xs font-semibold text-gray-500 uppercase px-3 py-2 bg-gray-50 text-left",
                        )
                        for h in [
                            "Risk band",
                            "Issues",
                            "Estimated cost",
                            "Programme delay",
                            "Unit cost",
                        ]
                    ]
                )
            ),
            Tbody(
                *[
                    Tr(
                        Td(band_badge(b), cls="px-3 py-2"),
                        Td(str(d["count"]), cls="px-3 py-2 text-sm"),
                        Td(f"£{d['cost']:,}", cls="px-3 py-2 text-sm font-semibold"),
                        Td(f"{d['days']} days", cls="px-3 py-2 text-sm"),
                        Td(
                            f"£{unit_costs[b]:,} / {unit_days[b]}d",
                            cls="px-3 py-2 text-xs text-gray-500",
                        ),
                        cls="border-t border-gray-100",
                    )
                    for b, d in by_band.items()
                    if d["count"] > 0
                ]
            ),
            cls="w-full text-sm",
        ),
        cls="bg-white rounded-xl border border-gray-200 overflow-auto mb-6",
    )

    # By mechanism table
    mech_tbl = Div(
        H2("Breakdown by mechanism", cls="text-base font-bold text-gray-700 mb-3"),
        Table(
            Thead(
                Tr(
                    *[
                        Th(
                            h,
                            cls="text-xs font-semibold text-gray-500 uppercase px-3 py-2 bg-gray-50 text-left",
                        )
                        for h in ["Mechanism", "Issues", "Estimated cost"]
                    ]
                )
            ),
            Tbody(
                *[
                    Tr(
                        Td(mech_badge(m), cls="px-3 py-2"),
                        Td(str(d["count"]), cls="px-3 py-2 text-sm"),
                        Td(f"£{d['cost']:,}", cls="px-3 py-2 text-sm font-semibold"),
                        cls="border-t border-gray-100",
                    )
                    for m, d in by_mech.items()
                    if d["count"] > 0
                ]
            ),
            cls="w-full text-sm",
        ),
        cls="bg-white rounded-xl border border-gray-200 overflow-auto mb-6",
    )

    # Issue-level table
    issue_tbl = Div(
        H2("Issue-level breakdown", cls="text-base font-bold text-gray-700 mb-3"),
        Table(
            Thead(
                Tr(
                    *[
                        Th(
                            h,
                            cls="text-xs font-semibold text-gray-500 uppercase px-3 py-2 bg-gray-50 text-left",
                        )
                        for h in [
                            "ID",
                            "Service",
                            "Band",
                            "Score",
                            "Mechanism",
                            "Unit cost",
                            "Days",
                        ]
                    ]
                )
            ),
            Tbody(
                *[
                    Tr(
                        Td(r["id"], cls="px-3 py-2 text-xs font-mono"),
                        Td(r["service"], cls="px-3 py-2 text-xs"),
                        Td(band_badge(r["combined_band"]), cls="px-3 py-2"),
                        Td(f"{r['combined_score']:.3f}", cls="px-3 py-2 text-xs"),
                        Td(mech_badge(r["primary_mechanism"]), cls="px-3 py-2"),
                        Td(
                            f"£{unit_costs.get(r['combined_band'], 0):,}",
                            cls="px-3 py-2 text-xs font-semibold",
                        ),
                        Td(f"{unit_days.get(r['combined_band'], 0)}d", cls="px-3 py-2 text-xs"),
                        cls="border-t border-gray-100 hover:bg-gray-50",
                    )
                    for r in issues
                ]
            ),
            cls="w-full text-sm",
        ),
        cls="bg-white rounded-xl border border-gray-200 overflow-auto",
    )

    return page_wrap(
        H1("Schedule & Cost Impact", cls="text-2xl font-bold text-gray-800 mb-6"),
        header_stats,
        band_tbl,
        mech_tbl,
        issue_tbl,
        title="BIMGUARD AI — Cost Impact",
    )


# ── IFC PARSER (for real file uploads) ───────────────────────────────────────
def _parse_ifc_elements(model) -> list:
    """
    Extract pipe elements from an IFC model.
    Returns list of dicts with material, zone, system type, position.
    """
    if not IFC_AVAILABLE:
        return []

    elements = []
    pipe_types = [
        "IfcPipeSegment",
        "IfcPipeFitting",
        "IfcFlowSegment",
        "IfcFlowFitting",
        "IfcValve",
    ]

    for ifc_type in pipe_types:
        try:
            for el in model.by_type(ifc_type):
                mat = _get_material(model, el)
                zone_cat, system_type = _get_zone_system(model, el)
                pos = _get_position(el)
                elements.append(
                    {
                        "id": el.GlobalId,
                        "type": ifc_type,
                        "service": system_type or ifc_type,
                        "floor": _get_floor(model, el),
                        "zone": zone_cat,
                        "mat_a": mat,
                        "mat_b": mat,
                        "area_a": 2.0,
                        "area_b": 2.0,
                        "joint": "weld neck flange",  # conservative default
                        "temp": _get_operating_temp(model, el),
                        "velocity": _get_flow_velocity(model, el),
                        "dead_leg": 0.0,
                        "x": pos[0],
                        "y": pos[1],
                        "z": pos[2],
                    }
                )
        except Exception:
            continue
    return elements[:200]  # cap at 200 for performance


def _get_material(model, el) -> str:
    try:
        for rel in getattr(el, "HasAssociations", []):
            if rel.is_a("IfcRelAssociatesMaterial"):
                mat = rel.RelatingMaterial
                if hasattr(mat, "Name") and mat.Name:
                    return mat.Name
                if hasattr(mat, "Materials"):
                    for m in mat.Materials:
                        if m.Name:
                            return m.Name
    except Exception:
        pass
    return "carbon_steel"  # conservative default


def _get_zone_system(model, el):
    try:
        for rel in getattr(el, "ContainedInStructure", []):
            sys = rel.RelatingStructure
            if sys.is_a("IfcDistributionSystem"):
                return sys.LongName or sys.Name or "", sys.PredefinedType or "UNKNOWN"
    except Exception:
        pass
    try:
        for rel in getattr(el, "Decomposes", []) or []:
            if hasattr(rel, "RelatingObject"):
                obj = rel.RelatingObject
                if hasattr(obj, "LongName"):
                    return obj.LongName or "", ""
    except Exception:
        pass
    return "", "UNKNOWN"


def _get_position(el):
    try:
        plmt = el.ObjectPlacement
        if plmt and hasattr(plmt, "RelativePlacement"):
            loc = plmt.RelativePlacement.Location
            if loc:
                coords = loc.Coordinates
                return (float(coords[0]), float(coords[1]), float(coords[2]))
    except Exception:
        pass
    return (0.0, 0.0, 0.0)


def _get_floor(model, el) -> str:
    try:
        for rel in model.get_inverse(el):
            if rel.is_a("IfcRelContainedInSpatialStructure"):
                s = rel.RelatingStructure
                if s.is_a("IfcBuildingStorey"):
                    return s.Name or s.LongName or "Unknown"
    except Exception:
        pass
    return "Unknown"


def _get_operating_temp(model, el) -> float:
    try:
        for rel in getattr(el, "IsDefinedBy", []):
            if not hasattr(rel, "RelatingPropertyDefinition"):
                continue
            pdef = rel.RelatingPropertyDefinition
            if pdef.is_a("IfcPropertySet"):
                for prop in pdef.HasProperties:
                    if "temperature" in prop.Name.lower() and hasattr(prop, "NominalValue"):
                        return float(prop.NominalValue.wrappedValue)
    except Exception:
        pass
    return 20.0


def _get_flow_velocity(model, el) -> float:
    try:
        for rel in getattr(el, "IsDefinedBy", []):
            if not hasattr(rel, "RelatingPropertyDefinition"):
                continue
            pdef = rel.RelatingPropertyDefinition
            if pdef.is_a("IfcPropertySet"):
                for prop in pdef.HasProperties:
                    if "velocity" in prop.Name.lower() and hasattr(prop, "NominalValue"):
                        return float(prop.NominalValue.wrappedValue)
    except Exception:
        pass
    return 0.3


def _run_engines_on_ifc(elements: list) -> list:
    """Run all three engines on IFC-parsed elements."""
    # Temporarily replace demo elements with IFC elements
    import demo_data as dd
    from demo_data import run_demo_compliance

    original = dd.DEMO_ELEMENTS
    dd.DEMO_ELEMENTS = elements
    results = run_demo_compliance()
    dd.DEMO_ELEMENTS = original
    return results


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
serve()
