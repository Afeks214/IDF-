#!/bin/bash
# IDF Testing Infrastructure - Comprehensive Health Monitoring
# Military-grade health checks and service monitoring

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/idf-health.log"
NAMESPACE="idf-testing"
HEALTH_CHECK_INTERVAL=30
MAX_RETRIES=3
TIMEOUT=10

# Health check endpoints
BACKEND_HEALTH_URL="http://backend-service.${NAMESPACE}.svc.cluster.local:8000/health"
API_HEALTH_URL="https://api.idf-testing.mil.il/health"
FRONTEND_URL="https://idf-testing.mil.il"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Health status tracking
declare -A service_status
declare -A service_last_check
declare -A service_failure_count

# Initialize Prometheus metrics
init_metrics() {
    # Create metrics directory if it doesn't exist
    mkdir -p /tmp/metrics
    
    cat > /tmp/metrics/health_metrics.prom <<EOF
# HELP idf_service_health Service health status (1=healthy, 0=unhealthy)
# TYPE idf_service_health gauge
# HELP idf_service_response_time Service response time in seconds
# TYPE idf_service_response_time gauge
# HELP idf_service_check_total Total number of health checks performed
# TYPE idf_service_check_total counter
# HELP idf_service_failure_total Total number of health check failures
# TYPE idf_service_failure_total counter
EOF
}

# Update Prometheus metrics
update_metrics() {
    local service="$1"
    local status="$2"
    local response_time="$3"
    
    local timestamp=$(date +%s)
    
    # Update metrics file
    {
        echo "idf_service_health{service=\"$service\",namespace=\"$NAMESPACE\"} $status $timestamp"
        echo "idf_service_response_time{service=\"$service\",namespace=\"$NAMESPACE\"} $response_time $timestamp"
        echo "idf_service_check_total{service=\"$service\",namespace=\"$NAMESPACE\"} 1 $timestamp"
        if [ "$status" -eq 0 ]; then
            echo "idf_service_failure_total{service=\"$service\",namespace=\"$NAMESPACE\"} 1 $timestamp"
        fi
    } >> /tmp/metrics/health_metrics.prom
}

# Send alert function
send_alert() {
    local service="$1"
    local status="$2"
    local message="$3"
    
    log "${RED}ALERT: $service - $message${NC}"
    
    # Send to Alertmanager
    if command -v curl >/dev/null 2>&1; then
        curl -XPOST http://alertmanager:9093/api/v1/alerts -H 'Content-Type: application/json' -d "[
            {
                \"labels\": {
                    \"alertname\": \"ServiceHealthCheck\",
                    \"service\": \"$service\",
                    \"severity\": \"$status\",
                    \"namespace\": \"$NAMESPACE\"
                },
                \"annotations\": {
                    \"summary\": \"$message\",
                    \"description\": \"Health check failed for service $service\"
                },
                \"startsAt\": \"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)\"
            }
        ]" 2>/dev/null || log "WARNING: Failed to send alert to Alertmanager"
    fi
    
    # Send to Slack webhook if configured
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        local emoji="🔴"
        if [ "$status" == "warning" ]; then
            emoji="🟡"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$emoji Health Alert: $service - $message\"}" \
            "$SLACK_WEBHOOK_URL" 2>/dev/null || log "WARNING: Failed to send Slack alert"
    fi
}

