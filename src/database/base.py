"""
SQLAlchemy declarative base for SUS — Spike Understanding System.

All ORM models inherit from this base class.
Uses SQLAlchemy 2.x style with DeclarativeBase.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.

    All models in src/database/models.py inherit from this class.
    This provides a single point of configuration for the ORM.
    """

    pass
