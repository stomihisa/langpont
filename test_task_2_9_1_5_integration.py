#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 Task 2.9.1.5 統合テストスイート
=====================================
目的: 包括的行動追跡システムの緊急改善対応の
     全機能を統合的にテストする
"""

import os
import sys
import json
import sqlite3
import time
from datetime import datetime
import unittest
from unittest.mock import patch, MagicMock

# プロジェクトパスの追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 改善版モジュールのインポート
from gemini_recommendation_analyzer import GeminiRecommendationAnalyzer
from enhanced_satisfaction_estimator import (
    EnhancedSatisfactionEstimator,
    EnhancedBehaviorMetrics,
    OPTIMIZED_WEIGHTS
)
from satisfaction_estimator import SatisfactionEstimator


class TestTask291_5Integration(unittest.TestCase):
    """Task 2.9.1.5 統合テストクラス"""
    
    def setUp(self):
        """テスト環境のセットアップ"""
        self.test_db = "test_task_2_9_1_5.db"
        self.analyzer = GeminiRecommendationAnalyzer()
        self.enhanced_estimator = EnhancedSatisfactionEstimator(
            analytics_db_path=self.test_db
        )
        self.original_estimator = SatisfactionEstimator(
            analytics_db_path=self.test_db
        )
        
        # テスト用データベースの初期化
        self._setup_test_database()
    
    def tearDown(self):
        """テスト環境のクリーンアップ"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def _setup_test_database(self):
        """テスト用データベースのセットアップ"""
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()
            
            # analytics_eventsテーブル作成
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analytics_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    timestamp INTEGER NOT NULL,
                    session_id VARCHAR(50),
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    custom_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # テストデータの挿入
            test_session_id = "test_session_2915"
            base_time = int(time.time() * 1000)
            
            test_events = [
                # テキスト選択イベント（新規追加）
                {
                    'event_type': 'text_selection',
                    'timestamp': base_time - 180000,
                    'custom_data': {
                        'selected_text': 'This is a selected phrase',
                        'selection_length': 24,
                        'selection_start': 10,
                        'selection_end': 34
                    }
                },
                {
                    'event_type': 'text_selection',
                    'timestamp': base_time - 175000,
                    'custom_data': {
                        'selected_text': 'Another important paragraph selection that is quite long',
                        'selection_length': 55,
                        'selection_start': 100,
                        'selection_end': 155
                    }
                },
                # CTAクリックイベント（新規追加）
                {
                    'event_type': 'cta_click',
                    'timestamp': base_time - 170000,
                    'custom_data': {
                        'button_id': 'try_now_button',
                        'page_section': 'hero'
                    }
                },
                {
                    'event_type': 'cta_click',
                    'timestamp': base_time - 160000,
                    'custom_data': {
                        'button_id': 'learn_more_button',
                        'page_section': 'features'
                    }
                },
                # 既存の翻訳コピーイベント
                {
                    'event_type': 'translation_copy',
                    'timestamp': base_time - 150000,
                    'custom_data': {
                        'translation_type': 'enhanced',
                        'copy_method': 'button_click',
                        'text_length': 150,
                        'user_choice_vs_recommendation': 'followed_recommendation'
                    }
                },
                # ページ滞在時間イベント（新規追加）
                {
                    'event_type': 'time_on_page',
                    'timestamp': base_time - 140000,
                    'custom_data': {
                        'page_url': '/translate',
                        'time_spent': 120.5
                    }
                },
                # ページビュー
                {
                    'event_type': 'page_view',
                    'timestamp': base_time - 200000,
                    'custom_data': {
                        'page_title': 'Translation Test'
                    }
                },
                # スクロール深度
                {
                    'event_type': 'scroll_depth',
                    'timestamp': base_time - 130000,
                    'custom_data': {
                        'scroll_percentage': 85
                    }
                }
            ]
            
            for i, event in enumerate(test_events):
                event_id = f"test_event_{test_session_id}_{i}"
                cursor.execute('''
                    INSERT INTO analytics_events (
                        event_id, event_type, timestamp, session_id,
                        ip_address, user_agent, custom_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event_id,
                    event['event_type'],
                    event['timestamp'],
                    test_session_id,
                    '127.0.0.1',
                    'TestAgent/1.0',
                    json.dumps(event['custom_data'])
                ))
            
            conn.commit()
    
    def test_gemini_recommendation_extraction(self):
        """Gemini推奨抽出機能テスト"""
        print("\n🔍 Test 1: Gemini推奨抽出機能")
        
        test_cases = [
            {
                'text': "3つの翻訳を比較した結果、Enhanced翻訳が最も自然で適切です。",
                'expected': 'enhanced'
            },
            {
                'text': "総合的に判断すると、Gemini翻訳を推奨します。",
                'expected': 'gemini'
            },
            {
                'text': "ChatGPT: ★★★☆☆\nEnhanced: ★★★★★\nGemini: ★★★★☆",
                'expected': 'enhanced'
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            result = self.analyzer.extract_gemini_recommendation(test_case['text'])
            self.assertEqual(result, test_case['expected'], 
                           f"テストケース{i}で推奨抽出が失敗")
            print(f"  ✅ ケース{i}: {test_case['expected']}を正しく抽出")
    
    def test_recommendation_vs_choice_analysis(self):
        """推奨vs実選択分析テスト"""
        print("\n🔍 Test 2: 推奨vs実選択分析")
        
        # テストケース1: 推奨に従った場合
        analysis1 = self.analyzer.analyze_recommendation_vs_choice(
            recommended='enhanced',
            actual_choice='enhanced',
            session_context={'text_length': 200}
        )
        
        self.assertTrue(analysis1['followed_recommendation'])
        self.assertEqual(analysis1['divergence_type'], 'aligned')
        print("  ✅ 推奨に従った場合の分析: 正常")
        
        # テストケース2: 推奨から逸脱した場合
        analysis2 = self.analyzer.analyze_recommendation_vs_choice(
            recommended='enhanced',
            actual_choice='gemini',
            session_context={
                'text_length': 600,
                'has_technical_terms': True
            }
        )
        
        self.assertFalse(analysis2['followed_recommendation'])
        self.assertEqual(analysis2['divergence_type'], 'diverged')
        self.assertIn('long_text_preference', analysis2['potential_reasons'])
        print("  ✅ 推奨から逸脱した場合の分析: 正常")
    
    def test_enhanced_satisfaction_calculation(self):
        """改善版満足度計算テスト"""
        print("\n🔍 Test 3: 改善版満足度計算")
        
        # テストセッションでの満足度計算
        result = self.enhanced_estimator.calculate_satisfaction(
            session_id="test_session_2915",
            user_id="test_user"
        )
        
        self.assertNotIn('error', result)
        self.assertGreater(result['satisfaction_score'], 0)
        
        print(f"  📊 総合満足度: {result['satisfaction_score']}/100")
        print(f"  📊 コピー行動: {result['copy_behavior_score']}/100")
        print(f"  📊 テキスト操作: {result['text_interaction_score']}/100")
        print(f"  📊 セッション行動: {result['session_pattern_score']}/100")
        print(f"  📊 エンゲージメント: {result['engagement_score']}/100")
        
        # 重み設定の確認
        self.assertEqual(result['weights_used'], OPTIMIZED_WEIGHTS)
        print("  ✅ 最適化された重みが適用されています")
    
    def test_no_more_fixed_scores(self):
        """50点固定問題解決確認テスト"""
        print("\n🔍 Test 4: 50点固定問題の解決確認")
        
        # 異なるセッションデータでテスト
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()
            
            # セッション1: テキスト選択なし
            session1_id = "test_no_text_selection"
            cursor.execute('''
                INSERT INTO analytics_events (
                    event_id, event_type, timestamp, session_id,
                    ip_address, user_agent, custom_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                f"test_event_{session1_id}_1",
                'page_view',
                int(time.time() * 1000),
                session1_id,
                '127.0.0.1',
                'TestAgent/1.0',
                '{}'
            ))
            
            # セッション2: 多数のテキスト選択
            session2_id = "test_many_text_selections"
            base_time = int(time.time() * 1000)
            for i in range(5):
                cursor.execute('''
                    INSERT INTO analytics_events (
                        event_id, event_type, timestamp, session_id,
                        ip_address, user_agent, custom_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    f"test_event_{session2_id}_{i}",
                    'text_selection',
                    base_time - (i * 1000),
                    session2_id,
                    '127.0.0.1',
                    'TestAgent/1.0',
                    json.dumps({
                        'selected_text': f'Selection {i}',
                        'selection_length': 20 + i * 10
                    })
                ))
            
            conn.commit()
        
        # 両セッションで満足度計算
        result1 = self.enhanced_estimator.calculate_satisfaction(session1_id)
        result2 = self.enhanced_estimator.calculate_satisfaction(session2_id)
        
        # テキスト操作スコアが異なることを確認
        self.assertNotEqual(result1['text_interaction_score'], 
                          result2['text_interaction_score'])
        self.assertNotEqual(result1['text_interaction_score'], 50.0)
        self.assertNotEqual(result2['text_interaction_score'], 50.0)
        
        print(f"  ✅ セッション1のテキスト操作スコア: {result1['text_interaction_score']}")
        print(f"  ✅ セッション2のテキスト操作スコア: {result2['text_interaction_score']}")
        print("  ✅ 50点固定問題は解決されました！")
    
    def test_individual_preference_patterns(self):
        """真の個人化パターン分析テスト"""
        print("\n🔍 Test 5: 真の個人化パターン分析")
        
        # テストユーザーの選択履歴データ
        user_data = [
            {
                'actual_choice': 'gemini',
                'followed_recommendation': False,
                'potential_reasons': ['prefer_modern_style'],
                'context_type': 'technical'
            },
            {
                'actual_choice': 'gemini',
                'followed_recommendation': True,
                'context_type': 'technical'
            },
            {
                'actual_choice': 'enhanced',
                'followed_recommendation': False,
                'potential_reasons': ['prefer_contextual_enhancement'],
                'context_type': 'casual'
            },
            {
                'actual_choice': 'gemini',
                'followed_recommendation': True,
                'context_type': 'business'
            },
            {
                'actual_choice': 'gemini',
                'followed_recommendation': True,
                'context_type': 'technical'
            }
        ]
        
        patterns = self.analyzer.detect_preference_patterns(user_data)
        
        # エンジン選好の確認
        self.assertEqual(patterns['engine_preferences']['gemini'], 4)
        self.assertEqual(patterns['engine_preferences']['enhanced'], 1)
        
        # 個人化インサイトの確認
        self.assertGreater(len(patterns['personalization_insights']), 0)
        
        print("  📊 エンジン選好:")
        for engine, count in patterns['engine_preferences'].items():
            percentage = (count / len(user_data)) * 100
            print(f"    - {engine}: {count}回 ({percentage:.0f}%)")
        
        print("  💡 個人化インサイト:")
        for insight in patterns['personalization_insights']:
            print(f"    - {insight}")
        
        print("  ✅ 真の個人化パターンが検出されました")
    
    def test_system_integration(self):
        """全システム統合テスト"""
        print("\n🔍 Test 6: 全システム統合動作確認")
        
        # 1. Gemini分析テキストから推奨抽出
        gemini_analysis = "詳細な分析の結果、Enhanced翻訳が最も文脈に適しています。"
        recommendation = self.analyzer.extract_gemini_recommendation(gemini_analysis)
        self.assertEqual(recommendation, 'enhanced')
        print("  ✅ Step 1: Gemini推奨抽出完了")
        
        # 2. ユーザーの実選択と比較分析
        actual_choice = 'gemini'  # ユーザーは推奨と異なる選択
        analysis = self.analyzer.analyze_recommendation_vs_choice(
            recommended=recommendation,
            actual_choice=actual_choice
        )
        self.assertFalse(analysis['followed_recommendation'])
        print("  ✅ Step 2: 推奨vs実選択分析完了")
        
        # 3. 改善版満足度計算
        satisfaction = self.enhanced_estimator.calculate_satisfaction(
            session_id="test_session_2915"
        )
        self.assertGreater(satisfaction['satisfaction_score'], 0)
        print(f"  ✅ Step 3: 満足度計算完了 ({satisfaction['satisfaction_score']}/100)")
        
        # 4. 改善インサイト生成
        insights = self.enhanced_estimator.generate_improvement_insights(
            "test_session_2915"
        )
        print("  ✅ Step 4: 改善インサイト生成完了")
        
        print("\n🎉 全システムが正常に統合動作しています！")


def run_comprehensive_tests():
    """包括的テストの実行"""
    print("=" * 60)
    print("🧪 Task 2.9.1.5 統合テストスイート実行")
    print("=" * 60)
    
    # テストスイートの作成と実行
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTask291_5Integration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ 全テスト合格！Task 2.9.1.5の実装は完全です。")
        print("🚀 Task 2.9.2への移行準備が整いました。")
    else:
        print("\n❌ テスト失敗 - 修正が必要です。")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)