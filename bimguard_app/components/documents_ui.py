from fasthtml.common import Div, Tbody, Td, Th, Thead, Tr
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
    MessageAlert,
    SaveAction,
    TableActionsMenu,
    TableSpec,
    TextAreaField,
    TextInputField,
    build_table_rows,
)


def documents_table_rows(rows: list[dict]):
    def _build_row(row: dict):
        extracted_text = (row.get("extracted_text") or "").strip()
        preview = extracted_text[:140] + ("..." if len(extracted_text) > 140 else "")
        return Tr(
            Td(row.get("filename", "-")),
            Td(row.get("md5_hash", "-"), cls="font-mono text-xs"),
            Td(row.get("upload_date", "-")),
            Td(preview or "No text extracted", cls="text-muted-foreground text-sm"),
            Td(
                TableActionsMenu(
                    edit_href=f"/library/documents/{row['id']}/edit",
                    delete_action=f"/library/documents/{row['id']}/delete",
                    view_href=f"/library/documents/{row['id']}",
                )
            ),
        )

    return build_table_rows(
        rows,
        _build_row,
        TableSpec(empty_message="No documents uploaded yet.", empty_colspan=5),
    )


def documents_panel(rows: list[dict], message: str | None = None, level: str = "success"):
    alert = MessageAlert(AlertSpec(message=message, level=level))

    return Div(
        *alert,
        Card(
            CardHeader(CardTitle("Stored Documents")),
            CardContent(
                Div(
                    Table(
                        Thead(
                            Tr(
                                Th("Filename"),
                                Th("MD5"),
                                Th("Uploaded"),
                                Th("Preview"),
                                Th("Actions"),
                            )
                        ),
                        Tbody(*documents_table_rows(rows)),
                        cls="min-w-[900px]",
                    ),
                    cls="w-full overflow-x-auto",
                ),
            ),
            cls="w-full max-w-full overflow-hidden",
        ),
        id="documents-panel",
        cls="space-y-4",
    )


def document_edit_form(document: dict):
    return Card(
        CardHeader(CardTitle(f"Edit: {document.get('filename', 'Document')}")),
        CardContent(
            Form(
                ActionRow(
                    SaveAction("Save Changes"),
                    CancelAction(href="/library/documents"),
                    cls="gap-2",
                ),
                TextInputField(
                    FieldSpec(
                        label="Filename",
                        field_id="filename",
                        name="filename",
                        value=document.get("filename", ""),
                        required=True,
                    )
                ),
                TextAreaField(
                    FieldSpec(
                        label="Extracted Text",
                        field_id="extracted_text",
                        name="extracted_text",
                        value=document.get("extracted_text", ""),
                    ),
                    rows=12,
                ),
                method="post",
                action=f"/library/documents/{document['id']}/update",
                cls="space-y-4",
            )
        ),
    )
