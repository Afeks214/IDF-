#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDF Testing Infrastructure - Advanced Caching Strategies
Multi-tier caching with intelligent invalidation and Hebrew optimization
"""

import asyncio
import json
import hashlib
import time
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import structlog
from functools import wraps

from core.redis_client import redis_client
from core.config import settings

logger = structlog.get_logger()


class CacheLevel(Enum):
    """Cache level enumeration"""
    L1_MEMORY = "l1_memory"      # In-process memory cache
    L2_REDIS = "l2_redis"        # Redis cache
    L3_DATABASE = "l3_database"   # Database query cache


class CacheStrategy(Enum):
    """Cache strategy enumeration"""
    WRITE_THROUGH = "write_through"       # Write to cache and storage simultaneously
    WRITE_BEHIND = "write_behind"         # Write to cache immediately, storage later
    WRITE_AROUND = "write_around"         # Write to storage, bypass cache
    CACHE_ASIDE = "cache_aside"           # Application manages cache


@dataclass
class CacheConfig:
    """Cache configuration"""
    ttl: int = 3600                       # Time to live in seconds
    max_size: int = 10000                 # Maximum cache size
    strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE
    levels: List[CacheLevel] = None       # Cache levels to use
    compression: bool = False             # Enable compression
    encryption: bool = False              # Enable encryption
    namespace: str = "default"            # Cache namespace
    hebrew_optimized: bool = True         # Hebrew text optimization


class InMemoryCache:
    """High-performance in-memory cache with LRU eviction"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.access_times = {}
        self.creation_times = {}
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self.creation_times:
            return True
        
        age = time.time() - self.creation_times[key]
        return age > self.ttl
    
    def _evict_lru(self):
        """Evict least recently used item"""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self._remove(lru_key)
    
    def _remove(self, key: str):
        """Remove item from cache"""
        self.cache.pop(key, None)
        self.access_times.pop(key, None)
        self.creation_times.pop(key, None)
    
    def get(self, key: str) -> Any:
        """Get item from cache"""
        if key not in self.cache:
            return None
        
        if self._is_expired(key):
            self._remove(key)
            return None
        
        # Update access time
        self.access_times[key] = time.time()
        return self.cache[key]
    
    def set(self, key: str, value: Any):
        """Set item in cache"""
        current_time = time.time()
        
        # Remove expired entries
        expired_keys = [k for k in self.cache.keys() if self._is_expired(k)]
        for expired_key in expired_keys:
            self._remove(expired_key)
        
        # Evict if at capacity
        while len(self.cache) >= self.max_size:
            self._evict_lru()
        
        # Add new item
        self.cache[key] = value
        self.access_times[key] = current_time
        self.creation_times[key] = current_time
    
    def delete(self, key: str) -> bool:
        """Delete item from cache"""
        if key in self.cache:
            self._remove(key)
            return True
        return False
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.access_times.clear()
        self.creation_times.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)
    
    def stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "hit_rate": getattr(self, "_hit_rate", 0.0)
        }


