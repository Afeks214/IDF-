"""
Comprehensive Report Service

Main service orchestrating all reporting functionality including
generation, template management, distribution, and scheduling.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import logging

from app.core.config import get_settings
from app.services.reporting.pdf_generator import PDFReportGenerator
from app.services.reporting.excel_exporter import ExcelExporter
from app.services.reporting.template_manager import ReportTemplateManager, TemplateType
from app.services.reporting.distribution_service import DistributionService
from app.models.core import TestingData

logger = logging.getLogger(__name__)

class ReportService:
    """
    Comprehensive Report Service
    
    Main orchestrator for all reporting functionality:
    - Report generation in multiple formats
    - Template management and customization
    - Automated distribution
    - Performance monitoring
    - Hebrew text processing
    - Security and compliance
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.pdf_generator = PDFReportGenerator()
        self.excel_exporter = ExcelExporter()
        self.template_manager = ReportTemplateManager()
        self.distribution_service = DistributionService()
        
    async def generate_report(
        self,
        template_id: str,
        parameters: Dict[str, Any],
        output_format: str = "pdf"
    ) -> Dict[str, Any]:
        """
        Generate report using specified template and parameters
        
        Args:
            template_id: ID of the template to use
            parameters: Parameters for report generation
            output_format: Output format (pdf, excel, html)
            
        Returns:
            Dictionary containing report result and metadata
        """
        try:
            # Load template
            template = self.template_manager.load_template(template_id)
            if not template:
                raise ValueError(f"Template not found: {template_id}")
                
            # Validate parameters against template
            validation_result = self.template_manager.validate_template_data(template_id, parameters)
            if not validation_result['valid']:
                raise ValueError(f"Parameter validation failed: {validation_result['errors']}")
                
            # Generate report based on format
            if output_format.lower() == "pdf":
                result = await self._generate_pdf_report(template, parameters)
            elif output_format.lower() == "excel":
                result = await self._generate_excel_report(template, parameters)
            elif output_format.lower() == "html":
                result = await self._generate_html_report(template, parameters)
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
                
            # Add metadata
            result['metadata'] = {
                'template_id': template_id,
                'template_name': template.name,
                'generated_at': datetime.now().isoformat(),
                'format': output_format,
                'parameters': parameters
            }
            
            logger.info(f"Generated report using template {template_id} in format {output_format}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {
                'success': False,
                'error': str(e),
                'metadata': {
                    'template_id': template_id,
                    'format': output_format,
                    'failed_at': datetime.now().isoformat()
                }
            }
            
    async def _generate_pdf_report(self, template, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate PDF report"""
        try:
            # Extract data for PDF generation
            inspection_data = parameters.get('inspection_data', [])
            report_config = parameters.get('report_config', {})
            
            # Add template information to config
            report_config['template_name'] = template.name
            report_config['template_id'] = template.template_id
            
            # Generate PDF
            pdf_content = self.pdf_generator.generate_inspection_report(
                inspection_data=inspection_data,
                report_config=report_config
            )
            
            return {
                'success': True,
                'content': pdf_content,
                'format': 'pdf',
                'size': len(pdf_content)
            }
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def _generate_excel_report(self, template, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Excel report"""
        try:
            # Extract data for Excel generation
            inspection_data = parameters.get('inspection_data', [])
            template_name = parameters.get('template_name')
            
            # Generate Excel
            excel_content = self.excel_exporter.export_inspection_data(
                inspection_data=inspection_data,
                template_name=template_name
            )
            
            return {
                'success': True,
                'content': excel_content,
                'format': 'excel',
                'size': len(excel_content)
            }
            
        except Exception as e:
            logger.error(f"Error generating Excel report: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def _generate_html_report(self, template, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate HTML report"""
        try:
            # This would generate HTML reports
            # For now, return a placeholder
            html_content = self._create_html_report(template, parameters)
            
            return {
                'success': True,
                'content': html_content.encode('utf-8'),
                'format': 'html',
                'size': len(html_content.encode('utf-8'))
            }
            
        except Exception as e:
            logger.error(f"Error generating HTML report: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def _create_html_report(self, template, parameters: Dict[str, Any]) -> str:
        """Create HTML report content"""
        try:
            inspection_data = parameters.get('inspection_data', [])
            report_config = parameters.get('report_config', {})
            
            html_content = f"""
            <!DOCTYPE html>
            <html dir="rtl" lang="he">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{template.name}</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        direction: rtl;
                        text-align: right;
                        margin: 20px;
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                        border-bottom: 2px solid #333;
                        padding-bottom: 20px;
                    }}
                    .section {{
                        margin-bottom: 30px;
                    }}
                    .section-title {{
                        font-size: 18px;
                        font-weight: bold;
                        margin-bottom: 15px;
                        color: #333;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-bottom: 20px;
                    }}
                    th, td {{
                        border: 1px solid #ddd;
                        padding: 8px;
                        text-align: right;
                    }}
                    th {{
                        background-color: #f2f2f2;
                        font-weight: bold;
                    }}
                    .summary {{
                        background-color: #f9f9f9;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{template.name}</h1>
                    <p>תאריך יצירה: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                </div>
                
                <div class="section">
                    <div class="section-title">סיכום כללי</div>
                    <div class="summary">
                        <p>סך הכל בדיקות: {len(inspection_data)}</p>
                        <p>תאריך הדוח: {datetime.now().strftime('%d/%m/%Y')}</p>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">תוצאות מפורטות</div>
                    <table>
                        <thead>
                            <tr>
                                <th>מספר מערכת</th>
                                <th>תאריך בדיקה</th>
                                <th>סטטוס</th>
                                <th>הערות</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            # Add inspection data rows
            for item in inspection_data:
                html_content += f"""
                            <tr>
                                <td>{item.get('system_id', '')}</td>
                                <td>{item.get('inspection_date', '')}</td>
                                <td>{item.get('status', '')}</td>
                                <td>{item.get('notes', '')}</td>
                            </tr>
                """
                
            html_content += """
                        </tbody>
                    </table>
                </div>
            </body>
            </html>
            """
            
            return html_content
            
        except Exception as e:
            logger.error(f"Error creating HTML report: {e}")
            return f"<html><body><h1>Error creating report: {str(e)}</h1></body></html>"
            
    async def generate_and_distribute_report(
        self,
        template_id: str,
        parameters: Dict[str, Any],
        distribution_rule_id: str,
        output_format: str = "pdf"
    ) -> Dict[str, Any]:
        """
        Generate and distribute report in one operation
        
        Args:
            template_id: ID of the template to use
            parameters: Parameters for report generation
            distribution_rule_id: ID of the distribution rule to use
            output_format: Output format (pdf, excel, html)
            
        Returns:
            Dictionary containing generation and distribution results
        """
        try:
            # Generate report
            generation_result = await self.generate_report(template_id, parameters, output_format)
            
            if not generation_result['success']:
                return {
                    'success': False,
                    'error': 'Report generation failed',
                    'generation_result': generation_result
                }
                
            # Distribute report
            report_id = f"report_{template_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            distribution_result = await self.distribution_service.distribute_report(
                report_id=report_id,
                report_content=generation_result['content'],
                report_format=output_format,
                distribution_rule_id=distribution_rule_id,
                metadata=generation_result['metadata']
            )
            
            return {
                'success': True,
                'report_id': report_id,
                'generation_result': generation_result,
                'distribution_result': distribution_result
            }
            
        except Exception as e:
            logger.error(f"Error generating and distributing report: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def get_report_data(self, data_source: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Get report data from various sources
        
        Args:
            data_source: Source of the data (database, api, file, etc.)
            filters: Optional filters to apply to the data
            
        Returns:
            List of data records
        """
        try:
            if data_source == "testing_data":
                return await self._get_testing_data(filters or {})
            elif data_source == "inspection_data":
                return await self._get_inspection_data(filters or {})
            elif data_source == "system_status":
                return await self._get_system_status_data(filters or {})
            else:
                raise ValueError(f"Unsupported data source: {data_source}")
                
        except Exception as e:
            logger.error(f"Error getting report data: {e}")
            return []
            
    async def _get_testing_data(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get testing data for reports"""
        try:
            # This would query the database for testing data
            # For now, return sample data
            sample_data = [
                {
                    'system_id': 'SYS001',
                    'inspection_date': '2024-01-15',
                    'inspector_name': 'דני כהן',
                    'status': 'עבר',
                    'score': 95,
                    'notes': 'בדיקה עברה בהצלחה',
                    'location': 'בניין א',
                    'category': 'אבטחה',
                    'priority': 'גבוה'
                },
                {
                    'system_id': 'SYS002',
                    'inspection_date': '2024-01-16',
                    'inspector_name': 'שרה לוי',
                    'status': 'נכשל',
                    'score': 65,
                    'notes': 'נדרש תיקון מערכת',
                    'location': 'בניין ב',
                    'category': 'רשת',
                    'priority': 'בינוני'
                }
            ]
            
            return sample_data
            
        except Exception as e:
            logger.error(f"Error getting testing data: {e}")
            return []
            
    async def _get_inspection_data(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get inspection data for reports"""
        try:
            # This would query the database for inspection data
            # For now, return sample data
            sample_data = [
                {
                    'inspection_id': 'INS001',
                    'system_id': 'SYS001',
                    'inspection_date': '2024-01-15',
                    'inspector_name': 'משה דוד',
                    'status': 'עבר',
                    'findings': 'מערכת פועלת כראוי',
                    'recommendations': 'המשך ניטור'
                },
                {
                    'inspection_id': 'INS002',
                    'system_id': 'SYS002',
                    'inspection_date': '2024-01-16',
                    'inspector_name': 'רחל אברהם',
                    'status': 'נכשל',
                    'findings': 'בעיה בחיבור רשת',
                    'recommendations': 'החלפת כבלי רשת'
                }
            ]
            
            return sample_data
            
        except Exception as e:
            logger.error(f"Error getting inspection data: {e}")
            return []
            
    async def _get_system_status_data(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get system status data for reports"""
        try:
            # This would query the database for system status
            # For now, return sample data
            sample_data = [
                {
                    'system_id': 'SYS001',
                    'system_name': 'מערכת אבטחה מרכזית',
                    'status': 'פעיל',
                    'uptime': '99.9%',
                    'last_check': '2024-01-17 10:00:00',
                    'issues': 0
                },
                {
                    'system_id': 'SYS002',
                    'system_name': 'מערכת רשת',
                    'status': 'בתיקון',
                    'uptime': '95.2%',
                    'last_check': '2024-01-17 09:30:00',
                    'issues': 2
                }
            ]
            
            return sample_data
            
        except Exception as e:
            logger.error(f"Error getting system status data: {e}")
            return []
            
    def create_report_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new report template
        
        Args:
            template_data: Template configuration data
            
        Returns:
            Result of template creation
        """
        try:
            template = self.template_manager.create_template(
                template_id=template_data['template_id'],
                name=template_data['name'],
                description=template_data['description'],
                template_type=TemplateType(template_data['template_type']),
                sections=template_data['sections'],
                metadata=template_data.get('metadata', {})
            )
            
            return {
                'success': True,
                'template': {
                    'template_id': template.template_id,
                    'name': template.name,
                    'description': template.description,
                    'template_type': template.template_type.value,
                    'created_at': template.created_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating report template: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """Get list of available report templates"""
        try:
            templates = self.template_manager.list_templates()
            return templates
            
        except Exception as e:
            logger.error(f"Error getting available templates: {e}")
            return []
            
    def get_template_details(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific template"""
        try:
            template = self.template_manager.load_template(template_id)
            if not template:
                return None
                
            return {
                'template_id': template.template_id,
                'name': template.name,
                'description': template.description,
                'template_type': template.template_type.value,
                'sections': [
                    {
                        'section_type': section.section_type.value,
                        'title': section.title,
                        'fields': [
                            {
                                'name': field.name,
                                'display_name': field.display_name,
                                'data_type': field.data_type,
                                'required': field.required
                            }
                            for field in section.fields
                        ]
                    }
                    for section in template.sections
                ],
                'metadata': template.metadata,
                'created_at': template.created_at.isoformat(),
                'updated_at': template.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting template details: {e}")
            return None
            
    async def preview_report(
        self,
        template_id: str,
        parameters: Dict[str, Any],
        output_format: str = "html"
    ) -> Dict[str, Any]:
        """
        Generate a preview of the report without full processing
        
        Args:
            template_id: ID of the template to use
            parameters: Parameters for report generation
            output_format: Output format for preview
            
        Returns:
            Preview result
        """
        try:
            # Load template
            template = self.template_manager.load_template(template_id)
            if not template:
                raise ValueError(f"Template not found: {template_id}")
                
            # Generate preview with limited data
            preview_parameters = parameters.copy()
            
            # Limit data for preview
            if 'inspection_data' in preview_parameters:
                preview_parameters['inspection_data'] = preview_parameters['inspection_data'][:5]
                
            # Generate preview
            preview_result = await self.generate_report(template_id, preview_parameters, output_format)
            
            # Add preview flag
            preview_result['is_preview'] = True
            preview_result['preview_generated_at'] = datetime.now().isoformat()
            
            return preview_result
            
        except Exception as e:
            logger.error(f"Error generating report preview: {e}")
            return {
                'success': False,
                'error': str(e),
                'is_preview': True
            }
            
    def get_report_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get report generation statistics
        
        Args:
            days: Number of days to include in statistics
            
        Returns:
            Statistics data
        """
        try:
            # This would query the database for statistics
            # For now, return sample statistics
            statistics = {
                'total_reports_generated': 156,
                'reports_last_30_days': 45,
                'most_used_templates': [
                    {'template_id': 'inspection_report_hebrew', 'count': 23},
                    {'template_id': 'summary_report_hebrew', 'count': 12},
                    {'template_id': 'technical_report_hebrew', 'count': 10}
                ],
                'formats_distribution': {
                    'pdf': 78,
                    'excel': 65,
                    'html': 13
                },
                'success_rate': 96.8,
                'average_generation_time': 2.3,
                'period_start': (datetime.now() - timedelta(days=days)).isoformat(),
                'period_end': datetime.now().isoformat()
            }
            
            return statistics
            
        except Exception as e:
            logger.error(f"Error getting report statistics: {e}")
            return {
                'total_reports_generated': 0,
                'reports_last_30_days': 0,
                'most_used_templates': [],
                'formats_distribution': {},
                'success_rate': 0,
                'average_generation_time': 0
            }