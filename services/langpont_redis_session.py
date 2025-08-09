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
import redis
from redis.exceptions import ConnectionError, TimeoutError, ResponseError
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from flask import Flask, Request, Response
from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict

# 🆕 SL-2.2 Phase 3: セキュリティログとの統合
try:
    from security.security_logger import log_security_event
except ImportError:
    # フォールバック: ダミー関数
    def log_security_event(event_type, details, severity):
        logger.warning(f"Security event (fallback): {event_type} - {details} - {severity}")

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
        🆕 SL-2.2 Phase 5: TTL自動更新対応セッション読み込み
        
        エラーハンドリング:
        - Redis接続エラー時のフォールバック
        - セッションデータ破損時の復旧
        - 不正なセッションIDの検出・対応
        
        TTL自動更新:
        - セッション読み込み成功時に自動でTTL延長
        - ユーザーアクティブ時のセッション期限切れ防止
        
        Returns:
            LangPontSession: セッションオブジェクト
        """
        try:
            # 1. Cookieからsession_idを取得・検証
            session_id = request.cookies.get(self.cookie_name)
            
            if not session_id:
                # 新規セッション
                logger.debug("🆕 SL-2.2 Phase 3: Creating new session - no cookie")
                return self._create_new_session()
            
            # セッションIDの基本的な妥当性チェック
            if len(session_id) < 16 or len(session_id) > 128:
                logger.warning(f"⚠️ SL-2.2 Phase 3: Invalid session ID length: {len(session_id)}")
                log_security_event(
                    "INVALID_SESSION_ID",
                    f"Invalid session ID length: {len(session_id)}",
                    "WARNING"
                )
                return self._create_new_session()
            
            # 2. Redis接続状態の確認
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("⚠️ SL-2.2 Phase 3: Redis not available, creating new session")
                log_security_event(
                    "REDIS_UNAVAILABLE_SESSION_OPEN",
                    "Redis unavailable during session open",
                    "WARNING"
                )
                return self._create_new_session()
            
            session_key = self._get_session_key(session_id)
            
            try:
                # 3. Redis Hash からセッションデータを取得
                session_data = self.redis_manager.redis_client.hgetall(session_key)
                
                if not session_data:
                    logger.debug(f"📭 SL-2.2 Phase 3: No session data found for {session_id}")
                    # セッションIDは有効だがデータが存在しない場合
                    log_security_event(
                        "SESSION_DATA_MISSING",
                        f"Session data missing for ID: {session_id[:16]}...",
                        "INFO"
                    )
                    return self._create_new_session()
                
                # 4. セッションデータのデコード（エラーハンドリング強化）
                try:
                    decoded_data = self._decode_session_data(session_data)
                    
                    if not decoded_data:
                        logger.warning(f"⚠️ SL-2.2 Phase 3: Session data decode failed for {session_id}")
                        log_security_event(
                            "SESSION_DECODE_FAILED",
                            f"Failed to decode session data for ID: {session_id[:16]}...",
                            "WARNING"
                        )
                        # データ破損時はセッションを削除して新規作成
                        self._delete_session(session_id)
                        return self._create_new_session()
                    
                except Exception as decode_error:
                    logger.error(f"❌ SL-2.2 Phase 3: Session data corruption detected: {decode_error}")
                    log_security_event(
                        "SESSION_DATA_CORRUPTION",
                        f"Session data corruption: {decode_error}",
                        "ERROR"
                    )
                    # 破損したセッションを削除
                    self._delete_session(session_id)
                    return self._create_new_session()
                
                # 5. セッションの整合性チェック
                if isinstance(decoded_data, dict):
                    # 必要に応じて特定のフィールドの存在チェック
                    # 例: ログイン状態の確認
                    if 'logged_in' in decoded_data and not isinstance(decoded_data['logged_in'], bool):
                        logger.warning("⚠️ SL-2.2 Phase 3: Session data integrity issue - logged_in field")
                        log_security_event(
                            "SESSION_INTEGRITY_WARNING",
                            "Session data integrity issue detected",
                            "WARNING"
                        )
                
                # 🆕 SL-2.2 Phase 5: TTL自動更新機能
                # セッション読み込み成功時にTTLを更新（アクセスごとに期限延長）
                try:
                    self.redis_manager.redis_client.expire(session_key, self.ttl)
                    logger.debug(f"✅ SL-2.2 Phase 5: TTL updated for session {session_id[:16]}...")
                except Exception as ttl_error:
                    logger.warning(f"⚠️ SL-2.2 Phase 5: Failed to update TTL: {ttl_error}")
                    # TTL更新失敗してもセッション自体は継続
                
                # 6. 正常なセッションオブジェクトを返す
                session = LangPontSession(decoded_data, session_id)
                logger.debug(f"📦 SL-2.2 Phase 3: Session loaded successfully: {session_id[:16]}... -> {list(decoded_data.keys())}")
                return session
                
            except ConnectionError as conn_error:
                logger.error(f"❌ SL-2.2 Phase 3: Redis connection error: {conn_error}")
                log_security_event(
                    "REDIS_CONNECTION_ERROR",
                    f"Redis connection error during session open: {conn_error}",
                    "ERROR"
                )
                return self._create_new_session()
                
            except TimeoutError as timeout_error:
                logger.error(f"❌ SL-2.2 Phase 3: Redis timeout error: {timeout_error}")
                log_security_event(
                    "REDIS_TIMEOUT_ERROR",
                    f"Redis timeout during session open: {timeout_error}",
                    "ERROR"
                )
                return self._create_new_session()
                
            except ResponseError as resp_error:
                logger.error(f"❌ SL-2.2 Phase 3: Redis response error: {resp_error}")
                log_security_event(
                    "REDIS_RESPONSE_ERROR",
                    f"Redis response error during session open: {resp_error}",
                    "ERROR"
                )
                return self._create_new_session()
                
            except Exception as redis_error:
                logger.error(f"❌ SL-2.2 Phase 3: Unexpected Redis error: {redis_error}")
                log_security_event(
                    "REDIS_UNEXPECTED_ERROR",
                    f"Unexpected Redis error during session open: {redis_error}",
                    "ERROR"
                )
                return self._create_new_session()
        
        except Exception as e:
            logger.error(f"❌ SL-2.2 Phase 3: Critical error in open_session: {e}")
            log_security_event(
                "SESSION_OPEN_CRITICAL_ERROR",
                f"Critical error in open_session: {e}",
                "ERROR"
            )
            # 最後の手段として新規セッション作成
            return self._create_new_session()
    
    def save_session(self, app: Flask, session: LangPontSession, response: Response) -> None:
        """
        🆕 SL-2.2 Phase 3: エラー対応強化版セッション保存
        
        エラーハンドリング:
        - Redis接続エラー時の代替処理
        - セッションデータ保存失敗時の復旧
        - Cookie設定エラー時のフォールバック
        
        Args:
            app: Flaskアプリケーション
            session: セッションオブジェクト
            response: HTTPレスポンス
        """
        try:
            # 1. セッション状態の確認
            if not session.modified and not session.new:
                logger.debug("🔄 SL-2.2 Phase 3: Session not modified, skipping save")
                return
            
            # 2. 空セッションの処理（削除処理）
            if not session:
                logger.debug("🗑️ SL-2.2 Phase 3: Empty session, processing deletion")
                
                if session.session_id:
                    # 既存セッションを安全に削除
                    deletion_success = self._delete_session(session.session_id)
                    
                    if deletion_success:
                        log_security_event(
                            "SESSION_DELETED_EMPTY",
                            f"Empty session deleted: {session.session_id[:16]}...",
                            "INFO"
                        )
                    
                    # Cookieを削除
                    try:
                        response.set_cookie(
                            self.cookie_name,
                            expires=0,
                            httponly=True,
                            secure=app.config.get('SESSION_COOKIE_SECURE', False),
                            samesite=app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
                        )
                        logger.debug("🍪 SL-2.2 Phase 3: Session cookie cleared")
                    except Exception as cookie_error:
                        logger.warning(f"⚠️ SL-2.2 Phase 3: Failed to clear session cookie: {cookie_error}")
                
                return
            
            # 3. セッションIDの生成または使用
            if not session.session_id:
                session.session_id = self._generate_session_id()
                session.new = False
                logger.debug(f"🆔 SL-2.2 Phase 3: New session ID generated: {session.session_id[:16]}...")
            
            # 4. セッションデータのRedis保存（エラーハンドリング強化）
            redis_save_success = False
            
            if self.redis_manager and self.redis_manager.is_connected:
                try:
                    session_key = self._get_session_key(session.session_id)
                    
                    # セッションデータの前処理・検証
                    redis_data = {}
                    for k, v in session.items():
                        # キーの検証
                        if not isinstance(k, str) or len(k) == 0:
                            logger.warning(f"⚠️ SL-2.2 Phase 3: Invalid session key: {k}")
                            continue
                        
                        # 値の変換
                        if isinstance(v, bool):
                            redis_data[k] = str(v).lower()
                        elif v is None:
                            redis_data[k] = ""
                        elif isinstance(v, (int, float)):
                            redis_data[k] = str(v)
                        elif isinstance(v, str):
                            # 文字列長の制限チェック（必要に応じて調整）
                            if len(v) > 10000:  # 10KB制限
                                logger.warning(f"⚠️ SL-2.2 Phase 3: Session value too large for key: {k}")
                                redis_data[k] = v[:10000]  # 切り詰め
                            else:
                                redis_data[k] = v
                        else:
                            # 複雑なオブジェクトはJSON化
                            try:
                                redis_data[k] = json.dumps(v)
                            except (TypeError, ValueError) as json_error:
                                logger.warning(f"⚠️ SL-2.2 Phase 3: Cannot serialize session value for key {k}: {json_error}")
                                redis_data[k] = str(v)  # 文字列にフォールバック
                    
                    # Redis保存の実行
                    self.redis_manager.redis_client.hset(session_key, mapping=redis_data)
                    self.redis_manager.redis_client.expire(session_key, self.ttl)
                    
                    redis_save_success = True
                    logger.debug(f"💾 SL-2.2 Phase 3: Session saved to Redis: {session.session_id[:16]}... -> {list(session.keys())}")
                    
                    # 保存成功のセキュリティログ
                    log_security_event(
                        "SESSION_SAVED_SUCCESS",
                        f"Session saved successfully: {session.session_id[:16]}...",
                        "INFO"
                    )
                    
                except ConnectionError as conn_error:
                    logger.error(f"❌ SL-2.2 Phase 3: Redis connection error during save: {conn_error}")
                    log_security_event(
                        "REDIS_CONNECTION_ERROR",
                        f"Redis connection error during session save: {conn_error}",
                        "ERROR"
                    )
                    
                except TimeoutError as timeout_error:
                    logger.error(f"❌ SL-2.2 Phase 3: Redis timeout during save: {timeout_error}")
                    log_security_event(
                        "REDIS_TIMEOUT_ERROR",
                        f"Redis timeout during session save: {timeout_error}",
                        "ERROR"
                    )
                    
                except ResponseError as resp_error:
                    logger.error(f"❌ SL-2.2 Phase 3: Redis response error during save: {resp_error}")
                    log_security_event(
                        "REDIS_RESPONSE_ERROR",
                        f"Redis response error during session save: {resp_error}",
                        "ERROR"
                    )
                    
                except Exception as redis_error:
                    logger.error(f"❌ SL-2.2 Phase 3: Unexpected Redis error during save: {redis_error}")
                    log_security_event(
                        "REDIS_SAVE_ERROR",
                        f"Unexpected Redis error during session save: {redis_error}",
                        "ERROR"
                    )
            else:
                logger.warning("⚠️ SL-2.2 Phase 3: Redis not available for session save")
                log_security_event(
                    "REDIS_UNAVAILABLE_SAVE",
                    "Redis unavailable during session save",
                    "WARNING"
                )
            
            # 5. Cookie設定（エラーハンドリング強化）
            try:
                cookie_config = {
                    'key': self.cookie_name,
                    'value': session.session_id,
                    'max_age': self.ttl,
                    'httponly': True,  # JavaScript経由のアクセス防止
                    'samesite': 'Lax',  # CSRF攻撃防止
                    'path': '/',
                    'domain': None
                }
                
                # HTTPS環境での追加セキュリティ
                if app.config.get('SESSION_COOKIE_SECURE', False):
                    cookie_config['secure'] = True  # HTTPS通信時のみ送信
                
                response.set_cookie(**cookie_config)
                
                logger.debug(f"🍪 SL-2.2 Phase 3: Session cookie set: {list(cookie_config.keys())}")
                
                # Cookie設定成功のログ
                if redis_save_success:
                    log_security_event(
                        "SESSION_COMPLETE_SUCCESS",
                        f"Session and cookie saved successfully: {session.session_id[:16]}...",
                        "INFO"
                    )
                else:
                    log_security_event(
                        "SESSION_PARTIAL_SUCCESS",
                        f"Cookie saved but Redis failed: {session.session_id[:16]}...",
                        "WARNING"
                    )
                
            except Exception as cookie_error:
                logger.error(f"❌ SL-2.2 Phase 3: Failed to set session cookie: {cookie_error}")
                log_security_event(
                    "COOKIE_SET_ERROR",
                    f"Failed to set session cookie: {cookie_error}",
                    "ERROR"
                )
                
                # Cookie設定失敗時でもRedis保存が成功していれば部分的成功
                if redis_save_success:
                    logger.warning("⚠️ SL-2.2 Phase 3: Session saved to Redis but cookie failed")
            
        except Exception as e:
            logger.error(f"❌ SL-2.2 Phase 3: Critical error in save_session: {e}")
            log_security_event(
                "SESSION_SAVE_CRITICAL_ERROR",
                f"Critical error in save_session: {e}",
                "ERROR"
            )
            # 重大エラー時でも処理を継続（フェイルセーフ）
    
    def make_null_session(self, app: Flask) -> LangPontSession:
        """
        🆕 SL-2.2 Phase 3: エラー対応強化版 null session生成
        
        エラーシナリオ:
        - Redis接続失敗時のフォールバック
        - セッションデータ破損時の復旧
        - 認証されていない場合のクリーンセッション
        
        Returns:
            LangPontSession: 空のセッションオブジェクト
        """
        try:
            # 1. セキュリティログ記録
            log_security_event(
                "NULL_SESSION_CREATED",
                "Creating null session for error recovery or unauthenticated access",
                "INFO"
            )
            
            # 2. 新しいセッションを作成
            null_session = self._create_new_session()
            
            # 3. クリーンセッションであることを確認
            null_session.modified = False
            null_session.new = True
            
            logger.debug("🔓 SL-2.2 Phase 3: Null session created successfully")
            return null_session
            
        except Exception as e:
            logger.error(f"❌ SL-2.2 Phase 3: Critical error in make_null_session: {e}")
            
            # 緊急時フォールバック: 直接LangPontSessionを作成
            try:
                emergency_session = LangPontSession()
                emergency_session.modified = False
                emergency_session.new = True
                
                # 緊急時セキュリティログ
                log_security_event(
                    "NULL_SESSION_EMERGENCY_FALLBACK",
                    f"Emergency fallback activated due to: {e}",
                    "WARNING"
                )
                
                logger.warning("⚠️ SL-2.2 Phase 3: Emergency fallback session created")
                return emergency_session
                
            except Exception as critical_error:
                logger.critical(f"💥 SL-2.2 Phase 3: CRITICAL - Cannot create any session: {critical_error}")
                
                # 最後の手段: 最小限のセッション
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
    
    def _create_new_session(self) -> LangPontSession:
        """
        新しいセッションを作成
        
        Returns:
            LangPontSession: 新しいセッションオブジェクト
        """
        try:
            new_session = LangPontSession()
            logger.debug("🆕 SL-2.2 Phase 3: New session created")
            return new_session
        except Exception as e:
            logger.error(f"❌ SL-2.2 Phase 3: Failed to create new session: {e}")
            # セキュリティログ記録
            log_security_event(
                "SESSION_CREATION_FAILED",
                f"Failed to create new session: {e}",
                "ERROR"
            )
            return LangPontSession()
    
    def _decode_session_data(self, raw_data: dict) -> dict:
        """
        Redisからの生データをセッションデータに変換
        
        Args:
            raw_data: Redisから取得した生データ
            
        Returns:
            dict: デコード済みセッションデータ
        """
        try:
            if not raw_data:
                return {}
            
            decoded_data = {}
            for k, v in raw_data.items():
                # キーのデコード
                key = k.decode('utf-8') if isinstance(k, bytes) else k
                value = v.decode('utf-8') if isinstance(v, bytes) else v
                
                # JSONフィールドの特別処理を追加（Phase 3c-4: translation_context一時復元テスト）
                json_fields = ["_data", "translation_context"]
                if key in json_fields and value:  # 空文字列チェックも含む
                    try:
                        decoded_data[key] = json.loads(value)
                    except json.JSONDecodeError as e:
                        # セッションIDの取得（可能であれば）
                        session_id = decoded_data.get('session_id', 'unknown')
                        
                        # 警告ログ出力
                        logger.warning(f"⚠️ SL-2.2 Phase 3: JSON corruption detected in session {session_id[:8]}... field {key}: {e}")
                        
                        # セキュリティイベント記録
                        log_security_event('SESSION_JSON_CORRUPTION', f'Corrupted {key} field in session {session_id[:8]}...', 'WARNING')
                        
                        # 安全なフォールバック：空の辞書を設定
                        decoded_data[key] = {}
                        
                        # 注意：例外は再発生させない（セッション全体を無効化しない）
                else:
                    # データ型の復元
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
            
            logger.debug(f"🔧 SL-2.2 Phase 3: Session data decoded: {list(decoded_data.keys())}")
            return decoded_data
            
        except Exception as e:
            logger.error(f"❌ SL-2.2 Phase 3: Failed to decode session data: {e}")
            # セキュリティログ記録
            log_security_event(
                "SESSION_DATA_CORRUPTION",
                f"Failed to decode session data: {e}",
                "ERROR"
            )
            return {}
    
    def _delete_session(self, session_id: str) -> bool:
        """
        セッションデータを安全に削除
        
        Args:
            session_id: セッションID
            
        Returns:
            bool: 削除成功フラグ
        """
        try:
            if not session_id:
                logger.warning("⚠️ SL-2.2 Phase 3: No session ID provided for deletion")
                return False
            
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("⚠️ SL-2.2 Phase 3: Redis not available for session deletion")
                return False
            
            session_key = self._get_session_key(session_id)
            
            # セッション削除の試行
            result = self.redis_manager.redis_client.delete(session_key)
            
            if result:
                logger.info(f"🗑️ SL-2.2 Phase 3: Session deleted successfully: {session_id}")
                # セキュリティログ記録
                log_security_event(
                    "SESSION_DELETED",
                    f"Session deleted: {session_id}",
                    "INFO"
                )
                return True
            else:
                logger.warning(f"⚠️ SL-2.2 Phase 3: Session not found for deletion: {session_id}")
                return False
                
        except ConnectionError as e:
            logger.error(f"❌ SL-2.2 Phase 3: Redis connection error during deletion: {e}")
            log_security_event(
                "REDIS_CONNECTION_ERROR",
                f"Connection error during session deletion: {e}",
                "ERROR"
            )
            return False
            
        except Exception as e:
            logger.error(f"❌ SL-2.2 Phase 3: Unexpected error during session deletion: {e}")
            log_security_event(
                "SESSION_DELETION_ERROR",
                f"Unexpected error during session deletion: {e}",
                "ERROR"
            )
            return False

    def regenerate_session_id(self, session: LangPontSession) -> str:
        """
        セッションIDを再生成（セッション固定攻撃対策）
        
        Args:
            session: 現在のセッションオブジェクト
            
        Returns:
            str: 新しいセッションID
        """
        try:
            # 1. 新しいセッションIDを生成（UUID4使用）
            import uuid
            new_session_id = str(uuid.uuid4())
            
            # 2. 既存のセッションIDを取得
            old_session_id = getattr(session, 'session_id', None)
            
            if old_session_id and self.redis_manager and self.redis_manager.is_connected:
                try:
                    # 3. Redisから既存データを取得
                    old_session_key = self._get_session_key(old_session_id)
                    session_data = self.redis_manager.redis_client.hgetall(old_session_key)
                    
                    if session_data:
                        # 4. 既存データを新IDにコピー
                        new_session_key = self._get_session_key(new_session_id)
                        self.redis_manager.redis_client.hset(new_session_key, mapping=session_data)
                        self.redis_manager.redis_client.expire(new_session_key, self.ttl)
                        
                        # 5. 古いセッションデータを削除
                        self.redis_manager.redis_client.delete(old_session_key)
                        
                        logger.info(f"🔄 SL-2.2: Session ID regenerated: {old_session_id} -> {new_session_id}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ SL-2.2: Failed to migrate session data: {e}")
            
            # 6. セッションオブジェクトのIDを更新
            session.session_id = new_session_id
            session.modified = True
            
            logger.info(f"✅ SL-2.2: Session ID regeneration completed: {new_session_id}")
            return new_session_id
            
        except Exception as e:
            logger.error(f"❌ SL-2.2: Error in regenerate_session_id: {e}")
            # フォールバック: 新しいIDのみ生成
            import uuid
            new_session_id = str(uuid.uuid4())
            session.session_id = new_session_id
            session.modified = True
            return new_session_id


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