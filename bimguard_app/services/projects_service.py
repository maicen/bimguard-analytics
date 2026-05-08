"""Project service for IFC-backed project CRUD and file handling."""

from pathlib import Path

from app.services.object_storage import ObjectStorage
from app.services.persistence import PersistenceService
from app.utils import (
    md5_hex,
    now_iso_utc,
    rows_desc_by_id,
    safe_upload_name,
)


class ProjectsService:
    """Encapsulates projects persistence and IFC file operations."""

    def __init__(self):
        """Initialize project storage and ensure required table columns exist."""
        self._storage = ObjectStorage()
        self._projects = PersistenceService.get_table(
            "projects",
            {
                "id": int,
                "name": str,
                "description": str,
                "status": str,
                "ifc_file_path": str,
                "ifc_md5_hash": str,
                "created_at": str,
                "updated_at": str,
            },
            required_columns={"ifc_file_path": str, "ifc_md5_hash": str},
        )

    def list_projects(self):
        """Return all projects ordered by newest first."""
        return rows_desc_by_id(self._projects)

    def total_projects(self) -> int:
        """Return the number of stored projects."""
        return len(self.list_projects())

    def get_project(self, project_id: int):
        """Return a single project by primary key."""
        return self._projects.get(project_id)

    async def prepare_ifc_upload(self, ifc_file) -> tuple[str, str]:
        """Validate and persist an uploaded IFC file, returning path and MD5 hash."""
        if not ifc_file or not getattr(ifc_file, "filename", None):
            return "", ""

        filename = safe_upload_name(ifc_file.filename)
        if not filename.lower().endswith(".ifc"):
            return "", ""

        content = await ifc_file.read()
        if not content:
            return "", ""

        ifc_md5_hash = md5_hex(content)
        storage_ref = self._storage.save_upload(filename, content, "uploads/ifc")
        return storage_ref, ifc_md5_hash

    def create_project(
        self,
        name: str,
        description: str = "",
        status: str = "Draft",
        ifc_file_path: str = "",
        ifc_md5_hash: str = "",
    ):
        """Insert a new project record into the database."""
        now = now_iso_utc()
        return self._projects.insert(
            {
                "name": name.strip(),
                "description": description.strip(),
                "status": status,
                "ifc_file_path": ifc_file_path,
                "ifc_md5_hash": ifc_md5_hash,
                "created_at": now,
                "updated_at": now,
            }
        )

    def update_project(
        self, project_id: int, name: str, description: str = "", status: str = "Draft"
    ):
        """Update editable fields for an existing project."""
        self._projects.update(
            updates={
                "name": name.strip(),
                "description": description.strip(),
                "status": status,
                "updated_at": now_iso_utc(),
            },
            pk_values=project_id,
        )

    def delete_project(self, project_id: int):
        """Delete a project row by primary key."""
        project = self.get_project(project_id)
        if project is not None:
            self._storage.delete(project.get("ifc_file_path") or "")
        self._projects.delete(project_id)

    def resolve_ifc_file(self, project_id: int) -> Path | None:
        """Return an existing IFC file path for a project, if present."""
        project = self.get_project(project_id)
        if project is None:
            return None

        ifc_file_path = project.get("ifc_file_path") or ""
        if not ifc_file_path:
            return None

        return self._storage.materialize_local_path(ifc_file_path)
