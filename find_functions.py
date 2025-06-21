#!/usr/bin/env python3

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

print("Looking for export_activity_log and make_response in app.py...")
print("=" * 60)

found_export = False
found_make_response = False

for i, line in enumerate(lines):
    if 'export_activity_log' in line:
        print(f'Line {i+1}: {line.strip()}')
        found_export = True
    if 'make_response' in line:
        print(f'Line {i+1}: {line.strip()}')
        found_make_response = True

print("=" * 60)
if not found_export:
    print("export_activity_log NOT FOUND")
if not found_make_response:
    print("make_response NOT FOUND")
    
print("Search completed.")