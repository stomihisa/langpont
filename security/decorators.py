"""
セキュリティデコレータ群モジュール
Task B2-9-Phase6で分離 - Task B2-9完全制覇

このモジュールは以下のデコレータを提供します：
- csrf_protect: CSRF保護デコレータ（強化版）
- require_rate_limit: レート制限デコレータ（強化版）
- require_analytics_rate_limit: Analytics専用レート制限デコレータ（緩和版）
- require_login: ログイン認証が必要なエンドポイント用デコレータ
"""

from functools import wraps
from flask import session, request, redirect, url_for, abort
from security.protection import validate_csrf_token, enhanced_rate_limit_check, analytics_rate_limit_check
from security.request_helpers import get_client_ip_safe, get_user_agent_safe, get_endpoint_safe
from security.security_logger import log_security_event


def csrf_protect(f):
    """CSRF保護デコレータ（強化版）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == "POST":
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            if not validate_csrf_token(token):
                # セキュリティログの記録（グローバル参照回避のため直接記録）
                import logging
                security_logger = logging.getLogger('security')
                security_logger.warning(
                    f"CSRF attack attempt - IP: {get_client_ip_safe()}, "
                    f"UA: {get_user_agent_safe()}, "
                    f"Endpoint: {get_endpoint_safe()}"
                )
                abort(403)
        return f(*args, **kwargs)
    return decorated_function


def require_rate_limit(f):
    """レート制限デコレータ（強化版）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = get_client_ip_safe()
        
        # rate_limit_storeを外部から取得する必要がある
        # アプリケーションのグローバル変数にアクセス
        import sys
        app_module = sys.modules.get('__main__')
        rate_limit_store = getattr(app_module, 'rate_limit_store', {}) if app_module else {}

        if not enhanced_rate_limit_check(client_ip, rate_limit_store=rate_limit_store):
            log_security_event(
                'RATE_LIMIT_BLOCKED',
                f'Request blocked for IP {client_ip}',
                'WARNING'
            )
            abort(429)

        return f(*args, **kwargs)
    return decorated_function


def require_analytics_rate_limit(f):
    """🆕 Analytics専用レート制限デコレータ（緩和版）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = get_client_ip_safe()

        # rate_limit_storeを外部から取得する必要がある
        # アプリケーションのグローバル変数にアクセス
        import sys
        app_module = sys.modules.get('__main__')
        rate_limit_store = getattr(app_module, 'rate_limit_store', {}) if app_module else {}

        # Analytics専用の緩い制限（500req/5min, 100burst/1min）
        if not analytics_rate_limit_check(client_ip, rate_limit_store=rate_limit_store):
            log_security_event(
                'ANALYTICS_RATE_LIMIT_BLOCKED',
                f'Analytics request blocked for IP {client_ip}',
                'WARNING'
            )
            abort(429)

        return f(*args, **kwargs)
    return decorated_function


def require_login(f):
    """ログイン認証が必要なエンドポイント用デコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 新旧認証システムの統合チェック
        new_auth = session.get('authenticated') and session.get('user_id')
        legacy_auth = session.get('logged_in')

        if not new_auth and not legacy_auth:
            log_security_event('UNAUTHORIZED_ACCESS', 
                             f'Attempted access to protected endpoint: {request.endpoint}', 
                             'WARNING')
            return redirect(url_for('login'))

        return f(*args, **kwargs)
    return decorated_function