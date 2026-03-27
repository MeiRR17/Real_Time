#!/bin/bash
# =========================================================================
# PRODUCTION SETUP SCRIPT
# Cisco Telephony Monitoring System
# =========================================================================

set -euo pipefail

# =========================================================================
# CONFIGURATION
# =========================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_DIR}/config/.env.production"
LOG_FILE="${PROJECT_DIR/logs/setup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

# =========================================================================
# LOGGING FUNCTIONS
# =========================================================================
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# =========================================================================
# UTILITY FUNCTIONS
# =========================================================================
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        exit 1
    fi
}

check_command() {
    local cmd="$1"
    local package="${2:-$cmd}"
    
    if ! command -v "$cmd" &> /dev/null; then
        log_error "$cmd is not installed. Please install $package"
        return 1
    fi
    return 0
}

confirm_action() {
    local message="$1"
    local default="${2:-n}"
    
    echo -n -e "${YELLOW}$message [y/N]:${NC} "
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

create_directory() {
    local dir="$1"
    local permissions="${2:-755}"
    local owner="${3:-$USER:$USER}"
    
    if [[ ! -d "$dir" ]]; then
        sudo mkdir -p "$dir"
        sudo chmod "$permissions" "$dir"
        sudo chown "$owner" "$dir"
        log "Created directory: $dir"
    fi
}

create_file() {
    local file="$1"
    local content="$2"
    local permissions="${3:-644}"
    local owner="${4:-$USER:$USER}"
    
    if [[ ! -f "$file" ]]; then
        echo "$content" | sudo tee "$file" > /dev/null
        sudo chmod "$permissions" "$file"
        sudo chown "$owner" "$file"
        log "Created file: $file"
    fi
}

# =========================================================================
# SYSTEM CHECKS
# =========================================================================
check_system_requirements() {
    log "Checking system requirements"
    
    # Check operating system
    if [[ ! -f /etc/os-release ]]; then
        log_error "Cannot determine operating system"
        exit 1
    fi
    
    source /etc/os-release
    log "Operating system: $PRETTY_NAME"
    
    # Check if supported OS
    case "$ID" in
        ubuntu|debian)
            log "Supported operating system detected"
            ;;
        centos|rhel|fedora)
            log_warning "RHEL-based systems detected. Some commands may differ."
            ;;
        *)
            log_warning "Unsupported operating system: $ID"
            ;;
    esac
    
    # Check architecture
    local arch=$(uname -m)
    log "Architecture: $arch"
    
    if [[ "$arch" != "x86_64" ]]; then
        log_warning "Non-x86_64 architecture detected. Some features may not work."
    fi
    
    # Check memory
    local total_memory=$(free -m | awk 'NR==2{print $2}')
    local available_memory=$(free -m | awk 'NR==2{print $7}')
    
    log "Total memory: ${total_memory}MB"
    log "Available memory: ${available_memory}MB"
    
    if [[ $total_memory -lt 8192 ]]; then
        log_warning "System has less than 8GB RAM. Performance may be affected."
    fi
    
    # Check disk space
    local available_disk=$(df -BG "$PROJECT_DIR" | tail -1 | awk '{print $4}' | sed 's/G//')
    
    log "Available disk space: ${available_disk}GB"
    
    if [[ $available_disk -lt 50 ]]; then
        log_warning "Less than 50GB disk space available. Consider allocating more space."
    fi
    
    # Check CPU cores
    local cpu_cores=$(nproc)
    log "CPU cores: $cpu_cores"
    
    if [[ $cpu_cores -lt 4 ]]; then
        log_warning "System has less than 4 CPU cores. Performance may be affected."
    fi
    
    log_success "System requirements check completed"
}

check_dependencies() {
    log "Checking dependencies"
    
    local missing_deps=()
    
    # Check required commands
    local commands=(
        "curl:curl"
        "wget:wget"
        "git:git"
        "python3:python3"
        "pip3:python3-pip"
        "docker:docker.io"
        "docker-compose:docker-compose"
    )
    
    for cmd_info in "${commands[@]}"; do
        IFS=':' read -r cmd package <<< "$cmd_info"
        
        if ! check_command "$cmd" "$package"; then
            missing_deps+=("$package")
        fi
    done
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version | cut -d' ' -f2)
        local python_major=$(echo "$python_version" | cut -d'.' -f1)
        local python_minor=$(echo "$python_version" | cut -d'.' -f2)
        
        log "Python version: $python_version"
        
        if [[ $python_major -lt 3 ]] || [[ $python_major -eq 3 && $python_minor -lt 8 ]]; then
            log_error "Python 3.8 or higher is required"
            missing_deps+=("python3.8+")
        fi
    fi
    
    # Report missing dependencies
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        
        echo ""
        echo "To install missing dependencies on Ubuntu/Debian:"
        echo "  sudo apt update"
        echo "  sudo apt install -y ${missing_deps[*]}"
        echo ""
        echo "To install missing dependencies on CentOS/RHEL:"
        echo "  sudo yum install -y ${missing_deps[*]}"
        echo ""
        echo "To install Docker on Ubuntu/Debian:"
        echo "  curl -fsSL https://get.docker.com -o get-docker.sh"
        echo "  sudo sh get-docker.sh"
        echo "  sudo usermod -aG docker \$USER"
        echo ""
        
        exit 1
    fi
    
    log_success "All dependencies are installed"
}

