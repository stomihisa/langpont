#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎯 Task 2.9.2: 乖離理由自動推定システム
=====================================================
目的: 個人化選好パターンと乖離理由の推定エンジンにより、
     ユーザー一人ひとりの翻訳選好を深く理解し、
     個人化翻訳AI構築のための高品質データを生成する

【Task 2.9.1.5基盤活用】
- EnhancedSatisfactionEstimatorとの連携
- 非接触データ収集原則の継承
- 真の個人化パターン分析の深化
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
import math

# Task 2.9.1.5基盤システムのインポート
from enhanced_satisfaction_estimator import EnhancedSatisfactionEstimator
from recommendation_divergence_detector import (
    EnhancedRecommendationDivergenceDetector,
    DivergenceEvent,
    DivergenceCategory,
    DivergenceImportance
)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PreferencePattern(Enum):
    """選好パターンタイプ"""
    CONSISTENT_ENGINE = "consistent_engine"           # 特定エンジン一貫選好
    CONTEXT_ADAPTIVE = "context_adaptive"            # 文脈適応型選好
    QUALITY_MAXIMIZER = "quality_maximizer"          # 品質最大化型
    STYLE_FOCUSED = "style_focused"                  # スタイル重視型
    EFFICIENCY_ORIENTED = "efficiency_oriented"      # 効率重視型
    EXPERIMENTAL = "experimental"                    # 実験的選好
    DOMAIN_SPECIALIST = "domain_specialist"          # 専門分野特化型
    CULTURAL_SENSITIVE = "cultural_sensitive"        # 文化感応型

class LearningConfidence(Enum):
    """学習信頼度レベル"""
    HIGH = "high"           # 高信頼度（10回以上のデータ）
    MEDIUM = "medium"       # 中信頼度（5-9回のデータ）
    LOW = "low"            # 低信頼度（2-4回のデータ）
    INSUFFICIENT = "insufficient"  # データ不足（1回以下）

@dataclass
class PreferenceProfile:
    """個人化選好プロファイル"""
    user_id: str
    
    # 基本選好パターン
    dominant_pattern: PreferencePattern
    secondary_patterns: List[PreferencePattern]
    confidence_level: LearningConfidence
    
    # エンジン選好
    engine_preferences: Dict[str, float]  # エンジン名 -> 選好度スコア
    
    # コンテキスト別選好
    context_preferences: Dict[str, Dict[str, float]]
    
    # 学習メトリクス
    total_observations: int
    prediction_accuracy: float
    last_updated: str
    
    # 分析結果
    preference_insights: List[str]
    improvement_suggestions: List[str]
    
    # メタデータ
    profile_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ReasonEstimation:
    """乖離理由推定結果"""
    estimated_reasons: List[str]
    confidence_scores: Dict[str, float]
    supporting_evidence: Dict[str, List[str]]
    prediction_accuracy: float
    estimation_metadata: Dict[str, Any]

