#!/bin/bash
# IDF Testing Infrastructure - Production Deployment Manager
# Military-grade deployment automation and management

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/idf-deployment.log"
NAMESPACE="idf-testing"
REGISTRY="ghcr.io/idf-testing"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "${RED}ERROR: $1${NC}"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log "${BLUE}Checking deployment prerequisites...${NC}"
    
    # Check required tools
    local tools=("kubectl" "docker" "helm" "aws" "jq" "curl")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            error_exit "$tool is required but not installed"
        fi
    done
    
    # Check Kubernetes connectivity
    if ! kubectl cluster-info >/dev/null 2>&1; then
        error_exit "Cannot connect to Kubernetes cluster"
    fi
    
    # Check Docker registry access
    if ! docker info >/dev/null 2>&1; then
        error_exit "Cannot connect to Docker daemon"
    fi
    
    # Verify namespace exists
    if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
        log "${YELLOW}Creating namespace $NAMESPACE${NC}"
        kubectl create namespace "$NAMESPACE"
    fi
    
    log "${GREEN}✓ Prerequisites check passed${NC}"
}

# Validate configuration
validate_configuration() {
    log "${BLUE}Validating deployment configuration...${NC}"
    
    # Check environment file
    if [ ! -f "$PROJECT_ROOT/config/production.env" ]; then
        if [ -f "$PROJECT_ROOT/config/production.env.template" ]; then
            log "${YELLOW}Creating production.env from template${NC}"
            cp "$PROJECT_ROOT/config/production.env.template" "$PROJECT_ROOT/config/production.env"
            log "${RED}WARNING: Please update production.env with actual values before deployment!${NC}"
            return 1
        else
            error_exit "production.env file not found"
        fi
    fi
    
    # Check for placeholder values
    if grep -q "CHANGE_ME" "$PROJECT_ROOT/config/production.env"; then
        log "${RED}ERROR: Found placeholder values in production.env${NC}"
        grep "CHANGE_ME" "$PROJECT_ROOT/config/production.env"
        error_exit "Please update all CHANGE_ME values in production.env"
    fi
    
    # Validate Kubernetes manifests
    find "$PROJECT_ROOT/k8s" -name "*.yaml" -exec kubectl --dry-run=client apply -f {} \; >/dev/null 2>&1 || {
        error_exit "Kubernetes manifest validation failed"
    }
    
    log "${GREEN}✓ Configuration validation passed${NC}"
}

# Create secrets from environment file
create_secrets() {
    log "${BLUE}Creating Kubernetes secrets...${NC}"
    
    # Source environment variables
    set -a
    source "$PROJECT_ROOT/config/production.env"
    set +a
    
    # Create PostgreSQL secrets
    kubectl create secret generic postgres-secret \
        --from-literal=postgres-password="$POSTGRES_PASSWORD" \
        --from-literal=replication-password="$POSTGRES_REPLICATION_PASSWORD" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Create backend secrets
    kubectl create secret generic backend-secret \
        --from-literal=secret-key="$SECRET_KEY" \
        --from-literal=database-url="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB" \
        --from-literal=redis-url="redis://:$REDIS_PASSWORD@$REDIS_NODE_1_HOST:$REDIS_NODE_1_PORT" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Create monitoring secrets
    kubectl create secret generic grafana-secret \
        --from-literal=admin-password="$(openssl rand -base64 32)" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Create backup encryption key
    kubectl create secret generic backup-encryption-key \
        --from-literal=backup.key="$(openssl rand -base64 32)" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Create TLS certificates (if not using cert-manager)
    if [ -f "$PROJECT_ROOT/certs/tls.crt" ] && [ -f "$PROJECT_ROOT/certs/tls.key" ]; then
        kubectl create secret tls idf-testing-tls \
            --cert="$PROJECT_ROOT/certs/tls.crt" \
            --key="$PROJECT_ROOT/certs/tls.key" \
            --namespace="$NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
    fi
    
    log "${GREEN}✓ Secrets created successfully${NC}"
}

# Build and push container images
build_images() {
    log "${BLUE}Building and pushing container images...${NC}"
    
    local tag="${1:-latest}"
    
    # Build backend image
    log "Building backend image..."
    docker build -t "$REGISTRY/backend:$tag" "$PROJECT_ROOT/backend" --target production
    docker push "$REGISTRY/backend:$tag"
    
    # Build frontend image (if exists)
    if [ -d "$PROJECT_ROOT/frontend" ]; then
        log "Building frontend image..."
        docker build -t "$REGISTRY/frontend:$tag" "$PROJECT_ROOT/frontend" --target production
        docker push "$REGISTRY/frontend:$tag"
    fi
    
    # Build nginx image
    log "Building nginx image..."
    docker build -t "$REGISTRY/nginx:$tag" "$PROJECT_ROOT/nginx"
    docker push "$REGISTRY/nginx:$tag"
    
    log "${GREEN}✓ Images built and pushed successfully${NC}"
}

