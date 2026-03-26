# =============================================================================
# Telephony Load Monitoring System - Configuration Management
# =============================================================================
# This module handles all configuration management using environment variables
# and provides type-safe configuration access throughout the application.
# =============================================================================

import os
from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from functools import lru_cache


# =============================================================================
# Database Configuration
# =============================================================================
class DatabaseConfig(BaseSettings):
    """Database connection and pool settings."""
    
    url: str = Field(
        default="postgresql://postgres:password@postgres:5432/telephony_db",
        env="DATABASE_URL",
        description="PostgreSQL connection string (legacy, for backward compatibility)"
    )
    
    pool_size: int = Field(
        default=10,
        env="DB_POOL_SIZE",
        description="Database connection pool size"
    )
    
    max_overflow: int = Field(
        default=20,
        env="DB_MAX_OVERFLOW",
        description="Maximum overflow connections"
    )
    
    pool_timeout: int = Field(
        default=30,
        env="DB_POOL_TIMEOUT",
        description="Connection pool timeout"
    )
    
    pool_recycle: int = Field(
        default=3600,
        env="DB_POOL_RECYCLE",
        description="Connection recycling time"
    )
    
    echo: bool = Field(
        default=False,
        env="DB_ECHO",
        description="Enable SQLAlchemy query logging"
    )
    
    class Config:
        env_prefix = "DB_"


# =============================================================================
# Component-Specific Database Configuration
# =============================================================================
class ComponentDatabaseConfig(BaseSettings):
    """Database configuration for a specific component with cluster support."""
    
    primary_url: str = Field(
        default="",
        env="",
        description="Primary database URL"
    )
    
    replica_urls: List[str] = Field(
        default=[],
        env="",
        description="Replica database URLs for read operations"
    )
    
    pool_size: int = Field(
        default=5,
        env="",
        description="Connection pool size for this component"
    )
    
    max_overflow: int = Field(
        default=10,
        env="",
        description="Maximum overflow connections"
    )
    
    pool_timeout: int = Field(
        default=30,
        env="",
        description="Connection pool timeout"
    )
    
    pool_recycle: int = Field(
        default=3600,
        env="",
        description="Connection recycling time"
    )
    
    echo: bool = Field(
        default=False,
        env="",
        description="Enable SQLAlchemy query logging"
    )
    
    def get_read_url(self) -> str:
        """Get a read URL (replica if available, otherwise primary)."""
        if self.replica_urls:
            import random
            return random.choice(self.replica_urls)
        return self.primary_url
    
    def get_write_url(self) -> str:
        """Get the write URL (always primary)."""
        return self.primary_url


