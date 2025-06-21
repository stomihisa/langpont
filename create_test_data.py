#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Data Creator for Unified Dashboard
統合ダッシュボード用のテストデータ作成
"""

import sys
import os
from datetime import datetime, timedelta

def create_test_data():
    print("=== 統合ダッシュボード用テストデータ作成 ===\n")
    
    try:
        from activity_logger import activity_logger, log_analysis_activity
        
        # テストデータの作成
        test_activities = [
            {
                'activity_type': 'normal_use',
                'user_id': 'admin',
                'japanese_text': 'おはようございます。今日の会議の準備をお願いします。',
                'button_pressed': 'Claude',
                'actual_analysis_llm': 'Claude',
                'recommendation_result': 'Enhanced',
                'confidence': 0.95,
                'full_analysis_text': 'このビジネス文章は丁寧で適切です。Enhancedバージョンが最も自然で効果的です。',
                'processing_duration': 2.3,
                'chatgpt_translation': 'Good morning. Please prepare for today\'s meeting.',
                'enhanced_translation': 'Good morning. Could you please prepare for today\'s meeting?',
                'gemini_translation': 'Good morning. Please get ready for today\'s meeting.'
            },
            {
                'activity_type': 'normal_use',
                'user_id': 'developer',
                'japanese_text': 'ありがとうございます。とても助かりました。',
                'button_pressed': 'Gemini',
                'actual_analysis_llm': 'Gemini',
                'recommendation_result': 'ChatGPT',
                'confidence': 0.87,
                'full_analysis_text': 'この感謝の表現はシンプルですが心のこもった内容です。ChatGPT翻訳が適切です。',
                'processing_duration': 1.8,
                'chatgpt_translation': 'Thank you very much. That was really helpful.',
                'enhanced_translation': 'Thank you so much. That was extremely helpful.',
                'gemini_translation': 'Thanks a lot. It was very helpful.'
            },
            {
                'activity_type': 'manual_test',
                'user_id': 'admin',
                'japanese_text': 'プロジェクトの進捗はいかがですか？',
                'button_pressed': 'ChatGPT',
                'actual_analysis_llm': 'ChatGPT',
                'recommendation_result': 'Gemini',
                'confidence': 0.72,
                'full_analysis_text': 'ビジネス質問です。Gemini翻訳がより自然でプロフェッショナルです。',
                'processing_duration': 3.1,
                'chatgpt_translation': 'How is the project progress?',
                'enhanced_translation': 'How is the progress of the project coming along?',
                'gemini_translation': 'How is the project progressing?'
            },
            {
                'activity_type': 'normal_use',
                'user_id': 'guest',
                'japanese_text': '明日の予定を確認させてください。',
                'button_pressed': 'Claude',
                'actual_analysis_llm': 'Claude',
                'recommendation_result': 'Enhanced',
                'confidence': 0.91,
                'full_analysis_text': '丁寧なビジネス表現です。Enhanced翻訳が最も適切で丁寧です。',
                'processing_duration': 2.7,
                'chatgpt_translation': 'Let me check tomorrow\'s schedule.',
                'enhanced_translation': 'Could you please let me confirm tomorrow\'s schedule?',
                'gemini_translation': 'I would like to check tomorrow\'s plans.'
            },
            {
                'activity_type': 'automated_test',
                'user_id': 'system',
                'japanese_text': 'システムテスト用のサンプル文章です。',
                'button_pressed': 'Gemini',
                'actual_analysis_llm': 'Gemini',
                'recommendation_result': 'ChatGPT',
                'confidence': 0.68,
                'full_analysis_text': 'テスト用文章です。ChatGPT翻訳がシンプルで適切です。',
                'processing_duration': 1.5,
                'error_occurred': False,
                'chatgpt_translation': 'This is a sample sentence for system testing.',
                'enhanced_translation': 'This is a sample sentence used for system testing purposes.',
                'gemini_translation': 'Sample text for system test.'
            }
        ]
        
        # テストデータを挿入
        inserted_count = 0
        for activity_data in test_activities:
            try:
                log_id = log_analysis_activity(activity_data)
                if log_id > 0:
                    inserted_count += 1
                    print(f"✅ テストデータ {inserted_count} 作成成功 (ID: {log_id})")
                else:
                    print(f"❌ テストデータ作成失敗")
            except Exception as e:
                print(f"❌ テストデータ作成エラー: {str(e)}")
        
        print(f"\n📊 作成完了: {inserted_count}/{len(test_activities)} 件のテストデータ")
        
        # 統計確認
        stats = activity_logger.get_activity_stats()
        print(f"\n📈 現在の統計:")
        print(f"  総活動数: {stats['basic']['total_activities']}")
        print(f"  今日の活動: {stats['basic']['today_activities']}")
        print(f"  エラー率: {stats['basic']['error_rate']}%")
        print(f"  LLM一致率: {stats['basic']['llm_match_rate']}%")
        
        print(f"\n🎯 次のステップ:")
        print("1. python app.py でアプリ起動")
        print("2. http://localhost:8080/admin/comprehensive_dashboard にアクセス")
        print("3. 統合ダッシュボードでデータを確認")
        
        return True
        
    except Exception as e:
        print(f"❌ テストデータ作成エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    create_test_data()