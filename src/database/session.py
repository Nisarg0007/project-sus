"""
Database session dependency for FastAPI.

Provides the get_db() generator that yields a database session
and ensures proper cleanup after each request.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from src.database.engine import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session.

    Usage in route handlers:
        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...

    The session is automatically closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
