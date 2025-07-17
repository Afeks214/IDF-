"""
Repository pattern implementation for data access layer.
Provides CRUD operations with Hebrew text support and validation.
"""

from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from abc import ABC, abstractmethod
from datetime import date, datetime

from sqlalchemy import and_, or_, func, desc, asc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from ..models.base import BaseModel
from ..models.core import Inspection, Building, InspectionType, Regulator, AuditLog, InspectionStatus

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType], ABC):
    """Base repository with common CRUD operations."""
    
    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model
    
    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get entity by ID."""
        return await self.session.get(self.model, id)
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all entities with pagination."""
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def create(self, obj_in: Dict[str, Any], user_id: Optional[str] = None) -> ModelType:
        """Create new entity."""
        obj_data = dict(obj_in)
        if user_id and hasattr(self.model, 'created_by'):
            obj_data['created_by'] = user_id
        
        db_obj = self.model(**obj_data)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj
    
    async def update(self, db_obj: ModelType, obj_in: Dict[str, Any], user_id: Optional[str] = None) -> ModelType:
        """Update existing entity."""
        update_data = dict(obj_in)
        if user_id and hasattr(self.model, 'updated_by'):
            update_data['updated_by'] = user_id
        
        db_obj.update_from_dict(update_data)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj
    
    async def delete(self, id: int) -> bool:
        """Delete entity by ID."""
        db_obj = await self.get_by_id(id)
        if db_obj:
            await self.session.delete(db_obj)
            return True
        return False
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filters."""
        query = select(func.count(self.model.id))
        if filters:
            query = self._apply_filters(query, filters)
        
        result = await self.session.execute(query)
        return result.scalar()
    
    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply filters to query."""
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                if isinstance(value, list):
                    query = query.where(getattr(self.model, key).in_(value))
                else:
                    query = query.where(getattr(self.model, key) == value)
        return query


