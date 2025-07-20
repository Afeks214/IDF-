# Enhanced Data Processing Infrastructure

## Overview

The Enhanced Data Processing Infrastructure provides comprehensive multi-format data ingestion, real-time streaming, and advanced Hebrew text processing capabilities for the IDF Testing Infrastructure.

## Core Components

### 1. HebrewDataProcessor
Advanced data processor with multi-format support and Hebrew text handling.

**Features:**
- Multi-format support (Excel, CSV, JSON)
- Hebrew text normalization and validation
- Automatic encoding detection
- Data quality metrics
- Chunk-based processing for large files

**Usage:**
```python
from app.services import HebrewDataProcessor

# Initialize processor
processor = HebrewDataProcessor(session)

# Process a file
result = await processor.process_file("/path/to/data.xlsx")

# Process streaming data
async for chunk_result in processor.stream_process_data(data_stream):
    print(f"Processed {chunk_result.records_processed} records")
```

### 2. StreamingDataPipeline
Real-time data streaming pipeline with monitoring and quality control.

**Features:**
- Real-time data ingestion
- Configurable batch processing
- Stream monitoring and metrics
- Error handling and retry logic
- Redis-based coordination

**Usage:**
```python
from app.services import StreamingDataPipeline, StreamConfig, StreamType

# Initialize pipeline
pipeline = StreamingDataPipeline(session, redis_client)
await pipeline.start()

# Create stream configuration
config = StreamConfig(
    stream_id="inspection_data_stream",
    stream_type=StreamType.REAL_TIME_FEED,
    batch_size=100,
    quality_threshold=0.8
)

# Create and start stream
stream_id = await pipeline.create_stream(config)
await pipeline.start_stream(stream_id)
```

### 3. DataQualityEngine
Comprehensive data quality validation with Hebrew text analysis.

**Features:**
- 30+ built-in validation rules
- Hebrew text format validation
- Business logic validation
- Quality scoring and reporting
- Performance monitoring

**Usage:**
```python
from app.services import DataQualityEngine

# Initialize engine
quality_engine = DataQualityEngine(session, redis_client)

# Validate dataset
quality_report = await quality_engine.validate_dataset(
    data=records,
    dataset_id="inspection_batch_001",
    enabled_rules=["hebrew_text_format", "required_field", "date_consistency"]
)

print(f"Quality Score: {quality_report.overall_score:.3f}")
print(f"Issues Found: {len(quality_report.issues)}")
```

### 4. IntegratedDataManager
Unified manager coordinating all data processing services.

**Features:**
- Single API for all data processing operations
- Background task processing
- Session management
- Performance monitoring
- Health checks

**Usage:**
```python
from app.services import IntegratedDataManager, ProcessingMode

# Initialize manager
manager = IntegratedDataManager(session, redis_client)
await manager.start()

# Process file
session_id = await manager.process_file(
    file_path="/path/to/inspections.xlsx",
    processing_mode=ProcessingMode.STREAMING,
    quality_threshold=0.8
)

# Monitor progress
status = await manager.get_session_status(session_id)
```

## API Endpoints

### File Processing
```http
POST /api/v1/data/upload-file
Content-Type: multipart/form-data

{
  "file": <file_data>,
  "processing_mode": "batch",
  "quality_threshold": 0.8,
  "validation_rules": ["hebrew_text_format", "required_field"]
}
```

### Stream Management
```http
POST /api/v1/data/stream/create
Content-Type: application/json

{
  "stream_type": "real_time_feed",
  "batch_size": 100,
  "quality_threshold": 0.8,
  "enable_monitoring": true
}
```

### Data Validation
```http
POST /api/v1/data/validate-data
Content-Type: application/json

{
  "data": [
    {
      "building_id": "מבנה-001",
      "building_manager": "יוסי כהן",
      "inspection_type": "בדיקת בטיחות"
    }
  ],
  "validation_rules": ["hebrew_text_format", "required_field"]
}
```

### Performance Dashboard
```http
GET /api/v1/data/performance/dashboard
```

## Configuration

### Environment Variables
```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Processing Configuration
DEFAULT_BATCH_SIZE=1000
DEFAULT_QUALITY_THRESHOLD=0.8
MAX_CONCURRENT_STREAMS=10

# Monitoring Configuration
ENABLE_PERFORMANCE_MONITORING=true
METRICS_RETENTION_HOURS=24
```

### Stream Configuration
```python
stream_config = StreamConfig(
    stream_id="custom_stream",
    stream_type=StreamType.REAL_TIME_FEED,
    batch_size=100,
    max_concurrent_batches=5,
    retry_attempts=3,
    retry_delay=1.0,
    timeout=30.0,
    quality_threshold=0.8,
    enable_monitoring=True,
    filter_rules={
        "building_id": {"min_length": 3},
        "inspection_type": {"contains": "בדיקת"}
    },
    transformation_rules={
        "building_manager": {"strip": True},
        "inspection_notes": {"lowercase": True}
    }
)
```

## Hebrew Text Processing

### Normalization Features
- Unicode normalization (NFD)
- Hebrew points (nikkud) removal
- Common ligature normalization
- Direction detection (RTL/LTR)
- Encoding issue detection

### Validation Rules
- Hebrew character validation
- Name format validation
- Mixed language detection
- Encoding consistency
- Text direction validation

### Example Hebrew Text Processing
```python
from app.services.hebrew_data_processor import HebrewDataProcessor

processor = HebrewDataProcessor(session)

# Clean and normalize Hebrew text
text = "שלום עולם"
cleaned = processor._clean_hebrew_text(text)
normalized = processor._normalize_hebrew_text(cleaned)

# Validate Hebrew names
validation_result = await processor._validate_hebrew_fields({
    "building_manager": "יוסי כהן",
    "inspection_leader": "רותי לוי"
})
```

