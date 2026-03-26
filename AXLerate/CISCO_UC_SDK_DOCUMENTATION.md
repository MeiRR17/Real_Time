# Cisco UC SDK Documentation

## Overview

The Cisco UC SDK is a comprehensive, production-ready Python SDK for interacting with Cisco Unified Communications Manager (UCM) SOAP APIs. It provides a clean, type-safe interface for all major UCM APIs, eliminating the complexity of direct SOAP integration while maintaining full functionality.

## 🚀 **Version 2.0.0 - Latest Updates**

### ✅ **New Features**
- **Production-Ready AXLerate Integration**: Full REST middleware deployment
- **Multi-Node Support**: Complete cluster monitoring capabilities
- **Enhanced Error Handling**: Robust fallback mechanisms
- **Comprehensive Documentation**: Updated with real-world examples
- **Type Safety**: Full TypedDict models for IDE auto-complete
- **100% REST Architecture**: Eliminates direct SOAP dependencies

### 🔧 **Integration Status**
- **CUCM**: ✅ Fully integrated with AXLerate REST APIs
- **UCCX**: ✅ Full contact center metrics via AXLerate
- **CMS/IMP/MeetingPlace/TGW/SBC/Expressway**: 🔄 Mock data with AXLerate-ready architecture
- **RisPort**: ✅ Device registration and status monitoring
- **Control Center**: ✅ Service management and control

## Features

- 🚀 **Production Ready**: Robust error handling, connection management, and fallback mechanisms
- 🔒 **Type Safe**: Full type hints and TypedDict models for IDE auto-complete
- 📚 **Developer Friendly**: Comprehensive documentation and examples
- 🛡️ **Error Resilient**: Graceful degradation when APIs are unavailable
- 🔄 **Connection Pooling**: Efficient SOAP client management
- 📊 **Comprehensive**: Covers all major UCM SOAP APIs
- 🎯 **Future Proof**: Extensible architecture for new APIs

## Quick Start

### Installation

```bash
pip install zeep requests fastapi uvicorn
```

### Basic Usage

```python
from cisco_uc_sdk import CiscoUCSDK

# Initialize the SDK
sdk = CiscoUCSDK("192.168.1.100", "admin", "password")

# Test all connections
results = sdk.test_all_connections()
print(results)

# Get phone information
phone = sdk.axl.get_phone("SEP001122334455")
print(phone)

# Get performance metrics
metrics = sdk.perfmon.get_system_metrics("192.168.1.100")
print(metrics)

# Get device status
devices = sdk.risport.get_device_by_name(["SEP001122334455"])
print(devices)

# Get service status
services = sdk.control_center.get_all_services_status("192.168.1.100")
print(services)
```

## API Reference

### AXL API (Administrative XML Layer)

The AXL API provides comprehensive CRUD operations for UCM configuration management.

#### SQL Operations

```python
# Execute SQL query
result = sdk.axl.execute_sql_query("SELECT * FROM device WHERE name LIKE 'SEP%'")

# Execute SQL update
result = sdk.axl.execute_sql_update("UPDATE device SET description = 'Updated' WHERE name = 'SEP001122334455'")
```

#### Phone Operations

```python
# Get phone information
phone = sdk.axl.get_phone("SEP001122334455")

# Add new phone
phone_data = {
    "name": "SEP001122334456",
    "product": "Cisco 8841",
    "devicePool": {"name": "Default"},
    "lines": {
        "line": [{
            "pattern": "1001",
            "routePartition": {"name": "Internal"}
        }]
    }
}
result = sdk.axl.add_phone(phone_data)

# Update phone
update_data = {"description": "Updated phone"}
result = sdk.axl.update_phone("SEP001122334456", update_data)

# Delete phone
result = sdk.axl.delete_phone("SEP001122334456")
```

#### User Operations

```python
# Get user information
user = sdk.axl.get_user("jdoe")

# Add new user
user_data = {
    "userid": "jdoe",
    "firstName": "John",
    "lastName": "Doe",
    "department": "IT"
}
result = sdk.axl.add_user(user_data)
```

#### Line Operations

