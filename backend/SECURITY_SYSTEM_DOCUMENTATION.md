# Military-Grade Security System - IDF Testing Infrastructure

## Overview

This document outlines the comprehensive military-grade security system implemented for the IDF Testing Infrastructure. The system provides advanced authentication, authorization, audit trails, threat detection, and compliance monitoring capabilities.

## 🔐 Core Security Components

### 1. Enhanced JWT Authentication System

- **Military-grade token security** with cryptographically secure JTI (JWT ID) for token tracking
- **Token blacklisting** with Redis-based storage for immediate revocation
- **Refresh token rotation** with secure storage and expiration management
- **Token metadata tracking** for audit trails and security monitoring

### 2. Role-Based Access Control (RBAC)

#### Military Hierarchy Roles:
- **SUPER_ADMIN**: System administrators with full access
- **ADMIN**: Unit administrators with broad permissions
- **COMMANDER**: Military commanders with classified access
- **OFFICER**: Military officers with tactical permissions
- **ANALYST**: Intelligence analysts with analysis capabilities
- **SPECIALIST**: Technical specialists with system access
- **OPERATOR**: System operators with operational permissions
- **VIEWER**: Read-only access users
- **GUEST**: Limited guest access

#### Granular Permissions:
- **Data Operations**: READ, WRITE, DELETE, EXPORT, CLASSIFY, DECLASSIFY
- **User Management**: READ, WRITE, DELETE, ROLE_CHANGE, SECURITY_CLEAR, AUDIT
- **System Operations**: MONITOR, CONFIG, BACKUP, RESTORE, SHUTDOWN, AUDIT
- **File Operations**: UPLOAD, DOWNLOAD, DELETE, ENCRYPT, DECRYPT
- **Analytics**: VIEW, EXPORT, ADVANCED
- **Security Operations**: MONITOR, INCIDENT, AUDIT, CONFIGURE
- **Military-Specific**: TACTICAL_READ/WRITE, INTELLIGENCE_READ/WRITE, CLASSIFIED_ACCESS, OPERATIONS_COMMAND

### 3. Comprehensive Audit Trail System

#### Features:
- **Asynchronous audit logging** to prevent performance impact
- **File-based audit storage** with structured JSON format
- **Redis-based audit indexing** for fast querying
- **Time-based audit retention** with configurable retention periods
- **Comprehensive event tracking** for all security-relevant actions

#### Audit Event Types:
- Login/logout events
- Permission denials
- Data access and modifications
- File operations
- System configuration changes
- Security violations
- Threat detections
- Compliance violations
- Role changes
- Account lockouts

### 4. Advanced Threat Detection System

#### Threat Detection Capabilities:
- **Brute Force Attack Detection**: Monitors failed login attempts with configurable thresholds
- **SQL Injection Detection**: Pattern-based detection of SQL injection attempts
- **XSS Attack Detection**: Identifies cross-site scripting attempts
- **Suspicious User Agent Detection**: Detects automated tools and scanners
- **Geographical Anomaly Detection**: Optional GeoIP-based location monitoring

#### Threat Response:
- **Automatic threat logging** with severity classification
- **Real-time threat indicators** generation
- **IP-based attack tracking** with time-window analysis
- **Configurable threat patterns** for custom detection rules

### 5. Security Compliance Monitoring

#### Compliance Rules:
- **Password Policy Enforcement**: Length, complexity, and age requirements
- **Session Management**: HTTPS requirements, secure cookies, idle timeouts
- **Access Control**: Failed attempt limits, lockout durations, 2FA requirements
- **Audit Logging**: Comprehensive logging requirements and retention

#### Compliance Checking:
- **Real-time compliance validation** during operations
- **Compliance violation reporting** with detailed explanations
- **Automated compliance alerts** for policy violations
- **Configurable compliance rules** for different environments

### 6. Military-Grade Security Enforcer

#### Classification System:
- **Data Classification Levels**: PUBLIC, CONFIDENTIAL, SECRET, TOP_SECRET
- **Automatic Data Sanitization**: Removes classified data based on user clearance
- **Classification Metadata**: Tracks classification authority and timestamps
- **Clearance-based Access Control**: Enforces security clearance requirements

#### Security Decorators:
- **@require_clearance_level**: Enforces minimum clearance requirements
- **@require_permission**: Validates specific permissions
- **@require_role**: Enforces minimum role requirements
- **@security_audit_context**: Automatic audit logging for operations

## 🛡️ Security Features

### Password Security
- **bcrypt hashing** with configurable rounds (default: 14)
- **Password strength validation** with comprehensive requirements
- **Common password detection** and rejection
- **Constant-time comparison** to prevent timing attacks

### Session Management
- **Secure session storage** in Redis with encryption
- **Session timeout management** with automatic cleanup
- **Session activity tracking** for security monitoring
- **Cross-site request forgery protection** with secure cookies

### Input Validation
- **Comprehensive input sanitization** for XSS prevention
- **Email format validation** with regex patterns
- **IP address validation** for network security
- **File name validation** to prevent directory traversal

### Security Headers
- **HTTP Strict Transport Security (HSTS)** enforcement
- **Content Security Policy (CSP)** implementation
- **X-Frame-Options** for clickjacking protection
- **X-Content-Type-Options** for MIME type sniffing protection

## 📊 Security Monitoring

### Real-time Monitoring
- **Security event metrics** collection and analysis
- **Threat detection statistics** with severity tracking
- **Login success/failure rates** monitoring
- **Compliance violation tracking** with trend analysis

### Alerting System
- **Configurable alert thresholds** for different security events
- **Real-time security alerts** for critical threats
- **Security report generation** with recommendations
- **Automated security status assessment**

