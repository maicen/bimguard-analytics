"""Toggle group component adapted from shadcn/ui."""

from fasthtml.common import Div

from .toggle import Toggle
from .utils import cn


def ToggleGroup(
    *items,
    variant: str = "default",
    size: str = "default",
    orientation: str = "horizontal",
    spacing: int = 0,
    cls: str | None = None,
    **kwargs,
):
    """
    Group of toggle buttons with shared styling.

    Args:
        items: List of (label, value, pressed) tuples or Toggle elements
        variant: "default" or "outline"
        size: "sm", "default", or "lg"
        orientation: "horizontal" or "vertical"
        spacing: Gap size in spacing units (0-4)
        cls: Additional CSS classes
        **kwargs: Additional HTML attributes

    Returns:
        Div containing toggle buttons with group styling
    """
    gap_cls = {
        0: "gap-0",
        1: "gap-1",
        2: "gap-2",
        3: "gap-3",
        4: "gap-4",
    }.get(spacing, "gap-0")

    orientation_cls = "flex-col items-stretch" if orientation == "vertical" else ""

    # Process items - support both tuples and pre-built Toggle elements
    processed_items = []
    for item in items:
        if isinstance(item, tuple) and len(item) == 3:
            label, value, pressed = item
            processed_items.append(
                Toggle(
                    label,
                    pressed=pressed,
                    variant=variant,
                    size=size,
                    name="toggle",
                    value=value,
                    data_value=value,
                )
            )
        else:
            # Assume it's already a Toggle element
            processed_items.append(item)

    return Div(
        *processed_items,
        cls=cn(
            "cn-toggle-group inline-flex rounded-lg border border-input bg-transparent p-1 "
            "transition-all",
            gap_cls,
            orientation_cls,
            cls,
        ),
        role="group",
        **kwargs,
    )
