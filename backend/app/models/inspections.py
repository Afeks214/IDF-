"""
Engineering inspection models for Infrastructure Competency & Inspection Management.
Handles detailed checklist items for engineering domain (ÔàÓáÔ).
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Dict, List, Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, 
    String, Text, JSON, Float
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from .base import BaseModel


class EngineeringInspectionType(str, PyEnum):
    """Engineering inspection categories."""
    SPECIFICATION = "specification"  # ĞäÙÕß
    RADIATION = "radiation"  # çèÙàÔ
    WATERPROOFING = "waterproofing"  # ĞÙØÕİ ÔæäÔ ÕàÙçÕÖÙİ
    SMOKE_EVACUATION = "smoke_evacuation"  # äÙàÕÙ âéß
    FURNITURE_INVENTORY = "furniture_inventory"  # áäÙèê èÙÔÕØ
    FLOORING_INTEGRITY = "flooring_integrity"  # éÜŞÕê èÙæÕã
    WINDOW_INTEGRITY = "window_integrity"  # éÜŞÕê ×ÜÕàÕê
    ELEVATOR_FUNCTIONALITY = "elevator_functionality"  # êçÙàÕê ŞâÜÙÕê
    RESTROOM_FUNCTIONALITY = "restroom_functionality"  # êçÙàÕê éÙèÕêÙİ


class ChecklistItemStatus(str, PyEnum):
    """Status of individual checklist items."""
    NOT_CHECKED = "not_checked"  # ÜĞ àÑÓç
    PASS = "pass"  # êçÙß
    FAIL = "fail"  # ÜĞ êçÙß
    PARTIAL = "partial"  # êçÙß ×ÜçÙê
    NOT_APPLICABLE = "not_applicable"  # ÜĞ èÜÕÕàØÙ


class Priority(str, PyEnum):
    """Priority levels for inspection items."""
    LOW = "low"  # àŞÕÚ
    MEDIUM = "medium"  # ÑÙàÕàÙ
    HIGH = "high"  # ÒÑÕÔ
    CRITICAL = "critical"  # çèÙØÙ


class EngineeringInspection(BaseModel):
    """Main engineering inspection record."""
    
    __tablename__ = "engineering_inspections"
    
    # Core identification
    building_id = Column(String(10), ForeignKey("buildings.building_code"), nullable=False, index=True)
    inspection_type = Column(Enum(EngineeringInspectionType), nullable=False, index=True)
    inspector_name = Column(String(100), nullable=False, comment="éİ ÔÑÕÓç")
    inspection_date = Column(DateTime, nullable=False, default=datetime.utcnow, comment="êĞèÙÚ ÑÓÙçÔ")
    
    # Progress tracking
    total_items = Column(Integer, default=0, comment="áÚ äèÙØÙİ")
    completed_items = Column(Integer, default=0, comment="äèÙØÙİ éÔÕéÜŞÕ")
    passed_items = Column(Integer, default=0, comment="äèÙØÙİ êçÙàÙİ")
    failed_items = Column(Integer, default=0, comment="äèÙØÙİ ÜĞ êçÙàÙİ")
    progress_percentage = Column(Float, default=0.0, comment="Ğ×ÕÖ ÔéÜŞÔ")
    
    # Status and metadata
    is_completed = Column(Boolean, default=False, comment="ÑÓÙçÔ ÔÕéÜŞÔ")
    completion_date = Column(DateTime, comment="êĞèÙÚ ÔéÜŞÔ")
    overall_notes = Column(Text, comment="ÔâèÕê ÛÜÜÙÕê")
    metadata = Column(JSONB, comment="àêÕàÙİ àÕáäÙİ")
    
    # Relationships
    building = relationship("Building", back_populates="engineering_inspections")
    checklist_items = relationship("EngineeringChecklistItem", back_populates="inspection", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_eng_inspection_building_type", "building_id", "inspection_type"),
        Index("idx_eng_inspection_date", "inspection_date"),
        Index("idx_eng_inspection_completed", "is_completed"),
    )


class EngineeringChecklistItem(BaseModel):
    """Individual checklist items for engineering inspections."""
    
    __tablename__ = "engineering_checklist_items"
    
    # Relations
    inspection_id = Column(Integer, ForeignKey("engineering_inspections.id"), nullable=False, index=True)
    
    # Item identification
    category = Column(Enum(EngineeringInspectionType), nullable=False, comment="çØÒÕèÙÔ")
    subcategory = Column(String(100), comment="êê-çØÒÕèÙÔ")
    item_code = Column(String(20), nullable=False, comment="çÕÓ äèÙØ")
    item_name_hebrew = Column(String(200), nullable=False, comment="éİ ÔäèÙØ ÑâÑèÙê")
    item_name_english = Column(String(200), comment="éİ ÔäèÙØ ÑĞàÒÜÙê")
    description = Column(Text, comment="êÙĞÕè ŞäÕèØ")
    
    # Status and evaluation
    status = Column(Enum(ChecklistItemStatus), default=ChecklistItemStatus.NOT_CHECKED, nullable=False)
    priority = Column(Enum(Priority), default=Priority.MEDIUM, nullable=False)
    is_required = Column(Boolean, default=True, comment="äèÙØ ×ÕÑÔ")
    
    # Inspection details
    inspector_notes = Column(Text, comment="ÔâèÕê ÑÕÓç")
    defect_description = Column(Text, comment="êÙĞÕè ÜÙçÕÙ")
    recommended_action = Column(Text, comment="äâÕÜÔ ŞÕŞÜæê")
    estimated_repair_cost = Column(Float, comment="âÜÕê êÙçÕß ŞéÕâèê")
    
    # Follow-up
    requires_followup = Column(Boolean, default=False, comment="ÓèÕéÔ ÑÓÙçÔ ×ÕÖèê")
    followup_date = Column(DateTime, comment="êĞèÙÚ ÑÓÙçÔ ×ÕÖèê")
    contractor_assigned = Column(String(100), comment="çÑÜß éÔÕçæÔ")
    
    # Technical data
    measured_values = Column(JSONB, comment="âèÛÙİ éàŞÓÓÕ")
    reference_standards = Column(JSONB, comment="êçàÙİ èÜÕÕàØÙÙİ")
    
    # Timestamps
    checked_at = Column(DateTime, comment="ÖŞß ÑÓÙçÔ")
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    inspection = relationship("EngineeringInspection", back_populates="checklist_items")
    
    __table_args__ = (
        Index("idx_checklist_inspection_category", "inspection_id", "category"),
        Index("idx_checklist_status", "status"),
        Index("idx_checklist_priority", "priority"),
        Index("idx_checklist_followup", "requires_followup"),
    )


class EngineeringChecklistTemplate(BaseModel):
    """Template for engineering checklist items."""
    
    __tablename__ = "engineering_checklist_templates"
    
    # Template identification
    category = Column(Enum(EngineeringInspectionType), nullable=False, index=True)
    subcategory = Column(String(100), comment="êê-çØÒÕèÙÔ")
    item_code = Column(String(20), nullable=False, unique=True, comment="çÕÓ äèÙØ")
    item_name_hebrew = Column(String(200), nullable=False, comment="éİ ÔäèÙØ ÑâÑèÙê")
    item_name_english = Column(String(200), comment="éİ ÔäèÙØ ÑĞàÒÜÙê")
    description = Column(Text, comment="êÙĞÕè ŞäÕèØ")
    
    # Default settings
    default_priority = Column(Enum(Priority), default=Priority.MEDIUM, nullable=False)
    is_required = Column(Boolean, default=True, comment="äèÙØ ×ÕÑÔ")
    sort_order = Column(Integer, default=0, comment="áÓè ÔæÒÔ")
    
    # Validation rules
    validation_rules = Column(JSONB, comment="ÛÜÜÙ ÕÜÙÓæÙÔ")
    reference_standards = Column(JSONB, comment="êçàÙİ èÜÕÕàØÙÙİ")
    
    # Status
    is_active = Column(Boolean, default=True, comment="äâÙÜ")
    
    __table_args__ = (
        Index("idx_template_category_order", "category", "sort_order"),
        Index("idx_template_active", "is_active"),
    )


class InspectionReport(BaseModel):
    """Generated inspection reports."""
    
    __tablename__ = "inspection_reports"
    
    # Relations
    inspection_id = Column(Integer, ForeignKey("engineering_inspections.id"), nullable=False, index=True)
    
    # Report metadata
    report_type = Column(String(50), nullable=False, comment="áÕÒ ÓÕ×")
    generated_by = Column(String(100), nullable=False, comment="àÕæè âÜ ÙÓÙ")
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Report content
    title = Column(String(200), nullable=False, comment="ÛÕêèê ÓÕ×")
    executive_summary = Column(Text, comment="áÙÛÕİ ŞàÔÜÙİ")
    detailed_findings = Column(Text, comment="ŞŞæĞÙİ ŞäÕèØÙİ")
    recommendations = Column(Text, comment="ÔŞÜæÕê")
    
    # File information
    file_path = Column(String(500), comment="àêÙÑ çÕÑå")
    file_size = Column(Integer, comment="ÒÕÓÜ çÕÑå")
    file_format = Column(String(10), comment="äÕèŞØ çÕÑå")
    
    # Distribution
    distributed_to = Column(JSONB, comment="ÔÕäå ĞÜ")
    distribution_date = Column(DateTime, comment="êĞèÙÚ ÔäæÔ")
    
    # Relationships
    inspection = relationship("EngineeringInspection")
    
    __table_args__ = (
        Index("idx_report_inspection", "inspection_id"),
        Index("idx_report_generated", "generated_at"),
    )


# Update Building model to include engineering inspections relationship
def update_building_model():
    """Add engineering inspections relationship to Building model."""
    from .core import Building
    if not hasattr(Building, 'engineering_inspections'):
        Building.engineering_inspections = relationship(
            "EngineeringInspection", 
            back_populates="building",
            cascade="all, delete-orphan"
        )