### Metrics Collection
- **Event-based metrics** for security operations
- **Performance metrics** for security system health
- **Compliance metrics** for regulatory requirements
- **Threat intelligence** for security improvements

## 🔧 Configuration

### Security Settings
All security configurations are centralized in `config.py`:

```python
class SecuritySettings:
    # JWT Configuration
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    
    # Password Security
    PASSWORD_MIN_LENGTH: int = 12
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    PASSWORD_HASH_ROUNDS: int = 14
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    AUTH_RATE_LIMIT_PER_MINUTE: int = 5
    
    # Audit Logging
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 365
    
    # Geographical Security
    ALLOWED_COUNTRIES: List[str] = ["IL"]  # Israel only
```

### Environment Variables
Security settings can be overridden with environment variables:
- `SECURITY_SECRET_KEY`: JWT secret key
- `SECURITY_PASSWORD_MIN_LENGTH`: Minimum password length
- `SECURITY_RATE_LIMIT_PER_MINUTE`: Rate limiting threshold
- `SECURITY_AUDIT_LOG_ENABLED`: Enable/disable audit logging

## 🚀 Usage Examples

### Basic Authentication
```python
from core.security import security_manager, jwt_manager

# Hash password
password_hash = security_manager.hash_password("user_password")

# Verify password
is_valid = security_manager.verify_password("user_password", password_hash)

# Create JWT token
token = await jwt_manager.create_access_token({"sub": "user_id", "role": "officer"})

# Verify JWT token
payload = await jwt_manager.verify_token(token)
```

### RBAC Implementation
```python
from core.security import check_permissions, UserRole, Permission

# Check single permission
has_access = check_permissions(UserRole.OFFICER, Permission.DATA_READ)

# Check multiple permissions
permissions = [Permission.DATA_READ, Permission.DATA_WRITE]
has_all_access = check_multiple_permissions(UserRole.OFFICER, permissions)
```

### Security Decorators
```python
from core.security import require_permission, require_role, Permission, UserRole

@require_permission(Permission.DATA_WRITE)
async def sensitive_operation():
    # Only users with DATA_WRITE permission can access
    pass

@require_role(UserRole.OFFICER)
async def military_operation():
    # Only officers and above can access
    pass
```

### Audit Logging
```python
from core.security import security_manager, SecurityEventType

# Log security event
await security_manager.log_security_event(
    SecurityEventType.DATA_ACCESS,
    user_id="user123",
    user_ip="192.168.1.100",
    resource="/api/classified-data",
    action="read",
    result="SUCCESS",
    severity="HIGH"
)
```

### Threat Detection
```python
from core.security import ThreatDetectionSystem

threat_detector = ThreatDetectionSystem()

# Check for threats in request data
request_data = {
    'ip': '192.168.1.200',
    'user_agent': 'sqlmap/1.0',
    'content': 'SELECT * FROM users'
}

threats = await threat_detector.detect_threats(request_data)
```

## 🔒 Security Best Practices

### Development Guidelines
1. **Always use security decorators** for protected endpoints
2. **Log all security-relevant operations** with appropriate severity
3. **Validate all user inputs** before processing
4. **Use constant-time comparisons** for sensitive data
5. **Implement proper error handling** to prevent information leakage

### Deployment Considerations
1. **Use strong secret keys** in production (32+ characters)
2. **Enable HTTPS** for all communications
3. **Configure proper CORS** settings
4. **Set up log monitoring** for security events
5. **Regular security audits** of the system

### Monitoring and Maintenance
1. **Monitor audit logs** for suspicious activities
2. **Review security reports** regularly
3. **Update threat detection patterns** as needed
4. **Maintain compliance** with security policies
5. **Backup security configurations** and audit data

## 🆘 Incident Response

### Security Incident Handling
1. **Automatic threat detection** and logging
2. **Real-time alerting** for critical security events
3. **Audit trail preservation** for forensic analysis
4. **Automated IP blocking** for detected threats
5. **Compliance violation reporting** for regulatory requirements

### Emergency Procedures
1. **System lockdown** capabilities for critical threats
2. **Emergency access** for administrators
3. **Audit log export** for external analysis
4. **Threat intelligence** sharing with security teams
5. **Recovery procedures** for security breaches

## 📚 Technical Documentation

### File Structure
```
backend/app/core/
├── security.py           # Main security system
├── config.py            # Security configurations
├── redis_client.py      # Redis client for caching
└── ...

backend/
├── test_security_system.py    # Security system tests
└── SECURITY_SYSTEM_DOCUMENTATION.md  # This file
```

### Key Classes
- **SecurityManager**: Central security management
- **AuditTrailManager**: Audit logging system
- **ThreatDetectionSystem**: Threat detection and analysis
- **ComplianceMonitor**: Compliance checking
- **MilitarySecurityEnforcer**: Military-grade enforcement
- **SecurityMonitor**: Real-time monitoring and alerting

### Dependencies
- **bcrypt**: Password hashing
- **jose**: JWT token handling
- **redis**: Caching and session storage
- **structlog**: Structured logging
- **geoip2**: Geographical IP analysis (optional)

## 🎯 Conclusion

This military-grade security system provides comprehensive protection for the IDF Testing Infrastructure with:

- **Multi-layered security** with defense in depth
- **Real-time threat detection** and response
- **Comprehensive audit trails** for compliance
- **Military-grade access control** with classification support
- **Automated security monitoring** and alerting
- **Scalable architecture** for enterprise deployment

The system is designed to meet the highest security standards while maintaining performance and usability for military operations.