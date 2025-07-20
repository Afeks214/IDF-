"""
AI Integration API endpoints for GrandModel integration with IDF system.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ....core.database import get_db
from ....core.auth_dependencies import get_current_user
from ....services.ai_integration_service import AIIntegrationService
from ....models.user import User

router = APIRouter(prefix="/ai", tags=["AI Integration"])


class BuildingAIInsightsRequest(BaseModel):
    """Request model for building AI insights"""
    building_ids: List[str] = Field(..., description="List of building IDs to analyze")
    include_predictions: bool = Field(True, description="Include predictive analytics")
    include_synergies: bool = Field(True, description="Include synergy detection")
    include_recommendations: bool = Field(True, description="Include AI recommendations")


class BuildingAIInsightsResponse(BaseModel):
    """Response model for building AI insights"""
    insights: dict
    synergies: dict
    timestamp: str
    ai_system_status: dict


class SynergyDetectionRequest(BaseModel):
    """Request model for synergy detection"""
    building_ids: List[str] = Field(..., description="List of building IDs to analyze")
    time_window_hours: Optional[int] = Field(24, description="Time window for analysis in hours")


class SynergyDetectionResponse(BaseModel):
    """Response model for synergy detection"""
    total_buildings_analyzed: int
    synergies_detected: int
    synergies: List[dict]
    timestamp: str


class PredictiveAnalyticsRequest(BaseModel):
    """Request model for predictive analytics"""
    building_ids: List[str] = Field(..., description="List of building IDs to analyze")
    prediction_horizon_days: Optional[int] = Field(30, description="Prediction horizon in days")


class PredictiveAnalyticsResponse(BaseModel):
    """Response model for predictive analytics"""
    total_buildings: int
    insights: List[dict]
    timestamp: str


class AIRecommendationResponse(BaseModel):
    """Response model for AI recommendations"""
    building_id: str
    recommendation_type: str
    priority: str
    title: str
    description: str
    expected_impact: float
    confidence: float
    actions: List[str]
    deadline: Optional[str]
    metadata: dict


class AISystemStatusResponse(BaseModel):
    """Response model for AI system status"""
    grandmodel_integration: dict
    predictive_analytics: dict
    marl_coordination: dict
    timestamp: str


@router.get("/status", response_model=AISystemStatusResponse)
async def get_ai_system_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get AI integration system status"""
    try:
        ai_service = AIIntegrationService(db)
        status = await ai_service.get_system_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting AI system status: {str(e)}")


