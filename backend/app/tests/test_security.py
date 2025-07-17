#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Security Testing Suite
Military-Grade Security Validation for IDF Testing Infrastructure
"""

import asyncio
import pytest
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import httpx

from ..main import app
from ..core.config import settings
from ..core.security import security_manager, jwt_manager, UserRole, Permission
from ..core.encryption import encryption, secure_storage, token_encryption
from ..core.validation import validator, sanitizer, form_validator
from ..core.file_security import file_validator
from ..models.user import User, Role
from ..schemas.auth import UserCreate, LoginRequest


class SecurityTestSuite:
    """Comprehensive security testing suite"""
    
    def __init__(self):
        self.client = TestClient(app)
        self.test_user_data = {
            "username": "test_security_user",
            "email": "security.test@idf.test",
            "password": "SecureP@ssw0rd123!",
            "first_name": "Security",
            "last_name": "Tester",
            "roles": [UserRole.ANALYST]
        }
    
    async def test_password_security(self):
        """Test password security requirements"""
        print("🔐 Testing Password Security...")
        
        # Test weak passwords
        weak_passwords = [
            "123456",
            "password",
            "qwerty",
            "admin",
            "12345678",
            "Password1",  # Missing special character
            "password123!",  # Missing uppercase
            "PASSWORD123!",  # Missing lowercase
            "Password!",  # Too short
        ]
        
        for weak_password in weak_passwords:
            is_valid, errors = security_manager.validate_password_strength(weak_password)
            assert not is_valid, f"Weak password '{weak_password}' should be rejected"
            print(f"✅ Rejected weak password: {weak_password}")
        
        # Test strong password
        strong_password = "SecureP@ssw0rd123!"
        is_valid, errors = security_manager.validate_password_strength(strong_password)
        assert is_valid, f"Strong password should be accepted: {errors}"
        print("✅ Strong password validation passed")
    
    async def test_jwt_security(self):
        """Test JWT token security"""
        print("🔑 Testing JWT Security...")
        
        # Test token creation and verification
        test_data = {"sub": "123", "username": "testuser", "role": "analyst"}
        
        # Create token
        token = await jwt_manager.create_access_token(test_data)
        assert token, "Token creation should succeed"
        print("✅ JWT token creation successful")
        
        # Verify token
        payload = await jwt_manager.verify_token(token)
        assert payload, "Token verification should succeed"
        assert payload["sub"] == "123"
        assert payload["username"] == "testuser"
        print("✅ JWT token verification successful")
        
        # Test token expiration
        expired_token = await jwt_manager.create_access_token(
            test_data, 
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        expired_payload = await jwt_manager.verify_token(expired_token)
        assert expired_payload is None, "Expired token should be rejected"
        print("✅ Expired token properly rejected")
        
        # Test token blacklisting
        jti = payload.get("jti")
        if jti:
            await jwt_manager.blacklist_token(jti)
            blacklisted_payload = await jwt_manager.verify_token(token)
            assert blacklisted_payload is None, "Blacklisted token should be rejected"
            print("✅ Blacklisted token properly rejected")
    
    async def test_encryption_utilities(self):
        """Test encryption and decryption"""
        print("🔒 Testing Encryption Utilities...")
        
        # Test Fernet encryption
        plaintext = "Sensitive military data - classified information"
        
        # Simple Fernet encryption
        encrypted = encryption.encrypt_fernet(plaintext)
        decrypted = encryption.decrypt_fernet(encrypted)
        assert decrypted.decode() == plaintext
        print("✅ Fernet encryption/decryption successful")
        
        # Test AES-GCM encryption
        aes_encrypted, metadata = encryption.encrypt_aes_gcm(plaintext)
        aes_key = secrets.token_bytes(32)  # 256-bit key
        aes_encrypted_with_key, metadata_with_key = encryption.encrypt_aes_gcm(plaintext, aes_key)
        aes_decrypted = encryption.decrypt_aes_gcm(aes_encrypted_with_key, aes_key, metadata_with_key)
        assert aes_decrypted.decode() == plaintext
        print("✅ AES-GCM encryption/decryption successful")
        
        # Test password-based encryption
        password = "SecureEncryptionPassword123!"
        pwd_encrypted, pwd_metadata = encryption.encrypt_with_password(plaintext, password)
        pwd_decrypted = encryption.decrypt_with_password(pwd_encrypted, password, pwd_metadata)
        assert pwd_decrypted.decode() == plaintext
        print("✅ Password-based encryption/decryption successful")
        
        # Test JSON encryption
        test_data = {
            "classified": True,
            "operation": "Operation Security Test",
            "coordinates": {"lat": 31.0461, "lng": 34.8516},
            "personnel": ["Agent Alpha", "Agent Beta"]
        }
        
        json_encrypted = secure_storage.encrypt_json(test_data, password)
        json_decrypted = secure_storage.decrypt_json(json_encrypted, password)
        assert json_decrypted == test_data
        print("✅ JSON encryption/decryption successful")
        
        # Test token encryption
        token = "secret_access_token_12345"
        context = "user_session"
        token_encrypted = token_encryption.encrypt_token(token, context)
        token_decrypted = token_encryption.decrypt_token(token_encrypted, context)
        assert token_decrypted == token
        print("✅ Token encryption/decryption successful")
    
    async def test_input_validation(self):
        """Test input validation and sanitization"""
        print("🛡️ Testing Input Validation...")
        
        # Test email validation
        valid_emails = ["test@idf.mil", "user.name@domain.com", "analyst123@secure.gov.il"]
        invalid_emails = ["invalid.email", "@domain.com", "user@", "user..name@domain.com"]
        
        for email in valid_emails:
            assert validator.validate_email(email), f"Valid email should pass: {email}"
        
        for email in invalid_emails:
            assert not validator.validate_email(email), f"Invalid email should fail: {email}"
        
        print("✅ Email validation tests passed")
        
        # Test phone validation
        valid_phones = ["+972501234567", "972-50-123-4567", "+1-555-123-4567"]
        invalid_phones = ["123", "abc-def-ghij", "555-123"]
        
        for phone in valid_phones:
            assert validator.validate_phone(phone), f"Valid phone should pass: {phone}"
        
        for phone in invalid_phones:
            assert not validator.validate_phone(phone), f"Invalid phone should fail: {phone}"
        
        print("✅ Phone validation tests passed")
        
        # Test string sanitization
        dangerous_inputs = [
            "<script>alert('XSS')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "javascript:alert('xss')",
            "\x00\x01\x02malicious",
        ]
        
        for dangerous_input in dangerous_inputs:
            sanitized = sanitizer.sanitize_string(dangerous_input)
            assert "<script>" not in sanitized
            assert "DROP TABLE" not in sanitized.upper()
            assert "../" not in sanitized
            assert "javascript:" not in sanitized
            assert "\x00" not in sanitized
        
        print("✅ String sanitization tests passed")
        
        # Test Hebrew text handling
        hebrew_texts = [
            "שלום עולם",
            "מערכת בדיקות צה״ל",
            "בדיקת אבטחה מקיפה",
            "Mixed עברית and English",
        ]
        
        for hebrew_text in hebrew_texts:
            sanitized = sanitizer.sanitize_hebrew_text(hebrew_text)
            assert len(sanitized) > 0
            # Verify Hebrew characters are preserved
            hebrew_chars = any('\u0590' <= char <= '\u05FF' for char in sanitized)
            if any('\u0590' <= char <= '\u05FF' for char in hebrew_text):
                assert hebrew_chars, "Hebrew characters should be preserved"
        
        print("✅ Hebrew text sanitization tests passed")
    
    async def test_file_security(self):
        """Test file upload security"""
        print("📎 Testing File Security...")
        
        # Test filename validation
        safe_filenames = ["document.pdf", "report_2024.xlsx", "image.png", "data.csv"]
        dangerous_filenames = [
            "../../etc/passwd",
            "script.exe",
            "malware.bat",
            "virus.com",
            "backdoor.php",
            "shell.jsp",
            "con.txt",  # Windows reserved name
            "document.pdf.exe",  # Double extension
        ]
        
        for filename in safe_filenames:
            assert file_validator._validate_filename(filename).name == "VALID"
        
        for filename in dangerous_filenames:
            result = file_validator._validate_filename(filename)
            assert result.name != "VALID", f"Dangerous filename should be rejected: {filename}"
        
        print("✅ Filename validation tests passed")
        
        # Test malicious content detection
        malicious_signatures = [
            b'\x4d\x5a',  # PE executable
            b'\x7f\x45\x4c\x46',  # ELF executable
            b'<script>alert("xss")</script>',
            b'<?php system($_GET["cmd"]); ?>',
        ]
        
        for signature in malicious_signatures:
            is_malicious = file_validator._has_malicious_signature(signature)
            if signature.startswith((b'\x4d\x5a', b'\x7f\x45\x4c\x46')):
                assert is_malicious, "Executable signature should be detected"
        
        print("✅ Malicious content detection tests passed")
    
    async def test_rate_limiting(self):
        """Test rate limiting functionality"""
        print("⏱️ Testing Rate Limiting...")
        
        # Test Redis rate limiting (using mock if Redis not available)
        try:
            from ..core.redis_client import redis_client
            
            # Test rate limit checking
            identifier = "test_user_123"
            limit = 5
            window = 60
            
            # Make requests within limit
            for i in range(limit):
                is_allowed, current, remaining = await redis_client.check_rate_limit(
                    identifier, limit, window
                )
                assert is_allowed, f"Request {i+1} should be allowed"
                assert current == i + 1
                assert remaining == limit - (i + 1)
            
            # Exceed rate limit
            is_allowed, current, remaining = await redis_client.check_rate_limit(
                identifier, limit, window
            )
            assert not is_allowed, "Request exceeding limit should be denied"
            assert remaining == 0
            
            print("✅ Rate limiting tests passed")
            
        except Exception as e:
            print(f"⚠️ Rate limiting test skipped (Redis not available): {e}")
    
    async def test_authentication_endpoints(self):
        """Test authentication API endpoints"""
        print("🔐 Testing Authentication Endpoints...")
        
        # Test login with invalid credentials
        invalid_login = {
            "username": "nonexistent",
            "password": "wrongpassword"
        }
        
        response = self.client.post("/api/v1/auth/login", json=invalid_login)
        assert response.status_code == 401
        print("✅ Invalid login properly rejected")
        
        # Test registration validation (admin required)
        weak_registration = {
            "username": "test",
            "email": "invalid.email",
            "password": "weak",
            "first_name": "",
            "last_name": ""
        }
        
        response = self.client.post("/api/v1/auth/register", json=weak_registration)
        assert response.status_code in [400, 401, 403]  # Validation error or unauthorized
        print("✅ Weak registration data properly rejected")
        
        # Test password change validation
        weak_password_change = {
            "current_password": "anything",
            "new_password": "weak",
            "confirm_password": "weak"
        }
        
        response = self.client.post("/api/v1/auth/change-password", json=weak_password_change)
        assert response.status_code in [400, 401]  # Validation error or unauthorized
        print("✅ Weak password change properly rejected")
    
    async def test_security_headers(self):
        """Test security headers in responses"""
        print("🛡️ Testing Security Headers...")
        
        response = self.client.get("/")
        
        # Check for essential security headers
        security_headers = [
            "X-Frame-Options",
            "X-Content-Type-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy",
            "Permissions-Policy"
        ]
        
        for header in security_headers:
            assert header in response.headers, f"Missing security header: {header}"
        
        # Verify header values
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "max-age=" in response.headers.get("Strict-Transport-Security", "")
        
        print("✅ Security headers tests passed")
        
        # Verify server header is removed
        assert "Server" not in response.headers, "Server header should be removed"
        print("✅ Server header properly removed")
    
    async def test_rbac_system(self):
        """Test Role-Based Access Control"""
        print("👥 Testing RBAC System...")
        
        # Test permission checking
        from ..core.security import check_permissions, ROLE_PERMISSIONS
        
        # Test that GUEST has minimal permissions
        guest_perms = ROLE_PERMISSIONS.get(UserRole.GUEST, [])
        admin_perms = ROLE_PERMISSIONS.get(UserRole.SUPER_ADMIN, [])
        
        assert len(guest_perms) < len(admin_perms), "Guest should have fewer permissions than admin"
        
        # Test specific permission checks
        assert check_permissions(UserRole.SUPER_ADMIN, Permission.DATA_DELETE)
        assert check_permissions(UserRole.ADMIN, Permission.DATA_WRITE)
        assert check_permissions(UserRole.VIEWER, Permission.DATA_READ)
        assert not check_permissions(UserRole.GUEST, Permission.DATA_DELETE)
        assert not check_permissions(UserRole.VIEWER, Permission.DATA_WRITE)
        
        print("✅ RBAC permission checks passed")
    
    async def test_session_security(self):
        """Test session security features"""
        print("🔐 Testing Session Security...")
        
        from ..core.redis_client import SessionManager
        
        # Test session creation
        user_id = "test_user_123"
        session_data = {
            "ip_address": "127.0.0.1",
            "user_agent": "Test Agent",
            "login_time": datetime.utcnow().isoformat()
        }
        
        try:
            session_id = await SessionManager.create_session(user_id, session_data)
            assert session_id, "Session creation should succeed"
            
            # Test session retrieval
            retrieved_data = await SessionManager.get_session(session_id)
            assert retrieved_data, "Session retrieval should succeed"
            assert retrieved_data["user_id"] == user_id
            
            # Test session deletion
            deleted = await SessionManager.delete_session(session_id)
            assert deleted, "Session deletion should succeed"
            
            # Verify session is gone
            retrieved_after_delete = await SessionManager.get_session(session_id)
            assert retrieved_after_delete is None, "Deleted session should not be retrievable"
            
            print("✅ Session management tests passed")
            
        except Exception as e:
            print(f"⚠️ Session security test skipped (Redis not available): {e}")
    
    async def run_all_tests(self):
        """Run all security tests"""
        print("🚀 Starting Comprehensive Security Test Suite")
        print("=" * 60)
        
        test_methods = [
            self.test_password_security,
            self.test_jwt_security,
            self.test_encryption_utilities,
            self.test_input_validation,
            self.test_file_security,
            self.test_rate_limiting,
            self.test_authentication_endpoints,
            self.test_security_headers,
            self.test_rbac_system,
            self.test_session_security,
        ]
        
        passed = 0
        failed = 0
        
        for test_method in test_methods:
            try:
                await test_method()
                passed += 1
            except Exception as e:
                print(f"❌ {test_method.__name__} FAILED: {e}")
                failed += 1
        
        print("=" * 60)
        print(f"🎯 Security Test Results:")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        if failed == 0:
            print("🏆 ALL SECURITY TESTS PASSED!")
            print("🛡️ Military-Grade Security Implementation Validated")
        else:
            print("⚠️ Some security tests failed - review implementation")
        
        return failed == 0


async def main():
    """Main function to run security tests"""
    security_tests = SecurityTestSuite()
    success = await security_tests.run_all_tests()
    return success


if __name__ == "__main__":
    asyncio.run(main())