# app\components\layout.py
from fasthtml.common import H2, Div, Main, Span
from monsterui.all import DivLAligned, TextT, UkIcon

from app.components.themed_ui import SiteStyles
from app.components.ui import (
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarInset,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarProvider,
    SidebarRail,
    SidebarTrigger,
)

# Standardized Apple-style icons for the sidebar
NAV_ICONS = {
    "Dashboard": "layout-dashboard",
    "Projects": "folder-open",
    "Viewer": "scan-eye",
    "Run Analysis": "cpu",
    "Reports": "file-text",
    "Documents": "book-open",
    "Rules": "list-checks",
    "Settings": "settings",
}


def NavItem(title, url):
    """Sidebar menu item using shared sidebar primitives."""
    icon = NAV_ICONS.get(title, "circle")
    return SidebarMenuItem(
        SidebarMenuButton(
            DivLAligned(
                UkIcon(icon, height=16, width=16, cls="opacity-70 shrink-0"),
                Span(
                    title,
                    cls="group-data-[sidebar-state=collapsed]/sidebar-wrapper:hidden",
                ),
                cls="gap-3 justify-start w-full",
            ),
            href=url,
            cls=f"{TextT.sm} font-medium rounded-lg hover:bg-muted",
        ),
    )


def NavSection(title, items):
    """Section group using shared sidebar primitives."""
    return SidebarGroup(
        SidebarGroupLabel(title, cls=SiteStyles.caption + " px-3 mb-2 mt-2"),
        SidebarGroupContent(SidebarMenu(*[NavItem(label, href) for label, href in items])),
    )


def AppSidebar():
    """Sidebar built from reusable UI sidebar components."""
    nav_sections = [
        (
            "Platform",
            [
                ("Dashboard", "/dashboard"),
                ("Projects", "/projects"),
                ("Viewer", "/viewer"),
            ],
        ),
        ("Analysis", [("Run Analysis", "/analysis/run"), ("Reports", "/reports")]),
        ("Library", [("Documents", "/library/documents"), ("Rules", "/library/rules")]),
    ]

    # Flatten sections into a list of MonsterUI nav components
    nav_groups = [NavSection(section_title, items) for section_title, items in nav_sections]

    return Sidebar(cls="apple-blur bg-sidebar border-r border-border h-svh")(
        SidebarTrigger(cls="self-end mb-1 border-border bg-background hover:bg-muted"),
        SidebarInset(
            SidebarContent(
                H2(
                    "BIM Guard",
                    cls="font-bold tracking-tighter text-2xl px-3 pb-2 group-data-[sidebar-state=collapsed]/sidebar-wrapper:hidden",
                ),
                *nav_groups,
                cls="px-2",
            ),
            SidebarFooter(
                SidebarMenu(
                    SidebarMenuItem(
                        SidebarMenuButton(
                            DivLAligned(
                                UkIcon(
                                    "settings",
                                    height=16,
                                    width=16,
                                    cls="opacity-70 shrink-0",
                                ),
                                Span(
                                    "Settings",
                                    cls="group-data-[sidebar-state=collapsed]/sidebar-wrapper:hidden",
                                ),
                                cls="gap-3 justify-start w-full",
                            ),
                            href="/settings",
                            cls="text-sm font-medium text-muted-foreground hover:text-foreground",
                        )
                    )
                ),
                cls="border-t border-border pt-3",
            ),
            cls="flex h-full flex-col",
        ),
        SidebarRail(),
    )


def DashboardLayout(*content):
    """
    Standard layout for dashboard pages with collapsible sidebar primitives.
    """
    return SidebarProvider(cls=SiteStyles.bg)(
        AppSidebar(),
        SidebarInset(Main(cls="flex-1")(Div(cls="p-10 max-w-6xl mx-auto space-y-10")(*content))),
    )
