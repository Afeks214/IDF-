#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel File Analysis Script for Hebrew Data
Analyzes all tabs in the Excel file and extracts complete data structure
"""

import pandas as pd
import openpyxl
import sys
import json
from pathlib import Path

def analyze_excel_file(file_path):
    """
    Comprehensive analysis of Excel file including all tabs and data structures
    """
    print(f"Analyzing Excel file: {file_path}")
    
    # Check if file exists
    if not Path(file_path).exists():
        print(f"ERROR: File not found: {file_path}")
        return None
    
    analysis_results = {
        "file_info": {
            "file_path": file_path,
            "file_size": Path(file_path).stat().st_size
        },
        "worksheets": {},
        "summary": {}
    }
    
    try:
        # Load workbook with openpyxl to get sheet names
        workbook = openpyxl.load_workbook(file_path, read_only=True)
        sheet_names = workbook.sheetnames
        workbook.close()
        
        print(f"Found {len(sheet_names)} worksheets:")
        for i, sheet_name in enumerate(sheet_names, 1):
            print(f"  {i}. {sheet_name}")
        
        analysis_results["summary"]["total_sheets"] = len(sheet_names)
        analysis_results["summary"]["sheet_names"] = sheet_names
        
        # Analyze each worksheet
        for sheet_name in sheet_names:
            print(f"\n--- Analyzing Sheet: {sheet_name} ---")
            
            try:
                # Read the sheet
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                
                sheet_analysis = {
                    "sheet_name": sheet_name,
                    "dimensions": {
                        "rows": len(df),
                        "columns": len(df.columns)
                    },
                    "data_types": {},
                    "sample_data": {},
                    "column_analysis": {},
                    "hebrew_content": False,
                    "empty_cells": 0,
                    "unique_values_count": {}
                }
                
                # Check for Hebrew content
                hebrew_found = False
                for col in df.columns:
                    for idx, value in df[col].head(20).items():  # Check first 20 rows
                        if pd.notna(value) and isinstance(value, str):
                            # Check for Hebrew characters (Unicode range)
                            if any('\u0590' <= char <= '\u05FF' for char in str(value)):
                                hebrew_found = True
                                break
                    if hebrew_found:
                        break
                
                sheet_analysis["hebrew_content"] = hebrew_found
                
                # Get sample data (first 10 rows)
                sample_rows = min(10, len(df))
                sample_data = {}
                for i in range(sample_rows):
                    row_data = {}
                    for col_idx, col in enumerate(df.columns):
                        cell_value = df.iloc[i, col_idx]
                        if pd.isna(cell_value):
                            row_data[f"col_{col_idx}"] = None
                        else:
                            row_data[f"col_{col_idx}"] = str(cell_value)
                    sample_data[f"row_{i}"] = row_data
                
                sheet_analysis["sample_data"] = sample_data
                
                # Analyze each column
                for col_idx, col in enumerate(df.columns):
                    col_data = df[col]
                    col_name = f"col_{col_idx}"
                    
                    # Data type analysis
                    non_null_data = col_data.dropna()
                    if len(non_null_data) > 0:
                        # Determine primary data type
                        if non_null_data.dtype == 'object':
                            # Check if it's numeric strings, dates, or text
                            numeric_count = 0
                            date_count = 0
                            text_count = 0
                            
                            for value in non_null_data.head(20):
                                str_val = str(value).strip()
                                
                                # Try to convert to number
                                try:
                                    float(str_val)
                                    numeric_count += 1
                                    continue
                                except ValueError:
                                    pass
                                
                                # Try to parse as date
                                try:
                                    pd.to_datetime(str_val)
                                    date_count += 1
                                    continue
                                except:
                                    pass
                                
                                text_count += 1
                            
                            if numeric_count > text_count and numeric_count > date_count:
                                data_type = "numeric_string"
                            elif date_count > text_count and date_count > numeric_count:
                                data_type = "date_string"
                            else:
                                data_type = "text"
                        else:
                            data_type = str(non_null_data.dtype)
                    else:
                        data_type = "empty"
                    
                    sheet_analysis["data_types"][col_name] = data_type
                    
                    # Column statistics
                    col_stats = {
                        "total_values": len(col_data),
                        "non_null_values": len(non_null_data),
                        "null_values": len(col_data) - len(non_null_data),
                        "unique_values": len(non_null_data.unique()) if len(non_null_data) > 0 else 0,
                        "data_type": data_type
                    }
                    
                    # Sample unique values (first 5)
                    if len(non_null_data) > 0:
                        unique_vals = non_null_data.unique()[:5]
                        col_stats["sample_values"] = [str(val) for val in unique_vals]
                    else:
                        col_stats["sample_values"] = []
                    
                    sheet_analysis["column_analysis"][col_name] = col_stats
                    sheet_analysis["unique_values_count"][col_name] = col_stats["unique_values"]
                
                # Count empty cells
                sheet_analysis["empty_cells"] = df.isnull().sum().sum()
                
                analysis_results["worksheets"][sheet_name] = sheet_analysis
                
                print(f"  Dimensions: {sheet_analysis['dimensions']['rows']} rows x {sheet_analysis['dimensions']['columns']} columns")
                print(f"  Hebrew content: {sheet_analysis['hebrew_content']}")
                print(f"  Empty cells: {sheet_analysis['empty_cells']}")
                
            except Exception as e:
                print(f"  ERROR analyzing sheet '{sheet_name}': {str(e)}")
                analysis_results["worksheets"][sheet_name] = {
                    "error": str(e),
                    "sheet_name": sheet_name
                }
        
        return analysis_results
        
    except Exception as e:
        print(f"ERROR: Failed to open Excel file: {str(e)}")
        return None

def print_detailed_analysis(results):
    """
    Print detailed analysis results in a readable format
    """
    if not results:
        print("No analysis results to display")
        return
    
    print("\n" + "="*80)
    print("COMPREHENSIVE EXCEL FILE ANALYSIS REPORT")
    print("="*80)
    
    print(f"\nFILE INFORMATION:")
    print(f"  Path: {results['file_info']['file_path']}")
    print(f"  Size: {results['file_info']['file_size']:,} bytes")
    
    print(f"\nSUMMARY:")
    print(f"  Total Worksheets: {results['summary']['total_sheets']}")
    print(f"  Worksheet Names: {', '.join(results['summary']['sheet_names'])}")
    
    print(f"\nDETAILED WORKSHEET ANALYSIS:")
    
    for sheet_name, sheet_data in results["worksheets"].items():
        print(f"\n{'-'*60}")
        print(f"WORKSHEET: {sheet_name}")
        print(f"{'-'*60}")
        
        if "error" in sheet_data:
            print(f"  ERROR: {sheet_data['error']}")
            continue
        
        print(f"  Dimensions: {sheet_data['dimensions']['rows']} rows × {sheet_data['dimensions']['columns']} columns")
        print(f"  Contains Hebrew: {sheet_data['hebrew_content']}")
        print(f"  Empty cells: {sheet_data['empty_cells']:,}")
        
        print(f"\n  COLUMN ANALYSIS:")
        for col_name, col_stats in sheet_data["column_analysis"].items():
            print(f"    {col_name}:")
            print(f"      Type: {col_stats['data_type']}")
            print(f"      Values: {col_stats['non_null_values']}/{col_stats['total_values']} (non-null/total)")
            print(f"      Unique: {col_stats['unique_values']}")
            if col_stats['sample_values']:
                sample_str = ', '.join([str(v)[:30] + ('...' if len(str(v)) > 30 else '') for v in col_stats['sample_values']])
                print(f"      Sample: {sample_str}")
        
        print(f"\n  SAMPLE DATA (first 5 rows):")
        sample_count = 0
        for row_key, row_data in sheet_data["sample_data"].items():
            if sample_count >= 5:
                break
            print(f"    {row_key}: {dict(list(row_data.items())[:5])}")  # Show first 5 columns
            sample_count += 1

def main():
    file_path = "/home/QuantNova/IDF-/קובץ בדיקות כולל לקריית התקשוב גרסא מלאה 150725 (1).xlsx"
    
    print("Starting Excel file analysis...")
    results = analyze_excel_file(file_path)
    
    if results:
        print_detailed_analysis(results)
        
        # Save results to JSON file (convert numpy types to native Python types)
        def convert_numpy_types(obj):
            if hasattr(obj, 'item'):
                return obj.item()
            elif isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            else:
                return obj
        
        results_serializable = convert_numpy_types(results)
        output_file = "/home/QuantNova/IDF-/excel_analysis_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_serializable, f, ensure_ascii=False, indent=2)
        print(f"\nDetailed analysis saved to: {output_file}")
    else:
        print("Analysis failed!")

if __name__ == "__main__":
    main()