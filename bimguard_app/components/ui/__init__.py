"""Public UI facade and shared UI helpers used across route/component modules."""

from dataclasses import dataclass
from typing import Callable

from fasthtml.common import Div, Option, Span, Style, Td, Tr
from monsterui.all import (
    Alert,
    AlertT,
    DivLAligned,
    DivVStacked,
    FormLabel,
    Input,
    Select,
    TextArea,
    UkIcon,
)

from .bento_box import BentoBox
from .button import (
    BackAction,
    CancelAction,
    CreateAction,
    DeleteAction,
    EditAction,
    IconLinkButton,
    IconPostButton,
    LinkButton,
    SaveAction,
    SubmitButton,
    ViewAction,
)
from .button_group import ButtonGroup
from .card import (
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
)
from .checkbox import Checkbox
from .collapsible import Collapsible, CollapsibleContent, CollapsibleTrigger
from .dropdown_menu import (
    DropdownMenu,
    DropdownMenuCheckboxItem,
    DropdownMenuContent,
    DropdownMenuGroup,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuPortal,
    DropdownMenuRadioGroup,
    DropdownMenuRadioItem,
    DropdownMenuSeparator,
    DropdownMenuShortcut,
    DropdownMenuSub,
    DropdownMenuSubContent,
    DropdownMenuSubTrigger,
    DropdownMenuTrigger,
)
from .label import Label
from .sidebar import (
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarHeader,
    SidebarInset,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarProvider,
    SidebarRail,
    SidebarSeparator,
    SidebarTrigger,
)
from .switch import Switch
from .table import (
    Table,
    TableBody,
    TableCaption,
    TableCell,
    TableFooter,
    TableHead,
    TableHeader,
    TableRow,
)
from .table_actions import TableActionsMenu
from .toggle import Toggle
from .toggle_group import ToggleGroup
from .tooltip import Tooltip, TooltipProvider
from .utils import cn

__all__ = [
    "AlertSpec",
    "TableSpec",
    "SelectOptionSpec",
    "FieldSpec",
    "CountTableItemSpec",
    "ActionRow",
    "MessageAlert",
    "build_select_options",
    "build_table_rows",
    "TextInputField",
    "TextAreaField",
    "SelectField",
    "HtmxSpinner",
    "ItemsCountDataTable",
    "NotFoundBlock",
    "IconLinkButton",
    "IconPostButton",
    "ViewAction",
    "EditAction",
    "DeleteAction",
    "BackAction",
    "CreateAction",
    "SaveAction",
    "CancelAction",
    "LinkButton",
    "SubmitButton",
    "Card",
    "CardHeader",
    "CardTitle",
    "CardDescription",
    "CardContent",
    "CardFooter",
    "ButtonGroup",
    "BentoBox",
    "TableActionsMenu",
    "cn",
    "Table",
    "TableHeader",
    "TableBody",
    "TableFooter",
    "TableRow",
    "TableHead",
    "TableCell",
    "TableCaption",
    "DropdownMenu",
    "DropdownMenuTrigger",
    "DropdownMenuPortal",
    "DropdownMenuContent",
    "DropdownMenuGroup",
    "DropdownMenuItem",
    "DropdownMenuCheckboxItem",
    "DropdownMenuRadioGroup",
    "DropdownMenuRadioItem",
    "DropdownMenuLabel",
    "DropdownMenuSeparator",
    "DropdownMenuShortcut",
    "DropdownMenuSub",
    "DropdownMenuSubTrigger",
    "DropdownMenuSubContent",
    "SidebarProvider",
    "Sidebar",
    "SidebarTrigger",
    "SidebarRail",
    "SidebarInset",
    "SidebarHeader",
    "SidebarFooter",
    "SidebarContent",
    "SidebarSeparator",
    "SidebarGroup",
    "SidebarGroupLabel",
    "SidebarGroupContent",
    "SidebarMenu",
    "SidebarMenuItem",
    "SidebarMenuButton",
    "Checkbox",
    "Toggle",
    "Switch",
    "ToggleGroup",
    "Label",
    "Tooltip",
    "TooltipProvider",
    "Collapsible",
    "CollapsibleTrigger",
    "CollapsibleContent",
]


@dataclass(frozen=True)
class AlertSpec:
    message: str | None = None
    level: str = "success"


@dataclass(frozen=True)
class TableSpec:
    empty_message: str
    empty_colspan: int


@dataclass(frozen=True)
class SelectOptionSpec:
    label: str
    value: str
    selected: bool = False


@dataclass(frozen=True)
class FieldSpec:
    label: str
    field_id: str
    name: str
    value: str = ""
    placeholder: str = ""
    required: bool = False


@dataclass(frozen=True)
class CountTableItemSpec:
    label: str
    total: int
    subtotal: int | None = None
    note: str = ""


def ActionRow(*actions, cls: str = "gap-1"):
    return DivLAligned(*actions, cls=cls)


def MessageAlert(spec: AlertSpec):
    if not spec.message:
        return ()

    alert_cls = AlertT.success if spec.level == "success" else AlertT.warning
    return (Alert(spec.message, cls=alert_cls),)


def build_select_options(options: list[SelectOptionSpec]) -> list:
    return [
        Option(option.label, value=option.value, selected=option.selected) for option in options
    ]


