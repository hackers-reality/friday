"""
Friday Security - Security tools and utilities.
Penetration testing helpers, vulnerability scanning, security auditing.
"""
from __future__ import annotations

import os
import sys
import json
import socket
import subprocess
import hashlib
import base64
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import re
import ssl
import requests
from urllib.parse import urlparse


# ─── Port Scanning ────────────────────────────#

class PortScanner:
    """Advanced port scanning."""
    
    def __init__(self):
        self.common_ports = {
            21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
            53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP",
            443: "HTTPS", 445: "SMB", 3306: "MySQL", 3389: "RDP",
            5432: "PostgreSQL", 8080: "HTTP-Alt", 8443: "HTTPS-Alt",
        }
        
    def scan_port(self, host: str, port: int, timeout: float = 1.0) -> Dict[str, Any]:
        """Scan a single port."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                service = self.common_ports.get(port, "Unknown")
                return {
                    "open": True,
                    "port": port,
                    "service": service,
                }
            else:
                return {"open": False, "port": port}
        except Exception as e:
            return {"open": False, "port": port, "error": str(e)}
    
    def scan_ports(
        self,
        host: str,
        ports: List[int] = None,
        timeout: float = 1.0,
    ) -> Dict[str, Any]:
        """Scan multiple ports."""
        ports = ports or list(self.common_ports.keys())
        open_ports = []
        
        for port in ports:
            result = self.scan_port(host, port, timeout)
            if result["open"]:
                open_ports.append(result)
        
        return {
            "host": host,
            "scanned_ports": len(ports),
            "open_ports": open_ports,
            "open_count": len(open_ports),
        }
    
    def scan_range(
        self,
        host: str,
        start_port: int,
        end_port: int,
        timeout: float = 0.5,
    ) -> Dict[str, Any]:
        """Scan a range of ports."""
        open_ports = []
        
        for port in range(start_port, end_port + 1):
            result = self.scan_port(host, port, timeout)
            if result["open"]:
                open_ports.append(result)
        
        return {
            "host": host,
            "range": f"{start_port}-{end_port}",
            "open_ports": open_ports,
            "open_count": len(open_ports),
        }


# ─── SSL/TLS Analysis ────────────────────────────#

class SSLAnalyzer:
    """SSL/TLS certificate and security analysis."""
    
    def check_ssl(self, hostname: str, port: int = 443) -> Dict[str, Any]:
        """Check SSL certificate."""
        try:
            context = ssl.create_default_context()
            
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    return {
                        "success": True,
                        "subject": dict(x[0] for x in cert.get("subject", [])),
                        "issuer": dict(x[0] for x in cert.get("issuer", [])),
                        "version": cert.get("version"),
                        "not_before": cert.get("notBefore"),
                        "not_after": cert.get("notAfter"),
                        "serial_number": cert.get("serialNumber"),
                        "protocol": ssock.version(),
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_https(self, url: str) -> Dict[str, Any]:
        """Check HTTPS security."""
        try:
            response = requests.get(url, timeout=5, allow_redirects=True)
            
            return {
                "success": True,
                "status_code": response.status_code,
                "https": url.startswith("https://"),
                "headers": {
                    "strict_transport_security": response.headers.get("strict-transport-security"),
                    "content_security_policy": response.headers.get("content-security-policy"),
                    "x_frame_options": response.headers.get("x-frame-options"),
                    "x_content_type_options": response.headers.get("x-content-type-options"),
                },
                "final_url": response.url,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Hash Analysis ────────────────────────────#

class HashAnalyzer:
    """File hash analysis and integrity checking."""
    
    @staticmethod
    def calculate_file_hash(file_path: str, algorithm: str = "sha256") -> Dict[str, Any]:
        """Calculate file hash."""
        try:
            hash_func = getattr(hashlib, algorithm, None)
            if not hash_func:
                return {"success": False, "error": f"Unknown algorithm: {algorithm}"}
            
            h = hash_func()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    h.update(chunk)
            
            return {
                "success": True,
                "hash": h.hexdigest(),
                "algorithm": algorithm,
                "file": file_path,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def check_integrity(file_path: str, expected_hash: str, algorithm: str = "sha256") -> Dict[str, Any]:
        """Check file integrity."""
        result = HashAnalyzer.calculate_file_hash(file_path, algorithm)
        
        if not result["success"]:
            return result
        
        is_valid = result["hash"] == expected_hash
        
        return {
            "success": True,
            "valid": is_valid,
            "actual_hash": result["hash"],
            "expected_hash": expected_hash,
        }
    
    @staticmethod
    def hash_string(text: str, algorithm: str = "sha256") -> str:
        """Hash a string."""
        hash_func = getattr(hashlib, algorithm, hashlib.sha256)
        return hash_func(text.encode()).hexdigest()


# ─── Password Security ────────────────────────────#

class PasswordAnalyzer:
    """Password strength analysis."""
    
    @staticmethod
    def check_strength(password: str) -> Dict[str, Any]:
        """Check password strength."""
        score = 0
        feedback = []
        
        # Length
        if len(password) >= 8:
            score += 1
        else:
            feedback.append("Password should be at least 8 characters.")
        
        if len(password) >= 12:
            score += 1
        
        # Character types
        if re.search(r"[a-z]", password):
            score += 1
        else:
            feedback.append("Add lowercase letters.")
        
        if re.search(r"[A-Z]", password):
            score += 1
        else:
            feedback.append("Add uppercase letters.")
        
        if re.search(r"\d", password):
            score += 1
        else:
            feedback.append("Add numbers.")
        
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 1
        else:
            feedback.append("Add special characters.")
        
        # Determine strength
        if score <= 2:
            strength = "Very Weak"
        elif score <= 3:
            strength = "Weak"
        elif score <= 4:
            strength = "Fair"
        elif score <= 5:
            strength = "Strong"
        else:
            strength = "Very Strong"
        
        return {
            "score": score,
            "strength": strength,
            "length": len(password),
            "feedback": feedback,
        }
    
    @staticmethod
    def generate_password(length: int = 16) -> str:
        """Generate a strong password."""
        import secrets
        import string
        
        chars = string.ascii_letters + string.digits + string.punctuation
        return "".join(secrets.choice(chars) for _ in range(length))


# ─── Header Security Analysis ────────────────────────────#

class SecurityHeaders:
    """Analyze security headers."""
    
    REQUIRED_HEADERS = [
        "strict-transport-security",
        "content-security-policy",
        "x-frame-options",
        "x-content-type-options",
        "referrer-policy",
    ]
    
    def analyze(self, url: str) -> Dict[str, Any]:
        """Analyze security headers of a URL."""
        try:
            response = requests.get(url, timeout=5)
            headers = {k.lower(): v for k, v in response.headers.items()}
            
            present = []
            missing = []
            
            for header in self.REQUIRED_HEADERS:
                if header in headers:
                    present.append(header)
                else:
                    missing.append(header)
            
            return {
                "success": True,
                "url": url,
                "present_headers": present,
                "missing_headers": missing,
                "score": len(present) / len(self.REQUIRED_HEADERS) * 100,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── DNS Security ────────────────────────────#

class DNSSecurity:
    """DNS security checks."""
    
    def check_dnssec(self, domain: str) -> Dict[str, Any]:
        """Check if DNSSEC is enabled (simplified)."""
        try:
            import dns.resolver
            import dns.flags
            
            resolver = dns.resolver.Resolver()
            response = resolver.resolve(domain, "DNSKEY")
            
            return {
                "success": True,
                "dnssec_enabled": len(response.response.answer) > 0,
                "has_dnskey": any(rr.rdtype == dns.rdatatype.DNSKEY for rr in response.response.answer),
            }
        except ImportError:
            return {"success": False, "error": "dnspython not available. Install: pip install dnspython"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_spf(self, domain: str) -> Dict[str, Any]:
        """Check SPF record."""
        try:
            import dns.resolver
            
            try:
                answers = dns.resolver.resolve(domain, "TXT")
                spf_records = []
                
                for rdata in answers:
                    for txt_string in rdata.strings:
                        txt = txt_string.decode()
                        if txt.startswith("v=spf1"):
                            spf_records.append(txt)
                
                return {
                    "success": True,
                    "has_spf": len(spf_records) > 0,
                    "records": spf_records,
                }
            except dns.resolver.NXDOMAIN:
                return {"success": True, "has_spf": False, "records": []}
        except ImportError:
            return {"success": False, "error": "dnspython not available."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_dmarc(self, domain: str) -> Dict[str, Any]:
        """Check DMARC record."""
        try:
            import dns.resolver
            
            dmarc_domain = f"_dmarc.{domain}"
            
            try:
                answers = dns.resolver.resolve(dmarc_domain, "TXT")
                dmarc_records = []
                
                for rdata in answers:
                    for txt_string in rdata.strings:
                        txt = txt_string.decode()
                        if txt.startswith("v=DMARC1"):
                            dmarc_records.append(txt)
                
                return {
                    "success": True,
                    "has_dmarc": len(dmarc_records) > 0,
                    "records": dmarc_records,
                }
            except dns.resolver.NXDOMAIN:
                return {"success": True, "has_dmarc": False, "records": []}
        except ImportError:
            return {"success": False, "error": "dnspython not available."}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Security Tool for Friday ────────────────────────────#

def security_tool(
    action: str = "status",
    target: str = None,
    params: Dict = None,
) -> str:
    """
    Friday tool for security operations.
    Actions: status, port_scan, ssl_check, hash_file, hash_check,
            password_strength, security_headers, dnssec, spf, dmarc
    """
    params = params or {}
    
    if action == "status":
        lines = ["### SECURITY STATUS", ""]
        lines.append("**Available Tools**:")
        lines.append("  - Port scanning (TCP connect)")
        lines.append("  - SSL/TLS certificate analysis")
        lines.append("  - File integrity checking (hash)")
        lines.append("  - Password strength analysis")
        lines.append("  - Security headers analysis")
        lines.append("  - DNS security (DNSSEC, SPF, DMARC)")
        return "\n".join(lines)
    
    if action == "port_scan":
        if not target:
            return "[FAIL] Host required."
        scanner = PortScanner()
        if "ports" in params:
            ports = params["ports"]
            result = scanner.scan_ports(target, ports)
        else:
            result = scanner.scan_ports(target)
        
        lines = [f"### PORT SCAN: {target}", ""]
        lines.append(f"**Open Ports**: {result['open_count']}/{result['scanned_ports']}")
        for port in result["open_ports"]:
            lines.append(f"  - Port {port['port']}: {port['service']} [OK]")
        return "\n".join(lines)
    
    if action == "ssl_check":
        if not target:
            return "[FAIL] Hostname required."
        analyzer = SSLAnalyzer()
        result = analyzer.check_ssl(target)
        if result["success"]:
            return f"""### SSL CHECK: {target}
