#!/usr/bin/env python3
"""
Database initialization script for IDF Testing Infrastructure.
Sets up database with Hebrew support, creates indexes, and seeds initial data.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.database import (
    create_tables, 
    drop_tables, 
    db_manager, 
    AsyncSessionLocal
)
from app.models.core import Building, InspectionType, Regulator
from app.services.search_service import SearchIndexManager
from app.services.performance_service import PerformanceOptimizationService
from app.services.excel_service import ExcelImportService


async def setup_hebrew_database():
    """Set up database with Hebrew language support."""
    print("🔧 Setting up database with Hebrew support...")
    
    try:
        # Test connection
        is_connected = await db_manager.check_connection()
        if not is_connected:
            print("❌ Database connection failed!")
            return False
        
        print("✅ Database connection successful")
        
        # Test Hebrew support
        hebrew_support = await db_manager.check_hebrew_support()
        if not hebrew_support:
            print("❌ Hebrew text support not working!")
            return False
        
        print("✅ Hebrew text support verified")
        
        # Apply Hebrew optimizations
        await db_manager.optimize_for_hebrew()
        print("✅ Hebrew optimizations applied")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        return False


async def create_database_schema():
    """Create database tables and schema."""
    print("📊 Creating database schema...")
    
    try:
        # Drop existing tables (if requested)
        if "--reset" in sys.argv:
            print("🗑️ Dropping existing tables...")
            await drop_tables()
        
        # Create all tables
        await create_tables()
        print("✅ Database tables created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema creation failed: {str(e)}")
        return False


async def create_search_indexes():
    """Create Hebrew-optimized search indexes."""
    print("🔍 Creating Hebrew search indexes...")
    
    try:
        async with AsyncSessionLocal() as session:
            index_manager = SearchIndexManager(session)
            await index_manager.create_hebrew_indexes()
            print("✅ Hebrew search indexes created")
            
            # Update statistics
            await index_manager.update_search_statistics()
            print("✅ Search statistics updated")
            
        return True
        
    except Exception as e:
        print(f"❌ Index creation failed: {str(e)}")
        return False


async def create_performance_indexes():
    """Create performance optimization indexes."""
    print("⚡ Creating performance indexes...")
    
    try:
        async with AsyncSessionLocal() as session:
            perf_service = PerformanceOptimizationService(session)
            result = await perf_service.create_optimized_indexes()
            
            if result["success"]:
                print(f"✅ Created {result['total_created']} performance indexes")
            else:
                print(f"⚠️ Index creation completed with {len(result['errors'])} errors")
                for error in result["errors"]:
                    print(f"   - {error}")
            
        return True
        
    except Exception as e:
        print(f"❌ Performance index creation failed: {str(e)}")
        return False


async def seed_initial_data():
    """Seed database with initial lookup data."""
    print("🌱 Seeding initial data...")
    
    try:
        async with AsyncSessionLocal() as session:
            # Sample buildings
            buildings_data = [
                {"building_code": "10A", "building_name": "מבנה מרכזי ראשי", "manager_name": "יוסי שמש"},
                {"building_code": "20B", "building_name": "מבנה תקשורת", "manager_name": "דנה אבני"},
                {"building_code": "30C", "building_name": "מבנה ביטחון", "manager_name": "יגאל גזמן"},
                {"building_code": "40", "building_name": "מבנה 40", "manager_name": "מנהל מבנה 40"},
                {"building_code": "50", "building_name": "מבנה 50", "manager_name": "מנהל מבנה 50"},
                {"building_code": "60", "building_name": "מבנה 60", "manager_name": "מנהל מבנה 60"},
            ]
            
            for building_data in buildings_data:
                existing = await session.get(Building, building_data["building_code"])
                if not existing:
                    building = Building(**building_data)
                    session.add(building)
            
            # Sample inspection types
            inspection_types_data = [
                {"type_name": "engineering", "type_name_hebrew": "בדיקה הנדסית", "description": "בדיקה הנדסית כללית"},
                {"type_name": "security", "type_name_hebrew": "בדיקת אבטחה", "description": "בדיקת מערכות אבטחה ובטיחות"},
                {"type_name": "network", "type_name_hebrew": "בדיקת רשת", "description": "בדיקת מערכות תקשורת ורשת"},
                {"type_name": "cyber", "type_name_hebrew": "בדיקת אבטחת מידע", "description": "בדיקת אבטחת מידע וסייבר"},
                {"type_name": "fire_safety", "type_name_hebrew": "בדיקת בטיחות אש", "description": "בדיקת מערכות כיבוי אש ובטיחות"},
            ]
            
            for type_data in inspection_types_data:
                existing = await session.execute(
                    select(InspectionType).where(InspectionType.type_name == type_data["type_name"])
                )
                if not existing.scalar():
                    inspection_type = InspectionType(**type_data)
                    session.add(inspection_type)
            
            # Sample regulators
            regulators_data = [
                {"regulator_name": "אהוב", "regulator_type": "primary"},
                {"regulator_name": "חושן", "regulator_type": "primary"},
                {"regulator_name": "מצוב", "regulator_type": "secondary"},
                {"regulator_name": "בטחון מידע", "regulator_type": "cyber"},
                {"regulator_name": "ברהצ", "regulator_type": "health"},
                {"regulator_name": "רבנות", "regulator_type": "religious"},
            ]
            
            for regulator_data in regulators_data:
                existing = await session.execute(
                    select(Regulator).where(Regulator.regulator_name == regulator_data["regulator_name"])
                )
                if not existing.scalar():
                    regulator = Regulator(**regulator_data)
                    session.add(regulator)
            
            await session.commit()
            print("✅ Initial data seeded successfully")
            
        return True
        
    except Exception as e:
        print(f"❌ Data seeding failed: {str(e)}")
        return False


async def import_excel_data():
    """Import data from Excel file if available."""
    excel_file_path = "/home/QuantNova/IDF-/קובץ בדיקות כולל לקריית התקשוב גרסא מלאה 150725 (1).xlsx"
    
    if not os.path.exists(excel_file_path):
        print("ℹ️ Excel file not found, skipping import")
        return True
    
    print("📊 Importing data from Excel file...")
    
    try:
        async with AsyncSessionLocal() as session:
            import_service = ExcelImportService(session)
            result = await import_service.import_excel_file(excel_file_path)
            
            print(f"✅ Excel import completed:")
            print(f"   - Processed: {result['stats']['processed']} records")
            print(f"   - Imported: {result['stats']['imported']} records")
            print(f"   - Errors: {result['stats']['errors']} records")
            
            if result['stats']['errors'] > 0:
                print("⚠️ Some records had errors during import")
            
        return True
        
    except Exception as e:
        print(f"❌ Excel import failed: {str(e)}")
        return False


async def run_database_tests():
    """Run basic database tests."""
    print("🧪 Running database tests...")
    
    try:
        # Test Hebrew text handling
        async with AsyncSessionLocal() as session:
            # Create test building with Hebrew text
            test_building = Building(
                building_code="TEST",
                building_name="מבנה בדיקה עם טקסט עברי",
                manager_name="מנהל בדיקה"
            )
            
            session.add(test_building)
            await session.commit()
            
            # Retrieve and verify
            retrieved = await session.get(Building, "TEST")
            assert retrieved.building_name == "מבנה בדיקה עם טקסט עברי"
            
            # Clean up
            await session.delete(retrieved)
            await session.commit()
            
        print("✅ Hebrew text handling test passed")
        
        # Test database connection pool
        pool_stats = await db_manager.get_database_info()
        if "error" not in pool_stats:
            print("✅ Database connection pool test passed")
        else:
            print(f"⚠️ Database info retrieval had issues: {pool_stats['error']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database tests failed: {str(e)}")
        return False


async def main():
    """Main initialization function."""
    print("🚀 IDF Testing Infrastructure - Database Initialization")
    print("=" * 60)
    
    steps = [
        ("Hebrew Database Setup", setup_hebrew_database),
        ("Database Schema Creation", create_database_schema),
        ("Hebrew Search Indexes", create_search_indexes),
        ("Performance Indexes", create_performance_indexes),
        ("Initial Data Seeding", seed_initial_data),
        ("Excel Data Import", import_excel_data),
        ("Database Tests", run_database_tests),
    ]
    
    success_count = 0
    total_steps = len(steps)
    
    for step_name, step_function in steps:
        print(f"\n📋 Step: {step_name}")
        print("-" * 40)
        
        try:
            success = await step_function()
            if success:
                success_count += 1
                print(f"✅ {step_name} completed successfully")
            else:
                print(f"❌ {step_name} failed")
        except Exception as e:
            print(f"💥 {step_name} crashed: {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"🏁 Initialization Complete: {success_count}/{total_steps} steps successful")
    
    if success_count == total_steps:
        print("🎉 Database is ready for use!")
        print("\nNext steps:")
        print("1. Start the FastAPI application")
        print("2. Access the API documentation at http://localhost:8000/docs")
        print("3. Begin importing inspection data")
    else:
        print("⚠️ Some steps failed. Please check the errors above.")
        return 1
    
    return 0


if __name__ == "__main__":
    # Import necessary modules
    from sqlalchemy.future import select
    
    # Run the initialization
    exit_code = asyncio.run(main())
    sys.exit(exit_code)