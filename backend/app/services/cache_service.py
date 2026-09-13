"""Cache service: Redis with automatic in-memory fallback for dev."""
import hashlib
import json
import logging
import time
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_memory: dict[str, tuple[float, str]] = {}
_redis = None
_redis_checked = False


def _get_redis():
    global _redis, _redis_checked
    if _redis_checked:
        return _redis
    _redis_checked = True
    if not settings.redis_url:
        return None
    try:
        import redis

        _redis = redis.Redis.from_url(settings.redis_url, socket_timeout=2, decode_responses=True)
        _redis.ping()
        logger.info("Redis connected")
    except Exception as exc:  # pragma: no cover
        logger.warning("Redis unavailable (%s) — using in-memory cache", exc)
        _redis = None
    return _redis


def _hash_key(parts: list) -> str:
    raw = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cache_get(prefix: str, parts: list) -> Any:
    key = f"gs:{prefix}:{_hash_key(parts)}"
    r = _get_redis()
    try:
        if r:
            val = r.get(key)
            return json.loads(val) if val else None
        item = _memory.get(key)
        if item and item[0] > time.time():
            return json.loads(item[1])
        if item:
            _memory.pop(key, None)
    except Exception as exc:
        logger.debug("cache_get error: %s", exc)
    return None


def cache_set(prefix: str, parts: list, value: Any, ttl: int | None = None) -> None:
    key = f"gs:{prefix}:{_hash_key(parts)}"
    ttl = ttl or settings.ai_cache_ttl
    r = _get_redis()
    try:
        payload = json.dumps(value, ensure_ascii=False, default=str)
        if r:
            r.setex(key, ttl, payload)
        else:
            _memory[key] = (time.time() + ttl, payload)
    except Exception as exc:
        logger.debug("cache_set error: %s", exc)


def cache_incr(prefix: str, parts: list, ttl: int = 60) -> int:
    """Increment a counter; returns the new value (rate limiting / quotas)."""
    key = f"gs:{prefix}:{_hash_key(parts)}"
    r = _get_redis()
    try:
        if r:
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl)
            _, val = pipe.execute()
            return int(val)
        now = time.time()
        item = _memory.get(key)
        if not item or item[0] < now:
            _memory[key] = (now + ttl, "1")
            return 1
        val = int(item[1]) + 1
        _memory[key] = (item[0], str(val))
        return val
    except Exception as exc:
        logger.debug("cache_incr error: %s", exc)
        return 0
