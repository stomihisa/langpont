#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Task 2.9.1: 満足度自動推定システム統合テスト
=============================================

満足度推定エンジンと翻訳履歴システムの統合動作を検証します。
"""

import os
import sys
import time
import json
import sqlite3
from datetime import datetime

# プロジェクトパスの追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from satisfaction_estimator import SatisfactionEstimator, BehaviorMetrics
from translation_history import TranslationHistoryManager

def setup_test_environment():
    """テスト環境のセットアップ"""
    print("🔧 テスト環境をセットアップしています...")
    
    # テスト用データベースパス
    test_analytics_db = "test_analytics.db"
    test_history_db = "test_translation_history.db"
    
    # 既存のテストDBを削除
    for db_file in [test_analytics_db, test_history_db]:
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"  - 既存のテストDB削除: {db_file}")
    
    return test_analytics_db, test_history_db

def create_test_analytics_data(analytics_db: str, session_id: str):
    """テスト用のアナリティクスデータを作成"""
    print("\n📊 テスト用アナリティクスデータを作成しています...")
    
    with sqlite3.connect(analytics_db) as conn:
        cursor = conn.cursor()
        
        # analytics_eventsテーブルを作成
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                timestamp INTEGER NOT NULL,
                page_url TEXT,
                action VARCHAR(100),
                language VARCHAR(10),
                session_id VARCHAR(50),
                user_id INTEGER,
                ip_address VARCHAR(45),
                user_agent TEXT,
                custom_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # テストイベントを挿入
        base_time = int(time.time() * 1000)
        
        test_events = [
            # ページビュー
            {
                'event_type': 'page_view',
                'timestamp': base_time - 180000,  # 3分前
                'custom_data': {
                    'page_title': 'LangPont Translation',
                    'page_path': '/',
                    'viewport_size': '1920x1080'
                }
            },
            # 翻訳リクエスト
            {
                'event_type': 'translation_request',
                'timestamp': base_time - 150000,  # 2.5分前
                'custom_data': {
                    'language_pair': 'ja-en',
                    'input_text_length': 50,
                    'has_context': True
                }
            },
            # スクロール深度
            {
                'event_type': 'scroll_depth',
                'timestamp': base_time - 120000,  # 2分前
                'custom_data': {
                    'scroll_percentage': 75,
                    'milestone': 75,
                    'time_to_scroll': 30000
                }
            },
            # 翻訳コピー（ボタンクリック）
            {
                'event_type': 'translation_copy',
                'timestamp': base_time - 90000,  # 1.5分前
                'custom_data': {
                    'translation_type': 'enhanced',
                    'copy_method': 'button_click',
                    'text_length': 55,
                    'user_choice_vs_recommendation': 'followed_recommendation'
                }
            },
            # 翻訳コピー（キーボードショートカット）
            {
                'event_type': 'translation_copy',
                'timestamp': base_time - 60000,  # 1分前
                'custom_data': {
                    'translation_type': 'gemini',
                    'copy_method': 'keyboard_shortcut',
                    'text_length': 60,
                    'user_choice_vs_recommendation': 'diverged_from_recommendation'
                }
            },
            # 翻訳完了
            {
                'event_type': 'translation_completion',
                'timestamp': base_time - 30000,  # 30秒前
                'custom_data': {
                    'processing_time': 2500,
                    'chatgpt_length': 55,
                    'enhanced_length': 58,
                    'gemini_length': 60,
                    'gemini_recommendation': 'enhanced'
                }
            }
        ]
        
        for i, event in enumerate(test_events):
            event_id = f"test_{session_id}_{i}_{int(time.time() * 1000)}"
            cursor.execute('''
                INSERT INTO analytics_events (
                    event_id, event_type, timestamp, session_id,
                    ip_address, user_agent, custom_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_id,
                event['event_type'],
                event['timestamp'],
                session_id,
                '127.0.0.1',
                'TestAgent/1.0',
                json.dumps(event['custom_data'])
            ))
        
        conn.commit()
        print(f"  ✅ {len(test_events)}個のテストイベントを作成しました")

def test_satisfaction_calculation():
    """満足度計算のテスト"""
    print("\n🧪 満足度計算テストを実行しています...")
    
    # テスト環境のセットアップ
    analytics_db, history_db = setup_test_environment()
    
    # テストセッションID
    test_session_id = f"test_session_{int(time.time())}"
    test_user_id = "test_user_123"
    
    # アナリティクスデータの作成
    create_test_analytics_data(analytics_db, test_session_id)
    
    # 満足度推定エンジンの初期化
    estimator = SatisfactionEstimator(analytics_db_path=analytics_db)
    
    # 満足度計算
    print("\n📈 満足度を計算しています...")
    result = estimator.calculate_satisfaction(
        session_id=test_session_id,
        user_id=test_user_id
    )
    
    # 結果表示
    print("\n✨ 満足度計算結果:")
    print(f"  - セッションID: {result['session_id']}")
    print(f"  - 総合満足度スコア: {result['satisfaction_score']}/100")
    print(f"  - コピー行動スコア: {result['copy_behavior_score']}")
    print(f"  - テキスト操作スコア: {result['text_interaction_score']}")
    print(f"  - セッション行動スコア: {result['session_pattern_score']}")
    print(f"  - エンゲージメントスコア: {result['engagement_score']}")
    
    # 行動メトリクスの詳細
    metrics = result['behavior_metrics']
    print("\n📊 行動メトリクスの詳細:")
    print(f"  - コピー回数: {metrics['copy_count']}")
    print(f"  - コピー方法: {metrics['copy_methods']}")
    print(f"  - 翻訳タイプ別コピー: {metrics['translation_types_copied']}")
    print(f"  - セッション継続時間: {metrics['session_duration']:.1f}秒")
    print(f"  - 最大スクロール深度: {metrics['scroll_depth_max']}%")
    print(f"  - Gemini推奨に従った: {metrics['gemini_recommendation_followed']}回")
    print(f"  - Gemini推奨から逸脱: {metrics['gemini_recommendation_diverged']}回")
    
    # クリーンアップ
    os.remove(analytics_db)
    print("\n🧹 テストデータベースをクリーンアップしました")
    
    return result

def test_translation_history_integration():
    """翻訳履歴システムとの統合テスト"""
    print("\n🔗 翻訳履歴システムとの統合テストを実行しています...")
    
    # テスト環境のセットアップ
    analytics_db, history_db = setup_test_environment()
    
    # テストデータ
    test_session_id = f"test_session_{int(time.time())}"
    test_user_id = 1
    
    # アナリティクスデータの作成
    create_test_analytics_data(analytics_db, test_session_id)
    
    # 満足度推定エンジンを使用して翻訳履歴マネージャーを初期化
    # （実際の環境ではデフォルトのパスを使用）
    os.environ['ANALYTICS_DB_PATH'] = analytics_db  # テスト用にパスを設定
    
    # 翻訳履歴マネージャーの初期化（カスタムDBパス）
    history_manager = TranslationHistoryManager(db_path=history_db)
    history_manager.satisfaction_estimator = SatisfactionEstimator(analytics_db_path=analytics_db)
    
    # テスト翻訳データの保存
    print("\n💾 テスト翻訳データを保存しています...")
    translations = {
        'chatgpt': 'Hello, how are you?',
        'enhanced': 'Hi there, how are you doing?',
        'gemini': 'Hello, how are you feeling?'
    }
    
    context_data = {
        'partner_message': 'Friend conversation',
        'context_info': 'Casual greeting',
        'ip_address': '127.0.0.1',
        'user_agent': 'TestAgent/1.0',
        'processing_time': 2.5
    }
    
    # 翻訳を保存（満足度計算も自動実行される）
    translation_uuid = history_manager.save_complete_translation(
        user_id=test_user_id,
        session_id=test_session_id,
        source_text='こんにちは、元気ですか？',
        source_language='ja',
        target_language='en',
        translations=translations,
        context_data=context_data
    )
    
    print(f"  ✅ 翻訳データ保存完了: UUID={translation_uuid}")
    
    # 満足度データの取得
    print("\n📊 満足度データを取得しています...")
    satisfaction_data = history_manager.get_satisfaction_data(
        session_id=test_session_id,
        user_id=test_user_id
    )
    
    if satisfaction_data:
        print(f"  ✅ 満足度データ取得成功:")
        print(f"     - 満足度スコア: {satisfaction_data['satisfaction_score']}/100")
        print(f"     - セッションID: {satisfaction_data.get('session_id', 'N/A')}")
        print(f"     - 作成日時: {satisfaction_data.get('created_at', 'N/A')}")
    else:
        print("  ❌ 満足度データが見つかりません")
    
    # 満足度分析データの取得
    print("\n📈 満足度分析データを取得しています...")
    analytics = history_manager.get_satisfaction_analytics(
        user_id=test_user_id,
        days=1
    )
    
    if analytics['available']:
        print(f"  ✅ 満足度分析データ取得成功:")
        print(f"     - 平均満足度: {analytics['average_satisfaction']}")
        if 'trends' in analytics and 'overall_stats' in analytics['trends']:
            stats = analytics['trends']['overall_stats']
            print(f"     - 総セッション数: {stats['total_sessions']}")
            print(f"     - コンポーネントスコア:")
            for component, score in stats['component_scores'].items():
                print(f"       • {component}: {score}")
    else:
        print(f"  ❌ 満足度分析データ取得失敗: {analytics.get('message', 'Unknown error')}")
    
    # クリーンアップ
    os.remove(analytics_db)
    os.remove(history_db)
    print("\n🧹 テストデータベースをクリーンアップしました")

def test_performance():
    """パフォーマンステスト"""
    print("\n⚡ パフォーマンステストを実行しています...")
    
    analytics_db = "test_perf_analytics.db"
    
    # 大量のテストデータを作成
    estimator = SatisfactionEstimator(analytics_db_path=analytics_db)
    
    with sqlite3.connect(analytics_db) as conn:
        cursor = conn.cursor()
        
        # テーブル作成（estimatorの初期化で作成済みだが念のため）
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
    
    # 100セッション分のデータを作成
    print("  📝 100セッション分のテストデータを作成中...")
    start_time = time.time()
    
    for i in range(100):
        session_id = f"perf_session_{i}"
        create_test_analytics_data(analytics_db, session_id)
    
    data_creation_time = time.time() - start_time
    print(f"  ✅ データ作成完了: {data_creation_time:.2f}秒")
    
    # 満足度計算のパフォーマンス測定
    print("\n  ⏱️ 満足度計算パフォーマンスを測定中...")
    calc_times = []
    
    for i in range(10):  # 10セッション分を計算
        session_id = f"perf_session_{i}"
        start_time = time.time()
        
        result = estimator.calculate_satisfaction(
            session_id=session_id,
            user_id=f"perf_user_{i}"
        )
        
        calc_time = time.time() - start_time
        calc_times.append(calc_time)
    
    avg_calc_time = sum(calc_times) / len(calc_times)
    print(f"  ✅ 平均計算時間: {avg_calc_time * 1000:.2f}ミリ秒/セッション")
    
    # トレンド分析のパフォーマンス測定
    print("\n  ⏱️ トレンド分析パフォーマンスを測定中...")
    start_time = time.time()
    
    trends = estimator.analyze_satisfaction_trends()
    
    trend_time = time.time() - start_time
    print(f"  ✅ トレンド分析時間: {trend_time:.2f}秒")
    print(f"     - 分析対象セッション数: {trends['overall_stats']['total_sessions']}")
    
    # クリーンアップ
    os.remove(analytics_db)
    print("\n🧹 テストデータベースをクリーンアップしました")

def main():
    """メインテスト実行"""
    print("=" * 60)
    print("🎯 Task 2.9.1: 満足度自動推定システム統合テスト")
    print("=" * 60)
    
    try:
        # 1. 満足度計算テスト
        test_satisfaction_calculation()
        
        # 2. 翻訳履歴統合テスト
        test_translation_history_integration()
        
        # 3. パフォーマンステスト
        test_performance()
        
        print("\n✅ すべてのテストが正常に完了しました！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ テストエラー: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()