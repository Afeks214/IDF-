#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final Comprehensive Analysis for Excel File
Complete data mapping and web app design recommendations
"""

import pandas as pd
import json
from datetime import datetime

def comprehensive_analysis():
    """
    Complete comprehensive analysis including all requirements
    """
    file_path = "/home/QuantNova/IDF-/קובץ בדיקות כולל לקריית התקשוב גרסא מלאה 150725 (1).xlsx"
    
    print("🔍 COMPREHENSIVE EXCEL DATA ANALYSIS")
    print("=" * 80)
    print("File: קובץ בדיקות כולל לקריית התקשוב גרסא מלאה 150725")
    print("Date: July 15, 2025")
    print("=" * 80)
    
    # 1. EXTRACT LOOKUP VALUES FROM ערכים SHEET
    print("\n📋 1. LOOKUP VALUES EXTRACTION")
    print("-" * 40)
    
    df_values = pd.read_excel(file_path, sheet_name='ערכים', header=None)
    
    lookup_data = {
        'buildings': [],
        'building_managers': [],
        'red_teams': [],
        'inspection_types': [],
        'inspection_leaders': [],
        'inspection_rounds': ['1', '2', '3', '4'],
        'regulators': [],
        'yes_no_options': ['כן', 'לא']
    }
    
    # Extract buildings (columns 1-2)
    for i in range(1, len(df_values)):
        if pd.notna(df_values.iloc[i, 1]) and str(df_values.iloc[i, 1]) != 'מבנה':
            lookup_data['buildings'].append(str(df_values.iloc[i, 1]))
    
    # Extract managers (columns 3-4)
    for i in range(1, len(df_values)):
        if pd.notna(df_values.iloc[i, 3]) and str(df_values.iloc[i, 3]) != 'מנהל מבנה':
            lookup_data['building_managers'].append(str(df_values.iloc[i, 3]))
    
    # Extract teams (columns 5-6)
    for i in range(1, len(df_values)):
        if pd.notna(df_values.iloc[i, 5]) and str(df_values.iloc[i, 5]) != 'צוות אדום':
            lookup_data['red_teams'].append(str(df_values.iloc[i, 5]))
    
    # Extract inspection types (columns 7-8)
    for i in range(1, len(df_values)):
        if pd.notna(df_values.iloc[i, 7]) and str(df_values.iloc[i, 7]) != 'סוג בדיקה':
            lookup_data['inspection_types'].append(str(df_values.iloc[i, 7]))
    
    # Extract leaders (columns 9-10)
    for i in range(1, len(df_values)):
        if pd.notna(df_values.iloc[i, 9]) and str(df_values.iloc[i, 9]) != 'מוביל בדיקה':
            lookup_data['inspection_leaders'].append(str(df_values.iloc[i, 9]))
    
    # Extract regulators (columns 13-14)
    for i in range(1, len(df_values)):
        if pd.notna(df_values.iloc[i, 13]) and str(df_values.iloc[i, 13]) not in ['רגולטור 1,2,3,4']:
            lookup_data['regulators'].append(str(df_values.iloc[i, 13]))
    
    print("Lookup Values Summary:")
    for category, values in lookup_data.items():
        print(f"  {category}: {len(values)} items")
    
    # 2. ANALYZE MAIN TABLE
    print("\n📊 2. MAIN TABLE ANALYSIS")
    print("-" * 40)
    
    df_main = pd.read_excel(file_path, sheet_name='טבלה מרכזת', header=3)
    
    column_mapping = {
        'מבנה': 'building_id',
        'מנהל\nמבנה': 'building_manager', 
        'צוות\nאדום': 'red_team',
        'סוג\nהבדיקה': 'inspection_type',
        'מוביל\nהבדיקה': 'inspection_leader',
        'סבב\nבדיקות': 'inspection_round',
        'רגולטור\n1': 'regulator_1',
        'רגולטור\n2': 'regulator_2', 
        'רגולטור\n3': 'regulator_3',
        'רגולטור\n4': 'regulator_4',
        'לו"ז ביצוע\nמתואם/ ריאלי': 'execution_schedule',
        'יעד\nלסיום': 'target_completion',
        'האם מתואם\nמול זכיין?': 'coordinated_with_contractor',
        'צרופת\nדו"ח ליקויים': 'defect_report_path',
        'האם\nהדו"ח הופץ': 'report_distributed',
        'תאריך\nהפצת הדו"ח': 'distribution_date',
        'בדיקה\nחוזרת': 'repeat_inspection',
        'התרשמות\nמהבדיקה': 'inspection_notes'
    }
    
    print(f"Total inspection records: {len(df_main)}")
    print(f"Total columns: {len(df_main.columns)}")
    
    # Analyze data usage
    buildings_used = [str(x) for x in df_main['מבנה'].dropna().unique()]
    managers_used = df_main['מנהל\nמבנה'].dropna().unique().tolist()
    types_used = df_main['סוג\nהבדיקה'].dropna().unique().tolist()
    leaders_used = df_main['מוביל\nהבדיקה'].dropna().unique().tolist()
    
    print(f"Buildings in use: {len(buildings_used)} ({', '.join(sorted(buildings_used)[:10])}...)")
    print(f"Managers in use: {len(managers_used)}")
    print(f"Inspection types in use: {len(types_used)}")
    print(f"Leaders in use: {len(leaders_used)}")
    
    # 3. DATABASE SCHEMA DESIGN
    print("\n🗄️ 3. DATABASE SCHEMA RECOMMENDATIONS")
    print("-" * 40)
    
    db_schema = {
        "main_table": {
            "name": "inspections",
            "description": "Primary inspection tracking table",
            "columns": [
                {"name": "id", "type": "INT PRIMARY KEY AUTO_INCREMENT", "description": "Unique inspection ID"},
                {"name": "building_id", "type": "VARCHAR(20)", "hebrew": "מבנה", "required": True},
                {"name": "building_manager", "type": "VARCHAR(100)", "hebrew": "מנהל מבנה", "required": False},
                {"name": "red_team", "type": "VARCHAR(200)", "hebrew": "צוות אדום", "required": False},
                {"name": "inspection_type", "type": "VARCHAR(150)", "hebrew": "סוג הבדיקה", "required": True},
                {"name": "inspection_leader", "type": "VARCHAR(100)", "hebrew": "מוביל הבדיקה", "required": True},
                {"name": "inspection_round", "type": "INT", "hebrew": "סבב בדיקות", "required": False},
                {"name": "regulator_1", "type": "VARCHAR(100)", "hebrew": "רגולטור 1", "required": False},
                {"name": "regulator_2", "type": "VARCHAR(100)", "hebrew": "רגולטור 2", "required": False},
                {"name": "regulator_3", "type": "VARCHAR(100)", "hebrew": "רגולטור 3", "required": False},
                {"name": "regulator_4", "type": "VARCHAR(100)", "hebrew": "רגולטור 4", "required": False},
                {"name": "execution_schedule", "type": "DATE", "hebrew": "לוח זמנים ביצוע", "required": False},
                {"name": "target_completion", "type": "DATE", "hebrew": "יעד לסיום", "required": False},
                {"name": "coordinated_with_contractor", "type": "ENUM('כן', 'לא')", "hebrew": "מתואם מול זכיין", "required": False},
                {"name": "defect_report_path", "type": "VARCHAR(500)", "hebrew": "נתיב דוח ליקויים", "required": False},
                {"name": "report_distributed", "type": "ENUM('כן', 'לא')", "hebrew": "דוח הופץ", "required": False},
                {"name": "distribution_date", "type": "DATE", "hebrew": "תאריך הפצה", "required": False},
                {"name": "repeat_inspection", "type": "ENUM('כן', 'לא')", "hebrew": "בדיקה חוזרת", "required": False},
                {"name": "inspection_notes", "type": "TEXT", "hebrew": "התרשמות", "required": False},
                {"name": "created_at", "type": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "description": "Record creation time"},
                {"name": "updated_at", "type": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP", "description": "Last update time"}
            ]
        },
        "lookup_tables": {
            "buildings": {
                "name": "buildings",
                "columns": [
                    {"name": "id", "type": "VARCHAR(20) PRIMARY KEY"},
                    {"name": "name", "type": "VARCHAR(200)"},
                    {"name": "description", "type": "TEXT"}
                ]
            },
            "managers": {
                "name": "building_managers", 
                "columns": [
                    {"name": "id", "type": "INT PRIMARY KEY AUTO_INCREMENT"},
                    {"name": "name", "type": "VARCHAR(100)"},
                    {"name": "email", "type": "VARCHAR(100)"},
                    {"name": "phone", "type": "VARCHAR(20)"}
                ]
            },
            "teams": {
                "name": "red_teams",
                "columns": [
                    {"name": "id", "type": "INT PRIMARY KEY AUTO_INCREMENT"},
                    {"name": "team_name", "type": "VARCHAR(200)"},
                    {"name": "members", "type": "TEXT"}
                ]
            },
            "inspection_types": {
                "name": "inspection_types",
                "columns": [
                    {"name": "id", "type": "INT PRIMARY KEY AUTO_INCREMENT"},
                    {"name": "type_name", "type": "VARCHAR(150)"},
                    {"name": "category", "type": "VARCHAR(50)"},
                    {"name": "description", "type": "TEXT"}
                ]
            },
            "regulators": {
                "name": "regulators",
                "columns": [
                    {"name": "id", "type": "INT PRIMARY KEY AUTO_INCREMENT"},
                    {"name": "name", "type": "VARCHAR(100)"},
                    {"name": "type", "type": "VARCHAR(50)"},
                    {"name": "contact_info", "type": "TEXT"}
                ]
            }
        }
    }
    
    # 4. HEBREW TEXT REQUIREMENTS
    print("\n🔤 4. HEBREW TEXT PRESERVATION REQUIREMENTS")
    print("-" * 40)
    
    hebrew_config = {
        "database": {
            "charset": "utf8mb4",
            "collation": "utf8mb4_unicode_ci",
            "connection_charset": "utf8mb4"
        },
        "web_app": {
            "html_charset": "UTF-8",
            "content_type": "text/html; charset=utf-8",
            "meta_charset": '<meta charset="UTF-8">',
            "text_direction": "rtl",
            "language": "he"
        },
        "css_requirements": {
            "direction": "rtl",
            "font_family": ["Arial", "Tahoma", "Segoe UI", "Open Sans Hebrew"],
            "text_align": "right"
        },
        "form_handling": {
            "encoding": "UTF-8",
            "submit_method": "POST",
            "accept_charset": "UTF-8"
        },
        "export_formats": {
            "csv": "UTF-8 with BOM",
            "excel": "UTF-8",
            "pdf": "Support Hebrew fonts"
        }
    }
    
    # 5. WEB APP DESIGN RECOMMENDATIONS
    print("\n🌐 5. WEB APPLICATION DESIGN RECOMMENDATIONS")
    print("-" * 40)
    
    web_app_recommendations = {
        "architecture": {
            "backend": "PHP/Laravel or Python/Django",
            "database": "MySQL 8.0+ or PostgreSQL 13+",
            "frontend": "Bootstrap 5 with RTL support",
            "css_framework": "Bootstrap RTL or custom RTL CSS"
        },
        "key_features": [
            "Inspection management dashboard",
            "Building and manager master data",
            "Inspection scheduling and tracking",
            "Report generation and distribution",
            "File upload for defect reports",
            "Search and filtering capabilities",
            "Export to Excel/PDF",
            "User authentication and roles",
            "Audit trail for changes",
            "Mobile-responsive design"
        ],
        "ui_considerations": [
            "Right-to-left text direction",
            "Hebrew-friendly fonts",
            "Date pickers with Hebrew calendar support",
            "Dropdown menus with Hebrew options",
            "Form validation in Hebrew",
            "Error messages in Hebrew",
            "Navigation in Hebrew"
        ],
        "data_validation": [
            "Building ID format validation",
            "Date range validation",
            "Required field validation",
            "File upload validation",
            "Hebrew text length limits",
            "Dropdown option validation"
        ]
    }
    
    # 6. DATA INSIGHTS
    print("\n📈 6. KEY DATA INSIGHTS")
    print("-" * 40)
    
    data_insights = {
        "data_volume": {
            "total_inspections": len(df_main),
            "unique_buildings": len(buildings_used),
            "unique_managers": len(managers_used), 
            "unique_types": len(types_used),
            "unique_leaders": len(leaders_used)
        },
        "data_quality": {
            "records_with_dates": int(df_main['לו"ז ביצוע\nמתואם/ ריאלי'].notna().sum()),
            "records_with_notes": int(df_main['התרשמות\nמהבדיקה'].notna().sum()),
            "records_with_regulators": int(df_main['רגולטור\n1'].notna().sum()),
            "completion_rate": f"{(df_main['לו\"ז ביצוע\nמתואם/ ריאלי'].notna().sum() / len(df_main) * 100):.1f}%"
        },
        "business_rules": [
            "Each inspection must have a building ID and type",
            "Inspection rounds are numbered 1-4",
            "Multiple regulators can be assigned to one inspection",
            "Reports can be distributed with tracking dates",
            "Repeat inspections are tracked with yes/no flag",
            "File attachments for defect reports are supported"
        ]
    }
    
    print(f"Data Volume Summary:")
    for key, value in data_insights["data_volume"].items():
        print(f"  {key}: {value}")
        
    print(f"\nData Quality Summary:")
    for key, value in data_insights["data_quality"].items():
        print(f"  {key}: {value}")
    
    # 7. SAVE COMPLETE ANALYSIS
    complete_analysis = {
        "analysis_metadata": {
            "file_analyzed": file_path,
            "analysis_date": datetime.now().isoformat(),
            "total_sheets": 2,
            "sheet_names": ["טבלה מרכזת", "ערכים"]
        },
        "lookup_data": lookup_data,
        "column_mapping": column_mapping,
        "database_schema": db_schema,
        "hebrew_requirements": hebrew_config,
        "web_app_recommendations": web_app_recommendations,
        "data_insights": data_insights
    }
    
    output_file = "/home/QuantNova/IDF-/FINAL_COMPREHENSIVE_ANALYSIS.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(complete_analysis, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ ANALYSIS COMPLETE!")
    print(f"📄 Full analysis saved to: {output_file}")
    
    return complete_analysis

if __name__ == "__main__":
    comprehensive_analysis()