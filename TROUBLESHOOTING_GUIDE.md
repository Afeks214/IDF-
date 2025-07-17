# IDF Testing Infrastructure - Troubleshooting Guide

## 🚨 Quick Diagnostics

### System Status Check
```bash
# Run the activation script to verify all components
./activate_system.sh

# Check all services status
curl http://localhost:8001/api/v1/health
curl http://localhost:3001/
docker ps -a
```

---

## 🔧 Common Issues & Solutions

### 1. Port Already in Use

**Symptoms:**
- Error: "Address already in use"
- Cannot start backend on port 8001
- Cannot start frontend on port 3001

**Solutions:**
```bash
# Check what's using the ports
ss -tlnp | grep ":8001"
ss -tlnp | grep ":3001"

# Kill conflicting processes
pkill -f "simple_backend.py"
pkill -f "http.server"

# Restart services
./activate_system.sh
```

### 2. Database Connection Failed

**Symptoms:**
- Backend API health check shows database error
- PostgreSQL not responding
- Connection refused errors

**Solutions:**
```bash
# Check PostgreSQL container status
docker ps | grep postgres

# Restart PostgreSQL
docker-compose restart postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test direct connection
docker exec idf_postgres psql -U idf_user -d idf_testing -c "SELECT 1;"
```

### 3. Redis Connection Issues

**Symptoms:**
- Cache not working
- Redis authentication errors
- NOAUTH errors

**Solutions:**
```bash
# Check Redis container
docker ps | grep redis

# Test Redis connection
docker exec idf_redis redis-cli -a dev_redis_password ping

# Restart Redis
docker-compose restart redis

# Check Redis logs
docker-compose logs redis
```

### 4. Frontend Not Loading

**Symptoms:**
- Cannot access http://localhost:3001
- Page not found errors
- Frontend server not responding

**Solutions:**
```bash
# Check if frontend server is running
ss -tlnp | grep ":3001"

# Restart frontend server
cd /home/QuantNova/IDF-
pkill -f "http.server"
python3 -m http.server 3001 &

# Verify index.html exists
ls -la index.html
```

### 5. Hebrew Text Not Displaying

**Symptoms:**
- Garbled text in browser
- Question marks or boxes instead of Hebrew
- Encoding issues

**Solutions:**
```bash
# Check file encoding
file -i index.html
file -i "קובץ בדיקות כולל לקריית התקשוב גרסא מלאה 150725 (1).xlsx"

# Verify database encoding
docker exec idf_postgres psql -U idf_user -d idf_testing -c "SHOW SERVER_ENCODING;"

# Test Hebrew API endpoint
curl -s http://localhost:8001/api/v1/buildings | head
```

### 6. Excel Data Not Loading

**Symptoms:**
- Excel endpoint returns error
- No data or empty records
- File not found errors

**Solutions:**
```bash
# Check if Excel file exists
ls -la "קובץ בדיקות כולל לקריית התקשוב גרסא מלאה 150725 (1).xlsx"

# Test Excel endpoint directly
curl -s http://localhost:8001/api/v1/excel-data | jq

# Check backend logs
tail -f backend.log

# Verify Python dependencies
backend_env/bin/pip list | grep -E "(pandas|openpyxl)"
```

### 7. Docker Container Issues

**Symptoms:**
- Containers not starting
- Exit codes in docker ps
- Container health check failures

**Solutions:**
```bash
# Check container status
docker ps -a

# Check container logs
docker-compose logs [container_name]

# Restart all containers
docker-compose down
docker-compose up -d

# Check Docker system resources
docker system df
docker stats
```

---

## 🔍 Diagnostic Commands

### Service Health Checks
```bash
# Backend API
curl -f http://localhost:8001/api/v1/health || echo "Backend FAILED"

# Frontend
curl -f http://localhost:3001/ > /dev/null && echo "Frontend OK" || echo "Frontend FAILED"

# Database
docker exec idf_postgres pg_isready -U idf_user -d idf_testing && echo "DB OK" || echo "DB FAILED"

# Redis
docker exec idf_redis redis-cli -a dev_redis_password ping && echo "Redis OK" || echo "Redis FAILED"
```

