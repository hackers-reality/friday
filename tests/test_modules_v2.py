"""Test task scheduler, health monitor, cache, and metrics."""
import sys, time
sys.path.insert(0, 'E:/open-interpreter')

from friday.task_scheduler import task_scheduler_tool
from friday.health_monitor import health_monitor_tool
from friday.cache_system import cache_system_tool
from friday.metrics_collector import metrics_collector_tool

print("=== TASK SCHEDULER ===")
r = task_scheduler_tool(action='add', name='test_task', schedule={'type': 'interval', 'interval_seconds': 60}, task_action='log', params={'message': 'hello'})
print("Add:", r.get('task_id', 'FAIL'))

r = task_scheduler_tool(action='list')
print("List:", len(r['tasks']), 'tasks')

r = task_scheduler_tool(action='stats')
print("Stats:", r['total_tasks'], 'tasks')

print("\n=== HEALTH MONITOR ===")
r = health_monitor_tool(action='status')
print("Overall:", r.get('overall_status', 'FAIL'))

r = health_monitor_tool(action='checks')
print("Checks:", len(r['checks']), 'checks')

r = health_monitor_tool(action='metrics')
print("Metrics:", 'cpu_percent' in r)

print("\n=== CACHE SYSTEM ===")
cache_system_tool(action='set', key='test_key', value='test_value', ttl=300)
r = cache_system_tool(action='get', key='test_key')
print("Get:", r.get('value', 'FAIL'))

r = cache_system_tool(action='exists', key='test_key')
print("Exists:", r.get('exists', False))

r = cache_system_tool(action='stats')
print("Stats:", r.get('hit_rate', 0), '% hit rate')

print("\n=== METRICS COLLECTOR ===")
metrics_collector_tool(action='counter', name='test_counter', increment=5)
r = metrics_collector_tool(action='counters')
print("Counters:", r.get('counters', {}).get('test_counter', 0) == 5)

metrics_collector_tool(action='gauge', name='test_gauge', value=42)
r = metrics_collector_tool(action='gauges')
print("Gauges:", r.get('gauges', {}).get('test_gauge', 0) == 42)

r = metrics_collector_tool(action='dashboard')
print("Dashboard:", 'system' in r)

print("\nALL 4 NEW MODULES OK")
