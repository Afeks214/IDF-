# Database Query Optimization Plan
## High-Performance Data Layer for Hebrew Processing System

### Overview
This document outlines comprehensive database optimization strategies specifically designed for Hebrew data processing applications, ensuring maximum query performance, efficient indexing, and optimal resource utilization.

## 1. DATABASE ARCHITECTURE OPTIMIZATION

### 1.1 Schema Design for Hebrew Data
```sql
-- Optimized table structure for Hebrew test data
CREATE TABLE test_documents (
    id SERIAL PRIMARY KEY,
    document_id UUID UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hebrew_normalized TEXT, -- Normalized Hebrew text for searching
    metadata JSONB DEFAULT '{}',
    test_category VARCHAR(50),
    test_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    search_vector tsvector -- Full-text search vector
);

-- Separate table for performance-critical lookups
CREATE TABLE test_summary (
    document_id UUID PRIMARY KEY REFERENCES test_documents(document_id),
    title_normalized TEXT,
    category VARCHAR(50),
    word_count INTEGER,
    character_count INTEGER,
    hebrew_word_count INTEGER,
    last_indexed_at TIMESTAMP WITH TIME ZONE
);

-- Table for Hebrew word analysis
CREATE TABLE hebrew_words (
    id SERIAL PRIMARY KEY,
    word TEXT UNIQUE NOT NULL,
    normalized_word TEXT NOT NULL,
    root_word TEXT,
    frequency INTEGER DEFAULT 1,
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document-word relationship for advanced search
CREATE TABLE document_words (
    document_id UUID REFERENCES test_documents(document_id),
    word_id INTEGER REFERENCES hebrew_words(id),
    position_array INTEGER[],
    tf_score FLOAT,
    PRIMARY KEY (document_id, word_id)
);
```

### 1.2 Advanced Indexing Strategy
```sql
-- Primary indexes for fast lookups
CREATE INDEX CONCURRENTLY idx_test_documents_category_date 
ON test_documents (test_category, test_date DESC) 
WHERE status = 'active';

CREATE INDEX CONCURRENTLY idx_test_documents_created_at 
ON test_documents (created_at DESC) 
WHERE status = 'active';

-- Hebrew text search indexes
CREATE INDEX CONCURRENTLY idx_test_documents_search_vector 
ON test_documents USING gin(search_vector);

CREATE INDEX CONCURRENTLY idx_test_documents_content_normalized 
ON test_documents USING gin(content_hebrew_normalized gin_trgm_ops);

-- JSONB metadata indexes
CREATE INDEX CONCURRENTLY idx_test_documents_metadata_gin 
ON test_documents USING gin(metadata);

CREATE INDEX CONCURRENTLY idx_test_documents_metadata_specific 
ON test_documents ((metadata->>'priority')) 
WHERE metadata->>'priority' IS NOT NULL;

-- Composite indexes for common query patterns
CREATE INDEX CONCURRENTLY idx_test_documents_category_status_date 
ON test_documents (test_category, status, test_date DESC);

CREATE INDEX CONCURRENTLY idx_test_documents_status_updated 
ON test_documents (status, updated_at DESC) 
WHERE updated_at > NOW() - INTERVAL '30 days';

-- Partial indexes for performance
CREATE INDEX CONCURRENTLY idx_test_documents_recent_active 
ON test_documents (created_at DESC) 
WHERE status = 'active' AND created_at > NOW() - INTERVAL '6 months';

-- Hebrew word indexes
CREATE INDEX CONCURRENTLY idx_hebrew_words_normalized 
ON hebrew_words (normalized_word);

CREATE INDEX CONCURRENTLY idx_hebrew_words_root 
ON hebrew_words (root_word) 
WHERE root_word IS NOT NULL;

CREATE INDEX CONCURRENTLY idx_hebrew_words_frequency 
ON hebrew_words (frequency DESC);

-- Document-word relationship indexes
CREATE INDEX CONCURRENTLY idx_document_words_document_id 
ON document_words (document_id);

CREATE INDEX CONCURRENTLY idx_document_words_word_id_tf 
ON document_words (word_id, tf_score DESC);
```

