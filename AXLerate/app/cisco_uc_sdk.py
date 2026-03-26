# =============================================================================
# Cisco Unified Communications SDK
# =============================================================================
# Comprehensive SDK for Cisco UCM SOAP APIs including:
# - AXL API (Administrative XML Layer)
# - Perfmon API (Performance Monitoring)
# - RisPort API (Real-Time Information Service)
# - Control Center Services API (Serviceability)
#
# Features:
# - Robust error handling and type safety
# - Comprehensive CRUD operations
# - Real-time device monitoring
# - Service management capabilities
# - Production-ready with extensive logging
# =============================================================================

import logging
import requests
from typing import Dict, Any, List, Optional, Union, TypedDict, Callable
from requests.auth import HTTPBasicAuth
from urllib.parse import urljoin
from datetime import datetime
from enum import Enum

# Import Zeep for SOAP API connections
try:
    from zeep import Client, Settings
    from zeep.transports import Transport
    from zeep.plugins import HistoryPlugin
    from zeep.exceptions import Fault, TransportError
    ZEEP_AVAILABLE = True
except ImportError:
    ZEEP_AVAILABLE = False
    logging.warning("Zeep not available - SOAP API calls will be mocked")

import urllib3

# Disable SSL warnings for development environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# =============================================================================
# Type Definitions and Data Models
# =============================================================================

class DeviceStatus(str, Enum):
    """Device registration status enumeration."""
    REGISTERED = "Registered"
    UNREGISTERED = "Unregistered"
    REJECTED = "Rejected"
    UNKNOWN = "Unknown"

class ServiceStatus(str, Enum):
    """Service status enumeration."""
    STARTED = "Started"
    STOPPED = "Stopped"
    PARTIALLY_SERVICING = "Partially Servicing"
    OUT_OF_SERVICE = "Out of Service"
    UNKNOWN = "Unknown"

class ServiceAction(str, Enum):
    """Service control action enumeration."""
    START = "Start"
    STOP = "Stop"
    RESTART = "Restart"

# TypedDict definitions for structured data
class PhoneInfo(TypedDict):
    """Phone information structure."""
    uuid: str
    name: str
    description: Optional[str]
    product: str
    model: str
    protocol: str
    device_pool: str
    calling_search_space: Optional[str]
    lines: List[str]

class UserInfo(TypedDict):
    """User information structure."""
    userid: str
    first_name: str
    last_name: str
    department: Optional[str]
    device_pool: Optional[str]
    primary_extension: Optional[str]
    associated_devices: List[str]

class LineInfo(TypedDict):
    """Line information structure."""
    pattern: str
    description: Optional[str]
    route_partition: str
    calling_search_space: Optional[str]
    usage: str

class DeviceInfo(TypedDict):
    """Real-time device information from RisPort."""
    name: str
    ip_address: str
    description: str
    model: str
    status: DeviceStatus
    timestamp: str
    cucm_node: str

class PerfmonCounter(TypedDict):
    """Performance counter information."""
    name: str
    value: Union[str, int, float]
    timestamp: str

class ServiceInfo(TypedDict):
    """Service information structure."""
    name: str
    status: ServiceStatus
    server: str
    timestamp: str

# =============================================================================
# Base Client Class
# =============================================================================

