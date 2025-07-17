#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDF Testing Infrastructure - Main FastAPI Application
Data Processing & Analytics Integration
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
import structlog
from contextlib import asynccontextmanager

from core.config import settings
from core.database import engine, create_tables
from core.redis_client import redis_client
from api.v1.api import api_router

# Import security middleware
from middleware.security import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    RequestTrackingMiddleware,
    SessionSecurityMiddleware,
    GeolocationMiddleware
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting IDF Testing Infrastructure API")
    
    # Create database tables
    await create_tables()
    logger.info("Database tables created/verified")
    
    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error("Redis connection failed", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("Shutting down IDF Testing Infrastructure API")
    await redis_client.close()


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="IDF Testing Infrastructure API",
        description="Data Processing & Analytics Integration System for Hebrew Excel Data",
        version="1.0.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan
    )
    
    # Add security middleware (order matters!)
    # 1. Security headers (first)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 2. Request tracking and monitoring
    app.add_middleware(RequestTrackingMiddleware)
    
    # 3. Rate limiting and DDoS protection
    app.add_middleware(RateLimitMiddleware)
    
    # 4. Geolocation filtering (if enabled)
    app.add_middleware(GeolocationMiddleware)
    
    # 5. Session security
    app.add_middleware(SessionSecurityMiddleware)
    
    # 6. CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
    )
    
    # 7. Trusted host middleware (production only)
    if settings.ENVIRONMENT == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )
    
    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Mount static files for uploads
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler with structured logging"""
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            exc_info=exc
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_id": "INTERNAL_ERROR",
                "message": "שגיאה פנימית בשרת"  # Hebrew error message
            }
        )
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "IDF Testing Infrastructure API",
            "version": "1.0.0",
            "status": "operational",
            "hebrew_support": True,
            "docs": f"{settings.API_V1_STR}/docs"
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        try:
            # Check Redis
            redis_status = "healthy"
            try:
                await redis_client.ping()
            except:
                redis_status = "unhealthy"
            
            return {
                "status": "healthy",
                "redis": redis_status,
                "timestamp": "2025-07-17T22:00:00Z"
            }
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "error": str(e)}
            )
    
    return app


# Create application instance
app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )