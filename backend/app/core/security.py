#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Military-Grade JWT Authentication and Security System
IDF Testing Infrastructure
"""

import secrets
from datetime import datetime, timedelta
from typing import Any, Union, Optional, Dict, List
from passlib.context import CryptContext
from jose import JWTError, jwt
import structlog
import re
import hashlib
import hmac
from enum import Enum
import ipaddress
import asyncio
import json
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import uuid
from collections import defaultdict
from urllib.parse import urlparse
import geoip2.database
import geoip2.errors
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import aiofiles
from functools import wraps

from .config import settings
from .redis_client import redis_client

logger = structlog.get_logger()

# Security event types for audit trail
class SecurityEventType(str, Enum):
    """Security event types for comprehensive audit trail"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGIN_BLOCKED = "login_blocked"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PERMISSION_DENIED = "permission_denied"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    FILE_DELETION = "file_deletion"
    SYSTEM_CONFIG_CHANGE = "system_config_change"
    SECURITY_VIOLATION = "security_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    THREAT_DETECTED = "threat_detected"
    COMPLIANCE_VIOLATION = "compliance_violation"
    ROLE_CHANGE = "role_change"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    
@dataclass
class SecurityEvent:
    """Security event data structure for audit trail"""
    event_id: str
    event_type: SecurityEventType
    user_id: Optional[str]
    user_ip: Optional[str]
    user_agent: Optional[str]
    resource: Optional[str]
    action: str
    result: str  # SUCCESS, FAILURE, BLOCKED
    timestamp: datetime
    details: Dict[str, Any]
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    location: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ThreatIndicator:
    """Threat detection indicator"""
    indicator_id: str
    threat_type: str
    severity: str
    description: str
    source_ip: str
    detected_at: datetime
    user_id: Optional[str] = None
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class UserRole(str, Enum):
    """Military-grade hierarchical roles for RBAC"""
    SUPER_ADMIN = "super_admin"  # System administrators
    ADMIN = "admin"              # Unit administrators
    COMMANDER = "commander"      # Military commanders
    OFFICER = "officer"          # Military officers
    ANALYST = "analyst"          # Intelligence analysts
    SPECIALIST = "specialist"    # Technical specialists
    OPERATOR = "operator"        # System operators
    VIEWER = "viewer"            # Read-only access
    GUEST = "guest"              # Limited guest access


class Permission(str, Enum):
    """Military-grade granular permissions for RBAC"""
    # Data operations
    DATA_READ = "data:read"
    DATA_WRITE = "data:write"
    DATA_DELETE = "data:delete"
    DATA_EXPORT = "data:export"
    DATA_CLASSIFY = "data:classify"
    DATA_DECLASSIFY = "data:declassify"
    
    # User management
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_ROLE_CHANGE = "user:role_change"
    USER_SECURITY_CLEAR = "user:security_clear"
    USER_AUDIT = "user:audit"
    
    # System operations
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_BACKUP = "system:backup"
    SYSTEM_RESTORE = "system:restore"
    SYSTEM_SHUTDOWN = "system:shutdown"
    SYSTEM_AUDIT = "system:audit"
    
    # File operations
    FILE_UPLOAD = "file:upload"
    FILE_DOWNLOAD = "file:download"
    FILE_DELETE = "file:delete"
    FILE_ENCRYPT = "file:encrypt"
    FILE_DECRYPT = "file:decrypt"
    
    # Analytics
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"
    ANALYTICS_ADVANCED = "analytics:advanced"
    
    # Security operations
    SECURITY_MONITOR = "security:monitor"
    SECURITY_INCIDENT = "security:incident"
    SECURITY_AUDIT = "security:audit"
    SECURITY_CONFIGURE = "security:configure"
    
    # Military-specific
    TACTICAL_READ = "tactical:read"
    TACTICAL_WRITE = "tactical:write"
    INTELLIGENCE_READ = "intelligence:read"
    INTELLIGENCE_WRITE = "intelligence:write"
    CLASSIFIED_ACCESS = "classified:access"
    OPERATIONS_COMMAND = "operations:command"


