# Cisco Telephony Monitoring System - Production Deployment Guide

## 🎯 **Table of Contents**
1. [System Overview](#system-overview)
2. [Architecture Components](#architecture-components)
3. [Production Deployment Strategy](#production-deployment-strategy)
4. [Server Preparation](#server-preparation)
5. [Application Packaging](#application-packaging)
6. [ESXi 6.7 Deployment](#esxi-67-deployment)
7. [WinSCP Transfer Process](#winscp-transfer-process)
8. [Service Configuration](#service-configuration)
9. [Cisco Component Integration](#cisco-component-integration)
10. [TGW & SBC Connectivity](#tgw--sbc-connectivity)
11. [SSH vs SNMP Configuration](#ssh-vs-snmp-configuration)
12. [Code Improvements](#code-improvements)
13. [Production Optimization](#production-optimization)
14. [Monitoring & Maintenance](#monitoring--maintenance)
15. [Troubleshooting](#troubleshooting)

---

## 🎯 **System Overview**

The Cisco Telephony Monitoring System is a comprehensive, production-ready microservices architecture designed to collect, process, and visualize telephony metrics from multiple Cisco components in real-time. This system provides centralized monitoring capabilities for enterprise telephony infrastructure, enabling proactive management and optimization of communication services.

### 🎯 **Key Objectives**
- **Unified Monitoring**: Single pane of glass for all Cisco telephony components
- **Real-time Data Collection**: Continuous polling and processing of telephony metrics  
- **Scalable Architecture**: Microservices design supporting horizontal scaling
- **Production Ready**: Enterprise-grade security, reliability, and maintainability
- **Multi-Protocol Support**: SSH, SNMP, and REST API integration capabilities

### 💼 **Business Value**
- Reduced downtime through proactive monitoring
- Optimized resource utilization based on real usage patterns
- Improved capacity planning with historical trend analysis
- Enhanced troubleshooting with correlated metrics across components
- Compliance reporting through comprehensive audit trails

---

## 🏗️ **Architecture Components**

### **Core Microservices**
- **AXLerate REST Middleware** (Port 8002): Cisco UC SDK with 4 major APIs
- **Proxy Gateway** (Port 8000): Central data collection and processing
- **Mock Server** (Port 8001): Development and testing simulation
- **Redis Cache**: Session management and caching layer
- **PostgreSQL Clusters**: 9 separate databases for component isolation

### **Data Flow Architecture**
```
Cisco Components → AXLerate → Proxy Gateway → PostgreSQL → APIs → Frontend
                    ↓           ↓              ↓           ↓
                REST APIs   Data Processing  Storage   Visualization
```

---

## 🚀 **Production Deployment Strategy**

### **Deployment Architecture**
```
Development Server → TAR Package → WinSCP → ESXi 6.7 Server → Production
       ↓                    ↓          ↓           ↓              ↓
   Local Docker        Packaging   File Transfer  VM Setup    Services
```

### **Key Considerations**
- **Server Isolation**: Dedicated ESXi 6.7 host for production
- **Network Security**: VLAN segmentation and firewall rules
- **Data Persistence**: Persistent storage for PostgreSQL databases
- **Backup Strategy**: Automated backups and disaster recovery
- **Monitoring**: System health and performance monitoring

---

## 🖥️ **Server Preparation**

### **ESXi 6.7 Server Requirements**
```bash
# Minimum Hardware Specifications
CPU: 8+ cores (Intel Xeon recommended)
RAM: 32GB+ (64GB recommended for production)
Storage: 500GB+ SSD (1TB+ for large deployments)
Network: Dual NICs for redundancy
```

### **ESXi 6.7 Configuration**
```bash
# 1. Enable SSH Access
# Navigate to: Manage > Services > TSM-SSH > Start

# 2. Create Datastore
# Navigate to: Storage > New Datastore
# Format: VMFS 6
# Size: Allocate sufficient space for containers and databases

# 3. Network Configuration
# Configure Port Groups for different traffic types:
# - Management Network
# - Application Network  
# - Database Network
# - Backup Network

# 4. Security Hardening
# Disable unnecessary services
# Configure firewall rules
# Set up NTP synchronization
```

### **VM Template Creation**
```bash
# Create VM Template with following specifications:
vCPU: 4 cores
RAM: 8GB
Storage: 100GB thin provisioned
OS: Ubuntu 22.04 LTS
Network: Connected to Application Network
```

---

## 📦 **Application Packaging**

### **Step 1: Clean Local Environment**
```bash
# Stop all services
cd /path/to/Real_Time
docker-compose down -v

# Clean up unnecessary files
docker system prune -a
docker volume prune
```

### **Step 2: Create Production TAR Package**
```bash
# Create comprehensive deployment package
tar -czf telephony-monitoring-production.tar.gz \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='.venv' \
    --exclude='tests/' \
    --exclude='*.log' \
    --exclude='node_modules/' \
    .

# Verify package integrity
tar -tzf telephony-monitoring-production.tar.gz | head -20
```

### **Step 3: Package Contents Verification**
```bash
# Expected package structure:
telephony-monitoring-production.tar.gz
├── AXLerate/
│   ├── app/
│   │   ├── main.py
│   │   └── cisco_uc_sdk.py
│   ├── Dockerfile
│   └── requirements.txt
├── proxy-gateway/
│   ├── main.py
│   ├── models.py
│   └── Dockerfile
├── mock-server/
│   ├── main.py
│   └── Dockerfile
├── postgres/
│   ├── cucm-init.sql
│   ├── uccx-init.sql
│   └── [component]-init.sql
├── docker-compose.yml
├── config.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔄 **WinSCP Transfer Process**

### **Step 1: WinSCP Configuration**
```bash
# Connection Settings:
Host: [ESXi Server IP]
Port: 22
Username: root
Password: [ESXi Root Password]
Protocol: SCP

# Advanced Settings:
- Enable compression
- Set timeout to 60 seconds
- Configure keep-alive every 30 seconds
```

### **Step 2: Directory Structure Creation**
```bash
# Create directory structure on ESXi server
mkdir -p /vmfs/volumes/datastore1/telephony-monitoring
mkdir -p /vmfs/volumes/datastore1/telephony-monitoring/app
mkdir -p /vmfs/volumes/datastore1/telephony-monitoring/data
mkdir -p /vmfs/volumes/datastore1/telephony-monitoring/logs
mkdir -p /vmfs/volumes/datastore1/telephony-monitoring/backups
```

### **Step 3: File Transfer**
```bash
# Transfer main package
# Drag telephony-monitoring-production.tar.gz to:
# /vmfs/volumes/datastore1/telephony-monitoring/

# Transfer additional configuration files
# .env.production → /vmfs/volumes/datastore1/telephony-monitoring/.env
# docker-compose.prod.yml → /vmfs/volumes/datastore1/telephony-monitoring/
```

### **Step 4: Post-Transfer Verification**
```bash
# SSH to ESXi server
ssh root@[ESXi IP]

# Verify file integrity
cd /vmfs/volumes/datastore1/telephony-monitoring
ls -la
md5sum telephony-monitoring-production.tar.gz

# Extract package
tar -xzf telephony-monitoring-production.tar.gz
```

---

## 🖥️ **ESXi 6.7 Deployment**

### **Step 1: VM Creation**
```bash
# Using vSphere Client or CLI:
# 1. Right-click on Datacenter > New Virtual Machine
# 2. Configuration: Custom
# 3. Name: telephony-monitoring-prod
# 4. Compatibility: ESXi 6.7
# 5. Guest OS: Linux > Ubuntu Linux (64-bit)
# 6. Storage: Select datastore1
# 7. Network: Application Network
```

### **Step 2: VM Configuration**
```bash
# Hardware Settings:
CPU: 4 vCPU (2 sockets x 2 cores)
RAM: 8192 MB
Hard Disk: 100 GB, Thin Provisioned
Network Adapter: VMXNET3
SCSI Controller: LSI Logic SAS
```

### **Step 3: Ubuntu 22.04 Installation**
```bash
# Mount Ubuntu 22.04 ISO
# Boot VM and install with following settings:
- Language: English
- Timezone: Your timezone
- Keyboard: US English
- Installation type: Minimal
- Network: Configure static IP
- User: telephony (sudo privileges)
```

### **Step 4: System Preparation**
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker telephony

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Configure firewall
sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 8001/tcp
sudo ufw allow 8002/tcp
sudo ufw allow 5432/tcp
sudo ufw allow 6379/tcp
sudo ufw enable
```

---

## ⚙️ **Service Configuration**

### **Step 1: Environment Configuration**
```bash
# Create production environment file
cp .env.example .env

# Edit .env with production values:
nano .env
```

```bash
# Production .env configuration:
# Database Configuration
POSTGRES_USER=telephony_user
POSTGRES_PASSWORD=[STRONG_PASSWORD]
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Multi-Database URLs
CUCM_PRIMARY_URL=postgresql://telephony_user:[PASSWORD]@cucm-postgres:5432/cucm_db
UCCX_PRIMARY_URL=postgresql://telephony_user:[PASSWORD]@uccx-postgres:5432/uccx_db
CMS_PRIMARY_URL=postgresql://telephony_user:[PASSWORD]@cms-postgres:5432/cms_db
IMP_PRIMARY_URL=postgresql://telephony_user:[PASSWORD]@imp-postgres:5432/imp_db
MEETING_PLACE_PRIMARY_URL=postgresql://telephony_user:[PASSWORD]@meeting-place-postgres:5432/meeting_place_db
TGW_PRIMARY_URL=postgresql://telephony_user:[PASSWORD]@tgw-postgres:5432/tgw_db
SBC_PRIMARY_URL=postgresql://telephony_user:[PASSWORD]@sbc-postgres:5432/sbc_db
EXPRESSWAY_PRIMARY_URL=postgresql://telephony_user:[PASSWORD]@expressway-postgres:5432/expressway_db

# Cisco Component Configuration
CUCM_HOST=192.168.1.100
CUCM_USERNAME=admin
CUCM_PASSWORD=[CUCM_PASSWORD]
CUCM_PORT=443

UCCX_HOST=192.168.1.101
UCCX_USERNAME=admin
UCCX_PASSWORD=[UCCX_PASSWORD]
UCCX_PORT=443

# TGW Configuration
TGW_HOST=192.168.1.102
TGW_SNMP_COMMUNITY=[SNMP_COMMUNITY]
TGW_SNMP_PORT=161
TGW_SNMP_VERSION=2c
TGW_SNMP_TIMEOUT=5
USE_REAL_TGW=true

# SBC Configuration
SBC_HOST=192.168.1.103
SBC_USERNAME=admin
SBC_PASSWORD=[SBC_PASSWORD]
SBC_PORT=443
SBC_VERIFY_SSL=false
USE_REAL_SBC=true

# Application Configuration
ENABLE_POLLING=true
POLLING_INTERVAL=60
REQUEST_TIMEOUT=10
PYTHONUNBUFFERED=1
```

### **Step 2: Production Docker Compose**
```bash
# Create production-specific docker-compose
cp docker-compose.yml docker-compose.prod.yml

# Edit for production settings:
nano docker-compose.prod.yml
```

```yaml
# Production modifications in docker-compose.prod.yml:
version: '3.8'

services:
  proxy-gateway:
    restart: always
    environment:
      DATABASE_URL: postgresql://telephony_user:[PASSWORD]@cucm-postgres:5432/cucm_db
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  axlerate:
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  mock-server:
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  redis:
    restart: always
    command: >
      redis-server
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --save 300 10
      --save 60 10000

  [component]-postgres:
    restart: always
    environment:
      POSTGRES_USER: telephony_user
      POSTGRES_PASSWORD: [STRONG_PASSWORD]
    volumes:
      - [component]_postgres_data:/var/lib/postgresql/data
      - ./logs/postgres/[component]:/var/log/postgresql
```

### **Step 3: Service Startup**
```bash
# Build and start services
docker-compose -f docker-compose.prod.yml up -d --build

# Verify service health
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f proxy-gateway
```

---

## 🔌 **Cisco Component Integration**

### **Step 1: Network Connectivity**
```bash
# Verify network connectivity to Cisco components
ping 192.168.1.100  # CUCM
ping 192.168.1.101  # UCCX
ping 192.168.1.102  # TGW
ping 192.168.1.103  # SBC

# Test port accessibility
telnet 192.168.1.100 443  # CUCM HTTPS
telnet 192.168.1.101 443  # UCCX HTTPS
telnet 192.168.1.102 161  # TGW SNMP
telnet 192.168.1.103 22   # SBC SSH
```

### **Step 2: CUCM Integration**
```bash
# Test AXL API access
curl -k -u "admin:[PASSWORD]" \
     "https://192.168.1.100:8443/axl/" \
     -H "Content-Type: text/xml" \
     -d '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:axl="http://www.cisco.com/AXL/API/1.0">
           <soapenv:Body>
             <axl:executeSQLQuery>
               <axl:sql>SELECT count(*) FROM device</axl:sql>
             </axl:executeSQLQuery>
           </soapenv:Body>
         </soapenv:Envelope>'

# Test Perfmon API
curl -k -u "admin:[PASSWORD]" \
     "https://192.168.1.100:8443/perfmonservice/"
```

### **Step 3: UCCX Integration**
```bash
# Test UCCX API access
curl -k -u "admin:[PASSWORD]" \
     "https://192.168.1.101:8443/adminapi/csq"

# Test Real-time data
curl -k -u "admin:[PASSWORD]" \
     "https://192.168.1.101:8443/adminapi/agent"
```

### **Step 4: Service Configuration Updates**
```python
# Update config.py with real Cisco credentials
# In config.py, update the following classes:

class CiscoServerConfig:
    # CUCM Configuration
    cucm_host: str = "192.168.1.100"
    cucm_username: str = "admin"
    cucm_password: str = "[CUCM_PASSWORD]"
    cucm_port: int = 443
    cucm_verify_ssl: bool = False
    
    # UCCX Configuration  
    uccx_host: str = "192.168.1.101"
    uccx_username: str = "admin"
    uccx_password: str = "[UCCX_PASSWORD]"
    uccx_port: int = 443
    uccx_verify_ssl: bool = False
    
    # TGW Configuration
    tgw_host: str = "192.168.1.102"
    tgw_snmp_community: str = "[SNMP_COMMUNITY]"
    tgw_snmp_port: int = 161
    tgw_snmp_version: str = "2c"
    
    # SBC Configuration
    sbc_host: str = "192.168.1.103"
    sbc_username: str = "admin"
    sbc_password: str = "[SBC_PASSWORD]"
    sbc_port: int = 443
    sbc_verify_ssl: bool = False
```

---

## 🌐 **TGW & SBC Connectivity**

### **TGW (Telephony Gateway) Integration**

#### **Step 1: SNMP Configuration**
```bash
# Install SNMP tools
sudo apt install snmp snmp-mibs-downloader -y

# Test SNMP connectivity
snmpwalk -v2c -c [SNMP_COMMUNITY] 192.168.1.102 1.3.6.1.2.1.1

# Test specific TGW OIDs
snmpget -v2c -c [SNMP_COMMUNITY] 192.168.1.102 \
         1.3.6.1.4.1.9.9.63.1.3.1.1.1  # Active calls
snmpget -v2c -c [SNMP_COMMUNITY] 192.168.1.102 \
         1.3.6.1.4.1.9.9.63.1.3.2.1.1  # CPU utilization
```

#### **Step 2: TGW SNMP Integration Code**
```python
# Create new file: TGW_SNMP_Client.py
import pysnmp.hlapi as snmp
from typing import Dict, List, Optional
import logging

class TGWSNMPClient:
    """SNMP client for Cisco Telephony Gateway monitoring"""
    
    def __init__(self, host: str, community: str, port: int = 161):
        self.host = host
        self.community = community
        self.port = port
        self.logger = logging.getLogger(__name__)
    
    def get_snmp_data(self, oid: str) -> Optional[str]:
        """Get SNMP data for specific OID"""
        try:
            error_indication, error_status, error_index, var_binds = next(
                snmp.getCmd(
                    snmp.SnmpEngine(),
                    snmp.CommunityData(self.community, mpModel=0),
                    snmp.UdpTransportTarget((self.host, self.port)),
                    snmp.ContextData(),
                    snmp.ObjectType(snmp.ObjectIdentity(oid))
                )
            )
            
            if error_indication:
                self.logger.error(f"SNMP error: {error_indication}")
                return None
            
            for var_bind in var_binds:
                return str(var_bind[1])
                
        except Exception as e:
            self.logger.error(f"SNMP query failed: {str(e)}")
            return None
    
    def get_active_calls(self) -> int:
        """Get number of active calls"""
        oid = "1.3.6.1.4.1.9.9.63.1.3.1.1.1"
        value = self.get_snmp_data(oid)
        return int(value) if value else 0
    
    def get_cpu_utilization(self) -> float:
        """Get CPU utilization percentage"""
        oid = "1.3.6.1.4.1.9.9.63.1.3.2.1.1"
        value = self.get_snmp_data(oid)
        return float(value) if value else 0.0
    
    def get_memory_utilization(self) -> float:
        """Get memory utilization percentage"""
        oid = "1.3.6.1.4.1.9.9.63.1.3.2.1.2"
        value = self.get_snmp_data(oid)
        return float(value) if value else 0.0
    
    def get_all_metrics(self) -> Dict[str, any]:
        """Get all TGW metrics"""
        return {
            "active_calls": self.get_active_calls(),
            "cpu_utilization": self.get_cpu_utilization(),
            "memory_utilization": self.get_memory_utilization(),
            "timestamp": datetime.utcnow().isoformat()
        }
```

### **SBC (Session Border Controller) Integration**

#### **Step 1: SSH Configuration**
```bash
# Test SSH connectivity
ssh admin@192.168.1.103 "show version"

# Set up SSH key authentication
ssh-keygen -t rsa -b 4096 -f ~/.ssh/sbc_key
ssh-copy-id -i ~/.ssh/sbc_key.pub admin@192.168.1.103
```

#### **Step 2: SBC SSH Integration Code**
```python
# Create new file: SBC_SSH_Client.py
import paramiko
from typing import Dict, List, Optional
import logging
from datetime import datetime

class SBCSSHClient:
    """SSH client for Cisco Session Border Controller monitoring"""
    
    def __init__(self, host: str, username: str, password: str, port: int = 22):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.logger = logging.getLogger(__name__)
        self.client = None
    
    def connect(self) -> bool:
        """Establish SSH connection"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            return True
        except Exception as e:
            self.logger.error(f"SSH connection failed: {str(e)}")
            return False
    
    def execute_command(self, command: str) -> Optional[str]:
        """Execute command via SSH"""
        if not self.client:
            if not self.connect():
                return None
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            output = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()
            
            if error:
                self.logger.warning(f"SSH command warning: {error}")
            
            return output
        except Exception as e:
            self.logger.error(f"SSH command failed: {str(e)}")
            return None
    
    def get_active_sessions(self) -> int:
        """Get number of active sessions"""
        command = "show sipd active sessions count"
        output = self.execute_command(command)
        
        if output:
            # Parse output to extract session count
            lines = output.split('\n')
            for line in lines:
                if 'Active sessions:' in line:
                    return int(line.split(':')[1].strip())
        return 0
    
    def get_cpu_utilization(self) -> float:
        """Get CPU utilization"""
        command = "show process cpu | include CPU"
        output = self.execute_command(command)
        
        if output:
            # Parse CPU percentage from output
            lines = output.split('\n')
            for line in lines:
                if '%' in line:
                    return float(line.split('%')[0].strip())
        return 0.0
    
    def get_memory_utilization(self) -> float:
        """Get memory utilization"""
        command = "show process memory | include Memory"
        output = self.execute_command(command)
        
        if output:
            # Parse memory percentage from output
            lines = output.split('\n')
            for line in lines:
                if '%' in line and 'Memory' in line:
                    return float(line.split('%')[0].strip())
        return 0.0
    
    def get_all_metrics(self) -> Dict[str, any]:
        """Get all SBC metrics"""
        return {
            "active_sessions": self.get_active_sessions(),
            "cpu_utilization": self.get_cpu_utilization(),
            "memory_utilization": self.get_memory_utilization(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def disconnect(self):
        """Close SSH connection"""
        if self.client:
            self.client.close()
            self.client = None
```

---

## 🔧 **SSH vs SNMP Configuration**

### **SSH Configuration (Preferred for SBC)**

#### **Advantages:**
- Secure encrypted communication
- Full command access
- Real-time data retrieval
- Detailed system information
- Better error handling

#### **Configuration Steps:**
```bash
# 1. Enable SSH on SBC
# Connect to SBC console and run:
configure terminal
ssh server enable
ssh server algorithm encryption aes128-cbc aes192-cbc aes256-cbc
ssh server algorithm hmac hmac-sha1 hmac-sha256
exit

# 2. Create monitoring user
configure terminal
username monitoring password [STRONG_PASSWORD] role network-operator
exit

# 3. Configure SSH access lists
configure terminal
ip access-list extended SSH_ACCESS
permit tcp host [MONITORING_SERVER_IP] any eq 22
deny tcp any any eq 22
permit ip any any
exit

# 4. Apply access list to SSH
line vty 0 4
access-class SSH_ACCESS in
transport input ssh
exit
```

### **SNMP Configuration (Preferred for TGW)**

#### **Advantages:**
- Lightweight protocol
- Standardized interface
- Low overhead
- Fast polling
- Wide tool support

#### **Configuration Steps:**
```bash
# 1. Enable SNMP on TGW
# Connect to TGW console and run:
configure terminal
snmp-server community [COMMUNITY_NAME] ro
snmp-server location "Data Center Rack 1"
snmp-server contact "Network Team"
exit

# 2. Configure SNMP access lists
configure terminal
snmp-server access-list SNMP_ACCESS
ip access-list standard SNMP_ACCESS
permit [MONITORING_SERVER_IP]
deny any
exit

# 3. Enable SNMP traps (optional)
configure terminal
snmp-server enable traps
snmp-server host [MONITORING_SERVER_IP] version 2c [COMMUNITY_NAME]
exit
```

### **Configuration Comparison**

| Feature | SSH | SNMP |
|---------|-----|------|
| Security | High (encrypted) | Medium (community string) |
| Data Access | Full command access | Limited to SNMP OIDs |
| Performance | Medium (connection overhead) | High (lightweight) |
| Complexity | Higher | Lower |
| Use Case | SBC (complex data) | TGW (simple metrics) |

---

## 🛠️ **Code Improvements**

### **1. Enhanced Error Handling**
```python
# Update proxy-gateway/main.py
import asyncio
from typing import Dict, Any, Optional
import backoff

class EnhancedDataCollector:
    """Enhanced data collector with retry logic and error handling"""
    
    @backoff.on_exception(backoff.expo,
                         (requests.exceptions.RequestException,
                          requests.exceptions.Timeout,
                          requests.exceptions.ConnectionError),
                         max_tries=3,
                         max_time=60)
    async def collect_metrics_with_retry(self, url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Collect metrics with exponential backoff retry"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.error(f"HTTP {response.status} from {url}")
                        return None
        except Exception as e:
            self.logger.error(f"Failed to collect metrics from {url}: {str(e)}")
            raise
    
    async def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect metrics from all sources with error handling"""
        results = {}
        
        # Collect from UCCX
        try:
            results['uccx'] = await self.collect_metrics_with_retry(
                f"{self.uccx_url}/api/uccx/stats"
            )
        except Exception as e:
            self.logger.error(f"UCCX collection failed: {str(e)}")
            results['uccx'] = {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
        
        # Collect from CUCM
        try:
            results['cucm'] = await self.collect_metrics_with_retry(
                f"{self.cucm_url}/api/cucm/system/stats"
            )
        except Exception as e:
            self.logger.error(f"CUCM collection failed: {str(e)}")
            results['cucm'] = {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
        
        # Collect from TGW
        try:
            results['tgw'] = await self.collect_tgw_metrics()
        except Exception as e:
            self.logger.error(f"TGW collection failed: {str(e)}")
            results['tgw'] = {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
        
        # Collect from SBC
        try:
            results['sbc'] = await self.collect_sbc_metrics()
        except Exception as e:
            self.logger.error(f"SBC collection failed: {str(e)}")
            results['sbc'] = {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
        
        return results
```

### **2. Production Configuration Management**
```python
# Create config/production.py
from pydantic import BaseSettings, validator
from typing import List, Optional
import os

class ProductionConfig(BaseSettings):
    """Production configuration with validation"""
    
    # Database Configuration
    postgres_user: str
    postgres_password: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    
    # Cisco Component Configuration
    cucm_host: str
    cucm_username: str
    cucm_password: str
    cucm_port: int = 443
    cucm_verify_ssl: bool = False
    
    uccx_host: str
    uccx_username: str
    uccx_password: str
    uccx_port: int = 443
    uccx_verify_ssl: bool = False
    
    # TGW Configuration
    tgw_host: str
    tgw_snmp_community: str
    tgw_snmp_port: int = 161
    tgw_snmp_version: str = "2c"
    tgw_snmp_timeout: int = 5
    
    # SBC Configuration
    sbc_host: str
    sbc_username: str
    sbc_password: str
    sbc_port: int = 443
    sbc_verify_ssl: bool = False
    
    # Application Configuration
    enable_polling: bool = True
    polling_interval: int = 60
    request_timeout: int = 10
    log_level: str = "INFO"
    
    @validator('postgres_password')
    def validate_password_strength(cls, v):
        if len(v) < 12:
            raise ValueError('Password must be at least 12 characters')
        return v
    
    @validator('cucm_host', 'uccx_host', 'tgw_host', 'sbc_host')
    def validate_ip_address(cls, v):
        import ipaddress
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f'Invalid IP address: {v}')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

### **3. Enhanced Logging**
```python
# Create logging_config.py
import logging
import logging.config
from pathlib import Path

def setup_production_logging():
    """Setup production logging configuration"""
    
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "detailed",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "json",
                "filename": "/app/logs/telephony-monitoring.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "json",
                "filename": "/app/logs/telephony-monitoring-error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "loggers": {
            "": {
                "level": "INFO",
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["file"],
                "propagate": False
            }
        }
    }
    
    # Create log directory
    Path("/app/logs").mkdir(exist_ok=True)
    
    # Apply configuration
    logging.config.dictConfig(log_config)
```

---

## 🚀 **Production Optimization**

### **1. Performance Tuning**
```yaml
# docker-compose.prod.yml performance optimizations
version: '3.8'

services:
  proxy-gateway:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
    environment:
      - WORKERS=4
      - MAX_CONNECTIONS=100
      - KEEP_ALIVE=2
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

  redis:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
    command: >
      redis-server
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --save 300 10
      --save 60 10000
      --tcp-keepalive 60
      --timeout 0

  postgres:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
    environment:
      - POSTGRES_SHARED_PRELOAD_LIBRARIES=pg_stat_statements
      - POSTGRES_MAX_CONNECTIONS=200
      - POSTGRES_SHARED_BUFFERS=256MB
      - POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
      - POSTGRES_WORK_MEM=4MB
      - POSTGRES_MAINTENANCE_WORK_MEM=64MB
```

### **2. Database Optimization**
```sql
-- Create indexes for performance
CREATE INDEX CONCURRENTLY idx_telephony_metrics_timestamp 
ON telephony_metrics (timestamp DESC);

CREATE INDEX CONCURRENTLY idx_telephony_metrics_server_type_timestamp 
ON telephony_metrics (server_type, timestamp DESC);

CREATE INDEX CONCURRENTLY idx_telephony_metrics_server_name_timestamp 
ON telephony_metrics (server_name, timestamp DESC);

-- Partitioning for large datasets (optional)
CREATE TABLE telephony_metrics_y2024m01 PARTITION OF telephony_metrics
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Materialized views for common queries
CREATE MATERIALIZED VIEW mv_current_metrics AS
SELECT 
    server_type,
    server_name,
    metric_name,
    metric_value,
    unit,
    timestamp
FROM telephony_metrics 
WHERE timestamp >= NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

-- Refresh materialized view
CREATE OR REPLACE FUNCTION refresh_current_metrics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_current_metrics;
END;
$$ LANGUAGE plpgsql;
```

### **3. Caching Strategy**
```python
# Enhanced caching with Redis
import redis
import json
from typing import Optional, Any
from datetime import timedelta

class ProductionCache:
    """Production-ready caching with Redis"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = 300  # 5 minutes
    
    async def get_cached_metrics(self, key: str) -> Optional[Any]:
        """Get cached metrics"""
        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logging.error(f"Cache get error: {str(e)}")
        return None
    
    async def cache_metrics(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Cache metrics with TTL"""
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(data, default=str)
            return self.redis.setex(key, ttl, serialized)
        except Exception as e:
            logging.error(f"Cache set error: {str(e)}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys by pattern"""
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
        except Exception as e:
            logging.error(f"Cache invalidation error: {str(e)}")
        return 0
```

---

## 📊 **Monitoring & Maintenance**

### **1. Health Check Endpoints**
```python
# Enhanced health checks
from fastapi import FastAPI, HTTPException
from typing import Dict, Any
import asyncio

app = FastAPI()

@app.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
        "metrics": {}
    }
    
    # Check database connectivity
    try:
        db_status = await check_database_health()
        health_status["services"]["database"] = db_status
    except Exception as e:
        health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Check Redis connectivity
    try:
        redis_status = await check_redis_health()
        health_status["services"]["redis"] = redis_status
    except Exception as e:
        health_status["services"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Check Cisco component connectivity
    try:
        cisco_status = await check_cisco_connectivity()
        health_status["services"]["cisco"] = cisco_status
    except Exception as e:
        health_status["services"]["cisco"] = {"status": "unhealthy", "error": str(e)}
    
    # Check system metrics
    try:
        system_metrics = await get_system_metrics()
        health_status["metrics"] = system_metrics
    except Exception as e:
        health_status["metrics"] = {"error": str(e)}
    
    return health_status

async def check_database_health() -> Dict[str, Any]:
    """Check database connectivity and performance"""
    # Implementation for database health check
    pass

async def check_redis_health() -> Dict[str, Any]:
    """Check Redis connectivity"""
    # Implementation for Redis health check
    pass

async def check_cisco_connectivity() -> Dict[str, Any]:
    """Check Cisco component connectivity"""
    # Implementation for Cisco connectivity check
    pass

async def get_system_metrics() -> Dict[str, Any]:
    """Get system performance metrics"""
    # Implementation for system metrics
    pass
```

### **2. Automated Maintenance**
```bash
#!/bin/bash
# maintenance.sh - Automated maintenance script

# Log rotation
logrotate() {
    echo "Rotating logs..."
    docker-compose exec proxy-gateway logrotate /etc/logrotate.d/telephony-monitoring
}

# Database maintenance
database_maintenance() {
    echo "Performing database maintenance..."
    
    # Vacuum and analyze tables
    docker-compose exec postgres psql -U telephony_user -d cucm_db -c "VACUUM ANALYZE;"
    docker-compose exec postgres psql -U telephony_user -d uccx_db -c "VACUUM ANALYZE;"
    
    # Update statistics
    docker-compose exec postgres psql -U telephony_user -d cucm_db -c "ANALYZE;"
    docker-compose exec postgres psql -U telephony_user -d uccx_db -c "ANALYZE;"
    
    # Refresh materialized views
    docker-compose exec postgres psql -U telephony_user -d cucm_db -c "SELECT refresh_current_metrics();"
}

# Cache cleanup
cache_cleanup() {
    echo "Cleaning up Redis cache..."
    docker-compose exec redis redis-cli FLUSHDB
}

# Health check
health_check() {
    echo "Performing health check..."
    curl -f http://localhost:8000/health/detailed || exit 1
}

# Backup
backup() {
    echo "Creating backup..."
    ./backup.sh
}

# Main execution
case "$1" in
    logrotate)
        logrotate
        ;;
    database)
        database_maintenance
        ;;
    cache)
        cache_cleanup
        ;;
    health)
        health_check
        ;;
    backup)
        backup
        ;;
    all)
        logrotate
        database_maintenance
        cache_cleanup
        health_check
        backup
        ;;
    *)
        echo "Usage: $0 {logrotate|database|cache|health|backup|all}"
        exit 1
        ;;
esac

echo "Maintenance completed successfully!"
```

### **3. Monitoring Dashboard**
```python
# monitoring.py - Production monitoring
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import FastAPI, Response
import time

# Prometheus metrics
REQUEST_COUNT = Counter('telephony_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('telephony_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('telephony_active_connections', 'Active connections')
METRICS_COLLECTED = Counter('telephony_metrics_collected_total', 'Metrics collected', ['component'])

@app.middleware("http")
async def monitor_requests(request, call_next):
    """Monitor HTTP requests"""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(duration)
    
    return response

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")

# Custom metrics collection
async def update_custom_metrics():
    """Update custom application metrics"""
    # Update active connections
    ACTIVE_CONNECTIONS.set(get_active_connections())
    
    # Update metrics collected
    for component in ['uccx', 'cucm', 'tgw', 'sbc']:
        METRICS_COLLECTED.labels(component=component).inc(get_metrics_count(component))
```

---

## 🔧 **Troubleshooting**

### **Common Issues and Solutions**

#### **1. Service Startup Failures**
```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# Check service logs
docker-compose -f docker-compose.prod.yml logs [service_name]

# Common startup issues:
# - Port conflicts: Check if ports 8000-8002 are available
# - Database connection: Verify PostgreSQL is running
# - Network issues: Check Docker network configuration
```

#### **2. Database Connection Issues**
```bash
# Test database connectivity
docker-compose exec postgres psql -U telephony_user -d cucm_db -c "SELECT 1;"

# Check database logs
docker-compose logs postgres

# Common database issues:
# - Incorrect credentials in .env file
# - Database not initialized
# - Network connectivity issues
```

#### **3. Cisco Component Connectivity**
```bash
# Test network connectivity
ping [CISCO_COMPONENT_IP]
telnet [CISCO_COMPONENT_IP] [PORT]

# Test API access
curl -k -u "username:password" "https://[CISCO_IP]:8443/axl/"

# Common Cisco issues:
# - Incorrect credentials
# - SSL certificate issues
# - Network firewall blocking
# - Service not running on Cisco component
```

#### **4. Performance Issues**
```bash
# Check system resources
docker stats
top
htop

# Check database performance
docker-compose exec postgres psql -U telephony_user -d cucm_db -c "SELECT * FROM pg_stat_activity;"

# Common performance issues:
# - Insufficient memory/CPU
# - Database query optimization
# - Network latency
# - Too many concurrent connections
```

#### **5. Memory Issues**
```bash
# Check memory usage
free -h
docker stats --no-stream

# Clean up Docker
docker system prune -a
docker volume prune

# Common memory issues:
# - Memory leaks in applications
# - Insufficient allocated memory
# - Database memory usage
# - Cache buildup
```

### **Emergency Procedures**

#### **Service Recovery**
```bash
# Emergency restart
docker-compose -f docker-compose.prod.yml restart [service_name]

# Full system restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# Database recovery
docker-compose exec postgres pg_dump -U telephony_user cucm_db > backup.sql
docker-compose exec postgres psql -U telephony_user cucm_db < backup.sql
```

#### **Data Recovery**
```bash
# Restore from backup
./restore.sh [backup_file]

# Manual data recovery
docker-compose exec postgres psql -U telephony_user -d cucm_db -c "SELECT COUNT(*) FROM telephony_metrics;"
```

---

## 📝 **Conclusion**

This comprehensive deployment guide provides everything needed to successfully deploy the Cisco Telephony Monitoring System in a production environment using ESXi 6.7. The system is designed to be:

- **Scalable**: Microservices architecture supporting horizontal scaling
- **Reliable**: Built-in redundancy and failover capabilities  
- **Secure**: Enterprise-grade security with encrypted communications
- **Maintainable**: Comprehensive logging, monitoring, and maintenance procedures
- **Production-Ready**: Optimized for performance and stability

The deployment process includes:
1. **Server Preparation** - ESXi 6.7 configuration and VM setup
2. **Application Packaging** - TAR file creation and transfer
3. **Service Deployment** - Docker Compose orchestration
4. **Cisco Integration** - Multi-protocol connectivity (SSH/SNMP)
5. **Monitoring Setup** - Comprehensive health monitoring
6. **Maintenance Procedures** - Automated maintenance and backup

With this guide, you can successfully deploy and manage a production-grade telephony monitoring system that provides real-time insights into your Cisco telephony infrastructure.

---

## 🎯 **Next Steps**

1. **Deploy the System**: Follow the deployment steps in order
2. **Configure Cisco Components**: Set up SSH/SNMP access
3. **Test Connectivity**: Verify all components are communicating
4. **Monitor Performance**: Set up monitoring and alerting
5. **Establish Maintenance**: Configure automated maintenance procedures

For additional support or questions, refer to the troubleshooting section or contact the system administrator.

---

## Architecture Components

### 1. AXLerate REST Middleware Service 🆕
**NEW**: Comprehensive REST middleware for Cisco UCM SOAP APIs
- **Cisco UC SDK**: Production-ready SDK supporting 4 major APIs
  - AXL API (Administrative XML Layer) - Configuration management
  - Perfmon API (Performance Monitoring) - Real-time metrics
  - RisPort API (Real-Time Information Service) - Device status
  - Control Center Services API (Serviceability) - Service management
- **REST Endpoints**: Complete CRUD operations for all Cisco components
- **Swagger Documentation**: Interactive API docs at `http://localhost:8002/docs`
- **Error Resilience**: Graceful degradation and fallback mechanisms
- **Multi-Node Support**: Handles multiple UCM nodes seamlessly

### 2. PostgreSQL Database Layer
The foundational data store providing persistence for all telephony metrics and system metadata.

**Technical Specifications:**
- PostgreSQL 15 Alpine for optimal performance and minimal footprint
- Dual database architecture: `telephony_db` (application data) and `superset_db` (metadata)
- Automated health checks with 10-second intervals
- Persistent volume storage for data durability
- Connection pooling support for high concurrency

**Database Design Principles:**
- Multi-node aware schema supporting clustered Cisco deployments
- Time-series optimization for efficient metric storage and retrieval
- Foreign key relationships maintaining data integrity across services
- Indexing strategy optimized for common query patterns in telephony analytics

### 3. Proxy Gateway Service
Enhanced data collection service now consuming AXLerate REST APIs instead of direct SOAP calls.

**NEW Features:**
- **AXLerate Integration**: Consumes REST endpoints for all Cisco components
- **Multi-Node Collection**: Iterates over multiple nodes per service type
- **Real API Integration**: 
  - CUCM: Full performance monitoring via AXLerate `/metrics/perfmon`
  - UCCX: Contact center metrics via AXLerate `/metrics/perfmon`
  - CMS/IMP/MeetingPlace/TGW/SBC/Expressway: Mock data with future AXLerate readiness
- **Error Resilience**: Fallback to safe values when AXLerate unavailable
- **Node Identification**: Metrics tagged with server_name and server_ip for database distinction

**Configuration:**
- `AXLERATE_URL=http://axlerate:8000` - AXLerate service endpoint
- Multi-node support via `CUCM_NODES`, `UCCX_NODES`, etc. environment variables
- Automatic retry logic with exponential backoff
- Comprehensive logging for debugging and monitoring

**Technical Specifications:**
- PostgreSQL 15 Alpine for optimal performance and minimal footprint
- Dual database architecture: `telephony_db` (application data) and `superset_db` (metadata)
- Automated health checks with 10-second intervals
- Persistent volume storage for data durability
- Connection pooling support for high concurrency

**Database Design Principles:**
- Normalized schema for data integrity
- Indexed columns for optimal query performance
- Time-series data partitioning capabilities
- Automated cleanup policies for historical data management

### 2. Mock Server Service
Development and testing component simulating Cisco telephony APIs with realistic data patterns.

**Service Characteristics:**
- FastAPI-based REST API server
- Supports all 8 major Cisco component types
- Generates realistic metrics with proper statistical distributions
- Health check endpoints for service monitoring
- Configurable data generation patterns

**API Endpoints:**
```
GET /health - Service health verification
GET /api/stats/{server_type} - Component-specific metrics
```

**Supported Component Types:**
- UCCX (Unified Contact Center Express)
- CUCM (Unified Communications Manager)
- IMP (Instant Messaging and Presence)
- MP (Media Processor)
- CMS (Meeting Server)
- TGW (Telephony Gateway)
- SBC (Session Border Controller)
- Expressway (Video Communication Gateway)

---

## AXLerate REST API Documentation

### 🚀 **Service Overview**
The AXLerate service provides a comprehensive REST interface for Cisco UCM SOAP APIs, eliminating the need for direct SOAP integration while maintaining full functionality.

### 📍 **Access Points**
- **Swagger UI**: `http://localhost:8002/docs`
- **ReDoc**: `http://localhost:8002/redoc`
- **OpenAPI JSON**: `http://localhost:8002/openapi.json`
- **Health Check**: `http://localhost:8002/health`

### 📊 **Core Endpoints**

#### **Performance Monitoring**
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

#### **AXL Administrative Operations**
```bash
# Phone Management
GET /axl/phone/{phone_name}           # Get phone info
POST /axl/phone                          # Add phone
PUT /axl/phone/{phone_name}           # Update phone
DELETE /axl/phone/{phone_name}        # Delete phone

# User Management  
GET /axl/user/{user_id}              # Get user info
POST /axl/user                         # Add user

# SQL Operations
POST /axl/sql/query
{
    "query": "SELECT * FROM device WHERE name LIKE 'SEP%'"
}

# Route Configuration
GET /axl/route-pattern/{pattern}/{partition}
POST /axl/route-pattern
GET /axl/route-partition/{name}
POST /axl/route-partition
GET /axl/calling-search-space/{name}
POST /axl/calling-search-space
```

#### **RisPort Device Information**
```bash
POST /risport/devices
{
    "device_names": ["SEP001122334455", "SEP001122334456"]
}

POST /risport/devices/mac  
{
    "mac_addresses": ["00:11:22:33:44:55", "00:11:22:33:44:56"]
}

GET /risport/devices/registered    # Get all registered devices
```

#### **Service Management**
```bash
GET /services/{server_name}                    # Get all services status
POST /services/{server_name}/{service_name}/control
{
    "action": "Start"  # or "Stop" or "Restart"
}
```

#### **System Information**
```bash
GET /health                    # Service health
GET /sdk/info                  # SDK capabilities and status
GET /                          # Service overview
```

### 🔧 **Cisco UC SDK Features**

#### **Supported APIs**
1. **AXL API** - Administrative XML Layer
   - Complete CRUD operations for phones, users, lines, route patterns
   - SQL query execution for custom reporting
   - Partition and Calling Search Space management

2. **Perfmon API** - Performance Monitoring
   - Real-time counter collection
   - Dynamic counter discovery
   - Multi-object monitoring (CallManager, UCCX, etc.)

3. **RisPort API** - Real-Time Information Service
   - Device registration status
   - IP address and node information
   - MAC address lookup capabilities

4. **Control Center Services API** - Serviceability
   - Service status monitoring
   - Start/Stop/Restart operations
   - Multi-service management

#### **Developer Experience**
- **Type Safety**: Full TypedDict models for IDE auto-complete
- **Error Handling**: Comprehensive SOAP fault handling
- **Connection Pooling**: Efficient client management
- **Factory Functions**: Easy instantiation patterns
- **Extensible Design**: Simple addition of new APIs

### 🛡️ **Production Features**
- **Graceful Degradation**: Fallback to mock data when APIs unavailable
- **Connection Management**: Automatic retry with exponential backoff
- **SSL Configuration**: Flexible certificate verification
- **Logging Integration**: Comprehensive error and performance logging
- **Health Monitoring**: Service availability checks

---

## Supported Cisco Components
Core data collection engine providing asynchronous polling and data processing capabilities.

**Architecture Highlights:**
- AsyncIO-based implementation for optimal resource utilization
- SQLModel integration for unified database operations
- HTTPx client for efficient network communications
- Background task management with proper lifecycle handling
- Comprehensive error handling and retry mechanisms

**Data Collection Process:**
1. Continuous 10-second polling cycle across all components
2. Parallel HTTP requests to minimize latency
3. Data validation and transformation
4. Batch database operations for performance
5. Comprehensive logging for audit trails

**Technical Features:**
- Connection pooling for database efficiency
- Graceful degradation during component failures
- Automatic retry logic with exponential backoff
- Memory-efficient streaming data processing

### 4. Apache Superset Visualization Layer
Enterprise-grade business intelligence platform providing interactive dashboards and analytics.

**Configuration Features:**
- Custom PostgreSQL driver integration
- Secure authentication configuration
- Automated admin user creation
- Optimized Gunicorn server deployment
- Inline initialization script for cross-platform compatibility

**Dashboard Capabilities:**
- Real-time metric visualization
- Historical trend analysis
- Custom chart types for telephony data
- Interactive filtering and drill-down
- Automated report generation

---

## Installation and Deployment

### 🚀 **Quick Start with AXLerate**

#### **Prerequisites**
- Docker and Docker Compose
- Git for source code management
- 8GB+ RAM for full stack deployment

#### **Step 1: Clone Repository**
```bash
git clone https://github.com/your-org/superset-conf-lab-master.git
cd superset-conf-lab-master
```

#### **Step 2: Configure Environment**
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Key Configuration for AXLerate:**
```bash
# AXLerate Service
AXLERATE_URL=http://axlerate:8000
AXL_USER=admin
AXL_PASSWORD=password
AXL_PORT=8443
AXL_VERIFY_SSL=false

# Multi-Node Support
CUCM_NODES=192.168.1.100,192.168.1.101
UCCX_NODES=192.168.1.110,192.168.1.111
```

#### **Step 3: Deploy Services**
```bash
# Deploy all services
docker-compose up -d

# Deploy specific services
docker-compose up -d postgres axlerate proxy-gateway superset
```

#### **Step 4: Verify Deployment**
```bash
# Check service status
docker-compose ps

# Check AXLerate health
curl http://localhost:8002/health

# Access Swagger documentation
open http://localhost:8002/docs
```

### 🐳 **Docker Service Architecture**

#### **AXLerate Service**
```yaml
axlerate:
  build: ./AXLerate
  ports:
    - "8002:8000"
  environment:
    - AXL_USER=${AXL_USER:-admin}
    - AXL_PASSWORD=${AXL_PASSWORD:-password}
    - AXL_PORT=${AXL_PORT:-8443}
    - AXL_VERIFY_SSL=${AXL_VERIFY_SSL:-false}
  depends_on:
    - postgres
  networks:
    - telephony-network
  healthcheck:
    test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
    interval: 30s
    timeout: 10s
    retries: 3
```

#### **Proxy Gateway Integration**
```yaml
proxy-gateway:
  build: ./proxy-gateway
  environment:
    - AXLERATE_URL=http://axlerate:8000
    - CUCM_NODES=${CUCM_NODES}
    - UCCX_NODES=${UCCX_NODES}
    # ... other node configurations
  depends_on:
    - postgres
    - axlerate
  networks:
    - telephony-network
```

### 🔧 **Configuration Management**

#### **Multi-Node Setup Examples**

**Single Node Configuration:**
```bash
# .env file for single CUCM node
CUCM_NODES=192.168.1.100
CUCM_USERNAME=administrator
CUCM_PASSWORD=your_password
CUCM_PORT=8443
```

**Cluster Configuration:**
```bash
# .env file for CUCM cluster
CUCM_NODES=192.168.1.100,192.168.1.101,192.168.1.102
CUCM_USERNAME=cluster_admin
CUCM_PASSWORD=cluster_password
CUCM_PORT=8443

# Results in database:
# - CUCM-Node-1 (192.168.1.100)
# - CUCM-Node-2 (192.168.1.101) 
# - CUCM-Node-3 (192.168.1.102)
```

**Mixed Environment Configuration:**
```bash
# Development environment
CUCM_NODES=dev-cucm-01,dev-cucm-02
UCCX_NODES=dev-uccx-01
CMS_NODES=dev-cms-01

# Production environment
CUCM_NODES=prod-cucm-01,prod-cucm-02,prod-cucm-03
UCCX_NODES=prod-uccx-01,prod-uccx-02
```

#### **Service Discovery and Health Checks**

**AXLerate Service Health:**
```bash
# Basic health check
curl http://localhost:8002/health

# Expected response
{
  "status": "healthy",
  "service": "axlerate", 
  "timestamp": "2026-03-26T01:42:41.671552"
}
```

**SDK Information:**
```bash
# Check SDK capabilities and connections
curl http://localhost:8002/sdk/info

# Expected response
{
  "sdk_version": "2.0.0",
  "supported_apis": ["AXL", "Perfmon", "RisPort", "Control Center"],
  "connections": {
    "axl": {"success": true},
    "perfmon": {"success": true},
    "risport": {"success": true},
    "control_center": {"success": true}
  }
}
```

---

## Data Flow Architecture

### Collection Pipeline
```
Cisco Components → Mock Server → Proxy Gateway → PostgreSQL → Superset
     ↓                ↓              ↓              ↓           ↓
   Real APIs     Development    Data Processing   Storage    Visualization
```

### Data Processing Stages

#### Stage 1: Data Acquisition
- **Source**: Cisco component APIs (real or mocked)
- **Protocol**: HTTP/HTTPS REST APIs
- **Frequency**: Every 10 seconds
- **Format**: JSON response structures

#### Stage 2: Data Processing
- **Validation**: Schema verification and data type enforcement
- **Transformation**: Normalization to unified data model
- **Enrichment**: Timestamp addition and server type classification
- **Batching**: Grouped database operations for efficiency

#### Stage 3: Data Storage
- **Database**: PostgreSQL with optimized indexing
- **Schema**: Unified metrics table with component classification
- **Retention**: Configurable data lifecycle policies
- **Backup**: Automated point-in-time recovery capabilities

#### Stage 4: Data Visualization
- **Real-time**: Live dashboard updates
- **Historical**: Trend analysis and reporting
- **Alerting**: Threshold-based notifications
- **Export**: Multiple format support (PDF, CSV, Excel)

---

## Supported Cisco Components

### 1. UCCX (Unified Contact Center Express)
**Functionality**: Contact center operations and call routing
**Metrics Collected**:
- Active calls count
- CPU utilization percentage
- Memory usage percentage
- Queue statistics
- Agent availability

**API Integration**: RESTful API endpoints for real-time statistics
**Data Frequency**: Every 10 seconds
**Historical Retention**: 13 months default

### 2. CUCM (Unified Communications Manager)
**Functionality**: Core call processing and telephony management
**Metrics Collected**:
- Active calls count
- CPU utilization percentage
- Memory usage percentage
- Registered devices
- Call completion rates

**API Integration**: AXL API and Real-Time Monitoring Tool (RTMT)
**Data Sources**: CDR (Call Detail Records) and RISDB (Real-time Information Service Database)
**Data Frequency**: Every 10 seconds

### 3. IMP (Instant Messaging and Presence)
**Functionality**: Instant messaging and presence services
**Metrics Collected**:
- Active users count
- CPU utilization percentage
- Memory usage percentage
- Message throughput
- Presence status distribution

**API Integration**: Presence REST APIs
**Data Frequency**: Every 10 seconds

### 4. MP (Media Processor)
**Functionality**: Media processing and transcoding services
**Metrics Collected**:
- Active media sessions
- CPU utilization percentage
- Memory usage percentage
- Transcoding operations
- Bandwidth utilization

**API Integration**: Media processing APIs
**Data Frequency**: Every 10 seconds

### 5. CMS (Meeting Server)
**Functionality**: Video conferencing and meeting services
**Metrics Collected**:
- Active meetings count
- CPU utilization percentage
- Memory usage percentage
- Participant statistics
- Video quality metrics

**API Integration**: Meeting Server APIs
**Data Frequency**: Every 10 seconds

### 6. TGW (Telephony Gateway)
**Functionality**: PSTN and SIP gateway services
**Metrics Collected**:
- Active gateway sessions
- CPU utilization percentage
- Memory usage percentage
- Call success rates
- Protocol distribution

**API Integration**: Gateway management APIs
**Data Frequency**: Every 10 seconds

### 7. SBC (Session Border Controller)
**Functionality**: Network border security and session management
**Metrics Collected**:
- Active sessions count
- CPU utilization percentage
- Memory usage percentage
- Security events
- Throughput metrics

**API Integration**: SBC management APIs
**Data Frequency**: Every 10 seconds

### 8. Expressway (Video Communication Gateway)
**Functionality**: Video communication and mobility services
**Metrics Collected**:
- Active video sessions
- CPU utilization percentage
- Memory usage percentage
- Mobility registrations
- Quality metrics

**API Integration**: Expressway APIs
**Data Frequency**: Every 10 seconds

---

## Data Types and Sources

### Call Detail Records (CDR)
**Description**: Comprehensive call logging information from CUCM
**Data Elements**:
- Calling and called party numbers
- Call start and end times
- Call duration and direction
- Route patterns and trunk usage
- Call disposition codes
- Quality of service metrics

**Collection Method**: Direct database connection to CUCM CDR database
**Processing**: Real-time extraction and transformation
**Storage**: Optimized for time-series queries and reporting

### Real-time Information Service Database (RISDB)
**Description**: Live status information from CUCM components
**Data Elements**:
- Device registration status
- Server performance metrics
- Service availability
- Resource utilization
- Network connectivity

**Collection Method**: RISDB API queries
**Processing**: Continuous polling with delta detection
**Storage**: Current state tracking with historical snapshots

### Performance Metrics
**Description**: System performance indicators across all components
**Data Elements**:
- CPU utilization (percentage)
- Memory usage (percentage)
- Disk I/O operations
- Network throughput
- Application-specific metrics

**Collection Method**: Component-specific APIs
**Processing**: Statistical aggregation and trend analysis
**Storage**: Time-series optimized schema

### Quality Metrics
**Description**: Call quality and user experience indicators
**Data Elements**:
- Mean Opinion Score (MOS)
- Jitter and latency measurements
- Packet loss statistics
- Codec utilization
- Bandwidth consumption

**Collection Method**: Quality monitoring APIs
**Processing**: Real-time calculation and alerting
**Storage**: Detailed quality records for analysis

---

## Database Schema Design

### Core Metrics Table
```sql
CREATE TABLE telephony_metrics (
    id SERIAL PRIMARY KEY,
    server_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    value DECIMAL(10,2) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_system VARCHAR(50),
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for optimal query performance
CREATE INDEX idx_telephony_metrics_server_type ON telephony_metrics(server_type);
CREATE INDEX idx_telephony_metrics_metric_name ON telephony_metrics(metric_name);
CREATE INDEX idx_telephony_metrics_timestamp ON telephony_metrics(timestamp);
CREATE INDEX idx_telephony_metrics_composite ON telephony_metrics(server_type, metric_name, timestamp);
```

### CDR Processing Table
```sql
CREATE TABLE cdr_records (
    id SERIAL PRIMARY KEY,
    global_call_id VARCHAR(50) UNIQUE NOT NULL,
    calling_party_number VARCHAR(50),
    called_party_number VARCHAR(50),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    orig_device_name VARCHAR(100),
    dest_device_name VARCHAR(100),
    calling_party_ip_addr INET,
    dest_ip_addr INET,
    cause_code INTEGER,
    original_cause_code INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for CDR queries
CREATE INDEX idx_cdr_global_call_id ON cdr_records(global_call_id);
CREATE INDEX idx_cdr_start_time ON cdr_records(start_time);
CREATE INDEX idx_cdr_calling_party ON cdr_records(calling_party_number);
CREATE INDEX idx_cdr_called_party ON cdr_records(called_party_number);
```

### Device Status Table
```sql
CREATE TABLE device_status (
    id SERIAL PRIMARY KEY,
    device_name VARCHAR(100) NOT NULL,
    device_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    ip_address INET,
    registration_time TIMESTAMP WITH TIME ZONE,
    last_seen TIMESTAMP WITH TIME ZONE,
    cpu_usage DECIMAL(5,2),
    memory_usage DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for device tracking
CREATE INDEX idx_device_status_device_name ON device_status(device_name);
CREATE INDEX idx_device_status_status ON device_status(status);
CREATE INDEX idx_device_status_last_seen ON device_status(last_seen);
```

### Alert Configuration Table
```sql
CREATE TABLE alert_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    server_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    threshold_value DECIMAL(10,2) NOT NULL,
    comparison_operator VARCHAR(10) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    notification_channels TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Data Retention Policies
```sql
-- Partitioning for large datasets
CREATE TABLE telephony_metrics_y2024m01 PARTITION OF telephony_metrics
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Automated cleanup procedure
CREATE OR REPLACE FUNCTION cleanup_old_metrics()
RETURNS void AS $$
BEGIN
    DELETE FROM telephony_metrics 
    WHERE timestamp < NOW() - INTERVAL '13 months';
    
    DELETE FROM cdr_records 
    WHERE start_time < NOW() - INTERVAL '13 months';
    
    DELETE FROM device_status 
    WHERE last_seen < NOW() - INTERVAL '13 months';
END;
$$ LANGUAGE plpgsql;

-- Schedule cleanup job
SELECT cron.schedule('cleanup-old-data', '0 2 * * 0', 'SELECT cleanup_old_metrics();');
```

---

## Installation and Deployment

### Prerequisites
- Docker Desktop (Windows) or Docker Engine (Linux)
- Docker Compose v2.0 or later
- Minimum 8GB RAM
- 50GB available disk space
- Network access to Cisco components (for production deployment)

### Quick Start Installation

#### Step 1: Environment Setup
```bash
# Clone the repository
git clone <repository-url>
cd cisco-telephony-monitor

# Verify Docker installation
docker --version
docker compose version
```

#### Step 2: Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit configuration parameters
nano .env
```

#### Step 3: Service Deployment
```bash
# Build and start all services
docker compose up -d --build

# Verify service status
docker compose ps

# Check service logs
docker compose logs -f
```

#### Step 4: Initial Configuration
```bash
# Wait for services to initialize (approximately 2 minutes)
sleep 120

# Verify database connectivity
docker compose exec postgres psql -U postgres -d telephony_db -c "SELECT COUNT(*) FROM telephony_metrics;"

# Test API endpoints
curl http://localhost:8001/health
curl http://localhost:8000/health
```

#### Step 5: Access Applications
- **Apache Superset**: http://localhost:8088 (admin/admin)
- **Mock Server API**: http://localhost:8001
- **Proxy Gateway API**: http://localhost:8000

### Production Deployment Considerations

#### Security Hardening
```bash
# Update default passwords
# Edit superset_config.py to change SECRET_KEY
# Update PostgreSQL credentials in docker-compose.yml
# Configure firewall rules for port access
```

#### Resource Allocation
```yaml
# Production docker-compose.yml modifications
services:
  postgres:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 2G
          cpus: '1.0'
  
  superset:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

#### High Availability Setup
```yaml
# Multiple instances for redundancy
services:
  postgres:
    image: postgres:15-alpine
    deploy:
      replicas: 2
      placement:
        max_replicas_per_node: 1
  
  proxy-gateway:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
```

---

## Configuration Management

### Environment Variables
```bash
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password_change_me
POSTGRES_DB=telephony_db

# Superset Configuration
SUPERSET_SECRET_KEY=your-secret-key-here
SUPERSET_ADMIN_USERNAME=admin
SUPERSET_ADMIN_PASSWORD=change_me

# API Configuration
API_TIMEOUT_SECONDS=30
POLLING_INTERVAL_SECONDS=10
MAX_RETRY_ATTEMPTS=3

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Component-Specific Configuration

#### Mock Server Configuration
```python
# mock-server/config.py
class MockServerConfig:
    SUPPORTED_SERVERS = [
        "uccx", "cucm", "imp", "mp", "cms", "tgw", "sbc", "expressway"
    ]
    
    # Data generation parameters
    MIN_ACTIVE_CALLS = 10
    MAX_ACTIVE_CALLS = 1000
    MIN_CPU_USAGE = 10.0
    MAX_CPU_USAGE = 95.0
    MIN_MEMORY_USAGE = 30.0
    MAX_MEMORY_USAGE = 90.0
    
    # API configuration
    API_HOST = "0.0.0.0"
    API_PORT = 8001
    WORKERS = 1
```

#### Proxy Gateway Configuration
```python
# proxy-gateway/config.py
class ProxyGatewayConfig:
    # Database configuration
    DATABASE_URL = "postgresql://postgres:password@postgres:5432/telephony_db"
    DATABASE_POOL_SIZE = 10
    DATABASE_MAX_OVERFLOW = 20
    
    # Polling configuration
    POLLING_INTERVAL = 10  # seconds
    TARGET_SERVERS = [
        "uccx", "cucm", "imp", "mp", "cms", "tgw", "sbc", "expressway"
    ]
    
    # HTTP client configuration
    HTTP_TIMEOUT = 30.0
    HTTP_RETRIES = 3
    HTTP_BACKOFF_FACTOR = 0.3
    
    # Logging configuration
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
```

#### Superset Configuration
```python
# superset/superset_config.py
# Database configuration
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:password@postgres:5432/superset_db'

# Security configuration
SECRET_KEY = 'super-secret-telephony-key-for-standalone-deployment-x86'

# Feature configuration
BABEL_DEFAULT_LOCALE = 'en'
WTF_CSRF_ENABLED = False

# Performance configuration
SUPERSET_WORKERS = 2
SUPERSET_TIMEOUT = 120

# Logging configuration
LOG_LEVEL = 'INFO'
```

### Dynamic Configuration Updates
```bash
# Reload configuration without restart
docker compose exec proxy-gateway kill -HUP 1

# Update environment variables
docker compose up -d --force-recreate proxy-gateway

# Scale services dynamically
docker compose up -d --scale proxy-gateway=3
```

---

## Real-world Implementation Guide

### Phase 1: Development Environment Setup

#### Step 1: Mock Data Generation
Configure the mock server to generate realistic data patterns matching your production environment:

```python
# mock-server/data_generator.py
class RealisticDataGenerator:
    def __init__(self):
        self.business_hours_start = 9
        self.business_hours_end = 17
        self.weekend_multiplier = 0.3
        
    def generate_active_calls(self, server_type, timestamp):
        base_calls = random.randint(50, 500)
        
        # Business hours adjustment
        if self.is_business_hours(timestamp):
            base_calls *= 2.5
        elif self.is_weekend(timestamp):
            base_calls *= self.weekend_multiplier
            
        # Server-specific adjustments
        if server_type == "uccx":
            base_calls *= 1.5  # Higher call center volume
        elif server_type == "cucm":
            base_calls *= 2.0  # Core PBX volume
            
        return int(base_calls)
```

#### Step 2: Data Validation
Implement comprehensive data validation to ensure data quality:

```python
# proxy-gateway/data_validator.py
class DataValidator:
    REQUIRED_FIELDS = ["server_type", "timestamp", "metrics"]
    
    def validate_response(self, data):
        """Validate API response structure"""
        for field in self.REQUIRED_FIELDS:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
                
        if not isinstance(data["metrics"], dict):
            raise ValidationError("Metrics must be a dictionary")
            
        return True
        
    def validate_metric_value(self, metric_name, value):
        """Validate individual metric values"""
        if metric_name == "active_calls":
            return isinstance(value, (int, float)) and value >= 0
        elif metric_name in ["cpu_usage", "memory_usage"]:
            return isinstance(value, (int, float)) and 0 <= value <= 100
        return False
```

### Phase 2: Production Integration

#### Step 1: Cisco Component Discovery
Automatically discover and register Cisco components in your network:

```python
# proxy-gateway/discovery.py
class CiscoComponentDiscovery:
    def __init__(self):
        self.cucm_servers = []
        self.uccx_servers = []
        self.other_components = []
        
    def discover_cucm_servers(self):
        """Discover CUCM servers via AXL API"""
        # Implementation for CUCM publisher discovery
        pass
        
    def discover_uccx_servers(self):
        """Discover UCCX servers via REST API"""
        # Implementation for UCCX discovery
        pass
        
    def register_components(self):
        """Register discovered components in database"""
        for server in self.cucm_servers:
            self.register_server("cucm", server)
```

#### Step 2: CDR Integration
Implement CDR data collection from CUCM:

```python
# proxy-gateway/cdr_collector.py
class CDRCollector:
    def __init__(self, cucm_connection):
        self.cucm_connection = cucm_connection
        self.last_cdr_id = 0
        
    def collect_cdr_data(self):
        """Collect new CDR records from CUCM"""
        query = """
        SELECT * FROM cdr 
        WHERE globalCallID > %s 
        ORDER BY globalCallID
        LIMIT 1000
        """
        
        with self.cucm_connection.cursor() as cursor:
            cursor.execute(query, (self.last_cdr_id,))
            records = cursor.fetchall()
            
        for record in records:
            self.process_cdr_record(record)
            self.last_cdr_id = max(self.last_cdr_id, record[0])
            
    def process_cdr_record(self, record):
        """Process individual CDR record"""
        cdr_data = {
            'global_call_id': record[0],
            'calling_party': record[1],
            'called_party': record[2],
            'start_time': record[3],
            'end_time': record[4],
            'duration': record[5]
        }
        
        self.store_cdr_record(cdr_data)
```

#### Step 3: RISDB Integration
Implement real-time status collection from RISDB:

```python
# proxy-gateway/risdb_collector.py
class RISDBCollector:
    def __init__(self, cucm_connection):
        self.cucm_connection = cucm_connection
        
    def collect_device_status(self):
        """Collect device status from RISDB"""
        query = """
        SELECT d.name, d.description, s.status, s.registrationTime
        FROM device d
        JOIN deviceStatus s ON d.pkid = s.fkdevice
        WHERE d.tkclass = 1
        """
        
        with self.cucm_connection.cursor() as cursor:
            cursor.execute(query)
            devices = cursor.fetchall()
            
        for device in devices:
            self.update_device_status(device)
            
    def collect_server_metrics(self):
        """Collect server performance metrics"""
        servers = self.get_cucm_servers()
        
        for server in servers:
            metrics = self.get_server_performance(server)
            self.store_server_metrics(server, metrics)
```

### Phase 3: Advanced Features

#### Step 1: Alerting System
Implement threshold-based alerting:

```python
# proxy-gateway/alerting.py
class AlertingSystem:
    def __init__(self):
        self.alert_rules = self.load_alert_rules()
        self.notification_channels = self.setup_notifications()
        
    def check_thresholds(self, metrics):
        """Check metrics against alert thresholds"""
        for metric in metrics:
            for rule in self.alert_rules:
                if self.matches_rule(metric, rule):
                    self.trigger_alert(metric, rule)
                    
    def trigger_alert(self, metric, rule):
        """Trigger alert notification"""
        alert_data = {
            'server_type': metric.server_type,
            'metric_name': metric.metric_name,
            'current_value': metric.value,
            'threshold': rule.threshold_value,
            'severity': rule.severity,
            'timestamp': datetime.utcnow()
        }
        
        for channel in rule.notification_channels:
            self.send_notification(channel, alert_data)
```

#### Step 2: Data Aggregation
Implement statistical aggregation for trend analysis:

```python
# proxy-gateway/aggregation.py
class DataAggregator:
    def __init__(self):
        self.aggregation_intervals = [5, 15, 60, 1440]  # minutes
        
    def aggregate_metrics(self, interval_minutes):
        """Aggregate metrics by time interval"""
        query = """
        SELECT 
            server_type,
            metric_name,
            date_trunc('minute', timestamp) as period,
            AVG(value) as avg_value,
            MIN(value) as min_value,
            MAX(value) as max_value,
            COUNT(*) as sample_count
        FROM telephony_metrics
        WHERE timestamp >= NOW() - INTERVAL '%s minutes'
        GROUP BY server_type, metric_name, period
        """
        
        with Session(engine) as session:
            results = session.execute(text(query), (interval_minutes,))
            return results.fetchall()
```

---

## Superset Dashboard Configuration

### Step 1: Database Connection Setup

#### Access Superset
1. Navigate to http://localhost:8088
2. Login with credentials: admin/admin
3. Access "Settings" → "Database Connections"

#### Configure PostgreSQL Connection
```
Connection String: postgresql://postgres:password@postgres:5432/telephony_db
Display Name: Cisco Telephony Database
Engine: PostgreSQL
```

#### Advanced Configuration
```sql
-- Enable SSL if required
sslmode=require

-- Set connection pool parameters
pool_size=5
max_overflow=10
```

### Step 2: Dataset Configuration

#### Create Metrics Dataset
1. Navigate to "Datasets" → "Add Dataset"
2. Select "Cisco Telephony Database"
3. Choose table: `telephony_metrics`
4. Configure columns:
   - `timestamp` (Temporal)
   - `server_type` (String)
   - `metric_name` (String)
   - `value` (Numeric)

#### Create CDR Dataset
1. Select table: `cdr_records`
2. Configure columns:
   - `start_time` (Temporal)
   - `calling_party_number` (String)
   - `called_party_number` (String)
   - `duration_seconds` (Numeric)
   - `cause_code` (Numeric)

#### Create Device Status Dataset
1. Select table: `device_status`
2. Configure columns:
   - `device_name` (String)
   - `device_type` (String)
   - `status` (String)
   - `last_seen` (Temporal)
   - `cpu_usage` (Numeric)

### Step 3: Chart Creation

#### Real-time Metrics Chart
1. Navigate to "Charts" → "Add Chart"
2. Select "telephony_metrics" dataset
3. Chart Type: "Time Series Line Chart"
4. Configuration:
   - Time Column: `timestamp`
   - Metric Column: `value`
   - Group By: `server_type`, `metric_name`
   - Time Range: "Last 24 hours"
   - Refresh Interval: "10 seconds"

#### CPU Utilization Gauge
1. Chart Type: "Gauge Chart"
2. Configuration:
   - Metric: `AVG(value)`
   - Filter: `metric_name = 'cpu_usage'`
   - Group By: `server_type`
   - Max Value: 100

#### Call Volume Bar Chart
1. Chart Type: "Bar Chart"
2. Configuration:
   - Metric: `SUM(value)`
   - Filter: `metric_name = 'active_calls'`
   - Group By: `server_type`
   - Time Range: "Last hour"

#### CDR Analysis Dashboard
1. Chart Type: "Histogram"
2. Configuration:
   - Metric: `COUNT(*)`
   - Group By: `duration_seconds`
   - Bins: 20
   - Time Range: "Last 7 days"

### Step 4: Dashboard Assembly

#### Create Main Dashboard
1. Navigate to "Dashboards" → "Add Dashboard"
2. Dashboard Name: "Cisco Telephony Monitoring"
3. Layout: "Grid"

#### Add Charts to Dashboard
1. Drag and drop charts onto dashboard
2. Configure chart sizes and positions
3. Set dashboard refresh interval: "30 seconds"

#### Dashboard Layout Example
```
┌─────────────────────────────────────────────────────────────┐
│                    System Overview                           │
├─────────────────┬─────────────────┬─────────────────────────┤
│  CPU Usage      │  Memory Usage   │  Active Calls           │
│  (Gauge Charts) │  (Gauge Charts) │  (Line Chart)           │
├─────────────────┼─────────────────┼─────────────────────────┤
│  Server Status  │  Call Quality   │  Historical Trends      │
│  (Table View)   │  (Heat Map)     │  (Time Series)          │
├─────────────────┴─────────────────┴─────────────────────────┤
│                    Alert Summary                             │
└─────────────────────────────────────────────────────────────┘
```

### Step 5: Advanced Dashboard Features

#### Custom SQL Queries
```sql
-- Average response time by server type
SELECT 
    server_type,
    AVG(value) as avg_response_time,
    COUNT(*) as sample_count
FROM telephony_metrics 
WHERE metric_name = 'response_time'
    AND timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY server_type
ORDER BY avg_response_time DESC;
```

#### Drill-down Configuration
1. Configure parent chart with drill-through links
2. Set target dashboard and filter parameters
3. Enable cross-filtering between charts

#### Dashboard Filters
1. Add global time range filter
2. Add server type multi-select filter
3. Add metric name filter
4. Add threshold filter for alerting

### Step 6: Dashboard Sharing and Export

#### Share Dashboard
1. Navigate to dashboard settings
2. Configure sharing permissions
3. Generate shareable links
4. Set up scheduled email reports

#### Export Options
1. PDF export for reports
2. CSV export for data analysis
3. Image export for presentations
4. API access for integration

---

## Monitoring and Alerting

### System Health Monitoring

#### Service Health Checks
```python
# monitoring/health_checker.py
class HealthChecker:
    def __init__(self):
        self.services = {
            'mock-server': 'http://mock-server:8001/health',
            'proxy-gateway': 'http://proxy-gateway:8000/health',
            'postgres': 'postgresql://postgres:password@postgres:5432/telephony_db',
            'superset': 'http://superset:8088/health'
        }
        
    def check_all_services(self):
        """Check health of all services"""
        results = {}
        
        for service, endpoint in self.services.items():
            results[service] = self.check_service_health(service, endpoint)
            
        return results
        
    def check_service_health(self, service, endpoint):
        """Check individual service health"""
        try:
            if service == 'postgres':
                return self.check_postgres_health(endpoint)
            else:
                return self.check_http_health(endpoint)
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
```

#### Database Performance Monitoring
```sql
-- Monitor database connections
SELECT 
    count(*) as active_connections,
    state,
    application_name
FROM pg_stat_activity 
WHERE state = 'active'
GROUP BY state, application_name;

-- Monitor slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Monitor table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Alert Configuration

#### Threshold-Based Alerts
```python
# alerting/threshold_alerts.py
class ThresholdAlerts:
    def __init__(self):
        self.thresholds = {
            'cpu_usage': {'warning': 70, 'critical': 90},
            'memory_usage': {'warning': 80, 'critical': 95},
            'active_calls': {'warning': 800, 'critical': 950}
        }
        
    def check_thresholds(self, metrics):
        """Check metrics against thresholds"""
        alerts = []
        
        for metric in metrics:
            if metric.metric_name in self.thresholds:
                threshold = self.thresholds[metric.metric_name]
                
                if metric.value >= threshold['critical']:
                    alerts.append(self.create_alert(metric, 'critical'))
                elif metric.value >= threshold['warning']:
                    alerts.append(self.create_alert(metric, 'warning'))
                    
        return alerts
```

#### Anomaly Detection
```python
# alerting/anomaly_detection.py
class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.1)
        self.training_data = []
        
    def train_model(self, historical_data):
        """Train anomaly detection model"""
        features = self.extract_features(historical_data)
        self.model.fit(features)
        
    def detect_anomalies(self, current_data):
        """Detect anomalies in current data"""
        features = self.extract_features(current_data)
        predictions = self.model.predict(features)
        
        anomalies = []
        for i, prediction in enumerate(predictions):
            if prediction == -1:  # Anomaly detected
                anomalies.append({
                    'timestamp': current_data[i]['timestamp'],
                    'server_type': current_data[i]['server_type'],
                    'metric_name': current_data[i]['metric_name'],
                    'value': current_data[i]['value'],
                    'anomaly_score': self.model.decision_function([features[i]])[0]
                })
                
        return anomalies
```

### Notification Channels

#### Email Notifications
```python
# notifications/email_notifier.py
class EmailNotifier:
    def __init__(self, smtp_config):
        self.smtp_server = smtp_config['server']
        self.smtp_port = smtp_config['port']
        self.username = smtp_config['username']
        self.password = smtp_config['password']
        
    def send_alert_email(self, alert):
        """Send alert via email"""
        subject = f"Cisco Telephony Alert: {alert['severity'].upper()}"
        body = self.format_alert_email(alert)
        
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(
                from_addr=self.username,
                to_addr=alert['recipients'],
                msg=f"Subject: {subject}\n\n{body}"
            )
```

#### Slack Integration
```python
# notifications/slack_notifier.py
class SlackNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        
    def send_slack_alert(self, alert):
        """Send alert to Slack channel"""
        payload = {
            'text': f"Cisco Telephony Alert: {alert['severity'].upper()}",
            'attachments': [{
                'color': self.get_color_by_severity(alert['severity']),
                'fields': [
                    {'title': 'Server Type', 'value': alert['server_type'], 'short': True},
                    {'title': 'Metric', 'value': alert['metric_name'], 'short': True},
                    {'title': 'Current Value', 'value': str(alert['value']), 'short': True},
                    {'title': 'Timestamp', 'value': alert['timestamp'], 'short': True}
                ]
            }]
        }
        
        requests.post(self.webhook_url, json=payload)
```

---

## Security Considerations

### Network Security

#### Firewall Configuration
```bash
# Docker network isolation
docker network create --driver bridge telephony-internal
docker network connect telephony-internal telephony-postgres
docker network connect telephony-internal telephony-proxy-gateway

# Port access control
# Only expose necessary ports to external network
# PostgreSQL: Internal only (5432)
# Mock Server: Internal only (8001)
# Proxy Gateway: External (8000)
# Superset: External (8088)
```

#### SSL/TLS Configuration
```python
# security/ssl_config.py
class SSLConfiguration:
    def configure_postgres_ssl(self):
        """Configure PostgreSQL SSL"""
        return {
            'sslmode': 'require',
            'sslcert': '/path/to/client-cert.pem',
            'sslkey': '/path/to/client-key.pem',
            'sslrootcert': '/path/to/ca-cert.pem'
        }
        
    def configure_api_ssl(self):
        """Configure API SSL endpoints"""
        return {
            'certfile': '/path/to/server-cert.pem',
            'keyfile': '/path/to/server-key.pem',
            'ca_certs': '/path/to/ca-cert.pem'
        }
```

### Authentication and Authorization

#### Superset Security
```python
# superset/security_config.py
# Enable authentication
AUTH_TYPE = 0  # Database authentication
AUTH_ROLE_ADMIN_PUBLIC = False

# Configure role-based access
ROLE_CONFIG = {
    'Admin': ['can_read', 'can_write', 'can_delete'],
    'Operator': ['can_read'],
    'Viewer': ['can_read']
}

# Session security
PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
```

#### API Security
```python
# security/api_security.py
class APISecurity:
    def __init__(self):
        self.api_keys = self.load_api_keys()
        
    def authenticate_request(self, request):
        """Authenticate API request"""
        api_key = request.headers.get('X-API-Key')
        
        if not api_key or api_key not in self.api_keys:
            return False
            
        return self.validate_api_key(api_key)
        
    def rate_limit_request(self, client_ip):
        """Implement rate limiting"""
        key = f"rate_limit:{client_ip}"
        current_count = redis.incr(key)
        
        if current_count == 1:
            redis.expire(key, 60)  # 1 minute window
            
        return current_count <= 100  # 100 requests per minute
```

### Data Protection

#### Encryption at Rest
```bash
# Configure PostgreSQL encryption
# Enable transparent data encryption
ALTER SYSTEM SET ssl = on;
ALTER SYSTEM SET ssl_cert_file = '/path/to/server-cert.pem';
ALTER SYSTEM SET ssl_key_file = '/path/to/server-key.pem';

# Restart PostgreSQL for changes to take effect
docker compose restart postgres
```

#### Encryption in Transit
```python
# security/encryption.py
class DataEncryption:
    def __init__(self):
        self.encryption_key = os.environ.get('ENCRYPTION_KEY')
        
    def encrypt_sensitive_data(self, data):
        """Encrypt sensitive data before storage"""
        cipher = Fernet(self.encryption_key)
        return cipher.encrypt(data.encode()).decode()
        
    def decrypt_sensitive_data(self, encrypted_data):
        """Decrypt sensitive data for processing"""
        cipher = Fernet(self.encryption_key)
        return cipher.decrypt(encrypted_data.encode()).decode()
```

### Audit Logging

#### Comprehensive Audit Trail
```sql
-- Create audit log table
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    action VARCHAR(100) NOT NULL,
    table_name VARCHAR(100),
    record_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

-- Create audit trigger
CREATE OR REPLACE FUNCTION audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (
        user_id, action, table_name, record_id,
        old_values, new_values, ip_address, user_agent
    ) VALUES (
        current_setting('app.current_user_id'),
        TG_OP,
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        row_to_json(OLD),
        row_to_json(NEW),
        inet_client_addr(),
        current_setting('app.user_agent')
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;
```

---

## Performance Optimization

### Database Optimization

#### Query Performance
```sql
-- Create optimal indexes
CREATE INDEX CONCURRENTLY idx_telephony_metrics_composite 
ON telephony_metrics (server_type, metric_name, timestamp DESC);

-- Partition large tables
CREATE TABLE telephony_metrics_y2024 PARTITION OF telephony_metrics
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- Optimize vacuum settings
ALTER TABLE telephony_metrics SET (autovacuum_vacuum_scale_factor = 0.1);
ALTER TABLE telephony_metrics SET (autovacuum_analyze_scale_factor = 0.05);
```

#### Connection Pooling
```python
# database/connection_pool.py
class ConnectionPool:
    def __init__(self):
        self.pool = create_engine(
            DATABASE_URL,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
    def get_connection(self):
        """Get database connection from pool"""
        return self.pool.connect()
        
    def execute_query(self, query, params=None):
        """Execute query with connection from pool"""
        with self.get_connection() as conn:
            return conn.execute(text(query), params or {})
```

### Application Performance

#### Caching Strategy
```python
# performance/caching.py
class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host='redis',
            port=6379,
            decode_responses=True
        )
        
    def cache_metrics(self, server_type, metrics, ttl=60):
        """Cache metrics for quick retrieval"""
        key = f"metrics:{server_type}"
        self.redis_client.setex(key, ttl, json.dumps(metrics))
        
    def get_cached_metrics(self, server_type):
        """Retrieve cached metrics"""
        key = f"metrics:{server_type}"
        cached_data = self.redis_client.get(key)
        
        if cached_data:
            return json.loads(cached_data)
        return None
```

#### Batch Processing
```python
# performance/batch_processor.py
class BatchProcessor:
    def __init__(self, batch_size=1000):
        self.batch_size = batch_size
        self.pending_records = []
        
    def add_record(self, record):
        """Add record to batch"""
        self.pending_records.append(record)
        
        if len(self.pending_records) >= self.batch_size:
            self.flush_batch()
            
    def flush_batch(self):
        """Flush pending records to database"""
        if not self.pending_records:
            return
            
        with Session(engine) as session:
            session.add_all(self.pending_records)
            session.commit()
            
        self.pending_records.clear()
```

### Resource Optimization

#### Memory Management
```python
# performance/memory_manager.py
class MemoryManager:
    def __init__(self):
        self.max_memory_usage = 0.8  # 80% of available memory
        
    def monitor_memory_usage(self):
        """Monitor memory usage and trigger cleanup"""
        current_usage = psutil.virtual_memory().percent / 100
        
        if current_usage > self.max_memory_usage:
            self.trigger_cleanup()
            
    def trigger_cleanup(self):
        """Trigger memory cleanup procedures"""
        # Clear caches
        self.clear_caches()
        
        # Force garbage collection
        gc.collect()
        
        # Close unused database connections
        self.close_idle_connections()
```

#### CPU Optimization
```python
# performance/cpu_optimizer.py
class CPUOptimizer:
    def __init__(self):
        self.max_cpu_usage = 0.7  # 70% CPU usage threshold
        
    def optimize_polling_frequency(self, current_cpu_usage):
        """Dynamically adjust polling frequency based on CPU usage"""
        if current_cpu_usage > self.max_cpu_usage:
            # Reduce polling frequency
            return 20  # Increase interval to 20 seconds
        else:
            return 10  # Normal interval
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Service Startup Problems

**Issue**: PostgreSQL container fails to start
```
Error: database files exist but server is starting up
```

**Solution**:
```bash
# Clean up existing data
docker compose down -v
docker volume rm loading-monitor_postgres_data

# Restart services
docker compose up -d --build
```

**Issue**: Superset initialization fails
```
Error: Database connection failed
```

**Solution**:
```bash
# Check PostgreSQL health
docker compose exec postgres pg_isready -U postgres

# Verify database exists
docker compose exec postgres psql -U postgres -c "\l"

# Restart Superset after PostgreSQL is healthy
docker compose restart superset
```

#### Performance Issues

**Issue**: Slow dashboard loading
**Symptoms**: Dashboards take >30 seconds to load

**Diagnosis**:
```sql
-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Check table sizes
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Solution**:
```bash
# Optimize database
docker compose exec postgres psql -U postgres -d telephony_db -c "VACUUM ANALYZE;"

# Rebuild indexes
docker compose exec postgres psql -U postgres -d telephony_db -c "REINDEX DATABASE telephony_db;"
```

#### Data Collection Issues

**Issue**: Missing metrics from certain servers
**Symptoms**: Some server types show no data in dashboards

**Diagnosis**:
```bash
# Check proxy-gateway logs
docker compose logs proxy-gateway | grep ERROR

# Test mock server endpoints
curl http://localhost:8001/api/stats/uccx
curl http://localhost:8001/api/stats/cucm
```

**Solution**:
```bash
# Restart proxy-gateway
docker compose restart proxy-gateway

# Verify mock server health
curl http://localhost:8001/health
```

### Debugging Tools

#### System Health Check
```bash
#!/bin/bash
# health_check.sh

echo "=== Service Status ==="
docker compose ps

echo "=== Resource Usage ==="
docker stats --no-stream

echo "=== Database Connections ==="
docker compose exec postgres psql -U postgres -c "
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';"

echo "=== Recent Errors ==="
docker compose logs --tail=50 | grep -i error
```

#### API Testing
```bash
#!/bin/bash
# api_test.sh

echo "Testing Mock Server..."
curl -s http://localhost:8001/health | jq .
curl -s http://localhost:8001/api/stats/uccx | jq .

echo "Testing Proxy Gateway..."
curl -s http://localhost:8000/health | jq .

echo "Testing Database..."
docker compose exec postgres psql -U postgres -d telephony_db -c "
SELECT server_type, metric_name, COUNT(*) as record_count 
FROM telephony_metrics 
GROUP BY server_type, metric_name 
ORDER BY record_count DESC;"
```

#### Log Analysis
```bash
#!/bin/bash
# log_analysis.sh

echo "=== Recent Metrics Collection ==="
docker compose logs proxy-gateway | grep "Collected data" | tail -10

echo "=== Database Operations ==="
docker compose logs proxy-gateway | grep "Database" | tail -10

echo "=== Error Summary ==="
docker compose logs --since=1h | grep -i error | sort | uniq -c
```

---

## Scaling Strategies

### Horizontal Scaling

#### Database Scaling
```yaml
# docker-compose.scale.yml
services:
  postgres:
    image: postgres:15-alpine
    deploy:
      replicas: 1  # Single primary
      resources:
        limits:
          memory: 8G
          cpus: '4.0'
  
  postgres-replica:
    image: postgres:15-alpine
    deploy:
      replicas: 2  # Read replicas
    environment:
      POSTGRES_REPLICATION_MODE: replica
      POSTGRES_MASTER_SERVICE: postgres
```

#### Application Scaling
```yaml
services:
  proxy-gateway:
    build: ./proxy-gateway
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    environment:
      - INSTANCE_ID=${HOSTNAME}
```

#### Load Balancing
```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "8000:8000"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - proxy-gateway
```

### Vertical Scaling

#### Resource Allocation
```yaml
services:
  postgres:
    deploy:
      resources:
        limits:
          memory: 16G
          cpus: '8.0'
        reservations:
          memory: 8G
          cpus: '4.0'
  
  superset:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 2G
          cpus: '1.0'
```

#### Performance Tuning
```sql
-- PostgreSQL configuration optimization
-- postgresql.conf
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 256MB
maintenance_work_mem = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 64MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

### Auto-scaling

#### CPU-based Auto-scaling
```yaml
# docker-compose.autoscale.yml
services:
  proxy-gateway:
    build: ./proxy-gateway
    deploy:
      replicas: 2
      update_config:
        parallelism: 2
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      placement:
        max_replicas_per_node: 2
      resources:
        limits:
          cpus: '0.50'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

#### Monitoring-based Scaling
```python
# scaling/auto_scaler.py
class AutoScaler:
    def __init__(self):
        self.min_replicas = 2
        self.max_replicas = 10
        self.scale_up_threshold = 0.8
        self.scale_down_threshold = 0.3
        
    def check_scaling_conditions(self):
        """Check if scaling is needed"""
        current_metrics = self.get_current_metrics()
        current_replicas = self.get_current_replicas()
        
        if self.should_scale_up(current_metrics, current_replicas):
            self.scale_up()
        elif self.should_scale_down(current_metrics, current_replicas):
            self.scale_down()
```

---

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily Tasks
```bash
#!/bin/bash
# daily_maintenance.sh

echo "=== Daily Health Check ==="
./health_check.sh

echo "=== Log Rotation ==="
docker compose exec superset find /var/log/superset -name "*.log" -mtime +7 -delete
docker compose exec postgres psql -U postgres -c "SELECT pg_rotate_logfile();"

echo "=== Cache Cleanup ==="
docker compose exec proxy-gateway python -c "
from performance.cache_manager import CacheManager
cache = CacheManager()
cache.clear_expired_cache()
"
```

#### Weekly Tasks
```bash
#!/bin/bash
# weekly_maintenance.sh

echo "=== Database Optimization ==="
docker compose exec postgres psql -U postgres -d telephony_db -c "
VACUUM ANALYZE;
REINDEX DATABASE telephony_db;
"

echo "=== Performance Report ==="
docker compose exec postgres psql -U postgres -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_stat_get_last_vacuum_time(c.oid) as last_vacuum
FROM pg_class c
LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

#### Monthly Tasks
```bash
#!/bin/bash
# monthly_maintenance.sh

echo "=== Data Archiving ==="
docker compose exec postgres psql -U postgres -d telephony_db -c "
-- Archive old data
CREATE TABLE telephony_metrics_archive_y2024m01 AS 
SELECT * FROM telephony_metrics 
WHERE timestamp >= '2024-01-01' AND timestamp < '2024-02-01';

DELETE FROM telephony_metrics 
WHERE timestamp >= '2024-01-01' AND timestamp < '2024-02-01';
"

echo "=== Security Audit ==="
./security_audit.sh

echo "=== Backup Verification ==="
./verify_backups.sh
```

### Backup Procedures

#### Database Backup
```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/backups/telephony_db"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/telephony_db_$DATE.sql"

mkdir -p $BACKUP_DIR

# Create backup
docker compose exec postgres pg_dump -U postgres telephony_db > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Remove old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

#### Configuration Backup
```bash
#!/bin/bash
# backup_config.sh

CONFIG_BACKUP_DIR="/backups/config"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $CONFIG_BACKUP_DIR

# Backup configuration files
tar -czf $CONFIG_BACKUP_DIR/config_$DATE.tar.gz \
    docker-compose.yml \
    .env \
    superset/superset_config.py \
    proxy-gateway/config.py \
    mock-server/config.py

# Remove old config backups
find $CONFIG_BACKUP_DIR -name "*.tar.gz" -mtime +90 -delete
```

### Update Procedures

#### Application Updates
```bash
#!/bin/bash
# update_application.sh

echo "=== Current Version ==="
docker compose images

echo "=== Pull Latest Images ==="
docker compose pull

echo "=== Backup Current Configuration ==="
./backup_config.sh

echo "=== Update Services ==="
docker compose up -d --force-recreate

echo "=== Verify Update ==="
./health_check.sh

echo "=== New Version ==="
docker compose images
```

#### Database Updates
```bash
#!/bin/bash
# update_database.sh

echo "=== Create Database Backup ==="
./backup_database.sh

echo "=== Apply Database Migrations ==="
docker compose exec proxy-gateway python -c "
from database.migrations import run_migrations
run_migrations()
"

echo "=== Verify Database Schema ==="
docker compose exec postgres psql -U postgres -d telephony_db -c "\d"
```

---

## Integration with External Systems

### Monitoring System Integration

#### Prometheus Integration
```python
# monitoring/prometheus_exporter.py
from prometheus_client import start_http_server, Gauge, Counter

class PrometheusExporter:
    def __init__(self):
        self.metrics_collected = Counter('metrics_collected_total', 'Total metrics collected')
        self.active_calls = Gauge('active_calls', 'Active calls by server', ['server_type'])
        self.cpu_usage = Gauge('cpu_usage_percent', 'CPU usage by server', ['server_type'])
        self.memory_usage = Gauge('memory_usage_percent', 'Memory usage by server', ['server_type'])
        
    def update_metrics(self, server_type, metrics):
        """Update Prometheus metrics"""
        self.metrics_collected.inc()
        
        if 'active_calls' in metrics:
            self.active_calls.labels(server_type=server_type).set(metrics['active_calls'])
        if 'cpu_usage' in metrics:
            self.cpu_usage.labels(server_type=server_type).set(metrics['cpu_usage'])
        if 'memory_usage' in metrics:
            self.memory_usage.labels(server_type=server_type).set(metrics['memory_usage'])
```

#### Grafana Dashboard Integration
```json
{
  "dashboard": {
    "title": "Cisco Telephony Monitoring",
    "panels": [
      {
        "title": "Active Calls by Server Type",
        "type": "stat",
        "targets": [
          {
            "expr": "sum by (server_type) (active_calls)",
            "legendFormat": "{{server_type}}"
          }
        ]
      },
      {
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "cpu_usage_percent",
            "legendFormat": "{{server_type}}"
          }
        ]
      }
    ]
  }
}
```

### SIEM Integration

#### Log Forwarding
```python
# integration/siem_integration.py
class SIEMIntegration:
    def __init__(self, siem_config):
        self.siem_endpoint = siem_config['endpoint']
        self.api_key = siem_config['api_key']
        
    def forward_security_events(self, events):
        """Forward security events to SIEM"""
        for event in events:
            siem_event = {
                'timestamp': event['timestamp'],
                'source': 'cisco-telephony-monitor',
                'event_type': event['type'],
                'severity': event['severity'],
                'details': event['details']
            }
            
            self.send_to_siem(siem_event)
            
    def send_to_siem(self, event):
        """Send event to SIEM system"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            self.siem_endpoint,
            json=event,
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to send event to SIEM: {response.text}")
```

### ITSM Integration

#### ServiceNow Integration
```python
# integration/servicenow_integration.py
class ServiceNowIntegration:
    def __init__(self, servicenow_config):
        self.instance_url = servicenow_config['instance_url']
        self.username = servicenow_config['username']
        self.password = servicenow_config['password']
        
    def create_incident(self, alert):
        """Create incident in ServiceNow"""
        incident_data = {
            'short_description': f"Cisco Telephony Alert: {alert['server_type']}",
            'description': self.format_incident_description(alert),
            'priority': self.map_severity_to_priority(alert['severity']),
            'assignment_group': 'Network Operations',
            'category': 'Telephony',
            'subcategory': 'Monitoring'
        }
        
        response = self.create_servicenow_record('incident', incident_data)
        return response
        
    def create_servicenow_record(self, table, data):
        """Create record in ServiceNow table"""
        url = f"{self.instance_url}/api/now/table/{table}"
        auth = (self.username, self.password)
        headers = {'Content-Type': 'application/json'}
        
        response = requests.post(url, json=data, auth=auth, headers=headers)
        return response.json()
```

---

## Backup and Recovery

### Backup Strategy

#### Full Database Backup
```bash
#!/bin/bash
# backup_full.sh

BACKUP_CONFIG="/etc/backup/config"
source $BACKUP_CONFIG

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_BASE_DIR/full/$DATE"
mkdir -p $BACKUP_DIR

echo "Starting full backup: $DATE"

# Database backup
docker compose exec postgres pg_dump -U postgres -Fc telephony_db > $BACKUP_DIR/telephony_db.dump

# Configuration backup
tar -czf $BACKUP_DIR/config.tar.gz \
    docker-compose.yml \
    .env \
    superset/ \
    proxy-gateway/ \
    mock-server/

# Backup metadata
echo "Backup Date: $DATE" > $BACKUP_DIR/metadata.txt
echo "Backup Type: Full" >> $BACKUP_DIR/metadata.txt
echo "Database Size: $(du -h $BACKUP_DIR/telephony_db.dump | cut -f1)" >> $BACKUP_DIR/metadata.txt

# Verify backup
if [ -f $BACKUP_DIR/telephony_db.dump ] && [ -f $BACKUP_DIR/config.tar.gz ]; then
    echo "Full backup completed successfully"
    # Upload to cloud storage if configured
    if [ -n "$CLOUD_STORAGE_BUCKET" ]; then
        aws s3 sync $BACKUP_DIR s3://$CLOUD_STORAGE_BUCKET/backups/full/$DATE
    fi
else
    echo "Full backup failed"
    exit 1
fi
```

#### Incremental Backup
```bash
#!/bin/bash
# backup_incremental.sh

BACKUP_CONFIG="/etc/backup/config"
source $BACKUP_CONFIG

DATE=$(date +%Y%m%d_%H%M%S)
LAST_FULL_BACKUP=$(find $BACKUP_BASE_DIR/full -type d -name "*_*" | sort | tail -1)
BACKUP_DIR="$BACKUP_BASE_DIR/incremental/$DATE"
mkdir -p $BACKUP_DIR

echo "Starting incremental backup: $DATE"
echo "Based on full backup: $LAST_FULL_BACKUP"

# Export changes since last backup
docker compose exec postgres pg_dump -U postgres --incremental telephony_db > $BACKUP_DIR/incremental.dump

# Backup recent log files
find /var/log -name "*.log" -mtime -1 -exec cp {} $BACKUP_DIR/ \;

# Create incremental metadata
echo "Backup Date: $DATE" > $BACKUP_DIR/metadata.txt
echo "Backup Type: Incremental" >> $BACKUP_DIR/metadata.txt
echo "Based On: $LAST_FULL_BACKUP" >> $BACKUP_DIR/metadata.txt
```

### Recovery Procedures

#### Full System Recovery
```bash
#!/bin/bash
# recovery_full.sh

BACKUP_DATE=$1
BACKUP_DIR="$BACKUP_BASE_DIR/full/$BACKUP_DATE"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "Starting full recovery from: $BACKUP_DATE"

# Stop current services
docker compose down

# Restore configuration
tar -xzf $BACKUP_DIR/config.tar.gz -C .

# Restore database
docker compose up -d postgres
sleep 30  # Wait for PostgreSQL to start

docker compose exec postgres dropdb -U postgres telephony_db
docker compose exec postgres createdb -U postgres telephony_db
docker compose exec -T postgres pg_restore -U postgres -d telephony_db < $BACKUP_DIR/telephony_db.dump

# Start all services
docker compose up -d

# Verify recovery
./health_check.sh

echo "Full recovery completed"
```

#### Point-in-Time Recovery
```bash
#!/bin/bash
# recovery_point_in_time.sh

BACKUP_DATE=$1
RECOVERY_TIME=$2

BACKUP_DIR="$BACKUP_BASE_DIR/full/$BACKUP_DATE"

echo "Starting point-in-time recovery to: $RECOVERY_TIME"

# Stop services
docker compose down

# Restore base backup
docker compose up -d postgres
sleep 30

docker compose exec postgres dropdb -U postgres telephony_db
docker compose exec postgres createdb -U postgres telephony_db
docker compose exec -T postgres pg_restore -U postgres -d telephony_db < $BACKUP_DIR/telephony_db.dump

# Apply WAL logs to reach target time
docker compose exec postgres psql -U postgres -d telephony_db -c "
SELECT pg_wal_replay_resume('$RECOVERY_TIME');
"

# Start services
docker compose up -d

echo "Point-in-time recovery completed"
```

### Disaster Recovery

#### Site Failover
```bash
#!/bin/bash
# disaster_recovery_failover.sh

DR_SITE_CONFIG="/etc/dr/config"
source $DR_SITE_CONFIG

echo "Initiating disaster recovery failover"

# Stop primary site
docker compose down

# Switch DNS to DR site
aws route53 change-resource-record-sets \
    --hosted-zone-id $HOSTED_ZONE_ID \
    --change-batch file://dns_failover.json

# Start DR site services
ssh $DR_SITE_USER@$DR_SITE_HOST "cd $DR_SITE_PATH && docker compose up -d"

# Verify DR site is operational
curl -f $DR_SITE_URL/health || {
    echo "DR site failed to start properly"
    exit 1
}

echo "Disaster recovery failover completed"
```

#### Data Replication
```python
# replication/data_replicator.py
class DataReplicator:
    def __init__(self, primary_config, replica_config):
        self.primary_db = create_engine(primary_config['database_url'])
        self.replica_db = create_engine(replica_config['database_url'])
        
    def replicate_data(self):
        """Replicate data from primary to replica"""
        # Get latest replication timestamp
        last_replication = self.get_last_replication_timestamp()
        
        # Fetch new data from primary
        new_data = self.fetch_new_data(last_replication)
        
        # Apply data to replica
        self.apply_data_to_replica(new_data)
        
        # Update replication timestamp
        self.update_replication_timestamp()
        
    def fetch_new_data(self, since_timestamp):
        """Fetch new data from primary database"""
        query = """
        SELECT * FROM telephony_metrics 
        WHERE timestamp > %s 
        ORDER BY timestamp
        """
        
        with self.primary_db.connect() as conn:
            result = conn.execute(text(query), (since_timestamp,))
            return result.fetchall()
```

---

## Compliance and Auditing

### Regulatory Compliance

#### GDPR Compliance
```python
# compliance/gdpr_compliance.py
class GDPRCompliance:
    def __init__(self):
        self.data_retention_days = 2555  # 7 years
        
    def anonymize_personal_data(self):
        """Anonymize personal data after retention period"""
        cutoff_date = datetime.now() - timedelta(days=self.data_retention_days)
        
        query = """
        UPDATE cdr_records 
        SET 
            calling_party_number = 'ANONYMIZED',
            called_party_number = 'ANONYMIZED',
            orig_device_name = 'ANONYMIZED',
            dest_device_name = 'ANONYMIZED'
        WHERE start_time < %s
        """
        
        with Session(engine) as session:
            session.execute(text(query), (cutoff_date,))
            session.commit()
            
    def export_user_data(self, user_identifier):
        """Export all data related to a specific user"""
        query = """
        SELECT * FROM cdr_records 
        WHERE calling_party_number = %1$s 
           OR called_party_number = %1$s
        ORDER BY start_time DESC
        """
        
        with Session(engine) as session:
            result = session.execute(text(query), (user_identifier,))
            return result.fetchall()
```

#### SOX Compliance
```python
# compliance/sox_compliance.py
class SOXCompliance:
    def __init__(self):
        self.audit_trail_retention_days = 2555  # 7 years
        
    def generate_compliance_report(self, start_date, end_date):
        """Generate SOX compliance report"""
        report_data = {
            'period': f"{start_date} to {end_date}",
            'system_availability': self.calculate_availability(start_date, end_date),
            'data_integrity_checks': self.run_integrity_checks(),
            'access_logs': self.get_access_logs(start_date, end_date),
            'change_management': self.get_change_records(start_date, end_date)
        }
        
        return self.format_compliance_report(report_data)
        
    def calculate_availability(self, start_date, end_date):
        """Calculate system availability percentage"""
        total_minutes = (end_date - start_date).total_seconds() / 60
        
        query = """
        SELECT COUNT(*) as available_minutes
        FROM system_health_log 
        WHERE timestamp BETWEEN %s AND %s 
        AND status = 'healthy'
        """
        
        with Session(engine) as session:
            result = session.execute(text(query), (start_date, end_date))
            available_minutes = result.scalar()
            
        availability_percentage = (available_minutes / total_minutes) * 100
        return round(availability_percentage, 2)
```

### Audit Trail

#### Comprehensive Auditing
```sql
-- Enhanced audit logging
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (
        user_id,
        action,
        table_name,
        record_id,
        old_values,
        new_values,
        timestamp,
        ip_address,
        user_agent,
        session_id
    ) VALUES (
        current_setting('app.current_user_id', true),
        TG_OP,
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD) ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW) ELSE NULL END,
        NOW(),
        inet_client_addr(),
        current_setting('app.user_agent', true),
        current_setting('app.session_id', true)
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Apply audit triggers
CREATE TRIGGER audit_telephony_metrics
    AFTER INSERT OR UPDATE OR DELETE ON telephony_metrics
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();
```

#### Access Control Auditing
```python
# auditing/access_audit.py
class AccessAuditor:
    def __init__(self):
        self.audit_logger = logging.getLogger('access_audit')
        
    def log_access_attempt(self, user_id, resource, action, success, ip_address):
        """Log access attempt for auditing"""
        audit_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'resource': resource,
            'action': action,
            'success': success,
            'ip_address': ip_address,
            'user_agent': self.get_user_agent()
        }
        
        self.audit_logger.info(json.dumps(audit_record))
        
        # Store in database for long-term retention
        self.store_audit_record(audit_record)
        
    def generate_access_report(self, start_date, end_date):
        """Generate access report for compliance"""
        query = """
        SELECT 
            user_id,
            resource,
            action,
            COUNT(*) as attempt_count,
            SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count,
            MIN(timestamp) as first_attempt,
            MAX(timestamp) as last_attempt
        FROM access_audit_log 
        WHERE timestamp BETWEEN %s AND %s
        GROUP BY user_id, resource, action
        ORDER BY attempt_count DESC
        """
        
        with Session(engine) as session:
            result = session.execute(text(query), (start_date, end_date))
            return result.fetchall()
```

### Security Auditing

#### Vulnerability Scanning
```bash
#!/bin/bash
# security/vulnerability_scan.sh

echo "Starting vulnerability scan..."

# Scan Docker images
docker compose images --format "table {{.Repository}}:{{.Tag}}" | grep -v REPOSITORY | while read image; do
    echo "Scanning image: $image"
    trivy image --severity HIGH,CRITICAL $image
done

# Scan running containers
docker compose ps --format "table {{.Names}}" | grep -v NAMES | while read container; do
    echo "Scanning container: $container"
    trivy container --severity HIGH,CRITICAL $container
done

# Generate security report
echo "Vulnerability scan completed: $(date)" >> /var/log/security_scan.log
```

#### Penetration Testing
```python
# security/penetration_test.py
class PenetrationTest:
    def __init__(self):
        self.test_endpoints = [
            'http://localhost:8000/health',
            'http://localhost:8001/health',
            'http://localhost:8088/health'
        ]
        
    def run_security_tests(self):
        """Run comprehensive security tests"""
        test_results = {}
        
        for endpoint in self.test_endpoints:
            test_results[endpoint] = {
                'sql_injection': self.test_sql_injection(endpoint),
                'xss': self.test_xss(endpoint),
                'authentication_bypass': self.test_auth_bypass(endpoint),
                'rate_limiting': self.test_rate_limiting(endpoint)
            }
            
        return self.generate_security_report(test_results)
        
    def test_sql_injection(self, endpoint):
        """Test for SQL injection vulnerabilities"""
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --"
        ]
        
        for payload in payloads:
            response = requests.get(f"{endpoint}?id={payload}")
            if response.status_code == 200:
                # Check for SQL error messages
                if any(error in response.text.lower() for error in ['sql', 'syntax', 'mysql', 'postgresql']):
                    return {'vulnerable': True, 'payload': payload}
                    
        return {'vulnerable': False}
```

---

## Future Enhancements

### Machine Learning Integration

#### Predictive Analytics
```python
# ml/predictive_analytics.py
class PredictiveAnalytics:
    def __init__(self):
        self.models = {
            'call_volume': self.load_call_volume_model(),
            'system_failure': self.load_failure_prediction_model()
        }
        
    def predict_call_volume(self, historical_data, forecast_hours=24):
        """Predict call volume for next N hours"""
        features = self.extract_time_series_features(historical_data)
        predictions = []
        
        for hour in range(forecast_hours):
            prediction = self.models['call_volume'].predict(features)
            predictions.append({
                'timestamp': datetime.now() + timedelta(hours=hour),
                'predicted_calls': prediction,
                'confidence_interval': self.calculate_confidence_interval(prediction)
            })
            
        return predictions
        
    def predict_system_failure(self, current_metrics):
        """Predict likelihood of system failure"""
        features = self.extract_failure_features(current_metrics)
        failure_probability = self.models['system_failure'].predict_proba(features)[0][1]
        
        return {
            'failure_probability': failure_probability,
            'risk_level': self.categorize_risk(failure_probability),
            'recommended_actions': self.get_mitigation_actions(failure_probability)
        }
```

#### Anomaly Detection
```python
# ml/anomaly_detection.py
class AdvancedAnomalyDetector:
    def __init__(self):
        self.isolation_forest = IsolationForest(contamination=0.1)
        self.lstm_autoencoder = self.load_lstm_model()
        
    def detect_anomalies(self, metrics_data):
        """Detect anomalies using multiple methods"""
        anomalies = []
        
        # Statistical anomalies
        statistical_anomalies = self.detect_statistical_anomalies(metrics_data)
        
        # Machine learning anomalies
        ml_anomalies = self.detect_ml_anomalies(metrics_data)
        
        # Time series anomalies
        ts_anomalies = self.detect_timeseries_anomalies(metrics_data)
        
        # Combine and rank anomalies
        combined_anomalies = self.combine_anomalies([
            statistical_anomalies,
            ml_anomalies,
            ts_anomalies
        ])
        
        return combined_anomalies
```

### Advanced Visualization

#### 3D Dashboard
```javascript
// frontend/3d_dashboard.js
class Telephony3DDashboard {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer();
        
        this.init();
    }
    
    init() {
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.container.appendChild(this.renderer.domElement);
        
        // Create 3D visualization of telephony components
        this.createServerVisualization();
        this.createConnectionLines();
        this.createDataFlowAnimation();
        
        this.animate();
    }
    
    createServerVisualization() {
        const serverGeometry = new THREE.BoxGeometry(1, 1, 1);
        const serverMaterials = {
            'uccx': new THREE.MeshBasicMaterial({color: 0x00ff00}),
            'cucm': new THREE.MeshBasicMaterial({color: 0x0000ff}),
            'imp': new THREE.MeshBasicMaterial({color: 0xff0000})
        };
        
        // Create server cubes with real-time metrics
        Object.keys(serverMaterials).forEach(serverType => {
            const serverMesh = new THREE.Mesh(serverGeometry, serverMaterials[serverType]);
            serverMesh.position.set(
                Math.random() * 10 - 5,
                Math.random() * 10 - 5,
                Math.random() * 10 - 5
            );
            this.scene.add(serverMesh);
        });
    }
}
```

#### Real-time Streaming
```python
# streaming/real_time_stream.py
class RealTimeStream:
    def __init__(self):
        self.websocket_clients = set()
        self.redis_client = redis.Redis()
        
    async def handle_websocket(self, websocket, path):
        """Handle WebSocket connections for real-time updates"""
        self.websocket_clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            self.websocket_clients.remove(websocket)
            
    async def broadcast_metrics(self, metrics):
        """Broadcast metrics to all connected clients"""
        message = json.dumps({
            'type': 'metrics_update',
            'data': metrics,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Send to WebSocket clients
        if self.websocket_clients:
            await asyncio.gather(
                *[client.send(message) for client in self.websocket_clients],
                return_exceptions=True
            )
            
        # Publish to Redis for other services
        self.redis_client.publish('telephony_metrics', message)
```

### Cloud Integration

#### Multi-Cloud Deployment
```yaml
# cloud/multi_cloud.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: telephony-monitor
spec:
  replicas: 3
  selector:
    matchLabels:
      app: telephony-monitor
  template:
    metadata:
      labels:
        app: telephony-monitor
    spec:
      containers:
      - name: proxy-gateway
        image: telephony-monitor/proxy-gateway:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
```

#### Serverless Architecture
```python
# serverless/functions.py
import azure.functions as func

class ServerlessTelephonyMonitor:
    def __init__(self):
        self.cosmos_client = cosmos_client.CosmosClient(
            endpoint=os.environ.get('COSMOS_ENDPOINT'),
            credential=os.environ.get('COSMOS_KEY')
        )
        
    @app.function_name(name="ProcessMetrics")
    @app.route(route="metrics", auth_level=func.AuthLevel.FUNCTION)
    async def process_metrics(req: func.HttpRequest) -> func.HttpResponse:
        """Process incoming metrics in serverless environment"""
        try:
            metrics_data = req.get_json()
            
            # Process and store metrics
            processed_metrics = process_telephony_data(metrics_data)
            
            # Store in Cosmos DB
            container = self.cosmos_client.get_database_client(
                'telephony_db'
            ).get_container_client('metrics')
            
            container.upsert_item(processed_metrics)
            
            return func.HttpResponse("Metrics processed successfully", status_code=200)
            
        except Exception as e:
            return func.HttpResponse(f"Error: {str(e)}", status_code=500)
```

### API Gateway Integration

#### GraphQL API
```python
# api/graphql_schema.py
import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType

class TelephonyMetricType(SQLAlchemyObjectType):
    class Meta:
        model = TelephonyMetric
        interfaces = (graphene.relay.Node,)

class Query(graphene.ObjectType):
    metrics = graphene.List(TelephonyMetricType, 
                           server_type=graphene.String(),
                           metric_name=graphene.String(),
                           start_time=graphene.DateTime(),
                           end_time=graphene.DateTime())
    
    def resolve_metrics(self, info, **kwargs):
        query = TelephonyMetric.get_query(info)
        
        if 'server_type' in kwargs:
            query = query.filter(TelephonyMetric.server_type == kwargs['server_type'])
        if 'metric_name' in kwargs:
            query = query.filter(TelephonyMetric.metric_name == kwargs['metric_name'])
        if 'start_time' in kwargs:
            query = query.filter(TelephonyMetric.timestamp >= kwargs['start_time'])
        if 'end_time' in kwargs:
            query = query.filter(TelephonyMetric.timestamp <= kwargs['end_time'])
            
        return query.all()

schema = graphene.Schema(query=Query)
```

---

## Conclusion

This comprehensive Cisco Telephony Monitoring System provides a robust, scalable, and production-ready solution for monitoring enterprise telephony infrastructure. The microservices architecture ensures high availability, while the modular design allows for easy customization and extension.

### Key Benefits Achieved

1. **Unified Monitoring**: Single platform for all Cisco telephony components
2. **Real-time Insights**: Sub-minute data collection and visualization
3. **Scalable Architecture**: Horizontal scaling support for enterprise deployments
4. **Production Ready**: Enterprise-grade security, monitoring, and maintenance procedures
5. **Future Proof**: Extensible design supporting emerging technologies and requirements

### Implementation Success Factors

- **Clean Architecture**: Separation of concerns with clear service boundaries
- **Modern Technologies**: SQLModel, AsyncIO, FastAPI for optimal performance
- **Comprehensive Documentation**: Detailed implementation guides and procedures
- **Security First**: Built-in security measures and compliance features
- **Operational Excellence**: Monitoring, alerting, and maintenance automation

### Next Steps

1. **Production Deployment**: Follow the deployment guide for production setup
2. **Customization**: Adapt the system to specific organizational requirements
3. **Integration**: Connect with existing monitoring and ITSM systems
4. **Optimization**: Fine-tune performance based on actual usage patterns
5. **Enhancement**: Implement advanced features as requirements evolve

This system provides a solid foundation for enterprise telephony monitoring that can grow and evolve with organizational needs while maintaining high standards of reliability, security, and performance.