### 1.3 Database Configuration Optimization
```sql
-- PostgreSQL configuration optimizations
-- postgresql.conf settings

-- Memory settings
shared_buffers = '256MB'                    -- 25% of system RAM
work_mem = '16MB'                          -- Per-operation memory
maintenance_work_mem = '128MB'             -- For maintenance operations
effective_cache_size = '1GB'              -- OS cache estimate

-- Connection and performance
max_connections = 100
shared_preload_libraries = 'pg_stat_statements'

-- Checkpoint and WAL settings
checkpoint_timeout = '10min'
checkpoint_completion_target = 0.9
wal_buffers = '16MB'
wal_level = 'replica'

-- Query planner settings
random_page_cost = 1.1                    -- SSD optimization
effective_io_concurrency = 200           -- SSD concurrent I/O

-- Hebrew text search configuration
default_text_search_config = 'hebrew'

-- Create Hebrew text search configuration
CREATE TEXT SEARCH CONFIGURATION hebrew (COPY=simple);
CREATE TEXT SEARCH DICTIONARY hebrew_stem (
    TEMPLATE = simple,
    STOPWORDS = hebrew
);
ALTER TEXT SEARCH CONFIGURATION hebrew
ALTER MAPPING FOR asciiword, asciihword, hword_asciipart, word, hword, hword_part
WITH hebrew_stem;
```

## 2. QUERY OPTIMIZATION STRATEGIES

