"""Repository layer for SUS — Spike Understanding System.

Provides data access abstractions that isolate services from raw
SQLAlchemy queries. Each repository accepts a Session through its
constructor and does NOT commit or close sessions.
"""
