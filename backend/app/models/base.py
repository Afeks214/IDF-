"""
Base model with common fields and Hebrew text support for IDF Testing Infrastructure.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, event
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.sql import func


@as_declarative()
class Base:
    """Base model class with common fields and Hebrew text support."""
    
    id: Any
    __name__: str
    
    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


class TimestampMixin:
    """Mixin for timestamp fields."""
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp"
    )


class HebrewTextMixin:
    """Mixin for Hebrew text handling utilities."""
    
    @staticmethod
    def sanitize_hebrew_text(text: Optional[str]) -> Optional[str]:
        """
        Sanitize Hebrew text for database storage.
        
        Args:
            text: Input text that may contain Hebrew characters
            
        Returns:
            Sanitized text safe for database storage
        """
        if not text:
            return text
            
        # Remove common problematic characters that might cause encoding issues
        text = text.strip()
        
        # Replace problematic quotes and dashes
        replacements = {
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '–': '-',
            '—': '-',
            '…': '...',
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    @staticmethod
    def normalize_hebrew_text(text: Optional[str]) -> Optional[str]:
        """
        Normalize Hebrew text for consistent storage and search.
        
        Args:
            text: Hebrew text to normalize
            
        Returns:
            Normalized Hebrew text
        """
        if not text:
            return text
            
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Normalize Hebrew punctuation
        text = text.replace('״', '"')  # Hebrew double quote (geresh)
        text = text.replace('׳', "'")  # Hebrew single quote (gershayim)
        
        return text.strip()


class AuditMixin:
    """Mixin for audit trail functionality."""
    
    created_by = Column(
        String(100),
        nullable=True,
        comment="User who created this record"
    )
    
    updated_by = Column(
        String(100),
        nullable=True,
        comment="User who last updated this record"
    )
    
    version = Column(
        Integer,
        default=1,
        nullable=False,
        comment="Record version for optimistic locking"
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Soft delete flag"
    )
    
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Soft delete timestamp"
    )
    
    deleted_by = Column(
        String(100),
        nullable=True,
        comment="User who soft deleted this record"
    )


class BaseModel(Base, TimestampMixin, HebrewTextMixin, AuditMixin):
    """Base model class with all common functionality."""
    
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")
    
    def to_dict(self, exclude_fields: Optional[list] = None) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Args:
            exclude_fields: List of field names to exclude from the dictionary
            
        Returns:
            Dictionary representation of the model
        """
        exclude_fields = exclude_fields or []
        
        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude_fields:
                value = getattr(self, column.name)
                
                # Handle datetime objects
                if isinstance(value, datetime):
                    value = value.isoformat()
                
                result[column.name] = value
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseModel":
        """
        Create model instance from dictionary.
        
        Args:
            data: Dictionary with model data
            
        Returns:
            Model instance
        """
        # Filter data to only include valid column names
        valid_columns = {column.name for column in cls.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_columns}
        
        return cls(**filtered_data)
    
    def update_from_dict(self, data: Dict[str, Any], exclude_fields: Optional[list] = None) -> None:
        """
        Update model instance from dictionary.
        
        Args:
            data: Dictionary with updated data
            exclude_fields: List of field names to exclude from update
        """
        exclude_fields = exclude_fields or ["id", "created_at", "created_by"]
        valid_columns = {column.name for column in self.__table__.columns}
        
        for key, value in data.items():
            if key in valid_columns and key not in exclude_fields:
                # Apply Hebrew text sanitization if it's a text field
                if hasattr(self.__table__.columns[key].type, 'length') or isinstance(self.__table__.columns[key].type, Text):
                    if isinstance(value, str):
                        value = self.sanitize_hebrew_text(value)
                        value = self.normalize_hebrew_text(value)
                
                setattr(self, key, value)


# Event listeners for Hebrew text handling
@event.listens_for(BaseModel, 'before_insert', propagate=True)
@event.listens_for(BaseModel, 'before_update', propagate=True)
def sanitize_hebrew_before_save(mapper, connection, target):
    """Automatically sanitize Hebrew text before saving to database."""
    
    for column in target.__table__.columns:
        # Check if column is a text type
        if hasattr(column.type, 'length') or isinstance(column.type, Text):
            value = getattr(target, column.name)
            
            if isinstance(value, str) and value:
                # Apply Hebrew text sanitization
                sanitized = target.sanitize_hebrew_text(value)
                normalized = target.normalize_hebrew_text(sanitized)
                setattr(target, column.name, normalized)


