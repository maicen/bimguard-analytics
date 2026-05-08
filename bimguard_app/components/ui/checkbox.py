"""Checkbox component adapted from shadcn/ui."""

from fasthtml.common import Input

from .utils import cn


def Checkbox(
    *,
    id: str = "",
    name: str = "",
    checked: bool = False,
    disabled: bool = False,
    cls: str | None = None,
    **kwargs,
):
    """
    Checkbox component with shadcn/ui styling.

    Args:
        id: HTML element id
        name: Form field name
        checked: Initial checked state
        disabled: Disabled state
        cls: Additional CSS classes
        **kwargs: Additional HTML attributes (e.g., data_*, onclick)

    Returns:
        Input element styled as a checkbox
    """
    return Input(
        type="checkbox",
        id=id,
        name=name,
        checked=checked,
        disabled=disabled,
        cls=cn(
            "cn-checkbox peer relative shrink-0 outline-none "
            "disabled:cursor-not-allowed disabled:opacity-50 "
            "w-4 h-4 rounded border border-primary",
            cls,
        ),
        **kwargs,
    )
