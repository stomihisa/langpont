#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ActivityLogger fix test script
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing ActivityLogger fix...")
    from activity_logger import activity_logger
    print("✅ ActivityLogger import successful")
    
    # Test basic functionality
    test_data = {
        'activity_type': 'manual_test',
        'user_id': 'test_user',
        'japanese_text': 'テスト用文章',
        'button_pressed': 'Claude',
        'actual_analysis_llm': 'Claude',
        'recommendation_result': 'Enhanced',
        'confidence': 0.95
    }
    
    log_id = activity_logger.log_activity(test_data)
    print(f"✅ Test activity logged with ID: {log_id}")
    
    # Test statistics
    stats = activity_logger.get_activity_stats()
    print(f"✅ Statistics retrieved: {stats['basic']['total_activities']} total activities")
    
    print("✅ ActivityLogger fix test completed successfully!")
    
except Exception as e:
    print(f"❌ ActivityLogger test failed: {str(e)}")
    import traceback
    traceback.print_exc()