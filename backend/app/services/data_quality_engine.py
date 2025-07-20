"""
Data Quality Validation Engine with Monitoring for IDF Testing Infrastructure.
Provides comprehensive data validation, quality scoring, and monitoring capabilities.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics
from collections import defaultdict, Counter
import unicodedata

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import aioredis

from ..core.redis_client import get_redis_client
from ..utils.logger import get_logger
from ..models.base import BaseModel

logger = get_logger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    """Categories of data validation."""
    SCHEMA = "schema"
    HEBREW_TEXT = "hebrew_text"
    DATA_FORMAT = "data_format"
    BUSINESS_LOGIC = "business_logic"
    CONSISTENCY = "consistency"
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    UNIQUENESS = "uniqueness"


@dataclass
class ValidationRule:
    """Definition of a validation rule."""
    rule_id: str
    name: str
    description: str
    category: ValidationCategory
    severity: ValidationSeverity
    enabled: bool = True
    weight: float = 1.0
    threshold: Optional[float] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationIssue:
    """A validation issue found in data."""
    rule_id: str
    severity: ValidationSeverity
    category: ValidationCategory
    message: str
    field_name: Optional[str] = None
    record_id: Optional[str] = None
    record_index: Optional[int] = None
    actual_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class QualityReport:
    """Comprehensive data quality report."""
    report_id: str
    dataset_id: str
    total_records: int
    validation_timestamp: datetime
    overall_score: float
    category_scores: Dict[ValidationCategory, float]
    severity_counts: Dict[ValidationSeverity, int]
    issues: List[ValidationIssue]
    metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class DataQualityEngine:
    """Advanced data quality validation engine with Hebrew text support."""
    
    # Hebrew text patterns for validation
    HEBREW_LETTERS = re.compile(r'[\u05D0-\u05EA]')
    HEBREW_POINTS = re.compile(r'[\u05B0-\u05BD\u05BF-\u05C2\u05C4-\u05C5\u05C7]')
    HEBREW_BLOCK = re.compile(r'[\u0590-\u05FF]')
    HEBREW_PUNCTUATION = re.compile(r'[\u05BE\u05C0\u05C3\u05C6\u05F3-\u05F4]')
    
    # Common Hebrew validation patterns
    HEBREW_NAME_PATTERN = re.compile(r'^[\u05D0-\u05EA\s\-\'\"]+$')
    HEBREW_SENTENCE_PATTERN = re.compile(r'^[\u05D0-\u05EA\s\-\'\".,!?()]+$')
    
    # Data format patterns
    PHONE_PATTERN = re.compile(r'^[\d\-\(\)\s\+]+$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    ID_PATTERN = re.compile(r'^\d{6,9}$')
    DATE_PATTERNS = [
        re.compile(r'^\d{4}-\d{2}-\d{2}$'),
        re.compile(r'^\d{2}/\d{2}/\d{4}$'),
        re.compile(r'^\d{2}\.\d{2}\.\d{4}$')
    ]
    
    def __init__(self, session: AsyncSession, redis_client: Optional[aioredis.Redis] = None):
        """
        Initialize the data quality engine.
        
        Args:
            session: Database session
            redis_client: Redis client for caching and monitoring
        """
        self.session = session
        self.redis_client = redis_client or get_redis_client()
        
        # Validation rules registry
        self.rules: Dict[str, ValidationRule] = {}
        
        # Quality monitoring
        self.quality_history: List[QualityReport] = []
        self.quality_trends: Dict[str, List[float]] = defaultdict(list)
        
        # Performance metrics
        self.validation_stats = {
            'total_validations': 0,
            'total_issues': 0,
            'avg_validation_time': 0.0,
            'last_validation': None
        }
        
        # Initialize default rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default validation rules."""
        
        # Schema validation rules
        self.register_rule(ValidationRule(
            rule_id="required_field",
            name="Required Field Check",
            description="Ensures required fields are not empty",
            category=ValidationCategory.SCHEMA,
            severity=ValidationSeverity.ERROR,
            parameters={"required_fields": ["building_id", "inspection_type"]}
        ))
        
        self.register_rule(ValidationRule(
            rule_id="field_length",
            name="Field Length Validation",
            description="Validates field length constraints",
            category=ValidationCategory.SCHEMA,
            severity=ValidationSeverity.WARNING,
            parameters={"max_lengths": {"building_id": 50, "inspection_notes": 1000}}
        ))
        
        # Hebrew text validation rules
        self.register_rule(ValidationRule(
            rule_id="hebrew_text_format",
            name="Hebrew Text Format",
            description="Validates Hebrew text format and encoding",
            category=ValidationCategory.HEBREW_TEXT,
            severity=ValidationSeverity.ERROR
        ))
        
        self.register_rule(ValidationRule(
            rule_id="hebrew_name_validation",
            name="Hebrew Name Validation",
            description="Validates Hebrew names contain only valid characters",
            category=ValidationCategory.HEBREW_TEXT,
            severity=ValidationSeverity.WARNING,
            parameters={"hebrew_fields": ["building_manager", "inspection_leader"]}
        ))
        
        self.register_rule(ValidationRule(
            rule_id="mixed_language_detection",
            name="Mixed Language Detection",
            description="Detects inappropriate mixing of Hebrew and other languages",
            category=ValidationCategory.HEBREW_TEXT,
            severity=ValidationSeverity.WARNING
        ))
        
        # Data format validation rules
        self.register_rule(ValidationRule(
            rule_id="date_format",
            name="Date Format Validation",
            description="Validates date fields format",
            category=ValidationCategory.DATA_FORMAT,
            severity=ValidationSeverity.ERROR,
            parameters={"date_fields": ["execution_schedule", "target_completion"]}
        ))
        
        self.register_rule(ValidationRule(
            rule_id="boolean_format",
            name="Boolean Format Validation",
            description="Validates boolean fields format",
            category=ValidationCategory.DATA_FORMAT,
            severity=ValidationSeverity.ERROR,
            parameters={"boolean_fields": ["coordinated_with_contractor", "report_distributed"]}
        ))
        
        # Business logic validation rules
        self.register_rule(ValidationRule(
            rule_id="date_consistency",
            name="Date Consistency Check",
            description="Ensures execution_schedule <= target_completion",
            category=ValidationCategory.BUSINESS_LOGIC,
            severity=ValidationSeverity.WARNING
        ))
        
        self.register_rule(ValidationRule(
            rule_id="status_consistency",
            name="Status Consistency Check",
            description="Validates status field consistency with other fields",
            category=ValidationCategory.BUSINESS_LOGIC,
            severity=ValidationSeverity.WARNING
        ))
        
        # Completeness validation rules
        self.register_rule(ValidationRule(
            rule_id="completeness_ratio",
            name="Completeness Ratio Check",
            description="Ensures minimum data completeness ratio",
            category=ValidationCategory.COMPLETENESS,
            severity=ValidationSeverity.WARNING,
            threshold=0.8
        ))
        
        # Uniqueness validation rules
        self.register_rule(ValidationRule(
            rule_id="duplicate_detection",
            name="Duplicate Record Detection",
            description="Detects duplicate records in dataset",
            category=ValidationCategory.UNIQUENESS,
            severity=ValidationSeverity.WARNING
        ))
    
    def register_rule(self, rule: ValidationRule):
        """Register a validation rule."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Registered validation rule: {rule.name}")
    
    def unregister_rule(self, rule_id: str):
        """Unregister a validation rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Unregistered validation rule: {rule_id}")
    
    def get_rule(self, rule_id: str) -> Optional[ValidationRule]:
        """Get a validation rule by ID."""
        return self.rules.get(rule_id)
    
    def list_rules(self, category: Optional[ValidationCategory] = None) -> List[ValidationRule]:
        """List all validation rules, optionally filtered by category."""
        if category:
            return [rule for rule in self.rules.values() if rule.category == category]
        return list(self.rules.values())
    
    async def validate_dataset(self, data: List[Dict[str, Any]], 
                             dataset_id: str = None,
                             enabled_rules: Optional[List[str]] = None) -> QualityReport:
        """
        Validate a complete dataset and generate quality report.
        
        Args:
            data: List of data records to validate
            dataset_id: Optional dataset identifier
            enabled_rules: Optional list of rule IDs to run (default: all enabled)
            
        Returns:
            Comprehensive quality report
        """
        start_time = datetime.now()
        dataset_id = dataset_id or f"dataset_{int(start_time.timestamp())}"
        
        logger.info(f"Starting validation of dataset {dataset_id} with {len(data)} records")
        
        # Determine which rules to run
        rules_to_run = []
        if enabled_rules:
            rules_to_run = [self.rules[rule_id] for rule_id in enabled_rules if rule_id in self.rules and self.rules[rule_id].enabled]
        else:
            rules_to_run = [rule for rule in self.rules.values() if rule.enabled]
        
        # Collect all validation issues
        all_issues = []
        
        # Run validation rules
        for rule in rules_to_run:
            issues = await self._execute_rule(rule, data)
            all_issues.extend(issues)
        
        # Generate quality report
        report = await self._generate_quality_report(
            dataset_id=dataset_id,
            data=data,
            issues=all_issues,
            validation_timestamp=start_time
        )
        
        # Update statistics
        validation_time = (datetime.now() - start_time).total_seconds()
        self.validation_stats['total_validations'] += 1
        self.validation_stats['total_issues'] += len(all_issues)
        self.validation_stats['avg_validation_time'] = (
            (self.validation_stats['avg_validation_time'] * (self.validation_stats['total_validations'] - 1) + validation_time) /
            self.validation_stats['total_validations']
        )
        self.validation_stats['last_validation'] = datetime.now()
        
        # Store quality report
        await self._store_quality_report(report)
        
        # Update quality trends
        self._update_quality_trends(report)
        
        logger.info(f"Validation completed in {validation_time:.2f}s. Overall score: {report.overall_score:.3f}")
        
        return report
    
    async def validate_record(self, record: Dict[str, Any], 
                            record_id: str = None,
                            enabled_rules: Optional[List[str]] = None) -> List[ValidationIssue]:
        """
        Validate a single record.
        
        Args:
            record: Data record to validate
            record_id: Optional record identifier
            enabled_rules: Optional list of rule IDs to run
            
        Returns:
            List of validation issues
        """
        # Run validation on single record dataset
        report = await self.validate_dataset([record], f"record_{record_id}", enabled_rules)
        return report.issues
    
    async def _execute_rule(self, rule: ValidationRule, data: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Execute a validation rule on dataset."""
        issues = []
        
        try:
            if rule.rule_id == "required_field":
                issues.extend(await self._validate_required_fields(rule, data))
            elif rule.rule_id == "field_length":
                issues.extend(await self._validate_field_lengths(rule, data))
            elif rule.rule_id == "hebrew_text_format":
                issues.extend(await self._validate_hebrew_text_format(rule, data))
            elif rule.rule_id == "hebrew_name_validation":
                issues.extend(await self._validate_hebrew_names(rule, data))
            elif rule.rule_id == "mixed_language_detection":
                issues.extend(await self._validate_mixed_language(rule, data))
            elif rule.rule_id == "date_format":
                issues.extend(await self._validate_date_format(rule, data))
            elif rule.rule_id == "boolean_format":
                issues.extend(await self._validate_boolean_format(rule, data))
            elif rule.rule_id == "date_consistency":
                issues.extend(await self._validate_date_consistency(rule, data))
            elif rule.rule_id == "status_consistency":
                issues.extend(await self._validate_status_consistency(rule, data))
            elif rule.rule_id == "completeness_ratio":
                issues.extend(await self._validate_completeness_ratio(rule, data))
            elif rule.rule_id == "duplicate_detection":
                issues.extend(await self._validate_duplicate_detection(rule, data))
            else:
                logger.warning(f"Unknown validation rule: {rule.rule_id}")
                
        except Exception as e:
            logger.error(f"Error executing rule {rule.rule_id}: {str(e)}")
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                severity=ValidationSeverity.ERROR,
                category=rule.category,
                message=f"Rule execution failed: {str(e)}"
            ))
        
        return issues
    
    async def _validate_required_fields(self, rule: ValidationRule, data: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate required fields are present and not empty."""
        issues = []
        required_fields = rule.parameters.get("required_fields", [])
        
        for idx, record in enumerate(data):
            for field in required_fields:
                value = record.get(field)
                if value is None or (isinstance(value, str) and not value.strip()):
                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        category=rule.category,
                        message=f"Required field '{field}' is missing or empty",
                        field_name=field,
                        record_index=idx,
                        actual_value=value
                    ))
        
        return issues
    
    async def _validate_field_lengths(self, rule: ValidationRule, data: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate field length constraints."""
        issues = []
        max_lengths = rule.parameters.get("max_lengths", {})
        
        for idx, record in enumerate(data):
            for field, max_length in max_lengths.items():
                value = record.get(field)
                if isinstance(value, str) and len(value) > max_length:
                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        category=rule.category,
                        message=f"Field '{field}' exceeds maximum length of {max_length}",
                        field_name=field,
                        record_index=idx,
                        actual_value=len(value),
                        expected_value=max_length
                    ))
        
        return issues
    
    async def _validate_hebrew_text_format(self, rule: ValidationRule, data: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate Hebrew text format and encoding."""
        issues = []
        
        hebrew_fields = ["building_manager", "red_team", "inspection_type", "inspection_leader", "inspection_notes"]
        
        for idx, record in enumerate(data):
            for field in hebrew_fields:
                value = record.get(field)
                if isinstance(value, str) and value:
                    # Check for encoding issues
                    if '�' in value or '\ufffd' in value:
                        issues.append(ValidationIssue(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            category=rule.category,
                            message=f"Hebrew text encoding issue in field '{field}'",
                            field_name=field,
                            record_index=idx,
                            actual_value=value
                        ))
                    
                    # Check for malformed Unicode
                    try:
                        unicodedata.normalize('NFC', value)
                    except ValueError:
                        issues.append(ValidationIssue(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            category=rule.category,
                            message=f"Malformed Unicode in Hebrew field '{field}'",
                            field_name=field,
                            record_index=idx,
                            actual_value=value
                        ))
        
        return issues
    
    async def _validate_hebrew_names(self, rule: ValidationRule, data: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate Hebrew names contain only valid characters."""
        issues = []
        hebrew_fields = rule.parameters.get("hebrew_fields", [])
        
        for idx, record in enumerate(data):
            for field in hebrew_fields:
                value = record.get(field)
                if isinstance(value, str) and value:
                    # Check if name contains valid Hebrew characters
                    if not self.HEBREW_NAME_PATTERN.match(value):
                        issues.append(ValidationIssue(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            category=rule.category,
                            message=f"Invalid characters in Hebrew name field '{field}'",
                            field_name=field,
                            record_index=idx,
                            actual_value=value
                        ))
                    
                    # Check for suspicious patterns
                    if len(value) < 2:
                        issues.append(ValidationIssue(
                            rule_id=rule.rule_id,
                            severity=ValidationSeverity.WARNING,
                            category=rule.category,
                            message=f"Hebrew name in field '{field}' is too short",
                            field_name=field,
                            record_index=idx,
                            actual_value=value
                        ))
        
        return issues
    
    async def _validate_mixed_language(self, rule: ValidationRule, data: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Detect inappropriate mixing of Hebrew and other languages."""
        issues = []
        
        text_fields = ["building_manager", "red_team", "inspection_type", "inspection_leader", "inspection_notes"]
        
        for idx, record in enumerate(data):
            for field in text_fields:
                value = record.get(field)
                if isinstance(value, str) and value and len(value) > 10:
                    hebrew_chars = len(self.HEBREW_LETTERS.findall(value))
                    latin_chars = len(re.findall(r'[a-zA-Z]', value))
                    total_chars = len(re.findall(r'[a-zA-Z\u05D0-\u05EA]', value))
                    
                    if total_chars > 0:
                        hebrew_ratio = hebrew_chars / total_chars
                        latin_ratio = latin_chars / total_chars
                        
                        # Flag if both languages are significantly present
                        if 0.2 < hebrew_ratio < 0.8 and 0.2 < latin_ratio < 0.8:
                            issues.append(ValidationIssue(
                                rule_id=rule.rule_id,
                                severity=rule.severity,
                                category=rule.category,
                                message=f"Mixed language content detected in field '{field}'",
                                field_name=field,
                                record_index=idx,
                                actual_value=f"Hebrew: {hebrew_ratio:.1%}, Latin: {latin_ratio:.1%}"
                            ))
        
        return issues
    
    async def _validate_date_format(self, rule: ValidationRule, data: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate date fields format."""
        issues = []
        date_fields = rule.parameters.get("date_fields", [])
        
        for idx, record in enumerate(data):
            for field in date_fields:
                value = record.get(field)
                if value is not None and not isinstance(value, (datetime, datetime.date)):
                    if isinstance(value, str) and value.strip():
                        # Check if matches any valid date pattern
                        valid_format = any(pattern.match(value.strip()) for pattern in self.DATE_PATTERNS)
                        if not valid_format:
                            issues.append(ValidationIssue(
                                rule_id=rule.rule_id,
                                severity=rule.severity,
                                category=rule.category,
                                message=f"Invalid date format in field '{field}'",
                                field_name=field,
                                record_index=idx,
                                actual_value=value,
                                expected_value="YYYY-MM-DD, DD/MM/YYYY, or DD.MM.YYYY"
                            ))
        
        return issues
    
    async def _validate_boolean_format(self, rule: ValidationRule, data: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate boolean fields format."""
        issues = []
        boolean_fields = rule.parameters.get("boolean_fields", [])
        valid_boolean_values = {"true", "false", "1", "0", "yes", "no", "כן", "לא"}
        
        for idx, record in enumerate(data):
            for field in boolean_fields:
                value = record.get(field)
                if value is not None and not isinstance(value, bool):
                    if isinstance(value, str):
                        if value.lower().strip() not in valid_boolean_values:
                            issues.append(ValidationIssue(
                                rule_id=rule.rule_id,
                                severity=rule.severity,
                                category=rule.category,
                                message=f"Invalid boolean value in field '{field}'",
                                field_name=field,
                                record_index=idx,
                                actual_value=value,
                                expected_value="true/false, כן/לא, yes/no, 1/0"
                            ))
                    else:
                        issues.append(ValidationIssue(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            category=rule.category,
                            message=f"Non-boolean value in boolean field '{field}'",
                            field_name=field,
                            record_index=idx,
                            actual_value=type(value).__name__,
                            expected_value="boolean"
                        ))
        
        return issues
    
    async def _validate_date_consistency(self, rule: ValidationRule, data: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate date field consistency."""
        issues = []
        
        for idx, record in enumerate(data):
            execution_date = record.get("execution_schedule")
            completion_date = record.get("target_completion")
            
            if execution_date and completion_date:
                # Convert to datetime objects if needed
                if isinstance(execution_date, str):
                    try:
                        execution_date = datetime.strptime(execution_date, "%Y-%m-%d")
                    except ValueError:
                        continue
                
                if isinstance(completion_date, str):
                    try:
                        completion_date = datetime.strptime(completion_date, "%Y-%m-%d")
                    except ValueError:
                        continue
                
                if execution_date > completion_date:
                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        category=rule.category,
                        message="Execution date is after target completion date",
                        record_index=idx,
                        actual_value=f"Execution: {execution_date}, Completion: {completion_date}"
                    ))
        
        return issues
    
    async def _validate_status_consistency(self, rule: ValidationRule, data: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate status field consistency with other fields."""
        issues = []
        
        for idx, record in enumerate(data):
            status = record.get("status")
            report_distributed = record.get("report_distributed")
            distribution_date = record.get("distribution_date")
            
            # If report is distributed, there should be a distribution date
            if report_distributed and not distribution_date:
                issues.append(ValidationIssue(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    category=rule.category,
                    message="Report marked as distributed but no distribution date provided",
                    record_index=idx,
                    field_name="distribution_date"
                ))
            
            # If distribution date exists, report should be marked as distributed
            if distribution_date and not report_distributed:
                issues.append(ValidationIssue(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    category=rule.category,
                    message="Distribution date provided but report not marked as distributed",
                    record_index=idx,
                    field_name="report_distributed"
                ))
        
        return issues
    
    async def _validate_completeness_ratio(self, rule: ValidationRule, data: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate data completeness ratio."""
        issues = []
        threshold = rule.threshold or 0.8
        
        if not data:
            return issues
        
        # Calculate completeness for each field
        field_completeness = {}
        all_fields = set()
        
        for record in data:
            all_fields.update(record.keys())
        
        for field in all_fields:
            non_empty_count = sum(1 for record in data if record.get(field) is not None and str(record.get(field)).strip())
            completeness = non_empty_count / len(data)
            field_completeness[field] = completeness
            
            if completeness < threshold:
                issues.append(ValidationIssue(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    category=rule.category,
                    message=f"Field '{field}' completeness ({completeness:.1%}) below threshold ({threshold:.1%})",
                    field_name=field,
                    actual_value=completeness,
                    expected_value=threshold
                ))
        
        return issues
    
    async def _validate_duplicate_detection(self, rule: ValidationRule, data: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Detect duplicate records in dataset."""
        issues = []
        
        # Create hashes for each record
        record_hashes = {}
        key_fields = ["building_id", "inspection_type", "execution_schedule"]
        
        for idx, record in enumerate(data):
            # Create a hash based on key fields
            key_values = []
            for field in key_fields:
                value = record.get(field)
                if value is not None:
                    key_values.append(str(value))
            
            if key_values:
                record_hash = "|".join(key_values)
                
                if record_hash in record_hashes:
                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        category=rule.category,
                        message=f"Duplicate record found (matches record at index {record_hashes[record_hash]})",
                        record_index=idx,
                        actual_value=record_hash
                    ))
                else:
                    record_hashes[record_hash] = idx
        
        return issues
    
    async def _generate_quality_report(self, dataset_id: str, data: List[Dict[str, Any]], 
                                     issues: List[ValidationIssue], 
                                     validation_timestamp: datetime) -> QualityReport:
        """Generate comprehensive quality report."""
        
        # Count issues by severity and category
        severity_counts = Counter(issue.severity for issue in issues)
        category_counts = Counter(issue.category for issue in issues)
        
        # Calculate scores by category
        category_scores = {}
        for category in ValidationCategory:
            category_issues = [issue for issue in issues if issue.category == category]
            if category_issues:
                # Weight issues by severity
                severity_weights = {
                    ValidationSeverity.INFO: 0.1,
                    ValidationSeverity.WARNING: 0.3,
                    ValidationSeverity.ERROR: 0.7,
                    ValidationSeverity.CRITICAL: 1.0
                }
                
                total_weight = sum(severity_weights.get(issue.severity, 0.5) for issue in category_issues)
                max_possible_weight = len(data) * 1.0  # Assuming worst case: all records have critical issues
                
                category_score = max(0, 1 - (total_weight / max_possible_weight))
            else:
                category_score = 1.0
            
            category_scores[category] = category_score
        
        # Calculate overall score
        if category_scores:
            overall_score = statistics.mean(category_scores.values())
        else:
            overall_score = 1.0
        
        # Generate metrics
        metrics = {
            'records_processed': len(data),
            'issues_found': len(issues),
            'completeness_ratio': self._calculate_completeness_ratio(data),
            'hebrew_text_ratio': self._calculate_hebrew_text_ratio(data),
            'validation_rules_applied': len(self.rules),
            'processing_time': (datetime.now() - validation_timestamp).total_seconds()
        }
        
        # Generate recommendations
        recommendations = self._generate_recommendations(issues, category_scores)
        
        return QualityReport(
            report_id=f"report_{dataset_id}_{int(validation_timestamp.timestamp())}",
            dataset_id=dataset_id,
            total_records=len(data),
            validation_timestamp=validation_timestamp,
            overall_score=overall_score,
            category_scores=category_scores,
            severity_counts=dict(severity_counts),
            issues=issues,
            metrics=metrics,
            recommendations=recommendations
        )
    
    def _calculate_completeness_ratio(self, data: List[Dict[str, Any]]) -> float:
        """Calculate overall data completeness ratio."""
        if not data:
            return 0.0
        
        total_fields = 0
        filled_fields = 0
        
        for record in data:
            for value in record.values():
                total_fields += 1
                if value is not None and str(value).strip():
                    filled_fields += 1
        
        return filled_fields / total_fields if total_fields > 0 else 0.0
    
    def _calculate_hebrew_text_ratio(self, data: List[Dict[str, Any]]) -> float:
        """Calculate ratio of Hebrew text in dataset."""
        if not data:
            return 0.0
        
        text_fields = 0
        hebrew_fields = 0
        
        for record in data:
            for value in record.values():
                if isinstance(value, str) and value.strip():
                    text_fields += 1
                    if self.HEBREW_LETTERS.search(value):
                        hebrew_fields += 1
        
        return hebrew_fields / text_fields if text_fields > 0 else 0.0
    
    def _generate_recommendations(self, issues: List[ValidationIssue], 
                                category_scores: Dict[ValidationCategory, float]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Recommendations based on category scores
        for category, score in category_scores.items():
            if score < 0.7:
                if category == ValidationCategory.HEBREW_TEXT:
                    recommendations.append("Consider improving Hebrew text encoding and format validation")
                elif category == ValidationCategory.COMPLETENESS:
                    recommendations.append("Improve data completeness by filling missing required fields")
                elif category == ValidationCategory.CONSISTENCY:
                    recommendations.append("Review data consistency rules and fix conflicting values")
                elif category == ValidationCategory.UNIQUENESS:
                    recommendations.append("Implement duplicate detection and removal processes")
        
        # Recommendations based on common issues
        issue_types = Counter(issue.rule_id for issue in issues)
        for rule_id, count in issue_types.most_common(5):
            rule = self.rules.get(rule_id)
            if rule and count > len(issues) * 0.1:  # If issue appears in >10% of cases
                recommendations.append(f"Address frequent {rule.name} issues ({count} occurrences)")
        
        return recommendations
    
    async def _store_quality_report(self, report: QualityReport):
        """Store quality report in Redis for monitoring."""
        report_data = {
            'report_id': report.report_id,
            'dataset_id': report.dataset_id,
            'total_records': report.total_records,
            'validation_timestamp': report.validation_timestamp.isoformat(),
            'overall_score': report.overall_score,
            'category_scores': {cat.value: score for cat, score in report.category_scores.items()},
            'severity_counts': {sev.value: count for sev, count in report.severity_counts.items()},
            'metrics': report.metrics,
            'recommendations': report.recommendations,
            'issues_count': len(report.issues)
        }
        
        # Store report (expire after 30 days)
        await self.redis_client.setex(
            f"quality_report:{report.report_id}",
            30 * 24 * 3600,  # 30 days
            json.dumps(report_data)
        )
        
        # Store in quality history list
        await self.redis_client.lpush(
            f"quality_history:{report.dataset_id}",
            json.dumps(report_data)
        )
        
        # Keep only last 100 reports
        await self.redis_client.ltrim(f"quality_history:{report.dataset_id}", 0, 99)
    
    def _update_quality_trends(self, report: QualityReport):
        """Update quality trends for monitoring."""
        # Update overall score trend
        self.quality_trends['overall_score'].append(report.overall_score)
        
        # Update category trends
        for category, score in report.category_scores.items():
            self.quality_trends[f'category_{category.value}'].append(score)
        
        # Keep only last 100 data points
        for trend_key in self.quality_trends:
            if len(self.quality_trends[trend_key]) > 100:
                self.quality_trends[trend_key] = self.quality_trends[trend_key][-100:]
    
    async def get_quality_trends(self, dataset_id: str = None) -> Dict[str, Any]:
        """Get quality trends and statistics."""
        if dataset_id:
            # Get trends for specific dataset from Redis
            history_data = await self.redis_client.lrange(f"quality_history:{dataset_id}", 0, -1)
            history = [json.loads(item) for item in history_data]
            
            if history:
                trends = {
                    'overall_score': [item['overall_score'] for item in history],
                    'total_records': [item['total_records'] for item in history],
                    'issues_count': [item['issues_count'] for item in history],
                    'timestamps': [item['validation_timestamp'] for item in history]
                }
                
                # Calculate statistics
                scores = trends['overall_score']
                stats = {
                    'current_score': scores[0] if scores else 0,
                    'average_score': statistics.mean(scores) if scores else 0,
                    'min_score': min(scores) if scores else 0,
                    'max_score': max(scores) if scores else 0,
                    'trend_direction': 'improving' if len(scores) > 1 and scores[0] > scores[-1] else 'stable'
                }
                
                return {'trends': trends, 'statistics': stats}
        
        # Return global trends
        return {
            'trends': dict(self.quality_trends),
            'statistics': self.validation_stats
        }
    
    async def get_validation_statistics(self) -> Dict[str, Any]:
        """Get comprehensive validation statistics."""
        return {
            'validation_stats': self.validation_stats,
            'registered_rules': len(self.rules),
            'enabled_rules': len([r for r in self.rules.values() if r.enabled]),
            'rules_by_category': {
                cat.value: len([r for r in self.rules.values() if r.category == cat])
                for cat in ValidationCategory
            },
            'rules_by_severity': {
                sev.value: len([r for r in self.rules.values() if r.severity == sev])
                for sev in ValidationSeverity
            }
        }