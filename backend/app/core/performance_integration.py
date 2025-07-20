#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance & Scalability Integration Module
Coordinates all performance optimization components for IDF Testing Infrastructure
"""

import asyncio
from typing import Dict, Any, Optional
import structlog
from contextlib import asynccontextmanager

from core.config import settings
from core.database import init_db, db_manager, close_db
from core.cache import initialize_cache, cleanup_cache, cache
from core.hebrew_search_indexes import hebrew_search
from core.performance_monitor import initialize_monitoring, cleanup_monitoring, performance_monitor
from core.load_balancer import initialize_load_balancer, cleanup_load_balancer, load_balancer, auto_scaler

logger = structlog.get_logger()


class PerformanceManager:
    """Central performance management system"""
    
    def __init__(self):
        self.initialized = False
        self.components = {
            "database": False,
            "cache": False,
            "search_indexes": False,
            "monitoring": False,
            "load_balancer": False
        }
    
    async def initialize_all(self):
        """Initialize all performance components"""
        logger.info("Initializing performance optimization system")
        
        try:
            # 1. Initialize database with optimizations
            logger.info("Initializing database with performance optimizations")
            await init_db()
            self.components["database"] = True
            
            # 2. Initialize Redis cache
            logger.info("Initializing Redis caching layer")
            await initialize_cache()
            self.components["cache"] = True
            
            # 3. Setup Hebrew search indexes
            logger.info("Setting up Hebrew search indexes")
            await self._setup_search_indexes()
            self.components["search_indexes"] = True
            
            # 4. Start performance monitoring
            logger.info("Starting performance monitoring")
            await initialize_monitoring()
            self.components["monitoring"] = True
            
            # 5. Initialize load balancer
            logger.info("Initializing load balancer")
            await initialize_load_balancer()
            self.components["load_balancer"] = True
            
            self.initialized = True
            logger.info("Performance optimization system initialized successfully")
            
            # Run initial optimizations
            await self._run_initial_optimizations()
            
        except Exception as e:
            logger.error("Failed to initialize performance system", error=str(e))
            await self.cleanup_all()
            raise
    
    async def _setup_search_indexes(self):
        """Setup Hebrew search indexes"""
        try:
            from core.database import get_db_session
            
            async with get_db_session() as session:
                await hebrew_search.setup_all_optimizations(session)
                logger.info("Hebrew search indexes setup completed")
        except Exception as e:
            logger.error("Failed to setup search indexes", error=str(e))
            raise
    
    async def _run_initial_optimizations(self):
        """Run initial optimization tasks"""
        try:
            # Warm up cache
            logger.info("Warming up cache")
            from core.cache import warm_inspection_cache, warm_building_cache
            await warm_inspection_cache()
            await warm_building_cache()
            
            # Update table statistics
            logger.info("Updating database statistics")
            from core.database import get_db_session
            async with get_db_session() as session:
                await hebrew_search.analyze_tables_for_performance(session)
            
            logger.info("Initial optimizations completed")
            
        except Exception as e:
            logger.warning("Some initial optimizations failed", error=str(e))
    
    async def cleanup_all(self):
        """Cleanup all performance components"""
        logger.info("Cleaning up performance optimization system")
        
        try:
            # Cleanup in reverse order
            if self.components["load_balancer"]:
                await cleanup_load_balancer()
            
            if self.components["monitoring"]:
                await cleanup_monitoring()
            
            if self.components["cache"]:
                await cleanup_cache()
            
            if self.components["database"]:
                await close_db()
            
            self.initialized = False
            logger.info("Performance optimization system cleanup completed")
            
        except Exception as e:
            logger.error("Error during performance system cleanup", error=str(e))
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        if not self.initialized:
            return {
                "status": "not_initialized",
                "components": self.components
            }
        
        try:
            # Get performance metrics
            current_metrics = await performance_monitor.get_current_metrics()
            
            # Get database stats
            db_stats = await db_manager.get_connection_stats()
            
            # Get cache stats
            cache_info = await cache.get_cache_info()
            
            # Get load balancer stats
            lb_stats = load_balancer.get_stats()
            
            # Get auto-scaler metrics
            scaler_metrics = auto_scaler.get_scaling_metrics()
            
            # Get index usage stats
            async with db_manager.get_db_session() as session:
                index_stats = await hebrew_search.get_index_usage_stats(session)
            
            return {
                "status": "operational",
                "timestamp": current_metrics.get("timestamp"),
                "components": self.components,
                "performance_metrics": current_metrics,
                "database_stats": db_stats,
                "cache_info": cache_info,
                "load_balancer_stats": lb_stats,
                "auto_scaler_metrics": scaler_metrics,
                "index_usage_stats": index_stats
            }
            
        except Exception as e:
            logger.error("Failed to get system status", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "components": self.components
            }
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        try:
            # Get performance report from monitor
            perf_report = await performance_monitor.get_performance_report()
            
            # Add additional metrics
            system_status = await self.get_system_status()
            
            # Calculate optimization effectiveness
            optimization_score = await self._calculate_optimization_score()
            
            return {
                **perf_report,
                "system_status": system_status,
                "optimization_score": optimization_score,
                "recommendations": await self._generate_optimization_recommendations()
            }
            
        except Exception as e:
            logger.error("Failed to generate performance report", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _calculate_optimization_score(self) -> Dict[str, float]:
        """Calculate optimization effectiveness score"""
        try:
            scores = {}
            
            # Database optimization score
            db_stats = await db_manager.get_connection_stats()
            pool_utilization = (db_stats.get("checked_out", 0) / 
                              max(db_stats.get("pool_size", 1), 1)) * 100
            scores["database"] = max(0, 100 - pool_utilization)
            
            # Cache optimization score
            cache_info = await cache.get_cache_info()
            cache_metrics = cache_info.get("metrics", {})
            scores["cache"] = cache_metrics.get("hit_rate", 0) * 100
            
            # Load balancer optimization score
            lb_stats = load_balancer.get_stats()
            scores["load_balancer"] = lb_stats.get("success_rate", 0)
            
            # Search optimization score (based on index usage)
            scores["search"] = 85.0  # Placeholder - would be calculated from actual usage
            
            # Overall optimization score
            scores["overall"] = sum(scores.values()) / len(scores)
            
            return scores
            
        except Exception as e:
            logger.error("Failed to calculate optimization score", error=str(e))
            return {"overall": 0.0}
    
    async def _generate_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        try:
            # Check database performance
            db_stats = await db_manager.get_connection_stats()
            if db_stats.get("checked_out", 0) > db_stats.get("pool_size", 20) * 0.8:
                recommendations.append("Consider increasing database connection pool size")
            
            # Check cache performance
            cache_info = await cache.get_cache_info()
            cache_metrics = cache_info.get("metrics", {})
            if cache_metrics.get("hit_rate", 0) < 0.8:
                recommendations.append("Cache hit rate is low - consider optimizing cache strategy")
            
            # Check load balancer performance
            lb_stats = load_balancer.get_stats()
            if lb_stats.get("success_rate", 100) < 95:
                recommendations.append("Load balancer success rate is low - check server health")
            
            # Check auto-scaler
            scaler_metrics = auto_scaler.get_scaling_metrics()
            if scaler_metrics.get("avg_cpu", 0) > 80:
                recommendations.append("High CPU usage detected - consider scaling up")
            
            if not recommendations:
                recommendations.append("System is performing well - continue monitoring")
            
        except Exception as e:
            logger.error("Failed to generate recommendations", error=str(e))
            recommendations.append("Unable to generate recommendations due to system error")
        
        return recommendations
    
    async def optimize_system(self) -> Dict[str, Any]:
        """Perform system optimization tasks"""
        optimization_results = {
            "timestamp": asyncio.get_event_loop().time(),
            "tasks_completed": [],
            "tasks_failed": [],
            "recommendations": []
        }
        
        try:
            # Refresh materialized views
            try:
                async with db_manager.get_db_session() as session:
                    await session.execute("SELECT refresh_all_materialized_views();")
                    await session.commit()
                optimization_results["tasks_completed"].append("Refreshed materialized views")
            except Exception as e:
                optimization_results["tasks_failed"].append(f"Failed to refresh materialized views: {str(e)}")
            
            # Clear expired cache entries
            try:
                await cache.clear_pattern("*:expired:*")
                optimization_results["tasks_completed"].append("Cleared expired cache entries")
            except Exception as e:
                optimization_results["tasks_failed"].append(f"Failed to clear expired cache: {str(e)}")
            
            # Update table statistics
            try:
                async with db_manager.get_db_session() as session:
                    await hebrew_search.analyze_tables_for_performance(session)
                optimization_results["tasks_completed"].append("Updated table statistics")
            except Exception as e:
                optimization_results["tasks_failed"].append(f"Failed to update table statistics: {str(e)}")
            
            # Generate recommendations
            optimization_results["recommendations"] = await self._generate_optimization_recommendations()
            
            logger.info("System optimization completed", 
                       completed=len(optimization_results["tasks_completed"]),
                       failed=len(optimization_results["tasks_failed"]))
            
        except Exception as e:
            logger.error("System optimization failed", error=str(e))
            optimization_results["tasks_failed"].append(f"System optimization error: {str(e)}")
        
        return optimization_results


# Global performance manager instance
performance_manager = PerformanceManager()


@asynccontextmanager
async def performance_context():
    """Context manager for performance system"""
    await performance_manager.initialize_all()
    try:
        yield performance_manager
    finally:
        await performance_manager.cleanup_all()


# Health check endpoint
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check for all performance components"""
    from core.performance_monitor import health_check as base_health_check
    
    health_status = await base_health_check()
    
    # Add performance-specific checks
    try:
        system_status = await performance_manager.get_system_status()
        health_status["performance_components"] = system_status["components"]
        
        # Check if all components are operational
        if all(system_status["components"].values()):
            health_status["performance_status"] = "healthy"
        else:
            health_status["performance_status"] = "degraded"
            health_status["status"] = "degraded"
    
    except Exception as e:
        health_status["performance_status"] = "unhealthy"
        health_status["performance_error"] = str(e)
        if health_status["status"] == "healthy":
            health_status["status"] = "unhealthy"
    
    return health_status


# Startup function
async def startup():
    """Startup function for performance system"""
    try:
        await performance_manager.initialize_all()
        logger.info("Performance system startup completed")
    except Exception as e:
        logger.error("Performance system startup failed", error=str(e))
        raise


# Shutdown function
async def shutdown():
    """Shutdown function for performance system"""
    try:
        await performance_manager.cleanup_all()
        logger.info("Performance system shutdown completed")
    except Exception as e:
        logger.error("Performance system shutdown failed", error=str(e))


# API endpoints for performance monitoring
async def get_performance_metrics():
    """Get current performance metrics"""
    return await performance_manager.get_system_status()


async def get_performance_report():
    """Get comprehensive performance report"""
    return await performance_manager.get_performance_report()


async def optimize_system():
    """Trigger system optimization"""
    return await performance_manager.optimize_system()


# Export main functions
__all__ = [
    'performance_manager',
    'performance_context',
    'health_check',
    'startup',
    'shutdown',
    'get_performance_metrics',
    'get_performance_report',
    'optimize_system'
]