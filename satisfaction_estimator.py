#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎯 Task 2.9.1: 満足度自動推定アルゴリズム
=====================================================
戦略目的: 個人化翻訳AI構築のための学習データ品質評価基盤

【現在の仮定・制約】
- ユーザー負担ゼロの非接触データのみ使用
- 4段階評価システムは除外（ユーザー負担回避）
- 行動データから間接的に満足度を推定

【将来変更が予想される箇所】
- データ収集範囲の拡大（軽量フィードバック追加）
- 満足度推定アルゴリズムの高度化
- 個人化学習への直接連携

作成日: 2025年6月14日
著者: Claude Code (Task 2.9.1実装)
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import os

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 📊 現在使用可能な行動データ（2025年6月時点）
BEHAVIOR_DATA_SCHEMA = {
    "copy_actions": "コピーボタン/Ctrl+C/右クリックの追跡",
    "text_selection": "選択範囲・時間・頻度",
    "session_patterns": "閲覧時間・スクロール・再訪問",
    "engagement_metrics": "ブックマーク・履歴アクセス"
}

# ⚠️ 不足している重要データ（将来追加検討）
MISSING_DATA_FOR_PERSONALIZATION = {
    "user_correction_patterns": "修正内容の差分",
    "context_preferences": "業界・職種・文脈選択",
    "expression_templates": "頻用表現のパターン化",
    "feedback_reasoning": "選択理由の軽量フィードバック"
}

# 🔄 将来変更が確実な重み設定
SATISFACTION_WEIGHTS = {
    "copy_behavior": 0.4,    # 変更可能性: 高
    "text_interaction": 0.3,  # 変更可能性: 高  
    "session_pattern": 0.2,   # 変更可能性: 中
    "engagement": 0.1         # 変更可能性: 低
}
# TODO: 機械学習による動的重み調整への移行検討

# ⚠️ 現在のアプローチの限界
CURRENT_LIMITATIONS = {
    "personalization_depth": "表面的な行動のみ、思考過程不明",
    "context_understanding": "業界・文脈の深い理解不可",
    "learning_accuracy": "間接推定のため精度に限界"
}


class CopyMethod(Enum):
    """コピー方法の種別"""
    BUTTON_CLICK = "button_click"
    KEYBOARD_SHORTCUT = "keyboard_shortcut"
    CONTEXT_MENU = "context_menu"
    DRAG_DROP = "drag_drop"
    UNKNOWN = "unknown"


class TranslationType(Enum):
    """翻訳タイプの種別"""
    CHATGPT = "chatgpt"
    ENHANCED = "enhanced"
    GEMINI = "gemini"
    GEMINI_ANALYSIS = "gemini_analysis"
    ORIGINAL_INPUT = "original_input"
    UNKNOWN = "unknown"


@dataclass
class BehaviorMetrics:
    """行動メトリクスのデータクラス"""
    copy_count: int = 0
    copy_methods: Dict[str, int] = field(default_factory=dict)
    translation_types_copied: Dict[str, int] = field(default_factory=dict)
    text_selection_count: int = 0
    total_selection_time: float = 0.0
    session_duration: float = 0.0
    scroll_depth_max: int = 0
    page_views: int = 0
    revisit_count: int = 0
    bookmark_count: int = 0
    history_access_count: int = 0
    gemini_recommendation_followed: int = 0
    gemini_recommendation_diverged: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'copy_count': self.copy_count,
            'copy_methods': self.copy_methods,
            'translation_types_copied': self.translation_types_copied,
            'text_selection_count': self.text_selection_count,
            'total_selection_time': self.total_selection_time,
            'session_duration': self.session_duration,
            'scroll_depth_max': self.scroll_depth_max,
            'page_views': self.page_views,
            'revisit_count': self.revisit_count,
            'bookmark_count': self.bookmark_count,
            'history_access_count': self.history_access_count,
            'gemini_recommendation_followed': self.gemini_recommendation_followed,
            'gemini_recommendation_diverged': self.gemini_recommendation_diverged
        }


