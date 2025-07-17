"""
Test suite for Hebrew data handling and database operations.
Tests data integrity, validation, and search functionality.
"""

import pytest
import asyncio
from datetime import date, datetime
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.base import Base
from app.models.core import Inspection, Building, InspectionStatus
from app.services.validation_service import ValidationService, HebrewTextValidator
from app.services.repository import InspectionRepository, BuildingRepository
from app.services.search_service import HebrewSearchService
from app.services.audit_service import AuditService, AuditContext


# Test database setup
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5432/test_idf"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create test database session."""
    TestSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def sample_buildings(test_session):
    """Create sample buildings for testing."""
    buildings_data = [
        {
            "building_code": "10A",
            "building_name": "מבנה מרכזי ראשי",
            "manager_name": "יוסי שמש",
            "is_active": True
        },
        {
            "building_code": "20B",
            "building_name": "מבנה תקשורת",
            "manager_name": "דנה אבני",
            "is_active": True
        },
        {
            "building_code": "30C",
            "building_name": "מבנה ביטחון",
            "manager_name": "יגאל גזמן",
            "is_active": True
        }
    ]
    
    buildings = []
    for building_data in buildings_data:
        building = Building(**building_data)
        test_session.add(building)
        buildings.append(building)
    
    await test_session.commit()
    return buildings


@pytest.fixture
async def sample_inspections(test_session, sample_buildings):
    """Create sample inspections for testing."""
    inspections_data = [
        {
            "building_id": "10A",
            "building_manager": "יוסי שמש",
            "red_team": "דנה אבני + ציון לחיאני",
            "inspection_type": "בדיקה הנדסית כללית",
            "inspection_leader": "יגאל גזמן",
            "inspection_round": 1,
            "status": InspectionStatus.PENDING,
            "regulator_1": "אהוב",
            "regulator_2": "חושן",
            "execution_schedule": date(2025, 8, 15),
            "target_completion": date(2025, 8, 30),
            "coordinated_with_contractor": True,
            "inspection_notes": "בדיקה ראשונית של מערכות הבניין"
        },
        {
            "building_id": "20B",
            "building_manager": "דנה אבני",
            "red_team": "צוות בטחון מידע",
            "inspection_type": "בדיקת אבטחת מידע",
            "inspection_leader": "משה כהן",
            "inspection_round": 2,
            "status": InspectionStatus.IN_PROGRESS,
            "regulator_1": "בטחון מידע",
            "execution_schedule": date(2025, 7, 20),
            "target_completion": date(2025, 8, 5),
            "coordinated_with_contractor": False,
            "inspection_notes": "בדיקת רשתות ומערכות תקשורת"
        },
        {
            "building_id": "30C",
            "building_manager": "יגאל גזמן",
            "red_team": "צוות פיזי",
            "inspection_type": "בדיקת מערכות בטיחות",
            "inspection_leader": "שרה לוי",
            "inspection_round": 1,
            "status": InspectionStatus.COMPLETED,
            "regulator_1": "מצוב",
            "regulator_2": "ברהצ",
            "execution_schedule": date(2025, 7, 1),
            "target_completion": date(2025, 7, 15),
            "actual_completion": date(2025, 7, 14),
            "coordinated_with_contractor": True,
            "inspection_notes": "הושלמה בדיקת מערכות כיבוי אש ואזעקה"
        }
    ]
    
    inspections = []
    for inspection_data in inspections_data:
        inspection = Inspection(**inspection_data)
        test_session.add(inspection)
        inspections.append(inspection)
    
    await test_session.commit()
    return inspections


