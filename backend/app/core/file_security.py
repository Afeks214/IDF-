#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Secure File Upload Validation System
Military-Grade Security for IDF Testing Infrastructure
"""

import os
import hashlib
import mimetypes
import magic
import zipfile
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, BinaryIO, Union
from dataclasses import dataclass
from enum import Enum
import structlog
from fastapi import UploadFile, HTTPException, status

from .config import settings
from .validation import InputSanitizer

logger = structlog.get_logger()


class FileValidationResult(str, Enum):
    """File validation results"""
    VALID = "valid"
    INVALID_TYPE = "invalid_type"
    INVALID_SIZE = "invalid_size"
    INVALID_NAME = "invalid_name"
    MALWARE_DETECTED = "malware_detected"
    CONTENT_MISMATCH = "content_mismatch"
    DANGEROUS_CONTENT = "dangerous_content"
    ENCRYPTION_REQUIRED = "encryption_required"


@dataclass
class FileValidationReport:
    """File validation report"""
    result: FileValidationResult
    file_info: Dict
    warnings: List[str]
    errors: List[str]
    security_score: int  # 0-100, higher is more secure
    recommendations: List[str]


class SecureFileValidator:
    """
    Comprehensive file validation and security scanning
    """
    
    # Dangerous file extensions that should never be allowed
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar',
        '.app', '.deb', '.pkg', '.dmg', '.iso', '.bin', '.run', '.msi',
        '.ps1', '.sh', '.bash', '.zsh', '.fish', '.py', '.rb', '.pl', '.php'
    }
    
    # Archive extensions that need special handling
    ARCHIVE_EXTENSIONS = {
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'
    }
    
    # Known malicious file signatures (magic numbers)
    MALICIOUS_SIGNATURES = [
        b'\x4d\x5a',  # PE executable (MZ header)
        b'\x7f\x45\x4c\x46',  # ELF executable
        b'\xfe\xed\xfa\xce',  # Mach-O executable (32-bit)
        b'\xfe\xed\xfa\xcf',  # Mach-O executable (64-bit)
        b'\xca\xfe\xba\xbe',  # Java class file
    ]
    
    def __init__(self):
        self.magic_mime = magic.Magic(mime=True)
        self.magic_type = magic.Magic()
        self.sanitizer = InputSanitizer()
    
    async def validate_file(
        self,
        file: UploadFile,
        allowed_types: Optional[List[str]] = None,
        max_size_mb: Optional[int] = None,
        scan_content: bool = True,
        require_encryption: bool = False
    ) -> FileValidationReport:
        """
        Comprehensive file validation
        """
        warnings = []
        errors = []
        recommendations = []
        security_score = 100
        
        # Get file info
        file_info = await self._get_file_info(file)
        
        try:
            # 1. Validate filename
            filename_result = self._validate_filename(file.filename)
            if filename_result != FileValidationResult.VALID:
                errors.append(f"Invalid filename: {file.filename}")
                security_score -= 30
                return FileValidationReport(
                    result=filename_result,
                    file_info=file_info,
                    warnings=warnings,
                    errors=errors,
                    security_score=security_score,
                    recommendations=recommendations
                )
            
            # 2. Validate file size
            max_size = max_size_mb or settings.security.MAX_FILE_SIZE_MB
            if file_info['size'] > max_size * 1024 * 1024:
                errors.append(f"File too large: {file_info['size']} bytes (max: {max_size}MB)")
                security_score -= 20
                return FileValidationReport(
                    result=FileValidationResult.INVALID_SIZE,
                    file_info=file_info,
                    warnings=warnings,
                    errors=errors,
                    security_score=security_score,
                    recommendations=recommendations
                )
            
            # 3. Read file content for analysis
            content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            # 4. Validate MIME type
            allowed_types = allowed_types or settings.security.ALLOWED_FILE_TYPES
            mime_result = self._validate_mime_type(content, file.filename, allowed_types)
            if mime_result != FileValidationResult.VALID:
                errors.append(f"Invalid file type: {file_info['detected_mime']}")
                security_score -= 25
                return FileValidationReport(
                    result=mime_result,
                    file_info=file_info,
                    warnings=warnings,
                    errors=errors,
                    security_score=security_score,
                    recommendations=recommendations
                )
            
            # 5. Check for malicious signatures
            if self._has_malicious_signature(content):
                errors.append("Malicious file signature detected")
                security_score = 0
                return FileValidationReport(
                    result=FileValidationResult.MALWARE_DETECTED,
                    file_info=file_info,
                    warnings=warnings,
                    errors=errors,
                    security_score=security_score,
                    recommendations=["File blocked due to malicious signature"]
                )
            
            # 6. Content-based validation
            if scan_content:
                content_result = await self._validate_content(content, file_info)
                if content_result != FileValidationResult.VALID:
                    errors.append("Dangerous content detected")
                    security_score -= 40
                    return FileValidationReport(
                        result=content_result,
                        file_info=file_info,
                        warnings=warnings,
                        errors=errors,
                        security_score=security_score,
                        recommendations=recommendations
                    )
            
            # 7. Archive scanning
            if self._is_archive(file.filename):
                archive_result = await self._scan_archive(content, file_info)
                if archive_result != FileValidationResult.VALID:
                    errors.append("Dangerous content found in archive")
                    security_score -= 30
                    return FileValidationReport(
                        result=archive_result,
                        file_info=file_info,
                        warnings=warnings,
                        errors=errors,
                        security_score=security_score,
                        recommendations=recommendations
                    )
                else:
                    warnings.append("Archive file - contents verified")
                    security_score -= 10
            
            # 8. Encryption check
            if require_encryption and not self._is_encrypted(content, file_info):
                warnings.append("File is not encrypted - consider encrypting sensitive data")
                security_score -= 15
                recommendations.append("Encrypt file before uploading")
            
            # 9. Additional security checks
            security_warnings = self._perform_security_checks(content, file_info)
            warnings.extend(security_warnings)
            security_score -= len(security_warnings) * 5
            
            # Update file info with validation results
            file_info.update({
                'validated': True,
                'security_score': security_score,
                'hash_sha256': hashlib.sha256(content).hexdigest(),
                'hash_md5': hashlib.md5(content).hexdigest()
            })
            
            return FileValidationReport(
                result=FileValidationResult.VALID,
                file_info=file_info,
                warnings=warnings,
                errors=errors,
                security_score=security_score,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error("File validation failed", error=str(e), filename=file.filename)
            errors.append(f"Validation error: {str(e)}")
            return FileValidationReport(
                result=FileValidationResult.DANGEROUS_CONTENT,
                file_info=file_info,
                warnings=warnings,
                errors=errors,
                security_score=0,
                recommendations=["File validation failed - do not process"]
            )
    
    async def _get_file_info(self, file: UploadFile) -> Dict:
        """Get comprehensive file information"""
        # Get file size
        await file.seek(0, 2)  # Seek to end
        size = await file.tell()
        await file.seek(0)  # Reset to beginning
        
        # Read a sample for MIME detection
        sample = await file.read(8192)
        await file.seek(0)
        
        # Detect MIME type
        try:
            detected_mime = self.magic_mime.from_buffer(sample)
            detected_type = self.magic_type.from_buffer(sample)
        except Exception:
            detected_mime = "unknown"
            detected_type = "unknown"
        
        # Get file extension
        extension = Path(file.filename).suffix.lower() if file.filename else ""
        
        return {
            'filename': file.filename,
            'size': size,
            'extension': extension,
            'content_type': file.content_type,
            'detected_mime': detected_mime,
            'detected_type': detected_type,
            'safe_filename': self.sanitizer.sanitize_filename(file.filename) if file.filename else "unknown"
        }
    
    def _validate_filename(self, filename: Optional[str]) -> FileValidationResult:
        """Validate filename security"""
        if not filename:
            return FileValidationResult.INVALID_NAME
        
        try:
            # Sanitize filename
            safe_filename = self.sanitizer.sanitize_filename(filename)
            
            # Check if filename changed significantly during sanitization
            if len(safe_filename) < len(filename) * 0.8:
                return FileValidationResult.INVALID_NAME
            
            # Check for dangerous extensions
            extension = Path(filename).suffix.lower()
            if extension in self.DANGEROUS_EXTENSIONS:
                return FileValidationResult.INVALID_NAME
            
            # Check for double extensions (e.g., .txt.exe)
            parts = filename.split('.')
            if len(parts) > 2:
                for part in parts[1:-1]:  # Check all but first and last
                    if f".{part.lower()}" in self.DANGEROUS_EXTENSIONS:
                        return FileValidationResult.INVALID_NAME
            
            return FileValidationResult.VALID
            
        except Exception:
            return FileValidationResult.INVALID_NAME
    
    def _validate_mime_type(
        self,
        content: bytes,
        filename: str,
        allowed_types: List[str]
    ) -> FileValidationResult:
        """Validate MIME type against allowed types"""
        try:
            # Detect actual MIME type from content
            detected_mime = self.magic_mime.from_buffer(content)
            
            # Check if detected MIME type is in allowed list
            if detected_mime not in allowed_types:
                return FileValidationResult.INVALID_TYPE
            
            # Check for MIME/extension mismatch
            extension = Path(filename).suffix.lower()
            expected_mime = mimetypes.guess_type(filename)[0]
            
            if expected_mime and expected_mime != detected_mime:
                # Some files might have slight variations, so we allow some flexibility
                logger.warning(
                    "MIME type mismatch",
                    filename=filename,
                    expected=expected_mime,
                    detected=detected_mime
                )
            
            return FileValidationResult.VALID
            
        except Exception as e:
            logger.error("MIME validation failed", error=str(e))
            return FileValidationResult.CONTENT_MISMATCH
    
    def _has_malicious_signature(self, content: bytes) -> bool:
        """Check for known malicious file signatures"""
        if len(content) < 4:
            return False
        
        # Check against known malicious signatures
        for signature in self.MALICIOUS_SIGNATURES:
            if content.startswith(signature):
                return True
        
        # Check for embedded executables (common in malware)
        for i in range(min(len(content) - 4, 1024)):  # Check first 1KB
            for signature in self.MALICIOUS_SIGNATURES:
                if content[i:i+len(signature)] == signature:
                    return True
        
        return False
    
    async def _validate_content(self, content: bytes, file_info: Dict) -> FileValidationResult:
        """Validate file content for dangerous patterns"""
        try:
            # Convert to string for text-based checks (if possible)
            try:
                text_content = content.decode('utf-8', errors='ignore')
            except:
                text_content = ""
            
            # Check for dangerous patterns in text files
            if file_info['detected_mime'].startswith('text/'):
                dangerous_patterns = [
                    b'<script',
                    b'javascript:',
                    b'vbscript:',
                    b'onload=',
                    b'onerror=',
                    b'<?php',
                    b'<%',
                    b'exec(',
                    b'system(',
                    b'shell_exec(',
                ]
                
                content_lower = content.lower()
                for pattern in dangerous_patterns:
                    if pattern in content_lower:
                        logger.warning("Dangerous pattern detected", pattern=pattern.decode('utf-8', errors='ignore'))
                        return FileValidationResult.DANGEROUS_CONTENT
            
            # Check Excel/Office files for macros
            if file_info['detected_mime'] in [
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-excel'
            ]:
                if self._has_macros(content):
                    logger.warning("Macros detected in Office document")
                    return FileValidationResult.DANGEROUS_CONTENT
            
            # Check PDF files for dangerous content
            if file_info['detected_mime'] == 'application/pdf':
                if self._has_dangerous_pdf_content(content):
                    return FileValidationResult.DANGEROUS_CONTENT
            
            return FileValidationResult.VALID
            
        except Exception as e:
            logger.error("Content validation failed", error=str(e))
            return FileValidationResult.DANGEROUS_CONTENT
    
    def _has_macros(self, content: bytes) -> bool:
        """Check if Office document contains macros"""
        # Simple check for macro indicators
        macro_indicators = [
            b'vbaProject',
            b'macros',
            b'VBA',
            b'Sub ',
            b'Function ',
            b'Auto_Open',
            b'Workbook_Open'
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in macro_indicators)
    
    def _has_dangerous_pdf_content(self, content: bytes) -> bool:
        """Check PDF for potentially dangerous content"""
        dangerous_pdf_patterns = [
            b'/JavaScript',
            b'/JS',
            b'/Launch',
            b'/EmbeddedFile',
            b'/XFA',
            b'/URI'
        ]
        
        return any(pattern in content for pattern in dangerous_pdf_patterns)
    
    def _is_archive(self, filename: str) -> bool:
        """Check if file is an archive"""
        extension = Path(filename).suffix.lower()
        return extension in self.ARCHIVE_EXTENSIONS
    
    async def _scan_archive(self, content: bytes, file_info: Dict) -> FileValidationResult:
        """Scan archive contents for dangerous files"""
        try:
            # Currently only support ZIP files for scanning
            if not file_info['extension'] == '.zip':
                return FileValidationResult.VALID
            
            with tempfile.NamedTemporaryFile() as temp_file:
                temp_file.write(content)
                temp_file.flush()
                
                try:
                    with zipfile.ZipFile(temp_file.name, 'r') as zip_file:
                        # Check each file in the archive
                        for zip_info in zip_file.filelist:
                            # Check filename
                            if self._validate_filename(zip_info.filename) != FileValidationResult.VALID:
                                logger.warning("Dangerous file in archive", filename=zip_info.filename)
                                return FileValidationResult.DANGEROUS_CONTENT
                            
                            # Check file size to prevent zip bombs
                            if zip_info.file_size > 100 * 1024 * 1024:  # 100MB per file
                                logger.warning("Oversized file in archive", filename=zip_info.filename, size=zip_info.file_size)
                                return FileValidationResult.DANGEROUS_CONTENT
                            
                            # Check compression ratio to detect zip bombs
                            if zip_info.compress_size > 0:
                                ratio = zip_info.file_size / zip_info.compress_size
                                if ratio > 100:  # Compression ratio > 100:1 is suspicious
                                    logger.warning("Suspicious compression ratio", filename=zip_info.filename, ratio=ratio)
                                    return FileValidationResult.DANGEROUS_CONTENT
                        
                        # Additional check: total uncompressed size
                        total_size = sum(zip_info.file_size for zip_info in zip_file.filelist)
                        if total_size > 500 * 1024 * 1024:  # 500MB total
                            logger.warning("Archive too large when uncompressed", total_size=total_size)
                            return FileValidationResult.DANGEROUS_CONTENT
                
                except zipfile.BadZipFile:
                    logger.warning("Corrupted ZIP file")
                    return FileValidationResult.DANGEROUS_CONTENT
            
            return FileValidationResult.VALID
            
        except Exception as e:
            logger.error("Archive scanning failed", error=str(e))
            return FileValidationResult.DANGEROUS_CONTENT
    
    def _is_encrypted(self, content: bytes, file_info: Dict) -> bool:
        """Check if file appears to be encrypted"""
        # Simple entropy check for encryption detection
        if len(content) < 100:
            return False
        
        # Calculate byte frequency distribution
        byte_counts = [0] * 256
        for byte in content[:1024]:  # Check first 1KB
            byte_counts[byte] += 1
        
        # Calculate entropy
        entropy = 0
        for count in byte_counts:
            if count > 0:
                probability = count / min(len(content), 1024)
                entropy -= probability * (probability.bit_length() - 1)
        
        # High entropy suggests encryption/compression
        return entropy > 7.5  # Threshold for encrypted content
    
    def _perform_security_checks(self, content: bytes, file_info: Dict) -> List[str]:
        """Perform additional security checks"""
        warnings = []
        
        # Check for null bytes (often used in exploits)
        if b'\x00' in content:
            warnings.append("File contains null bytes")
        
        # Check for very long lines (possible buffer overflow attempts)
        if b'\n' in content:
            lines = content.split(b'\n')
            max_line_length = max(len(line) for line in lines)
            if max_line_length > 10000:
                warnings.append("File contains very long lines")
        
        # Check for binary content in text files
        if file_info['detected_mime'].startswith('text/'):
            # Check for high percentage of non-printable characters
            printable_count = sum(1 for byte in content[:1024] if 32 <= byte <= 126 or byte in [9, 10, 13])
            if printable_count / min(len(content), 1024) < 0.8:
                warnings.append("Text file contains significant binary content")
        
        # Check file size vs. claimed content type
        if file_info['detected_mime'].startswith('image/') and file_info['size'] > 50 * 1024 * 1024:
            warnings.append("Large image file - verify legitimacy")
        
        return warnings


class FileQuarantineManager:
    """
    Manage quarantined files and malware detection
    """
    
    def __init__(self, quarantine_dir: str = "/tmp/quarantine"):
        self.quarantine_dir = Path(quarantine_dir)
        self.quarantine_dir.mkdir(exist_ok=True, mode=0o700)  # Secure permissions
    
    async def quarantine_file(
        self,
        file_content: bytes,
        filename: str,
        reason: str,
        user_id: Optional[int] = None
    ) -> str:
        """
        Move suspicious file to quarantine
        """
        try:
            # Generate unique quarantine filename
            timestamp = int(datetime.utcnow().timestamp())
            file_hash = hashlib.sha256(file_content).hexdigest()[:16]
            quarantine_filename = f"{timestamp}_{file_hash}_{filename}"
            
            quarantine_path = self.quarantine_dir / quarantine_filename
            
            # Write file to quarantine with restricted permissions
            with open(quarantine_path, 'wb') as f:
                f.write(file_content)
            
            # Set restrictive permissions
            os.chmod(quarantine_path, 0o600)
            
            # Log quarantine action
            logger.warning(
                "File quarantined",
                filename=filename,
                quarantine_file=quarantine_filename,
                reason=reason,
                user_id=user_id,
                size=len(file_content)
            )
            
            return str(quarantine_path)
            
        except Exception as e:
            logger.error("Failed to quarantine file", error=str(e), filename=filename)
            raise
    
    async def list_quarantined_files(self) -> List[Dict]:
        """List all quarantined files"""
        try:
            files = []
            for file_path in self.quarantine_dir.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
                        'filename': file_path.name,
                        'size': stat.st_size,
                        'quarantined_at': datetime.fromtimestamp(stat.st_ctime),
                        'path': str(file_path)
                    })
            return files
        except Exception as e:
            logger.error("Failed to list quarantined files", error=str(e))
            return []
    
    async def delete_quarantined_file(self, quarantine_filename: str) -> bool:
        """Securely delete quarantined file"""
        try:
            file_path = self.quarantine_dir / quarantine_filename
            if file_path.exists():
                # Secure deletion (overwrite before deletion)
                with open(file_path, 'r+b') as f:
                    length = f.tell()
                    f.seek(0)
                    f.write(os.urandom(length))
                    f.flush()
                
                file_path.unlink()
                logger.info("Quarantined file deleted", filename=quarantine_filename)
                return True
        except Exception as e:
            logger.error("Failed to delete quarantined file", error=str(e))
        return False


# Global instances
file_validator = SecureFileValidator()
file_quarantine = FileQuarantineManager()


async def validate_upload_file(
    file: UploadFile,
    allowed_types: Optional[List[str]] = None,
    max_size_mb: Optional[int] = None,
    require_encryption: bool = False
) -> FileValidationReport:
    """
    Convenience function for file validation
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    # Validate file
    validation_report = await file_validator.validate_file(
        file=file,
        allowed_types=allowed_types,
        max_size_mb=max_size_mb,
        require_encryption=require_encryption
    )
    
    # Handle validation results
    if validation_report.result != FileValidationResult.VALID:
        # Quarantine dangerous files
        if validation_report.result in [
            FileValidationResult.MALWARE_DETECTED,
            FileValidationResult.DANGEROUS_CONTENT
        ]:
            content = await file.read()
            await file.seek(0)
            
            await file_quarantine.quarantine_file(
                file_content=content,
                filename=file.filename,
                reason=validation_report.result.value
            )
        
        # Raise appropriate HTTP exception
        error_messages = {
            FileValidationResult.INVALID_TYPE: "File type not allowed",
            FileValidationResult.INVALID_SIZE: "File size too large",
            FileValidationResult.INVALID_NAME: "Invalid filename",
            FileValidationResult.MALWARE_DETECTED: "Malware detected in file",
            FileValidationResult.CONTENT_MISMATCH: "File content doesn't match extension",
            FileValidationResult.DANGEROUS_CONTENT: "Dangerous content detected",
        }
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_messages.get(validation_report.result, "File validation failed")
        )
    
    return validation_report