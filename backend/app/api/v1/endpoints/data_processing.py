"""
Data Processing API endpoints for IDF Testing Infrastructure.
Provides unified access to all enhanced data processing capabilities.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import json
import tempfile
import os
from datetime import datetime

from ....core.database import get_db
from ....core.auth_dependencies import get_current_user
from ....services.integrated_data_manager import (
    IntegratedDataManager, 
    ProcessingRequest, 
    ProcessingMode, 
    DataSource
)
from ....services.hebrew_data_processor import DataFormat
from ....services.streaming_data_pipeline import StreamConfig, StreamType
from ....schemas.auth import User

router = APIRouter()

# Global data manager instance (would be properly initialized in production)
data_manager: Optional[IntegratedDataManager] = None


async def get_data_manager(db: AsyncSession = Depends(get_db)) -> IntegratedDataManager:
    """Get or create data manager instance."""
    global data_manager
    if data_manager is None:
        data_manager = IntegratedDataManager(db)
        await data_manager.start()
    return data_manager


@router.post("/upload-file", response_model=Dict[str, Any])
async def upload_and_process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    processing_mode: ProcessingMode = ProcessingMode.BATCH,
    quality_threshold: float = 0.8,
    validation_rules: Optional[List[str]] = None,
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and process a data file with Hebrew text support.
    
    Supports Excel, CSV, and JSON formats with automatic detection.
    """
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Start processing in background
        session_id = await manager.process_file(
            file_path=tmp_file_path,
            processing_mode=processing_mode,
            quality_threshold=quality_threshold,
            validation_rules=validation_rules
        )
        
        # Clean up temp file in background
        background_tasks.add_task(os.unlink, tmp_file_path)
        
        return {
            "session_id": session_id,
            "filename": file.filename,
            "processing_mode": processing_mode.value,
            "quality_threshold": quality_threshold,
            "status": "processing",
            "message": "File upload successful, processing started"
        }
        
    except Exception as e:
        # Clean up temp file on error
        if 'tmp_file_path' in locals():
            os.unlink(tmp_file_path)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/session/{session_id}", response_model=Dict[str, Any])
