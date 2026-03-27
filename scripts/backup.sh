#!/bin/bash
# =========================================================================
# PRODUCTION BACKUP SCRIPT
# Cisco Telephony Monitoring System
# =========================================================================

set -euo pipefail

# =========================================================================
# CONFIGURATION
# =========================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
CONFIG_FILE="${PROJECT_DIR}/config/.env.production"
LOG_FILE="${PROJECT_DIR}/logs/backup.log"

# Load configuration
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    echo "ERROR: Configuration file not found: $CONFIG_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

# Backup settings
BACKUP_ENABLED="${BACKUP_ENABLED:-true}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
BACKUP_COMPRESSION="${BACKUP_COMPRESSION:-gzip}"
BACKUP_ENCRYPTION="${BACKUP_ENCRYPTION:-true}"
BACKUP_STORAGE_TYPE="${BACKUP_STORAGE_TYPE:-local}"
BACKUP_LOCAL_PATH="${BACKUP_LOCAL_PATH:-/app/backups}"

# Create backup directory
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# =========================================================================
# LOGGING FUNCTIONS
# =========================================================================
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1" | tee -a "$LOG_FILE"
}

# =========================================================================
# UTILITY FUNCTIONS
# =========================================================================
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
}

check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
}

generate_backup_filename() {
    local component="$1"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    echo "${component}_backup_${timestamp}.sql"
}

cleanup_old_backups() {
    local component="$1"
    local retention_days="$2"
    
    log "Cleaning up old ${component} backups (retention: ${retention_days} days)"
    
    find "$BACKUP_DIR" -name "${component}_backup_*.sql*" -type f -mtime "+${retention_days}" -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "${component}_backup_*.sql*" -type f -mtime "+${retention_days}" -exec rm -f {} \; 2>/dev/null || true
    
    log "Old ${component} backups cleanup completed"
}

compress_backup() {
    local backup_file="$1"
    
    if [[ "$BACKUP_COMPRESSION" == "gzip" ]]; then
        log "Compressing backup: $backup_file"
        gzip "$backup_file"
        backup_file="${backup_file}.gz"
        log_success "Backup compressed: ${backup_file}"
    fi
    
    echo "$backup_file"
}

encrypt_backup() {
    local backup_file="$1"
    
    if [[ "$BACKUP_ENCRYPTION" == "true" ]]; then
        log "Encrypting backup: $backup_file"
        
        # Generate encryption key if not exists
        local encryption_key_file="${PROJECT_DIR}/.backup_key"
        if [[ ! -f "$encryption_key_file" ]]; then
            openssl rand -hex 32 > "$encryption_key_file"
            chmod 600 "$encryption_key_file"
            log "Generated encryption key: $encryption_key_file"
        fi
        
        # Encrypt the backup
        openssl enc -aes-256-cbc -salt -in "$backup_file" -out "${backup_file}.enc" -pass file:"$encryption_key_file"
        rm -f "$backup_file"
        backup_file="${backup_file}.enc"
        
        log_success "Backup encrypted: ${backup_file}"
    fi
    
    echo "$backup_file"
}

# =========================================================================
# DATABASE BACKUP FUNCTIONS
# =========================================================================
backup_postgres_database() {
    local container="$1"
    local database="$2"
    local user="$3"
    
    log "Starting backup for ${database} database"
    
    local backup_file="${BACKUP_DIR}/$(generate_backup_filename "$database")"
    
    # Create backup
    if docker exec "$container" pg_dump -U "$user" -d "$database" --no-password --verbose --format=custom > "$backup_file" 2>> "$LOG_FILE"; then
        log_success "Database backup created: ${backup_file}"
        
        # Compress backup
        backup_file=$(compress_backup "$backup_file")
        
        # Encrypt backup
        backup_file=$(encrypt_backup "$backup_file")
        
        # Cleanup old backups
        cleanup_old_backups "$database" "$BACKUP_RETENTION_DAYS"
        
        return 0
    else
        log_error "Failed to backup ${database} database"
        rm -f "$backup_file"
        return 1
    fi
}

