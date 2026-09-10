"""
AI IT Helpdesk Agent - Diagnostic Tools Module
Safe, read-only system and network diagnostics with input validation and exception handling.
Strictly prohibits destructive operations and arbitrary shell execution.
"""

import os
import re
import sys
import time
import socket
import shutil
import platform
import subprocess
from typing import Dict, Any, Optional

# Regex pattern allowing only valid hostnames or IPv4 addresses (no spaces, shell metacharacters)
SAFE_HOST_REGEX = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*$")
IPV4_REGEX = re.compile(r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$")


def is_safe_host(host: str) -> bool:
    """Validates that a hostname or IP is strictly alphanumeric and safe for pinging."""
    if not host or len(host) > 100:
        return False
    host = host.strip()
    return bool(SAFE_HOST_REGEX.match(host) or IPV4_REGEX.match(host))


def check_internet() -> Dict[str, Any]:
    """
    Checks if active internet connectivity is available.
    Probes reliable DNS/HTTP endpoints and measures round-trip latency.
    """
    targets = [
        ("8.8.8.8", 53),     # Google Public DNS
        ("1.1.1.1", 53),     # Cloudflare DNS
        ("208.67.222.222", 53) # OpenDNS
    ]
    
    for host, port in targets:
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.5)
            sock.connect((host, port))
            latency_ms = round((time.time() - start_time) * 1000, 2)
            sock.close()

            # Test DNS resolution
            dns_ok = False
            try:
                socket.gethostbyname("www.google.com")
                dns_ok = True
            except Exception:
                dns_ok = False

            return {
                "status": "Online",
                "connected": True,
                "latency_ms": latency_ms,
                "dns_resolving": dns_ok,
                "tested_endpoint": f"{host}:{port}",
                "message": f"Internet connection is active with {latency_ms}ms latency. DNS resolution is {'healthy' if dns_ok else 'degraded'}."
            }
        except Exception:
            continue

    return {
        "status": "Offline",
        "connected": False,
        "latency_ms": None,
        "dns_resolving": False,
        "tested_endpoint": "None",
        "message": "No active internet connection detected. Unable to reach external DNS gateways."
    }


def get_ip_address() -> Dict[str, Any]:
    """
    Retrieves local network IP address, machine hostname, and public external IP.
    """
    try:
        hostname = socket.gethostname()
    except Exception as e:
        hostname = "Unknown Host"

    # Find primary local IP address
    local_ip = "127.0.0.1"
    try:
        # Connect to an external address without sending packets to get active interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        try:
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            local_ip = "127.0.0.1"

    # Attempt public IP discovery via external service with short timeout
    public_ip = "Not Available (Offline)"
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.ipify.org?format=json",
            headers={"User-Agent": "IT-Helpdesk-Diagnostic/1.0"}
        )
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            import json
            data = json.loads(resp.read().decode())
            public_ip = data.get("ip", "Unknown")
    except Exception:
        public_ip = "Offline / Restricted Gateway"

    return {
        "hostname": hostname,
        "local_ip": local_ip,
        "public_ip": public_ip,
        "is_loopback": local_ip.startswith("127."),
        "message": f"Device '{hostname}' has local IP {local_ip} and public IP {public_ip}."
    }


def ping_server(host: str = "8.8.8.8") -> Dict[str, Any]:
    """
    Safely pings a user-specified host or IP.
    Strictly validates input against injection characters.
    """
    cleaned_host = host.strip()
    if not is_safe_host(cleaned_host):
        return {
            "host": host,
            "success": False,
            "error": "Invalid host input. Only safe domain names (e.g. google.com) or IPv4 addresses are permitted.",
            "latency_ms": None,
            "packet_loss_pct": 100
        }

    # Execute system ping safely via subprocess with argument list (shell=False)
    is_win = platform.system().lower() == "windows"
    cmd = ["ping", "-n", "2", "-w", "1500", cleaned_host] if is_win else ["ping", "-c", "2", "-W", "2", cleaned_host]

    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        output = res.stdout

        # Parse latency and loss
        loss = 100
        latency = None

        # Windows ping output parser
        if "Average =" in output:
            match = re.search(r"Average\s*=\s*(\d+)ms", output)
            if match:
                latency = int(match.group(1))
        elif "time=" in output:
            match = re.search(r"time[=<](\d+\.?\d*)\s*ms", output)
            if match:
                latency = float(match.group(1))

        if "Lost = 0" in output or "0% packet loss" in output or "0% loss" in output:
            loss = 0
        elif "Lost = 1" in output or "50% packet loss" in output or "50% loss" in output:
            loss = 50
        elif "Lost = 2" in output or "100% packet loss" in output or "100% loss" in output:
            loss = 100
        else:
            loss = 0 if res.returncode == 0 else 100

        success = (res.returncode == 0 and loss < 100)
        return {
            "host": cleaned_host,
            "success": success,
            "latency_ms": latency if latency is not None else ("<1" if success else None),
            "packet_loss_pct": loss,
            "details": f"Ping to {cleaned_host}: {'Successful' if success else 'Failed'} with {loss}% packet loss and ~{latency}ms latency."
        }
    except subprocess.TimeoutExpired:
        return {
            "host": cleaned_host,
            "success": False,
            "error": f"Ping request to {cleaned_host} timed out.",
            "latency_ms": None,
            "packet_loss_pct": 100
        }
    except Exception as e:
        return {
            "host": cleaned_host,
            "success": False,
            "error": f"Diagnostic ping failed: {str(e)}",
            "latency_ms": None,
            "packet_loss_pct": 100
        }