check_docker() {
    log "Checking Docker configuration"
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        echo "Please start Docker daemon:"
        echo "  sudo systemctl start docker"
        echo "  sudo systemctl enable docker"
        exit 1
    fi
    
    # Check Docker version
    local docker_version=$(docker --version | cut -d' ' -f3 | sed 's/,//')
    log "Docker version: $docker_version"
    
    # Check if user can run Docker without sudo
    if ! docker ps &> /dev/null; then
        log_error "User cannot run Docker commands"
        echo "Please add user to docker group:"
        echo "  sudo usermod -aG docker \$USER"
        echo "  newgrp docker"
        echo "  (or log out and log back in)"
        exit 1
    fi
    
    # Check Docker Compose
    local compose_version=$(docker-compose --version | cut -d' ' -f3 | sed 's/,//')
    log "Docker Compose version: $compose_version"
    
    log_success "Docker configuration is correct"
}

# =========================================================================
# SETUP FUNCTIONS
# =========================================================================
setup_directories() {
    log "Setting up directory structure"
    
    local directories=(
        "$PROJECT_DIR/logs:755"
        "$PROJECT_DIR/backups:755"
        "$PROJECT_DIR/data:755"
        "$PROJECT_DIR/cache:755"
        "$PROJECT_DIR/keys:700"
        "$PROJECT_DIR/config:755"
        "$PROJECT_DIR/scripts:755"
        "$PROJECT_DIR/logs/proxy-gateway:755"
        "$PROJECT_DIR/logs/axlerate:755"
        "$PROJECT_DIR/logs/mock-server:755"
        "$PROJECT_DIR/logs/redis:755"
        "$PROJECT_DIR/logs/postgres:755"
        "$PROJECT_DIR/logs/postgres/cucm:755"
        "$PROJECT_DIR/logs/postgres/uccx:755"
        "$PROJECT_DIR/logs/postgres/tgw:755"
        "$PROJECT_DIR/logs/postgres/sbc:755"
        "$PROJECT_DIR/logs/postgres/cms:755"
        "$PROJECT_DIR/logs/postgres/imp:755"
        "$PROJECT_DIR/logs/postgres/meeting-place:755"
        "$PROJECT_DIR/logs/postgres/expressway:755"
    )
    
    for dir_info in "${directories[@]}"; do
        IFS=':' read -r dir permissions <<< "$dir_info"
        create_directory "$dir" "$permissions"
    done
    
    log_success "Directory structure created"
}

setup_configuration() {
    log "Setting up configuration files"
    
    # Check if production configuration exists
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Production configuration file not found: $CONFIG_FILE"
        echo "Please copy and configure:"
        echo "  cp config/.env.example config/.env.production"
        echo "Then edit config/.env.production with your settings"
        exit 1
    fi
    
    # Validate configuration
    source "$CONFIG_FILE"
    
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
            echo "Please edit $CONFIG_FILE and set the required variables"
            exit 1
        fi
    done
    
    log_success "Configuration files validated"
}

setup_ssh_keys() {
    log "Setting up SSH keys for SBC access"
    
    local keys_dir="$PROJECT_DIR/keys"
    local sbc_key="$keys_dir/sbc_key"
    local sbc_key_pub="$keys_dir/sbc_key.pub"
    
    if [[ ! -f "$sbc_key" ]]; then
        log "Generating SSH key for SBC access"
        ssh-keygen -t rsa -b 4096 -f "$sbc_key" -N "" -C "telephony-monitoring@sbc"
        
        chmod 600 "$sbc_key"
        chmod 644 "$sbc_key_pub"
        
        log_success "SSH key generated for SBC access"
        log "Public key: $sbc_key_pub"
        log "Add this key to your SBC's authorized_keys file"
    else
        log "SSH key already exists: $sbc_key"
    fi
}

