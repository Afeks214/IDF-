#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Audit Logging and Security Monitoring System
Military-Grade Security for IDF Testing Infrastructure
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from enum import Enum
from dataclasses import dataclass
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func

from .config import settings
from .redis_client import redis_client
from ..models.user import AuditLog, SecurityEvent, User

logger = structlog.get_logger()


class AuditEventType(str, Enum):
    """Audit event types"""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    TWO_FACTOR_ENABLED = "two_factor_enabled"
    TWO_FACTOR_DISABLED = "two_factor_disabled"
    
    # User management events
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_ACTIVATED = "user_activated"
    USER_DEACTIVATED = "user_deactivated"
    USER_LOCKED = "user_locked"
    USER_UNLOCKED = "user_unlocked"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REMOVED = "role_removed"
    
    # Data events
    DATA_READ = "data_read"
    DATA_CREATED = "data_created"
    DATA_UPDATED = "data_updated"
    DATA_DELETED = "data_deleted"
    DATA_EXPORTED = "data_exported"
    DATA_IMPORTED = "data_imported"
    
    # File events
    FILE_UPLOADED = "file_uploaded"
    FILE_DOWNLOADED = "file_downloaded"
    FILE_DELETED = "file_deleted"
    FILE_SHARED = "file_shared"
    
    # System events
    SYSTEM_CONFIG_CHANGED = "system_config_changed"
    SYSTEM_BACKUP_CREATED = "system_backup_created"
    SYSTEM_BACKUP_RESTORED = "system_backup_restored"
    
    # Security events
    SECURITY_POLICY_CHANGED = "security_policy_changed"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    SESSION_TERMINATED = "session_terminated"


class SecurityEventSeverity(str, Enum):
    """Security event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventCategory(str, Enum):
    """Security event categories"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    SYSTEM_SECURITY = "system_security"
    NETWORK_SECURITY = "network_security"
    MALICIOUS_ACTIVITY = "malicious_activity"
    COMPLIANCE = "compliance"


@dataclass
class AuditContext:
    """Context information for audit logging"""
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None


