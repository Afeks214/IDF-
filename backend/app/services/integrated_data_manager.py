"""
Integrated Data Manager for IDF Testing Infrastructure.
Coordinates all data processing services and provides unified API.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
import aioredis

from ..core.redis_client import get_redis_client
from ..utils.logger import get_logger
from .hebrew_data_processor import HebrewDataProcessor, ProcessingResult, DataFormat
from .streaming_data_pipeline import StreamingDataPipeline, StreamConfig, StreamType
from .data_quality_engine import DataQualityEngine, QualityReport, ValidationRule
from .excel_service import ExcelImportService, ExcelExportService
from .validation_service import ValidationService

logger = get_logger(__name__)


class ProcessingMode(Enum):
    """Data processing modes."""
    BATCH = "batch"
    STREAMING = "streaming"
    REAL_TIME = "real_time"
    HYBRID = "hybrid"


class DataSource(Enum):
    """Data source types."""
    FILE_UPLOAD = "file_upload"
    API_IMPORT = "api_import"
    WEBHOOK = "webhook"
    SCHEDULED_SYNC = "scheduled_sync"
    MANUAL_ENTRY = "manual_entry"


@dataclass
class ProcessingRequest:
    """Request for data processing."""
    request_id: str
    source: DataSource
    mode: ProcessingMode
    data_format: Optional[DataFormat] = None
    file_path: Optional[str] = None
    data_stream: Optional[AsyncIterator] = None
    validation_rules: Optional[List[str]] = None
    quality_threshold: float = 0.8
    enable_monitoring: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # 1=high, 2=medium, 3=low


@dataclass
class ProcessingSession:
    """Data processing session tracking."""
    session_id: str
    request: ProcessingRequest
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "active"
    results: List[ProcessingResult] = field(default_factory=list)
    quality_reports: List[QualityReport] = field(default_factory=list)
    stream_ids: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


class IntegratedDataManager:
    """Unified manager for all data processing services."""
    
    def __init__(self, session: AsyncSession, redis_client: Optional[aioredis.Redis] = None):
        """
        Initialize the integrated data manager.
        
        Args:
            session: Database session
            redis_client: Redis client for caching and coordination
        """
        self.session = session
        self.redis_client = redis_client or get_redis_client()
        
        # Initialize all data processing services
        self.hebrew_processor = HebrewDataProcessor(session)
        self.streaming_pipeline = StreamingDataPipeline(session, redis_client)
        self.quality_engine = DataQualityEngine(session, redis_client)
        self.excel_import_service = ExcelImportService(session)
        self.excel_export_service = ExcelExportService(session)
        self.validation_service = ValidationService()
        
        # Session management
        self.active_sessions: Dict[str, ProcessingSession] = {}
        self.processing_queue: asyncio.Queue = asyncio.Queue()
        
        # Performance monitoring
        self.performance_metrics = {
            'total_sessions': 0,
            'successful_sessions': 0,
            'failed_sessions': 0,
            'avg_processing_time': 0.0,
            'throughput_records_per_second': 0.0,
            'last_activity': None
        }
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.is_running = False
    
    async def start(self):
        """Start the integrated data manager."""
        if self.is_running:
            logger.warning("Data manager is already running")
            return
        
        self.is_running = True
        
        # Start streaming pipeline
        await self.streaming_pipeline.start()
        
        # Start background processing
        self.background_tasks = [
            asyncio.create_task(self._process_queue()),
            asyncio.create_task(self._monitor_performance()),
            asyncio.create_task(self._cleanup_old_sessions())
        ]
        
        logger.info("Integrated data manager started")
    
    async def stop(self):
        """Stop the integrated data manager."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop streaming pipeline
        await self.streaming_pipeline.stop()
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        logger.info("Integrated data manager stopped")
    
    async def submit_processing_request(self, request: ProcessingRequest) -> str:
        """
        Submit a data processing request.
        
        Args:
            request: Processing request
            
        Returns:
            Session ID for tracking
        """
        session_id = str(uuid.uuid4())
        
        # Create processing session
        session = ProcessingSession(
            session_id=session_id,
            request=request,
            start_time=datetime.now()
        )
        
        self.active_sessions[session_id] = session
        
        # Queue for processing
        await self.processing_queue.put((request.priority, session_id))
        
        logger.info(f"Processing request submitted: {session_id}")
        return session_id
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get processing session status.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session status information
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        return {
            'session_id': session_id,
            'status': session.status,
            'start_time': session.start_time.isoformat(),
            'end_time': session.end_time.isoformat() if session.end_time else None,
            'processing_mode': session.request.mode.value,
            'data_source': session.request.source.value,
            'results_count': len(session.results),
            'quality_reports_count': len(session.quality_reports),
            'stream_ids': session.stream_ids,
            'errors': session.errors,
            'metrics': session.metrics
        }
    
    async def process_file(self, file_path: str, 
                         processing_mode: ProcessingMode = ProcessingMode.BATCH,
                         quality_threshold: float = 0.8,
                         validation_rules: Optional[List[str]] = None) -> str:
        """
        Process a file with integrated data processing.
        
        Args:
            file_path: Path to file to process
            processing_mode: How to process the file
            quality_threshold: Minimum quality score required
            validation_rules: List of validation rules to apply
            
        Returns:
            Session ID for tracking
        """
        # Detect file format
        file_format = await self.hebrew_processor._detect_format(file_path)
        
        # Create processing request
        request = ProcessingRequest(
            request_id=str(uuid.uuid4()),
            source=DataSource.FILE_UPLOAD,
            mode=processing_mode,
            data_format=file_format,
            file_path=file_path,
            validation_rules=validation_rules,
            quality_threshold=quality_threshold,
            metadata={'original_filename': Path(file_path).name}
        )
        
        return await self.submit_processing_request(request)
    
    async def process_data_stream(self, data_stream: AsyncIterator[Dict[str, Any]],
                                stream_config: Optional[StreamConfig] = None,
                                quality_threshold: float = 0.8,
                                validation_rules: Optional[List[str]] = None) -> str:
        """
        Process real-time data stream.
        
        Args:
            data_stream: Async iterator of data records
            stream_config: Stream configuration
            quality_threshold: Minimum quality score required
            validation_rules: List of validation rules to apply
            
        Returns:
            Session ID for tracking
        """
        request = ProcessingRequest(
            request_id=str(uuid.uuid4()),
            source=DataSource.API_IMPORT,
            mode=ProcessingMode.STREAMING,
            data_stream=data_stream,
            validation_rules=validation_rules,
            quality_threshold=quality_threshold,
            metadata={'stream_config': stream_config.__dict__ if stream_config else None}
        )
        
        return await self.submit_processing_request(request)
    
    async def export_data(self, filters: Optional[Dict[str, Any]] = None,
                        output_format: str = "excel",
                        output_path: Optional[str] = None) -> str:
        """
        Export data with Hebrew text support.
        
        Args:
            filters: Optional filters for data selection
            output_format: Output format (excel, csv, json)
            output_path: Optional output file path
            
        Returns:
            Path to exported file
        """
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"/tmp/idf_export_{timestamp}.{output_format}"
        
        if output_format.lower() == "excel":
            return await self.excel_export_service.export_inspections_to_excel(
                output_path, filters
            )
        else:
            raise ValueError(f"Unsupported export format: {output_format}")
    
    async def validate_data(self, data: Union[List[Dict[str, Any]], str],
                          validation_rules: Optional[List[str]] = None) -> QualityReport:
        """
        Validate data quality.
        
        Args:
            data: Data to validate (records or file path)
            validation_rules: Optional list of validation rules
            
        Returns:
            Quality report
        """
        if isinstance(data, str):
            # Data is a file path
            result = await self.hebrew_processor.process_file(data)
            # Extract data from result for validation
            data_records = []  # This would need to be extracted from processing result
        else:
            data_records = data
        
        return await self.quality_engine.validate_dataset(
            data_records,
            enabled_rules=validation_rules
        )
    
    async def _process_queue(self):
        """Background task to process queued requests."""
        while self.is_running:
            try:
                # Get next request from queue (priority-based)
                priority, session_id = await asyncio.wait_for(
                    self.processing_queue.get(), timeout=1.0
                )
                
                session = self.active_sessions.get(session_id)
                if not session:
                    continue
                
                # Process the request
                await self._process_session(session)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Queue processing error: {str(e)}")
                await asyncio.sleep(1)
    
    async def _process_session(self, session: ProcessingSession):
        """Process a single session."""
        try:
            session.status = "processing"
            request = session.request
            
            logger.info(f"Processing session {session.session_id} with mode {request.mode.value}")
            
            if request.mode == ProcessingMode.BATCH:
                await self._process_batch_mode(session)
            elif request.mode == ProcessingMode.STREAMING:
                await self._process_streaming_mode(session)
            elif request.mode == ProcessingMode.REAL_TIME:
                await self._process_real_time_mode(session)
            elif request.mode == ProcessingMode.HYBRID:
                await self._process_hybrid_mode(session)
            
            # Finalize session
            session.status = "completed"
            session.end_time = datetime.now()
            
            # Update performance metrics
            self.performance_metrics['successful_sessions'] += 1
            self._update_performance_metrics(session)
            
            logger.info(f"Session {session.session_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Session {session.session_id} failed: {str(e)}")
            session.status = "failed"
            session.errors.append(str(e))
            session.end_time = datetime.now()
            
            self.performance_metrics['failed_sessions'] += 1
    
    async def _process_batch_mode(self, session: ProcessingSession):
        """Process request in batch mode."""
        request = session.request
        
        if request.file_path:
            # Process file
            result = await self.hebrew_processor.process_file(request.file_path)
            session.results.append(result)
            
            # Validate quality if enabled
            if request.validation_rules or request.quality_threshold < 1.0:
                # Extract data for validation (this would need to be implemented)
                # For now, we'll create a placeholder
                quality_report = await self.quality_engine.validate_dataset(
                    [],  # Data would be extracted from processing result
                    enabled_rules=request.validation_rules
                )
                session.quality_reports.append(quality_report)
                
                # Check quality threshold
                if quality_report.overall_score < request.quality_threshold:
                    session.errors.append(
                        f"Quality score {quality_report.overall_score:.3f} below threshold {request.quality_threshold}"
                    )
        
        session.metrics.update({
            'records_processed': sum(r.records_processed for r in session.results),
            'records_imported': sum(r.records_imported for r in session.results),
            'processing_time': sum(r.processing_time for r in session.results)
        })
    
    async def _process_streaming_mode(self, session: ProcessingSession):
        """Process request in streaming mode."""
        request = session.request
        
        if request.data_stream:
            # Create stream configuration
            stream_config = StreamConfig(
                stream_id=str(uuid.uuid4()),
                stream_type=StreamType.REAL_TIME_FEED,
                batch_size=100,
                quality_threshold=request.quality_threshold,
                enable_monitoring=request.enable_monitoring
            )
            
            # Start stream processing
            stream_id = await self.streaming_pipeline.process_real_time_data(
                request.data_stream, stream_config
            )
            session.stream_ids.append(stream_id)
            
            # Monitor stream progress
            await self._monitor_stream_progress(session, stream_id)
        
        elif request.file_path:
            # Process file as stream
            stream_id = await self.streaming_pipeline.process_file_stream(request.file_path)
            session.stream_ids.append(stream_id)
            
            # Monitor stream progress
            await self._monitor_stream_progress(session, stream_id)
    
    async def _process_real_time_mode(self, session: ProcessingSession):
        """Process request in real-time mode."""
        # Real-time processing would involve immediate processing
        # This is similar to streaming but with different performance characteristics
        await self._process_streaming_mode(session)
    
    async def _process_hybrid_mode(self, session: ProcessingSession):
        """Process request in hybrid mode (batch + streaming)."""
        # First process in batch mode for immediate results
        await self._process_batch_mode(session)
        
        # Then set up streaming for ongoing updates
        if session.request.data_stream:
            await self._process_streaming_mode(session)
    
    async def _monitor_stream_progress(self, session: ProcessingSession, stream_id: str):
        """Monitor stream processing progress."""
        max_wait_time = 300  # 5 minutes timeout
        check_interval = 5  # Check every 5 seconds
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            status = await self.streaming_pipeline.get_stream_status(stream_id)
            
            if status:
                session.metrics.update({
                    'stream_status': status['status'],
                    'stream_metrics': status['metrics']
                })
                
                if status['status'] in ['completed', 'error']:
                    break
            
            await asyncio.sleep(check_interval)
            elapsed_time += check_interval
        
        # Get final status
        final_status = await self.streaming_pipeline.get_stream_status(stream_id)
        if final_status:
            session.metrics['final_stream_status'] = final_status
    
    async def _monitor_performance(self):
        """Background task to monitor performance metrics."""
        while self.is_running:
            try:
                # Update performance metrics
                self.performance_metrics['total_sessions'] = len(self.active_sessions)
                self.performance_metrics['last_activity'] = datetime.now().isoformat()
                
                # Calculate throughput
                completed_sessions = [s for s in self.active_sessions.values() if s.status == "completed"]
                if completed_sessions:
                    total_records = sum(s.metrics.get('records_processed', 0) for s in completed_sessions)
                    total_time = sum(s.metrics.get('processing_time', 0) for s in completed_sessions)
                    
                    if total_time > 0:
                        self.performance_metrics['throughput_records_per_second'] = total_records / total_time
                
                # Store metrics in Redis
                await self.redis_client.setex(
                    'data_manager:performance',
                    300,  # 5 minutes TTL
                    json.dumps(self.performance_metrics)
                )
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _cleanup_old_sessions(self):
        """Background task to cleanup old sessions."""
        while self.is_running:
            try:
                current_time = datetime.now()
                expired_sessions = []
                
                for session_id, session in self.active_sessions.items():
                    # Remove sessions older than 24 hours
                    if current_time - session.start_time > timedelta(hours=24):
                        expired_sessions.append(session_id)
                
                # Remove expired sessions
                for session_id in expired_sessions:
                    del self.active_sessions[session_id]
                    logger.info(f"Cleaned up expired session: {session_id}")
                
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except Exception as e:
                logger.error(f"Session cleanup error: {str(e)}")
                await asyncio.sleep(3600)
    
    def _update_performance_metrics(self, session: ProcessingSession):
        """Update performance metrics based on completed session."""
        if session.end_time and session.start_time:
            processing_time = (session.end_time - session.start_time).total_seconds()
            
            # Update average processing time
            total_sessions = self.performance_metrics['successful_sessions']
            if total_sessions > 0:
                current_avg = self.performance_metrics['avg_processing_time']
                new_avg = ((current_avg * (total_sessions - 1)) + processing_time) / total_sessions
                self.performance_metrics['avg_processing_time'] = new_avg
    
    async def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data."""
        # Get streaming pipeline metrics
        pipeline_metrics = await self.streaming_pipeline.get_performance_metrics()
        
        # Get quality engine statistics
        quality_stats = await self.quality_engine.get_validation_statistics()
        
        # Get current session statistics
        session_stats = {
            'active_sessions': len([s for s in self.active_sessions.values() if s.status == "active"]),
            'processing_sessions': len([s for s in self.active_sessions.values() if s.status == "processing"]),
            'completed_sessions': len([s for s in self.active_sessions.values() if s.status == "completed"]),
            'failed_sessions': len([s for s in self.active_sessions.values() if s.status == "failed"])
        }
        
        return {
            'data_manager': self.performance_metrics,
            'streaming_pipeline': pipeline_metrics,
            'quality_engine': quality_stats,
            'session_stats': session_stats,
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health status."""
        health_status = {
            'status': 'healthy',
            'services': {
                'data_manager': 'healthy' if self.is_running else 'stopped',
                'streaming_pipeline': 'healthy',  # Would check actual status
                'quality_engine': 'healthy',
                'redis': 'healthy',  # Would check Redis connectivity
                'database': 'healthy'  # Would check database connectivity
            },
            'issues': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Check for issues
        failed_sessions = len([s for s in self.active_sessions.values() if s.status == "failed"])
        if failed_sessions > 0:
            health_status['issues'].append(f"{failed_sessions} failed processing sessions")
        
        error_rate = failed_sessions / max(len(self.active_sessions), 1)
        if error_rate > 0.1:  # More than 10% failure rate
            health_status['status'] = 'degraded'
            health_status['issues'].append("High error rate detected")
        
        return health_status
    
    async def create_processing_pipeline(self, pipeline_config: Dict[str, Any]) -> str:
        """Create a custom processing pipeline."""
        # This would allow creating custom processing workflows
        # combining different services based on configuration
        
        pipeline_id = str(uuid.uuid4())
        
        # Store pipeline configuration
        await self.redis_client.setex(
            f'pipeline_config:{pipeline_id}',
            3600,  # 1 hour TTL
            json.dumps(pipeline_config)
        )
        
        logger.info(f"Created processing pipeline: {pipeline_id}")
        return pipeline_id
    
    async def get_processing_recommendations(self, data_profile: Dict[str, Any]) -> List[str]:
        """Get processing recommendations based on data profile."""
        recommendations = []
        
        # Analyze data profile and suggest optimal processing approach
        record_count = data_profile.get('record_count', 0)
        hebrew_text_ratio = data_profile.get('hebrew_text_ratio', 0)
        data_quality_score = data_profile.get('quality_score', 1.0)
        
        if record_count > 10000:
            recommendations.append("Consider using streaming mode for large datasets")
        
        if hebrew_text_ratio > 0.8:
            recommendations.append("Enable Hebrew text validation rules")
        
        if data_quality_score < 0.8:
            recommendations.append("Run comprehensive quality validation before processing")
        
        return recommendations