```python
# Get line information
line = sdk.axl.get_line("1001", "Internal")

# Add new line
line_data = {
    "pattern": "1002",
    "routePartition": {"name": "Internal"},
    "description": "New line"
}
result = sdk.axl.add_line(line_data)
```

#### Route Pattern Operations

```python
# Get route pattern
pattern = sdk.axl.get_route_pattern("9.@", "PSTN")

# Add route pattern
pattern_data = {
    "pattern": "9.@",
    "routePartition": {"name": "PSTN"},
    "description": "PSTN access"
}
result = sdk.axl.add_route_pattern(pattern_data)
```

#### Partition and CSS Operations

```python
# Get route partition
partition = sdk.axl.get_route_partition("Internal")

# Add route partition
partition_data = {
    "name": "NewPartition",
    "description": "New partition"
}
result = sdk.axl.add_route_partition(partition_data)

# Get calling search space
css = sdk.axl.get_calling_search_space("Internal_CSS")

# Add calling search space
css_data = {
    "name": "New_CSS",
    "description": "New calling search space",
    "members": {"member": [{"routePartitionName": {"name": "Internal"}}]}
}
result = sdk.axl.add_calling_search_space(css_data)
```

### Perfmon API (Performance Monitoring)

The Perfmon API provides real-time performance metrics from UCM.

#### Basic Performance Collection

```python
# Get system metrics (CPU, Memory, Calls, etc.)
metrics = sdk.perfmon.get_system_metrics("192.168.1.100")

# Collect specific counters
counters = ["CPUUtilization", "MemoryUtilization", "RegisteredPhones"]
result = sdk.perfmon.perfmon_collect_counter_data(
    host="192.168.1.100",
    object_name="Cisco CallManager",
    counters=counters
)
```

#### Advanced Performance Operations

```python
# List available instances for an object
instances = sdk.perfmon.perfmon_list_instances(
    host="192.168.1.100",
    object_name="Cisco CallManager"
)

# List available counters for an object
counters = sdk.perfmon.perfmon_list_counters(
    host="192.168.1.100",
    object_name="Cisco CallManager"
)
```

### RisPort API (Real-Time Information Service)

The RisPort API provides real-time device status and registration information.

#### Device Queries

```python
# Get devices by name
devices = sdk.risport.get_device_by_name(["SEP001122334455", "SEP001122334456"])

# Get devices by MAC address
mac_devices = sdk.risport.get_device_by_mac(["00:11:22:33:44:55", "00:11:22:33:44:56"])

# Get all registered devices
all_registered = sdk.risport.get_all_registered_devices()
```

#### Advanced Device Queries

```python
# Custom device selection criteria
criteria = {
    "MaxReturnedDevices": 100,
    "DeviceClass": "Phone",
    "SelectBy": "Name",
    "SelectItems": {"item": ["SEP001122334455"]},
    "Status": "Registered"
}
result = sdk.risport.select_cm_device(criteria)
```

### Control Center Services API (Serviceability)

The Control Center Services API provides service management and monitoring capabilities.

#### Service Status

```python
# Get all services status
services = sdk.control_center.get_all_services_status("192.168.1.100")

# Get specific service status
cm_status = sdk.control_center.get_service_status("192.168.1.100", "Cisco CallManager")
```

#### Service Control

```python
# Start a service
result = sdk.control_center.start_service("192.168.1.100", "Cisco CTI Manager")

# Stop a service
result = sdk.control_center.stop_service("192.168.1.100", "Cisco CTI Manager")

# Restart a service
result = sdk.control_center.restart_service("192.168.1.100", "Cisco CTI Manager")

# Generic service control
result = sdk.control_center.soap_do_service_control(
    server_name="192.168.1.100",
    service_name="Cisco CallManager",
    action="Restart"
)
```

## Data Models

The SDK provides type-safe data models using TypedDict for better IDE support:

### PhoneInfo
```python
class PhoneInfo(TypedDict):
    uuid: str
    name: str
    description: Optional[str]
    product: str
    model: str
    protocol: str
    device_pool: str
    calling_search_space: Optional[str]
    lines: List[str]
```

