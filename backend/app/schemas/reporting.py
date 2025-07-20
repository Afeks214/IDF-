"""
Reporting API Schemas

Pydantic models for request/response validation in the reporting system.
Includes Hebrew text validation and RTL support.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator, root_validator

class ReportFormat(str, Enum):
    """Supported report formats"""
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"
    CSV = "csv"

class TemplateType(str, Enum):
    """Template types"""
    PDF = "pdf"
    EXCEL = "excel"
    WORD = "word"
    HTML = "html"
    CUSTOM = "custom"

class ReportSection(str, Enum):
    """Report section types"""
    HEADER = "header"
    SUMMARY = "summary"
    DETAILS = "details"
    CHARTS = "charts"
    STATISTICS = "statistics"
    RECOMMENDATIONS = "recommendations"
    APPENDIX = "appendix"
    FOOTER = "footer"

class DistributionChannel(str, Enum):
    """Distribution channels"""
    EMAIL = "email"
    SECURE_EMAIL = "secure_email"
    FILE_SYSTEM = "file_system"
    SECURE_PORTAL = "secure_portal"
    FTP = "ftp"
    SFTP = "sftp"
    API = "api"
    WEBHOOK = "webhook"

class SecurityLevel(str, Enum):
    """Security levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
    TOP_SECRET = "top_secret"

class JobStatus(str, Enum):
    """Job execution status"""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DISABLED = "disabled"

