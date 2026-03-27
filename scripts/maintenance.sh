#!/bin/bash
# =========================================================================
# PRODUCTION MAINTENANCE SCRIPT
# Cisco Telephony Monitoring System
# =========================================================================

set -euo pipefail

# =========================================================================
# CONFIGURATION
# =========================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_DIR}/config/.env.production"
LOG_FILE="${PROJECT_DIR}/logs/maintenance.log"

# Load configuration
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    echo "ERROR: Configuration file not found: $CONFIG_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

# Maintenance settings
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-telephony-monitoring-prod}"

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

get_service_status() {
    local service="$1"
    local status=$(docker-compose -f "$PROJECT_DIR/config/$COMPOSE_FILE" ps -q "$service" 2>/dev/null | xargs docker inspect --format='{{.State.Status}}' 2>/dev/null || echo "not_found")
    echo "$status"
}

wait_for_service() {
    local service="$1"
    local max_wait="$2"
    local wait_interval="$3"
    
    log "Waiting for service $service to be healthy..."
    
    local wait_count=0
    while [[ $wait_count -lt $max_wait ]]; do
        local status=$(get_service_status "$service")
        
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

# =========================================================================
# LOG ROTATION FUNCTIONS
# =========================================================================
rotate_logs() {
    log "Starting log rotation"
    
    local log_dirs=(
        "$PROJECT_DIR/logs/proxy-gateway"
        "$PROJECT_DIR/logs/axlerate"
        "$PROJECT_DIR/logs/mock-server"
        "$PROJECT_DIR/logs/redis"
        "$PROJECT_DIR/logs/postgres/cucm"
        "$PROJECT_DIR/logs/postgres/uccx"
        "$PROJECT_DIR/logs/postgres/tgw"
        "$PROJECT_DIR/logs/postgres/sbc"
        "$PROJECT_DIR/logs/postgres/cms"
        "$PROJECT_DIR/logs/postgres/imp"
        "$PROJECT_DIR/logs/postgres/meeting_place"
        "$PROJECT_DIR/logs/postgres/expressway"
    )
    
    for log_dir in "${log_dirs[@]}"; do
        if [[ -d "$log_dir" ]]; then
            log "Rotating logs in: $log_dir"
            
            # Rotate application logs
            find "$log_dir" -name "*.log" -type f -mtime +7 -exec gzip {} \; 2>/dev/null || true
            find "$log_dir" -name "*.log.gz" -type f -mtime +30 -delete 2>/dev/null || true
            
            # Rotate Docker logs
            find "$log_dir" -name "*.log.*" -type f -mtime +7 -delete 2>/dev/null || true
        fi
    done
    
    # Rotate main log files
    find "$PROJECT_DIR/logs" -name "*.log" -type f -mtime +7 -exec gzip {} \; 2>/dev/null || true
    find "$PROJECT_DIR/logs" -name "*.log.gz" -type f -mtime +30 -delete 2>/dev/null || true
    
    log_success "Log rotation completed"
}

# =========================================================================
# DATABASE MAINTENANCE FUNCTIONS
# =========================================================================
maintain_database() {
    local container="$1"
    local database="$2"
    local user="$3"
    
    log "Performing maintenance on database: $database"
    
    # Check if container is running
    local status=$(get_service_status "$(echo "$container" | sed 's/telephony-//g' | sed 's/-prod//g')")
    if [[ "$status" != "running" && "$status" != "healthy" ]]; then
        log_warning "Container $container is not running (status: $status), skipping maintenance"
        return 0
    fi
    
    # Vacuum and analyze tables
    log "Vacuuming and analyzing tables in $database"
    docker exec "$container" psql -U "$user" -d "$database" -c "VACUUM ANALYZE;" 2>> "$LOG_FILE" || {
        log_error "Failed to vacuum database $database"
        return 1
    }
    
    # Update table statistics
    log "Updating statistics for $database"
    docker exec "$container" psql -U "$user" -d "$database" -c "ANALYZE;" 2>> "$LOG_FILE" || {
        log_error "Failed to analyze database $database"
        return 1
    }
    
    # Reindex if needed
    log "Checking for index maintenance in $database"
    docker exec "$container" psql -U "$user" -d "$database" -c "
        SELECT schemaname, tablename, attname, n_distinct, correlation 
        FROM pg_stats 
        WHERE schemaname = 'public' 
        ORDER BY tablename, attname;
    " 2>> "$LOG_FILE" || true
    
    # Check database size
    local db_size=$(docker exec "$container" psql -U "$user" -d "$database" -t -c "
        SELECT pg_size_pretty(pg_database_size('$database'));
    " 2>> "$LOG_FILE" | xargs || echo "unknown")
    
    log "Database $database size: $db_size"
    
    log_success "Database maintenance completed: $database"
    return 0
}

maintain_all_databases() {
    log "Starting maintenance for all databases"
    
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
        
        if maintain_database "$container" "$database" "$user"; then
            ((success_count++))
        fi
    done
    
    log "Database maintenance completed: ${success_count}/${total_count} databases maintained successfully"
    
    if [[ $success_count -eq $total_count ]]; then
        return 0
    else
        return 1
    fi
}

# =========================================================================
# REDIS MAINTENANCE FUNCTIONS
# =========================================================================
maintain_redis() {
    log "Performing Redis maintenance"
    
    local container="telephony-redis-prod"
    local status=$(get_service_status "redis")
    
    if [[ "$status" != "running" && "$status" != "healthy" ]]; then
        log_warning "Redis container is not running (status: $status), skipping maintenance"
        return 0
    fi
    
    # Get Redis info
    local redis_info=$(docker exec "$container" redis-cli INFO server 2>> "$LOG_FILE" || echo "")
    local redis_version=$(echo "$redis_info" | grep "redis_version:" | cut -d: -f2 | tr -d '\r' || echo "unknown")
    local uptime=$(echo "$redis_info" | grep "uptime_in_seconds:" | cut -d: -f2 | tr -d '\r' || echo "unknown")
    local used_memory=$(echo "$redis_info" | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r' || echo "unknown")
    
    log "Redis version: $redis_version, uptime: ${uptime}s, memory: $used_memory"
    
    # Check memory usage
    local max_memory=$(docker exec "$container" redis-cli CONFIG GET maxmemory 2>> "$LOG_FILE" | tail -1 || echo "0")
    if [[ "$max_memory" != "0" ]]; then
        local memory_usage_percent=$(docker exec "$container" redis-cli INFO memory 2>> "$LOG_FILE" | grep "used_memory:" | cut -d: -f2 | tr -d '\r' || echo "0")
        if [[ "$memory_usage_percent" != "0" && "$max_memory" != "0" ]]; then
            local usage_percent=$((memory_usage_percent * 100 / max_memory))
            log "Redis memory usage: ${usage_percent}%"
            
            if [[ $usage_percent -gt 80 ]]; then
                log_warning "Redis memory usage is high (${usage_percent}%)"
                
                # Trigger memory cleanup
                log "Triggering Redis memory cleanup"
                docker exec "$container" redis-cli MEMORY PURGE 2>> "$LOG_FILE" || true
            fi
        fi
    fi
    
    # Check key expiration
    local expired_keys=$(docker exec "$container" redis-cli INFO stats 2>> "$LOG_FILE" | grep "expired_keys:" | cut -d: -f2 | tr -d '\r' || echo "0")
    log "Expired keys: $expired_keys"
    
    # Save current data
    log "Saving Redis data"
    docker exec "$container" redis-cli SAVE 2>> "$LOG_FILE" || {
        log_error "Failed to save Redis data"
        return 1
    }
    
    log_success "Redis maintenance completed"
    return 0
}

# =========================================================================
# CACHE CLEANUP FUNCTIONS
# =========================================================================
cleanup_cache() {
    log "Starting cache cleanup"
    
    local container="telephony-redis-prod"
    local status=$(get_service_status "redis")
    
    if [[ "$status" != "running" && "$status" != "healthy" ]]; then
        log_warning "Redis container is not running (status: $status), skipping cache cleanup"
        return 0
    fi
    
    # Get cache info before cleanup
    local cache_info=$(docker exec "$container" redis-cli INFO memory 2>> "$LOG_FILE" || echo "")
    local used_memory_before=$(echo "$cache_info" | grep "used_memory:" | cut -d: -f2 | tr -d '\r' || echo "0")
    local key_count_before=$(docker exec "$container" redis-cli DBSIZE 2>> "$LOG_FILE" || echo "0")
    
    log "Cache before cleanup: $key_count_before keys, $((used_memory_before / 1024 / 1024))MB memory"
    
    # Clean expired keys
    log "Cleaning expired keys"
    docker exec "$container" redis-cli --scan --pattern "*" | head -1000 | xargs -r docker exec "$container" redis-cli DEL 2>> "$LOG_FILE" || true
    
    # Flush if explicitly requested
    if [[ "${1:-}" == "flush" ]]; then
        log "Flushing all cache data"
        docker exec "$container" redis-cli FLUSHDB 2>> "$LOG_FILE" || {
            log_error "Failed to flush Redis cache"
            return 1
        }
    fi
    
    # Get cache info after cleanup
    local cache_info_after=$(docker exec "$container" redis-cli INFO memory 2>> "$LOG_FILE" || echo "")
    local used_memory_after=$(echo "$cache_info_after" | grep "used_memory:" | cut -d: -f2 | tr -d '\r' || echo "0")
    local key_count_after=$(docker exec "$container" redis-cli DBSIZE 2>> "$LOG_FILE" || echo "0")
    
    log "Cache after cleanup: $key_count_after keys, $((used_memory_after / 1024 / 1024))MB memory"
    
    local memory_freed=$((used_memory_before - used_memory_after))
    local keys_removed=$((key_count_before - key_count_after))
    
    log_success "Cache cleanup completed: ${keys_removed} keys removed, $((memory_freed / 1024 / 1024))MB freed"
    return 0
}

# =========================================================================
# HEALTH CHECK FUNCTIONS
# =========================================================================
check_service_health() {
    local service="$1"
    local url="$2"
    local timeout="${3:-10}"
    
    log "Checking health of service: $service"
    
    if curl -f -s --max-time "$timeout" "$url" > /dev/null 2>&1; then
        log_success "Service $service is healthy"
        return 0
    else
        log_error "Service $service is unhealthy"
        return 1
    fi
}

check_all_services_health() {
    log "Starting comprehensive health check"
    
    local services=(
        "Proxy Gateway:http://localhost:8000/health"
        "Mock Server:http://localhost:8001/health"
        "AXLerate:http://localhost:8002/health"
    )
    
    local healthy_count=0
    local total_count=${#services[@]}
    
    for service_info in "${services[@]}"; do
        IFS=':' read -r service url <<< "$service_info"
        
        if check_service_health "$service" "$url"; then
            ((healthy_count++))
        fi
    done
    
    # Check Docker containers
    log "Checking Docker container health"
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
    
    local container_healthy_count=0
    local container_total_count=${#containers[@]}
    
    for container in "${containers[@]}"; do
        local status=$(get_service_status "$container")
        
        if [[ "$status" == "healthy" ]]; then
            log_success "Container $container is healthy"
            ((container_healthy_count++))
        elif [[ "$status" == "running" ]]; then
            log_warning "Container $container is running but not healthy"
        else
            log_error "Container $container is not healthy (status: $status)"
        fi
    done
    
    log "Health check completed: ${healthy_count}/${total_count} services healthy, ${container_healthy_count}/${container_total_count} containers healthy"
    
    if [[ $healthy_count -eq $total_count && $container_healthy_count -eq $container_total_count ]]; then
        return 0
    else
        return 1
    fi
}

# =========================================================================
# SYSTEM CLEANUP FUNCTIONS
# =========================================================================
cleanup_docker() {
    log "Starting Docker cleanup"
    
    # Remove stopped containers
    local stopped_containers=$(docker ps -aq --filter "status=exited" 2>/dev/null || echo "")
    if [[ -n "$stopped_containers" ]]; then
        log "Removing stopped containers"
        echo "$stopped_containers" | xargs docker rm 2>> "$LOG_FILE" || true
    fi
    
    # Remove unused images
    log "Removing unused Docker images"
    docker image prune -f 2>> "$LOG_FILE" || true
    
    # Remove unused networks
    log "Removing unused Docker networks"
    docker network prune -f 2>> "$LOG_FILE" || true
    
    # Cleanup build cache
    log "Cleaning Docker build cache"
    docker builder prune -f 2>> "$LOG_FILE" || true
    
    log_success "Docker cleanup completed"
}

cleanup_system() {
    log "Starting system cleanup"
    
    # Clean temporary files
    log "Cleaning temporary files"
    find /tmp -name "*.tmp" -mtime +1 -delete 2>/dev/null || true
    find "$PROJECT_DIR" -name "*.pyc" -delete 2>/dev/null || true
    find "$PROJECT_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # Clean old backups (older than retention period)
    local backup_retention_days="${BACKUP_RETENTION_DAYS:-30}"
    log "Cleaning backups older than ${backup_retention_days} days"
    find "$PROJECT_DIR/backups" -name "*_backup_*" -mtime "+${backup_retention_days}" -delete 2>/dev/null || true
    
    log_success "System cleanup completed"
}

# =========================================================================
# SERVICE RESTART FUNCTIONS
# =========================================================================
restart_service() {
    local service="$1"
    
    log "Restarting service: $service"
    
    if docker-compose -f "$PROJECT_DIR/config/$COMPOSE_FILE" restart "$service" 2>> "$LOG_FILE"; then
        log_success "Service $service restarted successfully"
        
        # Wait for service to be healthy
        case "$service" in
            "proxy-gateway")
                wait_for_service "proxy-gateway" 60 5
                ;;
            "mock-server")
                wait_for_service "mock-server" 30 5
                ;;
            "axlerate")
                wait_for_service "axlerate" 60 5
                ;;
            "redis")
                wait_for_service "redis" 30 5
                ;;
        esac
        
        return 0
    else
        log_error "Failed to restart service: $service"
        return 1
    fi
}

restart_all_services() {
    log "Restarting all services"
    
    if docker-compose -f "$PROJECT_DIR/config/$COMPOSE_FILE" restart 2>> "$LOG_FILE"; then
        log_success "All services restarted successfully"
        
        # Wait for critical services
        wait_for_service "redis" 30 5
        wait_for_service "cucm-postgres" 60 5
        wait_for_service "proxy-gateway" 60 5
        
        return 0
    else
        log_error "Failed to restart all services"
        return 1
    fi
}

# =========================================================================
# PERFORMANCE MONITORING FUNCTIONS
# =========================================================================
monitor_performance() {
    log "Starting performance monitoring"
    
    # Get system metrics
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 || echo "0")
    local memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}' || echo "0")
    local disk_usage=$(df -h "$PROJECT_DIR" | tail -1 | awk '{print $5}' | sed 's/%//' || echo "0")
    
    log "System performance - CPU: ${cpu_usage}%, Memory: ${memory_usage}%, Disk: ${disk_usage}%"
    
    # Get Docker stats
    log "Docker container performance:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>> "$LOG_FILE" || true
    
    # Check database performance
    local databases=(
        "telephony-cucm-postgres-prod:cucm_db:telephony_user"
        "telephony-uccx-postgres-prod:uccx_db:telephony_user"
    )
    
    for db_info in "${databases[@]}"; do
        IFS=':' read -r container database user <<< "$db_info"
        
        local status=$(get_service_status "$(echo "$container" | sed 's/telephony-//g' | sed 's/-prod//g')")
        if [[ "$status" == "running" || "$status" == "healthy" ]]; then
            local connections=$(docker exec "$container" psql -U "$user" -d "$database" -t -c "SELECT count(*) FROM pg_stat_activity;" 2>> "$LOG_FILE" | xargs || echo "0")
            local db_size=$(docker exec "$container" psql -U "$user" -d "$database" -t -c "SELECT pg_size_pretty(pg_database_size('$database'));" 2>> "$LOG_FILE" | xargs || echo "unknown")
            
            log "Database $database: $connections connections, size: $db_size"
        fi
    done
    
    log_success "Performance monitoring completed"
}

