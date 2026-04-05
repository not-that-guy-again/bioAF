"""Utility for serializing SQLAlchemy models to snapshot dicts."""

from datetime import date, datetime
from decimal import Decimal


def serialize_entity(obj) -> dict:
    """Serialize a SQLAlchemy model instance to a JSON-safe dict.

    Handles datetime, date, and Decimal types. Skips relationship attributes.
    """
    result = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, datetime):
            val = val.isoformat()
        elif isinstance(val, date):
            val = val.isoformat()
        elif isinstance(val, Decimal):
            val = float(val)
        result[col.name] = val
    return result