# Deploy infrastructure components
deploy_infrastructure() {
    log "${BLUE}Deploying infrastructure components...${NC}"
    
    # Deploy namespace and RBAC
    kubectl apply -f "$PROJECT_ROOT/k8s/namespace.yaml"
    
    # Deploy storage classes and PVCs
    kubectl apply -f "$PROJECT_ROOT/k8s/storage/"* 2>/dev/null || true
    
    # Deploy PostgreSQL cluster
    kubectl apply -f "$PROJECT_ROOT/k8s/postgres-cluster.yaml"
    
    # Wait for PostgreSQL to be ready
    log "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres-primary -n "$NAMESPACE" --timeout=600s
    
    # Deploy Redis cluster
    kubectl apply -f "$PROJECT_ROOT/k8s/redis-cluster.yaml" 2>/dev/null || true
    
    # Deploy monitoring stack
    kubectl apply -f "$PROJECT_ROOT/k8s/monitoring-stack.yaml"
    
    log "${GREEN}✓ Infrastructure components deployed${NC}"
}

# Deploy application services
deploy_application() {
    log "${BLUE}Deploying application services...${NC}"
    
    local tag="${1:-latest}"
    
    # Update image tags in deployment manifests
    sed -i "s|image: .*/backend:.*|image: $REGISTRY/backend:$tag|g" "$PROJECT_ROOT/k8s/backend-deployment.yaml"
    sed -i "s|image: .*/frontend:.*|image: $REGISTRY/frontend:$tag|g" "$PROJECT_ROOT/k8s/frontend-deployment.yaml" 2>/dev/null || true
    
    # Deploy backend
    kubectl apply -f "$PROJECT_ROOT/k8s/backend-deployment.yaml"
    
    # Deploy frontend (if exists)
    if [ -f "$PROJECT_ROOT/k8s/frontend-deployment.yaml" ]; then
        kubectl apply -f "$PROJECT_ROOT/k8s/frontend-deployment.yaml"
    fi
    
    # Deploy ingress and load balancer
    kubectl apply -f "$PROJECT_ROOT/k8s/ingress.yaml"
    
    # Wait for deployments to be ready
    log "Waiting for backend deployment to be ready..."
    kubectl rollout status deployment/backend -n "$NAMESPACE" --timeout=600s
    
    if kubectl get deployment frontend -n "$NAMESPACE" >/dev/null 2>&1; then
        log "Waiting for frontend deployment to be ready..."
        kubectl rollout status deployment/frontend -n "$NAMESPACE" --timeout=600s
    fi
    
    log "${GREEN}✓ Application services deployed${NC}"
}

# Deploy backup and monitoring
deploy_observability() {
    log "${BLUE}Deploying observability and backup systems...${NC}"
    
    # Deploy backup CronJobs
    kubectl apply -f "$PROJECT_ROOT/k8s/backup-cronjob.yaml"
    
    # Deploy service monitors for Prometheus
    kubectl apply -f "$PROJECT_ROOT/k8s/service-monitors/" 2>/dev/null || true
    
    # Create Prometheus configuration
    kubectl create configmap prometheus-config \
        --from-file="$PROJECT_ROOT/monitoring/prometheus.yml" \
        --from-file="$PROJECT_ROOT/monitoring/alert-rules.yml" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Create Grafana dashboards
    if [ -d "$PROJECT_ROOT/monitoring/grafana/dashboards" ]; then
        kubectl create configmap grafana-dashboards \
            --from-file="$PROJECT_ROOT/monitoring/grafana/dashboards/" \
            --namespace="$NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
    fi
    
    log "${GREEN}✓ Observability and backup systems deployed${NC}"
}

# Run post-deployment tests
run_post_deployment_tests() {
    log "${BLUE}Running post-deployment tests...${NC}"
    
    # Wait for services to be fully ready
    sleep 30
    
    # Test backend health
    local backend_ip=$(kubectl get service backend-service -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}')
    kubectl run --rm -i --tty test-backend \
        --image=curlimages/curl:latest \
        --restart=Never \
        --namespace="$NAMESPACE" \
        -- curl -f "http://$backend_ip:8000/health" || error_exit "Backend health check failed"
    
    # Test database connectivity
    kubectl exec deployment/backend -n "$NAMESPACE" -- \
        pg_isready -h postgres-primary -U idf_user -d idf_testing || error_exit "Database connectivity test failed"
    
    # Test Redis connectivity
    kubectl exec deployment/backend -n "$NAMESPACE" -- \
        redis-cli -h redis-node-1 -p 7000 ping || error_exit "Redis connectivity test failed"
    
    # Test monitoring endpoints
    local prometheus_ip=$(kubectl get service prometheus -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}')
    kubectl run --rm -i --tty test-prometheus \
        --image=curlimages/curl:latest \
        --restart=Never \
        --namespace="$NAMESPACE" \
        -- curl -f "http://$prometheus_ip:9090/-/healthy" || log "${YELLOW}WARNING: Prometheus health check failed${NC}"
    
    log "${GREEN}✓ Post-deployment tests completed${NC}"
}

