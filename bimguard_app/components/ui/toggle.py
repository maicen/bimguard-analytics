"""Toggle button component adapted from shadcn/ui."""

from fasthtml.common import Button as HtmlButton

from .utils import cn


def Toggle(
    *children,
    pressed: bool = False,
    disabled: bool = False,
    variant: str = "default",
    size: str = "default",
    cls: str | None = None,
    **kwargs,
):
    """
    Toggle button component with shadcn/ui variants.

    Args:
        children: Button content (text or elements)
        pressed: Initial pressed/active state
        disabled: Disabled state
        variant: "default" or "outline"
        size: "sm", "default", or "lg"
        cls: Additional CSS classes
        **kwargs: Additional HTML attributes

    Returns:
        Button element with toggle styling
    """
    variant_cls = {
        "default": "bg-transparent hover:bg-muted",
        "outline": "border border-input hover:bg-muted",
    }.get(variant, "bg-transparent hover:bg-muted")

    size_cls = {
        "sm": "h-8 px-2 text-xs",
        "default": "h-9 px-3 text-sm",
        "lg": "h-10 px-4 text-base",
    }.get(size, "h-9 px-3 text-sm")

    return HtmlButton(
        *children,
        type="button",
        disabled=disabled,
        data_pressed="true" if pressed else "false",
        cls=cn(
            "cn-toggle group/toggle inline-flex items-center justify-center "
            "whitespace-nowrap outline-none transition-colors "
            "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 "
            "disabled:pointer-events-none disabled:opacity-50",
            size_cls,
            variant_cls,
            cls,
        ),
        **kwargs,
    )
