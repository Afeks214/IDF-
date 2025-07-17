# IDF Testing Infrastructure - Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the IDF Testing Infrastructure in a production environment with military-grade security, scalability, and reliability.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Internet/DMZ                                  │
├─────────────────────────────────────────────────────────────────┤
│                Load Balancer (Nginx)                            │
├─────────────────────────────────────────────────────────────────┤
│                  Kubernetes Cluster                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │   Frontend    │  │    Backend    │  │   Monitoring  │       │
│  │  (React SPA)  │  │  (FastAPI)    │  │ (Prometheus)  │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
│                                                                  │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │  PostgreSQL   │  │  Redis Cache  │  │   Grafana     │       │
│  │   Cluster     │  │   Cluster     │  │  Dashboard    │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### Components

- **Frontend**: React-based user interface (if applicable)
- **Backend**: FastAPI application with Hebrew data processing
- **Database**: PostgreSQL with read replicas
- **Cache**: Redis cluster for high availability
- **Load Balancer**: Nginx with SSL termination
- **Monitoring**: Prometheus, Grafana, AlertManager
- **Backup**: Automated encrypted backups
- **Security**: Network policies, RBAC, security scanning

## Prerequisites

### Infrastructure Requirements

1. **Kubernetes Cluster**
   - Kubernetes 1.25+
   - 3+ worker nodes
   - 16+ GB RAM per node
   - 100+ GB SSD storage per node