class Priority(str, Enum):
    """Priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# Template Management Schemas

class TemplateFieldCreate(BaseModel):
    """Template field creation schema"""
    name: str = Field(..., description="Field name")
    display_name: str = Field(..., description="Display name in Hebrew/English")
    data_type: str = Field(..., description="Field data type")
    required: bool = Field(False, description="Whether field is required")
    default_value: str = Field("", description="Default value")
    validation_rules: List[str] = Field([], description="Validation rules")
    formatting_rules: Dict[str, Any] = Field({}, description="Formatting rules")

class TemplateSectionCreate(BaseModel):
    """Template section creation schema"""
    section_type: ReportSection = Field(..., description="Section type")
    title: str = Field(..., description="Section title")
    fields: List[TemplateFieldCreate] = Field(..., description="Section fields")
    layout: Dict[str, Any] = Field({}, description="Layout configuration")
    styling: Dict[str, Any] = Field({}, description="Styling configuration")
    conditions: List[str] = Field([], description="Display conditions")

class TemplateCreate(BaseModel):
    """Template creation schema"""
    template_id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    template_type: TemplateType = Field(..., description="Template type")
    sections: List[TemplateSectionCreate] = Field(..., description="Template sections")
    metadata: Dict[str, Any] = Field({}, description="Additional metadata")
    
    @validator('template_id')
    def validate_template_id(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Template ID must be at least 3 characters')
        return v

class TemplateUpdate(BaseModel):
    """Template update schema"""
    name: Optional[str] = Field(None, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    sections: Optional[List[TemplateSectionCreate]] = Field(None, description="Template sections")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class TemplateResponse(BaseModel):
    """Template response schema"""
    template_id: str
    name: str
    description: str
    template_type: TemplateType
    sections: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    version: str

class TemplateListResponse(BaseModel):
    """Template list response schema"""
    templates: List[Dict[str, Any]]
    total: int
    page: int = 1
    page_size: int = 50

# Report Generation Schemas

class ReportGenerationRequest(BaseModel):
    """Report generation request schema"""
    template_id: str = Field(..., description="Template ID to use")
    parameters: Dict[str, Any] = Field(..., description="Report parameters")
    output_format: ReportFormat = Field(ReportFormat.PDF, description="Output format")
    output_filename: Optional[str] = Field(None, description="Output filename")
    
    @validator('template_id')
    def validate_template_id(cls, v):
        if not v:
            raise ValueError('Template ID is required')
        return v

class ReportGenerationResponse(BaseModel):
    """Report generation response schema"""
    success: bool
    report_id: Optional[str] = None
    format: Optional[ReportFormat] = None
    size: Optional[int] = None
    generated_at: Optional[datetime] = None
    download_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

class ReportPreviewRequest(BaseModel):
    """Report preview request schema"""
    template_id: str = Field(..., description="Template ID to use")
    parameters: Dict[str, Any] = Field(..., description="Report parameters")
    output_format: ReportFormat = Field(ReportFormat.HTML, description="Preview format")
    
class ReportPreviewResponse(BaseModel):
    """Report preview response schema"""
    success: bool
    content: Optional[str] = None
    is_preview: bool = True
    preview_generated_at: Optional[datetime] = None
    error: Optional[str] = None

# Distribution Schemas

class RecipientCreate(BaseModel):
    """Recipient creation schema"""
    email: str = Field(..., description="Recipient email address")
    name: str = Field(..., description="Recipient name")
    role: str = Field(..., description="Recipient role")
    security_clearance: SecurityLevel = Field(..., description="Security clearance level")
    preferred_language: str = Field("hebrew", description="Preferred language")
    notification_preferences: Dict[str, Any] = Field({}, description="Notification preferences")
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email address')
        return v

class DistributionRuleCreate(BaseModel):
    """Distribution rule creation schema"""
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    channels: List[DistributionChannel] = Field(..., description="Distribution channels")
    recipients: List[RecipientCreate] = Field(..., description="Recipients")
    conditions: List[str] = Field([], description="Distribution conditions")
    schedule: Dict[str, Any] = Field({}, description="Schedule configuration")
    security_requirements: Dict[str, Any] = Field({}, description="Security requirements")

class DistributionRequest(BaseModel):
    """Distribution request schema"""
    report_id: str = Field(..., description="Report ID to distribute")
    distribution_rule_id: str = Field(..., description="Distribution rule ID")
    metadata: Dict[str, Any] = Field({}, description="Additional metadata")

class DistributionResponse(BaseModel):
    """Distribution response schema"""
    success: bool
    batch_id: Optional[str] = None
    deliveries: List[Dict[str, Any]] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

# Scheduling Schemas

class ScheduledJobCreate(BaseModel):
    """Scheduled job creation schema"""
    job_id: str = Field(..., description="Unique job identifier")
    name: str = Field(..., description="Job name")
    description: str = Field(..., description="Job description")
    schedule_type: str = Field(..., description="Schedule type (cron, interval, once)")
    schedule_expression: str = Field(..., description="Schedule expression")
    report_template_id: str = Field(..., description="Template ID to use")
    distribution_rule_id: str = Field(..., description="Distribution rule ID")
    enabled: bool = Field(True, description="Whether job is enabled")
    priority: Priority = Field(Priority.MEDIUM, description="Job priority")
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_delay: int = Field(300, description="Retry delay in seconds")
    timeout: int = Field(3600, description="Job timeout in seconds")
    dependencies: List[str] = Field([], description="Job dependencies")
    parameters: Dict[str, Any] = Field({}, description="Job parameters")
    notifications: Dict[str, Any] = Field({}, description="Notification settings")
    
    @validator('schedule_expression')
    def validate_schedule_expression(cls, v, values):
        schedule_type = values.get('schedule_type')
        if schedule_type == 'cron':
            # Basic cron validation
            parts = v.split()
            if len(parts) != 5:
                raise ValueError('Cron expression must have 5 parts')
        elif schedule_type == 'interval':
            try:
                int(v)
            except ValueError:
                raise ValueError('Interval must be a number')
        return v

class ScheduledJobUpdate(BaseModel):
    """Scheduled job update schema"""
    name: Optional[str] = None
    description: Optional[str] = None
    schedule_expression: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[Priority] = None
    max_retries: Optional[int] = None
    retry_delay: Optional[int] = None
    timeout: Optional[int] = None
    parameters: Optional[Dict[str, Any]] = None
    notifications: Optional[Dict[str, Any]] = None

class ScheduledJobResponse(BaseModel):
    """Scheduled job response schema"""
    job_id: str
    name: str
    description: str
    schedule_type: str
    schedule_expression: str
    report_template_id: str
    distribution_rule_id: str
    enabled: bool
    priority: Priority
    max_retries: int
    retry_delay: int
    timeout: int
    dependencies: List[str]
    parameters: Dict[str, Any]
    notifications: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

class JobExecutionResponse(BaseModel):
    """Job execution response schema"""
    execution_id: str
    job_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: JobStatus
    error_message: str = ""
    retry_count: int = 0
    output: Dict[str, Any] = {}

# Data Schemas

class ReportDataRequest(BaseModel):
    """Report data request schema"""
    data_source: str = Field(..., description="Data source identifier")
    filters: Dict[str, Any] = Field({}, description="Data filters")
    date_range: Optional[Dict[str, str]] = Field(None, description="Date range filter")
    limit: Optional[int] = Field(None, description="Maximum records to return")
    offset: Optional[int] = Field(0, description="Records offset")

class ReportDataResponse(BaseModel):
    """Report data response schema"""
    data: List[Dict[str, Any]]
    total: int
    filtered: int
    page: int = 1
    page_size: int = 50
    metadata: Dict[str, Any] = {}

# Statistics Schemas

class ReportStatisticsResponse(BaseModel):
    """Report statistics response schema"""
    total_reports_generated: int
    reports_last_30_days: int
    most_used_templates: List[Dict[str, Any]]
    formats_distribution: Dict[str, int]
    success_rate: float
    average_generation_time: float
    period_start: datetime
    period_end: datetime

# Validation Schemas

class TemplateValidationRequest(BaseModel):
    """Template validation request schema"""
    template_id: str = Field(..., description="Template ID to validate")
    data: Dict[str, Any] = Field(..., description="Data to validate")

class TemplateValidationResponse(BaseModel):
    """Template validation response schema"""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []

# Error Schemas

class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ValidationError(BaseModel):
    """Validation error schema"""
    field: str
    message: str
    code: Optional[str] = None

class ValidationErrorResponse(BaseModel):
    """Validation error response schema"""
    error: str = "Validation Error"
    detail: str = "Request validation failed"
    validation_errors: List[ValidationError]
    timestamp: datetime = Field(default_factory=datetime.now)

# Pagination Schemas

class PaginationParams(BaseModel):
    """Pagination parameters schema"""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=1000, description="Page size")

class PaginatedResponse(BaseModel):
    """Paginated response schema"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int
    
    @root_validator
    def calculate_pages(cls, values):
        total = values.get('total', 0)
        page_size = values.get('page_size', 50)
        values['pages'] = (total + page_size - 1) // page_size
        return values

