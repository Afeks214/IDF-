"""
Report Scheduler Service

Advanced scheduling system for automated report generation and distribution
with cron-like scheduling, dependency management, and failure recovery.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
from croniter import croniter
import hashlib

from app.core.config import get_settings
from app.services.reporting.report_service import ReportService
from app.services.reporting.distribution_service import DistributionService

logger = logging.getLogger(__name__)

class ScheduleType(Enum):
    """Schedule types supported by the system"""
    CRON = "cron"
    INTERVAL = "interval"
    ONCE = "once"
    EVENT_DRIVEN = "event_driven"

class JobStatus(Enum):
    """Job execution status"""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DISABLED = "disabled"

class Priority(Enum):
    """Job priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ScheduledJob:
    """Scheduled job configuration"""
    job_id: str
    name: str
    description: str
    schedule_type: ScheduleType
    schedule_expression: str
    report_template_id: str
    distribution_rule_id: str
    enabled: bool = True
    priority: Priority = Priority.MEDIUM
    max_retries: int = 3
    retry_delay: int = 300  # seconds
    timeout: int = 3600  # seconds
    dependencies: List[str] = None
    parameters: Dict[str, Any] = None
    notifications: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None
    last_run: datetime = None
    next_run: datetime = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.parameters is None:
            self.parameters = {}
        if self.notifications is None:
            self.notifications = {}
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

@dataclass
class JobExecution:
    """Job execution record"""
    execution_id: str
    job_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: JobStatus = JobStatus.RUNNING
    error_message: str = ""
    retry_count: int = 0
    output: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.output is None:
            self.output = {}