### 2.1 Optimized Query Patterns
```python
# High-performance database query class
import asyncpg
import asyncio
from typing import List, Dict, Optional, Tuple
import json
import time
from contextlib import asynccontextmanager

class OptimizedDatabaseQueries:
    def __init__(self, database_url: str, pool_size: int = 20):
        self.database_url = database_url
        self.pool_size = pool_size
        self.pool = None
        
    async def initialize_pool(self):
        """Initialize connection pool with optimizations"""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=5,
            max_size=self.pool_size,
            command_timeout=60,
            server_settings={
                'application_name': 'hebrew_search_app',
                'tcp_keepalives_idle': '600',
                'tcp_keepalives_interval': '30',
                'tcp_keepalives_count': '3',
            }
        )
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection with automatic cleanup"""
        async with self.pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                # Log query errors for monitoring
                print(f"Database error: {e}")
                raise
    
    async def search_documents_optimized(
        self, 
        query: str, 
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Optimized document search with minimal data transfer"""
        
        # Prepare base query with proper indexing hints
        base_query = """
        SELECT 
            document_id,
            title,
            LEFT(content, 200) as snippet,
            test_category,
            test_date,
            ts_rank(search_vector, plainto_tsquery('hebrew', $1)) as rank,
            metadata->>'priority' as priority
        FROM test_documents 
        WHERE status = 'active'
        """
        
        params = [query]
        conditions = []
        param_count = 1
        
        # Add search condition
        if query.strip():
            conditions.append(f"search_vector @@ plainto_tsquery('hebrew', ${param_count})")
        
        # Add category filter
        if category:
            param_count += 1
            conditions.append(f"test_category = ${param_count}")
            params.append(category)
        
        # Add date filters
        if date_from:
            param_count += 1
            conditions.append(f"test_date >= ${param_count}")
            params.append(date_from)
        
        if date_to:
            param_count += 1
            conditions.append(f"test_date <= ${param_count}")
            params.append(date_to)
        
        # Combine conditions
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        
        # Add ordering and pagination
        base_query += """
        ORDER BY 
            CASE WHEN $1 != '' THEN ts_rank(search_vector, plainto_tsquery('hebrew', $1)) END DESC,
            test_date DESC
        LIMIT $%d OFFSET $%d
        """ % (param_count + 1, param_count + 2)
        
        params.extend([limit, offset])
        
        async with self.get_connection() as conn:
            start_time = time.time()
            
            # Use prepared statement for repeated queries
            rows = await conn.fetch(base_query, *params)
            
            query_time = time.time() - start_time
            
            # Log slow queries
            if query_time > 0.1:  # 100ms threshold
                print(f"Slow query detected: {query_time:.3f}s - Query: {query[:50]}")
            
            return [dict(row) for row in rows]
    
    async def get_document_by_id(self, document_id: str) -> Optional[Dict]:
        """Optimized single document retrieval"""
        query = """
        SELECT 
            document_id,
            title,
            content,
            test_category,
            test_date,
            metadata,
            created_at,
            updated_at
        FROM test_documents 
        WHERE document_id = $1 AND status = 'active'
        """
        
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, document_id)
            return dict(row) if row else None
    
    async def get_category_statistics(self) -> List[Dict]:
        """Get aggregated statistics by category with caching"""
        query = """
        SELECT 
            test_category,
            COUNT(*) as document_count,
            AVG(CHARACTER_LENGTH(content)) as avg_content_length,
            MAX(test_date) as latest_date,
            MIN(test_date) as earliest_date
        FROM test_documents 
        WHERE status = 'active'
        GROUP BY test_category
        ORDER BY document_count DESC
        """
        
        async with self.get_connection() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
    
    async def bulk_insert_documents(self, documents: List[Dict]) -> int:
        """Optimized bulk document insertion"""
        if not documents:
            return 0
        
        # Prepare data for COPY operation
        insert_query = """
        INSERT INTO test_documents 
        (document_id, title, content, content_hebrew_normalized, 
         test_category, test_date, metadata, search_vector)
        VALUES ($1, $2, $3, $4, $5, $6, $7, to_tsvector('hebrew', $3))
        ON CONFLICT (document_id) 
        DO UPDATE SET
            title = EXCLUDED.title,
            content = EXCLUDED.content,
            content_hebrew_normalized = EXCLUDED.content_hebrew_normalized,
            test_category = EXCLUDED.test_category,
            test_date = EXCLUDED.test_date,
            metadata = EXCLUDED.metadata,
            search_vector = EXCLUDED.search_vector,
            updated_at = NOW()
        """
        
        async with self.get_connection() as conn:
            async with conn.transaction():
                inserted_count = 0
                
                # Use executemany for batch processing
                for doc in documents:
                    await conn.execute(
                        insert_query,
                        doc['document_id'],
                        doc['title'],
                        doc['content'],
                        doc.get('content_hebrew_normalized', ''),
                        doc.get('test_category'),
                        doc.get('test_date'),
                        json.dumps(doc.get('metadata', {}))
                    )
                    inserted_count += 1
                
                return inserted_count
    
    async def update_search_vectors(self, batch_size: int = 1000) -> int:
        """Batch update search vectors for better performance"""
        update_query = """
        UPDATE test_documents 
        SET search_vector = to_tsvector('hebrew', title || ' ' || content),
            updated_at = NOW()
        WHERE search_vector IS NULL 
           OR updated_at < NOW() - INTERVAL '1 day'
        LIMIT $1
        """
        
        async with self.get_connection() as conn:
            result = await conn.execute(update_query, batch_size)
            # Extract number of updated rows from result string
            return int(result.split()[-1]) if result.startswith('UPDATE') else 0
    
    async def get_search_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """Fast autocomplete suggestions using trigram similarity"""
        query = """
        SELECT DISTINCT normalized_word
        FROM hebrew_words 
        WHERE normalized_word % $1  -- Trigram similarity
           OR normalized_word LIKE $2
        ORDER BY 
            similarity(normalized_word, $1) DESC,
            frequency DESC
        LIMIT $3
        """
        
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, prefix, f"{prefix}%", limit)
            return [row['normalized_word'] for row in rows]
    
    async def get_database_statistics(self) -> Dict:
        """Get comprehensive database performance statistics"""
        stats_queries = {
            'table_sizes': """
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """,
            
            'index_usage': """
                SELECT 
                    indexrelname as index_name,
                    idx_tup_read,
                    idx_tup_fetch,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                FROM pg_stat_user_indexes 
                ORDER BY idx_tup_read DESC
            """,
            
            'slow_queries': """
                SELECT 
                    query,
                    calls,
                    total_time,
                    mean_time,
                    rows
                FROM pg_stat_statements 
                WHERE query NOT LIKE '%pg_stat_statements%'
                ORDER BY mean_time DESC 
                LIMIT 10
            """,
            
            'connection_stats': """
                SELECT 
                    state,
                    COUNT(*) as connection_count
                FROM pg_stat_activity 
                WHERE datname = current_database()
                GROUP BY state
            """
        }
        
        results = {}
        
        async with self.get_connection() as conn:
            for stat_name, query in stats_queries.items():
                try:
                    rows = await conn.fetch(query)
                    results[stat_name] = [dict(row) for row in rows]
                except Exception as e:
                    results[stat_name] = f"Error: {str(e)}"
        
        return results
    
    async def cleanup_old_data(self, days_old: int = 365) -> int:
        """Clean up old inactive data"""
        cleanup_query = """
        DELETE FROM test_documents 
        WHERE status = 'inactive' 
          AND updated_at < NOW() - INTERVAL '%d days'
        """ % days_old
        
        async with self.get_connection() as conn:
            result = await conn.execute(cleanup_query)
            return int(result.split()[-1]) if result.startswith('DELETE') else 0
    
    async def close(self):
        """Close database pool"""
        if self.pool:
            await self.pool.close()
```

