#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDF Testing Infrastructure - Test Configuration
Comprehensive test setup with performance benchmarking
"""

import pytest
import asyncio
import os
import tempfile
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool
import redis
from unittest.mock import AsyncMock, MagicMock

# Test environment setup
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["SECRET_KEY"] = "test_secret_key_for_testing_only_32_chars"

from app.main import app
from app.core.database import Base, get_db
from app.core.redis_client import redis_manager
from app.core.config import TestSettings


# Test settings
test_settings = TestSettings()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine with in-memory SQLite"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        }
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with database override"""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def redis_client():
    """Create test Redis client"""
    try:
        client = redis.Redis(
            host='localhost',
            port=6379,
            db=1,  # Use test database
            decode_responses=True
        )
        
        # Test connection
        client.ping()
        
        # Clear test database
        client.flushdb()
        
        yield client
        
        # Cleanup
        client.flushdb()
        client.close()
        
    except redis.ConnectionError:
        # If Redis is not available, use mock
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.flushdb.return_value = True
        yield mock_redis


@pytest.fixture
def temp_file():
    """Create temporary file for testing file uploads"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp:
        yield temp.name
    
    # Cleanup
    if os.path.exists(temp.name):
        os.unlink(temp.name)


@pytest.fixture
def sample_hebrew_data():
    """Sample Hebrew data for testing"""
    return {
        "test_data": [
            {
                "id": 1,
                "name": "בדיקת מערכת תקשורת",
                "description": "בדיקה מקיפה של מערכת התקשורת הצבאית",
                "status": "active",
                "category": "תקשורת"
            },
            {
                "id": 2,
                "name": "בדיקת רדיו VHF",
                "description": "בדיקת תדרי VHF במערכת הרדיו",
                "status": "pending",
                "category": "רדיו"
            },
            {
                "id": 3,
                "name": "בדיקת הצפנה",
                "description": "בדיקת מערכות ההצפנה והאבטחה",
                "status": "completed",
                "category": "אבטחה"
            }
        ],
        "lookup_values": [
            {"key": "status_active", "value": "פעיל"},
            {"key": "status_pending", "value": "ממתין"},
            {"key": "status_completed", "value": "הושלם"},
            {"key": "category_communication", "value": "תקשורת"},
            {"key": "category_radio", "value": "רדיו"},
            {"key": "category_security", "value": "אבטחה"}
        ]
    }


@pytest.fixture
def performance_timer():
    """Performance timing fixture"""
    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.duration = None
        
        def start(self):
            import time
            self.start_time = time.perf_counter()
        
        def stop(self):
            import time
            self.end_time = time.perf_counter()
            self.duration = self.end_time - self.start_time
            return self.duration
        
        def assert_faster_than(self, max_seconds: float):
            """Assert that operation completed within time limit"""
            assert self.duration is not None, "Timer was not stopped"
            assert self.duration < max_seconds, f"Operation took {self.duration:.3f}s, expected < {max_seconds}s"
    
    return PerformanceTimer()


@pytest.fixture
def memory_profiler():
    """Memory usage profiler"""
    try:
        import psutil
        import os
        
        class MemoryProfiler:
            def __init__(self):
                self.process = psutil.Process(os.getpid())
                self.initial_memory = None
                self.peak_memory = None
            
            def start(self):
                self.initial_memory = self.process.memory_info().rss
            
            def check_peak(self):
                current = self.process.memory_info().rss
                if self.peak_memory is None or current > self.peak_memory:
                    self.peak_memory = current
            
            def get_usage_mb(self):
                if self.initial_memory is None:
                    return 0
                current = self.process.memory_info().rss
                return (current - self.initial_memory) / 1024 / 1024
            
            def assert_memory_under(self, max_mb: float):
                """Assert memory usage is under limit"""
                usage = self.get_usage_mb()
                assert usage < max_mb, f"Memory usage {usage:.1f}MB exceeds limit of {max_mb}MB"
        
        return MemoryProfiler()
        
    except ImportError:
        # If psutil is not available, return mock
        class MockMemoryProfiler:
            def start(self): pass
            def check_peak(self): pass
            def get_usage_mb(self): return 0
            def assert_memory_under(self, max_mb): pass
        
        return MockMemoryProfiler()


# Benchmark fixtures
@pytest.fixture
def benchmark_config():
    """Configuration for performance benchmarks"""
    return {
        "max_response_time": 2.0,  # seconds
        "max_memory_usage": 50.0,  # MB
        "max_db_query_time": 0.1,  # seconds
        "max_cache_operation_time": 0.01,  # seconds
        "concurrent_requests": 50,
        "load_test_duration": 10  # seconds
    }


# Hebrew text processing fixtures
@pytest.fixture
def hebrew_text_samples():
    """Sample Hebrew text for RTL testing"""
    return {
        "simple": "שלום עולם",
        "mixed": "Hello שלום World עולם",
        "numbers": "בדיקה 123 מספרים",
        "punctuation": "שלום, עולם! איך הולך?",
        "long_text": (
            "זהו טקסט ארוך בעברית לבדיקת ביצועים. "
            "הטקסט כולל מילים רבות ומשפטים מורכבים "
            "כדי לוודא שהמערכת מטפלת נכון בעברית. "
            "בדיקה זו חשובה לוודא שהמערכת פועלת בצורה אופטימלית."
        ),
        "rtl_ltr_mixed": (
            "This is English followed by עברית and then English again. "
            "המערכת צריכה לטפל נכון ב-RTL ו-LTR טקסט mixed together."
        )
    }


# Database test data fixtures
@pytest.fixture
async def test_data_bulk(db_session, sample_hebrew_data):
    """Create bulk test data for performance testing"""
    # This would be implemented when models are created
    # For now, return sample data structure
    return sample_hebrew_data


# Load testing fixtures
@pytest.fixture
def load_test_config():
    """Load testing configuration"""
    return {
        "users": 10,
        "spawn_rate": 2,
        "duration": "30s",
        "host": "http://localhost:8000"
    }


# Monitoring fixtures
@pytest.fixture
def metrics_collector():
    """Metrics collection for test analysis"""
    class MetricsCollector:
        def __init__(self):
            self.metrics = {
                "response_times": [],
                "memory_usage": [],
                "cache_hits": 0,
                "cache_misses": 0,
                "db_queries": 0,
                "errors": 0
            }
        
        def record_response_time(self, duration: float):
            self.metrics["response_times"].append(duration)
        
        def record_memory_usage(self, usage_mb: float):
            self.metrics["memory_usage"].append(usage_mb)
        
        def record_cache_hit(self):
            self.metrics["cache_hits"] += 1
        
        def record_cache_miss(self):
            self.metrics["cache_misses"] += 1
        
        def record_db_query(self):
            self.metrics["db_queries"] += 1
        
        def record_error(self):
            self.metrics["errors"] += 1
        
        def get_summary(self):
            response_times = self.metrics["response_times"]
            return {
                "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
                "max_response_time": max(response_times) if response_times else 0,
                "min_response_time": min(response_times) if response_times else 0,
                "cache_hit_rate": (
                    self.metrics["cache_hits"] / 
                    (self.metrics["cache_hits"] + self.metrics["cache_misses"])
                    if (self.metrics["cache_hits"] + self.metrics["cache_misses"]) > 0 else 0
                ),
                "total_db_queries": self.metrics["db_queries"],
                "total_errors": self.metrics["errors"]
            }
    
    return MetricsCollector()


# Pytest marks for test categorization
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "load: Load tests")
    config.addinivalue_line("markers", "hebrew: Hebrew/RTL specific tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


# Test database cleanup
@pytest.fixture(autouse=True)
async def cleanup_test_db(db_session):
    """Automatically cleanup test database after each test"""
    yield
    await db_session.rollback()


# Performance test setup
@pytest.fixture
def performance_test_setup():
    """Setup for performance testing"""
    class PerformanceTestSetup:
        def __init__(self):
            self.start_time = None
            self.metrics = {}
        
        def start_monitoring(self):
            import time
            self.start_time = time.perf_counter()
        
        def stop_monitoring(self):
            import time
            if self.start_time:
                duration = time.perf_counter() - self.start_time
                self.metrics['duration'] = duration
                return duration
            return 0
        
        def assert_performance_target(self, target_seconds: float):
            """Assert performance meets target"""
            duration = self.metrics.get('duration', 0)
            assert duration < target_seconds, f"Performance target missed: {duration:.3f}s > {target_seconds}s"
    
    return PerformanceTestSetup()