# Military-grade role-permission mapping
ROLE_PERMISSIONS: Dict[UserRole, list[Permission]] = {
    UserRole.SUPER_ADMIN: list(Permission),  # All permissions
    
    UserRole.ADMIN: [
        Permission.DATA_READ, Permission.DATA_WRITE, Permission.DATA_DELETE, Permission.DATA_EXPORT,
        Permission.USER_READ, Permission.USER_WRITE, Permission.USER_DELETE, Permission.USER_AUDIT,
        Permission.SYSTEM_MONITOR, Permission.SYSTEM_CONFIG, Permission.SYSTEM_BACKUP, Permission.SYSTEM_AUDIT,
        Permission.FILE_UPLOAD, Permission.FILE_DOWNLOAD, Permission.FILE_DELETE,
        Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT, Permission.ANALYTICS_ADVANCED,
        Permission.SECURITY_MONITOR, Permission.SECURITY_AUDIT, Permission.SECURITY_CONFIGURE,
    ],
    
    UserRole.COMMANDER: [
        Permission.DATA_READ, Permission.DATA_WRITE, Permission.DATA_EXPORT, Permission.DATA_CLASSIFY,
        Permission.USER_READ, Permission.USER_WRITE, Permission.USER_SECURITY_CLEAR,
        Permission.SYSTEM_MONITOR, Permission.SYSTEM_CONFIG,
        Permission.FILE_UPLOAD, Permission.FILE_DOWNLOAD, Permission.FILE_ENCRYPT, Permission.FILE_DECRYPT,
        Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT, Permission.ANALYTICS_ADVANCED,
        Permission.SECURITY_MONITOR, Permission.SECURITY_INCIDENT,
        Permission.TACTICAL_READ, Permission.TACTICAL_WRITE,
        Permission.INTELLIGENCE_READ, Permission.INTELLIGENCE_WRITE,
        Permission.CLASSIFIED_ACCESS, Permission.OPERATIONS_COMMAND,
    ],
    
    UserRole.OFFICER: [
        Permission.DATA_READ, Permission.DATA_WRITE, Permission.DATA_EXPORT,
        Permission.USER_READ,
        Permission.FILE_UPLOAD, Permission.FILE_DOWNLOAD,
        Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT,
        Permission.TACTICAL_READ, Permission.TACTICAL_WRITE,
        Permission.INTELLIGENCE_READ,
    ],
    
    UserRole.ANALYST: [
        Permission.DATA_READ, Permission.DATA_EXPORT,
        Permission.FILE_UPLOAD, Permission.FILE_DOWNLOAD,
        Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT, Permission.ANALYTICS_ADVANCED,
        Permission.INTELLIGENCE_READ, Permission.INTELLIGENCE_WRITE,
    ],
    
    UserRole.SPECIALIST: [
        Permission.DATA_READ, Permission.DATA_WRITE, Permission.DATA_EXPORT,
        Permission.FILE_UPLOAD, Permission.FILE_DOWNLOAD,
        Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT,
        Permission.SYSTEM_MONITOR,
    ],
    
    UserRole.OPERATOR: [
        Permission.DATA_READ, Permission.DATA_WRITE,
        Permission.FILE_UPLOAD, Permission.FILE_DOWNLOAD,
        Permission.ANALYTICS_VIEW,
        Permission.SYSTEM_MONITOR,
    ],
    
    UserRole.VIEWER: [
        Permission.DATA_READ,
        Permission.FILE_DOWNLOAD,
        Permission.ANALYTICS_VIEW,
    ],
    
    UserRole.GUEST: [
        Permission.DATA_READ,
        Permission.ANALYTICS_VIEW,
    ],
}


class AuditTrailManager:
    """Comprehensive audit trail management system"""
    
    def __init__(self):
        self.audit_queue = asyncio.Queue()
        self.audit_file_path = "/var/log/idf/security_audit.log"
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._running = False
        self._audit_task = None
    
    async def start(self):
        """Start audit trail processing"""
        if not self._running:
            self._running = True
            self._audit_task = asyncio.create_task(self._process_audit_queue())
            logger.info("Audit trail manager started")
    
    async def stop(self):
        """Stop audit trail processing"""
        self._running = False
        if self._audit_task:
            self._audit_task.cancel()
            try:
                await self._audit_task
            except asyncio.CancelledError:
                pass
        logger.info("Audit trail manager stopped")
    
    async def log_security_event(self, event: SecurityEvent):
        """Log security event to audit trail"""
        try:
            await self.audit_queue.put(event)
        except Exception as e:
            logger.error("Failed to queue security event", error=str(e))
    
    async def _process_audit_queue(self):
        """Process audit events from queue"""
        while self._running:
            try:
                event = await asyncio.wait_for(self.audit_queue.get(), timeout=1.0)
                await self._write_audit_event(event)
                await self._store_audit_event_redis(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("Error processing audit event", error=str(e))
    
    async def _write_audit_event(self, event: SecurityEvent):
        """Write audit event to file"""
        try:
            audit_line = json.dumps(event.to_dict()) + "\n"
            
            # Use thread executor for file I/O to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                self.executor, 
                self._write_to_file, 
                audit_line
            )
            
        except Exception as e:
            logger.error("Failed to write audit event to file", error=str(e))
    
    def _write_to_file(self, content: str):
        """Write content to audit file (blocking operation)"""
        import os
        os.makedirs(os.path.dirname(self.audit_file_path), exist_ok=True)
        with open(self.audit_file_path, 'a', encoding='utf-8') as f:
            f.write(content)
    
    async def _store_audit_event_redis(self, event: SecurityEvent):
        """Store audit event in Redis for fast querying"""
        try:
            if redis_client:
                # Store in Redis with expiration
                redis_key = f"audit:{event.event_id}"
                await redis_client.set(
                    redis_key, 
                    event.to_dict(), 
                    ttl=settings.security.AUDIT_LOG_RETENTION_DAYS * 24 * 3600
                )
                
                # Add to time-based index for querying
                date_key = f"audit:date:{event.timestamp.strftime('%Y-%m-%d')}"
                await redis_client.client.lpush(date_key, event.event_id)
                await redis_client.client.expire(
                    date_key, 
                    settings.security.AUDIT_LOG_RETENTION_DAYS * 24 * 3600
                )
                
        except Exception as e:
            logger.error("Failed to store audit event in Redis", error=str(e))
    
    async def query_audit_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[SecurityEventType] = None,
        user_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """Query audit events with filters"""
        try:
            if not redis_client:
                return []
            
            # Get event IDs from date range
            events = []
            current_date = start_date or datetime.utcnow() - timedelta(days=30)
            end_date = end_date or datetime.utcnow()
            
            while current_date <= end_date:
                date_key = f"audit:date:{current_date.strftime('%Y-%m-%d')}"
                event_ids = await redis_client.client.lrange(date_key, 0, -1)
                
                for event_id in event_ids:
                    if len(events) >= limit:
                        break
                    
                    event_data = await redis_client.get(f"audit:{event_id}")
                    if event_data:
                        event = SecurityEvent(**event_data)
                        
                        # Apply filters
                        if event_type and event.event_type != event_type:
                            continue
                        if user_id and event.user_id != user_id:
                            continue
                        if severity and event.severity != severity:
                            continue
                        
                        events.append(event)
                
                current_date += timedelta(days=1)
            
            return events
            
        except Exception as e:
            logger.error("Failed to query audit events", error=str(e))
            return []


