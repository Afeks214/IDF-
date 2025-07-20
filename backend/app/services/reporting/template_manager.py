"""
Report Template Manager

Advanced template management system for creating, storing, and managing
customizable report templates with Hebrew support.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from app.core.config import get_settings
from app.utils.hebrew import HebrewTextProcessor

logger = logging.getLogger(__name__)

class TemplateType(Enum):
    """Template types supported by the system"""
    PDF = "pdf"
    EXCEL = "excel"
    WORD = "word"
    HTML = "html"
    CUSTOM = "custom"

class ReportSection(Enum):
    """Report section types"""
    HEADER = "header"
    SUMMARY = "summary"
    DETAILS = "details"
    CHARTS = "charts"
    STATISTICS = "statistics"
    RECOMMENDATIONS = "recommendations"
    APPENDIX = "appendix"
    FOOTER = "footer"

@dataclass
class TemplateField:
    """Template field configuration"""
    name: str
    display_name: str
    data_type: str
    required: bool = False
    default_value: str = ""
    validation_rules: List[str] = None
    formatting_rules: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.validation_rules is None:
            self.validation_rules = []
        if self.formatting_rules is None:
            self.formatting_rules = {}

@dataclass
class TemplateSection:
    """Template section configuration"""
    section_type: ReportSection
    title: str
    fields: List[TemplateField]
    layout: Dict[str, Any] = None
    styling: Dict[str, Any] = None
    conditions: List[str] = None
    
    def __post_init__(self):
        if self.layout is None:
            self.layout = {}
        if self.styling is None:
            self.styling = {}
        if self.conditions is None:
            self.conditions = []

@dataclass
class ReportTemplate:
    """Complete report template definition"""
    template_id: str
    name: str
    description: str
    template_type: TemplateType
    sections: List[TemplateSection]
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None
    version: str = "1.0"
    author: str = ""
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

class ReportTemplateManager:
    """
    Advanced Report Template Manager
    
    Features:
    - Template creation and management
    - Template versioning and history
    - Template validation and testing
    - Template sharing and collaboration
    - Template localization (Hebrew/English)
    - Template inheritance and composition
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.hebrew_processor = HebrewTextProcessor()
        self.template_dir = Path(__file__).parent / "templates"
        self.template_dir.mkdir(exist_ok=True)
        self._load_default_templates()
        
    def _load_default_templates(self):
        """Load default system templates"""
        try:
            # Create default templates if they don't exist
            default_templates = [
                self._create_inspection_report_template(),
                self._create_summary_report_template(),
                self._create_statistical_report_template(),
                self._create_executive_summary_template(),
                self._create_technical_report_template()
            ]
            
            for template in default_templates:
                template_path = self.template_dir / f"{template.template_id}.json"
                if not template_path.exists():
                    self.save_template(template)
                    
            logger.info(f"Loaded {len(default_templates)} default templates")
            
        except Exception as e:
            logger.error(f"Error loading default templates: {e}")
            
    def create_template(
        self,
        template_id: str,
        name: str,
        description: str,
        template_type: TemplateType,
        sections: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReportTemplate:
        """
        Create a new report template
        
        Args:
            template_id: Unique template identifier
            name: Template display name
            description: Template description
            template_type: Type of template (PDF, Excel, etc.)
            sections: List of template sections
            metadata: Additional template metadata
            
        Returns:
            Created ReportTemplate instance
        """
        try:
            # Convert sections to TemplateSection objects
            template_sections = []
            for section_data in sections:
                fields = []
                for field_data in section_data.get('fields', []):
                    field = TemplateField(**field_data)
                    fields.append(field)
                    
                section = TemplateSection(
                    section_type=ReportSection(section_data['section_type']),
                    title=section_data['title'],
                    fields=fields,
                    layout=section_data.get('layout', {}),
                    styling=section_data.get('styling', {}),
                    conditions=section_data.get('conditions', [])
                )
                template_sections.append(section)
                
            # Create template
            template = ReportTemplate(
                template_id=template_id,
                name=name,
                description=description,
                template_type=template_type,
                sections=template_sections,
                metadata=metadata or {}
            )
            
            # Validate template
            self._validate_template(template)
            
            # Save template
            self.save_template(template)
            
            logger.info(f"Created template: {template_id}")
            return template
            
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            raise
            
    def save_template(self, template: ReportTemplate):
        """Save template to file system"""
        try:
            template_path = self.template_dir / f"{template.template_id}.json"
            
            # Convert template to dictionary
            template_dict = self._template_to_dict(template)
            
            # Save to file
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template_dict, f, ensure_ascii=False, indent=2, default=str)
                
            logger.info(f"Saved template: {template.template_id}")
            
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            raise
            
    def load_template(self, template_id: str) -> Optional[ReportTemplate]:
        """Load template from file system"""
        try:
            template_path = self.template_dir / f"{template_id}.json"
            
            if not template_path.exists():
                logger.warning(f"Template not found: {template_id}")
                return None
                
            with open(template_path, 'r', encoding='utf-8') as f:
                template_dict = json.load(f)
                
            # Convert to ReportTemplate object
            template = self._dict_to_template(template_dict)
            
            logger.info(f"Loaded template: {template_id}")
            return template
            
        except Exception as e:
            logger.error(f"Error loading template: {e}")
            return None
            
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates"""
        try:
            templates = []
            
            for template_file in self.template_dir.glob("*.json"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_dict = json.load(f)
                        
                    template_info = {
                        'template_id': template_dict['template_id'],
                        'name': template_dict['name'],
                        'description': template_dict['description'],
                        'template_type': template_dict['template_type'],
                        'version': template_dict['version'],
                        'created_at': template_dict['created_at'],
                        'updated_at': template_dict['updated_at']
                    }
                    templates.append(template_info)
                    
                except Exception as e:
                    logger.error(f"Error reading template file {template_file}: {e}")
                    continue
                    
            return templates
            
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            return []
            
    def delete_template(self, template_id: str) -> bool:
        """Delete a template"""
        try:
            template_path = self.template_dir / f"{template_id}.json"
            
            if not template_path.exists():
                logger.warning(f"Template not found: {template_id}")
                return False
                
            template_path.unlink()
            logger.info(f"Deleted template: {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            return False
            
    def update_template(self, template_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing template"""
        try:
            template = self.load_template(template_id)
            if not template:
                return False
                
            # Update template fields
            for key, value in updates.items():
                if hasattr(template, key):
                    setattr(template, key, value)
                    
            # Update timestamp
            template.updated_at = datetime.now()
            
            # Validate updated template
            self._validate_template(template)
            
            # Save updated template
            self.save_template(template)
            
            logger.info(f"Updated template: {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating template: {e}")
            return False
            
    def clone_template(self, source_template_id: str, new_template_id: str, new_name: str) -> Optional[ReportTemplate]:
        """Clone an existing template"""
        try:
            source_template = self.load_template(source_template_id)
            if not source_template:
                return None
                
            # Create cloned template
            cloned_template = ReportTemplate(
                template_id=new_template_id,
                name=new_name,
                description=f"Cloned from {source_template.name}",
                template_type=source_template.template_type,
                sections=source_template.sections,
                metadata=source_template.metadata.copy(),
                version="1.0",
                author=source_template.author
            )
            
            # Save cloned template
            self.save_template(cloned_template)
            
            logger.info(f"Cloned template {source_template_id} to {new_template_id}")
            return cloned_template
            
        except Exception as e:
            logger.error(f"Error cloning template: {e}")
            return None
            
    def validate_template_data(self, template_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against template requirements"""
        try:
            template = self.load_template(template_id)
            if not template:
                return {'valid': False, 'errors': ['Template not found']}
                
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': []
            }
            
            # Validate each section
            for section in template.sections:
                section_data = data.get(section.section_type.value, {})
                
                # Validate required fields
                for field in section.fields:
                    if field.required and field.name not in section_data:
                        validation_result['valid'] = False
                        validation_result['errors'].append(
                            f"Required field '{field.name}' missing in section '{section.title}'"
                        )
                        
                    # Validate field data types
                    if field.name in section_data:
                        field_value = section_data[field.name]
                        if not self._validate_field_type(field_value, field.data_type):
                            validation_result['valid'] = False
                            validation_result['errors'].append(
                                f"Invalid data type for field '{field.name}' in section '{section.title}'"
                            )
                            
                    # Apply validation rules
                    if field.name in section_data and field.validation_rules:
                        field_validation = self._apply_validation_rules(
                            section_data[field.name], field.validation_rules
                        )
                        if not field_validation['valid']:
                            validation_result['valid'] = False
                            validation_result['errors'].extend(field_validation['errors'])
                            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating template data: {e}")
            return {'valid': False, 'errors': [str(e)]}
            
    def _validate_template(self, template: ReportTemplate):
        """Validate template structure and configuration"""
        try:
            # Check required fields
            if not template.template_id:
                raise ValueError("Template ID is required")
                
            if not template.name:
                raise ValueError("Template name is required")
                
            if not template.sections:
                raise ValueError("Template must have at least one section")
                
            # Validate sections
            for section in template.sections:
                if not section.title:
                    raise ValueError("Section title is required")
                    
                if not section.fields:
                    raise ValueError("Section must have at least one field")
                    
                # Validate fields
                for field in section.fields:
                    if not field.name:
                        raise ValueError("Field name is required")
                        
                    if not field.display_name:
                        raise ValueError("Field display name is required")
                        
                    if not field.data_type:
                        raise ValueError("Field data type is required")
                        
            logger.info(f"Template validation passed: {template.template_id}")
            
        except Exception as e:
            logger.error(f"Template validation failed: {e}")
            raise
            
    def _validate_field_type(self, value: Any, expected_type: str) -> bool:
        """Validate field data type"""
        try:
            type_mapping = {
                'string': str,
                'integer': int,
                'float': float,
                'boolean': bool,
                'date': str,  # Date strings
                'list': list,
                'dict': dict
            }
            
            expected_python_type = type_mapping.get(expected_type.lower())
            if not expected_python_type:
                return False
                
            return isinstance(value, expected_python_type)
            
        except Exception as e:
            logger.error(f"Error validating field type: {e}")
            return False
            
    def _apply_validation_rules(self, value: Any, rules: List[str]) -> Dict[str, Any]:
        """Apply validation rules to field value"""
        try:
            validation_result = {
                'valid': True,
                'errors': []
            }
            
            for rule in rules:
                if rule.startswith('min_length:'):
                    min_length = int(rule.split(':')[1])
                    if len(str(value)) < min_length:
                        validation_result['valid'] = False
                        validation_result['errors'].append(f"Value must be at least {min_length} characters")
                        
                elif rule.startswith('max_length:'):
                    max_length = int(rule.split(':')[1])
                    if len(str(value)) > max_length:
                        validation_result['valid'] = False
                        validation_result['errors'].append(f"Value must not exceed {max_length} characters")
                        
                elif rule.startswith('pattern:'):
                    import re
                    pattern = rule.split(':', 1)[1]
                    if not re.match(pattern, str(value)):
                        validation_result['valid'] = False
                        validation_result['errors'].append(f"Value does not match required pattern")
                        
                elif rule == 'required':
                    if not value:
                        validation_result['valid'] = False
                        validation_result['errors'].append("Field is required")
                        
            return validation_result
            
        except Exception as e:
            logger.error(f"Error applying validation rules: {e}")
            return {'valid': False, 'errors': [str(e)]}
            
    def _template_to_dict(self, template: ReportTemplate) -> Dict[str, Any]:
        """Convert template to dictionary for JSON serialization"""
        try:
            template_dict = {
                'template_id': template.template_id,
                'name': template.name,
                'description': template.description,
                'template_type': template.template_type.value,
                'version': template.version,
                'author': template.author,
                'created_at': template.created_at.isoformat(),
                'updated_at': template.updated_at.isoformat(),
                'metadata': template.metadata,
                'sections': []
            }
            
            # Convert sections
            for section in template.sections:
                section_dict = {
                    'section_type': section.section_type.value,
                    'title': section.title,
                    'layout': section.layout,
                    'styling': section.styling,
                    'conditions': section.conditions,
                    'fields': []
                }
                
                # Convert fields
                for field in section.fields:
                    field_dict = {
                        'name': field.name,
                        'display_name': field.display_name,
                        'data_type': field.data_type,
                        'required': field.required,
                        'default_value': field.default_value,
                        'validation_rules': field.validation_rules,
                        'formatting_rules': field.formatting_rules
                    }
                    section_dict['fields'].append(field_dict)
                    
                template_dict['sections'].append(section_dict)
                
            return template_dict
            
        except Exception as e:
            logger.error(f"Error converting template to dict: {e}")
            raise
            
    def _dict_to_template(self, template_dict: Dict[str, Any]) -> ReportTemplate:
        """Convert dictionary to ReportTemplate object"""
        try:
            # Convert sections
            sections = []
            for section_dict in template_dict['sections']:
                fields = []
                for field_dict in section_dict['fields']:
                    field = TemplateField(
                        name=field_dict['name'],
                        display_name=field_dict['display_name'],
                        data_type=field_dict['data_type'],
                        required=field_dict.get('required', False),
                        default_value=field_dict.get('default_value', ''),
                        validation_rules=field_dict.get('validation_rules', []),
                        formatting_rules=field_dict.get('formatting_rules', {})
                    )
                    fields.append(field)
                    
                section = TemplateSection(
                    section_type=ReportSection(section_dict['section_type']),
                    title=section_dict['title'],
                    fields=fields,
                    layout=section_dict.get('layout', {}),
                    styling=section_dict.get('styling', {}),
                    conditions=section_dict.get('conditions', [])
                )
                sections.append(section)
                
            # Create template
            template = ReportTemplate(
                template_id=template_dict['template_id'],
                name=template_dict['name'],
                description=template_dict['description'],
                template_type=TemplateType(template_dict['template_type']),
                sections=sections,
                metadata=template_dict.get('metadata', {}),
                created_at=datetime.fromisoformat(template_dict['created_at']),
                updated_at=datetime.fromisoformat(template_dict['updated_at']),
                version=template_dict.get('version', '1.0'),
                author=template_dict.get('author', '')
            )
            
            return template
            
        except Exception as e:
            logger.error(f"Error converting dict to template: {e}")
            raise
            
    def _create_inspection_report_template(self) -> ReportTemplate:
        """Create default inspection report template"""
        sections = [
            TemplateSection(
                section_type=ReportSection.HEADER,
                title="כותרת הדוח",
                fields=[
                    TemplateField("report_title", "כותרת הדוח", "string", True),
                    TemplateField("report_date", "תאריך הדוח", "date", True),
                    TemplateField("classification", "סיווג", "string", True, "סודי"),
                    TemplateField("author", "מחבר", "string", True)
                ]
            ),
            TemplateSection(
                section_type=ReportSection.SUMMARY,
                title="סיכום מנהלים",
                fields=[
                    TemplateField("total_inspections", "סך הכל בדיקות", "integer", True),
                    TemplateField("passed_inspections", "בדיקות שעברו", "integer", True),
                    TemplateField("failed_inspections", "בדיקות שנכשלו", "integer", True),
                    TemplateField("success_rate", "אחוז הצלחה", "float", True)
                ]
            ),
            TemplateSection(
                section_type=ReportSection.DETAILS,
                title="תוצאות מפורטות",
                fields=[
                    TemplateField("inspection_data", "נתוני בדיקות", "list", True),
                    TemplateField("detailed_results", "תוצאות מפורטות", "dict", True)
                ]
            )
        ]
        
        return ReportTemplate(
            template_id="inspection_report_hebrew",
            name="דוח בדיקות בעברית",
            description="תבנית סטנדרטית לדוחות בדיקות עם תמיכה בעברית",
            template_type=TemplateType.PDF,
            sections=sections,
            metadata={
                "language": "hebrew",
                "rtl_support": True,
                "default_template": True
            }
        )
        
    def _create_summary_report_template(self) -> ReportTemplate:
        """Create default summary report template"""
        sections = [
            TemplateSection(
                section_type=ReportSection.HEADER,
                title="כותרת דוח סיכום",
                fields=[
                    TemplateField("summary_title", "כותרת הסיכום", "string", True),
                    TemplateField("period", "תקופת הדוח", "string", True),
                    TemplateField("author", "מחבר", "string", True)
                ]
            ),
            TemplateSection(
                section_type=ReportSection.STATISTICS,
                title="נתונים סטטיסטיים",
                fields=[
                    TemplateField("key_metrics", "מדדי מפתח", "dict", True),
                    TemplateField("trends", "מגמות", "list", True),
                    TemplateField("comparisons", "השוואות", "dict", True)
                ]
            )
        ]
        
        return ReportTemplate(
            template_id="summary_report_hebrew",
            name="דוח סיכום בעברית",
            description="תבנית לדוחות סיכום מנהלים",
            template_type=TemplateType.PDF,
            sections=sections,
            metadata={
                "language": "hebrew",
                "rtl_support": True,
                "executive_summary": True
            }
        )
        
    def _create_statistical_report_template(self) -> ReportTemplate:
        """Create default statistical report template"""
        sections = [
            TemplateSection(
                section_type=ReportSection.CHARTS,
                title="תרשימים וגרפים",
                fields=[
                    TemplateField("charts_data", "נתוני תרשימים", "list", True),
                    TemplateField("chart_types", "סוגי תרשימים", "list", True),
                    TemplateField("chart_labels", "תוויות תרשימים", "dict", True)
                ]
            ),
            TemplateSection(
                section_type=ReportSection.STATISTICS,
                title="ניתוח סטטיסטי",
                fields=[
                    TemplateField("statistical_analysis", "ניתוח סטטיסטי", "dict", True),
                    TemplateField("correlations", "קורלציות", "list", True),
                    TemplateField("trends", "מגמות", "list", True)
                ]
            )
        ]
        
        return ReportTemplate(
            template_id="statistical_report_hebrew",
            name="דוח סטטיסטי בעברית",
            description="תבנית לדוחות סטטיסטיים מפורטים",
            template_type=TemplateType.PDF,
            sections=sections,
            metadata={
                "language": "hebrew",
                "rtl_support": True,
                "statistical_analysis": True
            }
        )
        
    def _create_executive_summary_template(self) -> ReportTemplate:
        """Create executive summary template"""
        sections = [
            TemplateSection(
                section_type=ReportSection.SUMMARY,
                title="סיכום מנהלים",
                fields=[
                    TemplateField("executive_summary", "סיכום מנהלים", "string", True),
                    TemplateField("key_findings", "ממצאים עיקריים", "list", True),
                    TemplateField("recommendations", "המלצות", "list", True)
                ]
            )
        ]
        
        return ReportTemplate(
            template_id="executive_summary_hebrew",
            name="סיכום מנהלים בעברית",
            description="תבנית קצרה לסיכום מנהלים",
            template_type=TemplateType.PDF,
            sections=sections,
            metadata={
                "language": "hebrew",
                "rtl_support": True,
                "executive_level": True
            }
        )
        
    def _create_technical_report_template(self) -> ReportTemplate:
        """Create technical report template"""
        sections = [
            TemplateSection(
                section_type=ReportSection.DETAILS,
                title="פרטים טכניים",
                fields=[
                    TemplateField("technical_details", "פרטים טכניים", "dict", True),
                    TemplateField("system_specifications", "מפרטי מערכת", "dict", True),
                    TemplateField("test_results", "תוצאות בדיקות", "list", True)
                ]
            ),
            TemplateSection(
                section_type=ReportSection.APPENDIX,
                title="נספחים",
                fields=[
                    TemplateField("technical_appendix", "נספח טכני", "dict", True),
                    TemplateField("code_samples", "דוגמאות קוד", "list", False),
                    TemplateField("diagrams", "תרשימים", "list", False)
                ]
            )
        ]
        
        return ReportTemplate(
            template_id="technical_report_hebrew",
            name="דוח טכני בעברית",
            description="תבנית לדוחות טכניים מפורטים",
            template_type=TemplateType.PDF,
            sections=sections,
            metadata={
                "language": "hebrew",
                "rtl_support": True,
                "technical_report": True
            }
        )