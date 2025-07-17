#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDF Testing Infrastructure - Redis Client
High-performance caching and session management
"""

import asyncio
import json
import pickle
import hashlib
from typing import Any, Optional, Union, Dict, List
from datetime import timedelta, datetime
import aioredis
from aioredis import Redis
import structlog
from functools import wraps
import time

from core.config import settings

logger = structlog.get_logger()

# Global Redis client instance
redis_client: Optional[Redis] = None


class RedisManager:
    """High-performance Redis operations manager"""
    
    def __init__(self):
        self.client: Optional[Redis] = None
        self.connection_pool = None
        self.metrics = CacheMetrics()
    
    async def init_redis(self) -> None:
        """Initialize Redis connection with optimized pool"""
        if not settings.REDIS_URL:
            logger.warning("Redis URL not configured, caching disabled")
            return
        
        try:
            # Create connection pool for better performance
            self.connection_pool = aioredis.ConnectionPool.from_url(
                str(settings.REDIS_URL),
                max_connections=settings.REDIS_POOL_SIZE,
                retry_on_timeout=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                health_check_interval=30
            )
            
            self.client = aioredis.Redis(
                connection_pool=self.connection_pool,
                decode_responses=False  # We'll handle encoding manually
            )
            
            # Test connection
            await self.ping()
            logger.info("Redis connection initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Redis", error=str(e))
            self.client = None
            raise
    
    async def ping(self) -> bool:
        """Test Redis connection"""
        if not self.client:
            return False
        
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error("Redis ping failed", error=str(e))
            return False
    
    async def close(self) -> None:
        """Close Redis connections"""
        if self.client:
            await self.client.close()
        if self.connection_pool:
            await self.connection_pool.disconnect()
        logger.info("Redis connections closed")
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for Redis storage"""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps(value).encode('utf-8')
        else:
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from Redis"""
        try:
            # Try JSON first (faster for simple types)
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle for complex objects
            return pickle.loads(data)
    
    def _generate_key(self, key: str, prefix: str = "idf") -> str:
        """Generate namespaced cache key"""
        return f"{prefix}:{key}"
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with metrics tracking"""
        if not self.client:
            return default
        
        start_time = time.time()
        
        try:
            cache_key = self._generate_key(key)
            data = await self.client.get(cache_key)
            
            if data is None:
                self.metrics.record_miss()
                return default
            
            value = self._deserialize(data)
            self.metrics.record_hit()
            self.metrics.record_operation_time(time.time() - start_time)
            
            return value
            
        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            self.metrics.record_error()
            return default
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with optional TTL"""
        if not self.client:
            return False
        
        start_time = time.time()
        
        try:
            cache_key = self._generate_key(key)
            serialized = self._serialize(value)
            
            if ttl:
                await self.client.setex(cache_key, ttl, serialized)
            else:
                await self.client.set(cache_key, serialized)
            
            self.metrics.record_operation_time(time.time() - start_time)
            return True
            
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            self.metrics.record_error()
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.client:
            return False
        
        try:
            cache_key = self._generate_key(key)
            result = await self.client.delete(cache_key)
            return result > 0
            
        except Exception as e:
            logger.error("Cache delete error", key=key, error=str(e))
            self.metrics.record_error()
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.client:
            return False
        
        try:
            cache_key = self._generate_key(key)
            return bool(await self.client.exists(cache_key))
            
        except Exception as e:
            logger.error("Cache exists error", key=key, error=str(e))
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key"""
        if not self.client:
            return False
        
        try:
            cache_key = self._generate_key(key)
            return bool(await self.client.expire(cache_key, ttl))
            
        except Exception as e:
            logger.error("Cache expire error", key=key, error=str(e))
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment numeric value"""
        if not self.client:
            return 0
        
        try:
            cache_key = self._generate_key(key)
            return await self.client.incrby(cache_key, amount)
            
        except Exception as e:
            logger.error("Cache increment error", key=key, error=str(e))
            return 0
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values at once"""
        if not self.client or not keys:
            return {}
        
        try:
            cache_keys = [self._generate_key(key) for key in keys]
            values = await self.client.mget(cache_keys)
            
            result = {}
            for i, value in enumerate(values):
                if value is not None:
                    result[keys[i]] = self._deserialize(value)
                    self.metrics.record_hit()
                else:
                    self.metrics.record_miss()
            
            return result
            
        except Exception as e:
            logger.error("Cache get_many error", keys=keys, error=str(e))
            self.metrics.record_error()
            return {}
    
    async def set_many(self, mapping: Dict[str, Any], ttl: int = None) -> bool:
        """Set multiple values at once"""
        if not self.client or not mapping:
            return False
        
        try:
            # Prepare data for batch operation
            cache_mapping = {}
            for key, value in mapping.items():
                cache_key = self._generate_key(key)
                cache_mapping[cache_key] = self._serialize(value)
            
            # Use pipeline for batch operations
            pipe = self.client.pipeline()
            pipe.mset(cache_mapping)
            
            if ttl:
                for cache_key in cache_mapping.keys():
                    pipe.expire(cache_key, ttl)
            
            await pipe.execute()
            return True
            
        except Exception as e:
            logger.error("Cache set_many error", error=str(e))
            self.metrics.record_error()
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.client:
            return 0
        
        try:
            cache_pattern = self._generate_key(pattern)
            keys = await self.client.keys(cache_pattern)
            
            if keys:
                return await self.client.delete(*keys)
            return 0
            
        except Exception as e:
            logger.error("Cache clear_pattern error", pattern=pattern, error=str(e))
            self.metrics.record_error()
            return 0
    
    async def get_info(self) -> Dict[str, Any]:
        """Get Redis server information"""
        if not self.client:
            return {}
        
        try:
            info = await self.client.info()
            return {
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses")
            }
            
        except Exception as e:
            logger.error("Redis info error", error=str(e))
            return {}