class TestHebrewTextValidation:
    """Test Hebrew text validation and sanitization."""
    
    def test_hebrew_text_validator_basic(self):
        """Test basic Hebrew text validation."""
        validator = HebrewTextValidator()
        
        # Valid Hebrew text
        valid_text = "בדיקה הנדסית כללית"
        result = validator.validate_hebrew_text(valid_text)
        assert result == valid_text
        
        # Mixed Hebrew and English
        mixed_text = "בדיקה Engineering"
        result = validator.validate_hebrew_text(mixed_text)
        assert result == mixed_text
        
        # Text with numbers
        with_numbers = "מבנה 10A"
        result = validator.validate_hebrew_text(with_numbers)
        assert result == with_numbers
    
    def test_hebrew_text_sanitization(self):
        """Test Hebrew text sanitization."""
        validator = HebrewTextValidator()
        
        # Text with extra whitespace
        messy_text = "  בדיקה   הנדסית  "
        result = validator.validate_hebrew_text(messy_text)
        assert result == "בדיקה הנדסית"
        
        # Text with Hebrew punctuation
        with_punct = "בדיקה״נדסית׳"
        result = validator.validate_hebrew_text(with_punct)
        assert result == 'בדיקה"נדסית\''
    
    def test_hebrew_detection(self):
        """Test Hebrew character detection."""
        validator = HebrewTextValidator()
        
        assert validator.contains_hebrew("בדיקה") == True
        assert validator.contains_hebrew("Engineering") == False
        assert validator.contains_hebrew("בדיקה Engineering") == True
        assert validator.contains_hebrew("123") == False
        assert validator.contains_hebrew("") == False
    
    def test_text_direction_detection(self):
        """Test text direction detection."""
        validator = HebrewTextValidator()
        
        assert validator.get_text_direction("בדיקה") == "rtl"
        assert validator.get_text_direction("Engineering") == "ltr"
        assert validator.get_text_direction("בדיקה Engineering") == "rtl"


class TestValidationService:
    """Test data validation service."""
    
    def test_inspection_validation_success(self):
        """Test successful inspection validation."""
        service = ValidationService()
        
        valid_data = {
            "building_id": "10A",
            "building_manager": "יוסי שמש",
            "inspection_type": "בדיקה הנדסית",
            "inspection_leader": "יגאל גזמן",
            "inspection_round": 1,
            "execution_schedule": "2025-08-15",
            "target_completion": "2025-08-30",
            "coordinated_with_contractor": True
        }
        
        validated_data, errors = service.validate_inspection_data(valid_data)
        assert len(errors) == 0
        assert validated_data["building_id"] == "10A"
        assert validated_data["building_manager"] == "יוסי שמש"
    
    def test_inspection_validation_errors(self):
        """Test inspection validation with errors."""
        service = ValidationService()
        
        invalid_data = {
            "building_id": "",  # Empty building ID
            "inspection_type": "x" * 200,  # Too long
            "inspection_round": 5,  # Out of range
            "execution_schedule": "2025-08-30",
            "target_completion": "2025-08-15"  # Before execution
        }
        
        validated_data, errors = service.validate_inspection_data(invalid_data)
        assert len(errors) > 0
        
        # Check specific error types
        error_text = " ".join(errors)
        assert "building_id" in error_text
        assert "inspection_type" in error_text or "too long" in error_text.lower()
    
    def test_building_validation(self):
        """Test building data validation."""
        service = ValidationService()
        
        valid_data = {
            "building_code": "10a",  # Should be converted to uppercase
            "building_name": "מבנה מרכזי",
            "manager_name": "יוסי שמש"
        }
        
        validated_data, errors = service.validate_building_data(valid_data)
        assert len(errors) == 0
        assert validated_data["building_code"] == "10A"
    
    def test_search_query_validation(self):
        """Test search query validation."""
        service = ValidationService()
        
        # Valid Hebrew search
        query, errors = service.validate_search_query("בדיקה הנדסית")
        assert len(errors) == 0
        assert query == "בדיקה הנדסית"
        
        # Too long query
        long_query = "x" * 600
        query, errors = service.validate_search_query(long_query)
        assert len(errors) > 0
        assert len(query) <= 500


