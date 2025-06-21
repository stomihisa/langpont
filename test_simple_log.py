#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple Activity Log Test
"""

import sys
import os

# カレントディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== Simple Activity Log Test ===")

# 1. インポート
try:
    from activity_logger import activity_logger, log_analysis_activity
    print("✅ ActivityLogger インポート成功")
except Exception as e:
    print(f"❌ ActivityLogger インポート失敗: {e}")
    exit(1)

# 2. 最小限のテストデータ
test_data = {
    'activity_type': 'manual_test',
    'user_id': 'test_user',
    'japanese_text': 'テスト',
    'button_pressed': 'ChatGPT',
    'actual_analysis_llm': 'ChatGPT',
    'recommendation_result': 'Enhanced',
    'confidence': 0.95,
    'full_analysis_text': 'テスト分析'
}

# 3. ログ記録
try:
    log_id = log_analysis_activity(test_data)
    if log_id > 0:
        print(f"✅ ログ記録成功: ID={log_id}")
    else:
        print("❌ ログ記録失敗")
except Exception as e:
    print(f"❌ ログ記録エラー: {e}")
    import traceback
    traceback.print_exc()

# 4. 統計確認
try:
    from activity_logger import activity_logger
    stats = activity_logger.get_activity_stats()
    print(f"\n📊 統計:")
    print(f"  総活動数: {stats['basic']['total_activities']}")
    print(f"  今日の活動: {stats['basic']['today_activities']}")
except Exception as e:
    print(f"❌ 統計取得エラー: {e}")