setup_ssl_certificates() {
    log "Setting up SSL certificates"
    
    local certs_dir="$PROJECT_DIR/certs"
    
    create_directory "$certs_dir" 755
    
    local ca_key="$certs_dir/ca.key"
    local ca_cert="$certs_dir/ca.crt"
    local server_key="$certs_dir/server.key"
    local server_cert="$certs_dir/server.crt"
    local server_csr="$certs_dir/server.csr"
    
    # Generate CA certificate if not exists
    if [[ ! -f "$ca_key" ]]; then
        log "Generating CA certificate"
        openssl genrsa -out "$ca_key" 4096
        openssl req -new -x509 -days 3650 -key "$ca_key" -out "$ca_cert" \
            -subj "/C=US/ST=State/L=City/O=Telephony Monitoring/OU=IT/CN=Telephony CA"
        
        chmod 600 "$ca_key"
        chmod 644 "$ca_cert"
        
        log_success "CA certificate generated"
    fi
    
    # Generate server certificate if not exists
    if [[ ! -f "$server_key" ]]; then
        log "Generating server certificate"
        openssl genrsa -out "$server_key" 2048
        openssl req -new -key "$server_key" -out "$server_csr" \
            -subj "/C=US/ST=State/L=City/O=Telephony Monitoring/OU=IT/CN=localhost"
        
        # Sign server certificate with CA
        openssl x509 -req -in "$server_csr" -CA "$ca_cert" -CAkey "$ca_key" \
            -CAcreateserial -out "$server_cert" -days 365 -extensions v3_req \
            -extfile <(cat <<EOF
[v3_req]
subjectAltName = @alt_names
[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
IP.1 = 127.0.0.1
IP.2 = 0.0.0.0
EOF
        )
        
        chmod 600 "$server_key"
        chmod 644 "$server_cert"
        rm -f "$server_csr"
        
        log_success "Server certificate generated"
    fi
    
    log_success "SSL certificates setup completed"
}

setup_systemd_services() {
    log "Setting up systemd services"
    
    local service_file="/etc/systemd/system/telephony-monitoring.service"
    
    if [[ ! -f "$service_file" ]]; then
        log "Creating systemd service"
        
        cat <<EOF | sudo tee "$service_file" > /dev/null
[Unit]
Description=Cisco Telephony Monitoring System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/deploy.sh
ExecStop=$PROJECT_DIR/scripts/deploy.sh stop
ExecReload=$PROJECT_DIR/scripts/deploy.sh restart
TimeoutStartSec=300
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
EOF
        
        sudo systemctl daemon-reload
        sudo systemctl enable telephony-monitoring.service
        
        log_success "Systemd service created"
        log "To manage the service:"
        echo "  sudo systemctl start telephony-monitoring"
        echo "  sudo systemctl stop telephony-monitoring"
        echo "  sudo systemctl restart telephony-monitoring"
        echo "  sudo systemctl status telephony-monitoring"
    else
        log "Systemd service already exists"
    fi
}

setup_logrotate() {
    log "Setting up log rotation"
    
    local logrotate_config="/etc/logrotate.d/telephony-monitoring"
    
    if [[ ! -f "$logrotate_config" ]]; then
        log "Creating logrotate configuration"
        
        cat <<EOF | sudo tee "$logrotate_config" > /dev/null
$PROJECT_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        docker-compose -f $PROJECT_DIR/config/docker-compose.prod.yml restart proxy-gateway axlerate mock-server
    endscript
}

$PROJECT_DIR/logs/postgres/*/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
}

$PROJECT_DIR/logs/redis/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
}
EOF
        
        log_success "Logrotate configuration created"
    else
        log "Logrotate configuration already exists"
    fi
}

setup_cron_jobs() {
    log "Setting up cron jobs"
    
    local cron_file="$HOME/.telephony-cron"
    
    # Create temporary cron file
    cat <<EOF > "$cron_file"
# Cisco Telephony Monitoring System - Automated Tasks

# Backup every 6 hours
0 */6 * * * $PROJECT_DIR/scripts/backup.sh full >> $PROJECT_DIR/logs/cron-backup.log 2>&1

# Maintenance every day at 2 AM
0 2 * * * $PROJECT_DIR/scripts/maintenance.sh all >> $PROJECT_DIR/logs/cron-maintenance.log 2>&1

# Health check every 30 minutes
*/30 * * * * $PROJECT_DIR/scripts/maintenance.sh health >> $PROJECT_DIR/logs/cron-health.log 2>&1

# Log rotation every day at 1 AM
0 1 * * * $PROJECT_DIR/scripts/maintenance.sh logs >> $PROJECT_DIR/logs/cron-logs.log 2>&1

# Performance monitoring every hour
0 * * * * $PROJECT_DIR/scripts/maintenance.sh performance >> $PROJECT_DIR/logs/cron-performance.log 2>&1
EOF
    
    # Check if cron jobs already exist
    if crontab -l 2>/dev/null | grep -q "telephony-monitoring"; then
        log_warning "Cron jobs already exist"
        if confirm_action "Replace existing cron jobs?"; then
            # Remove existing telephony cron jobs
            crontab -l 2>/dev/null | grep -v "telephony-monitoring" | crontab -
            # Add new cron jobs
            (crontab -l 2>/dev/null; cat "$cron_file") | crontab -
            log_success "Cron jobs updated"
        fi
    else
        # Add new cron jobs
        (crontab -l 2>/dev/null; cat "$cron_file") | crontab -
        log_success "Cron jobs created"
    fi
    
    rm -f "$cron_file"
    
    log "Cron jobs configured:"
    echo "  - Backup: Every 6 hours"
    echo "  - Maintenance: Daily at 2 AM"
    echo "  - Health check: Every 30 minutes"
    echo "  - Log rotation: Daily at 1 AM"
    echo "  - Performance monitoring: Every hour"
}

