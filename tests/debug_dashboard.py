"""Debug dashboard - test all dashboard components."""
import sys, os, json
sys.path.insert(0, 'E:/open-interpreter')

print("=== 1. DASHBOARD CLI TOOL ===")
from friday.dashboard_cli import dashboard_cli_tool

r = dashboard_cli_tool(action='status')
print("status type:", type(r).__name__)
print("status:", str(r)[:200])

r = dashboard_cli_tool(action='json')
print("\njson type:", type(r).__name__)
print("json:", str(r)[:200])

print("\n=== 2. BOOTSTRAP STATUS ===")
from friday.bootstrap import bootstrap_tool
r = bootstrap_tool(action='status')
print("bootstrap type:", type(r).__name__)
print("bootstrap:", str(r)[:300])

print("\n=== 3. MEMORY STATS ===")
from friday.autonomous_memory import autonomous_memory_tool
r = autonomous_memory_tool(action='stats')
print("memory type:", type(r).__name__)
print("memory:", str(r)[:300])

print("\n=== 4. CODEBASE STATS ===")
from friday.codebase_analyzer import codebase_analyzer_tool
r = codebase_analyzer_tool(action='stats')
print("codebase type:", type(r).__name__)
print("codebase:", str(r)[:300])

print("\n=== 5. HEALTH MONITOR ===")
from friday.health_monitor import health_monitor_tool
r = health_monitor_tool(action='status')
print("health type:", type(r).__name__)
print("health:", str(r)[:300])

print("\n=== 6. METRICS DASHBOARD ===")
from friday.metrics_collector import metrics_collector_tool
r = metrics_collector_tool(action='dashboard')
print("metrics type:", type(r).__name__)
print("metrics:", str(r)[:300])

print("\n=== 7. CONFIG MANAGER ===")
from friday.config_manager import config_manager_tool
r = config_manager_tool(action='get_all')
print("config type:", type(r).__name__)
print("config:", str(r)[:300])

print("\n=== 8. SECURITY SCANNER ===")
from friday.security_scanner import security_scanner_tool
r = security_scanner_tool(action='stats')
print("security type:", type(r).__name__)
print("security:", str(r)[:300])

print("\n=== 9. GIT STATUS ===")
from friday.git_operations import git_operations_tool
r = git_operations_tool(action='stats')
print("git type:", type(r).__name__)
print("git:", str(r)[:300])

print("\n=== 10. RATE LIMITER ===")
from friday.rate_limiter import rate_limiter_tool
r = rate_limiter_tool(action='stats')
print("ratelimit type:", type(r).__name__)
print("ratelimit:", str(r)[:300])

print("\n=== 11. NOTIFICATION SYSTEM ===")
from friday.notification_system import notification_system_tool
r = notification_system_tool(action='stats')
print("notifications type:", type(r).__name__)
print("notifications:", str(r)[:300])

print("\n=== 12. BACKUP SYSTEM ===")
from friday.backup_system import backup_system_tool
r = backup_system_tool(action='stats')
print("backups type:", type(r).__name__)
print("backups:", str(r)[:300])

print("\n=== 13. API GATEWAY ===")
from friday.api_gateway import api_gateway_tool
r = api_gateway_tool(action='stats')
print("gateway type:", type(r).__name__)
print("gateway:", str(r)[:300])

print("\n=== 14. CACHE SYSTEM ===")
from friday.cache_system import cache_system_tool
r = cache_system_tool(action='stats')
print("cache type:", type(r).__name__)
print("cache:", str(r)[:300])

print("\n=== 15. TASK SCHEDULER ===")
from friday.task_scheduler import task_scheduler_tool
r = task_scheduler_tool(action='stats')
print("scheduler type:", type(r).__name__)
print("scheduler:", str(r)[:300])

print("\nDONE - ALL MODULES TESTED")
