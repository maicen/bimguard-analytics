"""Document and rule library routes, including extraction/import endpoints."""

from pathlib import Path

from fasthtml.common import (
    Div,
    P,
    Request,
    Span,
    Title,
    UploadFile,
)
from monsterui.all import (
    H1,
    Card,
    CardBody,
    CardHeader,
    CardTitle,
    Container,
    DivLAligned,
    Form,
    FormLabel,
    Input,
)

from app.components.documents_ui import document_edit_form, documents_panel
from app.components.layout import DashboardLayout
from app.components.rule_extraction_ui import (
    rule_extraction_empty_file_result,
    rule_extraction_page_content,
    rule_extraction_results,
)
from app.components.rules_ui import rule_form, rules_panel
from app.components.ui import (
    Alert,
    AlertT,
    BackAction,
    CreateAction,
    EditAction,
    HtmxSpinner,
    LinkButton,
    NotFoundBlock,
    SubmitButton,
)
from app.components.ui import (
    Card as UICard,
)
from app.components.ui import (
    CardContent as UICardContent,
)
from app.components.ui import (
    CardHeader as UICardHeader,
)
from app.components.ui import (
    CardTitle as UICardTitle,
)
from app.modules.module1_doc_parser import Module1_DocReader
from app.services.documents_service import DocumentService
from app.services.rule_extraction_service import RuleExtractionService
from app.services.rules_service import RuleService
from app.utils import (
    md5_hex,
    redirect_see_other,
    safe_upload_name,
    validate_document_upload,
)

_document_service = DocumentService()
_rule_service = RuleService()
_rule_extraction_service = RuleExtractionService()

# Server-side cache of the most recent extraction — avoids passing large JSON
# through form attributes or hidden inputs (encoding issues with special chars).
_last_extracted: list[dict] = []
_last_extracted_filename: str = ""


def _not_found_page(entity: str, back_href: str, back_title: str):
    return Title(f"{entity} Not Found - BIM Guard"), DashboardLayout(
        Container(NotFoundBlock(entity, back_href, back_title))
    )


