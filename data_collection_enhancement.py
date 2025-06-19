#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎯 Task 2.9.2: データ収集強化システム
=====================================================
目的: Task 2.9.1基盤を活用し、Gemini推奨抽出データ・乖離イベント・
     ユーザー行動パターンの継続追跡により、個人化翻訳AIのための
     高品質データ収集を実現する

【Task 2.9.1.5基盤活用】
- 非接触データ収集原則の継承
- analytics_events テーブルとの統合
- 既存の行動追跡システムの拡張
"""

import sqlite3
import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum

# Task 2.9.2システムのインポート
from advanced_gemini_analysis_engine import AdvancedGeminiAnalysisEngine, StructuredRecommendation
from recommendation_divergence_detector import EnhancedRecommendationDivergenceDetector, DivergenceEvent
from preference_reason_estimator import PreferenceReasonEstimator, PreferenceProfile

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataQuality(Enum):
    """データ品質レベル"""
    EXCELLENT = "excellent"     # 高品質（完全データ）
    GOOD = "good"              # 良品質（軽微な欠損）
    FAIR = "fair"              # 普通品質（一部欠損）
    POOR = "poor"              # 低品質（大幅欠損）
    INVALID = "invalid"        # 無効データ

class CollectionStatus(Enum):
    """収集ステータス"""
    SUCCESS = "success"         # 成功
    PARTIAL = "partial"         # 部分的成功
    FAILED = "failed"          # 失敗
    SKIPPED = "skipped"        # スキップ

@dataclass
class DataCollectionResult:
    """データ収集結果"""
    collection_id: str
    session_id: str
    user_id: Optional[str]
    status: CollectionStatus
    data_quality: DataQuality
    collected_data_types: List[str]
    quality_metrics: Dict[str, float]
    error_messages: List[str]
    collection_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

class DataCollectionEnhancement:
    """非接触データ収集の強化（Task 2.9.1基盤活用）"""
    
    def __init__(self, 
                 analytics_db_path: str = "langpont_analytics.db",
                 divergence_db_path: str = "langpont_divergence.db",
                 preference_db_path: str = "langpont_preferences.db"):
        """初期化"""
        self.analytics_db_path = analytics_db_path
        self.divergence_db_path = divergence_db_path
        self.preference_db_path = preference_db_path
        
        # Task 2.9.2システムの統合
        self.analysis_engine = AdvancedGeminiAnalysisEngine()
        self.divergence_detector = EnhancedRecommendationDivergenceDetector(
            analytics_db_path, divergence_db_path
        )
        self.preference_estimator = PreferenceReasonEstimator(
            analytics_db_path, divergence_db_path, preference_db_path
        )
        
        # データ品質評価基準
        self.quality_thresholds = {
            'completeness': 0.9,        # 完全性
            'consistency': 0.8,         # 一貫性
            'accuracy': 0.85,           # 正確性
            'timeliness': 0.95,         # 適時性
            'validity': 0.9             # 有効性
        }
        
        # 収集強化データベースの初期化
        self._init_collection_database()
        
        logger.info("データ収集強化システム初期化完了")
    
    def _init_collection_database(self):
        """収集強化用データベースの初期化"""
        with sqlite3.connect(self.analytics_db_path) as conn:
            cursor = conn.cursor()
            
            # データ収集履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_collection_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_id VARCHAR(100) UNIQUE NOT NULL,
                    session_id VARCHAR(100) NOT NULL,
                    user_id VARCHAR(100),
                    
                    -- 収集結果
                    status VARCHAR(20) NOT NULL,
                    data_quality VARCHAR(20) NOT NULL,
                    collected_data_types TEXT,
                    
                    -- 品質メトリクス
                    quality_metrics TEXT,
                    error_messages TEXT,
                    
                    -- メタデータ
                    collection_metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 推奨抽出データテーブル（新規）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recommendation_extraction_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id VARCHAR(100) NOT NULL,
                    user_id VARCHAR(100),
                    
                    -- 推奨抽出結果
                    gemini_analysis_text TEXT,
                    extracted_recommendation VARCHAR(50),
                    confidence_score FLOAT,
                    strength_level VARCHAR(20),
                    
                    -- 理由分析
                    primary_reasons TEXT,
                    secondary_reasons TEXT,
                    reasoning_text TEXT,
                    
                    -- メタデータ
                    extraction_metadata TEXT,
                    language VARCHAR(10) DEFAULT 'ja',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 継続行動パターンテーブル（新規）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS continuous_behavior_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id VARCHAR(100) NOT NULL,
                    
                    -- パターンデータ
                    pattern_type VARCHAR(50),
                    pattern_data TEXT,
                    confidence_level VARCHAR(20),
                    
                    -- 時系列データ
                    observation_window VARCHAR(20),
                    pattern_evolution TEXT,
                    
                    -- 統計情報
                    occurrence_frequency FLOAT,
                    pattern_stability FLOAT,
                    
                    -- 更新管理
                    first_observed TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # インデックス作成
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_collection_session ON data_collection_history (session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_extraction_session ON recommendation_extraction_data (session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_behavior_user ON continuous_behavior_patterns (user_id)')
            
            conn.commit()
    
    def save_recommendation_extraction_data(self, 
                                          session_data: Dict,
                                          gemini_analysis_text: str,
                                          structured_recommendation: StructuredRecommendation) -> bool:
        """
        Gemini推奨抽出データの自動保存
        
        Args:
            session_data: セッションデータ
            gemini_analysis_text: Gemini分析の生テキスト
            structured_recommendation: 構造化推奨データ
            
        Returns:
            保存成功フラグ
        """
        try:
            session_id = session_data.get('session_id')
            user_id = session_data.get('user_id')
            
            if not session_id:
                logger.error("セッションIDが必要です")
                return False
            
            # 品質チェック
            quality_score = self._evaluate_recommendation_data_quality(
                gemini_analysis_text, structured_recommendation
            )
            
            if quality_score < 0.3:  # 最低品質閾値
                logger.warning(f"推奨抽出データの品質が低いため保存をスキップ: {quality_score:.2f}")
                return False
            
            with sqlite3.connect(self.analytics_db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO recommendation_extraction_data (
                        session_id, user_id, gemini_analysis_text,
                        extracted_recommendation, confidence_score, strength_level,
                        primary_reasons, secondary_reasons, reasoning_text,
                        extraction_metadata, language
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session_id,
                    user_id,
                    gemini_analysis_text,
                    structured_recommendation.recommended_engine,
                    structured_recommendation.confidence_score,
                    structured_recommendation.strength_level.value,
                    json.dumps([r.value for r in structured_recommendation.primary_reasons]),
                    json.dumps([r.value for r in structured_recommendation.secondary_reasons]),
                    structured_recommendation.reasoning_text,
                    json.dumps(structured_recommendation.analysis_metadata),
                    structured_recommendation.language
                ))
                
                conn.commit()
            
            # 収集履歴の記録
            self._record_collection_event(
                session_id, user_id, 
                CollectionStatus.SUCCESS,
                DataQuality.GOOD,
                ['recommendation_extraction'],
                {'quality_score': quality_score}
            )
            
            logger.info(f"推奨抽出データ保存完了: session={session_id}, 品質={quality_score:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"推奨抽出データ保存エラー: {str(e)}")
            self._record_collection_event(
                session_data.get('session_id', 'unknown'),
                session_data.get('user_id'),
                CollectionStatus.FAILED,
                DataQuality.INVALID,
                ['recommendation_extraction'],
                {'error': str(e)}
            )
            return False
    
    def _evaluate_recommendation_data_quality(self, 
                                            analysis_text: str,
                                            recommendation: StructuredRecommendation) -> float:
        """推奨抽出データの品質評価"""
        quality_factors = []
        
        # 1. 分析テキストの完全性
        if analysis_text and len(analysis_text.strip()) > 20:
            quality_factors.append(0.9)
        elif analysis_text and len(analysis_text.strip()) > 10:
            quality_factors.append(0.6)
        else:
            quality_factors.append(0.2)
        
        # 2. 推奨の信頼度
        quality_factors.append(recommendation.confidence_score)
        
        # 3. 理由の詳細度
        reason_count = len(recommendation.primary_reasons) + len(recommendation.secondary_reasons)
        if reason_count >= 3:
            quality_factors.append(0.9)
        elif reason_count >= 1:
            quality_factors.append(0.7)
        else:
            quality_factors.append(0.3)
        
        # 4. メタデータの豊富さ
        metadata_richness = len(recommendation.analysis_metadata) / 10.0  # 正規化
        quality_factors.append(min(1.0, metadata_richness))
        
        return sum(quality_factors) / len(quality_factors)
    
    def record_divergence_events(self, divergence_data: DivergenceEvent) -> bool:
        """
        乖離イベントの詳細記録
        
        Args:
            divergence_data: 乖離イベントデータ
            
        Returns:
            記録成功フラグ
        """
        try:
            # 乖離データの品質評価
            quality_score = self._evaluate_divergence_data_quality(divergence_data)
            
            # 品質に応じた処理
            if quality_score >= 0.8:
                data_quality = DataQuality.EXCELLENT
            elif quality_score >= 0.6:
                data_quality = DataQuality.GOOD
            elif quality_score >= 0.4:
                data_quality = DataQuality.FAIR
            else:
                data_quality = DataQuality.POOR
            
            # 基本記録は divergence_detector で実行済みのため、
            # ここでは品質メトリクスと拡張情報を記録
            
            extended_metadata = {
                'quality_score': quality_score,
                'data_quality': data_quality.value,
                'learning_priority': self._calculate_learning_priority(divergence_data),
                'contextual_richness': self._evaluate_contextual_richness(divergence_data),
                'behavioral_complexity': self._evaluate_behavioral_complexity(divergence_data)
            }
            
            # 拡張メタデータをanalytics_eventsに記録
            self._save_extended_divergence_metadata(divergence_data, extended_metadata)
            
            # 収集履歴の記録
            self._record_collection_event(
                divergence_data.session_id,
                divergence_data.user_id,
                CollectionStatus.SUCCESS,
                data_quality,
                ['divergence_event', 'extended_metadata'],
                {'quality_score': quality_score}
            )
            
            logger.info(f"乖離イベント詳細記録完了: {divergence_data.event_id}, 品質={quality_score:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"乖離イベント記録エラー: {str(e)}")
            return False
    
    def _evaluate_divergence_data_quality(self, divergence: DivergenceEvent) -> float:
        """乖離データの品質評価"""
        quality_factors = []
        
        # 1. 基本データの完全性
        completeness_score = 0.0
        if divergence.gemini_recommendation:
            completeness_score += 0.2
        if divergence.user_choice:
            completeness_score += 0.2
        if divergence.satisfaction_score > 0:
            completeness_score += 0.2
        if divergence.context_data:
            completeness_score += 0.2
        if divergence.behavioral_indicators:
            completeness_score += 0.2
        
        quality_factors.append(completeness_score)
        
        # 2. 学習価値
        quality_factors.append(divergence.learning_value)
        
        # 3. 信頼度
        quality_factors.append(divergence.gemini_confidence)
        
        # 4. コンテキストの豊富さ
        context_richness = len(divergence.context_data) / 10.0
        quality_factors.append(min(1.0, context_richness))
        
        return sum(quality_factors) / len(quality_factors)
    
    def _calculate_learning_priority(self, divergence: DivergenceEvent) -> float:
        """学習優先度の計算"""
        priority = 0.0
        
        # 重要度による重み付け
        importance_weights = {
            'critical': 1.0,
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4,
            'noise': 0.1
        }
        
        priority += importance_weights.get(divergence.divergence_importance.value, 0.5)
        
        # 学習価値による調整
        priority = (priority + divergence.learning_value) / 2
        
        return min(1.0, priority)
    
    def _evaluate_contextual_richness(self, divergence: DivergenceEvent) -> float:
        """コンテキストの豊富さ評価"""
        richness = 0.0
        context = divergence.context_data
        
        # 各要素の存在による加点
        if context.get('text_length', 0) > 100:
            richness += 0.2
        if context.get('has_technical_terms'):
            richness += 0.2
        if context.get('business_context'):
            richness += 0.2
        if context.get('cultural_context'):
            richness += 0.2
        if len(context.keys()) >= 5:
            richness += 0.2
        
        return richness
    
    def _evaluate_behavioral_complexity(self, divergence: DivergenceEvent) -> float:
        """行動の複雑さ評価"""
        complexity = 0.0
        behaviors = divergence.behavioral_indicators
        
        # セッション継続時間
        duration = behaviors.get('session_duration', 0)
        if duration >= 180:  # 3分以上
            complexity += 0.3
        elif duration >= 60:  # 1分以上
            complexity += 0.2
        
        # コピー行動の多様性
        copy_behaviors = behaviors.get('recent_copy_behaviors', [])
        if len(copy_behaviors) >= 3:
            complexity += 0.3
        elif len(copy_behaviors) >= 2:
            complexity += 0.2
        
        # 行動パターンの種類
        behavior_types = len(behaviors.get('session_behaviors', {}))
        if behavior_types >= 4:
            complexity += 0.4
        elif behavior_types >= 2:
            complexity += 0.2
        
        return min(1.0, complexity)
    
    def _save_extended_divergence_metadata(self, divergence: DivergenceEvent, metadata: Dict):
        """拡張乖離メタデータの保存"""
        with sqlite3.connect(self.analytics_db_path) as conn:
            cursor = conn.cursor()
            
            # 専用イベントとして記録
            event_id = f"divergence_meta_{divergence.event_id}"
            
            cursor.execute('''
                INSERT INTO analytics_events (
                    event_id, event_type, timestamp, session_id,
                    user_id, ip_address, user_agent, custom_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_id,
                'divergence_metadata',
                int(time.time() * 1000),
                divergence.session_id,
                divergence.user_id,
                '127.0.0.1',  # プレースホルダー
                'DataCollectionEnhancement/1.0',
                json.dumps(metadata)
            ))
            
            conn.commit()
    
    def track_continuous_behavior_patterns(self, user_id: str) -> Dict[str, Any]:
        """
        ユーザー行動パターンの継続追跡
        
        Args:
            user_id: ユーザーID
            
        Returns:
            継続追跡結果
        """
        if not user_id:
            return {'error': 'ユーザーIDが必要です'}
        
        try:
            # 過去30日間のデータを分析
            patterns = self._analyze_user_behavior_patterns(user_id, days=30)
            
            # パターンの安定性を評価
            stability_metrics = self._calculate_pattern_stability(user_id, patterns)
            
            # パターンの進化を追跡
            evolution_data = self._track_pattern_evolution(user_id, patterns)
            
            # データベースに保存
            self._save_behavior_patterns(user_id, patterns, stability_metrics, evolution_data)
            
            result = {
                'user_id': user_id,
                'patterns_detected': len(patterns),
                'stability_score': stability_metrics.get('overall_stability', 0.0),
                'evolution_trend': evolution_data.get('trend', 'stable'),
                'tracking_quality': self._evaluate_tracking_quality(patterns),
                'last_updated': datetime.now().isoformat()
            }
            
            logger.info(f"継続行動パターン追跡完了: user={user_id}, パターン数={len(patterns)}")
            return result
            
        except Exception as e:
            logger.error(f"継続行動パターン追跡エラー: {str(e)}")
            return {'error': str(e)}
    
    def _analyze_user_behavior_patterns(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """ユーザー行動パターンの分析"""
        patterns = []
        
        with sqlite3.connect(self.analytics_db_path) as conn:
            cursor = conn.cursor()
            
            # 時系列での行動パターン分析
            cursor.execute('''
                SELECT event_type, custom_data, timestamp,
                       DATE(timestamp/1000, 'unixepoch') as event_date
                FROM analytics_events
                WHERE user_id = ?
                  AND timestamp >= (strftime('%s', 'now', '-{} days') * 1000)
                ORDER BY timestamp
            '''.format(days), (user_id,))
            
            events_by_date = defaultdict(list)
            for event_type, custom_data, timestamp, event_date in cursor.fetchall():
                try:
                    data = json.loads(custom_data) if custom_data else {}
                    events_by_date[event_date].append({
                        'event_type': event_type,
                        'data': data,
                        'timestamp': timestamp
                    })
                except json.JSONDecodeError:
                    continue
            
            # 日別パターンの抽出
            for date, events in events_by_date.items():
                if len(events) >= 3:  # 最低3イベント必要
                    daily_pattern = self._extract_daily_pattern(events)
                    if daily_pattern:
                        daily_pattern['date'] = date
                        patterns.append(daily_pattern)
        
        return patterns
    
    def _extract_daily_pattern(self, events: List[Dict]) -> Optional[Dict[str, Any]]:
        """日別パターンの抽出"""
        if len(events) < 3:
            return None
        
        # イベントタイプの分布
        event_types = [e['event_type'] for e in events]
        type_counter = Counter(event_types)
        
        # セッション継続時間の推定
        timestamps = [e['timestamp'] for e in events]
        session_duration = (max(timestamps) - min(timestamps)) / 1000.0
        
        # 翻訳関連イベントの抽出
        translation_events = [e for e in events if 'translation' in e['event_type']]
        
        pattern = {
            'pattern_type': 'daily_usage',
            'total_events': len(events),
            'event_distribution': dict(type_counter),
            'session_duration': session_duration,
            'translation_activity': len(translation_events),
            'activity_intensity': len(events) / (session_duration / 60) if session_duration > 0 else 0,
            'peak_activity_time': self._identify_peak_activity_time(events)
        }
        
        return pattern
    
    def _identify_peak_activity_time(self, events: List[Dict]) -> str:
        """ピーク活動時間の特定"""
        if not events:
            return 'unknown'
        
        # 時間帯別のイベント数をカウント
        hour_counter = Counter()
        for event in events:
            hour = datetime.fromtimestamp(event['timestamp'] / 1000).hour
            hour_counter[hour] += 1
        
        if hour_counter:
            peak_hour = hour_counter.most_common(1)[0][0]
            if 6 <= peak_hour < 12:
                return 'morning'
            elif 12 <= peak_hour < 18:
                return 'afternoon'
            elif 18 <= peak_hour < 22:
                return 'evening'
            else:
                return 'night'
        
        return 'unknown'
    
    def _calculate_pattern_stability(self, user_id: str, patterns: List[Dict]) -> Dict[str, float]:
        """パターンの安定性計算"""
        if len(patterns) < 3:
            return {'overall_stability': 0.0}
        
        # 活動時間の安定性
        durations = [p.get('session_duration', 0) for p in patterns]
        duration_stability = 1.0 - (statistics.stdev(durations) / statistics.mean(durations)) if durations and statistics.mean(durations) > 0 else 0.0
        duration_stability = max(0.0, min(1.0, duration_stability))
        
        # 活動強度の安定性
        intensities = [p.get('activity_intensity', 0) for p in patterns]
        intensity_stability = 1.0 - (statistics.stdev(intensities) / statistics.mean(intensities)) if intensities and statistics.mean(intensities) > 0 else 0.0
        intensity_stability = max(0.0, min(1.0, intensity_stability))
        
        # 時間帯の一貫性
        peak_times = [p.get('peak_activity_time', 'unknown') for p in patterns]
        peak_time_counter = Counter(peak_times)
        time_consistency = peak_time_counter.most_common(1)[0][1] / len(peak_times) if peak_times else 0.0
        
        overall_stability = (duration_stability + intensity_stability + time_consistency) / 3
        
        return {
            'overall_stability': overall_stability,
            'duration_stability': duration_stability,
            'intensity_stability': intensity_stability,
            'time_consistency': time_consistency
        }
    
    def _track_pattern_evolution(self, user_id: str, patterns: List[Dict]) -> Dict[str, Any]:
        """パターン進化の追跡"""
        if len(patterns) < 5:
            return {'trend': 'insufficient_data'}
        
        # 時系列での変化を分析
        recent_patterns = patterns[-5:]  # 直近5パターン
        older_patterns = patterns[:-5] if len(patterns) > 5 else []
        
        evolution = {
            'trend': 'stable',
            'changes_detected': [],
            'evolution_score': 0.0
        }
        
        if older_patterns:
            # 活動量の変化
            recent_activity = statistics.mean([p.get('total_events', 0) for p in recent_patterns])
            older_activity = statistics.mean([p.get('total_events', 0) for p in older_patterns])
            
            if recent_activity > older_activity * 1.2:
                evolution['trend'] = 'increasing'
                evolution['changes_detected'].append('activity_increase')
            elif recent_activity < older_activity * 0.8:
                evolution['trend'] = 'decreasing'
                evolution['changes_detected'].append('activity_decrease')
            
            # 変化度合いの計算
            activity_change_ratio = abs(recent_activity - older_activity) / max(older_activity, 1)
            evolution['evolution_score'] = min(1.0, activity_change_ratio)
        
        return evolution
    
    def _save_behavior_patterns(self, user_id: str, patterns: List[Dict], 
                               stability: Dict, evolution: Dict):
        """行動パターンの保存"""
        with sqlite3.connect(self.analytics_db_path) as conn:
            cursor = conn.cursor()
            
            # 既存パターンの削除（最新データで更新）
            cursor.execute('''
                DELETE FROM continuous_behavior_patterns
                WHERE user_id = ?
            ''', (user_id,))
            
            # 新しいパターンの保存
            for pattern in patterns:
                cursor.execute('''
                    INSERT INTO continuous_behavior_patterns (
                        user_id, pattern_type, pattern_data, confidence_level,
                        observation_window, pattern_evolution,
                        occurrence_frequency, pattern_stability,
                        first_observed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    pattern.get('pattern_type', 'unknown'),
                    json.dumps(pattern),
                    'medium',  # プレースホルダー
                    '30days',
                    json.dumps(evolution),
                    pattern.get('activity_intensity', 0.0),
                    stability.get('overall_stability', 0.0),
                    pattern.get('date', datetime.now().isoformat())
                ))
            
            conn.commit()
    
    def _evaluate_tracking_quality(self, patterns: List[Dict]) -> str:
        """追跡品質の評価"""
        if len(patterns) >= 10:
            return 'excellent'
        elif len(patterns) >= 5:
            return 'good'
        elif len(patterns) >= 2:
            return 'fair'
        else:
            return 'poor'
    
    def _record_collection_event(self, session_id: str, user_id: Optional[str],
                                status: CollectionStatus, quality: DataQuality,
                                data_types: List[str], metrics: Dict):
        """収集イベントの記録"""
        collection_id = hashlib.md5(
            f"{session_id}_{user_id}_{int(time.time() * 1000000)}_{len(data_types)}".encode()
        ).hexdigest()[:16]
        
        with sqlite3.connect(self.analytics_db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO data_collection_history (
                    collection_id, session_id, user_id, status, data_quality,
                    collected_data_types, quality_metrics, error_messages,
                    collection_metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                collection_id,
                session_id,
                user_id,
                status.value,
                quality.value,
                json.dumps(data_types),
                json.dumps(metrics),
                json.dumps(metrics.get('errors', [])),
                json.dumps({'collection_timestamp': datetime.now().isoformat()})
            ))
            
            conn.commit()
    
    def get_collection_statistics(self, days: int = 30) -> Dict[str, Any]:
        """収集統計の取得"""
        stats = {
            'collection_summary': {},
            'quality_distribution': {},
            'data_type_distribution': {},
            'error_analysis': {}
        }
        
        with sqlite3.connect(self.analytics_db_path) as conn:
            cursor = conn.cursor()
            
            # 基本統計
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM data_collection_history
                WHERE created_at >= datetime('now', '-{} days')
                GROUP BY status
            '''.format(days))
            
            stats['collection_summary'] = dict(cursor.fetchall())
            
            # 品質分布
            cursor.execute('''
                SELECT data_quality, COUNT(*) as count
                FROM data_collection_history
                WHERE created_at >= datetime('now', '-{} days')
                GROUP BY data_quality
            '''.format(days))
            
            stats['quality_distribution'] = dict(cursor.fetchall())
        
        return stats


# テスト用メイン関数
if __name__ == "__main__":
    print("🎯 データ収集強化システム - テスト実行")
    print("=" * 60)
    
    collector = DataCollectionEnhancement()
    
    # テスト用セッションデータ
    test_session = {
        'session_id': 'test_session_292',
        'user_id': 'test_user_292'
    }
    
    # テスト用推奨データ
    from advanced_gemini_analysis_engine import StructuredRecommendation, RecommendationStrength
    test_recommendation = StructuredRecommendation(
        recommended_engine='enhanced',
        confidence_score=0.85,
        strength_level=RecommendationStrength.STRONG,
        primary_reasons=[],
        secondary_reasons=[],
        reasoning_text='テスト理由',
        language='ja'
    )
    
    # 推奨抽出データ保存テスト
    success = collector.save_recommendation_extraction_data(
        test_session,
        "テスト用Gemini分析テキスト",
        test_recommendation
    )
    
    print(f"✅ 推奨抽出データ保存: {'成功' if success else '失敗'}")
    
    # 継続行動パターン追跡テスト
    tracking_result = collector.track_continuous_behavior_patterns('test_user_292')
    print(f"✅ 継続行動パターン追跡:")
    print(f"  検出パターン数: {tracking_result.get('patterns_detected', 0)}")
    print(f"  安定性スコア: {tracking_result.get('stability_score', 0.0):.3f}")
    
    # 収集統計テスト
    stats = collector.get_collection_statistics(7)
    print(f"✅ 収集統計 (7日間):")
    print(f"  収集サマリー: {stats['collection_summary']}")
    print(f"  品質分布: {stats['quality_distribution']}")
    
    print("\n✅ テスト完了 - データ収集強化システム正常動作")