"""
SL-2.2: 商用Redisセッション正式実装

LangPontRedisSession - Flask SessionInterface実装
AWS Auto Scaling環境での完全なステートレス化を実現

参照設計書:
- SL-1_Session_Management_Policy.md: 統一ポリシー
- SL-1_Session_Categorization_Report.md: セッション分類

設計方針:
- Flask標準セッションの完全置き換え
- 全セッションデータのRedis管理
- SL-2.1 SessionRedisManagerとの互換性維持
"""

import logging
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from flask import Flask, Request, Response
from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict

logger = logging.getLogger(__name__)


class LangPontSession(CallbackDict, SessionMixin):
    """
    Redis専用セッションクラス
    Flask標準セッションを完全に置き換える
    """
    
    def __init__(self, initial=None, session_id=None):
        def on_update(self):
            self.modified = True
        
        CallbackDict.__init__(self, initial, on_update)
        self.session_id = session_id
        self.modified = False
        self.new = False if session_id else True


class LangPontRedisSession(SessionInterface):
    """
    商用Redis専用SessionInterface
    
    設計方針:
    - 全セッションデータをRedisで管理
    - SL-2.1 SessionRedisManagerとの共存
    - 環境変数による動作制御
    """
    
    def __init__(self, redis_manager, cookie_name='langpont_session', ttl=3600):
        """
        初期化
        
        Args:
            redis_manager: SL-2.1で実装済みのSessionRedisManager
            cookie_name: セッションクッキー名
            ttl: セッション有効期限（秒）
        """
        self.redis_manager = redis_manager
        self.cookie_name = cookie_name
        self.ttl = ttl
        
        logger.info(f"✅ SL-2.2: LangPontRedisSession initialized - TTL: {ttl}s")
    
    def _get_session_key(self, session_id: str) -> str:
        """セッションデータ用Redisキー生成"""
        import os
        environment = os.getenv('ENVIRONMENT', 'development')
        if environment == 'production':
            prefix = 'langpont:prod:session'
        elif environment == 'staging':
            prefix = 'langpont:stage:session'
        else:
            prefix = 'langpont:dev:session'
        
        return f"{prefix}:data:{session_id}"
    
    def _generate_session_id(self) -> str:
        """安全なセッションID生成"""
        return secrets.token_hex(32)  # 64文字のランダムID
    
    def open_session(self, app: Flask, request: Request) -> Optional[LangPontSession]:
        """
        リクエスト開始時：Redisからセッションデータを読み込み
        
        Returns:
            LangPontSession: セッションオブジェクト
        """
        try:
            # 1. Cookieからsession_idを取得
            session_id = request.cookies.get(self.cookie_name)
            
            if not session_id:
                # 新規セッション
                logger.debug("🆕 SL-2.2: Creating new session")
                return LangPontSession()
            
            # 2. Redisから langpont:dev:session:data:{session_id} を読み込み
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("⚠️ SL-2.2: Redis not available, creating new session")
                return LangPontSession()
            
            session_key = self._get_session_key(session_id)
            
            try:
                # Redis Hash からセッションデータを取得
                session_data = self.redis_manager.redis_client.hgetall(session_key)
                
                if not session_data:
                    logger.debug(f"📭 SL-2.2: No session data found for {session_id}")
                    return LangPontSession()
                
                # バイトデータを文字列に変換
                if isinstance(session_data, dict):
                    decoded_data = {}
                    for k, v in session_data.items():
                        key = k.decode('utf-8') if isinstance(k, bytes) else k
                        value = v.decode('utf-8') if isinstance(v, bytes) else v
                        
                        # bool値の復元
                        if value == 'true':
                            decoded_data[key] = True
                        elif value == 'false':
                            decoded_data[key] = False
                        elif value == '':
                            decoded_data[key] = None
                        else:
                            # 数値の復元を試行
                            try:
                                if '.' in value:
                                    decoded_data[key] = float(value)
                                else:
                                    decoded_data[key] = int(value)
                            except ValueError:
                                decoded_data[key] = value
                    
                    session_data = decoded_data
                
                # 3. セッションオブジェクトを返す
                logger.debug(f"📦 SL-2.2: Session loaded: {session_id} -> {list(session_data.keys())}")
                return LangPontSession(session_data, session_id)
                
            except Exception as e:
                logger.warning(f"⚠️ SL-2.2: Failed to load session data: {e}")
                return LangPontSession()
        
        except Exception as e:
            logger.error(f"❌ SL-2.2: Error in open_session: {e}")
            return LangPontSession()
    
    def save_session(self, app: Flask, session: LangPontSession, response: Response) -> None:
        """
        レスポンス時：セッションデータをRedisに保存
        
        Args:
            app: Flaskアプリケーション
            session: セッションオブジェクト
            response: HTTPレスポンス
        """
        try:
            # セッションが変更されていない場合はスキップ
            if not session.modified and not session.new:
                return
            
            # 空セッションの場合
            if not session:
                if session.session_id:
                    # 既存セッションを削除
                    self._delete_session(session.session_id)
                    response.set_cookie(
                        self.cookie_name,
                        expires=0,
                        httponly=True,
                        secure=app.config.get('SESSION_COOKIE_SECURE', False),
                        samesite=app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
                    )
                return
            
            # セッションIDの生成または使用
            if not session.session_id:
                session.session_id = self._generate_session_id()
                session.new = False
            
            # 1. セッションデータをRedisに保存
            if self.redis_manager and self.redis_manager.is_connected:
                try:
                    session_key = self._get_session_key(session.session_id)
                    
                    # セッションデータをRedis Hash形式で保存
                    redis_data = {}
                    for k, v in session.items():
                        if isinstance(v, bool):
                            redis_data[k] = str(v).lower()
                        elif v is None:
                            redis_data[k] = ""
                        else:
                            redis_data[k] = str(v)
                    
                    self.redis_manager.redis_client.hset(session_key, mapping=redis_data)
                    
                    # 2. TTLを設定
                    self.redis_manager.redis_client.expire(session_key, self.ttl)
                    
                    logger.debug(f"💾 SL-2.2: Session saved: {session.session_id} -> {list(session.keys())}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ SL-2.2: Failed to save session to Redis: {e}")
            
            # 3. CookieにセッションIDを設定
            response.set_cookie(
                self.cookie_name,
                session.session_id,
                max_age=self.ttl,
                httponly=app.config.get('SESSION_COOKIE_HTTPONLY', True),
                secure=app.config.get('SESSION_COOKIE_SECURE', False),
                samesite=app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
            )
            
        except Exception as e:
            logger.error(f"❌ SL-2.2: Error in save_session: {e}")
    
    def make_null_session(self, app: Flask) -> LangPontSession:
        """
        認証されていない場合の空セッション生成
        
        Returns:
            LangPontSession: 空のセッションオブジェクト
        """
        logger.debug("🔓 SL-2.2: Creating null session")
        return LangPontSession()
    
    def _delete_session(self, session_id: str) -> bool:
        """
        セッションデータを削除
        
        Args:
            session_id: セッションID
            
        Returns:
            bool: 削除成功フラグ
        """
        try:
            if self.redis_manager and self.redis_manager.is_connected:
                session_key = self._get_session_key(session_id)
                result = self.redis_manager.redis_client.delete(session_key)
                logger.debug(f"🗑️ SL-2.2: Session deleted: {session_id}")
                return bool(result)
        except Exception as e:
            logger.warning(f"⚠️ SL-2.2: Failed to delete session: {e}")
        
        return False


def get_langpont_redis_session(redis_manager, cookie_name='langpont_session', ttl=3600):
    """
    LangPontRedisSessionのファクトリ関数
    
    Args:
        redis_manager: SessionRedisManager インスタンス
        cookie_name: セッションクッキー名
        ttl: セッション有効期限（秒）
        
    Returns:
        LangPontRedisSession: SessionInterface実装
    """
    return LangPontRedisSession(redis_manager, cookie_name, ttl)