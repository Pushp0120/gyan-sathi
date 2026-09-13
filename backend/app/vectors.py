"""pgvector Vector re-export so model imports are stable."""
from pgvector.sqlalchemy import Vector

__all__ = ["Vector"]