class ThreatDetectionSystem:
    """Advanced threat detection and monitoring system"""
    
    def __init__(self):
        self.threat_patterns = {
            'brute_force': {
                'max_attempts': 5,
                'time_window': 300,  # 5 minutes
                'severity': 'HIGH'
            },
            'sql_injection': {
                'patterns': [
                    r"(union|select|insert|update|delete|drop|alter|create)\s+",
                    r"['\"]s*(or|and)\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+",
                    r"['\"]s*(or|and)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+"
                ],
                'severity': 'CRITICAL'
            },
            'xss_attempt': {
                'patterns': [
                    r"<script[^>]*>.*?</script>",
                    r"javascript:\s*",
                    r"on\w+\s*=\s*['\"].*?['\"]?"
                ],
                'severity': 'HIGH'
            },
            'suspicious_user_agent': {
                'patterns': [
                    r"(nmap|sqlmap|nikto|burp|owasp|zap)",
                    r"(bot|crawler|spider|scraper)"
                ],
                'severity': 'MEDIUM'
            }
        }
        self.failed_attempts = defaultdict(list)
        self.threat_indicators = []
        self.geo_db = None
        self._init_geo_db()
    
    def _init_geo_db(self):
        """Initialize GeoIP database if available"""
        try:
            # Try to load GeoIP database (optional)
            import geoip2.database
            self.geo_db = geoip2.database.Reader('/usr/share/GeoIP/GeoLite2-City.mmdb')
        except Exception:
            logger.warning("GeoIP database not available")
    
    async def detect_threats(self, request_data: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect potential threats in request data"""
        threats = []
        
        # Check for brute force attacks
        if threat := await self._check_brute_force(request_data):
            threats.append(threat)
        
        # Check for SQL injection attempts
        if threat := await self._check_sql_injection(request_data):
            threats.append(threat)
        
        # Check for XSS attempts
        if threat := await self._check_xss_attempts(request_data):
            threats.append(threat)
        
        # Check for suspicious user agents
        if threat := await self._check_suspicious_user_agent(request_data):
            threats.append(threat)
        
        # Check for geographical anomalies
        if threat := await self._check_geo_anomalies(request_data):
            threats.append(threat)
        
        return threats
    
    async def _check_brute_force(self, request_data: Dict[str, Any]) -> Optional[ThreatIndicator]:
        """Check for brute force attack patterns"""
        try:
            ip = request_data.get('ip')
            event_type = request_data.get('event_type')
            
            if not ip or event_type != SecurityEventType.LOGIN_FAILURE:
                return None
            
            # Track failed attempts
            now = time.time()
            self.failed_attempts[ip] = [
                attempt for attempt in self.failed_attempts[ip]
                if now - attempt < self.threat_patterns['brute_force']['time_window']
            ]
            
            self.failed_attempts[ip].append(now)
            
            if len(self.failed_attempts[ip]) >= self.threat_patterns['brute_force']['max_attempts']:
                return ThreatIndicator(
                    indicator_id=str(uuid.uuid4()),
                    threat_type='brute_force',
                    severity=self.threat_patterns['brute_force']['severity'],
                    description=f"Brute force attack detected from {ip}",
                    source_ip=ip,
                    detected_at=datetime.utcnow(),
                    details={
                        'attempts': len(self.failed_attempts[ip]),
                        'time_window': self.threat_patterns['brute_force']['time_window']
                    }
                )
            
        except Exception as e:
            logger.error("Error checking brute force", error=str(e))
        
        return None
    
    async def _check_sql_injection(self, request_data: Dict[str, Any]) -> Optional[ThreatIndicator]:
        """Check for SQL injection attempts"""
        try:
            content = str(request_data.get('content', ''))
            
            for pattern in self.threat_patterns['sql_injection']['patterns']:
                if re.search(pattern, content, re.IGNORECASE):
                    return ThreatIndicator(
                        indicator_id=str(uuid.uuid4()),
                        threat_type='sql_injection',
                        severity=self.threat_patterns['sql_injection']['severity'],
                        description=f"SQL injection attempt detected",
                        source_ip=request_data.get('ip', 'unknown'),
                        detected_at=datetime.utcnow(),
                        details={
                            'matched_pattern': pattern,
                            'content_sample': content[:200]
                        }
                    )
            
        except Exception as e:
            logger.error("Error checking SQL injection", error=str(e))
        
        return None
    
    async def _check_xss_attempts(self, request_data: Dict[str, Any]) -> Optional[ThreatIndicator]:
        """Check for XSS attempts"""
        try:
            content = str(request_data.get('content', ''))
            
            for pattern in self.threat_patterns['xss_attempt']['patterns']:
                if re.search(pattern, content, re.IGNORECASE):
                    return ThreatIndicator(
                        indicator_id=str(uuid.uuid4()),
                        threat_type='xss_attempt',
                        severity=self.threat_patterns['xss_attempt']['severity'],
                        description=f"XSS attempt detected",
                        source_ip=request_data.get('ip', 'unknown'),
                        detected_at=datetime.utcnow(),
                        details={
                            'matched_pattern': pattern,
                            'content_sample': content[:200]
                        }
                    )
            
        except Exception as e:
            logger.error("Error checking XSS attempts", error=str(e))
        
        return None
    
    async def _check_suspicious_user_agent(self, request_data: Dict[str, Any]) -> Optional[ThreatIndicator]:
        """Check for suspicious user agents"""
        try:
            user_agent = request_data.get('user_agent', '')
            
            for pattern in self.threat_patterns['suspicious_user_agent']['patterns']:
                if re.search(pattern, user_agent, re.IGNORECASE):
                    return ThreatIndicator(
                        indicator_id=str(uuid.uuid4()),
                        threat_type='suspicious_user_agent',
                        severity=self.threat_patterns['suspicious_user_agent']['severity'],
                        description=f"Suspicious user agent detected",
                        source_ip=request_data.get('ip', 'unknown'),
                        detected_at=datetime.utcnow(),
                        details={
                            'user_agent': user_agent,
                            'matched_pattern': pattern
                        }
                    )
            
        except Exception as e:
            logger.error("Error checking user agent", error=str(e))
        
        return None
    
    async def _check_geo_anomalies(self, request_data: Dict[str, Any]) -> Optional[ThreatIndicator]:
        """Check for geographical anomalies"""
        try:
            if not self.geo_db:
                return None
            
            ip = request_data.get('ip')
            user_id = request_data.get('user_id')
            
            if not ip or not user_id:
                return None
            
            # Get location from IP
            try:
                response = self.geo_db.city(ip)
                country = response.country.iso_code
                
                # Check if country is allowed
                if settings.security.ALLOWED_COUNTRIES and country not in settings.security.ALLOWED_COUNTRIES:
                    return ThreatIndicator(
                        indicator_id=str(uuid.uuid4()),
                        threat_type='geo_anomaly',
                        severity='HIGH',
                        description=f"Access from restricted country: {country}",
                        source_ip=ip,
                        detected_at=datetime.utcnow(),
                        user_id=user_id,
                        details={
                            'country': country,
                            'city': response.city.name,
                            'allowed_countries': settings.security.ALLOWED_COUNTRIES
                        }
                    )
                
            except geoip2.errors.AddressNotFoundError:
                pass
            
        except Exception as e:
            logger.error("Error checking geo anomalies", error=str(e))
        
        return None


class ComplianceMonitor:
    """Security compliance monitoring system"""
    
    def __init__(self):
        self.compliance_rules = {
            'password_policy': {
                'min_length': 12,
                'require_uppercase': True,
                'require_lowercase': True,
                'require_numbers': True,
                'require_special': True,
                'max_age_days': 90
            },
            'session_management': {
                'max_idle_time': 3600,  # 1 hour
                'require_https': True,
                'secure_cookies': True
            },
            'access_control': {
                'max_failed_attempts': 5,
                'lockout_duration': 1800,  # 30 minutes
                'require_2fa': True
            },
            'audit_logging': {
                'log_all_access': True,
                'log_failed_attempts': True,
                'retention_days': 365
            }
        }
        self.compliance_violations = []
    
    async def check_compliance(self, context: Dict[str, Any]) -> List[str]:
        """Check security compliance violations"""
        violations = []
        
        # Check password policy compliance
        if password_violations := await self._check_password_policy(context):
            violations.extend(password_violations)
        
        # Check session management compliance
        if session_violations := await self._check_session_management(context):
            violations.extend(session_violations)
        
        # Check access control compliance
        if access_violations := await self._check_access_control(context):
            violations.extend(access_violations)
        
        return violations
    
    async def _check_password_policy(self, context: Dict[str, Any]) -> List[str]:
        """Check password policy compliance"""
        violations = []
        
        if password := context.get('password'):
            rules = self.compliance_rules['password_policy']
            
            if len(password) < rules['min_length']:
                violations.append(f"Password too short (min {rules['min_length']} chars)")
            
            if rules['require_uppercase'] and not re.search(r'[A-Z]', password):
                violations.append("Password must contain uppercase letters")
            
            if rules['require_lowercase'] and not re.search(r'[a-z]', password):
                violations.append("Password must contain lowercase letters")
            
            if rules['require_numbers'] and not re.search(r'\d', password):
                violations.append("Password must contain numbers")
            
            if rules['require_special'] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                violations.append("Password must contain special characters")
        
        return violations
    
    async def _check_session_management(self, context: Dict[str, Any]) -> List[str]:
        """Check session management compliance"""
        violations = []
        
        rules = self.compliance_rules['session_management']
        
        if not context.get('https_enabled') and rules['require_https']:
            violations.append("HTTPS required for secure communication")
        
        if not context.get('secure_cookies') and rules['secure_cookies']:
            violations.append("Secure cookie flags required")
        
        return violations
    
    async def _check_access_control(self, context: Dict[str, Any]) -> List[str]:
        """Check access control compliance"""
        violations = []
        
        rules = self.compliance_rules['access_control']
        
        if context.get('failed_attempts', 0) > rules['max_failed_attempts']:
            violations.append(f"Too many failed attempts (max {rules['max_failed_attempts']})")
        
        if context.get('requires_2fa') and not context.get('2fa_enabled'):
            violations.append("Two-factor authentication required")
        
        return violations


class SecurityMetrics:
    """Security metrics and statistics collector"""
    
    def __init__(self):
        self.metrics = {
            'events_by_type': defaultdict(int),
            'events_by_severity': defaultdict(int),
            'threats_detected': 0,
            'login_attempts': 0,
            'failed_logins': 0,
            'blocked_ips': set(),
            'compliance_violations': 0
        }
    
    def record_event(self, event_type: SecurityEventType, result: str, threat_count: int = 0):
        """Record security event metrics"""
        self.metrics['events_by_type'][event_type] += 1
        
        if event_type == SecurityEventType.LOGIN_SUCCESS:
            self.metrics['login_attempts'] += 1
        elif event_type == SecurityEventType.LOGIN_FAILURE:
            self.metrics['login_attempts'] += 1
            self.metrics['failed_logins'] += 1
        
        if threat_count > 0:
            self.metrics['threats_detected'] += threat_count
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get security metrics summary"""
        total_events = sum(self.metrics['events_by_type'].values())
        success_rate = (
            (self.metrics['login_attempts'] - self.metrics['failed_logins']) / 
            self.metrics['login_attempts'] * 100
            if self.metrics['login_attempts'] > 0 else 0
        )
        
        return {
            'total_events': total_events,
            'events_by_type': dict(self.metrics['events_by_type']),
            'events_by_severity': dict(self.metrics['events_by_severity']),
            'threats_detected': self.metrics['threats_detected'],
            'login_success_rate': success_rate,
            'blocked_ips_count': len(self.metrics['blocked_ips']),
            'compliance_violations': self.metrics['compliance_violations']
        }


class SecurityManager:
    """Enhanced central security management class"""
    
    def __init__(self):
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=settings.security.PASSWORD_HASH_ROUNDS
        )
        self.failed_attempts = {}  # In production, store in Redis
        self.audit_manager = AuditTrailManager()
        self.threat_detector = ThreatDetectionSystem()
        self.compliance_monitor = ComplianceMonitor()
        self._security_metrics = SecurityMetrics()
    
    async def start_security_systems(self):
        """Start all security subsystems"""
        await self.audit_manager.start()
        logger.info("Security systems started")
    
    async def stop_security_systems(self):
        """Stop all security subsystems"""
        await self.audit_manager.stop()
        logger.info("Security systems stopped")
    
    async def log_security_event(
        self,
        event_type: SecurityEventType,
        user_id: Optional[str] = None,
        user_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        action: str = "",
        result: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
        severity: str = "LOW",
        session_id: Optional[str] = None
    ):
        """Log security event with threat detection"""
        try:
            event = SecurityEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                user_id=user_id,
                user_ip=user_ip,
                user_agent=user_agent,
                resource=resource,
                action=action,
                result=result,
                timestamp=datetime.utcnow(),
                details=details or {},
                severity=severity,
                session_id=session_id
            )
            
            # Log to audit trail
            await self.audit_manager.log_security_event(event)
            
            # Check for threats
            request_data = {
                'ip': user_ip,
                'user_id': user_id,
                'user_agent': user_agent,
                'event_type': event_type,
                'content': str(details) if details else ''
            }
            
            threats = await self.threat_detector.detect_threats(request_data)
            
            # Log detected threats
            for threat in threats:
                threat_event = SecurityEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=SecurityEventType.THREAT_DETECTED,
                    user_id=user_id,
                    user_ip=user_ip,
                    user_agent=user_agent,
                    resource=resource,
                    action=f"threat_detected:{threat.threat_type}",
                    result="DETECTED",
                    timestamp=datetime.utcnow(),
                    details=threat.to_dict(),
                    severity=threat.severity,
                    session_id=session_id
                )
                
                await self.audit_manager.log_security_event(threat_event)
            
            # Update security metrics
            self._security_metrics.record_event(event_type, result, len(threats))
            
        except Exception as e:
            logger.error("Failed to log security event", error=str(e))
    
    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def validate_password_strength(self, password: str) -> tuple[bool, list[str]]:
        """Validate password meets security requirements"""
        errors = []
        
        if len(password) < settings.security.PASSWORD_MIN_LENGTH:
            errors.append(f"Password must be at least {settings.security.PASSWORD_MIN_LENGTH} characters long")
        
        if settings.security.PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if settings.security.PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if settings.security.PASSWORD_REQUIRE_NUMBERS and not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if settings.security.PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Check for common passwords
        common_passwords = ['password', '123456', 'admin', 'qwerty', 'letmein']
        if password.lower() in common_passwords:
            errors.append("Password is too common")
        
        return len(errors) == 0, errors
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    def constant_time_compare(self, a: str, b: str) -> bool:
        """Constant time string comparison to prevent timing attacks"""
        return hmac.compare_digest(a.encode('utf-8'), b.encode('utf-8'))


