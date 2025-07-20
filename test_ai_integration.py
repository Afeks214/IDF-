#!/usr/bin/env python3
"""
Test script for AI Integration between GrandModel and IDF system
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# Add paths to system path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.append('/home/QuantNova/GrandModel/src')

from backend.app.services.ai_integration_service import (
    AIIntegrationService,
    BuildingReadinessAnalyzer,
    GrandModelSynergyBridge,
    PredictiveAnalyticsEngine,
    GRANDMODEL_AVAILABLE
)

def test_grandmodel_availability():
    """Test if GrandModel components are available"""
    print("=== Testing GrandModel Availability ===")
    print(f"GrandModel Available: {GRANDMODEL_AVAILABLE}")
    
    if GRANDMODEL_AVAILABLE:
        try:
            from synergy.detector import SynergyDetector
            from synergy.base import SynergyPattern, Signal
            from synergy.patterns import MLMIPatternDetector, NWRQKPatternDetector, FVGPatternDetector
            print("✓ GrandModel synergy components imported successfully")
        except ImportError as e:
            print(f"✗ Failed to import GrandModel components: {e}")
            return False
    else:
        print("✗ GrandModel components not available")
        return False
    
    return True

def test_mock_building_readiness():
    """Test building readiness analysis with mock data"""
    print("\n=== Testing Building Readiness Analysis ===")
    
    # Create mock database session
    class MockDB:
        def query(self, model):
            return MockQuery()
        
        def commit(self):
            pass
    
    class MockQuery:
        def filter(self, *args):
            return self
        
        def first(self):
            return MockBuilding()
        
        def all(self):
            return [MockInspection() for _ in range(5)]
    
    class MockBuilding:
        building_code = "TEST001"
        building_name = "Test Building"
        
    class MockInspection:
        building_id = "TEST001"
        status = "completed"
        report_distributed = True
        coordinated_with_contractor = True
        actual_completion = datetime.now()
        target_completion = datetime.now()
    
    # Test analyzer
    try:
        analyzer = BuildingReadinessAnalyzer(MockDB())
        result = analyzer.analyze_building_readiness("TEST001")
        print(f"✓ Building readiness analysis completed: {result}")
        return True
    except Exception as e:
        print(f"✗ Building readiness analysis failed: {e}")
        return False

def test_synergy_bridge():
    """Test GrandModel synergy bridge"""
    print("\n=== Testing GrandModel Synergy Bridge ===")
    
    class MockDB:
        def query(self, model):
            return MockQuery()
        
        def commit(self):
            pass
    
    class MockQuery:
        def filter(self, *args):
            return self
        
        def first(self):
            return MockBuilding()
        
        def all(self):
            return [MockInspection() for _ in range(5)]
    
    class MockBuilding:
        building_code = "TEST001"
        building_name = "Test Building"
        
    class MockInspection:
        building_id = "TEST001"
        status = "completed"
        report_distributed = True
        coordinated_with_contractor = True
        actual_completion = datetime.now()
        target_completion = datetime.now()
    
    try:
        bridge = GrandModelSynergyBridge(MockDB())
        result = bridge.detect_building_readiness_synergies(["TEST001", "TEST002"])
        print(f"✓ Synergy detection completed: {result}")
        return True
    except Exception as e:
        print(f"✗ Synergy detection failed: {e}")
        return False

def test_predictive_analytics():
    """Test predictive analytics engine"""
    print("\n=== Testing Predictive Analytics Engine ===")
    
    class MockDB:
        def query(self, model):
            return MockQuery()
        
        def commit(self):
            pass
    
    class MockQuery:
        def filter(self, *args):
            return self
        
        def first(self):
            return MockBuilding()
        
        def all(self):
            return [MockInspection() for _ in range(5)]
    
    class MockBuilding:
        building_code = "TEST001"
        building_name = "Test Building"
        
    class MockInspection:
        building_id = "TEST001"
        status = "completed"
        report_distributed = True
        coordinated_with_contractor = True
        actual_completion = datetime.now()
        target_completion = datetime.now()
    
    try:
        engine = PredictiveAnalyticsEngine(MockDB())
        result = engine.generate_predictive_insights(["TEST001", "TEST002"])
        print(f"✓ Predictive analytics completed: {result}")
        return True
    except Exception as e:
        print(f"✗ Predictive analytics failed: {e}")
        return False

async def test_full_integration():
    """Test full AI integration service"""
    print("\n=== Testing Full AI Integration Service ===")
    
    class MockDB:
        def query(self, model):
            return MockQuery()
        
        def commit(self):
            pass
    
    class MockQuery:
        def filter(self, *args):
            return self
        
        def first(self):
            return MockBuilding()
        
        def all(self):
            return [MockInspection() for _ in range(5)]
    
    class MockBuilding:
        building_code = "TEST001"
        building_name = "Test Building"
        
    class MockInspection:
        building_id = "TEST001"
        status = "completed"
        report_distributed = True
        coordinated_with_contractor = True
        actual_completion = datetime.now()
        target_completion = datetime.now()
    
    try:
        service = AIIntegrationService(MockDB())
        
        # Test system status
        status = await service.get_system_status()
        print(f"✓ System status retrieved: {status}")
        
        # Test building insights
        insights = await service.get_building_ai_insights(["TEST001", "TEST002"])
        print(f"✓ Building insights retrieved: {len(insights.get('insights', {}).get('insights', []))} buildings analyzed")
        
        return True
    except Exception as e:
        print(f"✗ Full integration test failed: {e}")
        return False

def generate_integration_report():
    """Generate integration report"""
    print("\n=== AI Integration Report ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"GrandModel Available: {GRANDMODEL_AVAILABLE}")
    
    if GRANDMODEL_AVAILABLE:
        print("✓ GrandModel synergy detection: ACTIVE")
        print("✓ MARL coordination system: ACTIVE")
        print("✓ Predictive analytics: ACTIVE")
        print("✓ AI-powered recommendations: ACTIVE")
    else:
        print("✗ GrandModel synergy detection: INACTIVE")
        print("✗ MARL coordination system: INACTIVE")
        print("✓ Predictive analytics: ACTIVE (degraded mode)")
        print("✓ AI-powered recommendations: ACTIVE (degraded mode)")
    
    print("\nIntegration Features:")
    print("- Building readiness analysis")
    print("- Synergy pattern detection")
    print("- Predictive analytics engine")
    print("- AI-powered decision optimization")
    print("- MARL coordination system")
    print("- Real-time dashboard integration")
    print("- REST API endpoints")
    print("- Frontend components")
    
    return True

async def main():
    """Main test function"""
    print("AI Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("GrandModel Availability", test_grandmodel_availability),
        ("Building Readiness Analysis", test_mock_building_readiness),
        ("Synergy Bridge", test_synergy_bridge),
        ("Predictive Analytics", test_predictive_analytics),
        ("Full Integration", test_full_integration),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n=== Test Results ===")
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    # Generate integration report
    generate_integration_report()
    
    return passed == len(results)

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)