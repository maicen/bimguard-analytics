"""Dashboard page routes and high-level compliance stats view."""

# app/routes/dashboard.py

from fasthtml.common import Div, P, Title
from monsterui.all import (
    H1,
    DivFullySpaced,
    Grid,
)

from app.components.layout import DashboardLayout
from app.components.themed_ui import SiteStyles
from app.components.ui import BentoBox, LinkButton
from app.modules.orchestrator import BIMGuard_App

# Initialize orchestrator (provides run_dashboard stats)
_bim_guard_app = BIMGuard_App()


def setup_routes(rt):
    """Register dashboard page routes."""

    @rt("/dashboard")
    def dashboard_page():
        stats = _bim_guard_app.run_dashboard()

        return Title("Dashboard - BIM Guard"), DashboardLayout(
            # Page Header
            DivFullySpaced(cls="items-end mb-8")(
                Div(cls="space-y-1")(
                    P("Overview", cls=SiteStyles.caption),
                    H1("Compliance Dashboard", cls=SiteStyles.h1),
                ),
                LinkButton(
                    "New Check",
                    href="/projects/new",
                    variant="primary",
                    cls="rounded-full px-6 py-2",
                ),
            ),
            # Bento Stats Grid
            Grid(cols=2, cols_md=2, cols_lg=4, cls="gap-6")(
                BentoBox(
                    "Total Projects",
                    str(stats["total_projects"]),
                    "Active in project registry",
                ),
                BentoBox(
                    "Documents",
                    str(stats["total_documents"]),
                    "Uploaded specification documents",
                ),
                BentoBox("Rules", str(stats["total_rules"]), "Compliance rules defined"),
                BentoBox("Issues Found (TODO)", "34", "-12 from last week"),
            ),
        )
