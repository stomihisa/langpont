#!/usr/bin/env python3

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'export_activity_log' in line or 'make_response' in line:
        print(f'Line {i+1}: {line.strip()}')