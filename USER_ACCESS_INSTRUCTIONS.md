# IDF Testing Infrastructure - User Access Instructions

## 🎯 System Overview

The IDF Testing Infrastructure is a comprehensive Hebrew data management system designed for managing building inspections and testing data for the IDF Communications City (קריית התקשוב). The system provides a complete solution with:

- **PostgreSQL Database** with Hebrew UTF-8 support
- **FastAPI Backend** for data processing and API services
- **Web Frontend** with Hebrew RTL support
- **Excel Data Processing** for Hebrew content (494 records loaded)
- **Redis Caching** for performance optimization

---

## 🚀 Quick Start Guide

### 1. System Activation

To start the complete system, run the activation script:

```bash
cd /home/QuantNova/IDF-
./activate_system.sh
```

This script will:
- ✅ Start PostgreSQL and Redis containers
- ✅ Launch the backend API service
- ✅ Start the frontend web application
- ✅ Verify all integrations are working
- ✅ Load Hebrew Excel data (494 records)

### 2. Access the System

Once activated, you can access:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend App** | http://localhost:3001 | Main Hebrew web application |
| **Backend API** | http://localhost:8001 | REST API endpoints |
| **API Documentation** | http://localhost:8001/docs | Interactive API documentation |

---

## 🌐 Frontend Usage Guide

### Main Interface Features

1. **בדיקת מצב המערכת (System Health Check)**
   - Click: "🔄 בדוק מצב שרת"
   - Shows: Database connectivity, API status, system version

2. **רשימת מבנים (Buildings List)**
   - Click: "🏢 טען רשימת מבנים"
   - Displays: Building IDs, names, and managers in Hebrew

3. **נתוני אקסל עבריים (Hebrew Excel Data)**
   - Click: "📊 טען נתוני אקסל"
   - Shows: First 10 records from the Hebrew Excel file
   - Total: 494 records available

### Navigation Tips

- The interface is fully RTL (Right-to-Left) for Hebrew text
- All buttons and menus are in Hebrew
- Data tables display Hebrew content correctly
- Real-time status updates show connection status

---

## 🔌 API Usage Guide

### Health Check Endpoint

```bash
curl http://localhost:8001/api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "api_version": "1.0.0"
}
```

### Buildings Data Endpoint

```bash
curl http://localhost:8001/api/v1/buildings
```

**Response:**
```json
{
  "buildings": [
    {"id": "10A", "name": "בניין 10A", "manager": "יוסי כהן"},
    {"id": "15B", "name": "בניין 15B", "manager": "שרה לוי"},
    {"id": "20C", "name": "בניין 20C", "manager": "דוד ישראלי"}
  ]
}
```

### Hebrew Excel Data Endpoint

```bash
curl http://localhost:8001/api/v1/excel-data
```

**Response:**
```json
{
  "status": "success",
  "total_records": 494,
  "data": [...],
  "message": "Hebrew Excel data loaded successfully"
}
```

---

## 🗄️ Database Access

### PostgreSQL Connection Details

- **Host:** localhost
- **Port:** 5433
- **Database:** idf_testing
- **Username:** idf_user
- **Password:** dev_password_change_in_production

### Direct Database Access

```bash
docker exec -it idf_postgres psql -U idf_user -d idf_testing
```

### Redis Cache Access

```bash
docker exec -it idf_redis redis-cli -a dev_redis_password
```

---

## 📊 System Monitoring

### Real-time Health Monitoring

Check system status anytime:

```bash
# Backend health
curl http://localhost:8001/api/v1/health

# Service status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# View logs
docker-compose logs -f
```

### Port Usage

| Port | Service | Status |
|------|---------|--------|
| 3001 | Frontend Web App | ✅ Active |
| 5433 | PostgreSQL Database | ✅ Active |
| 6380 | Redis Cache | ✅ Active |
| 8001 | Backend API | ✅ Active |

---

## 🔧 System Management

### Starting Services

```bash
# Complete system activation
./activate_system.sh

# Individual services
docker-compose up -d postgres redis
docker-compose up -d backend frontend
```

### Stopping Services

```bash
# Stop all services
./stop.sh

# Stop individual services
docker-compose down
```

### Restarting Services

```bash
# Restart complete system
./restart.sh

# Restart specific service
docker-compose restart backend
```

---

## 📁 File Structure

```
/home/QuantNova/IDF-/
├── activate_system.sh          # System activation script
├── simple_frontend.html        # Hebrew web application
├── simple_backend.py          # FastAPI backend service
├── docker-compose.yml         # Container orchestration
├── index.html                 # Frontend served file
├── קובץ בדיקות כולל לקריית התקשוב גרסא מלאה 150725 (1).xlsx  # Hebrew Excel data
└── backend_env/               # Python virtual environment
```

---

## 🧪 Testing Workflows

### End-to-End Testing

1. **Open Frontend:** http://localhost:3001
2. **Test Health Check:** Click "בדוק מצב שרת"
3. **Load Buildings:** Click "טען רשימת מבנים"
4. **Load Excel Data:** Click "טען נתוני אקסל"
5. **Verify Results:** Check that all Hebrew text displays correctly

### API Testing

```bash
# Test all endpoints
curl http://localhost:8001/api/v1/health
curl http://localhost:8001/api/v1/buildings
curl http://localhost:8001/api/v1/excel-data
```

### Database Testing

```bash
# Test PostgreSQL
docker exec idf_postgres psql -U idf_user -d idf_testing -c "SELECT version();"

# Test Redis
docker exec idf_redis redis-cli -a dev_redis_password ping
```

---

## 🚨 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using the port
   ss -tlnp | grep ":8001"
   
   # Kill process if needed
   pkill -f "simple_backend.py"
   ```

2. **Database Connection Failed**
   ```bash
   # Restart PostgreSQL
   docker-compose restart postgres
   
   # Check logs
   docker-compose logs postgres
   ```

3. **Frontend Not Loading**
   ```bash
   # Restart frontend server
   pkill -f "http.server"
   cd /home/QuantNova/IDF-
   python3 -m http.server 3001 &
   ```

### Support Commands

```bash
# System status
./activate_system.sh

# View all logs
docker-compose logs -f

# Check running services
docker ps -a

# System resource usage
docker stats
```

---

## 📞 Contact & Support

For technical support or questions about the IDF Testing Infrastructure:

- **System Documentation:** Available in `/home/QuantNova/IDF-/`
- **API Documentation:** http://localhost:8001/docs
- **Log Files:** `docker-compose logs -f`

---

## 🔒 Security Notes

- Default passwords are for development only
- Change all credentials before production deployment
- Database is accessible only locally (localhost)
- API endpoints include CORS protection
- Hebrew text encoding is properly handled throughout

---

*Last Updated: July 17, 2025*
*System Version: 1.0.0*
*Agent 5: System Integration & Activation Director*