### UserInfo
```python
class UserInfo(TypedDict):
    userid: str
    first_name: str
    last_name: str
    department: Optional[str]
    device_pool: Optional[str]
    primary_extension: Optional[str]
    associated_devices: List[str]
```

### DeviceInfo
```python
class DeviceInfo(TypedDict):
    name: str
    ip_address: str
    description: str
    model: str
    status: DeviceStatus
    timestamp: str
    cucm_node: str
```

## Error Handling

The SDK provides comprehensive error handling with standardized response formats:

```python
# All methods return a standardized response
result = sdk.axl.get_phone("SEP001122334455")

if result["success"]:
    phone_data = result["data"]
    print(f"Phone: {phone_data['name']}")
else:
    error_msg = result["error"]
    print(f"Error: {error_msg}")
```

### Response Format

```python
{
    "success": bool,           # Whether the operation succeeded
    "data": dict,             # The returned data (if successful)
    "error": str,              # Error message (if failed)
    "code": str,              # Error code (for SOAP faults)
    "operation": str,          # Operation name
    "timestamp": str          # ISO timestamp
}
```

## Factory Functions

The SDK provides factory functions for creating specific clients:

```python
from cisco_uc_sdk import (
    create_cisco_sdk,
    create_axl_client,
    create_perfmon_client,
    create_risport_client,
    create_control_center_client
)

# Create unified SDK
sdk = create_cisco_sdk("192.168.1.100", "admin", "password")

# Create specific client
axl_client = create_axl_client("192.168.1.100", "admin", "password")
perfmon_client = create_perfmon_client("192.168.1.100", "admin", "password")
```

## Configuration

### SSL Configuration

```python
# Disable SSL verification (for development/lab environments)
sdk = CiscoUCSDK("192.168.1.100", "admin", "password", verify_ssl=False)

# Enable SSL verification (for production)
sdk = CiscoUCSDK("192.168.1.100", "admin", "password", verify_ssl=True)
```

### Port Configuration

```python
# Custom port for different services
sdk = CiscoUCSDK("192.168.1.100", "admin", "password", port=8443)

# UCCX typically uses port 8445
uccx_sdk = CiscoUCSDK("192.168.1.101", "admin", "password", port=8445)
```

## Examples

### Complete Phone Management Workflow

```python
from cisco_uc_sdk import CiscoUCSDK

# Initialize SDK
sdk = CiscoUCSDK("192.168.1.100", "admin", "password")

# 1. Check if phone exists
phone = sdk.axl.get_phone("SEP001122334455")
if not phone["success"]:
    # 2. Add new phone
    phone_data = {
        "name": "SEP001122334455",
        "product": "Cisco 8841",
        "devicePool": {"name": "Default"},
        "lines": {
            "line": [{
                "pattern": "1001",
                "routePartition": {"name": "Internal"}
            }]
        }
    }
    result = sdk.axl.add_phone(phone_data)
    print(f"Phone added: {result['success']}")
else:
    print(f"Phone already exists: {phone['data']['name']}")

# 3. Check device registration status
devices = sdk.risport.get_device_by_name(["SEP001122334455"])
if devices["success"] and devices["devices"]:
    device = devices["devices"][0]
    print(f"Device status: {device['status']}, IP: {device['ip_address']}")

# 4. Get performance metrics
metrics = sdk.perfmon.get_system_metrics("192.168.1.100")
print(f"System metrics: {len(metrics['data'])} counters collected")
```

### Service Health Monitoring

```python
from cisco_uc_sdk import CiscoUCSDK

sdk = CiscoUCSDK("192.168.1.100", "admin", "password")

# Get comprehensive server information
server_info = sdk.get_server_info()

if server_info["success"]:
    print(f"Server: {server_info['server_ip']}")
    print(f"Metrics collected: {len(server_info['metrics'])}")
    print(f"Services checked: {len(server_info['services'])}")
    
    # Check critical services
    critical_services = ["Cisco CallManager", "Cisco CTI Manager"]
    for service in server_info["services"]:
        if service["name"] in critical_services:
            status = service["status"]
            if status != "Started":
                print(f"ALERT: {service['name']} is {status}")
                # Attempt to restart
                restart_result = sdk.control_center.restart_service(
                    "192.168.1.100", service["name"]
                )
                print(f"Restart result: {restart_result['success']}")
```

