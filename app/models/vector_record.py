"""
vector_record.py — VectorRecord domain model alias.
Re-exports VectorRecord from app.models.embedding_record for domain consistency.
"""
from app.models.embedding_record import VectorRecord

__all__ = ["VectorRecord"]
