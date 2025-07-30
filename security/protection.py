"""
CSRF・レート制限保護機能モジュール
Task B2-9-Phase5で分離、Task #8 SL-4でRedis対応

このモジュールは以下の関数を提供します：
- generate_csrf_token: セキュアなCSRFトークンを生成（Redis対応）
- validate_csrf_token: CSRFトークンの厳密な検証（Redis対応）
- enhanced_rate_limit_check: 強化されたレート制限（通常 + バースト制限）
- analytics_rate_limit_check: Analytics専用の緩いレート制限
"""

import time
import secrets
from typing import Optional
from flask import session
from security.security_logger import log_security_event

# 🆕 Task #8 SL-4: CSRFRedisManager統合
_csrf_redis_manager = None

def _get_csrf_redis_manager():
    """CSRFRedisManagerのLazy初期化（循環インポート回避）"""
    global _csrf_redis_manager
    if _csrf_redis_manager is None:
        try:
            from services.csrf_redis_manager import get_csrf_redis_manager
            _csrf_redis_manager = get_csrf_redis_manager()
        except Exception as e:
            # Redis初期化失敗時はNoneのまま（フォールバック動作）
            pass
    return _csrf_redis_manager

def _get_session_id_for_csrf() -> Optional[str]:
    """CSRF用セッションID取得（app.pyのロジックと同一）"""
    # session_idの取得（app.pyと同じフォールバック順序）
    session_id = getattr(session, 'session_id', None) or session.get("session_id") or session.get("csrf_token", "")[:16]
    
    # 最終フォールバック：タイムスタンプベース
    if not session_id:
        import time
        session_id = f"csrf_{int(time.time())}"
        
    return session_id


def generate_csrf_token() -> str:
    """
    セキュアなCSRFトークンを生成（Redis対応）
    
    Task #8 SL-4: Redis保存を追加、フォールバック機構付き
    """
    # 既存のセッショントークンがある場合はそれを返す（変更なし）
    if 'csrf_token' in session:
        existing_token = session['csrf_token']
        
        # 🆕 Redis同期: 既存トークンをRedisにも保存
        csrf_manager = _get_csrf_redis_manager()
        if csrf_manager:
            session_id = _get_session_id_for_csrf()
            if session_id:
                csrf_manager.save_csrf_token(session_id, existing_token)
        
        return existing_token
    
    # 新規トークン生成
    new_token = secrets.token_urlsafe(32)
    session['csrf_token'] = new_token
    
    # 🆕 Redis保存: 新規トークンを保存（失敗してもセッション保存は継続）
    csrf_manager = _get_csrf_redis_manager()
    if csrf_manager:
        session_id = _get_session_id_for_csrf()
        if session_id:
            redis_saved = csrf_manager.save_csrf_token(session_id, new_token)
            if redis_saved:
                log_security_event('CSRF_TOKEN_REDIS_SAVED', f'CSRF token saved to Redis for session {session_id[:16]}...', 'DEBUG')
            else:
                log_security_event('CSRF_TOKEN_REDIS_FALLBACK', f'CSRF token Redis save failed, using session fallback for {session_id[:16]}...', 'WARNING')
    
    return new_token


def validate_csrf_token(token: Optional[str]) -> bool:
    """
    CSRFトークンの厳密な検証（Redis対応）
    
    Task #8 SL-4: Redis検証を追加、フォールバック機構付き
    🚨 重要: secrets.compare_digest()は絶対に維持（タイミング攻撃対策）
    """
    if not token:
        return False

    # 🆕 Redis検証を最優先で試行
    csrf_manager = _get_csrf_redis_manager()
    if csrf_manager:
        session_id = _get_session_id_for_csrf()
        if session_id:
            redis_token = csrf_manager.get_csrf_token(session_id)
            if redis_token:
                # Redis取得成功：タイミング攻撃対策でsecrets.compare_digest使用
                is_valid = secrets.compare_digest(token, redis_token)
                if is_valid:
                    log_security_event('CSRF_TOKEN_REDIS_VALID', f'CSRF token validated via Redis for session {session_id[:16]}...', 'DEBUG')
                else:
                    log_security_event('CSRF_TOKEN_REDIS_INVALID', f'CSRF token validation failed via Redis for session {session_id[:16]}...', 'WARNING')
                return is_valid
            else:
                # Redis取得失敗：フォールバックへ
                log_security_event('CSRF_TOKEN_REDIS_MISS', f'CSRF token not found in Redis, falling back to session for {session_id[:16]}...', 'DEBUG')

    # フォールバック：既存のセッション検証（変更なし）
    session_token = session.get('csrf_token')
    if not session_token:
        return False

    # 🚨 重要: タイミング攻撃を防ぐためのsecrets.compare_digest使用（維持）
    is_valid = secrets.compare_digest(token, session_token)
    if is_valid:
        log_security_event('CSRF_TOKEN_SESSION_VALID', 'CSRF token validated via session fallback', 'DEBUG')
    else:
        log_security_event('CSRF_TOKEN_SESSION_INVALID', 'CSRF token validation failed via session fallback', 'WARNING')
    
    return is_valid