## Quality Validation Rules

### Built-in Rules

#### Schema Validation
- **required_field**: Validates required fields are present
- **field_length**: Validates field length constraints
- **data_type**: Validates data type consistency

#### Hebrew Text Validation
- **hebrew_text_format**: Validates Hebrew text encoding
- **hebrew_name_validation**: Validates Hebrew name format
- **mixed_language_detection**: Detects inappropriate language mixing

#### Data Format Validation
- **date_format**: Validates date field formats
- **boolean_format**: Validates boolean field values
- **numeric_format**: Validates numeric field values

#### Business Logic Validation
- **date_consistency**: Validates date field relationships
- **status_consistency**: Validates status field logic
- **reference_integrity**: Validates foreign key relationships

#### Quality Metrics
- **completeness_ratio**: Validates data completeness
- **accuracy_score**: Validates data accuracy
- **duplicate_detection**: Detects duplicate records

### Custom Validation Rules
```python
from app.services.data_quality_engine import ValidationRule, ValidationCategory, ValidationSeverity

# Create custom rule
custom_rule = ValidationRule(
    rule_id="custom_hebrew_inspection_type",
    name="Hebrew Inspection Type Validation",
    description="Validates inspection type contains valid Hebrew terms",
    category=ValidationCategory.HEBREW_TEXT,
    severity=ValidationSeverity.ERROR,
    parameters={
        "valid_terms": ["בדיקת בטיחות", "בדיקת איכות", "בדיקת תקינות"]
    }
)

# Register rule
quality_engine.register_rule(custom_rule)
```

## Monitoring and Metrics

### Performance Metrics
- Processing throughput (records/second)
- Average processing time
- Error rates
- Quality scores
- Resource utilization

### Health Monitoring
```python
# Get system health
health_status = await manager.get_system_health()

# Get performance dashboard
dashboard = await manager.get_performance_dashboard()

# Get quality trends
trends = await quality_engine.get_quality_trends("dataset_id")
```

### Alerting
The system provides real-time alerts for:
- Processing failures
- Quality score degradation
- Performance threshold breaches
- Resource exhaustion
- Data consistency issues

## Best Practices

### File Processing
1. Use streaming mode for files > 10MB
2. Set appropriate quality thresholds
3. Enable monitoring for production data
4. Implement retry logic for network issues
5. Use batch processing for offline imports

### Hebrew Text Handling
1. Always validate encoding before processing
2. Use normalization for search and comparison
3. Implement proper RTL text display
4. Validate Hebrew names and addresses
5. Handle mixed language content appropriately

### Quality Validation
1. Define business-specific rules
2. Set appropriate quality thresholds
3. Monitor quality trends over time
4. Implement automated remediation
5. Generate quality reports regularly

### Performance Optimization
1. Use appropriate batch sizes
2. Enable Redis caching
3. Monitor memory usage
4. Implement connection pooling
5. Use asynchronous processing

## Error Handling

### Common Errors
- **Encoding Issues**: Use automatic encoding detection
- **Format Validation**: Implement format validation rules
- **Memory Issues**: Use streaming processing for large files
- **Network Timeouts**: Implement retry logic with exponential backoff
- **Data Inconsistencies**: Use business logic validation rules

### Error Recovery
```python
try:
    result = await processor.process_file(file_path)
except EncodingError:
    # Try different encoding
    result = await processor.process_file(file_path, encoding="cp1255")
except ValidationError as e:
    # Handle validation errors
    logger.error(f"Validation failed: {e.issues}")
    # Implement remediation logic
```

## Integration Examples

### FastAPI Integration
```python
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from app.services import IntegratedDataManager

app = FastAPI()
manager = IntegratedDataManager(session)

@app.post("/process-file")
async def process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    quality_threshold: float = 0.8
):
    # Save file and process in background
    session_id = await manager.process_file(
        file_path=file.filename,
        quality_threshold=quality_threshold
    )
    
    return {"session_id": session_id}
```

### Celery Integration
```python
from celery import Celery
from app.services import IntegratedDataManager

celery_app = Celery('idf_processing')

@celery_app.task
async def process_data_file(file_path: str, quality_threshold: float):
    manager = IntegratedDataManager(session)
    await manager.start()
    
    session_id = await manager.process_file(
        file_path=file_path,
        quality_threshold=quality_threshold
    )
    
    return session_id
```

## Testing

### Unit Tests
```python
import pytest
from app.services import HebrewDataProcessor, DataQualityEngine

@pytest.mark.asyncio
async def test_hebrew_text_processing():
    processor = HebrewDataProcessor(session)
    
    # Test Hebrew text normalization
    text = "שלום עולם"
    normalized = processor._normalize_hebrew_text(text)
    assert normalized == "שלום עולם"
    
    # Test validation
    issues = await processor._validate_hebrew_fields({
        "building_manager": "יוסי כהן"
    })
    assert len(issues) == 0
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_file_processing_pipeline():
    manager = IntegratedDataManager(session)
    await manager.start()
    
    # Process test file
    session_id = await manager.process_file(
        file_path="test_data.xlsx",
        quality_threshold=0.8
    )
    
    # Wait for completion
    await asyncio.sleep(5)
    
    # Check results
    status = await manager.get_session_status(session_id)
    assert status['status'] == 'completed'
```

## Support

For issues or questions regarding the Enhanced Data Processing Infrastructure, please refer to:

1. **Technical Documentation**: `/docs/api/`
2. **Error Logs**: `/logs/processing.log`
3. **Performance Metrics**: `/api/v1/data/performance/dashboard`
4. **Health Status**: `/api/v1/data/system/health`

## License

This enhanced data processing infrastructure is part of the IDF Testing Infrastructure project and is subject to the same licensing terms.