def build_table_rows(rows: list[dict], row_builder: Callable[[dict], object], spec: TableSpec):
    if not rows:
        return [
            Tr(
                Td(
                    spec.empty_message,
                    colspan=str(spec.empty_colspan),
                    cls="text-center text-muted-foreground",
                )
            )
        ]

    return [row_builder(row) for row in rows]


def TextInputField(spec: FieldSpec, input_type: str = "text"):
    return DivVStacked(
        FormLabel(spec.label, fr=spec.field_id),
        Input(
            id=spec.field_id,
            name=spec.name,
            type=input_type,
            value=spec.value,
            placeholder=spec.placeholder,
            required=spec.required,
        ),
        cls="space-y-1",
    )


def TextAreaField(spec: FieldSpec, rows: int = 5):
    return DivVStacked(
        FormLabel(spec.label, fr=spec.field_id),
        TextArea(
            spec.value,
            id=spec.field_id,
            name=spec.name,
            placeholder=spec.placeholder,
            rows=str(rows),
            required=spec.required,
        ),
        cls="space-y-1",
    )


def SelectField(spec: FieldSpec, options: list[SelectOptionSpec]):
    return DivVStacked(
        FormLabel(spec.label, fr=spec.field_id),
        Select(
            *build_select_options(options),
            id=spec.field_id,
            name=spec.name,
            required=spec.required,
        ),
        cls="space-y-1",
    )


def HtmxSpinner(spinner_id: str, message: str):
    return (
        Div(
            UkIcon("loader-2", cls="w-5 h-5 animate-spin"),
            Span(message, cls="ml-2 text-sm"),
            id=spinner_id,
            cls="htmx-indicator hidden items-center",
        ),
        Style(".htmx-indicator.htmx-request { display: flex !important; }"),
    )


def ItemsCountDataTable(
    items: list[CountTableItemSpec],
    caption: str = "Item counts summary",
    options_summary: str = "",
    built_type_breakdown: dict[str, int] | None = None,
):
    totals_sum = sum(item.total for item in items)
    subtotals_sum = sum(
        item.subtotal if item.subtotal is not None else item.total for item in items
    )

    body_rows = []
    for item in items:
        subtotal_value = item.subtotal if item.subtotal is not None else item.total
        body_rows.append(
            TableRow(
                TableCell(item.label, cls="font-medium"),
                TableCell(str(item.total), cls="text-right tabular-nums"),
                TableCell(str(subtotal_value), cls="text-right tabular-nums"),
                TableCell(item.note, cls="text-muted-foreground text-xs"),
            )
        )

    if options_summary:
        body_rows.append(
            TableRow(
                TableCell(
                    options_summary,
                    colspan="4",
                    cls="text-xs text-muted-foreground border-t",
                )
            )
        )

    if built_type_breakdown:
        breakdown_lines = [
            Div(
                Span(element_type, cls="font-medium text-sm"),
                Span(str(count), cls="text-sm tabular-nums"),
                cls="flex items-center justify-between rounded-sm px-1 py-0.5",
            )
            for element_type, count in sorted(built_type_breakdown.items())
        ]

        body_rows.append(
            TableRow(
                TableCell(
                    Collapsible(
                        CollapsibleTrigger(
                            Span("Built element type breakdown"),
                            Span(
                                f"{len(built_type_breakdown)} types",
                                cls="text-xs text-muted-foreground",
                            ),
                        ),
                        CollapsibleContent(
                            Div(*breakdown_lines, cls="space-y-1"),
                        ),
                        cls="border-0 rounded-none",
                    ),
                    colspan="4",
                    cls="p-0 border-t",
                )
            )
        )

    return Div(
        Table(
            TableCaption(caption),
            TableHeader(
                TableRow(
                    TableHead("Category"),
                    TableHead("Total", cls="text-right"),
                    TableHead("Subtotal", cls="text-right"),
                    TableHead("Notes"),
                )
            ),
            TableBody(*body_rows),
            TableFooter(
                TableRow(
                    TableCell("Totals", colspan="2", cls="font-semibold"),
                    TableCell(str(totals_sum), cls="text-right tabular-nums font-semibold"),
                    TableCell("Sum of base totals", cls="text-xs text-muted-foreground"),
                ),
                TableRow(
                    TableCell("Subtotals", colspan="2", cls="font-semibold"),
                    TableCell(str(subtotals_sum), cls="text-right tabular-nums font-semibold"),
                    TableCell(
                        "Sum after applied options",
                        cls="text-xs text-muted-foreground",
                    ),
                ),
                TableRow(
                    TableCell("Grand Total", colspan="2", cls="font-bold"),
                    TableCell(
                        str(subtotals_sum),
                        cls="text-right tabular-nums text-base font-bold",
                    ),
                    TableCell(
                        "Final aggregate used for comparison",
                        cls="text-xs text-muted-foreground",
                    ),
                ),
            ),
        ),
        cls="overflow-hidden rounded-md border",
    )


def NotFoundBlock(entity: str, back_href: str, back_title: str):
    return Div(
        Alert(f"{entity} not found.", cls=AlertT.warning),
        BackAction(href=back_href, title=back_title),
        cls="space-y-4",
    )
