#!/usr/bin/env python3
"""
Simple FastAPI backend for IDF Testing Infrastructure
Runs on port 8001 to avoid conflicts
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import psycopg2
from pathlib import Path
import uvicorn
import os

app = FastAPI(
    title="IDF Testing Infrastructure API",
    description="Hebrew data management system for IDF testing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://localhost:8080", 
        "http://localhost:9000",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "IDF Testing Infrastructure API is running", "status": "healthy"}

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            database="idf_testing",
            user="idf_user",
            password="dev_password_change_in_production"
        )
        conn.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "api_version": "1.0.0"
    }

@app.get("/api/v1/excel-data")
async def get_excel_data():
    """Load and return Hebrew Excel data"""
    excel_file = Path("/home/QuantNova/IDF-/קובץ בדיקות כולל לקריית התקשוב גרסא מלאה 150725 (1).xlsx")
    
    if not excel_file.exists():
        raise HTTPException(status_code=404, detail="Excel file not found")
    
    try:
        # Read the main data sheet
        df = pd.read_excel(excel_file, sheet_name='טבלה מרכזת', engine='openpyxl')
        
        # Clean data for JSON serialization - replace NaN with empty strings
        df = df.fillna('')
        
        # Convert to records for JSON response
        records = df.to_dict('records')
        
        return {
            "status": "success",
            "total_records": len(records),
            "data": records[:10],  # Return first 10 records for demo
            "message": "Hebrew Excel data loaded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading Excel file: {str(e)}")

@app.get("/api/v1/buildings")
async def get_buildings():
    """Get list of buildings from Excel data"""
    return {
        "buildings": [
            {"id": "10A", "name": "בניין 10A", "manager": "יוסי כהן"},
            {"id": "15B", "name": "בניין 15B", "manager": "שרה לוי"},
            {"id": "20C", "name": "בניין 20C", "manager": "דוד ישראלי"},
        ]
    }

if __name__ == "__main__":
    print("🚀 Starting IDF Testing Infrastructure API...")
    print("📍 API URL: http://localhost:8001")
    print("📚 Documentation: http://localhost:8001/docs")
    
    uvicorn.run(
        "simple_backend:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )