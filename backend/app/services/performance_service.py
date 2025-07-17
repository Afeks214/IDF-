"""
Database performance optimization service for IDF Testing Infrastructure.
Includes query optimization, indexing, and caching strategies.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import time

from sqlalchemy import text, func, Index
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..db.database import async_engine, db_manager


class PerformanceOptimizationService:
    """Service for database performance monitoring and optimization."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_optimized_indexes(self) -> Dict[str, Any]:
        """Create performance-optimized indexes for Hebrew data."""
        
        indexes_created = []
        errors = []
        
        # Core performance indexes
        core_indexes = [
            # Inspection table indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_building_status ON inspections(building_id, status)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_execution_date ON inspections(execution_schedule) WHERE execution_schedule IS NOT NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_target_date ON inspections(target_completion) WHERE target_completion IS NOT NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_created_at ON inspections(created_at)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_type_leader ON inspections(inspection_type, inspection_leader)",
            
            # Building table indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_buildings_active ON buildings(is_active) WHERE is_active = true",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_buildings_manager ON buildings(manager_name) WHERE manager_name IS NOT NULL",
            
            # Audit log indexes for compliance
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_table_record ON audit_logs(table_name, record_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_user_date ON audit_logs(user_id, created_at)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)",
        ]
        
        # Hebrew text search indexes
        hebrew_indexes = [
            # Full-text search indexes with Hebrew configuration
            """CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_fts_hebrew 
               ON inspections USING gin(
                   to_tsvector('hebrew', 
                       coalesce(inspection_type, '') || ' ' ||
                       coalesce(inspection_leader, '') || ' ' ||
                       coalesce(building_manager, '') || ' ' ||
                       coalesce(red_team, '') || ' ' ||
                       coalesce(inspection_notes, '')
                   )
               )""",
            
            # Trigram indexes for partial matching
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_type_trigram ON inspections USING gin(inspection_type gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_leader_trigram ON inspections USING gin(inspection_leader gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_buildings_name_trigram ON buildings USING gin(building_name gin_trgm_ops)",
        ]
        
        # Composite indexes for common query patterns
        composite_indexes = [
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_status_date ON inspections(status, execution_schedule, target_completion)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_building_round ON inspections(building_id, inspection_round) WHERE inspection_round IS NOT NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_overdue ON inspections(target_completion, status) WHERE target_completion < CURRENT_DATE AND status NOT IN ('completed', 'cancelled')",
        ]
        
        all_indexes = core_indexes + hebrew_indexes + composite_indexes
        
        for index_sql in all_indexes:
            try:
                await self.session.execute(text(index_sql))
                indexes_created.append(index_sql.split('idx_')[1].split(' ')[0] if 'idx_' in index_sql else 'unnamed')
            except Exception as e:
                errors.append(f"Failed to create index: {str(e)}")
        
        try:
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            errors.append(f"Failed to commit indexes: {str(e)}")
        
        return {
            "indexes_created": indexes_created,
            "total_created": len(indexes_created),
            "errors": errors,
            "success": len(errors) == 0
        }
    
    async def analyze_query_performance(self, query: str, parameters: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze performance of a specific query."""
        
        # Get query execution plan
        explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
        
        start_time = time.time()
        
        try:
            if parameters:
                result = await self.session.execute(text(explain_query), parameters)
            else:
                result = await self.session.execute(text(explain_query))
            
            execution_time = time.time() - start_time
            plan_data = result.scalar()
            
            # Parse execution plan
            plan = plan_data[0]['Plan'] if plan_data else {}
            
            analysis = {
                "execution_time_ms": round(execution_time * 1000, 2),
                "planning_time": plan_data[0].get('Planning Time', 0) if plan_data else 0,
                "execution_time": plan_data[0].get('Execution Time', 0) if plan_data else 0,
                "total_cost": plan.get('Total Cost', 0),
                "rows_processed": plan.get('Actual Rows', 0),
                "index_usage": self._analyze_index_usage(plan),
                "recommendations": self._generate_performance_recommendations(plan)
            }
            
            return analysis
            
        except Exception as e:
            return {
                "error": str(e),
                "execution_time_ms": round((time.time() - start_time) * 1000, 2)
            }
    
    async def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of slow queries from PostgreSQL statistics."""
        
        slow_queries_sql = """
        SELECT 
            query,
            calls,
            total_time,
            mean_time,
            rows,
            100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
        FROM pg_stat_statements 
        WHERE total_time > 1000  -- Queries taking more than 1 second total
        ORDER BY total_time DESC 
        LIMIT :limit
        """
        
        try:
            result = await self.session.execute(text(slow_queries_sql), {"limit": limit})
            rows = result.all()
            
            return [
                {
                    "query": row[0][:200] + "..." if len(row[0]) > 200 else row[0],  # Truncate long queries
                    "calls": row[1],
                    "total_time_ms": round(row[2], 2),
                    "avg_time_ms": round(row[3], 2),
                    "rows_processed": row[4],
                    "cache_hit_percent": round(row[5] or 0, 2)
                }
                for row in rows
            ]
            
        except Exception as e:
            return [{"error": f"Failed to retrieve slow queries: {str(e)}"}]
    
    async def get_index_usage_statistics(self) -> Dict[str, Any]:
        """Get statistics about index usage and effectiveness."""
        
        index_stats_sql = """
        SELECT 
            schemaname,
            tablename,
            indexname,
            idx_tup_read,
            idx_tup_fetch,
            idx_scan,
            pg_size_pretty(pg_relation_size(indexrelid)) as index_size
        FROM pg_stat_user_indexes 
        ORDER BY idx_tup_read DESC
        """
        
        try:
            result = await self.session.execute(text(index_stats_sql))
            rows = result.all()
            
            stats = []
            total_scans = 0
            total_reads = 0
            
            for row in rows:
                index_stat = {
                    "schema": row[0],
                    "table": row[1],
                    "index": row[2],
                    "tuples_read": row[3] or 0,
                    "tuples_fetched": row[4] or 0,
                    "scans": row[5] or 0,
                    "size": row[6],
                    "efficiency": round((row[4] or 0) / max(row[3] or 1, 1) * 100, 2)
                }
                stats.append(index_stat)
                total_scans += index_stat["scans"]
                total_reads += index_stat["tuples_read"]
            
            return {
                "index_statistics": stats,
                "summary": {
                    "total_indexes": len(stats),
                    "total_scans": total_scans,
                    "total_reads": total_reads,
                    "unused_indexes": [s for s in stats if s["scans"] == 0],
                    "most_used_indexes": sorted(stats, key=lambda x: x["scans"], reverse=True)[:5]
                }
            }
            
        except Exception as e:
            return {"error": f"Failed to retrieve index statistics: {str(e)}"}
    
    async def optimize_table_statistics(self) -> Dict[str, Any]:
        """Update table statistics for better query planning."""
        
        tables = ["inspections", "buildings", "audit_logs", "inspection_types", "regulators"]
        results = {"analyzed_tables": [], "errors": []}
        
        for table in tables:
            try:
                await self.session.execute(text(f"ANALYZE {table}"))
                results["analyzed_tables"].append(table)
            except Exception as e:
                results["errors"].append(f"Failed to analyze {table}: {str(e)}")
        
        try:
            await self.session.commit()
            results["success"] = len(results["errors"]) == 0
        except Exception as e:
            await self.session.rollback()
            results["errors"].append(f"Failed to commit analysis: {str(e)}")
            results["success"] = False
        
        return results
    
    async def get_database_size_statistics(self) -> Dict[str, Any]:
        """Get database size and growth statistics."""
        
        size_stats_sql = """
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
            pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """
        
        try:
            result = await self.session.execute(text(size_stats_sql))
            rows = result.all()
            
            # Get database total size
            db_size_result = await self.session.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))"))
            total_db_size = db_size_result.scalar()
            
            return {
                "total_database_size": total_db_size,
                "table_sizes": [
                    {
                        "schema": row[0],
                        "table": row[1],
                        "total_size": row[2],
                        "table_size": row[3],
                        "index_size": row[4]
                    }
                    for row in rows
                ]
            }
            
        except Exception as e:
            return {"error": f"Failed to retrieve size statistics: {str(e)}"}
    
    async def monitor_connection_pool(self) -> Dict[str, Any]:
        """Monitor database connection pool statistics."""
        
        pool_stats = {
            "pool_size": async_engine.pool.size(),
            "checked_in": async_engine.pool.checkedin(),
            "checked_out": async_engine.pool.checkedout(),
            "overflow": async_engine.pool.overflow(),
            "invalid": async_engine.pool.invalid(),
        }
        
        # Calculate utilization
        total_connections = pool_stats["checked_in"] + pool_stats["checked_out"]
        utilization = (pool_stats["checked_out"] / max(total_connections, 1)) * 100
        
        pool_stats.update({
            "total_connections": total_connections,
            "utilization_percent": round(utilization, 2),
            "health_status": "healthy" if utilization < 80 else "warning" if utilization < 95 else "critical"
        })
        
        return pool_stats
    
    async def get_performance_recommendations(self) -> List[Dict[str, str]]:
        """Generate performance optimization recommendations."""
        
        recommendations = []
        
        # Check for missing indexes on frequently queried columns
        missing_indexes_check = """
        SELECT 
            schemaname, 
            tablename, 
            attname, 
            n_distinct, 
            correlation
        FROM pg_stats 
        WHERE schemaname = 'public' 
        AND n_distinct > 100
        """
        
        try:
            result = await self.session.execute(text(missing_indexes_check))
            rows = result.all()
            
            for row in rows:
                if row[3] > 1000:  # High cardinality columns
                    recommendations.append({
                        "type": "index",
                        "priority": "medium",
                        "description": f"Consider adding index on {row[1]}.{row[2]} (high cardinality: {row[3]})",
                        "sql": f"CREATE INDEX CONCURRENTLY idx_{row[1]}_{row[2]} ON {row[1]}({row[2]})"
                    })
        
        except Exception:
            pass
        
        # Check connection pool utilization
        pool_stats = await self.monitor_connection_pool()
        if pool_stats.get("utilization_percent", 0) > 80:
            recommendations.append({
                "type": "connection_pool",
                "priority": "high",
                "description": f"Connection pool utilization is high ({pool_stats['utilization_percent']}%). Consider increasing pool size.",
                "sql": "# Update database configuration: increase pool_size and max_overflow"
            })
        
        # Add general Hebrew optimization recommendations
        recommendations.extend([
            {
                "type": "hebrew_optimization",
                "priority": "medium",
                "description": "Ensure Hebrew locale is properly configured for optimal text processing",
                "sql": "SET lc_collate = 'he_IL.UTF-8'; SET default_text_search_config = 'hebrew';"
            },
            {
                "type": "maintenance",
                "priority": "low",
                "description": "Regular VACUUM and ANALYZE operations for optimal performance",
                "sql": "-- Schedule regular VACUUM ANALYZE operations"
            }
        ])
        
        return recommendations
    
    def _analyze_index_usage(self, plan: Dict) -> List[str]:
        """Analyze index usage from query execution plan."""
        index_usage = []
        
        def traverse_plan(node):
            if isinstance(node, dict):
                node_type = node.get('Node Type', '')
                if 'Index' in node_type:
                    index_name = node.get('Index Name', 'unknown')
                    index_usage.append(f"{node_type} on {index_name}")
                
                # Traverse child plans
                for child in node.get('Plans', []):
                    traverse_plan(child)
        
        traverse_plan(plan)
        return index_usage
    
    def _generate_performance_recommendations(self, plan: Dict) -> List[str]:
        """Generate performance recommendations based on execution plan."""
        recommendations = []
        
        def analyze_node(node):
            if isinstance(node, dict):
                node_type = node.get('Node Type', '')
                actual_rows = node.get('Actual Rows', 0)
                planned_rows = node.get('Plan Rows', 0)
                
                # Check for large row count differences
                if planned_rows > 0 and abs(actual_rows - planned_rows) / planned_rows > 0.5:
                    recommendations.append(f"Row estimate difference detected in {node_type}. Consider updating table statistics.")
                
                # Check for sequential scans on large tables
                if node_type == 'Seq Scan' and actual_rows > 1000:
                    relation_name = node.get('Relation Name', 'unknown')
                    recommendations.append(f"Sequential scan on large table {relation_name}. Consider adding appropriate indexes.")
                
                # Check for nested loop joins with high cost
                if node_type == 'Nested Loop' and node.get('Total Cost', 0) > 1000:
                    recommendations.append("High-cost nested loop detected. Consider optimizing join conditions or adding indexes.")
                
                # Traverse child plans
                for child in node.get('Plans', []):
                    analyze_node(child)
        
        analyze_node(plan)
        return recommendations