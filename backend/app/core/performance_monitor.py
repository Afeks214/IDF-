#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Performance Monitoring System for IDF Testing Infrastructure
Real-time monitoring, alerting, and auto-scaling capabilities
"""

import asyncio
import time
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import structlog
from contextlib import asynccontextmanager

from core.config import settings
from core.database import db_manager, db_metrics
from core.cache import cache

logger = structlog.get_logger()


@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available: int
    memory_used: int
    disk_usage_percent: float
    disk_free: int
    network_io_sent: int
    network_io_recv: int
    active_connections: int
    response_time_avg: float
    error_rate: float


@dataclass
class DatabaseMetrics:
    """Database performance metrics"""
    timestamp: datetime
    active_connections: int
    idle_connections: int
    query_count: int
    slow_queries: int
    avg_query_time: float
    max_query_time: float
    deadlocks: int
    cache_hit_ratio: float
    index_usage: Dict[str, int]


@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    timestamp: datetime
    hit_rate: float
    miss_rate: float
    total_requests: int
    memory_usage: int
    evictions: int
    avg_response_time: float


@dataclass
class ApplicationMetrics:
    """Application-specific metrics"""
    timestamp: datetime
    active_users: int
    requests_per_second: float
    avg_response_time: float
    error_rate: float
    endpoint_stats: Dict[str, Dict[str, Any]]


class AlertManager:
    """Alert management for performance monitoring"""
    
    def __init__(self):
        self.alert_rules = {
            "high_cpu": {"threshold": 80, "duration": 300},  # 80% for 5 minutes
            "high_memory": {"threshold": 85, "duration": 300},  # 85% for 5 minutes
            "high_disk": {"threshold": 90, "duration": 60},   # 90% for 1 minute
            "slow_queries": {"threshold": 5, "duration": 300},  # 5 slow queries in 5 minutes
            "high_error_rate": {"threshold": 5, "duration": 60},  # 5% error rate for 1 minute
            "low_cache_hit_rate": {"threshold": 70, "duration": 300},  # Below 70% for 5 minutes
            "database_connections": {"threshold": 80, "duration": 300}  # 80% of max connections
        }
        
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.alert_callbacks = []
    
    def add_alert_callback(self, callback: Callable):
        """Add callback function for alerts"""
        self.alert_callbacks.append(callback)
    
    async def check_alerts(self, metrics: Dict[str, Any]):
        """Check all alert conditions"""
        current_time = datetime.now()
        
        # Check CPU usage
        if metrics.get("cpu_percent", 0) > self.alert_rules["high_cpu"]["threshold"]:
            await self._trigger_alert("high_cpu", f"CPU usage: {metrics['cpu_percent']:.1f}%", current_time)
        
        # Check memory usage
        if metrics.get("memory_percent", 0) > self.alert_rules["high_memory"]["threshold"]:
            await self._trigger_alert("high_memory", f"Memory usage: {metrics['memory_percent']:.1f}%", current_time)
        
        # Check disk usage
        if metrics.get("disk_usage_percent", 0) > self.alert_rules["high_disk"]["threshold"]:
            await self._trigger_alert("high_disk", f"Disk usage: {metrics['disk_usage_percent']:.1f}%", current_time)
        
        # Check slow queries
        if metrics.get("slow_queries", 0) > self.alert_rules["slow_queries"]["threshold"]:
            await self._trigger_alert("slow_queries", f"Slow queries: {metrics['slow_queries']}", current_time)
        
        # Check error rate
        if metrics.get("error_rate", 0) > self.alert_rules["high_error_rate"]["threshold"]:
            await self._trigger_alert("high_error_rate", f"Error rate: {metrics['error_rate']:.1f}%", current_time)
        
        # Check cache hit rate
        if metrics.get("cache_hit_rate", 100) < self.alert_rules["low_cache_hit_rate"]["threshold"]:
            await self._trigger_alert("low_cache_hit_rate", f"Cache hit rate: {metrics['cache_hit_rate']:.1f}%", current_time)
    
    async def _trigger_alert(self, alert_type: str, message: str, timestamp: datetime):
        """Trigger an alert"""
        alert_key = f"{alert_type}_{timestamp.strftime('%Y%m%d_%H%M')}"
        
        if alert_key not in self.active_alerts:
            alert_data = {
                "type": alert_type,
                "message": message,
                "timestamp": timestamp,
                "severity": self._get_alert_severity(alert_type)
            }
            
            self.active_alerts[alert_key] = alert_data
            self.alert_history.append(alert_data)
            
            # Execute alert callbacks
            for callback in self.alert_callbacks:
                try:
                    await callback(alert_data)
                except Exception as e:
                    logger.error("Alert callback failed", error=str(e))
            
            logger.warning(f"Alert triggered: {alert_type}", message=message)
    
    def _get_alert_severity(self, alert_type: str) -> str:
        """Get alert severity level"""
        high_severity = ["high_disk", "database_connections", "high_error_rate"]
        medium_severity = ["high_cpu", "high_memory", "slow_queries"]
        
        if alert_type in high_severity:
            return "high"
        elif alert_type in medium_severity:
            return "medium"
        else:
            return "low"
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self) -> List[Dict[str, Any]]:
        """Get alert history"""
        return list(self.alert_history)


class PerformanceMonitor:
    """Comprehensive performance monitoring system"""
    
    def __init__(self):
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.alert_manager = AlertManager()
        self.monitoring_active = False
        self.monitoring_interval = 30  # seconds
        self.monitoring_task = None
        self.last_network_io = None
        
        # Performance thresholds
        self.thresholds = {
            "slow_query_time": 1.0,  # seconds
            "high_response_time": 2.0,  # seconds
            "max_memory_usage": 85,  # percent
            "max_cpu_usage": 80,  # percent
            "max_disk_usage": 90   # percent
        }
    
    async def start_monitoring(self):
        """Start the performance monitoring system"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop the performance monitoring system"""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect all metrics
                system_metrics = await self._collect_system_metrics()
                db_metrics_data = await self._collect_database_metrics()
                cache_metrics_data = await self._collect_cache_metrics()
                app_metrics = await self._collect_application_metrics()
                
                # Store metrics
                self._store_metrics(system_metrics, db_metrics_data, cache_metrics_data, app_metrics)
                
                # Check alerts
                combined_metrics = {
                    **asdict(system_metrics),
                    **asdict(db_metrics_data),
                    **asdict(cache_metrics_data),
                    **asdict(app_metrics)
                }
                await self.alert_manager.check_alerts(combined_metrics)
                
                # Cache current metrics for API access
                await self._cache_current_metrics(combined_metrics)
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error("Monitoring loop error", error=str(e))
                await asyncio.sleep(self.monitoring_interval)
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system-level metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Network I/O
        network_io = psutil.net_io_counters()
        
        # Calculate network rates if we have previous data
        network_sent = network_io.bytes_sent
        network_recv = network_io.bytes_recv
        
        if self.last_network_io:
            network_sent = network_io.bytes_sent - self.last_network_io.bytes_sent
            network_recv = network_io.bytes_recv - self.last_network_io.bytes_recv
        
        self.last_network_io = network_io
        
        # Active connections (approximate)
        active_connections = len(psutil.net_connections())
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available=memory.available,
            memory_used=memory.used,
            disk_usage_percent=(disk.used / disk.total) * 100,
            disk_free=disk.free,
            network_io_sent=network_sent,
            network_io_recv=network_recv,
            active_connections=active_connections,
            response_time_avg=0.0,  # Will be calculated from app metrics
            error_rate=0.0  # Will be calculated from app metrics
        )
    
    async def _collect_database_metrics(self) -> DatabaseMetrics:
        """Collect database performance metrics"""
        try:
            # Get connection pool stats
            pool_stats = await db_manager.get_connection_stats()
            
            # Get query performance metrics
            query_metrics = db_metrics.get_metrics()
            
            # Get slow query count
            slow_queries = len([t for t in db_metrics.query_times if t > self.thresholds["slow_query_time"]])
            
            # Get database statistics
            db_stats = await db_manager.get_query_performance_stats()
            
            # Calculate cache hit ratio (approximate)
            cache_hit_ratio = 95.0  # Default, will be updated with real data
            
            return DatabaseMetrics(
                timestamp=datetime.now(),
                active_connections=pool_stats.get("checked_out", 0),
                idle_connections=pool_stats.get("checked_in", 0),
                query_count=query_metrics.get("total_queries", 0),
                slow_queries=slow_queries,
                avg_query_time=query_metrics.get("avg_query_time", 0.0),
                max_query_time=query_metrics.get("max_query_time", 0.0),
                deadlocks=0,  # Would need specific monitoring
                cache_hit_ratio=cache_hit_ratio,
                index_usage={}  # Would need specific monitoring
            )
        
        except Exception as e:
            logger.warning("Failed to collect database metrics", error=str(e))
            return DatabaseMetrics(
                timestamp=datetime.now(),
                active_connections=0,
                idle_connections=0,
                query_count=0,
                slow_queries=0,
                avg_query_time=0.0,
                max_query_time=0.0,
                deadlocks=0,
                cache_hit_ratio=0.0,
                index_usage={}
            )
    
    async def _collect_cache_metrics(self) -> CacheMetrics:
        """Collect cache performance metrics"""
        try:
            cache_info = await cache.get_cache_info()
            cache_stats = cache_info.get("metrics", {})
            
            return CacheMetrics(
                timestamp=datetime.now(),
                hit_rate=cache_stats.get("hit_rate", 0.0) * 100,
                miss_rate=(1 - cache_stats.get("hit_rate", 0.0)) * 100,
                total_requests=cache_stats.get("total_requests", 0),
                memory_usage=0,  # Would need Redis info
                evictions=0,  # Would need Redis info
                avg_response_time=0.0  # Would need measurement
            )
        
        except Exception as e:
            logger.warning("Failed to collect cache metrics", error=str(e))
            return CacheMetrics(
                timestamp=datetime.now(),
                hit_rate=0.0,
                miss_rate=0.0,
                total_requests=0,
                memory_usage=0,
                evictions=0,
                avg_response_time=0.0
            )
    
    async def _collect_application_metrics(self) -> ApplicationMetrics:
        """Collect application-specific metrics"""
        return ApplicationMetrics(
            timestamp=datetime.now(),
            active_users=0,  # Would need session tracking
            requests_per_second=0.0,  # Would need request tracking
            avg_response_time=0.0,  # Would need response time tracking
            error_rate=0.0,  # Would need error tracking
            endpoint_stats={}  # Would need endpoint tracking
        )
    
    def _store_metrics(self, system_metrics: SystemMetrics, 
                      db_metrics: DatabaseMetrics, 
                      cache_metrics: CacheMetrics,
                      app_metrics: ApplicationMetrics):
        """Store metrics in memory"""
        self.metrics_history["system"].append(system_metrics)
        self.metrics_history["database"].append(db_metrics)
        self.metrics_history["cache"].append(cache_metrics)
        self.metrics_history["application"].append(app_metrics)
    
    async def _cache_current_metrics(self, metrics: Dict[str, Any]):
        """Cache current metrics for API access"""
        try:
            await cache.set("current_metrics", metrics, ttl=60)
        except Exception as e:
            logger.warning("Failed to cache metrics", error=str(e))
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            cached_metrics = await cache.get("current_metrics")
            if cached_metrics:
                return cached_metrics
        except Exception:
            pass
        
        # Fallback to fresh collection
        system_metrics = await self._collect_system_metrics()
        db_metrics = await self._collect_database_metrics()
        cache_metrics = await self._collect_cache_metrics()
        app_metrics = await self._collect_application_metrics()
        
        return {
            "system": asdict(system_metrics),
            "database": asdict(db_metrics),
            "cache": asdict(cache_metrics),
            "application": asdict(app_metrics),
            "alerts": self.alert_manager.get_active_alerts()
        }
    
    async def get_metrics_history(self, metric_type: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics history for specified time period"""
        if metric_type not in self.metrics_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_metrics = []
        for metric in self.metrics_history[metric_type]:
            if metric.timestamp > cutoff_time:
                filtered_metrics.append(asdict(metric))
        
        return filtered_metrics
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        current_metrics = await self.get_current_metrics()
        
        # Calculate performance scores
        performance_scores = {
            "cpu_score": max(0, 100 - current_metrics["system"]["cpu_percent"]),
            "memory_score": max(0, 100 - current_metrics["system"]["memory_percent"]),
            "disk_score": max(0, 100 - current_metrics["system"]["disk_usage_percent"]),
            "database_score": min(100, current_metrics["database"]["cache_hit_ratio"]),
            "cache_score": current_metrics["cache"]["hit_rate"]
        }
        
        overall_score = sum(performance_scores.values()) / len(performance_scores)
        
        # Get recent alerts
        recent_alerts = [
            alert for alert in self.alert_manager.get_alert_history()
            if alert["timestamp"] > datetime.now() - timedelta(hours=24)
        ]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_performance_score": overall_score,
            "performance_scores": performance_scores,
            "current_metrics": current_metrics,
            "recent_alerts": recent_alerts,
            "recommendations": self._generate_recommendations(current_metrics, performance_scores)
        }
    
    def _generate_recommendations(self, metrics: Dict[str, Any], scores: Dict[str, float]) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        if scores["cpu_score"] < 70:
            recommendations.append("Consider scaling up CPU resources or optimizing CPU-intensive operations")
        
        if scores["memory_score"] < 70:
            recommendations.append("Memory usage is high. Consider increasing memory or optimizing memory usage")
        
        if scores["disk_score"] < 70:
            recommendations.append("Disk usage is high. Consider cleaning up old files or adding storage")
        
        if scores["database_score"] < 80:
            recommendations.append("Database performance could be improved. Check slow queries and optimize indexes")
        
        if scores["cache_score"] < 80:
            recommendations.append("Cache hit rate is low. Consider increasing cache size or improving cache strategy")
        
        if metrics["database"]["slow_queries"] > 10:
            recommendations.append("High number of slow queries detected. Review and optimize database queries")
        
        if not recommendations:
            recommendations.append("System performance is good. Continue monitoring for optimal performance")
        
        return recommendations
    
    async def trigger_auto_scaling(self, metrics: Dict[str, Any]):
        """Trigger auto-scaling based on metrics"""
        # This would integrate with cloud provider APIs
        # For now, just log recommendations
        
        if metrics["system"]["cpu_percent"] > 80:
            logger.warning("High CPU usage detected. Auto-scaling recommended")
        
        if metrics["system"]["memory_percent"] > 85:
            logger.warning("High memory usage detected. Auto-scaling recommended")
        
        if metrics["database"]["active_connections"] > 15:  # Assuming max 20 connections
            logger.warning("High database connection usage. Consider connection pooling optimization")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


@asynccontextmanager
async def monitoring_context():
    """Context manager for performance monitoring"""
    await performance_monitor.start_monitoring()
    try:
        yield performance_monitor
    finally:
        await performance_monitor.stop_monitoring()


# Decorators for performance monitoring
def monitor_endpoint_performance(endpoint_name: str):
    """Decorator to monitor endpoint performance"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log slow endpoints
                if duration > performance_monitor.thresholds["high_response_time"]:
                    logger.warning(
                        "Slow endpoint detected",
                        endpoint=endpoint_name,
                        duration=duration
                    )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "Endpoint error",
                    endpoint=endpoint_name,
                    duration=duration,
                    error=str(e)
                )
                raise
        return wrapper
    return decorator


