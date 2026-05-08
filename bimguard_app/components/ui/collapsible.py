"""Collapsible primitives adapted from shadcn/ui component anatomy."""

from fasthtml.common import Details, Div, Summary

from .utils import cn


def Collapsible(*children, open: bool = False, cls: str | None = None, **kwargs):
    """Container for collapsible content."""
    return Details(
        *children,
        open=open,
        cls=cn(
            "cn-collapsible group/collapsible w-full rounded-md border",
            "bg-background",
            cls,
        ),
        **kwargs,
    )


def CollapsibleTrigger(*children, cls: str | None = None, **kwargs):
    """Trigger row that toggles the collapsible content."""
    return Summary(
        *children,
        cls=cn(
            "cn-collapsible-trigger flex cursor-pointer list-none items-center justify-between",
            "gap-2 px-3 py-2 text-sm font-medium",
            "hover:bg-muted/50 [&::-webkit-details-marker]:hidden",
            cls,
        ),
        **kwargs,
    )


def CollapsibleContent(*children, cls: str | None = None, **kwargs):
    """Content area shown when collapsible is open."""
    return Div(
        *children,
        cls=cn("cn-collapsible-content border-t p-2", cls),
        **kwargs,
    )
