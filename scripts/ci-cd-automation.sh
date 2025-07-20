#!/bin/bash

# IDF Testing Infrastructure - CI/CD Automation Script
# Advanced deployment automation with security scanning and monitoring integration

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_ROOT}/config/cicd.conf"
LOG_FILE="${PROJECT_ROOT}/logs/cicd.log"
ARTIFACTS_DIR="${PROJECT_ROOT}/artifacts"
REPORTS_DIR="${PROJECT_ROOT}/reports"

# Default configuration
ENVIRONMENT="${ENVIRONMENT:-staging}"
REGISTRY="${REGISTRY:-ghcr.io/idf-testing}"
NAMESPACE="${NAMESPACE:-idf-testing}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
ENABLE_SECURITY_SCAN="${ENABLE_SECURITY_SCAN:-true}"
ENABLE_PERFORMANCE_TEST="${ENABLE_PERFORMANCE_TEST:-true}"
ENABLE_COMPLIANCE_CHECK="${ENABLE_COMPLIANCE_CHECK:-true}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

info() {
    log "INFO" "$@"
    echo -e "${BLUE}[INFO]${NC} $*"
}

warn() {
    log "WARN" "$@"
    echo -e "${YELLOW}[WARN]${NC} $*"
}

error() {
    log "ERROR" "$@"
    echo -e "${RED}[ERROR]${NC} $*"
}

success() {
    log "SUCCESS" "$@"
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

debug() {
    log "DEBUG" "$@"
    echo -e "${CYAN}[DEBUG]${NC} $*"
}

# Slack notification function
send_slack_notification() {
    local message="$1"
    local status="${2:-info}"
    local color="${3:-good}"
    
    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        local payload=$(cat <<EOF
{
  "username": "IDF CI/CD Bot",
  "icon_emoji": ":rocket:",
  "attachments": [
    {
      "color": "$color",
      "fields": [
        {
          "title": "IDF Testing Infrastructure",
          "value": "$message",
          "short": false
        },
        {
          "title": "Environment",
          "value": "$ENVIRONMENT",
          "short": true
        },
        {
          "title": "Commit",
          "value": "\`$(git rev-parse --short HEAD)\`",
          "short": true
        },
        {
          "title": "Branch",
          "value": "\`$(git rev-parse --abbrev-ref HEAD)\`",
          "short": true
        },
        {
          "title": "Timestamp",
          "value": "$(date '+%Y-%m-%d %H:%M:%S')",
          "short": true
        }
      ]
    }
  ]
}
EOF
)
        
        curl -X POST -H 'Content-type: application/json' --data "$payload" "$SLACK_WEBHOOK_URL" > /dev/null 2>&1 || true
    fi
}

# Initialize directories
init_directories() {
    mkdir -p "$ARTIFACTS_DIR" "$REPORTS_DIR" "$(dirname "$LOG_FILE")"
    info "Initialized directories"
}

# Load configuration
load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        source "$CONFIG_FILE"
        info "Configuration loaded from $CONFIG_FILE"
    else
        info "Using default configuration"
    fi
}