# Setup monitoring and alerting
setup_monitoring() {
    log "${BLUE}Setting up monitoring and alerting...${NC}"
    
    # Install Prometheus Operator (if not already installed)
    if ! kubectl get crd prometheuses.monitoring.coreos.com >/dev/null 2>&1; then
        log "Installing Prometheus Operator..."
        kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml
    fi
    
    # Install cert-manager (if not already installed)
    if ! kubectl get namespace cert-manager >/dev/null 2>&1; then
        log "Installing cert-manager..."
        kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
    fi
    
    # Install ingress-nginx (if not already installed)
    if ! kubectl get namespace ingress-nginx >/dev/null 2>&1; then
        log "Installing ingress-nginx..."
        kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
    fi
    
    log "${GREEN}✓ Monitoring and alerting setup completed${NC}"
}

# Rollback deployment
rollback_deployment() {
    local revision="${1:-1}"
    
    log "${YELLOW}Rolling back deployment to revision $revision...${NC}"
    
    # Rollback backend deployment
    kubectl rollout undo deployment/backend --to-revision="$revision" -n "$NAMESPACE"
    kubectl rollout status deployment/backend -n "$NAMESPACE" --timeout=600s
    
    # Rollback frontend deployment (if exists)
    if kubectl get deployment frontend -n "$NAMESPACE" >/dev/null 2>&1; then
        kubectl rollout undo deployment/frontend --to-revision="$revision" -n "$NAMESPACE"
        kubectl rollout status deployment/frontend -n "$NAMESPACE" --timeout=600s
    fi
    
    log "${GREEN}✓ Rollback completed${NC}"
}

# Clean up deployment
cleanup_deployment() {
    log "${YELLOW}Cleaning up deployment...${NC}"
    
    # Delete application resources
    kubectl delete -f "$PROJECT_ROOT/k8s/" --recursive --ignore-not-found=true
    
    # Delete secrets (optional)
    read -p "Delete secrets and persistent data? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
        log "${GREEN}✓ Complete cleanup completed${NC}"
    else
        log "${GREEN}✓ Application cleanup completed (secrets and data preserved)${NC}"
    fi
}

# Get deployment status
get_status() {
    log "${BLUE}Deployment Status for namespace: $NAMESPACE${NC}"
    
    echo -e "\n${PURPLE}=== Deployments ===${NC}"
    kubectl get deployments -n "$NAMESPACE" -o wide
    
    echo -e "\n${PURPLE}=== Services ===${NC}"
    kubectl get services -n "$NAMESPACE" -o wide
    
    echo -e "\n${PURPLE}=== Pods ===${NC}"
    kubectl get pods -n "$NAMESPACE" -o wide
    
    echo -e "\n${PURPLE}=== Ingress ===${NC}"
    kubectl get ingress -n "$NAMESPACE" -o wide
    
    echo -e "\n${PURPLE}=== PVCs ===${NC}"
    kubectl get pvc -n "$NAMESPACE" -o wide
    
    echo -e "\n${PURPLE}=== Recent Events ===${NC}"
    kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -10
}

# Main deployment function
main() {
    case "${1:-help}" in
        "deploy")
            local tag="${2:-latest}"
            check_prerequisites
            validate_configuration
            create_secrets
            build_images "$tag"
            deploy_infrastructure
            deploy_application "$tag"
            deploy_observability
            run_post_deployment_tests
            get_status
            log "${GREEN}🎉 Deployment completed successfully!${NC}"
            ;;
        "upgrade")
            local tag="${2:-latest}"
            check_prerequisites
            build_images "$tag"
            deploy_application "$tag"
            run_post_deployment_tests
            log "${GREEN}🎉 Upgrade completed successfully!${NC}"
            ;;
        "rollback")
            local revision="${2:-1}"
            rollback_deployment "$revision"
            ;;
        "status")
            get_status
            ;;
        "cleanup")
            cleanup_deployment
            ;;
        "setup-monitoring")
            setup_monitoring
            ;;
        "test")
            run_post_deployment_tests
            ;;
        "help"|*)
            echo "IDF Testing Infrastructure - Deployment Manager"
            echo ""
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  deploy [tag]        - Full deployment with specified image tag (default: latest)"
            echo "  upgrade [tag]       - Upgrade application with new image tag"
            echo "  rollback [revision] - Rollback to previous revision (default: 1)"
            echo "  status              - Show deployment status"
            echo "  cleanup             - Clean up deployment resources"
            echo "  setup-monitoring    - Install monitoring components"
            echo "  test                - Run post-deployment tests"
            echo "  help                - Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 deploy v1.2.3"
            echo "  $0 upgrade latest"
            echo "  $0 rollback 2"
            echo "  $0 status"
            ;;
    esac
}

# Run with provided arguments
main "$@"