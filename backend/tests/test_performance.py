#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDF Testing Infrastructure - Performance Tests
Comprehensive performance testing suite with benchmarks
"""

import pytest
import asyncio
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor
import statistics

from httpx import AsyncClient


@pytest.mark.performance
class TestAPIPerformance:
    """API performance tests"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_performance(self, test_client: AsyncClient, performance_timer):
        """Test health endpoint response time"""
        performance_timer.start()
        
        response = await test_client.get("/health")
        
        duration = performance_timer.stop()
        
        assert response.status_code == 200
        performance_timer.assert_faster_than(0.1)  # 100ms max
    
    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, test_client: AsyncClient, benchmark_config):
        """Test concurrent health check performance"""
        concurrent_requests = benchmark_config["concurrent_requests"]
        
        async def make_request():
            start_time = time.perf_counter()
            response = await test_client.get("/health")
            end_time = time.perf_counter()
            
            return {
                "status_code": response.status_code,
                "duration": end_time - start_time
            }
        
        # Run concurrent requests
        start_time = time.perf_counter()
        tasks = [make_request() for _ in range(concurrent_requests)]
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time
        
        # Analyze results
        durations = [r["duration"] for r in results]
        success_count = sum(1 for r in results if r["status_code"] == 200)
        
        # Assertions
        assert success_count == concurrent_requests, "Some requests failed"
        assert total_time < 5.0, f"Concurrent requests took too long: {total_time:.2f}s"
        assert statistics.mean(durations) < 0.5, "Average response time too high"
        assert max(durations) < 2.0, "Maximum response time too high"
    
    @pytest.mark.asyncio
    async def test_api_under_load(self, test_client: AsyncClient, benchmark_config):
        """Test API performance under sustained load"""
        duration = benchmark_config["load_test_duration"]
        concurrent_users = 20
        
        async def sustained_load():
            """Simulate sustained user activity"""
            start_time = time.time()
            request_count = 0
            errors = 0
            
            while time.time() - start_time < duration:
                try:
                    response = await test_client.get("/health")
                    if response.status_code != 200:
                        errors += 1
                    request_count += 1
                    await asyncio.sleep(0.1)  # 10 RPS per user
                except Exception:
                    errors += 1
            
            return {"requests": request_count, "errors": errors}
        
        # Run load test
        tasks = [sustained_load() for _ in range(concurrent_users)]
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        total_requests = sum(r["requests"] for r in results)
        total_errors = sum(r["errors"] for r in results)
        error_rate = total_errors / total_requests if total_requests > 0 else 0
        
        # Assertions
        assert error_rate < 0.05, f"Error rate too high: {error_rate:.2%}"
        assert total_requests > duration * concurrent_users * 5, "Request rate too low"


@pytest.mark.performance
class TestDatabasePerformance:
    """Database performance tests"""
    
    @pytest.mark.asyncio
    async def test_connection_pool_performance(self, db_session):
        """Test database connection pool performance"""
        start_time = time.perf_counter()
        
        # Simulate multiple quick queries
        for _ in range(100):
            await db_session.execute("SELECT 1")
        
        duration = time.perf_counter() - start_time
        
        # Should complete 100 simple queries quickly
        assert duration < 1.0, f"Connection pool performance poor: {duration:.3f}s"
    
    @pytest.mark.asyncio
    async def test_bulk_operations_performance(self, db_session, performance_timer):
        """Test bulk database operations performance"""
        # This test will be expanded when models are implemented
        performance_timer.start()
        
        # Simulate bulk operations
        queries = ["SELECT 1" for _ in range(1000)]
        for query in queries:
            await db_session.execute(query)
        
        duration = performance_timer.stop()
        
        # Should handle 1000 queries reasonably fast
        performance_timer.assert_faster_than(5.0)