**Subject**: {result['subject']}
**Issuer**: {result['issuer']}
**Protocol**: {result['protocol']}
**Valid Until**: {result['not_after']}"""
        else:
            return f"[FAIL] SSL check error: {result.get('error', 'Unknown')}"
    
    if action == "hash_file":
        if not target:
            return "[FAIL] File path required."
        algorithm = params.get("algorithm", "sha256")
        result = HashAnalyzer.calculate_file_hash(target, algorithm)
        if result["success"]:
            return f"### FILE HASH\n\n**Algorithm**: {algorithm}\n**Hash**: {result['hash']}"
        else:
            return f"[FAIL] Hash error: {result.get('error', 'Unknown')}"
    
    if action == "hash_check":
        if not target or "expected" not in params:
            return "[FAIL] File path and expected hash required."
        algorithm = params.get("algorithm", "sha256")
        result = HashAnalyzer.check_integrity(target, params["expected"], algorithm)
        if result["success"]:
            return f"### INTEGRITY CHECK\n\n{'[OK] Valid' if result['valid'] else '[FAIL] Invalid'}\nExpected: {result['expected_hash']}\nActual: {result['actual_hash']}"
        else:
            return f"[FAIL] Check error: {result.get('error', 'Unknown')}"
    
    if action == "password_strength":
        if not target:
            return "[FAIL] Password required."
        result = PasswordAnalyzer.check_strength(target)
        return f"""### PASSWORD STRENGTH
