#!/bin/bash
# =========================================================================
# PRODUCTION DEPLOYMENT SCRIPT
# Cisco Telephony Monitoring System
# =========================================================================

set -euo pipefail

# =========================================================================
# CONFIGURATION
# =========================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_DIR}/config/.env.production"
LOG_FILE="${PROJECT_DIR}/logs/deploy.log"

# Deployment settings
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-telephony-monitoring-prod}"
DEPLOYMENT_TIMEOUT="${DEPLOYMENT_TIMEOUT:-300}"

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
check_prerequisites() {
    log "Checking deployment prerequisites"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check configuration file
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Production configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    # Check Docker Compose file
    local compose_file="$PROJECT_DIR/config/$COMPOSE_FILE"
    if [[ ! -f "$compose_file" ]]; then
        log_error "Docker Compose file not found: $compose_file"
        exit 1
    fi
    
    # Check system resources
    local available_memory=$(free -m | awk 'NR==2{print $7}')
    local required_memory=8192  # 8GB minimum
    
    if [[ $available_memory -lt $required_memory ]]; then
        log_warning "Available memory (${available_memory}MB) is less than recommended (${required_memory}MB)"
    fi
    
    local available_disk=$(df -BG "$PROJECT_DIR" | tail -1 | awk '{print $4}' | sed 's/G//')
    local required_disk=50  # 50GB minimum
    
    if [[ $available_disk -lt $required_disk ]]; then
        log_warning "Available disk space (${available_disk}GB) is less than recommended (${required_disk}GB)"
    fi
    
    log_success "Prerequisites check completed"
}