@router.post("/insights", response_model=BuildingAIInsightsResponse)
async def get_building_ai_insights(
    request: BuildingAIInsightsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive AI insights for buildings"""
    try:
        if not request.building_ids:
            raise HTTPException(status_code=400, detail="Building IDs are required")
        
        ai_service = AIIntegrationService(db)
        insights = await ai_service.get_building_ai_insights(request.building_ids)
        
        if "error" in insights:
            raise HTTPException(status_code=500, detail=insights["error"])
        
        return insights
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting AI insights: {str(e)}")


@router.post("/synergy-detection", response_model=SynergyDetectionResponse)
async def detect_building_synergies(
    request: SynergyDetectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detect synergy patterns in building readiness data"""
    try:
        if not request.building_ids:
            raise HTTPException(status_code=400, detail="Building IDs are required")
        
        ai_service = AIIntegrationService(db)
        synergies = ai_service.synergy_bridge.detect_building_readiness_synergies(request.building_ids)
        
        if "error" in synergies:
            raise HTTPException(status_code=500, detail=synergies["error"])
        
        return synergies
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting synergies: {str(e)}")


@router.post("/predictive-analytics", response_model=PredictiveAnalyticsResponse)
async def generate_predictive_analytics(
    request: PredictiveAnalyticsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate predictive analytics for building readiness"""
    try:
        if not request.building_ids:
            raise HTTPException(status_code=400, detail="Building IDs are required")
        
        ai_service = AIIntegrationService(db)
        insights = ai_service.predictive_engine.generate_predictive_insights(request.building_ids)
        
        if "error" in insights:
            raise HTTPException(status_code=500, detail=insights["error"])
        
        return insights
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating predictive analytics: {str(e)}")


@router.get("/recommendations/{building_id}")
async def get_building_recommendations(
    building_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get AI recommendations for a specific building"""
    try:
        ai_service = AIIntegrationService(db)
        insights = ai_service.predictive_engine.generate_predictive_insights([building_id])
        
        if "error" in insights:
            raise HTTPException(status_code=500, detail=insights["error"])
        
        # Extract recommendations for the building
        building_insights = insights.get("insights", [])
        if not building_insights:
            return {"building_id": building_id, "recommendations": []}
        
        recommendations = building_insights[0].get("recommendations", [])
        
        # Convert recommendation objects to dictionaries
        recommendations_dict = []
        for rec in recommendations:
            recommendations_dict.append({
                "building_id": rec.building_id,
                "recommendation_type": rec.recommendation_type,
                "priority": rec.priority.value,
                "title": rec.title,
                "description": rec.description,
                "expected_impact": rec.expected_impact,
                "confidence": rec.confidence,
                "actions": rec.actions,
                "deadline": rec.deadline.isoformat() if rec.deadline else None,
                "metadata": rec.metadata
            })
        
        return {
            "building_id": building_id,
            "recommendations": recommendations_dict,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recommendations: {str(e)}")


@router.get("/buildings/readiness-analysis")
async def get_buildings_readiness_analysis(
    building_ids: List[str] = Query(..., description="List of building IDs to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get building readiness analysis without AI recommendations"""
    try:
        if not building_ids:
            raise HTTPException(status_code=400, detail="Building IDs are required")
        
        ai_service = AIIntegrationService(db)
        results = []
        
        for building_id in building_ids:
            analysis = ai_service.synergy_bridge.readiness_analyzer.analyze_building_readiness(building_id)
            if "error" not in analysis:
                results.append(analysis)
        
        return {
            "total_buildings": len(building_ids),
            "analyses": results,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting readiness analysis: {str(e)}")


@router.get("/marl/coordination-status")
async def get_marl_coordination_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get MARL coordination system status"""
    try:
        ai_service = AIIntegrationService(db)
        status = await ai_service.get_system_status()
        
        return {
            "marl_coordination": status.get("marl_coordination", {}),
            "synergy_detection": {
                "enabled": status.get("grandmodel_integration", {}).get("synergy_detector_initialized", False),
                "patterns_supported": ["SEQUENTIAL_SYNERGY", "TYPE_1_LEGACY", "TYPE_2_LEGACY", "TYPE_3_LEGACY"]
            },
            "signal_types": ["MLMI", "NWRQK", "FVG"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting MARL coordination status: {str(e)}")


@router.post("/marl/optimize-decisions")
async def optimize_building_decisions(
    request: BuildingAIInsightsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Use MARL coordination to optimize building readiness decisions"""
    try:
        if not request.building_ids:
            raise HTTPException(status_code=400, detail="Building IDs are required")
        
        ai_service = AIIntegrationService(db)
        
        # Get AI insights
        insights = await ai_service.get_building_ai_insights(request.building_ids)
        
        if "error" in insights:
            raise HTTPException(status_code=500, detail=insights["error"])
        
        # Extract optimization recommendations
        optimizations = []
        for insight in insights.get("insights", {}).get("insights", []):
            building_id = insight.get("building_id")
            predictions = insight.get("predictions", {})
            recommendations = insight.get("recommendations", [])
            
            # Calculate optimization score
            current_score = predictions.get("current_score", 0)
            predicted_30_day = predictions.get("predicted_30_day", 0)
            optimization_potential = predicted_30_day - current_score
            
            optimizations.append({
                "building_id": building_id,
                "current_readiness": current_score,
                "predicted_readiness": predicted_30_day,
                "optimization_potential": optimization_potential,
                "priority_actions": [rec.title for rec in recommendations[:3]],
                "marl_coordination_score": min(max(optimization_potential * 10, 0), 1)
            })
        
        # Sort by optimization potential
        optimizations.sort(key=lambda x: x["optimization_potential"], reverse=True)
        
        return {
            "total_buildings": len(request.building_ids),
            "optimizations": optimizations,
            "marl_coordination_active": True,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing decisions: {str(e)}")