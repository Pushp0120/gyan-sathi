"""Embedding generation + cosine similarity helper."""
import math
from functools import lru_cache

from app.services.ai_service import get_ai_provider


@lru_cache(maxsize=512)
def _cached_embed(text: str, input_type: str) -> tuple[float, ...]:
    vec = get_ai_provider().embed([text], input_type=input_type)[0]
    return tuple(vec)


def embed_texts(texts: list[str], input_type: str = "passage") -> list[list[float]]:
    """Embed multiple texts (batches under the hood)."""
    provider = get_ai_provider()
    return provider.embed(texts, input_type=input_type)


def embed_query(text: str) -> list[float]:
    return list(_cached_embed(text, "query"))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