### Real-time Device Monitoring

```python
from cisco_uc_sdk import CiscoUCSDK
import time

sdk = CiscoUCSDK("192.168.1.100", "admin", "password")

# Monitor specific devices
target_devices = ["SEP001122334455", "SEP001122334456", "SEP001122334457"]

while True:
    try:
        # Get device status
        devices = sdk.risport.get_device_by_name(target_devices)
        
        if devices["success"]:
            for device in devices["devices"]:
                name = device["name"]
                status = device["status"]
                ip = device["ip_address"]
                
                print(f"{name}: {status} ({ip})")
                
                # Alert on unregistered devices
                if status == "Unregistered":
                    print(f"ALERT: {name} is unregistered!")
        
        # Get performance metrics
        metrics = sdk.perfmon.get_system_metrics("192.168.1.100")
        if metrics["success"]:
            cpu = next((m["value"] for m in metrics["data"] if m["name"] == "CPUUtilization"), 0)
            memory = next((m["value"] for m in metrics["data"] if m["name"] == "MemoryUtilization"), 0)
            print(f"System: CPU={cpu}%, Memory={memory}%")
        
        time.sleep(60)  # Check every minute
        
    except KeyboardInterrupt:
        print("Monitoring stopped")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(30)  # Wait before retrying
```

## AXLerate REST API

The SDK is integrated into the AXLerate REST middleware, providing HTTP endpoints for all operations:

### Performance Monitoring Endpoint
```bash
POST /metrics/perfmon
Content-Type: application/json

{
    "server_ip": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "counters": ["CPUUtilization", "MemoryUtilization", "ActiveCalls"],
    "server_type": "cucm"
}
```

### AXL Operations
```bash
# Get phone
GET /axl/phone/SEP001122334455

# Add phone
POST /axl/phone
Content-Type: application/json

{
    "name": "SEP001122334456",
    "product": "Cisco 8841",
    "devicePool": {"name": "Default"}
}

# Execute SQL
POST /axl/sql/query
Content-Type: application/json

{
    "query": "SELECT * FROM device WHERE name LIKE 'SEP%'"
}
```

### Device Information
```bash
# Get devices by name
POST /risport/devices
Content-Type: application/json

{
    "device_names": ["SEP001122334455", "SEP001122334456"]
}

# Get devices by MAC
POST /risport/devices/mac
Content-Type: application/json

{
    "mac_addresses": ["00:11:22:33:44:55"]
}
```

### Service Management
```bash
# Get service status
GET /services/192.168.1.100

# Control service
POST /services/192.168.1.100/Cisco%20CallManager/control
Content-Type: application/json

{
    "action": "Restart"
}
```

## Best Practices

### 1. Connection Management
- Reuse SDK instances when possible for connection pooling
- Test connections before critical operations
- Implement proper error handling and retry logic

### 2. Error Handling
- Always check the `success` field in responses
- Log errors for debugging
- Implement fallback mechanisms for critical operations

### 3. Performance
- Use specific counters instead of getting all metrics
- Batch operations when possible
- Cache frequently accessed data

### 4. Security
- Use SSL verification in production
- Store credentials securely
- Implement proper authentication

### 5. Monitoring
- Monitor API response times
- Track error rates
- Implement health checks

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Verify server IP and credentials
   - Check SSL settings
   - Ensure ports are accessible

2. **Authentication Failures**
   - Verify username and password
   - Check user permissions
   - Ensure AXL service is enabled

3. **SOAP Faults**
   - Check error codes in response
   - Verify request parameters
   - Consult UCM documentation

4. **Performance Issues**
   - Use connection pooling
   - Implement caching
   - Optimize counter selection

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

sdk = CiscoUCSDK("192.168.1.100", "admin", "password")
results = sdk.test_all_connections()
```

## Support

For issues and questions:
1. Check the documentation
2. Review the examples
3. Enable debug logging
4. Check UCM service status
5. Verify network connectivity

## License

This SDK is provided as-is for educational and development purposes. Please ensure compliance with Cisco's licensing terms for production use.
