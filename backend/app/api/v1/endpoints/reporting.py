"""
Reporting API Endpoints

FastAPI endpoints for the comprehensive reporting system with Hebrew support.
Includes report generation, template management, distribution, and scheduling.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path
from fastapi.responses import StreamingResponse, FileResponse
from typing import List, Optional, Dict, Any
import io
import json
from datetime import datetime, timedelta
import logging

from app.core.auth_dependencies import get_current_user
from app.schemas.reporting import (
    # Template schemas
    TemplateCreate, TemplateUpdate, TemplateResponse, TemplateListResponse,
    TemplateValidationRequest, TemplateValidationResponse,
    # Report generation schemas
    ReportGenerationRequest, ReportGenerationResponse,
    ReportPreviewRequest, ReportPreviewResponse,
    # Distribution schemas
    DistributionRuleCreate, DistributionRequest, DistributionResponse,
    # Scheduling schemas
    ScheduledJobCreate, ScheduledJobUpdate, ScheduledJobResponse, JobExecutionResponse,
    # Data schemas
    ReportDataRequest, ReportDataResponse, ReportStatisticsResponse,
    # Utility schemas
    ErrorResponse, PaginationParams, ReportFilter, BulkReportGenerationRequest,
    BulkReportGenerationResponse, HealthCheckResponse, ReportingConfigResponse
)
from app.services.reporting import ReportService
from app.services.reporting.template_manager import ReportTemplateManager
from app.services.reporting.distribution_service import DistributionService
from app.services.reporting.report_scheduler import ReportScheduler
from app.models.user import User

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/reporting", tags=["reporting"])

# Initialize services
report_service = ReportService()
template_manager = ReportTemplateManager()
distribution_service = DistributionService()
report_scheduler = ReportScheduler(report_service, distribution_service)

# Template Management Endpoints

@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    template_data: TemplateCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new report template
    
    Creates a new report template with the specified configuration.
    Supports Hebrew text and RTL formatting.
    """
    try:
        result = report_service.create_report_template(template_data.dict())
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])
            
        return result['template']
        
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    current_user: User = Depends(get_current_user)
):
    """
    List all available report templates
    
    Returns a paginated list of all available report templates
    with their basic information.
    """
    try:
        templates = report_service.get_available_templates()
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_templates = templates[start_idx:end_idx]
        
        return TemplateListResponse(
            templates=paginated_templates,
            total=len(templates),
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str = Path(..., description="Template ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific template
    
    Returns detailed configuration and structure of the specified template.
    """
    try:
        template = report_service.get_template_details(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
            
        return template
        
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str = Path(..., description="Template ID"),
    template_update: TemplateUpdate = ...,
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing template
    
    Updates the configuration of an existing report template.
    """
    try:
        success = template_manager.update_template(template_id, template_update.dict(exclude_unset=True))
        
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
            
        # Return updated template
        updated_template = report_service.get_template_details(template_id)
        return updated_template
        
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str = Path(..., description="Template ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a template
    
    Permanently deletes the specified report template.
    """
    try:
        success = template_manager.delete_template(template_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
            
        return {"message": "Template deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/templates/{template_id}/validate", response_model=TemplateValidationResponse)
async def validate_template_data(
    template_id: str = Path(..., description="Template ID"),
    validation_request: TemplateValidationRequest = ...,
    current_user: User = Depends(get_current_user)
):
    """
    Validate data against template requirements
    
    Validates the provided data against the specified template's
    field requirements and validation rules.
    """
    try:
        result = template_manager.validate_template_data(template_id, validation_request.data)
        return result
        
    except Exception as e:
        logger.error(f"Error validating template data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Report Generation Endpoints

@router.post("/generate", response_model=ReportGenerationResponse)
async def generate_report(
    generation_request: ReportGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Generate a report using the specified template
    
    Generates a report in the requested format using the specified template
    and parameters. Supports Hebrew text and RTL formatting.
    """
    try:
        # Generate report
        result = await report_service.generate_report(
            template_id=generation_request.template_id,
            parameters=generation_request.parameters,
            output_format=generation_request.output_format
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])
            
        # Create response
        response = ReportGenerationResponse(
            success=True,
            report_id=f"report_{generation_request.template_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            format=generation_request.output_format,
            size=result['size'],
            generated_at=datetime.now(),
            metadata=result.get('metadata', {})
        )
        
        # Store report content for download (in production, use proper storage)
        report_id = response.report_id
        # This would typically store in Redis, database, or file system
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/preview", response_model=ReportPreviewResponse)
async def preview_report(
    preview_request: ReportPreviewRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate a preview of the report
    
    Generates a preview of the report with limited data for testing
    template configuration and layout.
    """
    try:
        result = await report_service.preview_report(
            template_id=preview_request.template_id,
            parameters=preview_request.parameters,
            output_format=preview_request.output_format
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])
            
        return ReportPreviewResponse(
            success=True,
            content=result['content'].decode('utf-8') if isinstance(result['content'], bytes) else result['content'],
            is_preview=True,
            preview_generated_at=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error generating report preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{report_id}")
async def download_report(
    report_id: str = Path(..., description="Report ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Download a generated report
    
    Downloads the specified report file.
    """
    try:
        # In production, retrieve from storage
        # For now, return a placeholder
        
        # This would retrieve the actual report content
        report_content = b"Sample report content"
        report_format = "pdf"
        
        # Create streaming response
        return StreamingResponse(
            io.BytesIO(report_content),
            media_type=f"application/{report_format}",
            headers={"Content-Disposition": f"attachment; filename={report_id}.{report_format}"}
        )
        
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-generate", response_model=BulkReportGenerationResponse)
async def bulk_generate_reports(
    bulk_request: BulkReportGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Generate multiple reports in batch
    
    Generates multiple reports based on the provided list of requests.
    Useful for generating reports for multiple templates or parameters.
    """
    try:
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results = []
        successful = 0
        failed = 0
        
        # Process each request
        for request in bulk_request.requests:
            try:
                result = await report_service.generate_report(
                    template_id=request.template_id,
                    parameters=request.parameters,
                    output_format=request.output_format
                )
                
                if result['success']:
                    successful += 1
                    response = ReportGenerationResponse(
                        success=True,
                        report_id=f"report_{request.template_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        format=request.output_format,
                        size=result['size'],
                        generated_at=datetime.now(),
                        metadata=result.get('metadata', {})
                    )
                else:
                    failed += 1
                    response = ReportGenerationResponse(
                        success=False,
                        error=result['error']
                    )
                    
                results.append(response)
                
            except Exception as e:
                failed += 1
                results.append(ReportGenerationResponse(
                    success=False,
                    error=str(e)
                ))
                
        return BulkReportGenerationResponse(
            batch_id=batch_id,
            total_requests=len(bulk_request.requests),
            successful=successful,
            failed=failed,
            results=results,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error in bulk report generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Distribution Endpoints

@router.post("/distribute", response_model=DistributionResponse)
async def distribute_report(
    distribution_request: DistributionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Distribute a report using the specified distribution rule
    
    Distributes an existing report to recipients based on the
    specified distribution rule configuration.
    """
    try:
        # This would retrieve the actual report content
        report_content = b"Sample report content"
        report_format = "pdf"
        
        result = await distribution_service.distribute_report(
            report_id=distribution_request.report_id,
            report_content=report_content,
            report_format=report_format,
            distribution_rule_id=distribution_request.distribution_rule_id,
            metadata=distribution_request.metadata
        )
        
        return DistributionResponse(
            success=True,
            batch_id=result['batch_id'],
            deliveries=result['deliveries'],
            started_at=datetime.fromisoformat(result['started_at']),
            completed_at=datetime.fromisoformat(result['completed_at'])
        )
        
    except Exception as e:
        logger.error(f"Error distributing report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-and-distribute", response_model=Dict[str, Any])
async def generate_and_distribute_report(
    template_id: str,
    parameters: Dict[str, Any],
    distribution_rule_id: str,
    output_format: str = "pdf",
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user)
):
    """
    Generate and distribute a report in one operation
    
    Generates a report and immediately distributes it using the
    specified distribution rule.
    """
    try:
        result = await report_service.generate_and_distribute_report(
            template_id=template_id,
            parameters=parameters,
            distribution_rule_id=distribution_rule_id,
            output_format=output_format
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])
            
        return result
        
    except Exception as e:
        logger.error(f"Error generating and distributing report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Scheduling Endpoints

@router.post("/schedule", response_model=ScheduledJobResponse)
async def create_scheduled_job(
    job_data: ScheduledJobCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new scheduled report job
    
    Creates a new scheduled job for automated report generation
    and distribution.
    """
    try:
        job = report_scheduler.create_scheduled_job(job_data.dict())
        
        return ScheduledJobResponse(
            job_id=job.job_id,
            name=job.name,
            description=job.description,
            schedule_type=job.schedule_type.value,
            schedule_expression=job.schedule_expression,
            report_template_id=job.report_template_id,
            distribution_rule_id=job.distribution_rule_id,
            enabled=job.enabled,
            priority=job.priority,
            max_retries=job.max_retries,
            retry_delay=job.retry_delay,
            timeout=job.timeout,
            dependencies=job.dependencies,
            parameters=job.parameters,
            notifications=job.notifications,
            created_at=job.created_at,
            updated_at=job.updated_at,
            last_run=job.last_run,
            next_run=job.next_run
        )
        
    except Exception as e:
        logger.error(f"Error creating scheduled job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schedule", response_model=List[ScheduledJobResponse])
async def list_scheduled_jobs(
    current_user: User = Depends(get_current_user)
):
    """
    List all scheduled report jobs
    
    Returns a list of all scheduled jobs with their configuration
    and status information.
    """
    try:
        jobs = report_scheduler.get_scheduled_jobs()
        
        return [
            ScheduledJobResponse(
                job_id=job['job_id'],
                name=job['name'],
                description=job['description'],
                schedule_type=job['schedule_type'],
                schedule_expression=job['schedule_expression'],
                report_template_id=job['report_template_id'],
                distribution_rule_id=job['distribution_rule_id'],
                enabled=job['enabled'],
                priority=job['priority'],
                max_retries=job['max_retries'],
                retry_delay=job['retry_delay'],
                timeout=job['timeout'],
                dependencies=job['dependencies'],
                parameters=job['parameters'],
                notifications=job['notifications'],
                created_at=datetime.fromisoformat(job['created_at']),
                updated_at=datetime.fromisoformat(job['updated_at']),
                last_run=datetime.fromisoformat(job['last_run']) if job['last_run'] else None,
                next_run=datetime.fromisoformat(job['next_run']) if job['next_run'] else None
            )
            for job in jobs
        ]
        
    except Exception as e:
        logger.error(f"Error listing scheduled jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schedule/{job_id}", response_model=ScheduledJobResponse)
async def get_scheduled_job(
    job_id: str = Path(..., description="Job ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific scheduled job
    
    Returns detailed information about the specified scheduled job.
    """
    try:
        jobs = report_scheduler.get_scheduled_jobs()
        job = next((j for j in jobs if j['job_id'] == job_id), None)
        
        if not job:
            raise HTTPException(status_code=404, detail="Scheduled job not found")
            
        return ScheduledJobResponse(
            job_id=job['job_id'],
            name=job['name'],
            description=job['description'],
            schedule_type=job['schedule_type'],
            schedule_expression=job['schedule_expression'],
            report_template_id=job['report_template_id'],
            distribution_rule_id=job['distribution_rule_id'],
            enabled=job['enabled'],
            priority=job['priority'],
            max_retries=job['max_retries'],
            retry_delay=job['retry_delay'],
            timeout=job['timeout'],
            dependencies=job['dependencies'],
            parameters=job['parameters'],
            notifications=job['notifications'],
            created_at=datetime.fromisoformat(job['created_at']),
            updated_at=datetime.fromisoformat(job['updated_at']),
            last_run=datetime.fromisoformat(job['last_run']) if job['last_run'] else None,
            next_run=datetime.fromisoformat(job['next_run']) if job['next_run'] else None
        )
        
    except Exception as e:
        logger.error(f"Error getting scheduled job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/schedule/{job_id}", response_model=ScheduledJobResponse)
async def update_scheduled_job(
    job_id: str = Path(..., description="Job ID"),
    job_update: ScheduledJobUpdate = ...,
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing scheduled job
    
    Updates the configuration of an existing scheduled job.
    """
    try:
        success = report_scheduler.update_scheduled_job(job_id, job_update.dict(exclude_unset=True))
        
        if not success:
            raise HTTPException(status_code=404, detail="Scheduled job not found")
            
        # Return updated job
        return await get_scheduled_job(job_id, current_user)
        
    except Exception as e:
        logger.error(f"Error updating scheduled job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/schedule/{job_id}")
async def delete_scheduled_job(
    job_id: str = Path(..., description="Job ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a scheduled job
    
    Permanently deletes the specified scheduled job.
    """
    try:
        success = report_scheduler.delete_scheduled_job(job_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Scheduled job not found")
            
        return {"message": "Scheduled job deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting scheduled job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schedule/{job_id}/executions", response_model=List[JobExecutionResponse])
async def get_job_executions(
    job_id: str = Path(..., description="Job ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Get execution history for a scheduled job
    
    Returns the execution history for the specified scheduled job.
    """
    try:
        executions = report_scheduler.get_job_executions(job_id)
        
        return [
            JobExecutionResponse(
                execution_id=exec['execution_id'],
                job_id=exec['job_id'],
                started_at=datetime.fromisoformat(exec['started_at']),
                completed_at=datetime.fromisoformat(exec['completed_at']) if exec['completed_at'] else None,
                status=exec['status'],
                error_message=exec['error_message'],
                retry_count=exec['retry_count'],
                output=exec['output']
            )
            for exec in executions
        ]
        
    except Exception as e:
        logger.error(f"Error getting job executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Data Endpoints

@router.post("/data", response_model=ReportDataResponse)
async def get_report_data(
    data_request: ReportDataRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Get data for report generation
    
    Retrieves data from the specified source with optional filtering
    for use in report generation.
    """
    try:
        data = await report_service.get_report_data(
            data_source=data_request.data_source,
            filters=data_request.filters
        )
        
        # Apply pagination if specified
        if data_request.limit:
            offset = data_request.offset or 0
            paginated_data = data[offset:offset + data_request.limit]
        else:
            paginated_data = data
            
        return ReportDataResponse(
            data=paginated_data,
            total=len(data),
            filtered=len(paginated_data),
            page=1,
            page_size=len(paginated_data),
            metadata={}
        )
        
    except Exception as e:
        logger.error(f"Error getting report data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Statistics Endpoints

@router.get("/statistics", response_model=ReportStatisticsResponse)
async def get_report_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    current_user: User = Depends(get_current_user)
):
    """
    Get report generation statistics
    
    Returns statistics about report generation including usage patterns,
    success rates, and performance metrics.
    """
    try:
        stats = report_service.get_report_statistics(days)
        
        return ReportStatisticsResponse(
            total_reports_generated=stats['total_reports_generated'],
            reports_last_30_days=stats['reports_last_30_days'],
            most_used_templates=stats['most_used_templates'],
            formats_distribution=stats['formats_distribution'],
            success_rate=stats['success_rate'],
            average_generation_time=stats['average_generation_time'],
            period_start=datetime.fromisoformat(stats['period_start']),
            period_end=datetime.fromisoformat(stats['period_end'])
        )
        
    except Exception as e:
        logger.error(f"Error getting report statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health Check Endpoints

@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint
    
    Returns the health status of the reporting system and its dependencies.
    """
    try:
        services = {
            "pdf_generator": "healthy",
            "excel_exporter": "healthy",
            "template_manager": "healthy",
            "distribution_service": "healthy",
            "report_scheduler": "healthy"
        }
        
        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.now(),
            version="1.0.0",
            services=services
        )
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config", response_model=ReportingConfigResponse)
async def get_reporting_config(
    current_user: User = Depends(get_current_user)
):
    """
    Get reporting system configuration
    
    Returns the current configuration settings for the reporting system.
    """
    try:
        from app.schemas.reporting import ReportFormat, SecurityLevel, DistributionChannel
        
        return ReportingConfigResponse(
            max_report_size=50 * 1024 * 1024,  # 50MB
            supported_formats=[ReportFormat.PDF, ReportFormat.EXCEL, ReportFormat.HTML],
            max_concurrent_jobs=5,
            default_template_language="hebrew",
            security_levels=list(SecurityLevel),
            distribution_channels=list(DistributionChannel)
        )
        
    except Exception as e:
        logger.error(f"Error getting reporting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add router to main API
def include_router(app):
    """Include the reporting router in the main FastAPI app"""
    app.include_router(router)