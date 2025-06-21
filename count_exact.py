#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
正確なカラム数を数える
"""

# activity_logger.py のINSERT文のカラムリスト（183-194行目）
insert_columns = """activity_type, session_id, user_id,
test_session_id, test_number, sample_id, sample_name,
japanese_text, target_language, language_pair, partner_message, context_info,
chatgpt_translation, enhanced_translation, gemini_translation,
button_pressed, actual_analysis_llm, llm_match,
recommendation_result, confidence, processing_method, extraction_method,
full_analysis_text, analysis_preview,
terminal_logs, debug_logs, error_occurred, error_message,
processing_duration, translation_duration, analysis_duration,
ip_address, user_agent, request_headers,
year, month, day, hour,
notes, tags"""

# カンマで分割してカラム数を数える
columns = [col.strip() for col in insert_columns.replace('\n', ' ').split(',')]
print(f"INSERT文のカラム数: {len(columns)}")

# ?の数を数える
placeholders = "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
question_marks = placeholders.count('?')
print(f"現在の?の数: {question_marks}")

# 各カラムを番号付きで表示
print("\nINSERT文のカラムリスト:")
for i, col in enumerate(columns, 1):
    print(f"{i:2d}. {col}")

print(f"\n結論: INSERT文のカラム数と?の数が一致{'しています' if len(columns) == question_marks else 'していません'}")