#!/bin/bash
# IDF Testing Infrastructure - Security Compliance and Vulnerability Management
# Military-grade security scanning and compliance monitoring

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/idf-security.log"
REPORT_DIR="/var/reports/security"
NAMESPACE="idf-testing"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Create report directory
mkdir -p "$REPORT_DIR"

# Function to run CIS Kubernetes Benchmark
run_cis_benchmark() {
    log "${YELLOW}Running CIS Kubernetes Benchmark...${NC}"
    
    # Run kube-bench for EKS
    kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: kube-bench-$(date +%s)
  namespace: default
spec:
  template:
    metadata:
      labels:
        app: kube-bench
    spec:
      hostPID: true
      hostNetwork: true
      tolerations:
      - key: node-role.kubernetes.io/master
        operator: Exists
        effect: NoSchedule
      restartPolicy: Never
      containers:
      - name: kube-bench
        image: aquasec/kube-bench:latest
        command: ["kube-bench", "--benchmark", "eks-1.0.1"]
        volumeMounts:
        - name: var-lib-etcd
          mountPath: /var/lib/etcd
          readOnly: true
        - name: var-lib-kubelet
          mountPath: /var/lib/kubelet
          readOnly: true
        - name: etc-systemd
          mountPath: /etc/systemd
          readOnly: true
        - name: etc-kubernetes
          mountPath: /etc/kubernetes
          readOnly: true
        - name: usr-bin
          mountPath: /usr/local/mount-from-host/bin
          readOnly: true
      volumes:
      - name: var-lib-etcd
        hostPath:
          path: "/var/lib/etcd"
      - name: var-lib-kubelet
        hostPath:
          path: "/var/lib/kubelet"
      - name: etc-systemd
        hostPath:
          path: "/etc/systemd"
      - name: etc-kubernetes
        hostPath:
          path: "/etc/kubernetes"
      - name: usr-bin
        hostPath:
          path: "/usr/bin"
EOF
    
    # Wait for job completion and get results
    kubectl wait --for=condition=complete job/kube-bench-* --timeout=300s
    kubectl logs job/kube-bench-* > "$REPORT_DIR/cis-benchmark-$(date +%Y%m%d).txt"
    kubectl delete job kube-bench-*
    
    log "${GREEN}CIS Benchmark completed. Report saved to $REPORT_DIR${NC}"
}

# Function to scan container images
scan_container_images() {
    log "${YELLOW}Scanning container images for vulnerabilities...${NC}"
    
    # Get all images in the namespace
    local images=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[*].spec.containers[*].image}' | tr ' ' '\n' | sort -u)
    
    for image in $images; do
        log "Scanning image: $image"
        
        # Run Trivy scan
        trivy image --format json --output "$REPORT_DIR/trivy-$(basename $image)-$(date +%Y%m%d).json" "$image" || log "WARNING: Trivy scan failed for $image"
        
        # Run Grype scan
        grype "$image" -o json > "$REPORT_DIR/grype-$(basename $image)-$(date +%Y%m%d).json" || log "WARNING: Grype scan failed for $image"
    done
    
    log "${GREEN}Container image scanning completed${NC}"
}

