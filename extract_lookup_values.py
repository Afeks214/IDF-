#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract actual lookup values from the Values sheet
"""

import pandas as pd
import json

def extract_lookup_values():
    """
    Extract all lookup values from the ערכים sheet
    """
    file_path = "/home/QuantNova/IDF-/קובץ בדיקות כולל לקריית התקשוב גרסא מלאה 150725 (1).xlsx"
    
    print("EXTRACTING LOOKUP VALUES FROM ערכים SHEET")
    print("=" * 50)
    
    # Read the values sheet
    df = pd.read_excel(file_path, sheet_name='ערכים', header=None)
    
    # Manually extract each column group based on the pattern observed
    lookup_values = {}
    
    # Buildings (columns 1-2)
    buildings = []
    for i in range(1, len(df)):
        if pd.notna(df.iloc[i, 1]):
            buildings.append(str(df.iloc[i, 1]))
    lookup_values['buildings'] = [b for b in buildings if b not in ['מבנה']]
    
    # Building Managers (columns 3-4) 
    managers = []
    for i in range(1, len(df)):
        if pd.notna(df.iloc[i, 3]):
            managers.append(str(df.iloc[i, 3]))
    lookup_values['building_managers'] = [m for m in managers if m not in ['מנהל מבנה']]
    
    # Red Teams (columns 5-6)
    teams = []
    for i in range(1, len(df)):
        if pd.notna(df.iloc[i, 5]):
            teams.append(str(df.iloc[i, 5]))
    lookup_values['red_teams'] = [t for t in teams if t not in ['צוות אדום']]
    
    # Inspection Types (columns 7-8)
    types = []
    for i in range(1, len(df)):
        if pd.notna(df.iloc[i, 7]):
            types.append(str(df.iloc[i, 7]))
    lookup_values['inspection_types'] = [t for t in types if t not in ['סוג בדיקה']]
    
    # Inspection Leaders (columns 9-10)
    leaders = []
    for i in range(1, len(df)):
        if pd.notna(df.iloc[i, 9]):
            leaders.append(str(df.iloc[i, 9]))
    lookup_values['inspection_leaders'] = [l for l in leaders if l not in ['מוביל בדיקה']]
    
    # Inspection Rounds (columns 11-12)
    rounds = []
    for i in range(1, len(df)):
        if pd.notna(df.iloc[i, 11]):
            rounds.append(str(df.iloc[i, 11]))
    lookup_values['inspection_rounds'] = [r for r in rounds if r not in ['סבב בדיקות']]
    
    # Regulators (columns 13-14)
    regulators = []
    for i in range(1, len(df)):
        if pd.notna(df.iloc[i, 13]):
            regulators.append(str(df.iloc[i, 13]))
    lookup_values['regulators'] = [r for r in regulators if r not in ['רגולטור 1,2,3,4']]
    
    # Yes/No values for various fields
    yes_no = ['כן', 'לא']
    lookup_values['yes_no_values'] = yes_no
    
    # Print extracted values
    for category, values in lookup_values.items():
        print(f"\n{category.upper()}:")
        for i, value in enumerate(values, 1):
            print(f"  {i}. {value}")
        print(f"  Total: {len(values)} items")
    
    # Also extract sample data from main table to show actual data usage
    print(f"\n\nSAMPLE DATA FROM MAIN TABLE:")
    print("-" * 30)
    
    df_main = pd.read_excel(file_path, sheet_name='טבלה מרכזת', header=3)
    
    # Show unique values for key columns
    buildings_used = [str(x) for x in df_main['מבנה'].dropna().unique().tolist()]
    print(f"\nUnique Buildings in use: {sorted(buildings_used)}")
    print(f"Unique Managers in use: {sorted(df_main['מנהל\\nמבנה'].dropna().unique().tolist())}")
    print(f"Unique Inspection Types in use: {sorted(df_main['סוג\\nהבדיקה'].dropna().unique().tolist())}")
    print(f"Unique Leaders in use: {sorted(df_main['מוביל\\nהבדיקה'].dropna().unique().tolist())}")
    
    # Check which regulators are actually used
    reg_cols = ['רגולטור\\n1', 'רגולטור\\n2', 'רגולטור\\n3', 'רגולטור\\n4']
    all_regulators_used = set()
    for col in reg_cols:
        if col in df_main.columns:
            regs = df_main[col].dropna().unique().tolist()
            all_regulators_used.update(regs)
    print(f"Regulators actually used: {sorted(list(all_regulators_used))}")
    
    # Data quality insights
    print(f"\n\nDATA QUALITY INSIGHTS:")
    print("-" * 25)
    print(f"Total inspection records: {len(df_main)}")
    print(f"Records with dates: {df_main['לו\"ז ביצוע\\nמתואם/ ריאלי'].notna().sum()}")
    print(f"Records with target dates: {df_main['יעד\\nלסיום'].notna().sum()}")
    print(f"Records with notes: {df_main['התרשמות\\nמהבדיקה'].notna().sum()}")
    
    # Save complete lookup values
    output_data = {
        'lookup_values': lookup_values,
        'data_statistics': {
            'total_records': len(df_main),
            'unique_buildings': len(df_main['מבנה'].dropna().unique()),
            'unique_managers': len(df_main['מנהל\\nמבנה'].dropna().unique()),
            'unique_types': len(df_main['סוג\\nהבדיקה'].dropna().unique()),
            'unique_leaders': len(df_main['מוביל\\nהבדיקה'].dropna().unique()),
            'records_with_dates': int(df_main['לו\"ז ביצוע\\nמתואם/ ריאלי'].notna().sum()),
            'records_with_notes': int(df_main['התרשמות\\nמהבדיקה'].notna().sum())
        }
    }
    
    output_file = "/home/QuantNova/IDF-/lookup_values_extracted.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nLookup values saved to: {output_file}")
    return output_data

if __name__ == "__main__":
    extract_lookup_values()