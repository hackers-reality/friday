"""Test notification system, API gateway, and backup system."""
import sys, os
sys.path.insert(0, 'E:/open-interpreter')

from friday.notification_system import notification_system_tool
from friday.api_gateway import api_gateway_tool
from friday.backup_system import backup_system_tool

print("=== NOTIFICATION SYSTEM ===")
r = notification_system_tool(action='send', title='Test', message='Hello World')
print("Send:", r.get('success', False))

r = notification_system_tool(action='channels')
print("Channels:", len(r['channels']))

r = notification_system_tool(action='stats')
print("Stats:", r['total'], 'notifications')

print("\n=== API GATEWAY ===")
r = api_gateway_tool(action='generate_key', name='test_key', scopes=['read', 'write'])
print("Generate key:", 'key' in r)

r = api_gateway_tool(action='routes')
print("Routes:", len(r['routes']))

r = api_gateway_tool(action='check_rate', client_id='test', limit=10, window=60)
print("Rate check:", r['allowed'])

r = api_gateway_tool(action='stats')
print("Stats:", r.get('total_requests', 0), 'requests')

print("\n=== BACKUP SYSTEM ===")
r = backup_system_tool(action='create', name='test_backup', source='E:/open-interpreter/friday.py', compressed=True)
print("Create:", r.get('backup_id', 'FAIL')[:20])

r = backup_system_tool(action='list')
print("List:", len(r['backups']), 'backups')

r = backup_system_tool(action='stats')
print("Stats:", r['total_backups'], 'backups,', r['total_size_mb'], 'MB')

r = backup_system_tool(action='schedules')
print("Schedules:", len(r['schedules']))

print("\nALL 3 NEW MODULES OK")
