#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Redis Caching Layer for IDF Testing Infrastructure
Optimized for Hebrew text and high-performance operations
"""

import asyncio
import json
import pickle
import hashlib
import time
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from functools import wraps
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import Redis
import structlog
from pydantic import BaseModel

from core.config import settings

logger = structlog.get_logger()


class CacheConfig:
    """Redis cache configuration"""
    
    # Cache TTL settings (in seconds)
    SHORT_TTL = 300      # 5 minutes
    MEDIUM_TTL = 1800    # 30 minutes
    LONG_TTL = 3600      # 1 hour
    VERY_LONG_TTL = 86400  # 24 hours
    
    # Cache key prefixes
    INSPECTION_PREFIX = "inspection:"
    BUILDING_PREFIX = "building:"
    SEARCH_PREFIX = "search:"
    STATS_PREFIX = "stats:"
    SESSION_PREFIX = "session:"
    
    # Cache sizes
    MAX_CACHE_SIZE = 1000
    BATCH_SIZE = 100


class CacheMetrics:
    """Cache performance metrics"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.total_requests = 0
        self.start_time = time.time()
    
    def record_hit(self):
        self.hits += 1
        self.total_requests += 1
    
    def record_miss(self):
        self.misses += 1
        self.total_requests += 1
    
    def record_error(self):
        self.errors += 1
    
    def get_hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests
    
    def get_stats(self) -> Dict[str, Any]:
        uptime = time.time() - self.start_time
        return {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "total_requests": self.total_requests,
            "hit_rate": self.get_hit_rate(),
            "uptime_seconds": uptime
        }