def check_disk_space(path: str = "C:\\" if platform.system().lower() == "windows" else "/") -> Dict[str, Any]:
    """
    Inspects storage capacity and returns total, used, and free space in GB.
    """
    try:
        # Fallback to current working drive if path does not exist
        target_path = path if os.path.exists(path) else os.getcwd()
        usage = shutil.disk_usage(target_path)

        total_gb = round(usage.total / (1024 ** 3), 2)
        used_gb = round(usage.used / (1024 ** 3), 2)
        free_gb = round(usage.free / (1024 ** 3), 2)
        pct_used = round((usage.used / usage.total) * 100, 1)

        health_status = "Healthy"
        if pct_used > 90:
            health_status = "Critical (Very Low Space)"
        elif pct_used > 80:
            health_status = "Warning (Low Space)"

        return {
            "path": target_path,
            "total_gb": total_gb,
            "used_gb": used_gb,
            "free_gb": free_gb,
            "percent_used": pct_used,
            "health_status": health_status,
            "message": f"Disk '{target_path}': {free_gb} GB free of {total_gb} GB ({pct_used}% utilized). Health: {health_status}."
        }
    except Exception as e:
        return {
            "error": f"Unable to read disk usage: {str(e)}",
            "total_gb": 0,
            "used_gb": 0,
            "free_gb": 0,
            "percent_used": 0,
            "health_status": "Unknown"
        }


def system_information() -> Dict[str, Any]:
    """
    Retrieves safe system hardware, OS, and runtime platform information.
    """
    try:
        uname = platform.uname()
        boot_time_str = "Available"
        
        return {
            "os": uname.system,
            "os_release": uname.release,
            "os_version": uname.version,
            "architecture": uname.machine,
            "processor": uname.processor or platform.processor() or "x86_64",
            "python_version": platform.python_version(),
            "cpu_cores": os.cpu_count() or 1,
            "message": f"{uname.system} {uname.release} ({uname.machine}) running Python {platform.python_version()} on {os.cpu_count() or 1} CPU cores."
        }
    except Exception as e:
        return {
            "error": f"Failed to retrieve system information: {str(e)}"
        }


def network_information() -> Dict[str, Any]:
    """
    Provides safe summary of network interfaces and connection capabilities.
    """
    try:
        hostname = socket.gethostname()
        ip_info = get_ip_address()
        internet_info = check_internet()

        adapters = []
        try:
            # Safe ipconfig summary on Windows
            if platform.system().lower() == "windows":
                res = subprocess.run(["ipconfig"], stdout=subprocess.PIPE, text=True, timeout=3)
                lines = res.stdout.splitlines()
                current_adapter = None
                for line in lines:
                    line_s = line.strip()
                    if line_s and not line.startswith(" ") and ":" in line:
                        current_adapter = line.split(":")[0].strip()
                    elif current_adapter and "IPv4 Address" in line:
                        parts = line.split(":")
                        if len(parts) > 1:
                            adapters.append({"adapter": current_adapter, "ipv4": parts[1].strip()})
        except Exception:
            pass

        return {
            "hostname": hostname,
            "local_ip": ip_info["local_ip"],
            "internet_status": internet_info["status"],
            "active_latency": internet_info["latency_ms"],
            "adapters": adapters if adapters else [{"adapter": "Default Adapter", "ipv4": ip_info["local_ip"]}],
            "message": f"Network active on {ip_info['local_ip']} ({'Internet Online' if internet_info['connected'] else 'No External Connection'})."
        }
    except Exception as e:
        return {
            "error": f"Failed to query network configuration: {str(e)}"
        }


# =====================================================================
# Tool Execution Registry
# =====================================================================

TOOL_DEFINITIONS = [
    {
        "name": "check_internet",
        "description": "Tests active internet connectivity, socket connectivity, and round-trip ping latency.",
        "parameters": {}
    },
    {
        "name": "get_ip_address",
        "description": "Returns the local private IP address, machine hostname, and public external IP address.",
        "parameters": {}
    },
    {
        "name": "ping_server",
        "description": "Sends safe ICMP ping packets to a target hostname (e.g. google.com) or IP address to measure packet loss and latency.",
        "parameters": {
            "host": {
                "type": "string",
                "description": "Safe domain name or IPv4 address to ping, e.g. '8.8.8.8' or 'google.com'",
                "default": "8.8.8.8"
            }
        }
    },
    {
        "name": "check_disk_space",
        "description": "Inspects storage drive usage, showing total, used, free GB, and usage percentage.",
        "parameters": {
            "path": {
                "type": "string",
                "description": "Drive letter or mount path to inspect",
                "default": "C:\\"
            }
        }
    },
    {
        "name": "system_information",
        "description": "Retrieves operating system details, processor architecture, CPU core count, and Python runtime.",
        "parameters": {}
    },
    {
        "name": "network_information",
        "description": "Fetches network adapter status, local IP assignments, and overall connection state.",
        "parameters": {}
    }
]


def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    Central dispatcher for safe diagnostic tool execution.
    Only allows explicitly registered tools.
    """
    dispatch = {
        "check_internet": lambda: check_internet(),
        "get_ip_address": lambda: get_ip_address(),
        "ping_server": lambda: ping_server(host=kwargs.get("host", "8.8.8.8")),
        "check_disk_space": lambda: check_disk_space(path=kwargs.get("path", "C:\\")),
        "system_information": lambda: system_information(),
        "network_information": lambda: network_information(),
    }

    if tool_name not in dispatch:
        return {
            "error": f"Tool '{tool_name}' is not recognized or permitted. Only safe predefined diagnostic tools may be executed."
        }

    try:
        return dispatch[tool_name]()
    except Exception as e:
        return {
            "error": f"Exception encountered while executing '{tool_name}': {str(e)}"
        }