setup_firewall() {
    log "Configuring firewall"
    
    # Check if UFW is available
    if command -v ufw &> /dev/null; then
        log "Configuring UFW firewall"
        
        # Allow required ports
        local ports=(
            "22/tcp:SSH"
            "8000/tcp:Proxy Gateway"
            "8001/tcp:Mock Server"
            "8002/tcp:AXLerate"
            "5432/tcp:PostgreSQL (internal)"
            "6379/tcp:Redis (internal)"
        )
        
        for port_info in "${ports[@]}"; do
            IFS=':' read -r port description <<< "$port_info"
            
            if ! sudo ufw status | grep -q "$port"; then
                sudo ufw allow "$port"
                log "Allowed port: $port ($description)"
            fi
        done
        
        # Enable UFW if not already enabled
        if ! sudo ufw status | grep -q "Status: active"; then
            if confirm_action "Enable UFW firewall?"; then
                sudo ufw --force enable
                log_success "UFW firewall enabled"
            fi
        fi
        
    elif command -v firewall-cmd &> /dev/null; then
        log "Configuring firewalld"
        
        # Check if firewalld is running
        if ! sudo systemctl is-active --quiet firewalld; then
            sudo systemctl start firewalld
            sudo systemctl enable firewalld
        fi
        
        # Allow required ports
        local ports=(
            "22/tcp:ssh"
            "8000/tcp:http"
            "8001/tcp:http"
            "8002/tcp:http"
        )
        
        for port_info in "${ports[@]}"; do
            IFS=':' read -r port service <<< "$port_info"
            
            if ! sudo firewall-cmd --list-ports | grep -q "$port"; then
                sudo firewall-cmd --permanent --add-port="$port"
                sudo firewall-cmd --reload
                log "Allowed port: $port"
            fi
        done
        
        log_success "Firewalld configured"
    else
        log_warning "No firewall management tool found (UFW or firewalld)"
        log "Please manually configure firewall to allow ports: 22, 8000, 8001, 8002"
    fi
}

