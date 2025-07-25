import sqlite3
conn = sqlite3.connect('/Users/shintaro_imac_2/langpont/langpont_activity_log.db')
cursor = conn.cursor()

# 1. Total records
cursor.execute("SELECT COUNT(*) FROM analysis_activity_log")
print(f"Total records: {cursor.fetchone()[0]}")

# 2. Today's count  
from datetime import datetime
today = datetime.now().strftime('%Y-%m-%d')
cursor.execute("SELECT COUNT(*) FROM analysis_activity_log WHERE DATE(created_at) = ?", (today,))
print(f"Today's count: {cursor.fetchone()[0]}")

# 3. Check recent records
cursor.execute("SELECT id, created_at, activity_type, button_pressed, actual_analysis_llm FROM analysis_activity_log ORDER BY id DESC LIMIT 5")
print("Recent 5 records:")
for row in cursor.fetchall():
    print(f"ID: {row[0]}, Date: {row[1]}, Type: {row[2]}, Button: {row[3]}, LLM: {row[4]}")

conn.close()
print("Done")