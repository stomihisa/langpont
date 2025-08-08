"""
SL-2.1: SessionRedisManager安全実装

参照設計書:
- SL-1_Session_Management_Policy.md: 統一ポリシー
- SL-1_Session_Categorization_Report.md: セッション分類

安全方針:
- Flask-Session不使用
- エラー時は警告ログのみ（アプリは継続動作）
- 手動同期のみ（既存セッション構造に影響なし）
"""

import redis
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
import os

# ログ設定
logger = logging.getLogger(__name__)

class SessionRedisManager:
    """
    認証情報Redis同期管理クラス（SL-2.1版）
    
    設計方針:
    - Flask標準セッションとの併用
    - エラー時は警告のみ（アプリ継続動作）
    - 認証情報の手動同期のみ
    """
    
    def __init__(self):
        # Redis接続設定
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.redis_password = os.getenv('REDIS_PASSWORD', None)
        self.redis_db = int(os.getenv('REDIS_SESSION_DB', 0))
        
        # 接続状態
        self.redis_client = None
        self.is_connected = False
        
        # TTL設定（認証情報用）
        self.auth_ttl = 3600  # 1時間
        
        # 安全な初期化
        self._safe_initialize()
    
    def _safe_initialize(self):
        """安全なRedis接続初期化"""
        try:
            # Redis接続設定
            self.redis_client = redis.StrictRedis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                db=self.redis_db,
                decode_responses=False,  # SL-2教訓: バイト型を維持
                socket_connect_timeout=5,
                socket_timeout=10,
                retry_on_timeout=True
            )
            
            # 接続テスト
            self.redis_client.ping()
            self.is_connected = True
            logger.info("✅ SessionRedisManager: Redis connection successful")
            
        except Exception as e:
            logger.warning(f"⚠️ SessionRedisManager: Redis connection failed: {e} - continuing with filesystem sessions only")
            self.redis_client = None
            self.is_connected = False
    
    def _get_auth_key(self, session_id: str) -> str:
        """認証情報用Redisキー生成"""
        environment = os.getenv('ENVIRONMENT', 'development')
        if environment == 'production':
            prefix = 'langpont:prod:session'
        elif environment == 'staging':
            prefix = 'langpont:stage:session'
        else:
            prefix = 'langpont:dev:session'
        
        return f"{prefix}:auth:{session_id}"
    
    def sync_auth_to_redis(self, session_id: str, auth_data: Dict[str, Any]) -> bool:
        """
        認証情報をRedisに同期
        
        重要: この処理が失敗してもアプリは継続動作
        """
        if not self.is_connected or not self.redis_client:
            logger.debug("Redis not connected, skipping auth sync")
            return False
        
        try:
            key = self._get_auth_key(session_id)
            
            # Hash型でRedisに保存（TTL付き）
            # bool値を文字列に変換
            redis_data = {}
            for k, v in auth_data.items():
                if isinstance(v, bool):
                    redis_data[k] = str(v).lower()  # True -> "true", False -> "false"
                elif v is None:
                    redis_data[k] = ""
                else:
                    redis_data[k] = str(v)
            
            self.redis_client.hset(key, mapping=redis_data)
            self.redis_client.expire(key, self.auth_ttl)
            
            logger.info(f"✅ Auth data synced to Redis: {session_id} -> {list(auth_data.keys())}")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Redis auth sync failed: {e} - continuing with filesystem session")
            return False
    
    def get_auth_from_redis(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Redisから認証情報を取得
        
        重要: この処理が失敗してもアプリは継続動作
        """
        if not self.is_connected or not self.redis_client:
            return None
        
        try:
            key = self._get_auth_key(session_id)
            
            # Redisから取得
            auth_json = self.redis_client.get(key)
            if not auth_json:
                return None
            
            # JSONデコード
            if isinstance(auth_json, bytes):
                auth_json = auth_json.decode('utf-8')
            
            auth_data = json.loads(auth_json)
            logger.debug(f"📦 Auth data retrieved from Redis: {session_id}")
            return auth_data
            
        except Exception as e:
            logger.warning(f"⚠️ Redis auth retrieval failed: {e}")
            return None
    
    def clear_auth_from_redis(self, session_id: str) -> bool:
        """
        Redisから認証情報を削除
        
        重要: この処理が失敗してもアプリは継続動作
        """
        if not self.is_connected or not self.redis_client:
            return False
        
        try:
            key = self._get_auth_key(session_id)
            
            # Redisから削除
            result = self.redis_client.delete(key)
            
            if result:
                logger.info(f"🗑️ Auth data cleared from Redis: {session_id}")
                return True
            else:
                logger.debug(f"📝 No auth data found in Redis: {session_id}")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ Redis auth clear failed: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Redis接続状態の確認"""
        health_status = {
            'redis_connected': self.is_connected,
            'redis_host': self.redis_host,
            'redis_port': self.redis_port,
            'timestamp': datetime.now().isoformat()
        }
        
        if self.is_connected and self.redis_client:
            try:
                response_time = time.time()
                self.redis_client.ping()
                response_time = (time.time() - response_time) * 1000
                
                health_status['redis_response_time_ms'] = round(response_time, 2)
                health_status['status'] = 'healthy'
                
            except Exception as e:
                health_status['redis_error'] = str(e)
                health_status['status'] = 'degraded'
                # 接続状態を更新
                self.is_connected = False
        else:
            health_status['status'] = 'disconnected'
        
        return health_status
    
    def reconnect(self):
        """Redis再接続試行"""
        if not self.is_connected:
            logger.info("🔄 Attempting Redis reconnection...")
            self._safe_initialize()


# シングルトンインスタンス
_session_redis_manager = None

def get_session_redis_manager() -> SessionRedisManager:
    """SessionRedisManagerのシングルトン取得"""
    global _session_redis_manager
    if _session_redis_manager is None:
        _session_redis_manager = SessionRedisManager()
    return _session_redis_manager