from fasthtml.common import Div, Span, Tbody, Td, Th, Thead, Tr
from monsterui.all import Form, Table

from app.components.ui import (
    ActionRow,
    AlertSpec,
    CancelAction,
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    FieldSpec,
    LinkButton,
    MessageAlert,
    SaveAction,
    SelectField,
    SelectOptionSpec,
    TableActionsMenu,
    TableSpec,
    TextAreaField,
    TextInputField,
    build_table_rows,
)

IFC_CLASS_OPTIONS = [
    "IfcProject",
    "IfcSite",
    "IfcBuilding",
    "IfcBuildingStorey",
    "IfcSpace",
    "IfcWall",
    "IfcDoor",
    "IfcWindow",
    "IfcSlab",
    "IfcRoof",
    "IfcColumn",
    "IfcBeam",
    "IfcStair",
    "IfcRailing",
    "IfcFlowTerminal",
    # MEP / piping types (corrosion engine targets)
    "IfcPipeSegment",
    "IfcPipeFitting",
    "IfcValve",
    "IfcFlowMovingDevice",
    "IfcFlowStorageDevice",
    "IfcFlowController",
    "IfcDistributionFlowElement",
    "IfcDistributionElement",
    "Unspecified",
]

MECHANISM_OPTIONS = [
    SelectOptionSpec(label="— Any —", value=""),
    SelectOptionSpec(label="OBC", value="OBC"),
    SelectOptionSpec(label="GC-001", value="GC-001"),
    SelectOptionSpec(label="CC-001", value="CC-001"),
    SelectOptionSpec(label="MC-001", value="MC-001"),
    SelectOptionSpec(label="IFC", value="IFC"),
]

RULE_CATEGORY_OPTIONS = [
    SelectOptionSpec(label="property_check", value="property_check"),
    SelectOptionSpec(label="scoring_model", value="scoring_model"),
    SelectOptionSpec(label="threshold_band", value="threshold_band"),
    SelectOptionSpec(label="material_property", value="material_property"),
    SelectOptionSpec(label="reference_config", value="reference_config"),
    SelectOptionSpec(label="mitigation", value="mitigation"),
]

_MECHANISM_BADGE = {
    "OBC": "bg-blue-100 text-blue-800",
    "GC-001": "bg-amber-100 text-amber-800",
    "CC-001": "bg-rose-100 text-rose-800",
    "MC-001": "bg-green-100 text-green-800",
    "IFC": "bg-purple-100 text-purple-800",
}


def _mechanism_badge(mechanism: str):
    mech = (mechanism or "").upper()
    css = _MECHANISM_BADGE.get(mech, "bg-muted text-muted-foreground")
    return Span(mech or "—", cls=f"text-xs font-medium px-2 py-0.5 rounded {css}")


def rules_table_rows(rows: list[dict]):
    def _build_row(row: dict):
        return Tr(
            Td(row.get("reference", "-")),
            Td(_mechanism_badge(row.get("mechanism", ""))),
            Td(row.get("rule_type", "-")),
            Td(row.get("target_ifc_class", "-")),
            Td(row.get("rule_category", "-"), cls="text-xs text-muted-foreground"),
            Td(row.get("updated_at", "-"), cls="text-sm text-muted-foreground"),
            Td(
                (row.get("description") or "")[:100]
                + ("..." if len(row.get("description") or "") > 100 else ""),
                cls="text-sm text-muted-foreground",
            ),
            Td(
                TableActionsMenu(
                    edit_href=f"/library/rules/{row['id']}/edit",
                    delete_action=f"/library/rules/{row['id']}/delete",
                    view_href=f"/library/rules/{row['id']}",
                )
            ),
        )

    return build_table_rows(
        rows,
        _build_row,
        TableSpec(empty_message="No rules available yet.", empty_colspan=8),
    )


