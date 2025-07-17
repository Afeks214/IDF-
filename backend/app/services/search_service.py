"""
Hebrew-optimized search service for IDF Testing Infrastructure.
Implements full-text search with PostgreSQL Hebrew support.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re
import unicodedata

from sqlalchemy import func, text, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.core import Inspection, Building
from ..models.base import BaseModel


class HebrewSearchService:
    """Search service optimized for Hebrew text using PostgreSQL features."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.hebrew_stop_words = {
            "את", "אל", "על", "אם", "כי", "לא", "של", "אין", "יש", "זה", "זו", "זהו",
            "היא", "הוא", "הם", "הן", "אני", "אתה", "את", "אנחנו", "אתם", "אתן",
            "בשביל", "כדי", "למען", "בגלל", "אחרי", "לפני", "תחת", "מעל", "ליד"
        }
    
    async def search_inspections(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search inspections using Hebrew-optimized full-text search.
        
        Args:
            query: Search query (Hebrew or English)
            filters: Additional filters
            limit: Maximum results to return
            
        Returns:
            List of search results with ranking
        """
        # Preprocess search query
        processed_query = self._preprocess_hebrew_query(query)
        
        if not processed_query.strip():
            return []
        
        # Build search vector for multiple fields
        search_vector = func.to_tsvector(
            'hebrew',
            func.coalesce(Inspection.inspection_type, '') + ' ' +
            func.coalesce(Inspection.inspection_leader, '') + ' ' +
            func.coalesce(Inspection.building_manager, '') + ' ' +
            func.coalesce(Inspection.red_team, '') + ' ' +
            func.coalesce(Inspection.inspection_notes, '') + ' ' +
            func.coalesce(Inspection.regulator_1, '') + ' ' +
            func.coalesce(Inspection.regulator_2, '') + ' ' +
            func.coalesce(Inspection.regulator_3, '') + ' ' +
            func.coalesce(Inspection.regulator_4, '')
        )
        
        # Create search query
        search_tsquery = func.plainto_tsquery('hebrew', processed_query)
        
        # Base query with ranking
        base_query = select(
            Inspection,
            func.ts_rank(search_vector, search_tsquery).label('rank'),
            func.ts_headline(
                'hebrew',
                func.coalesce(Inspection.inspection_notes, ''),
                search_tsquery,
                'MaxWords=20, MinWords=5, MaxFragments=3'
            ).label('headline')
        ).where(
            search_vector.op('@@')(search_tsquery)
        )
        
        # Apply additional filters
        if filters:
            base_query = self._apply_search_filters(base_query, filters)
        
        # Order by relevance and limit results
        base_query = base_query.order_by(text('rank DESC')).limit(limit)
        
        # Execute query
        result = await self.session.execute(base_query)
        rows = result.all()
        
        # Format results
        search_results = []
        for row in rows:
            inspection = row[0]
            rank = row[1]
            headline = row[2]
            
            result_data = {
                "inspection": inspection.to_dict(),
                "rank": float(rank),
                "headline": headline,
                "match_type": self._determine_match_type(inspection, processed_query)
            }
            search_results.append(result_data)
        
        return search_results
    
    async def search_buildings(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search buildings with Hebrew support."""
        processed_query = self._preprocess_hebrew_query(query)
        
        if not processed_query.strip():
            return []
        
        # Search in building names and manager names
        search_vector = func.to_tsvector(
            'hebrew',
            func.coalesce(Building.building_name, '') + ' ' +
            func.coalesce(Building.manager_name, '') + ' ' +
            func.coalesce(Building.building_code, '')
        )
        
        search_tsquery = func.plainto_tsquery('hebrew', processed_query)
        
        base_query = select(
            Building,
            func.ts_rank(search_vector, search_tsquery).label('rank')
        ).where(
            or_(
                search_vector.op('@@')(search_tsquery),
                Building.building_code.ilike(f"%{query}%"),
                Building.building_name.ilike(f"%{query}%")
            )
        ).order_by(text('rank DESC')).limit(limit)
        
        result = await self.session.execute(base_query)
        rows = result.all()
        
        return [
            {
                "building": row[0].to_dict(),
                "rank": float(row[1]) if row[1] else 0.0
            }
            for row in rows
        ]
    
    async def suggest_search_terms(self, partial_query: str, limit: int = 10) -> List[str]:
        """
        Provide search suggestions based on partial Hebrew input.
        
        Args:
            partial_query: Partial search string
            limit: Maximum suggestions to return
            
        Returns:
            List of suggested search terms
        """
        if len(partial_query) < 2:
            return []
        
        suggestions = set()
        
        # Search in inspection types
        result = await self.session.execute(
            select(Inspection.inspection_type)
            .where(Inspection.inspection_type.ilike(f"%{partial_query}%"))
            .distinct()
            .limit(limit)
        )
        for row in result:
            if row[0]:
                suggestions.add(row[0])
        
        # Search in leader names
        result = await self.session.execute(
            select(Inspection.inspection_leader)
            .where(Inspection.inspection_leader.ilike(f"%{partial_query}%"))
            .distinct()
            .limit(limit)
        )
        for row in result:
            if row[0]:
                suggestions.add(row[0])
        
        # Search in building managers
        result = await self.session.execute(
            select(Inspection.building_manager)
            .where(Inspection.building_manager.ilike(f"%{partial_query}%"))
            .distinct()
            .limit(limit)
        )
        for row in result:
            if row[0]:
                suggestions.add(row[0])
        
        return sorted(list(suggestions))[:limit]
    
    async def get_search_analytics(self) -> Dict[str, Any]:
        """Get search analytics and popular terms."""
        
        # Most common inspection types
        type_result = await self.session.execute(
            select(
                Inspection.inspection_type,
                func.count(Inspection.id).label('count')
            )
            .where(Inspection.inspection_type.isnot(None))
            .group_by(Inspection.inspection_type)
            .order_by(text('count DESC'))
            .limit(10)
        )
        
        popular_types = [
            {"term": row[0], "count": row[1]}
            for row in type_result.all()
        ]
        
        # Most active leaders
        leader_result = await self.session.execute(
            select(
                Inspection.inspection_leader,
                func.count(Inspection.id).label('count')
            )
            .where(Inspection.inspection_leader.isnot(None))
            .group_by(Inspection.inspection_leader)
            .order_by(text('count DESC'))
            .limit(10)
        )
        
        active_leaders = [
            {"term": row[0], "count": row[1]}
            for row in leader_result.all()
        ]
        
        # Most active buildings
        building_result = await self.session.execute(
            select(
                Inspection.building_id,
                func.count(Inspection.id).label('count')
            )
            .where(Inspection.building_id.isnot(None))
            .group_by(Inspection.building_id)
            .order_by(text('count DESC'))
            .limit(10)
        )
        
        active_buildings = [
            {"term": row[0], "count": row[1]}
            for row in building_result.all()
        ]
        
        return {
            "popular_inspection_types": popular_types,
            "active_leaders": active_leaders,
            "active_buildings": active_buildings
        }
    
    def _preprocess_hebrew_query(self, query: str) -> str:
        """
        Preprocess Hebrew search query for better matching.
        
        Args:
            query: Raw search query
            
        Returns:
            Processed query optimized for Hebrew search
        """
        if not query:
            return ""
        
        # Normalize Unicode characters
        query = unicodedata.normalize('NFKC', query)
        
        # Remove extra whitespace
        query = ' '.join(query.split())
        
        # Remove Hebrew stop words
        words = query.split()
        filtered_words = [
            word for word in words 
            if word not in self.hebrew_stop_words and len(word) > 1
        ]
        
        # If all words were filtered out, return original query
        if not filtered_words:
            return query
        
        return ' '.join(filtered_words)
    
    def _apply_search_filters(self, query, filters: Dict[str, Any]):
        """Apply additional filters to search query."""
        
        if "building_id" in filters and filters["building_id"]:
            query = query.where(Inspection.building_id == filters["building_id"])
        
        if "status" in filters and filters["status"]:
            query = query.where(Inspection.status == filters["status"])
        
        if "date_from" in filters and filters["date_from"]:
            query = query.where(Inspection.execution_schedule >= filters["date_from"])
        
        if "date_to" in filters and filters["date_to"]:
            query = query.where(Inspection.execution_schedule <= filters["date_to"])
        
        if "inspection_type" in filters and filters["inspection_type"]:
            query = query.where(Inspection.inspection_type == filters["inspection_type"])
        
        return query
    
    def _determine_match_type(self, inspection: Inspection, query: str) -> str:
        """Determine what type of match was found."""
        query_lower = query.lower()
        
        if inspection.inspection_type and query_lower in inspection.inspection_type.lower():
            return "inspection_type"
        elif inspection.inspection_leader and query_lower in inspection.inspection_leader.lower():
            return "leader"
        elif inspection.building_manager and query_lower in inspection.building_manager.lower():
            return "manager"
        elif inspection.red_team and query_lower in inspection.red_team.lower():
            return "team"
        elif inspection.inspection_notes and query_lower in inspection.inspection_notes.lower():
            return "notes"
        else:
            return "general"


class SearchIndexManager:
    """Manages search indexes for optimal Hebrew text search performance."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_hebrew_indexes(self):
        """Create Hebrew-optimized search indexes."""
        
        # Create GIN index for inspection search
        inspection_index = """
        CREATE INDEX IF NOT EXISTS idx_inspections_search_hebrew
        ON inspections USING gin(
            to_tsvector('hebrew', 
                coalesce(inspection_type, '') || ' ' ||
                coalesce(inspection_leader, '') || ' ' ||
                coalesce(building_manager, '') || ' ' ||
                coalesce(red_team, '') || ' ' ||
                coalesce(inspection_notes, '') || ' ' ||
                coalesce(regulator_1, '') || ' ' ||
                coalesce(regulator_2, '') || ' ' ||
                coalesce(regulator_3, '') || ' ' ||
                coalesce(regulator_4, '')
            )
        )
        """
        
        # Create GIN index for building search
        building_index = """
        CREATE INDEX IF NOT EXISTS idx_buildings_search_hebrew
        ON buildings USING gin(
            to_tsvector('hebrew',
                coalesce(building_name, '') || ' ' ||
                coalesce(manager_name, '') || ' ' ||
                coalesce(building_code, '')
            )
        )
        """
        
        # Create trigram indexes for partial matching
        trigram_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_inspections_type_trgm ON inspections USING gin(inspection_type gin_trgm_ops)",
            "CREATE INDEX IF NOT EXISTS idx_inspections_leader_trgm ON inspections USING gin(inspection_leader gin_trgm_ops)",
            "CREATE INDEX IF NOT EXISTS idx_buildings_name_trgm ON buildings USING gin(building_name gin_trgm_ops)",
        ]
        
        try:
            # Enable required extensions
            await self.session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            await self.session.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
            
            # Create indexes
            await self.session.execute(text(inspection_index))
            await self.session.execute(text(building_index))
            
            for index_sql in trigram_indexes:
                await self.session.execute(text(index_sql))
            
            await self.session.commit()
            
        except Exception as e:
            await self.session.rollback()
            raise Exception(f"Failed to create Hebrew search indexes: {str(e)}")
    
    async def update_search_statistics(self):
        """Update PostgreSQL search statistics for better query planning."""
        try:
            await self.session.execute(text("ANALYZE inspections"))
            await self.session.execute(text("ANALYZE buildings"))
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise Exception(f"Failed to update search statistics: {str(e)}")
    
    async def get_index_usage_stats(self) -> Dict[str, Any]:
        """Get statistics about search index usage."""
        
        index_stats_query = """
        SELECT 
            schemaname,
            tablename,
            indexname,
            idx_tup_read,
            idx_tup_fetch
        FROM pg_stat_user_indexes 
        WHERE indexname LIKE '%search%' OR indexname LIKE '%trgm%'
        ORDER BY idx_tup_read DESC
        """
        
        result = await self.session.execute(text(index_stats_query))
        rows = result.all()
        
        return [
            {
                "schema": row[0],
                "table": row[1],
                "index": row[2],
                "tuples_read": row[3],
                "tuples_fetched": row[4]
            }
            for row in rows
        ]