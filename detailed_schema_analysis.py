#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detailed Schema Analysis for Excel File
Creates proper column mappings and schema recommendations
"""

import pandas as pd
import json
from pathlib import Path

def detailed_schema_analysis():
    """
    Extract proper column headers and create detailed schema mapping
    """
    file_path = "/home/QuantNova/IDF-/קובץ בדיקות כולל לקריית התקשוב גרסא מלאה 150725 (1).xlsx"
    
    print("DETAILED SCHEMA ANALYSIS")
    print("=" * 60)
    
    # Read both sheets with proper header detection
    
    # Sheet 1: טבלה מרכזת (Main Table)
    print("\n1. MAIN TABLE ANALYSIS (טבלה מרכזת)")
    print("-" * 40)
    
    # Read with different header row strategies
    df_main_no_header = pd.read_excel(file_path, sheet_name='טבלה מרכזת', header=None)
    df_main_header3 = pd.read_excel(file_path, sheet_name='טבלה מרכזת', header=3)
    
    print("Raw header row (row 3):")
    header_row = df_main_no_header.iloc[3].tolist()
    for i, header in enumerate(header_row):
        if pd.notna(header):
            print(f"  Column {i}: {header}")
    
    print(f"\nDimensions with header row 3: {df_main_header3.shape}")
    print("Column names from row 3:")
    for i, col in enumerate(df_main_header3.columns):
        print(f"  {i}: {col}")
    
    # Show sample data with proper headers
    print("\nSample data (first 10 rows):")
    sample_df = df_main_header3.head(10)
    for idx, row in sample_df.iterrows():
        print(f"Row {idx}: {dict(row.dropna())}")
        if idx >= 4:  # Limit output
            break
    
    # Sheet 2: ערכים (Values/Lookup)
    print("\n\n2. VALUES/LOOKUP TABLE ANALYSIS (ערכים)")
    print("-" * 40)
    
    df_values = pd.read_excel(file_path, sheet_name='ערכים', header=None)
    
    print("Values sheet structure analysis:")
    print(f"Dimensions: {df_values.shape}")
    
    # Find where actual data starts for each "column group"
    print("\nColumn groups identified:")
    col_groups = {}
    current_group = None
    
    for col_idx in range(df_values.shape[1]):
        col_data = df_values[col_idx].dropna()
        if len(col_data) > 0:
            first_value = str(col_data.iloc[0])
            # Check if this looks like a header
            if first_value in ['מבנה', 'מנהל מבנה', 'צוות אדום', 'סוג בדיקה', 'מוביל בדיקה', 
                              'סבב בדיקות', 'רגולטור 1,2,3,4', 'האם מתואם מול זכיין?', 
                              'צרופת דו"ח ליקויים', 'האם הדו"ח הופץ', 'בדיקה חוזרת']:
                current_group = first_value
                col_groups[current_group] = {
                    'header_col': col_idx,
                    'data_col': col_idx + 1 if col_idx + 1 < df_values.shape[1] else None,
                    'values': []
                }
                
                # Get values from next column if available
                if col_groups[current_group]['data_col'] is not None:
                    data_col = df_values[col_groups[current_group]['data_col']].dropna()
                    col_groups[current_group]['values'] = data_col.tolist()
    
    for group_name, group_data in col_groups.items():
        print(f"\n  {group_name}:")
        print(f"    Header column: {group_data['header_col']}")
        print(f"    Data column: {group_data['data_col']}")
        print(f"    Values ({len(group_data['values'])}): {group_data['values'][:10]}")  # First 10 values
    
    # Create schema recommendations
    print("\n\n3. DATABASE SCHEMA RECOMMENDATIONS")
    print("-" * 40)
    
    # Main table schema
    main_table_schema = {
        "table_name": "inspections",
        "description": "Main inspection tracking table (טבלה מרכזת)",
        "columns": [
            {"name": "building_id", "type": "VARCHAR(10)", "hebrew": "מבנה", "description": "Building identifier"},
            {"name": "building_manager", "type": "VARCHAR(100)", "hebrew": "מנהל מבנה", "description": "Building manager name"},
            {"name": "red_team", "type": "VARCHAR(200)", "hebrew": "צוות אדום", "description": "Red team members"},
            {"name": "inspection_type", "type": "VARCHAR(100)", "hebrew": "סוג הבדיקה", "description": "Type of inspection"},
            {"name": "inspection_leader", "type": "VARCHAR(100)", "hebrew": "מוביל הבדיקה", "description": "Inspection team leader"},
            {"name": "inspection_round", "type": "INT", "hebrew": "סבב בדיקות", "description": "Inspection round number"},
            {"name": "regulator_1", "type": "VARCHAR(50)", "hebrew": "רגולטור 1", "description": "Primary regulator"},
            {"name": "regulator_2", "type": "VARCHAR(50)", "hebrew": "רגולטור 2", "description": "Secondary regulator"},
            {"name": "regulator_3", "type": "VARCHAR(50)", "hebrew": "רגולטור 3", "description": "Tertiary regulator"},
            {"name": "regulator_4", "type": "VARCHAR(50)", "hebrew": "רגולטור 4", "description": "Quaternary regulator"},
            {"name": "execution_schedule", "type": "DATE", "hebrew": "לו\"ז ביצוע מתואם/ ריאלי", "description": "Scheduled/actual execution date"},
            {"name": "target_completion", "type": "DATE", "hebrew": "יעד לסיום", "description": "Target completion date"},
            {"name": "coordinated_with_contractor", "type": "BOOLEAN", "hebrew": "האם מתואם מול זכיין?", "description": "Coordinated with contractor"},
            {"name": "defect_report_attached", "type": "VARCHAR(500)", "hebrew": "צרופת דו\"ח ליקויים", "description": "Defect report file path"},
            {"name": "report_distributed", "type": "BOOLEAN", "hebrew": "האם הדו\"ח הופץ", "description": "Report distributed flag"},
            {"name": "distribution_date", "type": "DATE", "hebrew": "תאריך הפצת הדו\"ח", "description": "Report distribution date"},
            {"name": "repeat_inspection", "type": "BOOLEAN", "hebrew": "בדיקה חוזרת", "description": "Requires repeat inspection"},
            {"name": "inspection_notes", "type": "TEXT", "hebrew": "התרשמות מהבדיקה", "description": "Inspection impressions/notes"}
        ]
    }
    
    # Lookup tables schema
    lookup_tables_schema = {
        "buildings": {
            "table_name": "buildings",
            "description": "Building master data",
            "columns": [
                {"name": "building_id", "type": "VARCHAR(10) PRIMARY KEY", "description": "Building identifier"},
                {"name": "building_name", "type": "VARCHAR(200)", "description": "Building full name"}
            ]
        },
        "managers": {
            "table_name": "building_managers", 
            "description": "Building managers lookup",
            "columns": [
                {"name": "manager_id", "type": "INT PRIMARY KEY AUTO_INCREMENT", "description": "Manager ID"},
                {"name": "manager_name", "type": "VARCHAR(100)", "description": "Manager full name"}
            ]
        },
        "teams": {
            "table_name": "red_teams",
            "description": "Red team configurations",
            "columns": [
                {"name": "team_id", "type": "INT PRIMARY KEY AUTO_INCREMENT", "description": "Team ID"},
                {"name": "team_members", "type": "VARCHAR(200)", "description": "Team member names"}
            ]
        },
        "inspection_types": {
            "table_name": "inspection_types",
            "description": "Types of inspections",
            "columns": [
                {"name": "type_id", "type": "INT PRIMARY KEY AUTO_INCREMENT", "description": "Type ID"},
                {"name": "type_name", "type": "VARCHAR(100)", "description": "Inspection type name"},
                {"name": "type_description", "type": "TEXT", "description": "Detailed description"}
            ]
        },
        "regulators": {
            "table_name": "regulators",
            "description": "Regulatory bodies",
            "columns": [
                {"name": "regulator_id", "type": "INT PRIMARY KEY AUTO_INCREMENT", "description": "Regulator ID"},
                {"name": "regulator_name", "type": "VARCHAR(100)", "description": "Regulator name"},
                {"name": "regulator_type", "type": "VARCHAR(50)", "description": "Type/level of regulator"}
            ]
        }
    }
    
    print("MAIN TABLE (inspections):")
    for col in main_table_schema["columns"]:
        print(f"  {col['name']} ({col['type']}) - {col['hebrew']} - {col['description']}")
    
    print("\nLOOKUP TABLES:")
    for table_name, table_info in lookup_tables_schema.items():
        print(f"\n  {table_info['table_name']}:")
        for col in table_info["columns"]:
            print(f"    {col['name']} ({col['type']}) - {col['description']}")
    
    # Hebrew text preservation requirements
    print("\n\n4. HEBREW TEXT PRESERVATION REQUIREMENTS")
    print("-" * 40)
    
    hebrew_requirements = {
        "database_charset": "utf8mb4",
        "database_collation": "utf8mb4_unicode_ci",
        "connection_charset": "utf8mb4",
        "html_meta_charset": "UTF-8",
        "content_type": "text/html; charset=utf-8",
        "form_encoding": "application/x-www-form-urlencoded; charset=UTF-8",
        "json_encoding": "UTF-8",
        "csv_export_encoding": "UTF-8 with BOM",
        "rtl_support": True,
        "font_recommendations": ["Arial", "Tahoma", "Segoe UI", "Open Sans Hebrew"],
        "text_direction": "rtl"
    }
    
    for key, value in hebrew_requirements.items():
        print(f"  {key}: {value}")
    
    # Save complete analysis
    complete_analysis = {
        "main_table_schema": main_table_schema,
        "lookup_tables_schema": lookup_tables_schema,
        "hebrew_requirements": hebrew_requirements,
        "column_groups": col_groups,
        "data_insights": {
            "total_inspections": df_main_header3.shape[0],
            "total_buildings": len(col_groups.get('מבנה', {}).get('values', [])),
            "unique_inspection_types": len(col_groups.get('סוג בדיקה', {}).get('values', [])),
            "unique_managers": len(col_groups.get('מנהל מבנה', {}).get('values', [])),
            "regulators_count": len(col_groups.get('רגולטור 1,2,3,4', {}).get('values', []))
        }
    }
    
    # Save to file
    output_file = "/home/QuantNova/IDF-/detailed_schema_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(complete_analysis, f, ensure_ascii=False, indent=2)
    
    print(f"\n\nComplete analysis saved to: {output_file}")
    return complete_analysis

if __name__ == "__main__":
    detailed_schema_analysis()