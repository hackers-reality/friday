# Fix friday_web.py line 401
with open('friday_web.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line 401 is at index 400 (0-indexed)
# The issue: has `[` instead of `[`
print("Before:", repr(lines[400]))

# Fix: Replace the line with proper syntax
lines[400] = '            for selector in ["[itemprop=datePublished]", ".date", ".published", "time"]:\n'

print("After:", repr(lines[400]))

with open('friday_web.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed line 401")
