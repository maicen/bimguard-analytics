"""Tooltip component adapted from shadcn/ui."""

from fasthtml.common import Div

from .utils import cn


def Tooltip(
    children,
    content: str,
    side: str = "top",
    *,
    trigger_cls: str | None = None,
    content_cls: str | None = None,
    **kwargs,
):
    """
    Tooltip component - displays on hover via title attribute.

    For server-side rendering, uses title attribute for native tooltip.
    For custom styling, wraps content in a positioned div (CSS-only, no JS).

    Args:
        children: Trigger element (text or component)
        content: Tooltip text content
        side: "top", "bottom", "left", or "right" (for CSS positioning)
        trigger_cls: Additional CSS classes for trigger
        content_cls: Additional CSS classes for tooltip content
        **kwargs: Additional HTML attributes

    Returns:
        Div with trigger and positioned tooltip
    """
    side_cls = {
        "top": "bottom-full mb-2",
        "bottom": "top-full mt-2",
        "left": "right-full mr-2",
        "right": "left-full ml-2",
    }.get(side, "bottom-full mb-2")

    arrow_cls = {
        "top": "top-full left-1/2 -translate-x-1/2 border-t-foreground border-l-transparent border-r-transparent",
        "bottom": "bottom-full left-1/2 -translate-x-1/2 border-b-foreground border-l-transparent border-r-transparent",
        "left": "left-full top-1/2 -translate-y-1/2 border-l-foreground border-t-transparent border-b-transparent",
        "right": "right-full top-1/2 -translate-y-1/2 border-r-foreground border-t-transparent border-b-transparent",
    }.get(side, "top-full left-1/2 -translate-x-1/2 border-b-foreground")

    return Div(
        Div(
            children,
            title=content,  # Native tooltip fallback
            cls=cn(
                "cn-tooltip-trigger relative",
                trigger_cls,
            ),
        ),
        # Positioned tooltip (visible on CSS :hover - requires JavaScript or CSS to show)
        Div(
            content,
            cls=cn(
                "cn-tooltip-content absolute z-50 hidden px-2 py-1 text-xs "
                "bg-foreground text-background rounded-md whitespace-nowrap pointer-events-none "
                "group-hover:block",
                side_cls,
                content_cls,
            ),
        ),
        # Tooltip arrow
        Div(
            cls=cn(
                "cn-tooltip-arrow absolute hidden w-2 h-2 "
                "border-2 border-solid pointer-events-none group-hover:block",
                arrow_cls,
            ),
        ),
        cls="cn-tooltip group relative inline-block",
        **kwargs,
    )


def TooltipProvider(*children, delay: int = 0):
    """
    Tooltip provider wrapper (no-op in server-side rendering).

    In React, this manages global tooltip timing. In FastHTML, it's just a container.

    Args:
        children: Child elements
        delay: Delay in milliseconds (informational only)

    Returns:
        Div containing children
    """
    return Div(*children, cls="cn-tooltip-provider")