class MultiTierCache:
    """Multi-tier caching system with L1 (memory) and L2 (Redis) layers"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.l1_cache = InMemoryCache(
            max_size=min(config.max_size // 10, 1000),  # 10% of total for L1
            ttl=min(config.ttl // 4, 300)               # 25% TTL for L1
        )
        self.metrics = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "total_requests": 0
        }
    
    def _generate_key(self, key: str) -> str:
        """Generate namespaced cache key"""
        namespace = self.config.namespace
        return f"{namespace}:{key}"
    
    def _optimize_hebrew_data(self, data: Any) -> Any:
        """Optimize Hebrew data for caching"""
        if not self.config.hebrew_optimized:
            return data
        
        if isinstance(data, str):
            # Normalize Hebrew text
            import unicodedata
            normalized = unicodedata.normalize('NFKC', data)
            return normalized
        elif isinstance(data, dict):
            # Recursively optimize dictionary values
            return {k: self._optimize_hebrew_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            # Recursively optimize list items
            return [self._optimize_hebrew_data(item) for item in data]
        
        return data
    
    async def get(self, key: str) -> Any:
        """Get from multi-tier cache"""
        self.metrics["total_requests"] += 1
        cache_key = self._generate_key(key)
        
        # Try L1 cache first
        value = self.l1_cache.get(cache_key)
        if value is not None:
            self.metrics["l1_hits"] += 1
            return value
        
        self.metrics["l1_misses"] += 1
        
        # Try L2 cache (Redis)
        if redis_client:
            value = await redis_client.get(cache_key)
            if value is not None:
                self.metrics["l2_hits"] += 1
                
                # Promote to L1 cache
                self.l1_cache.set(cache_key, value)
                return value
        
        self.metrics["l2_misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set in multi-tier cache"""
        cache_key = self._generate_key(key)
        cache_ttl = ttl or self.config.ttl
        
        # Optimize Hebrew data
        optimized_value = self._optimize_hebrew_data(value)
        
        # Set in L1 cache
        self.l1_cache.set(cache_key, optimized_value)
        
        # Set in L2 cache (Redis)
        if redis_client:
            success = await redis_client.set(cache_key, optimized_value, cache_ttl)
            return success
        
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete from multi-tier cache"""
        cache_key = self._generate_key(key)
        
        # Delete from L1
        l1_deleted = self.l1_cache.delete(cache_key)
        
        # Delete from L2
        l2_deleted = False
        if redis_client:
            l2_deleted = await redis_client.delete(cache_key)
        
        return l1_deleted or l2_deleted
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear cache entries matching pattern"""
        # Clear L1 cache (simple approach - clear all)
        self.l1_cache.clear()
        
        # Clear L2 cache pattern
        if redis_client:
            return await redis_client.clear_pattern(f"{self.config.namespace}:{pattern}")
        
        return 0
    
    def get_metrics(self) -> Dict:
        """Get cache performance metrics"""
        total_requests = self.metrics["total_requests"]
        if total_requests == 0:
            return {"status": "no_requests"}
        
        l1_hit_rate = self.metrics["l1_hits"] / total_requests
        l2_hit_rate = self.metrics["l2_hits"] / total_requests
        overall_hit_rate = (self.metrics["l1_hits"] + self.metrics["l2_hits"]) / total_requests
        
        return {
            "l1_hit_rate": l1_hit_rate,
            "l2_hit_rate": l2_hit_rate,
            "overall_hit_rate": overall_hit_rate,
            "l1_size": self.l1_cache.size(),
            "total_requests": total_requests,
            **self.metrics
        }


class HebrewTextCache:
    """Specialized cache for Hebrew text processing"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache = MultiTierCache(config)
        self.rtl_cache = {}  # RTL processing cache
        self.normalization_cache = {}  # Unicode normalization cache
    
    def _normalize_hebrew_text(self, text: str) -> str:
        """Normalize Hebrew text for consistent caching"""
        if text in self.normalization_cache:
            return self.normalization_cache[text]
        
        import unicodedata
        
        # Normalize Unicode
        normalized = unicodedata.normalize('NFKC', text)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        # Cache normalization result
        if len(self.normalization_cache) < 10000:  # Limit cache size
            self.normalization_cache[text] = normalized
        
        return normalized
    
    def _generate_text_key(self, text: str, operation: str) -> str:
        """Generate cache key for text operations"""
        normalized_text = self._normalize_hebrew_text(text)
        text_hash = hashlib.md5(normalized_text.encode('utf-8')).hexdigest()
        return f"hebrew:{operation}:{text_hash}"
    
    async def cache_rtl_processing(self, text: str, processed_result: str):
        """Cache RTL processing result"""
        key = self._generate_text_key(text, "rtl")
        await self.cache.set(key, processed_result, ttl=86400)  # 24 hours
    
    async def get_rtl_processing(self, text: str) -> Optional[str]:
        """Get cached RTL processing result"""
        key = self._generate_text_key(text, "rtl")
        return await self.cache.get(key)
    
    async def cache_search_result(self, query: str, results: List[Dict]):
        """Cache search results"""
        key = self._generate_text_key(query, "search")
        await self.cache.set(key, results, ttl=1800)  # 30 minutes
    
    async def get_search_result(self, query: str) -> Optional[List[Dict]]:
        """Get cached search results"""
        key = self._generate_text_key(query, "search")
        return await self.cache.get(key)
    
    async def cache_translation(self, text: str, target_lang: str, translation: str):
        """Cache translation result"""
        key = self._generate_text_key(f"{text}:{target_lang}", "translation")
        await self.cache.set(key, translation, ttl=604800)  # 7 days
    
    async def get_translation(self, text: str, target_lang: str) -> Optional[str]:
        """Get cached translation"""
        key = self._generate_text_key(f"{text}:{target_lang}", "translation")
        return await self.cache.get(key)


class SmartCacheInvalidation:
    """Intelligent cache invalidation based on data dependencies"""
    
    def __init__(self):
        self.dependencies = {}  # key -> set of dependent keys
        self.tags = {}         # tag -> set of keys
        self.watchers = {}     # pattern -> callback functions
    
    def add_dependency(self, parent_key: str, dependent_key: str):
        """Add cache dependency relationship"""
        if parent_key not in self.dependencies:
            self.dependencies[parent_key] = set()
        self.dependencies[parent_key].add(dependent_key)
    
    def tag_key(self, key: str, tag: str):
        """Tag a cache key for group invalidation"""
        if tag not in self.tags:
            self.tags[tag] = set()
        self.tags[tag].add(key)
    
    def add_watcher(self, pattern: str, callback: Callable):
        """Add watcher for cache key pattern"""
        if pattern not in self.watchers:
            self.watchers[pattern] = []
        self.watchers[pattern].append(callback)
    
    async def invalidate_key(self, key: str, cache: MultiTierCache):
        """Invalidate key and its dependencies"""
        # Invalidate the key itself
        await cache.delete(key)
        
        # Invalidate dependent keys
        if key in self.dependencies:
            for dependent_key in self.dependencies[key]:
                await cache.delete(dependent_key)
        
        # Trigger watchers
        for pattern, callbacks in self.watchers.items():
            if self._matches_pattern(key, pattern):
                for callback in callbacks:
                    try:
                        await callback(key)
                    except Exception as e:
                        logger.error(f"Cache watcher error: {e}")
    
    async def invalidate_tag(self, tag: str, cache: MultiTierCache):
        """Invalidate all keys with specific tag"""
        if tag in self.tags:
            for key in self.tags[tag]:
                await cache.delete(key)
            # Clear the tag
            del self.tags[tag]
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern"""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)


