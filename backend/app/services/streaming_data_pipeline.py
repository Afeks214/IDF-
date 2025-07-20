"""
Real-time Streaming Data Pipeline for IDF Testing Infrastructure.
Handles continuous data ingestion, processing, and monitoring.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncIterator, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from pathlib import Path
import aiofiles
import aioredis
from collections import deque, defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.redis_client import get_redis_client
from ..utils.logger import get_logger
from .hebrew_data_processor import HebrewDataProcessor, ProcessingResult, ProcessingStatus

logger = get_logger(__name__)


class StreamType(Enum):
    """Types of data streams."""
    FILE_UPLOAD = "file_upload"
    REAL_TIME_FEED = "real_time_feed"
    BATCH_IMPORT = "batch_import"
    WEBHOOK = "webhook"
    SCHEDULED = "scheduled"


class StreamStatus(Enum):
    """Stream processing status."""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class StreamMetrics:
    """Metrics for a data stream."""
    stream_id: str
    total_records: int = 0
    processed_records: int = 0
    failed_records: int = 0
    throughput_per_second: float = 0.0
    avg_processing_time: float = 0.0
    last_activity: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass
class StreamConfig:
    """Configuration for a data stream."""
    stream_id: str
    stream_type: StreamType
    batch_size: int = 100
    max_concurrent_batches: int = 5
    retry_attempts: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0
    quality_threshold: float = 0.8
    enable_monitoring: bool = True
    filter_rules: Optional[Dict[str, Any]] = None
    transformation_rules: Optional[Dict[str, Any]] = None


class StreamingDataPipeline:
    """Real-time streaming data pipeline with Hebrew text processing."""
    
    def __init__(self, session: AsyncSession, redis_client: Optional[aioredis.Redis] = None):
        """
        Initialize the streaming data pipeline.
        
        Args:
            session: Database session
            redis_client: Redis client for caching and pub/sub
        """
        self.session = session
        self.redis_client = redis_client or get_redis_client()
        self.hebrew_processor = HebrewDataProcessor(session)
        
        # Active streams management
        self.active_streams: Dict[str, StreamConfig] = {}
        self.stream_metrics: Dict[str, StreamMetrics] = {}
        self.stream_tasks: Dict[str, asyncio.Task] = {}
        
        # Performance monitoring
        self.performance_history = deque(maxlen=1000)
        self.error_history = deque(maxlen=100)
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Pipeline status
        self.is_running = False
        self.shutdown_event = asyncio.Event()
    
    async def start(self):
        """Start the streaming pipeline."""
        if self.is_running:
            logger.warning("Pipeline is already running")
            return
        
        self.is_running = True
        self.shutdown_event.clear()
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitor_pipeline())
        
        # Start Redis pub/sub listener
        self.pubsub_task = asyncio.create_task(self._listen_to_redis_streams())
        
        logger.info("Streaming data pipeline started")
    
    async def stop(self):
        """Stop the streaming pipeline."""
        if not self.is_running:
            return
        
        self.is_running = False
        self.shutdown_event.set()
        
        # Cancel all stream tasks
        for task in self.stream_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.stream_tasks:
            await asyncio.gather(*self.stream_tasks.values(), return_exceptions=True)
        
        # Cancel monitoring tasks
        if hasattr(self, 'monitoring_task'):
            self.monitoring_task.cancel()
        if hasattr(self, 'pubsub_task'):
            self.pubsub_task.cancel()
        
        logger.info("Streaming data pipeline stopped")
    
    async def create_stream(self, config: StreamConfig) -> str:
        """
        Create a new data stream.
        
        Args:
            config: Stream configuration
            
        Returns:
            Stream ID
        """
        stream_id = config.stream_id or str(uuid.uuid4())
        config.stream_id = stream_id
        
        # Store stream configuration
        self.active_streams[stream_id] = config
        
        # Initialize metrics
        self.stream_metrics[stream_id] = StreamMetrics(
            stream_id=stream_id,
            start_time=datetime.now()
        )
        
        # Store in Redis for persistence
        await self._store_stream_config(stream_id, config)
        
        logger.info(f"Created stream {stream_id} of type {config.stream_type.value}")
        return stream_id
    
    async def start_stream(self, stream_id: str) -> bool:
        """
        Start processing a data stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            True if started successfully
        """
        if stream_id not in self.active_streams:
            logger.error(f"Stream {stream_id} not found")
            return False
        
        if stream_id in self.stream_tasks:
            logger.warning(f"Stream {stream_id} is already running")
            return False
        
        config = self.active_streams[stream_id]
        
        # Create stream processing task
        task = asyncio.create_task(self._process_stream(stream_id, config))
        self.stream_tasks[stream_id] = task
        
        logger.info(f"Started stream {stream_id}")
        return True
    
    async def stop_stream(self, stream_id: str) -> bool:
        """
        Stop processing a data stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            True if stopped successfully
        """
        if stream_id not in self.stream_tasks:
            logger.warning(f"Stream {stream_id} is not running")
            return False
        
        task = self.stream_tasks[stream_id]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        del self.stream_tasks[stream_id]
        
        # Update metrics
        if stream_id in self.stream_metrics:
            self.stream_metrics[stream_id].end_time = datetime.now()
        
        logger.info(f"Stopped stream {stream_id}")
        return True
    
    async def process_file_stream(self, file_path: str, stream_config: Optional[StreamConfig] = None) -> str:
        """
        Process a file as a data stream.
        
        Args:
            file_path: Path to the file to process
            stream_config: Optional stream configuration
            
        Returns:
            Stream ID
        """
        # Create default config if not provided
        if not stream_config:
            stream_config = StreamConfig(
                stream_id=str(uuid.uuid4()),
                stream_type=StreamType.FILE_UPLOAD,
                batch_size=100
            )
        
        # Create the stream
        stream_id = await self.create_stream(stream_config)
        
        # Create file processing task
        task = asyncio.create_task(self._process_file_as_stream(stream_id, file_path))
        self.stream_tasks[stream_id] = task
        
        return stream_id
    
    async def process_real_time_data(self, data_iterator: AsyncIterator[Dict[str, Any]], 
                                   stream_config: Optional[StreamConfig] = None) -> str:
        """
        Process real-time data stream.
        
        Args:
            data_iterator: Async iterator of data records
            stream_config: Optional stream configuration
            
        Returns:
            Stream ID
        """
        # Create default config if not provided
        if not stream_config:
            stream_config = StreamConfig(
                stream_id=str(uuid.uuid4()),
                stream_type=StreamType.REAL_TIME_FEED,
                batch_size=50
            )
        
        # Create the stream
        stream_id = await self.create_stream(stream_config)
        
        # Create real-time processing task
        task = asyncio.create_task(self._process_real_time_stream(stream_id, data_iterator))
        self.stream_tasks[stream_id] = task
        
        return stream_id
    
    async def get_stream_status(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a data stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Stream status information
        """
        if stream_id not in self.stream_metrics:
            return None
        
        metrics = self.stream_metrics[stream_id]
        config = self.active_streams.get(stream_id)
        
        status = StreamStatus.ACTIVE if stream_id in self.stream_tasks else StreamStatus.STOPPED
        if stream_id in self.stream_tasks:
            task = self.stream_tasks[stream_id]
            if task.done():
                if task.exception():
                    status = StreamStatus.ERROR
                else:
                    status = StreamStatus.COMPLETED
        
        return {
            'stream_id': stream_id,
            'status': status.value,
            'stream_type': config.stream_type.value if config else None,
            'metrics': {
                'total_records': metrics.total_records,
                'processed_records': metrics.processed_records,
                'failed_records': metrics.failed_records,
                'throughput_per_second': metrics.throughput_per_second,
                'avg_processing_time': metrics.avg_processing_time,
                'last_activity': metrics.last_activity.isoformat() if metrics.last_activity else None,
                'start_time': metrics.start_time.isoformat() if metrics.start_time else None,
                'end_time': metrics.end_time.isoformat() if metrics.end_time else None,
            },
            'errors': metrics.errors[-10:],  # Last 10 errors
        }
    
    async def get_all_streams_status(self) -> List[Dict[str, Any]]:
        """Get status of all active streams."""
        statuses = []
        
        for stream_id in self.stream_metrics:
            status = await self.get_stream_status(stream_id)
            if status:
                statuses.append(status)
        
        return statuses
    
    async def _process_stream(self, stream_id: str, config: StreamConfig):
        """Main stream processing loop."""
        logger.info(f"Processing stream {stream_id}")
        
        try:
            # Get data source based on stream type
            if config.stream_type == StreamType.FILE_UPLOAD:
                # This would be handled by process_file_stream
                pass
            elif config.stream_type == StreamType.REAL_TIME_FEED:
                # This would be handled by process_real_time_data
                pass
            elif config.stream_type == StreamType.WEBHOOK:
                await self._process_webhook_stream(stream_id, config)
            elif config.stream_type == StreamType.SCHEDULED:
                await self._process_scheduled_stream(stream_id, config)
            
        except Exception as e:
            logger.error(f"Stream {stream_id} processing failed: {str(e)}")
            self.stream_metrics[stream_id].errors.append(str(e))
            await self._emit_event('stream_error', {'stream_id': stream_id, 'error': str(e)})
    
    async def _process_file_as_stream(self, stream_id: str, file_path: str):
        """Process a file as a streaming data source."""
        metrics = self.stream_metrics[stream_id]
        
        try:
            # Process file using Hebrew data processor
            result = await self.hebrew_processor.process_file(file_path)
            
            # Update metrics
            metrics.total_records = result.records_processed
            metrics.processed_records = result.records_imported
            metrics.failed_records = result.records_failed
            metrics.last_activity = datetime.now()
            
            # Emit events
            await self._emit_event('stream_completed', {
                'stream_id': stream_id,
                'result': result.__dict__
            })
            
        except Exception as e:
            logger.error(f"File stream {stream_id} processing failed: {str(e)}")
            metrics.errors.append(str(e))
            await self._emit_event('stream_error', {'stream_id': stream_id, 'error': str(e)})
    
    async def _process_real_time_stream(self, stream_id: str, data_iterator: AsyncIterator[Dict[str, Any]]):
        """Process real-time data stream."""
        config = self.active_streams[stream_id]
        metrics = self.stream_metrics[stream_id]
        
        batch = []
        batch_start_time = datetime.now()
        
        try:
            async for record in data_iterator:
                # Apply filters if configured
                if config.filter_rules and not self._apply_filters(record, config.filter_rules):
                    continue
                
                # Apply transformations if configured
                if config.transformation_rules:
                    record = self._apply_transformations(record, config.transformation_rules)
                
                batch.append(record)
                metrics.total_records += 1
                
                # Process batch when it reaches the configured size
                if len(batch) >= config.batch_size:
                    await self._process_batch(stream_id, batch, batch_start_time)
                    batch = []
                    batch_start_time = datetime.now()
                
                # Check for shutdown
                if self.shutdown_event.is_set():
                    break
            
            # Process remaining records
            if batch:
                await self._process_batch(stream_id, batch, batch_start_time)
            
            # Mark stream as completed
            metrics.end_time = datetime.now()
            await self._emit_event('stream_completed', {'stream_id': stream_id})
            
        except Exception as e:
            logger.error(f"Real-time stream {stream_id} processing failed: {str(e)}")
            metrics.errors.append(str(e))
            await self._emit_event('stream_error', {'stream_id': stream_id, 'error': str(e)})
    
    async def _process_batch(self, stream_id: str, batch: List[Dict[str, Any]], batch_start_time: datetime):
        """Process a batch of records."""
        config = self.active_streams[stream_id]
        metrics = self.stream_metrics[stream_id]
        
        try:
            # Process batch using Hebrew data processor
            batch_result = await self.hebrew_processor._process_data_chunk(batch, 0)
            
            # Update metrics
            metrics.processed_records += batch_result.records_imported
            metrics.failed_records += batch_result.records_failed
            metrics.last_activity = datetime.now()
            
            # Calculate throughput
            batch_time = (datetime.now() - batch_start_time).total_seconds()
            if batch_time > 0:
                metrics.throughput_per_second = len(batch) / batch_time
            
            # Emit batch processed event
            await self._emit_event('batch_processed', {
                'stream_id': stream_id,
                'batch_size': len(batch),
                'processing_time': batch_time,
                'result': batch_result.__dict__
            })
            
        except Exception as e:
            logger.error(f"Batch processing failed for stream {stream_id}: {str(e)}")
            metrics.errors.append(str(e))
            metrics.failed_records += len(batch)
    
    async def _process_webhook_stream(self, stream_id: str, config: StreamConfig):
        """Process webhook data stream."""
        # This would listen for webhook data in Redis
        logger.info(f"Starting webhook stream {stream_id}")
        
        # Implementation would depend on webhook source
        # For now, we'll just listen to Redis for webhook data
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(f"webhook:{stream_id}")
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    await self._process_batch(stream_id, [data], datetime.now())
        except Exception as e:
            logger.error(f"Webhook stream {stream_id} error: {str(e)}")
        finally:
            await pubsub.unsubscribe(f"webhook:{stream_id}")
    
    async def _process_scheduled_stream(self, stream_id: str, config: StreamConfig):
        """Process scheduled data stream."""
        logger.info(f"Starting scheduled stream {stream_id}")
        
        # Implementation would depend on the scheduling requirements
        # This could involve polling a database, API, or file system
        while not self.shutdown_event.is_set():
            try:
                # Placeholder for scheduled processing logic
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Scheduled stream {stream_id} error: {str(e)}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _monitor_pipeline(self):
        """Monitor pipeline performance and health."""
        while not self.shutdown_event.is_set():
            try:
                # Collect metrics from all streams
                total_throughput = 0
                total_errors = 0
                active_streams = 0
                
                for stream_id, metrics in self.stream_metrics.items():
                    if stream_id in self.stream_tasks:
                        active_streams += 1
                        total_throughput += metrics.throughput_per_second
                        total_errors += len(metrics.errors)
                
                # Store performance metrics
                performance_data = {
                    'timestamp': datetime.now().isoformat(),
                    'active_streams': active_streams,
                    'total_throughput': total_throughput,
                    'total_errors': total_errors,
                    'pipeline_status': 'healthy' if total_errors < 10 else 'degraded'
                }
                
                self.performance_history.append(performance_data)
                
                # Store in Redis for monitoring
                await self.redis_client.setex(
                    'pipeline:performance',
                    300,  # 5 minutes TTL
                    json.dumps(performance_data)
                )
                
                # Emit monitoring event
                await self._emit_event('pipeline_metrics', performance_data)
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                logger.error(f"Pipeline monitoring error: {str(e)}")
                await asyncio.sleep(30)
    
    async def _listen_to_redis_streams(self):
        """Listen to Redis streams for pipeline events."""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe('pipeline:events')
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    event_data = json.loads(message['data'])
                    await self._handle_pipeline_event(event_data)
        except Exception as e:
            logger.error(f"Redis stream listener error: {str(e)}")
        finally:
            await pubsub.unsubscribe('pipeline:events')
    
    async def _handle_pipeline_event(self, event_data: Dict[str, Any]):
        """Handle pipeline events from Redis."""
        event_type = event_data.get('type')
        
        if event_type == 'create_stream':
            config_data = event_data.get('config', {})
            config = StreamConfig(**config_data)
            await self.create_stream(config)
        elif event_type == 'start_stream':
            stream_id = event_data.get('stream_id')
            if stream_id:
                await self.start_stream(stream_id)
        elif event_type == 'stop_stream':
            stream_id = event_data.get('stream_id')
            if stream_id:
                await self.stop_stream(stream_id)
    
    def _apply_filters(self, record: Dict[str, Any], filter_rules: Dict[str, Any]) -> bool:
        """Apply filter rules to a record."""
        for field, rule in filter_rules.items():
            value = record.get(field)
            
            if 'equals' in rule and value != rule['equals']:
                return False
            if 'contains' in rule and isinstance(value, str) and rule['contains'] not in value:
                return False
            if 'min_length' in rule and isinstance(value, str) and len(value) < rule['min_length']:
                return False
            if 'max_length' in rule and isinstance(value, str) and len(value) > rule['max_length']:
                return False
        
        return True
    
    def _apply_transformations(self, record: Dict[str, Any], transformation_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Apply transformation rules to a record."""
        transformed = record.copy()
        
        for field, rule in transformation_rules.items():
            value = transformed.get(field)
            
            if 'uppercase' in rule and isinstance(value, str):
                transformed[field] = value.upper()
            elif 'lowercase' in rule and isinstance(value, str):
                transformed[field] = value.lower()
            elif 'strip' in rule and isinstance(value, str):
                transformed[field] = value.strip()
            elif 'replace' in rule and isinstance(value, str):
                old_value = rule['replace'].get('old', '')
                new_value = rule['replace'].get('new', '')
                transformed[field] = value.replace(old_value, new_value)
        
        return transformed
    
    async def _store_stream_config(self, stream_id: str, config: StreamConfig):
        """Store stream configuration in Redis."""
        config_data = {
            'stream_id': config.stream_id,
            'stream_type': config.stream_type.value,
            'batch_size': config.batch_size,
            'max_concurrent_batches': config.max_concurrent_batches,
            'retry_attempts': config.retry_attempts,
            'retry_delay': config.retry_delay,
            'timeout': config.timeout,
            'quality_threshold': config.quality_threshold,
            'enable_monitoring': config.enable_monitoring,
            'filter_rules': config.filter_rules,
            'transformation_rules': config.transformation_rules,
        }
        
        await self.redis_client.setex(
            f'stream:config:{stream_id}',
            3600,  # 1 hour TTL
            json.dumps(config_data)
        )
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to registered handlers and Redis."""
        event_data = {
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        # Call registered handlers
        for handler in self.event_handlers.get(event_type, []):
            try:
                await handler(event_data)
            except Exception as e:
                logger.error(f"Event handler error: {str(e)}")
        
        # Publish to Redis
        try:
            await self.redis_client.publish('pipeline:events', json.dumps(event_data))
        except Exception as e:
            logger.error(f"Redis event publish error: {str(e)}")
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler."""
        self.event_handlers[event_type].append(handler)
    
    def unregister_event_handler(self, event_type: str, handler: Callable):
        """Unregister an event handler."""
        if handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get pipeline performance metrics."""
        if not self.performance_history:
            return {}
        
        latest = self.performance_history[-1]
        
        # Calculate averages over last 10 measurements
        recent_metrics = list(self.performance_history)[-10:]
        avg_throughput = sum(m['total_throughput'] for m in recent_metrics) / len(recent_metrics)
        avg_errors = sum(m['total_errors'] for m in recent_metrics) / len(recent_metrics)
        
        return {
            'current': latest,
            'averages': {
                'throughput': avg_throughput,
                'errors': avg_errors,
            },
            'history_size': len(self.performance_history),
            'active_streams': len(self.stream_tasks),
            'total_streams': len(self.stream_metrics),
        }