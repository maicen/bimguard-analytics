from fasthtml.common import Div, Tbody, Td, Th, Thead, Tr
from monsterui.all import (
    H1,
    H2,
    Container,
    DivFullySpaced,
    DivVStacked,
    Form,
    FormLabel,
    Input,
    Subtitle,
    Table,
    TableT,
    UkIcon,
)

from app.components.layout import DashboardLayout
from app.components.ui import (
    ActionRow,
    AlertSpec,
    CancelAction,
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CreateAction,
    FieldSpec,
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


def project_form(title: str, action: str, project: dict | None = None, include_ifc: bool = False):
    project = project or {}
    ifc_field = (
        (
            DivVStacked(
                FormLabel("IFC Model", fr="ifc_file"),
                Input(
                    id="ifc_file",
                    name="ifc_file",
                    type="file",
                    accept=".ifc",
                ),
                cls="space-y-1",
            ),
        )
        if include_ifc
        else ()
    )
    return Card(
        CardHeader(
            CardTitle(H2(title)),
            Subtitle("Manage your BIM compliance projects."),
        ),
        CardContent(
            Form(
                TextInputField(
                    FieldSpec(
                        label="Project Name",
                        field_id="name",
                        name="name",
                        value=project.get("name", ""),
                        placeholder="e.g. Airport Terminal A",
                        required=True,
                    )
                ),
                TextAreaField(
                    FieldSpec(
                        label="Description",
                        field_id="description",
                        name="description",
                        value=project.get("description", ""),
                        placeholder="Scope, goals, and notes",
                    ),
                    rows=5,
                ),
                SelectField(
                    FieldSpec(label="Status", field_id="status", name="status"),
                    [
                        SelectOptionSpec(
                            "Draft",
                            "Draft",
                            selected=project.get("status") == "Draft",
                        ),
                        SelectOptionSpec(
                            "Active",
                            "Active",
                            selected=project.get("status") == "Active",
                        ),
                        SelectOptionSpec(
                            "Archived",
                            "Archived",
                            selected=project.get("status") == "Archived",
                        ),
                    ],
                ),
                *ifc_field,
                ActionRow(
                    SaveAction("Save Project"),
                    CancelAction(href="/projects"),
                    cls="gap-2",
                ),
                method="post",
                action=action,
                enctype="multipart/form-data" if include_ifc else None,
                cls="space-y-4",
            )
        ),
    )


def projects_table_rows(rows: list[dict]):
    def _actions_menu(row: dict):
        return TableActionsMenu(
            edit_href=f"/projects/{row['id']}/edit",
            delete_action=f"/projects/{row['id']}/delete",
            view_href=(f"/viewer?project_id={row['id']}" if row.get("ifc_file_path") else None),
            view_label="Open IFC in Viewer",
        )

    def _build_row(row: dict):
        return Tr(
            Td(str(row["id"])),
            Td(row["name"]),
            Td(row.get("status", "Draft")),
            Td(
                UkIcon("file-check", height=15, width=15, cls="text-success")
                if row.get("ifc_file_path")
                else UkIcon("file-x", height=15, width=15, cls="text-muted-foreground")
            ),
            Td(row.get("created_at", "-")),
            Td(row.get("updated_at", "-")),
            Td(_actions_menu(row)),
        )

    return build_table_rows(
        rows,
        _build_row,
        TableSpec(
            empty_message="No projects yet. Create your first one.",
            empty_colspan=7,
        ),
    )


def projects_page(rows: list[dict], message: str | None = None):
    msg_block = MessageAlert(AlertSpec(message=message, level="success"))

    return DashboardLayout(
        Container(
            DivFullySpaced(
                Div(
                    H1("Projects"),
                    Subtitle("Create, track, and update your project records."),
                ),
                CreateAction(href="/projects/new", title="New Project"),
            ),
            *msg_block,
            Card(
                CardHeader(CardTitle("Project Registry")),
                CardContent(
                    Table(
                        Thead(
                            Tr(
                                Th("ID"),
                                Th("Name"),
                                Th("Status"),
                                Th("IFC"),
                                Th("Created"),
                                Th("Updated"),
                                Th("Actions"),
                            )
                        ),
                        Tbody(*projects_table_rows(rows)),
                        cls=TableT.hover,
                    )
                ),
            ),
            cls="space-y-4",
        )
    )