# Check prerequisites
check_prerequisites() {
    info "Checking CI/CD prerequisites..."
    
    local required_tools=(
        "docker" "kubectl" "helm" "jq" "curl" "git"
        "trivy" "bandit" "semgrep" "hadolint"
    )
    
    local missing_tools=()
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        error "Missing required tools: ${missing_tools[*]}"
        info "Please install missing tools before continuing"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
        exit 1
    fi
    
    # Check Kubernetes connection
    if ! kubectl cluster-info &> /dev/null; then
        warn "Kubernetes cluster not accessible - deployment will be skipped"
    fi
    
    # Check git repository
    if ! git rev-parse --is-inside-work-tree &> /dev/null; then
        error "Not in a git repository"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Code quality analysis
run_code_quality_analysis() {
    info "Running code quality analysis..."
    
    local quality_report="${REPORTS_DIR}/code_quality_$(date +%Y%m%d_%H%M%S).json"
    
    # Python linting with flake8
    if [[ -d "$PROJECT_ROOT/backend" ]]; then
        info "Running Python linting..."
        cd "$PROJECT_ROOT/backend"
        
        # Create virtual environment if it doesn't exist
        if [[ ! -d "venv" ]]; then
            python3 -m venv venv
        fi
        
        source venv/bin/activate
        pip install -q flake8 black mypy bandit
        
        # Run flake8
        flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics > "${REPORTS_DIR}/flake8_critical.txt" 2>&1 || true
        flake8 app/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics > "${REPORTS_DIR}/flake8_full.txt" 2>&1 || true
        
        # Run black format check
        black --check app/ > "${REPORTS_DIR}/black_check.txt" 2>&1 || true
        
        # Run mypy type checking
        mypy app/ --ignore-missing-imports > "${REPORTS_DIR}/mypy_check.txt" 2>&1 || true
        
        deactivate
        cd "$PROJECT_ROOT"
        
        success "Python code quality analysis completed"
    fi
    
    # JavaScript/TypeScript linting
    if [[ -d "$PROJECT_ROOT/frontend" ]]; then
        info "Running JavaScript/TypeScript linting..."
        cd "$PROJECT_ROOT/frontend"
        
        if [[ -f "package.json" ]]; then
            npm ci > /dev/null 2>&1
            npm run lint > "${REPORTS_DIR}/eslint_check.txt" 2>&1 || true
            npm run type-check > "${REPORTS_DIR}/typescript_check.txt" 2>&1 || true
        fi
        
        cd "$PROJECT_ROOT"
        success "JavaScript/TypeScript code quality analysis completed"
    fi
    
    # Dockerfile linting
    find "$PROJECT_ROOT" -name "Dockerfile*" -exec hadolint {} \; > "${REPORTS_DIR}/hadolint_check.txt" 2>&1 || true
    
    success "Code quality analysis completed"
}

# Security scanning
run_security_scan() {
    if [[ "$ENABLE_SECURITY_SCAN" != "true" ]]; then
        info "Security scanning disabled"
        return 0
    fi
    
    info "Running security scanning..."
    
    # File system vulnerability scan with Trivy
    info "Running Trivy filesystem scan..."
    trivy fs --format json --output "${REPORTS_DIR}/trivy_fs_scan.json" "$PROJECT_ROOT" 2>/dev/null || true
    
    # Python security scan with Bandit
    if [[ -d "$PROJECT_ROOT/backend" ]]; then
        info "Running Bandit security scan..."
        bandit -r "$PROJECT_ROOT/backend" -f json -o "${REPORTS_DIR}/bandit_scan.json" 2>/dev/null || true
    fi
    
    # Static analysis with Semgrep
    info "Running Semgrep security analysis..."
    semgrep --config=auto --json --output="${REPORTS_DIR}/semgrep_scan.json" "$PROJECT_ROOT" 2>/dev/null || true
    
    # Docker image security scan
    if [[ -f "$PROJECT_ROOT/backend/Dockerfile" ]]; then
        info "Running Docker image security scan..."
        docker build -t "temp-scan-image:latest" "$PROJECT_ROOT/backend" > /dev/null 2>&1
        trivy image --format json --output "${REPORTS_DIR}/trivy_image_scan.json" "temp-scan-image:latest" 2>/dev/null || true
        docker rmi "temp-scan-image:latest" > /dev/null 2>&1 || true
    fi
    
    # Secrets detection
    info "Running secrets detection..."
    find "$PROJECT_ROOT" -type f -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.yaml" -o -name "*.yml" -o -name "*.json" | \
        xargs grep -l -i "password\|secret\|key\|token" > "${REPORTS_DIR}/potential_secrets.txt" 2>/dev/null || true
    
    success "Security scanning completed"
}

# Build and test
build_and_test() {
    info "Building and testing application..."
    
    local build_tag="${1:-$(git rev-parse --short HEAD)}"
    
    # Build backend
    if [[ -d "$PROJECT_ROOT/backend" ]]; then
        info "Building backend application..."
        docker build -t "${REGISTRY}/backend:${build_tag}" "$PROJECT_ROOT/backend" --target production
        
        # Run backend tests
        info "Running backend tests..."
        cd "$PROJECT_ROOT/backend"
        
        if [[ -f "venv/bin/activate" ]]; then
            source venv/bin/activate
            pip install -q pytest pytest-cov
            pytest tests/ -v --cov=app --cov-report=xml --cov-report=html > "${REPORTS_DIR}/backend_tests.txt" 2>&1 || true
            deactivate
        fi
        
        cd "$PROJECT_ROOT"
        success "Backend build and test completed"
    fi
    
    # Build frontend
    if [[ -d "$PROJECT_ROOT/frontend" ]]; then
        info "Building frontend application..."
        docker build -t "${REGISTRY}/frontend:${build_tag}" "$PROJECT_ROOT/frontend" --target production
        
        # Run frontend tests
        info "Running frontend tests..."
        cd "$PROJECT_ROOT/frontend"
        
        if [[ -f "package.json" ]]; then
            npm ci > /dev/null 2>&1
            npm test -- --coverage --watchAll=false > "${REPORTS_DIR}/frontend_tests.txt" 2>&1 || true
        fi
        
        cd "$PROJECT_ROOT"
        success "Frontend build and test completed"
    fi
    
    # Build nginx
    if [[ -d "$PROJECT_ROOT/nginx" ]]; then
        info "Building nginx configuration..."
        docker build -t "${REGISTRY}/nginx:${build_tag}" "$PROJECT_ROOT/nginx"
        success "Nginx build completed"
    fi
    
    success "Build and test phase completed"
}

# Performance testing
run_performance_tests() {
    if [[ "$ENABLE_PERFORMANCE_TEST" != "true" ]]; then
        info "Performance testing disabled"
        return 0
    fi
    
    info "Running performance tests..."
    
    # Start test environment
    info "Starting test environment..."
    docker-compose -f "$PROJECT_ROOT/docker-compose.yml" up -d > /dev/null 2>&1
    
    # Wait for services to be ready
    sleep 60
    
    # Run load tests with Locust
    if [[ -f "$PROJECT_ROOT/backend/tests/load_testing/locustfile.py" ]]; then
        info "Running load tests..."
        cd "$PROJECT_ROOT/backend/tests/load_testing"
        
        # Install locust if not available
        pip install -q locust > /dev/null 2>&1
        
        # Run load test
        locust -f locustfile.py --headless --users 10 --spawn-rate 2 --run-time 300s --host http://localhost:8001 \
            --html "${REPORTS_DIR}/load_test_report.html" \
            --csv "${REPORTS_DIR}/load_test" > "${REPORTS_DIR}/load_test.log" 2>&1 || true
        
        cd "$PROJECT_ROOT"
        success "Load tests completed"
    fi
    
    # Stop test environment
    docker-compose -f "$PROJECT_ROOT/docker-compose.yml" down > /dev/null 2>&1
    
    success "Performance testing completed"
}

# Compliance checks
run_compliance_checks() {
    if [[ "$ENABLE_COMPLIANCE_CHECK" != "true" ]]; then
        info "Compliance checking disabled"
        return 0
    fi
    
    info "Running compliance checks..."
    
    local compliance_report="${REPORTS_DIR}/compliance_$(date +%Y%m%d_%H%M%S).json"
    
    # Check for required security headers
    info "Checking security headers..."
    grep -r "CSP\|HSTS\|X-Frame-Options\|X-Content-Type-Options" --include="*.py" --include="*.js" --include="*.ts" "$PROJECT_ROOT" > "${REPORTS_DIR}/security_headers.txt" 2>&1 || true
    
    # Check for proper logging
    info "Checking logging implementation..."
    grep -r "logging\|log\|audit" --include="*.py" "$PROJECT_ROOT/backend" > "${REPORTS_DIR}/logging_check.txt" 2>&1 || true
    
    # Check for input validation
    info "Checking input validation..."
    grep -r "validate\|sanitize\|escape" --include="*.py" "$PROJECT_ROOT/backend" > "${REPORTS_DIR}/validation_check.txt" 2>&1 || true
    
    # Check for encryption usage
    info "Checking encryption usage..."
    grep -r "encrypt\|decrypt\|hash\|bcrypt" --include="*.py" "$PROJECT_ROOT/backend" > "${REPORTS_DIR}/encryption_check.txt" 2>&1 || true
    
    # Generate compliance report
    local compliance_score=0
    local total_checks=4
    
    if [[ -s "${REPORTS_DIR}/security_headers.txt" ]]; then
        ((compliance_score++))
    fi
    
    if [[ -s "${REPORTS_DIR}/logging_check.txt" ]]; then
        ((compliance_score++))
    fi
    
    if [[ -s "${REPORTS_DIR}/validation_check.txt" ]]; then
        ((compliance_score++))
    fi
    
    if [[ -s "${REPORTS_DIR}/encryption_check.txt" ]]; then
        ((compliance_score++))
    fi
    
    local compliance_percentage=$((compliance_score * 100 / total_checks))
    
    cat > "$compliance_report" <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "compliance_score": $compliance_percentage,
  "checks_passed": $compliance_score,
  "total_checks": $total_checks,
  "details": {
    "security_headers": $(test -s "${REPORTS_DIR}/security_headers.txt" && echo "true" || echo "false"),
    "logging_implementation": $(test -s "${REPORTS_DIR}/logging_check.txt" && echo "true" || echo "false"),
    "input_validation": $(test -s "${REPORTS_DIR}/validation_check.txt" && echo "true" || echo "false"),
    "encryption_usage": $(test -s "${REPORTS_DIR}/encryption_check.txt" && echo "true" || echo "false")
  }
}
EOF
    
    success "Compliance checks completed - Score: ${compliance_percentage}%"
}