# Check HTTP endpoint health
check_http_health() {
    local service="$1"
    local url="$2"
    local expected_status="${3:-200}"
    
    log "${BLUE}Checking $service health at $url${NC}"
    
    local start_time=$(date +%s.%N)
    local status_code response_time exit_code
    
    # Perform HTTP check with timeout
    if response=$(timeout "$TIMEOUT" curl -s -w "%{http_code}" -o /dev/null "$url" 2>/dev/null); then
        status_code="$response"
        exit_code=0
    else
        status_code="000"
        exit_code=1
    fi
    
    local end_time=$(date +%s.%N)
    response_time=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")
    
    # Evaluate health status
    if [ "$exit_code" -eq 0 ] && [ "$status_code" -eq "$expected_status" ]; then
        service_status["$service"]="healthy"
        service_failure_count["$service"]=0
        update_metrics "$service" 1 "$response_time"
        log "${GREEN}✓ $service is healthy (${status_code}, ${response_time}s)${NC}"
        return 0
    else
        service_status["$service"]="unhealthy"
        service_failure_count["$service"]=$((${service_failure_count["$service"]:-0} + 1))
        update_metrics "$service" 0 "$response_time"
        log "${RED}✗ $service is unhealthy (${status_code}, ${response_time}s)${NC}"
        
        # Send alert if failure count exceeds threshold
        if [ "${service_failure_count["$service"]}" -ge "$MAX_RETRIES" ]; then
            send_alert "$service" "critical" "Service is unhealthy after $MAX_RETRIES attempts"
        fi
        return 1
    fi
}

# Check Kubernetes pod health
check_pod_health() {
    local deployment="$1"
    
    log "${BLUE}Checking $deployment pods health${NC}"
    
    # Get pod status
    local ready_pods=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    local desired_pods=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
    
    if [ "$ready_pods" -eq "$desired_pods" ] && [ "$ready_pods" -gt 0 ]; then
        service_status["$deployment-pods"]="healthy"
        update_metrics "$deployment-pods" 1 0
        log "${GREEN}✓ $deployment pods are healthy ($ready_pods/$desired_pods ready)${NC}"
        return 0
    else
        service_status["$deployment-pods"]="unhealthy"
        update_metrics "$deployment-pods" 0 0
        log "${RED}✗ $deployment pods are unhealthy ($ready_pods/$desired_pods ready)${NC}"
        
        # Get pod details for troubleshooting
        kubectl get pods -n "$NAMESPACE" -l app="$deployment" --no-headers | while read -r line; do
            local pod_name=$(echo "$line" | awk '{print $1}')
            local pod_status=$(echo "$line" | awk '{print $3}')
            if [ "$pod_status" != "Running" ]; then
                log "${YELLOW}  Pod $pod_name status: $pod_status${NC}"
            fi
        done
        
        send_alert "$deployment-pods" "critical" "Pod health check failed ($ready_pods/$desired_pods ready)"
        return 1
    fi
}

# Check database connectivity
check_database_health() {
    log "${BLUE}Checking database connectivity${NC}"
    
    local start_time=$(date +%s.%N)
    
    # Check PostgreSQL primary
    if kubectl exec -n "$NAMESPACE" deployment/backend -- pg_isready -h postgres-primary -U idf_user -d idf_testing >/dev/null 2>&1; then
        local end_time=$(date +%s.%N)
        local response_time=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")
        
        service_status["database-primary"]="healthy"
        update_metrics "database-primary" 1 "$response_time"
        log "${GREEN}✓ Database primary is healthy (${response_time}s)${NC}"
    else
        service_status["database-primary"]="unhealthy"
        update_metrics "database-primary" 0 0
        log "${RED}✗ Database primary is unhealthy${NC}"
        send_alert "database-primary" "critical" "Primary database connection failed"
    fi
    
    # Check database connections
    local active_connections=$(kubectl exec -n "$NAMESPACE" deployment/backend -- psql -h postgres-primary -U idf_user -d idf_testing -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | tr -d ' ' || echo "0")
    local max_connections=$(kubectl exec -n "$NAMESPACE" deployment/backend -- psql -h postgres-primary -U idf_user -d idf_testing -t -c "SHOW max_connections;" 2>/dev/null | tr -d ' ' || echo "100")
    
    local connection_usage=$((active_connections * 100 / max_connections))
    
    if [ "$connection_usage" -lt 80 ]; then
        log "${GREEN}✓ Database connections usage: $connection_usage% ($active_connections/$max_connections)${NC}"
    elif [ "$connection_usage" -lt 90 ]; then
        log "${YELLOW}⚠ Database connections usage high: $connection_usage% ($active_connections/$max_connections)${NC}"
        send_alert "database-connections" "warning" "High database connection usage: $connection_usage%"
    else
        log "${RED}✗ Database connections usage critical: $connection_usage% ($active_connections/$max_connections)${NC}"
        send_alert "database-connections" "critical" "Critical database connection usage: $connection_usage%"
    fi
}

