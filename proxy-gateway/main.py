# =============================================================================
# Proxy Gateway - FastAPI Application
# =============================================================================
# This module serves as the central data collection gateway for the Telephony
# Load Monitoring System. It:
#   - Collects metrics from the mock Cisco servers (UCCX and CUCM)
#   - Transforms and normalizes the data
#   - Persists metrics to PostgreSQL via SQLAlchemy
#   - Provides a background polling mechanism for automatic collection
#   - Exposes REST API endpoints for manual collection and status checks
# =============================================================================

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# Import our database models and utilities
from models import (
    TelephonyMetric,
    get_engine,
    get_session_maker,
    init_database,
    DatabaseSession
)

# Import mock generators for multi-node support
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mock_generators import create_generators

# =============================================================================
# Logging Configuration
# =============================================================================
# Configure structured logging for production observability
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Configuration from Environment Variables
# =============================================================================
# These settings can be overridden via environment variables for flexibility
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/telephony_db"
)

MOCK_SERVER_URL = os.getenv(
    "MOCK_SERVER_URL",
    "http://mock-server:8001"  # Docker service name
)

AXLERATE_URL = os.getenv(
    "AXLERATE_URL",
    "http://axlerate:8000"  # Docker service name
)

# Polling interval in seconds (default: 60 seconds = 1 minute)
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "60"))

# Enable/disable automatic background polling
ENABLE_POLLING = os.getenv("ENABLE_POLLING", "true").lower() == "true"

# Request timeout for mock server calls (seconds)
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))

# =============================================================================
# Global State
# =============================================================================
# These are initialized during application startup
engine = None
SessionLocal = None
polling_task = None
last_collection_time = None
metrics_collected_count = 0
generators = []  # List of generators for all nodes

# =============================================================================
# Application Lifespan (Startup/Shutdown Events)
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown lifecycle.
    
    Startup:
        - Initialize database engine
        - Create tables if they don't exist
        - Start background polling task (if enabled)
    
    Shutdown:
        - Cancel background polling task
        - Close database connections
    """
    global engine, SessionLocal, polling_task, generators
    
    # ===========================
    # STARTUP
    # ===========================
    logger.info("=" * 60)
    logger.info("Proxy Gateway Starting Up")
    logger.info("=" * 60)
    
    # Initialize database connection
    logger.info(f"Connecting to database: {DATABASE_URL.replace('password', '***')}")
    engine = get_engine(DATABASE_URL)
    SessionLocal = get_session_maker(engine)
    
    # Initialize database schema
    logger.info("Initializing database schema...")
    init_database(engine)
    logger.info("Database schema ready")
    
    # Initialize generators for all nodes
    logger.info("Initializing generators for all configured nodes...")
    generators = create_generators()
    logger.info(f"Created {len(generators)} generators for multi-node collection")
    for generator in generators:
        logger.info(f"  - {generator.server_config.name} ({generator.server_config.ip_address})")
    
    # Start background polling if enabled
    if ENABLE_POLLING:
        logger.info(f"Starting background polling (interval: {POLLING_INTERVAL}s)")
        polling_task = asyncio.create_task(polling_loop())
        logger.info("Background polling started")
    else:
        logger.info("Background polling is disabled")
    
    logger.info("Proxy Gateway is ready")
    logger.info("=" * 60)
    
    yield  # Application runs here
    
    # ===========================
    # SHUTDOWN
    # ===========================
    logger.info("=" * 60)
    logger.info("Proxy Gateway Shutting Down")
    logger.info("=" * 60)
    
    # Cancel polling task
    if polling_task:
        logger.info("Stopping background polling...")
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        logger.info("Background polling stopped")
    
    # Close database connections
    if engine:
        logger.info("Closing database connections...")
        engine.dispose()
        logger.info("Database connections closed")
    
    logger.info("Proxy Gateway shutdown complete")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Telephony Metrics Proxy Gateway",
    description="Collects metrics from Cisco servers and persists to PostgreSQL",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Database Dependency
# =============================================================================

def get_db() -> Session:
    """
    FastAPI dependency that provides a database session.
    Automatically closes the session after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Data Collection Functions
