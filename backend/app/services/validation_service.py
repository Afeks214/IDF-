"""
Data validation service with Hebrew text sanitization for IDF Testing Infrastructure.
Ensures data integrity and proper Hebrew text handling.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel as PydanticBaseModel, validator, Field
from pydantic.validators import str_validator


class HebrewTextValidator:
    """Validator for Hebrew text with sanitization and normalization."""
    
    # Hebrew Unicode ranges
    HEBREW_BASIC = r'[\u0590-\u05FF]'  # Hebrew and Hebrew Presentation Forms
    HEBREW_EXTENDED = r'[\uFB1D-\uFB4F]'  # Hebrew Presentation Forms-A
    
    # Common Hebrew punctuation and symbols
    HEBREW_PUNCTUATION = r'[״׳]'  # Geresh and Gershayim
    
    # Allowed characters pattern (Hebrew + Latin + numbers + common punctuation)
    ALLOWED_PATTERN = re.compile(
        r'^[' +
        r'\u0590-\u05FF' +  # Hebrew
        r'\uFB1D-\uFB4F' +  # Hebrew Presentation Forms
        r'a-zA-Z' +         # Latin letters
        r'0-9' +            # Numbers
        r'\s' +             # Whitespace
        r'.,;:!?\-_()[]{}/"\'`~@#$%^&*+=<>|\\' +  # Common punctuation
        r']*$'
    )
    
    @classmethod
    def validate_hebrew_text(cls, value: str) -> str:
        """
        Validate and sanitize Hebrew text.
        
        Args:
            value: Input text string
            
        Returns:
            Sanitized and normalized Hebrew text
            
        Raises:
            ValueError: If text contains invalid characters
        """
        if not value:
            return value
        
        # Normalize Unicode
        normalized = unicodedata.normalize('NFC', value)
        
        # Check for disallowed characters
        if not cls.ALLOWED_PATTERN.match(normalized):
            raise ValueError("Text contains invalid characters")
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', normalized).strip()
        
        # Normalize Hebrew punctuation
        cleaned = cleaned.replace('״', '"')  # Hebrew double quote
        cleaned = cleaned.replace('׳', "'")  # Hebrew single quote
        
        # Remove common problematic characters
        problematic_chars = {
            '\u200e': '',  # Left-to-right mark
            '\u200f': '',  # Right-to-left mark
            '\u202a': '',  # Left-to-right embedding
            '\u202b': '',  # Right-to-left embedding
            '\u202c': '',  # Pop directional formatting
            '\u202d': '',  # Left-to-right override
            '\u202e': '',  # Right-to-left override
        }
        
        for char, replacement in problematic_chars.items():
            cleaned = cleaned.replace(char, replacement)
        
        return cleaned
    
    @classmethod
    def contains_hebrew(cls, value: str) -> bool:
        """Check if text contains Hebrew characters."""
        if not value:
            return False
        
        hebrew_pattern = re.compile(cls.HEBREW_BASIC + '|' + cls.HEBREW_EXTENDED)
        return bool(hebrew_pattern.search(value))
    
    @classmethod
    def get_text_direction(cls, value: str) -> str:
        """Determine text direction (RTL for Hebrew, LTR for others)."""
        if cls.contains_hebrew(value):
            return 'rtl'
        return 'ltr'


def hebrew_str_validator(v: Any) -> str:
    """Pydantic validator for Hebrew text fields."""
    if v is None:
        return v
    
    # Convert to string first
    str_v = str_validator(v)
    
    # Apply Hebrew validation
    return HebrewTextValidator.validate_hebrew_text(str_v)


class InspectionValidationSchema(PydanticBaseModel):
    """Validation schema for inspection data."""
    
    building_id: str = Field(..., min_length=1, max_length=10, description="Building identifier")
    building_manager: Optional[str] = Field(None, max_length=100, description="Building manager name")
    red_team: Optional[str] = Field(None, max_length=200, description="Red team members")
    inspection_type: str = Field(..., min_length=1, max_length=150, description="Type of inspection")
    inspection_leader: str = Field(..., min_length=1, max_length=100, description="Inspection leader")
    inspection_round: Optional[int] = Field(None, ge=1, le=4, description="Inspection round (1-4)")
    
    # Regulators
    regulator_1: Optional[str] = Field(None, max_length=100)
    regulator_2: Optional[str] = Field(None, max_length=100)
    regulator_3: Optional[str] = Field(None, max_length=100)
    regulator_4: Optional[str] = Field(None, max_length=100)
    
    # Dates
    execution_schedule: Optional[date] = Field(None, description="Execution date")
    target_completion: Optional[date] = Field(None, description="Target completion date")
    actual_completion: Optional[date] = Field(None, description="Actual completion date")
    
    # Flags
    coordinated_with_contractor: bool = Field(default=False)
    report_distributed: bool = Field(default=False)
    repeat_inspection: bool = Field(default=False)
    
    # Text fields
    defect_report_path: Optional[str] = Field(None, max_length=500)
    distribution_date: Optional[date] = None
    inspection_notes: Optional[str] = Field(None, max_length=10000)
    
    # Validators for Hebrew text fields
    _validate_building_manager = validator('building_manager', allow_reuse=True)(hebrew_str_validator)
    _validate_red_team = validator('red_team', allow_reuse=True)(hebrew_str_validator)
    _validate_inspection_type = validator('inspection_type', allow_reuse=True)(hebrew_str_validator)
    _validate_inspection_leader = validator('inspection_leader', allow_reuse=True)(hebrew_str_validator)
    _validate_regulator_1 = validator('regulator_1', allow_reuse=True)(hebrew_str_validator)
    _validate_regulator_2 = validator('regulator_2', allow_reuse=True)(hebrew_str_validator)
    _validate_regulator_3 = validator('regulator_3', allow_reuse=True)(hebrew_str_validator)
    _validate_regulator_4 = validator('regulator_4', allow_reuse=True)(hebrew_str_validator)
    _validate_inspection_notes = validator('inspection_notes', allow_reuse=True)(hebrew_str_validator)
    
    @validator('target_completion')
    def validate_target_after_execution(cls, v, values):
        """Ensure target completion is after execution schedule."""
        if v and 'execution_schedule' in values and values['execution_schedule']:
            if v < values['execution_schedule']:
                raise ValueError('Target completion must be after execution schedule')
        return v
    
    @validator('actual_completion')
    def validate_actual_after_execution(cls, v, values):
        """Ensure actual completion is after execution schedule."""
        if v and 'execution_schedule' in values and values['execution_schedule']:
            if v < values['execution_schedule']:
                raise ValueError('Actual completion must be after execution schedule')
        return v
    
    @validator('building_id')
    def validate_building_id_format(cls, v):
        """Validate building ID format."""
        if not re.match(r'^[A-Z0-9]+$', v.upper()):
            raise ValueError('Building ID must contain only letters and numbers')
        return v.upper()


class BuildingValidationSchema(PydanticBaseModel):
    """Validation schema for building data."""
    
    building_code: str = Field(..., min_length=1, max_length=10)
    building_name: Optional[str] = Field(None, max_length=200)
    manager_name: Optional[str] = Field(None, max_length=100)
    is_active: bool = Field(default=True)
    
    # Hebrew text validators
    _validate_building_name = validator('building_name', allow_reuse=True)(hebrew_str_validator)
    _validate_manager_name = validator('manager_name', allow_reuse=True)(hebrew_str_validator)
    
    @validator('building_code')
    def validate_building_code(cls, v):
        """Validate building code format."""
        if not re.match(r'^[A-Z0-9]+$', v.upper()):
            raise ValueError('Building code must contain only letters and numbers')
        return v.upper()


class ValidationService:
    """Service for comprehensive data validation with Hebrew support."""
    
    def __init__(self):
        self.text_validator = HebrewTextValidator()
    
    def validate_inspection_data(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validate inspection data and return cleaned data with errors.
        
        Args:
            data: Raw inspection data
            
        Returns:
            Tuple of (validated_data, validation_errors)
        """
        errors = []
        
        try:
            validated = InspectionValidationSchema(**data)
            return validated.dict(exclude_none=True), errors
        except Exception as e:
            # Parse validation errors
            if hasattr(e, 'errors'):
                for error in e.errors():
                    field = ' -> '.join(str(loc) for loc in error['loc'])
                    message = error['msg']
                    errors.append(f"{field}: {message}")
            else:
                errors.append(str(e))
            
            # Return original data with errors
            return data, errors
    
    def validate_building_data(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validate building data and return cleaned data with errors.
        
        Args:
            data: Raw building data
            
        Returns:
            Tuple of (validated_data, validation_errors)
        """
        errors = []
        
        try:
            validated = BuildingValidationSchema(**data)
            return validated.dict(exclude_none=True), errors
        except Exception as e:
            # Parse validation errors
            if hasattr(e, 'errors'):
                for error in e.errors():
                    field = ' -> '.join(str(loc) for loc in error['loc'])
                    message = error['msg']
                    errors.append(f"{field}: {message}")
            else:
                errors.append(str(e))
            
            return data, errors
    
    def sanitize_hebrew_text(self, text: str) -> str:
        """Sanitize Hebrew text using the text validator."""
        return self.text_validator.validate_hebrew_text(text)
    
    def validate_file_upload(self, filename: str, file_size: int, file_content: bytes) -> List[str]:
        """
        Validate file uploads for defect reports and attachments.
        
        Args:
            filename: Original filename
            file_size: File size in bytes
            file_content: File content
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check filename
        if not filename:
            errors.append("Filename is required")
        elif len(filename) > 255:
            errors.append("Filename is too long (max 255 characters)")
        
        # Check file extension
        allowed_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.txt'}
        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        if file_ext not in allowed_extensions:
            errors.append(f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}")
        
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            errors.append(f"File size too large (max {max_size // 1024 // 1024}MB)")
        
        # Check for malicious content (basic check)
        if file_content:
            # Check for common malicious patterns
            malicious_patterns = [
                b'<script',
                b'javascript:',
                b'eval(',
                b'document.cookie',
                b'window.location'
            ]
            
            content_lower = file_content.lower()
            for pattern in malicious_patterns:
                if pattern in content_lower:
                    errors.append("File contains potentially malicious content")
                    break
        
        return errors
    
    def validate_date_range(self, start_date: date, end_date: date) -> List[str]:
        """Validate date ranges for queries and reports."""
        errors = []
        
        if start_date and end_date:
            if start_date > end_date:
                errors.append("Start date must be before end date")
            
            # Check for reasonable date range (not more than 5 years)
            max_range_days = 5 * 365
            if (end_date - start_date).days > max_range_days:
                errors.append("Date range is too large (max 5 years)")
        
        # Check dates are not too far in the future
        today = date.today()
        future_limit = today.replace(year=today.year + 2)
        
        if start_date and start_date > future_limit:
            errors.append("Start date is too far in the future")
        
        if end_date and end_date > future_limit:
            errors.append("End date is too far in the future")
        
        return errors
    
    def validate_search_query(self, query: str) -> Tuple[str, List[str]]:
        """
        Validate and sanitize search queries.
        
        Args:
            query: Search query string
            
        Returns:
            Tuple of (sanitized_query, errors)
        """
        errors = []
        
        if not query:
            return "", ["Search query is required"]
        
        # Length check
        if len(query) > 500:
            errors.append("Search query is too long (max 500 characters)")
            query = query[:500]
        
        # Sanitize the query
        try:
            sanitized = self.text_validator.validate_hebrew_text(query)
        except ValueError as e:
            errors.append(f"Invalid characters in search query: {str(e)}")
            # Remove invalid characters and try again
            sanitized = re.sub(r'[^\u0590-\u05FF\uFB1D-\uFB4Fa-zA-Z0-9\s.,;:!?\-_()[\]{}/"\'`~@#$%^&*+=<>|\\]', '', query)
        
        # Check for potential injection attacks
        injection_patterns = [
            r'--',  # SQL comment
            r'/\*.*\*/',  # SQL block comment
            r'\bunion\b',  # SQL UNION
            r'\bselect\b',  # SQL SELECT
            r'\binsert\b',  # SQL INSERT
            r'\bupdate\b',  # SQL UPDATE
            r'\bdelete\b',  # SQL DELETE
            r'\bdrop\b',  # SQL DROP
        ]
        
        query_lower = sanitized.lower()
        for pattern in injection_patterns:
            if re.search(pattern, query_lower):
                errors.append("Search query contains potentially dangerous content")
                break
        
        return sanitized, errors
    
    def get_validation_summary(self, validation_results: List[Tuple[bool, List[str]]]) -> Dict[str, Any]:
        """
        Generate summary of validation results.
        
        Args:
            validation_results: List of (success, errors) tuples
            
        Returns:
            Validation summary
        """
        total_items = len(validation_results)
        successful_items = sum(1 for success, _ in validation_results if success)
        failed_items = total_items - successful_items
        
        all_errors = []
        for success, errors in validation_results:
            if not success:
                all_errors.extend(errors)
        
        error_counts = {}
        for error in all_errors:
            error_type = error.split(':')[0] if ':' in error else error
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            "total_items": total_items,
            "successful_items": successful_items,
            "failed_items": failed_items,
            "success_rate": (successful_items / total_items * 100) if total_items > 0 else 0,
            "total_errors": len(all_errors),
            "error_types": error_counts,
            "all_errors": all_errors
        }