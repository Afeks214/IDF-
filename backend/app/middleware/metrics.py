#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDF Testing Infrastructure - Metrics Middleware
Prometheus metrics collection and performance monitoring
"""

import time
import asyncio
from typing import Callable, Optional
from fastapi import Request, Response
from prometheus_client import (
    Counter, Histogram, Gauge, Info,
    generate_latest, CONTENT_TYPE_LATEST,
    CollectorRegistry, REGISTRY
)
import structlog
import psutil
import os
from datetime import datetime

from core.config import settings

logger = structlog.get_logger()

# Custom registry for application metrics
app_registry = CollectorRegistry()

# HTTP Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=app_registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=app_registry
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests currently being processed',
    registry=app_registry
)

# Database Metrics
db_connections_active = Gauge(
    'db_connections_active',
    'Number of active database connections',
    registry=app_registry
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=app_registry
)

db_queries_total = Counter(
    'db_queries_total',
    'Total number of database queries',
    ['operation', 'status'],
    registry=app_registry
)

# Cache Metrics
cache_operations_total = Counter(
    'cache_operations_total',
    'Total number of cache operations',
    ['operation', 'result'],
    registry=app_registry
)

cache_hit_ratio = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio',
    registry=app_registry
)

cache_operation_duration_seconds = Histogram(
    'cache_operation_duration_seconds',
    'Cache operation duration in seconds',
    ['operation'],
    buckets=[0.001, 0.002, 0.005, 0.01, 0.025, 0.05, 0.1],
    registry=app_registry
)

# System Metrics
system_cpu_usage_percent = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=app_registry
)

system_memory_usage_bytes = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes',
    registry=app_registry
)

system_disk_usage_bytes = Gauge(
    'system_disk_usage_bytes',
    'System disk usage in bytes',
    ['mountpoint'],
    registry=app_registry
)

# Application Metrics
app_info = Info(
    'app_info',
    'Application information',
    registry=app_registry
)

active_users = Gauge(
    'active_users',
    'Number of active users',
    registry=app_registry
)

hebrew_text_processing_duration = Histogram(
    'hebrew_text_processing_duration_seconds',
    'Hebrew text processing duration in seconds',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.5],
    registry=app_registry
)

file_upload_size_bytes = Histogram(
    'file_upload_size_bytes',
    'Size of uploaded files in bytes',
    ['file_type'],
    buckets=[1024, 10240, 102400, 1048576, 10485760, 104857600],  # 1KB to 100MB
    registry=app_registry
)

# Business Logic Metrics
excel_processing_duration = Histogram(
    'excel_processing_duration_seconds',
    'Excel file processing duration in seconds',
    ['operation'],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
    registry=app_registry
)

data_validation_errors = Counter(
    'data_validation_errors_total',
    'Total number of data validation errors',
    ['error_type'],
    registry=app_registry
)


class MetricsMiddleware:
    """FastAPI middleware for collecting metrics"""
    
    def __init__(self, app):
        self.app = app
        
        # Set application info
        app_info.info({
            'version': settings.VERSION,
            'environment': settings.ENVIRONMENT,
            'hebrew_support': str(settings.HEBREW_SUPPORT)
        })
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Skip metrics for metrics endpoint
        if request.url.path == "/metrics":
            await self.app(scope, receive, send)
            return
        
        # Record request start
        start_time = time.perf_counter()
        http_requests_in_progress.inc()
        
        # Process request
        try:
            await self.app(scope, receive, send)
        finally:
            # Record request completion
            duration = time.perf_counter() - start_time
            http_requests_in_progress.dec()
            
            # Get response status (if available)
            status_code = "unknown"
            try:
                # This is a simplified approach - in practice you'd need to wrap the send
                status_code = "200"  # Default assumption
            except:
                pass
            
            # Record metrics
            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=status_code
            ).inc()
            
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)


class SystemMetricsCollector:
    """Collects system-level metrics"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.collecting = False
    
    async def start_collection(self, interval: int = 30):
        """Start collecting system metrics at regular intervals"""
        if self.collecting:
            return
        
        self.collecting = True
        
        while self.collecting:
            try:
                await self.collect_metrics()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error("Error collecting system metrics", error=str(e))
                await asyncio.sleep(interval)
    
    def stop_collection(self):
        """Stop collecting system metrics"""
        self.collecting = False
    
    async def collect_metrics(self):
        """Collect current system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            system_cpu_usage_percent.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            system_memory_usage_bytes.set(memory.used)
            
            # Disk usage
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    system_disk_usage_bytes.labels(
                        mountpoint=partition.mountpoint
                    ).set(usage.used)
                except (PermissionError, FileNotFoundError):
                    continue
            
        except Exception as e:
            logger.error("Error in system metrics collection", error=str(e))


class DatabaseMetricsCollector:
    """Collects database-related metrics"""
    
    @staticmethod
    def record_query_start(operation: str):
        """Record the start of a database query"""
        return time.perf_counter()
    
    @staticmethod
    def record_query_end(operation: str, start_time: float, success: bool = True):
        """Record the completion of a database query"""
        duration = time.perf_counter() - start_time
        
        db_query_duration_seconds.labels(operation=operation).observe(duration)
        db_queries_total.labels(
            operation=operation,
            status="success" if success else "error"
        ).inc()
    
    @staticmethod
    def record_connection_count(count: int):
        """Record current database connection count"""
        db_connections_active.set(count)


class CacheMetricsCollector:
    """Collects cache-related metrics"""
    
    def __init__(self):
        self.total_operations = 0
        self.hits = 0
    
    def record_cache_operation(self, operation: str, hit: bool, duration: float):
        """Record cache operation"""
        self.total_operations += 1
        
        if hit:
            self.hits += 1
            result = "hit"
        else:
            result = "miss"
        
        cache_operations_total.labels(operation=operation, result=result).inc()
        cache_operation_duration_seconds.labels(operation=operation).observe(duration)
        
        # Update hit ratio
        if self.total_operations > 0:
            hit_ratio = self.hits / self.total_operations
            cache_hit_ratio.set(hit_ratio)


class HebrewProcessingMetricsCollector:
    """Collects Hebrew text processing metrics"""
    
    @staticmethod
    def record_hebrew_processing(operation: str, duration: float):
        """Record Hebrew text processing operation"""
        hebrew_text_processing_duration.labels(operation=operation).observe(duration)
    
    @staticmethod
    def record_file_upload(file_type: str, size_bytes: int):
        """Record file upload metrics"""
        file_upload_size_bytes.labels(file_type=file_type).observe(size_bytes)
    
    @staticmethod
    def record_excel_processing(operation: str, duration: float):
        """Record Excel processing operation"""
        excel_processing_duration.labels(operation=operation).observe(duration)
    
    @staticmethod
    def record_validation_error(error_type: str):
        """Record data validation error"""
        data_validation_errors.labels(error_type=error_type).inc()


# Decorators for automatic metrics collection
def track_database_operation(operation: str):
    """Decorator to track database operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = DatabaseMetricsCollector.record_query_start(operation)
            success = True
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                DatabaseMetricsCollector.record_query_end(operation, start_time, success)
        
        return wrapper
    return decorator