# =============================================================================

def fetch_uccx_metrics() -> List[Dict[str, Any]]:
    """
    Fetch metrics from UCCX server (mock or real based on feature toggle).
    
    Returns:
        List of metric dictionaries ready for database insertion.
    
    Raises:
        requests.RequestException: If the API call fails.
    """
    if settings.use_real_uccx:
        # Use real UCCX generator
        from real_generators import UCCXRealGenerator
        generator = UCCXRealGenerator(settings)
        metrics_data = generator.generate_metrics()
        server_type = metrics_data.get("server_type", "uccx")
        metrics = metrics_data.get("metrics", {})
    else:
        # Use mock UCCX generator
        from mock_generators import UCCXMockGenerator
        generator = UCCXMockGenerator(settings)
        metrics_data = generator.generate_metrics()
        server_type = metrics_data.get("server_type", "uccx")
        metrics = metrics_data.get("metrics", {})
    
    # Transform nested metrics into flat records
    flat_metrics = []
    for metric_name, metric_info in metrics.items():
        flat_metrics.append({
            "server_type": server_type,
            "metric_name": metric_name,
            "metric_value": metric_info["value"],
            "unit": metric_info["unit"]
        })
    
    logger.debug(f"Fetched {len(flat_metrics)} UCCX metrics")
    return flat_metrics


def fetch_cucm_metrics() -> List[Dict[str, Any]]:
    """
    Fetch metrics from CUCM server (mock or real based on feature toggle).
    
    Returns:
        List of metric dictionaries ready for database insertion.
    
    Raises:
        requests.RequestException: If the API call fails.
    """
    if settings.use_real_cucm:
        # Use real CUCM generator
        from real_generators import CUCMRealGenerator
        generator = CUCMRealGenerator(settings)
        metrics_data = generator.generate_metrics()
        server_type = metrics_data.get("server_type", "cucm")
        metrics = metrics_data.get("metrics", {})
    else:
        # Use mock CUCM generator
        from mock_generators import CUCMMockGenerator
        generator = CUCMMockGenerator(settings)
        metrics_data = generator.generate_metrics()
        server_type = metrics_data.get("server_type", "cucm")
        metrics = metrics_data.get("metrics", {})
    
    # Transform nested metrics into flat records
    flat_metrics = []
    for metric_name, metric_info in metrics.items():
        flat_metrics.append({
            "server_type": server_type,
            "metric_name": metric_name,
            "metric_value": metric_info["value"],
            "unit": metric_info["unit"]
        })
    
    logger.debug(f"Fetched {len(flat_metrics)} CUCM metrics")
    return flat_metrics


def fetch_tgw_metrics() -> List[Dict[str, Any]]:
    """
    Fetch metrics from TGW router (mock or real based on feature toggle).
    
    Returns:
        List of metric dictionaries ready for database insertion.
    
    Raises:
        requests.RequestException: If the API call fails.
    """
    if settings.use_real_tgw:
        # Use real TGW generator
        from real_generators import TGWRealGenerator
        generator = TGWRealGenerator(settings)
        metrics_data = generator.generate_metrics()
        server_type = metrics_data.get("server_type", "tgw")
        metrics = metrics_data.get("metrics", {})
    else:
        # Use mock TGW generator
        from mock_generators import TGWMockGenerator
        generator = TGWMockGenerator(settings)
        metrics_data = generator.generate_metrics()
        server_type = metrics_data.get("server_type", "tgw")
        metrics = metrics_data.get("metrics", {})
    
    # Transform nested metrics into flat records
    flat_metrics = []
    for metric_name, metric_info in metrics.items():
        flat_metrics.append({
            "server_type": server_type,
            "metric_name": metric_name,
            "metric_value": metric_info["value"],
            "unit": metric_info["unit"]
        })
    
    logger.debug(f"Fetched {len(flat_metrics)} TGW metrics")
    return flat_metrics


