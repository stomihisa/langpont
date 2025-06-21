#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

print("Testing ActivityLogger syntax...")

try:
    import activity_logger
    print("✅ activity_logger.py syntax is valid")
    
    from activity_logger import ActivityLogger
    print("✅ ActivityLogger class import successful")
    
    from activity_logger import log_analysis_activity
    print("✅ log_analysis_activity function import successful")
    
    # Test basic instantiation
    logger = ActivityLogger()
    print("✅ ActivityLogger instantiation successful")
    
    print("✅ All syntax tests passed!")
    
except SyntaxError as e:
    print(f"❌ Syntax Error: {e}")
    print(f"❌ File: {e.filename}")
    print(f"❌ Line: {e.lineno}")
    print(f"❌ Text: {e.text}")
    
except Exception as e:
    print(f"❌ Runtime Error: {e}")
    import traceback
    traceback.print_exc()