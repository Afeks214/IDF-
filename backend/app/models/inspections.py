"""
Engineering inspection models for Infrastructure Competency & Inspection Management.
Handles detailed checklist items for engineering domain (�����).
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
    SPECIFICATION = "specification"  # �����
    RADIATION = "radiation"  # �����
    WATERPROOFING = "waterproofing"  # ����� ���� ��������
    SMOKE_EVACUATION = "smoke_evacuation"  # ����� ���
    FURNITURE_INVENTORY = "furniture_inventory"  # ����� �����
    FLOORING_INTEGRITY = "flooring_integrity"  # ����� �����
    WINDOW_INTEGRITY = "window_integrity"  # ����� ������
    ELEVATOR_FUNCTIONALITY = "elevator_functionality"  # ������ ������
    RESTROOM_FUNCTIONALITY = "restroom_functionality"  # ������ �������


class ChecklistItemStatus(str, PyEnum):
    """Status of individual checklist items."""
    NOT_CHECKED = "not_checked"  # �� ����
    PASS = "pass"  # ����
    FAIL = "fail"  # �� ����
    PARTIAL = "partial"  # ���� �����
    NOT_APPLICABLE = "not_applicable"  # �� �������


class Priority(str, PyEnum):
    """Priority levels for inspection items."""
    LOW = "low"  # ����
    MEDIUM = "medium"  # ������
    HIGH = "high"  # ����
    CRITICAL = "critical"  # �����


class EngineeringInspection(BaseModel):
    """Main engineering inspection record."""
    
    __tablename__ = "engineering_inspections"
    
    # Core identification
    building_id = Column(String(10), ForeignKey("buildings.building_code"), nullable=False, index=True)
    inspection_type = Column(Enum(EngineeringInspectionType), nullable=False, index=True)
    inspector_name = Column(String(100), nullable=False, comment="�� �����")
    inspection_date = Column(DateTime, nullable=False, default=datetime.utcnow, comment="����� �����")
    
    # Progress tracking
    total_items = Column(Integer, default=0, comment="�� ������")
    completed_items = Column(Integer, default=0, comment="������ �������")
    passed_items = Column(Integer, default=0, comment="������ ������")
    failed_items = Column(Integer, default=0, comment="������ �� ������")
    progress_percentage = Column(Float, default=0.0, comment="���� �����")
    
    # Status and metadata
    is_completed = Column(Boolean, default=False, comment="����� ������")
    completion_date = Column(DateTime, comment="����� �����")
    overall_notes = Column(Text, comment="����� ������")
    metadata = Column(JSONB, comment="������ ������")
    
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
    category = Column(Enum(EngineeringInspectionType), nullable=False, comment="�������")
    subcategory = Column(String(100), comment="��-�������")
    item_code = Column(String(20), nullable=False, comment="��� ����")
    item_name_hebrew = Column(String(200), nullable=False, comment="�� ����� ������")
    item_name_english = Column(String(200), comment="�� ����� �������")
    description = Column(Text, comment="����� �����")
    
    # Status and evaluation
    status = Column(Enum(ChecklistItemStatus), default=ChecklistItemStatus.NOT_CHECKED, nullable=False)
    priority = Column(Enum(Priority), default=Priority.MEDIUM, nullable=False)
    is_required = Column(Boolean, default=True, comment="���� ����")
    
    # Inspection details
    inspector_notes = Column(Text, comment="����� ����")
    defect_description = Column(Text, comment="����� �����")
    recommended_action = Column(Text, comment="����� ������")
    estimated_repair_cost = Column(Float, comment="���� ����� ������")
    
    # Follow-up
    requires_followup = Column(Boolean, default=False, comment="����� ����� �����")
    followup_date = Column(DateTime, comment="����� ����� �����")
    contractor_assigned = Column(String(100), comment="���� ������")
    
    # Technical data
    measured_values = Column(JSONB, comment="����� ������")
    reference_standards = Column(JSONB, comment="����� ���������")
    
    # Timestamps
    checked_at = Column(DateTime, comment="��� �����")
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
    subcategory = Column(String(100), comment="��-�������")
    item_code = Column(String(20), nullable=False, unique=True, comment="��� ����")
    item_name_hebrew = Column(String(200), nullable=False, comment="�� ����� ������")
    item_name_english = Column(String(200), comment="�� ����� �������")
    description = Column(Text, comment="����� �����")
    
    # Default settings
    default_priority = Column(Enum(Priority), default=Priority.MEDIUM, nullable=False)
    is_required = Column(Boolean, default=True, comment="���� ����")
    sort_order = Column(Integer, default=0, comment="��� ����")
    
    # Validation rules
    validation_rules = Column(JSONB, comment="���� �������")
    reference_standards = Column(JSONB, comment="����� ���������")
    
    # Status
    is_active = Column(Boolean, default=True, comment="����")
    
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
    report_type = Column(String(50), nullable=False, comment="��� ���")
    generated_by = Column(String(100), nullable=False, comment="���� �� ���")
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Report content
    title = Column(String(200), nullable=False, comment="����� ���")
    executive_summary = Column(Text, comment="����� ������")
    detailed_findings = Column(Text, comment="������ �������")
    recommendations = Column(Text, comment="������")
    
    # File information
    file_path = Column(String(500), comment="���� ����")
    file_size = Column(Integer, comment="���� ����")
    file_format = Column(String(10), comment="����� ����")
    
    # Distribution
    distributed_to = Column(JSONB, comment="���� ��")
    distribution_date = Column(DateTime, comment="����� ����")
    
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