@pytest.mark.performance
class TestCachePerformance:
    """Cache performance tests"""
    
    @pytest.mark.asyncio
    async def test_redis_operation_performance(self, redis_client):
        """Test Redis operation performance"""
        
        # Test SET operations
        start_time = time.perf_counter()
        for i in range(1000):
            redis_client.set(f"test_key_{i}", f"test_value_{i}")
        set_duration = time.perf_counter() - start_time
        
        # Test GET operations
        start_time = time.perf_counter()
        for i in range(1000):
            redis_client.get(f"test_key_{i}")
        get_duration = time.perf_counter() - start_time
        
        # Performance assertions
        assert set_duration < 1.0, f"SET operations too slow: {set_duration:.3f}s"
        assert get_duration < 0.5, f"GET operations too slow: {get_duration:.3f}s"
        
        # Cleanup
        for i in range(1000):
            redis_client.delete(f"test_key_{i}")
    
    @pytest.mark.asyncio
    async def test_cache_hit_ratio(self, redis_client):
        """Test cache hit ratio performance"""
        # Populate cache
        test_data = {f"key_{i}": f"value_{i}" for i in range(100)}
        for key, value in test_data.items():
            redis_client.set(key, value)
        
        # Test cache hits
        hits = 0
        misses = 0
        
        for i in range(200):  # 100 hits, 100 misses expected
            key = f"key_{i}"
            result = redis_client.get(key)
            if result is not None:
                hits += 1
            else:
                misses += 1
        
        hit_ratio = hits / (hits + misses)
        assert hit_ratio == 0.5, f"Unexpected hit ratio: {hit_ratio:.2%}"
        
        # Cleanup
        for key in test_data.keys():
            redis_client.delete(key)


@pytest.mark.performance
@pytest.mark.hebrew
class TestHebrewTextPerformance:
    """Hebrew text processing performance tests"""
    
    def test_hebrew_text_processing_speed(self, hebrew_text_samples, performance_timer):
        """Test Hebrew text processing performance"""
        long_text = hebrew_text_samples["long_text"]
        
        performance_timer.start()
        
        # Simulate text processing operations
        for _ in range(1000):
            # Basic string operations
            processed = long_text.strip()
            processed = processed.replace(" ", "_")
            processed = processed.upper()
            words = processed.split("_")
            result = "_".join(words)
        
        duration = performance_timer.stop()
        
        # Should process Hebrew text efficiently
        performance_timer.assert_faster_than(0.5)
    
    def test_rtl_text_rendering_performance(self, hebrew_text_samples, performance_timer):
        """Test RTL text rendering performance"""
        mixed_text = hebrew_text_samples["rtl_ltr_mixed"]
        
        performance_timer.start()
        
        # Simulate RTL processing
        for _ in range(500):
            # Basic RTL detection and processing
            has_hebrew = any('\u0590' <= char <= '\u05FF' for char in mixed_text)
            if has_hebrew:
                # Simulate RTL wrapper addition
                processed = f'<div dir="rtl">{mixed_text}</div>'
            else:
                processed = mixed_text
        
        duration = performance_timer.stop()
        
        # Should handle RTL processing efficiently
        performance_timer.assert_faster_than(0.3)


@pytest.mark.performance
class TestMemoryPerformance:
    """Memory usage performance tests"""
    
    def test_memory_usage_under_load(self, memory_profiler, sample_hebrew_data):
        """Test memory usage during data processing"""
        memory_profiler.start()
        
        # Simulate heavy data processing
        large_dataset = []
        for i in range(10000):
            data_copy = sample_hebrew_data.copy()
            data_copy["id"] = i
            large_dataset.append(data_copy)
            
            # Check memory periodically
            if i % 1000 == 0:
                memory_profiler.check_peak()
        
        # Memory should stay reasonable
        memory_profiler.assert_memory_under(100.0)  # 100MB limit
    
    def test_memory_leak_detection(self, memory_profiler):
        """Test for memory leaks in repeated operations"""
        memory_profiler.start()
        
        # Simulate repeated operations that might leak
        for cycle in range(10):
            # Create and destroy objects
            temp_objects = []
            for i in range(1000):
                temp_objects.append({"data": f"test_{i}" * 100})
            
            # Clear objects
            temp_objects.clear()
            
            # Check memory after each cycle
            memory_profiler.check_peak()
        
        # Memory usage should be reasonable
        memory_profiler.assert_memory_under(50.0)