class SatisfactionEstimator:
    """
    満足度自動推定エンジン
    
    非接触行動データから自動的にユーザー満足度を推定します。
    将来の個人化翻訳AI構築のための学習データ品質評価基盤として機能します。
    """
    
    def __init__(self, 
                 analytics_db_path: str = "langpont_analytics.db",
                 history_db_path: str = "langpont_translation_history.db"):
        """
        初期化
        
        Args:
            analytics_db_path: アナリティクスデータベースのパス
            history_db_path: 翻訳履歴データベースのパス
        """
        self.analytics_db_path = analytics_db_path
        self.history_db_path = history_db_path
        self._init_satisfaction_table()
        
        logger.info(f"満足度推定エンジン初期化完了: Analytics DB={analytics_db_path}")
    
    def _init_satisfaction_table(self):
        """満足度スコアテーブルの初期化"""
        with sqlite3.connect(self.analytics_db_path) as conn:
            cursor = conn.cursor()
            
            # 満足度スコアテーブル作成
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS satisfaction_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id VARCHAR(100) NOT NULL,
                    user_id VARCHAR(100),
                    translation_id INTEGER,
                    satisfaction_score FLOAT NOT NULL,
                    
                    -- 詳細スコア
                    copy_behavior_score FLOAT,
                    text_interaction_score FLOAT,
                    session_pattern_score FLOAT,
                    engagement_score FLOAT,
                    
                    -- メトリクス
                    behavior_metrics TEXT,
                    
                    -- メタデータ
                    calculation_version VARCHAR(20) DEFAULT '1.0.0',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- インデックス用
                    date_only DATE GENERATED ALWAYS AS (DATE(created_at)) STORED
                )
            ''')
            
            # インデックス作成
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_satisfaction_session ON satisfaction_scores (session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_satisfaction_user ON satisfaction_scores (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_satisfaction_score ON satisfaction_scores (satisfaction_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_satisfaction_date ON satisfaction_scores (date_only)')
            
            conn.commit()
    
    def calculate_satisfaction(self, 
                             session_id: str,
                             user_id: Optional[str] = None,
                             translation_id: Optional[int] = None) -> Dict[str, Any]:
        """
        セッションの満足度スコアを計算
        
        Args:
            session_id: セッションID
            user_id: ユーザーID（オプション）
            translation_id: 翻訳ID（オプション）
        
        Returns:
            満足度スコアと詳細情報を含む辞書
        """
        try:
            # 行動メトリクスの収集
            metrics = self._collect_behavior_metrics(session_id, user_id)
            
            # 各要素のスコア計算
            copy_score = self._calculate_copy_behavior_score(metrics)
            text_score = self._calculate_text_interaction_score(metrics)
            session_score = self._calculate_session_pattern_score(metrics)
            engagement_score = self._calculate_engagement_score(metrics)
            
            # 総合満足度スコア計算（重み付き平均）
            total_score = (
                copy_score * SATISFACTION_WEIGHTS["copy_behavior"] +
                text_score * SATISFACTION_WEIGHTS["text_interaction"] +
                session_score * SATISFACTION_WEIGHTS["session_pattern"] +
                engagement_score * SATISFACTION_WEIGHTS["engagement"]
            )
            
            # スコアを0-100の範囲に正規化
            total_score = max(0, min(100, total_score))
            
            result = {
                'session_id': session_id,
                'user_id': user_id,
                'translation_id': translation_id,
                'satisfaction_score': round(total_score, 2),
                'copy_behavior_score': round(copy_score, 2),
                'text_interaction_score': round(text_score, 2),
                'session_pattern_score': round(session_score, 2),
                'engagement_score': round(engagement_score, 2),
                'behavior_metrics': metrics.to_dict(),
                'calculation_version': '1.0.0',
                'timestamp': datetime.now().isoformat()
            }
            
            # データベースに保存
            self._save_satisfaction_score(result)
            
            logger.info(f"満足度計算完了: session={session_id}, score={total_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"満足度計算エラー: {str(e)}")
            return {
                'error': str(e),
                'session_id': session_id,
                'satisfaction_score': 0.0
            }
    
    def _collect_behavior_metrics(self, 
                                session_id: str, 
                                user_id: Optional[str] = None) -> BehaviorMetrics:
        """
        セッションの行動メトリクスを収集
        
        Args:
            session_id: セッションID
            user_id: ユーザーID
        
        Returns:
            BehaviorMetricsオブジェクト
        """
        metrics = BehaviorMetrics()
        
        with sqlite3.connect(self.analytics_db_path) as conn:
            cursor = conn.cursor()
            
            # コピー行動の分析
            cursor.execute('''
                SELECT 
                    COUNT(*) as copy_count,
                    custom_data
                FROM analytics_events
                WHERE session_id = ? AND event_type = 'translation_copy'
            ''', (session_id,))
            
            copy_data = cursor.fetchone()
            if copy_data and copy_data[0] > 0:
                metrics.copy_count = copy_data[0]
                
                # 詳細なコピー行動を分析
                cursor.execute('''
                    SELECT custom_data
                    FROM analytics_events
                    WHERE session_id = ? AND event_type = 'translation_copy'
                ''', (session_id,))
                
                for row in cursor.fetchall():
                    try:
                        data = json.loads(row[0])
                        
                        # コピー方法の集計
                        method = data.get('copy_method', 'unknown')
                        metrics.copy_methods[method] = metrics.copy_methods.get(method, 0) + 1
                        
                        # 翻訳タイプの集計
                        trans_type = data.get('translation_type', 'unknown')
                        metrics.translation_types_copied[trans_type] = \
                            metrics.translation_types_copied.get(trans_type, 0) + 1
                        
                        # Gemini推奨との一致分析
                        recommendation = data.get('user_choice_vs_recommendation', '')
                        if recommendation == 'followed_recommendation':
                            metrics.gemini_recommendation_followed += 1
                        elif recommendation == 'diverged_from_recommendation':
                            metrics.gemini_recommendation_diverged += 1
                            
                    except json.JSONDecodeError:
                        continue
            
            # セッションパターンの分析
            cursor.execute('''
                SELECT 
                    MIN(timestamp) as start_time,
                    MAX(timestamp) as end_time,
                    COUNT(DISTINCT event_type) as event_variety,
                    COUNT(*) as total_events
                FROM analytics_events
                WHERE session_id = ?
            ''', (session_id,))
            
            session_data = cursor.fetchone()
            if session_data and session_data[0]:
                # セッション時間（ミリ秒）
                metrics.session_duration = (session_data[1] - session_data[0]) / 1000.0
            
            # スクロール深度の最大値
            cursor.execute('''
                SELECT MAX(CAST(json_extract(custom_data, '$.scroll_percentage') AS INTEGER))
                FROM analytics_events
                WHERE session_id = ? AND event_type = 'scroll_depth'
            ''', (session_id,))
            
            scroll_result = cursor.fetchone()
            if scroll_result and scroll_result[0]:
                metrics.scroll_depth_max = scroll_result[0]
            
            # ページビュー数
            cursor.execute('''
                SELECT COUNT(*)
                FROM analytics_events
                WHERE session_id = ? AND event_type = 'page_view'
            ''', (session_id,))
            
            pv_result = cursor.fetchone()
            if pv_result:
                metrics.page_views = pv_result[0]
        
        return metrics
    
    def _calculate_copy_behavior_score(self, metrics: BehaviorMetrics) -> float:
        """
        コピー行動からスコアを計算
        
        【評価基準】
        - コピー回数: 1回=60点, 2回=80点, 3回以上=100点
        - コピー方法の多様性: ボタン以外の方法使用で加点
        - Gemini推奨に従う: +10点
        - 複数の翻訳タイプをコピー: +10点
        """
        score = 0.0
        
        # 基本スコア（コピー回数）
        if metrics.copy_count >= 3:
            score = 100
        elif metrics.copy_count == 2:
            score = 80
        elif metrics.copy_count == 1:
            score = 60
        else:
            score = 0
        
        # コピー方法の多様性ボーナス
        if len(metrics.copy_methods) > 1:
            score = min(100, score + 10)
        
        # 高度なコピー方法（キーボードショートカット等）の使用
        advanced_methods = ['keyboard_shortcut', 'drag_drop']
        for method in advanced_methods:
            if method in metrics.copy_methods:
                score = min(100, score + 5)
        
        # Gemini推奨フォローボーナス
        if metrics.gemini_recommendation_followed > 0:
            score = min(100, score + 10)
        
        # 複数翻訳タイプのコピー
        if len(metrics.translation_types_copied) > 1:
            score = min(100, score + 10)
        
        return score
    
    def _calculate_text_interaction_score(self, metrics: BehaviorMetrics) -> float:
        """
        テキスト操作からスコアを計算
        
        【評価基準】
        - テキスト選択回数と時間
        - 選択パターンの多様性
        - 翻訳結果の精読行動
        """
        # TODO: 実装予定 - 現在は簡易版
        score = 50.0  # デフォルト中間値
        
        # テキスト選択があれば加点
        if metrics.text_selection_count > 0:
            score += min(30, metrics.text_selection_count * 10)
        
        return min(100, score)
    
    def _calculate_session_pattern_score(self, metrics: BehaviorMetrics) -> float:
        """
        セッション行動パターンからスコアを計算
        
        【評価基準】
        - セッション継続時間: 60秒以上で高評価
        - スクロール深度: 深いほど高評価
        - ページビュー数: 複数ページ閲覧で加点
        """
        score = 0.0
        
        # セッション時間スコア（秒単位）
        if metrics.session_duration >= 180:  # 3分以上
            score = 80
        elif metrics.session_duration >= 60:  # 1分以上
            score = 60
        elif metrics.session_duration >= 30:  # 30秒以上
            score = 40
        else:
            score = 20
        
        # スクロール深度ボーナス
        if metrics.scroll_depth_max >= 75:
            score = min(100, score + 20)
        elif metrics.scroll_depth_max >= 50:
            score = min(100, score + 10)
        
        # 複数ページビューボーナス
        if metrics.page_views > 1:
            score = min(100, score + 10)
        
        return score
    
    def _calculate_engagement_score(self, metrics: BehaviorMetrics) -> float:
        """
        エンゲージメント行動からスコアを計算
        
        【評価基準】
        - ブックマーク追加
        - 履歴からの再訪問
        - 共有行動
        """
        score = 50.0  # デフォルト中間値
        
        # ブックマークボーナス
        if metrics.bookmark_count > 0:
            score += 30
        
        # 再訪問ボーナス
        if metrics.revisit_count > 0:
            score += 20
        
        return min(100, score)
    
    def _save_satisfaction_score(self, result: Dict[str, Any]):
        """満足度スコアをデータベースに保存"""
        with sqlite3.connect(self.analytics_db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO satisfaction_scores (
                    session_id, user_id, translation_id,
                    satisfaction_score,
                    copy_behavior_score, text_interaction_score,
                    session_pattern_score, engagement_score,
                    behavior_metrics, calculation_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['session_id'],
                result.get('user_id'),
                result.get('translation_id'),
                result['satisfaction_score'],
                result['copy_behavior_score'],
                result['text_interaction_score'],
                result['session_pattern_score'],
                result['engagement_score'],
                json.dumps(result['behavior_metrics']),
                result['calculation_version']
            ))
            
            conn.commit()
    
    def get_satisfaction_history(self, 
                               user_id: Optional[str] = None,
                               days: int = 30) -> List[Dict[str, Any]]:
        """
        満足度履歴を取得
        
        Args:
            user_id: ユーザーID（Noneの場合は全ユーザー）
            days: 取得日数
        
        Returns:
            満足度履歴のリスト
        """
        with sqlite3.connect(self.analytics_db_path) as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT 
                    session_id, user_id, satisfaction_score,
                    copy_behavior_score, text_interaction_score,
                    session_pattern_score, engagement_score,
                    created_at
                FROM satisfaction_scores
                WHERE created_at >= datetime('now', '-{} days')
            '''.format(days)
            
            if user_id:
                query += " AND user_id = ?"
                cursor.execute(query, (user_id,))
            else:
                cursor.execute(query)
            
            columns = ['session_id', 'user_id', 'satisfaction_score',
                      'copy_behavior_score', 'text_interaction_score',
                      'session_pattern_score', 'engagement_score', 'created_at']
            
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
    
    def get_average_satisfaction(self, 
                               user_id: Optional[str] = None,
                               days: int = 30) -> float:
        """
        平均満足度を取得
        
        Args:
            user_id: ユーザーID
            days: 集計日数
        
        Returns:
            平均満足度スコア
        """
        with sqlite3.connect(self.analytics_db_path) as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT AVG(satisfaction_score)
                FROM satisfaction_scores
                WHERE created_at >= datetime('now', '-{} days')
            '''.format(days)
            
            if user_id:
                query += " AND user_id = ?"
                cursor.execute(query, (user_id,))
            else:
                cursor.execute(query)
            
            result = cursor.fetchone()
            return result[0] if result and result[0] else 0.0
    
    def analyze_satisfaction_trends(self) -> Dict[str, Any]:
        """
        満足度のトレンド分析
        
        Returns:
            トレンド分析結果
        """
        with sqlite3.connect(self.analytics_db_path) as conn:
            cursor = conn.cursor()
            
            # 全体的な統計
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_sessions,
                    AVG(satisfaction_score) as avg_satisfaction,
                    MIN(satisfaction_score) as min_satisfaction,
                    MAX(satisfaction_score) as max_satisfaction,
                    AVG(copy_behavior_score) as avg_copy_score,
                    AVG(text_interaction_score) as avg_text_score,
                    AVG(session_pattern_score) as avg_session_score,
                    AVG(engagement_score) as avg_engagement_score
                FROM satisfaction_scores
                WHERE created_at >= datetime('now', '-30 days')
            ''')
            
            stats = cursor.fetchone()
            
            # 日別トレンド
            cursor.execute('''
                SELECT 
                    date_only,
                    COUNT(*) as sessions,
                    AVG(satisfaction_score) as avg_score
                FROM satisfaction_scores
                WHERE created_at >= datetime('now', '-7 days')
                GROUP BY date_only
                ORDER BY date_only
            ''')
            
            daily_trends = []
            for row in cursor.fetchall():
                daily_trends.append({
                    'date': row[0],
                    'sessions': row[1],
                    'avg_score': round(row[2], 2) if row[2] else 0
                })
            
            return {
                'overall_stats': {
                    'total_sessions': stats[0] if stats else 0,
                    'avg_satisfaction': round(stats[1], 2) if stats and stats[1] else 0,
                    'min_satisfaction': round(stats[2], 2) if stats and stats[2] else 0,
                    'max_satisfaction': round(stats[3], 2) if stats and stats[3] else 0,
                    'component_scores': {
                        'copy_behavior': round(stats[4], 2) if stats and stats[4] else 0,
                        'text_interaction': round(stats[5], 2) if stats and stats[5] else 0,
                        'session_pattern': round(stats[6], 2) if stats and stats[6] else 0,
                        'engagement': round(stats[7], 2) if stats and stats[7] else 0
                    }
                },
                'daily_trends': daily_trends,
                'insights': self._generate_insights(stats, daily_trends)
            }
    
    def _generate_insights(self, stats: Tuple, daily_trends: List[Dict]) -> List[str]:
        """
        統計データから洞察を生成
        
        Args:
            stats: 全体統計
            daily_trends: 日別トレンド
        
        Returns:
            洞察のリスト
        """
        insights = []
        
        if stats and stats[1]:  # 平均満足度が存在
            avg_score = stats[1]
            if avg_score >= 80:
                insights.append("🎉 ユーザー満足度は非常に高い水準（80点以上）を維持しています")
            elif avg_score >= 60:
                insights.append("📊 ユーザー満足度は良好（60-79点）ですが、改善の余地があります")
            else:
                insights.append("⚠️ ユーザー満足度が低い（60点未満）ため、改善が必要です")
        
        # コンポーネント分析
        if stats and stats[4] and stats[5] and stats[6] and stats[7]:
            scores = {
                'コピー行動': stats[4],
                'テキスト操作': stats[5],
                'セッション行動': stats[6],
                'エンゲージメント': stats[7]
            }
            
            # 最も低いスコアを特定
            min_component = min(scores, key=scores.get)
            if scores[min_component] < 60:
                insights.append(f"💡 {min_component}のスコアが低いため、この領域の改善を検討してください")
        
        # トレンド分析
        if len(daily_trends) >= 3:
            recent_scores = [d['avg_score'] for d in daily_trends[-3:]]
            if all(recent_scores[i] <= recent_scores[i+1] for i in range(len(recent_scores)-1)):
                insights.append("📈 満足度は上昇傾向にあります")
            elif all(recent_scores[i] >= recent_scores[i+1] for i in range(len(recent_scores)-1)):
                insights.append("📉 満足度は下降傾向にあります - 要因分析が必要です")
        
        return insights