# Check Redis connectivity
check_redis_health() {
    log "${BLUE}Checking Redis connectivity${NC}"
    
    local start_time=$(date +%s.%N)
    
    if kubectl exec -n "$NAMESPACE" deployment/backend -- redis-cli -h redis-node-1 -p 7000 ping >/dev/null 2>&1; then
        local end_time=$(date +%s.%N)
        local response_time=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")
        
        service_status["redis"]="healthy"
        update_metrics "redis" 1 "$response_time"
        log "${GREEN}✓ Redis is healthy (${response_time}s)${NC}"
    else
        service_status["redis"]="unhealthy"
        update_metrics "redis" 0 0
        log "${RED}✗ Redis is unhealthy${NC}"
        send_alert "redis" "critical" "Redis connection failed"
    fi
}

# Check application-specific metrics
check_application_metrics() {
    log "${BLUE}Checking application-specific metrics${NC}"
    
    # Check if backend metrics endpoint is available
    if curl -s "http://backend-service.${NAMESPACE}.svc.cluster.local:8001/metrics" >/dev/null; then
        # Get application metrics
        local http_requests=$(curl -s "http://backend-service.${NAMESPACE}.svc.cluster.local:8001/metrics" | grep "http_requests_total" | tail -1 | awk '{print $2}' || echo "0")
        local error_rate=$(curl -s "http://backend-service.${NAMESPACE}.svc.cluster.local:8001/metrics" | grep "http_requests_total.*5.." | awk '{sum+=$2} END {print sum+0}' || echo "0")
        
        if [ "$http_requests" -gt 0 ]; then
            local error_percentage=$((error_rate * 100 / http_requests))
            if [ "$error_percentage" -lt 5 ]; then
                log "${GREEN}✓ Application error rate: $error_percentage%${NC}"
            elif [ "$error_percentage" -lt 10 ]; then
                log "${YELLOW}⚠ Application error rate elevated: $error_percentage%${NC}"
                send_alert "application-errors" "warning" "Elevated error rate: $error_percentage%"
            else
                log "${RED}✗ Application error rate critical: $error_percentage%${NC}"
                send_alert "application-errors" "critical" "High error rate: $error_percentage%"
            fi
        fi
        
        log "${GREEN}✓ Application metrics available${NC}"
    else
        log "${YELLOW}⚠ Application metrics endpoint unavailable${NC}"
    fi
}

