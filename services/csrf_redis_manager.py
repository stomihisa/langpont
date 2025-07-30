"""
Task #8 SL-4: CSRFトークンRedis管理モジュール

このモジュールは以下の機能を提供します：
- CSRFトークンのRedis保存・取得・削除
- セキュアなキー生成（環境別プレフィックス付き）
- TTL管理による自動期限切れ
- Redis障害時のエラーハンドリング

設計方針：
- セキュリティファースト: TTL必須、適切なキー管理
- フォールバック対応: Redis障害時の安全な失敗
- 既存インフラ活用: SessionRedisManagerとの統合
"""

import os
import logging
from typing import Optional
from config import SESSION_TTL_SECONDS
from services.session_redis_manager import get_session_redis_manager

logger = logging.getLogger(__name__)


class CSRFRedisManager:
    """
    CSRFトークンのRedis管理クラス
    
    責務:
    - CSRFトークンのRedis保存・取得・削除
    - セキュアなキー生成（環境別プレフィックス）
    - TTL管理による期限切れ制御
    - Redis障害時の安全なエラーハンドリング
    """
    
    def __init__(self):
        """初期化"""
        self.redis_manager = get_session_redis_manager()
        self.ttl = SESSION_TTL_SECONDS  # config.pyから取得（3600秒）
        logger.info("✅ SL-4: CSRFRedisManager initialized")
        
    def _get_key(self, session_id: str) -> str:
        """
        環境別プレフィックス付きCSRFキー生成
        
        Args:
            session_id: セッションID
            
        Returns:
            str: Redis用CSRFキー
        """
        environment = os.getenv('ENVIRONMENT', 'development')
        if environment == 'production':
            prefix = 'langpont:prod:csrf'
        elif environment == 'staging':
            prefix = 'langpont:stage:csrf'
        else:
            prefix = 'langpont:dev:csrf'
            
        return f"{prefix}:{session_id}"
    
    def save_csrf_token(self, session_id: str, token: str) -> bool:
        """
        CSRFトークンをRedisに保存
        
        Args:
            session_id: セッションID
            token: CSRFトークン
            
        Returns:
            bool: 保存成功フラグ
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("⚠️ SL-4: Redis not available for CSRF token save")
                return False
                
            if not session_id or not token:
                logger.warning("⚠️ SL-4: Invalid session_id or token for CSRF save")
                return False
                
            cache_key = self._get_key(session_id)
            
            # TTL付きでRedis保存
            self.redis_manager.redis_client.set(cache_key, token, ex=self.ttl)
            
            logger.debug(f"✅ SL-4: CSRF token saved for session {session_id[:16]}... TTL={self.ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"❌ SL-4: Failed to save CSRF token: {e}")
            return False
    
    def get_csrf_token(self, session_id: str) -> Optional[str]:
        """
        RedisからCSRFトークンを取得
        
        Args:
            session_id: セッションID
            
        Returns:
            Optional[str]: CSRFトークンまたはNone
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("⚠️ SL-4: Redis not available for CSRF token get")
                return None
                
            if not session_id:
                logger.warning("⚠️ SL-4: Invalid session_id for CSRF get")
                return None
                
            cache_key = self._get_key(session_id)
            
            # Redis取得
            cached_token = self.redis_manager.redis_client.get(cache_key)
            
            if cached_token is None:
                logger.debug(f"📭 SL-4: No CSRF token found for session {session_id[:16]}...")
                return None
            
            # バイト型から文字列へ変換
            try:
                token = cached_token.decode('utf-8')
                logger.debug(f"📦 SL-4: CSRF token retrieved for session {session_id[:16]}...")
                return token
            except UnicodeDecodeError as e:
                logger.error(f"❌ SL-4: Unicode decode error for CSRF token: {e}")
                return None
                
        except Exception as e:
            logger.error(f"❌ SL-4: Failed to get CSRF token: {e}")
            return None
    
    def delete_csrf_token(self, session_id: str) -> bool:
        """
        CSRFトークンをRedisから削除
        
        Args:
            session_id: セッションID
            
        Returns:
            bool: 削除成功フラグ
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("⚠️ SL-4: Redis not available for CSRF token delete")
                return False
                
            if not session_id:
                logger.warning("⚠️ SL-4: Invalid session_id for CSRF delete")
                return False
                
            cache_key = self._get_key(session_id)
            
            # Redis削除
            result = self.redis_manager.redis_client.delete(cache_key)
            
            if result:
                logger.info(f"🗑️ SL-4: CSRF token deleted for session {session_id[:16]}...")
                return True
            else:
                logger.debug(f"📭 SL-4: CSRF token not found for deletion - session {session_id[:16]}...")
                return False
                
        except Exception as e:
            logger.error(f"❌ SL-4: Failed to delete CSRF token: {e}")
            return False
    
    def is_expired(self, session_id: str) -> bool:
        """
        CSRFトークンの有効期限チェック
        
        Args:
            session_id: セッションID
            
        Returns:
            bool: 期限切れの場合True
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("⚠️ SL-4: Redis not available for CSRF TTL check")
                return True  # Redis不可用時は期限切れとみなす
                
            if not session_id:
                return True  # 無効なセッションIDは期限切れとみなす
                
            cache_key = self._get_key(session_id)
            
            # TTL確認
            ttl = self.redis_manager.redis_client.ttl(cache_key)
            
            # ttl = -2: キーが存在しない
            # ttl = -1: キーは存在するがTTLが設定されていない（想定外）
            # ttl >= 0: 残り秒数
            
            if ttl == -2:
                logger.debug(f"📭 SL-4: CSRF token expired (not found) for session {session_id[:16]}...")
                return True
            elif ttl == -1:
                logger.warning(f"⚠️ SL-4: CSRF token exists but no TTL set for session {session_id[:16]}...")
                return False  # 存在はしているので有効とみなす
            else:
                is_expired = ttl <= 0
                if is_expired:
                    logger.debug(f"⏰ SL-4: CSRF token expired (TTL={ttl}) for session {session_id[:16]}...")
                else:
                    logger.debug(f"✅ SL-4: CSRF token valid (TTL={ttl}s) for session {session_id[:16]}...")
                return is_expired
                
        except Exception as e:
            logger.error(f"❌ SL-4: Failed to check CSRF token expiry: {e}")
            return True  # エラー時は期限切れとみなす


def get_csrf_redis_manager() -> CSRFRedisManager:
    """
    CSRFRedisManagerのファクトリ関数
    
    Returns:
        CSRFRedisManager: インスタンス
    """
    return CSRFRedisManager()