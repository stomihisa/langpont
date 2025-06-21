#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct execution of test data creation
"""

import sys
import os

# Add the directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the function
from create_test_data import create_test_data

# Execute the function
if __name__ == "__main__":
    result = create_test_data()
    if result:
        print("\n✅ Test data creation completed successfully!")
    else:
        print("\n❌ Test data creation failed!")