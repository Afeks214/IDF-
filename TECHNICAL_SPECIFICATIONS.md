# IDF Testing Infrastructure - Technical Specifications

## System Architecture

### High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Presentation  │    │    Business     │    │      Data       │
│      Layer      │◄──►│     Logic       │◄──►│     Layer       │
│                 │    │     Layer       │    │                 │
│  • React UI     │    │  • FastAPI      │    │  • PostgreSQL   │
│  • Hebrew RTL   │    │  • Business     │    │  • Redis Cache  │
│  • Responsive   │    │    Rules        │    │  • File Storage │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Technology Stack Detailed

#### Backend Components
- **Framework**: FastAPI 0.104+ (Python 3.12)
- **Database**: PostgreSQL 15+ with Hebrew collation support
- **Cache**: Redis 7+ for session and query caching
- **Authentication**: OAuth 2.0 + JWT tokens
- **File Storage**: MinIO/S3 for document management
- **Search**: Elasticsearch for advanced text search

#### Frontend Components
- **Framework**: React 18+ with TypeScript 5+
- **UI Library**: Material-UI v5 with RTL theme
- **State Management**: Redux Toolkit Query
- **Routing**: React Router v6
- **Forms**: React Hook Form with Yup validation
- **Charts**: Recharts for data visualization

#### Infrastructure
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Kubernetes for production deployment
- **Monitoring**: Prometheus + Grafana + AlertManager
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **CI/CD**: GitLab CI with security scanning

## Database Schema Design

### Core Entities

