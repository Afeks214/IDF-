#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Military-Grade JWT Authentication and Security System
IDF Testing Infrastructure
"""

import secrets
from datetime import datetime, timedelta
from typing import Any, Union, Optional, Dict
from passlib.context import CryptContext
from jose import JWTError, jwt
import structlog
import re
import hashlib
import hmac
from enum import Enum
import ipaddress

from .config import settings
from .redis_client import redis_client

logger = structlog.get_logger()


class UserRole(str, Enum):
    """User roles for RBAC"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    OFFICER = "officer"
    ANALYST = "analyst"
    VIEWER = "viewer"
    GUEST = "guest"


class Permission(str, Enum):
    """Granular permissions for RBAC"""
    # Data operations
    DATA_READ = "data:read"
    DATA_WRITE = "data:write"
    DATA_DELETE = "data:delete"
    DATA_EXPORT = "data:export"
    
    # User management
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_ROLE_CHANGE = "user:role_change"
    
    # System operations
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_BACKUP = "system:backup"
    
    # File operations
    FILE_UPLOAD = "file:upload"
    FILE_DOWNLOAD = "file:download"
    FILE_DELETE = "file:delete"
    
    # Analytics
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"


# Role-permission mapping
ROLE_PERMISSIONS: Dict[UserRole, list[Permission]] = {
    UserRole.SUPER_ADMIN: list(Permission),  # All permissions
    UserRole.ADMIN: [
        Permission.DATA_READ, Permission.DATA_WRITE, Permission.DATA_DELETE, Permission.DATA_EXPORT,
        Permission.USER_READ, Permission.USER_WRITE, Permission.USER_DELETE,
        Permission.SYSTEM_MONITOR, Permission.SYSTEM_CONFIG,
        Permission.FILE_UPLOAD, Permission.FILE_DOWNLOAD, Permission.FILE_DELETE,
        Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT,
    ],
    UserRole.OFFICER: [
        Permission.DATA_READ, Permission.DATA_WRITE, Permission.DATA_EXPORT,
        Permission.USER_READ,
        Permission.FILE_UPLOAD, Permission.FILE_DOWNLOAD,
        Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT,
    ],
    UserRole.ANALYST: [
        Permission.DATA_READ, Permission.DATA_EXPORT,
        Permission.FILE_UPLOAD, Permission.FILE_DOWNLOAD,
        Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT,
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


class SecurityManager:
    """Central security management class"""
    
    def __init__(self):
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=settings.security.PASSWORD_HASH_ROUNDS
        )
        self.failed_attempts = {}  # In production, store in Redis
    
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
        await redis_client.set_secure(
            f"blacklist:{jti}",
            True,
            expire_seconds=settings.security.REFRESH_TOKEN_EXPIRE_MINUTES * 60
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
        await redis_client.set_secure(f"token:{jti}", metadata, expire_seconds=ttl)
    
    async def _is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted"""
        result = await redis_client.get_secure(f"blacklist:{jti}")
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


# Helper functions for FastAPI dependencies
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