class JWTManager:
    """JWT token management with enhanced security"""
    
    def __init__(self):
        self.security_manager = SecurityManager()
    
    async def create_access_token(
        self, 
        data: dict, 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.security.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        # Add standard claims
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
            "jti": self.security_manager.generate_secure_token(16),  # JWT ID for blacklisting
        })
        
        token = jwt.encode(
            to_encode, 
            settings.security.SECRET_KEY, 
            algorithm=settings.security.ALGORITHM
        )
        
        # Store token metadata in Redis for tracking
        await self._store_token_metadata(to_encode["jti"], data.get("sub"), expire)
        
        return token
    
    async def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(
            minutes=settings.security.REFRESH_TOKEN_EXPIRE_MINUTES
        )
        
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": self.security_manager.generate_secure_token(16),
        }
        
        token = jwt.encode(
            to_encode,
            settings.security.SECRET_KEY,
            algorithm=settings.security.ALGORITHM
        )
        
        # Store refresh token metadata
        await self._store_token_metadata(to_encode["jti"], user_id, expire, is_refresh=True)
        
        return token
    
    async def verify_token(self, token: str, token_type: str = "access") -> Optional[dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.security.SECRET_KEY,
                algorithms=[settings.security.ALGORITHM]
            )
            
            # Check token type
            if payload.get("type") != token_type:
                logger.warning("Invalid token type", expected=token_type, actual=payload.get("type"))
                return None
            
            # Check if token is blacklisted
            jti = payload.get("jti")
            if jti and await self._is_token_blacklisted(jti):
                logger.warning("Token is blacklisted", jti=jti)
                return None
            
            return payload
            
        except JWTError as e:
            logger.warning("JWT verification failed", error=str(e))
            return None
    
    async def blacklist_token(self, jti: str):
        """Add token to blacklist"""
        await redis_client.set(
            f"blacklist:{jti}",
            True,
            ttl=settings.security.REFRESH_TOKEN_EXPIRE_MINUTES * 60
        )
    
    async def _store_token_metadata(
        self, 
        jti: str, 
        user_id: str, 
        expires: datetime, 
        is_refresh: bool = False
    ):
        """Store token metadata for tracking"""
        metadata = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires.isoformat(),
            "is_refresh": is_refresh,
        }
        
        ttl = int((expires - datetime.utcnow()).total_seconds())
        await redis_client.set(f"token:{jti}", metadata, ttl=ttl)
    
    async def _is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted"""
        result = await redis_client.get(f"blacklist:{jti}")
        return result is not None


class SecurityValidator:
    """Input validation and sanitization utilities"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """Validate IP address format"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def sanitize_input(input_str: str, max_length: int = 1000) -> str:
        """Sanitize user input"""
        # Remove null bytes
        sanitized = input_str.replace('\x00', '')
        
        # Limit length
        sanitized = sanitized[:max_length]
        
        # Remove potentially dangerous characters for SQL injection
        dangerous_chars = ['<script', '</script>', 'javascript:', 'data:', 'vbscript:']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized
    
    @staticmethod
    def validate_file_name(filename: str) -> bool:
        """Validate file name for security"""
        # Check for directory traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return False
        
        # Check for reserved names (Windows)
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 
                         'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 
                         'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 
                         'LPT7', 'LPT8', 'LPT9']
        
        base_name = filename.split('.')[0].upper()
        if base_name in reserved_names:
            return False
        
        # Check for valid characters
        valid_pattern = r'^[a-zA-Z0-9._\-\(\)\[\] ]+$'
        return re.match(valid_pattern, filename) is not None


