#!/bin/bash
# =========================================================================
# PRODUCTION RESTORE SCRIPT
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
LOG_FILE="${PROJECT_DIR}/logs/restore.log"

# Load configuration
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    echo "ERROR: Configuration file not found: $CONFIG_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

# Restore settings
BACKUP_ENCRYPTION="${BACKUP_ENCRYPTION:-true}"
BACKUP_STORAGE_TYPE="${BACKUP_STORAGE_TYPE:-local}"
BACKUP_S3_BUCKET="${BACKUP_S3_BUCKET:-telephony-backups}"
BACKUP_S3_REGION="${BACKUP_S3_REGION:-us-east-1}"

# Create log directory
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

log_warning() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1" | tee -a "$LOG_FILE"
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

confirm_action() {
    local message="$1"
    local default="${2:-n}"
    
    echo -n "$message [y/N]: "
    read -r response
    response=${response:-$default}
    
    case "$response" in
        [yY]|[yY][eE][sS])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

decrypt_backup() {
    local backup_file="$1"
    
    if [[ "$backup_file" == *.enc ]]; then
        log "Decrypting backup: $backup_file"
        
        local encryption_key_file="${PROJECT_DIR}/.backup_key"
        if [[ ! -f "$encryption_key_file" ]]; then
            log_error "Encryption key not found: $encryption_key_file"
            return 1
        fi
        
        local decrypted_file="${backup_file%.enc}"
        if openssl enc -aes-256-cbc -d -in "$backup_file" -out "$decrypted_file" -pass file:"$encryption_key_file" 2>> "$LOG_FILE"; then
            log_success "Backup decrypted: ${decrypted_file}"
            echo "$decrypted_file"
            return 0
        else
            log_error "Failed to decrypt backup: $backup_file"
            return 1
        fi
    else
        echo "$backup_file"
        return 0
    fi
}

decompress_backup() {
    local backup_file="$1"
    
    if [[ "$backup_file" == *.gz ]]; then
        log "Decompressing backup: $backup_file"
        
        local decompressed_file="${backup_file%.gz}"
        if gunzip -c "$backup_file" > "$decompressed_file" 2>> "$LOG_FILE"; then
            log_success "Backup decompressed: ${decompressed_file}"
            echo "$decompressed_file"
            return 0
        else
            log_error "Failed to decompress backup: $backup_file"
            return 1
        fi
    else
        echo "$backup_file"
        return 0
    fi
}

download_from_s3() {
    local backup_file="$1"
    local local_path="$2"
    
    if [[ "$BACKUP_STORAGE_TYPE" == "s3" ]] && command -v aws &> /dev/null; then
        log "Downloading backup from S3: $backup_file"
        
        if aws s3 cp "s3://${BACKUP_S3_BUCKET}/$backup_file" "$local_path" --region "$BACKUP_S3_REGION" 2>> "$LOG_FILE"; then
            log_success "Backup downloaded from S3: $backup_file"
            return 0
        else
            log_error "Failed to download backup from S3: $backup_file"
            return 1
        fi
    fi
    
    return 0
}