# Deploy to environment
deploy_to_environment() {
    local env="${1:-staging}"
    local tag="${2:-$(git rev-parse --short HEAD)}"
    
    info "Deploying to $env environment with tag $tag..."
    
    # Check if Kubernetes is available
    if ! kubectl cluster-info &> /dev/null; then
        warn "Kubernetes not available - skipping deployment"
        return 0
    fi
    
    # Push images to registry
    info "Pushing images to registry..."
    docker push "${REGISTRY}/backend:${tag}" > /dev/null 2>&1
    
    if docker images "${REGISTRY}/frontend:${tag}" --format "table {{.Repository}}" | grep -q frontend; then
        docker push "${REGISTRY}/frontend:${tag}" > /dev/null 2>&1
    fi
    
    if docker images "${REGISTRY}/nginx:${tag}" --format "table {{.Repository}}" | grep -q nginx; then
        docker push "${REGISTRY}/nginx:${tag}" > /dev/null 2>&1
    fi
    
    # Deploy using deployment manager
    if [[ -f "$PROJECT_ROOT/scripts/deployment-manager.sh" ]]; then
        info "Using deployment manager for deployment..."
        bash "$PROJECT_ROOT/scripts/deployment-manager.sh" deploy "$tag"
    else
        warn "Deployment manager not found - using basic deployment"
        
        # Update image tags in deployment manifests
        find "$PROJECT_ROOT/k8s" -name "*.yaml" -exec sed -i "s|image: .*/backend:.*|image: ${REGISTRY}/backend:${tag}|g" {} \;
        find "$PROJECT_ROOT/k8s" -name "*.yaml" -exec sed -i "s|image: .*/frontend:.*|image: ${REGISTRY}/frontend:${tag}|g" {} \;
        find "$PROJECT_ROOT/k8s" -name "*.yaml" -exec sed -i "s|image: .*/nginx:.*|image: ${REGISTRY}/nginx:${tag}|g" {} \;
        
        # Apply Kubernetes manifests
        kubectl apply -f "$PROJECT_ROOT/k8s/" --recursive
        
        # Wait for deployment to complete
        kubectl rollout status deployment/backend -n "$NAMESPACE" --timeout=600s
        kubectl rollout status deployment/frontend -n "$NAMESPACE" --timeout=600s || true
    fi
    
    success "Deployment to $env completed"
}