# Global instances
security_manager = SecurityManager()
jwt_manager = JWTManager()
security_validator = SecurityValidator()


# Additional security utilities
class SecurityContext:
    """Thread-local security context for request processing"""
    
    def __init__(self):
        self._context = threading.local()
    
    def set_user(self, user_id: str, role: UserRole, permissions: List[Permission]):
        """Set current user context"""
        self._context.user_id = user_id
        self._context.role = role
        self._context.permissions = permissions
    
    def get_user_id(self) -> Optional[str]:
        """Get current user ID"""
        return getattr(self._context, 'user_id', None)
    
    def get_user_role(self) -> Optional[UserRole]:
        """Get current user role"""
        return getattr(self._context, 'role', None)
    
    def get_user_permissions(self) -> List[Permission]:
        """Get current user permissions"""
        return getattr(self._context, 'permissions', [])
    
    def clear(self):
        """Clear security context"""
        for attr in ['user_id', 'role', 'permissions']:
            if hasattr(self._context, attr):
                delattr(self._context, attr)


# Context managers for security operations
@asynccontextmanager
async def security_audit_context(
    action: str,
    resource: Optional[str] = None,
    user_id: Optional[str] = None,
    user_ip: Optional[str] = None
):
    """Context manager for automatic security auditing"""
    start_time = datetime.utcnow()
    
    try:
        # Log start of operation
        await security_manager.log_security_event(
            SecurityEventType.DATA_ACCESS,
            user_id=user_id,
            user_ip=user_ip,
            resource=resource,
            action=f"start:{action}",
            result="STARTED",
            severity="LOW"
        )
        
        yield
        
        # Log successful completion
        await security_manager.log_security_event(
            SecurityEventType.DATA_ACCESS,
            user_id=user_id,
            user_ip=user_ip,
            resource=resource,
            action=f"complete:{action}",
            result="SUCCESS",
            details={
                "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000)
            },
            severity="LOW"
        )
        
    except Exception as e:
        # Log failure
        await security_manager.log_security_event(
            SecurityEventType.SECURITY_VIOLATION,
            user_id=user_id,
            user_ip=user_ip,
            resource=resource,
            action=f"failed:{action}",
            result="FAILURE",
            details={
                "error": str(e),
                "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000)
            },
            severity="HIGH"
        )
        raise