# =============================================================================
# Multi-Component Database Configuration
# =============================================================================
class MultiDatabaseConfig(BaseSettings):
    """Configuration for all component databases."""
    
    # CUCM Database Configuration
    cucm_primary_url: str = Field(
        default="postgresql://postgres:password@cucm-postgres:5432/cucm_db",
        env="CUCM_PRIMARY_URL",
        description="CUCM primary database URL"
    )
    
    cucm_replica_urls: List[str] = Field(
        default=[],
        env="CUCM_REPLICA_URLS",
        description="CUCM replica database URLs (comma-separated)"
    )
    
    cucm_pool_size: int = Field(
        default=5,
        env="CUCM_DB_POOL_SIZE",
        description="CUCM database connection pool size"
    )
    
    # UCCX Database Configuration
    uccx_primary_url: str = Field(
        default="postgresql://postgres:password@uccx-postgres:5432/uccx_db",
        env="UCCX_PRIMARY_URL",
        description="UCCX primary database URL"
    )
    
    uccx_replica_urls: List[str] = Field(
        default=[],
        env="UCCX_REPLICA_URLS",
        description="UCCX replica database URLs (comma-separated)"
    )
    
    uccx_pool_size: int = Field(
        default=5,
        env="UCCX_DB_POOL_SIZE",
        description="UCCX database connection pool size"
    )
    
    # CMS Database Configuration
    cms_primary_url: str = Field(
        default="postgresql://postgres:password@cms-postgres:5432/cms_db",
        env="CMS_PRIMARY_URL",
        description="CMS primary database URL"
    )
    
    cms_replica_urls: List[str] = Field(
        default=[],
        env="CMS_REPLICA_URLS",
        description="CMS replica database URLs (comma-separated)"
    )
    
    cms_pool_size: int = Field(
        default=5,
        env="CMS_DB_POOL_SIZE",
        description="CMS database connection pool size"
    )
    
    # IMP Database Configuration
    imp_primary_url: str = Field(
        default="postgresql://postgres:password@imp-postgres:5432/imp_db",
        env="IMP_PRIMARY_URL",
        description="IMP primary database URL"
    )
    
    imp_replica_urls: List[str] = Field(
        default=[],
        env="IMP_REPLICA_URLS",
        description="IMP replica database URLs (comma-separated)"
    )
    
    imp_pool_size: int = Field(
        default=5,
        env="IMP_DB_POOL_SIZE",
        description="IMP database connection pool size"
    )
    
    # Meeting Place Database Configuration
    meeting_place_primary_url: str = Field(
        default="postgresql://postgres:password@meeting-place-postgres:5432/meeting_place_db",
        env="MEETING_PLACE_PRIMARY_URL",
        description="Meeting Place primary database URL"
    )
    
    meeting_place_replica_urls: List[str] = Field(
        default=[],
        env="MEETING_PLACE_REPLICA_URLS",
        description="Meeting Place replica database URLs (comma-separated)"
    )
    
    meeting_place_pool_size: int = Field(
        default=5,
        env="MEETING_PLACE_DB_POOL_SIZE",
        description="Meeting Place database connection pool size"
    )
    
    # TGW Database Configuration
    tgw_primary_url: str = Field(
        default="postgresql://postgres:password@tgw-postgres:5432/tgw_db",
        env="TGW_PRIMARY_URL",
        description="TGW primary database URL"
    )
    
    tgw_replica_urls: List[str] = Field(
        default=[],
        env="TGW_REPLICA_URLS",
        description="TGW replica database URLs (comma-separated)"
    )
    
    tgw_pool_size: int = Field(
        default=5,
        env="TGW_DB_POOL_SIZE",
        description="TGW database connection pool size"
    )
    
    # SBC Database Configuration
    sbc_primary_url: str = Field(
        default="postgresql://postgres:password@sbc-postgres:5432/sbc_db",
        env="SBC_PRIMARY_URL",
        description="SBC primary database URL"
    )
    
    sbc_replica_urls: List[str] = Field(
        default=[],
        env="SBC_REPLICA_URLS",
        description="SBC replica database URLs (comma-separated)"
    )
    
    sbc_pool_size: int = Field(
        default=5,
        env="SBC_DB_POOL_SIZE",
        description="SBC database connection pool size"
    )
    
    # Expressway Database Configuration
    expressway_primary_url: str = Field(
        default="postgresql://postgres:password@expressway-postgres:5432/expressway_db",
        env="EXPRESSWAY_PRIMARY_URL",
        description="Expressway primary database URL"
    )
    
    expressway_replica_urls: List[str] = Field(
        default=[],
        env="EXPRESSWAY_REPLICA_URLS",
        description="Expressway replica database URLs (comma-separated)"
    )
    
    expressway_pool_size: int = Field(
        default=5,
        env="EXPRESSWAY_DB_POOL_SIZE",
        description="Expressway database connection pool size"
    )
    
    # Superset Database Configuration (for dashboards and metadata)
    superset_primary_url: str = Field(
        default="postgresql://postgres:password@superset-postgres:5432/superset_db",
        env="SUPERSET_PRIMARY_URL",
        description="Superset primary database URL"
    )
    
    superset_replica_urls: List[str] = Field(
        default=[],
        env="SUPERSET_REPLICA_URLS",
        description="Superset replica database URLs (comma-separated)"
    )
    
    superset_pool_size: int = Field(
        default=10,
        env="SUPERSET_DB_POOL_SIZE",
        description="Superset database connection pool size"
    )
    
    @validator("cucm_replica_urls", "uccx_replica_urls", "cms_replica_urls", 
              "imp_replica_urls", "meeting_place_replica_urls", "tgw_replica_urls",
              "sbc_replica_urls", "expressway_replica_urls", "superset_replica_urls", 
              pre=True)
    def parse_replica_urls(cls, v):
        """Parse replica URLs from comma-separated string."""
        if isinstance(v, str):
            return [url.strip() for url in v.split(",") if url.strip()]
        return v
    
    def get_component_config(self, component: str) -> ComponentDatabaseConfig:
        """Get database configuration for a specific component."""
        configs = {
            "cucm": ComponentDatabaseConfig(
                primary_url=self.cucm_primary_url,
                replica_urls=self.cucm_replica_urls,
                pool_size=self.cucm_pool_size
            ),
            "uccx": ComponentDatabaseConfig(
                primary_url=self.uccx_primary_url,
                replica_urls=self.uccx_replica_urls,
                pool_size=self.uccx_pool_size
            ),
            "cms": ComponentDatabaseConfig(
                primary_url=self.cms_primary_url,
                replica_urls=self.cms_replica_urls,
                pool_size=self.cms_pool_size
            ),
            "imp": ComponentDatabaseConfig(
                primary_url=self.imp_primary_url,
                replica_urls=self.imp_replica_urls,
                pool_size=self.imp_pool_size
            ),
            "meeting_place": ComponentDatabaseConfig(
                primary_url=self.meeting_place_primary_url,
                replica_urls=self.meeting_place_replica_urls,
                pool_size=self.meeting_place_pool_size
            ),
            "tgw": ComponentDatabaseConfig(
                primary_url=self.tgw_primary_url,
                replica_urls=self.tgw_replica_urls,
                pool_size=self.tgw_pool_size
            ),
            "sbc": ComponentDatabaseConfig(
                primary_url=self.sbc_primary_url,
                replica_urls=self.sbc_replica_urls,
                pool_size=self.sbc_pool_size
            ),
            "expressway": ComponentDatabaseConfig(
                primary_url=self.expressway_primary_url,
                replica_urls=self.expressway_replica_urls,
                pool_size=self.expressway_pool_size
            ),
            "superset": ComponentDatabaseConfig(
                primary_url=self.superset_primary_url,
                replica_urls=self.superset_replica_urls,
                pool_size=self.superset_pool_size
            )
        }
        
        if component not in configs:
            raise ValueError(f"Unknown component: {component}")
        
        return configs[component]


