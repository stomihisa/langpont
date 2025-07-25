#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Activity Logging Debug Script
活動ログが正しく記録されているかデバッグ
"""

import os
import sqlite3
from datetime import datetime

def debug_activity_logging():
    print("=== Activity Logging Debug ===")
    print("")
    
    # 1. ActivityLogger インポートテスト
    print("1. ActivityLogger インポートテスト")
    try:
        from activity_logger import activity_logger, log_analysis_activity
        print("✅ ActivityLogger インポート成功")
    except Exception as e:
        print(f"❌ ActivityLogger インポート失敗: {e}")
        return
    
    # 2. データベースファイル確認
    print("\n2. データベースファイル確認")
    db_path = "langpont_activity_log.db"
    if os.path.exists(db_path):
        print(f"✅ データベースファイル存在: {db_path}")
        size = os.path.getsize(db_path)
        print(f"📊 ファイルサイズ: {size} bytes")
    else:
        print(f"❌ データベースファイル不存在: {db_path}")
    
    # 3. データベース内容確認
    print("\n3. データベース内容確認")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # テーブル存在確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📋 テーブル一覧: {[t[0] for t in tables]}")
        
        # analysis_activity_log テーブル確認
        if ('analysis_activity_log',) in tables:
            cursor.execute("SELECT COUNT(*) FROM analysis_activity_log")
            count = cursor.fetchone()[0]
            print(f"📊 総レコード数: {count}")
            
            if count > 0:
                # 最新レコード表示
                cursor.execute("""
                    SELECT id, activity_type, user_id, created_at, japanese_text, 
                           button_pressed, recommendation_result, confidence
                    FROM analysis_activity_log 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """)
                records = cursor.fetchall()
                print("\n📋 最新5件のレコード:")
                for record in records:
                    print(f"  ID:{record[0]} | {record[1]} | {record[2]} | {record[3]}")
                    print(f"    Text: {record[4][:50]}...")
                    print(f"    Button: {record[5]} | Result: {record[6]} | Confidence: {record[7]}")
            else:
                print("📝 レコードが空です")
        else:
            print("❌ analysis_activity_log テーブルが存在しません")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ データベース確認エラー: {e}")
    
    # 4. 手動テストログ記録
    print("\n4. 手動テストログ記録")
    try:
        test_data = {
            'activity_type': 'manual_test',
            'user_id': 'debug_script',
            'japanese_text': 'デバッグテスト用の日本語文章です',
            'button_pressed': 'ChatGPT',
            'actual_analysis_llm': 'ChatGPT',
            'recommendation_result': 'Enhanced',
            'confidence': 0.95,
            'full_analysis_text': 'これはデバッグ用のテスト分析結果です',
            'processing_duration': 2.5,
            'notes': 'Debug script test'
        }
        
        log_id = log_analysis_activity(test_data)
        if log_id > 0:
            print(f"✅ テストログ記録成功: ID={log_id}")
        else:
            print("❌ テストログ記録失敗")
            
    except Exception as e:
        print(f"❌ テストログ記録エラー: {e}")
    
    # 5. 統計取得テスト
    print("\n5. 統計取得テスト")
    try:
        stats = activity_logger.get_activity_stats()
        print("📊 統計データ:")
        print(f"  総活動数: {stats['basic']['total_activities']}")
        print(f"  今日の活動: {stats['basic']['today_activities']}")
        print(f"  エラー率: {stats['basic']['error_rate']}%")
        print(f"  LLM一致率: {stats['basic']['llm_match_rate']}%")
        
    except Exception as e:
        print(f"❌ 統計取得エラー: {e}")
    
    # 6. ダッシュボードAPI接続テスト
    print("\n6. ダッシュボードAPI接続テスト")
    try:
        import requests
        
        # 統計API テスト
        response = requests.get('http://127.0.0.1:8080/admin/api/activity_stats', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 統計API応答: {data['basic']['total_activities']} 活動")
        elif response.status_code == 403:
            print("⚠️ 統計API: 認証が必要（管理者ログイン必要）")
        else:
            print(f"❌ 統計API: {response.status_code}")
            
    except Exception as e:
        print(f"❌ API接続エラー: {e}")

if __name__ == "__main__":
    debug_activity_logging()
    print("\n=== デバッグ完了 ===")
    print("📝 次の手順:")
    print("1. レコード数が0の場合: ニュアンス分析を数回実行")
    print("2. テストログが記録されない場合: ActivityLoggerの初期化問題")
    print("3. API認証エラーの場合: admin/developerでログイン")