def track_cache_operation(operation: str):
    """Decorator to track cache operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            hit = False
            
            try:
                result = await func(*args, **kwargs)
                hit = result is not None
                return result
            finally:
                duration = time.perf_counter() - start_time
                cache_metrics_collector.record_cache_operation(operation, hit, duration)
        
        return wrapper
    return decorator


def track_hebrew_processing(operation: str):
    """Decorator to track Hebrew text processing"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start_time
                HebrewProcessingMetricsCollector.record_hebrew_processing(operation, duration)
        
        return wrapper
    return decorator


# Global collectors
system_metrics_collector = SystemMetricsCollector()
db_metrics_collector = DatabaseMetricsCollector()
cache_metrics_collector = CacheMetricsCollector()
hebrew_metrics_collector = HebrewProcessingMetricsCollector()


async def get_metrics():
    """Get Prometheus metrics in text format"""
    return generate_latest(app_registry)


class PerformanceMonitor:
    """Main performance monitoring class"""
    
    def __init__(self):
        self.monitoring_active = False
        self.alerts = []
    
    async def start_monitoring(self):
        """Start performance monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        logger.info("Performance monitoring started")
        
        # Start system metrics collection
        asyncio.create_task(system_metrics_collector.start_collection())
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        system_metrics_collector.stop_collection()
        logger.info("Performance monitoring stopped")
    
    def check_performance_thresholds(self):
        """Check if performance metrics exceed thresholds"""
        alerts = []
        
        # Check response time
        # This would be implemented with actual metric values
        
        # Check memory usage
        try:
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                alerts.append({
                    "type": "high_memory_usage",
                    "value": memory.percent,
                    "threshold": 85,
                    "timestamp": datetime.utcnow().isoformat()
                })
        except Exception:
            pass
        
        # Check CPU usage
        try:
            cpu_percent = psutil.cpu_percent()
            if cpu_percent > 80:
                alerts.append({
                    "type": "high_cpu_usage",
                    "value": cpu_percent,
                    "threshold": 80,
                    "timestamp": datetime.utcnow().isoformat()
                })
        except Exception:
            pass
        
        return alerts
    
    def get_performance_summary(self):
        """Get performance summary"""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            
            return {
                "memory_usage_percent": memory.percent,
                "cpu_usage_percent": cpu_percent,
                "monitoring_active": self.monitoring_active,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error("Error getting performance summary", error=str(e))
            return {"error": str(e)}


# Global performance monitor
performance_monitor = PerformanceMonitor()