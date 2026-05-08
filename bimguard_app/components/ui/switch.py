"""Switch (toggle switch) component adapted from shadcn/ui."""

from fasthtml.common import Div, Input
from fasthtml.common import Label as HtmlLabel

from .utils import cn


def Switch(
    *,
    id: str = "",
    name: str = "",
    checked: bool = False,
    disabled: bool = False,
    size: str = "default",
    cls: str | None = None,
    **kwargs,
):
    """
    Switch (toggle switch) component with shadcn/ui styling.

    Args:
        id: HTML element id
        name: Form field name
        checked: Initial checked state
        disabled: Disabled state
        size: "sm" or "default"
        cls: Additional CSS classes
        **kwargs: Additional HTML attributes

    Returns:
        Div containing hidden input and styled switch display element
    """
    size_cls = {
        "sm": "h-5 w-9",
        "default": "h-6 w-11",
    }.get(size, "h-6 w-11")

    thumb_cls = {
        "sm": "h-4 w-4 data-checked:translate-x-4",
        "default": "h-5 w-5 data-checked:translate-x-5",
    }.get(size, "h-5 w-5 data-checked:translate-x-5")

    return Div(
        # Hidden input for form submission
        Input(
            type="checkbox",
            id=id,
            name=name,
            checked=checked,
            disabled=disabled,
            cls="sr-only peer",
            **kwargs,
        ),
        # Visible switch element
        HtmlLabel(
            # Track background
            Div(
                cls=cn(
                    "cn-switch-track absolute inset-0 rounded-full "
                    "bg-muted peer-checked:bg-primary transition-colors",
                    "peer-disabled:opacity-50 peer-disabled:cursor-not-allowed",
                ),
            ),
            # Animated thumb
            Div(
                cls=cn(
                    "cn-switch-thumb absolute left-0.5 top-0.5 rounded-full "
                    "bg-background transition-transform pointer-events-none",
                    thumb_cls,
                ),
            ),
            htmlFor=id,
            cls=cn(
                "cn-switch peer group/switch relative inline-flex items-center "
                "cursor-pointer outline-none transition-all",
                size_cls,
                cls,
            ),
        ),
        role="switch",
        aria_checked="true" if checked else "false",
        aria_disabled="true" if disabled else "false",
    )