async def get_processing_session_status(
    session_id: str,
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """Get the status of a processing session."""
    status = await manager.get_session_status(session_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return status


@router.get("/sessions", response_model=List[Dict[str, Any]])
async def list_processing_sessions(
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """List all active processing sessions."""
    sessions = []
    for session_id in manager.active_sessions:
        status = await manager.get_session_status(session_id)
        if status:
            sessions.append(status)
    
    return sessions


@router.post("/validate-data", response_model=Dict[str, Any])
async def validate_data_quality(
    data: List[Dict[str, Any]],
    validation_rules: Optional[List[str]] = None,
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """Validate data quality using the quality engine."""
    try:
        quality_report = await manager.validate_data(
            data=data,
            validation_rules=validation_rules
        )
        
        return {
            "report_id": quality_report.report_id,
            "overall_score": quality_report.overall_score,
            "total_records": quality_report.total_records,
            "validation_timestamp": quality_report.validation_timestamp.isoformat(),
            "category_scores": {cat.value: score for cat, score in quality_report.category_scores.items()},
            "severity_counts": {sev.value: count for sev, count in quality_report.severity_counts.items()},
            "recommendations": quality_report.recommendations,
            "metrics": quality_report.metrics,
            "issues_summary": {
                "total_issues": len(quality_report.issues),
                "critical_issues": len([i for i in quality_report.issues if i.severity.value == "critical"]),
                "error_issues": len([i for i in quality_report.issues if i.severity.value == "error"]),
                "warning_issues": len([i for i in quality_report.issues if i.severity.value == "warning"])
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/export-data")
async def export_data(
    filters: Optional[Dict[str, Any]] = None,
    output_format: str = "excel",
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """Export data with Hebrew text support."""
    try:
        # Generate export file
        export_path = await manager.export_data(
            filters=filters,
            output_format=output_format
        )
        
        # Return file for download
        return FileResponse(
            path=export_path,
            filename=f"idf_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{output_format}",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/stream/create", response_model=Dict[str, Any])
async def create_data_stream(
    stream_config: Dict[str, Any],
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """Create a new data stream for real-time processing."""
    try:
        # Create stream configuration
        config = StreamConfig(
            stream_id=stream_config.get("stream_id"),
            stream_type=StreamType(stream_config.get("stream_type", "real_time_feed")),
            batch_size=stream_config.get("batch_size", 100),
            max_concurrent_batches=stream_config.get("max_concurrent_batches", 5),
            quality_threshold=stream_config.get("quality_threshold", 0.8),
            enable_monitoring=stream_config.get("enable_monitoring", True)
        )
        
        # Create stream
        stream_id = await manager.streaming_pipeline.create_stream(config)
        
        return {
            "stream_id": stream_id,
            "status": "created",
            "config": stream_config,
            "message": "Stream created successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream creation failed: {str(e)}")


@router.post("/stream/{stream_id}/start", response_model=Dict[str, Any])
async def start_data_stream(
    stream_id: str,
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """Start processing a data stream."""
    try:
        success = await manager.streaming_pipeline.start_stream(stream_id)
        
        if success:
            return {
                "stream_id": stream_id,
                "status": "started",
                "message": "Stream processing started"
            }
        else:
            raise HTTPException(status_code=404, detail="Stream not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream start failed: {str(e)}")


@router.post("/stream/{stream_id}/stop", response_model=Dict[str, Any])
async def stop_data_stream(
    stream_id: str,
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """Stop processing a data stream."""
    try:
        success = await manager.streaming_pipeline.stop_stream(stream_id)
        
        if success:
            return {
                "stream_id": stream_id,
                "status": "stopped",
                "message": "Stream processing stopped"
            }
        else:
            raise HTTPException(status_code=404, detail="Stream not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream stop failed: {str(e)}")


@router.get("/stream/{stream_id}/status", response_model=Dict[str, Any])
async def get_stream_status(
    stream_id: str,
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """Get the status of a data stream."""
    status = await manager.streaming_pipeline.get_stream_status(stream_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    return status


@router.get("/streams", response_model=List[Dict[str, Any]])
async def list_data_streams(
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """List all data streams."""
    return await manager.streaming_pipeline.get_all_streams_status()


@router.get("/performance/dashboard", response_model=Dict[str, Any])
async def get_performance_dashboard(
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive performance dashboard data."""
    return await manager.get_performance_dashboard()


@router.get("/system/health", response_model=Dict[str, Any])
async def get_system_health(
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """Get system health status."""
    return await manager.get_system_health()


@router.get("/validation/rules", response_model=List[Dict[str, Any]])
async def list_validation_rules(
    category: Optional[str] = None,
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """List available validation rules."""
    from ....services.data_quality_engine import ValidationCategory
    
    category_filter = None
    if category:
        try:
            category_filter = ValidationCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    
    rules = manager.quality_engine.list_rules(category_filter)
    
    return [
        {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "description": rule.description,
            "category": rule.category.value,
            "severity": rule.severity.value,
            "enabled": rule.enabled,
            "weight": rule.weight,
            "threshold": rule.threshold,
            "parameters": rule.parameters
        }
        for rule in rules
    ]


@router.post("/validation/rules", response_model=Dict[str, Any])
async def create_validation_rule(
    rule_data: Dict[str, Any],
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """Create a new validation rule."""
    try:
        from ....services.data_quality_engine import ValidationRule, ValidationCategory, ValidationSeverity
        
        rule = ValidationRule(
            rule_id=rule_data["rule_id"],
            name=rule_data["name"],
            description=rule_data["description"],
            category=ValidationCategory(rule_data["category"]),
            severity=ValidationSeverity(rule_data["severity"]),
            enabled=rule_data.get("enabled", True),
            weight=rule_data.get("weight", 1.0),
            threshold=rule_data.get("threshold"),
            parameters=rule_data.get("parameters", {})
        )
        
        manager.quality_engine.register_rule(rule)
        
        return {
            "rule_id": rule.rule_id,
            "status": "created",
            "message": "Validation rule created successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rule creation failed: {str(e)}")


@router.get("/recommendations", response_model=List[str])
async def get_processing_recommendations(
    data_profile: Dict[str, Any],
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """Get processing recommendations based on data profile."""
    return await manager.get_processing_recommendations(data_profile)


@router.post("/pipeline/create", response_model=Dict[str, Any])
async def create_processing_pipeline(
    pipeline_config: Dict[str, Any],
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """Create a custom processing pipeline."""
    try:
        pipeline_id = await manager.create_processing_pipeline(pipeline_config)
        
        return {
            "pipeline_id": pipeline_id,
            "status": "created",
            "config": pipeline_config,
            "message": "Processing pipeline created successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline creation failed: {str(e)}")


# Hebrew text specific endpoints
@router.post("/hebrew/validate", response_model=Dict[str, Any])
async def validate_hebrew_text(
    text_data: Dict[str, str],
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """Validate Hebrew text format and encoding."""
    try:
        from ....services.hebrew_data_processor import HebrewDataProcessor
        
        results = {}
        for field, text in text_data.items():
            # Check Hebrew text properties
            processor = HebrewDataProcessor(manager.session)
            
            results[field] = {
                "original_text": text,
                "contains_hebrew": processor.HEBREW_LETTERS.search(text) is not None,
                "has_encoding_issues": '�' in text or '\ufffd' in text,
                "cleaned_text": processor._clean_hebrew_text(text),
                "normalized_text": processor._normalize_hebrew_text(text),
                "text_length": len(text),
                "hebrew_char_count": len(processor.HEBREW_LETTERS.findall(text)),
                "validation_passed": '�' not in text and '\ufffd' not in text
            }
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hebrew validation failed: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_processing_statistics(
    manager: IntegratedDataManager = Depends(get_data_manager),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive processing statistics."""
    return {
        "data_manager_stats": manager.performance_metrics,
        "hebrew_processor_stats": await manager.hebrew_processor.get_processing_statistics(),
        "streaming_pipeline_stats": await manager.streaming_pipeline.get_performance_metrics(),
        "quality_engine_stats": await manager.quality_engine.get_validation_statistics(),
        "timestamp": datetime.now().isoformat()
    }