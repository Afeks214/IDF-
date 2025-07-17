"""
Core models for IDF Testing Infrastructure with Hebrew support.
"""

from datetime import date
from enum import Enum as PyEnum
from sqlalchemy import (
    Boolean, Column, Date, Enum, ForeignKey, Index, Integer, 
    String, Text, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from .base import BaseModel


class InspectionStatus(str, PyEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled" 
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    FOLLOW_UP_REQUIRED = "follow_up_required"
    UNDER_REVIEW = "under_review"


class Priority(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FollowUpType(str, PyEnum):
    DEFECT_RESOLUTION = "defect_resolution"
    DOCUMENTATION_UPDATE = "documentation_update"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    CONTRACTOR_COORDINATION = "contractor_coordination"
    RETEST_REQUIRED = "retest_required"


class ITInspectionType(str, PyEnum):
    """IT & Communications inspection types - תקשוב domain"""
    INFRASTRUCTURE_CABLING = "infrastructure_cabling"  # תשתית וחיווט
    NETWORK_SYSTEMS = "network_systems"  # מערכות רשת
    ENDPOINT_FACILITY_SYSTEMS = "endpoint_facility_systems"  # מערכות קצה ומתקן


class InfrastructureCablingType(str, PyEnum):
    """Infrastructure & Cabling inspection subtypes"""
    PHYSICAL_INFRASTRUCTURE_PATHWAYS = "physical_infrastructure_pathways"  # בדיקת בינוי
    INTERNAL_BUILDING_PASSIVE_INFRASTRUCTURE = "internal_building_passive_infrastructure"  # תשתית פאסיבית פנים מבנה


class NetworkSecurityClassification(str, PyEnum):
    """Network security classifications - רמות אבטחת רשת"""
    SECURED_ACTIVE = "secured_active"  # רשת אקטיבית שמורה
    SECRET_ACTIVE = "secret_active"  # רשת אקטיבית סודית
    TOP_SECRET_ACTIVE = "top_secret_active"  # רשת אקטיבית סודי ביותר


class EndpointFacilitySystemType(str, PyEnum):
    """Endpoint & Facility Systems inspection subtypes"""
    SECURITY_SYSTEMS = "security_systems"  # בדיקת מערכות אבטחה
    MULTIMEDIA_SYSTEMS = "multimedia_systems"  # בדיקת מערכות מולטימדיה
    ENDPOINT_WORKSTATIONS = "endpoint_workstations"  # בדיקות עמדות קצה


class ITCheckItemStatus(str, PyEnum):
    """Status for individual IT checklist items"""
    NOT_CHECKED = "not_checked"  # לא נבדק
    PASS = "pass"  # עבר
    FAIL = "fail"  # נכשל
    NOT_APPLICABLE = "not_applicable"  # לא רלוונטי
    NEEDS_FOLLOW_UP = "needs_follow_up"  # נדרש מעקב


class Inspection(BaseModel):
    """Main inspection tracking table with Hebrew support."""
    
    __tablename__ = "inspections"
    
    # Core fields
    building_id = Column(String(10), ForeignKey("buildings.building_code"), nullable=False, index=True)
    building_manager = Column(String(100), comment="מנהל מבנה")
    red_team = Column(String(200), comment="צוות אדום")
    inspection_type = Column(String(150), nullable=False, comment="סוג הבדיקה")
    inspection_leader = Column(String(100), nullable=False, comment="מוביל הבדיקה")
    inspection_round = Column(Integer, comment="סבב בדיקות")
    
    # Status
    status = Column(Enum(InspectionStatus), default=InspectionStatus.PENDING, nullable=False, index=True)
    
    # Regulators
    regulator_1 = Column(String(100), comment="רגולטור 1")
    regulator_2 = Column(String(100), comment="רגולטור 2")
    regulator_3 = Column(String(100), comment="רגולטור 3")
    regulator_4 = Column(String(100), comment="רגולטור 4")
    
    # Dates
    execution_schedule = Column(Date, index=True, comment="לו\"ז ביצוע")
    target_completion = Column(Date, comment="יעד לסיום")
    actual_completion = Column(Date, comment="סיום בפועל")
    
    # Flags
    coordinated_with_contractor = Column(Boolean, default=False, comment="מתואם מול זכיין")
    report_distributed = Column(Boolean, default=False, comment="דו\"ח הופץ")
    repeat_inspection = Column(Boolean, default=False, comment="בדיקה חוזרת")
    
    # Text fields
    defect_report_path = Column(String(500), comment="נתיב דו\"ח ליקויים")
    distribution_date = Column(Date, comment="תאריך הפצה")
    inspection_notes = Column(Text, comment="התרשמות מהבדיקה")
    
    # Metadata
    metadata = Column(JSONB, comment="Additional data")
    
    # Relationships
    building = relationship("Building", back_populates="inspections")
    
    __table_args__ = (
        CheckConstraint("inspection_round >= 1 AND inspection_round <= 4"),
        Index("idx_inspections_building_type", "building_id", "inspection_type"),
        Index("idx_inspections_status", "status"),
    )


class Building(BaseModel):
    """Building master data."""
    
    __tablename__ = "buildings"
    
    building_code = Column(String(10), primary_key=True, comment="Building identifier")
    building_name = Column(String(200), comment="Building name")
    manager_name = Column(String(100), comment="Manager name")
    is_active = Column(Boolean, default=True, comment="Active status")
    
    # Relationships
    inspections = relationship("Inspection", back_populates="building")


class InspectionType(BaseModel):
    """Inspection types lookup."""
    
    __tablename__ = "inspection_types"
    
    type_name = Column(String(150), unique=True, nullable=False)
    type_name_hebrew = Column(String(150), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)


class Regulator(BaseModel):
    """Regulatory bodies lookup."""
    
    __tablename__ = "regulators"
    
    regulator_name = Column(String(100), unique=True, nullable=False)
    regulator_type = Column(String(50))
    is_active = Column(Boolean, default=True)


class AuditLog(BaseModel):
    """Audit logging for compliance."""
    
    __tablename__ = "audit_logs"
    
    table_name = Column(String(50), nullable=False, index=True)
    record_id = Column(Integer, nullable=False, index=True)
    action = Column(String(20), nullable=False)
    field_name = Column(String(100))
    old_value = Column(Text)
    new_value = Column(Text)
    user_id = Column(String(100), nullable=False)
    ip_address = Column(String(45))
    
    __table_args__ = (
        Index("idx_audit_table_record", "table_name", "record_id"),
        Index("idx_audit_user_action", "user_id", "action"),
    )