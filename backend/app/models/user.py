#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User Authentication Models for Military-Grade Security
IDF Testing Infrastructure
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Table, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .base import BaseModel
from ..core.security import UserRole


class UserStatus(str, enum.Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    PENDING_VERIFICATION = "pending_verification"


class LoginAttemptStatus(str, enum.Enum):
    """Login attempt status"""
    SUCCESS = "success"
    FAILED_PASSWORD = "failed_password"
    FAILED_USER_NOT_FOUND = "failed_user_not_found"
    FAILED_ACCOUNT_LOCKED = "failed_account_locked"
    FAILED_ACCOUNT_SUSPENDED = "failed_account_suspended"
    FAILED_TOO_MANY_ATTEMPTS = "failed_too_many_attempts"


# Association table for user roles (many-to-many)
user_roles = Table(
    'user_roles',
    BaseModel.metadata,
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('role.id'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), server_default=func.now()),
    Column('assigned_by', String(100)),
    Column('expires_at', DateTime(timezone=True), nullable=True),
)


class User(BaseModel):
    """User model with military-grade security features"""
    
    __tablename__ = "user"
    
    # Basic user information
    username = Column(
        String(50), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="Unique username for login"
    )
    
    email = Column(
        String(255), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="User email address"
    )
    
    first_name = Column(
        String(100), 
        nullable=False,
        comment="User first name (Hebrew supported)"
    )
    
    last_name = Column(
        String(100), 
        nullable=False,
        comment="User last name (Hebrew supported)"
    )
    
    # Security fields
    password_hash = Column(
        String(255), 
        nullable=False,
        comment="Bcrypt password hash"
    )
    
    is_active = Column(
        Boolean, 
        default=True, 
        nullable=False,
        comment="Account active status"
    )
    
    status = Column(
        SQLEnum(UserStatus),
        default=UserStatus.ACTIVE,
        nullable=False,
        comment="Detailed account status"
    )
    
    # Authentication tracking
    last_login_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful login timestamp"
    )
    
    last_login_ip = Column(
        String(45),  # IPv6 compatible
        nullable=True,
        comment="Last login IP address"
    )
    
    failed_login_attempts = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Consecutive failed login attempts"
    )
    
    locked_until = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Account locked until this timestamp"
    )
    
    # Password management
    password_changed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Last password change timestamp"
    )
    
    must_change_password = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Force password change on next login"
    )
    
    # Two-factor authentication
    two_factor_enabled = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Two-factor authentication enabled"
    )
    
    two_factor_secret = Column(
        String(32),
        nullable=True,
        comment="TOTP secret for 2FA"
    )
    
    backup_codes = Column(
        Text,
        nullable=True,
        comment="JSON array of backup codes for 2FA"
    )
    
    # Profile information
    phone = Column(
        String(20),
        nullable=True,
        comment="Phone number"
    )
    
    department = Column(
        String(100),
        nullable=True,
        comment="User department (Hebrew supported)"
    )
    
    rank = Column(
        String(50),
        nullable=True,
        comment="Military rank (Hebrew supported)"
    )
    
    personal_number = Column(
        String(20),
        nullable=True,
        unique=True,
        comment="Personal/Service number"
    )
    
    # Session management
    current_session_id = Column(
        String(255),
        nullable=True,
        comment="Current active session ID"
    )
    
    max_concurrent_sessions = Column(
        Integer,
        default=1,
        nullable=False,
        comment="Maximum allowed concurrent sessions"
    )
    
    # Email verification
    email_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Email address verified"
    )
    
    email_verification_token = Column(
        String(255),
        nullable=True,
        comment="Email verification token"
    )
    
    email_verification_expires = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Email verification token expiration"
    )
    
    # Password reset
    password_reset_token = Column(
        String(255),
        nullable=True,
        comment="Password reset token"
    )
    
    password_reset_expires = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Password reset token expiration"
    )
    
    # Relationships
    roles = relationship(
        "Role",
        secondary=user_roles,
        back_populates="users",
        lazy="selectin"
    )
    
    login_attempts = relationship(
        "LoginAttempt",
        back_populates="user",
        order_by="LoginAttempt.created_at.desc()"
    )
    
    sessions = relationship(
        "UserSession",
        back_populates="user",
        order_by="UserSession.created_at.desc()"
    )
    
    # Properties
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked"""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    @property
    def primary_role(self) -> Optional[UserRole]:
        """Get user's primary role"""
        if not self.roles:
            return UserRole.GUEST
        
        # Return highest privilege role
        role_hierarchy = [
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.OFFICER,
            UserRole.ANALYST,
            UserRole.VIEWER,
            UserRole.GUEST
        ]
        
        user_role_names = [role.name for role in self.roles]
        for role in role_hierarchy:
            if role.value in user_role_names:
                return role
        
        return UserRole.GUEST
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has specific role"""
        return any(user_role.name == role.value for user_role in self.roles)
    
    def has_any_role(self, roles: List[UserRole]) -> bool:
        """Check if user has any of the specified roles"""
        return any(self.has_role(role) for role in roles)


class Role(BaseModel):
    """Role model for RBAC"""
    
    __tablename__ = "role"
    
    name = Column(
        String(50),
        unique=True,
        nullable=False,
        comment="Role name (matches UserRole enum)"
    )
    
    display_name = Column(
        String(100),
        nullable=False,
        comment="Human-readable role name (Hebrew supported)"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Role description (Hebrew supported)"
    )
    
    is_system_role = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="System role (cannot be deleted)"
    )
    
    # Relationships
    users = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles"
    )


class LoginAttempt(BaseModel):
    """Login attempt tracking for security monitoring"""
    
    __tablename__ = "login_attempt"
    
    user_id = Column(
        Integer,
        ForeignKey('user.id', ondelete='CASCADE'),
        nullable=True,  # Nullable for failed attempts with non-existent users
        comment="User ID (if user exists)"
    )
    
    username_attempted = Column(
        String(50),
        nullable=False,
        comment="Username attempted (for tracking failed attempts)"
    )
    
    ip_address = Column(
        String(45),  # IPv6 compatible
        nullable=False,
        index=True,
        comment="IP address of attempt"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        comment="User agent string"
    )
    
    status = Column(
        SQLEnum(LoginAttemptStatus),
        nullable=False,
        comment="Attempt status"
    )
    
    failure_reason = Column(
        String(255),
        nullable=True,
        comment="Detailed failure reason"
    )
    
    geolocation = Column(
        Text,  # JSON
        nullable=True,
        comment="Geolocation data (JSON)"
    )
    
    session_id = Column(
        String(255),
        nullable=True,
        comment="Session ID if login succeeded"
    )
    
    # Relationships
    user = relationship("User", back_populates="login_attempts")


class UserSession(BaseModel):
    """User session tracking"""
    
    __tablename__ = "user_session"
    
    user_id = Column(
        Integer,
        ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
        comment="User ID"
    )
    
    session_id = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Session identifier"
    )
    
    ip_address = Column(
        String(45),
        nullable=False,
        comment="IP address"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        comment="User agent string"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Session active status"
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Session expiration"
    )
    
    last_activity = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last activity timestamp"
    )
    
    logout_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Logout timestamp"
    )
    
    # Relationships
    user = relationship("User", back_populates="sessions")


class AuditLog(BaseModel):
    """Comprehensive audit logging"""
    
    __tablename__ = "audit_log"
    
    user_id = Column(
        Integer,
        ForeignKey('user.id', ondelete='SET NULL'),
        nullable=True,
        comment="User who performed the action"
    )
    
    action = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Action performed"
    )
    
    resource_type = Column(
        String(50),
        nullable=True,
        comment="Type of resource affected"
    )
    
    resource_id = Column(
        String(50),
        nullable=True,
        comment="ID of resource affected"
    )
    
    ip_address = Column(
        String(45),
        nullable=True,
        comment="IP address of the action"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        comment="User agent string"
    )
    
    details = Column(
        Text,  # JSON
        nullable=True,
        comment="Additional action details (JSON)"
    )
    
    success = Column(
        Boolean,
        nullable=False,
        comment="Whether the action succeeded"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if action failed"
    )
    
    session_id = Column(
        String(255),
        nullable=True,
        comment="Session ID"
    )
    
    # Relationships
    user = relationship("User")


class SecurityEvent(BaseModel):
    """Security event tracking"""
    
    __tablename__ = "security_event"
    
    event_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of security event"
    )
    
    severity = Column(
        String(20),
        nullable=False,
        comment="Event severity (low, medium, high, critical)"
    )
    
    user_id = Column(
        Integer,
        ForeignKey('user.id', ondelete='SET NULL'),
        nullable=True,
        comment="Associated user (if any)"
    )
    
    ip_address = Column(
        String(45),
        nullable=True,
        comment="IP address"
    )
    
    description = Column(
        Text,
        nullable=False,
        comment="Event description"
    )
    
    metadata = Column(
        Text,  # JSON
        nullable=True,
        comment="Additional event metadata (JSON)"
    )
    
    resolved = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the event has been resolved"
    )
    
    resolved_by = Column(
        Integer,
        ForeignKey('user.id', ondelete='SET NULL'),
        nullable=True,
        comment="User who resolved the event"
    )
    
    resolved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Resolution timestamp"
    )
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])