class MilitarySecurityEnforcer:
    """Military-grade security enforcement utilities"""
    
    @staticmethod
    def require_clearance_level(required_level: str):
        """Decorator to require specific security clearance level"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Check clearance level (implementation depends on your user model)
                # This is a placeholder for actual clearance verification
                user_clearance = kwargs.get('user_clearance', 'PUBLIC')
                
                clearance_hierarchy = {
                    'PUBLIC': 0,
                    'CONFIDENTIAL': 1,
                    'SECRET': 2,
                    'TOP_SECRET': 3
                }
                
                if clearance_hierarchy.get(user_clearance, 0) < clearance_hierarchy.get(required_level, 999):
                    raise PermissionError(f"Insufficient clearance level. Required: {required_level}")
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def classify_data(classification: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add classification metadata to data"""
        return {
            **data,
            '_classification': classification,
            '_classified_at': datetime.utcnow().isoformat(),
            '_classification_authority': 'IDF_SYSTEM'
        }
    
    @staticmethod
    def sanitize_classified_data(data: Dict[str, Any], user_clearance: str) -> Dict[str, Any]:
        """Remove or redact classified information based on user clearance"""
        if not isinstance(data, dict):
            return data
        
        classification = data.get('_classification', 'PUBLIC')
        
        clearance_hierarchy = {
            'PUBLIC': 0,
            'CONFIDENTIAL': 1,
            'SECRET': 2,
            'TOP_SECRET': 3
        }
        
        user_level = clearance_hierarchy.get(user_clearance, 0)
        data_level = clearance_hierarchy.get(classification, 0)
        
        if user_level < data_level:
            return {
                'message': '[CLASSIFIED]',
                'classification': classification,
                'access_denied': True
            }
        
        return data


