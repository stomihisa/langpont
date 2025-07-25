#!/usr/bin/env python3
import subprocess
import os

os.chdir('/Users/shintaro_imac_2/langpont')

# Execute the debug script
result = subprocess.run(['python3', 'debug_database.py'], capture_output=True, text=True)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")