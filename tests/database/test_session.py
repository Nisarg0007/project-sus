"""
Tests for database session management and configuration.

Verifies that:
1. get_db() yields a working database session
2. Database configuration default is correct
3. Engine and SessionLocal are properly configured
4. Session lifecycle works correctly
"""

from unittest.mock import patch

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from src.config import Settings


# ---------------------------------------------------------------------------
# Test: get_db() Dependency
# ---------------------------------------------------------------------------


class TestGetDb:
    """Test the FastAPI get_db() dependency."""

    def test_get_db_yields_session(self):
        """get_db() should yield a SQLAlchemy Session."""
        from src.database.session import get_db

        gen = get_db()
        db = next(gen)
        try:
            assert isinstance(db, Session)
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

    def test_get_db_session_is_usable(self):
        """The yielded session should be able to execute queries."""
        from src.database.session import get_db

        gen = get_db()
        db = next(gen)
        try:
            result = db.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
            assert result.scalar() == 1
        finally:
            try:
                next(gen)
            except StopIteration:
                pass


# ---------------------------------------------------------------------------
# Test: Database Configuration
# ---------------------------------------------------------------------------


class TestDatabaseConfig:
    """Test that database configuration is correct."""

    def test_default_database_url(self):
        """Default database_url should be sqlite:///data/sus.db."""
        s = Settings()
        assert s.database_url == "sqlite:///data/sus.db"

    def test_database_url_override(self):
        """database_url should be overridable via env var."""
        with patch.dict("os.environ", {"SUS_DATABASE_URL": "sqlite:///tmp/test.db"}):
            s = Settings()
            assert s.database_url == "sqlite:///tmp/test.db"

    def test_settings_preserves_existing_fields(self):
        """Adding database_url should not break existing settings."""
        s = Settings()
        assert s.app_name == "SUS — Spike Understanding System"
        assert s.api_prefix == "/api/v1"
        assert s.default_z_threshold == 0.5


# ---------------------------------------------------------------------------
# Test: Engine
# ---------------------------------------------------------------------------


class TestEngine:
    """Test that the database engine is properly configured."""

    def test_engine_is_created(self):
        """Engine should be created from config."""
        from src.database.engine import engine
        assert engine is not None

    def test_session_local_is_configured(self):
        """SessionLocal should be a configured sessionmaker."""
        from src.database.engine import SessionLocal
        assert SessionLocal is not None

    def test_session_local_creates_usable_session(self):
        """SessionLocal should create a working session."""
        from src.database.engine import SessionLocal
        db = SessionLocal()
        try:
            assert isinstance(db, Session)
            result = db.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
            assert result.scalar() == 1
        finally:
            db.close()
