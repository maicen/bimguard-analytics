"""
orchestrator.py
----------------
Runs the full BIMGuard Module 1 + Module 3 pipeline end to end.
This is the single entry point — call run_pipeline() with a PDF path.

Pipeline flow:
    PDF file
        ↓  Module 1 — Step 1
    DoclingExtractor          → prose text + table DataFrames
        ↓  Module 1 — Step 2
    TableRuleBuilder          → tables → rules.db directly (no LLM)
        ↓  Module 1 — Step 3
    SectionChunker            → 13 OBC section chunks
        ↓  Module 1 — Step 4
    KeywordFilter             → scored + confidence-labelled paragraphs
        ↓  Handoff M1 → M3
    RuleConverter             → Regex (default) or GPT-4o → structured rule dicts
        ↓  Module 3
    RuleGenerator             → validate + enrich entity types
        ↓
    RuleStore                 → save to rules.db
        ↓
    Return summary dict       → back to caller (CLI or future API)

SWITCHING BETWEEN REGEX AND GPT-4o:
    Set USE_GPT4O = False  → uses regex (free, no API key needed)
    Set USE_GPT4O = True   → uses GPT-4o (accurate, costs per call)

Usage:
    # Run from project root
    python orchestrator.py data/input_docs/OBC_Part9.pdf

    # Or import and call:
    from orchestrator import run_pipeline
    result = run_pipeline("data/input_docs/OBC_Part9.pdf")
"""

import os
import sys
from pathlib import Path

from app.services.persistence import PersistenceService

DB_PATH = PersistenceService.DB_PATH
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ── SWITCH HERE ───────────────────────────────────────────────────────────────
# False = regex (free, no API key, works offline)
# True  = GPT-4o (more accurate, costs per API call)
USE_GPT4O = False
# ─────────────────────────────────────────────────────────────────────────────

try:
    from .module1_doc_parser.docling_extractor import DoclingExtractor
    from .module1_doc_parser.keyword_filter import KeywordFilter
    from .module1_doc_parser.section_chunker import SectionChunker
    from .module1_doc_parser.table_rule_builder import TableRuleBuilder
    from .module3_rule_builder.obc_seed_rules import seed_rules
    from .module3_rule_builder.rule_generator import RuleGenerator
    from .module3_rule_builder.rule_store import RuleStore

    if USE_GPT4O:
        from .module3_rule_builder.rule_converter import RuleConverter
    else:
        from .module3_rule_builder.regex_rule_converter import RegexRuleConverter as RuleConverter
    _PIPELINE_AVAILABLE = True
except ImportError:
    _PIPELINE_AVAILABLE = False


