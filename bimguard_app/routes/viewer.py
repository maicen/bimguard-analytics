"""IFC model viewer routes and preload wiring for project model files."""

import json

from fasthtml.common import Div, Script, Title
from monsterui.all import H2, Container

from app.components.layout import DashboardLayout
from app.components.ui import BackAction, NotFoundBlock
from app.services.projects_service import ProjectsService

_projects_service = ProjectsService()


def setup_routes(rt):
    """Register 3D viewer page routes."""

    @rt("/viewer")
    def viewer_page(project_id: int | None = None):
        project = _projects_service.get_project(project_id) if project_id is not None else None

        if project_id is not None and project is None:
            return Title("Not Found — BIM Guard"), DashboardLayout(
                Container(NotFoundBlock("Project", "/projects", "Back to Projects"))
            )

        ifc_url = ""
        if project and project.get("ifc_file_path"):
            ifc_url = f"/projects/{project_id}/ifc"
        viewer_title = "3D Viewer"
        if project is not None:
            viewer_title = f"3D Viewer - {project.get('name', 'Project')}"
        preload_ifc_url = json.dumps(ifc_url)

        return Title("Viewer - BIM Guard"), DashboardLayout(
            Div(
                # Toolbar
                Div(
                    H2(
                        viewer_title,
                        cls="text-primary-foreground bg-primary px-4 py-2 rounded-md font-semibold",
                    ),
                    Div(
                        BackAction(href="javascript:history.back()", title="Back"),
                        cls="flex gap-2",
                    ),
                    cls="flex justify-between items-center mb-4",
                ),
                # Viewer Container
                Div(
                    id="viewer-container",
                    cls="w-full h-full min-h-[75vh] rounded-xl shadow-xl overflow-hidden border border-border relative z-10",
                    style="background-color: hsl(var(--foreground) / 0.95);",
                ),
                # Initialization Script
                Script(
                    """
import { initViewer } from '/static/js/ifc-viewer.js';

window.addEventListener('DOMContentLoaded', async () => {
    const viewerAPI = await initViewer('viewer-container');
    if (viewerAPI) {
        const ifcUrl = IFC_URL_PLACEHOLDER;
        if (ifcUrl) {
            await viewerAPI.loadIfc(ifcUrl);
        }
    }
});
                """.replace("IFC_URL_PLACEHOLDER", preload_ifc_url),
                    type="module",
                ),
                cls="h-full flex flex-col p-4 bg-muted/30 rounded-xl",
            )
        )
