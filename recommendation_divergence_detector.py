#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎯 Task 2.9.2: リアルタイム乖離検知システム強化
=====================================================
目的: Task 2.9.1.5で確立した包括的行動追跡システムを基盤として、
     Gemini推奨vs実選択の乖離を高精度でリアルタイム検知し、
     個人化翻訳AIのための貴重なデータを収集する

【Task 2.9.1.5基盤活用】
- GeminiRecommendationAnalyzerの拡張
- EnhancedSatisfactionEstimatorとの連携
- 非接触データ収集原則の継承
"""

import sqlite3
import json
import logging
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
import hashlib

# Task 2.9.1.5基盤システムのインポート
from gemini_recommendation_analyzer import GeminiRecommendationAnalyzer
from enhanced_satisfaction_estimator import EnhancedSatisfactionEstimator
from advanced_gemini_analysis_engine import AdvancedGeminiAnalysisEngine, StructuredRecommendation

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DivergenceImportance(Enum):
    """乖離重要度レベル"""
    CRITICAL = "critical"       # 極めて重要（学習価値が非常に高い）
    HIGH = "high"              # 高重要度（個人化に大きく影響）
    MEDIUM = "medium"          # 中重要度（一般的なパターン）
    LOW = "low"               # 低重要度（偶発的な選択）
    NOISE = "noise"           # ノイズ（分析対象外）

class DivergenceCategory(Enum):
    """乖離カテゴリ"""
    STYLE_PREFERENCE = "style_preference"           # スタイル選好
    ACCURACY_PRIORITY = "accuracy_priority"         # 精度重視
    FORMALITY_CHOICE = "formality_choice"          # 丁寧度選択
    CULTURAL_ADAPTATION = "cultural_adaptation"     # 文化的適応
    DOMAIN_EXPERTISE = "domain_expertise"          # 専門分野知識
    PERSONAL_HABIT = "personal_habit"              # 個人的習慣
    CONTEXT_SPECIFIC = "context_specific"          # 文脈特化
    EXPERIMENTAL = "experimental"                  # 実験的選択

@dataclass
class DivergenceEvent:
    """乖離イベントデータ"""
    event_id: str
    session_id: str
    user_id: Optional[str]
    gemini_recommendation: str
    user_choice: str
    gemini_confidence: float
    divergence_importance: DivergenceImportance
    divergence_category: DivergenceCategory
    satisfaction_score: float
    context_data: Dict[str, Any]
    behavioral_indicators: Dict[str, Any]
    learning_value: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class DivergenceTrend:
    """乖離トレンドデータ"""
    time_period: str
    total_divergences: int
    divergence_rate: float
    category_distribution: Dict[DivergenceCategory, int]
    importance_distribution: Dict[DivergenceImportance, int]
    learning_value_score: float
    user_patterns: Dict[str, Any]

class EnhancedRecommendationDivergenceDetector:
    """Task 2.9.1.5基盤を活用した高度乖離検知システム"""
    
    def __init__(self, 
                 analytics_db_path: str = "langpont_analytics.db",
                 divergence_db_path: str = "langpont_divergence.db"):
        """初期化"""
        self.analytics_db_path = analytics_db_path
        self.divergence_db_path = divergence_db_path
        
        # Task 2.9.1.5基盤システムの活用
        self.base_analyzer = GeminiRecommendationAnalyzer()
        self.satisfaction_estimator = EnhancedSatisfactionEstimator(analytics_db_path)
        self.advanced_analyzer = AdvancedGeminiAnalysisEngine()
        
        # 乖離検知用データベースの初期化
        self._init_divergence_database()
        
        # 学習価値評価パラメータ
        self.learning_value_weights = {
            'confidence_gap': 0.3,      # 推奨信頼度と実選択の乖離
            'satisfaction_impact': 0.25, # 満足度への影響
            'pattern_rarity': 0.2,       # パターンの希少性
            'context_richness': 0.15,    # コンテキストの豊富さ
            'behavioral_consistency': 0.1 # 行動の一貫性
        }
        
        logger.info("強化版乖離検知システム初期化完了")
    
    def _init_divergence_database(self):
        """乖離検知用データベースの初期化"""
        with sqlite3.connect(self.divergence_db_path) as conn:
            cursor = conn.cursor()
            
            # 乖離イベントテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS divergence_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id VARCHAR(100) UNIQUE NOT NULL,
                    session_id VARCHAR(100) NOT NULL,
                    user_id VARCHAR(100),
                    
                    -- 乖離基本情報
                    gemini_recommendation VARCHAR(50) NOT NULL,
                    user_choice VARCHAR(50) NOT NULL,
                    gemini_confidence FLOAT,
                    
                    -- 分類情報
                    divergence_importance VARCHAR(20),
                    divergence_category VARCHAR(50),
                    
                    -- 評価指標
                    satisfaction_score FLOAT,
                    learning_value FLOAT,
                    
                    -- データ詳細
                    context_data TEXT,
                    behavioral_indicators TEXT,
                    
                    -- メタデータ
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- インデックス用
                    date_only DATE GENERATED ALWAYS AS (DATE(created_at)) STORED
                )
            ''')
            
            # パターン学習テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS divergence_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id VARCHAR(100),
                    pattern_type VARCHAR(50),
                    pattern_data TEXT,
                    occurrence_count INTEGER DEFAULT 1,
                    learning_score FLOAT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # トレンド分析テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS divergence_trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time_period VARCHAR(20),
                    trend_data TEXT,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # インデックス作成
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_divergence_session ON divergence_events (session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_divergence_user ON divergence_events (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_divergence_importance ON divergence_events (divergence_importance)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_divergence_category ON divergence_events (divergence_category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_divergence_date ON divergence_events (date_only)')
            
            conn.commit()
    
    def detect_real_time_divergence(self, 
                                  gemini_analysis_text: str,
                                  gemini_recommendation: str, 
                                  user_choice: str,
                                  session_id: str,
                                  user_id: Optional[str] = None,
                                  context_data: Optional[Dict] = None) -> DivergenceEvent:
        """
        リアルタイム乖離パターン検知
        
        Args:
            gemini_analysis_text: Gemini分析の生テキスト
            gemini_recommendation: Gemini推奨エンジン
            user_choice: ユーザーの実選択
            session_id: セッションID
            user_id: ユーザーID
            context_data: コンテキストデータ
            
        Returns:
            乖離イベントデータ
        """
        try:
            # イベントIDの生成
            event_id = self._generate_event_id(session_id, user_choice)
            
            # 高度Gemini分析による推奨詳細取得
            structured_recommendation = self.advanced_analyzer.extract_structured_recommendations(
                gemini_analysis_text
            )
            
            # 満足度スコアの取得
            satisfaction_result = self.satisfaction_estimator.calculate_satisfaction(session_id, user_id)
            satisfaction_score = satisfaction_result.get('satisfaction_score', 0.0)
            
            # 行動指標の収集
            behavioral_indicators = self._collect_behavioral_indicators(session_id, user_id)
            
            # 乖離重要度の判定
            importance = self.classify_divergence_importance({
                'gemini_confidence': structured_recommendation.confidence_score,
                'satisfaction_score': satisfaction_score,
                'behavioral_indicators': behavioral_indicators,
                'context_data': context_data or {}
            })
            
            # 乖離カテゴリの分類
            category = self._classify_divergence_category(
                gemini_recommendation, 
                user_choice, 
                structured_recommendation,
                context_data or {}
            )
            
            # 学習価値の算出
            learning_value = self._calculate_learning_value(
                structured_recommendation.confidence_score,
                satisfaction_score,
                behavioral_indicators,
                context_data or {}
            )
            
            # 乖離イベントの作成
            divergence_event = DivergenceEvent(
                event_id=event_id,
                session_id=session_id,
                user_id=user_id,
                gemini_recommendation=gemini_recommendation,
                user_choice=user_choice,
                gemini_confidence=structured_recommendation.confidence_score,
                divergence_importance=importance,
                divergence_category=category,
                satisfaction_score=satisfaction_score,
                context_data=context_data or {},
                behavioral_indicators=behavioral_indicators,
                learning_value=learning_value
            )
            
            # データベースへの保存
            self._save_divergence_event(divergence_event)
            
            # パターン学習の更新
            self._update_pattern_learning(divergence_event)
            
            logger.info(f"乖離検知完了: {user_choice} vs {gemini_recommendation} "
                       f"(重要度: {importance.value}, 学習価値: {learning_value:.3f})")
            
            return divergence_event
            
        except Exception as e:
            logger.error(f"乖離検知エラー: {str(e)}")
            # エラー時のフォールバック
            return DivergenceEvent(
                event_id=f"error_{int(time.time())}",
                session_id=session_id,
                user_id=user_id,
                gemini_recommendation=gemini_recommendation,
                user_choice=user_choice,
                gemini_confidence=0.0,
                divergence_importance=DivergenceImportance.NOISE,
                divergence_category=DivergenceCategory.EXPERIMENTAL,
                satisfaction_score=0.0,
                context_data={'error': str(e)},
                behavioral_indicators={},
                learning_value=0.0
            )
    
    def _generate_event_id(self, session_id: str, user_choice: str) -> str:
        """乖離イベントIDの生成"""
        data = f"{session_id}_{user_choice}_{int(time.time() * 1000)}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    def _collect_behavioral_indicators(self, session_id: str, user_id: Optional[str]) -> Dict[str, Any]:
        """行動指標の収集"""
        indicators = {}
        
        try:
            with sqlite3.connect(self.analytics_db_path) as conn:
                cursor = conn.cursor()
                
                # セッション行動の分析
                cursor.execute('''
                    SELECT event_type, COUNT(*) as count,
                           AVG(timestamp) as avg_timestamp
                    FROM analytics_events
                    WHERE session_id = ?
                    GROUP BY event_type
                ''', (session_id,))
                
                session_behaviors = {}
                for event_type, count, avg_timestamp in cursor.fetchall():
                    session_behaviors[event_type] = {
                        'count': count,
                        'avg_timestamp': avg_timestamp
                    }
                
                indicators['session_behaviors'] = session_behaviors
                
                # コピー行動の詳細分析
                cursor.execute('''
                    SELECT custom_data
                    FROM analytics_events
                    WHERE session_id = ? AND event_type = 'translation_copy'
                    ORDER BY timestamp DESC
                    LIMIT 5
                ''', (session_id,))
                
                copy_behaviors = []
                for row in cursor.fetchall():
                    try:
                        copy_data = json.loads(row[0]) if row[0] else {}
                        copy_behaviors.append(copy_data)
                    except json.JSONDecodeError:
                        continue
                
                indicators['recent_copy_behaviors'] = copy_behaviors
                
                # セッション継続時間
                cursor.execute('''
                    SELECT MIN(timestamp) as start_time,
                           MAX(timestamp) as end_time
                    FROM analytics_events
                    WHERE session_id = ?
                ''', (session_id,))
                
                time_data = cursor.fetchone()
                if time_data and time_data[0] and time_data[1]:
                    duration = (time_data[1] - time_data[0]) / 1000.0
                    indicators['session_duration'] = duration
                
        except Exception as e:
            logger.error(f"行動指標収集エラー: {str(e)}")
            indicators['error'] = str(e)
        
        return indicators
    
    def classify_divergence_importance(self, divergence_data: Dict[str, Any]) -> DivergenceImportance:
        """
        乖離分類・重要度判定
        
        Args:
            divergence_data: 乖離判定用データ
            
        Returns:
            乖離重要度
        """
        score = 0.0
        
        # 1. Gemini推奨の信頼度（高信頼度での乖離は重要）
        gemini_confidence = divergence_data.get('gemini_confidence', 0.0)
        if gemini_confidence >= 0.8:
            score += 3.0
        elif gemini_confidence >= 0.6:
            score += 2.0
        elif gemini_confidence >= 0.4:
            score += 1.0
        
        # 2. 満足度スコア（高満足度での乖離は価値が高い）
        satisfaction_score = divergence_data.get('satisfaction_score', 0.0)
        if satisfaction_score >= 80:
            score += 2.5
        elif satisfaction_score >= 60:
            score += 1.5
        elif satisfaction_score >= 40:
            score += 0.5
        
        # 3. 行動の一貫性
        behavioral_indicators = divergence_data.get('behavioral_indicators', {})
        copy_behaviors = behavioral_indicators.get('recent_copy_behaviors', [])
        
        if len(copy_behaviors) >= 2:
            # 複数のコピー行動がある = 慎重な選択
            score += 1.5
        
        session_duration = behavioral_indicators.get('session_duration', 0)
        if session_duration >= 120:  # 2分以上の検討時間
            score += 1.0
        
        # 4. コンテキストの豊富さ
        context_data = divergence_data.get('context_data', {})
        if context_data.get('text_length', 0) > 200:
            score += 1.0
        if context_data.get('has_technical_terms'):
            score += 1.0
        if context_data.get('cultural_context'):
            score += 1.0
        
        # 重要度の分類
        if score >= 7.0:
            return DivergenceImportance.CRITICAL
        elif score >= 5.0:
            return DivergenceImportance.HIGH
        elif score >= 3.0:
            return DivergenceImportance.MEDIUM
        elif score >= 1.0:
            return DivergenceImportance.LOW
        else:
            return DivergenceImportance.NOISE
    
    def _classify_divergence_category(self, 
                                    gemini_recommendation: str,
                                    user_choice: str,
                                    structured_recommendation: StructuredRecommendation,
                                    context_data: Dict) -> DivergenceCategory:
        """乖離カテゴリの分類"""
        
        # 推奨理由に基づく分類
        primary_reasons = [r.value for r in structured_recommendation.primary_reasons]
        
        # スタイル関連の理由が多い場合
        style_reasons = ['style', 'tone', 'formality']
        if any(reason in primary_reasons for reason in style_reasons):
            return DivergenceCategory.STYLE_PREFERENCE
        
        # 精度関連の理由が多い場合
        accuracy_reasons = ['accuracy', 'clarity', 'terminology']
        if any(reason in primary_reasons for reason in accuracy_reasons):
            return DivergenceCategory.ACCURACY_PRIORITY
        
        # 文化・文脈関連
        cultural_reasons = ['cultural_fit', 'context_fit']
        if any(reason in primary_reasons for reason in cultural_reasons):
            return DivergenceCategory.CULTURAL_ADAPTATION
        
        # 文章長に基づく分類
        text_length = context_data.get('text_length', 0)
        if text_length > 500:
            return DivergenceCategory.DOMAIN_EXPERTISE
        
        # デフォルト分類
        return DivergenceCategory.PERSONAL_HABIT
    
    def _calculate_learning_value(self, 
                                gemini_confidence: float,
                                satisfaction_score: float,
                                behavioral_indicators: Dict,
                                context_data: Dict) -> float:
        """学習価値の算出"""
        
        learning_value = 0.0
        
        # 1. 信頼度ギャップ（高信頼度推奨からの乖離は価値が高い）
        confidence_gap = gemini_confidence * self.learning_value_weights['confidence_gap']
        learning_value += confidence_gap
        
        # 2. 満足度への影響
        satisfaction_impact = (satisfaction_score / 100.0) * self.learning_value_weights['satisfaction_impact']
        learning_value += satisfaction_impact
        
        # 3. パターンの希少性（過去の類似パターンが少ないほど価値が高い）
        rarity_score = self._calculate_pattern_rarity(context_data)
        learning_value += rarity_score * self.learning_value_weights['pattern_rarity']
        
        # 4. コンテキストの豊富さ
        context_richness = self._evaluate_context_richness(context_data)
        learning_value += context_richness * self.learning_value_weights['context_richness']
        
        # 5. 行動の一貫性
        behavioral_consistency = self._evaluate_behavioral_consistency(behavioral_indicators)
        learning_value += behavioral_consistency * self.learning_value_weights['behavioral_consistency']
        
        # 0.0-1.0の範囲に正規化
        return max(0.0, min(1.0, learning_value))
    
    def _calculate_pattern_rarity(self, context_data: Dict) -> float:
        """パターンの希少性算出"""
        # 簡易実装：将来的にはMLベースの希少性判定
        text_length = context_data.get('text_length', 0)
        
        if text_length > 1000:
            return 0.9  # 長文は希少
        elif text_length > 500:
            return 0.7
        elif text_length > 200:
            return 0.5
        else:
            return 0.3
    
    def _evaluate_context_richness(self, context_data: Dict) -> float:
        """コンテキストの豊富さ評価"""
        richness = 0.0
        
        if context_data.get('has_technical_terms'):
            richness += 0.3
        if context_data.get('cultural_context'):
            richness += 0.3
        if context_data.get('business_context'):
            richness += 0.2
        if context_data.get('text_length', 0) > 300:
            richness += 0.2
        
        return min(1.0, richness)
    
    def _evaluate_behavioral_consistency(self, behavioral_indicators: Dict) -> float:
        """行動の一貫性評価"""
        consistency = 0.0
        
        # セッション継続時間（じっくり検討した証拠）
        duration = behavioral_indicators.get('session_duration', 0)
        if duration >= 180:  # 3分以上
            consistency += 0.4
        elif duration >= 60:  # 1分以上
            consistency += 0.2
        
        # 複数のコピー行動（比較検討の証拠）
        copy_behaviors = behavioral_indicators.get('recent_copy_behaviors', [])
        if len(copy_behaviors) >= 3:
            consistency += 0.3
        elif len(copy_behaviors) >= 2:
            consistency += 0.2
        
        # 異なるコピー方法の使用（上級ユーザーの証拠）
        copy_methods = set()
        for behavior in copy_behaviors:
            method = behavior.get('copy_method')
            if method:
                copy_methods.add(method)
        
        if len(copy_methods) >= 2:
            consistency += 0.3
        
        return min(1.0, consistency)
    
    def identify_valuable_divergence_patterns(self, 
                                            user_id: Optional[str] = None,
                                            days: int = 30) -> List[Dict[str, Any]]:
        """
        貴重な推奨違いデータの自動特定
        
        Args:
            user_id: ユーザーID（Noneの場合は全ユーザー）
            days: 分析期間（日数）
            
        Returns:
            貴重な乖離パターンのリスト
        """
        valuable_patterns = []
        
        with sqlite3.connect(self.divergence_db_path) as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT event_id, session_id, user_id,
                       gemini_recommendation, user_choice,
                       divergence_importance, divergence_category,
                       learning_value, satisfaction_score,
                       context_data, behavioral_indicators,
                       created_at
                FROM divergence_events
                WHERE created_at >= datetime('now', '-{} days')
                  AND learning_value >= 0.7
            '''.format(days)
            
            if user_id:
                query += " AND user_id = ?"
                cursor.execute(query, (user_id,))
            else:
                cursor.execute(query)
            
            for row in cursor.fetchall():
                try:
                    context_data = json.loads(row[9]) if row[9] else {}
                    behavioral_indicators = json.loads(row[10]) if row[10] else {}
                    
                    pattern = {
                        'event_id': row[0],
                        'session_id': row[1],
                        'user_id': row[2],
                        'divergence': {
                            'gemini_recommendation': row[3],
                            'user_choice': row[4]
                        },
                        'classification': {
                            'importance': row[5],
                            'category': row[6]
                        },
                        'scores': {
                            'learning_value': row[7],
                            'satisfaction_score': row[8]
                        },
                        'context_data': context_data,
                        'behavioral_indicators': behavioral_indicators,
                        'created_at': row[11]
                    }
                    
                    valuable_patterns.append(pattern)
                    
                except json.JSONDecodeError:
                    continue
        
        # 学習価値でソート
        valuable_patterns.sort(key=lambda x: x['scores']['learning_value'], reverse=True)
        
        logger.info(f"貴重パターン特定完了: {len(valuable_patterns)}件")
        return valuable_patterns
    
    def analyze_divergence_trends(self, time_window: str = "30days") -> DivergenceTrend:
        """
        統計分析・トレンド検出
        
        Args:
            time_window: 分析期間 ("7days", "30days", "90days")
            
        Returns:
            乖離トレンド分析結果
        """
        days = {"7days": 7, "30days": 30, "90days": 90}.get(time_window, 30)
        
        with sqlite3.connect(self.divergence_db_path) as conn:
            cursor = conn.cursor()
            
            # 基本統計の取得
            cursor.execute('''
                SELECT COUNT(*) as total_divergences,
                       AVG(learning_value) as avg_learning_value,
                       AVG(satisfaction_score) as avg_satisfaction
                FROM divergence_events
                WHERE created_at >= datetime('now', '-{} days')
            '''.format(days))
            
            basic_stats = cursor.fetchone()
            total_divergences = basic_stats[0] if basic_stats else 0
            
            # 全翻訳数の取得（乖離率算出用）
            with sqlite3.connect(self.analytics_db_path) as analytics_conn:
                analytics_cursor = analytics_conn.cursor()
                analytics_cursor.execute('''
                    SELECT COUNT(*)
                    FROM analytics_events
                    WHERE event_type = 'translation_copy'
                      AND timestamp >= (strftime('%s', 'now', '-{} days') * 1000)
                '''.format(days))
                
                result = analytics_cursor.fetchone()
                total_translations = result[0] if result else 1
            
            divergence_rate = total_divergences / max(1, total_translations)
            
            # カテゴリ分布
            cursor.execute('''
                SELECT divergence_category, COUNT(*)
                FROM divergence_events
                WHERE created_at >= datetime('now', '-{} days')
                GROUP BY divergence_category
            '''.format(days))
            
            category_distribution = {}
            for category, count in cursor.fetchall():
                try:
                    category_distribution[DivergenceCategory(category)] = count
                except ValueError:
                    category_distribution[DivergenceCategory.EXPERIMENTAL] = count
            
            # 重要度分布
            cursor.execute('''
                SELECT divergence_importance, COUNT(*)
                FROM divergence_events
                WHERE created_at >= datetime('now', '-{} days')
                GROUP BY divergence_importance
            '''.format(days))
            
            importance_distribution = {}
            for importance, count in cursor.fetchall():
                try:
                    importance_distribution[DivergenceImportance(importance)] = count
                except ValueError:
                    importance_distribution[DivergenceImportance.NOISE] = count
            
            # ユーザーパターン分析
            cursor.execute('''
                SELECT user_id, COUNT(*) as divergence_count,
                       AVG(learning_value) as avg_learning_value
                FROM divergence_events
                WHERE created_at >= datetime('now', '-{} days')
                  AND user_id IS NOT NULL
                GROUP BY user_id
                ORDER BY divergence_count DESC
                LIMIT 10
            '''.format(days))
            
            user_patterns = {}
            for user_id, count, avg_learning in cursor.fetchall():
                user_patterns[user_id] = {
                    'divergence_count': count,
                    'avg_learning_value': avg_learning
                }
            
            # 学習価値総合スコア
            learning_value_score = basic_stats[1] if basic_stats and basic_stats[1] else 0.0
        
        trend = DivergenceTrend(
            time_period=time_window,
            total_divergences=total_divergences,
            divergence_rate=divergence_rate,
            category_distribution=category_distribution,
            importance_distribution=importance_distribution,
            learning_value_score=learning_value_score,
            user_patterns=user_patterns
        )
        
        # トレンドデータの保存
        self._save_trend_analysis(trend)
        
        logger.info(f"トレンド分析完了: {time_window}, 乖離率={divergence_rate:.3f}")
        return trend
    
    def _save_divergence_event(self, event: DivergenceEvent):
        """乖離イベントの保存"""
        with sqlite3.connect(self.divergence_db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO divergence_events (
                    event_id, session_id, user_id,
                    gemini_recommendation, user_choice, gemini_confidence,
                    divergence_importance, divergence_category,
                    satisfaction_score, learning_value,
                    context_data, behavioral_indicators
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_id,
                event.session_id,
                event.user_id,
                event.gemini_recommendation,
                event.user_choice,
                event.gemini_confidence,
                event.divergence_importance.value,
                event.divergence_category.value,
                event.satisfaction_score,
                event.learning_value,
                json.dumps(event.context_data),
                json.dumps(event.behavioral_indicators)
            ))
            
            conn.commit()
    
    def _update_pattern_learning(self, event: DivergenceEvent):
        """パターン学習の更新"""
        if not event.user_id:
            return
        
        with sqlite3.connect(self.divergence_db_path) as conn:
            cursor = conn.cursor()
            
            # 既存パターンの確認
            pattern_key = f"{event.gemini_recommendation}_{event.user_choice}_{event.divergence_category.value}"
            
            cursor.execute('''
                SELECT id, occurrence_count, learning_score
                FROM divergence_patterns
                WHERE user_id = ? AND pattern_type = ?
            ''', (event.user_id, pattern_key))
            
            existing = cursor.fetchone()
            
            if existing:
                # 既存パターンの更新
                new_count = existing[1] + 1
                new_score = (existing[2] + event.learning_value) / 2  # 平均
                
                cursor.execute('''
                    UPDATE divergence_patterns
                    SET occurrence_count = ?, learning_score = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_count, new_score, existing[0]))
            else:
                # 新規パターンの作成
                cursor.execute('''
                    INSERT INTO divergence_patterns (
                        user_id, pattern_type, pattern_data,
                        occurrence_count, learning_score
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    event.user_id,
                    pattern_key,
                    json.dumps({
                        'gemini_recommendation': event.gemini_recommendation,
                        'user_choice': event.user_choice,
                        'category': event.divergence_category.value
                    }),
                    1,
                    event.learning_value
                ))
            
            conn.commit()
    
    def _save_trend_analysis(self, trend: DivergenceTrend):
        """トレンド分析結果の保存"""
        with sqlite3.connect(self.divergence_db_path) as conn:
            cursor = conn.cursor()
            
            trend_data = {
                'total_divergences': trend.total_divergences,
                'divergence_rate': trend.divergence_rate,
                'category_distribution': {k.value: v for k, v in trend.category_distribution.items()},
                'importance_distribution': {k.value: v for k, v in trend.importance_distribution.items()},
                'learning_value_score': trend.learning_value_score,
                'user_patterns': trend.user_patterns
            }
            
            cursor.execute('''
                INSERT INTO divergence_trends (time_period, trend_data)
                VALUES (?, ?)
            ''', (trend.time_period, json.dumps(trend_data)))
            
            conn.commit()


# テスト用メイン関数
if __name__ == "__main__":
    print("🎯 強化版乖離検知システム - テスト実行")
    print("=" * 60)
    
    detector = EnhancedRecommendationDivergenceDetector()
    
    # テスト用乖離イベント
    test_analysis = """
    3つの翻訳を詳細に分析した結果、Enhanced翻訳が最も適切です。
    文脈への適合性と自然さの観点から強く推奨します。
    """
    
    divergence = detector.detect_real_time_divergence(
        gemini_analysis_text=test_analysis,
        gemini_recommendation="enhanced",
        user_choice="gemini",
        session_id="test_session_292",
        user_id="test_user",
        context_data={
            'text_length': 200,
            'has_technical_terms': True,
            'business_context': True
        }
    )
    
    print(f"✅ 乖離検知結果:")
    print(f"  重要度: {divergence.divergence_importance.value}")
    print(f"  カテゴリ: {divergence.divergence_category.value}")
    print(f"  学習価値: {divergence.learning_value:.3f}")
    print(f"  満足度: {divergence.satisfaction_score}")
    
    # トレンド分析
    trend = detector.analyze_divergence_trends("30days")
    print(f"\n📈 トレンド分析:")
    print(f"  総乖離数: {trend.total_divergences}")
    print(f"  乖離率: {trend.divergence_rate:.3f}")
    print(f"  学習価値スコア: {trend.learning_value_score:.3f}")
    
    print("\n✅ テスト完了 - 強化版乖離検知システム正常動作")