### 2.2 Query Performance Monitoring
```python
import time
import asyncio
from collections import defaultdict, deque
from typing import Dict, List
import json

class DatabasePerformanceMonitor:
    def __init__(self, max_slow_queries: int = 100):
        self.query_times = deque(maxlen=1000)
        self.slow_queries = deque(maxlen=max_slow_queries)
        self.query_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.connection_pool_stats = {}
        
    def record_query(self, query: str, execution_time: float, row_count: int = 0):
        """Record query execution metrics"""
        timestamp = time.time()
        
        # Normalize query for pattern matching
        query_pattern = self.normalize_query(query)
        
        self.query_times.append({
            'timestamp': timestamp,
            'query_pattern': query_pattern,
            'execution_time': execution_time,
            'row_count': row_count
        })
        
        self.query_counts[query_pattern] += 1
        
        # Track slow queries
        if execution_time > 0.1:  # 100ms threshold
            self.slow_queries.append({
                'timestamp': timestamp,
                'query': query[:200],  # Truncate for storage
                'execution_time': execution_time,
                'row_count': row_count
            })
    
    def record_error(self, query: str, error: str):
        """Record database errors"""
        query_pattern = self.normalize_query(query)
        self.error_counts[query_pattern] += 1
    
    def normalize_query(self, query: str) -> str:
        """Normalize query to identify patterns"""
        # Remove parameter values and normalize whitespace
        import re
        
        # Replace parameter placeholders
        normalized = re.sub(r'\$\d+', '?', query)
        
        # Replace string literals
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        
        # Replace numbers
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        
        # Normalize whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized[:100]  # Limit length
    
    def get_performance_summary(self, time_window_minutes: int = 60) -> Dict:
        """Get performance summary for specified time window"""
        cutoff_time = time.time() - (time_window_minutes * 60)
        
        recent_queries = [
            q for q in self.query_times 
            if q['timestamp'] > cutoff_time
        ]
        
        if not recent_queries:
            return {'message': 'No recent queries'}
        
        execution_times = [q['execution_time'] for q in recent_queries]
        row_counts = [q['row_count'] for q in recent_queries]
        
        # Calculate percentiles
        sorted_times = sorted(execution_times)
        p50 = sorted_times[len(sorted_times) // 2] if sorted_times else 0
        p95 = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0
        p99 = sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0
        
        return {
            'time_window_minutes': time_window_minutes,
            'total_queries': len(recent_queries),
            'queries_per_minute': len(recent_queries) / time_window_minutes,
            'execution_time': {
                'avg': sum(execution_times) / len(execution_times),
                'min': min(execution_times),
                'max': max(execution_times),
                'p50': p50,
                'p95': p95,
                'p99': p99
            },
            'row_counts': {
                'avg': sum(row_counts) / len(row_counts) if row_counts else 0,
                'total': sum(row_counts)
            },
            'slow_query_count': len([q for q in recent_queries if q['execution_time'] > 0.1]),
            'top_query_patterns': self.get_top_query_patterns(recent_queries),
            'error_summary': dict(self.error_counts)
        }
    
    def get_top_query_patterns(self, queries: List[Dict], limit: int = 5) -> List[Dict]:
        """Get most frequent query patterns"""
        pattern_stats = defaultdict(lambda: {'count': 0, 'total_time': 0, 'avg_time': 0})
        
        for query in queries:
            pattern = query['query_pattern']
            pattern_stats[pattern]['count'] += 1
            pattern_stats[pattern]['total_time'] += query['execution_time']
        
        # Calculate averages and sort
        for stats in pattern_stats.values():
            stats['avg_time'] = stats['total_time'] / stats['count']
        
        sorted_patterns = sorted(
            pattern_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        return [
            {
                'pattern': pattern,
                'count': stats['count'],
                'avg_time': stats['avg_time'],
                'total_time': stats['total_time']
            }
            for pattern, stats in sorted_patterns[:limit]
        ]
    
    def get_slow_queries_report(self, limit: int = 10) -> List[Dict]:
        """Get recent slow queries report"""
        sorted_slow = sorted(
            self.slow_queries,
            key=lambda x: x['execution_time'],
            reverse=True
        )
        
        return list(sorted_slow)[:limit]
    
    def export_metrics(self) -> Dict:
        """Export all metrics for external monitoring"""
        return {
            'timestamp': time.time(),
            'performance_summary': self.get_performance_summary(),
            'slow_queries': self.get_slow_queries_report(),
            'query_patterns': dict(self.query_counts),
            'error_counts': dict(self.error_counts),
            'connection_pool_stats': self.connection_pool_stats
        }

# Global database performance monitor
db_monitor = DatabasePerformanceMonitor()
```

