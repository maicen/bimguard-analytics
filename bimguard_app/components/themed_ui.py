from fasthtml.common import A, Div, Link, Nav, Script, Style
from monsterui.all import Container, Theme

BASECOAT_CSS_CDN = "https://cdn.jsdelivr.net/npm/basecoat-css@0.3.11/dist/basecoat.cdn.min.css"
BASECOAT_JS_LOCAL = "/static/js/all.min.js"
GLOBALS_CSS_LOCAL = "/static/css/globals.css"
DROPDOWN_JS_LOCAL = "/static/js/dropdown-menu.js"


class SiteStyles:
    # Colors & Effects
    bg = "bg-background antialiased text-foreground"
    glass = "apple-blur bg-background border-b border-border sticky top-0 z-50"
    card = "bg-muted border border-border rounded-[2rem] transition-all duration-300 hover:scale-[1.01]"

    # Typography
    h1 = "text-5xl font-bold tracking-tight leading-tight text-foreground"
    sub = "text-xl font-medium text-muted-foreground"
    caption = "text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground"


def SiteTheme():
    return (
        Theme.blue.headers(),  # Base MonsterUI
        Link(rel="stylesheet", href=BASECOAT_CSS_CDN),
        Link(rel="stylesheet", href=GLOBALS_CSS_LOCAL),
        Script(src=BASECOAT_JS_LOCAL, defer=True),
        Script(src=DROPDOWN_JS_LOCAL, defer=True),
        Style("""
            :root { --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif; }
            .apple-blur { backdrop-filter: saturate(180%) blur(20px); -webkit-backdrop-filter: saturate(180%) blur(20px); }
        """),
    )


def SiteNav(title: str = "BIM Guard"):
    return Nav(cls=SiteStyles.glass)(
        Container(cls="flex items-center justify-between h-12")(
            A(title, href="/", cls="font-semibold text-xl tracking-tight"),
            Div(cls="flex space-x-6 text-sm")(
                A("Dashboard", href="/dashboard"),
                A("Projects", href="/projects"),
                A("Library", href="/library"),
            ),
        )
    )