### Log Monitoring
```bash
# Watch all logs in real-time
docker-compose logs -f

# Backend application logs
tail -f backend.log

# Frontend server logs
tail -f frontend.log

# System logs
journalctl -f -u docker
```

### Resource Monitoring
```bash
# Container resource usage
docker stats

# System memory and disk
free -h
df -h

# Network connections
ss -tuln
```

---

## 🛠️ Recovery Procedures

### Complete System Reset
```bash
# Stop all services
docker-compose down

# Remove containers (keeps data)
docker-compose rm -f

# Remove volumes (WARNING: destroys data)
docker-compose down -v

# Restart from scratch
./activate_system.sh
```

### Database Recovery
```bash
# Backup current database
docker exec idf_postgres pg_dump -U idf_user idf_testing > backup.sql

# Reset database
docker-compose restart postgres

# Restore from backup if needed
docker exec -i idf_postgres psql -U idf_user idf_testing < backup.sql
```

### Service Restart Sequence
```bash
# 1. Stop all application services
pkill -f "simple_backend.py"
pkill -f "http.server"

# 2. Restart infrastructure
docker-compose restart postgres redis

# 3. Wait for infrastructure
sleep 10

# 4. Start application services
./activate_system.sh
```

---

## ⚡ Performance Troubleshooting

### Slow Response Times
```bash
# Check system load
top
htop

# Check container resources
docker stats

# Test endpoint response times
time curl http://localhost:8001/api/v1/health
time curl http://localhost:8001/api/v1/excel-data
```

### Memory Issues
```bash
# Check memory usage
free -h
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Restart memory-heavy services
docker-compose restart backend
```

### Disk Space Issues
```bash
# Check disk usage
df -h
docker system df

# Clean up Docker
docker system prune -f
docker volume prune -f
```

---

## 🔐 Security Troubleshooting

### Permission Issues
```bash
# Check file permissions
ls -la activate_system.sh
ls -la index.html

# Fix permissions
chmod +x activate_system.sh
chmod 644 index.html
```

### Network Security
```bash
# Check listening ports
ss -tuln | grep -E ":(3001|5433|6380|8001)"

# Verify local access only
netstat -an | grep LISTEN
```

---

## 📞 Emergency Procedures

### System Not Responding
1. **Check if host is reachable:** `ping localhost`
2. **Verify Docker is running:** `systemctl status docker`
3. **Force restart Docker:** `sudo systemctl restart docker`
4. **Reactivate system:** `./activate_system.sh`

### Data Corruption
1. **Stop all services:** `docker-compose down`
2. **Check data integrity:** `docker exec idf_postgres psql -U idf_user -d idf_testing -c "SELECT count(*) FROM pg_tables;"`
3. **Restore from backup if available**
4. **Reinitialize if necessary:** `docker-compose down -v && ./activate_system.sh`

### Complete System Failure
1. **Document the error:** `docker-compose logs > error.log`
2. **Reset environment:** `docker-compose down -v`
3. **Rebuild from scratch:** `./activate_system.sh`
4. **Reload Hebrew Excel data**

---

## 📋 Maintenance Checklist

### Daily Checks
- [ ] System health check: `./activate_system.sh`
- [ ] API endpoints responding
- [ ] Hebrew data displaying correctly
- [ ] Container health status

### Weekly Maintenance
- [ ] Check log sizes: `du -sh *.log`
- [ ] Database backup: `pg_dump...`
- [ ] Update containers: `docker-compose pull`
- [ ] Resource usage review

### Monthly Tasks
- [ ] Security updates
- [ ] Performance optimization
- [ ] Data archiving
- [ ] Documentation updates

---

## 🆘 Support Resources

### Log Locations
- **Backend:** `backend.log`
- **Frontend:** `frontend.log`
- **Docker:** `docker-compose logs`
- **System:** `/var/log/`

### Configuration Files
- **Docker Compose:** `docker-compose.yml`
- **Backend:** `simple_backend.py`
- **Frontend:** `simple_frontend.html`
- **Activation:** `activate_system.sh`

### Contact Information
- **System Documentation:** `USER_ACCESS_INSTRUCTIONS.md`
- **System Status:** `FINAL_SYSTEM_STATUS_REPORT.md`
- **API Documentation:** http://localhost:8001/docs

---

*Last Updated: July 17, 2025*  
*Agent 5: System Integration & Activation Director*