# =========================================================================
# MAIN EXECUTION
# =========================================================================
main() {
    local action="${1:-help}"
    
    # Check prerequisites
    check_docker
    check_docker_compose
    
    case "$action" in
        "logs")
            rotate_logs
            ;;
        "database")
            maintain_all_databases
            ;;
        "redis")
            maintain_redis
            ;;
        "cache")
            cleanup_cache "${2:-}"
            ;;
        "health")
            check_all_services_health
            ;;
        "docker")
            cleanup_docker
            ;;
        "system")
            cleanup_system
            ;;
        "restart")
            if [[ -n "${2:-}" ]]; then
                restart_service "$2"
            else
                restart_all_services
            fi
            ;;
        "performance")
            monitor_performance
            ;;
        "all")
            log "Starting comprehensive maintenance"
            rotate_logs
            maintain_all_databases
            maintain_redis
            cleanup_cache
            check_all_services_health
            cleanup_docker
            cleanup_system
            monitor_performance
            log_success "Comprehensive maintenance completed"
            ;;
        "help"|*)
            echo "Cisco Telephony Monitoring System - Maintenance Script"
            echo ""
            echo "Usage: $0 <action> [options]"
            echo ""
            echo "Actions:"
            echo "  logs                    - Rotate log files"
            echo "  database                - Maintain all databases"
            echo "  redis                   - Maintain Redis"
            echo "  cache [flush]           - Clean cache (add 'flush' to clear all)"
            echo "  health                  - Check all service health"
            echo "  docker                  - Clean Docker resources"
            echo "  system                  - Clean system resources"
            echo "  restart [service]       - Restart service(s)"
            echo "  performance             - Monitor performance"
            echo "  all                     - Run all maintenance tasks"
            echo "  help                    - Show this help"
            echo ""
            echo "Services for restart:"
            echo "  proxy-gateway, mock-server, axlerate, redis, cucm-postgres, uccx-postgres, etc."
            echo ""
            echo "Examples:"
            echo "  $0 all                  - Run comprehensive maintenance"
            echo "  $0 database             - Maintain databases only"
            echo "  $0 cache flush          - Clear all cache"
            echo "  $0 restart proxy-gateway - Restart specific service"
            echo "  $0 performance           - Monitor system performance"
            exit 0
            ;;
    esac
}

# Execute main function
main "$@"