validate_configuration() {
    log "Validating configuration"
    
    # Load configuration
    source "$CONFIG_FILE"
    
    # Validate required variables
    local required_vars=(
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "CUCM_HOST"
        "CUCM_USERNAME"
        "CUCM_PASSWORD"
        "UCCX_HOST"
        "UCCX_USERNAME"
        "UCCX_PASSWORD"
        "SECRET_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required configuration variable not set: $var"
            exit 1
        fi
    done
    
    # Validate IP addresses
    local ip_vars=("CUCM_HOST" "UCCX_HOST" "TGW_HOST" "SBC_HOST")
    for var in "${ip_vars[@]}"; do
        local ip="${!var:-}"
        if [[ -n "$ip" ]]; then
            if ! [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                log_error "Invalid IP address for $var: $ip"
                exit 1
            fi
        fi
    done
    
    # Validate secret key
    if [[ ${#SECRET_KEY} -lt 32 ]]; then
        log_error "SECRET_KEY must be at least 32 characters"
        exit 1
    fi
    
    log_success "Configuration validation completed"
}

backup_current_deployment() {
    log "Creating backup of current deployment"
    
    # Stop current services
    log "Stopping current services"
    docker-compose -f "$PROJECT_DIR/config/$COMPOSE_FILE" down 2>> "$LOG_FILE" || true
    
    # Create backup
    local backup_dir="$PROJECT_DIR/backups/deployment_backup_$(date '+%Y%m%d_%H%M%S')"
    mkdir -p "$backup_dir"
    
    # Backup configuration
    cp -r "$PROJECT_DIR/config" "$backup_dir/"
    
    # Backup databases if they exist
    local containers=(
        "telephony-cucm-postgres-prod:cucm_db:telephony_user"
        "telephony-uccx-postgres-prod:uccx_db:telephony_user"
        "telephony-tgw-postgres-prod:tgw_db:telephony_user"
        "telephony-sbc-postgres-prod:sbc_db:telephony_user"
    )
    
    for container_info in "${containers[@]}"; do
        IFS=':' read -r container database user <<< "$container_info"
        
        if docker ps -q --filter "name=$container" | grep -q .; then
            log "Backing up database: $database"
            local backup_file="$backup_dir/${database}_backup.sql"
            
            if docker exec "$container" pg_dump -U "$user" -d "$database" --no-password --format=custom > "$backup_file" 2>> "$LOG_FILE"; then
                log_success "Database backup created: $database"
            else
                log_warning "Failed to backup database: $database"
            fi
        fi
    done
    
    log_success "Deployment backup created: $backup_dir"
    echo "$backup_dir"
}

wait_for_service() {
    local service="$1"
    local max_wait="$2"
    local wait_interval="$3"
    
    log "Waiting for service $service to be healthy..."
    
    local wait_count=0
    while [[ $wait_count -lt $max_wait ]]; do
        local status=$(docker-compose -f "$PROJECT_DIR/config/$COMPOSE_FILE" ps -q "$service" 2>/dev/null | xargs docker inspect --format='{{.State.Status}}' 2>/dev/null || echo "not_found")
        
        if [[ "$status" == "healthy" ]]; then
            log_success "Service $service is healthy"
            return 0
        elif [[ "$status" == "running" ]]; then
            log "Service $service is running (waiting for health check)..."
        elif [[ "$status" == "not_found" ]]; then
            log_error "Service $service not found"
            return 1
        else
            log "Service $service status: $status"
        fi
        
        sleep "$wait_interval"
        ((wait_count++))
    done
    
    log_error "Service $service did not become healthy within ${max_wait}s"
    return 1
}

check_service_health() {
    local service="$1"
    local url="$2"
    local timeout="${3:-10}"
    
    log "Checking health of service: $service"
    
    local retry_count=0
    local max_retries=30
    
    while [[ $retry_count -lt $max_retries ]]; do
        if curl -f -s --max-time "$timeout" "$url" > /dev/null 2>&1; then
            log_success "Service $service is healthy"
            return 0
        fi
        
        sleep 5
        ((retry_count++))
    done
    
    log_error "Service $service is unhealthy"
    return 1
}

# =========================================================================
# DEPLOYMENT FUNCTIONS
# =========================================================================
build_images() {
    log "Building Docker images"
    
    local compose_file="$PROJECT_DIR/config/$COMPOSE_FILE"
    
    # Build images with no cache for fresh build
    if docker-compose -f "$compose_file" build --no-cache 2>> "$LOG_FILE"; then
        log_success "Docker images built successfully"
    else
        log_error "Failed to build Docker images"
        exit 1
    fi
}

start_services() {
    log "Starting services"
    
    local compose_file="$PROJECT_DIR/config/$COMPOSE_FILE"
    
    # Start services
    if docker-compose -f "$compose_file" up -d 2>> "$LOG_FILE"; then
        log_success "Services started successfully"
    else
        log_error "Failed to start services"
        exit 1
    fi
    
    # Wait for critical services
    log "Waiting for critical services to be healthy"
    
    # Wait for databases first
    wait_for_service "cucm-postgres" 120 10
    wait_for_service "uccx-postgres" 120 10
    wait_for_service "redis" 60 5
    
    # Wait for application services
    wait_for_service "proxy-gateway" 120 10
    wait_for_service "mock-server" 60 5
    wait_for_service "axlerate" 120 10
}

verify_deployment() {
    log "Verifying deployment"
    
    local services_healthy=0
    local total_services=0
    
    # Check service health endpoints
    local health_checks=(
        "Proxy Gateway:http://localhost:8000/health"
        "Mock Server:http://localhost:8001/health"
        "AXLerate:http://localhost:8002/health"
    )
    
    for service_info in "${health_checks[@]}"; do
        IFS=':' read -r service url <<< "$service_info"
        ((total_services++))
        
        if check_service_health "$service" "$url"; then
            ((services_healthy++))
        fi
    done
    
    # Check container health
    local containers_healthy=0
    local total_containers=0
    
    local containers=(
        "proxy-gateway"
        "mock-server"
        "axlerate"
        "redis"
        "cucm-postgres"
        "uccx-postgres"
        "tgw-postgres"
        "sbc-postgres"
    )
    
    for container in "${containers[@]}"; do
        ((total_containers++))
        
        local status=$(docker-compose -f "$PROJECT_DIR/config/$COMPOSE_FILE" ps -q "$container" 2>/dev/null | xargs docker inspect --format='{{.State.Status}}' 2>/dev/null || echo "not_found")
        
        if [[ "$status" == "healthy" ]]; then
            ((containers_healthy++))
            log_success "Container $container is healthy"
        elif [[ "$status" == "running" ]]; then
            log_warning "Container $container is running but not healthy"
        else
            log_error "Container $container is not healthy (status: $status)"
        fi
    done
    
    # Test API endpoints
    log "Testing API endpoints"
    
    # Test Proxy Gateway
    if curl -f -s "http://localhost:8000/api/metrics/summary" > /dev/null 2>&1; then
        log_success "Proxy Gateway API is working"
    else
        log_warning "Proxy Gateway API test failed"
    fi
    
    # Test Mock Server
    if curl -f -s "http://localhost:8001/api/cucm/system/stats" > /dev/null 2>&1; then
        log_success "Mock Server API is working"
    else
        log_warning "Mock Server API test failed"
    fi
    
    # Test AXLerate
    if curl -f -s "http://localhost:8002/sdk/info" > /dev/null 2>&1; then
        log_success "AXLerate API is working"
    else
        log_warning "AXLerate API test failed"
    fi
    
    log "Deployment verification completed: ${services_healthy}/${total_services} services healthy, ${containers_healthy}/${total_containers} containers healthy"
    
    if [[ $services_healthy -eq $total_services && $containers_healthy -eq $total_containers ]]; then
        return 0
    else
        return 1
    fi
}

run_post_deployment_tests() {
    log "Running post-deployment tests"
    
    # Test database connectivity
    log "Testing database connectivity"
    
    local databases=(
        "telephony-cucm-postgres-prod:cucm_db:telephony_user"
        "telephony-uccx-postgres-prod:uccx_db:telephony_user"
    )
    
    for db_info in "${databases[@]}"; do
        IFS=':' read -r container database user <<< "$db_info"
        
        if docker exec "$container" psql -U "$user" -d "$database" -c "SELECT 1;" > /dev/null 2>&1; then
            log_success "Database $database is accessible"
        else
            log_error "Database $database is not accessible"
            return 1
        fi
    done
    
    # Test Redis connectivity
    log "Testing Redis connectivity"
    
    if docker exec "telephony-redis-prod" redis-cli ping > /dev/null 2>&1; then
        log_success "Redis is accessible"
    else
        log_error "Redis is not accessible"
        return 1
    fi
    
    # Test data collection
    log "Testing data collection"
    
    # Trigger manual data collection
    if curl -f -s -X POST "http://localhost:8000/api/collect" > /dev/null 2>&1; then
        log_success "Data collection test passed"
    else
        log_warning "Data collection test failed"
    fi
    
    log_success "Post-deployment tests completed"
}

# =========================================================================
# ROLLBACK FUNCTIONS
# =========================================================================
rollback_deployment() {
    local backup_dir="$1"
    
    log "Starting rollback from backup: $backup_dir"
    
    if [[ ! -d "$backup_dir" ]]; then
        log_error "Backup directory not found: $backup_dir"
        exit 1
    fi
    
    # Stop current services
    log "Stopping current services"
    docker-compose -f "$PROJECT_DIR/config/$COMPOSE_FILE" down 2>> "$LOG_FILE" || true
    
    # Restore configuration
    log "Restoring configuration"
    if [[ -d "$backup_dir/config" ]]; then
        cp -r "$backup_dir/config"/* "$PROJECT_DIR/config/"
        log_success "Configuration restored"
    fi
    
    # Restore databases
    local database_backups=$(find "$backup_dir" -name "*_backup.sql" 2>/dev/null || true)
    
    for backup_file in $database_backups; do
        local database=$(basename "$backup_file" | sed 's/_backup.sql//')
        
        log "Restoring database: $database"
        
        case "$database" in
            "cucm_db")
                docker-compose -f "$PROJECT_DIR/config/$COMPOSE_FILE" up -d cucm-postgres
                wait_for_service "cucm-postgres" 60 5
                docker exec "telephony-cucm-postgres-prod" psql -U telephony_user -c "DROP DATABASE IF EXISTS cucm_db;" 2>> "$LOG_FILE" || true
                docker exec "telephony-cucm-postgres-prod" psql -U telephony_user -c "CREATE DATABASE cucm_db;" 2>> "$LOG_FILE" || true
                docker exec -i "telephony-cucm-postgres-prod" pg_restore -U telephony_user -d cucm_db --clean --if-exists < "$backup_file" 2>> "$LOG_FILE" || true
                ;;
            "uccx_db")
                docker-compose -f "$PROJECT_DIR/config/$COMPOSE_FILE" up -d uccx-postgres
                wait_for_service "uccx-postgres" 60 5
                docker exec "telephony-uccx-postgres-prod" psql -U telephony_user -c "DROP DATABASE IF EXISTS uccx_db;" 2>> "$LOG_FILE" || true
                docker exec "telephony-uccx-postgres-prod" psql -U telephony_user -c "CREATE DATABASE uccx_db;" 2>> "$LOG_FILE" || true
                docker exec -i "telephony-uccx-postgres-prod" pg_restore -U telephony_user -d uccx_db --clean --if-exists < "$backup_file" 2>> "$LOG_FILE" || true
                ;;
        esac
        
        log_success "Database $database restored"
    done
    
    # Start all services
    log "Starting services after rollback"
    docker-compose -f "$PROJECT_DIR/config/$COMPOSE_FILE" up -d 2>> "$LOG_FILE"
    
    # Wait for services
    wait_for_service "redis" 60 5
    wait_for_service "cucm-postgres" 60 5
    wait_for_service "proxy-gateway" 120 10
    
    log_success "Rollback completed"
}

# =========================================================================
# MAIN DEPLOYMENT FUNCTION
# =========================================================================
deploy() {
    local skip_backup="${1:-false}"
    
    log "Starting production deployment"
    local start_time=$(date +%s)
    
    # Check prerequisites
    check_prerequisites
    
    # Validate configuration
    validate_configuration
    
    # Create backup unless skipped
    local backup_dir=""
    if [[ "$skip_backup" != "true" ]]; then
        backup_dir=$(backup_current_deployment)
    fi
    
    # Build images
    build_images
    
    # Start services
    start_services
    
    # Verify deployment
    if verify_deployment; then
        # Run post-deployment tests
        run_post_deployment_tests
        
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log_success "Deployment completed successfully in ${duration} seconds"
        
        if [[ -n "$backup_dir" ]]; then
            log "Backup available at: $backup_dir"
        fi
        
        return 0
    else
        log_error "Deployment verification failed"
        
        # Attempt rollback if backup exists
        if [[ -n "$backup_dir" ]]; then
            log "Attempting rollback..."
            rollback_deployment "$backup_dir"
        fi
        
        return 1
    fi
}

# =========================================================================
# MAIN EXECUTION
# =========================================================================
main() {
    local action="${1:-deploy}"
    local option="${2:-}"
    
    case "$action" in
        "deploy")
            deploy "${option}"
            ;;
        "rollback")
            if [[ -z "$option" ]]; then
                log_error "Backup directory required for rollback"
                echo "Usage: $0 rollback <backup_directory>"
                exit 1
            fi
            rollback_deployment "$option"
            ;;
        "verify")
            verify_deployment
            ;;
        "test")
            run_post_deployment_tests
            ;;
        "status")
            docker-compose -f "$PROJECT_DIR/config/$COMPOSE_FILE" ps
            ;;
        "logs")
            if [[ -n "$option" ]]; then
                docker-compose -f "$PROJECT_DIR/config/$COMPOSE_FILE" logs -f "$option"
            else
                docker-compose -f "$PROJECT_DIR/config/$COMPOSE_FILE" logs
            fi
            ;;
        "stop")
            log "Stopping all services"
            docker-compose -f "$PROJECT_DIR/config/$COMPOSE_FILE" down
            ;;
        "restart")
            log "Restarting all services"
            docker-compose -f "$PROJECT_DIR/config/$COMPOSE_FILE" restart
            verify_deployment
            ;;
        "help"|*)
            echo "Cisco Telephony Monitoring System - Deployment Script"
            echo ""
            echo "Usage: $0 <action> [options]"
            echo ""
            echo "Actions:"
            echo "  deploy [skip-backup]    - Deploy the system (add 'skip-backup' to skip backup)"
            echo "  rollback <backup_dir>   - Rollback to previous deployment"
            echo "  verify                  - Verify current deployment"
            echo "  test                    - Run post-deployment tests"
            echo "  status                  - Show service status"
            echo "  logs [service]          - Show logs (all or specific service)"
            echo "  stop                    - Stop all services"
            echo "  restart                 - Restart all services"
            echo "  help                    - Show this help"
            echo ""
            echo "Examples:"
            echo "  $0 deploy               - Full deployment with backup"
            echo "  $0 deploy skip-backup   - Deployment without backup"
            echo "  $0 rollback /path/to/backup - Rollback to backup"
            echo "  $0 verify               - Verify current deployment"
            echo "  $0 logs proxy-gateway  - Show proxy-gateway logs"
            echo ""
            exit 0
            ;;
    esac
}

# Execute main function
main "$@"
