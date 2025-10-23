#!/usr/bin/env python3
"""
Redis-based Metrics Tracking for Artemis

Single Responsibility: Track and aggregate pipeline metrics
Stores time-series data for analytics and monitoring
"""

import json
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from redis_client import RedisClient, get_redis_client, is_redis_available


class RedisMetrics:
    """
    Metrics tracker using Redis

    Features:
    - Time-series data storage
    - Aggregate statistics (counters, averages)
    - Cost tracking
    - Performance monitoring
    """

    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        key_prefix: str = "artemis:metrics"
    ):
        """
        Initialize metrics tracker

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
            print("⚠️  Redis not available - Metrics tracking disabled")

    def track_pipeline_completion(
        self,
        card_id: str,
        duration_seconds: float,
        status: str,
        total_cost: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track pipeline completion

        Args:
            card_id: Card ID
            duration_seconds: Pipeline duration
            status: Final status (COMPLETED, FAILED, etc.)
            total_cost: Total LLM API cost
            metadata: Additional metadata

        Returns:
            True if tracked successfully
        """
        if not self.enabled:
            return False

        try:
            timestamp = time.time()
            date_key = datetime.now().strftime("%Y-%m-%d")

            # Store in time-series (sorted set)
            ts_key = f"{self.key_prefix}:timeseries:pipelines"
            pipeline_data = {
                "card_id": card_id,
                "duration_seconds": duration_seconds,
                "status": status,
                "cost": total_cost,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            self.redis.client.zadd(ts_key, {json.dumps(pipeline_data): timestamp})

            # Update aggregate counters
            self.redis.client.hincrby(f"{self.key_prefix}:total", "pipelines_completed", 1)
            self.redis.client.hincrbyfloat(f"{self.key_prefix}:total", "total_cost", total_cost)
            self.redis.client.hincrbyfloat(f"{self.key_prefix}:total", "total_duration", duration_seconds)

            # Update daily counters
            day_key = f"{self.key_prefix}:daily:{date_key}"
            self.redis.client.hincrby(day_key, "completions", 1)
            self.redis.client.hincrbyfloat(day_key, "cost", total_cost)
            self.redis.client.hincrbyfloat(day_key, "duration", duration_seconds)
            self.redis.expire(day_key, 2592000)  # 30 days

            # Track by status
            status_key = f"{self.key_prefix}:status:{status.lower()}"
            self.redis.incr(status_key)

            return True

        except Exception as e:
            print(f"⚠️  Failed to track pipeline completion: {e}")
            return False

    def track_llm_request(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        cache_hit: bool = False
    ) -> bool:
        """
        Track LLM API request

        Args:
            provider: LLM provider (openai, anthropic)
            model: Model name
            prompt_tokens: Prompt tokens used
            completion_tokens: Completion tokens used
            cost: Request cost
            cache_hit: Whether response was cached

        Returns:
            True if tracked successfully
        """
        if not self.enabled:
            return False

        try:
            # Update totals
            self.redis.client.hincrby(f"{self.key_prefix}:llm", "total_requests", 1)
            self.redis.client.hincrby(f"{self.key_prefix}:llm", "prompt_tokens", prompt_tokens)
            self.redis.client.hincrby(f"{self.key_prefix}:llm", "completion_tokens", completion_tokens)
            self.redis.client.hincrbyfloat(f"{self.key_prefix}:llm", "total_cost", cost)

            # Track cache hits
            if cache_hit:
                self.redis.client.hincrby(f"{self.key_prefix}:llm", "cache_hits", 1)
            else:
                self.redis.client.hincrby(f"{self.key_prefix}:llm", "cache_misses", 1)

            # Track by provider
            provider_key = f"{self.key_prefix}:llm:{provider}"
            self.redis.client.hincrby(provider_key, "requests", 1)
            self.redis.client.hincrbyfloat(provider_key, "cost", cost)

            # Track by model
            model_key = f"{self.key_prefix}:llm:model:{model}"
            self.redis.client.hincrby(model_key, "requests", 1)
            self.redis.client.hincrbyfloat(model_key, "cost", cost)

            return True

        except Exception as e:
            print(f"⚠️  Failed to track LLM request: {e}")
            return False

    def track_code_review(
        self,
        developer: str,
        overall_score: int,
        critical_issues: int,
        high_issues: int,
        status: str
    ) -> bool:
        """
        Track code review results

        Args:
            developer: Developer name (developer-a, developer-b)
            overall_score: Overall score (0-100)
            critical_issues: Number of critical issues
            high_issues: Number of high issues
            status: Review status (PASS, FAIL, etc.)

        Returns:
            True if tracked successfully
        """
        if not self.enabled:
            return False

        try:
            # Track by developer
            dev_key = f"{self.key_prefix}:code_review:{developer}"
            self.redis.client.hincrby(dev_key, "total_reviews", 1)
            self.redis.client.hincrby(dev_key, "total_score", overall_score)
            self.redis.client.hincrby(dev_key, "critical_issues", critical_issues)
            self.redis.client.hincrby(dev_key, "high_issues", high_issues)

            # Track by status
            status_key = f"{self.key_prefix}:code_review:status:{status.lower()}"
            self.redis.incr(status_key)

            return True

        except Exception as e:
            print(f"⚠️  Failed to track code review: {e}")
            return False

    def get_total_metrics(self) -> Dict[str, Any]:
        """
        Get total aggregate metrics

        Returns:
            Dictionary with total metrics
        """
        if not self.enabled:
            return {"enabled": False}

        try:
            pipeline_metrics = self.redis.hgetall(f"{self.key_prefix}:total")
            llm_metrics = self.redis.hgetall(f"{self.key_prefix}:llm")

            # Calculate averages
            pipelines = int(pipeline_metrics.get("pipelines_completed", 0))
            avg_duration = 0.0
            avg_cost = 0.0

            if pipelines > 0:
                total_duration = float(pipeline_metrics.get("total_duration", 0))
                total_cost = float(pipeline_metrics.get("total_cost", 0))
                avg_duration = total_duration / pipelines
                avg_cost = total_cost / pipelines

            # Calculate cache hit rate
            cache_hits = int(llm_metrics.get("cache_hits", 0))
            cache_misses = int(llm_metrics.get("cache_misses", 0))
            total_llm_requests = cache_hits + cache_misses
            cache_hit_rate = (cache_hits / total_llm_requests * 100) if total_llm_requests > 0 else 0

            return {
                "enabled": True,
                "pipelines": {
                    "total_completed": pipelines,
                    "total_duration_seconds": float(pipeline_metrics.get("total_duration", 0)),
                    "average_duration_seconds": round(avg_duration, 2),
                    "total_cost": float(pipeline_metrics.get("total_cost", 0)),
                    "average_cost": round(avg_cost, 4)
                },
                "llm": {
                    "total_requests": int(llm_metrics.get("total_requests", 0)),
                    "cache_hits": cache_hits,
                    "cache_misses": cache_misses,
                    "cache_hit_rate_percent": round(cache_hit_rate, 2),
                    "total_cost": float(llm_metrics.get("total_cost", 0)),
                    "prompt_tokens": int(llm_metrics.get("prompt_tokens", 0)),
                    "completion_tokens": int(llm_metrics.get("completion_tokens", 0))
                }
            }

        except Exception as e:
            print(f"⚠️  Failed to get total metrics: {e}")
            return {"enabled": True, "error": str(e)}

    def get_daily_metrics(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get metrics for a specific day

        Args:
            date: Date to get metrics for (default: today)

        Returns:
            Dictionary with daily metrics
        """
        if not self.enabled:
            return {"enabled": False}

        try:
            if date is None:
                date = datetime.now()

            date_key = date.strftime("%Y-%m-%d")
            day_key = f"{self.key_prefix}:daily:{date_key}"
            metrics = self.redis.hgetall(day_key)

            completions = int(metrics.get("completions", 0))
            return {
                "enabled": True,
                "date": date_key,
                "completions": completions,
                "total_cost": float(metrics.get("cost", 0)),
                "total_duration": float(metrics.get("duration", 0))
            }

        except Exception as e:
            print(f"⚠️  Failed to get daily metrics: {e}")
            return {"enabled": True, "error": str(e)}

    def get_recent_pipelines(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent pipeline executions

        Args:
            limit: Max number of pipelines to return

        Returns:
            List of recent pipeline data
        """
        if not self.enabled:
            return []

        try:
            ts_key = f"{self.key_prefix}:timeseries:pipelines"

            # Get recent pipelines (sorted by timestamp, descending)
            recent = self.redis.client.zrevrange(ts_key, 0, limit - 1)

            pipelines = []
            for item in recent:
                try:
                    pipeline_data = json.loads(item)
                    pipelines.append(pipeline_data)
                except json.JSONDecodeError:
                    continue

            return pipelines

        except Exception as e:
            print(f"⚠️  Failed to get recent pipelines: {e}")
            return []


# ============================================================================
# MAIN - TESTING
# ============================================================================

if __name__ == "__main__":
    print("Testing Redis metrics...")

    try:
        metrics = RedisMetrics()

        if not metrics.enabled:
            print("❌ Redis not available. Start Redis with:")
            print("   docker run -d -p 6379:6379 redis")
            exit(1)

        # Track some sample data
        print("\n1. Tracking sample pipeline completions...")
        for i in range(5):
            metrics.track_pipeline_completion(
                card_id=f"test-card-{i}",
                duration_seconds=120.5 + i * 10,
                status="COMPLETED",
                total_cost=0.15 + i * 0.05,
                metadata={"test": True}
            )

        # Track LLM requests
        print("\n2. Tracking sample LLM requests...")
        for i in range(10):
            metrics.track_llm_request(
                provider="openai",
                model="gpt-4o",
                prompt_tokens=1000,
                completion_tokens=500,
                cost=0.05,
                cache_hit=(i % 2 == 0)  # 50% cache hit rate
            )

        # Get total metrics
        print("\n3. Getting total metrics...")
        total = metrics.get_total_metrics()
        print(f"   Pipelines: {total['pipelines']['total_completed']}")
        print(f"   Avg Duration: {total['pipelines']['average_duration_seconds']}s")
        print(f"   Total Cost: ${total['pipelines']['total_cost']:.2f}")
        print(f"   LLM Requests: {total['llm']['total_requests']}")
        print(f"   Cache Hit Rate: {total['llm']['cache_hit_rate_percent']}%")

        # Get recent pipelines
        print("\n4. Getting recent pipelines...")
        recent = metrics.get_recent_pipelines(limit=3)
        for pipeline in recent:
            print(f"   {pipeline['card_id']}: {pipeline['status']} in {pipeline['duration_seconds']}s")

        print("\n✅ All metrics tests passed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
