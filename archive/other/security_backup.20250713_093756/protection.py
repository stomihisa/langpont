"""
CSRF・レート制限保護機能モジュール
Task B2-9-Phase5で分離

このモジュールは以下の関数を提供します：
- generate_csrf_token: セキュアなCSRFトークンを生成
- validate_csrf_token: CSRFトークンの厳密な検証
- enhanced_rate_limit_check: 強化されたレート制限（通常 + バースト制限）
- analytics_rate_limit_check: Analytics専用の緩いレート制限
"""

import time
import secrets
from typing import Optional
from flask import session
from security.security_logger import log_security_event


def generate_csrf_token() -> str:
    """セキュアなCSRFトークンを生成"""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


def validate_csrf_token(token: Optional[str]) -> bool:
    """CSRFトークンの厳密な検証"""
    if not token:
        return False

    session_token = session.get('csrf_token')
    if not session_token:
        return False

    # タイミング攻撃を防ぐためのsecrets.compare_digest使用
    return secrets.compare_digest(token, session_token)


def enhanced_rate_limit_check(client_ip: str, limit: int = 50, window: int = 300, burst_limit: int = 15, burst_window: int = 60, rate_limit_store: dict = None) -> bool:
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