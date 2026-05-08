from fasthtml.common import A, Aside, Div, Main, Nav


def Sidebar():
    return Aside(
        Nav(
            A(
                "Dashboard",
                href="/dashboard",
                cls="block px-4 py-2 text-foreground hover:bg-muted",
            ),
            A(
                "Library",
                href="/library/documents",
                cls="block px-4 py-2 text-foreground hover:bg-muted",
            ),
            A(
                "Rules",
                href="/library/rules",
                cls="block px-4 py-2 text-foreground hover:bg-muted",
            ),
            A(
                "Reports",
                href="/reports",
                cls="block px-4 py-2 text-foreground hover:bg-muted",
            ),
            cls="space-y-2",
        ),
        cls="w-64 min-h-screen bg-card border-r border-border",
    )


def DashboardLayout(*content):
    return Div(Sidebar(), Main(*content, cls="flex-1 p-8 bg-muted"), cls="flex min-h-screen")