class InspectionRepository(BaseRepository[Inspection]):
    """Repository for inspection operations with Hebrew search support."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Inspection)
    
    async def get_by_building(self, building_id: str, skip: int = 0, limit: int = 100) -> List[Inspection]:
        """Get inspections by building ID."""
        result = await self.session.execute(
            select(Inspection)
            .where(Inspection.building_id == building_id)
            .options(selectinload(Inspection.building))
            .offset(skip)
            .limit(limit)
            .order_by(desc(Inspection.created_at))
        )
        return result.scalars().all()
    
    async def get_by_status(self, status: InspectionStatus, skip: int = 0, limit: int = 100) -> List[Inspection]:
        """Get inspections by status."""
        result = await self.session.execute(
            select(Inspection)
            .where(Inspection.status == status)
            .options(selectinload(Inspection.building))
            .offset(skip)
            .limit(limit)
            .order_by(desc(Inspection.execution_schedule))
        )
        return result.scalars().all()
    
    async def search_hebrew_text(self, search_term: str, skip: int = 0, limit: int = 100) -> List[Inspection]:
        """Search inspections using Hebrew text."""
        # Use PostgreSQL full-text search with Hebrew support
        search_vector = func.to_tsvector('hebrew', 
            func.coalesce(Inspection.inspection_type, '') + ' ' +
            func.coalesce(Inspection.inspection_leader, '') + ' ' +
            func.coalesce(Inspection.building_manager, '') + ' ' +
            func.coalesce(Inspection.inspection_notes, '')
        )
        
        search_query = func.plainto_tsquery('hebrew', search_term)
        
        result = await self.session.execute(
            select(Inspection)
            .where(search_vector.op('@@')(search_query))
            .options(selectinload(Inspection.building))
            .offset(skip)
            .limit(limit)
            .order_by(desc(func.ts_rank(search_vector, search_query)))
        )
        return result.scalars().all()
    
    async def get_overdue_inspections(self) -> List[Inspection]:
        """Get overdue inspections."""
        today = date.today()
        result = await self.session.execute(
            select(Inspection)
            .where(
                and_(
                    Inspection.target_completion < today,
                    Inspection.status.not_in([InspectionStatus.COMPLETED, InspectionStatus.CANCELLED])
                )
            )
            .options(selectinload(Inspection.building))
            .order_by(asc(Inspection.target_completion))
        )
        return result.scalars().all()
    
    async def get_upcoming_inspections(self, days_ahead: int = 7) -> List[Inspection]:
        """Get inspections due in the next N days."""
        today = date.today()
        future_date = date.today() + timedelta(days=days_ahead)
        
        result = await self.session.execute(
            select(Inspection)
            .where(
                and_(
                    Inspection.execution_schedule.between(today, future_date),
                    Inspection.status == InspectionStatus.SCHEDULED
                )
            )
            .options(selectinload(Inspection.building))
            .order_by(asc(Inspection.execution_schedule))
        )
        return result.scalars().all()
    
    async def get_inspection_statistics(self) -> Dict[str, Any]:
        """Get inspection statistics for dashboard."""
        # Total counts by status
        status_counts = {}
        for status in InspectionStatus:
            result = await self.session.execute(
                select(func.count(Inspection.id))
                .where(Inspection.status == status)
            )
            status_counts[status.value] = result.scalar()
        
        # Overdue count
        today = date.today()
        overdue_result = await self.session.execute(
            select(func.count(Inspection.id))
            .where(
                and_(
                    Inspection.target_completion < today,
                    Inspection.status.not_in([InspectionStatus.COMPLETED, InspectionStatus.CANCELLED])
                )
            )
        )
        overdue_count = overdue_result.scalar()
        
        # Recent completions (last 30 days)
        thirty_days_ago = date.today() - timedelta(days=30)
        recent_result = await self.session.execute(
            select(func.count(Inspection.id))
            .where(
                and_(
                    Inspection.actual_completion >= thirty_days_ago,
                    Inspection.status == InspectionStatus.COMPLETED
                )
            )
        )
        recent_completions = recent_result.scalar()
        
        return {
            "status_counts": status_counts,
            "overdue_count": overdue_count,
            "recent_completions": recent_completions,
            "total_inspections": sum(status_counts.values())
        }
    
    async def get_filtered_inspections(
        self, 
        filters: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 100,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[Inspection]:
        """Get filtered inspections with sorting."""
        
        query = select(Inspection).options(selectinload(Inspection.building))
        
        # Apply filters
        if "building_id" in filters and filters["building_id"]:
            query = query.where(Inspection.building_id == filters["building_id"])
        
        if "status" in filters and filters["status"]:
            query = query.where(Inspection.status == filters["status"])
        
        if "inspection_type" in filters and filters["inspection_type"]:
            query = query.where(Inspection.inspection_type.ilike(f"%{filters['inspection_type']}%"))
        
        if "leader" in filters and filters["leader"]:
            query = query.where(Inspection.inspection_leader.ilike(f"%{filters['leader']}%"))
        
        if "date_from" in filters and filters["date_from"]:
            query = query.where(Inspection.execution_schedule >= filters["date_from"])
        
        if "date_to" in filters and filters["date_to"]:
            query = query.where(Inspection.execution_schedule <= filters["date_to"])
        
        if "regulators" in filters and filters["regulators"]:
            regulator_filter = or_(
                Inspection.regulator_1.in_(filters["regulators"]),
                Inspection.regulator_2.in_(filters["regulators"]),
                Inspection.regulator_3.in_(filters["regulators"]),
                Inspection.regulator_4.in_(filters["regulators"])
            )
            query = query.where(regulator_filter)
        
        # Apply sorting
        sort_column = getattr(Inspection, sort_by, Inspection.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()


class BuildingRepository(BaseRepository[Building]):
    """Repository for building operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Building)
    
    async def get_by_code(self, building_code: str) -> Optional[Building]:
        """Get building by code."""
        result = await self.session.execute(
            select(Building).where(Building.building_code == building_code)
        )
        return result.scalar_one_or_none()
    
    async def get_active_buildings(self) -> List[Building]:
        """Get all active buildings."""
        result = await self.session.execute(
            select(Building)
            .where(Building.is_active == True)
            .order_by(Building.building_code)
        )
        return result.scalars().all()
    
    async def get_buildings_with_stats(self) -> List[Dict[str, Any]]:
        """Get buildings with inspection statistics."""
        buildings = await self.get_active_buildings()
        
        result = []
        for building in buildings:
            # Get inspection counts by status
            status_counts = {}
            for status in InspectionStatus:
                count_result = await self.session.execute(
                    select(func.count(Inspection.id))
                    .where(
                        and_(
                            Inspection.building_id == building.building_code,
                            Inspection.status == status
                        )
                    )
                )
                status_counts[status.value] = count_result.scalar()
            
            building_data = building.to_dict()
            building_data["inspection_stats"] = status_counts
            building_data["total_inspections"] = sum(status_counts.values())
            
            result.append(building_data)
        
        return result


class AuditRepository(BaseRepository[AuditLog]):
    """Repository for audit log operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, AuditLog)
    
    async def log_action(
        self,
        table_name: str,
        record_id: int,
        action: str,
        user_id: str,
        field_name: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Create audit log entry."""
        audit_data = {
            "table_name": table_name,
            "record_id": record_id,
            "action": action,
            "user_id": user_id,
            "field_name": field_name,
            "old_value": old_value,
            "new_value": new_value,
            "ip_address": ip_address
        }
        
        return await self.create(audit_data)
    
    async def get_audit_trail(
        self,
        table_name: Optional[str] = None,
        record_id: Optional[int] = None,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get audit trail with filters."""
        
        query = select(AuditLog).order_by(desc(AuditLog.created_at))
        
        if table_name:
            query = query.where(AuditLog.table_name == table_name)
        
        if record_id:
            query = query.where(AuditLog.record_id == record_id)
        
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        
        query = query.offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()


# Repository factory for dependency injection
class RepositoryFactory:
    """Factory for creating repository instances."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @property
    def inspections(self) -> InspectionRepository:
        return InspectionRepository(self.session)
    
    @property
    def buildings(self) -> BuildingRepository:
        return BuildingRepository(self.session)
    
    @property
    def audit(self) -> AuditRepository:
        return AuditRepository(self.session)


# Import timedelta for date calculations
from datetime import timedelta