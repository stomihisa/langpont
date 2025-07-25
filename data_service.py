#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangPont 統一データアクセスサービス
AWS移行対応 & データ整合性保証
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import os
from contextlib import contextmanager

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DataSourceInfo:
    """データソース情報"""
    source_name: str
    database_file: str
    table_name: str
    description: str
    record_count: int
    last_updated: str

@dataclass
class UnifiedMetrics:
    """統一メトリクス"""
    total_activities: int
    today_activities: int
    total_users: int
    active_users: int
    error_rate: float
    avg_processing_time: float
    data_sources: List[DataSourceInfo]
    generated_at: str

class LangPontDataService:
    """
    LangPont統一データアクセスサービス
    - Single Source of Truth の確立
    - AWS移行準備
    - データ整合性保証
    """
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.cache = {}
        self.cache_ttl = 300  # 5分キャッシュ
        
        # データベースファイルの定義
        self.databases = {
            'activity': 'langpont_activity_log.db',
            'users': 'langpont_users.db', 
            'analytics': 'langpont_analytics.db',
            'history': 'langpont_translation_history.db'
        }
        
        logger.info("🔧 LangPont統一データサービス初期化開始")
        self._validate_databases()
        logger.info("✅ 統一データサービス初期化完了")
    
    def _validate_databases(self):
        """データベースファイルの存在確認"""
        for db_name, db_file in self.databases.items():
            db_path = os.path.join(self.base_dir, db_file)
            if os.path.exists(db_path):
                logger.info(f"✅ {db_name} DB確認: {db_file}")
            else:
                logger.warning(f"⚠️ {db_name} DB未発見: {db_file}")
    
    @contextmanager
    def get_connection(self, db_name: str):
        """データベース接続の取得（コンテキストマネージャー）"""
        if db_name not in self.databases:
            raise ValueError(f"未知のデータベース: {db_name}")
        
        db_path = os.path.join(self.base_dir, self.databases[db_name])
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def get_master_activity_metrics(self) -> Dict[str, Any]:
        """
        マスター活動メトリクス取得
        - 4段階分析システムのメインデータソース
        - 全ダッシュボードの統一データソース
        - フェールセーフ対応済み
        """
        cache_key = "master_activity_metrics"
        
        # キャッシュチェック
        if self._is_cache_valid(cache_key):
            logger.info("📋 キャッシュからマスターメトリクス取得")
            return self.cache[cache_key]['data']
        
        logger.info("🔍 マスター活動メトリクス取得開始")
        
        # 🆕 フェールセーフ対応
        try:
            return self._fetch_master_metrics_with_fallback()
        except Exception as e:
            logger.critical(f"🚨 マスターメトリクス取得でクリティカルエラー: {e}")
            return self._get_emergency_fallback_data()
    
    def _fetch_master_metrics_with_fallback(self) -> Dict[str, Any]:
        """フェールセーフ付きメトリクス取得"""
        
        cache_key = "master_activity_metrics"
        
        try:
            with self.get_connection('activity') as conn:
                cursor = conn.cursor()
                
                # 基本統計（エラーハンドリング付き）
                try:
                    cursor.execute("SELECT COUNT(*) as total FROM analysis_activity_log")
                    total_count = cursor.fetchone()['total']
                except Exception as e:
                    logger.error(f"📊 基本統計取得エラー: {e}")
                    total_count = 0
                
                # 今日の活動
                today = datetime.now().strftime('%Y-%m-%d')
                cursor.execute("""
                    SELECT COUNT(*) as today_count 
                    FROM analysis_activity_log 
                    WHERE DATE(created_at) = ?
                """, (today,))
                today_count = cursor.fetchone()['today_count']
                
                # エラー率
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN error_occurred = 1 THEN 1 ELSE 0 END) as errors
                    FROM analysis_activity_log
                """)
                error_data = cursor.fetchone()
                error_rate = (error_data['errors'] / error_data['total'] * 100) if error_data['total'] > 0 else 0
                
                # 平均処理時間
                cursor.execute("""
                    SELECT AVG(processing_duration) as avg_time
                    FROM analysis_activity_log 
                    WHERE processing_duration > 0
                """)
                avg_time_result = cursor.fetchone()
                avg_time = avg_time_result['avg_time'] or 0
                
                # エンジン統計
                cursor.execute("""
                    SELECT 
                        button_pressed,
                        COUNT(*) as count,
                        AVG(confidence) as avg_confidence
                    FROM analysis_activity_log 
                    WHERE button_pressed IS NOT NULL
                    GROUP BY button_pressed
                    ORDER BY count DESC
                """)
                engine_stats = [dict(row) for row in cursor.fetchall()]
                
                # 推奨結果統計
                cursor.execute("""
                    SELECT 
                        recommendation_result,
                        COUNT(*) as count
                    FROM analysis_activity_log 
                    WHERE recommendation_result IS NOT NULL
                    GROUP BY recommendation_result
                    ORDER BY count DESC
                """)
                recommendation_stats = [dict(row) for row in cursor.fetchall()]
                
                # 4段階分析統計（既存のカラム名に対応）
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_stages,
                        SUM(CASE WHEN human_check_result IS NOT NULL THEN 1 ELSE 0 END) as stage0_complete,
                        SUM(CASE WHEN stage1_extraction_method IS NOT NULL THEN 1 ELSE 0 END) as stage1_complete,
                        SUM(CASE WHEN actual_user_choice IS NOT NULL THEN 1 ELSE 0 END) as stage2_complete,
                        SUM(CASE WHEN recommendation_vs_choice_match IS NOT NULL THEN 1 ELSE 0 END) as stage3_complete
                    FROM analysis_activity_log
                """)
                stage_stats = dict(cursor.fetchone())
                
                # 最新活動（既存のカラム名に対応）
                cursor.execute("""
                    SELECT 
                        id, created_at, japanese_text, user_id,
                        button_pressed, recommendation_result, actual_user_choice
                    FROM analysis_activity_log 
                    ORDER BY created_at DESC 
                    LIMIT 10
                """)
                recent_activities = [dict(row) for row in cursor.fetchall()]
            
            result = {
                'basic_stats': {
                    'total_activities': total_count,
                    'today_activities': today_count,
                    'error_rate': round(error_rate, 2),
                    'avg_processing_time': round(avg_time, 2)
                },
                'engine_stats': engine_stats,
                'recommendation_stats': recommendation_stats,
                'four_stage_stats': stage_stats,
                'recent_activities': recent_activities,
                'data_source': {
                    'database': 'langpont_activity_log.db',
                    'table': 'analysis_activity_log',
                    'description': 'マスター活動ログ（4段階分析システム）',
                    'generated_at': datetime.now().isoformat()
                }
            }
            
            # キャッシュに保存
            self._save_to_cache(cache_key, result)
            
            logger.info(f"✅ マスター活動メトリクス取得完了: {total_count}件")
            return result
            
        except sqlite3.Error as e:
            logger.error(f"🗃️ データベースエラー: {e}")
            return self._get_database_error_fallback()
        except Exception as e:
            logger.error(f"📊 統計取得エラー: {e}")
            return self._get_general_error_fallback()
    
    def _get_database_error_fallback(self) -> Dict[str, Any]:
        """データベースエラー時のフォールバックデータ"""
        return {
            'basic_stats': {
                'total_activities': -1,
                'today_activities': -1,
                'error_rate': 100.0,
                'avg_processing_time': 0.0
            },
            'engine_stats': [],
            'recommendation_stats': [],
            'four_stage_stats': {},
            'recent_activities': [],
            'data_source': {
                'database': 'ERROR',
                'table': 'ERROR',
                'description': 'データベースエラー',
                'generated_at': datetime.now().isoformat()
            },
            'status': 'database_error'
        }
    
    def _get_general_error_fallback(self) -> Dict[str, Any]:
        """一般エラー時のフォールバックデータ"""
        return {
            'basic_stats': {
                'total_activities': -2,
                'today_activities': -2,
                'error_rate': 100.0,
                'avg_processing_time': 0.0
            },
            'engine_stats': [],
            'recommendation_stats': [],
            'four_stage_stats': {},
            'recent_activities': [],
            'data_source': {
                'database': 'SYSTEM_ERROR',
                'table': 'SYSTEM_ERROR',
                'description': 'システムエラー',
                'generated_at': datetime.now().isoformat()
            },
            'status': 'system_error'
        }
    
    def _get_emergency_fallback_data(self) -> Dict[str, Any]:
        """緊急時フォールバックデータ"""
        return {
            'basic_stats': {
                'total_activities': -3,
                'today_activities': -3,
                'error_rate': 100.0,
                'avg_processing_time': 0.0
            },
            'engine_stats': [],
            'recommendation_stats': [],
            'four_stage_stats': {},
            'recent_activities': [],
            'data_source': {
                'database': 'EMERGENCY_MODE',
                'table': 'EMERGENCY_MODE',
                'description': '緊急モード - データベース接続不可',
                'generated_at': datetime.now().isoformat()
            },
            'status': 'emergency_mode'
        }
    
    def get_data_source_summary(self) -> List[DataSourceInfo]:
        """全データソースの概要取得"""
        logger.info("🔍 データソース概要取得開始")
        
        sources = []
        
        for db_name, db_file in self.databases.items():
            db_path = os.path.join(self.base_dir, db_file)
            
            if not os.path.exists(db_path):
                continue
                
            with self.get_connection(db_name) as conn:
                cursor = conn.cursor()
                
                # テーブル一覧取得
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row['name'] for row in cursor.fetchall()]
                
                for table in tables:
                    try:
                        # レコード数取得
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                        count = cursor.fetchone()['count']
                        
                        # 最終更新日取得（created_atまたは類似カラムがある場合）
                        last_updated = "不明"
                        try:
                            cursor.execute(f"SELECT MAX(created_at) as last_update FROM {table}")
                            result = cursor.fetchone()
                            if result['last_update']:
                                last_updated = result['last_update']
                        except:
                            pass
                        
                        sources.append(DataSourceInfo(
                            source_name=f"{db_name}.{table}",
                            database_file=db_file,
                            table_name=table,
                            description=self._get_table_description(db_name, table),
                            record_count=count,
                            last_updated=last_updated
                        ))
                    except Exception as e:
                        logger.warning(f"⚠️ テーブル {table} 情報取得エラー: {e}")
        
        logger.info(f"✅ データソース概要取得完了: {len(sources)}個のテーブル")
        return sources
    
    def _get_table_description(self, db_name: str, table_name: str) -> str:
        """テーブルの説明を取得"""
        descriptions = {
            'activity.analysis_activity_log': 'メイン活動ログ（4段階分析システム）',
            'users.users': 'ユーザーアカウント情報',
            'users.user_sessions': 'ユーザーセッション管理',
            'analytics.satisfaction_metrics': '満足度分析データ',
            'history.translation_history': '翻訳履歴アーカイブ'
        }
        
        key = f"{db_name}.{table_name}"
        return descriptions.get(key, f"{db_name}データベースの{table_name}テーブル")
    
    def get_unified_dashboard_data(self) -> UnifiedMetrics:
        """統一ダッシュボード用データ取得"""
        logger.info("📊 統一ダッシュボードデータ取得開始")
        
        # マスター活動メトリクス
        activity_metrics = self.get_master_activity_metrics()
        
        # ユーザー統計
        user_stats = self._get_user_statistics()
        
        # データソース情報
        data_sources = self.get_data_source_summary()
        
        unified_metrics = UnifiedMetrics(
            total_activities=activity_metrics['basic_stats']['total_activities'],
            today_activities=activity_metrics['basic_stats']['today_activities'],
            total_users=user_stats['total_users'],
            active_users=user_stats['active_users'],
            error_rate=activity_metrics['basic_stats']['error_rate'],
            avg_processing_time=activity_metrics['basic_stats']['avg_processing_time'],
            data_sources=data_sources,
            generated_at=datetime.now().isoformat()
        )
        
        logger.info("✅ 統一ダッシュボードデータ取得完了")
        return unified_metrics
    
    def _get_user_statistics(self) -> Dict[str, int]:
        """ユーザー統計取得"""
        try:
            with self.get_connection('users') as conn:
                cursor = conn.cursor()
                
                # 総ユーザー数
                cursor.execute("SELECT COUNT(*) as total FROM users")
                total_users = cursor.fetchone()['total']
                
                # アクティブユーザー（30日以内にログイン）
                thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
                cursor.execute("""
                    SELECT COUNT(*) as active 
                    FROM users 
                    WHERE last_login_at > ?
                """, (thirty_days_ago,))
                active_users = cursor.fetchone()['active']
                
                return {
                    'total_users': total_users,
                    'active_users': active_users
                }
        except Exception as e:
            logger.warning(f"⚠️ ユーザー統計取得エラー: {e}")
            return {'total_users': 0, 'active_users': 0}
    
    def _is_cache_valid(self, key: str) -> bool:
        """キャッシュの有効性チェック"""
        if key not in self.cache:
            return False
        
        cache_time = self.cache[key]['timestamp']
        return (datetime.now() - cache_time).seconds < self.cache_ttl
    
    def _save_to_cache(self, key: str, data: Any):
        """キャッシュに保存"""
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    def clear_cache(self):
        """キャッシュクリア"""
        self.cache.clear()
        logger.info("🗑️ キャッシュクリア完了")
    
    def health_check(self) -> Dict[str, Any]:
        """システムヘルスチェック"""
        logger.info("🏥 システムヘルスチェック開始")
        
        health_status = {
            'status': 'healthy',
            'databases': {},
            'cache_size': len(self.cache),
            'checked_at': datetime.now().isoformat()
        }
        
        for db_name, db_file in self.databases.items():
            db_path = os.path.join(self.base_dir, db_file)
            
            if os.path.exists(db_path):
                try:
                    with self.get_connection(db_name) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT 1")
                        health_status['databases'][db_name] = {
                            'status': 'connected',
                            'file': db_file,
                            'size_mb': round(os.path.getsize(db_path) / 1024 / 1024, 2)
                        }
                except Exception as e:
                    health_status['databases'][db_name] = {
                        'status': 'error',
                        'error': str(e)
                    }
                    health_status['status'] = 'degraded'
            else:
                health_status['databases'][db_name] = {
                    'status': 'not_found',
                    'file': db_file
                }
                health_status['status'] = 'degraded'
        
        logger.info(f"✅ ヘルスチェック完了: {health_status['status']}")
        return health_status

# グローバルインスタンス
data_service = LangPontDataService()

def get_data_service() -> LangPontDataService:
    """データサービスインスタンス取得"""
    return data_service

if __name__ == "__main__":
    # テスト実行
    print("🧪 LangPont統一データサービステスト")
    
    # ヘルスチェック
    health = data_service.health_check()
    print(f"📊 ヘルス状況: {health['status']}")
    
    # データソース概要
    sources = data_service.get_data_source_summary()
    print(f"📋 データソース数: {len(sources)}")
    for source in sources:
        print(f"  - {source.source_name}: {source.record_count}件")
    
    # 統一メトリクス
    metrics = data_service.get_unified_dashboard_data()
    print(f"📈 総活動数: {metrics.total_activities}")
    print(f"📈 今日の活動: {metrics.today_activities}")
    print(f"👥 総ユーザー数: {metrics.total_users}")
    
    print("✅ テスト完了")