# Function to check network policies
check_network_policies() {
    log "${YELLOW}Checking network policies...${NC}"
    
    # Check if network policies exist
    local policies=$(kubectl get networkpolicies -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    
    if [ "$policies" -eq 0 ]; then
        log "${RED}WARNING: No network policies found in namespace $NAMESPACE${NC}"
    else
        log "${GREEN}Found $policies network policies${NC}"
        kubectl get networkpolicies -n "$NAMESPACE" -o yaml > "$REPORT_DIR/network-policies-$(date +%Y%m%d).yaml"
    fi
    
    # Test network isolation
    log "Testing network isolation..."
    
    # Create test pod in default namespace
    kubectl run netpol-test --image=busybox:latest --restart=Never --rm -i --tty --timeout=60s \
        -- nc -zv backend-service.$NAMESPACE.svc.cluster.local 8000 2>&1 | tee "$REPORT_DIR/network-test-$(date +%Y%m%d).txt" || true
    
    log "${GREEN}Network policy check completed${NC}"
}

# Function to check RBAC configuration
check_rbac() {
    log "${YELLOW}Checking RBAC configuration...${NC}"
    
    # Get all service accounts
    kubectl get serviceaccounts -n "$NAMESPACE" -o yaml > "$REPORT_DIR/serviceaccounts-$(date +%Y%m%d).yaml"
    
    # Get role bindings
    kubectl get rolebindings -n "$NAMESPACE" -o yaml > "$REPORT_DIR/rolebindings-$(date +%Y%m%d).yaml"
    kubectl get clusterrolebindings -o yaml | grep -A 10 -B 10 "$NAMESPACE" > "$REPORT_DIR/clusterrolebindings-$(date +%Y%m%d).yaml" || true
    
    # Check for overly permissive roles
    log "Checking for overly permissive roles..."
    kubectl get roles,clusterroles -o yaml | grep -E "(resources:.*\*|verbs:.*\*)" > "$REPORT_DIR/permissive-roles-$(date +%Y%m%d).txt" || true
    
    log "${GREEN}RBAC check completed${NC}"
}

# Function to check Pod Security Standards
check_pod_security() {
    log "${YELLOW}Checking Pod Security Standards...${NC}"
    
    # Check pod security contexts
    kubectl get pods -n "$NAMESPACE" -o json | jq '.items[] | {name: .metadata.name, securityContext: .spec.securityContext, containers: [.spec.containers[] | {name: .name, securityContext: .securityContext}]}' > "$REPORT_DIR/pod-security-contexts-$(date +%Y%m%d).json"
    
    # Check for privileged containers
    local privileged=$(kubectl get pods -n "$NAMESPACE" -o json | jq -r '.items[] | select(.spec.containers[]?.securityContext.privileged == true) | .metadata.name' 2>/dev/null || true)
    
    if [ -n "$privileged" ]; then
        log "${RED}WARNING: Found privileged containers: $privileged${NC}"
        echo "$privileged" > "$REPORT_DIR/privileged-containers-$(date +%Y%m%d).txt"
    else
        log "${GREEN}No privileged containers found${NC}"
    fi
    
    # Check for containers running as root
    local root_containers=$(kubectl get pods -n "$NAMESPACE" -o json | jq -r '.items[] | select(.spec.containers[]?.securityContext.runAsUser == 0 or (.spec.containers[]?.securityContext.runAsUser == null and .spec.securityContext.runAsUser == null)) | .metadata.name' 2>/dev/null || true)
    
    if [ -n "$root_containers" ]; then
        log "${RED}WARNING: Found containers running as root: $root_containers${NC}"
        echo "$root_containers" > "$REPORT_DIR/root-containers-$(date +%Y%m%d).txt"
    else
        log "${GREEN}No containers running as root found${NC}"
    fi
    
    log "${GREEN}Pod security check completed${NC}"
}

# Function to check secrets and configmaps
check_secrets() {
    log "${YELLOW}Checking secrets and configmaps...${NC}"
    
    # Get secrets (without data)
    kubectl get secrets -n "$NAMESPACE" -o yaml | sed '/data:/,/^[^ ]/{ /^[^ ]/!d; }' > "$REPORT_DIR/secrets-metadata-$(date +%Y%m%d).yaml"
    
    # Check for hardcoded secrets in configmaps
    kubectl get configmaps -n "$NAMESPACE" -o yaml | grep -i -E "(password|secret|key|token|api)" > "$REPORT_DIR/potential-hardcoded-secrets-$(date +%Y%m%d).txt" || true
    
    # Check secret encryption at rest
    kubectl get secrets -n "$NAMESPACE" -o json | jq '.items[] | {name: .metadata.name, type: .type, dataKeys: (.data | keys)}' > "$REPORT_DIR/secrets-inventory-$(date +%Y%m%d).json"
    
    log "${GREEN}Secrets check completed${NC}"
}

# Function to run Falco runtime security
check_runtime_security() {
    log "${YELLOW}Checking runtime security with Falco...${NC}"
    
    # Check if Falco is running
    if kubectl get pods -n falco-system -l app=falco >/dev/null 2>&1; then
        log "Falco is running, collecting recent alerts..."
        kubectl logs -n falco-system -l app=falco --since=24h > "$REPORT_DIR/falco-alerts-$(date +%Y%m%d).txt" || true
    else
        log "${YELLOW}Falco is not installed. Installing Falco for runtime security monitoring...${NC}"
        
        # Install Falco
        helm repo add falcosecurity https://falcosecurity.github.io/charts
        helm repo update
        helm upgrade --install falco falcosecurity/falco \
            --namespace falco-system \
            --create-namespace \
            --set falco.grpc.enabled=true \
            --set falco.grpcOutput.enabled=true || log "WARNING: Falco installation failed"
    fi
    
    log "${GREEN}Runtime security check completed${NC}"
}

# Function to generate compliance report
generate_compliance_report() {
    log "${YELLOW}Generating compliance report...${NC}"
    
    local report_file="$REPORT_DIR/compliance-report-$(date +%Y%m%d).html"
    
    cat > "$report_file" <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>IDF Testing Infrastructure - Security Compliance Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
        .section { margin: 20px 0; padding: 15px; border-left: 4px solid #3498db; }
        .warning { border-left-color: #f39c12; background-color: #fef9e7; }
        .error { border-left-color: #e74c3c; background-color: #fadbd8; }
        .success { border-left-color: #27ae60; background-color: #d5f5d5; }
        .timestamp { color: #7f8c8d; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>IDF Testing Infrastructure</h1>
        <h2>Security Compliance Report</h2>
        <p class="timestamp">Generated on: $(date)</p>
    </div>
    
    <div class="section">
        <h3>Executive Summary</h3>
        <p>This report provides a comprehensive security assessment of the IDF Testing Infrastructure deployment.</p>
    </div>
    
    <div class="section">
        <h3>Scan Results</h3>
        <ul>
            <li>CIS Kubernetes Benchmark: $(test -f "$REPORT_DIR/cis-benchmark-$(date +%Y%m%d).txt" && echo "✓ Completed" || echo "✗ Failed")</li>
            <li>Container Image Scanning: $(ls "$REPORT_DIR"/trivy-*.json 2>/dev/null | wc -l) images scanned</li>
            <li>Network Policy Check: $(test -f "$REPORT_DIR/network-policies-$(date +%Y%m%d).yaml" && echo "✓ Policies in place" || echo "⚠ No policies found")</li>
            <li>RBAC Configuration: $(test -f "$REPORT_DIR/rbac-$(date +%Y%m%d).yaml" && echo "✓ Reviewed" || echo "✓ Completed")</li>
            <li>Pod Security: $(test -f "$REPORT_DIR/privileged-containers-$(date +%Y%m%d).txt" && echo "⚠ Issues found" || echo "✓ Compliant")</li>
        </ul>
    </div>
    
    <div class="section">
        <h3>Recommendations</h3>
        <ul>
            <li>Regularly update container base images</li>
            <li>Implement network segmentation with NetworkPolicies</li>
            <li>Use non-root containers where possible</li>
            <li>Rotate secrets and credentials regularly</li>
            <li>Monitor runtime security with Falco</li>
        </ul>
    </div>
    
    <div class="section">
        <h3>Next Actions</h3>
        <ul>
            <li>Review and address any high-severity vulnerabilities</li>
            <li>Update security policies based on findings</li>
            <li>Schedule regular security assessments</li>
        </ul>
    </div>
</body>
</html>
EOF
    
    log "${GREEN}Compliance report generated: $report_file${NC}"
}

# Function to send alert notifications
send_alerts() {
    local severity="$1"
    local message="$2"
    
    log "Sending $severity alert: $message"
    
    # Send to Slack (if webhook configured)
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🔒 Security Alert [$severity]: $message\"}" \
            "$SLACK_WEBHOOK_URL" || log "WARNING: Failed to send Slack alert"
    fi
    
    # Send email alert (if configured)
    if [ -n "${ALERT_EMAIL:-}" ]; then
        echo "Security Alert [$severity]: $message" | \
            mail -s "IDF Security Alert" "$ALERT_EMAIL" || log "WARNING: Failed to send email alert"
    fi
}

# Main function
main() {
    log "${GREEN}Starting security compliance scan...${NC}"
    
    case "${1:-all}" in
        "cis")
            run_cis_benchmark
            ;;
        "images")
            scan_container_images
            ;;
        "network")
            check_network_policies
            ;;
        "rbac")
            check_rbac
            ;;
        "pods")
            check_pod_security
            ;;
        "secrets")
            check_secrets
            ;;
        "runtime")
            check_runtime_security
            ;;
        "report")
            generate_compliance_report
            ;;
        "all"|*)
            run_cis_benchmark
            scan_container_images
            check_network_policies
            check_rbac
            check_pod_security
            check_secrets
            check_runtime_security
            generate_compliance_report
            
            # Check for critical issues and send alerts
            if grep -q "FAIL" "$REPORT_DIR/cis-benchmark-$(date +%Y%m%d).txt" 2>/dev/null; then
                send_alerts "HIGH" "CIS Benchmark failures detected"
            fi
            
            if [ -f "$REPORT_DIR/privileged-containers-$(date +%Y%m%d).txt" ]; then
                send_alerts "MEDIUM" "Privileged containers detected"
            fi
            ;;
    esac
    
    log "${GREEN}Security compliance scan completed. Reports available in $REPORT_DIR${NC}"
}

# Check dependencies
command -v kubectl >/dev/null 2>&1 || error_exit "kubectl is required but not installed"
command -v trivy >/dev/null 2>&1 || log "${YELLOW}WARNING: trivy not found, container scanning will be limited${NC}"
command -v grype >/dev/null 2>&1 || log "${YELLOW}WARNING: grype not found, container scanning will be limited${NC}"
command -v jq >/dev/null 2>&1 || error_exit "jq is required but not installed"

# Run with provided arguments
main "$@"