def enhanced_rate_limit_check(client_ip: str, limit: int = 1000, window: int = 300, burst_limit: int = 500, burst_window: int = 60, rate_limit_store: dict = None) -> bool:
    """強化されたレート制限（通常 + バースト制限）"""
    if rate_limit_store is None:
        # フォールバック用の空辞書（本来はapp.pyから渡される）
        rate_limit_store = {}
    
    now = time.time()

    # 通常のレート制限
    cutoff = now - window
    rate_limit_store.setdefault(client_ip, [])
    rate_limit_store[client_ip] = [
        timestamp for timestamp in rate_limit_store[client_ip]
        if timestamp > cutoff
    ]

    current_requests = len(rate_limit_store[client_ip])

    # バースト制限チェック
    burst_cutoff = now - burst_window
    recent_requests = [
        timestamp for timestamp in rate_limit_store[client_ip]
        if timestamp > burst_cutoff
    ]

    if len(recent_requests) >= burst_limit:
        log_security_event(
            'BURST_RATE_LIMIT_EXCEEDED',
            f'IP {client_ip} exceeded burst limit: {len(recent_requests)}/{burst_limit} in {burst_window}s',
            'WARNING'
        )
        return False

    if current_requests >= limit:
        log_security_event(
            'RATE_LIMIT_EXCEEDED',
            f'IP {client_ip} exceeded rate limit: {current_requests}/{limit} in {window}s',
            'WARNING'
        )
        return False

    # 新しいリクエストを記録
    rate_limit_store[client_ip].append(now)
    return True


def analytics_rate_limit_check(client_ip: str, limit: int = 500, window: int = 300, burst_limit: int = 100, burst_window: int = 60, rate_limit_store: dict = None) -> bool:
    """
    🆕 Task 2.9.1: Analytics専用の緩いレート制限
    Analytics追跡のための高頻度リクエストに対応
    - 通常制限: 500req/5分 (vs 一般的な50req/5分)
    - バースト制限: 100req/1分 (vs 一般的な15req/1分)
    """
    if rate_limit_store is None:
        # フォールバック用の空辞書（本来はapp.pyから渡される）
        rate_limit_store = {}
    
    now = time.time()

    # Analytics専用のレート制限ストレージ
    analytics_key = f"analytics_{client_ip}"
    rate_limit_store.setdefault(analytics_key, [])

    # 古いリクエストを削除
    cutoff = now - window
    rate_limit_store[analytics_key] = [
        timestamp for timestamp in rate_limit_store[analytics_key]
        if timestamp > cutoff
    ]

    current_requests = len(rate_limit_store[analytics_key])

    # バースト制限チェック
    burst_cutoff = now - burst_window
    recent_requests = [
        timestamp for timestamp in rate_limit_store[analytics_key]
        if timestamp > burst_cutoff
    ]

    if len(recent_requests) >= burst_limit:
        log_security_event(
            'ANALYTICS_BURST_LIMIT_EXCEEDED',
            f'IP {client_ip} exceeded analytics burst limit: {len(recent_requests)}/{burst_limit} in {burst_window}s',
            'WARNING'
        )
        return False

    if current_requests >= limit:
        log_security_event(
            'ANALYTICS_RATE_LIMIT_EXCEEDED',
            f'IP {client_ip} exceeded analytics rate limit: {current_requests}/{limit} in {window}s',
            'WARNING'
        )
        return False

    # 新しいリクエストを記録
    rate_limit_store[analytics_key].append(now)
    return True