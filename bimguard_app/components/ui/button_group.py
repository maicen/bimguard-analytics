from typing import Literal

from fasthtml.common import Div


def _cx(*parts: str | None) -> str:
    return " ".join(part for part in parts if part)


def ButtonGroup(
    *children,
    orientation: Literal["horizontal", "vertical"] = "horizontal",
    cls: str | None = None,
    **kwargs,
):
    base = "inline-flex w-fit"
    if orientation == "vertical":
        orientation_cls = "flex-col"
        join_cls = (
            "[&>*:not(:first-child)]:rounded-t-none "
            "[&>*:not(:last-child)]:rounded-b-none "
            "[&>*:not(:first-child)]:-mt-px"
        )
    else:
        orientation_cls = "flex-row items-center"
        join_cls = (
            "[&>*:not(:first-child)]:rounded-l-none "
            "[&>*:not(:last-child)]:rounded-r-none "
            "[&>*:not(:first-child)]:-ml-px"
        )

    return Div(
        *children,
        role="group",
        cls=_cx(base, orientation_cls, join_cls, cls),
        **kwargs,
    )
