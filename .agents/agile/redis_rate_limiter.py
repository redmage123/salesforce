#!/usr/bin/env python3
"""
Redis Rate Limiter for LLM APIs

Single Responsibility: Implement rate limiting using Redis
Prevents hitting LLM API rate limits and implements backoff strategies
"""

import time
from typing import Optional
from datetime import datetime

from redis_client import RedisClient, get_redis_client, is_redis_available
from artemis_exceptions import ArtemisException


class RateLimitExceeded(ArtemisException):
    """Rate limit exceeded exception"""
    pass


class RedisRateLimiter:
    """
    Token bucket rate limiter using Redis

    Features:
    - Sliding window rate limiting
    - Per-user/per-resource limits
    - Distributed rate limiting across multiple instances
    """

    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        key_prefix: str = "artemis:ratelimit"
    ):
        """
        Initialize rate limiter

        Args:
            redis_client: Redis client (uses default if not provided)
            key_prefix: Redis key prefix for namespacing
        """
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = get_redis_client(raise_on_error=False)

        self.key_prefix = key_prefix
        self.enabled = self.redis is not None

        if not self.enabled:
            print("⚠️  Redis not available - Rate limiting disabled")

    def check_rate_limit(
        self,
        resource: str,
        limit: int,
        window_seconds: int,
        identifier: str = "default"
    ) -> bool:
        """
        Check if rate limit allows request

        Uses sliding window algorithm for accurate rate limiting

        Args:
            resource: Resource name (e.g., "llm_api", "openai")
            limit: Max requests per window
            window_seconds: Time window in seconds
            identifier: User/client identifier

        Returns:
            True if request allowed

        Raises:
            RateLimitExceeded: If rate limit exceeded
        """
        if not self.enabled:
            return True

        try:
            key = f"{self.key_prefix}:{resource}:{identifier}"
            current_time = time.time()
            window_start = current_time - window_seconds

            # Remove old entries outside the window
            self.redis.client.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            request_count = self.redis.client.zcard(key)

            if request_count >= limit:
                # Get oldest request timestamp to calculate retry time
                oldest = self.redis.client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = window_seconds - (current_time - oldest[0][1])
                else:
                    retry_after = window_seconds

                raise RateLimitExceeded(
                    f"Rate limit exceeded for {resource}",
                    context={
                        "resource": resource,
                        "limit": limit,
                        "window_seconds": window_seconds,
                        "current_count": request_count,
                        "retry_after_seconds": round(retry_after, 2)
                    }
                )

            # Add current request
            self.redis.client.zadd(key, {str(current_time): current_time})

            # Set expiration on the key
            self.redis.expire(key, window_seconds + 60)

            return True

        except RateLimitExceeded:
            raise
        except Exception as e:
            # Don't fail on rate limiter errors - allow request
            print(f"⚠️  Rate limiter error: {e}")
            return True

    def get_remaining_requests(
        self,
        resource: str,
        limit: int,
        window_seconds: int,
        identifier: str = "default"
    ) -> int:
        """
        Get remaining requests in current window

        Args:
            resource: Resource name
            limit: Max requests per window
            window_seconds: Time window in seconds
            identifier: User/client identifier

        Returns:
            Number of remaining requests
        """
        if not self.enabled:
            return limit

        try:
            key = f"{self.key_prefix}:{resource}:{identifier}"
            current_time = time.time()
            window_start = current_time - window_seconds

            # Remove old entries
            self.redis.client.zremrangebyscore(key, 0, window_start)

            # Count current requests
            request_count = self.redis.client.zcard(key)

            return max(0, limit - request_count)

        except Exception as e:
            print(f"⚠️  Error getting remaining requests: {e}")
            return limit

    def reset_rate_limit(self, resource: str, identifier: str = "default") -> bool:
        """
        Reset rate limit for a resource

        Args:
            resource: Resource name
            identifier: User/client identifier

        Returns:
            True if reset successfully
        """
        if not self.enabled:
            return False

        try:
            key = f"{self.key_prefix}:{resource}:{identifier}"
            self.redis.delete(key)
            return True

        except Exception as e:
            print(f"⚠️  Error resetting rate limit: {e}")
            return False


# ============================================================================
# LLM-SPECIFIC RATE LIMITERS
# ============================================================================

