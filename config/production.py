"""
Production Configuration Template
Comprehensive configuration management for Cisco Telephony Monitoring System
"""

from pydantic import BaseSettings, validator
from typing import List, Optional, Dict, Any
import os
import ipaddress
from pathlib import Path

class ProductionConfig(BaseSettings):
    """Production configuration with validation and security"""
    
    # =========================================================================
    # DATABASE CONFIGURATION
    # =========================================================================
    postgres_user: str
    postgres_password: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_ssl_mode: str = "require"
    postgres_pool_size: int = 20
    postgres_max_overflow: int = 30
    
    # Multi-Database URLs (automatically generated)
    cucm_primary_url: Optional[str] = None
    uccx_primary_url: Optional[str] = None
    cms_primary_url: Optional[str] = None
    imp_primary_url: Optional[str] = None
    meeting_place_primary_url: Optional[str] = None
    tgw_primary_url: Optional[str] = None
    sbc_primary_url: Optional[str] = None
    expressway_primary_url: Optional[str] = None
    
    # =========================================================================
    # CISCO COMPONENT CONFIGURATION
    # =========================================================================
    
    # CUCM Configuration
    cucm_host: str
    cucm_username: str
    cucm_password: str
    cucm_port: int = 443
    cucm_verify_ssl: bool = False
    cucm_timeout: int = 30
    cucm_retry_attempts: int = 3
    
    # UCCX Configuration
    uccx_host: str
    uccx_username: str
    uccx_password: str
    uccx_port: int = 443
    uccx_verify_ssl: bool = False
    uccx_timeout: int = 30
    uccx_retry_attempts: int = 3
    
    # TGW Configuration (SNMP)
    tgw_host: str
    tgw_snmp_community: str
    tgw_snmp_port: int = 161
    tgw_snmp_version: str = "2c"
    tgw_snmp_timeout: int = 5
    tgw_snmp_retries: int = 3
    
    # SBC Configuration (SSH)
    sbc_host: str
    sbc_username: str
    sbc_password: str
    sbc_port: int = 22
    sbc_ssh_key_path: Optional[str] = None
    sbc_timeout: int = 30
    sbc_retry_attempts: int = 3
    
    # =========================================================================
    # APPLICATION CONFIGURATION
    # =========================================================================
    enable_polling: bool = True
    polling_interval: int = 60
    request_timeout: int = 10
    log_level: str = "INFO"
    log_format: str = "json"
    max_workers: int = 4
    keep_alive: int = 2
    
    # =========================================================================
    # SECURITY CONFIGURATION
    # =========================================================================
    secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    api_key_length: int = 32
    rate_limit_per_minute: int = 100
    
    # =========================================================================
    # MONITORING CONFIGURATION
    # =========================================================================
    enable_metrics: bool = True
    metrics_port: int = 9090
    health_check_interval: int = 30
    alert_webhook_url: Optional[str] = None
    
    # =========================================================================
    # BACKUP CONFIGURATION
    # =========================================================================
    backup_enabled: bool = True
    backup_interval_hours: int = 6
    backup_retention_days: int = 30
    backup_location: str = "/app/backups"
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @validator('postgres_password')
    def validate_password_strength(cls, v):
        """Validate database password strength"""
        if len(v) < 12:
            raise ValueError('Database password must be at least 12 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Database password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Database password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Database password must contain at least one digit')
        return v
    
    @validator('cucm_host', 'uccx_host', 'tgw_host', 'sbc_host')
    def validate_ip_address(cls, v):
        """Validate IP addresses"""
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f'Invalid IP address: {v}')
        return v
    
    @validator('cucm_port', 'uccx_port')
    def validate_port_range(cls, v):
        """Validate port ranges"""
        if not 1 <= v <= 65535:
            raise ValueError(f'Port must be between 1 and 65535, got {v}')
        return v
    
    @validator('tgw_snmp_version')
    def validate_snmp_version(cls, v):
        """Validate SNMP version"""
        if v not in ['1', '2c', '3']:
            raise ValueError(f'SNMP version must be 1, 2c, or 3, got {v}')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}, got {v}')
        return v.upper()
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        """Validate secret key strength"""
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters')
        return v
    
    # =========================================================================
    # POST-INITIALIZATION SETUP
    # =========================================================================
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._generate_database_urls()
        self._create_directories()
    
    def _generate_database_urls(self):
        """Generate database URLs from base configuration"""
        base_url = f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}"
        
        self.cucm_primary_url = f"{base_url}/cucm_db"
        self.uccx_primary_url = f"{base_url}/uccx_db"
        self.cms_primary_url = f"{base_url}/cms_db"
        self.imp_primary_url = f"{base_url}/imp_db"
        self.meeting_place_primary_url = f"{base_url}/meeting_place_db"
        self.tgw_primary_url = f"{base_url}/tgw_db"
        self.sbc_primary_url = f"{base_url}/sbc_db"
        self.expressway_primary_url = f"{base_url}/expressway_db"
    
    def _create_directories(self):
        """Create necessary directories"""
        directories = [
            self.backup_location,
            "/app/logs",
            "/app/data",
            "/app/cache"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def get_cisco_config(self, component: str) -> Dict[str, Any]:
        """Get configuration for specific Cisco component"""
        configs = {
            'cucm': {
                'host': self.cucm_host,
                'username': self.cucm_username,
                'password': self.cucm_password,
                'port': self.cucm_port,
                'verify_ssl': self.cucm_verify_ssl,
                'timeout': self.cucm_timeout,
                'retry_attempts': self.cucm_retry_attempts
            },
            'uccx': {
                'host': self.uccx_host,
                'username': self.uccx_username,
                'password': self.uccx_password,
                'port': self.uccx_port,
                'verify_ssl': self.uccx_verify_ssl,
                'timeout': self.uccx_timeout,
                'retry_attempts': self.uccx_retry_attempts
            },
            'tgw': {
                'host': self.tgw_host,
                'snmp_community': self.tgw_snmp_community,
                'snmp_port': self.tgw_snmp_port,
                'snmp_version': self.tgw_snmp_version,
                'snmp_timeout': self.tgw_snmp_timeout,
                'snmp_retries': self.tgw_snmp_retries
            },
            'sbc': {
                'host': self.sbc_host,
                'username': self.sbc_username,
                'password': self.sbc_password,
                'port': self.sbc_port,
                'ssh_key_path': self.sbc_ssh_key_path,
                'timeout': self.sbc_timeout,
                'retry_attempts': self.sbc_retry_attempts
            }
        }
        
        if component not in configs:
            raise ValueError(f"Unknown component: {component}")
        
        return configs[component]
    
    def get_database_config(self, component: str) -> str:
        """Get database URL for specific component"""
        db_urls = {
            'cucm': self.cucm_primary_url,
            'uccx': self.uccx_primary_url,
            'cms': self.cms_primary_url,
            'imp': self.imp_primary_url,
            'meeting_place': self.meeting_place_primary_url,
            'tgw': self.tgw_primary_url,
            'sbc': self.sbc_primary_url,
            'expressway': self.expressway_primary_url
        }
        
        if component not in db_urls:
            raise ValueError(f"Unknown component: {component}")
        
        return db_urls[component]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# =========================================================================
# DEVELOPMENT CONFIGURATION (for testing)
# =========================================================================

class DevelopmentConfig(ProductionConfig):
    """Development configuration with relaxed security"""
    
    postgres_user: str = "postgres"
    postgres_password: str = "password"
    postgres_host: str = "localhost"
    
    cucm_host: str = "192.168.1.100"
    cucm_username: str = "admin"
    cucm_password: str = "password"
    
    uccx_host: str = "192.168.1.101"
    uccx_username: str = "admin"
    uccx_password: str = "password"
    
    tgw_host: str = "192.168.1.102"
    tgw_snmp_community: str = "public"
    
    sbc_host: str = "192.168.1.103"
    sbc_username: str = "admin"
    sbc_password: str = "password"
    
    secret_key: str = "development-secret-key-change-in-production"
    log_level: str = "DEBUG"
    enable_metrics: bool = False
    
    # Override validators for development
    @validator('postgres_password')
    def validate_password_strength_dev(cls, v):
        return v  # Skip validation in development
    
    @validator('secret_key')
    def validate_secret_key_dev(cls, v):
        return v  # Skip validation in development


# =========================================================================
# CONFIGURATION FACTORY
# =========================================================================

def get_config(environment: str = "production") -> ProductionConfig:
    """Get configuration based on environment"""
    configs = {
        "production": ProductionConfig,
        "development": DevelopmentConfig,
        "dev": DevelopmentConfig
    }
    
    if environment not in configs:
        raise ValueError(f"Unknown environment: {environment}")
    
    return configs[environment]()


# =========================================================================
# CONFIGURATION VALIDATION
# =========================================================================

def validate_config_file(config_path: str) -> bool:
    """Validate configuration file"""
    try:
        config = ProductionConfig(_env_file=config_path)
        return True
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False


# =========================================================================
# EXPORTED CONFIGURATION
# =========================================================================

# Default production configuration
config = get_config(os.getenv("ENVIRONMENT", "production"))