def fetch_sbc_metrics() -> List[Dict[str, Any]]:
    """
    Fetch metrics from SBC server (mock or real based on feature toggle).
    
    Returns:
        List of metric dictionaries ready for database insertion.
    
    Raises:
        requests.RequestException: If the API call fails.
    """
    if settings.use_real_sbc:
        # Use real SBC generator
        from real_generators import SBCRealGenerator
        generator = SBCRealGenerator(settings)
        metrics_data = generator.generate_metrics()
        server_type = metrics_data.get("server_type", "sbc")
        metrics = metrics_data.get("metrics", {})
    else:
        # Use mock SBC generator
        from mock_generators import SBCMockGenerator
        generator = SBCMockGenerator(settings)
        metrics_data = generator.generate_metrics()
        server_type = metrics_data.get("server_type", "sbc")
        metrics = metrics_data.get("metrics", {})
    
    # Transform nested metrics into flat records
    flat_metrics = []
    for metric_name, metric_info in metrics.items():
        flat_metrics.append({
            "server_type": server_type,
            "metric_name": metric_name,
            "metric_value": metric_info["value"],
            "unit": metric_info["unit"]
        })
    
    logger.debug(f"Fetched {len(flat_metrics)} SBC metrics")
    return flat_metrics


def fetch_expressway_metrics() -> List[Dict[str, Any]]:
    """
    Fetch metrics from Expressway server (mock or real based on feature toggle).
    
    Returns:
        List of metric dictionaries ready for database insertion.
    
    Raises:
        requests.RequestException: If the API call fails.
    """
    if settings.use_real_expressway:
        # Use real Expressway generator
        from real_generators import ExpresswayRealGenerator
        generator = ExpresswayRealGenerator(settings)
        metrics_data = generator.generate_metrics()
        server_type = metrics_data.get("server_type", "expressway")
        metrics = metrics_data.get("metrics", {})
    else:
        # Use mock Expressway generator
        from mock_generators import ExpresswayMockGenerator
        generator = ExpresswayMockGenerator(settings)
        metrics_data = generator.generate_metrics()
        server_type = metrics_data.get("server_type", "expressway")
        metrics = metrics_data.get("metrics", {})
    
    # Transform nested metrics into flat records
    flat_metrics = []
    for metric_name, metric_info in metrics.items():
        flat_metrics.append({
            "server_type": server_type,
            "metric_name": metric_name,
            "metric_value": metric_info["value"],
            "unit": metric_info["unit"]
        })
    
    logger.debug(f"Fetched {len(flat_metrics)} Expressway metrics")
    return flat_metrics


def save_metrics_to_database(metrics: List[Dict[str, Any]]) -> int:
    """
    Save a list of metrics to the PostgreSQL database.
    
    Args:
        metrics: List of metric dictionaries with keys:
                 server_type, server_name, server_ip, metric_name, metric_value, unit
    
    Returns:
        Number of metrics saved.
    
    Raises:
        SQLAlchemyError: If database operation fails.
    """
    count = 0
    with DatabaseSession(SessionLocal) as db:
        for metric_data in metrics:
            metric = TelephonyMetric(
                server_type=metric_data["server_type"],
                server_name=metric_data.get("server_name", "Unknown"),
                server_ip=metric_data.get("server_ip", "Unknown"),
                metric_name=metric_data["metric_name"],
                metric_value=metric_data["metric_value"],
                unit=metric_data["unit"]
            )
            db.add(metric)
            count += 1
    
    logger.debug(f"Saved {count} metrics to database")
    return count