class AuditLogger:
    """
    Comprehensive audit logging system
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db_session = db_session
        
    async def log_audit_event(
        self,
        event_type: AuditEventType,
        context: AuditContext,
        resource_type: Optional[str] = None,
        resource_id: Optional[Union[str, int]] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[AuditLog]:
        """
        Log an audit event
        """
        try:
            db = db or self.db_session
            if not db:
                logger.error("No database session available for audit logging")
                return None
            
            # Create audit log entry
            audit_entry = AuditLog(
                user_id=context.user_id,
                action=event_type.value,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                details=json.dumps(details) if details else None,
                success=success,
                error_message=error_message,
                session_id=context.session_id
            )
            
            db.add(audit_entry)
            await db.commit()
            
            # Also log to structured logger
            log_data = {
                "event_type": event_type.value,
                "user_id": context.user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "success": success,
                "ip_address": context.ip_address,
                "session_id": context.session_id,
                "request_id": context.request_id,
                "correlation_id": context.correlation_id
            }
            
            if success:
                logger.info("Audit event logged", **log_data)
            else:
                logger.warning("Audit event logged - failed action", error=error_message, **log_data)
            
            # Store in Redis for real-time monitoring
            await self._store_in_redis(audit_entry, details)
            
            return audit_entry
            
        except Exception as e:
            logger.error("Failed to log audit event", error=str(e), event_type=event_type.value)
            return None
    
    async def _store_in_redis(self, audit_entry: AuditLog, details: Optional[Dict] = None):
        """Store audit event in Redis for real-time monitoring"""
        try:
            redis_key = f"audit:{datetime.utcnow().strftime('%Y%m%d')}:{audit_entry.id}"
            redis_data = {
                "id": audit_entry.id,
                "user_id": audit_entry.user_id,
                "action": audit_entry.action,
                "resource_type": audit_entry.resource_type,
                "resource_id": audit_entry.resource_id,
                "success": audit_entry.success,
                "timestamp": audit_entry.created_at.isoformat(),
                "details": details or {}
            }
            
            await redis_client.set_secure(redis_key, redis_data, expire_seconds=86400)  # 24 hours
            
        except Exception as e:
            logger.error("Failed to store audit event in Redis", error=str(e))
    
    async def get_audit_trail(
        self,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        event_types: Optional[List[AuditEventType]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        db: Optional[AsyncSession] = None
    ) -> List[AuditLog]:
        """
        Retrieve audit trail with filtering
        """
        try:
            db = db or self.db_session
            if not db:
                return []
            
            query = select(AuditLog)
            
            # Apply filters
            conditions = []
            
            if user_id:
                conditions.append(AuditLog.user_id == user_id)
            
            if resource_type:
                conditions.append(AuditLog.resource_type == resource_type)
            
            if resource_id:
                conditions.append(AuditLog.resource_id == str(resource_id))
            
            if event_types:
                event_values = [event.value for event in event_types]
                conditions.append(AuditLog.action.in_(event_values))
            
            if start_date:
                conditions.append(AuditLog.created_at >= start_date)
            
            if end_date:
                conditions.append(AuditLog.created_at <= end_date)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Order by timestamp (newest first)
            query = query.order_by(desc(AuditLog.created_at))
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            result = await db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error("Failed to retrieve audit trail", error=str(e))
            return []


class SecurityMonitor:
    """
    Security monitoring and threat detection system
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db_session = db_session
        
    async def log_security_event(
        self,
        event_type: str,
        severity: SecurityEventSeverity,
        category: SecurityEventCategory,
        description: str,
        context: AuditContext,
        metadata: Optional[Dict[str, Any]] = None,
        auto_resolve: bool = False,
        db: Optional[AsyncSession] = None
    ) -> Optional[SecurityEvent]:
        """
        Log a security event
        """
        try:
            db = db or self.db_session
            if not db:
                logger.error("No database session available for security event logging")
                return None
            
            # Create security event entry
            security_event = SecurityEvent(
                event_type=event_type,
                severity=severity.value,
                user_id=context.user_id,
                ip_address=context.ip_address,
                description=description,
                metadata=json.dumps(metadata) if metadata else None,
                resolved=auto_resolve
            )
            
            db.add(security_event)
            await db.commit()
            
            # Log to structured logger
            log_data = {
                "event_type": event_type,
                "severity": severity.value,
                "category": category.value,
                "user_id": context.user_id,
                "ip_address": context.ip_address,
                "description": description,
                "request_id": context.request_id
            }
            
            if severity in [SecurityEventSeverity.HIGH, SecurityEventSeverity.CRITICAL]:
                logger.error("Critical security event", **log_data)
            elif severity == SecurityEventSeverity.MEDIUM:
                logger.warning("Security event", **log_data)
            else:
                logger.info("Security event", **log_data)
            
            # Store in Redis for real-time alerts
            await self._store_security_event_in_redis(security_event, category, metadata)
            
            # Trigger automated response for critical events
            if severity == SecurityEventSeverity.CRITICAL:
                await self._trigger_automated_response(security_event, context)
            
            return security_event
            
        except Exception as e:
            logger.error("Failed to log security event", error=str(e))
            return None
    
    async def _store_security_event_in_redis(
        self,
        event: SecurityEvent,
        category: SecurityEventCategory,
        metadata: Optional[Dict] = None
    ):
        """Store security event in Redis for real-time monitoring"""
        try:
            redis_key = f"security_event:{datetime.utcnow().strftime('%Y%m%d')}:{event.id}"
            redis_data = {
                "id": event.id,
                "event_type": event.event_type,
                "severity": event.severity,
                "category": category.value,
                "user_id": event.user_id,
                "ip_address": event.ip_address,
                "description": event.description,
                "timestamp": event.created_at.isoformat(),
                "metadata": metadata or {}
            }
            
            # Store with longer TTL for security events
            await redis_client.set_secure(redis_key, redis_data, expire_seconds=7 * 86400)  # 7 days
            
            # Also add to real-time alerts queue for critical events
            if event.severity in ["high", "critical"]:
                alert_key = f"security_alert:{event.severity}:{int(datetime.utcnow().timestamp())}"
                await redis_client.set_secure(alert_key, redis_data, expire_seconds=3600)  # 1 hour
            
        except Exception as e:
            logger.error("Failed to store security event in Redis", error=str(e))
    
    async def _trigger_automated_response(self, event: SecurityEvent, context: AuditContext):
        """Trigger automated security responses for critical events"""
        try:
            # Automated IP blocking for certain critical events
            if event.event_type in ["brute_force_attack", "sql_injection_attempt", "xss_attempt"]:
                if context.ip_address:
                    await self._block_ip_temporarily(context.ip_address, 3600)  # 1 hour
            
            # Account lockout for authentication failures
            if event.event_type == "multiple_failed_logins" and context.user_id:
                await self._lock_user_account(context.user_id, 1800)  # 30 minutes
            
            # TODO: Add email notifications, webhook calls, etc.
            
        except Exception as e:
            logger.error("Failed to trigger automated response", error=str(e))
    
    async def _block_ip_temporarily(self, ip_address: str, duration_seconds: int):
        """Temporarily block IP address"""
        try:
            await redis_client.set_secure(
                f"blocked_ip:{ip_address}",
                {
                    "blocked_at": datetime.utcnow().isoformat(),
                    "reason": "automated_security_response",
                    "duration": duration_seconds
                },
                expire_seconds=duration_seconds
            )
            
            logger.warning("IP temporarily blocked", ip=ip_address, duration=duration_seconds)
            
        except Exception as e:
            logger.error("Failed to block IP", error=str(e))
    
    async def _lock_user_account(self, user_id: int, duration_seconds: int):
        """Temporarily lock user account"""
        try:
            # This would update the user's locked_until field in the database
            # Implementation depends on your user management system
            
            await redis_client.set_secure(
                f"locked_user:{user_id}",
                {
                    "locked_at": datetime.utcnow().isoformat(),
                    "reason": "automated_security_response",
                    "duration": duration_seconds
                },
                expire_seconds=duration_seconds
            )
            
            logger.warning("User account temporarily locked", user_id=user_id, duration=duration_seconds)
            
        except Exception as e:
            logger.error("Failed to lock user account", error=str(e))
    
    async def get_security_events(
        self,
        severity: Optional[SecurityEventSeverity] = None,
        category: Optional[SecurityEventCategory] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        resolved: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
        db: Optional[AsyncSession] = None
    ) -> List[SecurityEvent]:
        """
        Retrieve security events with filtering
        """
        try:
            db = db or self.db_session
            if not db:
                return []
            
            query = select(SecurityEvent)
            
            # Apply filters
            conditions = []
            
            if severity:
                conditions.append(SecurityEvent.severity == severity.value)
            
            if start_date:
                conditions.append(SecurityEvent.created_at >= start_date)
            
            if end_date:
                conditions.append(SecurityEvent.created_at <= end_date)
            
            if resolved is not None:
                conditions.append(SecurityEvent.resolved == resolved)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Order by timestamp (newest first)
            query = query.order_by(desc(SecurityEvent.created_at))
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            result = await db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error("Failed to retrieve security events", error=str(e))
            return []
    
    async def get_security_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get security metrics and statistics
        """
        try:
            db = db or self.db_session
            if not db:
                return {}
            
            end_date = end_date or datetime.utcnow()
            start_date = start_date or (end_date - timedelta(days=30))
            
            # Query security events by severity
            severity_query = select(
                SecurityEvent.severity,
                func.count(SecurityEvent.id).label('count')
            ).where(
                and_(
                    SecurityEvent.created_at >= start_date,
                    SecurityEvent.created_at <= end_date
                )
            ).group_by(SecurityEvent.severity)
            
            severity_result = await db.execute(severity_query)
            severity_counts = {row.severity: row.count for row in severity_result}
            
            # Query audit events by type
            audit_query = select(
                AuditLog.action,
                func.count(AuditLog.id).label('count')
            ).where(
                and_(
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date
                )
            ).group_by(AuditLog.action)
            
            audit_result = await db.execute(audit_query)
            audit_counts = {row.action: row.count for row in audit_result}
            
            # Query failed actions
            failed_query = select(
                func.count(AuditLog.id).label('count')
            ).where(
                and_(
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date,
                    AuditLog.success == False
                )
            )
            
            failed_result = await db.execute(failed_query)
            failed_count = failed_result.scalar() or 0
            
            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "security_events_by_severity": severity_counts,
                "audit_events_by_type": audit_counts,
                "failed_actions_count": failed_count,
                "total_security_events": sum(severity_counts.values()),
                "total_audit_events": sum(audit_counts.values())
            }
            
        except Exception as e:
            logger.error("Failed to get security metrics", error=str(e))
            return {}


class ComplianceReporter:
    """
    Compliance reporting and audit trail generation
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db_session = db_session
    
    async def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        report_type: str = "full",
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Generate compliance report for specified period
        """
        try:
            db = db or self.db_session
            if not db:
                return {}
            
            audit_logger = AuditLogger(db)
            security_monitor = SecurityMonitor(db)
            
            # Get audit events
            audit_events = await audit_logger.get_audit_trail(
                start_date=start_date,
                end_date=end_date,
                limit=10000  # Large limit for comprehensive report
            )
            
            # Get security events
            security_events = await security_monitor.get_security_events(
                start_date=start_date,
                end_date=end_date,
                limit=10000
            )
            
            # Get metrics
            metrics = await security_monitor.get_security_metrics(start_date, end_date, db)
            
            # Generate report
            report = {
                "report_metadata": {
                    "generated_at": datetime.utcnow().isoformat(),
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    },
                    "report_type": report_type
                },
                "summary": {
                    "total_audit_events": len(audit_events),
                    "total_security_events": len(security_events),
                    "failed_actions": len([e for e in audit_events if not e.success]),
                    "critical_security_events": len([e for e in security_events if e.severity == "critical"])
                },
                "metrics": metrics,
                "audit_events": [self._format_audit_event(event) for event in audit_events[:1000]],  # Limit for size
                "security_events": [self._format_security_event(event) for event in security_events[:1000]]
            }
            
            return report
            
        except Exception as e:
            logger.error("Failed to generate compliance report", error=str(e))
            return {}
    
    def _format_audit_event(self, event: AuditLog) -> Dict[str, Any]:
        """Format audit event for report"""
        return {
            "id": event.id,
            "timestamp": event.created_at.isoformat(),
            "user_id": event.user_id,
            "action": event.action,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "success": event.success,
            "ip_address": event.ip_address,
            "error_message": event.error_message
        }
    
    def _format_security_event(self, event: SecurityEvent) -> Dict[str, Any]:
        """Format security event for report"""
        return {
            "id": event.id,
            "timestamp": event.created_at.isoformat(),
            "event_type": event.event_type,
            "severity": event.severity,
            "user_id": event.user_id,
            "ip_address": event.ip_address,
            "description": event.description,
            "resolved": event.resolved
        }


# Global instances
audit_logger = AuditLogger()
security_monitor = SecurityMonitor()
compliance_reporter = ComplianceReporter()