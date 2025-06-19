#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🚀 Task 2.9.2 Phase B-2: 高度な分析機能とリアルタイム監視
================================================================
目的: Task 2.9.2システムの詳細監視とデータ収集強化
機能: 推奨抽出精度分析、API監視、個人化データ収集
"""

import logging
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
import time
import os
import threading
from dataclasses import dataclass, field

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Task292Metrics:
    """Task 2.9.2 メトリクス"""
    total_extractions: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    llm_successes: int = 0
    llm_failures: int = 0
    api_errors: int = 0
    average_confidence: float = 0.0
    extraction_methods: Dict[str, int] = field(default_factory=dict)
    recommendations: Dict[str, int] = field(default_factory=dict)
    language_distribution: Dict[str, int] = field(default_factory=dict)
    error_patterns: Dict[str, int] = field(default_factory=dict)
    
class AdvancedDashboardAnalytics:
    """高度な分析機能とリアルタイム監視システム"""
    
    def __init__(self, db_path: str = "task292_analytics.db"):
        """初期化"""
        self.db_path = db_path
        self.lock = threading.Lock()
        
        # リアルタイムメトリクス
        self.current_metrics = Task292Metrics()
        
        # API使用統計
        self.api_stats = {
            'openai': {
                'total_calls': 0,
                'successful_calls': 0,
                'failed_calls': 0,
                'total_duration_ms': 0,
                'average_duration_ms': 0,
                'error_types': defaultdict(int)
            },
            'gemini': {
                'total_calls': 0,
                'successful_calls': 0,
                'failed_calls': 0,
                'total_duration_ms': 0,
                'average_duration_ms': 0,
                'error_types': defaultdict(int)
            }
        }
        
        # アラート設定
        self.alert_thresholds = {
            'error_rate': 0.2,  # 20%以上のエラー率でアラート
            'api_response_time': 3000,  # 3秒以上でアラート
            'extraction_failure_rate': 0.3,  # 30%以上の失敗率でアラート
            'low_confidence_rate': 0.5  # 50%以上が低信頼度でアラート
        }
        
        # アクティブアラート
        self.active_alerts = []
        
        # 個人化データ収集
        self.personalization_data = defaultdict(lambda: {
            'translation_preferences': Counter(),
            'language_pairs': Counter(),
            'rejection_patterns': [],
            'style_preferences': {},
            'interaction_count': 0
        })
        
        self._init_database()
        logger.info("🚀 Phase B-2: 高度な分析システム初期化完了")
    
    def _init_database(self):
        """データベース初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Task 2.9.2 推奨抽出詳細ログ
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS task292_extraction_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        session_id TEXT,
                        user_id TEXT,
                        input_text TEXT,
                        analysis_language TEXT,
                        extraction_method TEXT,
                        recommendation TEXT,
                        confidence REAL,
                        processing_time_ms INTEGER,
                        success BOOLEAN,
                        error_details TEXT,
                        llm_response TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # API監視ログ
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS api_monitoring (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        api_provider TEXT NOT NULL,
                        endpoint TEXT,
                        method TEXT,
                        status_code INTEGER,
                        response_time_ms INTEGER,
                        success BOOLEAN,
                        error_type TEXT,
                        error_message TEXT,
                        request_size INTEGER,
                        response_size INTEGER,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 個人化データ収集
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS personalization_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        event_type TEXT,
                        gemini_recommendation TEXT,
                        user_choice TEXT,
                        rejection_reason TEXT,
                        language_pair TEXT,
                        translation_context TEXT,
                        style_attributes TEXT,
                        confidence_score REAL,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # アラート履歴
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS alert_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        alert_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT,
                        metric_value REAL,
                        threshold_value REAL,
                        resolved BOOLEAN DEFAULT 0,
                        resolved_at TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # インデックス作成
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_task292_timestamp ON task292_extraction_logs(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_task292_user ON task292_extraction_logs(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_timestamp ON api_monitoring(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_personalization_user ON personalization_data(user_id)")
                
                conn.commit()
                logger.info("📊 Task 2.9.2 分析データベース初期化完了")
                
        except Exception as e:
            logger.error(f"❌ データベース初期化エラー: {str(e)}")
    
    def log_task292_extraction(self, session_id: str, user_id: str, input_text: str,
                              analysis_language: str, method: str, recommendation: Optional[str],
                              confidence: float, processing_time_ms: int, success: bool,
                              error_details: str = "", llm_response: str = "",
                              metadata: Dict[str, Any] = None):
        """Task 2.9.2 推奨抽出の詳細ログ記録"""
        try:
            timestamp = datetime.now().isoformat()
            
            # リアルタイムメトリクス更新
            with self.lock:
                self.current_metrics.total_extractions += 1
                if success:
                    self.current_metrics.successful_extractions += 1
                    if method.startswith("llm"):
                        self.current_metrics.llm_successes += 1
                else:
                    self.current_metrics.failed_extractions += 1
                    if method.startswith("llm"):
                        self.current_metrics.llm_failures += 1
                    if "api" in error_details.lower():
                        self.current_metrics.api_errors += 1
                
                # メソッド統計
                self.current_metrics.extraction_methods[method] = \
                    self.current_metrics.extraction_methods.get(method, 0) + 1
                
                # 推奨統計
                if recommendation:
                    self.current_metrics.recommendations[recommendation] = \
                        self.current_metrics.recommendations.get(recommendation, 0) + 1
                
                # 言語分布
                self.current_metrics.language_distribution[analysis_language] = \
                    self.current_metrics.language_distribution.get(analysis_language, 0) + 1
                
                # エラーパターン
                if not success and error_details:
                    error_key = error_details.split(':')[0] if ':' in error_details else error_details
                    self.current_metrics.error_patterns[error_key] = \
                        self.current_metrics.error_patterns.get(error_key, 0) + 1
                
                # 平均信頼度更新
                if success and confidence > 0:
                    total_conf = self.current_metrics.average_confidence * (self.current_metrics.successful_extractions - 1)
                    self.current_metrics.average_confidence = (total_conf + confidence) / self.current_metrics.successful_extractions
            
            # データベースに保存
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO task292_extraction_logs 
                    (timestamp, session_id, user_id, input_text, analysis_language,
                     extraction_method, recommendation, confidence, processing_time_ms,
                     success, error_details, llm_response, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp, session_id, user_id, input_text[:500], analysis_language,
                    method, recommendation, confidence, processing_time_ms,
                    success, error_details, llm_response[:1000] if llm_response else "",
                    json.dumps(metadata) if metadata else None
                ))
                conn.commit()
            
            # アラートチェック
            self._check_extraction_alerts()
            
            logger.info(f"📊 Task 2.9.2 抽出ログ記録: method={method}, success={success}, confidence={confidence}")
            
        except Exception as e:
            logger.error(f"❌ Task 2.9.2 ログ記録エラー: {str(e)}")
    
    def log_api_call(self, api_provider: str, endpoint: str, method: str,
                     status_code: int, response_time_ms: int, success: bool,
                     error_type: str = "", error_message: str = "",
                     request_size: int = 0, response_size: int = 0,
                     metadata: Dict[str, Any] = None):
        """API呼び出しの監視ログ記録"""
        try:
            timestamp = datetime.now().isoformat()
            
            # API統計更新
            with self.lock:
                api_stat = self.api_stats[api_provider]
                api_stat['total_calls'] += 1
                
                if success:
                    api_stat['successful_calls'] += 1
                else:
                    api_stat['failed_calls'] += 1
                    if error_type:
                        api_stat['error_types'][error_type] += 1
                
                # 平均応答時間更新
                api_stat['total_duration_ms'] += response_time_ms
                api_stat['average_duration_ms'] = api_stat['total_duration_ms'] / api_stat['total_calls']
            
            # データベースに保存
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO api_monitoring
                    (timestamp, api_provider, endpoint, method, status_code,
                     response_time_ms, success, error_type, error_message,
                     request_size, response_size, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp, api_provider, endpoint, method, status_code,
                    response_time_ms, success, error_type, error_message,
                    request_size, response_size,
                    json.dumps(metadata) if metadata else None
                ))
                conn.commit()
            
            # APIアラートチェック
            self._check_api_alerts(api_provider, response_time_ms)
            
        except Exception as e:
            logger.error(f"❌ API監視ログエラー: {str(e)}")
    
    def log_personalization_event(self, user_id: str, event_type: str,
                                 gemini_recommendation: Optional[str],
                                 user_choice: Optional[str],
                                 language_pair: str,
                                 translation_context: str = "",
                                 style_attributes: Dict[str, Any] = None,
                                 confidence_score: float = 0.0,
                                 rejection_reason: str = "",
                                 metadata: Dict[str, Any] = None):
        """個人化データ収集イベント記録"""
        try:
            timestamp = datetime.now().isoformat()
            
            # メモリ内個人化データ更新
            with self.lock:
                user_data = self.personalization_data[user_id]
                user_data['interaction_count'] += 1
                
                # 翻訳選好記録
                if user_choice:
                    user_data['translation_preferences'][user_choice] += 1
                
                # 言語ペア記録
                user_data['language_pairs'][language_pair] += 1
                
                # 拒否パターン記録
                if event_type == 'rejection' and rejection_reason:
                    user_data['rejection_patterns'].append({
                        'timestamp': timestamp,
                        'recommendation': gemini_recommendation,
                        'reason': rejection_reason
                    })
                
                # スタイル選好更新
                if style_attributes:
                    for attr, value in style_attributes.items():
                        if attr not in user_data['style_preferences']:
                            user_data['style_preferences'][attr] = Counter()
                        user_data['style_preferences'][attr][value] += 1
            
            # データベースに保存
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO personalization_data
                    (user_id, timestamp, event_type, gemini_recommendation,
                     user_choice, rejection_reason, language_pair,
                     translation_context, style_attributes, confidence_score, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, timestamp, event_type, gemini_recommendation,
                    user_choice, rejection_reason, language_pair,
                    translation_context[:500],
                    json.dumps(style_attributes) if style_attributes else None,
                    confidence_score,
                    json.dumps(metadata) if metadata else None
                ))
                conn.commit()
            
            logger.info(f"📊 個人化イベント記録: user={user_id}, type={event_type}")
            
        except Exception as e:
            logger.error(f"❌ 個人化データ記録エラー: {str(e)}")
    
    def _check_extraction_alerts(self):
        """推奨抽出関連のアラートチェック"""
        try:
            with self.lock:
                # エラー率チェック
                if self.current_metrics.total_extractions > 10:
                    error_rate = self.current_metrics.failed_extractions / self.current_metrics.total_extractions
                    if error_rate > self.alert_thresholds['extraction_failure_rate']:
                        self._create_alert(
                            alert_type='high_extraction_failure_rate',
                            severity='WARNING',
                            message=f'推奨抽出失敗率が閾値を超過: {error_rate:.2%}',
                            metric_value=error_rate,
                            threshold_value=self.alert_thresholds['extraction_failure_rate']
                        )
                
                # 低信頼度チェック
                if self.current_metrics.successful_extractions > 10:
                    if self.current_metrics.average_confidence < 0.5:
                        self._create_alert(
                            alert_type='low_confidence_extractions',
                            severity='INFO',
                            message=f'平均信頼度が低下: {self.current_metrics.average_confidence:.2f}',
                            metric_value=self.current_metrics.average_confidence,
                            threshold_value=0.5
                        )
                        
        except Exception as e:
            logger.error(f"❌ アラートチェックエラー: {str(e)}")
    
    def _check_api_alerts(self, api_provider: str, response_time_ms: int):
        """API関連のアラートチェック"""
        try:
            # 応答時間チェック
            if response_time_ms > self.alert_thresholds['api_response_time']:
                self._create_alert(
                    alert_type='slow_api_response',
                    severity='WARNING',
                    message=f'{api_provider} API応答時間が閾値を超過: {response_time_ms}ms',
                    metric_value=response_time_ms,
                    threshold_value=self.alert_thresholds['api_response_time']
                )
            
            # エラー率チェック
            with self.lock:
                api_stat = self.api_stats[api_provider]
                if api_stat['total_calls'] > 10:
                    error_rate = api_stat['failed_calls'] / api_stat['total_calls']
                    if error_rate > self.alert_thresholds['error_rate']:
                        self._create_alert(
                            alert_type='high_api_error_rate',
                            severity='CRITICAL',
                            message=f'{api_provider} APIエラー率が閾値を超過: {error_rate:.2%}',
                            metric_value=error_rate,
                            threshold_value=self.alert_thresholds['error_rate']
                        )
                        
        except Exception as e:
            logger.error(f"❌ APIアラートチェックエラー: {str(e)}")
    
    def _create_alert(self, alert_type: str, severity: str, message: str,
                     metric_value: float, threshold_value: float,
                     metadata: Dict[str, Any] = None):
        """アラート作成"""
        try:
            timestamp = datetime.now().isoformat()
            
            # アクティブアラートに追加
            alert = {
                'timestamp': timestamp,
                'alert_type': alert_type,
                'severity': severity,
                'message': message,
                'metric_value': metric_value,
                'threshold_value': threshold_value,
                'resolved': False
            }
            
            with self.lock:
                self.active_alerts.append(alert)
                # 最新20件のみ保持
                if len(self.active_alerts) > 20:
                    self.active_alerts = self.active_alerts[-20:]
            
            # データベースに保存
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO alert_history
                    (timestamp, alert_type, severity, message,
                     metric_value, threshold_value, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp, alert_type, severity, message,
                    metric_value, threshold_value,
                    json.dumps(metadata) if metadata else None
                ))
                conn.commit()
            
            logger.warning(f"🚨 アラート発生: {severity} - {message}")
            
        except Exception as e:
            logger.error(f"❌ アラート作成エラー: {str(e)}")
    
    def get_task292_metrics(self) -> Dict[str, Any]:
        """Task 2.9.2 メトリクス取得"""
        with self.lock:
            return {
                'total_extractions': self.current_metrics.total_extractions,
                'successful_extractions': self.current_metrics.successful_extractions,
                'failed_extractions': self.current_metrics.failed_extractions,
                'success_rate': (self.current_metrics.successful_extractions / 
                               self.current_metrics.total_extractions * 100) 
                               if self.current_metrics.total_extractions > 0 else 0,
                'average_confidence': self.current_metrics.average_confidence,
                'llm_success_rate': (self.current_metrics.llm_successes / 
                                   (self.current_metrics.llm_successes + self.current_metrics.llm_failures) * 100)
                                   if (self.current_metrics.llm_successes + self.current_metrics.llm_failures) > 0 else 0,
                'extraction_methods': dict(self.current_metrics.extraction_methods),
                'recommendations': dict(self.current_metrics.recommendations),
                'language_distribution': dict(self.current_metrics.language_distribution),
                'error_patterns': dict(self.current_metrics.error_patterns),
                'api_errors': self.current_metrics.api_errors
            }
    
    def get_api_statistics(self) -> Dict[str, Any]:
        """API統計取得"""
        with self.lock:
            return {
                'openai': {
                    'total_calls': self.api_stats['openai']['total_calls'],
                    'success_rate': (self.api_stats['openai']['successful_calls'] /
                                   self.api_stats['openai']['total_calls'] * 100)
                                   if self.api_stats['openai']['total_calls'] > 0 else 0,
                    'average_response_time': self.api_stats['openai']['average_duration_ms'],
                    'error_types': dict(self.api_stats['openai']['error_types'])
                },
                'gemini': {
                    'total_calls': self.api_stats['gemini']['total_calls'],
                    'success_rate': (self.api_stats['gemini']['successful_calls'] /
                                   self.api_stats['gemini']['total_calls'] * 100)
                                   if self.api_stats['gemini']['total_calls'] > 0 else 0,
                    'average_response_time': self.api_stats['gemini']['average_duration_ms'],
                    'error_types': dict(self.api_stats['gemini']['error_types'])
                }
            }
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """アクティブアラート取得"""
        with self.lock:
            return list(self.active_alerts)
    
    def get_personalization_insights(self, user_id: str) -> Dict[str, Any]:
        """ユーザー個人化インサイト取得"""
        with self.lock:
            user_data = self.personalization_data.get(user_id, {})
            
            if not user_data or user_data.get('interaction_count', 0) == 0:
                return {'available': False}
            
            # 最も好まれる翻訳エンジン
            preferred_engine = None
            if user_data.get('translation_preferences'):
                preferred_engine = user_data['translation_preferences'].most_common(1)[0]
            
            # 最も使用される言語ペア
            top_language_pair = None
            if user_data.get('language_pairs'):
                top_language_pair = user_data['language_pairs'].most_common(1)[0]
            
            return {
                'available': True,
                'interaction_count': user_data.get('interaction_count', 0),
                'preferred_engine': preferred_engine,
                'top_language_pair': top_language_pair,
                'style_preferences': dict(user_data.get('style_preferences', {})),
                'rejection_patterns': len(user_data.get('rejection_patterns', []))
            }
    
    def get_extraction_history(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """推奨抽出履歴取得"""
        try:
            since_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp, user_id, analysis_language, extraction_method,
                           recommendation, confidence, processing_time_ms, success,
                           error_details
                    FROM task292_extraction_logs
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (since_time, limit))
                
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"❌ 抽出履歴取得エラー: {str(e)}")
            return []
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """古いデータのクリーンアップ"""
        try:
            cutoff_time = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                tables = ['task292_extraction_logs', 'api_monitoring', 
                         'personalization_data', 'alert_history']
                
                for table in tables:
                    cursor.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff_time,))
                
                conn.commit()
                logger.info(f"🧹 {days_to_keep}日以前のデータをクリーンアップしました")
                
        except Exception as e:
            logger.error(f"❌ データクリーンアップエラー: {str(e)}")