class HebrewTextProcessor:
    """Hebrew text processing utilities for caching"""
    
    @staticmethod
    def normalize_hebrew_text(text: str) -> str:
        """Normalize Hebrew text for consistent caching"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = " ".join(text.split())
        
        # Convert to lowercase (for non-Hebrew characters)
        # Hebrew characters don't have case distinction
        normalized = ""
        for char in text:
            if ord(char) >= 1488 and ord(char) <= 1514:  # Hebrew Unicode range
                normalized += char
            else:
                normalized += char.lower()
        
        return normalized
    
    @staticmethod
    def generate_search_key(query: str, filters: Dict[str, Any] = None) -> str:
        """Generate a consistent cache key for Hebrew search queries"""
        normalized_query = HebrewTextProcessor.normalize_hebrew_text(query)
        
        # Create a hash of the query and filters
        key_data = {
            "query": normalized_query,
            "filters": filters or {}
        }
        
        key_string = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        key_hash = hashlib.md5(key_string.encode('utf-8')).hexdigest()
        
        return f"{CacheConfig.SEARCH_PREFIX}{key_hash}"


class RedisCache:
    """High-performance Redis cache with Hebrew text support"""
    
    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.metrics = CacheMetrics()
        self.hebrew_processor = HebrewTextProcessor()
        self._connection_pool = None
    
    async def initialize(self) -> None:
        """Initialize Redis connection with optimized settings"""
        try:
            # Create connection pool for better performance
            self._connection_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                password=getattr(settings, 'REDIS_PASSWORD', None),
                ssl=getattr(settings, 'REDIS_SSL', False),
                max_connections=20,
                retry_on_timeout=True,
                health_check_interval=30,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 3,  # TCP_KEEPINTVL
                    3: 5,  # TCP_KEEPCNT
                }
            )
            
            self.redis_client = Redis(
                connection_pool=self._connection_pool,
                decode_responses=False,  # We handle encoding ourselves
                socket_timeout=5.0,
                socket_connect_timeout=5.0
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Redis cache", error=str(e))
            raise
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for Redis storage"""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps(value, ensure_ascii=False).encode('utf-8')
        elif isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False).encode('utf-8')
        else:
            return pickle.dumps(value)
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from Redis storage"""
        try:
            # Try JSON first (more common)
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(data)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            await self.initialize()
        
        try:
            data = await self.redis_client.get(key)
            if data is None:
                self.metrics.record_miss()
                return None
            
            self.metrics.record_hit()
            return self._deserialize_value(data)
            
        except Exception as e:
            self.metrics.record_error()
            logger.warning("Cache get failed", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: int = CacheConfig.MEDIUM_TTL) -> bool:
        """Set value in cache with TTL"""
        if not self.redis_client:
            await self.initialize()
        
        try:
            serialized_value = self._serialize_value(value)
            await self.redis_client.setex(key, ttl, serialized_value)
            return True
            
        except Exception as e:
            self.metrics.record_error()
            logger.warning("Cache set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            await self.initialize()
        
        try:
            result = await self.redis_client.delete(key)
            return result > 0
            
        except Exception as e:
            self.metrics.record_error()
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache"""
        if not self.redis_client or not keys:
            return {}
        
        try:
            pipeline = self.redis_client.pipeline()
            for key in keys:
                pipeline.get(key)
            
            results = await pipeline.execute()
            
            cache_data = {}
            for key, data in zip(keys, results):
                if data is not None:
                    try:
                        cache_data[key] = self._deserialize_value(data)
                        self.metrics.record_hit()
                    except Exception as e:
                        logger.warning("Failed to deserialize cached data", key=key, error=str(e))
                        self.metrics.record_error()
                else:
                    self.metrics.record_miss()
            
            return cache_data
            
        except Exception as e:
            self.metrics.record_error()
            logger.warning("Cache get_many failed", keys=keys, error=str(e))
            return {}
    
    async def set_many(self, data: Dict[str, Any], ttl: int = CacheConfig.MEDIUM_TTL) -> bool:
        """Set multiple values in cache"""
        if not self.redis_client or not data:
            return False
        
        try:
            pipeline = self.redis_client.pipeline()
            for key, value in data.items():
                serialized_value = self._serialize_value(value)
                pipeline.setex(key, ttl, serialized_value)
            
            await pipeline.execute()
            return True
            
        except Exception as e:
            self.metrics.record_error()
            logger.warning("Cache set_many failed", error=str(e))
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter in cache"""
        if not self.redis_client:
            await self.initialize()
        
        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            self.metrics.record_error()
            logger.warning("Cache increment failed", key=key, error=str(e))
            return 0
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key"""
        if not self.redis_client:
            await self.initialize()
        
        try:
            return await self.redis_client.expire(key, ttl)
        except Exception as e:
            self.metrics.record_error()
            logger.warning("Cache expire failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            await self.initialize()
        
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            self.metrics.record_error()
            logger.warning("Cache exists check failed", key=key, error=str(e))
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.redis_client:
            await self.initialize()
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            self.metrics.record_error()
            logger.warning("Cache clear_pattern failed", pattern=pattern, error=str(e))
            return 0
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """Get cache statistics and info"""
        if not self.redis_client:
            return {"status": "disconnected"}
        
        try:
            info = await self.redis_client.info()
            return {
                "status": "connected",
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "metrics": self.metrics.get_stats()
            }
        except Exception as e:
            self.metrics.record_error()
            logger.warning("Failed to get cache info", error=str(e))
            return {"status": "error", "error": str(e)}


def cache_key_for_inspection(inspection_id: int) -> str:
    """Generate cache key for inspection"""
    return f"{CacheConfig.INSPECTION_PREFIX}{inspection_id}"


def cache_key_for_building(building_code: str) -> str:
    """Generate cache key for building"""
    return f"{CacheConfig.BUILDING_PREFIX}{building_code}"


def cache_key_for_search(query: str, filters: Dict[str, Any] = None) -> str:
    """Generate cache key for search results"""
    return HebrewTextProcessor.generate_search_key(query, filters)


def cached(ttl: int = CacheConfig.MEDIUM_TTL, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = {
                "function": func.__name__,
                "args": str(args),
                "kwargs": str(kwargs)
            }
            key_string = json.dumps(key_data, sort_keys=True)
            key_hash = hashlib.md5(key_string.encode('utf-8')).hexdigest()
            cache_key = f"{key_prefix}{func.__name__}:{key_hash}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


# Global cache instance
cache = RedisCache()


@asynccontextmanager
async def cache_context():
    """Context manager for cache operations"""
    try:
        if not cache.redis_client:
            await cache.initialize()
        yield cache
    finally:
        # Don't close connection here as it's shared
        pass


# Cache warming utilities
async def warm_inspection_cache():
    """Pre-warm cache with frequently accessed inspection data"""
    try:
        from models.core import Inspection
        from core.database import get_db_session
        
        async with get_db_session() as session:
            # Get recent inspections
            recent_inspections = await session.execute(
                f"""
                SELECT id, building_id, inspection_type, status
                FROM inspections 
                WHERE created_at > NOW() - INTERVAL '7 days'
                ORDER BY created_at DESC
                LIMIT 100
                """
            )
            
            cache_data = {}
            for inspection in recent_inspections:
                key = cache_key_for_inspection(inspection.id)
                cache_data[key] = dict(inspection)
            
            if cache_data:
                await cache.set_many(cache_data, CacheConfig.LONG_TTL)
                logger.info(f"Warmed cache with {len(cache_data)} inspections")
    
    except Exception as e:
        logger.warning("Failed to warm inspection cache", error=str(e))


async def warm_building_cache():
    """Pre-warm cache with building data"""
    try:
        from models.core import Building
        from core.database import get_db_session
        
        async with get_db_session() as session:
            buildings = await session.execute(
                "SELECT building_code, building_name, manager_name FROM buildings WHERE is_active = true"
            )
            
            cache_data = {}
            for building in buildings:
                key = cache_key_for_building(building.building_code)
                cache_data[key] = dict(building)
            
            if cache_data:
                await cache.set_many(cache_data, CacheConfig.VERY_LONG_TTL)
                logger.info(f"Warmed cache with {len(cache_data)} buildings")
    
    except Exception as e:
        logger.warning("Failed to warm building cache", error=str(e))


async def initialize_cache():
    """Initialize cache and warm it up"""
    await cache.initialize()
    
    # Warm up cache in background
    asyncio.create_task(warm_inspection_cache())
    asyncio.create_task(warm_building_cache())


async def cleanup_cache():
    """Clean up cache resources"""
    await cache.close()