class CacheMetrics:
    """Cache performance metrics collector"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.operation_times = []
    
    def record_hit(self):
        """Record cache hit"""
        self.hits += 1
    
    def record_miss(self):
        """Record cache miss"""
        self.misses += 1
    
    def record_error(self):
        """Record cache error"""
        self.errors += 1
    
    def record_operation_time(self, duration: float):
        """Record operation duration"""
        self.operation_times.append(duration)
        
        # Keep only last 1000 entries
        if len(self.operation_times) > 1000:
            self.operation_times = self.operation_times[-1000:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics summary"""
        total_operations = self.hits + self.misses
        hit_rate = self.hits / total_operations if total_operations > 0 else 0
        
        avg_time = (
            sum(self.operation_times) / len(self.operation_times)
            if self.operation_times else 0
        )
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "hit_rate": hit_rate,
            "total_operations": total_operations,
            "avg_operation_time": avg_time,
            "max_operation_time": max(self.operation_times) if self.operation_times else 0
        }


# Decorators for caching
def cached(ttl: int = 3600, key_prefix: str = "func"):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not redis_client:
                return await func(*args, **kwargs)
            
            # Generate cache key from function name and arguments
            key_data = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = f"{key_prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"
            
            # Try to get from cache
            cached_result = await redis_client.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await redis_client.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


def invalidate_cache(pattern: str):
    """Decorator to invalidate cache after function execution"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            if redis_client:
                await redis_client.clear_pattern(pattern)
            
            return result
        return wrapper
    return decorator


# Session management for Redis
class SessionManager:
    """Redis-based session management"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager
        self.session_prefix = "session"
    
    async def create_session(self, user_id: str, data: Dict[str, Any]) -> str:
        """Create new session"""
        session_id = hashlib.md5(f"{user_id}:{time.time()}".encode()).hexdigest()
        session_key = f"{self.session_prefix}:{session_id}"
        
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            **data
        }
        
        success = await self.redis.set(session_key, session_data, settings.REDIS_SESSION_TTL)
        return session_id if success else None
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        session_key = f"{self.session_prefix}:{session_id}"
        return await self.redis.get(session_key)
    
    async def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update session data"""
        session_key = f"{self.session_prefix}:{session_id}"
        existing_data = await self.redis.get(session_key) or {}
        
        updated_data = {
            **existing_data,
            **data,
            "last_activity": datetime.utcnow().isoformat()
        }
        
        return await self.redis.set(session_key, updated_data, settings.REDIS_SESSION_TTL)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        session_key = f"{self.session_prefix}:{session_id}"
        return await self.redis.delete(session_key)
    
    async def extend_session(self, session_id: str) -> bool:
        """Extend session TTL"""
        session_key = f"{self.session_prefix}:{session_id}"
        return await self.redis.expire(session_key, settings.REDIS_SESSION_TTL)


# Global instances
redis_manager = RedisManager()
redis_client = redis_manager
session_manager = SessionManager(redis_manager)


# Initialize Redis connection
async def init_redis():
    """Initialize global Redis connection"""
    await redis_manager.init_redis()


# Close Redis connection
async def close_redis():
    """Close global Redis connection"""
    await redis_manager.close()