# =============================================================================
# Scheduler Configuration
# =============================================================================
class SchedulerConfig(BaseSettings):
    """APScheduler configuration settings."""
    
    timezone: str = Field(
        default="UTC",
        env="SCHEDULER_TIMEZONE",
        description="Scheduler timezone"
    )
    
    enabled: bool = Field(
        default=True,
        env="SCHEDULER_ENABLED",
        description="Enable/disable scheduler"
    )
    
    job_defaults_coalesce: bool = Field(
        default=True,
        env="SCHEDULER_JOB_DEFAULTS_COALESCE",
        description="Coalesce multiple job instances"
    )
    
    job_defaults_max_instances: int = Field(
        default=1,
        env="SCHEDULER_JOB_DEFAULTS_MAX_INSTANCES",
        description="Maximum job instances"
    )
    
    collection_interval: int = Field(
        default=300,
        env="COLLECTION_INTERVAL",
        description="Collection interval in seconds"
    )
    
    class Config:
        env_prefix = "SCHEDULER_"


# =============================================================================
# Mock Server Configuration
# =============================================================================
class MockServerConfig(BaseSettings):
    """Mock server configuration for development/testing."""
    
    enabled: bool = Field(
        default=True,
        env="MOCK_SERVER_ENABLED",
        description="Enable mock server"
    )
    
    host: str = Field(
        default="0.0.0.0",
        env="MOCK_SERVER_HOST",
        description="Mock server host"
    )
    
    port: int = Field(
        default=8001,
        env="MOCK_SERVER_PORT",
        description="Mock server port"
    )
    
    data_fluctuation: bool = Field(
        default=True,
        env="MOCK_DATA_FLUCTUATION",
        description="Enable realistic data fluctuation"
    )
    
    seed: int = Field(
        default=12345,
        env="MOCK_DATA_SEED",
        description="Random seed for reproducible data"
    )
    
    business_hours_only: bool = Field(
        default=False,
        env="MOCK_DATA_BUSINESS_HOURS_ONLY",
        description="Generate data only during business hours"
    )
    
    class Config:
        env_prefix = "MOCK_"


# =============================================================================
# API Configuration
# =============================================================================
class APIConfig(BaseSettings):
    """FastAPI server configuration."""
    
    host: str = Field(
        default="0.0.0.0",
        env="API_HOST",
        description="API server host"
    )
    
    port: int = Field(
        default=8000,
        env="API_PORT",
        description="API server port"
    )
    
    debug: bool = Field(
        default=False,
        env="API_DEBUG",
        description="Enable debug mode"
    )
    
    reload: bool = Field(
        default=False,
        env="API_RELOAD",
        description="Enable auto-reload"
    )
    
    cors_origins: List[str] = Field(
        default=["*"],
        env="API_CORS_ORIGINS",
        description="CORS allowed origins"
    )
    
    cors_credentials: bool = Field(
        default=True,
        env="API_CORS_CREDENTIALS",
        description="Allow CORS credentials"
    )
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_prefix = "API_"


