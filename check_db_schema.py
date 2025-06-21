#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Check Database Schema
データベースの実際のスキーマを確認
"""

import sqlite3

def check_schema():
    print("=== Database Schema Check ===")
    
    try:
        conn = sqlite3.connect('langpont_activity_log.db')
        cursor = conn.cursor()
        
        # テーブル情報を取得
        cursor.execute("PRAGMA table_info(analysis_activity_log)")
        columns = cursor.fetchall()
        
        print(f"📋 analysis_activity_log テーブルのカラム数: {len(columns)}")
        print("\n📊 カラム詳細:")
        
        insert_columns = []
        for i, col in enumerate(columns):
            cid, name, type_, notnull, dflt_value, pk = col
            print(f"{cid:3d}. {name:30s} {type_:20s} {'NOT NULL' if notnull else 'NULL':8s} {f'DEFAULT {dflt_value}' if dflt_value else ''}")
            
            # PRIMARY KEY と DEFAULT 値があるカラムはINSERTで指定しない
            if not pk and dflt_value is None:
                insert_columns.append(name)
            elif not pk and dflt_value != 'CURRENT_TIMESTAMP':
                insert_columns.append(name)
        
        print(f"\n📝 INSERT時に指定すべきカラム数: {len(insert_columns)}")
        print("INSERT対象カラム:")
        for i, col in enumerate(insert_columns):
            print(f"  {i+1:2d}. {col}")
        
        print(f"\n✅ 必要な?の数: {len(insert_columns)}")
        print(f"正しいプレースホルダー: ({', '.join(['?'] * len(insert_columns))})")
        
        conn.close()
        
        return len(insert_columns)
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return -1

if __name__ == "__main__":
    required_placeholders = check_schema()
    
    if required_placeholders > 0:
        print(f"\n💡 activity_logger.py の INSERT 文で {required_placeholders} 個の ? が必要です")