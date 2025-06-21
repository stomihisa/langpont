#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Recreate Activity Log Database
データベースを削除して再作成
"""

import os
import sys

def recreate_db():
    print("=== Recreate Activity Log Database ===")
    
    # 1. 既存データベースの削除
    db_path = "langpont_activity_log.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"✅ 既存データベース削除: {db_path}")
        except Exception as e:
            print(f"❌ データベース削除失敗: {e}")
            return False
    else:
        print("ℹ️ 既存データベースなし")
    
    # 2. ActivityLogger を再インポートして初期化
    try:
        # モジュールをリロード
        if 'activity_logger' in sys.modules:
            del sys.modules['activity_logger']
        
        from activity_logger import activity_logger
        print("✅ ActivityLogger 再初期化完了")
        
        # 3. テストデータ挿入
        test_data = {
            'activity_type': 'manual_test',
            'user_id': 'recreate_test',
            'japanese_text': 'データベース再作成テスト',
            'button_pressed': 'ChatGPT',
            'actual_analysis_llm': 'ChatGPT',
            'recommendation_result': 'Enhanced',
            'confidence': 0.99,
            'full_analysis_text': 'DB再作成後の初回テスト'
        }
        
        from activity_logger import log_analysis_activity
        log_id = log_analysis_activity(test_data)
        
        if log_id > 0:
            print(f"✅ テストログ挿入成功: ID={log_id}")
            
            # 統計確認
            stats = activity_logger.get_activity_stats()
            print(f"\n📊 統計確認:")
            print(f"  総活動数: {stats['basic']['total_activities']}")
            
            return True
        else:
            print("❌ テストログ挿入失敗")
            return False
            
    except Exception as e:
        print(f"❌ 再作成エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = recreate_db()
    
    if success:
        print("\n✅ データベース再作成成功")
        print("💡 次の手順:")
        print("1. python insert_test_data.py でテストデータ挿入")
        print("2. ダッシュボードをリロード")
    else:
        print("\n❌ データベース再作成失敗")
        print("🔧 activity_logger.py の修正が必要です")