class CacheWarmup:
    """Cache warming strategies for improved performance"""
    
    def __init__(self, cache: MultiTierCache):
        self.cache = cache
        self.warmup_tasks = []
    
    async def warmup_common_queries(self, queries: List[str]):
        """Warm up cache with common queries"""
        logger.info(f"Warming up cache with {len(queries)} common queries")
        
        for query in queries:
            try:
                # This would execute the query and cache the result
                # Implementation depends on actual business logic
                key = f"common_query:{hashlib.md5(query.encode()).hexdigest()}"
                # await self.cache.set(key, query_result)
                pass
            except Exception as e:
                logger.error(f"Error warming up query '{query}': {e}")
    
    async def warmup_hebrew_processing(self, sample_texts: List[str]):
        """Warm up Hebrew text processing cache"""
        logger.info(f"Warming up Hebrew processing cache with {len(sample_texts)} texts")
        
        hebrew_cache = HebrewTextCache(self.cache.config)
        
        for text in sample_texts:
            try:
                # Pre-process common Hebrew operations
                normalized = text.strip()
                key = f"hebrew_normalized:{hashlib.md5(text.encode()).hexdigest()}"
                await self.cache.set(key, normalized)
            except Exception as e:
                logger.error(f"Error warming up Hebrew text: {e}")
    
    async def scheduled_warmup(self, interval_seconds: int = 3600):
        """Run scheduled cache warmup"""
        while True:
            try:
                # Implement scheduled warmup logic
                logger.info("Running scheduled cache warmup")
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduled warmup error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry


# Decorators for cache management
def cached_result(cache_config: CacheConfig, key_generator: Callable = None):
    """Decorator for caching function results"""
    def decorator(func):
        cache = MultiTierCache(cache_config)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_generator:
                key = key_generator(*args, **kwargs)
            else:
                args_str = str(args) + str(kwargs)
                key = f"{func.__name__}:{hashlib.md5(args_str.encode()).hexdigest()}"
            
            # Try cache first
            cached_value = await cache.get(key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache.set(key, result)
            
            return result
        
        return wrapper
    return decorator


def invalidate_on_change(cache: MultiTierCache, patterns: List[str]):
    """Decorator to invalidate cache on data changes"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Invalidate matching cache patterns
            for pattern in patterns:
                await cache.clear_pattern(pattern)
            
            return result
        
        return wrapper
    return decorator


# Global cache instances
default_cache_config = CacheConfig(
    ttl=3600,
    max_size=10000,
    namespace="idf_default",
    hebrew_optimized=True
)

# Initialize global caches
multi_tier_cache = MultiTierCache(default_cache_config)
hebrew_text_cache = HebrewTextCache(default_cache_config)
cache_invalidation = SmartCacheInvalidation()
cache_warmup = CacheWarmup(multi_tier_cache)


async def initialize_caching_system():
    """Initialize the caching system"""
    logger.info("Initializing advanced caching system")
    
    # Setup cache dependencies
    cache_invalidation.add_dependency("user_data", "user_sessions")
    cache_invalidation.add_dependency("test_data", "test_results")
    
    # Setup tags
    cache_invalidation.tag_key("hebrew_rtl_processing", "hebrew")
    cache_invalidation.tag_key("search_results", "search")
    
    # Start cache warmup if needed
    if settings.CACHE_ENABLED:
        # asyncio.create_task(cache_warmup.scheduled_warmup())
        pass
    
    logger.info("Advanced caching system initialized")