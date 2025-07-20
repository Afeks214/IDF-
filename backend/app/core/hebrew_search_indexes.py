#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hebrew Search Optimization - Database Indexes and Full-Text Search
IDF Testing Infrastructure
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger()


class HebrewSearchIndexes:
    """Manages Hebrew text search optimization indexes"""
    
    def __init__(self):
        self.indexes_created = []
    
    async def create_hebrew_search_indexes(self, session: AsyncSession) -> None:
        """Create optimized indexes for Hebrew text search"""
        
        indexes = [
            # 1. Inspections table indexes for Hebrew search
            {
                "name": "idx_inspections_hebrew_search",
                "query": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_hebrew_search
                ON inspections USING gin(
                    (
                        COALESCE(building_manager, '') || ' ' ||
                        COALESCE(red_team, '') || ' ' ||
                        COALESCE(inspection_type, '') || ' ' ||
                        COALESCE(inspection_leader, '') || ' ' ||
                        COALESCE(regulator_1, '') || ' ' ||
                        COALESCE(regulator_2, '') || ' ' ||
                        COALESCE(regulator_3, '') || ' ' ||
                        COALESCE(regulator_4, '') || ' ' ||
                        COALESCE(inspection_notes, '')
                    ) gin_trgm_ops
                );
                """,
                "description": "Full-text search index for Hebrew text in inspections"
            },
            
            # 2. Individual field indexes for targeted searches
            {
                "name": "idx_inspections_building_manager_trgm",
                "query": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_building_manager_trgm
                ON inspections USING gin(building_manager gin_trgm_ops);
                """,
                "description": "Trigram index for building manager Hebrew text search"
            },
            
            {
                "name": "idx_inspections_red_team_trgm",
                "query": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_red_team_trgm
                ON inspections USING gin(red_team gin_trgm_ops);
                """,
                "description": "Trigram index for red team Hebrew text search"
            },
            
            {
                "name": "idx_inspections_inspection_type_trgm",
                "query": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_inspection_type_trgm
                ON inspections USING gin(inspection_type gin_trgm_ops);
                """,
                "description": "Trigram index for inspection type Hebrew text search"
            },
            
            {
                "name": "idx_inspections_inspection_leader_trgm",
                "query": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_inspection_leader_trgm
                ON inspections USING gin(inspection_leader gin_trgm_ops);
                """,
                "description": "Trigram index for inspection leader Hebrew text search"
            },
            
            {
                "name": "idx_inspections_notes_trgm",
                "query": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_notes_trgm
                ON inspections USING gin(inspection_notes gin_trgm_ops);
                """,
                "description": "Trigram index for inspection notes Hebrew text search"
            },
            
            # 3. Composite indexes for common query patterns
            {
                "name": "idx_inspections_status_type_date",
                "query": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_status_type_date
                ON inspections (status, inspection_type, execution_schedule);
                """,
                "description": "Composite index for status, type, and date filtering"
            },
            
            {
                "name": "idx_inspections_building_status_date",
                "query": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_building_status_date
                ON inspections (building_id, status, execution_schedule);
                """,
                "description": "Composite index for building, status, and date filtering"
            },
            
            # 4. Buildings table indexes
            {
                "name": "idx_buildings_name_trgm",
                "query": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_buildings_name_trgm
                ON buildings USING gin(building_name gin_trgm_ops);
                """,
                "description": "Trigram index for building name Hebrew text search"
            },
            
            {
                "name": "idx_buildings_manager_trgm",
                "query": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_buildings_manager_trgm
                ON buildings USING gin(manager_name gin_trgm_ops);
                """,
                "description": "Trigram index for building manager Hebrew text search"
            },
            
            # 5. Inspection types table indexes
            {
                "name": "idx_inspection_types_hebrew_trgm",
                "query": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspection_types_hebrew_trgm
                ON inspection_types USING gin(type_name_hebrew gin_trgm_ops);
                """,
                "description": "Trigram index for inspection type Hebrew names"
            },
            
            # 6. Audit logs indexes for performance
            {
                "name": "idx_audit_logs_created_at",
                "query": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_created_at
                ON audit_logs (created_at);
                """,
                "description": "Index for audit logs date filtering"
            },
            
            # 7. Partial indexes for active records
            {
                "name": "idx_inspections_active_pending",
                "query": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_active_pending
                ON inspections (building_id, execution_schedule)
                WHERE status IN ('pending', 'scheduled', 'in_progress');
                """,
                "description": "Partial index for active/pending inspections"
            },
            
            {
                "name": "idx_buildings_active",
                "query": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_buildings_active
                ON buildings (building_code, building_name)
                WHERE is_active = true;
                """,
                "description": "Partial index for active buildings"
            }
        ]
        
        # Create pg_trgm extension if not exists
        try:
            await session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
            logger.info("pg_trgm extension created/verified")
        except Exception as e:
            logger.warning("Failed to create pg_trgm extension", error=str(e))
        
        # Create indexes
        for index in indexes:
            try:
                await session.execute(text(index["query"]))
                await session.commit()
                self.indexes_created.append(index["name"])
                logger.info(f"Created index: {index['name']} - {index['description']}")
            except Exception as e:
                logger.warning(f"Failed to create index {index['name']}", error=str(e))
                await session.rollback()
        
        logger.info(f"Successfully created {len(self.indexes_created)} indexes for Hebrew search optimization")
    
    async def create_fulltext_search_functions(self, session: AsyncSession) -> None:
        """Create custom PostgreSQL functions for Hebrew text search"""
        
        functions = [
            # 1. Hebrew text similarity function
            {
                "name": "hebrew_similarity",
                "query": """
                CREATE OR REPLACE FUNCTION hebrew_similarity(text1 TEXT, text2 TEXT)
                RETURNS FLOAT AS $$
                BEGIN
                    -- Normalize Hebrew text by removing nikud and extra spaces
                    text1 := regexp_replace(trim(text1), '\s+', ' ', 'g');
                    text2 := regexp_replace(trim(text2), '\s+', ' ', 'g');
                    
                    -- Use trigram similarity
                    RETURN similarity(text1, text2);
                END;
                $$ LANGUAGE plpgsql IMMUTABLE;
                """,
                "description": "Hebrew text similarity function using trigrams"
            },
            
            # 2. Hebrew text search ranking function
            {
                "name": "hebrew_search_rank",
                "query": """
                CREATE OR REPLACE FUNCTION hebrew_search_rank(
                    search_text TEXT,
                    target_text TEXT,
                    exact_match_bonus FLOAT DEFAULT 2.0,
                    prefix_match_bonus FLOAT DEFAULT 1.5
                )
                RETURNS FLOAT AS $$
                DECLARE
                    base_similarity FLOAT;
                    final_rank FLOAT;
                BEGIN
                    -- Calculate base similarity
                    base_similarity := hebrew_similarity(search_text, target_text);
                    final_rank := base_similarity;
                    
                    -- Boost exact matches
                    IF lower(trim(target_text)) = lower(trim(search_text)) THEN
                        final_rank := final_rank * exact_match_bonus;
                    END IF;
                    
                    -- Boost prefix matches
                    IF lower(trim(target_text)) LIKE lower(trim(search_text)) || '%' THEN
                        final_rank := final_rank * prefix_match_bonus;
                    END IF;
                    
                    RETURN final_rank;
                END;
                $$ LANGUAGE plpgsql IMMUTABLE;
                """,
                "description": "Hebrew text search ranking with exact and prefix match bonuses"
            },
            
            # 3. Hebrew text normalization function
            {
                "name": "normalize_hebrew_text",
                "query": """
                CREATE OR REPLACE FUNCTION normalize_hebrew_text(input_text TEXT)
                RETURNS TEXT AS $$
                BEGIN
                    -- Remove nikud (Hebrew vowel marks) and normalize spacing
                    RETURN regexp_replace(
                        regexp_replace(trim(input_text), '[\u05B0-\u05C7]', '', 'g'),
                        '\s+', ' ', 'g'
                    );
                END;
                $$ LANGUAGE plpgsql IMMUTABLE;
                """,
                "description": "Normalize Hebrew text by removing nikud and extra spaces"
            },
            
            # 4. Multi-field Hebrew search function
            {
                "name": "search_inspections_hebrew",
                "query": """
                CREATE OR REPLACE FUNCTION search_inspections_hebrew(
                    search_query TEXT,
                    similarity_threshold FLOAT DEFAULT 0.3,
                    max_results INTEGER DEFAULT 100
                )
                RETURNS TABLE (
                    id INTEGER,
                    building_id VARCHAR(10),
                    inspection_type VARCHAR(150),
                    inspection_leader VARCHAR(100),
                    building_manager VARCHAR(100),
                    red_team VARCHAR(200),
                    status VARCHAR(50),
                    execution_schedule DATE,
                    search_rank FLOAT
                ) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        i.id,
                        i.building_id,
                        i.inspection_type,
                        i.inspection_leader,
                        i.building_manager,
                        i.red_team,
                        i.status::VARCHAR(50),
                        i.execution_schedule,
                        GREATEST(
                            hebrew_search_rank(search_query, COALESCE(i.building_manager, '')),
                            hebrew_search_rank(search_query, COALESCE(i.red_team, '')),
                            hebrew_search_rank(search_query, COALESCE(i.inspection_type, '')),
                            hebrew_search_rank(search_query, COALESCE(i.inspection_leader, '')),
                            hebrew_search_rank(search_query, COALESCE(i.inspection_notes, ''))
                        ) as search_rank
                    FROM inspections i
                    WHERE 
                        hebrew_similarity(search_query, COALESCE(i.building_manager, '')) > similarity_threshold OR
                        hebrew_similarity(search_query, COALESCE(i.red_team, '')) > similarity_threshold OR
                        hebrew_similarity(search_query, COALESCE(i.inspection_type, '')) > similarity_threshold OR
                        hebrew_similarity(search_query, COALESCE(i.inspection_leader, '')) > similarity_threshold OR
                        hebrew_similarity(search_query, COALESCE(i.inspection_notes, '')) > similarity_threshold
                    ORDER BY search_rank DESC, i.created_at DESC
                    LIMIT max_results;
                END;
                $$ LANGUAGE plpgsql;
                """,
                "description": "Multi-field Hebrew text search function for inspections"
            }
        ]
        
        # Create functions
        for func in functions:
            try:
                await session.execute(text(func["query"]))
                await session.commit()
                logger.info(f"Created function: {func['name']} - {func['description']}")
            except Exception as e:
                logger.warning(f"Failed to create function {func['name']}", error=str(e))
                await session.rollback()
        
        logger.info(f"Successfully created {len(functions)} Hebrew search functions")
    
    async def analyze_tables_for_performance(self, session: AsyncSession) -> None:
        """Analyze tables to update statistics for better query planning"""
        
        tables = [
            "inspections",
            "buildings", 
            "inspection_types",
            "regulators",
            "audit_logs"
        ]
        
        for table in tables:
            try:
                await session.execute(text(f"ANALYZE {table};"))
                logger.info(f"Analyzed table: {table}")
            except Exception as e:
                logger.warning(f"Failed to analyze table {table}", error=str(e))
        
        await session.commit()
        logger.info("Table analysis completed")
    
    async def create_materialized_views(self, session: AsyncSession) -> None:
        """Create materialized views for frequently accessed data"""
        
        views = [
            # 1. Active inspections summary
            {
                "name": "mv_active_inspections_summary",
                "query": """
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_active_inspections_summary AS
                SELECT 
                    i.building_id,
                    b.building_name,
                    i.inspection_type,
                    i.status,
                    i.inspection_leader,
                    i.execution_schedule,
                    i.created_at,
                    i.updated_at
                FROM inspections i
                JOIN buildings b ON i.building_id = b.building_code
                WHERE i.status IN ('pending', 'scheduled', 'in_progress')
                AND b.is_active = true
                ORDER BY i.execution_schedule ASC;
                """,
                "description": "Materialized view for active inspections with building info"
            },
            
            # 2. Inspection statistics by building
            {
                "name": "mv_inspection_stats_by_building",
                "query": """
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_inspection_stats_by_building AS
                SELECT 
                    b.building_code,
                    b.building_name,
                    COUNT(i.id) as total_inspections,
                    COUNT(CASE WHEN i.status = 'completed' THEN 1 END) as completed_inspections,
                    COUNT(CASE WHEN i.status IN ('pending', 'scheduled') THEN 1 END) as pending_inspections,
                    COUNT(CASE WHEN i.status = 'in_progress' THEN 1 END) as in_progress_inspections,
                    MAX(i.execution_schedule) as latest_inspection_date,
                    MIN(i.execution_schedule) as earliest_inspection_date
                FROM buildings b
                LEFT JOIN inspections i ON b.building_code = i.building_id
                WHERE b.is_active = true
                GROUP BY b.building_code, b.building_name
                ORDER BY total_inspections DESC;
                """,
                "description": "Materialized view for inspection statistics by building"
            },
            
            # 3. Recent activity summary
            {
                "name": "mv_recent_activity_summary",
                "query": """
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_recent_activity_summary AS
                SELECT 
                    'inspection' as activity_type,
                    i.id::TEXT as activity_id,
                    i.building_id,
                    b.building_name,
                    i.inspection_type as description,
                    i.status as activity_status,
                    i.updated_at as activity_date
                FROM inspections i
                JOIN buildings b ON i.building_id = b.building_code
                WHERE i.updated_at > NOW() - INTERVAL '30 days'
                ORDER BY i.updated_at DESC;
                """,
                "description": "Materialized view for recent activity across the system"
            }
        ]
        
        # Create materialized views
        for view in views:
            try:
                await session.execute(text(view["query"]))
                await session.commit()
                logger.info(f"Created materialized view: {view['name']} - {view['description']}")
            except Exception as e:
                logger.warning(f"Failed to create materialized view {view['name']}", error=str(e))
                await session.rollback()
        
        logger.info(f"Successfully created {len(views)} materialized views")
    
    async def create_refresh_functions(self, session: AsyncSession) -> None:
        """Create functions to refresh materialized views"""
        
        refresh_function = """
        CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
        RETURNS VOID AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY mv_active_inspections_summary;
            REFRESH MATERIALIZED VIEW CONCURRENTLY mv_inspection_stats_by_building;
            REFRESH MATERIALIZED VIEW CONCURRENTLY mv_recent_activity_summary;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        try:
            await session.execute(text(refresh_function))
            await session.commit()
            logger.info("Created materialized view refresh function")
        except Exception as e:
            logger.warning("Failed to create refresh function", error=str(e))
            await session.rollback()
    
    async def setup_all_optimizations(self, session: AsyncSession) -> None:
        """Setup all Hebrew search optimizations"""
        logger.info("Starting Hebrew search optimization setup")
        
        # 1. Create indexes
        await self.create_hebrew_search_indexes(session)
        
        # 2. Create search functions
        await self.create_fulltext_search_functions(session)
        
        # 3. Create materialized views
        await self.create_materialized_views(session)
        
        # 4. Create refresh functions
        await self.create_refresh_functions(session)
        
        # 5. Analyze tables
        await self.analyze_tables_for_performance(session)
        
        logger.info("Hebrew search optimization setup completed")
    
    async def get_index_usage_stats(self, session: AsyncSession) -> list:
        """Get index usage statistics"""
        stats_query = """
        SELECT 
            schemaname,
            tablename,
            indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch
        FROM pg_stat_user_indexes
        WHERE indexname LIKE 'idx_%hebrew%' OR indexname LIKE 'idx_%trgm%'
        ORDER BY idx_scan DESC;
        """
        
        try:
            result = await session.execute(text(stats_query))
            return [dict(row) for row in result.fetchall()]
        except Exception as e:
            logger.warning("Failed to get index usage stats", error=str(e))
            return []


# Global instance
hebrew_search = HebrewSearchIndexes()