backup_all_databases() {
    log "Starting backup of all databases"
    
    local databases=(
        "telephony-cucm-postgres-prod:cucm_db:telephony_user"
        "telephony-uccx-postgres-prod:uccx_db:telephony_user"
        "telephony-tgw-postgres-prod:tgw_db:telephony_user"
        "telephony-sbc-postgres-prod:sbc_db:telephony_user"
        "telephony-cms-postgres-prod:cms_db:telephony_user"
        "telephony-imp-postgres-prod:imp_db:telephony_user"
        "telephony-meeting-place-postgres-prod:meeting_place_db:telephony_user"
        "telephony-expressway-postgres-prod:expressway_db:telephony_user"
    )
    
    local success_count=0
    local total_count=${#databases[@]}
    
    for db_info in "${databases[@]}"; do
        IFS=':' read -r container database user <<< "$db_info"
        
        if backup_postgres_database "$container" "$database" "$user"; then
            ((success_count++))
        fi
    done
    
    log "Database backup completed: ${success_count}/${total_count} databases backed up successfully"
    
    if [[ $success_count -eq $total_count ]]; then
        return 0
    else
        return 1
    fi
}

# =========================================================================
# REDIS BACKUP FUNCTIONS
# =========================================================================
backup_redis() {
    log "Starting Redis backup"
    
    local container="telephony-redis-prod"
    local backup_file="${BACKUP_DIR}/$(generate_backup_filename "redis")"
    
    # Create Redis backup
    if docker exec "$container" redis-cli BGSAVE > /dev/null 2>> "$LOG_FILE"; then
        # Wait for backup to complete
        local retry_count=0
        local max_retries=30
        
        while [[ $retry_count -lt $max_retries ]]; do
            local last_save=$(docker exec "$container" redis-cli LASTSAVE 2>/dev/null || echo "0")
            local current_save=$(docker exec "$container" redis-cli LASTSAVE 2>/dev/null || echo "0")
            
            if [[ "$last_save" != "$current_save" ]]; then
                break
            fi
            
            sleep 2
            ((retry_count++))
        done
        
        # Copy RDB file
        if docker cp "$container:/data/dump.rdb" "$backup_file" 2>> "$LOG_FILE"; then
            log_success "Redis backup created: ${backup_file}"
            
            # Compress backup
            backup_file=$(compress_backup "$backup_file")
            
            # Encrypt backup
            backup_file=$(encrypt_backup "$backup_file")
            
            # Cleanup old backups
            cleanup_old_backups "redis" "$BACKUP_RETENTION_DAYS"
            
            return 0
        else
            log_error "Failed to copy Redis RDB file"
            return 1
        fi
    else
        log_error "Failed to trigger Redis backup"
        return 1
    fi
}

# =========================================================================
# CONFIGURATION BACKUP FUNCTIONS
# =========================================================================
backup_configuration() {
    log "Starting configuration backup"
    
    local config_backup_dir="${BACKUP_DIR}/config_backup_$(date '+%Y%m%d_%H%M%S')"
    mkdir -p "$config_backup_dir"
    
    # Backup configuration files
    local config_files=(
        "config/.env.production"
        "config/.env.development"
        "config/production.py"
        "config/docker-compose.prod.yml"
        "docker-compose.yml"
        "config.py"
        "requirements.txt"
    )
    
    for config_file in "${config_files[@]}"; do
        if [[ -f "$PROJECT_DIR/$config_file" ]]; then
            cp "$PROJECT_DIR/$config_file" "$config_backup_dir/"
            log "Copied configuration: $config_file"
        fi
    done
    
    # Backup Docker volumes information
    docker-compose -f "${PROJECT_DIR}/config/docker-compose.prod.yml" config > "$config_backup_dir/docker-compose-config.yml" 2>> "$LOG_FILE"
    
    # Create archive
    local archive_file="${BACKUP_DIR}/$(generate_backup_filename "config")"
    cd "$BACKUP_DIR"
    tar -czf "$archive_file" -C "$BACKUP_DIR" "$(basename "$config_backup_dir")"
    rm -rf "$config_backup_dir"
    
    log_success "Configuration backup created: ${archive_file}"
    
    # Cleanup old backups
    cleanup_old_backups "config" "$BACKUP_RETENTION_DAYS"
}

# =========================================================================
# CLOUD BACKUP FUNCTIONS
# =========================================================================
backup_to_s3() {
    local backup_file="$1"
    
    if [[ "$BACKUP_STORAGE_TYPE" == "s3" ]] && command -v aws &> /dev/null; then
        log "Uploading backup to S3: $backup_file"
        
        local s3_bucket="${BACKUP_S3_BUCKET:-telephony-backups}"
        local s3_region="${BACKUP_S3_REGION:-us-east-1}"
        
        if aws s3 cp "$backup_file" "s3://${s3_bucket}/$(basename "$backup_file")" --region "$s3_region" 2>> "$LOG_FILE"; then
            log_success "Backup uploaded to S3: $(basename "$backup_file")"
            return 0
        else
            log_error "Failed to upload backup to S3: $(basename "$backup_file")"
            return 1
        fi
    fi
    
    return 0
}

# =========================================================================
# MAIN BACKUP FUNCTION
# =========================================================================
perform_full_backup() {
    log "Starting full system backup"
    
    local start_time=$(date +%s)
    local backup_success=true
    
    # Check prerequisites
    check_docker
    check_docker_compose
    
    # Backup databases
    if ! backup_all_databases; then
        backup_success=false
    fi
    
    # Backup Redis
    if ! backup_redis; then
        backup_success=false
    fi
    
    # Backup configuration
    backup_configuration
    
    # Upload to cloud if configured
    if [[ "$BACKUP_STORAGE_TYPE" == "s3" ]]; then
        for backup_file in "$BACKUP_DIR"/*_backup_*.sql*; do
            if [[ -f "$backup_file" ]]; then
                backup_to_s3 "$backup_file"
            fi
        done
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [[ "$backup_success" == "true" ]]; then
        log_success "Full backup completed successfully in ${duration} seconds"
        return 0
    else
        log_error "Full backup completed with errors in ${duration} seconds"
        return 1
    fi
}

# =========================================================================
# HEALTH CHECK FUNCTION
# =========================================================================
check_backup_health() {
    log "Checking backup health"
    
    local backup_count=$(find "$BACKUP_DIR" -name "*_backup_*" -type f | wc -l)
    local latest_backup=$(find "$BACKUP_DIR" -name "*_backup_*" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
    
    log "Total backups: $backup_count"
    
    if [[ -n "$latest_backup" ]]; then
        local backup_age=$(($(date +%s) - $(stat -c %Y "$latest_backup")))
        local backup_age_hours=$((backup_age / 3600))
        
        log "Latest backup: $(basename "$latest_backup") (${backup_age_hours} hours ago)"
        
        if [[ $backup_age_hours -gt 24 ]]; then
            log_error "Latest backup is older than 24 hours"
            return 1
        fi
    else
        log_error "No backups found"
        return 1
    fi
    
    return 0
}

# =========================================================================
# MAIN EXECUTION
# =========================================================================
main() {
    case "${1:-full}" in
        "full")
            if [[ "$BACKUP_ENABLED" == "true" ]]; then
                perform_full_backup
            else
                log "Backup is disabled in configuration"
                exit 0
            fi
            ;;
        "databases")
            backup_all_databases
            ;;
        "redis")
            backup_redis
            ;;
        "config")
            backup_configuration
            ;;
        "health")
            check_backup_health
            ;;
        "cleanup")
            log "Running backup cleanup"
            cleanup_old_backups "cucm" "$BACKUP_RETENTION_DAYS"
            cleanup_old_backups "uccx" "$BACKUP_RETENTION_DAYS"
            cleanup_old_backups "tgw" "$BACKUP_RETENTION_DAYS"
            cleanup_old_backups "sbc" "$BACKUP_RETENTION_DAYS"
            cleanup_old_backups "redis" "$BACKUP_RETENTION_DAYS"
            cleanup_old_backups "config" "$BACKUP_RETENTION_DAYS"
            ;;
        *)
            echo "Usage: $0 {full|databases|redis|config|health|cleanup}"
            echo "  full      - Perform full system backup"
            echo "  databases - Backup all databases"
            echo "  redis     - Backup Redis data"
            echo "  config    - Backup configuration files"
            echo "  health    - Check backup health"
            echo "  cleanup   - Clean up old backups"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