# =========================================================================
# BACKUP SELECTION FUNCTIONS
# =========================================================================
list_available_backups() {
    local component="$1"
    
    log "Available backups for ${component}:"
    
    local backups=()
    if [[ "$BACKUP_STORAGE_TYPE" == "s3" ]] && command -v aws &> /dev/null; then
        # List S3 backups
        while IFS= read -r line; do
            backups+=("$line")
        done < <(aws s3 ls "s3://${BACKUP_S3_BUCKET}/" --region "$BACKUP_S3_REGION" 2>/dev/null | grep "${component}_backup_" | sort -r)
    fi
    
    # List local backups
    while IFS= read -r -d '' backup_file; do
        backups+=("local:$(basename "$backup_file")")
    done < <(find "$BACKUP_DIR" -name "${component}_backup_*" -type f -print0 2>/dev/null | sort -rz)
    
    if [[ ${#backups[@]} -eq 0 ]]; then
        log_warning "No backups found for ${component}"
        return 1
    fi
    
    local i=1
    for backup in "${backups[@]}"; do
        echo "  $i) $backup"
        ((i++))
    done
    
    return 0
}

select_backup() {
    local component="$1"
    
    if ! list_available_backups "$component"; then
        return 1
    fi
    
    echo -n "Select backup number (or 'q' to quit): "
    read -r selection
    
    if [[ "$selection" == "q" ]]; then
        return 1
    fi
    
    if ! [[ "$selection" =~ ^[0-9]+$ ]]; then
        log_error "Invalid selection: $selection"
        return 1
    fi
    
    local backup_file
    if [[ "$BACKUP_STORAGE_TYPE" == "s3" ]] && command -v aws &> /dev/null; then
        backup_file=$(aws s3 ls "s3://${BACKUP_S3_BUCKET}/" --region "$BACKUP_S3_REGION" 2>/dev/null | grep "${component}_backup_" | sort -r | sed -n "${selection}p" | awk '{print $4}')
    else
        backup_file=$(find "$BACKUP_DIR" -name "${component}_backup_*" -type f | sort -r | sed -n "${selection}p")
    fi
    
    if [[ -z "$backup_file" ]]; then
        log_error "Invalid backup selection: $selection"
        return 1
    fi
    
    echo "$backup_file"
}

# =========================================================================
# DATABASE RESTORE FUNCTIONS
# =========================================================================
restore_postgres_database() {
    local container="$1"
    local database="$2"
    local user="$3"
    local backup_file="$4"
    
    log "Starting restore for ${database} database from: $(basename "$backup_file")"
    
    # Download from S3 if needed
    if [[ "$backup_file" == s3://* ]]; then
        local local_backup="${BACKUP_DIR}/$(basename "$backup_file")"
        if ! download_from_s3 "${backup_file#s3://*/}" "$local_backup"; then
            return 1
        fi
        backup_file="$local_backup"
    fi
    
    # Decrypt backup
    backup_file=$(decrypt_backup "$backup_file")
    if [[ $? -ne 0 ]]; then
        return 1
    fi
    
    # Decompress backup
    backup_file=$(decompress_backup "$backup_file")
    if [[ $? -ne 0 ]]; then
        return 1
    fi
    
    # Drop existing database (with confirmation)
    if confirm_action "Drop existing database '$database'? This will delete all current data."; then
        log "Dropping existing database: $database"
        docker exec "$container" psql -U "$user" -c "DROP DATABASE IF EXISTS $database;" 2>> "$LOG_FILE" || true
    fi
    
    # Create database
    log "Creating database: $database"
    docker exec "$container" psql -U "$user" -c "CREATE DATABASE $database;" 2>> "$LOG_FILE"
    
    # Restore database
    log "Restoring database from backup"
    if docker exec -i "$container" pg_restore -U "$user" -d "$database" --verbose --clean --if-exists --no-owner --no-privileges < "$backup_file" 2>> "$LOG_FILE"; then
        log_success "Database restore completed: $database"
        
        # Cleanup temporary files
        if [[ "$backup_file" == *.sql ]]; then
            rm -f "$backup_file"
        fi
        
        return 0
    else
        log_error "Failed to restore database: $database"
        return 1
    fi
}

# =========================================================================
# REDIS RESTORE FUNCTIONS
# =========================================================================
restore_redis() {
    local container="$1"
    local backup_file="$2"
    
    log "Starting Redis restore from: $(basename "$backup_file")"
    
    # Download from S3 if needed
    if [[ "$backup_file" == s3://* ]]; then
        local local_backup="${BACKUP_DIR}/$(basename "$backup_file")"
        if ! download_from_s3 "${backup_file#s3://*/}" "$local_backup"; then
            return 1
        fi
        backup_file="$local_backup"
    fi
    
    # Decrypt backup
    backup_file=$(decrypt_backup "$backup_file")
    if [[ $? -ne 0 ]]; then
        return 1
    fi
    
    # Decompress backup
    backup_file=$(decompress_backup "$backup_file")
    if [[ $? -ne 0 ]]; then
        return 1
    fi
    
    # Stop Redis
    log "Stopping Redis service"
    docker exec "$container" redis-cli SHUTDOWN NOSAVE 2>> "$LOG_FILE" || true
    
    # Copy RDB file
    log "Copying RDB file to container"
    if docker cp "$backup_file" "$container:/data/dump.rdb" 2>> "$LOG_FILE"; then
        # Start Redis
        log "Starting Redis service"
        docker start "$container" 2>> "$LOG_FILE"
        
        # Wait for Redis to start
        local retry_count=0
        local max_retries=30
        
        while [[ $retry_count -lt $max_retries ]]; do
            if docker exec "$container" redis-cli ping 2>/dev/null | grep -q "PONG"; then
                break
            fi
            
            sleep 2
            ((retry_count++))
        done
        
        if [[ $retry_count -lt $max_retries ]]; then
            log_success "Redis restore completed"
            
            # Cleanup temporary files
            rm -f "$backup_file"
            
            return 0
        else
            log_error "Redis failed to start after restore"
            return 1
        fi
    else
        log_error "Failed to copy RDB file to container"
        return 1
    fi
}

# =========================================================================
# CONFIGURATION RESTORE FUNCTIONS
# =========================================================================
restore_configuration() {
    local backup_file="$1"
    
    log "Starting configuration restore from: $(basename "$backup_file")"
    
    # Download from S3 if needed
    if [[ "$backup_file" == s3://* ]]; then
        local local_backup="${BACKUP_DIR}/$(basename "$backup_file")"
        if ! download_from_s3 "${backup_file#s3://*/}" "$local_backup"; then
            return 1
        fi
        backup_file="$local_backup"
    fi
    
    # Extract configuration backup
    local temp_dir="${BACKUP_DIR}/config_restore_$(date '+%Y%m%d_%H%M%S')"
    mkdir -p "$temp_dir"
    
    if tar -xzf "$backup_file" -C "$temp_dir" 2>> "$LOG_FILE"; then
        # Restore configuration files
        local config_backup_dir=$(find "$temp_dir" -name "config_backup_*" -type d | head -1)
        
        if [[ -n "$config_backup_dir" ]]; then
            log "Restoring configuration files"
            
            # Backup current configuration
            local current_config_backup="${BACKUP_DIR}/current_config_backup_$(date '+%Y%m%d_%H%M%S')"
            mkdir -p "$current_config_backup"
            
            local config_files=(
                ".env.production"
                ".env.development"
                "production.py"
                "docker-compose.prod.yml"
                "docker-compose.yml"
                "config.py"
                "requirements.txt"
            )
            
            for config_file in "${config_files[@]}"; do
                if [[ -f "$PROJECT_DIR/config/$config_file" ]]; then
                    cp "$PROJECT_DIR/config/$config_file" "$current_config_backup/"
                fi
                if [[ -f "$config_backup_dir/$config_file" ]]; then
                    cp "$config_backup_dir/$config_file" "$PROJECT_DIR/config/"
                    log "Restored configuration: $config_file"
                fi
            done
            
            log_success "Configuration restore completed"
            log "Current configuration backed up to: $current_config_backup"
            
            # Cleanup
            rm -rf "$temp_dir"
            
            return 0
        else
            log_error "Invalid configuration backup format"
            return 1
        fi
    else
        log_error "Failed to extract configuration backup"
        return 1
    fi
}

# =========================================================================
# MAIN RESTORE FUNCTIONS
# =========================================================================
restore_database() {
    local component="$1"
    local backup_file="$2"
    
    case "$component" in
        "cucm")
            restore_postgres_database "telephony-cucm-postgres-prod" "cucm_db" "telephony_user" "$backup_file"
            ;;
        "uccx")
            restore_postgres_database "telephony-uccx-postgres-prod" "uccx_db" "telephony_user" "$backup_file"
            ;;
        "tgw")
            restore_postgres_database "telephony-tgw-postgres-prod" "tgw_db" "telephony_user" "$backup_file"
            ;;
        "sbc")
            restore_postgres_database "telephony-sbc-postgres-prod" "sbc_db" "telephony_user" "$backup_file"
            ;;
        "cms")
            restore_postgres_database "telephony-cms-postgres-prod" "cms_db" "telephony_user" "$backup_file"
            ;;
        "imp")
            restore_postgres_database "telephony-imp-postgres-prod" "imp_db" "telephony_user" "$backup_file"
            ;;
        "meeting_place")
            restore_postgres_database "telephony-meeting-place-postgres-prod" "meeting_place_db" "telephony_user" "$backup_file"
            ;;
        "expressway")
            restore_postgres_database "telephony-expressway-postgres-prod" "expressway_db" "telephony_user" "$backup_file"
            ;;
        *)
            log_error "Unknown database component: $component"
            return 1
            ;;
    esac
}