class BaseCiscoClient:
    """
    Base client for Cisco UCM SOAP APIs.
    Provides common functionality for authentication, connection management,
    and error handling.
    """
    
    def __init__(self, server_ip: str, username: str, password: str, 
                 port: int = 8443, verify_ssl: bool = False):
        """
        Initialize base Cisco client.
        
        Args:
            server_ip: IP address of the Cisco UCM server
            username: Username for authentication
            password: Password for authentication
            port: Port number (default: 8443)
            verify_ssl: Whether to verify SSL certificates
        """
        self.server_ip = server_ip
        self.username = username
        self.password = password
        self.port = port
        self.verify_ssl = verify_ssl
        self.base_url = f"https://{server_ip}:{port}"
        self.history = HistoryPlugin()
        self._clients: Dict[str, Client] = {}
        
        if ZEEP_AVAILABLE:
            self._setup_base_client()
    
    def _setup_base_client(self):
        """Set up base SOAP client configuration."""
        try:
            # Create session with authentication
            session = requests.Session()
            session.auth = HTTPBasicAuth(self.username, self.password)
            session.verify = self.verify_ssl
            
            # Create transport with session
            transport = Transport(session=session, timeout=30)
            
            # Configure Zeep settings
            zeep_settings = Settings(
                strict=False,
                xml_huge_tree=True,
                force_https=True,
                plugins=[self.history]
            )
            
            self._base_transport = transport
            self._base_settings = zeep_settings
            
            logger.info(f"Base Cisco client initialized for {self.server_ip}")
            
        except Exception as e:
            logger.error(f"Failed to initialize base Cisco client for {self.server_ip}: {str(e)}")
            raise
    
    def _get_client(self, service_name: str, wsdl_path: str) -> Client:
        """
        Get or create a SOAP client for a specific service.
        
        Args:
            service_name: Name of the service (for caching)
            wsdl_path: WSDL endpoint path
        
        Returns:
            Configured Zeep Client instance
        """
        if service_name not in self._clients:
            try:
                full_wsdl_path = f"{self.base_url}/{wsdl_path}"
                self._clients[service_name] = Client(
                    wsdl=full_wsdl_path,
                    transport=self._base_transport,
                    settings=self._base_settings
                )
                logger.info(f"Created {service_name} client for {self.server_ip}")
            except Exception as e:
                logger.error(f"Failed to create {service_name} client: {str(e)}")
                raise
        
        return self._clients[service_name]
    
    def _handle_soap_error(self, error: Exception, operation: str) -> Dict[str, Any]:
        """
        Handle SOAP errors and return standardized response.
        
        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
        
        Returns:
            Standardized error response
        """
        error_msg = f"SOAP error during {operation}: {str(error)}"
        logger.error(error_msg)
        
        if isinstance(error, Fault):
            return {
                "success": False,
                "error": error.message,
                "code": error.code,
                "operation": operation,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "error": str(error),
                "operation": operation,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def test_connection(self) -> bool:
        """
        Test connection to the Cisco server.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to create a basic client to test connection
            self._get_client("test", "axl/")
            return True
        except Exception as e:
            logger.error(f"Connection test failed for {self.server_ip}: {str(e)}")
            return False

# =============================================================================
# AXL API Client
# =============================================================================

class AXLClient(BaseCiscoClient):
    """
    Client for Cisco UCM AXL (Administrative XML Layer) API.
    Provides comprehensive CRUD operations for UCM configuration.
    """
    
    def __init__(self, server_ip: str, username: str, password: str, 
                 port: int = 8443, verify_ssl: bool = False):
        """
        Initialize AXL client.
        
        Args:
            server_ip: IP address of the Cisco UCM server
            username: Username for authentication
            password: Password for authentication
            port: Port number (default: 8443)
            verify_ssl: Whether to verify SSL certificates
        """
        super().__init__(server_ip, username, password, port, verify_ssl)
        self.axl_version = "12.5"  # Default AXL version
    
    def _get_axl_client(self) -> Client:
        """Get AXL SOAP client."""
        return self._get_client("axl", f"axl/{self.axl_version}/")
    
    # SQL Operations
    def execute_sql_query(self, sql_query: str) -> Dict[str, Any]:
        """
        Execute SQL query on UCM database.
        
        Args:
            sql_query: SQL query to execute (SELECT statements only)
        
        Returns:
            Query results or error information
        """
        try:
            client = self._get_axl_client()
            response = client.service.executeSQLQuery(sql=sql_query)
            
            return {
                "success": True,
                "data": response,
                "query": sql_query,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, "execute_sql_query")
    
    def execute_sql_update(self, sql_update: str) -> Dict[str, Any]:
        """
        Execute SQL update on UCM database.
        
        Args:
            sql_update: SQL update statement (INSERT, UPDATE, DELETE)
        
        Returns:
            Update results or error information
        """
        try:
            client = self._get_axl_client()
            response = client.service.executeSQLUpdate(sql=sql_update)
            
            return {
                "success": True,
                "data": response,
                "update": sql_update,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, "execute_sql_update")
    
    # Phone Operations
    def get_phone(self, phone_name: str) -> Dict[str, Any]:
        """
        Get phone information by name.
        
        Args:
            phone_name: Phone name/pattern
        
        Returns:
            Phone information or error
        """
        try:
            client = self._get_axl_client()
            response = client.service.getPhone(name=phone_name)
            
            if response['return']:
                phone_data = response['return']['phone']
                return {
                    "success": True,
                    "data": {
                        "uuid": phone_data.get('uuid', ''),
                        "name": phone_data.get('name', ''),
                        "description": phone_data.get('description', ''),
                        "product": phone_data.get('product', ''),
                        "model": phone_data.get('model', ''),
                        "protocol": phone_data.get('protocol', ''),
                        "device_pool": phone_data.get('devicePool', {}).get('name', ''),
                        "calling_search_space": phone_data.get('callingSearchSpace', {}).get('name', ''),
                        "lines": [line.get('pattern', '') for line in phone_data.get('lines', {}).get('line', [])]
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"Phone {phone_name} not found",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return self._handle_soap_error(e, f"get_phone({phone_name})")
    
    def add_phone(self, phone_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new phone to UCM.
        
        Args:
            phone_data: Dictionary containing phone configuration
        
        Returns:
            Creation result or error
        """
        try:
            client = self._get_axl_client()
            response = client.service.addPhone(phone=phone_data)
            
            return {
                "success": True,
                "uuid": response['return'],
                "data": phone_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, "add_phone")
    
    def update_phone(self, phone_name: str, phone_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update existing phone in UCM.
        
        Args:
            phone_name: Phone name to update
            phone_data: Updated phone configuration
        
        Returns:
            Update result or error
        """
        try:
            client = self._get_axl_client()
            response = client.service.updatePhone(name=phone_name, phone=phone_data)
            
            return {
                "success": True,
                "data": phone_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, f"update_phone({phone_name})")
    
    def delete_phone(self, phone_name: str) -> Dict[str, Any]:
        """
        Delete phone from UCM.
        
        Args:
            phone_name: Phone name to delete
        
        Returns:
            Deletion result or error
        """
        try:
            client = self._get_axl_client()
            response = client.service.removePhone(name=phone_name)
            
            return {
                "success": True,
                "phone_name": phone_name,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, f"delete_phone({phone_name})")
    
    # User Operations
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get user information by user ID.
        
        Args:
            user_id: User ID to retrieve
        
        Returns:
            User information or error
        """
        try:
            client = self._get_axl_client()
            response = client.service.getUser(userid=user_id)
            
            if response['return']:
                user_data = response['return']['user']
                return {
                    "success": True,
                    "data": {
                        "userid": user_data.get('userid', ''),
                        "first_name": user_data.get('firstName', ''),
                        "last_name": user_data.get('lastName', ''),
                        "department": user_data.get('department', ''),
                        "device_pool": user_data.get('devicePool', {}).get('name', ''),
                        "primary_extension": user_data.get('primaryExtension', {}).get('pattern', ''),
                        "associated_devices": [device.get('name', '') for device in user_data.get('associatedDevices', {}).get('device', [])]
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"User {user_id} not found",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return self._handle_soap_error(e, f"get_user({user_id})")
    
    def add_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new user to UCM.
        
        Args:
            user_data: Dictionary containing user configuration
        
        Returns:
            Creation result or error
        """
        try:
            client = self._get_axl_client()
            response = client.service.addUser(user=user_data)
            
            return {
                "success": True,
                "uuid": response['return'],
                "data": user_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, "add_user")
    
    # Line Operations
    def get_line(self, pattern: str, partition: str) -> Dict[str, Any]:
        """
        Get line information by pattern and partition.
        
        Args:
            pattern: Directory number pattern
            partition: Route partition name
        
        Returns:
            Line information or error
        """
        try:
            client = self._get_axl_client()
            response = client.service.getLine(
                pattern=pattern,
                routePartitionName=partition
            )
            
            if response['return']:
                line_data = response['return']['line']
                return {
                    "success": True,
                    "data": {
                        "pattern": line_data.get('pattern', ''),
                        "description": line_data.get('description', ''),
                        "route_partition": line_data.get('routePartition', {}).get('name', ''),
                        "calling_search_space": line_data.get('callingSearchSpace', {}).get('name', ''),
                        "usage": line_data.get('usage', '')
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"Line {pattern} in partition {partition} not found",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return self._handle_soap_error(e, f"get_line({pattern}, {partition})")
    
    def add_line(self, line_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new line to UCM.
        
        Args:
            line_data: Dictionary containing line configuration
        
        Returns:
            Creation result or error
        """
        try:
            client = self._get_axl_client()
            response = client.service.addLine(line=line_data)
            
            return {
                "success": True,
                "uuid": response['return'],
                "data": line_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, "add_line")
    
    # Route Pattern Operations
    def get_route_pattern(self, pattern: str, partition: str) -> Dict[str, Any]:
        """
        Get route pattern information.
        
        Args:
            pattern: Route pattern
            partition: Route partition name
        
        Returns:
            Route pattern information or error
        """
        try:
            client = self._get_axl_client()
            response = client.service.getRoutePattern(
                pattern=pattern,
                routePartitionName=partition
            )
            
            if response['return']:
                pattern_data = response['return']['routePattern']
                return {
                    "success": True,
                    "data": pattern_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"Route pattern {pattern} not found",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return self._handle_soap_error(e, f"get_route_pattern({pattern})")
    
    def add_route_pattern(self, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new route pattern.
        
        Args:
            pattern_data: Dictionary containing route pattern configuration
        
        Returns:
            Creation result or error
        """
        try:
            client = self._get_axl_client()
            response = client.service.addRoutePattern(routePattern=pattern_data)
            
            return {
                "success": True,
                "uuid": response['return'],
                "data": pattern_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, "add_route_pattern")
    
    # Partition Operations
    def get_route_partition(self, partition_name: str) -> Dict[str, Any]:
        """
        Get route partition information.
        
        Args:
            partition_name: Route partition name
        
        Returns:
            Route partition information or error
        """
        try:
            client = self._get_axl_client()
            response = client.service.getRoutePartition(name=partition_name)
            
            if response['return']:
                partition_data = response['return']['routePartition']
                return {
                    "success": True,
                    "data": partition_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"Route partition {partition_name} not found",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return self._handle_soap_error(e, f"get_route_partition({partition_name})")
    
    def add_route_partition(self, partition_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new route partition.
        
        Args:
            partition_data: Dictionary containing partition configuration
        
        Returns:
            Creation result or error
        """
        try:
            client = self._get_axl_client()
            response = client.service.addRoutePartition(routePartition=partition_data)
            
            return {
                "success": True,
                "uuid": response['return'],
                "data": partition_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, "add_route_partition")
    
    # Calling Search Space Operations
    def get_calling_search_space(self, css_name: str) -> Dict[str, Any]:
        """
        Get calling search space information.
        
        Args:
            css_name: Calling search space name
        
        Returns:
            CSS information or error
        """
        try:
            client = self._get_axl_client()
            response = client.service.getCallingSearchSpace(name=css_name)
            
            if response['return']:
                css_data = response['return']['callingSearchSpace']
                return {
                    "success": True,
                    "data": css_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"Calling Search Space {css_name} not found",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return self._handle_soap_error(e, f"get_calling_search_space({css_name})")
    
    def add_calling_search_space(self, css_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new calling search space.
        
        Args:
            css_data: Dictionary containing CSS configuration
        
        Returns:
            Creation result or error
        """
        try:
            client = self._get_axl_client()
            response = client.service.addCallingSearchSpace(callingSearchSpace=css_data)
            
            return {
                "success": True,
                "uuid": response['return'],
                "data": css_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, "add_calling_search_space")

# =============================================================================
# Perfmon API Client
# =============================================================================

class PerfmonClient(BaseCiscoClient):
    """
    Client for Cisco UCM Performance Monitoring API.
    Provides real-time performance metrics and counter information.
    """
    
    def __init__(self, server_ip: str, username: str, password: str, 
                 port: int = 8443, verify_ssl: bool = False):
        """
        Initialize Perfmon client.
        
        Args:
            server_ip: IP address of the Cisco UCM server
            username: Username for authentication
            password: Password for authentication
            port: Port number (default: 8443)
            verify_ssl: Whether to verify SSL certificates
        """
        super().__init__(server_ip, username, password, port, verify_ssl)
    
    def _get_perfmon_client(self) -> Client:
        """Get Perfmon SOAP client."""
        return self._get_client("perfmon", "PerfmonService/PerfmonService")
    
    def perfmon_collect_counter_data(self, host: str, object_name: str, 
                                   counters: List[str]) -> Dict[str, Any]:
        """
        Collect performance counter data.
        
        Args:
            host: Host name or IP address
            object_name: Performance object name (e.g., "Cisco CallManager")
            counters: List of counter names to collect
        
        Returns:
            Performance counter data or error
        """
        try:
            client = self._get_perfmon_client()
            response = client.service.PerfmonCollectCounterData(
                Host=host,
                Object=object_name,
                Counter=counters
            )
            
            # Parse response
            metrics = []
            if response and response.PerfmonCounter:
                for counter_data in response.PerfmonCounter:
                    metrics.append({
                        "name": counter_data.Name,
                        "value": counter_data.Value,
                        "timestamp": counter_data.Timestamp if hasattr(counter_data, 'Timestamp') else datetime.utcnow().isoformat()
                    })
            
            return {
                "success": True,
                "host": host,
                "object": object_name,
                "counters": counters,
                "data": metrics,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, f"perfmon_collect_counter_data({host}, {object_name})")
    
    def perfmon_list_instances(self, host: str, object_name: str) -> Dict[str, Any]:
        """
        List available performance counter instances for an object.
        
        Args:
            host: Host name or IP address
            object_name: Performance object name
        
        Returns:
            List of available instances or error
        """
        try:
            client = self._get_perfmon_client()
            response = client.service.PerfmonListInstances(
                Host=host,
                Object=object_name
            )
            
            instances = []
            if response and response.InstanceInfo:
                for instance in response.InstanceInfo:
                    instances.append({
                        "name": instance.Name,
                        "description": getattr(instance, 'Description', ''),
                        "counters": getattr(instance, 'Counter', [])
                    })
            
            return {
                "success": True,
                "host": host,
                "object": object_name,
                "instances": instances,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, f"perfmon_list_instances({host}, {object_name})")
    
    def perfmon_list_counters(self, host: str, object_name: str) -> Dict[str, Any]:
        """
        List available performance counters for an object.
        
        Args:
            host: Host name or IP address
            object_name: Performance object name
        
        Returns:
            List of available counters or error
        """
        try:
            client = self._get_perfmon_client()
            response = client.service.PerfmonListCounters(
                Host=host,
                Object=object_name
            )
            
            counters = []
            if response and response.CounterInfo:
                for counter in response.CounterInfo:
                    counters.append({
                        "name": counter.Name,
                        "description": getattr(counter, 'Description', ''),
                        "type": getattr(counter, 'CounterType', ''),
                        "unit": getattr(counter, 'Unit', '')
                    })
            
            return {
                "success": True,
                "host": host,
                "object": object_name,
                "counters": counters,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, f"perfmon_list_counters({host}, {object_name})")
    
    def get_system_metrics(self, host: str) -> Dict[str, Any]:
        """
        Get common system performance metrics.
        
        Args:
            host: Host name or IP address
        
        Returns:
            System performance metrics or error
        """
        common_counters = [
            "CPUUtilization",
            "MemoryUtilization",
            "RegisteredPhones",
            "ActiveCalls",
            "CallsInProgress",
            "TotalCalls",
            "DiskUsage"
        ]
        
        return self.perfmon_collect_counter_data(host, "Cisco CallManager", common_counters)

# =============================================================================
# RisPort API Client
# =============================================================================

class RisPortClient(BaseCiscoClient):
    """
    Client for Cisco UCM RisPort (Real-Time Information Service) API.
    Provides real-time device status and registration information.
    """
    
    def __init__(self, server_ip: str, username: str, password: str, 
                 port: int = 8443, verify_ssl: bool = False):
        """
        Initialize RisPort client.
        
        Args:
            server_ip: IP address of the Cisco UCM server
            username: Username for authentication
            password: Password for authentication
            port: Port number (default: 8443)
            verify_ssl: Whether to verify SSL certificates
        """
        super().__init__(server_ip, username, password, port, verify_ssl)
    
    def _get_risport_client(self) -> Client:
        """Get RisPort SOAP client."""
        return self._get_client("risport", "realtimeservice/services/RisPort")
    
    def select_cm_device(self, device_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select CM device information based on criteria.
        
        Args:
            device_criteria: Dictionary containing device selection criteria
        
        Returns:
            Device information or error
        """
        try:
            client = self._get_risport_client()
            response = client.service.SelectCmDevice(
                CmSelectionCriteria=device_criteria
            )
            
            devices = []
            if response and response.SelectCmDeviceResult:
                for device in response.SelectCmDeviceResult:
                    device_info = {
                        "name": getattr(device, 'Name', ''),
                        "ip_address": getattr(device, 'IPAddress', {}).get('IP', ''),
                        "description": getattr(device, 'Description', ''),
                        "model": getattr(device, 'Model', ''),
                        "status": getattr(device, 'Status', ''),
                        "timestamp": getattr(device, 'TimeStamp', ''),
                        "cucm_node": getattr(device, 'CmName', '')
                    }
                    devices.append(device_info)
            
            return {
                "success": True,
                "devices": devices,
                "criteria": device_criteria,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, "select_cm_device")
    
    def get_device_by_name(self, device_names: List[str]) -> Dict[str, Any]:
        """
        Get device information by device names.
        
        Args:
            device_names: List of device names
        
        Returns:
            Device information or error
        """
        criteria = {
            "MaxReturnedDevices": len(device_names),
            "DeviceClass": "Phone",
            "SelectBy": "Name",
            "SelectItems": {"item": device_names}
        }
        
        return self.select_cm_device(criteria)
    
    def get_device_by_mac(self, mac_addresses: List[str]) -> Dict[str, Any]:
        """
        Get device information by MAC addresses.
        
        Args:
            mac_addresses: List of MAC addresses
        
        Returns:
            Device information or error
        """
        criteria = {
            "MaxReturnedDevices": len(mac_addresses),
            "DeviceClass": "Phone",
            "SelectBy": "Name",  # MAC addresses are often used as device names
            "SelectItems": {"item": mac_addresses}
        }
        
        return self.select_cm_device(criteria)
    
    def get_all_registered_devices(self) -> Dict[str, Any]:
        """
        Get all registered devices.
        
        Returns:
            All registered device information or error
        """
        criteria = {
            "MaxReturnedDevices": 1000,  # Large number to get all devices
            "DeviceClass": "Phone",
            "SelectBy": "Name",
            "Status": "Registered"
        }
        
        return self.select_cm_device(criteria)

# =============================================================================
# Control Center Services API Client
# =============================================================================

class ControlCenterClient(BaseCiscoClient):
    """
    Client for Cisco UCM Control Center Services API.
    Provides service management and monitoring capabilities.
    """
    
    def __init__(self, server_ip: str, username: str, password: str, 
                 port: int = 8443, verify_ssl: bool = False):
        """
        Initialize Control Center client.
        
        Args:
            server_ip: IP address of the Cisco UCM server
            username: Username for authentication
            password: Password for authentication
            port: Port number (default: 8443)
            verify_ssl: Whether to verify SSL certificates
        """
        super().__init__(server_ip, username, password, port, verify_ssl)
    
    def _get_control_center_client(self) -> Client:
        """Get Control Center SOAP client."""
        return self._get_client("control_center", "controlcenterservice/services/ControlCenterService")
    
    def soap_do_control_services(self, server_name: str, service_names: List[str]) -> Dict[str, Any]:
        """
        Get status of specific services on a server.
        
        Args:
            server_name: Server name
            service_names: List of service names to check
        
        Returns:
            Service status information or error
        """
        try:
            client = self._get_control_center_client()
            
            # Prepare service list
            service_list = {"ServiceName": service_names}
            
            response = client.service.soapDoControlServices(
                ServerName=server_name,
                ServiceList=service_list
            )
            
            services = []
            if response and response.ControlServiceResponse:
                for service in response.ControlServiceResponse:
                    service_info = {
                        "name": getattr(service, 'ServiceName', ''),
                        "status": getattr(service, 'ServiceState', ''),
                        "server": server_name,
                        "timestamp": getattr(service, 'TimeStamp', '')
                    }
                    services.append(service_info)
            
            return {
                "success": True,
                "server": server_name,
                "services": services,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, f"soap_do_control_services({server_name})")
    
    def soap_do_service_control(self, server_name: str, service_name: str, 
                              action: str) -> Dict[str, Any]:
        """
        Control a service (start/stop/restart).
        
        Args:
            server_name: Server name
            service_name: Service name to control
            action: Action to perform (Start/Stop/Restart)
        
        Returns:
            Service control result or error
        """
        try:
            client = self._get_control_center_client()
            
            response = client.service.soapDoServiceControl(
                ServerName=server_name,
                ServiceName=service_name,
                ControlAction=action
            )
            
            return {
                "success": True,
                "server": server_name,
                "service": service_name,
                "action": action,
                "response": response,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return self._handle_soap_error(e, f"soap_do_service_control({server_name}, {service_name}, {action})")
    
    def get_service_status(self, server_name: str, service_name: str) -> Dict[str, Any]:
        """
        Get status of a specific service.
        
        Args:
            server_name: Server name
            service_name: Service name
        
        Returns:
            Service status or error
        """
        return self.soap_do_control_services(server_name, [service_name])
    
    def start_service(self, server_name: str, service_name: str) -> Dict[str, Any]:
        """
        Start a service.
        
        Args:
            server_name: Server name
            service_name: Service name to start
        
        Returns:
            Service start result or error
        """
        return self.soap_do_service_control(server_name, service_name, "Start")
    
    def stop_service(self, server_name: str, service_name: str) -> Dict[str, Any]:
        """
        Stop a service.
        
        Args:
            server_name: Server name
            service_name: Service name to stop
        
        Returns:
            Service stop result or error
        """
        return self.soap_do_service_control(server_name, service_name, "Stop")
    
    def restart_service(self, server_name: str, service_name: str) -> Dict[str, Any]:
        """
        Restart a service.
        
        Args:
            server_name: Server name
            service_name: Service name to restart
        
        Returns:
            Service restart result or error
        """
        return self.soap_do_service_control(server_name, service_name, "Restart")
    
    def get_all_services_status(self, server_name: str) -> Dict[str, Any]:
        """
        Get status of all services on a server.
        
        Args:
            server_name: Server name
        
        Returns:
            All services status or error
        """
        common_services = [
            "Cisco CallManager",
            "Cisco CTI Manager",
            "Cisco Tftp",
            "Cisco IP Voice Media Streaming App",
            "Cisco DRF Master",
            "Cisco DRF Local"
        ]
        
        return self.soap_do_control_services(server_name, common_services)

# =============================================================================
# Unified Cisco UC SDK
# =============================================================================

class CiscoUCSDK:
    """
    Unified Cisco UC SDK providing access to all major UCM SOAP APIs.
    This is the main interface for developers to interact with Cisco UCM.
    """
    
    def __init__(self, server_ip: str, username: str, password: str, 
                 port: int = 8443, verify_ssl: bool = False):
        """
        Initialize Cisco UC SDK.
        
        Args:
            server_ip: IP address of the Cisco UCM server
            username: Username for authentication
            password: Password for authentication
            port: Port number (default: 8443)
            verify_ssl: Whether to verify SSL certificates
        
        Example:
            >>> sdk = CiscoUCSDK("192.168.1.100", "admin", "password")
            >>> phones = sdk.axl.get_phone("SEP001122334455")
            >>> devices = sdk.risport.get_device_by_name(["SEP001122334455"])
            >>> metrics = sdk.perfmon.get_system_metrics("192.168.1.100")
        """
        self.server_ip = server_ip
        self.username = username
        self.password = password
        self.port = port
        self.verify_ssl = verify_ssl
        
        # Initialize all API clients
        self.axl = AXLClient(server_ip, username, password, port, verify_ssl)
        self.perfmon = PerfmonClient(server_ip, username, password, port, verify_ssl)
        self.risport = RisPortClient(server_ip, username, password, port, verify_ssl)
        self.control_center = ControlCenterClient(server_ip, username, password, port, verify_ssl)
    
    def test_all_connections(self) -> Dict[str, Any]:
        """
        Test connections to all API endpoints.
        
        Returns:
            Connection test results for all APIs
        """
        results = {
            "server_ip": self.server_ip,
            "timestamp": datetime.utcnow().isoformat(),
            "apis": {}
        }
        
        # Test AXL
        try:
            results["apis"]["axl"] = self.axl.test_connection()
        except Exception as e:
            results["apis"]["axl"] = {"success": False, "error": str(e)}
        
        # Test Perfmon
        try:
            results["apis"]["perfmon"] = self.perfmon.test_connection()
        except Exception as e:
            results["apis"]["perfmon"] = {"success": False, "error": str(e)}
        
        # Test RisPort
        try:
            results["apis"]["risport"] = self.risport.test_connection()
        except Exception as e:
            results["apis"]["risport"] = {"success": False, "error": str(e)}
        
        # Test Control Center
        try:
            results["apis"]["control_center"] = self.control_center.test_connection()
        except Exception as e:
            results["apis"]["control_center"] = {"success": False, "error": str(e)}
        
        return results
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        Get general server information.
        
        Returns:
            Server information including version and status
        """
        try:
            # Get basic system metrics
            metrics_result = self.perfmon.get_system_metrics(self.server_ip)
            
            # Get service status
            services_result = self.control_center.get_all_services_status(self.server_ip)
            
            return {
                "success": True,
                "server_ip": self.server_ip,
                "metrics": metrics_result.get("data", []),
                "services": services_result.get("services", []),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "server_ip": self.server_ip,
                "timestamp": datetime.utcnow().isoformat()
            }

# =============================================================================
# Factory Functions
# =============================================================================

def create_cisco_sdk(server_ip: str, username: str, password: str, 
                    port: int = 8443, verify_ssl: bool = False) -> CiscoUCSDK:
    """
    Factory function to create Cisco UC SDK instance.
    
    Args:
        server_ip: IP address of the Cisco UCM server
        username: Username for authentication
        password: Password for authentication
        port: Port number (default: 8443)
        verify_ssl: Whether to verify SSL certificates
    
    Returns:
        Configured CiscoUCSDK instance
    """
    return CiscoUCSDK(server_ip, username, password, port, verify_ssl)

def create_axl_client(server_ip: str, username: str, password: str, 
                     port: int = 8443, verify_ssl: bool = False) -> AXLClient:
    """
    Factory function to create AXL client instance.
    
    Args:
        server_ip: IP address of the Cisco UCM server
        username: Username for authentication
        password: Password for authentication
        port: Port number (default: 8443)
        verify_ssl: Whether to verify SSL certificates
    
    Returns:
        Configured AXLClient instance
    """
    return AXLClient(server_ip, username, password, port, verify_ssl)

def create_perfmon_client(server_ip: str, username: str, password: str, 
                         port: int = 8443, verify_ssl: bool = False) -> PerfmonClient:
    """
    Factory function to create Perfmon client instance.
    
    Args:
        server_ip: IP address of the Cisco UCM server
        username: Username for authentication
        password: Password for authentication
        port: Port number (default: 8443)
        verify_ssl: Whether to verify SSL certificates
    
    Returns:
        Configured PerfmonClient instance
    """
    return PerfmonClient(server_ip, username, password, port, verify_ssl)

def create_risport_client(server_ip: str, username: str, password: str, 
                         port: int = 8443, verify_ssl: bool = False) -> RisPortClient:
    """
    Factory function to create RisPort client instance.
    
    Args:
        server_ip: IP address of the Cisco UCM server
        username: Username for authentication
        password: Password for authentication
        port: Port number (default: 8443)
        verify_ssl: Whether to verify SSL certificates
    
    Returns:
        Configured RisPortClient instance
    """
    return RisPortClient(server_ip, username, password, port, verify_ssl)

def create_control_center_client(server_ip: str, username: str, password: str, 
                                port: int = 8443, verify_ssl: bool = False) -> ControlCenterClient:
    """
    Factory function to create Control Center client instance.
    
    Args:
        server_ip: IP address of the Cisco UCM server
        username: Username for authentication
        password: Password for authentication
        port: Port number (default: 8443)
        verify_ssl: Whether to verify SSL certificates
    
    Returns:
        Configured ControlCenterClient instance
    """
    return ControlCenterClient(server_ip, username, password, port, verify_ssl)

# =============================================================================
# Usage Examples (for documentation)
# =============================================================================

"""
Usage Examples:

# Initialize the SDK
sdk = CiscoUCSDK("192.168.1.100", "admin", "password")

# Test all connections
results = sdk.test_all_connections()
print(results)

# AXL Operations
phone = sdk.axl.get_phone("SEP001122334455")
users = sdk.axl.execute_sql_query("SELECT * FROM user")
new_phone = sdk.axl.add_phone({
    "name": "SEP001122334456",
    "product": "Cisco 8841",
    "devicePool": {"name": "Default"},
    "lines": {"line": [{"pattern": "1001", "routePartition": {"name": "Internal"}}]}
})

# Perfmon Operations
metrics = sdk.perfmon.get_system_metrics("192.168.1.100")
cpu_metrics = sdk.perfmon.perfmon_collect_counter_data(
    "192.168.1.100", "Cisco CallManager", ["CPUUtilization", "MemoryUtilization"]
)
counters = sdk.perfmon.perfmon_list_counters("192.168.1.100", "Cisco CallManager")

# RisPort Operations
devices = sdk.risport.get_device_by_name(["SEP001122334455", "SEP001122334456"])
mac_devices = sdk.risport.get_device_by_mac(["00:11:22:33:44:55"])
all_registered = sdk.risport.get_all_registered_devices()

# Control Center Operations
services = sdk.control_center.get_all_services_status("192.168.1.100")
cm_status = sdk.control_center.get_service_status("192.168.1.100", "Cisco CallManager")
sdk.control_center.restart_service("192.168.1.100", "Cisco CTI Manager")

# Get comprehensive server info
info = sdk.get_server_info()
print(info)
"""
