"""
Audit logging service for military compliance requirements.
Tracks all data changes with full Hebrew text support.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date
import json
import hashlib
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import event, inspect
from sqlalchemy.orm import InstanceState

from ..models.core import AuditLog
from ..models.base import BaseModel


@dataclass
class AuditContext:
    """Context information for audit operations."""
    user_id: str
    user_role: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    action_reason: Optional[str] = None


class AuditService:
    """Service for comprehensive audit logging with Hebrew support."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._audit_context: Optional[AuditContext] = None
    
    def set_audit_context(self, context: AuditContext):
        """Set audit context for current operations."""
        self._audit_context = context
    
    async def log_action(
        self,
        table_name: str,
        record_id: int,
        action: str,
        field_name: Optional[str] = None,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        context: Optional[AuditContext] = None
    ) -> AuditLog:
        """
        Log an audit action.
        
        Args:
            table_name: Name of the affected table
            record_id: ID of the affected record
            action: Action performed (CREATE, UPDATE, DELETE, etc.)
            field_name: Name of the changed field (for updates)
            old_value: Previous value
            new_value: New value
            context: Audit context (uses current context if not provided)
            
        Returns:
            Created audit log entry
        """
        audit_context = context or self._audit_context
        
        if not audit_context:
            raise ValueError("Audit context is required for logging actions")
        
        # Serialize values for storage
        old_value_str = self._serialize_value(old_value) if old_value is not None else None
        new_value_str = self._serialize_value(new_value) if new_value is not None else None
        
        audit_log = AuditLog(
            table_name=table_name,
            record_id=record_id,
            action=action.upper(),
            field_name=field_name,
            old_value=old_value_str,
            new_value=new_value_str,
            user_id=audit_context.user_id,
            ip_address=audit_context.ip_address,
            created_by=audit_context.user_id
        )
        
        # Add metadata if available
        if hasattr(audit_log, 'metadata'):
            metadata = {
                "user_role": audit_context.user_role,
                "user_agent": audit_context.user_agent,
                "session_id": audit_context.session_id,
                "action_reason": audit_context.action_reason,
                "timestamp_iso": datetime.utcnow().isoformat()
            }
            audit_log.metadata = metadata
        
        self.session.add(audit_log)
        await self.session.flush()
        return audit_log
    
    async def log_entity_changes(
        self,
        entity: BaseModel,
        action: str,
        changed_fields: Optional[Dict[str, tuple]] = None,
        context: Optional[AuditContext] = None
    ):
        """
        Log changes to an entity with field-level detail.
        
        Args:
            entity: The entity that was changed
            action: Action performed
            changed_fields: Dict of field_name -> (old_value, new_value)
            context: Audit context
        """
        table_name = entity.__tablename__
        record_id = entity.id
        
        if action.upper() in ['CREATE', 'DELETE']:
            # For create/delete, log the entire action
            await self.log_action(
                table_name=table_name,
                record_id=record_id,
                action=action,
                context=context
            )
        elif action.upper() == 'UPDATE' and changed_fields:
            # For updates, log each changed field
            for field_name, (old_value, new_value) in changed_fields.items():
                await self.log_action(
                    table_name=table_name,
                    record_id=record_id,
                    action=action,
                    field_name=field_name,
                    old_value=old_value,
                    new_value=new_value,
                    context=context
                )
    
    async def get_audit_trail(
        self,
        table_name: Optional[str] = None,
        record_id: Optional[int] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail with filters.
        
        Returns:
            List of audit log entries with enriched information
        """
        from ..services.repository import AuditRepository
        
        audit_repo = AuditRepository(self.session)
        
        # Build filters
        filters = {}
        if table_name:
            filters['table_name'] = table_name
        if record_id:
            filters['record_id'] = record_id
        if user_id:
            filters['user_id'] = user_id
        if action:
            filters['action'] = action.upper()
        
        # Get audit logs
        audit_logs = await audit_repo.get_audit_trail(
            table_name=table_name,
            record_id=record_id,
            user_id=user_id,
            skip=skip,
            limit=limit
        )
        
        # Enrich with additional information
        enriched_logs = []
        for log in audit_logs:
            log_dict = log.to_dict()
            
            # Add Hebrew-friendly formatting
            log_dict['action_hebrew'] = self._get_hebrew_action(log.action)
            log_dict['formatted_timestamp'] = self._format_hebrew_timestamp(log.created_at)
            
            # Parse and format values
            if log.old_value:
                log_dict['old_value_formatted'] = self._format_audit_value(log.old_value)
            if log.new_value:
                log_dict['new_value_formatted'] = self._format_audit_value(log.new_value)
            
            enriched_logs.append(log_dict)
        
        return enriched_logs
    
    async def get_user_activity_summary(
        self,
        user_id: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get summary of user's audit activity."""
        
        from sqlalchemy import func, and_
        from sqlalchemy.future import select
        
        # Base filter
        filters = [AuditLog.user_id == user_id]
        
        if date_from:
            filters.append(AuditLog.created_at >= date_from)
        if date_to:
            filters.append(AuditLog.created_at <= date_to)
        
        # Get action counts
        action_query = select(
            AuditLog.action,
            func.count(AuditLog.id).label('count')
        ).where(and_(*filters)).group_by(AuditLog.action)
        
        action_result = await self.session.execute(action_query)
        action_counts = {row[0]: row[1] for row in action_result.all()}
        
        # Get table counts
        table_query = select(
            AuditLog.table_name,
            func.count(AuditLog.id).label('count')
        ).where(and_(*filters)).group_by(AuditLog.table_name)
        
        table_result = await self.session.execute(table_query)
        table_counts = {row[0]: row[1] for row in table_result.all()}
        
        # Get total count
        total_query = select(func.count(AuditLog.id)).where(and_(*filters))
        total_result = await self.session.execute(total_query)
        total_actions = total_result.scalar()
        
        return {
            "user_id": user_id,
            "total_actions": total_actions,
            "action_counts": action_counts,
            "table_counts": table_counts,
            "date_range": {
                "from": date_from.isoformat() if date_from else None,
                "to": date_to.isoformat() if date_to else None
            }
        }
    
    async def generate_compliance_report(
        self,
        date_from: date,
        date_to: date,
        include_details: bool = False
    ) -> Dict[str, Any]:
        """
        Generate compliance report for military audit requirements.
        
        Args:
            date_from: Start date for report
            date_to: End date for report
            include_details: Whether to include detailed audit entries
            
        Returns:
            Comprehensive compliance report
        """
        from sqlalchemy import func, and_
        from sqlalchemy.future import select
        
        filters = [
            AuditLog.created_at >= date_from,
            AuditLog.created_at <= date_to
        ]
        
        # Overall statistics
        total_query = select(func.count(AuditLog.id)).where(and_(*filters))
        total_result = await self.session.execute(total_query)
        total_actions = total_result.scalar()
        
        # User activity
        user_query = select(
            AuditLog.user_id,
            func.count(AuditLog.id).label('action_count'),
            func.min(AuditLog.created_at).label('first_action'),
            func.max(AuditLog.created_at).label('last_action')
        ).where(and_(*filters)).group_by(AuditLog.user_id).order_by(text('action_count DESC'))
        
        user_result = await self.session.execute(user_query)
        user_activity = [
            {
                "user_id": row[0],
                "action_count": row[1],
                "first_action": row[2].isoformat(),
                "last_action": row[3].isoformat()
            }
            for row in user_result.all()
        ]
        
        # Action type distribution
        action_query = select(
            AuditLog.action,
            func.count(AuditLog.id).label('count')
        ).where(and_(*filters)).group_by(AuditLog.action)
        
        action_result = await self.session.execute(action_query)
        action_distribution = {row[0]: row[1] for row in action_result.all()}
        
        # Table activity
        table_query = select(
            AuditLog.table_name,
            func.count(AuditLog.id).label('count')
        ).where(and_(*filters)).group_by(AuditLog.table_name)
        
        table_result = await self.session.execute(table_query)
        table_activity = {row[0]: row[1] for row in table_result.all()}
        
        report = {
            "report_period": {
                "from": date_from.isoformat(),
                "to": date_to.isoformat(),
                "generated_at": datetime.utcnow().isoformat()
            },
            "summary": {
                "total_audit_entries": total_actions,
                "unique_users": len(user_activity),
                "action_types": len(action_distribution),
                "affected_tables": len(table_activity)
            },
            "user_activity": user_activity,
            "action_distribution": action_distribution,
            "table_activity": table_activity
        }
        
        if include_details:
            # Get detailed audit entries
            detailed_logs = await self.get_audit_trail(
                date_from=date_from,
                date_to=date_to,
                limit=1000  # Limit for performance
            )
            report["detailed_entries"] = detailed_logs
        
        return report
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize a value for audit storage."""
        if value is None:
            return "NULL"
        elif isinstance(value, (str, int, float, bool)):
            return str(value)
        elif isinstance(value, (date, datetime)):
            return value.isoformat()
        else:
            # For complex objects, use JSON serialization
            try:
                return json.dumps(value, default=str, ensure_ascii=False)
            except:
                return str(value)
    
    def _format_audit_value(self, value_str: str) -> str:
        """Format audit value for display."""
        if not value_str or value_str == "NULL":
            return "ריק"  # Hebrew for "empty"
        
        # Try to parse as JSON for complex values
        try:
            parsed = json.loads(value_str)
            if isinstance(parsed, dict):
                return f"אובייקט עם {len(parsed)} שדות"  # "Object with N fields"
            elif isinstance(parsed, list):
                return f"רשימה עם {len(parsed)} פריטים"  # "List with N items"
        except:
            pass
        
        # Truncate long values
        if len(value_str) > 100:
            return value_str[:97] + "..."
        
        return value_str
    
    def _get_hebrew_action(self, action: str) -> str:
        """Get Hebrew translation for audit action."""
        translations = {
            'CREATE': 'יצירה',
            'UPDATE': 'עדכון',
            'DELETE': 'מחיקה',
            'LOGIN': 'כניסה למערכת',
            'LOGOUT': 'יציאה מהמערכת',
            'VIEW': 'צפייה',
            'EXPORT': 'ייצוא',
            'IMPORT': 'ייבוא',
            'APPROVE': 'אישור',
            'REJECT': 'דחייה'
        }
        return translations.get(action.upper(), action)
    
    def _format_hebrew_timestamp(self, timestamp: datetime) -> str:
        """Format timestamp for Hebrew display."""
        # Convert to Israel timezone if needed
        formatted = timestamp.strftime("%d/%m/%Y %H:%M:%S")
        return formatted


# SQLAlchemy event listeners for automatic audit logging
class AutoAuditMixin:
    """Mixin to enable automatic audit logging for models."""
    
    _audit_service: Optional[AuditService] = None
    
    @classmethod
    def set_audit_service(cls, audit_service: AuditService):
        """Set the audit service for automatic logging."""
        cls._audit_service = audit_service


def setup_auto_audit_listeners():
    """Set up SQLAlchemy event listeners for automatic audit logging."""
    
    @event.listens_for(BaseModel, 'after_insert', propagate=True)
    def log_after_insert(mapper, connection, target):
        """Log entity creation."""
        if hasattr(target, '_audit_service') and target._audit_service:
            # This would be called in an async context, so we'd need to handle differently
            pass
    
    @event.listens_for(BaseModel, 'after_update', propagate=True)
    def log_after_update(mapper, connection, target):
        """Log entity updates."""
        if hasattr(target, '_audit_service') and target._audit_service:
            # Track changed fields
            state: InstanceState = inspect(target)
            changes = {}
            
            for attr in state.attrs:
                hist = attr.load_history()
                if hist.has_changes():
                    old_value = hist.deleted[0] if hist.deleted else None
                    new_value = hist.added[0] if hist.added else None
                    changes[attr.key] = (old_value, new_value)
            
            # This would be called in an async context, so we'd need to handle differently
            pass
    
    @event.listens_for(BaseModel, 'after_delete', propagate=True)
    def log_after_delete(mapper, connection, target):
        """Log entity deletion."""
        if hasattr(target, '_audit_service') and target._audit_service:
            # This would be called in an async context, so we'd need to handle differently
            pass


# Import text for SQL ordering
from sqlalchemy import text