# =============================================================================
# Logging Configuration
# =============================================================================
class LoggingConfig(BaseSettings):
    """Logging configuration settings."""
    
    level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level"
    )
    
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT",
        description="Log format string"
    )
    
    class Config:
        env_prefix = "LOG_"


# =============================================================================
# Cisco Server Configuration
# =============================================================================
class CiscoServerConfig(BaseSettings):
    """Cisco server connection settings."""
    
    # CUCM Configuration
    cucm_nodes: List[str] = Field(
        default=["192.168.1.100"],
        env="CUCM_NODES",
        description="CUCM server nodes (comma-separated IP addresses)"
    )
    
    cucm_username: str = Field(
        default="admin",
        env="CUCM_USERNAME",
        description="CUCM username"
    )
    
    cucm_password: str = Field(
        default="password",
        env="CUCM_PASSWORD",
        description="CUCM password"
    )
    
    cucm_port: int = Field(
        default=8443,
        env="CUCM_PORT",
        description="CUCM port"
    )
    
    cucm_verify_ssl: bool = Field(
        default=False,
        env="CUCM_VERIFY_SSL",
        description="Verify SSL certificate"
    )
    
    # UCCX Configuration
    uccx_nodes: List[str] = Field(
        default=["192.168.1.101"],
        env="UCCX_NODES",
        description="UCCX server nodes (comma-separated IP addresses)"
    )
    
    uccx_username: str = Field(
        default="admin",
        env="UCCX_USERNAME",
        description="UCCX username"
    )
    
    uccx_password: str = Field(
        default="password",
        env="UCCX_PASSWORD",
        description="UCCX password"
    )
    
    uccx_port: int = Field(
        default=8445,
        env="UCCX_PORT",
        description="UCCX port"
    )
    
    uccx_verify_ssl: bool = Field(
        default=False,
        env="UCCX_VERIFY_SSL",
        description="Verify SSL certificate"
    )
    
    # CMS Configuration
    cms_nodes: List[str] = Field(
        default=["192.168.1.102"],
        env="CMS_NODES",
        description="CMS server nodes (comma-separated IP addresses)"
    )
    
    cms_username: str = Field(
        default="admin",
        env="CMS_USERNAME",
        description="CMS username"
    )
    
    cms_password: str = Field(
        default="password",
        env="CMS_PASSWORD",
        description="CMS password"
    )
    
    cms_port: int = Field(
        default=445,
        env="CMS_PORT",
        description="CMS port"
    )
    
    cms_verify_ssl: bool = Field(
        default=False,
        env="CMS_VERIFY_SSL",
        description="Verify SSL certificate"
    )
    
    # IMP Configuration
    imp_nodes: List[str] = Field(
        default=["192.168.1.103"],
        env="IMP_NODES",
        description="IMP server nodes (comma-separated IP addresses)"
    )
    
    imp_username: str = Field(
        default="admin",
        env="IMP_USERNAME",
        description="IMP username"
    )
    
    imp_password: str = Field(
        default="password",
        env="IMP_PASSWORD",
        description="IMP password"
    )
    
    imp_port: int = Field(
        default=8222,
        env="IMP_PORT",
        description="IMP port"
    )
    
    imp_verify_ssl: bool = Field(
        default=False,
        env="IMP_VERIFY_SSL",
        description="Verify SSL certificate"
    )
    
    # Meeting Place Configuration
    meeting_place_nodes: List[str] = Field(
        default=["192.168.1.104"],
        env="MEETING_PLACE_NODES",
        description="Meeting Place server nodes (comma-separated IP addresses)"
    )
    
    meeting_place_username: str = Field(
        default="admin",
        env="MEETING_PLACE_USERNAME",
        description="Meeting Place username"
    )
    
    meeting_place_password: str = Field(
        default="password",
        env="MEETING_PLACE_PASSWORD",
        description="Meeting Place password"
    )
    
    meeting_place_port: int = Field(
        default=8080,
        env="MEETING_PLACE_PORT",
        description="Meeting Place port"
    )
    
    meeting_place_verify_ssl: bool = Field(
        default=False,
        env="MEETING_PLACE_VERIFY_SSL",
        description="Verify SSL certificate"
    )
    
    # TGW (Trunk Gateway) Configuration
    tgw_nodes: List[str] = Field(
        default=["localhost"],
        env="TGW_NODES",
        description="TGW nodes (comma-separated IP addresses)"
    )
    
    tgw_username: str = Field(
        default="",
        env="TGW_USERNAME",
        description="TGW username"
    )
    
    tgw_password: str = Field(
        default="",
        env="TGW_PASSWORD",
        description="TGW password"
    )
    
    tgw_port: int = Field(
        default=161,
        env="TGW_PORT",
        description="TGW port"
    )
    
    tgw_verify_ssl: bool = Field(
        default=False,
        env="TGW_VERIFY_SSL",
        description="Verify SSL certificate for TGW"
    )
    
    tgw_snmp_community: str = Field(
        default="public",
        env="TGW_SNMP_COMMUNITY",
        description="SNMP community string for TGW"
    )
    
    tgw_snmp_version: str = Field(
        default="2c",
        env="TGW_SNMP_VERSION",
        description="SNMP version (2c or 3)"
    )
    
    tgw_snmp_timeout: int = Field(
        default=5,
        env="TGW_SNMP_TIMEOUT",
        description="SNMP timeout in seconds"
    )
    
    # SBC (Session Border Controller) Configuration
    sbc_nodes: List[str] = Field(
        default=["localhost"],
        env="SBC_NODES",
        description="SBC nodes (comma-separated IP addresses)"
    )
    
    sbc_username: str = Field(
        default="",
        env="SBC_USERNAME",
        description="SBC API username"
    )
    
    sbc_password: str = Field(
        default="",
        env="SBC_PASSWORD",
        description="SBC API password"
    )
    
    sbc_port: int = Field(
        default=443,
        env="SBC_PORT",
        description="SBC API port"
    )
    
    sbc_verify_ssl: bool = Field(
        default=False,
        env="SBC_VERIFY_SSL",
        description="Verify SSL certificate for SBC"
    )
    
    sbc_api_version: str = Field(
        default="v1",
        env="SBC_API_VERSION",
        description="SBC API version"
    )
    
    # Expressway Configuration
    expressway_nodes: List[str] = Field(
        default=["localhost"],
        env="EXPRESSWAY_NODES",
        description="Expressway nodes (comma-separated IP addresses)"
    )
    
    expressway_username: str = Field(
        default="",
        env="EXPRESSWAY_USERNAME",
        description="Expressway API username"
    )
    
    expressway_password: str = Field(
        default="",
        env="EXPRESSWAY_PASSWORD",
        description="Expressway API password"
    )
    
    expressway_port: int = Field(
        default=443,
        env="EXPRESSWAY_PORT",
        description="Expressway API port"
    )
    
    expressway_verify_ssl: bool = Field(
        default=False,
        env="EXPRESSWAY_VERIFY_SSL",
        description="Verify SSL certificate for Expressway"
    )
    
    expressway_api_version: str = Field(
        default="v1",
        env="EXPRESSWAY_API_VERSION",
        description="Expressway API version"
    )
    
    # Feature Toggle Configuration
    @validator("cucm_nodes", "uccx_nodes", "cms_nodes", "imp_nodes", 
              "meeting_place_nodes", "tgw_nodes", "sbc_nodes", "expressway_nodes", 
              pre=True)
    def parse_nodes(cls, v):
        """Parse nodes from comma-separated string."""
        if isinstance(v, str):
            return [node.strip() for node in v.split(",") if node.strip()]
        elif isinstance(v, list):
            return v
        else:
            return [str(v)] if v else []
    
    use_real_cucm: bool = Field(
        default=False,
        env="USE_REAL_CUCM",
        description="Use real CUCM API instead of mock data"
    )
    
    use_real_uccx: bool = Field(
        default=False,
        env="USE_REAL_UCCX",
        description="Use real UCCX API instead of mock data"
    )
    
    use_real_cms: bool = Field(
        default=False,
        env="USE_REAL_CMS",
        description="Use real CMS API instead of mock data"
    )
    
    use_real_imp: bool = Field(
        default=False,
        env="USE_REAL_IMP",
        description="Use real IMP API instead of mock data"
    )
    
    use_real_meeting_place: bool = Field(
        default=False,
        env="USE_REAL_MEETING_PLACE",
        description="Use real Meeting Place API instead of mock data"
    )
    
    use_real_tgw: bool = Field(
        default=False,
        env="USE_REAL_TGW",
        description="Use real TGW SNMP instead of mock data"
    )
    
    use_real_sbc: bool = Field(
        default=False,
        env="USE_REAL_SBC",
        description="Use real SBC API instead of mock data"
    )
    
    use_real_expressway: bool = Field(
        default=False,
        env="USE_REAL_EXPRESSWAY",
        description="Use real Expressway API instead of mock data"
    )
    
    # Performance Configuration
