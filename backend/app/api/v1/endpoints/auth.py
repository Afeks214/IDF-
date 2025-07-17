#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication API Endpoints
Military-Grade Security for IDF Testing Infrastructure
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ....core.database import get_db
from ....core.auth_dependencies import (
    get_current_user, get_current_active_user, require_admin,
    require_permission, Permission, AuditContext, audit_action
)
from ....core.validation import form_validator, COMMON_RULES
from ....services.auth_service import AuthService
from ....schemas.auth import (
    LoginRequest, TokenResponse, UserCreate, UserResponse, UserUpdate,
    PasswordChange, RefreshTokenRequest, TwoFactorSetupResponse,
    TwoFactorVerifyRequest, SecurityMetrics, SecuritySettings
)
from ....models.user import User

logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer()


def get_audit_context(request: Request) -> AuditContext:
    """Extract audit context from request"""
    return AuditContext(
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
        request_id=getattr(request.state, 'request_id', None)
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Register a new user (Admin only)
    """
    try:
        # Validate input data
        validated_data = form_validator.validate_and_sanitize(
            user_data.dict(),
            {
                "username": COMMON_RULES["username"],
                "email": COMMON_RULES["email"],
                "password": COMMON_RULES["password"],
                "first_name": COMMON_RULES["hebrew_name"],
                "last_name": COMMON_RULES["hebrew_name"],
                "phone": COMMON_RULES["phone"],
            }
        )
        
        auth_service = AuthService(db)
        context = get_audit_context(request)
        context.user_id = current_user.id
        
        # Create user
        user = await auth_service.register_user(
            UserCreate(**validated_data),
            created_by=current_user.id,
            context=context
        )
        
        # Audit the action
        await audit_action(
            action="user_registration",
            user=current_user,
            resource_type="user",
            resource_id=user.id,
            details={"registered_username": user.username},
            db=db
        )
        
        return UserResponse.from_orm(user)
        
    except Exception as e:
        logger.error("User registration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    User login with JWT token generation
    """
    try:
        # Validate input
        validated_data = form_validator.validate_and_sanitize(
            login_data.dict(),
            {
                "username": COMMON_RULES["username"],
                "password": {"type": "string", "required": True, "max_length": 128},
                "two_factor_code": {
                    "type": "string",
                    "required": False,
                    "min_length": 6,
                    "max_length": 6,
                    "pattern": r"^\d{6}$"
                }
            }
        )
        
        auth_service = AuthService(db)
        context = get_audit_context(request)
        
        # Authenticate user
        user, temp_session_id = await auth_service.authenticate_user(
            LoginRequest(**validated_data),
            context
        )
        
        # If 2FA required but not provided, return partial response
        if temp_session_id and not login_data.two_factor_code:
            response.headers["X-2FA-Required"] = "true"
            response.headers["X-Temp-Session"] = temp_session_id
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Two-factor authentication required",
                headers={"X-2FA-Required": "true"}
            )
        
        # Create tokens
        token_response = await auth_service.create_tokens(
            user,
            remember_me=login_data.remember_me,
            context=context
        )
        
        # Set secure cookies if in production
        if settings.ENVIRONMENT == "production":
            response.set_cookie(
                key="session_token",
                value=token_response.access_token,
                httponly=True,
                secure=True,
                samesite="strict",
                max_age=token_response.expires_in
            )
        
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        auth_service = AuthService(db)
        context = get_audit_context(request)
        
        token_response = await auth_service.refresh_token(
            refresh_data.refresh_token,
            context
        )
        
        return token_response
        
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    User logout
    """
    try:
        auth_service = AuthService(db)
        context = get_audit_context(request)
        context.user_id = current_user.id
        
        # Extract session ID from token if available
        session_id = getattr(request.state, 'session_id', None)
        
        await auth_service.logout_user(current_user, session_id, context)
        
        # Clear cookies
        response.delete_cookie(key="session_token")
        
        return {"message": "Logout successful"}
        
    except Exception as e:
        logger.error("Logout failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user password
    """
    try:
        # Validate password data
        validated_data = form_validator.validate_and_sanitize(
            password_data.dict(),
            {
                "current_password": {"type": "string", "required": True, "max_length": 128},
                "new_password": COMMON_RULES["password"],
                "confirm_password": {"type": "string", "required": True, "max_length": 128}
            }
        )
        
        auth_service = AuthService(db)
        context = get_audit_context(request)
        context.user_id = current_user.id
        
        await auth_service.change_password(
            current_user,
            PasswordChange(**validated_data),
            context
        )
        
        # Audit the action
        await audit_action(
            action="password_change",
            user=current_user,
            resource_type="user",
            resource_id=current_user.id,
            db=db
        )
        
        return {"message": "Password changed successfully"}
        
    except Exception as e:
        logger.error("Password change failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user profile
    """
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user profile
    """
    try:
        # Validate update data
        update_data = user_update.dict(exclude_unset=True)
        if update_data:
            validation_rules = {}
            if "email" in update_data:
                validation_rules["email"] = COMMON_RULES["email"]
            if "first_name" in update_data:
                validation_rules["first_name"] = COMMON_RULES["hebrew_name"]
            if "last_name" in update_data:
                validation_rules["last_name"] = COMMON_RULES["hebrew_name"]
            if "phone" in update_data:
                validation_rules["phone"] = COMMON_RULES["phone"]
            
            if validation_rules:
                validated_data = form_validator.validate_and_sanitize(
                    update_data, validation_rules
                )
                
                # Update user fields
                for field, value in validated_data.items():
                    setattr(current_user, field, value)
        
        current_user.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(current_user)
        
        # Audit the action
        await audit_action(
            action="profile_update",
            user=current_user,
            resource_type="user",
            resource_id=current_user.id,
            details={"updated_fields": list(update_data.keys())},
            db=db
        )
        
        return UserResponse.from_orm(current_user)
        
    except Exception as e:
        await db.rollback()
        logger.error("Profile update failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_two_factor_auth(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Setup two-factor authentication
    """
    try:
        if current_user.two_factor_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Two-factor authentication is already enabled"
            )
        
        auth_service = AuthService(db)
        setup_response = await auth_service.setup_two_factor(current_user)
        
        return setup_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("2FA setup failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Two-factor authentication setup failed"
        )


@router.post("/2fa/verify")
async def verify_two_factor_auth(
    verify_data: TwoFactorVerifyRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify and enable two-factor authentication
    """
    try:
        auth_service = AuthService(db)
        context = get_audit_context(request)
        context.user_id = current_user.id
        
        await auth_service.verify_and_enable_two_factor(
            current_user,
            verify_data,
            context
        )
        
        # Audit the action
        await audit_action(
            action="2fa_enabled",
            user=current_user,
            resource_type="user",
            resource_id=current_user.id,
            db=db
        )
        
        return {"message": "Two-factor authentication enabled successfully"}
        
    except Exception as e:
        logger.error("2FA verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/2fa/disable")
async def disable_two_factor_auth(
    password: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Disable two-factor authentication
    """
    try:
        if not current_user.two_factor_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Two-factor authentication is not enabled"
            )
        
        auth_service = AuthService(db)
        context = get_audit_context(request)
        context.user_id = current_user.id
        
        await auth_service.disable_two_factor(current_user, password, context)
        
        # Audit the action
        await audit_action(
            action="2fa_disabled",
            user=current_user,
            resource_type="user",
            resource_id=current_user.id,
            db=db
        )
        
        return {"message": "Two-factor authentication disabled successfully"}
        
    except Exception as e:
        logger.error("2FA disable failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/security/metrics", response_model=SecurityMetrics)
async def get_security_metrics(
    current_user: User = Depends(require_permission(Permission.SYSTEM_MONITOR)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get security metrics (Admin/Monitor only)
    """
    try:
        auth_service = AuthService(db)
        metrics = await auth_service.get_security_metrics()
        
        return metrics
        
    except Exception as e:
        logger.error("Failed to get security metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve security metrics"
        )


@router.get("/security/settings", response_model=SecuritySettings)
async def get_security_settings(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get user security settings
    """
    return SecuritySettings(
        two_factor_enabled=current_user.two_factor_enabled,
        max_concurrent_sessions=current_user.max_concurrent_sessions,
        email_notifications=True,  # Default - could be stored in user preferences
        login_notifications=True   # Default - could be stored in user preferences
    )


@router.put("/security/settings")
async def update_security_settings(
    settings_data: SecuritySettings,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user security settings
    """
    try:
        # Update allowed settings
        current_user.max_concurrent_sessions = settings_data.max_concurrent_sessions
        
        await db.commit()
        
        # Audit the action
        await audit_action(
            action="security_settings_update",
            user=current_user,
            resource_type="user",
            resource_id=current_user.id,
            details={"max_concurrent_sessions": settings_data.max_concurrent_sessions},
            db=db
        )
        
        return {"message": "Security settings updated successfully"}
        
    except Exception as e:
        await db.rollback()
        logger.error("Security settings update failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/health")
async def auth_health_check():
    """
    Authentication service health check
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }