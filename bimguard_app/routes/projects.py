"""Project management routes for creating and maintaining IFC projects."""

from fasthtml.common import (
    FileResponse,
    Title,
    UploadFile,
)
from monsterui.all import Container

from app.components.layout import DashboardLayout
from app.components.projects_ui import project_form, projects_page
from app.services.projects_service import ProjectsService
from app.utils import redirect_see_other

_projects_service = ProjectsService()


def setup_routes(rt):
    """Register project CRUD and IFC download routes."""

    @rt("/projects")
    def projects_list():
        return Title("Projects - BIM Guard"), projects_page(_projects_service.list_projects())

    @rt("/projects/new")
    def projects_new():
        return Title("New Project - BIM Guard"), DashboardLayout(
            Container(project_form("Create Project", "/projects/create", include_ifc=True))
        )

    @rt("/projects/create", methods=["POST"])
    async def projects_create(
        name: str,
        description: str = "",
        status: str = "Draft",
        ifc_file: UploadFile = None,
    ):
        ifc_file_path, ifc_md5_hash = await _projects_service.prepare_ifc_upload(ifc_file)
        _projects_service.create_project(
            name=name,
            description=description,
            status=status,
            ifc_file_path=ifc_file_path,
            ifc_md5_hash=ifc_md5_hash,
        )
        return redirect_see_other("/projects")

    @rt("/projects/{project_id}/edit")
    def projects_edit(project_id: int):
        project = _projects_service.get_project(project_id)
        return Title("Edit Project - BIM Guard"), DashboardLayout(
            Container(project_form("Edit Project", f"/projects/{project_id}/update", project))
        )

    @rt("/projects/{project_id}/update", methods=["POST"])
    def projects_update(project_id: int, name: str, description: str = "", status: str = "Draft"):
        _projects_service.update_project(project_id, name, description, status)
        return redirect_see_other("/projects")

    @rt("/projects/{project_id}/delete", methods=["POST"])
    def projects_delete(project_id: int):
        _projects_service.delete_project(project_id)
        return redirect_see_other("/projects")

    @rt("/projects/{project_id}/ifc")
    def project_ifc_file(project_id: int):
        file_path = _projects_service.resolve_ifc_file(project_id)
        if file_path is None:
            return redirect_see_other("/projects")

        return FileResponse(
            file_path, media_type="application/octet-stream", filename=file_path.name
        )
