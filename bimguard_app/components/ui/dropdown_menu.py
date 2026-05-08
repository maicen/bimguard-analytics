from fasthtml.common import Details, Div, Hr, Input, Label, Span, Summary

from .utils import cn


def DropdownMenu(*children, cls: str | None = None, **kwargs):
    return Details(
        *children,
        data_dropdown_menu="root",
        data_state="closed",
        cls=cn("relative inline-block text-left", cls),
        **kwargs,
    )


def DropdownMenuTrigger(
    *children,
    cls: str | None = None,
    disabled: bool = False,
    **kwargs,
):
    return Summary(
        *children,
        data_dropdown_menu="trigger",
        data_disabled="true" if disabled else "false",
        aria_disabled="true" if disabled else "false",
        tabIndex=-1 if disabled else 0,
        cls=cn(
            "list-none inline-flex items-center justify-center rounded-md outline-none",
            "cursor-pointer [&::-webkit-details-marker]:hidden",
            "pointer-events-none opacity-50" if disabled else None,
            cls,
        ),
        **kwargs,
    )


def DropdownMenuPortal(*children, cls: str | None = None, **kwargs):
    return Div(
        *children,
        data_dropdown_menu="portal",
        cls=cn("z-50", cls),
        **kwargs,
    )


def DropdownMenuContent(
    *children,
    cls: str | None = None,
    side_offset: int = 4,
    align: str = "start",
    **kwargs,
):
    align_cls = "left-0" if align == "start" else "right-0"
    return Div(
        *children,
        data_dropdown_menu="content",
        data_state="closed",
        data_align=align,
        data_side_offset=str(side_offset),
        cls=cn(
            "absolute z-50 mt-1 min-w-56 rounded-md border bg-popover text-popover-foreground shadow-md outline-none",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "p-1",
            align_cls,
            cls,
        ),
        **kwargs,
    )


def DropdownMenuGroup(*children, cls: str | None = None, **kwargs):
    return Div(*children, data_dropdown_menu="group", cls=cn("p-1", cls), **kwargs)


def DropdownMenuLabel(*children, inset: bool = False, cls: str | None = None, **kwargs):
    return Div(
        *children,
        data_dropdown_menu="label",
        cls=cn("px-2 py-1.5 text-sm font-semibold", "pl-8" if inset else None, cls),
        **kwargs,
    )


def DropdownMenuItem(
    *children,
    inset: bool = False,
    destructive: bool = False,
    disabled: bool = False,
    cls: str | None = None,
    **kwargs,
):
    return Div(
        *children,
        role="menuitem",
        tabIndex=-1 if disabled else 0,
        data_dropdown_menu="item",
        data_disabled="true" if disabled else "false",
        aria_disabled="true" if disabled else "false",
        cls=cn(
            "relative flex cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none",
            "hover:bg-accent hover:text-accent-foreground",
            "pl-8" if inset else None,
            "text-destructive hover:bg-destructive hover:text-destructive-foreground"
            if destructive
            else None,
            "pointer-events-none opacity-50" if disabled else None,
            cls,
        ),
        **kwargs,
    )


def DropdownMenuCheckboxItem(
    *children,
    checked: bool = False,
    disabled: bool = False,
    cls: str | None = None,
    name: str | None = None,
    **kwargs,
):
    hidden_control = Input(type="checkbox", checked=checked, name=name, cls="sr-only")
    return Label(
        hidden_control,
        Span(
            "✓" if checked else "",
            data_dropdown_menu="item-indicator",
            cls="inline-flex h-4 w-4 items-center justify-center text-xs",
        ),
        Span(*children),
        role="menuitemcheckbox",
        tabIndex=-1 if disabled else 0,
        data_state="checked" if checked else "unchecked",
        data_dropdown_menu="checkbox-item",
        data_disabled="true" if disabled else "false",
        aria_disabled="true" if disabled else "false",
        cls=cn(
            "relative flex cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none",
            "hover:bg-accent hover:text-accent-foreground",
            "pointer-events-none opacity-50" if disabled else None,
            cls,
        ),
        **kwargs,
    )


def DropdownMenuRadioGroup(*children, cls: str | None = None, **kwargs):
    return Div(
        *children,
        role="radiogroup",
        data_dropdown_menu="radio-group",
        cls=cn("p-1", cls),
        **kwargs,
    )


def DropdownMenuRadioItem(
    *children,
    value: str,
    name: str,
    checked: bool = False,
    disabled: bool = False,
    cls: str | None = None,
    **kwargs,
):
    hidden_control = Input(type="radio", value=value, name=name, checked=checked, cls="sr-only")
    return Label(
        hidden_control,
        Span(
            "●" if checked else "",
            data_dropdown_menu="item-indicator",
            cls="inline-flex h-4 w-4 items-center justify-center text-[10px]",
        ),
        Span(*children),
        role="menuitemradio",
        tabIndex=-1 if disabled else 0,
        data_state="checked" if checked else "unchecked",
        data_dropdown_menu="radio-item",
        data_disabled="true" if disabled else "false",
        aria_disabled="true" if disabled else "false",
        cls=cn(
            "relative flex cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none",
            "hover:bg-accent hover:text-accent-foreground",
            "pointer-events-none opacity-50" if disabled else None,
            cls,
        ),
        **kwargs,
    )


def DropdownMenuSeparator(cls: str | None = None, **kwargs):
    return Hr(
        data_dropdown_menu="separator",
        cls=cn("-mx-1 my-1 border-border", cls),
        **kwargs,
    )


def DropdownMenuShortcut(*children, cls: str | None = None, **kwargs):
    return Span(
        *children,
        data_dropdown_menu="shortcut",
        cls=cn("ml-auto text-xs tracking-widest text-muted-foreground", cls),
        **kwargs,
    )


def DropdownMenuSub(*children, cls: str | None = None, **kwargs):
    return Details(
        *children,
        data_dropdown_menu="sub",
        data_state="closed",
        cls=cn("relative", cls),
        **kwargs,
    )


def DropdownMenuSubTrigger(
    *children,
    inset: bool = False,
    disabled: bool = False,
    cls: str | None = None,
    **kwargs,
):
    return Summary(
        *children,
        data_dropdown_menu="sub-trigger",
        data_disabled="true" if disabled else "false",
        aria_disabled="true" if disabled else "false",
        tabIndex=-1 if disabled else 0,
        cls=cn(
            "relative flex cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none",
            "hover:bg-accent hover:text-accent-foreground",
            "list-none [&::-webkit-details-marker]:hidden",
            "pl-8" if inset else None,
            "pointer-events-none opacity-50" if disabled else None,
            cls,
        ),
        **kwargs,
    )


def DropdownMenuSubContent(*children, cls: str | None = None, **kwargs):
    return Div(
        *children,
        data_dropdown_menu="sub-content",
        data_state="closed",
        cls=cn(
            "absolute left-full top-0 z-50 min-w-48 rounded-md border bg-popover p-1 text-popover-foreground shadow-md",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            cls,
        ),
        **kwargs,
    )
