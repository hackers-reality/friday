#!/usr/bin/env python3
"""Debug authority policy loading."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

from friday._paths import FRIDAY_MEMORY
from friday.authority import should_allow_tool, load_authority_policy, classify_tool_risk, _get_default_policy

policy_file = os.path.join(FRIDAY_MEMORY, "authority_policy.json")
print(f"Policy file exists: {os.path.exists(policy_file)}")
if os.path.exists(policy_file):
    with open(policy_file) as f:
        print(f"Policy content: {json.load(f)}")
else:
    # Remove to force default
    print("No policy file - will use defaults")

print(f"Default policy keys: {list(_get_default_policy().keys())}")
print(f"Default allow_read_only: {_get_default_policy().get('allow_read_only', 'NOT FOUND')}")

# Clear any stale policy file to force defaults
if os.path.exists(policy_file):
    os.remove(policy_file)
    print(f"Removed stale policy file")

print(f"Classify read_file: {classify_tool_risk('read_file')}")

p = load_authority_policy()
print(f"Loaded policy keys: {list(p.keys())}")
print(f"Loaded policy allow_read_only: {p.get('allow_read_only', 'NOT FOUND')}")

d = should_allow_tool("read_file")
print(f"Decision: {d}")

# Now test with fresh default
from friday.authority import RISK_LEVELS
risk = classify_tool_risk("read_file")
risk_level = RISK_LEVELS.get(risk, 0)
max_level = p.get("max_risk_level", 2)
perm_key = f"allow_{risk}"
print(f"risk={risk}, risk_level={risk_level}, max_level={max_level}, perm_key={perm_key}")
print(f"perm_key in policy: {perm_key in p}")
print(f"perm_key value: {p.get(perm_key, 'NOT FOUND')}")
