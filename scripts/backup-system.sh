#!/bin/bash
# IDF Testing Infrastructure - Database Backup and Recovery System
# Military-grade backup with encryption and redundancy

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/backup.conf"
LOG_FILE="/var/log/idf-backup.log"
RETENTION_DAYS=30
BACKUP_USER="idf_user"
DATABASE="idf_testing"

# Encryption settings
ENCRYPTION_KEY_FILE="/etc/idf/backup.key"
GPG_RECIPIENT="idf-backup@mil.il"

# Load configuration
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Generate encryption key if not exists
generate_encryption_key() {
    if [[ ! -f "$ENCRYPTION_KEY_FILE" ]]; then
        log "Generating new encryption key..."
        mkdir -p "$(dirname "$ENCRYPTION_KEY_FILE")"
        openssl rand -base64 32 > "$ENCRYPTION_KEY_FILE"
        chmod 600 "$ENCRYPTION_KEY_FILE"
        log "Encryption key generated: $ENCRYPTION_KEY_FILE"
    fi
}

# Database backup function
backup_database() {
    local backup_type="$1"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_dir="/backups/${backup_type}/${timestamp}"
    
    log "Starting $backup_type backup..."
    
    # Create backup directory
    mkdir -p "$backup_dir"
    
    # Full database backup
    if [[ "$backup_type" == "full" ]]; then
        log "Creating full database backup..."
        pg_dump -h postgres-primary -U "$BACKUP_USER" -d "$DATABASE" \
            --verbose --format=custom --compress=9 \
            --file="$backup_dir/database_full.dump" || error_exit "Full backup failed"
        
        # Schema-only backup
        pg_dump -h postgres-primary -U "$BACKUP_USER" -d "$DATABASE" \
            --schema-only --verbose \
            --file="$backup_dir/schema.sql" || error_exit "Schema backup failed"
        
        # Globals backup
        pg_dumpall -h postgres-primary -U "$BACKUP_USER" \
            --globals-only --verbose \
            --file="$backup_dir/globals.sql" || error_exit "Globals backup failed"
    
    # Incremental backup (WAL archives)
    elif [[ "$backup_type" == "incremental" ]]; then
        log "Creating incremental backup..."
        # Archive WAL files
        pg_receivewal -h postgres-primary -U "$BACKUP_USER" \
            --directory="$backup_dir/wal" \
            --compress=9 --verbose || error_exit "WAL backup failed"
    fi
    
    # Backup application uploads
    if [[ -d "/app/uploads" ]]; then
        log "Backing up application uploads..."
        tar -czf "$backup_dir/uploads.tar.gz" -C /app uploads/
    fi
    
    # Backup configuration files
    log "Backing up configuration files..."
    tar -czf "$backup_dir/config.tar.gz" \
        /etc/postgresql/ \
        /etc/nginx/ \
        /etc/idf/ 2>/dev/null || true
    
    # Create backup manifest
    cat > "$backup_dir/manifest.json" << EOF
{
    "backup_type": "$backup_type",
    "timestamp": "$timestamp",
    "database": "$DATABASE",
    "files": [
        $(find "$backup_dir" -type f -name "*.dump" -o -name "*.sql" -o -name "*.tar.gz" | \
          xargs -I {} basename {} | sed 's/^/        "/' | sed 's/$/",/' | sed '$s/,$//')
    ],
    "size_bytes": $(du -sb "$backup_dir" | cut -f1),
    "checksum": "$(find "$backup_dir" -type f -exec sha256sum {} \; | sha256sum | cut -d' ' -f1)"
}
EOF
    
    # Encrypt backup
    log "Encrypting backup..."
    tar -czf - -C "$(dirname "$backup_dir")" "$(basename "$backup_dir")" | \
        gpg --cipher-algo AES256 --compress-algo 2 --symmetric \
            --passphrase-file "$ENCRYPTION_KEY_FILE" \
            --output "$backup_dir.gpg" || error_exit "Encryption failed"
    
    # Remove unencrypted backup
    rm -rf "$backup_dir"
    
    # Upload to remote storage (if configured)
    if [[ -n "${S3_BUCKET:-}" ]]; then
        log "Uploading backup to S3..."
        aws s3 cp "$backup_dir.gpg" "s3://$S3_BUCKET/backups/" \
            --storage-class STANDARD_IA || log "WARNING: S3 upload failed"
    fi
    
    log "$backup_type backup completed: $backup_dir.gpg"
}