# Global security context
security_context = SecurityContext()
military_enforcer = MilitarySecurityEnforcer()


# Enhanced helper functions for FastAPI dependencies
def get_password_hash(password: str) -> str:
    """Get password hash - wrapper function"""
    return security_manager.hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password - wrapper function"""
    return security_manager.verify_password(plain_password, hashed_password)


def check_permissions(user_role: UserRole, required_permission: Permission) -> bool:
    """Check if user role has required permission"""
    user_permissions = ROLE_PERMISSIONS.get(user_role, [])
    return required_permission in user_permissions


def check_multiple_permissions(user_role: UserRole, required_permissions: list[Permission]) -> bool:
    """Check if user role has all required permissions"""
    user_permissions = ROLE_PERMISSIONS.get(user_role, [])
    return all(permission in user_permissions for permission in required_permissions)


def require_permission(permission: Permission):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_role = security_context.get_user_role()
            if not user_role or not check_permissions(user_role, permission):
                raise PermissionError(f"Required permission: {permission}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role: UserRole):
    """Decorator to require specific role or higher"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_role = security_context.get_user_role()
            
            # Define role hierarchy
            role_hierarchy = {
                UserRole.GUEST: 0,
                UserRole.VIEWER: 1,
                UserRole.OPERATOR: 2,
                UserRole.SPECIALIST: 3,
                UserRole.ANALYST: 4,
                UserRole.OFFICER: 5,
                UserRole.COMMANDER: 6,
                UserRole.ADMIN: 7,
                UserRole.SUPER_ADMIN: 8
            }
            
            if not user_role or role_hierarchy.get(user_role, 0) < role_hierarchy.get(role, 999):
                raise PermissionError(f"Required role: {role} or higher")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def initialize_security_systems():
    """Initialize all security systems"""
    try:
        await security_manager.start_security_systems()
        logger.info("Military-grade security systems initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize security systems", error=str(e))
        raise