**Strength**: {result['strength']}
**Score**: {result['score']}/6
**Length**: {result['length']}
**Feedback**: {', '.join(result['feedback']) if result['feedback'] else 'None'}"""
    
    if action == "security_headers":
        if not target:
            return "[FAIL] URL required."
        analyzer = SecurityHeaders()
        result = analyzer.analyze(target)
        if result["success"]:
            lines = [f"### SECURITY HEADERS: {target}", ""]
            lines.append(f"**Score**: {result['score']:.0f}%")
            lines.append("**Present**: " + ", ".join(result["present_headers"]))
            if result["missing_headers"]:
                lines.append("**Missing**: " + ", ".join(result["missing_headers"]))
            return "\n".join(lines)
        else:
            return f"[FAIL] Headers error: {result.get('error', 'Unknown')}"
    
    if action == "dnssec":
        if not target:
            return "[FAIL] Domain required."
        dnssec = DNSSecurity()
        result = dnssec.check_dnssec(target)
        if result["success"]:
            return f"### DNSSEC CHECK\n\n**Domain**: {target}\n**DNSSEC Enabled**: {'[OK]' if result['dnssec_enabled'] else '[FAIL]'}"
        else:
            return f"[FAIL] DNSSEC error: {result.get('error', 'Unknown')}"
    
    if action == "spf":
        if not target:
            return "[FAIL] Domain required."
        dnssec = DNSSecurity()
        result = dnssec.check_spf(target)
        if result["success"]:
            return f"### SPF CHECK\n\n**Domain**: {target}\n**Has SPF**: {'[OK]' if result['has_spf'] else '[FAIL]'}\n**Records**: {result['records']}"
        else:
            return f"[FAIL] SPF error: {result.get('error', 'Unknown')}"
    
    if action == "dmarc":
        if not target:
            return "[FAIL] Domain required."
        dnssec = DNSSecurity()
        result = dnssec.check_dmarc(target)
        if result["success"]:
            return f"### DMARC CHECK\n\n**Domain**: {target}\n**Has DMARC**: {'[OK]' if result['has_dmarc'] else '[FAIL]'}\n**Records**: {result['records']}"
        else:
            return f"[FAIL] DMARC error: {result.get('error', 'Unknown')}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday Security...\n")
    
    # Test port scan
    print("--- Port Scan ---")
    print(security_tool("port_scan", target="localhost"))
    
    # Test password strength
    print("\n--- Password Strength ---")
    print(security_tool("password_strength", target="Test123!"))