def collect_all_metrics() -> Dict[str, Any]:
    """
    Collect metrics from all configured nodes and save to database.
    
    This is the main collection orchestrator that:
    1. Iterates through all node generators
    2. Generates metrics for each individual node
    3. Saves all metrics to database with proper server identification
    4. Returns summary of collection results
    
    Returns:
        Dictionary with collection results including:
        - success: Boolean indicating overall success
        - node_count: Number of nodes processed
        - total_saved: Total metrics saved to database
        - errors: List of any errors encountered
        - timestamp: ISO format timestamp of collection
    """
    global last_collection_time, metrics_collected_count
    
    errors = []
    all_metrics = []
    node_count = 0
    
    logger.info("Starting multi-node metrics collection cycle...")
    
    # Collect metrics from each node generator
    for generator in generators:
        try:
            node_name = generator.server_config.name
            node_ip = generator.server_config.ip_address
            server_type = generator.server_config.server_type
            
            logger.info(f"Collecting metrics from {node_name} ({node_ip})")
            
            # Generate metrics for this specific node
            metrics_data = generator.generate_metrics()
            
            # Ensure server identification is included
            metrics_data["server_name"] = node_name
            metrics_data["server_ip"] = node_ip
            
            # Convert to database format
            db_metrics = convert_metrics_to_db_format(metrics_data, server_type)
            all_metrics.extend(db_metrics)
            
            node_count += 1
            logger.info(f"Collected {len(db_metrics)} metrics from {node_name}")
            
        except Exception as e:
            error_msg = f"Failed to collect metrics from {generator.server_config.name}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    # Save to database if we have any metrics
    total_saved = 0
    if all_metrics:
        try:
            total_saved = save_metrics_to_database(all_metrics)
            metrics_collected_count += total_saved
            logger.info(f"Saved {total_saved} metrics to database")
        except Exception as e:
            error_msg = f"Failed to save metrics to database: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    last_collection_time = datetime.utcnow()
    
    return {
        "success": len(errors) == 0,
        "node_count": node_count,
        "total_saved": total_saved,
        "errors": errors,
        "timestamp": last_collection_time.isoformat()
    }


def convert_metrics_to_db_format(metrics_data: Dict[str, Any], server_type: str) -> List[Dict[str, Any]]:
    """
    Convert generator metrics to database format.
    
    Args:
        metrics_data: Raw metrics from generator
        server_type: Type of server (cucm, uccx, etc.)
    
    Returns:
        List of metrics in database format
    """
    db_metrics = []
    
    # Convert each metric field to the database format
    for key, value in metrics_data.items():
        if key not in ["server_name", "server_ip"]:  # Skip identification fields
            db_metric = {
                "server_type": server_type,
                "server_name": metrics_data.get("server_name", "Unknown"),
                "server_ip": metrics_data.get("server_ip", "Unknown"),
                "metric_name": key,
                "metric_value": str(value),
                "unit": get_metric_unit(key, server_type)
            }
            db_metrics.append(db_metric)
    
    return db_metrics


def get_metric_unit(metric_name: str, server_type: str) -> str:
    """
    Get the appropriate unit for a metric based on its name and server type.
    
    Args:
        metric_name: Name of the metric
        server_type: Type of server
    
    Returns:
        Unit string for the metric
    """
    # Common metric units
    if "percent" in metric_name or "usage" in metric_name:
        return "%"
    elif "count" in metric_name or "sessions" in metric_name or "calls" in metric_name:
        return "count"
    elif "time" in metric_name or "duration" in metric_name:
        return "seconds"
    elif "bandwidth" in metric_name:
        return "Mbps"
    elif "jitter" in metric_name:
        return "ms"
    elif "loss" in metric_name:
        return "%"
    else:
        return "units"


# =============================================================================
# Background Polling Task
# =============================================================================

