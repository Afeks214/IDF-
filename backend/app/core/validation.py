#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Input Validation and Sanitization Framework
Military-Grade Security for IDF Testing Infrastructure
"""

import re
import html
import unicodedata
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import validators
import structlog
from pydantic import BaseModel, validator, ValidationError
import bleach

logger = structlog.get_logger()


class ValidationError(Exception):
    """Custom validation error"""
    pass


class SanitizationConfig:
    """Configuration for sanitization rules"""
    
    # Allowed HTML tags (very restrictive)
    ALLOWED_TAGS = ['b', 'i', 'em', 'strong', 'p', 'br']
    
    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {}
    
    # Maximum string lengths
    MAX_STRING_LENGTH = 10000
    MAX_TEXT_LENGTH = 100000
    MAX_FILENAME_LENGTH = 255
    
    # Regex patterns for validation
    PATTERNS = {
        'username': r'^[a-zA-Z0-9_.-]{3,50}$',
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'phone': r'^\+?[1-9]\d{1,14}$',
        'ip_address': r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$',
        'ipv6_address': r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$',
        'url': r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$',
        'filename': r'^[a-zA-Z0-9._\-\(\)\[\] ]+$',
        'hex_color': r'^#[0-9a-fA-F]{6}$',
        'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        'hebrew_text': r'^[\u0590-\u05FF\s\d\p{P}a-zA-Z]*$',
    }


class InputSanitizer:
    """Advanced input sanitization utilities"""
    
    @staticmethod
    def sanitize_string(
        value: str,
        max_length: Optional[int] = None,
        strip_html: bool = True,
        normalize_unicode: bool = True,
        remove_control_chars: bool = True
    ) -> str:
        """
        Comprehensive string sanitization
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Normalize Unicode
        if normalize_unicode:
            value = unicodedata.normalize('NFKC', value)
        
        # Remove control characters (except common whitespace)
        if remove_control_chars:
            value = ''.join(char for char in value if unicodedata.category(char)[0] != 'C' or char in '\t\n\r ')
        
        # Strip/sanitize HTML
        if strip_html:
            value = bleach.clean(
                value,
                tags=SanitizationConfig.ALLOWED_TAGS,
                attributes=SanitizationConfig.ALLOWED_ATTRIBUTES,
                strip=True
            )
        
        # Limit length
        if max_length:
            value = value[:max_length]
        
        return value.strip()
    
    @staticmethod
    def sanitize_html(value: str, allowed_tags: Optional[List[str]] = None) -> str:
        """
        Sanitize HTML content
        """
        if not isinstance(value, str):
            value = str(value)
        
        tags = allowed_tags or SanitizationConfig.ALLOWED_TAGS
        
        return bleach.clean(
            value,
            tags=tags,
            attributes=SanitizationConfig.ALLOWED_ATTRIBUTES,
            strip=True
        )
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename for secure file operations
        """
        if not filename:
            raise ValidationError("Filename cannot be empty")
        
        # Remove path separators
        filename = filename.replace('/', '').replace('\\', '')
        
        # Remove dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\x00']
        for char in dangerous_chars:
            filename = filename.replace(char, '')
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Check for reserved names (Windows)
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        
        base_name = filename.split('.')[0].upper()
        if base_name in reserved_names:
            filename = f"file_{filename}"
        
        # Limit length
        if len(filename) > SanitizationConfig.MAX_FILENAME_LENGTH:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name_length = SanitizationConfig.MAX_FILENAME_LENGTH - len(ext) - 1
            filename = f"{name[:max_name_length]}.{ext}" if ext else name[:SanitizationConfig.MAX_FILENAME_LENGTH]
        
        if not filename:
            raise ValidationError("Invalid filename after sanitization")
        
        return filename
    
    @staticmethod
    def sanitize_hebrew_text(text: str) -> str:
        """
        Sanitize Hebrew text with special handling
        """
        if not text:
            return text
        
        # Basic sanitization
        text = InputSanitizer.sanitize_string(text)
        
        # Hebrew-specific character replacements
        replacements = {
            '״': '"',  # Hebrew double quote (geresh)
            '׳': "'",  # Hebrew single quote (gershayim)
            '־': '-',  # Hebrew hyphen (maqaf)
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    @staticmethod
    def escape_sql_like(value: str) -> str:
        """
        Escape special characters for SQL LIKE queries
        """
        return value.replace('%', '\\%').replace('_', '\\_').replace('\\', '\\\\')


class InputValidator:
    """Comprehensive input validation utilities"""
    
    @staticmethod
    def validate_email(email: str, strict: bool = True) -> bool:
        """
        Validate email address
        """
        try:
            email = email.strip().lower()
            
            if strict:
                # Use validators library for strict validation
                return validators.email(email) is True
            else:
                # Simple regex validation
                pattern = SanitizationConfig.PATTERNS['email']
                return re.match(pattern, email) is not None
                
        except Exception:
            return False
    
    @staticmethod
    def validate_phone(phone: str, international: bool = True) -> bool:
        """
        Validate phone number
        """
        try:
            # Remove common separators
            cleaned = re.sub(r'[-\s\(\)]', '', phone)
            
            if international:
                # International format validation
                pattern = SanitizationConfig.PATTERNS['phone']
                return re.match(pattern, cleaned) is not None
            else:
                # Simple numeric validation
                return cleaned.isdigit() and 7 <= len(cleaned) <= 15
                
        except Exception:
            return False
    
    @staticmethod
    def validate_url(url: str, schemes: Optional[List[str]] = None) -> bool:
        """
        Validate URL
        """
        try:
            schemes = schemes or ['http', 'https']
            
            # Use validators library
            if validators.url(url):
                # Check scheme
                for scheme in schemes:
                    if url.startswith(f"{scheme}://"):
                        return True
                        
        except Exception:
            pass
            
        return False
    
    @staticmethod
    def validate_ip_address(ip: str, version: Optional[int] = None) -> bool:
        """
        Validate IP address
        """
        try:
            import ipaddress
            
            ip_obj = ipaddress.ip_address(ip)
            
            if version:
                return ip_obj.version == version
                
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def validate_date_range(
        date_value: Union[date, datetime, str],
        min_date: Optional[Union[date, datetime]] = None,
        max_date: Optional[Union[date, datetime]] = None
    ) -> bool:
        """
        Validate date is within specified range
        """
        try:
            if isinstance(date_value, str):
                date_value = datetime.fromisoformat(date_value).date()
            elif isinstance(date_value, datetime):
                date_value = date_value.date()
            
            if min_date and date_value < (min_date.date() if isinstance(min_date, datetime) else min_date):
                return False
                
            if max_date and date_value > (max_date.date() if isinstance(max_date, datetime) else max_date):
                return False
                
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def validate_numeric_range(
        value: Union[int, float, Decimal, str],
        min_value: Optional[Union[int, float, Decimal]] = None,
        max_value: Optional[Union[int, float, Decimal]] = None,
        decimal_places: Optional[int] = None
    ) -> bool:
        """
        Validate numeric value is within specified range
        """
        try:
            if isinstance(value, str):
                value = Decimal(value)
            elif isinstance(value, (int, float)):
                value = Decimal(str(value))
            
            if min_value is not None and value < min_value:
                return False
                
            if max_value is not None and value > max_value:
                return False
            
            if decimal_places is not None:
                # Check decimal places
                decimal_part = str(value).split('.')[-1] if '.' in str(value) else ''
                if len(decimal_part) > decimal_places:
                    return False
                    
            return True
            
        except (InvalidOperation, ValueError):
            return False
    
    @staticmethod
    def validate_length(
        value: Union[str, List, Dict],
        min_length: Optional[int] = None,
        max_length: Optional[int] = None
    ) -> bool:
        """
        Validate length of string, list, or dict
        """
        try:
            length = len(value)
            
            if min_length is not None and length < min_length:
                return False
                
            if max_length is not None and length > max_length:
                return False
                
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def validate_pattern(value: str, pattern: str, flags: int = 0) -> bool:
        """
        Validate string matches regex pattern
        """
        try:
            return re.match(pattern, value, flags) is not None
        except Exception:
            return False
    
    @staticmethod
    def validate_hebrew_text(text: str) -> bool:
        """
        Validate text contains valid Hebrew characters
        """
        try:
            # Check if text contains Hebrew characters or common punctuation
            hebrew_pattern = r'^[\u0590-\u05FF\s\d\p{P}a-zA-Z]*$'
            return re.match(hebrew_pattern, text, re.UNICODE) is not None
        except Exception:
            return False


class SecureFormValidator:
    """
    Secure form validation with sanitization
    """
    
    def __init__(self, sanitize: bool = True, strict: bool = True):
        self.sanitize = sanitize
        self.strict = strict
        self.sanitizer = InputSanitizer()
        self.validator = InputValidator()
    
    def validate_and_sanitize(
        self,
        data: Dict[str, Any],
        rules: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate and sanitize form data according to rules
        
        Args:
            data: Input data to validate
            rules: Validation rules per field
            
        Returns:
            Sanitized and validated data
            
        Raises:
            ValidationError: If validation fails
        """
        result = {}
        errors = []
        
        for field, field_rules in rules.items():
            value = data.get(field)
            
            try:
                # Check required fields
                if field_rules.get('required', False) and (value is None or value == ''):
                    errors.append(f"Field '{field}' is required")
                    continue
                
                # Skip validation for optional empty fields
                if value is None or value == '':
                    result[field] = None
                    continue
                
                # Sanitize if enabled
                if self.sanitize and isinstance(value, str):
                    value = self._sanitize_field(value, field_rules)
                
                # Validate
                validated_value = self._validate_field(value, field_rules)
                result[field] = validated_value
                
            except Exception as e:
                errors.append(f"Field '{field}': {str(e)}")
        
        if errors:
            logger.warning("Form validation failed", errors=errors)
            raise ValidationError(f"Validation failed: {'; '.join(errors)}")
        
        return result
    
    def _sanitize_field(self, value: str, rules: Dict[str, Any]) -> str:
        """
        Sanitize field value according to rules
        """
        field_type = rules.get('type', 'string')
        
        if field_type == 'email':
            return value.strip().lower()
        elif field_type == 'filename':
            return self.sanitizer.sanitize_filename(value)
        elif field_type == 'hebrew_text':
            return self.sanitizer.sanitize_hebrew_text(value)
        elif field_type == 'html':
            allowed_tags = rules.get('allowed_tags')
            return self.sanitizer.sanitize_html(value, allowed_tags)
        else:
            max_length = rules.get('max_length')
            return self.sanitizer.sanitize_string(value, max_length)
    
    def _validate_field(self, value: Any, rules: Dict[str, Any]) -> Any:
        """
        Validate field value according to rules
        """
        field_type = rules.get('type', 'string')
        
        # Type-specific validation
        if field_type == 'email':
            if not self.validator.validate_email(value, self.strict):
                raise ValidationError("Invalid email format")
        
        elif field_type == 'phone':
            if not self.validator.validate_phone(value):
                raise ValidationError("Invalid phone number format")
        
        elif field_type == 'url':
            schemes = rules.get('schemes', ['http', 'https'])
            if not self.validator.validate_url(value, schemes):
                raise ValidationError("Invalid URL format")
        
        elif field_type == 'ip_address':
            version = rules.get('version')
            if not self.validator.validate_ip_address(value, version):
                raise ValidationError("Invalid IP address format")
        
        elif field_type == 'date':
            min_date = rules.get('min_date')
            max_date = rules.get('max_date')
            if not self.validator.validate_date_range(value, min_date, max_date):
                raise ValidationError("Date out of allowed range")
        
        elif field_type in ['int', 'float', 'decimal']:
            min_value = rules.get('min_value')
            max_value = rules.get('max_value')
            decimal_places = rules.get('decimal_places')
            if not self.validator.validate_numeric_range(value, min_value, max_value, decimal_places):
                raise ValidationError("Number out of allowed range")
        
        elif field_type == 'hebrew_text':
            if not self.validator.validate_hebrew_text(value):
                raise ValidationError("Invalid Hebrew text")
        
        # Length validation
        min_length = rules.get('min_length')
        max_length = rules.get('max_length')
        if not self.validator.validate_length(value, min_length, max_length):
            raise ValidationError(f"Length must be between {min_length} and {max_length}")
        
        # Pattern validation
        pattern = rules.get('pattern')
        if pattern and isinstance(value, str):
            if not self.validator.validate_pattern(value, pattern):
                raise ValidationError("Value does not match required pattern")
        
        # Custom validation function
        custom_validator = rules.get('validator')
        if custom_validator and callable(custom_validator):
            if not custom_validator(value):
                raise ValidationError("Custom validation failed")
        
        return value


# Global instances
sanitizer = InputSanitizer()
validator = InputValidator()
form_validator = SecureFormValidator()


# Common validation rule sets
COMMON_RULES = {
    'username': {
        'type': 'string',
        'required': True,
        'min_length': 3,
        'max_length': 50,
        'pattern': SanitizationConfig.PATTERNS['username']
    },
    'email': {
        'type': 'email',
        'required': True,
        'max_length': 255
    },
    'password': {
        'type': 'string',
        'required': True,
        'min_length': 12,
        'max_length': 128
    },
    'phone': {
        'type': 'phone',
        'required': False,
        'max_length': 20
    },
    'filename': {
        'type': 'filename',
        'required': True,
        'max_length': 255
    },
    'hebrew_name': {
        'type': 'hebrew_text',
        'required': True,
        'min_length': 1,
        'max_length': 100
    }
}