@pytest.mark.asyncio
class TestRepositoryOperations:
    """Test repository CRUD operations with Hebrew data."""
    
    async def test_create_inspection_with_hebrew(self, test_session):
        """Test creating inspection with Hebrew text."""
        repo = InspectionRepository(test_session)
        
        # First create a building
        building = Building(
            building_code="TEST1",
            building_name="מבנה בדיקה",
            manager_name="מנהל בדיקה"
        )
        test_session.add(building)
        await test_session.commit()
        
        inspection_data = {
            "building_id": "TEST1",
            "building_manager": "מנהל בדיקה",
            "inspection_type": "בדיקה הנדסית",
            "inspection_leader": "מוביל בדיקה",
            "inspection_round": 1,
            "status": InspectionStatus.PENDING,
            "inspection_notes": "הערות בעברית עם תוכן מפורט"
        }
        
        inspection = await repo.create(inspection_data, user_id="test_user")
        
        assert inspection.id is not None
        assert inspection.building_manager == "מנהל בדיקה"
        assert inspection.inspection_type == "בדיקה הנדסית"
        assert inspection.inspection_notes == "הערות בעברית עם תוכן מפורט"
    
    async def test_search_hebrew_text(self, test_session, sample_inspections):
        """Test Hebrew text search functionality."""
        repo = InspectionRepository(test_session)
        
        # Search for Hebrew term
        results = await repo.search_hebrew_text("הנדסית")
        assert len(results) >= 1
        
        # Check that results contain the search term
        found_engineering = any("הנדסית" in result.inspection_type for result in results)
        assert found_engineering
        
        # Search for leader name
        results = await repo.search_hebrew_text("יגאל")
        assert len(results) >= 1
    
    async def test_get_by_building(self, test_session, sample_inspections):
        """Test getting inspections by building."""
        repo = InspectionRepository(test_session)
        
        results = await repo.get_by_building("10A")
        assert len(results) >= 1
        
        # All results should be for the specified building
        for inspection in results:
            assert inspection.building_id == "10A"
    
    async def test_get_overdue_inspections(self, test_session, sample_inspections):
        """Test getting overdue inspections."""
        repo = InspectionRepository(test_session)
        
        # Create an overdue inspection
        overdue_data = {
            "building_id": "10A",
            "inspection_type": "בדיקה מאוחרת",
            "inspection_leader": "מוביל",
            "status": InspectionStatus.PENDING,
            "target_completion": date(2025, 1, 1)  # Past date
        }
        
        await repo.create(overdue_data)
        
        overdue_inspections = await repo.get_overdue_inspections()
        assert len(overdue_inspections) >= 1
        
        # Check that returned inspections are actually overdue
        today = date.today()
        for inspection in overdue_inspections:
            assert inspection.target_completion < today
            assert inspection.status not in [InspectionStatus.COMPLETED, InspectionStatus.CANCELLED]


@pytest.mark.asyncio
class TestHebrewSearch:
    """Test Hebrew search functionality."""
    
    async def test_search_inspections_hebrew(self, test_session, sample_inspections):
        """Test searching inspections with Hebrew terms."""
        search_service = HebrewSearchService(test_session)
        
        # Search for inspection type
        results = await search_service.search_inspections("בדיקה")
        assert len(results) >= 1
        
        # Check result structure
        for result in results:
            assert "inspection" in result
            assert "rank" in result
            assert "headline" in result
            assert result["rank"] > 0
    
    async def test_search_suggestions(self, test_session, sample_inspections):
        """Test search term suggestions."""
        search_service = HebrewSearchService(test_session)
        
        suggestions = await search_service.suggest_search_terms("בד")
        assert len(suggestions) >= 1
        
        # Check that suggestions contain the partial term
        hebrew_suggestions = [s for s in suggestions if "בד" in s]
        assert len(hebrew_suggestions) >= 1
    
    async def test_search_analytics(self, test_session, sample_inspections):
        """Test search analytics."""
        search_service = HebrewSearchService(test_session)
        
        analytics = await search_service.get_search_analytics()
        
        assert "popular_inspection_types" in analytics
        assert "active_leaders" in analytics
        assert "active_buildings" in analytics
        
        # Check that we have some data
        assert len(analytics["popular_inspection_types"]) >= 1


