from fasthtml.common import A
from fasthtml.common import Button as HtmlButton
from monsterui.all import Form, UkIcon

ACTION_ICON_CLS = (
    "inline-flex h-9 w-9 items-center justify-center rounded-lg p-0 "
    "text-foreground/80 hover:bg-muted hover:text-foreground transition-colors"
)

ICON_BUTTON_RESET_STYLE = (
    "background: transparent; border: 0; box-shadow: none; color: inherit; padding: 0; "
    "width: 36px; min-width: 36px; height: 36px;"
)

TEXT_BUTTON_BASE_CLS = (
    "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 "
    "text-sm font-medium transition-colors"
)

TEXT_BUTTON_VARIANTS = {
    "primary": "bg-primary text-primary-foreground hover:opacity-90",
    "secondary": "bg-muted text-foreground hover:bg-muted/80",
    "ghost": "text-foreground hover:bg-muted",
}


def _resolve_icon_cls(cls: str | None) -> str:
    return cls or ACTION_ICON_CLS


def _resolve_text_button_cls(variant: str, cls: str | None = None) -> str:
    variant_cls = TEXT_BUTTON_VARIANTS.get(variant, TEXT_BUTTON_VARIANTS["primary"])
    if cls:
        return f"{TEXT_BUTTON_BASE_CLS} {variant_cls} {cls}"
    return f"{TEXT_BUTTON_BASE_CLS} {variant_cls}"


def LinkButton(label: str, href: str, variant: str = "primary", cls: str | None = None):
    return A(label, href=href, cls=_resolve_text_button_cls(variant, cls))


def SubmitButton(
    label: str,
    variant: str = "primary",
    cls: str | None = None,
    button_type: str = "submit",
):
    return HtmlButton(
        label,
        type=button_type,
        cls=_resolve_text_button_cls(variant, cls),
    )


def IconLinkButton(icon_name: str, href: str, title: str, cls: str | None = None):
    return A(
        UkIcon(icon_name, height=20, width=20),
        href=href,
        title=title,
        cls=_resolve_icon_cls(cls),
        aria_label=title,
    )


def IconPostButton(
    icon_name: str,
    action: str | None,
    title: str,
    cls: str | None = None,
    button_type: str = "submit",
):
    button = HtmlButton(
        UkIcon(icon_name, height=20, width=20),
        type=button_type,
        title=title,
        cls=_resolve_icon_cls(cls),
        style=ICON_BUTTON_RESET_STYLE,
        aria_label=title,
    )
    if action is None:
        return button

    return Form(
        button,
        method="post",
        action=action,
        title=title,
        cls="inline-block m-0 p-0",
    )


def ViewAction(href: str, title: str = "View", cls: str | None = None):
    return IconLinkButton("eye", href=href, title=title, cls=cls)


def EditAction(href: str, title: str = "Edit", cls: str | None = None):
    return IconLinkButton("pencil", href=href, title=title, cls=cls)


def DeleteAction(action: str, title: str = "Delete", cls: str | None = None):
    return IconPostButton("trash-2", action=action, title=title, cls=cls)


def BackAction(href: str, title: str = "Back", cls: str | None = None):
    return IconLinkButton("arrow-left", href=href, title=title, cls=cls)


def CreateAction(href: str, title: str = "Create", cls: str | None = None):
    return IconLinkButton("plus", href=href, title=title, cls=cls)


def SaveAction(title: str = "Save", cls: str | None = None):
    return IconPostButton("save", action=None, title=title, cls=cls, button_type="submit")


def CancelAction(href: str, title: str = "Cancel", cls: str | None = None):
    return IconLinkButton("x", href=href, title=title, cls=cls)