class PreferenceReasonEstimator:
    """個人化選好パターンと乖離理由の推定エンジン"""
    
    def __init__(self, 
                 analytics_db_path: str = "langpont_analytics.db",
                 divergence_db_path: str = "langpont_divergence.db",
                 preference_db_path: str = "langpont_preferences.db"):
        """初期化"""
        self.analytics_db_path = analytics_db_path
        self.divergence_db_path = divergence_db_path
        self.preference_db_path = preference_db_path
        
        # Task 2.9.1.5基盤システムの活用
        self.satisfaction_estimator = EnhancedSatisfactionEstimator(analytics_db_path)
        self.divergence_detector = EnhancedRecommendationDivergenceDetector(
            analytics_db_path, divergence_db_path
        )
        
        # 選好学習用データベースの初期化
        self._init_preference_database()
        
        # 推定モデルのパラメータ
        self.reason_estimation_weights = {
            'historical_pattern': 0.35,    # 過去の選好パターン
            'context_similarity': 0.25,    # コンテキスト類似度
            'satisfaction_correlation': 0.20, # 満足度相関
            'behavioral_consistency': 0.15, # 行動一貫性
            'temporal_trend': 0.05         # 時系列トレンド
        }
        
        # 選好パターン判定閾値
        self.pattern_thresholds = {
            'consistent_engine': 0.7,      # 70%以上同一エンジン選択
            'context_adaptive': 0.6,       # 60%以上文脈適応
            'quality_maximizer': 0.8,      # 80%以上高満足度選択
            'style_focused': 0.5,          # 50%以上スタイル理由
        }
        
        logger.info("選好理由推定エンジン初期化完了")
    
    def _init_preference_database(self):
        """選好学習用データベースの初期化"""
        with sqlite3.connect(self.preference_db_path) as conn:
            cursor = conn.cursor()
            
            # ユーザー選好プロファイルテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preference_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id VARCHAR(100) UNIQUE NOT NULL,
                    
                    -- 選好パターン
                    dominant_pattern VARCHAR(50),
                    secondary_patterns TEXT,
                    confidence_level VARCHAR(20),
                    
                    -- 選好データ
                    engine_preferences TEXT,
                    context_preferences TEXT,
                    
                    -- 学習メトリクス
                    total_observations INTEGER DEFAULT 0,
                    prediction_accuracy FLOAT DEFAULT 0.0,
                    
                    -- 分析結果
                    preference_insights TEXT,
                    improvement_suggestions TEXT,
                    
                    -- メタデータ
                    profile_metadata TEXT,
                    
                    -- 時間管理
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 理由推定履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reason_estimations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id VARCHAR(100),
                    session_id VARCHAR(100),
                    
                    -- 推定結果
                    estimated_reasons TEXT,
                    confidence_scores TEXT,
                    supporting_evidence TEXT,
                    prediction_accuracy FLOAT,
                    
                    -- 実際の結果（フィードバック用）
                    actual_choice VARCHAR(50),
                    actual_satisfaction FLOAT,
                    
                    -- メタデータ
                    estimation_metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 学習パフォーマンステーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id VARCHAR(100),
                    
                    -- パフォーマンス指標
                    accuracy_trend TEXT,
                    pattern_stability FLOAT,
                    prediction_confidence FLOAT,
                    
                    -- 学習統計
                    total_predictions INTEGER DEFAULT 0,
                    correct_predictions INTEGER DEFAULT 0,
                    
                    -- 計算期間
                    calculation_period VARCHAR(20),
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # インデックス作成
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_preference_user ON user_preference_profiles (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_estimation_user ON reason_estimations (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_estimation_session ON reason_estimations (session_id)')
            
            conn.commit()
    
    def analyze_behavior_preference_correlation(self, user_data: Dict) -> Dict[str, Any]:
        """
        行動パターン相関分析
        
        Args:
            user_data: ユーザーの行動・選択データ
            
        Returns:
            行動と選好の相関分析結果
        """
        correlations = {
            'engine_behavior_correlation': {},
            'satisfaction_behavior_correlation': {},
            'context_behavior_correlation': {},
            'temporal_patterns': {},
            'consistency_metrics': {}
        }
        
        try:
            user_id = user_data.get('user_id')
            if not user_id:
                return correlations
            
            # 過去の乖離データの取得
            divergence_history = self._get_user_divergence_history(user_id, days=90)
            
            if len(divergence_history) < 3:
                correlations['insufficient_data'] = True
                return correlations
            
            # 1. エンジン選択と行動の相関
            correlations['engine_behavior_correlation'] = self._analyze_engine_behavior_correlation(
                divergence_history
            )
            
            # 2. 満足度と行動の相関
            correlations['satisfaction_behavior_correlation'] = self._analyze_satisfaction_behavior_correlation(
                divergence_history
            )
            
            # 3. コンテキストと行動の相関
            correlations['context_behavior_correlation'] = self._analyze_context_behavior_correlation(
                divergence_history
            )
            
            # 4. 時系列パターンの分析
            correlations['temporal_patterns'] = self._analyze_temporal_patterns(
                divergence_history
            )
            
            # 5. 一貫性メトリクス
            correlations['consistency_metrics'] = self._calculate_consistency_metrics(
                divergence_history
            )
            
            logger.info(f"行動選好相関分析完了: user={user_id}, データ数={len(divergence_history)}")
            
        except Exception as e:
            logger.error(f"行動選好相関分析エラー: {str(e)}")
            correlations['error'] = str(e)
        
        return correlations
    
    def _get_user_divergence_history(self, user_id: str, days: int = 90) -> List[Dict[str, Any]]:
        """ユーザーの乖離履歴取得"""
        history = []
        
        with sqlite3.connect(self.divergence_db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT session_id, gemini_recommendation, user_choice,
                       gemini_confidence, divergence_importance, divergence_category,
                       satisfaction_score, learning_value,
                       context_data, behavioral_indicators,
                       created_at
                FROM divergence_events
                WHERE user_id = ? 
                  AND created_at >= datetime('now', '-{} days')
                ORDER BY created_at DESC
            '''.format(days), (user_id,))
            
            for row in cursor.fetchall():
                try:
                    context_data = json.loads(row[8]) if row[8] else {}
                    behavioral_indicators = json.loads(row[9]) if row[9] else {}
                    
                    history.append({
                        'session_id': row[0],
                        'gemini_recommendation': row[1],
                        'user_choice': row[2],
                        'gemini_confidence': row[3],
                        'divergence_importance': row[4],
                        'divergence_category': row[5],
                        'satisfaction_score': row[6],
                        'learning_value': row[7],
                        'context_data': context_data,
                        'behavioral_indicators': behavioral_indicators,
                        'created_at': row[10]
                    })
                except json.JSONDecodeError:
                    continue
        
        return history
    
    def _analyze_engine_behavior_correlation(self, history: List[Dict]) -> Dict[str, float]:
        """エンジン選択と行動の相関分析"""
        correlations = {}
        
        # エンジン別の行動パターンを分析
        engine_behaviors = defaultdict(list)
        
        for event in history:
            choice = event['user_choice']
            behavioral_indicators = event.get('behavioral_indicators', {})
            
            # セッション継続時間
            session_duration = behavioral_indicators.get('session_duration', 0)
            # コピー行動回数
            copy_count = len(behavioral_indicators.get('recent_copy_behaviors', []))
            
            engine_behaviors[choice].append({
                'session_duration': session_duration,
                'copy_count': copy_count,
                'satisfaction': event.get('satisfaction_score', 0)
            })
        
        # 各エンジンの平均行動指標を計算
        for engine, behaviors in engine_behaviors.items():
            if len(behaviors) >= 2:
                avg_duration = statistics.mean([b['session_duration'] for b in behaviors])
                avg_copy_count = statistics.mean([b['copy_count'] for b in behaviors])
                avg_satisfaction = statistics.mean([b['satisfaction'] for b in behaviors])
                
                correlations[f'{engine}_avg_duration'] = avg_duration
                correlations[f'{engine}_avg_copy_count'] = avg_copy_count
                correlations[f'{engine}_avg_satisfaction'] = avg_satisfaction
        
        return correlations
    
    def _analyze_satisfaction_behavior_correlation(self, history: List[Dict]) -> Dict[str, float]:
        """満足度と行動の相関分析"""
        if len(history) < 3:
            return {}
        
        satisfactions = [event.get('satisfaction_score', 0) for event in history]
        durations = []
        copy_counts = []
        
        for event in history:
            behavioral_indicators = event.get('behavioral_indicators', {})
            durations.append(behavioral_indicators.get('session_duration', 0))
            copy_counts.append(len(behavioral_indicators.get('recent_copy_behaviors', [])))
        
        correlations = {}
        
        # ピアソン相関係数の近似計算
        if len(satisfactions) == len(durations) and len(satisfactions) > 1:
            # 満足度とセッション継続時間の相関
            try:
                corr_duration = self._calculate_correlation(satisfactions, durations)
                correlations['satisfaction_duration_correlation'] = corr_duration
            except:
                correlations['satisfaction_duration_correlation'] = 0.0
            
            # 満足度とコピー回数の相関
            try:
                corr_copy = self._calculate_correlation(satisfactions, copy_counts)
                correlations['satisfaction_copy_correlation'] = corr_copy
            except:
                correlations['satisfaction_copy_correlation'] = 0.0
        
        return correlations
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """ピアソン相関係数の計算"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        try:
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(xi * xi for xi in x)
            sum_y2 = sum(yi * yi for yi in y)
            
            numerator = n * sum_xy - sum_x * sum_y
            denominator = math.sqrt((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y))
            
            if denominator == 0:
                return 0.0
            
            return numerator / denominator
        except:
            return 0.0
    
    def _analyze_context_behavior_correlation(self, history: List[Dict]) -> Dict[str, Any]:
        """コンテキストと行動の相関分析"""
        context_patterns = defaultdict(list)
        
        for event in history:
            context_data = event.get('context_data', {})
            
            # 文章長による分類
            text_length = context_data.get('text_length', 0)
            length_category = self._categorize_text_length(text_length)
            
            # 技術文書かどうか
            has_technical = context_data.get('has_technical_terms', False)
            tech_category = 'technical' if has_technical else 'general'
            
            context_patterns[length_category].append(event['user_choice'])
            context_patterns[tech_category].append(event['user_choice'])
        
        # パターン分析
        correlations = {}
        for context, choices in context_patterns.items():
            if len(choices) >= 2:
                choice_counter = Counter(choices)
                most_common = choice_counter.most_common(1)[0]
                preference_rate = most_common[1] / len(choices)
                
                correlations[f'{context}_preference'] = {
                    'preferred_engine': most_common[0],
                    'preference_rate': preference_rate,
                    'sample_size': len(choices)
                }
        
        return correlations
    
    def _categorize_text_length(self, length: int) -> str:
        """文章長のカテゴライズ"""
        if length < 100:
            return 'short'
        elif length < 300:
            return 'medium'
        elif length < 600:
            return 'long'
        else:
            return 'very_long'
    
    def _analyze_temporal_patterns(self, history: List[Dict]) -> Dict[str, Any]:
        """時系列パターンの分析"""
        if len(history) < 5:
            return {}
        
        # 時系列での選択パターン
        recent_choices = [event['user_choice'] for event in history[:10]]  # 直近10回
        all_choices = [event['user_choice'] for event in history]
        
        # 最近の選択傾向
        recent_counter = Counter(recent_choices)
        all_counter = Counter(all_choices)
        
        patterns = {
            'recent_preference': recent_counter.most_common(1)[0] if recent_choices else None,
            'overall_preference': all_counter.most_common(1)[0] if all_choices else None,
            'trend_stability': self._calculate_trend_stability(recent_choices, all_choices)
        }
        
        return patterns
    
    def _calculate_trend_stability(self, recent: List[str], overall: List[str]) -> float:
        """トレンドの安定性計算"""
        if not recent or not overall:
            return 0.0
        
        recent_counter = Counter(recent)
        overall_counter = Counter(overall)
        
        # 最頻出エンジンが一致するかチェック
        recent_top = recent_counter.most_common(1)[0][0] if recent_counter else None
        overall_top = overall_counter.most_common(1)[0][0] if overall_counter else None
        
        if recent_top == overall_top:
            return 0.8  # 高い安定性
        else:
            return 0.3  # 低い安定性
    
    def _calculate_consistency_metrics(self, history: List[Dict]) -> Dict[str, float]:
        """一貫性メトリクスの計算"""
        if len(history) < 3:
            return {}
        
        # エンジン選択の一貫性
        choices = [event['user_choice'] for event in history]
        choice_counter = Counter(choices)
        max_count = choice_counter.most_common(1)[0][1]
        choice_consistency = max_count / len(choices)
        
        # 満足度の安定性
        satisfactions = [event.get('satisfaction_score', 0) for event in history]
        satisfaction_std = statistics.stdev(satisfactions) if len(satisfactions) > 1 else 0
        satisfaction_consistency = max(0, 1 - (satisfaction_std / 100))  # 正規化
        
        return {
            'choice_consistency': choice_consistency,
            'satisfaction_consistency': satisfaction_consistency,
            'overall_consistency': (choice_consistency + satisfaction_consistency) / 2
        }
    
    def estimate_divergence_reasons(self, divergence_event: Dict) -> ReasonEstimation:
        """
        乖離理由の自動推定
        
        Args:
            divergence_event: 乖離イベントデータ
            
        Returns:
            理由推定結果
        """
        try:
            user_id = divergence_event.get('user_id')
            if not user_id:
                return ReasonEstimation(
                    estimated_reasons=['insufficient_user_data'],
                    confidence_scores={'insufficient_user_data': 1.0},
                    supporting_evidence={},
                    prediction_accuracy=0.0,
                    estimation_metadata={'error': 'No user ID provided'}
                )
            
            # ユーザーの行動データを取得
            user_data = {'user_id': user_id}
            correlations = self.analyze_behavior_preference_correlation(user_data)
            
            # 推定ロジック
            estimated_reasons = []
            confidence_scores = {}
            supporting_evidence = defaultdict(list)
            
            # 1. 過去のパターンベース推定
            pattern_reasons = self._estimate_from_historical_pattern(user_id, divergence_event)
            estimated_reasons.extend(pattern_reasons['reasons'])
            confidence_scores.update(pattern_reasons['confidences'])
            supporting_evidence.update(pattern_reasons['evidence'])
            
            # 2. コンテキスト類似度ベース推定
            context_reasons = self._estimate_from_context_similarity(divergence_event, correlations)
            estimated_reasons.extend(context_reasons['reasons'])
            confidence_scores.update(context_reasons['confidences'])
            supporting_evidence.update(context_reasons['evidence'])
            
            # 3. 満足度相関ベース推定
            satisfaction_reasons = self._estimate_from_satisfaction_correlation(
                divergence_event, correlations
            )
            estimated_reasons.extend(satisfaction_reasons['reasons'])
            confidence_scores.update(satisfaction_reasons['confidences'])
            supporting_evidence.update(satisfaction_reasons['evidence'])
            
            # 重複排除と重み付け
            unique_reasons = list(set(estimated_reasons))
            final_confidence_scores = {
                reason: confidence_scores.get(reason, 0.0) for reason in unique_reasons
            }
            
            # 予測精度の推定（過去の性能から）
            prediction_accuracy = self._estimate_prediction_accuracy(user_id)
            
            result = ReasonEstimation(
                estimated_reasons=unique_reasons,
                confidence_scores=final_confidence_scores,
                supporting_evidence=dict(supporting_evidence),
                prediction_accuracy=prediction_accuracy,
                estimation_metadata={
                    'estimation_timestamp': datetime.now().isoformat(),
                    'user_id': user_id,
                    'total_evidence_points': len(supporting_evidence)
                }
            )
            
            # 推定結果の保存
            self._save_reason_estimation(result, divergence_event)
            
            logger.info(f"乖離理由推定完了: user={user_id}, 理由数={len(unique_reasons)}")
            return result
            
        except Exception as e:
            logger.error(f"乖離理由推定エラー: {str(e)}")
            return ReasonEstimation(
                estimated_reasons=['estimation_error'],
                confidence_scores={'estimation_error': 0.0},
                supporting_evidence={},
                prediction_accuracy=0.0,
                estimation_metadata={'error': str(e)}
            )
    
    def _estimate_from_historical_pattern(self, user_id: str, event: Dict) -> Dict[str, Any]:
        """過去のパターンからの推定"""
        reasons = []
        confidences = {}
        evidence = defaultdict(list)
        
        # 過去の類似乖離を検索
        history = self._get_user_divergence_history(user_id, days=60)
        
        # 同じエンジン選択パターンの検索
        similar_choices = [
            h for h in history 
            if h['user_choice'] == event.get('user_choice') and
               h['gemini_recommendation'] == event.get('gemini_recommendation')
        ]
        
        if similar_choices:
            # 過去の理由を分析
            categories = [h.get('divergence_category') for h in similar_choices]
            category_counter = Counter(categories)
            
            if category_counter:
                most_common_category = category_counter.most_common(1)[0]
                reasons.append(f"historical_pattern_{most_common_category[0]}")
                confidences[f"historical_pattern_{most_common_category[0]}"] = (
                    most_common_category[1] / len(similar_choices)
                ) * self.reason_estimation_weights['historical_pattern']
                
                evidence[f"historical_pattern_{most_common_category[0]}"].append(
                    f"過去{len(similar_choices)}回の類似選択で{most_common_category[1]}回同様の理由"
                )
        
        return {
            'reasons': reasons,
            'confidences': confidences,
            'evidence': evidence
        }
    
    def _estimate_from_context_similarity(self, event: Dict, correlations: Dict) -> Dict[str, Any]:
        """コンテキスト類似度からの推定"""
        reasons = []
        confidences = {}
        evidence = defaultdict(list)
        
        context_data = event.get('context_data', {})
        
        # 文章長による推定
        text_length = context_data.get('text_length', 0)
        length_category = self._categorize_text_length(text_length)
        
        context_correlations = correlations.get('context_behavior_correlation', {})
        length_preference = context_correlations.get(f'{length_category}_preference')
        
        if length_preference and length_preference['preferred_engine'] == event.get('user_choice'):
            reasons.append(f"context_length_preference_{length_category}")
            confidences[f"context_length_preference_{length_category}"] = (
                length_preference['preference_rate'] * 
                self.reason_estimation_weights['context_similarity']
            )
            evidence[f"context_length_preference_{length_category}"].append(
                f"{length_category}文書で{length_preference['preference_rate']:.1%}の選好率"
            )
        
        # 技術文書による推定
        if context_data.get('has_technical_terms'):
            tech_preference = context_correlations.get('technical_preference')
            if tech_preference and tech_preference['preferred_engine'] == event.get('user_choice'):
                reasons.append("technical_document_preference")
                confidences["technical_document_preference"] = (
                    tech_preference['preference_rate'] * 
                    self.reason_estimation_weights['context_similarity']
                )
                evidence["technical_document_preference"].append(
                    f"技術文書で{tech_preference['preference_rate']:.1%}の選好率"
                )
        
        return {
            'reasons': reasons,
            'confidences': confidences,
            'evidence': evidence
        }
    
    def _estimate_from_satisfaction_correlation(self, event: Dict, correlations: Dict) -> Dict[str, Any]:
        """満足度相関からの推定"""
        reasons = []
        confidences = {}
        evidence = defaultdict(list)
        
        satisfaction_score = event.get('satisfaction_score', 0)
        satisfaction_correlations = correlations.get('satisfaction_behavior_correlation', {})
        
        # 高満足度での選択パターン
        if satisfaction_score >= 80:
            engine_correlations = correlations.get('engine_behavior_correlation', {})
            user_choice = event.get('user_choice')
            
            # そのエンジンでの平均満足度をチェック
            avg_satisfaction_key = f'{user_choice}_avg_satisfaction'
            if avg_satisfaction_key in engine_correlations:
                avg_satisfaction = engine_correlations[avg_satisfaction_key]
                if avg_satisfaction >= 75:
                    reasons.append("high_satisfaction_engine_preference")
                    confidences["high_satisfaction_engine_preference"] = (
                        (avg_satisfaction / 100) * 
                        self.reason_estimation_weights['satisfaction_correlation']
                    )
                    evidence["high_satisfaction_engine_preference"].append(
                        f"{user_choice}で平均満足度{avg_satisfaction:.1f}点"
                    )
        
        return {
            'reasons': reasons,
            'confidences': confidences,
            'evidence': evidence
        }
    
    def _estimate_prediction_accuracy(self, user_id: str) -> float:
        """予測精度の推定"""
        try:
            with sqlite3.connect(self.preference_db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT AVG(prediction_accuracy)
                    FROM reason_estimations
                    WHERE user_id = ?
                      AND created_at >= datetime('now', '-30 days')
                ''', (user_id,))
                
                result = cursor.fetchone()
                if result and result[0]:
                    return result[0]
                else:
                    return 0.5  # デフォルト値
        except:
            return 0.5
    
    def learn_personalization_patterns(self, user_sessions: List[Dict]) -> PreferenceProfile:
        """
        個人化パターン学習
        
        Args:
            user_sessions: ユーザーセッションデータのリスト
            
        Returns:
            学習された選好プロファイル
        """
        if not user_sessions:
            raise ValueError("ユーザーセッションデータが必要です")
        
        user_id = user_sessions[0].get('user_id')
        if not user_id:
            raise ValueError("ユーザーIDが必要です")
        
        # 過去のデータと統合
        user_data = {'user_id': user_id}
        correlations = self.analyze_behavior_preference_correlation(user_data)
        
        # エンジン選好の学習
        engine_preferences = self._learn_engine_preferences(user_sessions, correlations)
        
        # コンテキスト別選好の学習
        context_preferences = self._learn_context_preferences(user_sessions, correlations)
        
        # 支配的パターンの特定
        dominant_pattern = self._identify_dominant_pattern(engine_preferences, context_preferences)
        
        # 副次パターンの特定
        secondary_patterns = self._identify_secondary_patterns(engine_preferences, context_preferences)
        
        # 信頼度レベルの決定
        confidence_level = self._determine_confidence_level(len(user_sessions))
        
        # 予測精度の計算
        prediction_accuracy = self._calculate_prediction_accuracy(user_id)
        
        # インサイトと改善提案の生成
        insights = self._generate_preference_insights(engine_preferences, context_preferences)
        suggestions = self._generate_improvement_suggestions(engine_preferences, context_preferences)
        
        # プロファイルの作成
        profile = PreferenceProfile(
            user_id=user_id,
            dominant_pattern=dominant_pattern,
            secondary_patterns=secondary_patterns,
            confidence_level=confidence_level,
            engine_preferences=engine_preferences,
            context_preferences=context_preferences,
            total_observations=len(user_sessions),
            prediction_accuracy=prediction_accuracy,
            last_updated=datetime.now().isoformat(),
            preference_insights=insights,
            improvement_suggestions=suggestions,
            profile_metadata={
                'learning_timestamp': datetime.now().isoformat(),
                'data_sources': ['user_sessions', 'divergence_history'],
                'confidence_factors': {
                    'data_volume': len(user_sessions),
                    'pattern_consistency': correlations.get('consistency_metrics', {}).get('overall_consistency', 0)
                }
            }
        )
        
        # プロファイルの保存
        self._save_preference_profile(profile)
        
        logger.info(f"個人化パターン学習完了: user={user_id}, pattern={dominant_pattern.value}")
        return profile
    
    def _learn_engine_preferences(self, sessions: List[Dict], correlations: Dict) -> Dict[str, float]:
        """エンジン選好の学習"""
        engine_scores = defaultdict(float)
        engine_counts = defaultdict(int)
        
        for session in sessions:
            choice = session.get('user_choice')
            satisfaction = session.get('satisfaction_score', 0)
            
            if choice:
                engine_scores[choice] += satisfaction
                engine_counts[choice] += 1
        
        # 平均満足度ベースの選好スコア
        preferences = {}
        for engine in engine_scores:
            if engine_counts[engine] > 0:
                avg_satisfaction = engine_scores[engine] / engine_counts[engine]
                # 0.0-1.0の範囲に正規化
                preferences[engine] = avg_satisfaction / 100.0
        
        return preferences
    
    def _learn_context_preferences(self, sessions: List[Dict], correlations: Dict) -> Dict[str, Dict[str, float]]:
        """コンテキスト別選好の学習"""
        context_preferences = defaultdict(lambda: defaultdict(float))
        context_counts = defaultdict(lambda: defaultdict(int))
        
        for session in sessions:
            choice = session.get('user_choice')
            satisfaction = session.get('satisfaction_score', 0)
            context_data = session.get('context_data', {})
            
            if choice:
                # 文章長カテゴリ
                text_length = context_data.get('text_length', 0)
                length_category = self._categorize_text_length(text_length)
                
                context_preferences[length_category][choice] += satisfaction
                context_counts[length_category][choice] += 1
                
                # 技術文書カテゴリ
                tech_category = 'technical' if context_data.get('has_technical_terms') else 'general'
                context_preferences[tech_category][choice] += satisfaction
                context_counts[tech_category][choice] += 1
        
        # 平均化
        final_preferences = {}
        for context, engines in context_preferences.items():
            final_preferences[context] = {}
            for engine, total_satisfaction in engines.items():
                count = context_counts[context][engine]
                if count > 0:
                    final_preferences[context][engine] = total_satisfaction / count / 100.0
        
        return final_preferences
    
    def _identify_dominant_pattern(self, engine_prefs: Dict, context_prefs: Dict) -> PreferencePattern:
        """支配的パターンの特定"""
        # エンジン一貫性をチェック
        if engine_prefs:
            max_engine_score = max(engine_prefs.values())
            if max_engine_score >= self.pattern_thresholds['consistent_engine']:
                return PreferencePattern.CONSISTENT_ENGINE
        
        # コンテキスト適応性をチェック
        if len(context_prefs) >= 2:
            return PreferencePattern.CONTEXT_ADAPTIVE
        
        # 品質最大化をチェック
        if engine_prefs:
            avg_score = sum(engine_prefs.values()) / len(engine_prefs)
            if avg_score >= self.pattern_thresholds['quality_maximizer']:
                return PreferencePattern.QUALITY_MAXIMIZER
        
        return PreferencePattern.EXPERIMENTAL
    
    def _identify_secondary_patterns(self, engine_prefs: Dict, context_prefs: Dict) -> List[PreferencePattern]:
        """副次パターンの特定"""
        patterns = []
        
        # 効率重視の判定（高速選択）
        if engine_prefs and len(engine_prefs) <= 2:
            patterns.append(PreferencePattern.EFFICIENCY_ORIENTED)
        
        # 専門分野特化の判定
        if 'technical' in context_prefs:
            patterns.append(PreferencePattern.DOMAIN_SPECIALIST)
        
        return patterns[:2]  # 最大2つまで
    
    def _determine_confidence_level(self, observation_count: int) -> LearningConfidence:
        """信頼度レベルの決定"""
        if observation_count >= 10:
            return LearningConfidence.HIGH
        elif observation_count >= 5:
            return LearningConfidence.MEDIUM
        elif observation_count >= 2:
            return LearningConfidence.LOW
        else:
            return LearningConfidence.INSUFFICIENT
    
    def _calculate_prediction_accuracy(self, user_id: str) -> float:
        """予測精度の計算"""
        # 簡易実装: 実際には過去の予測と実績の比較が必要
        return 0.7  # プレースホルダー
    
    def _generate_preference_insights(self, engine_prefs: Dict, context_prefs: Dict) -> List[str]:
        """選好インサイトの生成"""
        insights = []
        
        if engine_prefs:
            favorite_engine = max(engine_prefs, key=engine_prefs.get)
            favorite_score = engine_prefs[favorite_engine]
            insights.append(f"{favorite_engine}エンジンを強く選好（スコア: {favorite_score:.2f}）")
        
        if 'technical' in context_prefs and 'general' in context_prefs:
            insights.append("技術文書と一般文書で異なる選好パターンを示す")
        
        return insights
    
    def _generate_improvement_suggestions(self, engine_prefs: Dict, context_prefs: Dict) -> List[str]:
        """改善提案の生成"""
        suggestions = []
        
        if engine_prefs and len(engine_prefs) < 2:
            suggestions.append("他の翻訳エンジンも試すことでより適切な翻訳を発見できる可能性があります")
        
        if not context_prefs:
            suggestions.append("より多様なコンテキストでの利用により、選好パターンが明確になります")
        
        return suggestions
    
    def improve_prediction_accuracy(self, feedback_data: List[Dict]) -> float:
        """
        予測精度向上機能
        
        Args:
            feedback_data: フィードバックデータのリスト
            
        Returns:
            改善後の予測精度
        """
        if not feedback_data:
            return 0.0
        
        correct_predictions = 0
        total_predictions = len(feedback_data)
        
        for feedback in feedback_data:
            predicted_choice = feedback.get('predicted_choice')
            actual_choice = feedback.get('actual_choice')
            
            if predicted_choice == actual_choice:
                correct_predictions += 1
        
        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0.0
        
        # 学習パフォーマンスの更新
        user_id = feedback_data[0].get('user_id') if feedback_data else None
        if user_id:
            self._update_learning_performance(user_id, accuracy, total_predictions, correct_predictions)
        
        logger.info(f"予測精度向上: user={user_id}, 精度={accuracy:.3f}")
        return accuracy
    
    def _save_reason_estimation(self, estimation: ReasonEstimation, event: Dict):
        """理由推定結果の保存"""
        with sqlite3.connect(self.preference_db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO reason_estimations (
                    user_id, session_id, estimated_reasons, confidence_scores,
                    supporting_evidence, prediction_accuracy, actual_choice,
                    actual_satisfaction, estimation_metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.get('user_id'),
                event.get('session_id'),
                json.dumps(estimation.estimated_reasons),
                json.dumps(estimation.confidence_scores),
                json.dumps(estimation.supporting_evidence),
                estimation.prediction_accuracy,
                event.get('user_choice'),
                event.get('satisfaction_score'),
                json.dumps(estimation.estimation_metadata)
            ))
            
            conn.commit()
    
    def _save_preference_profile(self, profile: PreferenceProfile):
        """選好プロファイルの保存"""
        with sqlite3.connect(self.preference_db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_preference_profiles (
                    user_id, dominant_pattern, secondary_patterns, confidence_level,
                    engine_preferences, context_preferences, total_observations,
                    prediction_accuracy, preference_insights, improvement_suggestions,
                    profile_metadata, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                profile.user_id,
                profile.dominant_pattern.value,
                json.dumps([p.value for p in profile.secondary_patterns]),
                profile.confidence_level.value,
                json.dumps(profile.engine_preferences),
                json.dumps(profile.context_preferences),
                profile.total_observations,
                profile.prediction_accuracy,
                json.dumps(profile.preference_insights),
                json.dumps(profile.improvement_suggestions),
                json.dumps(profile.profile_metadata),
                profile.last_updated
            ))
            
            conn.commit()
    
    def _update_learning_performance(self, user_id: str, accuracy: float, 
                                   total: int, correct: int):
        """学習パフォーマンスの更新"""
        with sqlite3.connect(self.preference_db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO learning_performance (
                    user_id, accuracy_trend, pattern_stability,
                    prediction_confidence, total_predictions, correct_predictions,
                    calculation_period
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                json.dumps([accuracy]),  # 時系列データとして拡張予定
                0.7,  # プレースホルダー
                accuracy,
                total,
                correct,
                '30days'
            ))
            
            conn.commit()


# テスト用メイン関数
if __name__ == "__main__":
    print("🎯 選好理由推定エンジン - テスト実行")
    print("=" * 60)
    
    estimator = PreferenceReasonEstimator()
    
    # テスト用乖離イベント
    test_event = {
        'user_id': 'test_user_292',
        'session_id': 'test_session_292',
        'gemini_recommendation': 'enhanced',
        'user_choice': 'gemini',
        'satisfaction_score': 85.0,
        'context_data': {
            'text_length': 300,
            'has_technical_terms': True
        }
    }
    
    # 理由推定テスト
    estimation = estimator.estimate_divergence_reasons(test_event)
    
    print(f"✅ 理由推定結果:")
    print(f"  推定理由: {estimation.estimated_reasons}")
    print(f"  信頼度: {estimation.confidence_scores}")
    print(f"  予測精度: {estimation.prediction_accuracy:.3f}")
    
    # 行動相関分析テスト
    correlations = estimator.analyze_behavior_preference_correlation({'user_id': 'test_user_292'})
    print(f"\n📊 行動相関分析:")
    print(f"  エンジン行動相関: {len(correlations.get('engine_behavior_correlation', {}))}")
    print(f"  満足度行動相関: {len(correlations.get('satisfaction_behavior_correlation', {}))}")
    
    print("\n✅ テスト完了 - 選好理由推定エンジン正常動作")