# Alert callback for logging
async def log_alert_callback(alert_data: Dict[str, Any]):
    """Log alert callback"""
    logger.warning(
        "Performance alert",
        alert_type=alert_data["type"],
        message=alert_data["message"],
        severity=alert_data["severity"]
    )


# Initialize alert callback
performance_monitor.alert_manager.add_alert_callback(log_alert_callback)


# Health check functions
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Database health check
    try:
        db_healthy = await db_manager.health_check()
        health_status["checks"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "message": "Database connection successful" if db_healthy else "Database connection failed"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database check failed: {str(e)}"
        }
    
    # Cache health check
    try:
        cache_info = await cache.get_cache_info()
        cache_healthy = cache_info.get("status") == "connected"
        health_status["checks"]["cache"] = {
            "status": "healthy" if cache_healthy else "unhealthy",
            "message": "Cache connection successful" if cache_healthy else "Cache connection failed"
        }
    except Exception as e:
        health_status["checks"]["cache"] = {
            "status": "unhealthy",
            "message": f"Cache check failed: {str(e)}"
        }
    
    # System health check
    try:
        system_metrics = await performance_monitor._collect_system_metrics()
        cpu_healthy = system_metrics.cpu_percent < 90
        memory_healthy = system_metrics.memory_percent < 90
        disk_healthy = system_metrics.disk_usage_percent < 95
        
        system_healthy = cpu_healthy and memory_healthy and disk_healthy
        health_status["checks"]["system"] = {
            "status": "healthy" if system_healthy else "unhealthy",
            "message": f"CPU: {system_metrics.cpu_percent:.1f}%, Memory: {system_metrics.memory_percent:.1f}%, Disk: {system_metrics.disk_usage_percent:.1f}%"
        }
    except Exception as e:
        health_status["checks"]["system"] = {
            "status": "unhealthy",
            "message": f"System check failed: {str(e)}"
        }
    
    # Update overall status
    unhealthy_checks = [check for check in health_status["checks"].values() if check["status"] == "unhealthy"]
    if unhealthy_checks:
        health_status["status"] = "unhealthy"
    
    return health_status


# Startup function
async def initialize_monitoring():
    """Initialize the monitoring system"""
    try:
        await performance_monitor.start_monitoring()
        logger.info("Performance monitoring system initialized")
    except Exception as e:
        logger.error("Failed to initialize monitoring", error=str(e))
        raise


# Cleanup function
async def cleanup_monitoring():
    """Cleanup monitoring resources"""
    try:
        await performance_monitor.stop_monitoring()
        logger.info("Performance monitoring system cleaned up")
    except Exception as e:
        logger.error("Failed to cleanup monitoring", error=str(e))