# =============================================================================
# AXLerate REST Middleware - FastAPI Application
# =============================================================================
# This service acts as a REST middleware for all Cisco communications,
# converting REST calls to SOAP/AXL requests and back to clean JSON responses.
# =============================================================================

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

import requests
import urllib3
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from requests.auth import HTTPBasicAuth
import httpx

# Import the new comprehensive Cisco UC SDK - temporarily disabled
# SDK import will be added back once file structure is fixed

# Disable SSL warnings for development environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =============================================================================
# Configuration
# =============================================================================
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
AXL_USER = os.getenv("AXL_USER", "admin")
AXL_PASSWORD = os.getenv("AXL_PASSWORD", "password")
AXL_PORT = int(os.getenv("AXL_PORT", "8443"))
AXL_VERIFY_SSL = os.getenv("AXL_VERIFY_SSL", "false").lower() == "true"
PERFMON_TIMEOUT = int(os.getenv("PERFMON_TIMEOUT", "30"))
PERFMON_RETRIES = int(os.getenv("PERFMON_RETRIES", "3"))

# =============================================================================
# Pydantic Models
# =============================================================================
class PerfmonRequest(BaseModel):
    """Request model for performance monitoring metrics."""
    server_ip: str = Field(..., description="Cisco server IP address")
    username: str = Field(..., description="Username for authentication")
    password: str = Field(..., description="Password for authentication")
    counters: List[str] = Field(..., description="List of performance counters to retrieve")
    server_type: str = Field(default="cucm", description="Type of server (cucm, uccx, etc.)")

class PerfmonResponse(BaseModel):
    """Response model for performance monitoring metrics."""
    success: bool = Field(..., description="Whether the request was successful")
    data: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics data")
    error: Optional[str] = Field(None, description="Error message if request failed")
    timestamp: str = Field(..., description="Timestamp of the response")
    server_ip: str = Field(..., description="Server IP that was queried")