# =============================================================================
class PerformanceConfig(BaseSettings):
    """Performance and timeout settings."""
    
    request_timeout: int = Field(
        default=30,
        env="REQUEST_TIMEOUT",
        description="Request timeout in seconds"
    )
    
    collection_timeout: int = Field(
        default=60,
        env="COLLECTION_TIMEOUT",
        description="Collection timeout in seconds"
    )
    
    max_retries: int = Field(
        default=3,
        env="MAX_RETRIES",
        description="Maximum retry attempts"
    )
    
    retry_delay: int = Field(
        default=5,
        env="RETRY_DELAY",
        description="Delay between retries"
    )
    
    class Config:
        env_prefix = "PERF_"


# =============================================================================
# Development Configuration
# =============================================================================
class DevelopmentConfig(BaseSettings):
    """Development and testing settings."""
    
    dev_mode: bool = Field(
        default=False,
        env="DEV_MODE",
        description="Enable development mode"
    )
    
    mock_external_apis: bool = Field(
        default=True,
        env="MOCK_EXTERNAL_APIS",
        description="Mock external API calls"
    )
    
    skip_ssl_verification: bool = Field(
        default=True,
        env="SKIP_SSL_VERIFICATION",
        description="Skip SSL verification"
    )
    
    class Config:
        env_prefix = "DEV_"


