import json
from fasthtml.common import Button, Details, Div, P, Pre, Span, Summary
from monsterui.all import H1, H3, Alert, Form, FormLabel, Input, UkIcon
from app.components.ui import (
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    HtmxSpinner,
    SubmitButton,
)


def rule_extraction_page_content():
    spinner, spinner_style = HtmxSpinner(
        "extract-spinner", "Scanning document and building rules via AI..."
    )

    return Div(
        Div(
            Div(
                H1(
                    "Rule Extraction Studio",
                    cls="text-lg font-semibold tracking-tight",
                ),
                P(
                    "Upload a BEP document to extract rules via AI.",
                    cls="text-xs text-muted-foreground",
                ),
            ),
            cls="flex items-center justify-between px-6 py-3 border-b bg-background",
        ),
        Div(
            Div(
                Card(
                    CardHeader(CardTitle("Upload BEP Document")),
                    CardContent(
                        Form(
                            Div(
                                FormLabel("Upload BEP Document (PDF)", fr="extract-document"),
                                Input(
                                    id="extract-document",
                                    type="file",
                                    name="document",
                                    accept=".pdf",
                                    required=True,
                                    cls="mt-2",
                                ),
                                cls="space-y-1",
                            ),
                            SubmitButton("Extract Rules", variant="primary", cls="mt-2"),
                            spinner,
                            spinner_style,
                            hx_post="/api/rules/extract",
                            hx_target="#extracted-rules-container",
                            hx_indicator="#extract-spinner",
                            enctype="multipart/form-data",
                            cls="space-y-4",
                        )
                    ),
                ),
                cls="flex-1 bg-muted/30 p-6 overflow-auto",
            ),
            Div(cls="w-px bg-border"),
            Div(
                Div(
                    H3("Extracted Rules", cls="text-lg font-semibold"),
                    cls="flex items-center justify-between px-6 py-3 border-b bg-background",
                ),
                Div(
                    P(
                        "Upload a document and click 'Extract' to see results here.",
                        cls="text-sm text-muted-foreground text-center py-10",
                    ),
                    id="extracted-rules-container",
                    cls="px-6 pb-6 space-y-4 overflow-y-auto flex-1",
                ),
                cls="w-full md:w-[400px] lg:w-[500px] bg-background border-l flex flex-col",
            ),
            cls="flex flex-1 overflow-hidden",
        ),
        cls="flex flex-col h-[calc(100vh-4rem)] -m-6",
    )