def setup_routes(rt):
    """Register document and rule library routes."""

    @rt("/library/documents")
    def documents():
        upload_spinner, upload_spinner_style = HtmxSpinner(
            "documents-upload-spinner", "Processing document..."
        )

        return Title("Documents - BIM Guard"), DashboardLayout(
            Container(
                H1("Documents", cls="text-3xl font-bold tracking-tight"),
                P(
                    "Upload PDF, Markdown, or text references, extract their text, and manage your document library.",
                    cls="text-muted-foreground",
                ),
                UICard(
                    UICardHeader(UICardTitle("Upload Document")),
                    UICardContent(
                        Form(
                            Div(
                                FormLabel("Document (.pdf, .md, .txt)", fr="document"),
                                Input(
                                    id="document",
                                    type="file",
                                    name="document",
                                    accept=".pdf,.md,.txt",
                                    required=True,
                                ),
                                cls="space-y-1",
                            ),
                            SubmitButton("Upload Document", variant="primary"),
                            upload_spinner,
                            upload_spinner_style,
                            hx_post="/api/documents/upload",
                            hx_target="#documents-panel",
                            hx_indicator="#documents-upload-spinner",
                            enctype="multipart/form-data",
                            cls="space-y-4",
                        )
                    ),
                ),
                documents_panel(_document_service.list_documents()),
                cls="space-y-4",
            )
        )

    @rt("/api/documents/upload", methods=["POST"])
    async def documents_upload(document: UploadFile):
        filename = safe_upload_name(document.filename)
        file_content = await document.read()
        validation_error = validate_document_upload(
            filename,
            document.content_type,
            file_content,
        )
        if validation_error:
            return documents_panel(
                _document_service.list_documents(),
                validation_error,
                level="warning",
            )

        md5_hash = md5_hex(file_content)
        existing = _document_service.find_by_md5(md5_hash)
        if existing is not None:
            return documents_panel(
                _document_service.list_documents(),
                f"Document already exists: {existing.get('filename', filename)}",
                level="warning",
            )

        stored_path = _document_service.store_document_file(filename, file_content)

        reader = Module1_DocReader()
        if filename.lower().endswith(".pdf"):
            extracted_text = reader.parse_pdf(file_content)
        else:
            extracted_text = file_content.decode("utf-8", errors="replace").strip()

        _document_service.create_document(
            md5_hash=md5_hash,
            filename=filename,
            file_path=stored_path,
            extracted_text=extracted_text,
        )

        return documents_panel(
            _document_service.list_documents(),
            f"Uploaded and stored: {filename}",
            level="success",
        )

    @rt("/library/documents/{document_id}")
    def document_details(document_id: int):
        document = _document_service.get_document(document_id)
        if document is None:
            return _not_found_page("Document", "/library/documents", "Back to Documents")

        extracted_text = (document.get("extracted_text") or "").strip()
        return Title(f"{document.get('filename', 'Document')} - BIM Guard"), DashboardLayout(
            Container(
                H1(document.get("filename", "Document")),
                DivLAligned(
                    P(
                        f"MD5: {document.get('md5_hash', '-')}",
                        cls="font-mono text-xs text-muted-foreground",
                    ),
                    P(
                        f"Uploaded: {document.get('upload_date', '-')}",
                        cls="text-sm text-muted-foreground",
                    ),
                    EditAction(href=f"/library/documents/{document_id}/edit"),
                    BackAction(href="/library/documents", title="Back to Documents"),
                    cls="gap-2",
                ),
                Card(
                    CardHeader(CardTitle("Extracted Text")),
                    CardBody(
                        P(
                            extracted_text or "No text extracted for this document.",
                            cls="whitespace-pre-wrap text-sm",
                        ),
                        cls="max-h-[60vh] overflow-y-auto",
                    ),
                ),
                cls="space-y-4",
            )
        )

    @rt("/library/documents/{document_id}/edit")
    def document_edit(document_id: int):
        document = _document_service.get_document(document_id)
        if document is None:
            return _not_found_page("Document", "/library/documents", "Back to Documents")

        return Title("Edit Document - BIM Guard"), DashboardLayout(
            Container(
                document_edit_form(document),
                cls="space-y-4",
            )
        )

    @rt("/library/documents/{document_id}/update", methods=["POST"])
    def document_update(document_id: int, filename: str, extracted_text: str = ""):
        document = _document_service.get_document(document_id)
        if document is None:
            return redirect_see_other("/library/documents")

        _document_service.update_document(
            document_id=document_id,
            filename=Path(filename).name.strip() or document.get("filename", "document.pdf"),
            extracted_text=extracted_text,
        )
        return redirect_see_other(f"/library/documents/{document_id}")

    @rt("/library/documents/{document_id}/delete", methods=["POST"])
    def document_delete(document_id: int):
        _document_service.delete_document_with_file(document_id)

        return redirect_see_other("/library/documents")

    @rt("/library/rules")
    def rules_list(message: str = ""):
        return Title("Rules - BIM Guard"), DashboardLayout(
            Container(
                DivLAligned(
                    H1("Rule Library", cls="text-3xl font-bold tracking-tight"),
                    CreateAction(href="/library/rules/new", title="Create Rule"),
                    cls="justify-between",
                ),
                P(
                    "Create, update, and manage compliance rules used during analysis.",
                    cls="text-muted-foreground",
                ),
                DivLAligned(
                    LinkButton(
                        "Open Extraction Studio",
                        href="/library/rules/extract",
                        variant="secondary",
                    ),
                    cls="justify-end",
                ),
                rules_panel(_rule_service.list_rules(), message=message or None),
                cls="space-y-4",
            )
        )

    @rt("/library/rules/new")
    def rules_new():
        return Title("Create Rule - BIM Guard"), DashboardLayout(
            Container(rule_form("Create Rule", "/library/rules/create"), cls="space-y-4")
        )

    @rt("/library/rules/create", methods=["POST"])
    def rules_create(
        reference: str,
        rule_type: str,
        description: str,
        target_ifc_class: str,
        parameters: str = "{}",
    ):
        _rule_service.create_rule(
            reference,
            rule_type,
            description,
            target_ifc_class,
            parameters,
        )
        return redirect_see_other("/library/rules")

    @rt("/library/rules/extract")
    def rules_extract_page():
        return (
            Title("Rule Extraction - BIM Guard"),
            DashboardLayout(rule_extraction_page_content()),
        )

    @rt("/library/rules/import-json")
    def rules_import_json_page():
        return Title("Import JSON Ruleset - BIM Guard"), DashboardLayout(
            Container(
                H1("Import JSON Ruleset", cls="text-3xl font-bold tracking-tight"),
                P(
                    "Upload a JSON ruleset file. The file must have a 'ruleset_id' field and a 'rules' array.",
                    cls="text-muted-foreground",
                ),
                UICard(
                    UICardHeader(UICardTitle("Upload Ruleset JSON")),
                    UICardContent(
                        Form(
                            Div(
                                FormLabel("Ruleset JSON file (.json)", fr="ruleset_file"),
                                Input(
                                    id="ruleset_file",
                                    type="file",
                                    name="ruleset_file",
                                    accept=".json",
                                    required=True,
                                ),
                                cls="space-y-1",
                            ),
                            SubmitButton("Import Ruleset", variant="primary"),
                            hx_post="/api/rules/import-json",
                            hx_target="#import-result",
                            enctype="multipart/form-data",
                            cls="space-y-4",
                        ),
                        Div(id="import-result"),
                    ),
                ),
                cls="space-y-4",
            )
        )

    @rt("/library/rules/{rule_id}")
    def rules_details(rule_id: int):
        rule = _rule_service.get_rule(rule_id)
        if rule is None:
            return _not_found_page("Rule", "/library/rules", "Back to Rules")

        return Title(f"{rule.get('reference', 'Rule')} - BIM Guard"), DashboardLayout(
            Container(
                DivLAligned(
                    H1(rule.get("reference", "Rule")),
                    EditAction(href=f"/library/rules/{rule_id}/edit"),
                    cls="justify-between",
                ),
                Card(
                    CardHeader(CardTitle("Rule Details")),
                    CardBody(
                        P(f"Type: {rule.get('rule_type', '-')}", cls="text-sm"),
                        P(
                            f"Target IFC Class: {rule.get('target_ifc_class', '-')}",
                            cls="text-sm",
                        ),
                        P(rule.get("description", ""), cls="text-sm"),
                        Div(
                            rule.get("parameters", "{}"),
                            cls="font-mono text-xs bg-muted p-2 rounded border",
                        ),
                        cls="space-y-3",
                    ),
                ),
                BackAction(href="/library/rules", title="Back to Rules"),
                cls="space-y-4",
            )
        )

    @rt("/library/rules/{rule_id}/edit")
    def rules_edit(rule_id: int):
        rule = _rule_service.get_rule(rule_id)
        if rule is None:
            return redirect_see_other("/library/rules")

        return Title("Edit Rule - BIM Guard"), DashboardLayout(
            Container(
                rule_form("Edit Rule", f"/library/rules/{rule_id}/update", rule),
                cls="space-y-4",
            )
        )

    @rt("/library/rules/{rule_id}/update", methods=["POST"])
    def rules_update(
        rule_id: int,
        reference: str,
        rule_type: str,
        description: str,
        target_ifc_class: str,
        parameters: str = "{}",
        # identity
        mechanism: str = "",
        ruleset_id: str = "",
        rule_category: str = "",
        # ifc target
        property_set: str = "",
        property_name: str = "",
        fallback_property: str = "",
        # rule logic
        operator: str = "",
        check_value: str = "",
        value_min: str = "",
        value_max: str = "",
        unit: str = "",
        # classification
        severity: str = "mandatory",
        keyword: str = "",
        compliance_type: str = "",
        # content
        source_text: str = "",
        # meta
        confidence: str = "",
        needs_review: str = "",
    ):
        if _rule_service.get_rule(rule_id) is None:
            return redirect_see_other("/library/rules")

        _rule_service.update_rule(
            rule_id,
            reference=reference,
            rule_type=rule_type,
            description=description,
            target_ifc_class=target_ifc_class,
            parameters=parameters,
            mechanism=mechanism,
            ruleset_id=ruleset_id,
            rule_category=rule_category,
            property_set=property_set,
            property_name=property_name,
            fallback_property=fallback_property,
            operator=operator,
            check_value=check_value or None,
            value_min=value_min or None,
            value_max=value_max or None,
            unit=unit,
            severity=severity,
            keyword=keyword,
            compliance_type=compliance_type,
            source_text=source_text,
            confidence=float(confidence) if confidence.strip() else None,
            needs_review=bool(needs_review),
        )
        return redirect_see_other(f"/library/rules/{rule_id}")

    @rt("/library/rules/{rule_id}/delete", methods=["POST"])
    def rules_delete(rule_id: int):
        if _rule_service.get_rule(rule_id) is not None:
            _rule_service.delete_rule(rule_id)
        return redirect_see_other("/library/rules")

    @rt("/api/rules/save-extracted", methods=["POST"])
    async def rules_save_extracted(req: Request):
        import json as _json

        form = await req.form()
        rule_json = form.get("rule_json", "{}")
        try:
            rule = _json.loads(rule_json)
        except Exception:
            rule = {}

        # check_value: prefer explicit "check_value" key, fall back to "value"
        _cv = rule.get("check_value") if rule.get("check_value") is not None else rule.get("value")
        _rule_service.create_rule(
            reference=str(rule.get("ref") or "REQ-AI").strip(),
            rule_type=str(rule.get("rule_type") or "numeric_comparison"),
            description=str(rule.get("desc") or ""),
            target_ifc_class=str(rule.get("target") or "Unspecified"),
            source_text=str(rule.get("source_text") or ""),
            property_set=str(rule.get("property_set") or ""),
            property_name=str(rule.get("property_name") or ""),
            fallback_property=str(rule.get("fallback_property") or ""),
            operator=str(rule.get("operator") or ""),
            check_value=_cv,
            value_min=rule.get("value_min"),
            value_max=rule.get("value_max"),
            unit=str(rule.get("unit") or ""),
            applies_when=rule.get("applies_when") or {},
            severity=str(rule.get("severity") or "mandatory"),
            keyword=str(rule.get("keyword") or ""),
            compliance_type=str(rule.get("compliance_type") or ""),
            exceptions=rule.get("exceptions") or [],
            related_refs=rule.get("related_refs") or [],
            confidence=float(rule.get("confidence") or 0.8),
            extraction_method=str(rule.get("extraction_method") or "llm"),
            needs_review=bool(rule.get("needs_review", False)),
        )
        return Span(
            "Saved \u2713",
            cls="text-xs px-3 py-1 rounded bg-muted text-muted-foreground cursor-default",
        )

    @rt("/api/rules/save-all-extracted", methods=["POST"])
    async def rules_save_all_extracted():
        """Save every rule from the last extraction. Reads from server cache \u2014 no form data needed."""
        global _last_extracted
        saved = 0
        for rule in _last_extracted:
            if not isinstance(rule, dict):
                continue
            desc = str(rule.get("desc") or "").strip()
            if not desc:
                continue
            _cv = (
                rule.get("check_value")
                if rule.get("check_value") is not None
                else rule.get("value")
            )
            _rule_service.create_rule(
                reference=str(rule.get("ref") or "REQ-AI").strip(),
                rule_type=str(rule.get("rule_type") or "numeric_comparison"),
                description=desc,
                target_ifc_class=str(rule.get("target") or "Unspecified").strip(),
                source_text=str(rule.get("source_text") or ""),
                property_set=str(rule.get("property_set") or ""),
                property_name=str(rule.get("property_name") or ""),
                fallback_property=str(rule.get("fallback_property") or ""),
                operator=str(rule.get("operator") or ""),
                check_value=_cv,
                value_min=rule.get("value_min"),
                value_max=rule.get("value_max"),
                unit=str(rule.get("unit") or ""),
                applies_when=rule.get("applies_when") or {},
                severity=str(rule.get("severity") or "mandatory"),
                keyword=str(rule.get("keyword") or ""),
                compliance_type=str(rule.get("compliance_type") or ""),
                exceptions=rule.get("exceptions") or [],
                related_refs=rule.get("related_refs") or [],
                confidence=float(rule.get("confidence") or 0.8),
                extraction_method=str(rule.get("extraction_method") or "llm"),
                needs_review=bool(rule.get("needs_review", False)),
            )
            saved += 1

        return Span(
            f"Saved {saved} rules \u2713",
            cls="text-xs font-medium text-emerald-700",
        )

    @rt("/api/rules/export-json")
    def rules_export_json():
        """Download the last extraction as a JSON file \u2014 no data passed through UI."""
        import json as _json
        from fasthtml.common import Response

        global _last_extracted, _last_extracted_filename
        safe = (_last_extracted_filename or "rules").replace(".pdf", "").replace(" ", "_")
        return Response(
            content=_json.dumps(_last_extracted, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{safe}_rules.json"'},
        )

    @rt("/api/rules/import-json", methods=["POST"])
    async def rules_import_json_api(ruleset_file: UploadFile):
        import json as _json

        file_content = await ruleset_file.read()
        if not file_content:
            return Alert("No file received.", cls=AlertT.error)
        try:
            json_data = _json.loads(file_content.decode("utf-8"))
        except Exception as exc:
            return Alert(f"Invalid JSON: {exc}", cls=AlertT.error)
        try:
            count = _rule_service.import_ruleset(json_data)
        except ValueError as exc:
            return Alert(str(exc), cls=AlertT.error)
        except Exception as exc:
            return Alert(f"Import failed: {exc}", cls=AlertT.error)
        ruleset_id = json_data.get("ruleset_id", "")
        return Span(
            f"Imported {count} rules from '{ruleset_id}' ✓",
            cls="text-sm px-4 py-1.5 rounded bg-green-100 text-green-800 font-medium",
        )

    @rt("/api/rules/extract", methods=["POST"])
    async def rules_extract_api(document: UploadFile):
        global _last_extracted, _last_extracted_filename
        file_content = await document.read()
        if not file_content:
            return rule_extraction_empty_file_result()

        try:
            result = await _rule_extraction_service.extract_rules(file_content)
        except RuntimeError as exc:
            msg = str(exc)
            if "api key" in msg.lower() or "openai" in msg.lower():
                msg = (
                    "OpenAI API key not configured. "
                    "Copy example.env to .env and set OPENAI_API_KEY, then restart the server."
                )
            return Alert(msg, cls=AlertT.error)
        except Exception as exc:
            return Alert(
                f"Rule extraction failed: {type(exc).__name__}: {exc}",
                cls=AlertT.error,
            )

        _last_extracted = result.rules
        _last_extracted_filename = document.filename or ""

        return rule_extraction_results(result.rules, document.filename, warnings=result.warnings)
