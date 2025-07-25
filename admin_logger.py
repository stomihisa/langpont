#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🚀 Task 2.9.2 Phase B-1: ログ収集・構造化システム
================================================================
目的: ターミナルメッセージを整理・構造化し、管理者ダッシュボードで表示
機能: リアルタイムログ収集、カテゴリ分類、データ可視化用フォーマット
"""

import logging
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
import time
import os

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdminLogger:
    """管理者ダッシュボード用ログ収集・構造化システム"""
    
    def __init__(self, db_path: str = "admin_logs.db"):
        """初期化"""
        self.db_path = db_path
        self.lock = threading.Lock()
        
        # リアルタイムログ保持（メモリ）
        self.recent_logs = deque(maxlen=1000)  # 最新1000件
        self.system_stats = {
            'total_translations': 0,
            'total_api_calls': 0,
            'gemini_recommendations': defaultdict(int),
            'user_choices': defaultdict(int),
            'error_count': 0,
            'active_users': set(),
            'performance_metrics': []
        }
        
        # ログカテゴリ定義
        self.log_categories = {
            'translation': 'translation',
            'gemini_analysis': 'gemini_analysis',
            'user_auth': 'user_auth',
            'admin_access': 'admin_access',
            'api_call': 'api_call',
            'error': 'error',
            'system': 'system',
            'performance': 'performance'
        }
        
        self._init_database()
        logger.info("🗂️ AdminLogger初期化完了")
    
    def _init_database(self):
        """データベース初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # ログエントリテーブル
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS admin_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        category TEXT NOT NULL,
                        level TEXT NOT NULL,
                        username TEXT,
                        session_id TEXT,
                        action TEXT,
                        details TEXT,
                        metadata TEXT,
                        ip_address TEXT,
                        user_agent TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # システム統計テーブル
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        metric_value TEXT NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # パフォーマンス統計テーブル
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        duration_ms INTEGER,
                        success BOOLEAN,
                        details TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                logger.info("📊 AdminLoggerデータベース初期化完了")
                
        except Exception as e:
            logger.error(f"❌ データベース初期化エラー: {str(e)}")
    
    def log_event(self, category: str, level: str, action: str, details: str = "", 
                  username: str = None, session_id: str = None, metadata: Dict = None):
        """ログイベントを記録"""
        try:
            timestamp = datetime.now().isoformat()
            
            log_entry = {
                'timestamp': timestamp,
                'category': category,
                'level': level,
                'username': username,
                'session_id': session_id,
                'action': action,
                'details': details,
                'metadata': json.dumps(metadata) if metadata else None,
                'ip_address': None,  # リクエストコンテキストから取得
                'user_agent': None   # リクエストコンテキストから取得
            }
            
            # メモリ内キャッシュに追加
            with self.lock:
                self.recent_logs.append(log_entry)
                self._update_stats(log_entry)
            
            # データベースに保存
            self._save_to_database(log_entry)
            
            # コンソールログ出力
            log_message = f"📊 {category.upper()}: {action} - {details}"
            if level == 'ERROR':
                logger.error(log_message)
            elif level == 'WARNING':
                logger.warning(log_message)
            else:
                logger.info(log_message)
                
        except Exception as e:
            logger.error(f"❌ ログ記録エラー: {str(e)}")
    
    def _save_to_database(self, log_entry: Dict):
        """ログをデータベースに保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO admin_logs 
                    (timestamp, category, level, username, session_id, action, details, metadata, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log_entry['timestamp'],
                    log_entry['category'],
                    log_entry['level'],
                    log_entry['username'],
                    log_entry['session_id'],
                    log_entry['action'],
                    log_entry['details'],
                    log_entry['metadata'],
                    log_entry['ip_address'],
                    log_entry['user_agent']
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ データベース保存エラー: {str(e)}")
    
    def _update_stats(self, log_entry: Dict):
        """統計情報を更新"""
        try:
            category = log_entry['category']
            
            if category == 'translation':
                self.system_stats['total_translations'] += 1
                if log_entry['username']:
                    self.system_stats['active_users'].add(log_entry['username'])
            
            elif category == 'gemini_analysis':
                # Gemini推奨統計
                metadata = json.loads(log_entry['metadata']) if log_entry['metadata'] else {}
                recommendation = metadata.get('recommendation')
                if recommendation:
                    self.system_stats['gemini_recommendations'][recommendation] += 1
            
            elif category == 'api_call':
                self.system_stats['total_api_calls'] += 1
            
            elif category == 'error':
                self.system_stats['error_count'] += 1
            
            # パフォーマンス統計
            if 'duration_ms' in log_entry.get('metadata', {}):
                duration = json.loads(log_entry['metadata'])['duration_ms']
                self.system_stats['performance_metrics'].append({
                    'timestamp': log_entry['timestamp'],
                    'operation': log_entry['action'],
                    'duration': duration
                })
                
                # 最新100件のみ保持
                if len(self.system_stats['performance_metrics']) > 100:
                    self.system_stats['performance_metrics'] = self.system_stats['performance_metrics'][-100:]
                    
        except Exception as e:
            logger.error(f"❌ 統計更新エラー: {str(e)}")
    
    def get_recent_logs(self, limit: int = 50, category: str = None) -> List[Dict]:
        """最新ログを取得"""
        with self.lock:
            if category:
                filtered_logs = [log for log in self.recent_logs if log['category'] == category]
                return list(filtered_logs)[-limit:]
            else:
                return list(self.recent_logs)[-limit:]
    
    def get_system_stats(self) -> Dict[str, Any]:
        """システム統計を取得"""
        with self.lock:
            return {
                'total_translations': self.system_stats['total_translations'],
                'total_api_calls': self.system_stats['total_api_calls'],
                'gemini_recommendations': dict(self.system_stats['gemini_recommendations']),
                'user_choices': dict(self.system_stats['user_choices']),
                'error_count': self.system_stats['error_count'],
                'active_users_count': len(self.system_stats['active_users']),
                'active_users': list(self.system_stats['active_users']),
                'avg_response_time': self._calculate_avg_response_time(),
                'last_updated': datetime.now().isoformat()
            }
    
    def _calculate_avg_response_time(self) -> float:
        """平均レスポンス時間を計算"""
        try:
            if not self.system_stats['performance_metrics']:
                return 0.0
            
            durations = [m['duration'] for m in self.system_stats['performance_metrics']]
            return sum(durations) / len(durations)
        except:
            return 0.0
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """エラーサマリーを取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                since_time = (datetime.now() - timedelta(hours=hours)).isoformat()
                
                cursor.execute("""
                    SELECT action, COUNT(*) as count, details
                    FROM admin_logs
                    WHERE category = 'error' AND timestamp > ?
                    GROUP BY action
                    ORDER BY count DESC
                """, (since_time,))
                
                errors = [{'action': row[0], 'count': row[1], 'details': row[2]} 
                         for row in cursor.fetchall()]
                
                return {
                    'total_errors': sum(e['count'] for e in errors),
                    'error_types': errors,
                    'time_range': f"Past {hours} hours"
                }
                
        except Exception as e:
            logger.error(f"❌ エラーサマリー取得エラー: {str(e)}")
            return {'total_errors': 0, 'error_types': [], 'time_range': f"Past {hours} hours"}
    
    def get_translation_analytics(self, days: int = 7) -> Dict[str, Any]:
        """翻訳分析データを取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                since_time = (datetime.now() - timedelta(days=days)).isoformat()
                
                # 日別翻訳数
                cursor.execute("""
                    SELECT DATE(timestamp) as date, COUNT(*) as count
                    FROM admin_logs
                    WHERE category = 'translation' AND timestamp > ?
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                """, (since_time,))
                
                daily_translations = [{'date': row[0], 'count': row[1]} 
                                    for row in cursor.fetchall()]
                
                # ユーザー別統計
                cursor.execute("""
                    SELECT username, COUNT(*) as count
                    FROM admin_logs
                    WHERE category = 'translation' AND timestamp > ? AND username IS NOT NULL
                    GROUP BY username
                    ORDER BY count DESC
                    LIMIT 10
                """, (since_time,))
                
                top_users = [{'username': row[0], 'count': row[1]} 
                           for row in cursor.fetchall()]
                
                return {
                    'daily_translations': daily_translations,
                    'top_users': top_users,
                    'time_range': f"Past {days} days"
                }
                
        except Exception as e:
            logger.error(f"❌ 翻訳分析取得エラー: {str(e)}")
            return {'daily_translations': [], 'top_users': [], 'time_range': f"Past {days} days"}
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """古いログをクリーンアップ"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_time = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
                
                cursor.execute("DELETE FROM admin_logs WHERE timestamp < ?", (cutoff_time,))
                cursor.execute("DELETE FROM system_stats WHERE created_at < ?", (cutoff_time,))
                cursor.execute("DELETE FROM performance_logs WHERE timestamp < ?", (cutoff_time,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"🧹 古いログ削除完了: {deleted_count}件")
                
        except Exception as e:
            logger.error(f"❌ ログクリーンアップエラー: {str(e)}")


# グローバルインスタンス
admin_logger = AdminLogger()


# 便利関数
def log_translation_event(username: str, language_pair: str, success: bool, duration_ms: int = None):
    """翻訳イベントをログ"""
    admin_logger.log_event(
        category='translation',
        level='INFO' if success else 'ERROR',
        action='translation_request',
        details=f"Language: {language_pair}, Success: {success}",
        username=username,
        metadata={'language_pair': language_pair, 'success': success, 'duration_ms': duration_ms}
    )


def log_gemini_analysis(username: str, recommendation: str, confidence: float, method: str):
    """Gemini分析イベントをログ"""
    admin_logger.log_event(
        category='gemini_analysis',
        level='INFO',
        action='recommendation_extracted',
        details=f"Recommendation: {recommendation}, Confidence: {confidence:.3f}",
        username=username,
        metadata={'recommendation': recommendation, 'confidence': confidence, 'method': method}
    )


def log_api_call(api_name: str, success: bool, duration_ms: int, details: str = ""):
    """API呼び出しをログ"""
    admin_logger.log_event(
        category='api_call',
        level='INFO' if success else 'ERROR',
        action=f'{api_name}_api_call',
        details=f"Success: {success}, Duration: {duration_ms}ms, {details}",
        metadata={'api_name': api_name, 'success': success, 'duration_ms': duration_ms}
    )


def log_error(error_type: str, error_message: str, username: str = None, details: str = ""):
    """エラーをログ"""
    admin_logger.log_event(
        category='error',
        level='ERROR',
        action=error_type,
        details=f"{error_message} - {details}",
        username=username,
        metadata={'error_type': error_type, 'error_message': error_message}
    )


# テスト関数
def test_admin_logger():
    """AdminLoggerのテスト"""
    print("🧪 AdminLoggerテスト開始")
    print("=" * 60)
    
    # テストログ生成
    log_translation_event("test_user", "ja-en", True, 1500)
    log_translation_event("test_user2", "en-fr", True, 2000)
    log_gemini_analysis("test_user", "chatgpt", 0.95, "llm_chatgpt_a9")
    log_api_call("openai", True, 800, "GPT-3.5-turbo")
    log_error("validation_error", "Invalid input text", "test_user")
    
    time.sleep(1)  # ログ処理待機
    
    # 統計確認
    stats = admin_logger.get_system_stats()
    print(f"📊 システム統計: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    # 最新ログ確認
    recent_logs = admin_logger.get_recent_logs(5)
    print(f"\n📝 最新ログ (5件):")
    for log in recent_logs:
        print(f"   {log['timestamp']} [{log['category']}] {log['action']}: {log['details']}")
    
    # エラーサマリー確認
    error_summary = admin_logger.get_error_summary(24)
    print(f"\n❌ エラーサマリー: {json.dumps(error_summary, indent=2, ensure_ascii=False)}")
    
    print("\n✅ AdminLoggerテスト完了")


if __name__ == "__main__":
    test_admin_logger()