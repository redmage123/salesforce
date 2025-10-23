#!/usr/bin/env python3
"""
LLM Response Cache using Redis

Single Responsibility: Cache LLM responses to reduce API costs
Implements caching strategy with TTL and cache invalidation
"""

import json
import hashlib
from typing import Optional, List, Dict, Any
from dataclasses import asdict

from llm_client import LLMClientInterface, LLMMessage, LLMResponse
from redis_client import RedisClient, get_redis_client, is_redis_available
from artemis_exceptions import RedisCacheError, wrap_exception


class LLMCache:
    """
    LLM response cache using Redis

    Single Responsibility: Cache LLM API responses
    """

    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        ttl_seconds: int = 604800,  # 7 days default
        key_prefix: str = "artemis:llm:cache"
    ):
        """
        Initialize LLM cache

        Args:
            redis_client: Redis client (uses default if not provided)
            ttl_seconds: Cache TTL in seconds (default 7 days)
            key_prefix: Redis key prefix for namespacing
        """
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = get_redis_client(raise_on_error=False)

        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix
        self.enabled = self.redis is not None

        if not self.enabled:
            print("⚠️  Redis not available - LLM caching disabled")

    def _generate_cache_key(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """
        Generate deterministic cache key from request parameters

        Args:
            messages: List of messages
            model: Model name
            temperature: Temperature parameter
            max_tokens: Max tokens parameter

        Returns:
            Cache key string
        """
        # Create deterministic string representation
        cache_data = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Serialize to JSON with sorted keys for consistency
        cache_str = json.dumps(cache_data, sort_keys=True)

        # Hash to create shorter key
        hash_digest = hashlib.sha256(cache_str.encode()).hexdigest()

        return f"{self.key_prefix}:{hash_digest}"

    def get(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Optional[LLMResponse]:
        """
        Get cached LLM response

        Args:
            messages: List of messages
            model: Model name
            temperature: Temperature
            max_tokens: Max tokens

        Returns:
            Cached LLMResponse or None if not cached
        """
        if not self.enabled:
            return None

        try:
            cache_key = self._generate_cache_key(messages, model, temperature, max_tokens)
            cached_json = self.redis.get(cache_key)

            if cached_json:
                cached_data = json.loads(cached_json)
                return LLMResponse(**cached_data)

            return None

        except Exception as e:
            # Don't fail on cache errors - just return None
            print(f"⚠️  Cache read error: {e}")
            return None

    def set(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int,
        response: LLMResponse
    ) -> bool:
        """
        Cache LLM response

        Args:
            messages: List of messages
            model: Model name
            temperature: Temperature
            max_tokens: Max tokens
            response: LLMResponse to cache

        Returns:
            True if cached successfully
        """
        if not self.enabled:
            return False

        try:
            cache_key = self._generate_cache_key(messages, model, temperature, max_tokens)

            # Serialize response
            response_data = {
                "content": response.content,
                "model": response.model,
                "provider": response.provider,
                "usage": response.usage,
                "raw_response": response.raw_response
            }
            response_json = json.dumps(response_data)

            # Cache with TTL
            self.redis.set(cache_key, response_json, ex=self.ttl_seconds)

            return True

        except Exception as e:
            # Don't fail on cache errors
            print(f"⚠️  Cache write error: {e}")
            return False

    def invalidate_all(self) -> int:
        """
        Invalidate all cached LLM responses

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            # Get all keys with our prefix
            pattern = f"{self.key_prefix}:*"
            keys = list(self.redis.client.scan_iter(match=pattern))

            if keys:
                return self.redis.delete(*keys)
            return 0

        except Exception as e:
            print(f"⚠️  Cache invalidation error: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        if not self.enabled:
            return {"enabled": False}

        try:
            pattern = f"{self.key_prefix}:*"
            keys = list(self.redis.client.scan_iter(match=pattern))

            return {
                "enabled": True,
                "total_cached_responses": len(keys),
                "ttl_seconds": self.ttl_seconds,
                "key_prefix": self.key_prefix
            }

        except Exception as e:
            return {"enabled": True, "error": str(e)}


class CachedLLMClient(LLMClientInterface):
    """
    LLM client wrapper with caching

    Single Responsibility: Add caching layer to LLM client
    Open/Closed: Extends LLM client without modifying it
    """

    def __init__(
        self,
        llm_client: LLMClientInterface,
        cache: Optional[LLMCache] = None,
        verbose: bool = False
    ):
        """
        Initialize cached LLM client

        Args:
            llm_client: Underlying LLM client
            cache: LLM cache (creates default if not provided)
            verbose: Print cache hit/miss messages
        """
        self.llm_client = llm_client
        self.cache = cache or LLMCache()
        self.verbose = verbose
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "total_requests": 0
        }

    def complete(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[Dict] = None
    ) -> LLMResponse:
        """
        Complete with caching

        First checks cache, then calls LLM if not cached
        """
        self.stats["total_requests"] += 1

        # Use default model if not specified
        actual_model = model or self._get_default_model()

        # Try cache first
        cached_response = self.cache.get(messages, actual_model, temperature, max_tokens)

        if cached_response:
            self.stats["cache_hits"] += 1
            if self.verbose:
                print(f"✅ Cache HIT ({self.stats['cache_hits']}/{self.stats['total_requests']}) - Saved API call!")
            return cached_response

        # Cache miss - call LLM
        self.stats["cache_misses"] += 1
        if self.verbose:
            print(f"⚠️  Cache MISS ({self.stats['cache_misses']}/{self.stats['total_requests']}) - Calling LLM API")

        response = self.llm_client.complete(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format
        )

        # Cache the response
        self.cache.set(messages, actual_model, temperature, max_tokens, response)

        return response

    def get_available_models(self) -> List[str]:
        """Get available models from underlying client"""
        return self.llm_client.get_available_models()

    def _get_default_model(self) -> str:
        """Get default model from underlying client"""
        models = self.llm_client.get_available_models()
        return models[0] if models else "unknown"

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats including hit rate
        """
        total = self.stats["total_requests"]
        hit_rate = (self.stats["cache_hits"] / total * 100) if total > 0 else 0

        cache_stats = self.cache.get_stats()

        return {
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_enabled": cache_stats.get("enabled", False),
            "total_cached_responses": cache_stats.get("total_cached_responses", 0)
        }


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def create_cached_llm_client(
    provider: str = "openai",
    api_key: Optional[str] = None,
    cache_ttl_seconds: int = 604800,
    verbose: bool = False
) -> CachedLLMClient:
    """
    Create LLM client with caching enabled

    Args:
        provider: LLM provider ("openai" or "anthropic")
        api_key: API key (optional)
        cache_ttl_seconds: Cache TTL in seconds (default 7 days)
        verbose: Print cache hit/miss messages

    Returns:
        CachedLLMClient instance

    Example:
        client = create_cached_llm_client("openai", verbose=True)
        response = client.complete([LLMMessage(role="user", content="Hello")])
        # Second call with same message will use cache
        response2 = client.complete([LLMMessage(role="user", content="Hello")])
    """
    from llm_client import create_llm_client

    llm_client = create_llm_client(provider, api_key)
    cache = LLMCache(ttl_seconds=cache_ttl_seconds)

    return CachedLLMClient(llm_client, cache, verbose)


# ============================================================================
# MAIN - TESTING
# ============================================================================

if __name__ == "__main__":
    print("Testing LLM cache...")

    try:
        from llm_client import LLMMessage

        # Create cached client
        print("\n1. Creating cached LLM client...")
        client = create_cached_llm_client("openai", verbose=True)

        # First request (cache miss)
        print("\n2. First request (should be MISS)...")
        messages = [
            LLMMessage(role="system", content="You are a helpful assistant"),
            LLMMessage(role="user", content="Say 'Hello World' and nothing else")
        ]

        response1 = client.complete(messages, max_tokens=50)
        print(f"Response: {response1.content[:100]}")

        # Second identical request (cache hit)
        print("\n3. Second identical request (should be HIT)...")
        response2 = client.complete(messages, max_tokens=50)
        print(f"Response: {response2.content[:100]}")

        # Verify responses are identical
        assert response1.content == response2.content, "Cached responses should match!"
        print("✅ Cached response matches original")

        # Show stats
        print("\n4. Cache statistics:")
        stats = client.get_cache_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")

        # Calculate cost savings
        if stats["cache_hits"] > 0:
            print(f"\n💰 Cost Savings:")
            print(f"   Cache hits: {stats['cache_hits']}")
            print(f"   Hit rate: {stats['hit_rate_percent']}%")
            print(f"   Estimated savings: ${stats['cache_hits'] * 0.01:.2f} (at $0.01/request)")

        print("\n✅ All LLM cache tests passed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