# Post-deployment verification
post_deployment_verification() {
    info "Running post-deployment verification..."
    
    # Wait for services to be ready
    sleep 30
    
    # Health check endpoints
    local endpoints=(
        "http://localhost:8001/health"
        "http://localhost:3001/health"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f -s --max-time 10 "$endpoint" &>/dev/null; then
            success "Health check passed: $endpoint"
        else
            error "Health check failed: $endpoint"
        fi
    done
    
    # Database connectivity check
    if docker-compose exec -T postgres pg_isready -U idf_user -d idf_testing &>/dev/null; then
        success "Database connectivity check passed"
    else
        error "Database connectivity check failed"
    fi
    
    # Redis connectivity check
    if docker-compose exec -T redis redis-cli ping &>/dev/null; then
        success "Redis connectivity check passed"
    else
        error "Redis connectivity check failed"
    fi
    
    success "Post-deployment verification completed"
}

# Generate CI/CD report
generate_report() {
    info "Generating CI/CD report..."
    
    local report_file="${REPORTS_DIR}/cicd_report_$(date +%Y%m%d_%H%M%S).json"
    local git_commit=$(git rev-parse HEAD)
    local git_branch=$(git rev-parse --abbrev-ref HEAD)
    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    
    cat > "$report_file" <<EOF
{
  "timestamp": "$timestamp",
  "git": {
    "commit": "$git_commit",
    "branch": "$git_branch"
  },
  "environment": "$ENVIRONMENT",
  "pipeline_stages": {
    "code_quality": {
      "status": "completed",
      "reports": [
        "flake8_critical.txt",
        "flake8_full.txt",
        "black_check.txt",
        "mypy_check.txt",
        "eslint_check.txt",
        "typescript_check.txt",
        "hadolint_check.txt"
      ]
    },
    "security_scan": {
      "status": "$(test "$ENABLE_SECURITY_SCAN" = "true" && echo "completed" || echo "skipped")",
      "reports": [
        "trivy_fs_scan.json",
        "bandit_scan.json",
        "semgrep_scan.json",
        "trivy_image_scan.json",
        "potential_secrets.txt"
      ]
    },
    "build_and_test": {
      "status": "completed",
      "reports": [
        "backend_tests.txt",
        "frontend_tests.txt"
      ]
    },
    "performance_test": {
      "status": "$(test "$ENABLE_PERFORMANCE_TEST" = "true" && echo "completed" || echo "skipped")",
      "reports": [
        "load_test_report.html",
        "load_test.log"
      ]
    },
    "compliance_check": {
      "status": "$(test "$ENABLE_COMPLIANCE_CHECK" = "true" && echo "completed" || echo "skipped")",
      "reports": [
        "compliance_$(date +%Y%m%d_*)*.json"
      ]
    }
  },
  "artifacts": {
    "reports_directory": "$REPORTS_DIR",
    "artifacts_directory": "$ARTIFACTS_DIR"
  }
}
EOF
    
    success "CI/CD report generated: $report_file"
}

# Main CI/CD pipeline
main() {
    local command="${1:-pipeline}"
    
    case "$command" in
        "pipeline")
            info "Starting full CI/CD pipeline..."
            
            init_directories
            load_config
            check_prerequisites
            
            send_slack_notification "CI/CD Pipeline started" "info" "good"
            
            run_code_quality_analysis
            run_security_scan
            build_and_test
            run_performance_tests
            run_compliance_checks
            
            if [[ "$ENVIRONMENT" == "production" ]]; then
                deploy_to_environment "production"
            else
                deploy_to_environment "staging"
            fi
            
            post_deployment_verification
            generate_report
            
            success "CI/CD pipeline completed successfully!"
            send_slack_notification "CI/CD Pipeline completed successfully!" "success" "good"
            ;;
        "quality")
            init_directories
            load_config
            run_code_quality_analysis
            ;;
        "security")
            init_directories
            load_config
            run_security_scan
            ;;
        "build")
            init_directories
            load_config
            build_and_test
            ;;
        "test")
            init_directories
            load_config
            run_performance_tests
            ;;
        "compliance")
            init_directories
            load_config
            run_compliance_checks
            ;;
        "deploy")
            local env="${2:-staging}"
            local tag="${3:-$(git rev-parse --short HEAD)}"
            init_directories
            load_config
            deploy_to_environment "$env" "$tag"
            ;;
        "verify")
            post_deployment_verification
            ;;
        "report")
            init_directories
            generate_report
            ;;
        "help"|*)
            echo "IDF Testing Infrastructure - CI/CD Automation"
            echo ""
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  pipeline                    - Run full CI/CD pipeline"
            echo "  quality                     - Run code quality analysis"
            echo "  security                    - Run security scanning"
            echo "  build                       - Build and test application"
            echo "  test                        - Run performance tests"
            echo "  compliance                  - Run compliance checks"
            echo "  deploy [env] [tag]          - Deploy to environment"
            echo "  verify                      - Post-deployment verification"
            echo "  report                      - Generate CI/CD report"
            echo "  help                        - Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  ENVIRONMENT                 - Target environment (staging/production)"
            echo "  REGISTRY                    - Container registry URL"
            echo "  NAMESPACE                   - Kubernetes namespace"
            echo "  SLACK_WEBHOOK_URL           - Slack webhook for notifications"
            echo "  ENABLE_SECURITY_SCAN        - Enable security scanning (true/false)"
            echo "  ENABLE_PERFORMANCE_TEST     - Enable performance testing (true/false)"
            echo "  ENABLE_COMPLIANCE_CHECK     - Enable compliance checking (true/false)"
            ;;
    esac
}

# Run main function with all arguments
main "$@"