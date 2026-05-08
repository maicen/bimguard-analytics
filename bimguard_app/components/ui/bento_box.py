from fasthtml.common import Div, P
from monsterui.all import H3

DEFAULT_CARD_CLS = (
    "bg-muted border border-border rounded-[2rem] transition-all duration-300 hover:scale-[1.01]"
)
DEFAULT_CAPTION_CLS = "text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground"


def BentoBox(
    title: str,
    value: str,
    description: str | None = None,
    dark: bool = False,
    cls: str = "",
    card_cls: str = DEFAULT_CARD_CLS,
    caption_cls: str = DEFAULT_CAPTION_CLS,
    **kwargs,
):
    bg_cls = "bg-foreground" if dark else card_cls
    txt_main = "text-background" if dark else "text-foreground"
    txt_sec = "text-muted-foreground"

    return Div(cls=f"{bg_cls} p-8 flex flex-col justify-between {cls}", **kwargs)(
        Div(cls="space-y-1")(
            P(title, cls=caption_cls),
            H3(value, cls=f"text-3xl font-bold {txt_main}"),
        ),
        P(description, cls=f"text-sm font-medium mt-2 {txt_sec}") if description else None,
    )