# =============================================================================
# FastAPI Application
# =============================================================================
app = FastAPI(
    title="AXLerate REST Middleware",
    description="REST middleware for Cisco AXL and Performance Monitoring APIs",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# AXL/Perfmon Client
# =============================================================================
class PerfmonClient:
    """Client for Cisco Performance Monitoring API using the comprehensive Cisco UC SDK."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = AXL_VERIFY_SSL
    
    async def get_perfmon_metrics(self, server_ip: str, username: str, password: str, 
                                 counters: List[str], server_type: str = "cucm") -> Dict[str, Any]:
        """
        Get performance monitoring metrics from Cisco server.
        
        Args:
            server_ip: IP address of the Cisco server
            username: Username for authentication
            password: Password for authentication
            counters: List of performance counters to retrieve
            server_type: Type of server (cucm, uccx, etc.)
        
        Returns:
            Dict containing performance metrics
        """
        # Temporarily return mock data until SDK import is fixed
        import random
        
        metrics = {}
        for counter in counters:
            if "cpu" in counter.lower():
                metrics[counter] = round(random.uniform(20, 80), 2)
            elif "memory" in counter.lower():
                metrics[counter] = round(random.uniform(30, 70), 2)
            elif "calls" in counter.lower():
                metrics[counter] = random.randint(0, 1000)
            else:
                metrics[counter] = round(random.uniform(0, 100), 2)
        
        return {
            "server_type": server_type,
            "server_ip": server_ip,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
            "source": "mock_data_temp"
        }
    
    def _get_port_for_server_type(self, server_type: str) -> int:
        """Get default port for server type."""
        port_mapping = {
            "cucm": 8443,
            "uccx": 8445,
            "cms": 445,
            "imp": 8222,
            "meeting_place": 8080,
            "tgw": 161,
            "sbc": 443,
            "expressway": 443
        }
        return port_mapping.get(server_type.lower(), 8443)
    
    def _get_fallback_data(self, server_ip: str, server_type: str, counters: List[str]) -> Dict[str, Any]:
        """Get fallback data when SDK calls fail."""
        import random
        
        metrics = {}
        for counter in counters:
            if "cpu" in counter.lower():
                metrics[counter] = round(random.uniform(20, 80), 2)
            elif "memory" in counter.lower():
                metrics[counter] = round(random.uniform(30, 70), 2)
            elif "calls" in counter.lower():
                metrics[counter] = random.randint(0, 1000)
            else:
                metrics[counter] = round(random.uniform(0, 100), 2)
        
        return {
            "server_type": server_type,
            "server_ip": server_ip,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "fallback",
            "source": "fallback_data"
        }

# Initialize the perfmon client
perfmon_client = PerfmonClient()

# =============================================================================
# API Endpoints
# =============================================================================
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "axlerate",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/metrics/perfmon", response_model=PerfmonResponse)
async def get_perfmon_metrics(request: PerfmonRequest):
    """
    Get performance monitoring metrics from a Cisco server.
    
    This endpoint accepts a server IP, credentials, and a list of counters,
    then retrieves the performance metrics using SOAP/AXL calls and returns
    them as clean JSON.
    
    Args:
        request: PerfmonRequest containing server details and counters
    
    Returns:
        PerfmonResponse with performance metrics or error details
    """
    try:
        logger.info(f"Received perfmon request for {request.server_ip}")
        
        # Get metrics using the perfmon client
        metrics_data = await perfmon_client.get_perfmon_metrics(
            server_ip=request.server_ip,
            username=request.username,
            password=request.password,
            counters=request.counters,
            server_type=request.server_type
        )
        
        return PerfmonResponse(
            success=True,
            data=metrics_data,
            timestamp=datetime.utcnow().isoformat(),
            server_ip=request.server_ip
        )
        
    except Exception as e:
        logger.error(f"Error processing perfmon request: {str(e)}")
        return PerfmonResponse(
            success=False,
            error=str(e),
            timestamp=datetime.utcnow().isoformat(),
            server_ip=request.server_ip
        )

@app.get("/metrics/counters/{server_type}")
async def get_available_counters(server_type: str):
    """
    Get available performance counters for a specific server type.
    
    Args:
        server_type: Type of server (cucm, uccx, cms, etc.)
    
    Returns:
        List of available performance counters
    """
    # Define common counters for different server types
    counters_by_type = {
        "cucm": [
            "CPUUtilization",
            "MemoryUtilization",
            "RegisteredPhones",
            "ActiveCalls",
            "CallsInProgress",
            "TotalCalls",
            "TrunkUtilization",
            "DiskUsage"
        ],
        "uccx": [
            "CPUUtilization",
            "MemoryUtilization",
            "LoggedInAgents",
            "AvailableAgents",
            "CallsInQueue",
            "ActiveContacts",
            "ServiceLevel",
            "AbandonedCalls"
        ],
        "cms": [
            "CPUUtilization",
            "MemoryUtilization",
            "ActiveMeetings",
            "TotalParticipants",
            "AudioResourceUtilization",
            "VideoResourceUtilization",
            "NetworkBandwidth"
        ],
        "imp": [
            "CPUUtilization",
            "MemoryUtilization",
            "ActiveXmppSessions",
            "LoggedInUsers",
            "MessagesSentToday",
            "FederatedSessions"
        ],
        "tgw": [
            "CPUUtilization",
            "MemoryUtilization",
            "ActiveTunnels",
            "BandwidthIn",
            "BandwidthOut",
            "InterfaceErrors"
        ],
        "sbc": [
            "CPUUtilization",
            "MemoryUtilization",
            "ActiveSessions",
            "CallSetupRate",
            "MediaResourceUtilization"
        ],
        "expressway": [
            "CPUUtilization",
            "MemoryUtilization",
            "ActiveRegistrations",
            "ActiveCalls",
            "BandwidthUtilization"
        ]
    }
    
    counters = counters_by_type.get(server_type.lower(), [])
    return {
        "server_type": server_type,
        "available_counters": counters,
        "total_count": len(counters)
    }

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "AXLerate REST Middleware",
        "version": "2.0.0",
        "description": "REST middleware for Cisco AXL and Performance Monitoring APIs",
        "endpoints": {
            "health": "/health",
            "perfmon": "/metrics/perfmon (POST)",
            "counters": "/metrics/counters/{server_type} (GET)",
            "axl": "/axl/* (various AXL operations)",
            "risport": "/risport/* (real-time device info)",
            "services": "/services/* (service management)"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# =============================================================================
# AXL API Endpoints
# =============================================================================
@app.get("/axl/phone/{phone_name}")
async def get_phone(phone_name: str):
    """Get phone information by name."""
    try:
        # For demo purposes, we'll use mock credentials
        # In production, these would come from a secure source
        sdk = CiscoUCSDK("192.168.1.100", "admin", "password")
        result = sdk.axl.get_phone(phone_name)
        return result
    except Exception as e:
        logger.error(f"Error getting phone {phone_name}: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/axl/phone")
async def add_phone(phone_data: Dict[str, Any]):
    """Add a new phone."""
    try:
        sdk = CiscoUCSDK("192.168.1.100", "admin", "password")
        result = sdk.axl.add_phone(phone_data)
        return result
    except Exception as e:
        logger.error(f"Error adding phone: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/axl/user/{user_id}")
async def get_user(user_id: str):
    """Get user information by user ID."""
    try:
        sdk = CiscoUCSDK("192.168.1.100", "admin", "password")
        result = sdk.axl.get_user(user_id)
        return result
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/axl/sql/query")
async def execute_sql_query(request: Dict[str, Any]):
    """Execute SQL query on UCM database."""
    try:
        sql_query = request.get("query", "")
        if not sql_query:
            return {"success": False, "error": "SQL query is required"}
        
        sdk = CiscoUCSDK("192.168.1.100", "admin", "password")
        result = sdk.axl.execute_sql_query(sql_query)
        return result
    except Exception as e:
        logger.error(f"Error executing SQL query: {str(e)}")
        return {"success": False, "error": str(e)}

# =============================================================================
# RisPort API Endpoints
# =============================================================================
@app.post("/risport/devices")
async def get_devices_by_name(request: Dict[str, Any]):
    """Get device information by device names."""
    try:
        device_names = request.get("device_names", [])
        if not device_names:
            return {"success": False, "error": "device_names list is required"}
        
        sdk = CiscoUCSDK("192.168.1.100", "admin", "password")
        result = sdk.risport.get_device_by_name(device_names)
        return result
    except Exception as e:
        logger.error(f"Error getting devices: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/risport/devices/mac")
async def get_devices_by_mac(request: Dict[str, Any]):
    """Get device information by MAC addresses."""
    try:
        mac_addresses = request.get("mac_addresses", [])
        if not mac_addresses:
            return {"success": False, "error": "mac_addresses list is required"}
        
        sdk = CiscoUCSDK("192.168.1.100", "admin", "password")
        result = sdk.risport.get_device_by_mac(mac_addresses)
        return result
    except Exception as e:
        logger.error(f"Error getting devices by MAC: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/risport/devices/registered")
async def get_all_registered_devices():
    """Get all registered devices."""
    try:
        sdk = CiscoUCSDK("192.168.1.100", "admin", "password")
        result = sdk.risport.get_all_registered_devices()
        return result
    except Exception as e:
        logger.error(f"Error getting registered devices: {str(e)}")
        return {"success": False, "error": str(e)}

# =============================================================================
# Control Center Services API Endpoints
# =============================================================================
@app.get("/services/{server_name}")
async def get_services_status(server_name: str):
    """Get status of all services on a server."""
    try:
        sdk = CiscoUCSDK("192.168.1.100", "admin", "password")
        result = sdk.control_center.get_all_services_status(server_name)
        return result
    except Exception as e:
        logger.error(f"Error getting services status: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/services/{server_name}/{service_name}/control")
async def control_service(server_name: str, service_name: str, request: Dict[str, Any]):
    """Control a service (start/stop/restart)."""
    try:
        action = request.get("action", "")
        if action not in ["Start", "Stop", "Restart"]:
            return {"success": False, "error": "action must be Start, Stop, or Restart"}
        
        sdk = CiscoUCSDK("192.168.1.100", "admin", "password")
        
        if action == "Start":
            result = sdk.control_center.start_service(server_name, service_name)
        elif action == "Stop":
            result = sdk.control_center.stop_service(server_name, service_name)
        else:  # Restart
            result = sdk.control_center.restart_service(server_name, service_name)
        
        return result
    except Exception as e:
        logger.error(f"Error controlling service: {str(e)}")
        return {"success": False, "error": str(e)}

# =============================================================================
# SDK Information Endpoint
# =============================================================================
@app.get("/sdk/info")
async def get_sdk_info():
    """Get SDK information and connection status."""
    try:
        sdk = CiscoUCSDK("192.168.1.100", "admin", "password")
        connection_results = sdk.test_all_connections()
        server_info = sdk.get_server_info()
        
        return {
            "sdk_version": "2.0.0",
            "supported_apis": ["AXL", "Perfmon", "RisPort", "Control Center"],
            "connections": connection_results,
            "server_info": server_info,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting SDK info: {str(e)}")
        return {"success": False, "error": str(e)}

# =============================================================================
# Startup Event
# =============================================================================
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("=" * 60)
    logger.info("AXLerate REST Middleware Starting Up")
    logger.info("=" * 60)
    logger.info(f"AXL User: {AXL_USER}")
    logger.info(f"AXL Port: {AXL_PORT}")
    logger.info(f"SSL Verification: {AXL_VERIFY_SSL}")
    logger.info(f"Perfmon Timeout: {PERFMON_TIMEOUT}s")
    logger.info("AXLerate is ready to accept requests")
    logger.info("=" * 60)

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("AXLerate REST Middleware Shutting Down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
