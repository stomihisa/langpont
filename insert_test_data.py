#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Data Insertion
テスト用データを手動で挿入してダッシュボードが動作するか確認
"""

from datetime import datetime, timedelta
import random

def insert_test_data():
    print("=== Test Data Insertion ===")
    
    try:
        from activity_logger import activity_logger, log_analysis_activity
        print("✅ ActivityLogger インポート成功")
    except Exception as e:
        print(f"❌ ActivityLogger インポート失敗: {e}")
        return False
    
    # テスト用データのセット
    test_datasets = [
        {
            'activity_type': 'normal_use',
            'user_id': 'developer',
            'japanese_text': 'おはようございます。今日の会議の件でご連絡いたします。',
            'button_pressed': 'ChatGPT',
            'actual_analysis_llm': 'ChatGPT',
            'recommendation_result': 'Enhanced',
            'confidence': 0.92,
            'full_analysis_text': 'ChatGPT翻訳は適切ですが、Enhanced翻訳の方がより丁寧で適切です。',
        },
        {
            'activity_type': 'normal_use',
            'user_id': 'developer',
            'japanese_text': 'プロジェクトの進捗はいかがでしょうか？',
            'button_pressed': 'Gemini',
            'actual_analysis_llm': 'Gemini',
            'recommendation_result': 'ChatGPT',
            'confidence': 0.88,
            'full_analysis_text': 'Gemini翻訳も良いですが、ChatGPT翻訳がより自然です。',
        },
        {
            'activity_type': 'normal_use',
            'user_id': 'admin',
            'japanese_text': '申し訳ございませんが、会議の時間を変更させていただけませんでしょうか。',
            'button_pressed': 'Claude',
            'actual_analysis_llm': 'Claude',
            'recommendation_result': 'Enhanced',
            'confidence': 0.95,
            'full_analysis_text': 'Claude分析では、Enhanced翻訳が最も丁寧で適切な表現です。',
        },
        {
            'activity_type': 'manual_test',
            'user_id': 'developer',
            'japanese_text': 'システムのテストを実行しています。',
            'button_pressed': 'ChatGPT',
            'actual_analysis_llm': 'ChatGPT',
            'recommendation_result': 'Gemini',
            'confidence': 0.82,
            'full_analysis_text': 'テスト用の分析結果です。Gemini翻訳を推奨します。',
            'error_occurred': False,
        },
        {
            'activity_type': 'normal_use',
            'user_id': 'developer',
            'japanese_text': 'ご質問がございましたら、お気軽にお声がけください。',
            'button_pressed': 'Gemini',
            'actual_analysis_llm': 'Gemini',
            'recommendation_result': 'Enhanced',
            'confidence': 0.91,
            'full_analysis_text': 'Enhanced翻訳が最も適切な表現です。',
            'error_occurred': False,
        }
    ]
    
    success_count = 0
    for i, data in enumerate(test_datasets, 1):
        try:
            # 基本データを補完
            data.update({
                'target_language': 'en',
                'language_pair': 'ja-en',
                'chatgpt_translation': f'ChatGPT translation {i}',
                'enhanced_translation': f'Enhanced translation {i}',
                'gemini_translation': f'Gemini translation {i}',
                'processing_duration': round(random.uniform(1.5, 4.0), 2),
                'ip_address': '127.0.0.1',
                'user_agent': 'Test Script',
                'notes': f'Test data insertion #{i}'
            })
            
            log_id = log_analysis_activity(data)
            if log_id > 0:
                print(f"✅ テストデータ {i} 挿入成功: ID={log_id}")
                success_count += 1
            else:
                print(f"❌ テストデータ {i} 挿入失敗")
                
        except Exception as e:
            print(f"❌ テストデータ {i} エラー: {e}")
    
    print(f"\n📊 挿入結果: {success_count}/{len(test_datasets)} 件成功")
    
    # 統計確認
    try:
        stats = activity_logger.get_activity_stats()
        print(f"\n📈 更新後統計:")
        print(f"  総活動数: {stats['basic']['total_activities']}")
        print(f"  今日の活動: {stats['basic']['today_activities']}")
        print(f"  エラー率: {stats['basic']['error_rate']}%")
        print(f"  LLM一致率: {stats['basic']['llm_match_rate']}%")
        
        return stats['basic']['total_activities'] > 0
        
    except Exception as e:
        print(f"❌ 統計取得エラー: {e}")
        return False

if __name__ == "__main__":
    success = insert_test_data()
    if success:
        print("\n🎯 テストデータ挿入完了")
        print("💡 ダッシュボードを更新して数値を確認してください")
        print("🔗 http://127.0.0.1:8080/admin/comprehensive_dashboard")
    else:
        print("\n❌ テストデータ挿入失敗")
        print("🔧 ActivityLogger の設定を確認してください")