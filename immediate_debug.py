#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
即座にデータベース調査を実行
"""

import sqlite3
from datetime import datetime, timezone, timedelta
import os

# langpontディレクトリに移動
os.chdir('/Users/shintaro_imac_2/langpont')

print("🔍 データベース調査開始...")

try:
    conn = sqlite3.connect('langpont_activity_log.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n📊 1. 総レコード数確認")
    cursor.execute("SELECT COUNT(*) as total FROM analysis_activity_log")
    total = cursor.fetchone()[0]
    print(f"総レコード数: {total}件")
    
    print("\n📊 2. full_analysis_text の状況確認")
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(full_analysis_text) as with_analysis,
            COUNT(CASE WHEN full_analysis_text IS NOT NULL AND full_analysis_text != '' THEN 1 END) as non_empty_analysis
        FROM analysis_activity_log
    """)
    result = cursor.fetchone()
    print(f"全レコード: {result['total']}件")
    print(f"full_analysis_textがNULLでない: {result['with_analysis']}件")
    print(f"full_analysis_textが空でない: {result['non_empty_analysis']}件")
    
    print("\n📊 3. 最新10件のfull_analysis_text確認")
    cursor.execute("""
        SELECT 
            id, created_at, 
            CASE 
                WHEN full_analysis_text IS NULL THEN 'NULL'
                WHEN full_analysis_text = '' THEN 'EMPTY'
                ELSE SUBSTR(full_analysis_text, 1, 50) || '...'
            END as analysis_preview
        FROM analysis_activity_log 
        ORDER BY id DESC 
        LIMIT 10
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID {row['id']}: {row['created_at']} - {row['analysis_preview']}")
    
    print("\n📊 4. stage0_human_check の状況確認")
    cursor.execute("""
        SELECT 
            stage0_human_check,
            COUNT(*) as count
        FROM analysis_activity_log 
        GROUP BY stage0_human_check
    """)
    rows = cursor.fetchall()
    print("人間チェック状況:")
    for row in rows:
        check_value = row['stage0_human_check'] if row['stage0_human_check'] else 'NULL'
        print(f"  {check_value}: {row['count']}件")
    
    print("\n📊 5. 今日の活動確認（複数のタイムゾーンで）")
    today_jst = datetime.now(timezone(timedelta(hours=9))).date()
    today_utc = datetime.now(timezone.utc).date()
    
    # JSTで確認
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM analysis_activity_log 
        WHERE DATE(created_at, '+9 hours') = ?
    """, (str(today_jst),))
    jst_count = cursor.fetchone()[0]
    print(f"今日の活動 (JST {today_jst}): {jst_count}件")
    
    # UTCで確認
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM analysis_activity_log 
        WHERE DATE(created_at) = ?
    """, (str(today_utc),))
    utc_count = cursor.fetchone()[0]
    print(f"今日の活動 (UTC {today_utc}): {utc_count}件")
    
    print("\n📊 6. activity_typeの分布確認")
    cursor.execute("""
        SELECT activity_type, COUNT(*) as count 
        FROM analysis_activity_log 
        GROUP BY activity_type
    """)
    rows = cursor.fetchall()
    print("活動タイプ分布:")
    for row in rows:
        activity_type = row['activity_type'] if row['activity_type'] else 'NULL'
        print(f"  {activity_type}: {row['count']}件")
    
    print("\n📊 7. LLM一致率の詳細確認")
    cursor.execute("""
        SELECT 
            button_pressed,
            actual_analysis_llm,
            COUNT(*) as count,
            CASE WHEN button_pressed = actual_analysis_llm THEN 'MATCH' ELSE 'MISMATCH' END as match_status
        FROM analysis_activity_log 
        WHERE button_pressed IS NOT NULL AND actual_analysis_llm IS NOT NULL
        GROUP BY button_pressed, actual_analysis_llm, match_status
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()
    print("ボタン押下 vs 実際実行:")
    for row in rows:
        print(f"  {row['button_pressed']} → {row['actual_analysis_llm']} ({row['match_status']}): {row['count']}件")
    
    print("\n📊 8. 最新レコードの詳細確認")
    cursor.execute("""
        SELECT * FROM analysis_activity_log 
        ORDER BY id DESC 
        LIMIT 3
    """)
    rows = cursor.fetchall()
    print("最新3件の詳細:")
    for i, row in enumerate(rows, 1):
        print(f"\n--- レコード {i} (ID: {row['id']}) ---")
        print(f"作成日時: {row['created_at']}")
        print(f"日本語文: {row['japanese_text'][:50] if row['japanese_text'] else 'NULL'}...")
        print(f"活動タイプ: {row['activity_type']}")
        print(f"ボタン押下: {row['button_pressed']}")
        print(f"実際のLLM: {row['actual_analysis_llm']}")
        print(f"推奨結果: {row['recommendation_result']}")
        print(f"人間チェック: {row['stage0_human_check']}")
        print(f"分析テキスト有無: {'有' if row['full_analysis_text'] else '無'}")
    
    conn.close()
    print("\n✅ 調査完了")
    
except Exception as e:
    print(f"❌ エラー発生: {str(e)}")
    import traceback
    traceback.print_exc()