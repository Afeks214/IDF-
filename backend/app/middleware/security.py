#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Military-Grade Security Middleware for FastAPI
IDF Testing Infrastructure
"""

import time
import json
import ipaddress
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
import user_agents

from ..core.config import settings
from ..core.redis_client import redis_client
from ..models.user import SecurityEvent

logger = structlog.get_logger()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add comprehensive security headers
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        if settings.security.SECURITY_HEADERS_ENABLED:
            # Strict Transport Security
            response.headers["Strict-Transport-Security"] = f"max-age={settings.security.HSTS_MAX_AGE}; includeSubDomains; preload"
            
            # Content Security Policy
            response.headers["Content-Security-Policy"] = settings.security.CONTENT_SECURITY_POLICY
            
            # X-Frame-Options
            response.headers["X-Frame-Options"] = "DENY"
            
            # X-Content-Type-Options
            response.headers["X-Content-Type-Options"] = "nosniff"
            
            # X-XSS-Protection
            response.headers["X-XSS-Protection"] = "1; mode=block"
            
            # Referrer Policy
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            
            # Permissions Policy
            response.headers["Permissions-Policy"] = (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=(), "
                "accelerometer=(), ambient-light-sensor=()"
            )
            
            # Remove server header
            response.headers.pop("server", None)
            
            # Add custom security headers
            response.headers["X-Security-Framework"] = "IDF-Military-Grade"
            response.headers["X-Request-ID"] = request.state.request_id if hasattr(request.state, 'request_id') else "unknown"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Advanced rate limiting middleware with IP-based and user-based limits
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limits = {
            "global": (settings.security.RATE_LIMIT_PER_MINUTE, 60),
            "auth": (settings.security.AUTH_RATE_LIMIT_PER_MINUTE, 60),
            "hourly": (settings.security.RATE_LIMIT_PER_HOUR, 3600),
            "daily": (settings.security.RATE_LIMIT_PER_DAY, 86400),
        }
    
    async def dispatch(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)
        
        # Check if IP is in blocked ranges
        if await self._is_ip_blocked(client_ip):
            logger.warning("Blocked IP attempted access", ip=client_ip)
            await self._log_security_event(
                "blocked_ip_access",
                "medium",
                client_ip,
                f"Blocked IP {client_ip} attempted access"
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access denied"}
            )
        
        # Determine rate limit type based on endpoint
        limit_type = "auth" if self._is_auth_endpoint(request.url.path) else "global"
        
        # Check rate limits
        for period_name, (limit, window) in self.rate_limits.items():
            if period_name == "global" and limit_type != "global":
                continue
            if period_name == "auth" and limit_type != "auth":
                continue
                
            is_allowed, current_count, remaining = await redis_client.check_rate_limit(
                f"{client_ip}:{period_name}",
                limit,
                window
            )
            
            if not is_allowed:
                logger.warning(
                    "Rate limit exceeded",
                    ip=client_ip,
                    limit_type=period_name,
                    current_count=current_count,
                    limit=limit
                )
                
                await self._log_security_event(
                    "rate_limit_exceeded",
                    "medium",
                    client_ip,
                    f"Rate limit exceeded: {current_count}/{limit} in {window}s"
                )
                
                # Add rate limit headers
                headers = {
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(int(time.time() + window)),
                    "Retry-After": str(window)
                }
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Rate limit exceeded",
                        "retry_after": window
                    },
                    headers=headers
                )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to successful responses
        response.headers["X-RateLimit-Limit"] = str(self.rate_limits[limit_type][0])
        response.headers["X-RateLimit-Window"] = str(self.rate_limits[limit_type][1])
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address with proxy support"""
        # Check X-Forwarded-For header (from load balancer/proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            ip = forwarded_for.split(",")[0].strip()
            return ip
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to request client
        return request.client.host if request.client else "unknown"
    
    def _is_auth_endpoint(self, path: str) -> bool:
        """Check if endpoint is authentication-related"""
        auth_paths = ["/auth/login", "/auth/register", "/auth/refresh", "/auth/reset-password"]
        return any(path.startswith(auth_path) for auth_path in auth_paths)
    
    async def _is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is in blocked ranges"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            # Check against blocked ranges
            for blocked_range in settings.security.BLOCKED_IP_RANGES:
                if ip_obj in ipaddress.ip_network(blocked_range, strict=False):
                    return True
            
            # Check Redis blocklist
            is_blocked = await redis_client.get_secure(f"blocked_ip:{ip}")
            return is_blocked is not None
            
        except ValueError:
            # Invalid IP format - block it
            return True
        
        return False
    
    async def _log_security_event(
        self,
        event_type: str,
        severity: str,
        ip_address: str,
        description: str,
        metadata: Optional[dict] = None
    ):
        """Log security event to Redis for later processing"""
        event_data = {
            "event_type": event_type,
            "severity": severity,
            "ip_address": ip_address,
            "description": description,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await redis_client.set_secure(
            f"security_event:{datetime.utcnow().timestamp()}",
            event_data,
            expire_seconds=86400  # Keep for 24 hours
        )


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking requests and detecting suspicious activity
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.suspicious_patterns = [
            # SQL injection patterns
            r"(\bunion\b|\bselect\b|\binsert\b|\bdelete\b|\bdrop\b)",
            # XSS patterns
            r"(<script|javascript:|data:text/html)",
            # Directory traversal
            r"(\.\.\/|\.\.\\)",
            # Command injection
            r"(\;|\||\&|\$\(|\`)",
        ]
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Generate request ID
        import uuid
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Get client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        
        # Parse user agent
        parsed_ua = user_agents.parse(user_agent)
        
        # Check for suspicious patterns in request
        await self._check_suspicious_request(request, client_ip)
        
        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log request details
            logger.info(
                "Request processed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                client_ip=client_ip,
                user_agent=user_agent,
                browser=parsed_ua.browser.family,
                os=parsed_ua.os.family,
                status_code=response.status_code,
                process_time=process_time
            )
            
            # Track slow requests
            if process_time > 5.0:  # 5 second threshold
                await self._log_slow_request(request, client_ip, process_time)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            logger.error(
                "Request failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                client_ip=client_ip,
                error=str(e),
                process_time=process_time
            )
            
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _check_suspicious_request(self, request: Request, client_ip: str):
        """Check for suspicious request patterns"""
        import re
        
        # Check URL path
        path = str(request.url.path)
        query = str(request.url.query)
        
        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, path + query, re.IGNORECASE):
                logger.warning(
                    "Suspicious request pattern detected",
                    ip=client_ip,
                    path=path,
                    query=query,
                    pattern=pattern
                )
                
                await self._log_security_event(
                    "suspicious_request_pattern",
                    "high",
                    client_ip,
                    f"Suspicious pattern in request: {pattern}",
                    {"path": path, "query": query, "pattern": pattern}
                )
                
                # Could implement automatic blocking here
                break
        
        # Check for excessive query parameters
        if len(request.query_params) > 50:
            await self._log_security_event(
                "excessive_query_parameters",
                "medium",
                client_ip,
                f"Excessive query parameters: {len(request.query_params)}",
                {"param_count": len(request.query_params)}
            )
        
        # Check for unusual HTTP methods
        if request.method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]:
            await self._log_security_event(
                "unusual_http_method",
                "medium",
                client_ip,
                f"Unusual HTTP method: {request.method}",
                {"method": request.method}
            )
    
    async def _log_slow_request(self, request: Request, client_ip: str, process_time: float):
        """Log slow requests for performance monitoring"""
        await self._log_security_event(
            "slow_request",
            "low",
            client_ip,
            f"Slow request: {process_time:.2f}s",
            {
                "path": str(request.url.path),
                "method": request.method,
                "process_time": process_time
            }
        )
    
    async def _log_security_event(
        self,
        event_type: str,
        severity: str,
        ip_address: str,
        description: str,
        metadata: Optional[dict] = None
    ):
        """Log security event"""
        event_data = {
            "event_type": event_type,
            "severity": severity,
            "ip_address": ip_address,
            "description": description,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await redis_client.set_secure(
            f"security_event:{datetime.utcnow().timestamp()}",
            event_data,
            expire_seconds=86400
        )


class SessionSecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for session security and management
    """
    
    async def dispatch(self, request: Request, call_next):
        # Check for session hijacking indicators
        await self._check_session_security(request)
        
        response = await call_next(request)
        
        # Add session security cookies
        if hasattr(request.state, 'user_id'):
            self._set_secure_session_cookies(response)
        
        return response
    
    async def _check_session_security(self, request: Request):
        """Check for session security issues"""
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return
        
        # Extract session info from token
        # This would be integrated with JWT verification
        pass
    
    def _set_secure_session_cookies(self, response: Response):
        """Set secure session cookies"""
        if settings.security.SESSION_SECURE_ONLY:
            # Set secure session attributes
            response.headers["Set-Cookie"] = (
                f"session_secure=true; "
                f"HttpOnly; "
                f"Secure; "
                f"SameSite={settings.security.SESSION_SAMESITE}; "
                f"Max-Age={settings.security.SESSION_EXPIRE_MINUTES * 60}"
            )


class GeolocationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for geolocation-based security
    """
    
    async def dispatch(self, request: Request, call_next):
        if settings.security.GEO_BLOCKING_ENABLED:
            client_ip = self._get_client_ip(request)
            
            # Check geolocation (placeholder - would integrate with GeoIP service)
            is_allowed = await self._check_geolocation(client_ip)
            
            if not is_allowed:
                logger.warning("Geo-blocked request", ip=client_ip)
                await self._log_security_event(
                    "geo_blocked_access",
                    "medium",
                    client_ip,
                    f"Access denied from unauthorized location"
                )
                
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access denied from this location"}
                )
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    async def _check_geolocation(self, ip: str) -> bool:
        """Check if IP is from allowed location"""
        # Placeholder implementation
        # In production, integrate with GeoIP service
        return True
    
    async def _log_security_event(
        self,
        event_type: str,
        severity: str,
        ip_address: str,
        description: str
    ):
        """Log security event"""
        event_data = {
            "event_type": event_type,
            "severity": severity,
            "ip_address": ip_address,
            "description": description,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await redis_client.set_secure(
            f"security_event:{datetime.utcnow().timestamp()}",
            event_data,
            expire_seconds=86400
        )