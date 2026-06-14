"""Test all new FRIDAY modules."""
import sys
sys.path.insert(0, 'E:/open-interpreter')

from friday.security_scanner import security_scanner_tool
from friday.config_manager import config_manager_tool
from friday.logging_system import logging_tool
from friday.rate_limiter import rate_limiter_tool

print("=== SECURITY SCANNER ===")
r = security_scanner_tool(action='scan_code', code='password = "abc123"\neval(user_input)')
print("Issues found:", r["count"])
for v in r["vulnerabilities"][:3]:
    print("  ", v["severity"], v["title"])

r = security_scanner_tool(action='stats')
print("Stats:", r["total_scans"], "scans,", r["total_vulnerabilities"], "vulns")

print("\n=== CONFIG MANAGER ===")
r = config_manager_tool(action='get', key='server.port')
print("Get:", r)

r = config_manager_tool(action='set', key='server.port', value=8080)
print("Set:", r)

r = config_manager_tool(action='stats')
print("Stats:", r["total_keys"], "keys")

r = config_manager_tool(action='validate')
print("Validate:", r["count"], "issues")

print("\n=== LOGGING SYSTEM ===")
r = logging_tool(action='log', level='info', message='Test log entry')
print("Log:", r)

r = logging_tool(action='log', level='error', message='Test error entry')
print("Log error:", r)

r = logging_tool(action='stats')
print("Stats:", r["total"], "entries")

r = logging_tool(action='get_recent', count=5)
print("Recent:", len(r["entries"]), "entries")

print("\n=== RATE LIMITER ===")
r = rate_limiter_tool(action='check', rule='api_global', client_id='test')
print("Check:", "allowed" if r["allowed"] else "denied", "remaining:", r["remaining"])

r = rate_limiter_tool(action='rules')
print("Rules:", len(r["rules"]), "rules")

r = rate_limiter_tool(action='stats')
print("Stats:", r["total_requests"], "requests")

print("\nALL NEW MODULES OK")