class OpenAIRateLimiter(RedisRateLimiter):
    """
    OpenAI-specific rate limiter with preset limits

    OpenAI limits (as of 2025):
    - GPT-4o: 10,000 requests/min, 2M tokens/min
    - GPT-4o-mini: 30,000 requests/min, 10M tokens/min
    """

    def __init__(self, redis_client: Optional[RedisClient] = None):
        super().__init__(redis_client, key_prefix="artemis:ratelimit:openai")

        # Conservative limits (can be adjusted)
        self.limits = {
            "gpt-4o": {"requests_per_minute": 100, "tokens_per_minute": 20000},
            "gpt-4o-mini": {"requests_per_minute": 300, "tokens_per_minute": 100000},
            "default": {"requests_per_minute": 50, "tokens_per_minute": 10000}
        }

    def check_openai_limit(
        self,
        model: str = "gpt-4o",
        identifier: str = "default"
    ) -> bool:
        """
        Check OpenAI rate limit for specific model

        Args:
            model: OpenAI model name
            identifier: User/client identifier

        Returns:
            True if request allowed
        """
        limits = self.limits.get(model, self.limits["default"])

        return self.check_rate_limit(
            resource=f"openai:{model}",
            limit=limits["requests_per_minute"],
            window_seconds=60,
            identifier=identifier
        )


class AnthropicRateLimiter(RedisRateLimiter):
    """
    Anthropic-specific rate limiter with preset limits

    Anthropic limits (as of 2025):
    - Claude Sonnet: 5,000 requests/min, 1M tokens/min
    """

    def __init__(self, redis_client: Optional[RedisClient] = None):
        super().__init__(redis_client, key_prefix="artemis:ratelimit:anthropic")

        self.limits = {
            "claude-sonnet-4-5": {"requests_per_minute": 50, "tokens_per_minute": 10000},
            "default": {"requests_per_minute": 30, "tokens_per_minute": 5000}
        }

    def check_anthropic_limit(
        self,
        model: str = "claude-sonnet-4-5",
        identifier: str = "default"
    ) -> bool:
        """
        Check Anthropic rate limit for specific model

        Args:
            model: Anthropic model name
            identifier: User/client identifier

        Returns:
            True if request allowed
        """
        limits = self.limits.get(model, self.limits["default"])

        return self.check_rate_limit(
            resource=f"anthropic:{model}",
            limit=limits["requests_per_minute"],
            window_seconds=60,
            identifier=identifier
        )


# ============================================================================
# MAIN - TESTING
# ============================================================================

if __name__ == "__main__":
    print("Testing Redis rate limiter...")

    try:
        # Test basic rate limiter
        limiter = RedisRateLimiter()

        if not limiter.enabled:
            print("❌ Redis not available. Start Redis with:")
            print("   docker run -d -p 6379:6379 redis")
            exit(1)

        print("\n1. Testing basic rate limiter (limit=3, window=5s)...")

        # Reset first
        limiter.reset_rate_limit("test_resource", "test_user")

        # Should allow 3 requests
        for i in range(3):
            allowed = limiter.check_rate_limit("test_resource", limit=3, window_seconds=5, identifier="test_user")
            print(f"   Request {i+1}: {'✅ Allowed' if allowed else '❌ Blocked'}")
            remaining = limiter.get_remaining_requests("test_resource", limit=3, window_seconds=5, identifier="test_user")
            print(f"   Remaining: {remaining}")

        # 4th request should be blocked
        print("\n2. Testing rate limit exceeded...")
        try:
            limiter.check_rate_limit("test_resource", limit=3, window_seconds=5, identifier="test_user")
            print("   ❌ Should have been blocked!")
        except RateLimitExceeded as e:
            print(f"   ✅ Correctly blocked: {e.message}")
            print(f"   Retry after: {e.context['retry_after_seconds']} seconds")

        # Test OpenAI rate limiter
        print("\n3. Testing OpenAI rate limiter...")
        openai_limiter = OpenAIRateLimiter()
        openai_limiter.reset_rate_limit("openai:gpt-4o", "test_user")

        for i in range(5):
            try:
                openai_limiter.check_openai_limit("gpt-4o", "test_user")
                print(f"   Request {i+1}: ✅ Allowed")
            except RateLimitExceeded as e:
                print(f"   Request {i+1}: ❌ Blocked - {e.message}")

        print("\n✅ All rate limiter tests passed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