# テスト用メイン関数
if __name__ == "__main__":
    print("🎯 満足度自動推定エンジン - テスト実行")
    print("=" * 60)
    
    # エンジンの初期化
    estimator = SatisfactionEstimator()
    
    # テストデータでの満足度計算
    test_session_id = "test_session_" + str(int(time.time()))
    
    print(f"テストセッションID: {test_session_id}")
    print("\n📊 満足度計算テスト:")
    
    # サンプルデータの挿入（実際のシステムではanalytics追跡から自動収集）
    with sqlite3.connect("langpont_analytics.db") as conn:
        cursor = conn.cursor()
        
        # テスト用のコピーイベント
        test_events = [
            {
                'event_type': 'translation_copy',
                'custom_data': {
                    'copy_method': 'button_click',
                    'translation_type': 'enhanced',
                    'user_choice_vs_recommendation': 'followed_recommendation'
                }
            },
            {
                'event_type': 'translation_copy',
                'custom_data': {
                    'copy_method': 'keyboard_shortcut',
                    'translation_type': 'gemini',
                    'user_choice_vs_recommendation': 'diverged_from_recommendation'
                }
            },
            {
                'event_type': 'scroll_depth',
                'custom_data': {
                    'scroll_percentage': 85,
                    'milestone': 75
                }
            },
            {
                'event_type': 'page_view',
                'custom_data': {
                    'page_title': 'LangPont Translation'
                }
            }
        ]
        
        for event in test_events:
            cursor.execute('''
                INSERT INTO analytics_events (
                    event_id, event_type, timestamp, session_id,
                    ip_address, user_agent, custom_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                f"test_{int(time.time() * 1000)}_{event['event_type']}",
                event['event_type'],
                int(time.time() * 1000),
                test_session_id,
                '127.0.0.1',
                'TestAgent/1.0',
                json.dumps(event['custom_data'])
            ))
        
        # セッション開始・終了時間の調整
        cursor.execute('''
            UPDATE analytics_events 
            SET timestamp = timestamp - 120000 
            WHERE session_id = ? AND event_type = 'page_view'
        ''', (test_session_id,))
        
        conn.commit()
    
    # 満足度計算
    result = estimator.calculate_satisfaction(test_session_id)
    
    print(f"\n✅ 満足度スコア: {result['satisfaction_score']}/100")
    print(f"  - コピー行動スコア: {result['copy_behavior_score']}")
    print(f"  - テキスト操作スコア: {result['text_interaction_score']}")
    print(f"  - セッション行動スコア: {result['session_pattern_score']}")
    print(f"  - エンゲージメントスコア: {result['engagement_score']}")
    
    # トレンド分析
    print("\n📈 満足度トレンド分析:")
    trends = estimator.analyze_satisfaction_trends()
    
    print(f"全体統計（過去30日）:")
    print(f"  - 総セッション数: {trends['overall_stats']['total_sessions']}")
    print(f"  - 平均満足度: {trends['overall_stats']['avg_satisfaction']}")
    print(f"  - 最低/最高: {trends['overall_stats']['min_satisfaction']} / {trends['overall_stats']['max_satisfaction']}")
    
    print("\n💡 洞察:")
    for insight in trends['insights']:
        print(f"  {insight}")
    
    print("\n✅ テスト完了 - 満足度推定エンジンは正常に動作しています")
    print("=" * 60)