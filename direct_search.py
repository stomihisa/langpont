#!/usr/bin/env python3

# Search directly in app.py for export_activity_log and make_response
app_py_path = '/Users/shintaro_imac_2/langpont/app.py'

try:
    with open(app_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')

    print("=== Searching for export_activity_log and make_response ===")
    print()

    found_export = False
    found_make_response = False

    for i, line in enumerate(lines):
        if 'export_activity_log' in line:
            print(f'Line {i+1}: {line.strip()}')
            found_export = True
        if 'make_response' in line:
            print(f'Line {i+1}: {line.strip()}')
            found_make_response = True

    print("\n" + "=" * 60)
    if not found_export:
        print("❌ export_activity_log NOT FOUND")
    else:
        print("✅ export_activity_log FOUND")
        
    if not found_make_response:
        print("❌ make_response NOT FOUND")
    else:
        print("✅ make_response FOUND")
        
    print("Search completed.")

except FileNotFoundError:
    print(f"Error: File {app_py_path} not found")
except Exception as e:
    print(f"Error: {e}")