@pytest.mark.performance
class TestConcurrencyPerformance:
    """Concurrency performance tests"""
    
    @pytest.mark.asyncio
    async def test_async_operation_performance(self, performance_timer):
        """Test async operation performance"""
        performance_timer.start()
        
        async def async_task(task_id: int):
            # Simulate async work
            await asyncio.sleep(0.01)
            return f"Task {task_id} completed"
        
        # Run many concurrent tasks
        tasks = [async_task(i) for i in range(100)]
        results = await asyncio.gather(*tasks)
        
        duration = performance_timer.stop()
        
        assert len(results) == 100
        # Should complete concurrent tasks efficiently
        performance_timer.assert_faster_than(2.0)
    
    @pytest.mark.asyncio
    async def test_thread_pool_performance(self, performance_timer):
        """Test thread pool performance for CPU-bound tasks"""
        performance_timer.start()
        
        def cpu_bound_task(n: int):
            # Simulate CPU-bound work
            total = sum(i * i for i in range(n))
            return total
        
        # Use thread pool for CPU-bound tasks
        with ThreadPoolExecutor(max_workers=4) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, cpu_bound_task, 1000)
                for _ in range(20)
            ]
            results = await asyncio.gather(*tasks)
        
        duration = performance_timer.stop()
        
        assert len(results) == 20
        # Should handle CPU-bound tasks efficiently
        performance_timer.assert_faster_than(3.0)


@pytest.mark.performance
class TestPerformanceRegression:
    """Performance regression tests"""
    
    @pytest.mark.asyncio
    async def test_response_time_regression(self, test_client: AsyncClient, metrics_collector):
        """Test for response time regression"""
        # Run baseline performance test
        for _ in range(50):
            start_time = time.perf_counter()
            response = await test_client.get("/health")
            duration = time.perf_counter() - start_time
            
            assert response.status_code == 200
            metrics_collector.record_response_time(duration)
        
        # Analyze performance metrics
        summary = metrics_collector.get_summary()
        
        # Performance thresholds (adjust based on requirements)
        assert summary["avg_response_time"] < 0.1, "Average response time regression"
        assert summary["max_response_time"] < 0.5, "Maximum response time regression"
    
    def test_memory_usage_regression(self, memory_profiler, sample_hebrew_data):
        """Test for memory usage regression"""
        memory_profiler.start()
        
        # Simulate typical application workload
        for _ in range(100):
            # Process Hebrew data
            data = sample_hebrew_data.copy()
            
            # Simulate data transformations
            for item in data["test_data"]:
                processed = {
                    "name": item["name"].upper(),
                    "description": item["description"].strip(),
                    "status": item["status"],
                    "category": item["category"]
                }
            
            memory_profiler.check_peak()
        
        # Check for memory regression
        memory_profiler.assert_memory_under(25.0)  # Baseline memory limit


@pytest.mark.performance
@pytest.mark.slow
class TestLoadPerformance:
    """Load testing performance tests"""
    
    @pytest.mark.asyncio
    async def test_sustained_load_performance(self, test_client: AsyncClient, load_test_config):
        """Test performance under sustained load"""
        
        async def user_simulation():
            """Simulate user behavior"""
            session_requests = 0
            session_errors = 0
            
            for _ in range(30):  # 30 requests per user session
                try:
                    response = await test_client.get("/health")
                    if response.status_code == 200:
                        session_requests += 1
                    else:
                        session_errors += 1
                    
                    await asyncio.sleep(0.1)  # Think time
                    
                except Exception:
                    session_errors += 1
            
            return session_requests, session_errors
        
        # Simulate multiple users
        start_time = time.perf_counter()
        user_count = 25
        tasks = [user_simulation() for _ in range(user_count)]
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time
        
        # Analyze load test results
        total_requests = sum(r[0] for r in results)
        total_errors = sum(r[1] for r in results)
        error_rate = total_errors / (total_requests + total_errors) if (total_requests + total_errors) > 0 else 0
        throughput = total_requests / total_time
        
        # Performance assertions
        assert error_rate < 0.02, f"Error rate too high under load: {error_rate:.2%}"
        assert throughput > 50, f"Throughput too low under load: {throughput:.1f} req/s"
        assert total_time < 60, f"Load test took too long: {total_time:.1f}s"


# Performance test utilities
class PerformanceBenchmark:
    """Utility class for performance benchmarking"""
    
    @staticmethod
    def measure_operation_time(func, *args, **kwargs):
        """Measure operation execution time"""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        return result, end_time - start_time
    
    @staticmethod
    async def measure_async_operation_time(coro):
        """Measure async operation execution time"""
        start_time = time.perf_counter()
        result = await coro
        end_time = time.perf_counter()
        return result, end_time - start_time
    
    @staticmethod
    def percentile(data: List[float], p: float) -> float:
        """Calculate percentile of performance data"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * p / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


@pytest.fixture
def performance_benchmark():
    """Performance benchmark utility fixture"""
    return PerformanceBenchmark()