@pytest.mark.asyncio
class TestAuditLogging:
    """Test audit logging functionality."""
    
    async def test_audit_logging_creation(self, test_session):
        """Test audit logging for record creation."""
        audit_service = AuditService(test_session)
        
        # Set audit context
        context = AuditContext(
            user_id="test_user",
            user_role="admin",
            ip_address="192.168.1.1"
        )
        audit_service.set_audit_context(context)
        
        # Log an action
        audit_log = await audit_service.log_action(
            table_name="inspections",
            record_id=123,
            action="CREATE",
            context=context
        )
        
        assert audit_log.id is not None
        assert audit_log.table_name == "inspections"
        assert audit_log.record_id == 123
        assert audit_log.action == "CREATE"
        assert audit_log.user_id == "test_user"
        assert audit_log.ip_address == "192.168.1.1"
    
    async def test_audit_trail_retrieval(self, test_session):
        """Test retrieving audit trail."""
        audit_service = AuditService(test_session)
        
        # Create some audit entries
        context = AuditContext(user_id="test_user")
        
        for i in range(3):
            await audit_service.log_action(
                table_name="inspections",
                record_id=i + 1,
                action="CREATE",
                context=context
            )
        
        # Retrieve audit trail
        trail = await audit_service.get_audit_trail(
            table_name="inspections",
            user_id="test_user"
        )
        
        assert len(trail) >= 3
        
        for entry in trail:
            assert entry["table_name"] == "inspections"
            assert entry["user_id"] == "test_user"
            assert entry["action"] == "CREATE"


@pytest.mark.asyncio
class TestDataIntegrity:
    """Test data integrity and constraints."""
    
    async def test_foreign_key_constraints(self, test_session):
        """Test foreign key constraints work properly."""
        # Try to create inspection for non-existent building
        inspection = Inspection(
            building_id="NONEXISTENT",
            inspection_type="בדיקה",
            inspection_leader="מוביל"
        )
        
        test_session.add(inspection)
        
        # This should raise an integrity error
        with pytest.raises(Exception):  # IntegrityError or similar
            await test_session.commit()
    
    async def test_hebrew_text_preservation(self, test_session):
        """Test that Hebrew text is preserved exactly."""
        # Create building with Hebrew text
        original_text = "מבנה עם טקסט עברי מורכב: 'ציטוט' ו״גרשיים״"
        
        building = Building(
            building_code="HEB1",
            building_name=original_text,
            manager_name="מנהל עם שם עברי"
        )
        
        test_session.add(building)
        await test_session.commit()
        
        # Retrieve and verify text preservation
        retrieved = await test_session.get(Building, "HEB1")
        assert retrieved.building_name == original_text
        
        # Check that Hebrew characters are not corrupted
        assert "עברי" in retrieved.building_name
        assert "מורכב" in retrieved.building_name


@pytest.mark.asyncio 
class TestPerformance:
    """Test database performance with Hebrew data."""
    
    async def test_large_dataset_creation(self, test_session):
        """Test creating and querying large dataset with Hebrew text."""
        # Create multiple buildings
        buildings = []
        for i in range(10):
            building = Building(
                building_code=f"B{i:03d}",
                building_name=f"מבנה מספר {i}",
                manager_name=f"מנהל {i}"
            )
            buildings.append(building)
            test_session.add(building)
        
        await test_session.commit()
        
        # Create multiple inspections
        inspections = []
        for i in range(50):
            building_id = f"B{i % 10:03d}"
            inspection = Inspection(
                building_id=building_id,
                inspection_type=f"בדיקה מספר {i}",
                inspection_leader=f"מוביל {i % 5}",
                inspection_notes=f"הערות בעברית עבור בדיקה {i}"
            )
            inspections.append(inspection)
            test_session.add(inspection)
        
        await test_session.commit()
        
        # Test query performance
        repo = InspectionRepository(test_session)
        
        # Query all inspections (should be fast)
        start_time = datetime.now()
        all_inspections = await repo.get_all(limit=100)
        query_time = (datetime.now() - start_time).total_seconds()
        
        assert len(all_inspections) >= 50
        assert query_time < 1.0  # Should complete in less than 1 second
        
        # Test Hebrew search performance
        search_service = HebrewSearchService(test_session)
        
        start_time = datetime.now()
        search_results = await search_service.search_inspections("בדיקה")
        search_time = (datetime.now() - start_time).total_seconds()
        
        assert len(search_results) >= 1
        assert search_time < 2.0  # Hebrew search should complete in reasonable time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])