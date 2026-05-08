from fasthtml.common import A, Div, Hr, Li, Span, Ul
from fasthtml.common import Button as HtmlButton
from monsterui.all import UkIcon


def _cx(*parts: str | None) -> str:
    return " ".join(part for part in parts if part)


def SidebarProvider(*children, default_open: bool = True, cls: str | None = None, **kwargs):
    state = "expanded" if default_open else "collapsed"
    return Div(
        *children,
        data_sidebar_provider="true",
        data_sidebar_state=state,
        cls=_cx("group/sidebar-wrapper flex min-h-svh w-full", cls),
        **kwargs,
    )


def Sidebar(*children, cls: str | None = None, **kwargs):
    return Div(
        *children,
        data_sidebar="sidebar",
        cls=_cx(
            "relative hidden md:flex md:flex-col shrink-0 border-r bg-sidebar text-sidebar-foreground "
            "w-64 transition-[width] duration-200 ease-linear "
            "group-data-[sidebar-state=collapsed]/sidebar-wrapper:w-14",
            cls,
        ),
        **kwargs,
    )


def SidebarInset(*children, cls: str | None = None, **kwargs):
    return Div(
        *children,
        data_sidebar="inset",
        cls=_cx("flex min-w-0 flex-1 flex-col", cls),
        **kwargs,
    )


def SidebarTrigger(label: str = "Toggle Sidebar", cls: str | None = None, **kwargs):
    return HtmlButton(
        UkIcon("panel-left", height=16, width=16, cls="text-foreground/80"),
        Span(label, cls="sr-only"),
        type="button",
        data_sidebar_trigger="true",
        onclick="(function(btn){const root=btn.closest('[data-sidebar-provider]');if(!root)return;root.dataset.sidebarState=root.dataset.sidebarState==='collapsed'?'expanded':'collapsed';})(this)",
        cls=_cx(
            "inline-flex h-9 w-9 items-center justify-center rounded-md border bg-background "
            "hover:bg-muted transition-colors",
            cls,
        ),
        **kwargs,
    )


def SidebarRail(cls: str | None = None, **kwargs):
    return Div(
        data_sidebar="rail",
        cls=_cx(
            "absolute inset-y-0 -right-px hidden w-1 bg-border/50 md:block",
            "group-data-[sidebar-state=collapsed]/sidebar-wrapper:bg-border",
            cls,
        ),
        **kwargs,
    )


def SidebarHeader(*children, cls: str | None = None, **kwargs):
    return Div(
        *children,
        data_sidebar="header",
        cls=_cx("flex flex-col gap-2 p-2", cls),
        **kwargs,
    )


def SidebarFooter(*children, cls: str | None = None, **kwargs):
    return Div(
        *children,
        data_sidebar="footer",
        cls=_cx("mt-auto flex flex-col gap-2 p-2", cls),
        **kwargs,
    )


def SidebarContent(*children, cls: str | None = None, **kwargs):
    return Div(
        *children,
        data_sidebar="content",
        cls=_cx("flex min-h-0 flex-1 flex-col gap-2 overflow-auto p-2", cls),
        **kwargs,
    )


def SidebarSeparator(cls: str | None = None, **kwargs):
    return Hr(data_sidebar="separator", cls=_cx("my-2 border-border", cls), **kwargs)


def SidebarGroup(*children, cls: str | None = None, **kwargs):
    return Div(
        *children,
        data_sidebar="group",
        cls=_cx("relative flex w-full min-w-0 flex-col p-1", cls),
        **kwargs,
    )


def SidebarGroupLabel(*children, cls: str | None = None, **kwargs):
    return Div(
        *children,
        data_sidebar="group-label",
        cls=_cx(
            "px-2 py-1 text-xs font-medium text-muted-foreground "
            "group-data-[sidebar-state=collapsed]/sidebar-wrapper:sr-only",
            cls,
        ),
        **kwargs,
    )


def SidebarGroupContent(*children, cls: str | None = None, **kwargs):
    return Div(
        *children,
        data_sidebar="group-content",
        cls=_cx("w-full text-sm", cls),
        **kwargs,
    )


def SidebarMenu(*children, cls: str | None = None, **kwargs):
    return Ul(
        *children,
        data_sidebar="menu",
        cls=_cx("flex w-full min-w-0 flex-col gap-1", cls),
        **kwargs,
    )


def SidebarMenuItem(*children, cls: str | None = None, **kwargs):
    return Li(
        *children,
        data_sidebar="menu-item",
        cls=_cx("group/menu-item relative", cls),
        **kwargs,
    )


def SidebarMenuButton(*children, href: str | None = None, cls: str | None = None, **kwargs):
    button_cls = _cx(
        "flex w-full items-center gap-2 overflow-hidden rounded-md px-2 py-1.5 text-left text-sm outline-none",
        "hover:bg-muted hover:text-foreground transition-colors",
        "group-data-[sidebar-state=collapsed]/sidebar-wrapper:justify-center",
        cls,
    )

    if href is not None:
        return A(*children, href=href, data_sidebar="menu-button", cls=button_cls, **kwargs)

    return HtmlButton(
        *children,
        type="button",
        data_sidebar="menu-button",
        cls=button_cls,
        **kwargs,
    )