def rule_extraction_results(
    rules: list[dict],
    filename: str | None,
    *,
    warnings: list[str] | None = None,
):
    warning_banners = [
        Alert(
            UkIcon("alert-triangle", cls="h-4 w-4"),
            Span(w),
            cls="mb-3 text-amber-700 border-amber-400 [&>svg]:text-amber-700",
        )
        for w in (warnings or [])
    ]

    if not rules:
        return Div(
            *warning_banners,
            Alert(
                UkIcon("info", cls="h-4 w-4"),
                Span(
                    f"No compliance rules were found in {filename or 'the uploaded file'}. "
                    "Try a document that contains explicit BIM or building code requirements."
                ),
                cls="mb-4 text-yellow-700 border-yellow-500 [&>svg]:text-yellow-700",
            ),
        )

    fragments = []
    for rule in rules:
        ref = rule.get("ref", "REQ")
        desc = rule.get("desc", "")
        target = rule.get("target", "Unspecified")
        operator = rule.get("operator", "")
        value = rule.get("value")
        value_min = rule.get("value_min")
        value_max = rule.get("value_max")
        unit = rule.get("unit", "")
        severity = rule.get("severity", "")
        prop = rule.get("property_name", "")
        prop_set = rule.get("property_set", "")
        source_text = rule.get("source_text", "")
        related_refs = rule.get("related_refs") or []
        conf = rule.get("confidence")
        needs_review = rule.get("needs_review", False)
        method = rule.get("extraction_method", "llm")
        compliance_type = rule.get("compliance_type", "")

        # Condition string: handle between vs single value
        if operator == "between" and value_min is not None and value_max is not None:
            condition = f"{prop} between {value_min}–{value_max} {unit}".strip()
        else:
            parts = []
            if prop:
                parts.append(prop)
            if operator:
                parts.append(operator)
            if value is not None:
                parts.append(str(value))
            if unit:
                parts.append(unit)
            condition = " ".join(parts) if parts else None

        severity_cls = {
            "mandatory": "bg-red-100 text-red-800",
            "recommended": "bg-yellow-100 text-yellow-800",
            "informational": "bg-blue-100 text-blue-800",
        }.get(severity, "bg-muted text-muted-foreground")

        method_cls = (
            "bg-emerald-100 text-emerald-800"
            if method == "table"
            else "bg-purple-100 text-purple-800"
        )
        method_label = "table" if method == "table" else "AI"

        badges = Div(
            Span(
                severity or "mandatory",
                cls=f"inline-block px-1.5 py-0.5 rounded text-xs font-medium {severity_cls} mr-1",
            )
            if severity
            else "",
            Span(
                method_label,
                cls=f"inline-block px-1.5 py-0.5 rounded text-xs font-medium {method_cls} mr-1",
            ),
            Span(
                f"{int(conf * 100)}% conf",
                cls="inline-block px-1.5 py-0.5 rounded text-xs bg-muted text-muted-foreground mr-1",
            )
            if conf is not None
            else "",
            Span(
                "⚠ Review",
                cls="inline-block px-1.5 py-0.5 rounded text-xs bg-orange-100 text-orange-700",
            )
            if needs_review
            else "",
            cls="flex flex-wrap gap-1 mb-2",
        )

        # Rule structure block
        structure_rows = [
            ("Target", target),
            ("Check", condition) if condition else None,
            ("Property Set", prop_set) if prop_set else None,
            ("Type", f"{rule.get('rule_type', '')} · {compliance_type}")
            if compliance_type
            else ("Type", rule.get("rule_type", "")),
            ("Refs", ", ".join(related_refs)) if related_refs else None,
        ]
        structure = Div(
            *[
                Div(
                    Span(label + ":", cls="text-muted-foreground w-20 shrink-0"),
                    Span(val, cls="font-mono text-xs text-blue-700 break-all"),
                    cls="flex gap-2",
                )
                for row in structure_rows
                if row is not None
                for label, val in [row]
                if val
            ],
            cls="bg-muted p-1.5 rounded mb-2 space-y-0.5 text-xs",
        )

        # Source text collapsible
        source_block = (
            Details(
                Summary(
                    "Source text", cls="text-xs text-muted-foreground cursor-pointer select-none"
                ),
                P(source_text, cls="text-xs text-muted-foreground mt-1 italic"),
                cls="mb-2",
            )
            if source_text
            else ""
        )

        # JSON collapsible
        json_block = Details(
            Summary("View JSON", cls="text-xs text-muted-foreground cursor-pointer select-none"),
            Pre(
                json.dumps(rule, indent=2),
                cls="text-xs bg-muted p-2 rounded overflow-x-auto mt-1 max-h-48",
            ),
            cls="mb-2",
        )

        fragments.append(
            Card(
                CardContent(
                    Div(
                        Span(ref, cls="font-semibold text-sm"),
                        Span(
                            "New",
                            cls="inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-xs",
                        ),
                        cls="flex justify-between items-center mb-1",
                    ),
                    badges,
                    P(desc, cls="text-sm text-muted-foreground mb-2"),
                    structure,
                    source_block,
                    json_block,
                    Form(
                        Input(type="hidden", name="rule_json", value=json.dumps(rule)),
                        Button(
                            "Save to Library",
                            type="submit",
                            cls="text-xs px-3 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/90",
                        ),
                        hx_post="/api/rules/save-extracted",
                        hx_target="this",
                        hx_swap="outerHTML",
                    ),
                    cls="space-y-2",
                ),
                cls="mb-4",
            )
        )

    llm_count = sum(1 for r in rules if r.get("extraction_method") != "table")
    table_count = sum(1 for r in rules if r.get("extraction_method") == "table")
    summary_parts = [f"{len(rules)} rules"]
    if table_count:
        summary_parts.append(f"{table_count} from tables")
    if llm_count:
        summary_parts.append(f"{llm_count} via AI")

    success_msg = Alert(
        UkIcon("check-circle", cls="h-4 w-4"),
        Span(f"Extracted {' · '.join(summary_parts)} from {filename or 'uploaded file'}"),
        cls="mb-3 text-emerald-600 border-emerald-600 [&>svg]:text-emerald-600",
    )

    _btn = (
        "display:inline-flex;align-items:center;gap:5px;"
        "font-size:12px;font-weight:500;padding:6px 14px;"
        "border-radius:6px;border:none;cursor:pointer;"
        "background:#1e293b;color:#ffffff;"
    )

    # Save All — plain HTMX POST, no data in the request (server reads its own cache)
    # Export JSON — plain browser navigation to a download endpoint
    action_bar = Div(
        Button(
            UkIcon("save", cls="h-3.5 w-3.5"),
            "Save All",
            type="button",
            style=_btn,
            hx_post="/api/rules/save-all-extracted",
            hx_target="#save-all-msg",
            hx_swap="innerHTML",
        ),
        Button(
            UkIcon("download", cls="h-3.5 w-3.5"),
            "Export JSON",
            type="button",
            style=_btn,
            onclick="window.location='/api/rules/export-json'",
        ),
        Span("", id="save-all-msg", cls="text-xs text-emerald-700 ml-1"),
        cls="sticky top-0 z-10 bg-background border-b py-2 mb-3 -mx-6 px-6 flex gap-2 items-center",
    )

    return Div(*warning_banners, success_msg, action_bar, *fragments)


def rule_extraction_empty_file_result():
    return Alert("Uploaded file is empty.")