class ReportScheduler:
    """
    Advanced Report Scheduler Service
    
    Features:
    - Cron-like scheduling with flexible expressions
    - Job dependency management
    - Retry mechanisms with exponential backoff
    - Priority-based execution
    - Resource management and throttling
    - Failure recovery and alerting
    - Job monitoring and reporting
    - Hebrew notifications and logging
    """
    
    def __init__(self, report_service: ReportService, distribution_service: DistributionService):
        self.settings = get_settings()
        self.report_service = report_service
        self.distribution_service = distribution_service
        self.scheduled_jobs: Dict[str, ScheduledJob] = {}
        self.job_executions: Dict[str, JobExecution] = {}
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self.scheduler_task: Optional[asyncio.Task] = None
        self.is_running = False
        self._load_scheduled_jobs()
        
    def _load_scheduled_jobs(self):
        """Load scheduled jobs from configuration"""
        try:
            jobs_file = Path(__file__).parent / "scheduled_jobs.json"
            if jobs_file.exists():
                with open(jobs_file, 'r', encoding='utf-8') as f:
                    jobs_data = json.load(f)
                    
                for job_data in jobs_data:
                    job = self._dict_to_scheduled_job(job_data)
                    self.scheduled_jobs[job.job_id] = job
                    # Calculate next run time
                    self._calculate_next_run(job)
                    
            logger.info(f"Loaded {len(self.scheduled_jobs)} scheduled jobs")
            
        except Exception as e:
            logger.error(f"Error loading scheduled jobs: {e}")
            
    def _save_scheduled_jobs(self):
        """Save scheduled jobs to configuration file"""
        try:
            jobs_file = Path(__file__).parent / "scheduled_jobs.json"
            
            jobs_data = []
            for job in self.scheduled_jobs.values():
                job_dict = self._scheduled_job_to_dict(job)
                jobs_data.append(job_dict)
                
            with open(jobs_file, 'w', encoding='utf-8') as f:
                json.dump(jobs_data, f, ensure_ascii=False, indent=2, default=str)
                
            logger.info(f"Saved {len(jobs_data)} scheduled jobs")
            
        except Exception as e:
            logger.error(f"Error saving scheduled jobs: {e}")
            
    async def start_scheduler(self):
        """Start the job scheduler"""
        try:
            if self.is_running:
                logger.warning("Scheduler is already running")
                return
                
            self.is_running = True
            self.scheduler_task = asyncio.create_task(self._scheduler_loop())
            
            logger.info("Report scheduler started")
            
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            self.is_running = False
            
    async def stop_scheduler(self):
        """Stop the job scheduler"""
        try:
            self.is_running = False
            
            if self.scheduler_task:
                self.scheduler_task.cancel()
                try:
                    await self.scheduler_task
                except asyncio.CancelledError:
                    pass
                    
            # Cancel running jobs
            for job_id, task in self.running_jobs.items():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
            self.running_jobs.clear()
            
            logger.info("Report scheduler stopped")
            
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
            
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        try:
            while self.is_running:
                await self._check_and_execute_jobs()
                await asyncio.sleep(60)  # Check every minute
                
        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")
            
    async def _check_and_execute_jobs(self):
        """Check for jobs that need to be executed"""
        try:
            now = datetime.now()
            
            # Get jobs that are due for execution
            due_jobs = []
            for job in self.scheduled_jobs.values():
                if (job.enabled and 
                    job.next_run and 
                    job.next_run <= now and 
                    job.job_id not in self.running_jobs):
                    due_jobs.append(job)
                    
            # Sort by priority
            due_jobs.sort(key=lambda x: self._get_priority_value(x.priority), reverse=True)
            
            # Execute jobs
            for job in due_jobs:
                if len(self.running_jobs) < self._get_max_concurrent_jobs():
                    await self._execute_job(job)
                else:
                    logger.info(f"Max concurrent jobs reached, postponing job {job.job_id}")
                    
        except Exception as e:
            logger.error(f"Error checking and executing jobs: {e}")
            
    async def _execute_job(self, job: ScheduledJob):
        """Execute a scheduled job"""
        try:
            # Check dependencies
            if not await self._check_job_dependencies(job):
                logger.info(f"Job {job.job_id} dependencies not met, postponing")
                return
                
            # Create execution record
            execution_id = self._generate_execution_id()
            execution = JobExecution(
                execution_id=execution_id,
                job_id=job.job_id,
                started_at=datetime.now(),
                status=JobStatus.RUNNING
            )
            
            self.job_executions[execution_id] = execution
            
            # Create and start job task
            task = asyncio.create_task(self._run_job_task(job, execution))
            self.running_jobs[job.job_id] = task
            
            # Update job timing
            job.last_run = datetime.now()
            self._calculate_next_run(job)
            
            logger.info(f"Started job {job.job_id} with execution ID {execution_id}")
            
        except Exception as e:
            logger.error(f"Error executing job {job.job_id}: {e}")
            
    async def _run_job_task(self, job: ScheduledJob, execution: JobExecution):
        """Run the actual job task"""
        try:
            # Generate report
            report_result = await self._generate_scheduled_report(job, execution)
            
            if report_result['success']:
                # Distribute report
                distribution_result = await self._distribute_scheduled_report(job, execution, report_result)
                
                if distribution_result['success']:
                    execution.status = JobStatus.COMPLETED
                    execution.output = {
                        'report_result': report_result,
                        'distribution_result': distribution_result
                    }
                    logger.info(f"Job {job.job_id} completed successfully")
                else:
                    raise Exception(f"Distribution failed: {distribution_result.get('error', 'Unknown error')}")
            else:
                raise Exception(f"Report generation failed: {report_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Job {job.job_id} failed: {e}")
            execution.status = JobStatus.FAILED
            execution.error_message = str(e)
            
            # Handle retry logic
            if execution.retry_count < job.max_retries:
                await self._schedule_job_retry(job, execution)
            else:
                await self._handle_job_failure(job, execution)
                
        finally:
            execution.completed_at = datetime.now()
            
            # Remove from running jobs
            if job.job_id in self.running_jobs:
                del self.running_jobs[job.job_id]
                
            # Send notifications
            await self._send_job_notifications(job, execution)
            
    async def _generate_scheduled_report(self, job: ScheduledJob, execution: JobExecution) -> Dict[str, Any]:
        """Generate report for scheduled job"""
        try:
            # Get job parameters
            parameters = job.parameters.copy()
            
            # Add execution context
            parameters['execution_id'] = execution.execution_id
            parameters['job_id'] = job.job_id
            parameters['scheduled_run'] = True
            
            # Generate report using report service
            report_result = await self.report_service.generate_report(
                template_id=job.report_template_id,
                parameters=parameters
            )
            
            return report_result
            
        except Exception as e:
            logger.error(f"Error generating scheduled report: {e}")
            return {'success': False, 'error': str(e)}
            
    async def _distribute_scheduled_report(self, job: ScheduledJob, execution: JobExecution, report_result: Dict[str, Any]) -> Dict[str, Any]:
        """Distribute report for scheduled job"""
        try:
            # Get report content
            report_content = report_result.get('content')
            report_format = report_result.get('format', 'pdf')
            
            # Add job metadata
            metadata = {
                'job_id': job.job_id,
                'execution_id': execution.execution_id,
                'scheduled_run': True,
                'generated_at': datetime.now().isoformat()
            }
            
            # Distribute report
            distribution_result = await self.distribution_service.distribute_report(
                report_id=f"scheduled_{job.job_id}_{execution.execution_id}",
                report_content=report_content,
                report_format=report_format,
                distribution_rule_id=job.distribution_rule_id,
                metadata=metadata
            )
            
            return distribution_result
            
        except Exception as e:
            logger.error(f"Error distributing scheduled report: {e}")
            return {'success': False, 'error': str(e)}
            
    async def _check_job_dependencies(self, job: ScheduledJob) -> bool:
        """Check if job dependencies are satisfied"""
        try:
            if not job.dependencies:
                return True
                
            # Check each dependency
            for dependency_id in job.dependencies:
                dependency_job = self.scheduled_jobs.get(dependency_id)
                if not dependency_job:
                    logger.warning(f"Dependency job {dependency_id} not found")
                    return False
                    
                # Check if dependency job completed successfully recently
                if not self._is_dependency_satisfied(dependency_job):
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Error checking job dependencies: {e}")
            return False
            
    def _is_dependency_satisfied(self, dependency_job: ScheduledJob) -> bool:
        """Check if a dependency job is satisfied"""
        try:
            # Find the most recent execution of the dependency job
            recent_executions = [
                exec for exec in self.job_executions.values()
                if exec.job_id == dependency_job.job_id and
                exec.status == JobStatus.COMPLETED
            ]
            
            if not recent_executions:
                return False
                
            # Get the most recent successful execution
            latest_execution = max(recent_executions, key=lambda x: x.started_at)
            
            # Check if it's recent enough (within last 24 hours)
            if (datetime.now() - latest_execution.started_at).total_seconds() > 86400:
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking dependency satisfaction: {e}")
            return False
            
    async def _schedule_job_retry(self, job: ScheduledJob, execution: JobExecution):
        """Schedule job retry with exponential backoff"""
        try:
            execution.retry_count += 1
            
            # Calculate retry delay with exponential backoff
            delay = job.retry_delay * (2 ** (execution.retry_count - 1))
            retry_time = datetime.now() + timedelta(seconds=delay)
            
            # Schedule retry
            retry_job = ScheduledJob(
                job_id=f"{job.job_id}_retry_{execution.retry_count}",
                name=f"{job.name} (Retry {execution.retry_count})",
                description=f"Retry of {job.description}",
                schedule_type=ScheduleType.ONCE,
                schedule_expression=retry_time.isoformat(),
                report_template_id=job.report_template_id,
                distribution_rule_id=job.distribution_rule_id,
                enabled=True,
                priority=job.priority,
                max_retries=0,  # No retries for retry jobs
                parameters=job.parameters,
                next_run=retry_time
            )
            
            self.scheduled_jobs[retry_job.job_id] = retry_job
            
            logger.info(f"Scheduled retry {execution.retry_count} for job {job.job_id} at {retry_time}")
            
        except Exception as e:
            logger.error(f"Error scheduling job retry: {e}")
            
    async def _handle_job_failure(self, job: ScheduledJob, execution: JobExecution):
        """Handle job failure after all retries exhausted"""
        try:
            logger.error(f"Job {job.job_id} failed after {execution.retry_count} retries")
            
            # Send failure notifications
            await self._send_failure_notifications(job, execution)
            
            # Log failure for audit
            self._log_job_failure(job, execution)
            
        except Exception as e:
            logger.error(f"Error handling job failure: {e}")
            
    async def _send_job_notifications(self, job: ScheduledJob, execution: JobExecution):
        """Send job completion notifications"""
        try:
            notifications = job.notifications
            
            if not notifications:
                return
                
            # Send email notifications
            if notifications.get('email'):
                await self._send_email_notification(job, execution, notifications['email'])
                
            # Send webhook notifications
            if notifications.get('webhook'):
                await self._send_webhook_notification(job, execution, notifications['webhook'])
                
        except Exception as e:
            logger.error(f"Error sending job notifications: {e}")
            
    async def _send_email_notification(self, job: ScheduledJob, execution: JobExecution, email_config: Dict[str, Any]):
        """Send email notification for job completion"""
        try:
            # This would integrate with the email service
            logger.info(f"Sending email notification for job {job.job_id}")
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            
    async def _send_webhook_notification(self, job: ScheduledJob, execution: JobExecution, webhook_config: Dict[str, Any]):
        """Send webhook notification for job completion"""
        try:
            # This would send HTTP POST to webhook URL
            logger.info(f"Sending webhook notification for job {job.job_id}")
            
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            
    async def _send_failure_notifications(self, job: ScheduledJob, execution: JobExecution):
        """Send failure notifications"""
        try:
            # Send critical failure notifications
            logger.critical(f"Job {job.job_id} failed permanently")
            
        except Exception as e:
            logger.error(f"Error sending failure notifications: {e}")
            
    def _calculate_next_run(self, job: ScheduledJob):
        """Calculate next run time for a job"""
        try:
            if job.schedule_type == ScheduleType.CRON:
                cron = croniter(job.schedule_expression, datetime.now())
                job.next_run = cron.get_next(datetime)
                
            elif job.schedule_type == ScheduleType.INTERVAL:
                interval_seconds = int(job.schedule_expression)
                base_time = job.last_run or datetime.now()
                job.next_run = base_time + timedelta(seconds=interval_seconds)
                
            elif job.schedule_type == ScheduleType.ONCE:
                if isinstance(job.schedule_expression, str):
                    job.next_run = datetime.fromisoformat(job.schedule_expression)
                else:
                    job.next_run = None
                    
            else:
                job.next_run = None
                
        except Exception as e:
            logger.error(f"Error calculating next run for job {job.job_id}: {e}")
            job.next_run = None
            
    def _get_priority_value(self, priority: Priority) -> int:
        """Get numeric value for priority"""
        priority_values = {
            Priority.LOW: 1,
            Priority.MEDIUM: 2,
            Priority.HIGH: 3,
            Priority.CRITICAL: 4
        }
        return priority_values.get(priority, 2)
        
    def _get_max_concurrent_jobs(self) -> int:
        """Get maximum number of concurrent jobs"""
        return getattr(self.settings, 'MAX_CONCURRENT_JOBS', 5)
        
    def _generate_execution_id(self) -> str:
        """Generate unique execution ID"""
        return f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"
        
    def _log_job_failure(self, job: ScheduledJob, execution: JobExecution):
        """Log job failure for audit trail"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'event': 'job_failure',
                'job_id': job.job_id,
                'execution_id': execution.execution_id,
                'error_message': execution.error_message,
                'retry_count': execution.retry_count,
                'duration': (execution.completed_at - execution.started_at).total_seconds() if execution.completed_at else None
            }
            
            logger.error(f"Job failure: {json.dumps(log_entry, ensure_ascii=False)}")
            
        except Exception as e:
            logger.error(f"Error logging job failure: {e}")
            
    def _scheduled_job_to_dict(self, job: ScheduledJob) -> Dict[str, Any]:
        """Convert ScheduledJob to dictionary"""
        return {
            'job_id': job.job_id,
            'name': job.name,
            'description': job.description,
            'schedule_type': job.schedule_type.value,
            'schedule_expression': job.schedule_expression,
            'report_template_id': job.report_template_id,
            'distribution_rule_id': job.distribution_rule_id,
            'enabled': job.enabled,
            'priority': job.priority.value,
            'max_retries': job.max_retries,
            'retry_delay': job.retry_delay,
            'timeout': job.timeout,
            'dependencies': job.dependencies,
            'parameters': job.parameters,
            'notifications': job.notifications,
            'created_at': job.created_at.isoformat(),
            'updated_at': job.updated_at.isoformat(),
            'last_run': job.last_run.isoformat() if job.last_run else None,
            'next_run': job.next_run.isoformat() if job.next_run else None
        }
        
    def _dict_to_scheduled_job(self, job_data: Dict[str, Any]) -> ScheduledJob:
        """Convert dictionary to ScheduledJob"""
        return ScheduledJob(
            job_id=job_data['job_id'],
            name=job_data['name'],
            description=job_data['description'],
            schedule_type=ScheduleType(job_data['schedule_type']),
            schedule_expression=job_data['schedule_expression'],
            report_template_id=job_data['report_template_id'],
            distribution_rule_id=job_data['distribution_rule_id'],
            enabled=job_data.get('enabled', True),
            priority=Priority(job_data.get('priority', 'medium')),
            max_retries=job_data.get('max_retries', 3),
            retry_delay=job_data.get('retry_delay', 300),
            timeout=job_data.get('timeout', 3600),
            dependencies=job_data.get('dependencies', []),
            parameters=job_data.get('parameters', {}),
            notifications=job_data.get('notifications', {}),
            created_at=datetime.fromisoformat(job_data['created_at']),
            updated_at=datetime.fromisoformat(job_data['updated_at']),
            last_run=datetime.fromisoformat(job_data['last_run']) if job_data.get('last_run') else None,
            next_run=datetime.fromisoformat(job_data['next_run']) if job_data.get('next_run') else None
        )
        
    # Public API methods
    
    def create_scheduled_job(self, job_data: Dict[str, Any]) -> ScheduledJob:
        """Create a new scheduled job"""
        try:
            job = ScheduledJob(
                job_id=job_data['job_id'],
                name=job_data['name'],
                description=job_data['description'],
                schedule_type=ScheduleType(job_data['schedule_type']),
                schedule_expression=job_data['schedule_expression'],
                report_template_id=job_data['report_template_id'],
                distribution_rule_id=job_data['distribution_rule_id'],
                enabled=job_data.get('enabled', True),
                priority=Priority(job_data.get('priority', 'medium')),
                max_retries=job_data.get('max_retries', 3),
                retry_delay=job_data.get('retry_delay', 300),
                timeout=job_data.get('timeout', 3600),
                dependencies=job_data.get('dependencies', []),
                parameters=job_data.get('parameters', {}),
                notifications=job_data.get('notifications', {})
            )
            
            # Calculate next run time
            self._calculate_next_run(job)
            
            # Store job
            self.scheduled_jobs[job.job_id] = job
            
            # Save to file
            self._save_scheduled_jobs()
            
            logger.info(f"Created scheduled job: {job.job_id}")
            return job
            
        except Exception as e:
            logger.error(f"Error creating scheduled job: {e}")
            raise
            
    def update_scheduled_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing scheduled job"""
        try:
            job = self.scheduled_jobs.get(job_id)
            if not job:
                return False
                
            # Update job fields
            for key, value in updates.items():
                if hasattr(job, key):
                    setattr(job, key, value)
                    
            # Update timestamp
            job.updated_at = datetime.now()
            
            # Recalculate next run if schedule changed
            if 'schedule_expression' in updates or 'schedule_type' in updates:
                self._calculate_next_run(job)
                
            # Save to file
            self._save_scheduled_jobs()
            
            logger.info(f"Updated scheduled job: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating scheduled job: {e}")
            return False
            
    def delete_scheduled_job(self, job_id: str) -> bool:
        """Delete a scheduled job"""
        try:
            if job_id not in self.scheduled_jobs:
                return False
                
            # Cancel if running
            if job_id in self.running_jobs:
                self.running_jobs[job_id].cancel()
                del self.running_jobs[job_id]
                
            # Remove job
            del self.scheduled_jobs[job_id]
            
            # Save to file
            self._save_scheduled_jobs()
            
            logger.info(f"Deleted scheduled job: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting scheduled job: {e}")
            return False
            
    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled jobs"""
        try:
            jobs = []
            for job in self.scheduled_jobs.values():
                job_dict = self._scheduled_job_to_dict(job)
                jobs.append(job_dict)
                
            return jobs
            
        except Exception as e:
            logger.error(f"Error getting scheduled jobs: {e}")
            return []
            
    def get_job_executions(self, job_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get job execution history"""
        try:
            executions = []
            for execution in self.job_executions.values():
                if job_id is None or execution.job_id == job_id:
                    execution_dict = {
                        'execution_id': execution.execution_id,
                        'job_id': execution.job_id,
                        'started_at': execution.started_at.isoformat(),
                        'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                        'status': execution.status.value,
                        'error_message': execution.error_message,
                        'retry_count': execution.retry_count,
                        'output': execution.output
                    }
                    executions.append(execution_dict)
                    
            return executions
            
        except Exception as e:
            logger.error(f"Error getting job executions: {e}")
            return []