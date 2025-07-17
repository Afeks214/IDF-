#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core Configuration System with Military-Grade Security Settings
IDF Testing Infrastructure
"""

import secrets
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseSettings, validator, AnyHttpUrl
from pydantic_settings import BaseSettings
import os


class SecuritySettings(BaseSettings):
    """Military-grade security configuration"""
    
    # JWT Configuration
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    
    # Session Security
    SESSION_SECRET_KEY: str = secrets.token_urlsafe(32)
    SESSION_EXPIRE_MINUTES: int = 60
    SESSION_SECURE_ONLY: bool = True
    SESSION_HTTPONLY: bool = True
    SESSION_SAMESITE: str = "strict"
    
    # Password Security
    PASSWORD_MIN_LENGTH: int = 12
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    PASSWORD_HASH_ROUNDS: int = 14  # bcrypt rounds
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    RATE_LIMIT_PER_DAY: int = 10000
    AUTH_RATE_LIMIT_PER_MINUTE: int = 5
    
    # Encryption
    ENCRYPTION_KEY: str = secrets.token_urlsafe(32)
    DATA_ENCRYPTION_ALGORITHM: str = "AES-256-GCM"
    
    # Security Headers
    SECURITY_HEADERS_ENABLED: bool = True
    HSTS_MAX_AGE: int = 31536000  # 1 year
    CONTENT_SECURITY_POLICY: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' https:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none';"
    )
    
    # File Upload Security
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: List[str] = [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        "application/vnd.ms-excel",  # .xls
        "text/csv",  # .csv
        "application/pdf",  # .pdf
        "image/jpeg",  # .jpg
        "image/png",  # .png
    ]
    UPLOAD_SCAN_ENABLED: bool = True
    
    # Audit Logging
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_LEVEL: str = "INFO"
    AUDIT_LOG_RETENTION_DAYS: int = 365
    
    # IP Security
    TRUSTED_IP_RANGES: List[str] = []
    BLOCKED_IP_RANGES: List[str] = []
    GEO_BLOCKING_ENABLED: bool = False
    ALLOWED_COUNTRIES: List[str] = ["IL"]  # Israel
    
    # API Security
    API_KEY_ENABLED: bool = True
    API_KEY_HEADER: str = "X-API-Key"
    CORS_STRICT_MODE: bool = True
    
    class Config:
        env_file = ".env"
        env_prefix = "SECURITY_"


class Settings(BaseSettings):
    """Main application settings with integrated security"""
    
    # Application
    PROJECT_NAME: str = "IDF Testing Infrastructure"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://idf_user:secure_password@localhost:5432/idf_testing"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_SSL: bool = False
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Trusted Hosts
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "0.0.0.0"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Security Settings Integration
    security: SecuritySettings = SecuritySettings()
    
    # Email (Optional)
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None
    
    # Monitoring
    MONITORING_ENABLED: bool = True
    METRICS_ENABLED: bool = True
    HEALTH_CHECK_ENABLED: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Security validation on startup
def validate_security_settings():
    """Validate security settings for production readiness"""
    issues = []
    
    if settings.ENVIRONMENT == "production":
        # Check critical security settings
        if settings.DEBUG:
            issues.append("DEBUG mode should be disabled in production")
        
        if len(settings.security.SECRET_KEY) < 32:
            issues.append("SECRET_KEY must be at least 32 characters in production")
            
        if not settings.security.SESSION_SECURE_ONLY:
            issues.append("Session cookies must be secure in production")
            
        if not settings.security.SECURITY_HEADERS_ENABLED:
            issues.append("Security headers must be enabled in production")
            
        if settings.security.RATE_LIMIT_PER_MINUTE > 100:
            issues.append("Rate limiting should be stricter in production")
    
    if issues:
        print("SECURITY WARNINGS:")
        for issue in issues:
            print(f"  - {issue}")
        
        if settings.ENVIRONMENT == "production":
            raise ValueError("Critical security issues detected. Fix before deploying to production.")
    
    return len(issues) == 0


# Validate on import
validate_security_settings()