"""
Shared database accessor. Import this instead of calling PersistenceService directly.

Usage:
    from app.db import db
    conn = db()
"""

from app.services.persistence import PersistenceService

db = PersistenceService.get_db