# =============================================================================
# Main Configuration Class
# =============================================================================
class Settings(BaseSettings):
    """Main application configuration class."""
    
    # Sub-configurations
    database: DatabaseConfig = DatabaseConfig()
    multi_database: MultiDatabaseConfig = MultiDatabaseConfig()
    scheduler: SchedulerConfig = SchedulerConfig()
    mock_server: MockServerConfig = MockServerConfig()
    api: APIConfig = APIConfig()
    logging: LoggingConfig = LoggingConfig()
    cisco: CiscoServerConfig = CiscoServerConfig()
    performance: PerformanceConfig = PerformanceConfig()
    development: DevelopmentConfig = DevelopmentConfig()
    
    # Application settings
    app_name: str = Field(
        default="Telephony Load Monitoring System",
        env="APP_NAME",
        description="Application name"
    )
    
    app_version: str = Field(
        default="1.0.0",
        env="APP_VERSION",
        description="Application version"
    )
    
    environment: str = Field(
        default="development",
        env="ENVIRONMENT",
        description="Environment (development, staging, production)"
    )
    
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY",
        description="Application secret key"
    )
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# =============================================================================
# Configuration Instance
# =============================================================================
@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: Application configuration
    """
    return Settings()


# =============================================================================
# Convenience Functions
# =============================================================================
def get_database_url() -> str:
    """Get database URL from settings."""
    return get_settings().database.url


def is_development() -> bool:
    """Check if running in development mode."""
    return get_settings().environment == "development"


def is_production() -> bool:
    """Check if running in production mode."""
    return get_settings().environment == "production"


def get_log_level() -> str:
    """Get logging level from settings."""
    return get_settings().logging.level


def get_collection_interval() -> int:
    """Get collection interval from settings."""
    return get_settings().scheduler.collection_interval


# =============================================================================
# Configuration Validation
# =============================================================================
def validate_configuration() -> List[str]:
    """
    Validate configuration and return list of issues.
    
    Returns:
        List[str]: List of configuration issues
    """
    issues = []
    settings = get_settings()
    
    # Validate database URL
    if not settings.database.url:
        issues.append("Database URL is required")
    
    # Validate collection interval
    if settings.scheduler.collection_interval < 60:
        issues.append("Collection interval should be at least 60 seconds")
    
    # Validate ports
    if not (1 <= settings.api.port <= 65535):
        issues.append("API port must be between 1 and 65535")
    
    if not (1 <= settings.mock_server.port <= 65535):
        issues.append("Mock server port must be between 1 and 65535")
    
    # Validate secret key in production
    if is_production() and settings.secret_key == "your-secret-key-change-in-production":
        issues.append("Secret key must be changed in production")
    
    return issues


# =============================================================================
# Export settings
# =============================================================================
settings = get_settings()

__all__ = [
    "Settings",
    "get_settings",
    "get_database_url",
    "is_development",
    "is_production",
    "get_log_level",
    "get_collection_interval",
    "validate_configuration",
    "settings",
]
