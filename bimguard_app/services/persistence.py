"""Persistence bootstrap utilities for SQLite tables and upload directories."""

import os
from pathlib import Path

from fastlite import database
from supabase import create_client

from app.services.db_adapters import SQLiteTableAdapter, SupabaseTableAdapter


class PersistenceService:
    """Centralizes database and storage path bootstrap for route modules."""

    DATA_DIR = Path("data")
    DB_PATH = DATA_DIR / "bimguard.sqlite"
    UPLOADS_DIR = DATA_DIR / "uploads"
    DB_BACKEND = os.getenv("BIM_GUARD_DB_BACKEND", "supabase").strip().lower()
    _db = None

    @classmethod
    def get_db(cls):
        """Return a singleton FastLite database connection."""
        if cls._db is not None:
            return cls._db

        if cls.DB_BACKEND == "supabase":
            url = os.getenv("SUPABASE_URL", "").strip()
            key = (
                os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
                or os.getenv("SUPABASE_KEY", "").strip()
            )
            if not url:
                raise ValueError("SUPABASE_URL is required when BIM_GUARD_DB_BACKEND=supabase")
            if not key:
                raise ValueError(
                    "SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY is required "
                    "when BIM_GUARD_DB_BACKEND=supabase"
                )
            cls._db = create_client(url, key)
            return cls._db

        cls.DATA_DIR.mkdir(exist_ok=True)
        cls._db = database(str(cls.DB_PATH))
        return cls._db

    @classmethod
    def get_table(
        cls,
        table_name: str,
        schema: dict,
        pk: str = "id",
        required_columns: dict | None = None,
    ):
        """Create or migrate a table, then return the table handle."""
        db = cls.get_db()
        if cls.DB_BACKEND == "supabase":
            table = SupabaseTableAdapter(db, table_name, schema, pk=pk)
            for column_name, column_type in (required_columns or {}).items():
                table.add_column(column_name, column_type)
            return table

        table = SQLiteTableAdapter(db[table_name])
        table.create(schema, pk=pk, if_not_exists=True)

        for column_name, column_type in (required_columns or {}).items():
            if column_name not in table.columns_dict:
                table.add_column(column_name, column_type)

        return table

    @classmethod
    def uploads_dir(cls, *parts: str) -> Path:
        """Return an uploads subdirectory, creating it when missing."""
        path = cls.UPLOADS_DIR.joinpath(*parts)
        path.mkdir(parents=True, exist_ok=True)
        return path
