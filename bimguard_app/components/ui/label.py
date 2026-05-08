"""Label component adapted from shadcn/ui."""

from fasthtml.common import Label as HtmlLabel

from .utils import cn


def Label(
    children,
    *,
    for_: str | None = None,
    required: bool = False,
    disabled: bool = False,
    error: bool = False,
    cls: str | None = None,
    **kwargs,
):
    """
    Label component with shadcn/ui styling.

    Args:
        children: Label text content
        for_: HTML for attribute (links to input id)
        required: If True, adds a red asterisk
        disabled: If True, dims the label
        error: If True, colors the label red
        cls: Additional CSS classes
        **kwargs: Additional HTML attributes

    Returns:
        Label element with cn-label styling
    """
    label_cls = cn(
        "cn-label text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
        error and "text-destructive",
        disabled and "opacity-50 cursor-not-allowed",
        cls,
    )

    content = [children]
    if required:
        content.append(" ")
        content.append("*")

    return HtmlLabel(
        *content,
        fr=for_,  # FastHTML uses 'fr' for HTML 'for' attribute
        cls=label_cls,
        **kwargs,
    )