def run_pipeline(
    pdf_path: str | Path,
    run_sections: str | list = "all",
    seed_db_first: bool = True,
) -> dict:
    """
    Run the full Module 1 → Module 3 pipeline on an OBC PDF.

    Args:
        pdf_path      (str | Path): path to the OBC PDF file
        run_sections  (str | list): "all" or list e.g. ["4", "6"]
                                    Use a single section to test first.
        seed_db_first (bool):       seed 25 pre-built OBC rules before processing

    Returns:
        dict: {
            pdf_file        (str),
            converter_used  (str),   "regex" or "gpt-4o"
            table_rules     (int),   rules from tables (no LLM/regex)
            prose_rules     (int),   rules from converter
            total_rules     (int),   total in DB after run
            sections_run    (int),
            db_summary      (dict),
        }
    """
    pdf_path = Path(pdf_path)
    converter_name = "gpt-4o" if USE_GPT4O else "regex"

    print(f"\n{'=' * 60}")
    print("  BIMGuard AI — Module 1 + 3 Pipeline")
    print(f"  PDF       : {pdf_path.name}")
    print(f"  Converter : {converter_name.upper()}")
    print(f"  Sections  : {run_sections}")
    print(f"  DB        : {DB_PATH}")
    print(f"{'=' * 60}\n")

    # ── Initialise ────────────────────────────────────────────────────────────
    store = RuleStore()  # delegates to RuleService (shared web DB)
    generator = RuleGenerator(store)

    if USE_GPT4O:
        converter = RuleConverter(api_key=GEMINI_API_KEY, rule_store=store)
    else:
        converter = RuleConverter()  # regex needs no arguments

    # ── Seed pre-built rules ──────────────────────────────────────────────────
    if seed_db_first:
        print("── SEEDING DB WITH PRE-BUILT OBC RULES ──")
        seed_rules(store, generator)

    rules_before = store.count()

    # ─────────────────────────────────────────────────────────────────────────
    # MODULE 1 — STEP 1: Docling extraction
    # ─────────────────────────────────────────────────────────────────────────
    print("\n── MODULE 1 / STEP 1: DOCLING EXTRACTION ──")
    extractor = DoclingExtractor()
    text, tables = extractor.extract(pdf_path)

    # ─────────────────────────────────────────────────────────────────────────
    # MODULE 1 — STEP 2: Table → Direct Rules (no converter needed)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n── MODULE 1 / STEP 2: TABLE RULE BUILDER ──")
    table_builder = TableRuleBuilder(store)
    table_rules = table_builder.process_all_tables(tables, generator)

    # ─────────────────────────────────────────────────────────────────────────
    # MODULE 1 — STEP 3: Section Chunker
    # ─────────────────────────────────────────────────────────────────────────
    print("\n── MODULE 1 / STEP 3: SECTION CHUNKER ──")
    chunks = SectionChunker().chunk(text)

    # Filter to requested sections only
    if run_sections != "all":
        chunks = [c for c in chunks if c["section_number"] in run_sections]
        print(f"  Running sections: {run_sections}")

    # ─────────────────────────────────────────────────────────────────────────
    # MODULE 1 — STEP 4: Keyword Filter
    # ─────────────────────────────────────────────────────────────────────────
    print("\n── MODULE 1 / STEP 4: KEYWORD FILTER ──")
    filtered_chunks = KeywordFilter().score_chunks(chunks)

    # ─────────────────────────────────────────────────────────────────────────
    # MODULE 3: Converter → RuleGenerator → RuleStore
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n── MODULE 3: {converter_name.upper()} CONVERTER ──")
    prose_rules = 0

    for chunk in filtered_chunks:
        section = chunk["section_number"]
        name = chunk["section_name"]
        print(f"\n  Section {section}: {name}")

        raw_rules = converter.extract_rules(chunk)
        print(f"    Extracted : {len(raw_rules)} rules")

        if raw_rules:
            saved_ids = generator.save_batch(raw_rules)
            prose_rules += len(saved_ids)
            print(f"    Saved     : {len(saved_ids)} rules")

    # ── Summary ───────────────────────────────────────────────────────────────
    total_rules = store.count()
    db_summary = store.summary()

    print(f"\n{'=' * 60}")
    print("  PIPELINE COMPLETE")
    print(f"  Converter used               : {converter_name}")
    print(f"  Table rules (no converter)   : {table_rules}")
    print(f"  Prose rules ({converter_name})  : {prose_rules}")
    print(f"  Total rules in DB            : {total_rules}")
    print(f"{'=' * 60}\n")

    return {
        "pdf_file": str(pdf_path),
        "converter_used": converter_name,
        "table_rules": table_rules,
        "prose_rules": prose_rules,
        "total_rules": total_rules,
        "sections_run": len(filtered_chunks),
        "db_summary": db_summary,
    }


