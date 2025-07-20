"""
AI Integration Service - GrandModel Synergy Detection Bridge
Integrates GrandModel AI synergy detection with IDF building readiness system.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import sys
import os

# Add GrandModel to path
sys.path.append('/home/QuantNova/GrandModel/src')

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..core.database import get_db
from ..models.core import Inspection, Building, InspectionStatus, Priority
from ..models.base import BaseModel
from ..core.audit import AuditLogger

# Import GrandModel synergy components
try:
    from synergy.detector import SynergyDetector
    from synergy.base import SynergyPattern, Signal
    from synergy.patterns import MLMIPatternDetector, NWRQKPatternDetector, FVGPatternDetector
    from core.minimal_dependencies import ComponentBase, EventType
    GRANDMODEL_AVAILABLE = True
except ImportError as e:
    logging.warning(f"GrandModel components not available: {e}")
    GRANDMODEL_AVAILABLE = False

logger = logging.getLogger(__name__)


class BuildingReadinessMetric(str, Enum):
    """Building readiness metrics derived from inspection data"""
    COMPLETION_RATE = "completion_rate"
    DEFECT_RATE = "defect_rate"
    SCHEDULE_ADHERENCE = "schedule_adherence"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    CONTRACTOR_COORDINATION = "contractor_coordination"


@dataclass
class BuildingReadinessSignal:
    """Signal representing building readiness state"""
    building_id: str
    metric: BuildingReadinessMetric
    value: float
    timestamp: datetime
    direction: int  # 1 for improving, -1 for degrading
    confidence: float
    metadata: Dict[str, Any]


@dataclass
class AIRecommendation:
    """AI-powered recommendation for building readiness optimization"""
    building_id: str
    recommendation_type: str
    priority: Priority
    title: str
    description: str
    expected_impact: float
    confidence: float
    actions: List[str]
    deadline: Optional[datetime]
    metadata: Dict[str, Any]


class BuildingReadinessAnalyzer:
    """Analyzes building readiness using IDF inspection data"""
    
    def __init__(self, db: Session):
        self.db = db
        self.audit_logger = AuditLogger(db)
    
    def analyze_building_readiness(self, building_id: str) -> Dict[str, Any]:
        """Analyze building readiness metrics"""
        try:
            # Get building and inspections
            building = self.db.query(Building).filter(
                Building.building_code == building_id
            ).first()
            
            if not building:
                return {"error": f"Building {building_id} not found"}
            
            inspections = self.db.query(Inspection).filter(
                Inspection.building_id == building_id
            ).all()
            
            if not inspections:
                return {
                    "building_id": building_id,
                    "total_inspections": 0,
                    "readiness_score": 0.0,
                    "signals": [],
                    "recommendations": []
                }
            
            # Calculate readiness metrics
            metrics = self._calculate_readiness_metrics(inspections)
            
            # Generate readiness signals
            signals = self._generate_readiness_signals(building_id, metrics)
            
            # Calculate overall readiness score
            readiness_score = self._calculate_overall_readiness_score(metrics)
            
            return {
                "building_id": building_id,
                "building_name": building.building_name,
                "total_inspections": len(inspections),
                "readiness_score": readiness_score,
                "metrics": metrics,
                "signals": [self._signal_to_dict(s) for s in signals],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing building readiness: {e}")
            return {"error": str(e)}
    
    def _calculate_readiness_metrics(self, inspections: List[Inspection]) -> Dict[str, float]:
        """Calculate readiness metrics from inspection data"""
        total_inspections = len(inspections)
        
        # Completion rate
        completed = sum(1 for i in inspections if i.status == InspectionStatus.COMPLETED)
        completion_rate = completed / total_inspections if total_inspections > 0 else 0
        
        # Defect rate (inspections with follow-up required)
        defects = sum(1 for i in inspections if i.status == InspectionStatus.FOLLOW_UP_REQUIRED)
        defect_rate = defects / total_inspections if total_inspections > 0 else 0
        
        # Schedule adherence
        on_schedule = sum(1 for i in inspections 
                         if i.actual_completion and i.target_completion and 
                         i.actual_completion <= i.target_completion)
        schedule_adherence = on_schedule / completed if completed > 0 else 0
        
        # Regulatory compliance (report distributed)
        compliant = sum(1 for i in inspections if i.report_distributed)
        regulatory_compliance = compliant / completed if completed > 0 else 0
        
        # Contractor coordination
        coordinated = sum(1 for i in inspections if i.coordinated_with_contractor)
        contractor_coordination = coordinated / total_inspections if total_inspections > 0 else 0
        
        return {
            "completion_rate": completion_rate,
            "defect_rate": defect_rate,
            "schedule_adherence": schedule_adherence,
            "regulatory_compliance": regulatory_compliance,
            "contractor_coordination": contractor_coordination
        }
    
    def _generate_readiness_signals(self, building_id: str, metrics: Dict[str, float]) -> List[BuildingReadinessSignal]:
        """Generate readiness signals based on metrics"""
        signals = []
        timestamp = datetime.now()
        
        # Completion rate signal
        completion_direction = 1 if metrics["completion_rate"] > 0.8 else -1
        signals.append(BuildingReadinessSignal(
            building_id=building_id,
            metric=BuildingReadinessMetric.COMPLETION_RATE,
            value=metrics["completion_rate"],
            timestamp=timestamp,
            direction=completion_direction,
            confidence=0.9,
            metadata={"threshold": 0.8}
        ))
        
        # Defect rate signal (inverted - lower is better)
        defect_direction = 1 if metrics["defect_rate"] < 0.2 else -1
        signals.append(BuildingReadinessSignal(
            building_id=building_id,
            metric=BuildingReadinessMetric.DEFECT_RATE,
            value=1 - metrics["defect_rate"],  # Invert for positive signal
            timestamp=timestamp,
            direction=defect_direction,
            confidence=0.8,
            metadata={"threshold": 0.2}
        ))
        
        # Schedule adherence signal
        schedule_direction = 1 if metrics["schedule_adherence"] > 0.9 else -1
        signals.append(BuildingReadinessSignal(
            building_id=building_id,
            metric=BuildingReadinessMetric.SCHEDULE_ADHERENCE,
            value=metrics["schedule_adherence"],
            timestamp=timestamp,
            direction=schedule_direction,
            confidence=0.85,
            metadata={"threshold": 0.9}
        ))
        
        return signals
    
    def _calculate_overall_readiness_score(self, metrics: Dict[str, float]) -> float:
        """Calculate overall readiness score"""
        weights = {
            "completion_rate": 0.3,
            "defect_rate": 0.25,
            "schedule_adherence": 0.25,
            "regulatory_compliance": 0.15,
            "contractor_coordination": 0.05
        }
        
        score = 0.0
        for metric, weight in weights.items():
            value = metrics.get(metric, 0)
            if metric == "defect_rate":
                value = 1 - value  # Invert defect rate
            score += value * weight
        
        return min(max(score, 0.0), 1.0)
    
    def _signal_to_dict(self, signal: BuildingReadinessSignal) -> Dict[str, Any]:
        """Convert signal to dictionary"""
        return {
            "building_id": signal.building_id,
            "metric": signal.metric.value,
            "value": signal.value,
            "timestamp": signal.timestamp.isoformat(),
            "direction": signal.direction,
            "confidence": signal.confidence,
            "metadata": signal.metadata
        }


class GrandModelSynergyBridge:
    """Bridge between GrandModel synergy detection and IDF building readiness"""
    
    def __init__(self, db: Session):
        self.db = db
        self.readiness_analyzer = BuildingReadinessAnalyzer(db)
        self.audit_logger = AuditLogger(db)
        self.synergy_detector = None
        
        if GRANDMODEL_AVAILABLE:
            self._initialize_synergy_detector()
    
    def _initialize_synergy_detector(self):
        """Initialize GrandModel synergy detector"""
        try:
            # Create mock kernel for synergy detector
            class MockKernel:
                def __init__(self):
                    self.config = {
                        'synergy_detector': {
                            'time_window_bars': 10,
                            'cooldown_bars': 5,
                            'mlmi_threshold': 0.5,
                            'nwrqk_threshold': 0.3,
                            'fvg_min_size': 0.001,
                            'synergy_expiration_minutes': 30
                        }
                    }
                    self.event_bus = MockEventBus()
            
            class MockEventBus:
                def subscribe(self, event_type, handler):
                    pass
                
                def unsubscribe(self, event_type, handler):
                    pass
                
                def create_event(self, event_type, payload, source):
                    return MockEvent(event_type, payload, source)
                
                def publish(self, event):
                    pass
            
            class MockEvent:
                def __init__(self, event_type, payload, source):
                    self.event_type = event_type
                    self.payload = payload
                    self.source = source
                    self.timestamp = datetime.now()
            
            mock_kernel = MockKernel()
            self.synergy_detector = SynergyDetector("synergy_detector", mock_kernel)
            logger.info("GrandModel synergy detector initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize synergy detector: {e}")
            self.synergy_detector = None
    
    def detect_building_readiness_synergies(self, building_ids: List[str]) -> Dict[str, Any]:
        """Detect synergies in building readiness patterns"""
        try:
            synergies = []
            
            for building_id in building_ids:
                # Analyze building readiness
                readiness_data = self.readiness_analyzer.analyze_building_readiness(building_id)
                
                if "error" in readiness_data:
                    continue
                
                # Convert readiness signals to GrandModel-compatible format
                features = self._convert_readiness_to_features(readiness_data)
                
                # Apply synergy detection if available
                if self.synergy_detector and features:
                    synergy = self.synergy_detector.process_features(features, datetime.now())
                    if synergy:
                        synergies.append({
                            "building_id": building_id,
                            "synergy_type": synergy.synergy_type,
                            "direction": synergy.direction,
                            "confidence": synergy.confidence,
                            "signals": [self._signal_to_dict(s) for s in synergy.signals],
                            "completion_time": synergy.completion_time.isoformat(),
                            "bars_to_complete": synergy.bars_to_complete,
                            "readiness_context": readiness_data
                        })
            
            return {
                "total_buildings_analyzed": len(building_ids),
                "synergies_detected": len(synergies),
                "synergies": synergies,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error detecting building readiness synergies: {e}")
            return {"error": str(e)}
    
    def _convert_readiness_to_features(self, readiness_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert building readiness data to GrandModel-compatible features"""
        if "metrics" not in readiness_data:
            return {}
        
        metrics = readiness_data["metrics"]
        
        # Map readiness metrics to trading-like signals
        features = {
            "timestamp": datetime.now(),
            "current_price": readiness_data["readiness_score"],
            
            # MLMI-like signal (completion rate)
            "mlmi_signal": 1 if metrics["completion_rate"] > 0.8 else -1,
            "mlmi_value": metrics["completion_rate"] * 100,
            
            # NWRQK-like signal (schedule adherence trend)
            "nwrqk_signal": 1 if metrics["schedule_adherence"] > 0.9 else -1,
            "nwrqk_slope": (metrics["schedule_adherence"] - 0.5) * 2,
            "nwrqk_value": metrics["schedule_adherence"],
            
            # FVG-like signal (defect mitigation)
            "fvg_mitigation_signal": metrics["defect_rate"] < 0.2,
            "fvg_bullish_mitigated": metrics["defect_rate"] < 0.1,
            "fvg_bearish_mitigated": metrics["defect_rate"] > 0.3,
            "fvg_bullish_size": 1 - metrics["defect_rate"],
            "fvg_bearish_size": metrics["defect_rate"],
            "fvg_bullish_level": 1 - metrics["defect_rate"],
            "fvg_bearish_level": metrics["defect_rate"],
            
            # Additional context
            "volatility_30": abs(metrics["completion_rate"] - 0.5) * 2,
            "volume_ratio": metrics["contractor_coordination"] + 0.1,
            "volume_momentum_30": metrics["regulatory_compliance"]
        }
        
        return features
    
    def _signal_to_dict(self, signal) -> Dict[str, Any]:
        """Convert GrandModel signal to dictionary"""
        return {
            "signal_type": signal.signal_type,
            "direction": signal.direction,
            "timestamp": signal.timestamp.isoformat(),
            "value": signal.value,
            "strength": signal.strength,
            "metadata": signal.metadata
        }


