"""Test document parser, database connector, and git operations."""
import sys, os
sys.path.insert(0, 'E:/open-interpreter')

from friday.document_parser import document_parser_tool
from friday.database_connector import database_connector_tool
from friday.git_operations import git_operations_tool

print("=== DOCUMENT PARSER ===")
r = document_parser_tool(action='supported')
print("Supported:", len(r['extensions']), 'extensions')

r = document_parser_tool(action='parse_text', text='Hello world\nThis is a test\nLine 3')
print("Parse text:", r['success'], r['lines'], 'lines')

r = document_parser_tool(action='parse', path='E:/open-interpreter/friday.py')
print("Parse file:", r['success'], r.get('file_type', 'unknown'))

print("\n=== DATABASE CONNECTOR ===")
r = database_connector_tool(action='list')
print("Databases:", len(r['databases']))

r = database_connector_tool(action='create_table', table='test_users',
    columns={'id': 'INTEGER PRIMARY KEY', 'name': 'TEXT', 'email': 'TEXT'})
print("Create table:", r['success'])

r = database_connector_tool(action='insert', table='test_users',
    data={'id': 1, 'name': 'John', 'email': 'john@test.com'})
print("Insert:", r['success'])

r = database_connector_tool(action='insert_many', table='test_users', rows=[
    {'id': 2, 'name': 'Jane', 'email': 'jane@test.com'},
    {'id': 3, 'name': 'Bob', 'email': 'bob@test.com'},
])
print("Insert many:", r['success'], r.get('row_count', 0), 'rows')

r = database_connector_tool(action='select', table='test_users')
print("Select:", r['success'], r.get('row_count', 0), 'rows')

r = database_connector_tool(action='execute', query="SELECT COUNT(*) as cnt FROM test_users")
print("Count:", r['rows'][0]['cnt'] if r['rows'] else 0)

r = database_connector_tool(action='drop_table', table='test_users')
print("Drop:", r['success'])

print("\n=== GIT OPERATIONS ===")
r = git_operations_tool(action='status')
print("Is repo:", 'branch' in r or 'error' not in r)

r = git_operations_tool(action='log', count=3)
print("Log:", len(r.get('commits', [])), 'commits')

r = git_operations_tool(action='branches')
print("Branches:", len(r.get('branches', [])))

r = git_operations_tool(action='stats')
print("Stats:", r.get('branch', 'unknown'))

print("\nALL 3 NEW MODULES OK")