# Filter Schemas

class DateRangeFilter(BaseModel):
    """Date range filter schema"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @validator('end_date')
    def validate_end_date(cls, v, values):
        start_date = values.get('start_date')
        if start_date and v and v < start_date:
            raise ValueError('End date must be after start date')
        return v

class ReportFilter(BaseModel):
    """Report filter schema"""
    template_ids: Optional[List[str]] = None
    formats: Optional[List[ReportFormat]] = None
    date_range: Optional[DateRangeFilter] = None
    status: Optional[List[str]] = None
    created_by: Optional[str] = None

# Bulk Operations Schemas

class BulkReportGenerationRequest(BaseModel):
    """Bulk report generation request schema"""
    requests: List[ReportGenerationRequest] = Field(..., description="List of report generation requests")
    batch_name: Optional[str] = Field(None, description="Batch name for tracking")
    
    @validator('requests')
    def validate_requests(cls, v):
        if not v:
            raise ValueError('At least one request is required')
        if len(v) > 100:
            raise ValueError('Maximum 100 requests per batch')
        return v

class BulkReportGenerationResponse(BaseModel):
    """Bulk report generation response schema"""
    batch_id: str
    total_requests: int
    successful: int
    failed: int
    results: List[ReportGenerationResponse]
    started_at: datetime
    completed_at: Optional[datetime] = None

# Health Check Schemas

class HealthCheckResponse(BaseModel):
    """Health check response schema"""
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]
    
class ServiceStatusResponse(BaseModel):
    """Service status response schema"""
    service: str
    status: str
    uptime: Optional[float] = None
    last_check: datetime
    details: Dict[str, Any] = {}

# Configuration Schemas

class ReportingConfigResponse(BaseModel):
    """Reporting configuration response schema"""
    max_report_size: int
    supported_formats: List[ReportFormat]
    max_concurrent_jobs: int
    default_template_language: str
    security_levels: List[SecurityLevel]
    distribution_channels: List[DistributionChannel]