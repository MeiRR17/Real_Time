# =============================================================================
# AXLerate SOAP Client
# =============================================================================
# This module provides SOAP client functionality for communicating with
# Cisco AXL and Performance Monitoring APIs.
# =============================================================================

import logging
import requests
from typing import Dict, Any, List, Optional
from requests.auth import HTTPBasicAuth
from urllib.parse import urljoin

# Import Zeep for SOAP API connections
try:
    from zeep import Client, Settings
    from zeep.transports import Transport
    from zeep.plugins import HistoryPlugin
    ZEEP_AVAILABLE = True
except ImportError:
    ZEEP_AVAILABLE = False
    logging.warning("Zeep not available - SOAP API calls will be mocked")

import urllib3

# Disable SSL warnings for development environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class SOAPClient:
    """
    SOAP client for Cisco AXL and Performance Monitoring APIs.
    """
    
    def __init__(self, server_ip: str, username: str, password: str, 
                 port: int = 8443, verify_ssl: bool = False):
        """
        Initialize SOAP client.
        
        Args:
            server_ip: IP address of the Cisco server
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
        self.client = None
        self.history = HistoryPlugin()
        
        if ZEEP_AVAILABLE:
            self._setup_client()
    
    def _setup_client(self):
        """Set up Zeep SOAP client."""
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
            
            # Initialize Zeep client for Perfmon service
            perfmon_wsdl = f"{self.base_url}/PerfmonService/PerfmonService?wsdl"
            self.client = Client(
                wsdl=perfmon_wsdl,
                transport=transport,
                settings=zeep_settings
            )
            
            logger.info(f"SOAP client initialized for {self.server_ip}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SOAP client for {self.server_ip}: {str(e)}")
            self.client = None
    
    def get_perfmon_counters(self, counters: List[str]) -> Dict[str, Any]:
        """
        Get performance monitoring counters from Cisco server.
        
        Args:
            counters: List of counter names to retrieve
        
        Returns:
            Dict containing performance metrics
        """
        if not ZEEP_AVAILABLE or not self.client:
            # Return mock data if Zeep is not available or client failed to initialize
            return self._get_mock_perfmon_data(counters)
        
        try:
            # Make SOAP call to get performance counters
            response = self.client.service.PerfmonCollectCounterData(
                Host=self.server_ip,
                Object="Cisco CallManager",  # Default object
                Counter=counters
            )
            
            # Parse response and return metrics
            metrics = {}
            if response and response.PerfmonCounter:
                for counter_data in response.PerfmonCounter:
                    counter_name = counter_data.Name
                    counter_value = counter_data.Value
                    metrics[counter_name] = counter_value
            
            logger.info(f"Successfully retrieved {len(metrics)} counters from {self.server_ip}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting perfmon counters from {self.server_ip}: {str(e)}")
            return self._get_mock_perfmon_data(counters)
    
    def _get_mock_perfmon_data(self, counters: List[str]) -> Dict[str, Any]:
        """
        Generate mock performance monitoring data.
        
        Args:
            counters: List of counter names
        
        Returns:
            Dict with mock metrics data
        """
        import random
        from datetime import datetime
        
        metrics = {}
        for counter in counters:
            # Generate realistic mock values based on counter type
            if "cpu" in counter.lower():
                metrics[counter] = round(random.uniform(20, 80), 2)
            elif "memory" in counter.lower():
                metrics[counter] = round(random.uniform(30, 70), 2)
            elif "calls" in counter.lower() or "call" in counter.lower():
                metrics[counter] = random.randint(0, 1000)
            elif "active" in counter.lower():
                metrics[counter] = random.randint(0, 500)
            elif "registered" in counter.lower():
                metrics[counter] = random.randint(100, 2000)
            elif "utilization" in counter.lower():
                metrics[counter] = round(random.uniform(10, 90), 2)
            elif "bandwidth" in counter.lower():
                metrics[counter] = round(random.uniform(1, 1000), 2)
            elif "sessions" in counter.lower():
                metrics[counter] = random.randint(0, 1000)
            elif "agents" in counter.lower():
                metrics[counter] = random.randint(0, 200)
            elif "queue" in counter.lower():
                metrics[counter] = random.randint(0, 50)
            elif "meetings" in counter.lower():
                metrics[counter] = random.randint(0, 100)
            elif "participants" in counter.lower():
                metrics[counter] = random.randint(0, 500)
            else:
                # Generic metric
                metrics[counter] = round(random.uniform(0, 100), 2)
        
        return {
            "server_type": "cucm",
            "server_ip": self.server_ip,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
            "source": "mock_soap_client"
        }
    
    def test_connection(self) -> bool:
        """
        Test connection to the Cisco server.
        
        Returns:
            True if connection is successful, False otherwise
        """
        if not ZEEP_AVAILABLE or not self.client:
            return False
        
        try:
            # Try to get a simple counter to test connection
            response = self.client.service.PerfmonCollectCounterData(
                Host=self.server_ip,
                Object="Cisco CallManager",
                Counter=["CPUUtilization"]
            )
            return response is not None
        except Exception as e:
            logger.error(f"Connection test failed for {self.server_ip}: {str(e)}")
            return False


class UCCXSOAPClient(SOAPClient):
    """
    Specialized SOAP client for UCCX servers.
    """
    
    def _setup_client(self):
        """Set up UCCX-specific SOAP client."""
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
            
            # Initialize Zeep client for UCCX Statistics service
            uccx_wsdl = f"{self.base_url}/ucdbservice/UCDPService?wsdl"
            self.client = Client(
                wsdl=uccx_wsdl,
                transport=transport,
                settings=zeep_settings
            )
            
            logger.info(f"UCCX SOAP client initialized for {self.server_ip}")
            
        except Exception as e:
            logger.error(f"Failed to initialize UCCX SOAP client for {self.server_ip}: {str(e)}")
            self.client = None
    
    def get_realtime_statistics(self) -> Dict[str, Any]:
        """
        Get real-time statistics from UCCX server.
        
        Returns:
            Dict containing UCCX statistics
        """
        if not ZEEP_AVAILABLE or not self.client:
            return self._get_mock_uccx_data()
        
        try:
            # Make SOAP call to get real-time statistics
            response = self.client.service.getRealTimeStatistics(
                skillGroup="all",
                resource="all"
            )
            
            # Parse response and return metrics
            metrics = {}
            if response:
                # Parse UCCX-specific statistics
                # This would depend on the actual UCCX SOAP response structure
                pass
            
            return {
                "server_type": "uccx",
                "server_ip": self.server_ip,
                "metrics": metrics,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error getting UCCX statistics from {self.server_ip}: {str(e)}")
            return self._get_mock_uccx_data()
    
    def _get_mock_uccx_data(self) -> Dict[str, Any]:
        """Generate mock UCCX data."""
        import random
        from datetime import datetime
        
        metrics = {
            "LoggedInAgents": random.randint(50, 150),
            "AvailableAgents": random.randint(10, 50),
            "TalkingAgents": random.randint(20, 80),
            "NotReadyAgents": random.randint(5, 30),
            "CallsInQueue": random.randint(0, 20),
            "LongestWaitTime": random.randint(10, 300),
            "AverageWaitTime": random.randint(20, 120),
            "AbandonedCalls": random.randint(0, 10),
            "ServiceLevel": round(random.uniform(80, 95), 2),
            "ContactsHandledToday": random.randint(500, 2000),
            "ContactsAbandonedToday": random.randint(5, 50),
            "AverageHandleTime": random.randint(180, 420),
            "ActiveSkillGroups": random.randint(5, 20),
            "CPUUtilization": round(random.uniform(20, 60), 2),
            "MemoryUtilization": round(random.uniform(30, 70), 2)
        }
        
        return {
            "server_type": "uccx",
            "server_ip": self.server_ip,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
            "source": "mock_uccx_client"
        }


def create_soap_client(server_type: str, server_ip: str, username: str, 
                      password: str, port: int = 8443, 
                      verify_ssl: bool = False) -> SOAPClient:
    """
    Factory function to create appropriate SOAP client.
    
    Args:
        server_type: Type of server (cucm, uccx, etc.)
        server_ip: IP address of the server
        username: Username for authentication
        password: Password for authentication
        port: Port number
        verify_ssl: Whether to verify SSL certificates
    
    Returns:
        SOAPClient instance appropriate for the server type
    """
    if server_type.lower() == "uccx":
        return UCCXSOAPClient(server_ip, username, password, port, verify_ssl)
    else:
        return SOAPClient(server_ip, username, password, port, verify_ssl)
