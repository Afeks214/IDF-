#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main API Router for IDF Testing Infrastructure
Manager Dashboard Endpoints with Hebrew Support
"""

from fastapi import APIRouter

from .endpoints import auth
from .endpoints import ai_integration
from .endpoints import data_processing
from .endpoints import reporting
from .endpoints import building_readiness
# TODO: Uncomment when these endpoints are ready
# from .endpoints import dashboard, inspections, buildings

api_router = APIRouter()

# Authentication endpoints
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"],
)

# AI Integration endpoints
api_router.include_router(
    ai_integration.router,
    prefix="/ai",
    tags=["AI Integration"],
)

# Enhanced Data Processing endpoints
api_router.include_router(
    data_processing.router,
    prefix="/data",
    tags=["Data Processing"],
)

# Reporting endpoints
api_router.include_router(
    reporting.router,
    prefix="/reporting",
    tags=["Reporting"],
)

# Building Readiness endpoints (PRD Compliant)
api_router.include_router(
    building_readiness.router,
    prefix="/buildings-readiness",
    tags=["Building Readiness"],
)

# Include all endpoint routers
# TODO: Uncomment when these endpoints are ready
# api_router.include_router(
#     dashboard.router,
#     prefix="/dashboard",
#     tags=["dashboard"],
# )

# api_router.include_router(
#     inspections.router,
#     prefix="/inspections",
#     tags=["inspections"],
# )

# api_router.include_router(
#     buildings.router,
#     prefix="/buildings",
#     tags=["buildings"],
# )