2. **External Dependencies**
   - Container registry (GitHub Container Registry recommended)
   - DNS management (for domain configuration)
   - SSL certificates (Let's Encrypt or enterprise CA)
   - SMTP server (for notifications)
   - S3-compatible storage (for backups)

3. **Required Tools**
   - kubectl
   - Docker
   - Helm 3.x
   - AWS CLI (if using AWS)
   - jq
   - curl

### Security Requirements

- Network segmentation with firewalls
- RBAC configured for least privilege
- Pod Security Standards enforced
- Image vulnerability scanning
- Runtime security monitoring

## Deployment Steps

### 1. Initial Setup

Clone the repository and navigate to the project directory:

```bash
git clone <repository-url>
cd IDF-testing-infrastructure
```

### 2. Configure Environment

Copy the production environment template:

```bash
cp config/production.env.template config/production.env
```

Edit `config/production.env` and update all `CHANGE_ME` values:

```bash
# Critical values to update:
SECRET_KEY=<secure-random-string>
POSTGRES_PASSWORD=<secure-database-password>
REDIS_PASSWORD=<secure-redis-password>
JWT_SECRET_KEY=<secure-jwt-secret>
DOMAIN=idf-testing.mil.il
# ... and others
```

### 3. SSL Certificates

#### Option A: Let's Encrypt (Recommended)

Install cert-manager:

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

#### Option B: Custom Certificates

Place your certificates in the `certs/` directory:

```bash
mkdir -p certs/
cp your-certificate.crt certs/tls.crt
cp your-private-key.key certs/tls.key
```

### 4. Deploy Infrastructure

Use the deployment manager script:

```bash
# Full deployment
./scripts/deployment-manager.sh deploy v1.0.0

# Or step by step:
./scripts/deployment-manager.sh setup-monitoring
./scripts/deployment-manager.sh deploy v1.0.0
```

### 5. Verify Deployment

Check deployment status:

```bash
./scripts/deployment-manager.sh status
```

Run health checks:

```bash
./scripts/health-monitor.sh check
```

### 6. Configure Monitoring

Access Grafana dashboard:

```bash
kubectl port-forward service/grafana 3000:3000 -n idf-testing
```

Default credentials: `admin` / `<generated-password>`

Get Grafana password:

```bash
kubectl get secret grafana-secret -n idf-testing -o jsonpath='{.data.admin-password}' | base64 -d
```

### 7. Setup Backups

Verify backup configuration:

```bash
./scripts/backup-system.sh health
```

Test backup:

```bash
./scripts/backup-system.sh full
```

## Configuration Reference

### Environment Variables

See `config/production.env.template` for a complete list of configuration options.

#### Critical Security Settings

```bash
# Application Security
SECRET_KEY=<64-character-random-string>
JWT_SECRET_KEY=<64-character-random-string>
DEBUG=false
ENVIRONMENT=production

# Database Security
POSTGRES_PASSWORD=<complex-password>
POSTGRES_REPLICATION_PASSWORD=<complex-password>

# Redis Security
REDIS_PASSWORD=<complex-password>

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100
```

#### Performance Tuning

```bash
# Database Connections
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30

# Application Workers
WORKERS=4
WORKER_CONNECTIONS=1000
WORKER_TIMEOUT=30

# Auto-scaling
HPA_MIN_REPLICAS=3
HPA_MAX_REPLICAS=10
HPA_CPU_THRESHOLD=70
HPA_MEMORY_THRESHOLD=80
```

### Kubernetes Resources

#### Resource Requests and Limits

```yaml
# Backend pods
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"

# Database pods
resources:
  requests:
    memory: "4Gi"
    cpu: "2000m"
  limits:
    memory: "8Gi"
    cpu: "4000m"
```

## Operations

### Monitoring and Alerting

#### Prometheus Metrics

Access Prometheus:

```bash
kubectl port-forward service/prometheus 9090:9090 -n idf-testing
```

Key metrics to monitor:
- `idf_service_health` - Service health status
- `http_requests_total` - Request volume and errors
- `pg_up` - Database connectivity
- `redis_up` - Cache connectivity

#### Grafana Dashboards

Pre-configured dashboards include:
- System Overview
- Application Performance
- Database Metrics
- Security Monitoring
- Error Tracking

#### AlertManager Rules

Critical alerts configured:
- Service Down
- High Error Rate
- Database Connection Failure
- High CPU/Memory Usage
- Disk Space Low
- Security Incidents

### Backup and Recovery

#### Automated Backups

Backups run automatically:
- Full backup: Weekly (Sunday 2 AM)
- Incremental backup: Every 6 hours
- Retention: 30 days
- Encryption: AES-256

#### Manual Backup

```bash
# Full backup
./scripts/backup-system.sh full

# Incremental backup
./scripts/backup-system.sh incremental
```

#### Restore Process

```bash
# Restore from backup
./scripts/backup-system.sh restore /path/to/backup.gpg

# Restore and switch database
./scripts/backup-system.sh restore /path/to/backup.gpg switch
```

### Scaling

#### Manual Scaling

```bash
# Scale backend
kubectl scale deployment backend --replicas=5 -n idf-testing

# Scale database (read replicas)
kubectl scale statefulset postgres-replica --replicas=2 -n idf-testing
```

#### Auto-scaling

Horizontal Pod Autoscaler is configured for:
- Backend: 3-10 replicas based on CPU/memory
- Frontend: 2-5 replicas based on CPU

### Updates and Rollbacks

#### Deploy New Version

```bash
./scripts/deployment-manager.sh upgrade v1.1.0
```

#### Rollback

```bash
# Rollback to previous version
./scripts/deployment-manager.sh rollback

# Rollback to specific revision
./scripts/deployment-manager.sh rollback 3
```

### Security Operations

#### Security Scanning

```bash
# Full security scan
./scripts/security-compliance.sh all

# Specific scans
./scripts/security-compliance.sh images
./scripts/security-compliance.sh network
./scripts/security-compliance.sh cis
```

#### Compliance Reports

Reports are generated in `/var/reports/security/`:
- CIS Kubernetes Benchmark
- Container vulnerability scans
- Network policy compliance
- RBAC configuration audit

## Troubleshooting

### Common Issues

#### Pod Startup Issues

```bash
# Check pod logs
kubectl logs -f deployment/backend -n idf-testing

# Check pod events
kubectl describe pod <pod-name> -n idf-testing

# Check node resources
kubectl top nodes
```

#### Database Connection Issues

```bash
# Test database connectivity
kubectl exec deployment/backend -n idf-testing -- pg_isready -h postgres-primary

# Check database logs
kubectl logs statefulset/postgres-primary -n idf-testing

# Check connection pool
kubectl exec deployment/backend -n idf-testing -- psql -h postgres-primary -c "SELECT count(*) FROM pg_stat_activity;"
```

#### Performance Issues

```bash
# Check resource usage
kubectl top pods -n idf-testing

# Check HPA status
kubectl get hpa -n idf-testing

# Check application metrics
curl http://localhost:8001/metrics
```

### Health Checks

```bash
# Run comprehensive health check
./scripts/health-monitor.sh check

# Continuous monitoring
./scripts/health-monitor.sh monitor

# Generate health report
./scripts/health-monitor.sh report
```

### Log Analysis

```bash
# Application logs
kubectl logs -f deployment/backend -n idf-testing

# Database logs
kubectl logs -f statefulset/postgres-primary -n idf-testing

# Nginx logs
kubectl logs -f deployment/nginx -n idf-testing

# System events
kubectl get events -n idf-testing --sort-by='.lastTimestamp'
```

## Security Considerations

### Network Security

- All traffic encrypted with TLS 1.2+
- Network policies isolate namespaces
- Ingress controller with rate limiting
- WAF protection (if available)

### Authentication and Authorization

- RBAC with least privilege principle
- Service accounts for pod-to-pod communication
- JWT tokens with short expiration
- Multi-factor authentication (if configured)

### Data Protection

- Database encryption at rest and in transit
- Encrypted backups with key rotation
- Secrets management with Kubernetes secrets
- PII data handling compliance

### Compliance

- CIS Kubernetes Benchmark compliance
- Regular vulnerability scanning
- Security audit logging
- Incident response procedures

## Maintenance

### Regular Tasks

#### Daily
- Monitor health dashboards
- Review security alerts
- Check backup status

#### Weekly
- Update container images
- Review performance metrics
- Analyze error logs

#### Monthly
- Security compliance scan
- Backup restore testing
- Capacity planning review

### Updates

#### Security Updates

```bash
# Update base images
docker pull postgres:15-alpine
docker pull redis:7-alpine

# Rebuild and deploy
./scripts/deployment-manager.sh upgrade latest
```

#### Application Updates

```bash
# Deploy new version
./scripts/deployment-manager.sh upgrade v1.2.0

# Verify deployment
./scripts/deployment-manager.sh test
```

## Support and Contact

For support and questions:
- Technical Lead: [technical-lead@idf.mil.il]
- DevOps Team: [devops@idf.mil.il]
- Security Team: [security@idf.mil.il]

Emergency contact: [emergency-contact]

## Appendix

### Resource Requirements

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit | Storage |
|-----------|-------------|-----------|----------------|--------------|---------|
| Backend | 1000m | 2000m | 2Gi | 4Gi | - |
| Frontend | 250m | 500m | 512Mi | 1Gi | - |
| PostgreSQL | 2000m | 4000m | 4Gi | 8Gi | 100Gi |
| Redis | 500m | 1000m | 1Gi | 2Gi | 10Gi |
| Monitoring | 1000m | 2000m | 2Gi | 4Gi | 50Gi |

### Network Ports

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| Nginx | 80, 443 | TCP | HTTP/HTTPS ingress |
| Backend | 8000 | TCP | Application API |
| Backend Metrics | 8001 | TCP | Prometheus metrics |
| PostgreSQL | 5432 | TCP | Database connections |
| Redis | 7000-7002 | TCP | Cache cluster |
| Prometheus | 9090 | TCP | Metrics collection |
| Grafana | 3000 | TCP | Dashboard UI |

### Backup Schedule

| Type | Frequency | Retention | Encryption |
|------|-----------|-----------|------------|
| Full Database | Weekly | 12 weeks | AES-256 |
| Incremental | 6 hours | 1 week | AES-256 |
| Configuration | Daily | 30 days | AES-256 |
| Logs | Daily | 7 days | AES-256 |