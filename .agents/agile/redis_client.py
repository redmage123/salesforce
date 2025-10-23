#!/usr/bin/env python3
"""
Redis Client Wrapper for Artemis

Single Responsibility: Provide unified Redis client interface
Open/Closed: Can add new Redis features without modifying core
Dependency Inversion: Depends on abstract interfaces
"""

import os
import redis
from typing import Optional, Any, Dict, List
from dataclasses import dataclass
from enum import Enum

from artemis_exceptions import (
    ArtemisException,
    ConfigurationError,
    wrap_exception
)


class RedisConnectionError(ArtemisException):
    """Redis connection error"""
    pass


class RedisCacheError(ArtemisException):
    """Redis cache operation error"""
    pass


@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    decode_responses: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5

    @classmethod
    def from_env(cls) -> 'RedisConfig':
        """Create config from environment variables"""
        return cls(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
            socket_timeout=int(os.getenv("REDIS_TIMEOUT", "5")),
            socket_connect_timeout=int(os.getenv("REDIS_CONNECT_TIMEOUT", "5"))
        )


class RedisClient:
    """
    Redis client wrapper with connection management

    Single Responsibility: Manage Redis connection and basic operations
    """

    def __init__(self, config: Optional[RedisConfig] = None):
        """
        Initialize Redis client

        Args:
            config: Redis configuration (uses env vars if not provided)
        """
        self.config = config or RedisConfig.from_env()
        self._client: Optional[redis.Redis] = None
        self._connect()

    def _connect(self) -> None:
        """Establish Redis connection"""
        try:
            self._client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                decode_responses=self.config.decode_responses,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout
            )
            # Test connection
            self._client.ping()
        except redis.ConnectionError as e:
            raise wrap_exception(
                e,
                RedisConnectionError,
                f"Failed to connect to Redis at {self.config.host}:{self.config.port}",
                context={
                    "host": self.config.host,
                    "port": self.config.port,
                    "db": self.config.db
                }
            )
        except Exception as e:
            raise wrap_exception(
                e,
                RedisConnectionError,
                f"Unexpected error connecting to Redis",
                context={"config": str(self.config)}
            )

    @property
    def client(self) -> redis.Redis:
        """Get Redis client (auto-reconnect if needed)"""
        if self._client is None:
            self._connect()
        return self._client

    def ping(self) -> bool:
        """Test Redis connection"""
        try:
            return self.client.ping()
        except Exception as e:
            raise wrap_exception(
                e,
                RedisConnectionError,
                "Redis ping failed",
                context={"host": self.config.host, "port": self.config.port}
            )

    def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        Set key to value

        Args:
            key: Redis key
            value: Value to store
            ex: Expire time in seconds
            px: Expire time in milliseconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists
        """
        try:
            return self.client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
        except Exception as e:
            raise wrap_exception(
                e,
                RedisCacheError,
                f"Failed to set Redis key",
                context={"key": key, "ex": ex}
            )

    def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        try:
            return self.client.get(key)
        except Exception as e:
            raise wrap_exception(
                e,
                RedisCacheError,
                f"Failed to get Redis key",
                context={"key": key}
            )

    def delete(self, *keys: str) -> int:
        """Delete one or more keys"""
        try:
            return self.client.delete(*keys)
        except Exception as e:
            raise wrap_exception(
                e,
                RedisCacheError,
                f"Failed to delete Redis keys",
                context={"keys": keys}
            )

    def exists(self, *keys: str) -> int:
        """Check if keys exist"""
        try:
            return self.client.exists(*keys)
        except Exception as e:
            raise wrap_exception(
                e,
                RedisCacheError,
                f"Failed to check Redis key existence",
                context={"keys": keys}
            )

    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        try:
            return self.client.expire(key, seconds)
        except Exception as e:
            raise wrap_exception(
                e,
                RedisCacheError,
                f"Failed to set expiration on Redis key",
                context={"key": key, "seconds": seconds}
            )

    def incr(self, key: str, amount: int = 1) -> int:
        """Increment key by amount"""
        try:
            return self.client.incr(key, amount)
        except Exception as e:
            raise wrap_exception(
                e,
                RedisCacheError,
                f"Failed to increment Redis key",
                context={"key": key, "amount": amount}
            )

    def hset(self, name: str, key: str, value: Any) -> int:
        """Set hash field"""
        try:
            return self.client.hset(name, key, value)
        except Exception as e:
            raise wrap_exception(
                e,
                RedisCacheError,
                f"Failed to set Redis hash field",
                context={"name": name, "key": key}
            )

    def hget(self, name: str, key: str) -> Optional[Any]:
        """Get hash field"""
        try:
            return self.client.hget(name, key)
        except Exception as e:
            raise wrap_exception(
                e,
                RedisCacheError,
                f"Failed to get Redis hash field",
                context={"name": name, "key": key}
            )

    def hgetall(self, name: str) -> Dict:
        """Get all hash fields"""
        try:
            return self.client.hgetall(name)
        except Exception as e:
            raise wrap_exception(
                e,
                RedisCacheError,
                f"Failed to get Redis hash",
                context={"name": name}
            )

    def publish(self, channel: str, message: Any) -> int:
        """Publish message to channel"""
        try:
            return self.client.publish(channel, message)
        except Exception as e:
            raise wrap_exception(
                e,
                RedisCacheError,
                f"Failed to publish to Redis channel",
                context={"channel": channel}
            )

    def close(self) -> None:
        """Close Redis connection"""
        if self._client:
            self._client.close()
            self._client = None


# Singleton instance for convenience
_default_client: Optional[RedisClient] = None


def get_redis_client(config: Optional[RedisConfig] = None, raise_on_error: bool = True) -> Optional[RedisClient]:
    """
    Get default Redis client (singleton)

    Args:
        config: Redis configuration (only used on first call)
        raise_on_error: If False, returns None instead of raising on connection error

    Returns:
        RedisClient instance or None if unavailable and raise_on_error=False
    """
    global _default_client
    if _default_client is None:
        try:
            _default_client = RedisClient(config)
        except RedisConnectionError:
            if raise_on_error:
                raise
            return None
    return _default_client


def is_redis_available() -> bool:
    """
    Check if Redis is available without raising exceptions

    Returns:
        True if Redis is available, False otherwise
    """
    try:
        config = RedisConfig.from_env()
        test_client = redis.Redis(
            host=config.host,
            port=config.port,
            db=config.db,
            password=config.password,
            decode_responses=config.decode_responses,
            socket_timeout=config.socket_timeout,
            socket_connect_timeout=config.socket_connect_timeout
        )
        test_client.ping()
        test_client.close()
        return True
    except Exception:
        return False


# ============================================================================
# MAIN - TESTING
# ============================================================================

if __name__ == "__main__":
    print("Testing Redis client...")

    try:
        # Test connection
        client = RedisClient()
        print(f"✅ Connected to Redis at {client.config.host}:{client.config.port}")

        # Test ping
        client.ping()
        print("✅ Ping successful")

        # Test set/get
        client.set("test_key", "test_value", ex=60)
        value = client.get("test_key")
        print(f"✅ Set/Get successful: {value}")

        # Test delete
        client.delete("test_key")
        print("✅ Delete successful")

        # Test hash
        client.hset("test_hash", "field1", "value1")
        hash_value = client.hget("test_hash", "field1")
        print(f"✅ Hash set/get successful: {hash_value}")

        # Cleanup
        client.delete("test_hash")
        client.close()
        print("✅ All Redis tests passed!")

    except RedisConnectionError as e:
        print(f"❌ Redis connection error: {e.message}")
        print(f"   Context: {e.context}")
        print(f"   Make sure Redis is running: docker run -d -p 6379:6379 redis")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