restore_redis_data() {
    local backup_file="$1"
    restore_redis "telephony-redis-prod" "$backup_file"
}

restore_config_files() {
    local backup_file="$1"
    restore_configuration "$backup_file"
}

# =========================================================================
# MAIN EXECUTION
# =========================================================================
main() {
    local action="${1:-help}"
    local component="${2:-}"
    local backup_file="${3:-}"
    
    # Check prerequisites
    check_docker
    check_docker_compose
    
    case "$action" in
        "database")
            if [[ -z "$component" ]]; then
                log_error "Component name required for database restore"
                echo "Available components: cucm, uccx, tgw, sbc, cms, imp, meeting_place, expressway"
                exit 1
            fi
            
            if [[ -z "$backup_file" ]]; then
                backup_file=$(select_backup "$component")
                if [[ $? -ne 0 ]]; then
                    exit 1
                fi
            fi
            
            if confirm_action "Restore database '$component' from backup? This will replace all current data."; then
                restore_database "$component" "$backup_file"
            else
                log "Database restore cancelled"
            fi
            ;;
        "redis")
            if [[ -z "$backup_file" ]]; then
                backup_file=$(select_backup "redis")
                if [[ $? -ne 0 ]]; then
                    exit 1
                fi
            fi
            
            if confirm_action "Restore Redis from backup? This will replace all current data."; then
                restore_redis_data "$backup_file"
            else
                log "Redis restore cancelled"
            fi
            ;;
        "config")
            if [[ -z "$backup_file" ]]; then
                backup_file=$(select_backup "config")
                if [[ $? -ne 0 ]]; then
                    exit 1
                fi
            fi
            
            if confirm_action "Restore configuration files? This will replace current configuration."; then
                restore_config_files "$backup_file"
            else
                log "Configuration restore cancelled"
            fi
            ;;
        "list")
            if [[ -z "$component" ]]; then
                echo "Available components: cucm, uccx, tgw, sbc, cms, imp, meeting_place, expressway, redis, config"
                echo "Usage: $0 list <component>"
                exit 1
            fi
            
            list_available_backups "$component"
            ;;
        "full")
            log_error "Full system restore is not implemented. Please restore components individually."
            echo "Usage: $0 database <component> [backup_file]"
            echo "       $0 redis [backup_file]"
            echo "       $0 config [backup_file]"
            echo "       $0 list <component>"
            exit 1
            ;;
        "help"|*)
            echo "Cisco Telephony Monitoring System - Restore Script"
            echo ""
            echo "Usage: $0 <action> [component] [backup_file]"
            echo ""
            echo "Actions:"
            echo "  database <component> [backup_file]  - Restore specific database"
            echo "  redis [backup_file]                   - Restore Redis data"
            echo "  config [backup_file]                  - Restore configuration files"
            echo "  list <component>                      - List available backups"
            echo "  help                                  - Show this help"
            echo ""
            echo "Components:"
            echo "  cucm, uccx, tgw, sbc, cms, imp, meeting_place, expressway, redis, config"
            echo ""
            echo "Examples:"
            echo "  $0 database cucm                       - Interactive CUCM database restore"
            echo "  $0 database cucm cucm_backup_20240301.sql.gz - Restore specific backup"
            echo "  $0 redis                               - Interactive Redis restore"
            echo "  $0 config                              - Interactive configuration restore"
            echo "  $0 list cucm                           - List CUCM backups"
            exit 0
            ;;
    esac
}

# Execute main function
main "$@"
