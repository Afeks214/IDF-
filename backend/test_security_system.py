#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the military-grade security system
IDF Testing Infrastructure
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from core.security import (
    SecurityManager,
    SecurityEventType,
    UserRole,
    Permission,
    ThreatDetectionSystem,
    ComplianceMonitor,
    SecurityContext,
    MilitarySecurityEnforcer,
    SecurityMonitor,
    check_permissions,
    check_multiple_permissions,
    require_permission,
    require_role,
    security_audit_context,
    initialize_security_systems,
    shutdown_security_systems
)


async def test_security_system():
    """Test the complete security system"""
    print("🔐 Testing Military-Grade Security System")
    print("=" * 50)
    
    # Initialize security systems
    try:
        await initialize_security_systems()
        print("✅ Security systems initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize security systems: {e}")
        return False
    
    # Test password hashing
    print("\n🔒 Testing Password Security")
    security_manager = SecurityManager()
    
    test_password = "MilitarySecure123!"
    hashed = security_manager.hash_password(test_password)
    verified = security_manager.verify_password(test_password, hashed)
    print(f"✅ Password hashing and verification: {'PASS' if verified else 'FAIL'}")
    
    # Test password strength validation
    strong_password = "VerySecurePassword123!@#"
    weak_password = "123"
    
    is_strong, strong_errors = security_manager.validate_password_strength(strong_password)
    is_weak, weak_errors = security_manager.validate_password_strength(weak_password)
    
    print(f"✅ Strong password validation: {'PASS' if is_strong else 'FAIL'}")
    print(f"✅ Weak password detection: {'PASS' if not is_weak else 'FAIL'}")
    
    # Test RBAC system
    print("\n🛡️  Testing Role-Based Access Control")
    
    # Test permission checking
    admin_has_user_write = check_permissions(UserRole.ADMIN, Permission.USER_WRITE)
    guest_has_user_write = check_permissions(UserRole.GUEST, Permission.USER_WRITE)
    
    print(f"✅ Admin has USER_WRITE permission: {'PASS' if admin_has_user_write else 'FAIL'}")
    print(f"✅ Guest denied USER_WRITE permission: {'PASS' if not guest_has_user_write else 'FAIL'}")
    
    # Test multiple permissions
    admin_permissions = [Permission.DATA_READ, Permission.DATA_WRITE, Permission.USER_READ]
    admin_has_all = check_multiple_permissions(UserRole.ADMIN, admin_permissions)
    guest_has_all = check_multiple_permissions(UserRole.GUEST, admin_permissions)
    
    print(f"✅ Admin has multiple permissions: {'PASS' if admin_has_all else 'FAIL'}")
    print(f"✅ Guest denied multiple permissions: {'PASS' if not guest_has_all else 'FAIL'}")
    
    # Test security event logging
    print("\n📊 Testing Security Event Logging")
    
    try:
        await security_manager.log_security_event(
            SecurityEventType.LOGIN_SUCCESS,
            user_id="test_user",
            user_ip="192.168.1.100",
            user_agent="Mozilla/5.0 Test",
            resource="/api/login",
            action="login",
            result="SUCCESS",
            details={"method": "password"},
            severity="LOW"
        )
        print("✅ Security event logged successfully")
    except Exception as e:
        print(f"❌ Security event logging failed: {e}")
    
    # Test threat detection
    print("\n🚨 Testing Threat Detection System")
    
    threat_detector = ThreatDetectionSystem()
    
    # Test SQL injection detection
    sql_injection_data = {
        'ip': '192.168.1.200',
        'user_id': 'attacker',
        'content': "'; DROP TABLE users; --"
    }
    
    threats = await threat_detector.detect_threats(sql_injection_data)
    sql_threat_detected = any(threat.threat_type == 'sql_injection' for threat in threats)
    print(f"✅ SQL injection detection: {'PASS' if sql_threat_detected else 'FAIL'}")
    
    # Test XSS detection
    xss_data = {
        'ip': '192.168.1.201',
        'user_id': 'xss_attacker',
        'content': "<script>alert('XSS')</script>"
    }
    
    threats = await threat_detector.detect_threats(xss_data)
    xss_threat_detected = any(threat.threat_type == 'xss_attempt' for threat in threats)
    print(f"✅ XSS detection: {'PASS' if xss_threat_detected else 'FAIL'}")
    
    # Test compliance monitoring
    print("\n📋 Testing Compliance Monitoring")
    
    compliance_monitor = ComplianceMonitor()
    
    # Test password policy compliance
    weak_password_context = {'password': '123'}
    violations = await compliance_monitor.check_compliance(weak_password_context)
    password_violation_detected = len(violations) > 0
    print(f"✅ Password policy compliance: {'PASS' if password_violation_detected else 'FAIL'}")
    
    # Test security context
    print("\n🔐 Testing Security Context")
    
    security_context = SecurityContext()
    security_context.set_user("test_user", UserRole.ADMIN, [Permission.DATA_READ])
    
    user_id = security_context.get_user_id()
    user_role = security_context.get_user_role()
    user_permissions = security_context.get_user_permissions()
    
    context_test_pass = (
        user_id == "test_user" and
        user_role == UserRole.ADMIN and
        Permission.DATA_READ in user_permissions
    )
    print(f"✅ Security context management: {'PASS' if context_test_pass else 'FAIL'}")
    
    # Test military security enforcer
    print("\n🎖️  Testing Military Security Enforcer")
    
    military_enforcer = MilitarySecurityEnforcer()
    
    # Test data classification
    classified_data = military_enforcer.classify_data(
        "SECRET",
        {"operation": "Test Operation", "details": "Classified details"}
    )
    
    classification_test = (
        classified_data.get('_classification') == 'SECRET' and
        classified_data.get('_classification_authority') == 'IDF_SYSTEM'
    )
    print(f"✅ Data classification: {'PASS' if classification_test else 'FAIL'}")
    
    # Test data sanitization
    sanitized_data = military_enforcer.sanitize_classified_data(classified_data, "PUBLIC")
    sanitization_test = sanitized_data.get('access_denied') == True
    print(f"✅ Data sanitization: {'PASS' if sanitization_test else 'FAIL'}")
    
    # Test security monitoring
    print("\n📈 Testing Security Monitoring")
    
    security_monitor = SecurityMonitor()
    
    try:
        security_report = await security_monitor.generate_security_report()
        report_test = (
            'report_id' in security_report and
            'generated_at' in security_report and
            'metrics' in security_report
        )
        print(f"✅ Security report generation: {'PASS' if report_test else 'FAIL'}")
    except Exception as e:
        print(f"❌ Security report generation failed: {e}")
    
    # Test audit context manager
    print("\n📝 Testing Audit Context Manager")
    
    try:
        async with security_audit_context(
            action="test_operation",
            resource="/api/test",
            user_id="test_user",
            user_ip="192.168.1.100"
        ):
            # Simulate some operation
            await asyncio.sleep(0.1)
        
        print("✅ Audit context manager: PASS")
    except Exception as e:
        print(f"❌ Audit context manager failed: {e}")
    
    # Shutdown security systems
    try:
        await shutdown_security_systems()
        print("\n✅ Security systems shutdown successfully")
    except Exception as e:
        print(f"❌ Failed to shutdown security systems: {e}")
    
    print("\n🎯 Military-Grade Security System Test Complete!")
    print("=" * 50)
    return True


if __name__ == "__main__":
    try:
        asyncio.run(test_security_system())
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()