# =========================================================================
# VALIDATION FUNCTIONS
# =========================================================================
validate_setup() {
    log "Validating setup"
    
    local validation_errors=0
    
    # Check directories
    local directories=(
        "$PROJECT_DIR/logs"
        "$PROJECT_DIR/backups"
        "$PROJECT_DIR/data"
        "$PROJECT_DIR/cache"
        "$PROJECT_DIR/keys"
        "$PROJECT_DIR/certs"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            log_error "Directory not found: $dir"
            ((validation_errors++))
        fi
    done
    
    # Check configuration files
    local config_files=(
        "$CONFIG_FILE"
        "$PROJECT_DIR/config/docker-compose.prod.yml"
        "$PROJECT_DIR/config/production.py"
        "$PROJECT_DIR/config/postgres.conf"
        "$PROJECT_DIR/config/redis.conf"
    )
    
    for file in "${config_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "Configuration file not found: $file"
            ((validation_errors++))
        fi
    done
    
    # Check scripts
    local scripts=(
        "$PROJECT_DIR/scripts/deploy.sh"
        "$PROJECT_DIR/scripts/backup.sh"
        "$PROJECT_DIR/scripts/restore.sh"
        "$PROJECT_DIR/scripts/maintenance.sh"
    )
    
    for script in "${scripts[@]}"; do
        if [[ ! -f "$script" ]]; then
            log_error "Script not found: $script"
            ((validation_errors++))
        elif [[ ! -x "$script" ]]; then
            chmod +x "$script"
            log "Made script executable: $script"
        fi
    done
    
    # Check SSH keys
    if [[ ! -f "$PROJECT_DIR/keys/sbc_key" ]]; then
        log_warning "SSH key for SBC not found"
    fi
    
    # Check SSL certificates
    if [[ ! -f "$PROJECT_DIR/certs/server.crt" ]]; then
        log_warning "SSL certificates not found"
    fi
    
    if [[ $validation_errors -eq 0 ]]; then
        log_success "Setup validation passed"
        return 0
    else
        log_error "Setup validation failed with $validation_errors errors"
        return 1
    fi
}

# =========================================================================
# MAIN SETUP FUNCTION
# =========================================================================
main() {
    local action="${1:-full}"
    
    echo -e "${BLUE}========================================================================${NC}"
    echo -e "${BLUE}Cisco Telephony Monitoring System - Production Setup${NC}"
    echo -e "${BLUE}========================================================================${NC}"
    echo ""
    
    case "$action" in
        "check")
            check_system_requirements
            check_dependencies
            check_docker
            ;;
        "directories")
            setup_directories
            ;;
        "config")
            setup_configuration
            ;;
        "ssh")
            setup_ssh_keys
            ;;
        "ssl")
            setup_ssl_certificates
            ;;
        "systemd")
            setup_systemd_services
            ;;
        "logrotate")
            setup_logrotate
            ;;
        "cron")
            setup_cron_jobs
            ;;
        "firewall")
            setup_firewall
            ;;
        "validate")
            validate_setup
            ;;
        "full")
            check_root
            
            log "Starting full production setup"
            
            # Run all setup steps
            check_system_requirements
            check_dependencies
            check_docker
            setup_directories
            setup_configuration
            setup_ssh_keys
            setup_ssl_certificates
            setup_systemd_services
            setup_logrotate
            setup_cron_jobs
            setup_firewall
            
            # Validate setup
            if validate_setup; then
                echo ""
                log_success "Production setup completed successfully!"
                echo ""
                echo -e "${GREEN}Next steps:${NC}"
                echo "1. Review and update configuration files in config/"
                echo "2. Run deployment: ./scripts/deploy.sh"
                echo "3. Monitor deployment: ./scripts/deploy.sh status"
                echo "4. Check logs: ./scripts/deploy.sh logs"
                echo ""
                echo -e "${GREEN}Useful commands:${NC}"
                echo "  ./scripts/deploy.sh deploy          - Deploy the system"
                echo "  ./scripts/deploy.sh status          - Check status"
                echo "  ./scripts/deploy.sh logs            - View logs"
                echo "  ./scripts/backup.sh full            - Create backup"
                echo "  ./scripts/maintenance.sh all        - Run maintenance"
                echo "  ./scripts/deploy.sh restart         - Restart services"
                echo ""
                echo -e "${GREEN}Service management:${NC}"
                echo "  sudo systemctl start telephony-monitoring"
                echo "  sudo systemctl stop telephony-monitoring"
                echo "  sudo systemctl status telephony-monitoring"
                echo ""
            else
                log_error "Setup validation failed"
                echo "Please fix the errors and run setup again"
                exit 1
            fi
            ;;
        "help"|*)
            echo "Cisco Telephony Monitoring System - Setup Script"
            echo ""
            echo "Usage: $0 <action>"
            echo ""
            echo "Actions:"
            echo "  full        - Complete production setup"
            echo "  check       - Check system requirements"
            echo "  directories - Create directory structure"
            echo "  config      - Setup configuration files"
            echo "  ssh         - Setup SSH keys for SBC"
            echo "  ssl         - Setup SSL certificates"
            echo "  systemd     - Setup systemd services"
            echo "  logrotate   - Setup log rotation"
            echo "  cron        - Setup cron jobs"
            echo "  firewall    - Configure firewall"
            echo "  validate    - Validate setup"
            echo "  help        - Show this help"
            echo ""
            echo "Examples:"
            echo "  $0 full                    - Complete setup"
            echo "  $0 check                   - Check requirements only"
            echo "  $0 config                  - Setup configuration only"
            echo ""
            exit 0
            ;;
    esac
}

# Execute main function
main "$@"
