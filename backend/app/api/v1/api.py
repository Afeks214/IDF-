#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main API Router for IDF Testing Infrastructure
Manager Dashboard Endpoints with Hebrew Support
"""

from fastapi import APIRouter

from .endpoints import auth
# TODO: Uncomment when these endpoints are ready
# from .endpoints import dashboard, inspections, buildings

api_router = APIRouter()

# Authentication endpoints
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"],
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