async def shutdown_security_systems():
    """Shutdown all security systems"""
    try:
        await security_manager.stop_security_systems()
        logger.info("Security systems shutdown completed")
    except Exception as e:
        logger.error("Error during security systems shutdown", error=str(e))


# Security monitoring utilities
class SecurityMonitor:
    """Real-time security monitoring and alerting"""
    
    def __init__(self):
        self.alert_thresholds = {
            'failed_logins_per_hour': 50,
            'threats_per_hour': 10,
            'compliance_violations_per_hour': 5
        }
        self.metrics_window = 3600  # 1 hour
    
    async def check_security_alerts(self) -> List[Dict[str, Any]]:
        """Check for security alerts based on metrics"""
        alerts = []
        
        try:
            metrics = security_manager._security_metrics.get_metrics_summary()
            
            # Check for excessive failed logins
            if metrics['failed_logins'] > self.alert_thresholds['failed_logins_per_hour']:
                alerts.append({
                    'type': 'SECURITY_ALERT',
                    'severity': 'HIGH',
                    'message': f"High number of failed logins: {metrics['failed_logins']}",
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            # Check for high threat detection
            if metrics['threats_detected'] > self.alert_thresholds['threats_per_hour']:
                alerts.append({
                    'type': 'THREAT_ALERT',
                    'severity': 'CRITICAL',
                    'message': f"High threat detection rate: {metrics['threats_detected']}",
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            # Check for compliance violations
            if metrics['compliance_violations'] > self.alert_thresholds['compliance_violations_per_hour']:
                alerts.append({
                    'type': 'COMPLIANCE_ALERT',
                    'severity': 'MEDIUM',
                    'message': f"High compliance violations: {metrics['compliance_violations']}",
                    'timestamp': datetime.utcnow().isoformat()
                })
            
        except Exception as e:
            logger.error("Error checking security alerts", error=str(e))
        
        return alerts
    
    async def generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        try:
            metrics = security_manager._security_metrics.get_metrics_summary()
            alerts = await self.check_security_alerts()
            
            return {
                'report_id': str(uuid.uuid4()),
                'generated_at': datetime.utcnow().isoformat(),
                'metrics': metrics,
                'alerts': alerts,
                'system_status': 'OPERATIONAL' if not alerts else 'ALERT',
                'recommendations': self._generate_recommendations(metrics, alerts)
            }
            
        except Exception as e:
            logger.error("Error generating security report", error=str(e))
            return {}
    
    def _generate_recommendations(self, metrics: Dict, alerts: List) -> List[str]:
        """Generate security recommendations based on metrics and alerts"""
        recommendations = []
        
        if metrics.get('login_success_rate', 100) < 80:
            recommendations.append("Consider implementing additional authentication factors")
        
        if metrics.get('threats_detected', 0) > 0:
            recommendations.append("Review and strengthen threat detection rules")
        
        if len(alerts) > 0:
            recommendations.append("Immediate security review required")
        
        return recommendations


# Global security monitor
security_monitor = SecurityMonitor()