"""Tests for the lazy cache with TTL."""

import asyncio
import time

import pytest

from usaspending_mcp.client.cache import LazyCache


@pytest.fixture
def cache():
    return LazyCache()


async def test_basic_get_and_put(cache: LazyCache):
    cache.put("test_key", {"data": 42}, ttl=60)
    result = await cache.get("test_key")
    assert result == {"data": 42}


async def test_cache_miss_triggers_loader(cache: LazyCache):
    call_count = 0

    async def loader():
        nonlocal call_count
        call_count += 1
        return ["agency_a", "agency_b"]

    cache.register_loader("agencies", loader)
    result = await cache.get("agencies")

    assert result == ["agency_a", "agency_b"]
    assert call_count == 1

    # Second call should hit cache, not loader
    result2 = await cache.get("agencies")
    assert result2 == ["agency_a", "agency_b"]
    assert call_count == 1


async def test_ttl_expiration(cache: LazyCache):
    call_count = 0

    async def loader():
        nonlocal call_count
        call_count += 1
        return f"data_v{call_count}"

    cache.register_loader("short_lived", loader)

    # Put with very short TTL
    cache.put("short_lived", "stale_data", ttl=0.01)
    await asyncio.sleep(0.02)

    # Should re-fetch because TTL expired
    result = await cache.get("short_lived")
    assert result == "data_v1"
    assert call_count == 1


async def test_no_loader_raises_key_error(cache: LazyCache):
    with pytest.raises(KeyError, match="No loader registered"):
        await cache.get("nonexistent")


async def test_clear_single_key(cache: LazyCache):
    call_count = 0

    async def loader():
        nonlocal call_count
        call_count += 1
        return "fresh"

    cache.register_loader("evictable", loader)
    cache.put("evictable", "old", ttl=3600)
    assert await cache.get("evictable") == "old"
    assert call_count == 0

    cache.clear("evictable")
    result = await cache.get("evictable")
    assert result == "fresh"
    assert call_count == 1


async def test_clear_all(cache: LazyCache):
    cache.put("a", 1, ttl=3600)
    cache.put("b", 2, ttl=3600)
    assert cache.is_cached("a")
    assert cache.is_cached("b")

    cache.clear_all()
    assert not cache.is_cached("a")
    assert not cache.is_cached("b")


async def test_concurrent_access_single_load(cache: LazyCache):
    """Multiple concurrent gets should only trigger one loader call."""
    call_count = 0

    async def slow_loader():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return "loaded_once"

    cache.register_loader("contested", slow_loader)

    results = await asyncio.gather(
        cache.get("contested"),
        cache.get("contested"),
        cache.get("contested"),
    )

    assert all(r == "loaded_once" for r in results)
    assert call_count == 1


async def test_is_cached(cache: LazyCache):
    assert not cache.is_cached("missing")
    cache.put("present", "val", ttl=3600)
    assert cache.is_cached("present")