# グローバルインスタンス
advanced_analytics = AdvancedDashboardAnalytics()

# テスト関数
def test_advanced_analytics():
    """高度な分析システムのテスト"""
    print("🧪 Phase B-2: 高度な分析システムテスト開始")
    print("=" * 60)
    
    # テストデータ生成
    test_user_id = "test_user_001"
    test_session_id = "test_session_001"
    
    # 1. Task 2.9.2 推奨抽出ログテスト
    print("\n📝 Test 1: Task 2.9.2 推奨抽出ログ")
    advanced_analytics.log_task292_extraction(
        session_id=test_session_id,
        user_id=test_user_id,
        input_text="これはテスト翻訳テキストです。",
        analysis_language="Japanese",
        method="llm_chatgpt_a8",
        recommendation="enhanced",
        confidence=0.95,
        processing_time_ms=1200,
        success=True,
        metadata={'test': True}
    )
    print("✅ 成功ケースログ記録")
    
    # 失敗ケース
    advanced_analytics.log_task292_extraction(
        session_id=test_session_id,
        user_id=test_user_id,
        input_text="エラーテストケース",
        analysis_language="Japanese",
        method="llm_chatgpt_a8",
        recommendation=None,
        confidence=0.0,
        processing_time_ms=5000,
        success=False,
        error_details="api_timeout: Request timeout after 5s"
    )
    print("✅ 失敗ケースログ記録")
    
    # 2. API監視ログテスト
    print("\n📝 Test 2: API監視ログ")
    advanced_analytics.log_api_call(
        api_provider="openai",
        endpoint="/v1/chat/completions",
        method="POST",
        status_code=200,
        response_time_ms=850,
        success=True,
        request_size=1024,
        response_size=2048
    )
    
    # 遅いAPIレスポンス（アラート発生）
    advanced_analytics.log_api_call(
        api_provider="gemini",
        endpoint="/v1beta/models/gemini-1.5-pro:generateContent",
        method="POST",
        status_code=200,
        response_time_ms=4500,  # アラート閾値超過
        success=True
    )
    print("✅ API監視ログ記録（アラート発生含む）")
    
    # 3. 個人化データ収集テスト
    print("\n📝 Test 3: 個人化データ収集")
    advanced_analytics.log_personalization_event(
        user_id=test_user_id,
        event_type="translation_selection",
        gemini_recommendation="chatgpt",
        user_choice="enhanced",
        language_pair="ja-en",
        translation_context="business_email",
        style_attributes={'formality': 'formal', 'tone': 'professional'},
        confidence_score=0.85
    )
    
    advanced_analytics.log_personalization_event(
        user_id=test_user_id,
        event_type="rejection",
        gemini_recommendation="gemini",
        user_choice="chatgpt",
        language_pair="ja-en",
        rejection_reason="too_casual",
        confidence_score=0.92
    )
    print("✅ 個人化イベント記録")
    
    # 4. メトリクス取得テスト
    print("\n📊 Test 4: メトリクス取得")
    task292_metrics = advanced_analytics.get_task292_metrics()
    print(f"Task 2.9.2 メトリクス:")
    print(f"  - 総抽出数: {task292_metrics['total_extractions']}")
    print(f"  - 成功率: {task292_metrics['success_rate']:.1f}%")
    print(f"  - 平均信頼度: {task292_metrics['average_confidence']:.2f}")
    print(f"  - LLM成功率: {task292_metrics['llm_success_rate']:.1f}%")
    
    # 5. API統計取得テスト
    print("\n📊 Test 5: API統計")
    api_stats = advanced_analytics.get_api_statistics()
    for provider, stats in api_stats.items():
        print(f"{provider}:")
        print(f"  - 総呼び出し: {stats['total_calls']}")
        print(f"  - 成功率: {stats['success_rate']:.1f}%")
        print(f"  - 平均応答時間: {stats['average_response_time']:.0f}ms")
    
    # 6. アラート確認
    print("\n🚨 Test 6: アクティブアラート")
    alerts = advanced_analytics.get_active_alerts()
    print(f"アクティブアラート数: {len(alerts)}")
    for alert in alerts:
        print(f"  - [{alert['severity']}] {alert['message']}")
    
    # 7. 個人化インサイト取得
    print("\n💡 Test 7: 個人化インサイト")
    insights = advanced_analytics.get_personalization_insights(test_user_id)
    if insights['available']:
        print(f"ユーザー {test_user_id} のインサイト:")
        print(f"  - インタラクション数: {insights['interaction_count']}")
        print(f"  - 好みのエンジン: {insights['preferred_engine']}")
        print(f"  - よく使う言語ペア: {insights['top_language_pair']}")
    
    print("\n✅ Phase B-2: 高度な分析システムテスト完了")
    print("=" * 60)

if __name__ == "__main__":
    test_advanced_analytics()