# Check storage health
check_storage_health() {
    log "${BLUE}Checking storage health${NC}"
    
    # Check PVC status
    local pvcs=$(kubectl get pvc -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    local bound_pvcs=$(kubectl get pvc -n "$NAMESPACE" --no-headers 2>/dev/null | grep -c "Bound" || echo "0")
    
    if [ "$pvcs" -eq "$bound_pvcs" ] && [ "$pvcs" -gt 0 ]; then
        log "${GREEN}✓ All PVCs are bound ($bound_pvcs/$pvcs)${NC}"
    else
        log "${RED}✗ PVC binding issues ($bound_pvcs/$pvcs bound)${NC}"
        send_alert "storage" "critical" "PVC binding issues detected"
    fi
    
    # Check disk usage for mounted volumes
    kubectl get pods -n "$NAMESPACE" -o name | while read -r pod; do
        local pod_name=$(basename "$pod")
        local disk_usage=$(kubectl exec -n "$NAMESPACE" "$pod_name" -- df /app 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//' || echo "0")
        
        if [ "$disk_usage" -lt 80 ]; then
            log "${GREEN}✓ $pod_name disk usage: $disk_usage%${NC}"
        elif [ "$disk_usage" -lt 90 ]; then
            log "${YELLOW}⚠ $pod_name disk usage high: $disk_usage%${NC}"
            send_alert "disk-usage" "warning" "High disk usage on $pod_name: $disk_usage%"
        else
            log "${RED}✗ $pod_name disk usage critical: $disk_usage%${NC}"
            send_alert "disk-usage" "critical" "Critical disk usage on $pod_name: $disk_usage%"
        fi
    done 2>/dev/null || true
}

# Generate health report
generate_health_report() {
    local report_file="/tmp/health-report-$(date +%Y%m%d-%H%M%S).json"
    
    log "${BLUE}Generating health report${NC}"
    
    cat > "$report_file" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)",
    "namespace": "$NAMESPACE",
    "overall_status": "$([ ${#service_status[@]} -eq $(printf '%s\n' "${service_status[@]}" | grep -c "healthy") ] && echo "healthy" || echo "unhealthy")",
    "services": {
EOF

    local first=true
    for service in "${!service_status[@]}"; do
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> "$report_file"
        fi
        echo "        \"$service\": {" >> "$report_file"
        echo "            \"status\": \"${service_status[$service]}\"," >> "$report_file"
        echo "            \"last_check\": \"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)\"," >> "$report_file"
        echo "            \"failure_count\": ${service_failure_count[$service]:-0}" >> "$report_file"
        echo -n "        }" >> "$report_file"
    done

    cat >> "$report_file" <<EOF

    },
    "summary": {
        "total_services": ${#service_status[@]},
        "healthy_services": $(printf '%s\n' "${service_status[@]}" | grep -c "healthy"),
        "unhealthy_services": $(printf '%s\n' "${service_status[@]}" | grep -c "unhealthy")
    }
}
EOF

    log "${GREEN}Health report generated: $report_file${NC}"
    
    # Send report to monitoring system
    if command -v curl >/dev/null 2>&1 && [ -n "${HEALTH_REPORT_WEBHOOK:-}" ]; then
        curl -X POST -H 'Content-Type: application/json' \
            --data @"$report_file" \
            "$HEALTH_REPORT_WEBHOOK" || log "WARNING: Failed to send health report"
    fi
}

# Continuous monitoring loop
monitor_continuously() {
    log "${GREEN}Starting continuous health monitoring (interval: ${HEALTH_CHECK_INTERVAL}s)${NC}"
    
    while true; do
        log "${BLUE}=== Health Check Cycle Started ===${NC}"
        
        # Run all health checks
        check_pod_health "backend"
        check_pod_health "frontend" || true  # Frontend might not be deployed yet
        check_http_health "backend-internal" "$BACKEND_HEALTH_URL"
        check_http_health "api-external" "$API_HEALTH_URL" || true  # External might not be accessible
        check_http_health "frontend-external" "$FRONTEND_URL" || true
        check_database_health
        check_redis_health
        check_application_metrics
        check_storage_health
        
        # Generate report
        generate_health_report
        
        log "${BLUE}=== Health Check Cycle Completed ===${NC}"
        
        # Wait for next check
        sleep "$HEALTH_CHECK_INTERVAL"
    done
}

# Main function
main() {
    case "${1:-monitor}" in
        "check")
            init_metrics
            check_pod_health "backend"
            check_http_health "backend" "$BACKEND_HEALTH_URL"
            check_database_health
            check_redis_health
            generate_health_report
            ;;
        "monitor")
            init_metrics
            monitor_continuously
            ;;
        "report")
            generate_health_report
            ;;
        *)
            echo "Usage: $0 {check|monitor|report}"
            echo "  check   - Run health checks once"
            echo "  monitor - Run continuous monitoring"
            echo "  report  - Generate health report"
            exit 1
            ;;
    esac
}

# Check dependencies
command -v kubectl >/dev/null 2>&1 || { log "${RED}ERROR: kubectl is required but not installed${NC}"; exit 1; }
command -v curl >/dev/null 2>&1 || { log "${YELLOW}WARNING: curl not found, some checks will be limited${NC}"; }
command -v bc >/dev/null 2>&1 || { log "${YELLOW}WARNING: bc not found, response time calculations will be limited${NC}"; }

# Run with provided arguments
main "$@"