#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手動データベース調査スクリプト
デバッグに必要な全ての情報を取得
"""

import sqlite3
import json
from datetime import datetime, timezone, timedelta
import os

# データベースパス
DB_PATH = '/Users/shintaro_imac_2/langpont/langpont_activity_log.db'

def investigate():
    print("=== LangPont データベース調査 ===\n")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ データベースファイルが存在しません: {DB_PATH}")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. 基本情報
        print("1. 基本データベース情報")
        print("-" * 30)
        cursor.execute("SELECT COUNT(*) as total FROM analysis_activity_log")
        total = cursor.fetchone()[0]
        print(f"総レコード数: {total}件")
        
        # 2. 今日のアクティビティ
        print("\n2. 今日のアクティビティ（複数タイムゾーン）")
        print("-" * 30)
        today_utc = datetime.now(timezone.utc).date()
        today_jst = datetime.now(timezone(timedelta(hours=9))).date()
        
        # UTC時間での今日
        cursor.execute("SELECT COUNT(*) FROM analysis_activity_log WHERE DATE(created_at) = ?", (str(today_utc),))
        utc_count = cursor.fetchone()[0]
        print(f"今日(UTC {today_utc}): {utc_count}件")
        
        # JST時間での今日 
        cursor.execute("SELECT COUNT(*) FROM analysis_activity_log WHERE DATE(created_at, '+9 hours') = ?", (str(today_jst),))
        jst_count = cursor.fetchone()[0]
        print(f"今日(JST {today_jst}): {jst_count}件")
        
        # 3. full_analysis_text の状況
        print("\n3. full_analysis_text の状況")
        print("-" * 30)
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(full_analysis_text) as not_null,
                COUNT(CASE WHEN full_analysis_text IS NOT NULL AND full_analysis_text != '' THEN 1 END) as not_empty
            FROM analysis_activity_log
        """)
        result = cursor.fetchone()
        print(f"全レコード: {result['total']}件")
        print(f"NULLでない: {result['not_null']}件")
        print(f"空文字でない: {result['not_empty']}件")
        
        # 4. stage0_human_check の状況
        print("\n4. stage0_human_check の状況")
        print("-" * 30)
        cursor.execute("""
            SELECT stage0_human_check, COUNT(*) as count 
            FROM analysis_activity_log 
            GROUP BY stage0_human_check
        """)
        for row in cursor.fetchall():
            value = row['stage0_human_check'] if row['stage0_human_check'] else 'NULL'
            print(f"{value}: {row['count']}件")
        
        # 5. アクティビティタイプ分布
        print("\n5. アクティビティタイプ分布")
        print("-" * 30)
        cursor.execute("""
            SELECT activity_type, COUNT(*) as count 
            FROM analysis_activity_log 
            GROUP BY activity_type
        """)
        for row in cursor.fetchall():
            activity_type = row['activity_type'] if row['activity_type'] else 'NULL'
            print(f"{activity_type}: {row['count']}件")
        
        # 6. LLM一致状況
        print("\n6. LLM一致状況")
        print("-" * 30)
        cursor.execute("""
            SELECT 
                button_pressed, actual_analysis_llm, 
                COUNT(*) as count,
                CASE WHEN button_pressed = actual_analysis_llm THEN 'MATCH' ELSE 'MISMATCH' END as status
            FROM analysis_activity_log 
            WHERE button_pressed IS NOT NULL AND actual_analysis_llm IS NOT NULL
            GROUP BY button_pressed, actual_analysis_llm
            ORDER BY count DESC
        """)
        for row in cursor.fetchall():
            print(f"{row['button_pressed']} → {row['actual_analysis_llm']} ({row['status']}): {row['count']}件")
        
        # 7. 最新レコードの詳細
        print("\n7. 最新5件の詳細")
        print("-" * 30)
        cursor.execute("""
            SELECT id, created_at, activity_type, button_pressed, actual_analysis_llm, 
                   recommendation_result, stage0_human_check,
                   CASE WHEN full_analysis_text IS NULL THEN 'NULL'
                        WHEN full_analysis_text = '' THEN 'EMPTY'
                        ELSE 'OK' END as analysis_status
            FROM analysis_activity_log 
            ORDER BY id DESC LIMIT 5
        """)
        
        for i, row in enumerate(cursor.fetchall(), 1):
            print(f"\n#{i} - ID: {row['id']}")
            print(f"  日時: {row['created_at']}")
            print(f"  タイプ: {row['activity_type']}")
            print(f"  ボタン: {row['button_pressed']}")
            print(f"  実行LLM: {row['actual_analysis_llm']}")
            print(f"  推奨結果: {row['recommendation_result']}")
            print(f"  人間チェック: {row['stage0_human_check']}")
            print(f"  分析テキスト: {row['analysis_status']}")
        
        # 8. エラー統計
        print("\n8. エラー統計")
        print("-" * 30)
        cursor.execute("SELECT COUNT(*) FROM analysis_activity_log WHERE error_occurred = 1")
        error_count = cursor.fetchone()[0]
        print(f"エラー発生件数: {error_count}件")
        print(f"エラー率: {(error_count/total*100):.1f}%")
        
        # 9. 推奨結果の分布
        print("\n9. 推奨結果の分布")
        print("-" * 30)
        cursor.execute("""
            SELECT recommendation_result, COUNT(*) as count 
            FROM analysis_activity_log 
            WHERE recommendation_result IS NOT NULL
            GROUP BY recommendation_result
            ORDER BY count DESC
        """)
        for row in cursor.fetchall():
            print(f"{row['recommendation_result']}: {row['count']}件")
        
        conn.close()
        print("\n✅ 調査完了")
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate()