"""Document persistence service for uploaded source files and extracted text."""

from app.services.object_storage import ObjectStorage
from app.services.persistence import PersistenceService
from app.utils import find_row_by_field, now_iso_utc, rows_desc_by_id


class DocumentService:
    """Encapsulates CRUD and lookup operations for uploaded documents."""

    def __init__(self):
        """Initialize the documents table and upload storage directory."""
        self._storage = ObjectStorage()
        self.upload_dir = PersistenceService.uploads_dir()
        self._documents = PersistenceService.get_table(
            "documents",
            {
                "id": int,
                "md5_hash": str,
                "filename": str,
                "file_path": str,
                "extracted_text": str,
                "upload_date": str,
            },
        )

    def list_documents(self):
        """Return all documents ordered by newest first."""
        return rows_desc_by_id(self._documents)

    def get_document(self, document_id: int):
        """Return a single document row by primary key."""
        return self._documents.get(document_id)

    def find_by_md5(self, md5_hash: str):
        """Return a document row matching the provided file hash."""
        return find_row_by_field(self._documents, "md5_hash", md5_hash)

    def create_document(self, md5_hash: str, filename: str, file_path: str, extracted_text: str):
        """Create and persist a new uploaded document record."""
        return self._documents.insert(
            {
                "md5_hash": md5_hash,
                "filename": filename,
                "file_path": file_path,
                "extracted_text": extracted_text,
                "upload_date": now_iso_utc(),
            }
        )

    def store_document_file(self, filename: str, content: bytes) -> str:
        """Persist document bytes and return the durable storage reference."""
        return self._storage.save_upload(filename, content, "uploads")

    def update_document(self, document_id: int, filename: str, extracted_text: str):
        """Update mutable document metadata and extracted text."""
        self._documents.update(
            updates={"filename": filename, "extracted_text": extracted_text},
            pk_values=document_id,
        )

    def delete_document(self, document_id: int):
        """Delete a document row by primary key."""
        self._documents.delete(document_id)

    def delete_document_with_file(self, document_id: int):
        """Delete a document and best-effort remove its stored file from disk."""
        document = self.get_document(document_id)
        if document is None:
            return

        file_path = document.get("file_path")
        if file_path:
            try:
                self._storage.delete(file_path)
            except OSError:
                # Keep DB deletion resilient even when file cleanup fails.
                pass

        self.delete_document(document_id)