async def polling_loop():
    """
    Background task that continuously collects metrics at fixed intervals.
    
    This runs indefinitely until cancelled. Each iteration:
    1. Collects metrics from all sources
    2. Waits for the polling interval
    3. Repeats
    
    The asyncio.sleep allows other tasks to run during the wait period.
    """
    logger.info(f"Polling loop started (interval: {POLLING_INTERVAL} seconds)")
    
    while True:
        try:
            # Run the blocking collection in a thread pool
            result = await asyncio.to_thread(collect_all_metrics)
            
            if result["success"]:
                logger.info(
                    f"Collection cycle complete: {result['total_saved']} metrics saved"
                )
            else:
                logger.warning(
                    f"Collection cycle had errors: {len(result['errors'])} errors"
                )
        
        except asyncio.CancelledError:
            # Graceful shutdown
            logger.info("Polling loop cancelled")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error in polling loop: {str(e)}")
        
        # Wait for next collection cycle
        logger.debug(f"Waiting {POLLING_INTERVAL} seconds until next collection...")
        await asyncio.sleep(POLLING_INTERVAL)


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/health", tags=["health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for container orchestration.
    Returns service status and basic statistics.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "proxy-gateway",
        "polling_enabled": ENABLE_POLLING,
        "polling_interval_seconds": POLLING_INTERVAL,
        "last_collection": last_collection_time.isoformat() if last_collection_time else None,
        "total_metrics_collected": metrics_collected_count
    }


@app.get("/api/collect", tags=["collection"])
async def trigger_collection(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Manually trigger a metrics collection cycle.
    
    This endpoint can be called to force immediate collection, independent
    of the background polling schedule. Useful for:
    - On-demand data refresh
    - Testing the collection pipeline
    - Recovery from failures
    
    Returns:
        Collection result summary
    """
    logger.info("Manual collection triggered via API")
    result = collect_all_metrics()
    
    if not result["success"]:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Collection completed with errors",
                "errors": result["errors"],
                "partial_results": {
                    "uccx_metrics_count": result["uccx_metrics_count"],
                    "cucm_metrics_count": result["cucm_metrics_count"],
                    "total_saved": result["total_saved"]
                }
            }
        )
    
    return result


@app.get("/api/metrics/recent", tags=["metrics"])
async def get_recent_metrics(
    limit: int = 100,
    server_type: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retrieve recently collected metrics from the database.
    
    Args:
        limit: Maximum number of records to return (default: 100)
        server_type: Optional filter by server type ('uccx' or 'cucm')
    
    Returns:
        List of recent metrics with metadata
    """
    query = db.query(TelephonyMetric)
    
    if server_type:
        query = query.filter(TelephonyMetric.server_type == server_type)
    
    metrics = (
        query.order_by(TelephonyMetric.timestamp.desc())
        .limit(limit)
        .all()
    )
    
    return {
        "count": len(metrics),
        "limit": limit,
        "server_type_filter": server_type,
        "metrics": [m.to_dict() for m in metrics]
    }


@app.get("/api/metrics/summary", tags=["metrics"])
async def get_metrics_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get a summary of collected metrics statistics.
    
    Returns:
        Aggregate statistics about the metrics in the database
    """
    from sqlalchemy import func
    
    # Get counts by server type
    server_counts = (
        db.query(
            TelephonyMetric.server_type,
            func.count(TelephonyMetric.id).label("count")
        )
        .group_by(TelephonyMetric.server_type)
        .all()
    )
    
    # Get total count
    total_count = db.query(TelephonyMetric).count()
    
    # Get time range
    oldest = db.query(TelephonyMetric).order_by(TelephonyMetric.timestamp.asc()).first()
    newest = db.query(TelephonyMetric).order_by(TelephonyMetric.timestamp.desc()).first()
    
    return {
        "total_metrics": total_count,
        "by_server_type": {s[0]: s[1] for s in server_counts},
        "time_range": {
            "oldest": oldest.timestamp.isoformat() if oldest else None,
            "newest": newest.timestamp.isoformat() if newest else None
        }
    }


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler to ensure all errors return JSON.
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# =============================================================================
# Application Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        proxy_headers=True
    )
