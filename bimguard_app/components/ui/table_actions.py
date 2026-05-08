from fasthtml.common import Form, Span
from monsterui.all import UkIcon

from .dropdown_menu import (
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
)


def TableActionsMenu(
    edit_href: str,
    delete_action: str,
    view_href: str | None = None,
    view_label: str = "View",
    extra_items: list | None = None,
):
    menu_items = []

    if extra_items:
        menu_items.extend(extra_items)

    if view_href:
        menu_items.append(
            DropdownMenuItem(
                view_label,
                onclick=f"window.location.href='{view_href}'",
            )
        )

    menu_items.append(
        DropdownMenuItem(
            "Edit",
            onclick=f"window.location.href='{edit_href}'",
        )
    )
    menu_items.append(DropdownMenuSeparator())
    menu_items.append(
        DropdownMenuItem(
            "Delete",
            destructive=True,
            onclick="this.closest('form').submit()",
        )
    )

    return Form(
        DropdownMenu(
            DropdownMenuTrigger(
                UkIcon(icon="ellipsis", height=16, width=16),
                Span("Open menu", cls="sr-only"),
                cls="h-8 w-8 p-0 rounded-md hover:bg-muted",
            ),
            DropdownMenuContent(
                *menu_items,
                align="end",
                cls="min-w-44",
            ),
        ),
        method="post",
        action=delete_action,
        cls="inline-block m-0 p-0",
    )