## 3. CONNECTION POOLING & RESOURCE MANAGEMENT

### 3.1 Advanced Connection Pool Configuration
```python
import asyncpg
import asyncio
import time
from typing import Optional, Dict, Any
import logging

class AdvancedConnectionPool:
    def __init__(
        self,
        database_url: str,
        min_size: int = 5,
        max_size: int = 20,
        command_timeout: int = 60,
        health_check_interval: int = 30
    ):
        self.database_url = database_url
        self.min_size = min_size
        self.max_size = max_size
        self.command_timeout = command_timeout
        self.health_check_interval = health_check_interval
        
        self.pool: Optional[asyncpg.Pool] = None
        self.health_check_task: Optional[asyncio.Task] = None
        self.stats = {
            'connections_created': 0,
            'connections_closed': 0,
            'queries_executed': 0,
            'query_errors': 0,
            'pool_exhaustions': 0
        }
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize connection pool with advanced settings"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.min_size,
                max_size=self.max_size,
                command_timeout=self.command_timeout,
                setup=self._setup_connection,
                init=self._init_connection,
                server_settings={
                    'application_name': 'hebrew_processing_system',
                    'tcp_keepalives_idle': '600',
                    'tcp_keepalives_interval': '30',
                    'tcp_keepalives_count': '3',
                    'statement_timeout': '300000',  # 5 minutes
                    'lock_timeout': '30000',        # 30 seconds
                    'idle_in_transaction_session_timeout': '300000'
                }
            )
            
            # Start health check task
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            self.logger.info(f"Database pool initialized: {self.min_size}-{self.max_size} connections")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def _setup_connection(self, connection):
        """Setup individual connections with optimizations"""
        try:
            # Enable additional PostgreSQL extensions
            await connection.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
            await connection.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")
            
            # Set connection-specific optimizations
            await connection.execute("SET work_mem = '32MB';")
            await connection.execute("SET maintenance_work_mem = '128MB';")
            await connection.execute("SET random_page_cost = 1.1;")
            
            self.stats['connections_created'] += 1
            
        except Exception as e:
            self.logger.warning(f"Connection setup warning: {e}")
    
    async def _init_connection(self, connection):
        """Initialize connection with custom types and functions"""
        try:
            # Register custom types if needed
            await connection.set_type_codec(
                'json',
                encoder=lambda x: x,
                decoder=lambda x: x,
                schema='pg_catalog'
            )
            
        except Exception as e:
            self.logger.warning(f"Connection init warning: {e}")
    
    async def _health_check_loop(self):
        """Periodic health check for connections"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if self.pool:
                    # Test pool health
                    async with self.pool.acquire() as conn:
                        await conn.fetchval("SELECT 1")
                    
                    # Log pool statistics
                    pool_size = self.pool.get_size()
                    idle_connections = self.pool.get_idle_size()
                    
                    self.logger.info(
                        f"Pool health: {pool_size} total, "
                        f"{idle_connections} idle, "
                        f"{pool_size - idle_connections} active"
                    )
                    
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
    
    async def execute_query(
        self, 
        query: str, 
        *args, 
        timeout: Optional[float] = None,
        retry_count: int = 3
    ):
        """Execute query with automatic retry and monitoring"""
        start_time = time.time()
        
        for attempt in range(retry_count):
            try:
                async with self.pool.acquire() as conn:
                    if timeout:
                        result = await asyncio.wait_for(
                            conn.fetch(query, *args),
                            timeout=timeout
                        )
                    else:
                        result = await conn.fetch(query, *args)
                    
                    execution_time = time.time() - start_time
                    
                    # Record metrics
                    self.stats['queries_executed'] += 1
                    db_monitor.record_query(query, execution_time, len(result))
                    
                    return result
                    
            except asyncio.TimeoutError:
                self.logger.warning(f"Query timeout on attempt {attempt + 1}: {query[:100]}")
                if attempt == retry_count - 1:
                    self.stats['query_errors'] += 1
                    raise
                    
            except asyncpg.exceptions.PostgresError as e:
                self.logger.error(f"Database error on attempt {attempt + 1}: {e}")
                self.stats['query_errors'] += 1
                
                if attempt == retry_count - 1:
                    db_monitor.record_error(query, str(e))
                    raise
                    
                # Wait before retry with exponential backoff
                await asyncio.sleep(2 ** attempt)
            
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                self.stats['query_errors'] += 1
                raise
    
    async def execute_transaction(self, operations: list):
        """Execute multiple operations in a transaction"""
        start_time = time.time()
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    results = []
                    for operation in operations:
                        query, args = operation['query'], operation.get('args', [])
                        result = await conn.fetch(query, *args)
                        results.append(result)
                    
                    execution_time = time.time() - start_time
                    self.stats['queries_executed'] += len(operations)
                    
                    return results
                    
        except Exception as e:
            self.logger.error(f"Transaction failed: {e}")
            self.stats['query_errors'] += len(operations)
            raise
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get comprehensive pool statistics"""
        if not self.pool:
            return {'error': 'Pool not initialized'}
        
        return {
            'pool_size': self.pool.get_size(),
            'idle_connections': self.pool.get_idle_size(),
            'active_connections': self.pool.get_size() - self.pool.get_idle_size(),
            'min_size': self.min_size,
            'max_size': self.max_size,
            'stats': self.stats.copy(),
            'utilization_rate': (self.pool.get_size() - self.pool.get_idle_size()) / self.pool.get_size()
        }
    
    async def close(self):
        """Gracefully close pool and cleanup"""
        if self.health_check_task:
            self.health_check_task.cancel()
            
        if self.pool:
            await self.pool.close()
            self.logger.info("Database pool closed")
            
        self.stats['connections_closed'] = self.stats['connections_created']

# Global database pool instance
db_pool = AdvancedConnectionPool("postgresql://user:pass@localhost/db")
```

## 4. IMPLEMENTATION CHECKLIST

### Phase 1: Database Schema & Indexing (Week 1)
- [ ] Create optimized table schemas for Hebrew data
- [ ] Implement comprehensive indexing strategy
- [ ] Configure PostgreSQL for Hebrew text processing
- [ ] Set up database monitoring and logging

### Phase 2: Query Optimization (Week 2)
- [ ] Implement optimized query classes
- [ ] Add performance monitoring and metrics
- [ ] Create connection pooling with health checks
- [ ] Implement query caching strategies

### Phase 3: Advanced Features (Week 3)
- [ ] Add automatic query optimization
- [ ] Implement database maintenance procedures
- [ ] Set up performance alerting
- [ ] Create database backup and recovery procedures

### Success Metrics
- **Query Response Time**: < 100ms for simple queries, < 500ms for complex searches
- **Connection Pool Efficiency**: > 90% utilization without exhaustion
- **Index Hit Rate**: > 95% for common query patterns
- **Database Size Growth**: Linear with data volume, not exponential
- **Concurrent User Support**: 100+ simultaneous users without performance degradation

This comprehensive database optimization plan ensures maximum performance for Hebrew data processing while maintaining scalability and reliability.