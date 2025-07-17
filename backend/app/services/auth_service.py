#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication Service for Military-Grade Security
IDF Testing Infrastructure
"""

import secrets
import qrcode
import io
import base64
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update
from sqlalchemy.orm import selectinload
import pyotp
import structlog
from fastapi import HTTPException, status

from ..core.security import (
    security_manager, jwt_manager, UserRole, Permission,
    get_password_hash, verify_password
)
from ..core.redis_client import SessionManager, redis_client
from ..core.audit import AuditLogger, AuditEventType, AuditContext, SecurityMonitor, SecurityEventSeverity, SecurityEventCategory
from ..core.encryption import token_encryption, secure_compare
from ..models.user import User, Role, LoginAttempt, UserSession, UserStatus, LoginAttemptStatus
from ..schemas.auth import (
    UserCreate, UserUpdate, LoginRequest, TokenResponse, UserResponse,
    PasswordChange, TwoFactorSetupResponse, TwoFactorVerifyRequest,
    EmailVerificationRequest, PasswordResetRequest, PasswordResetConfirm,
    SecuritySettings, SecurityMetrics
)

logger = structlog.get_logger()


class AuthenticationError(Exception):
    """Authentication specific error"""
    pass


class AuthorizationError(Exception):
    """Authorization specific error"""
    pass


class TwoFactorAuthService:
    """Two-factor authentication service"""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_qr_code(secret: str, user_email: str, issuer: str = "IDF Testing Infrastructure") -> str:
        """Generate QR code for TOTP setup"""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name=issuer
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> List[str]:
        """Generate backup codes for 2FA"""
        return [secrets.token_hex(4).upper() for _ in range(count)]
    
    @staticmethod
    def verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
        """Verify TOTP code with time window"""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)
    
    @staticmethod
    def verify_backup_code(backup_codes: List[str], code: str) -> Tuple[bool, List[str]]:
        """Verify backup code and remove it from the list"""
        code_upper = code.upper()
        if code_upper in backup_codes:
            updated_codes = [c for c in backup_codes if c != code_upper]
            return True, updated_codes
        return False, backup_codes


class AuthService:
    """Comprehensive authentication service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_logger = AuditLogger(db)
        self.security_monitor = SecurityMonitor(db)
        self.two_factor = TwoFactorAuthService()
    
    async def register_user(
        self,
        user_data: UserCreate,
        created_by: Optional[int] = None,
        context: Optional[AuditContext] = None
    ) -> User:
        """
        Register a new user with comprehensive validation
        """
        try:
            # Check if username already exists
            existing_user = await self.db.execute(
                select(User).where(
                    or_(User.username == user_data.username, User.email == user_data.email)
                )
            )
            if existing_user.scalar_one_or_none():
                raise AuthenticationError("Username or email already exists")
            
            # Validate password strength
            is_valid, errors = security_manager.validate_password_strength(user_data.password)
            if not is_valid:
                raise AuthenticationError(f"Password validation failed: {', '.join(errors)}")
            
            # Hash password
            password_hash = get_password_hash(user_data.password)
            
            # Create user
            user = User(
                username=user_data.username,
                email=user_data.email,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                phone=user_data.phone,
                department=user_data.department,
                rank=user_data.rank,
                personal_number=user_data.personal_number,
                password_hash=password_hash,
                created_by=str(created_by) if created_by else None
            )
            
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            
            # Assign default roles
            await self._assign_default_roles(user, user_data.roles or [UserRole.GUEST])
            
            # Log audit event
            if context:
                await self.audit_logger.log_audit_event(
                    event_type=AuditEventType.USER_CREATED,
                    context=context,
                    resource_type="user",
                    resource_id=user.id,
                    details={"username": user.username, "email": user.email}
                )
            
            logger.info("User registered successfully", user_id=user.id, username=user.username)
            return user
            
        except Exception as e:
            await self.db.rollback()
            logger.error("User registration failed", error=str(e))
            raise AuthenticationError(f"Registration failed: {str(e)}")
    
    async def authenticate_user(
        self,
        login_data: LoginRequest,
        context: AuditContext
    ) -> Tuple[User, Optional[str]]:
        """
        Authenticate user with comprehensive security checks
        """
        # Track login attempt
        login_attempt = LoginAttempt(
            username_attempted=login_data.username,
            ip_address=context.ip_address,
            user_agent=context.user_agent,
            status=LoginAttemptStatus.FAILED_USER_NOT_FOUND
        )
        
        try:
            # Check rate limiting for this IP
            rate_limit_key = f"login_attempts:{context.ip_address}"
            is_allowed, current_count, remaining = await redis_client.check_rate_limit(
                rate_limit_key, 5, 300  # 5 attempts per 5 minutes
            )
            
            if not is_allowed:
                await self.security_monitor.log_security_event(
                    event_type="rate_limit_exceeded",
                    severity=SecurityEventSeverity.MEDIUM,
                    category=SecurityEventCategory.AUTHENTICATION,
                    description=f"Login rate limit exceeded: {current_count} attempts",
                    context=context
                )
                raise AuthenticationError("Too many login attempts. Please try again later.")
            
            # Get user
            result = await self.db.execute(
                select(User).options(selectinload(User.roles))
                .where(User.username == login_data.username)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                login_attempt.status = LoginAttemptStatus.FAILED_USER_NOT_FOUND
                await self._save_login_attempt(login_attempt)
                
                await self.security_monitor.log_security_event(
                    event_type="login_failed_user_not_found",
                    severity=SecurityEventSeverity.LOW,
                    category=SecurityEventCategory.AUTHENTICATION,
                    description=f"Login attempt with non-existent username: {login_data.username}",
                    context=context
                )
                
                raise AuthenticationError("Invalid credentials")
            
            login_attempt.user_id = user.id
            
            # Check account status
            if not user.is_active:
                login_attempt.status = LoginAttemptStatus.FAILED_ACCOUNT_SUSPENDED
                await self._save_login_attempt(login_attempt)
                raise AuthenticationError("Account is inactive")
            
            if user.is_locked:
                login_attempt.status = LoginAttemptStatus.FAILED_ACCOUNT_LOCKED
                await self._save_login_attempt(login_attempt)
                raise AuthenticationError("Account is locked")
            
            # Verify password
            if not verify_password(login_data.password, user.password_hash):
                # Increment failed attempts
                user.failed_login_attempts += 1
                
                # Lock account after too many failures
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                    await self.security_monitor.log_security_event(
                        event_type="account_locked_multiple_failures",
                        severity=SecurityEventSeverity.HIGH,
                        category=SecurityEventCategory.AUTHENTICATION,
                        description=f"Account locked due to {user.failed_login_attempts} failed attempts",
                        context=context
                    )
                
                login_attempt.status = LoginAttemptStatus.FAILED_PASSWORD
                await self._save_login_attempt(login_attempt)
                await self.db.commit()
                
                await self.security_monitor.log_security_event(
                    event_type="login_failed_wrong_password",
                    severity=SecurityEventSeverity.MEDIUM,
                    category=SecurityEventCategory.AUTHENTICATION,
                    description=f"Failed login attempt for user {user.username}",
                    context=context
                )
                
                raise AuthenticationError("Invalid credentials")
            
            # Check 2FA if enabled
            session_id = None
            if user.two_factor_enabled:
                if not login_data.two_factor_code:
                    # Create temporary session for 2FA completion
                    session_id = await self._create_temp_2fa_session(user.id)
                    return user, session_id
                
                # Verify 2FA code
                if not self._verify_2fa_code(user, login_data.two_factor_code):
                    login_attempt.status = LoginAttemptStatus.FAILED_PASSWORD
                    login_attempt.failure_reason = "Invalid 2FA code"
                    await self._save_login_attempt(login_attempt)
                    
                    await self.security_monitor.log_security_event(
                        event_type="login_failed_invalid_2fa",
                        severity=SecurityEventSeverity.MEDIUM,
                        category=SecurityEventCategory.AUTHENTICATION,
                        description="Login failed due to invalid 2FA code",
                        context=context
                    )
                    
                    raise AuthenticationError("Invalid two-factor authentication code")
            
            # Successful login
            user.failed_login_attempts = 0
            user.last_login_at = datetime.utcnow()
            user.last_login_ip = context.ip_address
            
            login_attempt.status = LoginAttemptStatus.SUCCESS
            await self._save_login_attempt(login_attempt)
            
            await self.audit_logger.log_audit_event(
                event_type=AuditEventType.LOGIN_SUCCESS,
                context=context,
                resource_type="user",
                resource_id=user.id,
                details={"username": user.username}
            )
            
            await self.db.commit()
            
            logger.info("User authenticated successfully", user_id=user.id, username=user.username)
            return user, session_id
            
        except AuthenticationError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error("Authentication failed", error=str(e))
            raise AuthenticationError("Authentication failed")
    
    async def create_tokens(
        self,
        user: User,
        remember_me: bool = False,
        context: Optional[AuditContext] = None
    ) -> TokenResponse:
        """
        Create JWT tokens for authenticated user
        """
        try:
            # Create session
            session_id = await SessionManager.create_session(
                str(user.id),
                {
                    "username": user.username,
                    "ip_address": context.ip_address if context else None,
                    "user_agent": context.user_agent if context else None
                }
            )
            
            # Create user session record
            session_expires = datetime.utcnow() + timedelta(
                minutes=settings.security.SESSION_EXPIRE_MINUTES
            )
            
            user_session = UserSession(
                user_id=user.id,
                session_id=session_id,
                ip_address=context.ip_address if context else None,
                user_agent=context.user_agent if context else None,
                expires_at=session_expires
            )
            
            self.db.add(user_session)
            
            # Determine token expiration
            if remember_me:
                access_token_expires = timedelta(hours=24)
                refresh_token_expires = timedelta(days=30)
            else:
                access_token_expires = timedelta(minutes=settings.security.ACCESS_TOKEN_EXPIRE_MINUTES)
                refresh_token_expires = timedelta(minutes=settings.security.REFRESH_TOKEN_EXPIRE_MINUTES)
            
            # Create token data
            token_data = {
                "sub": str(user.id),
                "username": user.username,
                "role": user.primary_role.value,
                "session_id": session_id
            }
            
            # Create tokens
            access_token = await jwt_manager.create_access_token(
                data=token_data,
                expires_delta=access_token_expires
            )
            
            refresh_token = await jwt_manager.create_refresh_token(str(user.id))
            
            # Update user's current session
            user.current_session_id = session_id
            
            await self.db.commit()
            
            # Log session creation
            if context:
                await self.audit_logger.log_audit_event(
                    event_type=AuditEventType.SESSION_CREATED,
                    context=context,
                    resource_type="session",
                    resource_id=session_id,
                    details={"user_id": user.id, "remember_me": remember_me}
                )
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=int(access_token_expires.total_seconds()),
                user=UserResponse.from_orm(user)
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Token creation failed", error=str(e))
            raise AuthenticationError("Token creation failed")
    
    async def refresh_token(
        self,
        refresh_token: str,
        context: AuditContext
    ) -> TokenResponse:
        """
        Refresh access token using refresh token
        """
        try:
            # Verify refresh token
            token_payload = await jwt_manager.verify_token(refresh_token, "refresh")
            if not token_payload:
                raise AuthenticationError("Invalid refresh token")
            
            user_id = token_payload.get("sub")
            if not user_id:
                raise AuthenticationError("Invalid token payload")
            
            # Get user
            result = await self.db.execute(
                select(User).options(selectinload(User.roles))
                .where(User.id == int(user_id))
            )
            user = result.scalar_one_or_none()
            
            if not user or not user.is_active:
                raise AuthenticationError("User not found or inactive")
            
            # Blacklist old refresh token
            jti = token_payload.get("jti")
            if jti:
                await jwt_manager.blacklist_token(jti)
            
            # Create new tokens
            return await self.create_tokens(user, False, context)
            
        except Exception as e:
            logger.error("Token refresh failed", error=str(e))
            raise AuthenticationError("Token refresh failed")
    
    async def logout_user(
        self,
        user: User,
        session_id: Optional[str] = None,
        context: Optional[AuditContext] = None
    ):
        """
        Logout user and invalidate session
        """
        try:
            # Invalidate session
            if session_id:
                await SessionManager.delete_session(session_id)
                
                # Update user session record
                await self.db.execute(
                    update(UserSession)
                    .where(UserSession.session_id == session_id)
                    .values(is_active=False, logout_at=datetime.utcnow())
                )
            
            # Clear user's current session
            user.current_session_id = None
            
            await self.db.commit()
            
            # Log logout
            if context:
                await self.audit_logger.log_audit_event(
                    event_type=AuditEventType.LOGOUT,
                    context=context,
                    resource_type="session",
                    resource_id=session_id,
                    details={"user_id": user.id}
                )
            
            logger.info("User logged out successfully", user_id=user.id)
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Logout failed", error=str(e))
            raise
    
    async def change_password(
        self,
        user: User,
        password_data: PasswordChange,
        context: AuditContext
    ):
        """
        Change user password with validation
        """
        try:
            # Verify current password
            if not verify_password(password_data.current_password, user.password_hash):
                await self.security_monitor.log_security_event(
                    event_type="password_change_failed_wrong_current",
                    severity=SecurityEventSeverity.MEDIUM,
                    category=SecurityEventCategory.AUTHENTICATION,
                    description="Password change failed - wrong current password",
                    context=context
                )
                raise AuthenticationError("Current password is incorrect")
            
            # Validate new password strength
            is_valid, errors = security_manager.validate_password_strength(password_data.new_password)
            if not is_valid:
                raise AuthenticationError(f"New password validation failed: {', '.join(errors)}")
            
            # Hash new password
            new_password_hash = get_password_hash(password_data.new_password)
            
            # Update user
            user.password_hash = new_password_hash
            user.password_changed_at = datetime.utcnow()
            user.must_change_password = False
            
            await self.db.commit()
            
            # Log audit event
            await self.audit_logger.log_audit_event(
                event_type=AuditEventType.PASSWORD_CHANGE,
                context=context,
                resource_type="user",
                resource_id=user.id,
                details={"username": user.username}
            )
            
            logger.info("Password changed successfully", user_id=user.id)
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Password change failed", error=str(e))
            raise
    
    async def setup_two_factor(self, user: User) -> TwoFactorSetupResponse:
        """
        Setup two-factor authentication for user
        """
        try:
            # Generate secret and backup codes
            secret = self.two_factor.generate_secret()
            backup_codes = self.two_factor.generate_backup_codes()
            
            # Generate QR code
            qr_code_data = self.two_factor.generate_qr_code(secret, user.email)
            qr_code_url = f"data:image/png;base64,{qr_code_data}"
            
            # Store temporarily (user must verify before enabling)
            temp_2fa_data = {
                "secret": secret,
                "backup_codes": backup_codes,
                "user_id": user.id
            }
            
            temp_key = f"temp_2fa:{user.id}"
            await redis_client.set_secure(temp_key, temp_2fa_data, expire_seconds=600)  # 10 minutes
            
            return TwoFactorSetupResponse(
                secret=secret,
                qr_code_url=qr_code_url,
                backup_codes=backup_codes
            )
            
        except Exception as e:
            logger.error("2FA setup failed", error=str(e))
            raise AuthenticationError("Two-factor authentication setup failed")
    
    async def verify_and_enable_two_factor(
        self,
        user: User,
        verify_data: TwoFactorVerifyRequest,
        context: AuditContext
    ):
        """
        Verify 2FA setup and enable it
        """
        try:
            # Get temporary 2FA data
            temp_key = f"temp_2fa:{user.id}"
            temp_data = await redis_client.get_secure(temp_key)
            
            if not temp_data:
                raise AuthenticationError("2FA setup session expired")
            
            secret = temp_data["secret"]
            backup_codes = temp_data["backup_codes"]
            
            # Verify TOTP code
            if not self.two_factor.verify_totp_code(secret, verify_data.code):
                raise AuthenticationError("Invalid verification code")
            
            # Enable 2FA for user
            user.two_factor_enabled = True
            user.two_factor_secret = token_encryption.encrypt_token(secret, "2fa_secret")
            user.backup_codes = token_encryption.encrypt_token(
                json.dumps(backup_codes), "backup_codes"
            )
            
            await self.db.commit()
            
            # Clean up temporary data
            await redis_client.delete(temp_key)
            
            # Log audit event
            await self.audit_logger.log_audit_event(
                event_type=AuditEventType.TWO_FACTOR_ENABLED,
                context=context,
                resource_type="user",
                resource_id=user.id,
                details={"username": user.username}
            )
            
            logger.info("2FA enabled successfully", user_id=user.id)
            
        except Exception as e:
            await self.db.rollback()
            logger.error("2FA verification failed", error=str(e))
            raise
    
    async def disable_two_factor(
        self,
        user: User,
        password: str,
        context: AuditContext
    ):
        """
        Disable two-factor authentication
        """
        try:
            # Verify password
            if not verify_password(password, user.password_hash):
                raise AuthenticationError("Password verification failed")
            
            # Disable 2FA
            user.two_factor_enabled = False
            user.two_factor_secret = None
            user.backup_codes = None
            
            await self.db.commit()
            
            # Log audit event
            await self.audit_logger.log_audit_event(
                event_type=AuditEventType.TWO_FACTOR_DISABLED,
                context=context,
                resource_type="user",
                resource_id=user.id,
                details={"username": user.username}
            )
            
            logger.info("2FA disabled successfully", user_id=user.id)
            
        except Exception as e:
            await self.db.rollback()
            logger.error("2FA disable failed", error=str(e))
            raise
    
    async def get_security_metrics(self) -> SecurityMetrics:
        """
        Get security metrics for dashboard
        """
        try:
            # Get user counts
            total_users_result = await self.db.execute(select(func.count(User.id)))
            total_users = total_users_result.scalar() or 0
            
            active_users_result = await self.db.execute(
                select(func.count(User.id)).where(User.is_active == True)
            )
            active_users = active_users_result.scalar() or 0
            
            locked_users_result = await self.db.execute(
                select(func.count(User.id)).where(User.locked_until > datetime.utcnow())
            )
            locked_users = locked_users_result.scalar() or 0
            
            suspended_users_result = await self.db.execute(
                select(func.count(User.id)).where(User.status == UserStatus.SUSPENDED)
            )
            suspended_users = suspended_users_result.scalar() or 0
            
            # Get 24h login metrics
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            failed_logins_result = await self.db.execute(
                select(func.count(LoginAttempt.id))
                .where(and_(
                    LoginAttempt.created_at >= yesterday,
                    LoginAttempt.status != LoginAttemptStatus.SUCCESS
                ))
            )
            failed_login_attempts_24h = failed_logins_result.scalar() or 0
            
            successful_logins_result = await self.db.execute(
                select(func.count(LoginAttempt.id))
                .where(and_(
                    LoginAttempt.created_at >= yesterday,
                    LoginAttempt.status == LoginAttemptStatus.SUCCESS
                ))
            )
            successful_logins_24h = successful_logins_result.scalar() or 0
            
            # Get active sessions
            active_sessions_result = await self.db.execute(
                select(func.count(UserSession.id))
                .where(and_(
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.utcnow()
                ))
            )
            active_sessions = active_sessions_result.scalar() or 0
            
            # Get 2FA adoption rate
            total_active_users = max(active_users, 1)  # Avoid division by zero
            users_with_2fa_result = await self.db.execute(
                select(func.count(User.id))
                .where(and_(User.is_active == True, User.two_factor_enabled == True))
            )
            users_with_2fa = users_with_2fa_result.scalar() or 0
            two_factor_adoption_rate = (users_with_2fa / total_active_users) * 100
            
            return SecurityMetrics(
                total_users=total_users,
                active_users=active_users,
                locked_users=locked_users,
                suspended_users=suspended_users,
                failed_login_attempts_24h=failed_login_attempts_24h,
                successful_logins_24h=successful_logins_24h,
                active_sessions=active_sessions,
                security_events_24h=0,  # Would need SecurityEvent model
                two_factor_adoption_rate=round(two_factor_adoption_rate, 2)
            )
            
        except Exception as e:
            logger.error("Failed to get security metrics", error=str(e))
            return SecurityMetrics(
                total_users=0, active_users=0, locked_users=0, suspended_users=0,
                failed_login_attempts_24h=0, successful_logins_24h=0,
                active_sessions=0, security_events_24h=0, two_factor_adoption_rate=0.0
            )
    
    # Helper methods
    
    async def _assign_default_roles(self, user: User, roles: List[UserRole]):
        """Assign default roles to user"""
        for role_name in roles:
            role_result = await self.db.execute(
                select(Role).where(Role.name == role_name.value)
            )
            role = role_result.scalar_one_or_none()
            if role:
                user.roles.append(role)
    
    async def _save_login_attempt(self, login_attempt: LoginAttempt):
        """Save login attempt to database"""
        self.db.add(login_attempt)
        try:
            await self.db.commit()
        except:
            await self.db.rollback()
    
    async def _create_temp_2fa_session(self, user_id: int) -> str:
        """Create temporary session for 2FA completion"""
        session_id = secrets.token_urlsafe(32)
        session_data = {
            "user_id": str(user_id),
            "temp_2fa": True,
            "created_at": datetime.utcnow().isoformat()
        }
        
        await redis_client.set_secure(
            f"temp_2fa_session:{session_id}",
            session_data,
            expire_seconds=300  # 5 minutes
        )
        
        return session_id
    
    def _verify_2fa_code(self, user: User, code: str) -> bool:
        """Verify 2FA code (TOTP or backup)"""
        try:
            # Decrypt secret
            secret = token_encryption.decrypt_token(user.two_factor_secret, "2fa_secret")
            
            # Try TOTP first
            if self.two_factor.verify_totp_code(secret, code):
                return True
            
            # Try backup codes
            if user.backup_codes:
                backup_codes_json = token_encryption.decrypt_token(user.backup_codes, "backup_codes")
                backup_codes = json.loads(backup_codes_json)
                
                is_valid, updated_codes = self.two_factor.verify_backup_code(backup_codes, code)
                if is_valid:
                    # Update backup codes (remove used one)
                    user.backup_codes = token_encryption.encrypt_token(
                        json.dumps(updated_codes), "backup_codes"
                    )
                    return True
            
            return False
            
        except Exception as e:
            logger.error("2FA verification failed", error=str(e))
            return False