class PredictiveAnalyticsEngine:
    """Predictive analytics engine for building readiness optimization"""
    
    def __init__(self, db: Session):
        self.db = db
        self.synergy_bridge = GrandModelSynergyBridge(db)
        self.audit_logger = AuditLogger(db)
    
    def generate_predictive_insights(self, building_ids: List[str]) -> Dict[str, Any]:
        """Generate predictive insights for building readiness"""
        try:
            insights = []
            
            for building_id in building_ids:
                # Get building data
                building = self.db.query(Building).filter(
                    Building.building_code == building_id
                ).first()
                
                if not building:
                    continue
                
                # Analyze current readiness
                readiness_data = self.synergy_bridge.readiness_analyzer.analyze_building_readiness(building_id)
                
                if "error" in readiness_data:
                    continue
                
                # Generate predictions
                predictions = self._generate_predictions(building_id, readiness_data)
                
                # Generate recommendations
                recommendations = self._generate_recommendations(building_id, readiness_data, predictions)
                
                insights.append({
                    "building_id": building_id,
                    "building_name": building.building_name,
                    "current_readiness": readiness_data,
                    "predictions": predictions,
                    "recommendations": recommendations,
                    "timestamp": datetime.now().isoformat()
                })
            
            return {
                "total_buildings": len(building_ids),
                "insights": insights,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating predictive insights: {e}")
            return {"error": str(e)}
    
    def _generate_predictions(self, building_id: str, readiness_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate predictions for building readiness"""
        current_score = readiness_data.get("readiness_score", 0)
        metrics = readiness_data.get("metrics", {})
        
        # Simple prediction model based on current trends
        completion_trend = 1 if metrics.get("completion_rate", 0) > 0.8 else -1
        schedule_trend = 1 if metrics.get("schedule_adherence", 0) > 0.9 else -1
        defect_trend = 1 if metrics.get("defect_rate", 0) < 0.2 else -1
        
        # Predict 7-day and 30-day readiness
        trend_factor = (completion_trend + schedule_trend + defect_trend) / 3
        
        predicted_7_day = min(max(current_score + (trend_factor * 0.1), 0), 1)
        predicted_30_day = min(max(current_score + (trend_factor * 0.3), 0), 1)
        
        return {
            "current_score": current_score,
            "predicted_7_day": predicted_7_day,
            "predicted_30_day": predicted_30_day,
            "trend_direction": trend_factor,
            "confidence": 0.75,
            "factors": {
                "completion_trend": completion_trend,
                "schedule_trend": schedule_trend,
                "defect_trend": defect_trend
            }
        }
    
    def _generate_recommendations(self, building_id: str, readiness_data: Dict[str, Any], predictions: Dict[str, Any]) -> List[AIRecommendation]:
        """Generate AI-powered recommendations"""
        recommendations = []
        metrics = readiness_data.get("metrics", {})
        
        # Completion rate recommendation
        if metrics.get("completion_rate", 0) < 0.8:
            recommendations.append(AIRecommendation(
                building_id=building_id,
                recommendation_type="completion_acceleration",
                priority=Priority.HIGH,
                title="Accelerate Inspection Completion",
                description="Building completion rate is below target. Focus on completing pending inspections.",
                expected_impact=0.15,
                confidence=0.85,
                actions=[
                    "Schedule remaining inspections within 7 days",
                    "Assign additional inspection teams if needed",
                    "Prioritize critical inspection types"
                ],
                deadline=datetime.now() + timedelta(days=7),
                metadata={"current_rate": metrics.get("completion_rate", 0)}
            ))
        
        # Defect rate recommendation
        if metrics.get("defect_rate", 0) > 0.2:
            recommendations.append(AIRecommendation(
                building_id=building_id,
                recommendation_type="defect_mitigation",
                priority=Priority.MEDIUM,
                title="Address Defect Management",
                description="Defect rate is above acceptable threshold. Implement corrective actions.",
                expected_impact=0.12,
                confidence=0.8,
                actions=[
                    "Review defect patterns and root causes",
                    "Coordinate with contractors for defect resolution",
                    "Implement preventive measures"
                ],
                deadline=datetime.now() + timedelta(days=14),
                metadata={"current_rate": metrics.get("defect_rate", 0)}
            ))
        
        # Schedule adherence recommendation
        if metrics.get("schedule_adherence", 0) < 0.9:
            recommendations.append(AIRecommendation(
                building_id=building_id,
                recommendation_type="schedule_optimization",
                priority=Priority.MEDIUM,
                title="Improve Schedule Adherence",
                description="Schedule adherence is below target. Optimize planning and execution.",
                expected_impact=0.1,
                confidence=0.75,
                actions=[
                    "Review and adjust inspection schedules",
                    "Improve coordination between teams",
                    "Implement buffer time for complex inspections"
                ],
                deadline=datetime.now() + timedelta(days=10),
                metadata={"current_rate": metrics.get("schedule_adherence", 0)}
            ))
        
        return recommendations


class AIIntegrationService:
    """Main AI integration service for IDF system"""
    
    def __init__(self, db: Session):
        self.db = db
        self.synergy_bridge = GrandModelSynergyBridge(db)
        self.predictive_engine = PredictiveAnalyticsEngine(db)
        self.audit_logger = AuditLogger(db)
    
    async def get_building_ai_insights(self, building_ids: List[str]) -> Dict[str, Any]:
        """Get comprehensive AI insights for buildings"""
        try:
            # Generate predictive insights
            insights = self.predictive_engine.generate_predictive_insights(building_ids)
            
            # Detect synergies
            synergies = self.synergy_bridge.detect_building_readiness_synergies(building_ids)
            
            # Combine results
            result = {
                "insights": insights,
                "synergies": synergies,
                "timestamp": datetime.now().isoformat(),
                "ai_system_status": {
                    "grandmodel_available": GRANDMODEL_AVAILABLE,
                    "synergy_detection_enabled": self.synergy_bridge.synergy_detector is not None,
                    "predictive_analytics_enabled": True
                }
            }
            
            # Log the AI analysis
            await self.audit_logger.log_action(
                table_name="ai_analysis",
                record_id=0,
                action="ANALYZE",
                user_id="system",
                new_value=f"AI analysis for {len(building_ids)} buildings"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting AI insights: {e}")
            return {"error": str(e)}
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get AI integration system status"""
        return {
            "grandmodel_integration": {
                "available": GRANDMODEL_AVAILABLE,
                "synergy_detector_initialized": self.synergy_bridge.synergy_detector is not None,
                "version": "1.0.0"
            },
            "predictive_analytics": {
                "enabled": True,
                "version": "1.0.0"
            },
            "marl_coordination": {
                "enabled": GRANDMODEL_AVAILABLE,
                "status": "ready" if GRANDMODEL_AVAILABLE else "unavailable"
            },
            "timestamp": datetime.now().isoformat()
        }