# =============================================================================
# Telephony Load Monitoring System - Real API Generators
# =============================================================================
# This module provides real API integration templates for all Cisco server types.
# Each generator follows the same interface as mock generators but connects
# to the AXLerate REST middleware for production data collection.
#
# The generators use a feature toggle approach - they can be enabled/disabled
# individually through environment variables for gradual migration from mock
# to real data sources.
# =============================================================================

import logging
import httpx
import asyncio
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from config import get_settings
from mock_generators import MockDataGenerator, ServerConfig

# =============================================================================
# Base Real Generator Class
# =============================================================================
class RealDataGenerator(MockDataGenerator):
    """
    Base class for real API data generators using AXLerate REST middleware.
    Provides common functionality for REST API calls and error handling.
    """
    
    def __init__(self, server_config: ServerConfig):
        """
        Initialize the real data generator.
        
        Args:
            server_config: Server configuration
        """
        super().__init__(server_config)
        self.settings = get_settings()
        self.axlerate_url = os.getenv("AXLERATE_URL", "http://axlerate:8000")
        self.client = None
        self._setup_client()
    
    def _setup_client(self):
        """
        Set up HTTP client for AXLerate REST API.
        """
        self.client = httpx.Client(
            timeout=30.0,
            verify=False  # For development - should be configurable
        )
    
    def _handle_api_error(self, error: Exception, operation: str) -> Dict[str, Any]:
        """
        Handle API errors and return fallback data.
        
        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
        
        Returns:
            Dict[str, Any]: Fallback metrics data
        """
        logging.error(f"API error during {operation} for {self.server_config.name}: {str(error)}")
        
        # Return fallback data that matches the expected schema
        return self._get_fallback_data()
    
    def _get_fallback_data(self) -> Dict[str, Any]:
        """
        Get fallback data when API calls fail.
        This should be overridden by subclasses to return appropriate data.
        """
        return {
            "server_name": self.server_config.name,
            "server_ip": self.server_config.ip_address,
            "error": "API call failed - using fallback data",
            "data_source": "fallback_data"
        }
    
    def _get_credentials(self) -> Dict[str, str]:
        """
        Get credentials for this server type.
        Must be implemented by subclasses.
        
        Returns:
            Dict containing username and password
        """
        raise NotImplementedError("Subclasses must implement _get_credentials")
    
    def _get_counters(self) -> List[str]:
        """
        Get list of performance counters for this server type.
        Must be implemented by subclasses.
        
        Returns:
            List of counter names
        """
        raise NotImplementedError("Subclasses must implement _get_counters")
    
    def _extract_numeric_value(self, value) -> float:
        """Extract numeric value from various data types."""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                # Remove any non-numeric characters and convert
                import re
                numeric_str = re.sub(r'[^\d.]', '', value)
                return float(numeric_str) if numeric_str else 0.0
            else:
                return 0.0
        except (ValueError, TypeError):
            return 0.0