def rules_panel(rows: list[dict], message: str | None = None, level: str = "success"):
    alert = MessageAlert(AlertSpec(message=message, level=level))

    return Div(
        *alert,
        Card(
            CardHeader(
                Div(
                    CardTitle("Rule Library"),
                    LinkButton(
                        "Import JSON Ruleset",
                        href="/library/rules/import-json",
                        variant="secondary",
                        cls="text-sm",
                    ),
                    cls="flex items-center justify-between",
                )
            ),
            CardContent(
                Table(
                    Thead(
                        Tr(
                            Th("Reference"),
                            Th("Mechanism"),
                            Th("Type"),
                            Th("Target Class"),
                            Th("Category"),
                            Th("Updated"),
                            Th("Description"),
                            Th("Actions"),
                        )
                    ),
                    Tbody(*rules_table_rows(rows)),
                    cls="min-w-[1200px]",
                )
            ),
        ),
        cls="space-y-4",
    )


def rule_form(title: str, action: str, rule: dict | None = None):
    rule = rule or {}
    selected_ifc_class = rule.get("target_ifc_class", "")
    ifc_options = [
        SelectOptionSpec(
            label=ifc_class,
            value=ifc_class,
            selected=selected_ifc_class == ifc_class,
        )
        for ifc_class in IFC_CLASS_OPTIONS
    ]
    if selected_ifc_class and selected_ifc_class not in IFC_CLASS_OPTIONS:
        ifc_options.insert(
            0,
            SelectOptionSpec(label=selected_ifc_class, value=selected_ifc_class, selected=True),
        )

    selected_mech = rule.get("mechanism", "")
    mech_options = [
        SelectOptionSpec(label=o.label, value=o.value, selected=o.value == selected_mech)
        for o in MECHANISM_OPTIONS
    ]

    selected_cat = rule.get("rule_category", "property_check")
    cat_options = [
        SelectOptionSpec(label=o.label, value=o.value, selected=o.value == selected_cat)
        for o in RULE_CATEGORY_OPTIONS
    ]

    return Card(
        CardHeader(CardTitle(title)),
        CardContent(
            Form(
                ActionRow(
                    SaveAction("Save Rule"),
                    CancelAction(href="/library/rules"),
                    cls="gap-2",
                ),
                TextInputField(
                    FieldSpec(
                        label="Reference",
                        field_id="reference",
                        name="reference",
                        value=rule.get("reference", ""),
                        placeholder="e.g. REQ-ISO-001",
                        required=True,
                    )
                ),
                TextInputField(
                    FieldSpec(
                        label="Rule Type",
                        field_id="rule_type",
                        name="rule_type",
                        value=rule.get("rule_type", "numeric_comparison"),
                        required=True,
                    )
                ),
                SelectField(
                    FieldSpec(
                        label="Mechanism",
                        field_id="mechanism",
                        name="mechanism",
                    ),
                    mech_options,
                ),
                TextInputField(
                    FieldSpec(
                        label="Ruleset ID",
                        field_id="ruleset_id",
                        name="ruleset_id",
                        value=rule.get("ruleset_id", ""),
                        placeholder="e.g. OBC-PART9",
                    )
                ),
                SelectField(
                    FieldSpec(
                        label="Rule Category",
                        field_id="rule_category",
                        name="rule_category",
                    ),
                    cat_options,
                ),
                SelectField(
                    FieldSpec(
                        label="Target IFC Class",
                        field_id="target_ifc_class",
                        name="target_ifc_class",
                        required=True,
                    ),
                    ifc_options,
                ),
                TextAreaField(
                    FieldSpec(
                        label="Description",
                        field_id="description",
                        name="description",
                        value=rule.get("description", ""),
                        required=True,
                    ),
                    rows=5,
                ),
                TextAreaField(
                    FieldSpec(
                        label="Parameters (JSON or text)",
                        field_id="parameters",
                        name="parameters",
                        value=rule.get("parameters", "{}"),
                    ),
                    rows=6,
                ),
                method="post",
                action=action,
                cls="space-y-4",
            )
        ),
    )
