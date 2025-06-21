#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 実際の値リスト（activity_logger.py 197-236行目）
values = """activity_data.get('activity_type'),
activity_data.get('session_id'),
activity_data.get('user_id'),
activity_data.get('test_session_id'),
activity_data.get('test_number'),
activity_data.get('sample_id'),
activity_data.get('sample_name'),
activity_data.get('japanese_text'),
activity_data.get('target_language', 'en'),
activity_data.get('language_pair', 'ja-en'),
activity_data.get('partner_message'),
activity_data.get('context_info'),
activity_data.get('chatgpt_translation'),
activity_data.get('enhanced_translation'),
activity_data.get('gemini_translation'),
activity_data.get('button_pressed'),
activity_data.get('actual_analysis_llm'),
llm_match,
activity_data.get('recommendation_result'),
activity_data.get('confidence'),
activity_data.get('processing_method'),
activity_data.get('extraction_method'),
activity_data.get('full_analysis_text'),
analysis_preview,
activity_data.get('terminal_logs'),
activity_data.get('debug_logs'),
activity_data.get('error_occurred', False),
activity_data.get('error_message'),
activity_data.get('processing_duration'),
activity_data.get('translation_duration'),
activity_data.get('analysis_duration'),
activity_data.get('ip_address'),
activity_data.get('user_agent'),
json.dumps(activity_data.get('request_headers', {})),
now.year,
now.month,
now.day,
now.hour,
activity_data.get('notes'),
json.dumps(activity_data.get('tags', []))"""

# カラムリスト（activity_logger.py 183-195行目）
columns = """activity_type, session_id, user_id,
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

values_list = [v.strip() for v in values.split(',\n')]
columns_list = [c.strip() for c in columns.replace('\n', ' ').split(',')]

print(f"Values count: {len(values_list)}")
print(f"Columns count: {len(columns_list)}")
print(f"Difference: {len(columns_list) - len(values_list)}")

if len(values_list) != len(columns_list):
    print("\nMismatch details:")
    for i, (col, val) in enumerate(zip(columns_list, values_list)):
        print(f"{i+1:2d}. {col:25s} = {val}")
    
    if len(columns_list) > len(values_list):
        print("\nMissing values for columns:")
        for i in range(len(values_list), len(columns_list)):
            print(f"{i+1:2d}. {columns_list[i]:25s} = ???")