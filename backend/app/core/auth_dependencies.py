#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication Dependencies for Military-Grade Security
IDF Testing Infrastructure - RBAC Implementation
"""

from datetime import datetime
from typing import Optional, List, Callable
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from .database import get_db
from .security import jwt_manager, UserRole, Permission, check_permissions, check_multiple_permissions
from .redis_client import redis_client, SessionManager
from ..models.user import User, AuditLog
from ..schemas.auth import UserResponse, PermissionResponse

logger = structlog.get_logger()

# Security scheme
security_scheme = HTTPBearer(auto_error=False)


class AuthenticationError(HTTPException):
    """Custom authentication error"""
    
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Custom authorization error"""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def get_current_user_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[dict]:
    """
    Extract and verify JWT token from request
    Returns token payload if valid, None if no token provided
    """
    if not credentials:
        return None
    
    token_payload = await jwt_manager.verify_token(credentials.credentials)
    if not token_payload:
        raise AuthenticationError("Invalid or expired token")
    
    return token_payload


async def get_current_user(
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    """
    if not token_payload:
        raise AuthenticationError("Authentication required")
    
    user_id = token_payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token payload")
    
    # Get user from database
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise AuthenticationError("User not found")
    
    if not user.is_active:
        raise AuthenticationError("Account is inactive")
    
    if user.is_locked:
        raise AuthenticationError("Account is locked")
    
    # Verify session is still active
    session_id = token_payload.get("session_id")
    if session_id:
        session_data = await SessionManager.get_session(session_id)
        if not session_data or session_data.get("user_id") != str(user.id):
            raise AuthenticationError("Session expired or invalid")
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (additional check for active status)
    """
    if not current_user.is_active:
        raise AuthenticationError("Account is inactive")
    
    return current_user


def require_role(required_role: UserRole) -> Callable:
    """
    Dependency to require specific role
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if not current_user.has_role(required_role):
            logger.warning(
                "Access denied - insufficient role",
                user_id=current_user.id,
                required_role=required_role.value,
                user_roles=[role.name for role in current_user.roles]
            )
            raise AuthorizationError(f"Role '{required_role.value}' required")
        
        return current_user
    
    return role_checker


def require_any_role(required_roles: List[UserRole]) -> Callable:
    """
    Dependency to require any of the specified roles
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if not current_user.has_any_role(required_roles):
            logger.warning(
                "Access denied - insufficient roles",
                user_id=current_user.id,
                required_roles=[role.value for role in required_roles],
                user_roles=[role.name for role in current_user.roles]
            )
            required_roles_str = ", ".join([role.value for role in required_roles])
            raise AuthorizationError(f"One of these roles required: {required_roles_str}")
        
        return current_user
    
    return role_checker


def require_permission(required_permission: Permission) -> Callable:
    """
    Dependency to require specific permission
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if not check_permissions(current_user.primary_role, required_permission):
            logger.warning(
                "Access denied - insufficient permissions",
                user_id=current_user.id,
                required_permission=required_permission.value,
                user_role=current_user.primary_role.value
            )
            raise AuthorizationError(f"Permission '{required_permission.value}' required")
        
        return current_user
    
    return permission_checker


def require_permissions(required_permissions: List[Permission]) -> Callable:
    """
    Dependency to require multiple permissions
    """
    async def permissions_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if not check_multiple_permissions(current_user.primary_role, required_permissions):
            logger.warning(
                "Access denied - insufficient permissions",
                user_id=current_user.id,
                required_permissions=[perm.value for perm in required_permissions],
                user_role=current_user.primary_role.value
            )
            permissions_str = ", ".join([perm.value for perm in required_permissions])
            raise AuthorizationError(f"These permissions required: {permissions_str}")
        
        return current_user
    
    return permissions_checker


def optional_auth() -> Callable:
    """
    Optional authentication - returns user if authenticated, None otherwise
    """
    async def optional_auth_checker(
        credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
        db: AsyncSession = Depends(get_db)
    ) -> Optional[User]:
        if not credentials:
            return None
        
        try:
            token_payload = await jwt_manager.verify_token(credentials.credentials)
            if not token_payload:
                return None
            
            user_id = token_payload.get("sub")
            if not user_id:
                return None
            
            from sqlalchemy import select
            result = await db.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()
            
            if user and user.is_active and not user.is_locked:
                return user
                
        except Exception as e:
            logger.warning("Optional auth failed", error=str(e))
        
        return None
    
    return optional_auth_checker


async def audit_action(
    action: str,
    user: User,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Create audit log entry
    """
    try:
        audit_entry = AuditLog(
            user_id=user.id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            success=success,
            error_message=error_message,
            session_id=session_id
        )
        
        db.add(audit_entry)
        await db.commit()
        
        logger.info(
            "Action audited",
            user_id=user.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success
        )
        
    except Exception as e:
        logger.error("Failed to create audit log", error=str(e))
        # Don't fail the request if audit logging fails
        pass


class RBACChecker:
    """
    Role-Based Access Control checker with advanced features
    """
    
    @staticmethod
    async def check_user_permission(
        user: User,
        permission: Permission,
        resource_id: Optional[str] = None
    ) -> PermissionResponse:
        """
        Check if user has specific permission with optional resource context
        """
        # Check basic permission
        has_permission = check_permissions(user.primary_role, permission)
        
        if not has_permission:
            return PermissionResponse(
                allowed=False,
                reason=f"Role '{user.primary_role.value}' does not have permission '{permission.value}'"
            )
        
        # Additional resource-level checks can be added here
        # For example, checking ownership of specific resources
        
        return PermissionResponse(allowed=True)
    
    @staticmethod
    async def check_resource_access(
        user: User,
        resource_type: str,
        resource_id: str,
        action: str,
        db: AsyncSession
    ) -> bool:
        """
        Check if user can access specific resource
        This can be extended for more granular resource-level permissions
        """
        # Basic implementation - can be extended for specific resource types
        
        # Example: Users can only access their own profile
        if resource_type == "user" and action in ["read", "update"]:
            return str(user.id) == resource_id or user.has_role(UserRole.ADMIN)
        
        # Example: Only admins can delete users
        if resource_type == "user" and action == "delete":
            return user.has_role(UserRole.ADMIN)
        
        # Default: use role-based permissions
        permission_map = {
            "read": Permission.DATA_READ,
            "write": Permission.DATA_WRITE,
            "delete": Permission.DATA_DELETE,
            "export": Permission.DATA_EXPORT,
        }
        
        required_permission = permission_map.get(action)
        if required_permission:
            return check_permissions(user.primary_role, required_permission)
        
        return False


# Shorthand dependencies for common roles
require_super_admin = require_role(UserRole.SUPER_ADMIN)
require_admin = require_role(UserRole.ADMIN)
require_officer = require_role(UserRole.OFFICER)
require_analyst = require_role(UserRole.ANALYST)
require_viewer = require_role(UserRole.VIEWER)

# Common role combinations
require_admin_or_officer = require_any_role([UserRole.ADMIN, UserRole.OFFICER])
require_staff = require_any_role([UserRole.ADMIN, UserRole.OFFICER, UserRole.ANALYST])

# Common permissions
require_data_read = require_permission(Permission.DATA_READ)
require_data_write = require_permission(Permission.DATA_WRITE)
require_data_delete = require_permission(Permission.DATA_DELETE)
require_user_management = require_permission(Permission.USER_WRITE)
require_system_config = require_permission(Permission.SYSTEM_CONFIG)

# Global RBAC checker instance
rbac = RBACChecker()