# Restore database function
restore_database() {
    local backup_file="$1"
    local restore_point="${2:-latest}"
    
    log "Starting database restoration from: $backup_file"
    
    # Verify backup file exists
    [[ -f "$backup_file" ]] || error_exit "Backup file not found: $backup_file"
    
    # Create temporary directory for restoration
    local temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" EXIT
    
    # Decrypt backup
    log "Decrypting backup..."
    gpg --quiet --batch --yes --decrypt \
        --passphrase-file "$ENCRYPTION_KEY_FILE" \
        --output "$temp_dir/backup.tar.gz" \
        "$backup_file" || error_exit "Decryption failed"
    
    # Extract backup
    log "Extracting backup..."
    tar -xzf "$temp_dir/backup.tar.gz" -C "$temp_dir"
    
    local backup_dir=$(find "$temp_dir" -maxdepth 1 -type d -name "20*" | head -1)
    [[ -d "$backup_dir" ]] || error_exit "Backup directory not found"
    
    # Verify backup integrity
    log "Verifying backup integrity..."
    local manifest_file="$backup_dir/manifest.json"
    [[ -f "$manifest_file" ]] || error_exit "Backup manifest not found"
    
    # Stop application services
    log "Stopping application services..."
    kubectl scale deployment backend --replicas=0 -n idf-testing || true
    
    # Create new database (if needed)
    log "Preparing database for restoration..."
    createdb -h postgres-primary -U "$BACKUP_USER" "${DATABASE}_restore" || true
    
    # Restore globals
    if [[ -f "$backup_dir/globals.sql" ]]; then
        log "Restoring database globals..."
        psql -h postgres-primary -U "$BACKUP_USER" -d postgres \
            -f "$backup_dir/globals.sql" || log "WARNING: Globals restoration failed"
    fi
    
    # Restore database
    if [[ -f "$backup_dir/database_full.dump" ]]; then
        log "Restoring database..."
        pg_restore -h postgres-primary -U "$BACKUP_USER" \
            --dbname="${DATABASE}_restore" --verbose --clean --if-exists \
            "$backup_dir/database_full.dump" || error_exit "Database restoration failed"
    fi
    
    # Restore uploads
    if [[ -f "$backup_dir/uploads.tar.gz" ]]; then
        log "Restoring application uploads..."
        tar -xzf "$backup_dir/uploads.tar.gz" -C /app/
    fi
    
    # Switch databases (careful operation)
    if [[ "$restore_point" == "switch" ]]; then
        log "Switching to restored database..."
        psql -h postgres-primary -U "$BACKUP_USER" -d postgres -c \
            "ALTER DATABASE $DATABASE RENAME TO ${DATABASE}_old;"
        psql -h postgres-primary -U "$BACKUP_USER" -d postgres -c \
            "ALTER DATABASE ${DATABASE}_restore RENAME TO $DATABASE;"
    fi
    
    # Restart application services
    log "Restarting application services..."
    kubectl scale deployment backend --replicas=3 -n idf-testing
    
    log "Database restoration completed successfully"
}

# Cleanup old backups
cleanup_backups() {
    log "Cleaning up old backups..."
    
    find /backups -name "*.gpg" -type f -mtime +$RETENTION_DAYS -delete || true
    
    # Clean S3 backups if configured
    if [[ -n "${S3_BUCKET:-}" ]]; then
        aws s3 ls "s3://$S3_BUCKET/backups/" | \
        awk '$1 < "'$(date -d "-$RETENTION_DAYS days" '+%Y-%m-%d')'" {print $4}' | \
        xargs -I {} aws s3 rm "s3://$S3_BUCKET/backups/{}" || true
    fi
    
    log "Backup cleanup completed"
}

# Health check function
health_check() {
    log "Performing backup system health check..."
    
    # Check database connectivity
    pg_isready -h postgres-primary -U "$BACKUP_USER" || error_exit "Database not accessible"
    
    # Check encryption key
    [[ -f "$ENCRYPTION_KEY_FILE" ]] || error_exit "Encryption key not found"
    
    # Check backup directory
    [[ -d "/backups" ]] || mkdir -p /backups
    
    # Check available space
    local available_space=$(df /backups | awk 'NR==2 {print $4}')
    [[ $available_space -gt 1048576 ]] || log "WARNING: Low disk space on backup volume"
    
    # Test backup and restore
    if [[ "${1:-}" == "test" ]]; then
        log "Running backup/restore test..."
        backup_database "test"
        # Note: Full restore test should be done in non-production environment
    fi
    
    log "Health check completed"
}

# Main function
main() {
    case "${1:-}" in
        "full")
            generate_encryption_key
            backup_database "full"
            cleanup_backups
            ;;
        "incremental")
            generate_encryption_key
            backup_database "incremental"
            ;;
        "restore")
            [[ -n "${2:-}" ]] || error_exit "Backup file required for restore"
            restore_database "$2" "${3:-latest}"
            ;;
        "cleanup")
            cleanup_backups
            ;;
        "health")
            health_check "${2:-}"
            ;;
        *)
            echo "Usage: $0 {full|incremental|restore|cleanup|health} [options]"
            echo "  full                    - Create full encrypted backup"
            echo "  incremental             - Create incremental backup"
            echo "  restore <file> [switch] - Restore from backup file"
            echo "  cleanup                 - Remove old backups"
            echo "  health [test]           - Check backup system health"
            exit 1
            ;;
    esac
}

# Run with provided arguments
main "$@"