class BIMGuard_App:
    """
    Application-level orchestrator used by the web routes.
    Provides run_dashboard() for stats and orchestrate_workflow() for
    full IFC + compliance analysis.
    """

    def run_dashboard(self) -> dict:
        """Return summary counts for the dashboard page."""
        from app.services.documents_service import DocumentService
        from app.services.projects_service import ProjectsService
        from app.services.rules_service import RuleService

        projects_svc = ProjectsService()
        documents_svc = DocumentService()
        rules_svc = RuleService()

        return {
            "total_projects": projects_svc.total_projects(),
            "total_documents": len(documents_svc.list_documents()),
            "total_rules": rules_svc.count(),
        }

    def orchestrate_workflow(
        self,
        project_id: int,
        doc_ids: list[int],
        analysis_theme: str = "Architecture",
        include_openings: bool = True,
        include_spaces: bool = True,
        include_type_definitions: bool = False,
    ) -> dict:
        """
        Run the full analysis pipeline for a project:
        1. Load project + documents from DB
        2. Parse the IFC file (or use synthetic demo data)
        3. Run corrosion compliance checks
        4. Return a unified result dict consumed by the analyze route
        """
        from app.services.documents_service import DocumentService
        from app.services.projects_service import ProjectsService
        from app.services.projects_service import ProjectsService
        from app.services.rules_service import RuleService
        from .module2_ifc_read.ifc_parser import parse_ifc, generate_synthetic_elements
        from .module4_comparator.compliance_runner import run_compliance_checks

        projects_svc = ProjectsService()
        documents_svc = DocumentService()
        selected_theme = RuleService.normalize_theme(analysis_theme)

        project = projects_svc.get_project(project_id)
        if project is None:
            return {"error": f"Project {project_id} not found."}

        # ── Documents ────────────────────────────────────────────────────────
        documents = []
        for doc_id in doc_ids:
            doc = documents_svc.get_document(doc_id)
            if doc is None:
                continue
            text = doc.get("extracted_text") or ""
            documents.append(
                {
                    "filename": doc.get("filename", ""),
                    "section_count": len([l for l in text.splitlines() if l.strip()]),
                }
            )

        # ── IFC parsing ──────────────────────────────────────────────────────
        ifc_path = projects_svc.resolve_ifc_file(project_id)
        ifc_error = None
        elements = []
        ifc_type_counts: dict = {}
        ifc_totals: dict = {}
        is_demo = False

        if ifc_path:
            try:
                elements = parse_ifc(str(ifc_path))

                # Count by IFC type
                for el in elements:
                    ifc_type_counts[el.ifc_type] = ifc_type_counts.get(el.ifc_type, 0) + 1

                n = len(elements)
                ifc_totals = {
                    "built_elements": n,
                    "all_physical_elements": n,
                    "adjusted_physical_elements": n,
                    "all_products": n,
                    "adjusted_products": n,
                    "filters": {
                        "include_openings": include_openings,
                        "include_spaces": include_spaces,
                        "include_type_definitions": include_type_definitions,
                    },
                    "excluded_or_added": {"openings": 0, "spaces": 0, "type_definitions": 0},
                }
            except Exception as exc:
                ifc_error = str(exc)
        else:
            # No IFC file — run on synthetic demo data so the UI still renders
            elements = generate_synthetic_elements(25)
            is_demo = True
            ifc_totals = {
                "built_elements": len(elements),
                "all_physical_elements": len(elements),
                "adjusted_physical_elements": len(elements),
                "all_products": len(elements),
                "adjusted_products": len(elements),
                "filters": {
                    "include_openings": include_openings,
                    "include_spaces": include_spaces,
                    "include_type_definitions": include_type_definitions,
                },
                "excluded_or_added": {"openings": 0, "spaces": 0, "type_definitions": 0},
            }
            for el in elements:
                ifc_type_counts[el.ifc_type] = ifc_type_counts.get(el.ifc_type, 0) + 1

        # ── Compliance checks ─────────────────────────────────────────────────
        compliance_results = []
        compliance_error = None
        cost_impact = None
        issue_stats: dict = {}

        if selected_theme == "MEP":
            try:
                raw_results = run_compliance_checks(elements)
                # Normalise band names to Title case for the UI
                band_map = {
                    "LOW": "Low",
                    "MEDIUM": "Medium",
                    "HIGH": "High",
                    "CRITICAL": "Critical",
                }
                for r in raw_results:
                    r["risk_band"] = band_map.get(r.get("overall_band", "Low"), "Low")
                compliance_results = raw_results

                bands = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
                for r in compliance_results:
                    b = r.get("risk_band", "Low")
                    if b in bands:
                        bands[b] += 1
                issue_stats = bands
            except Exception as exc:
                compliance_error = str(exc)

        # ── Module 2 + 4 + 5: Rule-based compliance check ────────────────────
        rule_compliance: list[dict] = []
        rule_compliance_summary: dict = {}
        rule_compliance_error: str | None = None
        rule_validations: list[dict] = []  # kept for backward-compat

        try:
            from .module2_ifc_read import Module2_IFCRead
            from .module4_comparator import Module4_Comparator
            from .module5_reporter import Module5_Reporter

            library_rules = RuleService().list_by_theme(selected_theme)

            # Basic element-presence check (legacy rule_validations card)
            for rule in library_rules:
                target = rule.get("target_ifc_class", "")
                count = ifc_type_counts.get(target, 0)
                rule_validations.append(
                    {
                        "reference": rule.get("reference", "—"),
                        "description": rule.get("description", ""),
                        "rule_type": rule.get("rule_type", ""),
                        "target_ifc_class": target,
                        "element_count": count,
                        "status": "present" if count > 0 else "not_found",
                    }
                )

            # Full Module 2 → 4 → 5 compliance pipeline (only when IFC file exists)
            if ifc_path and not ifc_error and library_rules:
                m2 = Module2_IFCRead(ifc_path)
                extraction = m2.extract_for_compliance(library_rules)
                rule_compliance = Module4_Comparator().validate_metadata(extraction)
                rule_compliance_summary = Module5_Reporter().render_visual_report(rule_compliance)

        except Exception as exc:
            rule_compliance_error = str(exc)

        return {
            "project": project,
            "analysis_theme": selected_theme,
            "ifc_element_count": len(elements),
            "ifc_type_counts": ifc_type_counts,
            "ifc_totals": ifc_totals,
            "ifc_error": ifc_error,
            "documents": documents,
            "compliance_results": compliance_results,
            "cost_impact": cost_impact,
            "issue_stats": issue_stats,
            "compliance_is_demo": is_demo,
            "bcf_project_id": project_id,
            "compliance_error": compliance_error,
            "rule_validations": rule_validations,
            # Module 4 results
            "rule_compliance": rule_compliance,
            "rule_compliance_summary": rule_compliance_summary,
            "rule_compliance_error": rule_compliance_error,
        }


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <path_to_obc_pdf>")
        print("Example: python orchestrator.py data/input_docs/OBC_Part9.pdf")
        print(f"\nCurrent converter: {'GPT-4o' if USE_GPT4O else 'Regex'}")
        print("To switch: change USE_GPT4O = True/False at top of file")
        sys.exit(1)

    run_pipeline(
        pdf_path=sys.argv[1],
        run_sections="all",
        seed_db_first=True,
    )
