#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication Schemas for Military-Grade Security
IDF Testing Infrastructure
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, validator, Field
import re

from ..core.security import UserRole, Permission
from ..models.user import UserStatus, LoginAttemptStatus


class PasswordValidation(BaseModel):
    """Password validation schema"""
    
    password: str = Field(..., min_length=12, max_length=128)
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength according to security policy"""
        from ..core.security import security_manager
        
        is_valid, errors = security_manager.validate_password_strength(v)
        if not is_valid:
            raise ValueError(f"Password does not meet security requirements: {', '.join(errors)}")
        
        return v


class UserCreate(PasswordValidation):
    """Schema for user creation"""
    
    username: str = Field(..., min_length=3, max_length=50, regex=r'^[a-zA-Z0-9_.-]+$')
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=100)
    rank: Optional[str] = Field(None, max_length=50)
    personal_number: Optional[str] = Field(None, max_length=20)
    roles: Optional[List[UserRole]] = Field(default=[UserRole.GUEST])
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Username can only contain letters, numbers, dots, hyphens, and underscores')
        return v.lower()
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format"""
        if v and not re.match(r'^\+?[1-9]\d{1,14}$', v.replace('-', '').replace(' ', '')):
            raise ValueError('Invalid phone number format')
        return v


class UserUpdate(BaseModel):
    """Schema for user updates"""
    
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=100)
    rank: Optional[str] = Field(None, max_length=50)
    personal_number: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    status: Optional[UserStatus] = None
    two_factor_enabled: Optional[bool] = None
    max_concurrent_sessions: Optional[int] = Field(None, ge=1, le=10)
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format"""
        if v and not re.match(r'^\+?[1-9]\d{1,14}$', v.replace('-', '').replace(' ', '')):
            raise ValueError('Invalid phone number format')
        return v


class PasswordChange(PasswordValidation):
    """Schema for password change"""
    
    current_password: str
    new_password: str = Field(..., min_length=12, max_length=128)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Ensure passwords match"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('new_password')
    def validate_new_password(cls, v, values):
        """Validate new password is different from current"""
        if 'current_password' in values and v == values['current_password']:
            raise ValueError('New password must be different from current password')
        return v


class LoginRequest(BaseModel):
    """Schema for login request"""
    
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)
    remember_me: bool = False
    two_factor_code: Optional[str] = Field(None, min_length=6, max_length=6)
    
    @validator('username')
    def validate_username(cls, v):
        """Normalize username"""
        return v.lower().strip()
    
    @validator('two_factor_code')
    def validate_2fa_code(cls, v):
        """Validate 2FA code format"""
        if v and not re.match(r'^\d{6}$', v):
            raise ValueError('Two-factor code must be 6 digits')
        return v


class TokenResponse(BaseModel):
    """Schema for token response"""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: "UserResponse"


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    
    refresh_token: str


class UserResponse(BaseModel):
    """Schema for user response"""
    
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    full_name: str
    phone: Optional[str]
    department: Optional[str]
    rank: Optional[str]
    personal_number: Optional[str]
    is_active: bool
    status: UserStatus
    email_verified: bool
    two_factor_enabled: bool
    last_login_at: Optional[datetime]
    last_login_ip: Optional[str]
    password_changed_at: datetime
    must_change_password: bool
    roles: List["RoleResponse"]
    primary_role: UserRole
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class RoleResponse(BaseModel):
    """Schema for role response"""
    
    id: int
    name: str
    display_name: str
    description: Optional[str]
    is_system_role: bool
    
    class Config:
        orm_mode = True


class RoleCreate(BaseModel):
    """Schema for role creation"""
    
    name: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    
    @validator('name')
    def validate_role_name(cls, v):
        """Validate role name format"""
        if not re.match(r'^[a-z_]+$', v):
            raise ValueError('Role name can only contain lowercase letters and underscores')
        return v


class RoleUpdate(BaseModel):
    """Schema for role updates"""
    
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class UserRoleAssignment(BaseModel):
    """Schema for assigning roles to users"""
    
    user_id: int
    role_ids: List[int]
    expires_at: Optional[datetime] = None


class LoginAttemptResponse(BaseModel):
    """Schema for login attempt response"""
    
    id: int
    username_attempted: str
    ip_address: str
    user_agent: Optional[str]
    status: LoginAttemptStatus
    failure_reason: Optional[str]
    geolocation: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        orm_mode = True


class SessionResponse(BaseModel):
    """Schema for session response"""
    
    id: int
    session_id: str
    ip_address: str
    user_agent: Optional[str]
    is_active: bool
    expires_at: datetime
    last_activity: datetime
    created_at: datetime
    
    class Config:
        orm_mode = True


class AuditLogResponse(BaseModel):
    """Schema for audit log response"""
    
    id: int
    user_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Optional[Dict[str, Any]]
    success: bool
    error_message: Optional[str]
    session_id: Optional[str]
    created_at: datetime
    
    class Config:
        orm_mode = True


class SecurityEventResponse(BaseModel):
    """Schema for security event response"""
    
    id: int
    event_type: str
    severity: str
    user_id: Optional[int]
    ip_address: Optional[str]
    description: str
    metadata: Optional[Dict[str, Any]]
    resolved: bool
    resolved_by: Optional[int]
    resolved_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        orm_mode = True


class TwoFactorSetupResponse(BaseModel):
    """Schema for 2FA setup response"""
    
    secret: str
    qr_code_url: str
    backup_codes: List[str]


class TwoFactorVerifyRequest(BaseModel):
    """Schema for 2FA verification request"""
    
    code: str = Field(..., min_length=6, max_length=6)
    
    @validator('code')
    def validate_code(cls, v):
        """Validate 2FA code format"""
        if not re.match(r'^\d{6}$', v):
            raise ValueError('Code must be 6 digits')
        return v


class EmailVerificationRequest(BaseModel):
    """Schema for email verification request"""
    
    token: str


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""
    
    email: EmailStr


class PasswordResetConfirm(PasswordValidation):
    """Schema for password reset confirmation"""
    
    token: str
    new_password: str = Field(..., min_length=12, max_length=128)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Ensure passwords match"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class SecuritySettings(BaseModel):
    """Schema for user security settings"""
    
    two_factor_enabled: bool
    max_concurrent_sessions: int = Field(..., ge=1, le=10)
    email_notifications: bool = True
    login_notifications: bool = True
    
    
class PermissionCheck(BaseModel):
    """Schema for permission check request"""
    
    permission: Permission
    resource_id: Optional[str] = None


class PermissionResponse(BaseModel):
    """Schema for permission check response"""
    
    allowed: bool
    reason: Optional[str] = None


class SecurityMetrics(BaseModel):
    """Schema for security metrics response"""
    
    total_users: int
    active_users: int
    locked_users: int
    suspended_users: int
    failed_login_attempts_24h: int
    successful_logins_24h: int
    active_sessions: int
    security_events_24h: int
    two_factor_adoption_rate: float


# Update forward references
TokenResponse.update_forward_refs()
UserResponse.update_forward_refs()