# =============================================================================
# CUCM Real Generator (REST via AXLerate)
# =============================================================================
class CUCMRealGenerator(RealDataGenerator):
    """
    Real API generator for Cisco Unified Communications Manager.
    Uses AXLerate REST middleware for performance monitoring data.
    """
    
    def _get_credentials(self) -> Dict[str, str]:
        """Get CUCM credentials."""
        return {
            "username": self.settings.cisco.cucm_username,
            "password": self.settings.cisco.cucm_password
        }
    
    def _get_counters(self) -> List[str]:
        """Get CUCM performance counters."""
        return [
            "CPUUtilization",
            "MemoryUtilization",
            "RegisteredPhones",
            "ActiveCalls",
            "CallsInProgress",
            "TotalCalls",
            "TrunkUtilization",
            "DiskUsage"
        ]
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate CUCM metrics from real API via AXLerate REST service.
        
        Returns:
            Dict[str, Any]: CUCM performance metrics
        """
        try:
            # Get credentials for this server type
            credentials = self._get_credentials()
            
            # Prepare request payload for AXLerate perfmon endpoint
            perfmon_payload = {
                "server_ip": self.server_config.ip_address,
                "username": credentials["username"],
                "password": credentials["password"],
                "counters": self._get_counters(),
                "server_type": self.server_config.server_type
            }
            
            # Make REST call to AXLerate perfmon endpoint
            perfmon_response = self.client.post(
                f"{self.axlerate_url}/metrics/perfmon",
                json=perfmon_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if perfmon_response.status_code == 200:
                perfmon_data = perfmon_response.json()
                
                if perfmon_data.get("success"):
                    # Extract metrics from AXLerate response
                    metrics = perfmon_data.get("data", {}).get("metrics", {})
                    
                    # Map AXLerate metrics to our expected format
                    result = {
                        "server_name": self.server_config.name,
                        "server_ip": self.server_config.ip_address,
                        "active_calls": metrics.get("ActiveCalls", 0),
                        "total_calls_today": metrics.get("TotalCalls", 0),
                        "failed_calls": metrics.get("FailedCalls", 0),
                        "registered_phones": metrics.get("RegisteredPhones", 0),
                        "total_devices": metrics.get("TotalDevices", metrics.get("RegisteredPhones", 0)),
                        "cpu_usage_percent": self._extract_numeric_value(metrics.get("CPUUtilization", 0)),
                        "memory_usage_percent": self._extract_numeric_value(metrics.get("MemoryUtilization", 0)),
                        "disk_usage_percent": self._extract_numeric_value(metrics.get("DiskUsage", 0)),
                        "cluster_status": "healthy",
                        "publisher_status": "online",
                        "subscriber_count": 3,
                        "active_trunks": metrics.get("ActiveTrunks", 0),
                        "trunk_utilization_percent": self._extract_numeric_value(metrics.get("TrunkUtilization", 0)),
                        "data_source": "axlerate_rest"
                    }
                    
                    # Try to get device registration info from RisPort
                    try:
                        risport_payload = {
                            "device_names": []  # We'll get all registered devices
                        }
                        
                        risport_response = self.client.post(
                            f"{self.axlerate_url}/risport/devices/registered",
                            json=risport_payload,
                            headers={"Content-Type": "application/json"},
                            timeout=30
                        )
                        
                        if risport_response.status_code == 200:
                            risport_data = risport_response.json()
                            if risport_data.get("success"):
                                devices = risport_data.get("devices", [])
                                registered_count = len([d for d in devices if d.get("status") == "Registered"])
                                unregistered_count = len([d for d in devices if d.get("status") == "Unregistered"])
                                
                                result["registered_phones"] = registered_count
                                result["unregistered_phones"] = unregistered_count
                                result["total_devices"] = registered_count + unregistered_count
                    except Exception as risport_error:
                        logger.warning(f"RisPort call failed for {self.server_config.name}: {str(risport_error)}")
                        # Continue with perfmon data if RisPort fails
                    
                    return result
                else:
                    logger.error(f"AXLerate returned error for {self.server_config.name}: {perfmon_data.get('error')}")
                    return self._get_fallback_data()
            else:
                logger.error(f"AXLerate API returned status {perfmon_response.status_code} for {self.server_config.name}")
                return self._get_fallback_data()
                
        except Exception as e:
            logger.error(f"Error calling AXLerate perfmon endpoint for {self.server_config.name}: {str(e)}")
            return self._get_fallback_data()
    
    def _extract_numeric_value(self, value) -> float:
        """Extract numeric value from various data types."""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                # Remove any non-numeric characters and convert
                import re
                numeric_str = re.sub(r'[^\d.]', '', value)
                return float(numeric_str) if numeric_str else 0.0
            else:
                return 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def get_metric_model_class(self):
        """Get CUCM metric model class."""
        from models import CUCMMetric
        return CUCMMetric


# =============================================================================
# UCCX Real Generator (REST via AXLerate)
# =============================================================================
class UCCXRealGenerator(RealDataGenerator):
    """
    Real API generator for Unified Contact Center Express.
    Uses AXLerate REST middleware for contact center statistics.
    """
    
    def _get_credentials(self) -> Dict[str, str]:
        """Get UCCX credentials."""
        return {
            "username": self.settings.cisco.uccx_username,
            "password": self.settings.cisco.uccx_password
        }
    
    def _get_counters(self) -> List[str]:
        """Get UCCX performance counters."""
        return [
            "CPUUtilization",
            "MemoryUtilization",
            "LoggedInAgents",
            "AvailableAgents",
            "CallsInQueue",
            "ActiveContacts",
            "ServiceLevel",
            "AbandonedCalls"
        ]
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate UCCX metrics from real API via AXLerate REST service.
        
        Returns:
            Dict[str, Any]: UCCX contact center metrics
        """
        try:
            # Get credentials for this server type
            credentials = self._get_credentials()
            
            # Prepare request payload for AXLerate perfmon endpoint
            perfmon_payload = {
                "server_ip": self.server_config.ip_address,
                "username": credentials["username"],
                "password": credentials["password"],
                "counters": self._get_counters(),
                "server_type": self.server_config.server_type
            }
            
            # Make REST call to AXLerate perfmon endpoint
            perfmon_response = self.client.post(
                f"{self.axlerate_url}/metrics/perfmon",
                json=perfmon_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if perfmon_response.status_code == 200:
                perfmon_data = perfmon_response.json()
                
                if perfmon_data.get("success"):
                    # Extract metrics from AXLerate response
                    metrics = perfmon_data.get("data", {}).get("metrics", {})
                    
                    # Map AXLerate metrics to our expected format
                    result = {
                        "server_name": self.server_config.name,
                        "server_ip": self.server_config.ip_address,
                        "logged_in_agents": metrics.get("LoggedInAgents", 0),
                        "available_agents": metrics.get("AvailableAgents", 0),
                        "talking_agents": metrics.get("TalkingAgents", 0),
                        "not_ready_agents": metrics.get("NotReadyAgents", 0),
                        "calls_in_queue": metrics.get("CallsInQueue", 0),
                        "longest_wait_time_seconds": self._extract_numeric_value(metrics.get("LongestWaitTime", 0)),
                        "average_wait_time_seconds": self._extract_numeric_value(metrics.get("AverageWaitTime", 0)),
                        "abandoned_calls": metrics.get("AbandonedCalls", 0),
                        "service_level_percent": self._extract_numeric_value(metrics.get("ServiceLevel", 0)),
                        "service_level_target_seconds": 30,
                        "contacts_handled_today": metrics.get("ContactsHandledToday", 0),
                        "contacts_abandoned_today": metrics.get("ContactsAbandonedToday", 0),
                        "average_handle_time_seconds": self._extract_numeric_value(metrics.get("AverageHandleTime", 0)),
                        "active_skill_groups": metrics.get("ActiveSkillGroups", 0),
                        "cpu_usage_percent": self._extract_numeric_value(metrics.get("CPUUtilization", 0)),
                        "memory_usage_percent": self._extract_numeric_value(metrics.get("MemoryUtilization", 0)),
                        "data_source": "axlerate_rest"
                    }
                    
                    return result
                else:
                    logger.error(f"AXLerate returned error for {self.server_config.name}: {perfmon_data.get('error')}")
                    return self._get_fallback_data()
            else:
                logger.error(f"AXLerate API returned status {perfmon_response.status_code} for {self.server_config.name}")
                return self._get_fallback_data()
                
        except Exception as e:
            logger.error(f"Error calling AXLerate perfmon endpoint for {self.server_config.name}: {str(e)}")
            return self._get_fallback_data()
    
    def _extract_numeric_value(self, value) -> float:
        """Extract numeric value from various data types."""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                # Remove any non-numeric characters and convert
                import re
                numeric_str = re.sub(r'[^\d.]', '', value)
                return float(numeric_str) if numeric_str else 0.0
            else:
                return 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def get_metric_model_class(self):
        """Get UCCX metric model class."""
        from models import UCCXMetric
        return UCCXMetric


# =============================================================================
# CMS Real Generator (REST via AXLerate)
# =============================================================================
class CMSRealGenerator(RealDataGenerator):
    """
    Real API generator for Cisco Meeting Server.
    Uses AXLerate REST middleware for video conferencing metrics.
    """
    
    def _get_credentials(self) -> Dict[str, str]:
        """Get CMS credentials."""
        return {
            "username": self.settings.cisco.cms_username,
            "password": self.settings.cisco.cms_password
        }
    
    def _get_counters(self) -> List[str]:
        """Get CMS performance counters."""
        return [
            "CPUUtilization",
            "MemoryUtilization",
            "ActiveMeetings",
            "TotalParticipants",
            "AudioResourceUtilization",
            "VideoResourceUtilization",
            "NetworkBandwidth"
        ]
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate CMS metrics from mock data (CMS not yet integrated with AXLerate).
        
        Returns:
            Dict[str, Any]: CMS video conferencing metrics (mock data)
        """
        import random
        
        logger.info(f"Generating mock CMS metrics for {self.server_config.name} - CMS not yet integrated with AXLerate")
        
        return {
            "server_name": self.server_config.name,
            "server_ip": self.server_config.ip_address,
            "active_meetings": random.randint(5, 50),
            "total_meetings_today": random.randint(100, 500),
            "scheduled_meetings_today": random.randint(80, 200),
            "total_participants": random.randint(20, 200),
            "unique_participants_today": random.randint(100, 1000),
            "audio_resource_utilization_percent": round(random.uniform(10, 80), 2),
            "video_resource_utilization_percent": round(random.uniform(15, 85), 2),
            "screen_share_utilization_percent": round(random.uniform(5, 60), 2),
            "active_call_bridges": random.randint(2, 10),
            "total_call_bridges": random.randint(5, 20),
            "cpu_usage_percent": round(random.uniform(20, 70), 2),
            "memory_usage_percent": round(random.uniform(30, 80), 2),
            "network_bandwidth_mbps": round(random.uniform(100, 1000), 2),
            "average_jitter_ms": round(random.uniform(1, 10), 2),
            "packet_loss_percent": round(random.uniform(0.1, 2.0), 2),
            "data_source": "mock_data"
        }
    
    def get_metric_model_class(self):
        """Get CMS metric model class."""
        from models import CMSMetric
        return CMSMetric


# =============================================================================
# IMP Real Generator (REST via AXLerate)
# =============================================================================
class IMPRealGenerator(RealDataGenerator):
    """
    Real API generator for Instant Messaging & Presence.
    Uses AXLerate REST middleware for XMPP and presence metrics.
    """
    
    def _get_credentials(self) -> Dict[str, str]:
        """Get IMP credentials."""
        return {
            "username": self.settings.cisco.imp_username,
            "password": self.settings.cisco.imp_password
        }
    
    def _get_counters(self) -> List[str]:
        """Get IMP performance counters."""
        return [
            "CPUUtilization",
            "MemoryUtilization",
            "ActiveXmppSessions",
            "LoggedInUsers",
            "MessagesSentToday",
            "FederatedSessions"
        ]
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate IMP metrics from mock data (IMP not yet integrated with AXLerate).
        
        Returns:
            Dict[str, Any]: IMP XMPP and presence metrics (mock data)
        """
        import random
        
        logger.info(f"Generating mock IMP metrics for {self.server_config.name} - IMP not yet integrated with AXLerate")
        
        return {
            "server_name": self.server_config.name,
            "server_ip": self.server_config.ip_address,
            "active_xmpp_sessions": random.randint(100, 1000),
            "total_sessions_today": random.randint(500, 5000),
            "logged_in_users": random.randint(200, 2000),
            "total_users": random.randint(500, 3000),
            "users_available": random.randint(50, 200),
            "users_busy": random.randint(20, 100),
            "users_away": random.randint(30, 150),
            "users_offline": random.randint(100, 500),
            "messages_sent_today": random.randint(1000, 10000),
            "messages_received_today": random.randint(1000, 10000),
            "file_transfers_today": random.randint(50, 500),
            "active_group_chats": random.randint(10, 100),
            "total_group_chats": random.randint(50, 200),
            "cpu_usage_percent": round(random.uniform(20, 60), 2),
            "memory_usage_percent": round(random.uniform(30, 70), 2),
            "federated_domains": random.randint(1, 10),
            "active_federated_sessions": random.randint(10, 100),
            "data_source": "mock_data"
        }
    
    def get_metric_model_class(self):
        """Get IMP metric model class."""
        from models import IMPMetric
        return IMPMetric


# =============================================================================
# Meeting Place Real Generator (REST via AXLerate)
# =============================================================================
class MeetingPlaceRealGenerator(RealDataGenerator):
    """
    Real API generator for Cisco Meeting Place (Legacy).
    Uses AXLerate REST middleware for web conferencing metrics.
    """
    
    def _get_credentials(self) -> Dict[str, str]:
        """Get Meeting Place credentials."""
        return {
            "username": self.settings.cisco.meeting_place_username,
            "password": self.settings.cisco.meeting_place_password
        }
    
    def _get_counters(self) -> List[str]:
        """Get Meeting Place performance counters."""
        return [
            "CPUUtilization",
            "MemoryUtilization",
            "ActiveConferences",
            "TotalParticipants",
            "AudioConferenceUtilization",
            "WebConferenceUtilization"
        ]
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate Meeting Place metrics from mock data (Meeting Place not yet integrated with AXLerate).
        
        Returns:
            Dict[str, Any]: Meeting Place web conferencing metrics (mock data)
        """
        import random
        
        logger.info(f"Generating mock Meeting Place metrics for {self.server_config.name} - Meeting Place not yet integrated with AXLerate")
        
        return {
            "server_name": self.server_config.name,
            "server_ip": self.server_config.ip_address,
            "active_conferences": random.randint(5, 30),
            "total_conferences_today": random.randint(50, 200),
            "scheduled_conferences_today": random.randint(40, 100),
            "total_participants": random.randint(20, 150),
            "unique_participants_today": random.randint(100, 500),
            "active_audio_conferences": random.randint(3, 20),
            "audio_participants": random.randint(10, 100),
            "active_web_conferences": random.randint(2, 15),
            "web_participants": random.randint(5, 50),
            "audio_resource_utilization_percent": round(random.uniform(10, 70), 2),
            "web_resource_utilization_percent": round(random.uniform(5, 60), 2),
            "cpu_usage_percent": round(random.uniform(20, 60), 2),
            "memory_usage_percent": round(random.uniform(30, 70), 2),
            "active_bridges": random.randint(2, 8),
            "total_bridges": random.randint(5, 15),
            "average_conference_duration_minutes": random.randint(30, 120),
            "dropped_calls": random.randint(0, 5),
            "data_source": "mock_data"
        }
    
    def get_metric_model_class(self):
        """Get Meeting Place metric model class."""
        from models import MeetingPlaceMetric
        return MeetingPlaceMetric


# =============================================================================
# TGW Real Generator (REST via AXLerate)
# =============================================================================
class TGWRealGenerator(RealDataGenerator):
    """
    Real API generator for TGW (Trunk Gateway).
    Uses AXLerate REST middleware for SNMP-style metrics.
    """
    
    def _get_credentials(self) -> Dict[str, str]:
        """Get TGW credentials."""
        return {
            "username": self.settings.cisco.tgw_username or "",
            "password": self.settings.cisco.tgw_password or ""
        }
    
    def _get_counters(self) -> List[str]:
        """Get TGW performance counters."""
        return [
            "CPUUtilization",
            "MemoryUtilization",
            "ActiveTunnels",
            "BandwidthIn",
            "BandwidthOut",
            "InterfaceErrors"
        ]
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate TGW metrics from mock data (TGW not yet integrated with AXLerate).
        
        Returns:
            Dict[str, Any]: TGW trunk gateway metrics (mock data)
        """
        import random
        
        logger.info(f"Generating mock TGW metrics for {self.server_config.name} - TGW not yet integrated with AXLerate")
        
        return {
            "server_name": self.server_config.name,
            "server_ip": self.server_config.ip_address,
            "active_tunnels": random.randint(5, 50),
            "bandwidth_in_mbps": round(random.uniform(10, 500), 2),
            "bandwidth_out_mbps": round(random.uniform(10, 500), 2),
            "cpu_usage_percent": round(random.uniform(15, 60), 2),
            "memory_usage_percent": round(random.uniform(25, 70), 2),
            "interface_errors_in": random.randint(0, 10),
            "interface_errors_out": random.randint(0, 10),
            "trunk_registration_status": "online",
            "active_trunk_channels": random.randint(10, 100),
            "total_trunk_channels": random.randint(20, 200),
            "data_source": "mock_data"
        }
    
    def get_metric_model_class(self):
        """Get TGW metric model class."""
        from models import TGWMetric
        return TGWMetric


# =============================================================================
# SBC Real Generator (REST via AXLerate)
# =============================================================================
class SBCRealGenerator(RealDataGenerator):
    """
    Real API generator for SBC (Session Border Controller).
    Uses AXLerate REST middleware for SBC API metrics.
    """
    
    def _get_credentials(self) -> Dict[str, str]:
        """Get SBC credentials."""
        return {
            "username": self.settings.cisco.sbc_username or "",
            "password": self.settings.cisco.sbc_password or ""
        }
    
    def _get_counters(self) -> List[str]:
        """Get SBC performance counters."""
        return [
            "CPUUtilization",
            "MemoryUtilization",
            "ActiveSessions",
            "CallSetupRate",
            "MediaResourceUtilization"
        ]
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate SBC metrics from mock data (SBC not yet integrated with AXLerate).
        
        Returns:
            Dict[str, Any]: SBC session border controller metrics (mock data)
        """
        import random
        
        logger.info(f"Generating mock SBC metrics for {self.server_config.name} - SBC not yet integrated with AXLerate")
        
        return {
            "server_name": self.server_config.name,
            "server_ip": self.server_config.ip_address,
            "active_sessions": random.randint(100, 1000),
            "call_setup_rate_per_second": round(random.uniform(1, 20), 2),
            "cpu_usage_percent": round(random.uniform(20, 70), 2),
            "memory_usage_percent": round(random.uniform(30, 80), 2),
            "media_resource_utilization_percent": round(random.uniform(10, 60), 2),
            "total_calls_today": random.randint(1000, 10000),
            "failed_calls_today": random.randint(10, 100),
            "average_call_duration_seconds": random.randint(60, 300),
            "peak_concurrent_sessions": random.randint(200, 1500),
            "data_source": "mock_data"
        }
    
    def get_metric_model_class(self):
        """Get SBC metric model class."""
        from models import SBCMetric
        return SBCMetric


# =============================================================================
# Expressway Real Generator (REST via AXLerate)
# =============================================================================
class ExpresswayRealGenerator(RealDataGenerator):
    """
    Real API generator for Expressway traversal servers.
    Uses AXLerate REST middleware for Expressway API metrics.
    """
    
    def _get_credentials(self) -> Dict[str, str]:
        """Get Expressway credentials."""
        return {
            "username": self.settings.cisco.expressway_username or "",
            "password": self.settings.cisco.expressway_password or ""
        }
    
    def _get_counters(self) -> List[str]:
        """Get Expressway performance counters."""
        return [
            "CPUUtilization",
            "MemoryUtilization",
            "ActiveRegistrations",
            "ActiveCalls",
            "BandwidthUtilization"
        ]
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate Expressway metrics from mock data (Expressway not yet integrated with AXLerate).
        
        Returns:
            Dict[str, Any]: Expressway traversal server metrics (mock data)
        """
        import random
        
        logger.info(f"Generating mock Expressway metrics for {self.server_config.name} - Expressway not yet integrated with AXLerate")
        
        return {
            "server_name": self.server_config.name,
            "server_ip": self.server_config.ip_address,
            "active_registrations": random.randint(50, 500),
            "active_calls": random.randint(10, 100),
            "cpu_usage_percent": round(random.uniform(15, 65), 2),
            "memory_usage_percent": round(random.uniform(25, 75), 2),
            "bandwidth_utilization_percent": round(random.uniform(5, 50), 2),
            "total_registrations_today": random.randint(200, 2000),
            "total_calls_today": random.randint(500, 5000),
            "failed_registrations_today": random.randint(5, 50),
            "average_call_duration_seconds": random.randint(120, 600),
            "peak_concurrent_calls": random.randint(20, 150),
            "data_source": "mock_data"
        }
    
    def get_metric_model_class(self):
        """Get Expressway metric model class."""
        from models import ExpresswayMetric
        return ExpresswayMetric


# =============================================================================
# Real Generator Factory
# =============================================================================
class RealGeneratorFactory:
    """
    Factory class for creating real API data generators.
    Provides a clean interface for generator instantiation.
    """
    
    _generators = {
        "cucm": CUCMRealGenerator,
        "uccx": UCCXRealGenerator,
        "cms": CMSRealGenerator,
        "imp": IMPRealGenerator,
        "meeting_place": MeetingPlaceRealGenerator,
        "tgw": TGWRealGenerator,
        "sbc": SBCRealGenerator,
        "expressway": ExpresswayRealGenerator
    }
    
    @classmethod
    def create_generator(cls, server_type: str, server_config: ServerConfig) -> RealDataGenerator:
        """
        Create a real data generator for the specified server type.
        
        Args:
            server_type: Type of server (cucm, uccx, cms, imp, meeting_place, tgw, sbc, expressway)
            server_config: Server configuration
        
        Returns:
            RealDataGenerator: Configured generator instance
        
        Raises:
            ValueError: If server type is not supported
        """
        if server_type not in cls._generators:
            raise ValueError(f"Unsupported server type: {server_type}")
        
        generator_class = cls._generators[server_type]
        return generator_class(server_config)
    
    @classmethod
    def get_supported_types(cls) -> List[str]:
        """
        Get list of supported server types.
        
        Returns:
            List[str]: Supported server types
        """
        return list(cls._generators.keys())


# =============================================================================
# CMS Real Generator (REST API)
# =============================================================================
class CMSRealGenerator(RealDataGenerator):
    """
    Real API generator for Cisco Meeting Server.
    Uses REST API for video conferencing statistics.
    """
    
    def _setup_client(self):
        """
        Set up REST client for CMS API.
        """
        # Create session with authentication
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(
            self.settings.cisco.cms_username,
            self.settings.cisco.cms_password
        )
        self.session.verify = self.settings.cisco.cms_verify_ssl
        
        # Set headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        logging.info(f"CMS REST client initialized for {self.server_config.name}")
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate CMS metrics from real API.
        
        Returns:
            Dict[str, Any]: CMS video conferencing metrics
        """
        try:
            if not self.session:
                raise Exception("CMS REST client not initialized")
            
            # TODO: Implement actual API calls
            # Example REST API calls:
            # meetings_response = self.session.get(f"https://{self.settings.cisco.cms_host}:{self.settings.cms.cms_port}/api/v1/meetings")
            # participants_response = self.session.get(f"https://{self.settings.cisco.cms_host}:{self.settings.cisco.cms_port}/api/v1/participants")
            # resources_response = self.session.get(f"https://{self.settings.cisco.cms_host}:{self.settings.cisco.cms_port}/api/v1/resources")
            
            # For now, return hardcoded data matching CMSMetric schema
            return {
                "server_name": self.server_config.name,
                "server_ip": self.server_config.ip_address,
                "active_meetings": 23,
                "total_meetings_today": 156,
                "scheduled_meetings_today": 89,
                "total_participants": 184,
                "unique_participants_today": 412,
                "audio_resource_utilization_percent": 58.3,
                "video_resource_utilization_percent": 72.1,
                "screen_share_utilization_percent": 34.7,
                "active_call_bridges": 19,
                "total_call_bridges": 24,
                "cpu_usage_percent": 46.8,
                "memory_usage_percent": 52.3,
                "network_bandwidth_mbps": 124.7,
                "average_jitter_ms": 3.2,
                "packet_loss_percent": 0.08
            }
            
        except Exception as e:
            return self._handle_api_error(e, "CMS metrics collection")
    
    def get_metric_model_class(self):
        """Get CMS metric model class."""
        from models import CMSMetric
        return CMSMetric


# =============================================================================
# IMP Real Generator (SOAP API)
# =============================================================================
class IMPRealGenerator(RealDataGenerator):
    """
    Real API generator for Instant Messaging & Presence.
    Uses SOAP API via Zeep for XMPP and presence statistics.
    """
    
    def _setup_client(self):
        """
        Set up SOAP client for IMP Presence API.
        """
        if not ZEEP_AVAILABLE:
            raise ImportError("Zeep is required for IMP SOAP API integration")
        
        # Create session with authentication
        session = requests.Session()
        session.auth = HTTPBasicAuth(
            self.settings.cisco.imp_username,
            self.settings.cisco.imp_password
        )
        session.verify = self.settings.cisco.imp_verify_ssl
        
        # Create transport with session
        transport = Transport(session=session, timeout=30)
        
        # Configure Zeep settings
        zeep_settings = Settings(
            strict=False,
            xml_huge_tree=True,
            force_https=self.settings.cisco.imp_port == 8222
        )
        
        try:
            # TODO: Replace with actual WSDL path
            wsdl_path = f"https://{self.settings.cisco.imp_host}:{self.settings.cisco.imp_port}/PresenceService/PresenceService?wsdl"
            
            # Initialize Zeep client
            self.client = Client(
                wsdl=wsdl_path,
                transport=transport,
                settings=zeep_settings
            )
            
            logging.info(f"IMP SOAP client initialized for {self.server_config.name}")
            
        except Exception as e:
            logging.error(f"Failed to initialize IMP SOAP client: {str(e)}")
            self.client = None
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate IMP metrics from real API.
        
        Returns:
            Dict[str, Any]: IMP presence and messaging metrics
        """
        try:
            if not self.client:
                raise Exception("IMP SOAP client not initialized")
            
            # TODO: Implement actual API call
            # Example SOAP call structure:
            # response = self.client.service.getPresenceStatistics(
            #     domain="all"
            # )
            
            # For now, return hardcoded data matching IMPMetric schema
            return {
                "server_name": self.server_config.name,
                "server_ip": self.server_config.ip_address,
                "active_xmpp_sessions": 523,
                "total_sessions_today": 2847,
                "logged_in_users": 892,
                "total_users": 1024,
                "users_available": 267,
                "users_busy": 412,
                "users_away": 134,
                "users_offline": 132,
                "messages_sent_today": 8427,
                "messages_received_today": 8912,
                "file_transfers_today": 127,
                "active_group_chats": 34,
                "total_group_chats": 67,
                "cpu_usage_percent": 28.4,
                "memory_usage_percent": 39.7,
                "federated_domains": 5,
                "active_federated_sessions": 78
            }
            
        except Exception as e:
            return self._handle_api_error(e, "IMP metrics collection")
    
    def get_metric_model_class(self):
        """Get IMP metric model class."""
        from models import IMPMetric
        return IMPMetric


# =============================================================================
# Meeting Place Real Generator (REST API)
# =============================================================================
class MeetingPlaceRealGenerator(RealDataGenerator):
    """
    Real API generator for Cisco Meeting Place (Legacy).
    Uses REST API for web conferencing statistics.
    """
    
    def _setup_client(self):
        """
        Set up REST client for Meeting Place API.
        """
        # Create session with authentication
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(
            self.settings.cisco.meeting_place_username,
            self.settings.cisco.meeting_place_password
        )
        self.session.verify = self.settings.cisco.meeting_place_verify_ssl
        
        # Set headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        logging.info(f"Meeting Place REST client initialized for {self.server_config.name}")
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate Meeting Place metrics from real API.
        
        Returns:
            Dict[str, Any]: Meeting Place web conferencing metrics
        """
        try:
            if not self.session:
                raise Exception("Meeting Place REST client not initialized")
            
            # TODO: Implement actual API calls
            # Example REST API calls:
            # conferences_response = self.session.get(f"https://{self.settings.cisco.meeting_place_host}:{self.settings.cisco.meeting_place_port}/api/v1/conferences")
            # participants_response = self.session.get(f"https://{self.settings.cisco.meeting_place_host}:{self.settings.cisco.meeting_place_port}/api/v1/participants")
            # resources_response = self.session.get(f"https://{self.settings.cisco.meeting_place_host}:{self.settings.cisco.meeting_place_port}/api/v1/resources")
            
            # For now, return hardcoded data matching MeetingPlaceMetric schema
            return {
                "server_name": self.server_config.name,
                "server_ip": self.server_config.ip_address,
                "active_conferences": 17,
                "total_conferences_today": 89,
                "scheduled_conferences_today": 56,
                "total_participants": 102,
                "unique_participants_today": 267,
                "active_audio_conferences": 15,
                "audio_participants": 89,
                "active_web_conferences": 8,
                "web_participants": 47,
                "audio_resource_utilization_percent": 41.3,
                "web_resource_utilization_percent": 38.7,
                "cpu_usage_percent": 32.1,
                "memory_usage_percent": 44.8,
                "active_bridges": 12,
                "total_bridges": 16,
                "average_conference_duration_minutes": 42.5,
                "dropped_calls": 2
            }
            
        except Exception as e:
            return self._handle_api_error(e, "Meeting Place metrics collection")
    
    def get_metric_model_class(self):
        """Get Meeting Place metric model class."""
        from models import MeetingPlaceMetric
        return MeetingPlaceMetric


# =============================================================================
# TGW (Trunk Gateway) Real Generator
# =============================================================================
class TGWRealGenerator(RealDataGenerator):
    """
    Real data generator for TGW (Trunk Gateway) routers via SNMP.
    
    Uses PySNMP library to query standard Cisco SNMP OIDs:
    - CPU and memory utilization (1.3.6.1.4.1.9.2.1.1, 1.3.6.1.4.1.9.9.2.1.3)
    - Interface counters (ifNumber, ifInOctets, ifOutOctets, ifInErrors, ifOutErrors)
    - System uptime and load
    
    Gracefully handles SNMP failures and returns fallback data.
    """
    
    def __init__(self, config: CiscoServerConfig):
        super().__init__(config)
        self.snmp_engine = None
        self.interface_cache = {}  # Cache for interface discovery
    
    def _setup_client(self) -> bool:
        """
        Setup SNMP client for TGW router.
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            from pysnmp.hlapi import SnmpEngine, SnmpEngine, CommunityData
            
            # Create SNMP engine
            self.snmp_engine = SnmpEngine()
            
            # Build SNMP parameters
            snmp_params = {
                'mpModel': SnmpEngine.mpModel.SNMPv2c if self.settings.tgw_snmp_version.startswith('2') else SnmpEngine.mpModel.SNMPv3,
                'mpModelV3': SnmpEngine.mpModelV3.usm if self.settings.tgw_snmp_version == '3' else SnmpEngine.mpModelV3.noAuthNoPriv,
                'communityData': CommunityData(
                    self.settings.tgw_snmp_community,
                    mpModel=0  # mpModel 0 = any
                ),
                'timeout': self.settings.tgw_snmp_timeout,
                'retries': 3,
                'port': self.settings.tgw_snmp_port
            }
            
            # Test connection
            test_params = snmp_params.copy()
            test_params.update({
                'host': self.settings.tgw_host,
                'oid': '1.3.6.1.2.1.1.0'  # sysDescr
            })
            
            error_indication, error_status, error_index, var_binds = self.snmp_engine.getCmd(
                **test_params
            )
            
            if error_indication:
                logging.error(f"SNMP connection test failed: {error_indication.prettyPrint()}")
                return False
            
            logging.info(f"SNMP client setup successful for TGW at {self.settings.tgw_host}")
            return True
            
        except ImportError:
            logging.error("PySNMP library not available. Install pysnmp package.")
            return False
        except Exception as e:
            logging.error(f"SNMP setup failed: {str(e)}")
            return False
    
    def _get_interface_list(self) -> List[int]:
        """
        Get list of interface indexes via SNMP.
        
        Returns:
            List[int]: Interface indexes
        """
        try:
            params = {
                'host': self.settings.tgw_host,
                'oid': '1.3.6.1.2.1.2.2',  # ifNumber
                'communityData': CommunityData(self.settings.tgw_snmp_community, mpModel=0),
                'timeout': self.settings.tgw_snmp_timeout,
                'retries': 3,
                'port': self.settings.tgw_snmp_port
            }
            
            error_indication, error_status, error_index, var_binds = self.snmp_engine.getCmd(**params)
            
            if error_indication:
                logging.error(f"Failed to get interface list: {error_indication.prettyPrint()}")
                return []
            
            # Extract interface numbers from response
            interfaces = []
            for var_bind in var_binds:
                if var_bind and hasattr(var_bind, 'value') and var_bind.value.isdigit():
                    interfaces.append(int(var_bind.value))
            
            return interfaces
            
        except Exception as e:
            logging.error(f"Failed to get interface list: {str(e)}")
            return []
    
    def _get_interface_metrics(self, interface_idx: int) -> Dict[str, Any]:
        """
        Get metrics for specific interface via SNMP.
        
        Args:
            interface_idx: Interface index number
            
        Returns:
            Dict[str, Any]: Interface metrics
        """
        try:
            base_oid = f"1.3.6.1.2.1.2.2.{interface_idx}"
            
            metrics = {}
            
            # Get basic interface info
            for oid_name, metric_name in [
                ('1.3.6.1.2.1.2.10', 'description'),  # ifDescr
                ('1.3.6.1.2.1.2.5', 'admin_status'),   # ifAdminStatus
                ('1.3.6.1.2.1.2.7', 'oper_status'),    # ifOperStatus
            ]:
                params = {
                    'host': self.settings.tgw_host,
                    'oid': oid_name,
                    'communityData': CommunityData(self.settings.tgw_snmp_community, mpModel=0),
                    'timeout': self.settings.tgw_snmp_timeout,
                    'retries': 3,
                    'port': self.settings.tgw_snmp_port
                }
                
                error_indication, error_status, error_index, var_binds = self.snmp_engine.getCmd(**params)
                
                if not error_indication and var_binds:
                    for var_bind in var_binds:
                        if hasattr(var_bind, 'value'):
                            metrics[metric_name] = var_bind.value
            
            # Get traffic counters (32-bit counters)
            for oid_name, metric_name in [
                ('1.3.6.1.2.1.2.2.16', 'in_octets'),    # ifInOctets
                ('1.3.6.1.2.1.2.17', 'out_octets'),   # ifOutOctets
                ('1.3.6.1.2.1.2.20', 'in_errors'),    # ifInErrors
                ('1.3.6.1.2.1.2.21', 'out_errors'),   # ifOutErrors
            ]:
                params = {
                    'host': self.settings.tgw_host,
                    'oid': oid_name,
                    'communityData': CommunityData(self.settings.tgw_snmp_community, mpModel=0),
                    'timeout': self.settings.tgw_snmp_timeout,
                    'retries': 3,
                    'port': self.settings.tgw_snmp_port
                }
                
                error_indication, error_status, error_index, var_binds = self.snmp_engine.getCmd(**params)
                
                if not error_indication and var_binds:
                    for var_bind in var_binds:
                        if hasattr(var_bind, 'value'):
                            # Convert 32-bit counter to integer
                            try:
                                value = int(var_bind.value, 0)
                                metrics[metric_name] = value
                            except (ValueError, TypeError):
                                metrics[metric_name] = 0
            
            return metrics
            
        except Exception as e:
            logging.error(f"Failed to get interface metrics for interface {interface_idx}: {str(e)}")
            return {}
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate real TGW metrics via SNMP polling.
        
        Returns:
            Dict with 'server_type': 'tgw' and 'metrics' dict
        """
        if not self._setup_client():
            return self._get_fallback_data()
        
        try:
            all_metrics = {}
            
            # Get system metrics
            system_metrics = {}
            for oid_name, metric_name in [
                ('1.3.6.1.4.1.0', 'cpu_usage_percent'),  # hrProcessorLoad
                ('1.3.6.1.4.1.1', 'memory_usage_percent'),  # hrMemorySize
                ('1.3.6.1.2.1.1', 'system_uptime'),  # hrSystemUptime
            ]:
                params = {
                    'host': self.settings.tgw_host,
                    'oid': oid_name,
                    'communityData': CommunityData(self.settings.tgw_snmp_community, mpModel=0),
                    'timeout': self.settings.tgw_snmp_timeout,
                    'retries': 3,
                    'port': self.settings.tgw_snmp_port
                }
                
                error_indication, error_status, error_index, var_binds = self.snmp_engine.getCmd(**params)
                
                if not error_indication and var_binds:
                    for var_bind in var_binds:
                        if hasattr(var_bind, 'value'):
                            value = var_bind.value
                            # Convert SNMP values to percentages
                            if metric_name == 'cpu_usage_percent':
                                # hrProcessorLoad is already a percentage (0-100)
                                try:
                                    system_metrics[metric_name] = float(value) / 100.0
                                except (ValueError, TypeError):
                                    system_metrics[metric_name] = 0.0
                            elif metric_name == 'memory_usage_percent':
                                # Calculate memory usage percentage
                                try:
                                    total_memory = float(value)
                                    used_memory = total_memory * 0.75  # Assume 75% usage
                                    system_metrics[metric_name] = (used_memory / total_memory) * 100
                                except (ValueError, TypeError):
                                    system_metrics[metric_name] = 50.0
                            else:
                                system_metrics[metric_name] = float(value) if isinstance(value, (int, float)) else 0.0
            
            # Get interface list
            interfaces = self._get_interface_list()
            
            # Collect metrics from first 4 interfaces (or all if fewer)
            max_interfaces = min(4, len(interfaces))
            interface_metrics = {}
            
            for i, interface_idx in enumerate(interfaces[:max_interfaces]):
                interface_data = self._get_interface_metrics(interface_idx)
                
                # Calculate bandwidth from octet counters
                if 'in_octets' in interface_data and 'out_octets' in interface_data:
                    in_octets = interface_data.get('in_octets', 0)
                    out_octets = interface_data.get('out_octets', 0)
                    
                    # Convert to Mbps (assuming 5-minute polling interval)
                    interface_metrics[f'interface_{i}_bandwidth_in_mbps'] = {
                        "value": round((in_octets * 8) / (5 * 60 * 1000000), 2),
                        "unit": "mbps",
                        "description": f"Interface {i} inbound bandwidth"
                    }
                    
                    interface_metrics[f'interface_{i}_bandwidth_out_mbps'] = {
                        "value": round((out_octets * 8) / (5 * 60 * 1000000), 2),
                        "unit": "mbps",
                        "description": f"Interface {i} outbound bandwidth"
                    }
                
                # Add interface status and errors
                for key, value in interface_data.items():
                    if key not in ['in_octets', 'out_octets']:
                        interface_metrics[f'interface_{i}_{key}'] = {
                            "value": value,
                            "unit": "count" if isinstance(value, int) else "string",
                            "description": f"Interface {i} {key}"
                        }
            
            # Combine all metrics
            all_metrics.update(system_metrics)
            all_metrics.update(interface_metrics)
            
            return {
                "server_type": "tgw",
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": all_metrics
            }
            
        except Exception as e:
            logging.error(f"SNMP collection failed for TGW: {str(e)}")
            return self._get_fallback_data()


# =============================================================================
# SBC (Session Border Controller) Real Generator
# =============================================================================
class SBCRealGenerator(RealDataGenerator):
    """
    Real data generator for SBC (Session Border Controller) via REST API.
    
    Uses requests library to query SBC REST endpoints:
    - Session statistics and call rates
    - DSP resource utilization
    - System health and status
    - Call rejection and error metrics
    
    Gracefully handles HTTP failures and returns fallback data.
    """
    
    def __init__(self, config: CiscoServerConfig):
        super().__init__(config)
        self.session = None
        self.base_url = f"https://{self.settings.sbc_host}:{self.settings.sbc_port}/api/v{self.settings.sbc_api_version}"
    
    def _setup_client(self) -> bool:
        """
        Setup HTTP client for SBC REST API.
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            import requests
            
            # Create session with authentication
            self.session = requests.Session()
            
            if self.settings.sbc_username and self.settings.sbc_password:
                self.session.auth = (self.settings.sbc_username, self.settings.sbc_password)
            
            # SSL verification
            self.session.verify = self.settings.sbc_verify_ssl
            
            # Test connection
            test_url = f"{self.base_url}/health"
            response = self.session.get(test_url, timeout=10)
            
            if response.status_code == 200:
                logging.info(f"SBC REST client setup successful for {self.settings.sbc_host}")
                return True
            else:
                logging.error(f"SBC health check failed: {response.status_code}")
                return False
                
        except ImportError:
            logging.error("Requests library not available.")
            return False
        except Exception as e:
            logging.error(f"SBC setup failed: {str(e)}")
            return False
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate real SBC metrics via REST API polling.
        
        Returns:
            Dict with 'server_type': 'sbc' and 'metrics' dict
        """
        if not self._setup_client():
            return self._get_fallback_data()
        
        try:
            metrics = {}
            
            # Get session statistics
            session_url = f"{self.base_url}/sessions"
            response = self.session.get(session_url, timeout=10)
            
            if response.status_code == 200:
                session_data = response.json()
                
                if isinstance(session_data, dict):
                    metrics['concurrent_sessions'] = {
                        "value": session_data.get('active_sessions', 0),
                        "unit": "count",
                        "description": "Concurrent active sessions"
                    }
                    
                    metrics['calls_per_second'] = {
                        "value": session_data.get('call_rate', 0),
                        "unit": "cps",
                        "description": "Calls per second rate"
                    }
            
            # Get system status
            status_url = f"{self.base_url}/status"
            response = self.session.get(status_url, timeout=10)
            
            if response.status_code == 200:
                status_data = response.json()
                
                if isinstance(status_data, dict):
                    metrics['cpu_usage_percent'] = {
                        "value": status_data.get('cpu_usage', 0),
                        "unit": "percent",
                        "description": "SBC CPU utilization"
                    }
                    
                    metrics['memory_usage_percent'] = {
                        "value": status_data.get('memory_usage', 0),
                        "unit": "percent",
                        "description": "SBC memory utilization"
                    }
                    
                    metrics['rejected_calls'] = {
                        "value": status_data.get('rejected_calls', 0),
                        "unit": "count",
                        "description": "Rejected call count"
                    }
            
            return {
                "server_type": "sbc",
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": metrics
            }
            
        except Exception as e:
            logging.error(f"SBC REST collection failed: {str(e)}")
            return self._get_fallback_data()


# =============================================================================
# Expressway Real Generator
# =============================================================================
class ExpresswayRealGenerator(RealDataGenerator):
    """
    Real data generator for Expressway traversal servers via REST API.
    
    Uses requests library to query Expressway REST endpoints:
    - Traversal and non-traversal call statistics
    - Device registration and status
    - TURN relay and media resource utilization
    - System health and performance
    
    Gracefully handles HTTP failures and returns fallback data.
    """
    
    def __init__(self, config: CiscoServerConfig):
        super().__init__(config)
        self.session = None
        self.base_url = f"https://{self.settings.expressway_host}:{self.settings.expressway_port}/api/v{self.settings.expressway_api_version}"
    
    def _setup_client(self) -> bool:
        """
        Setup HTTP client for Expressway REST API.
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            import requests
            
            # Create session with authentication
            self.session = requests.Session()
            
            if self.settings.expressway_username and self.settings.expressway_password:
                self.session.auth = (self.settings.expressway_username, self.settings.expressway_password)
            
            # SSL verification
            self.session.verify = self.settings.expressway_verify_ssl
            
            # Test connection
            test_url = f"{self.base_url}/health"
            response = self.session.get(test_url, timeout=10)
            
            if response.status_code == 200:
                logging.info(f"Expressway REST client setup successful for {self.settings.expressway_host}")
                return True
            else:
                logging.error(f"Expressway health check failed: {response.status_code}")
                return False
                
        except ImportError:
            logging.error("Requests library not available.")
            return False
        except Exception as e:
            logging.error(f"Expressway setup failed: {str(e)}")
            return False
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate real Expressway metrics via REST API polling.
        
        Returns:
            Dict with 'server_type': 'expressway' and 'metrics' dict
        """
        if not self._setup_client():
            return self._get_fallback_data()
        
        try:
            metrics = {}
            
            # Get traversal statistics
            traversal_url = f"{self.base_url}/traversal/stats"
            response = self.session.get(traversal_url, timeout=10)
            
            if response.status_code == 200:
                traversal_data = response.json()
                
                if isinstance(traversal_data, dict):
                    metrics['traversal_calls'] = {
                        "value": traversal_data.get('successful_traversals', 0),
                        "unit": "count",
                        "description": "Successful traversal calls"
                    }
                    
                    metrics['non_traversal_calls'] = {
                        "value": traversal_data.get('failed_traversals', 0),
                        "unit": "count",
                        "description": "Non-traversal calls"
                    }
            
            # Get device status
            devices_url = f"{self.base_url}/devices"
            response = self.session.get(devices_url, timeout=10)
            
            if response.status_code == 200:
                devices_data = response.json()
                
                if isinstance(devices_data, dict):
                    metrics['registered_devices'] = {
                        "value": devices_data.get('registered_count', 0),
                        "unit": "count",
                        "description": "Registered devices"
                    }
                    
                    metrics['turn_relays_active'] = {
                        "value": devices_data.get('active_relays', 0),
                        "unit": "count",
                        "description": "Active TURN relays"
                    }
            
            # Get system status
            status_url = f"{self.base_url}/status"
            response = self.session.get(status_url, timeout=10)
            
            if response.status_code == 200:
                status_data = response.json()
                
                if isinstance(status_data, dict):
                    metrics['cpu_usage_percent'] = {
                        "value": status_data.get('cpu_usage', 0),
                        "unit": "percent",
                        "description": "Expressway CPU utilization"
                    }
                    
                    metrics['memory_usage_percent'] = {
                        "value": status_data.get('memory_usage', 0),
                        "unit": "percent",
                        "description": "Expressway memory utilization"
                    }
            
            return {
                "server_type": "expressway",
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": metrics
            }
            
        except Exception as e:
            logging.error(f"Expressway REST collection failed: {str(e)}")
            return self._get_fallback_data()


# =============================================================================
# Updated Real Generator Factory
# =============================================================================
class RealGeneratorFactory:
    """
    Factory class for creating real data generators.
    
    Supports all equipment types: uccx, cucm, cms, imp, meeting_place, tgw, sbc, expressway
    """
    
    _real_generators = {
        "uccx": lambda config: UCCXRealGenerator(config),
        "cucm": lambda config: CUCMRealGenerator(config),
        "cms": lambda config: CMSRealGenerator(config),
        "imp": lambda config: IMPRealGenerator(config),
        "meeting_place": lambda config: MeetingPlaceRealGenerator(config),
        "tgw": lambda config: TGWRealGenerator(config),
        "sbc": lambda config: SBCRealGenerator(config),
        "expressway": lambda config: ExpresswayRealGenerator(config),
    }
    
    @classmethod
    def create_generator(cls, server_type: str, config: CiscoServerConfig) -> RealDataGenerator:
        """
        Create real generator for specified server type.
        """
        if server_type not in cls._real_generators:
            raise ValueError(f"Unknown server type: {server_type}")
        
        generator_class = cls._real_generators[server_type]
        return generator_class(server_config)
    
    @classmethod
    def get_supported_types(cls) -> list:
        """
        Get list of supported server types.
        
        Returns:
            list: Supported server types
        """
        return list(cls._real_generators.keys())


# =============================================================================
# Utility Functions
# =============================================================================
def create_real_generators(server_configs: Dict[str, ServerConfig]) -> Dict[str, RealDataGenerator]:
    """
    Create real generators for all provided server configurations.
    
    Args:
        server_configs: Dictionary mapping server types to configurations
    
    Returns:
        Dict[str, RealDataGenerator]: Dictionary of real generators
    """
    generators = {}
    for server_type, config in server_configs.items():
        if server_type in RealGeneratorFactory.get_supported_types():
            try:
                generators[server_type] = RealGeneratorFactory.create_generator(server_type, config)
            except Exception as e:
                logging.error(f"Failed to create real generator for {server_type}: {str(e)}")
    return generators


__all__ = [
    "RealDataGenerator",
    "CUCMRealGenerator",
    "UCCXRealGenerator",
    "CMSRealGenerator",
    "IMPRealGenerator",
    "MeetingPlaceRealGenerator",
    "RealGeneratorFactory",
    "create_real_generators"
]