#### Buildings (מבנה) - Table: buildings
```sql
CREATE TABLE buildings (
    id SERIAL PRIMARY KEY,
    building_code VARCHAR(10) NOT NULL UNIQUE,
    building_name VARCHAR(100),
    manager_name VARCHAR(100),
    red_team VARCHAR(200),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Test Records (בדיקות) - Table: test_records
```sql
CREATE TABLE test_records (
    id SERIAL PRIMARY KEY,
    building_id INTEGER REFERENCES buildings(id),
    test_type VARCHAR(50) NOT NULL,
    test_leader VARCHAR(100),
    test_round INTEGER,
    test_date DATE,
    status VARCHAR(20) DEFAULT 'pending',
    results TEXT,
    report_distributed BOOLEAN DEFAULT FALSE,
    retest_required BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Test Types (סוגי בדיקות) - Table: test_types
```sql
CREATE TABLE test_types (
    id SERIAL PRIMARY KEY,
    type_name VARCHAR(100) NOT NULL UNIQUE,
    type_name_hebrew VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE
);
```

### Indexes for Performance
```sql
CREATE INDEX idx_test_records_building ON test_records(building_id);
CREATE INDEX idx_test_records_date ON test_records(test_date);
CREATE INDEX idx_test_records_status ON test_records(status);
CREATE INDEX idx_buildings_code ON buildings(building_code);
```

## API Specifications

### REST API Endpoints

#### Authentication
```
POST /api/v1/auth/login
POST /api/v1/auth/logout
POST /api/v1/auth/refresh
GET  /api/v1/auth/me
```

#### Buildings Management
```
GET    /api/v1/buildings                    # List all buildings
POST   /api/v1/buildings                    # Create new building
GET    /api/v1/buildings/{id}               # Get building details
PUT    /api/v1/buildings/{id}               # Update building
DELETE /api/v1/buildings/{id}               # Soft delete building
GET    /api/v1/buildings/{id}/tests         # Get tests for building
```

#### Test Records Management
```
GET    /api/v1/tests                        # List tests with filters
POST   /api/v1/tests                        # Create new test
GET    /api/v1/tests/{id}                   # Get test details
PUT    /api/v1/tests/{id}                   # Update test
DELETE /api/v1/tests/{id}                   # Soft delete test
POST   /api/v1/tests/{id}/complete          # Mark test as complete
POST   /api/v1/tests/bulk-import            # Import from Excel
```

#### Reporting
```
GET    /api/v1/reports/dashboard            # Dashboard summary
GET    /api/v1/reports/tests/export         # Export test data
GET    /api/v1/reports/buildings/summary    # Building status summary
POST   /api/v1/reports/custom               # Generate custom report
```

### API Response Format
```json
{
  "success": true,
  "data": {
    // Response data
  },
  "message": "Operation completed successfully",
  "timestamp": "2025-07-17T22:30:00Z",
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 523,
    "pages": 27
  }
}
```

## Security Implementation

### Authentication & Authorization
- **JWT Tokens**: Short-lived access tokens (15 min) + refresh tokens (7 days)
- **Role-Based Access Control (RBAC)**:
  - `admin`: Full system access
  - `manager`: Building management + test oversight
  - `tester`: Test execution + status updates
  - `viewer`: Read-only access
- **Multi-Factor Authentication**: TOTP for admin users
- **Session Management**: Redis-based session store

### Data Security
- **Encryption at Rest**: AES-256 for sensitive data
- **Encryption in Transit**: TLS 1.3 for all communications
- **Database Security**: Row-level security policies
- **Input Validation**: Comprehensive sanitization and validation
- **SQL Injection Prevention**: Parameterized queries only

### IDF Compliance Requirements
- **Data Classification**: Handling of restricted military data
- **Audit Logging**: Complete action trail for compliance
- **Network Isolation**: VPN-only access to production
- **Regular Security Scans**: Weekly vulnerability assessments
- **Incident Response**: 24/7 security monitoring

## Performance Specifications

### Response Time Requirements
| Endpoint Type | Target Response Time | Max Acceptable |
|---------------|---------------------|----------------|
| Authentication | <500ms | 1s |
| List Operations | <1s | 2s |
| Detail Views | <800ms | 1.5s |
| Report Generation | <3s | 5s |
| File Uploads | <2s | 4s |

### Scalability Requirements
- **Concurrent Users**: Support 500+ simultaneous users
- **Data Volume**: Handle 100K+ test records efficiently
- **File Storage**: Support up to 10GB of documents
- **Database Connections**: Pool of 20-50 connections
- **Memory Usage**: <2GB per application instance

### Caching Strategy
- **Redis Cache Layers**:
  - Session cache (15-minute TTL)
  - Query results cache (5-minute TTL)
  - Static data cache (1-hour TTL)
- **Browser Caching**: Static assets with 1-year cache
- **Database Query Optimization**: Materialized views for reports

## Data Migration Strategy

### Excel to Database Migration
```python
# Migration Pipeline Pseudocode
def migrate_excel_data():
    # Phase 1: Extract and validate
    excel_data = extract_excel_sheets()
    validated_data = validate_data_integrity(excel_data)
    
    # Phase 2: Transform and normalize
    normalized_buildings = normalize_buildings_data(validated_data)
    normalized_tests = normalize_tests_data(validated_data)
    
    # Phase 3: Load with rollback capability
    with database_transaction():
        load_buildings(normalized_buildings)
        load_test_records(normalized_tests)
        verify_migration_integrity()
```

### Data Validation Rules
- **Building Codes**: Must be 2-3 characters (alphanumeric)
- **Hebrew Text**: UTF-8 encoding validation
- **Date Formats**: ISO 8601 standard
- **Required Fields**: No null values for critical fields
- **Referential Integrity**: All foreign keys must exist

## Development Environment Setup

### Local Development Stack
```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: idf_testing
      POSTGRES_USER: dev_user
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    
  app:
    build: .
    environment:
      DATABASE_URL: postgresql://dev_user:dev_password@postgres:5432/idf_testing
      REDIS_URL: redis://redis:6379
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
```

### Development Dependencies
```txt
# requirements-dev.txt
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
black>=23.7.0
isort>=5.12.0
mypy>=1.5.0
pre-commit>=3.3.0
```

## Testing Strategy Implementation

### Unit Testing Framework
```python
# Example test structure
@pytest.mark.asyncio
async def test_create_building():
    """Test building creation with Hebrew characters."""
    building_data = {
        "building_code": "40",
        "building_name": "מבנה ראשי",
        "manager_name": "יוסי שמש"
    }
    
    result = await building_service.create_building(building_data)
    
    assert result.success is True
    assert result.data.building_code == "40"
    assert "יוסי שמש" in result.data.manager_name
```

### Integration Testing
- **Database Integration**: Test complete CRUD operations
- **API Integration**: Test all endpoints with realistic data
- **Cache Integration**: Verify Redis caching behavior
- **File Upload Integration**: Test document handling

### Load Testing Configuration
```python
# locust_test.py
from locust import HttpUser, task, between

class IDF_TestUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def view_dashboard(self):
        self.client.get("/api/v1/reports/dashboard")
    
    @task(2)
    def list_buildings(self):
        self.client.get("/api/v1/buildings")
    
    @task(1)
    def create_test_record(self):
        data = {
            "building_id": 1,
            "test_type": "הנדסית",
            "test_leader": "יגאל גזמן"
        }
        self.client.post("/api/v1/tests", json=data)
```

## Deployment Configuration

### Production Environment
```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: idf-testing-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: idf-testing
  template:
    metadata:
      labels:
        app: idf-testing
    spec:
      containers:
      - name: app
        image: idf-testing:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

### Monitoring Configuration
```yaml
# prometheus-rules.yaml
groups:
- name: idf-testing-alerts
  rules:
  - alert: HighResponseTime
    expr: http_request_duration_seconds{job="idf-testing"} > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time detected"
      
  - alert: DatabaseConnectionsHigh
    expr: pg_stat_activity_count > 40
    for: 2m
    labels:
      severity: critical
```

---

**Document Version**: 1.0  
**Last Updated**: July 17, 2025  
**Review Cycle**: Bi-weekly technical review  
**Approval Required**: Lead Architect, Security Team, IDF IT