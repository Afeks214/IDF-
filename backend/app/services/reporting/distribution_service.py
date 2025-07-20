"""
Automated Report Distribution Service

Advanced distribution system for automated report delivery with multiple channels,
security controls, and delivery tracking.
"""

import asyncio
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging
import json
import hashlib
import base64

from app.core.config import get_settings
from app.core.security import encrypt_data, decrypt_data
from app.utils.hebrew import HebrewTextProcessor

logger = logging.getLogger(__name__)

class DistributionChannel(Enum):
    """Distribution channels supported by the system"""
    EMAIL = "email"
    SECURE_EMAIL = "secure_email"
    FILE_SYSTEM = "file_system"
    SECURE_PORTAL = "secure_portal"
    FTP = "ftp"
    SFTP = "sftp"
    API = "api"
    WEBHOOK = "webhook"

class DeliveryStatus(Enum):
    """Delivery status types"""
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class SecurityLevel(Enum):
    """Security levels for report distribution"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
    TOP_SECRET = "top_secret"

@dataclass
class Recipient:
    """Report recipient information"""
    email: str
    name: str
    role: str
    security_clearance: SecurityLevel
    preferred_language: str = "hebrew"
    notification_preferences: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.notification_preferences is None:
            self.notification_preferences = {}

@dataclass
class DistributionRule:
    """Distribution rule configuration"""
    rule_id: str
    name: str
    description: str
    channels: List[DistributionChannel]
    recipients: List[Recipient]
    conditions: List[str] = None
    schedule: Dict[str, Any] = None
    security_requirements: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.conditions is None:
            self.conditions = []
        if self.schedule is None:
            self.schedule = {}
        if self.security_requirements is None:
            self.security_requirements = {}

@dataclass
class DeliveryRecord:
    """Delivery tracking record"""
    delivery_id: str
    report_id: str
    recipient_email: str
    channel: DistributionChannel
    status: DeliveryStatus
    created_at: datetime
    updated_at: datetime
    delivery_attempts: int = 0
    error_message: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class DistributionService:
    """
    Advanced Automated Report Distribution Service
    
    Features:
    - Multi-channel distribution (email, secure portal, file system)
    - Security-aware distribution with clearance validation
    - Delivery tracking and retry mechanisms
    - Automated scheduling and recurring distributions
    - Hebrew message templates
    - Encrypted delivery for sensitive reports
    - Audit trail and compliance logging
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.hebrew_processor = HebrewTextProcessor()
        self.distribution_rules = {}
        self.delivery_records = {}
        self._load_distribution_rules()
        self._setup_email_client()
        
    def _load_distribution_rules(self):
        """Load distribution rules from configuration"""
        try:
            rules_file = Path(__file__).parent / "distribution_rules.json"
            if rules_file.exists():
                with open(rules_file, 'r', encoding='utf-8') as f:
                    rules_data = json.load(f)
                    
                for rule_data in rules_data:
                    rule = self._dict_to_distribution_rule(rule_data)
                    self.distribution_rules[rule.rule_id] = rule
                    
            logger.info(f"Loaded {len(self.distribution_rules)} distribution rules")
            
        except Exception as e:
            logger.error(f"Error loading distribution rules: {e}")
            
    def _setup_email_client(self):
        """Setup email client for report distribution"""
        try:
            self.smtp_server = getattr(self.settings, 'SMTP_SERVER', 'localhost')
            self.smtp_port = getattr(self.settings, 'SMTP_PORT', 587)
            self.smtp_username = getattr(self.settings, 'SMTP_USERNAME', '')
            self.smtp_password = getattr(self.settings, 'SMTP_PASSWORD', '')
            self.smtp_use_tls = getattr(self.settings, 'SMTP_USE_TLS', True)
            
            logger.info("Email client configured successfully")
            
        except Exception as e:
            logger.error(f"Error setting up email client: {e}")
            
    async def distribute_report(
        self,
        report_id: str,
        report_content: bytes,
        report_format: str,
        distribution_rule_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Distribute report using specified distribution rule
        
        Args:
            report_id: Unique report identifier
            report_content: Report content as bytes
            report_format: Report format (pdf, excel, etc.)
            distribution_rule_id: Distribution rule to use
            metadata: Additional metadata for distribution
            
        Returns:
            Distribution result with delivery tracking information
        """
        try:
            # Get distribution rule
            distribution_rule = self.distribution_rules.get(distribution_rule_id)
            if not distribution_rule:
                raise ValueError(f"Distribution rule not found: {distribution_rule_id}")
                
            # Validate security requirements
            if not self._validate_security_requirements(metadata or {}, distribution_rule.security_requirements):
                raise ValueError("Security requirements not met for distribution")
                
            # Create distribution batch
            batch_id = self._generate_batch_id()
            distribution_results = {
                'batch_id': batch_id,
                'report_id': report_id,
                'rule_id': distribution_rule_id,
                'started_at': datetime.now().isoformat(),
                'deliveries': []
            }
            
            # Distribute to each recipient
            for recipient in distribution_rule.recipients:
                # Check security clearance
                if not self._validate_recipient_clearance(recipient, metadata or {}):
                    logger.warning(f"Recipient {recipient.email} lacks required clearance")
                    continue
                    
                # Distribute via each channel
                for channel in distribution_rule.channels:
                    delivery_result = await self._distribute_via_channel(
                        report_id=report_id,
                        report_content=report_content,
                        report_format=report_format,
                        recipient=recipient,
                        channel=channel,
                        metadata=metadata or {}
                    )
                    distribution_results['deliveries'].append(delivery_result)
                    
            # Update completion timestamp
            distribution_results['completed_at'] = datetime.now().isoformat()
            
            # Log distribution activity
            self._log_distribution_activity(distribution_results)
            
            logger.info(f"Distributed report {report_id} to {len(distribution_results['deliveries'])} recipients")
            return distribution_results
            
        except Exception as e:
            logger.error(f"Error distributing report: {e}")
            raise
            
    async def _distribute_via_channel(
        self,
        report_id: str,
        report_content: bytes,
        report_format: str,
        recipient: Recipient,
        channel: DistributionChannel,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Distribute report via specific channel"""
        try:
            delivery_id = self._generate_delivery_id()
            
            # Create delivery record
            delivery_record = DeliveryRecord(
                delivery_id=delivery_id,
                report_id=report_id,
                recipient_email=recipient.email,
                channel=channel,
                status=DeliveryStatus.PROCESSING,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata=metadata
            )
            
            # Store delivery record
            self.delivery_records[delivery_id] = delivery_record
            
            # Distribute based on channel
            if channel == DistributionChannel.EMAIL:
                result = await self._distribute_via_email(
                    report_content, report_format, recipient, delivery_record
                )
            elif channel == DistributionChannel.SECURE_EMAIL:
                result = await self._distribute_via_secure_email(
                    report_content, report_format, recipient, delivery_record
                )
            elif channel == DistributionChannel.FILE_SYSTEM:
                result = await self._distribute_via_file_system(
                    report_content, report_format, recipient, delivery_record
                )
            elif channel == DistributionChannel.SECURE_PORTAL:
                result = await self._distribute_via_secure_portal(
                    report_content, report_format, recipient, delivery_record
                )
            else:
                raise ValueError(f"Unsupported distribution channel: {channel}")
                
            # Update delivery status
            delivery_record.status = DeliveryStatus.DELIVERED if result['success'] else DeliveryStatus.FAILED
            delivery_record.updated_at = datetime.now()
            
            if not result['success']:
                delivery_record.error_message = result.get('error', 'Unknown error')
                
            return {
                'delivery_id': delivery_id,
                'recipient': recipient.email,
                'channel': channel.value,
                'status': delivery_record.status.value,
                'success': result['success'],
                'message': result.get('message', ''),
                'error': result.get('error', '')
            }
            
        except Exception as e:
            logger.error(f"Error distributing via {channel}: {e}")
            return {
                'delivery_id': delivery_id,
                'recipient': recipient.email,
                'channel': channel.value,
                'status': DeliveryStatus.FAILED.value,
                'success': False,
                'error': str(e)
            }
            
    async def _distribute_via_email(
        self,
        report_content: bytes,
        report_format: str,
        recipient: Recipient,
        delivery_record: DeliveryRecord
    ) -> Dict[str, Any]:
        """Distribute report via email"""
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = recipient.email
            msg['Subject'] = self._get_email_subject(delivery_record.report_id, recipient.preferred_language)
            
            # Create email body
            body = self._get_email_body(delivery_record.report_id, recipient)
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Attach report
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(report_content)
            encoders.encode_base64(attachment)
            
            filename = f"report_{delivery_record.report_id}.{report_format}"
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            msg.attach(attachment)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls(context=context)
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                
            return {
                'success': True,
                'message': f'Email sent successfully to {recipient.email}'
            }
            
        except Exception as e:
            logger.error(f"Error sending email to {recipient.email}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def _distribute_via_secure_email(
        self,
        report_content: bytes,
        report_format: str,
        recipient: Recipient,
        delivery_record: DeliveryRecord
    ) -> Dict[str, Any]:
        """Distribute report via secure encrypted email"""
        try:
            # Encrypt report content
            encrypted_content = encrypt_data(report_content)
            
            # Create secure email message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = recipient.email
            msg['Subject'] = self._get_secure_email_subject(delivery_record.report_id, recipient.preferred_language)
            
            # Create secure email body with decryption instructions
            body = self._get_secure_email_body(delivery_record.report_id, recipient)
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Attach encrypted report
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(encrypted_content)
            encoders.encode_base64(attachment)
            
            filename = f"secure_report_{delivery_record.report_id}.encrypted"
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            msg.attach(attachment)
            
            # Send secure email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls(context=context)
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                
            return {
                'success': True,
                'message': f'Secure email sent successfully to {recipient.email}'
            }
            
        except Exception as e:
            logger.error(f"Error sending secure email to {recipient.email}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def _distribute_via_file_system(
        self,
        report_content: bytes,
        report_format: str,
        recipient: Recipient,
        delivery_record: DeliveryRecord
    ) -> Dict[str, Any]:
        """Distribute report via file system"""
        try:
            # Create recipient directory
            reports_dir = Path(__file__).parent / "distributed_reports" / recipient.email
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # Save report file
            filename = f"report_{delivery_record.report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{report_format}"
            file_path = reports_dir / filename
            
            with open(file_path, 'wb') as f:
                f.write(report_content)
                
            # Create metadata file
            metadata_file = reports_dir / f"{filename}.metadata.json"
            metadata = {
                'report_id': delivery_record.report_id,
                'recipient': recipient.email,
                'created_at': datetime.now().isoformat(),
                'file_size': len(report_content),
                'format': report_format
            }
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
            return {
                'success': True,
                'message': f'Report saved to file system: {file_path}',
                'file_path': str(file_path)
            }
            
        except Exception as e:
            logger.error(f"Error saving report to file system: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def _distribute_via_secure_portal(
        self,
        report_content: bytes,
        report_format: str,
        recipient: Recipient,
        delivery_record: DeliveryRecord
    ) -> Dict[str, Any]:
        """Distribute report via secure portal"""
        try:
            # Generate secure access token
            access_token = self._generate_secure_access_token(recipient.email, delivery_record.report_id)
            
            # Store report in secure portal
            portal_storage = Path(__file__).parent / "secure_portal" / access_token
            portal_storage.mkdir(parents=True, exist_ok=True)
            
            # Encrypt and store report
            encrypted_content = encrypt_data(report_content)
            report_file = portal_storage / f"report.{report_format}.encrypted"
            
            with open(report_file, 'wb') as f:
                f.write(encrypted_content)
                
            # Create access record
            access_record = {
                'report_id': delivery_record.report_id,
                'recipient_email': recipient.email,
                'access_token': access_token,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=7)).isoformat(),
                'download_count': 0,
                'max_downloads': 3
            }
            
            access_file = portal_storage / "access.json"
            with open(access_file, 'w', encoding='utf-8') as f:
                json.dump(access_record, f, ensure_ascii=False, indent=2)
                
            # Send notification email with access link
            await self._send_portal_notification(recipient, access_token, delivery_record.report_id)
            
            return {
                'success': True,
                'message': f'Report uploaded to secure portal',
                'access_token': access_token,
                'portal_url': f"{self.settings.BASE_URL}/secure-portal/{access_token}"
            }
            
        except Exception as e:
            logger.error(f"Error uploading to secure portal: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def _send_portal_notification(self, recipient: Recipient, access_token: str, report_id: str):
        """Send notification email for secure portal access"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = recipient.email
            msg['Subject'] = self._get_portal_notification_subject(report_id, recipient.preferred_language)
            
            # Create notification body
            body = self._get_portal_notification_body(
                recipient, access_token, report_id
            )
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Send notification
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls(context=context)
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                
            logger.info(f"Portal notification sent to {recipient.email}")
            
        except Exception as e:
            logger.error(f"Error sending portal notification: {e}")
            
    def _get_email_subject(self, report_id: str, language: str) -> str:
        """Get email subject based on language"""
        if language == 'hebrew':
            return f"דוח מערכת IDF - {report_id}"
        else:
            return f"IDF System Report - {report_id}"
            
    def _get_secure_email_subject(self, report_id: str, language: str) -> str:
        """Get secure email subject based on language"""
        if language == 'hebrew':
            return f"דוח מאובטח - {report_id} - סודי"
        else:
            return f"Secure Report - {report_id} - Confidential"
            
    def _get_portal_notification_subject(self, report_id: str, language: str) -> str:
        """Get portal notification subject based on language"""
        if language == 'hebrew':
            return f"דוח זמין בפורטל המאובטח - {report_id}"
        else:
            return f"Report Available in Secure Portal - {report_id}"
            
    def _get_email_body(self, report_id: str, recipient: Recipient) -> str:
        """Get email body based on recipient language"""
        if recipient.preferred_language == 'hebrew':
            return f"""
שלום {recipient.name},

מצורף דוח מערכת IDF מספר {report_id}.

הדוח מכיל מידע חשוב ועדכני על מצב המערכות.

בברכה,
מערכת IDF
            """
        else:
            return f"""
Hello {recipient.name},

Please find attached the IDF system report {report_id}.

The report contains important and current information about system status.

Best regards,
IDF System
            """
            
    def _get_secure_email_body(self, report_id: str, recipient: Recipient) -> str:
        """Get secure email body with decryption instructions"""
        if recipient.preferred_language == 'hebrew':
            return f"""
שלום {recipient.name},

מצורף דוח מאובטח מספר {report_id}.

הדוח מוצפן ודורש פתיחה באמצעות מערכת האבטחה.

לפתיחת הדוח:
1. שמור את הקובץ המצורף
2. השתמש בכלי הפענוח של המערכת
3. הזן את קוד הגישה שלך

בברכה,
מערכת IDF
            """
        else:
            return f"""
Hello {recipient.name},

Please find attached the secure report {report_id}.

The report is encrypted and requires opening through the security system.

To open the report:
1. Save the attached file
2. Use the system decryption tool
3. Enter your access code

Best regards,
IDF System
            """
            
    def _get_portal_notification_body(self, recipient: Recipient, access_token: str, report_id: str) -> str:
        """Get portal notification body"""
        portal_url = f"{self.settings.BASE_URL}/secure-portal/{access_token}"
        
        if recipient.preferred_language == 'hebrew':
            return f"""
שלום {recipient.name},

דוח מספר {report_id} זמין כעת בפורטל המאובטח.

לגישה לדוח:
קישור: {portal_url}
קוד גישה: {access_token}

הקישור תקף למשך 7 ימים ומאפשר עד 3 הורדות.

בברכה,
מערכת IDF
            """
        else:
            return f"""
Hello {recipient.name},

Report {report_id} is now available in the secure portal.

To access the report:
Link: {portal_url}
Access code: {access_token}

The link is valid for 7 days and allows up to 3 downloads.

Best regards,
IDF System
            """
            
    def _validate_security_requirements(self, metadata: Dict[str, Any], requirements: Dict[str, Any]) -> bool:
        """Validate security requirements for distribution"""
        try:
            # Check minimum security level
            min_security_level = requirements.get('min_security_level')
            if min_security_level:
                report_security_level = metadata.get('security_level', 'public')
                if not self._compare_security_levels(report_security_level, min_security_level):
                    return False
                    
            # Check required approvals
            required_approvals = requirements.get('required_approvals', [])
            report_approvals = metadata.get('approvals', [])
            
            for required_approval in required_approvals:
                if required_approval not in report_approvals:
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Error validating security requirements: {e}")
            return False
            
    def _validate_recipient_clearance(self, recipient: Recipient, metadata: Dict[str, Any]) -> bool:
        """Validate recipient security clearance"""
        try:
            report_security_level = metadata.get('security_level', 'public')
            recipient_clearance = recipient.security_clearance.value
            
            return self._compare_security_levels(recipient_clearance, report_security_level)
            
        except Exception as e:
            logger.error(f"Error validating recipient clearance: {e}")
            return False
            
    def _compare_security_levels(self, user_level: str, required_level: str) -> bool:
        """Compare security levels"""
        levels = ['public', 'internal', 'confidential', 'secret', 'top_secret']
        
        try:
            user_index = levels.index(user_level.lower())
            required_index = levels.index(required_level.lower())
            return user_index >= required_index
        except ValueError:
            return False
            
    def _generate_batch_id(self) -> str:
        """Generate unique batch ID"""
        return f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"
        
    def _generate_delivery_id(self) -> str:
        """Generate unique delivery ID"""
        return f"delivery_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"
        
    def _generate_secure_access_token(self, email: str, report_id: str) -> str:
        """Generate secure access token"""
        token_data = f"{email}:{report_id}:{datetime.now().isoformat()}"
        return base64.urlsafe_b64encode(hashlib.sha256(token_data.encode()).digest()).decode()[:32]
        
    def _dict_to_distribution_rule(self, rule_data: Dict[str, Any]) -> DistributionRule:
        """Convert dictionary to DistributionRule object"""
        recipients = []
        for recipient_data in rule_data.get('recipients', []):
            recipient = Recipient(
                email=recipient_data['email'],
                name=recipient_data['name'],
                role=recipient_data['role'],
                security_clearance=SecurityLevel(recipient_data['security_clearance']),
                preferred_language=recipient_data.get('preferred_language', 'hebrew'),
                notification_preferences=recipient_data.get('notification_preferences', {})
            )
            recipients.append(recipient)
            
        channels = [DistributionChannel(ch) for ch in rule_data.get('channels', [])]
        
        return DistributionRule(
            rule_id=rule_data['rule_id'],
            name=rule_data['name'],
            description=rule_data['description'],
            channels=channels,
            recipients=recipients,
            conditions=rule_data.get('conditions', []),
            schedule=rule_data.get('schedule', {}),
            security_requirements=rule_data.get('security_requirements', {})
        )
        
    def _log_distribution_activity(self, distribution_results: Dict[str, Any]):
        """Log distribution activity for audit trail"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'activity': 'report_distribution',
                'batch_id': distribution_results['batch_id'],
                'report_id': distribution_results['report_id'],
                'rule_id': distribution_results['rule_id'],
                'delivery_count': len(distribution_results['deliveries']),
                'success_count': sum(1 for d in distribution_results['deliveries'] if d['success']),
                'failure_count': sum(1 for d in distribution_results['deliveries'] if not d['success'])
            }
            
            # Log to audit system
            logger.info(f"Distribution activity: {json.dumps(log_entry, ensure_ascii=False)}")
            
        except Exception as e:
            logger.error(f"Error logging distribution activity: {e}")
            
    def get_delivery_status(self, delivery_id: str) -> Optional[Dict[str, Any]]:
        """Get delivery status by ID"""
        try:
            delivery_record = self.delivery_records.get(delivery_id)
            if not delivery_record:
                return None
                
            return {
                'delivery_id': delivery_record.delivery_id,
                'report_id': delivery_record.report_id,
                'recipient_email': delivery_record.recipient_email,
                'channel': delivery_record.channel.value,
                'status': delivery_record.status.value,
                'created_at': delivery_record.created_at.isoformat(),
                'updated_at': delivery_record.updated_at.isoformat(),
                'delivery_attempts': delivery_record.delivery_attempts,
                'error_message': delivery_record.error_message
            }
            
        except Exception as e:
            logger.error(f"Error getting delivery status: {e}")
            return None
            
    def retry_failed_delivery(self, delivery_id: str) -> Dict[str, Any]:
        """Retry failed delivery"""
        try:
            delivery_record = self.delivery_records.get(delivery_id)
            if not delivery_record:
                return {'success': False, 'error': 'Delivery record not found'}
                
            if delivery_record.status != DeliveryStatus.FAILED:
                return {'success': False, 'error': 'Delivery is not in failed state'}
                
            # Increment retry count
            delivery_record.delivery_attempts += 1
            delivery_record.status = DeliveryStatus.PROCESSING
            delivery_record.updated_at = datetime.now()
            
            # This would trigger the actual retry logic
            # For now, just update the status
            
            return {
                'success': True,
                'message': f'Retry initiated for delivery {delivery_id}',
                'attempt_number': delivery_record.delivery_attempts
            }
            
        except Exception as e:
            logger.error(f"Error retrying delivery: {e}")
            return {'success': False, 'error': str(e)}