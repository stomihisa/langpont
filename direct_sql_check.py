#!/usr/bin/env python3
import sqlite3
import os

# Set working directory
os.chdir('/Users/shintaro_imac_2/langpont')

# Database path
db_path = 'langpont_activity_log.db'

print("=== Direct SQL Database Check ===\n")

if not os.path.exists(db_path):
    print(f"❌ Database file not found: {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Basic info
    cursor.execute("SELECT COUNT(*) FROM analysis_activity_log")
    total = cursor.fetchone()[0]
    print(f"Total records: {total}")

    # Today's records (UTC and JST)
    from datetime import datetime, timezone, timedelta
    
    today_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    cursor.execute("SELECT COUNT(*) FROM analysis_activity_log WHERE DATE(created_at) = ?", (today_utc,))
    today_utc_count = cursor.fetchone()[0]
    
    today_jst = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
    cursor.execute("SELECT COUNT(*) FROM analysis_activity_log WHERE DATE(created_at, '+9 hours') = ?", (today_jst,))
    today_jst_count = cursor.fetchone()[0]
    
    print(f"Today's records (UTC {today_utc}): {today_utc_count}")
    print(f"Today's records (JST {today_jst}): {today_jst_count}")

    # Check full_analysis_text
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN full_analysis_text IS NOT NULL AND full_analysis_text != '' THEN 1 END) as non_empty
        FROM analysis_activity_log
    """)
    result = cursor.fetchone()
    print(f"Records with non-empty full_analysis_text: {result[1]}/{result[0]}")

    # Check stage0_human_check
    cursor.execute("SELECT stage0_human_check, COUNT(*) FROM analysis_activity_log GROUP BY stage0_human_check")
    print("\nstage0_human_check distribution:")
    for row in cursor.fetchall():
        check_val = row[0] if row[0] else 'NULL'
        print(f"  {check_val}: {row[1]} records")

    # Recent records
    cursor.execute("""
        SELECT id, created_at, button_pressed, actual_analysis_llm, recommendation_result
        FROM analysis_activity_log 
        ORDER BY id DESC 
        LIMIT 5
    """)
    print("\nLatest 5 records:")
    for row in cursor.fetchall():
        print(f"  ID {row[0]}: {row[1]} | Button: {row[2]} | LLM: {row[3]} | Rec: {row[4]}")

    conn.close()
    print("\n✅ Check completed")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=== End of Direct SQL Check ===")