import os
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
import hashlib
import logging
import re
from functools import wraps
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from logging.handlers import RotatingFileHandler
from typing import Tuple, Dict, Any, List, Optional, Union
import gc
import threading
import time

# 🆕 Task 2.9.2 Phase B-3.5.10: 統合活動ログシステム
try:
    from activity_logger import log_analysis_activity, activity_logger, get_jst_today
    print("✅ Activity Logger imported successfully")
except ImportError as e:
    print(f"⚠️ Activity Logger import failed: {e}")
    # フォールバック：ダミー関数
    def log_analysis_activity(data):
        pass
    activity_logger = None
    def get_jst_today():
        from datetime import datetime
        return datetime.now().date()

# Configuration import
from config import VERSION, ENVIRONMENT, FEATURES, DEPLOYMENT, USAGE_LIMITS

# 🆕 Task B2-8: 推奨抽出システム分離
from analysis.recommendation import extract_recommendation_from_analysis

# 🆕 Task B2-9-Phase1: セキュリティモジュール分離
from security.input_validation import EnhancedInputValidator
from security.session_security import SecureSessionManager, SecurePasswordManager
from security.request_helpers import (
    get_client_ip, get_client_ip_safe, get_user_agent_safe, 
    get_endpoint_safe, get_method_safe
)
from security.security_logger import log_security_event, log_access_event
from security.protection import (
    generate_csrf_token, validate_csrf_token,
    enhanced_rate_limit_check, analytics_rate_limit_check
)
from security.decorators import (
    csrf_protect, require_rate_limit, 
    require_analytics_rate_limit, require_login
)

# 🆕 Task B2-10-Phase1a: 翻訳モジュール分離 (Phase 3c-1b: TranslationContext統合済み)

# 🆕 Task B2-10-Phase1b: 分析エンジン管理モジュール分離
from translation.analysis_engine import AnalysisEngineManager

# 🆕 Task B2-10-Phase1c: 翻訳エキスパートAI安全部分分離
from translation.expert_ai import LangPontTranslationExpertAI

# 🆕 Task #9 AP-1 Phase 1: 翻訳API分離
from routes.translation import init_translation_routes
from services.translation_service import TranslationService

# 🎯 TaskH2-2(B2-3) Stage 2 Phase 7: エンジン状態管理モジュール統合
from routes.engine_management import create_engine_management_blueprint

# 🆕 認証システムインポート（緊急デバッグ版）
try:
    from user_auth import UserAuthSystem

    from auth_routes import init_auth_routes

    AUTH_SYSTEM_AVAILABLE = True
    app_logger = logging.getLogger('app')
    app_logger.info("認証システム正常にインポートされました")

except ImportError as e:
    import traceback
    AUTH_SYSTEM_AVAILABLE = False
    app_logger = logging.getLogger('app')
    app_logger.warning(f"認証システムのインポートに失敗: {str(e)}")
    app_logger.info("従来の認証システムを使用します")
except Exception as e:
    import traceback
    AUTH_SYSTEM_AVAILABLE = False

# 🆕 翻訳履歴システムインポート
try:
    from translation_history import (
        TranslationHistoryManager, TranslationRequest, TranslationResult,
        TranslationEngine, translation_history_manager
    )
    TRANSLATION_HISTORY_AVAILABLE = True
    app_logger = logging.getLogger('app')
    app_logger.info("翻訳履歴システム正常にインポートされました")
except ImportError as e:
    TRANSLATION_HISTORY_AVAILABLE = False
    app_logger = logging.getLogger('app')
    app_logger.warning(f"翻訳履歴システムのインポートに失敗: {str(e)}")
    app_logger.info("翻訳履歴機能は無効になります")
except Exception as e:
    TRANSLATION_HISTORY_AVAILABLE = False
    app_logger = logging.getLogger('app')
    app_logger.error(f"翻訳履歴システムの初期化エラー: {str(e)}")
    app_logger.info("翻訳履歴機能は無効になります")

# バージョン情報の定義
VERSION_INFO = {
    "file_name": "app.py",
    "version": VERSION,
    "environment": ENVIRONMENT,
    "created_date": "2025/6/4",
    "optimization": "🛡️ 友人アドバイス反映版: セキュリティ強化完全版",
    "status": "本番準備完了"
}

# .env を読み込む
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from flask import Flask, render_template, request, session, redirect, url_for, jsonify, abort, make_response
from werkzeug.exceptions import RequestEntityTooLarge
from openai import OpenAI
from anthropic import Anthropic
import requests
import time
import re
import sqlite3  # 🆕 Task 2.9.1: Analytics database support
from labels import labels

# 🆕 強化されたログ設定（ログローテーション対応）
def setup_enhanced_logging() -> Tuple[logging.Logger, logging.Logger, logging.Logger]:
    """ログローテーション対応の強化ログ設定"""

    # ログディレクトリ作成
    os.makedirs('logs', exist_ok=True)

    # ログレベル設定
    log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO

    # セキュリティログ（10MB x 5ファイル）
    security_logger = logging.getLogger('security')
    security_logger.setLevel(log_level)
    security_handler = RotatingFileHandler(
        'logs/security.log', 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )

    # アプリケーションログ（10MB x 5ファイル）
    app_logger = logging.getLogger('app')
    app_logger.setLevel(log_level)
    app_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )

    # アクセスログ（新規追加）
    access_logger = logging.getLogger('access')
    access_logger.setLevel(logging.INFO)
    access_handler = RotatingFileHandler(
        'logs/access.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )

    # フォーマッター（IP、User-Agent含む）
    security_formatter = logging.Formatter(
        '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
    )
    app_formatter = logging.Formatter(
        '%(asctime)s - APP - %(levelname)s - %(message)s'
    )
    access_formatter = logging.Formatter(
        '%(asctime)s - ACCESS - %(message)s'
    )

    security_handler.setFormatter(security_formatter)
    app_handler.setFormatter(app_formatter)
    access_handler.setFormatter(access_formatter)

    security_logger.addHandler(security_handler)
    app_logger.addHandler(app_handler)
    access_logger.addHandler(access_handler)

    # services.langpont_redis_session ロガー
    langpont_session_logger = logging.getLogger('services.langpont_redis_session')
    langpont_session_logger.setLevel(log_level)
    langpont_session_logger.addHandler(app_handler)  # app.log に出力
    langpont_session_logger.propagate = False

    return security_logger, app_logger, access_logger

# ログ初期化
security_logger, app_logger, access_logger = setup_enhanced_logging()

# 🆕 Flask-Talisman相当のセキュリティヘッダー設定

# APIキー取得
api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_TEST")
if not api_key:
    raise ValueError("OPENAI_API_KEY が環境変数に見つかりません")

# Flask設定
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB制限

# 🆕 本番環境での詳細設定
if ENVIRONMENT == "production":
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
else:
    app.config['DEBUG'] = FEATURES["debug_mode"]

# セキュリティ設定
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

# 🆕 SL-2.1: Flask標準セッション設定（明示的に確認）
app.config['SESSION_TYPE'] = 'filesystem'  # 絶対に変更しない

# 🆕 SL-2.1: SessionRedisManager初期化（Redisが利用可能な場合のみ）
try:
    from services.session_redis_manager import get_session_redis_manager
    session_redis_manager = get_session_redis_manager()
    app.session_redis_manager = session_redis_manager
    app_logger.info("✅ SL-2.1: SessionRedisManager initialized successfully")
except Exception as e:
    app_logger.warning(f"⚠️ SL-2.1: Redis manager initialization failed: {e} - continuing with filesystem sessions only")
    session_redis_manager = None
    app.session_redis_manager = None

# 🆕 SL-3 Phase 1: TranslationStateManager初期化
try:
    from services.translation_state_manager import get_translation_state_manager
    translation_state_manager = get_translation_state_manager()
    app.translation_state_manager = translation_state_manager
    app_logger.info("✅ SL-3 Phase 1: TranslationStateManager initialized successfully")
except Exception as e:
    app_logger.warning(f"⚠️ SL-3 Phase 1: TranslationStateManager initialization failed: {e} - using session fallback")
    translation_state_manager = None
    app.translation_state_manager = None

# 🆕 SL-2.2: Redis Session Implementation
from config import USE_REDIS_SESSION, SESSION_TTL_SECONDS, SESSION_COOKIE_NAME
from config import SESSION_COOKIE_SECURE, SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SAMESITE

if USE_REDIS_SESSION:
    try:
        from services.langpont_redis_session import LangPontRedisSession
        app.session_interface = LangPontRedisSession(
            redis_manager=session_redis_manager,
            cookie_name=SESSION_COOKIE_NAME,
            ttl=SESSION_TTL_SECONDS
        )
        app_logger.info("✅ SL-2.2: LangPontRedisSession enabled")
    except Exception as e:
        app_logger.error(f"❌ SL-2.2: Failed to enable Redis session: {e}")
        # フォールバック：標準セッションを使用
else:
    app_logger.info("📝 SL-2.2: Using Flask standard session (filesystem)")

# 🆕 SL-2.2: Session security configuration
app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE
app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY
app.config['SESSION_COOKIE_SAMESITE'] = SESSION_COOKIE_SAMESITE
app.config['SESSION_COOKIE_NAME'] = SESSION_COOKIE_NAME

# 🆕 SL-2.2 Phase 2: Flask標準Cookieの無効化確認
@app.after_request
def check_session_cookies(response):
    """セッションCookieの状態を確認"""
    cookies = response.headers.getlist('Set-Cookie')
    for cookie in cookies:
        if cookie.startswith('session='):
            app_logger.warning("⚠️ SL-2.2: Flask standard session cookie detected - should be disabled!")
        elif cookie.startswith('langpont_session='):
            app_logger.debug("✅ SL-2.2: LangPont session cookie detected")
    return response

# 🆕 SL-2.1: 認証チェック機能（Redis復元付き）
def check_auth_with_redis_fallback():
    """
    認証チェック（Redisフォールバック付き）
    
    1. まずFlaskセッションを確認（メイン）
    2. 失敗時はRedisから復元を試行（補助）
    """
    # まずFlaskセッションを確認（これが主）
    if session.get("logged_in"):
        return True
    
    # Redisからの復元を試みる（あくまで補助）
    if session_redis_manager and getattr(session, 'session_id', None):
        try:
            auth_data = session_redis_manager.get_auth_from_redis(
                session_id=session.session_id
            )
            if auth_data and auth_data.get('logged_in'):
                # Flaskセッションに復元
                session.update({
                    'logged_in': auth_data.get('logged_in'),
                    'username': auth_data.get('username'),
                    'user_role': auth_data.get('user_role'),
                    'daily_limit': auth_data.get('daily_limit')
                })
                app_logger.info(f"✅ SL-2.1: Auth restored from Redis for user: {auth_data.get('username')}")
                return True
        except Exception as e:
            app_logger.debug(f"Redis auth fallback failed: {e}")
    
    return False

# OpenAI client
client = OpenAI(api_key=api_key)

# 🆕 Claude API client (Task 2.9.2 Phase B-3.5.7)
claude_api_key = os.getenv("CLAUDE_API_KEY")
if not claude_api_key:
    app_logger.warning("CLAUDE_API_KEY not found - Claude analysis will be disabled")
    claude_client = None
else:
    try:
        claude_client = Anthropic(api_key=claude_api_key)
        app_logger.info("Claude API client initialized successfully")
    except Exception as e:
        app_logger.error(f"Failed to initialize Claude client: {e}")
        claude_client = None

# Task #9 AP-1 Phase 1: TranslationService initialization moved after check_daily_usage definition

# 🚀 Task 2.9.2 Phase B-1: 管理者システム統合
print("🚀 Phase B-1: 管理者システム統合開始")
try:
    from admin_routes import init_admin_routes
    from admin_logger import admin_logger, log_translation_event, log_gemini_analysis, log_api_call, log_error
    from admin_auth import admin_auth_manager, require_admin_access
    from routes.debug_routes import debug_bp  # 🆕 デバッグルート追加
    from routes.security_routes import init_security_routes  # 🆕 セキュリティルート追加
    from routes.dev_api_routes import init_dev_api_routes  # 🆕 Phase 4b-1: Dev API分離
    from routes.admin_api_routes import init_admin_api_routes  # 🆕 Phase 4b-2: Admin API分離

    # 管理者ルートを登録
    init_admin_routes(app)
    app.register_blueprint(debug_bp)  # 🆕 デバッグBlueprintの登録
    init_security_routes(app)  # 🆕 セキュリティBlueprintの登録
    init_dev_api_routes(app)  # 🆕 Phase 4b-1: Dev API Blueprint登録
    init_admin_api_routes(app)  # 🆕 Phase 4b-2: Admin API Blueprint登録

    # 🆕 Phase 4b-3: ランディングページBlueprint登録
    try:
        from routes.landing_routes import landing_bp
        app.register_blueprint(landing_bp)
        print("✅ Phase 4b-3: Landing routes Blueprint registered successfully")
    except ImportError as e:
        print(f"❌ Phase 4b-3: Landing routes Blueprint import failed: {e}")

    # 🎯 TaskH2-2(B2-3) Stage 2 Phase 7: エンジン管理Blueprint登録
    try:
        engine_management_bp = create_engine_management_blueprint(
            app_logger=app_logger,
            log_access_event=log_access_event,
            require_rate_limit=require_rate_limit
        )
        app.register_blueprint(engine_management_bp)
        print("✅ Phase 7: Engine management Blueprint registered successfully")
    except ImportError as e:
        print(f"❌ Phase 7: Engine management Blueprint import failed: {e}")

    print("✅ Phase B-1: 管理者システム統合完了")
    ADMIN_SYSTEM_AVAILABLE = True

except ImportError as e:
    print(f"❌ Phase B-1: 管理者システムインポートエラー: {str(e)}")
    ADMIN_SYSTEM_AVAILABLE = False

    # フォールバック用ダミー関数
    def log_translation_event(*args, **kwargs): pass
    def log_gemini_analysis(*args, **kwargs): pass
    def log_api_call(*args, **kwargs): pass
    def log_error(*args, **kwargs): pass

except Exception as e:
    print(f"❌ Phase B-1: 管理者システム初期化エラー: {str(e)}")
    ADMIN_SYSTEM_AVAILABLE = False

    # フォールバック用ダミー関数
    def log_translation_event(*args, **kwargs): pass
    def log_gemini_analysis(*args, **kwargs): pass
    def log_api_call(*args, **kwargs): pass
    def log_error(*args, **kwargs): pass

# 🆕 認証システムの初期化（緊急デバッグ版）
auth_system = None

if AUTH_SYSTEM_AVAILABLE:
    try:
        auth_system = UserAuthSystem()

        result = init_auth_routes(app)

        # Blueprint登録後のルート確認
        for blueprint_name, blueprint in app.blueprints.items():
            print(f"  ✅ Blueprint登録済み: {blueprint_name} -> {blueprint}")

        # URL マップの確認
        for rule in app.url_map.iter_rules():
            print(f"  📋 {rule.methods} {rule.rule} -> {rule.endpoint}")

        # 特に/auth/profileルートを確認
        auth_routes = [rule for rule in app.url_map.iter_rules() if '/auth/' in rule.rule]
        for route in auth_routes:
            print(f"  🔐 {route.methods} {route.rule} -> {route.endpoint}")

        app_logger.info("認証システムが正常に初期化されました")

    except Exception as e:
        import traceback
        app_logger.error(f"認証システム初期化エラー: {str(e)}")
        auth_system = None
        AUTH_SYSTEM_AVAILABLE = False
else:
    pass

# 🆕 完全版セキュリティヘッダー設定（Flask-Talisman相当）

@app.after_request
def add_comprehensive_security_headers(response) -> Any:
    """包括的なセキュリティヘッダー設定"""

    # 基本セキュリティヘッダー
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # HTTPS強制（本番環境）
    if ENVIRONMENT == "production":
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

    # 🆕 包括的なCSP設定
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data:",
        "connect-src 'self' https://api.openai.com https://generativelanguage.googleapis.com",
        "media-src 'none'",
        "object-src 'none'",
        "frame-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "upgrade-insecure-requests"
    ]

    if ENVIRONMENT == "development":
        # 開発環境では'unsafe-eval'を追加（script-srcを置換して重複回避）
        for i, directive in enumerate(csp_directives):
            if directive.startswith("script-src"):
                csp_directives[i] = "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net"
                break

    response.headers['Content-Security-Policy'] = "; ".join(csp_directives)

    # 🆕 追加のセキュリティヘッダー
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'

    # サーバー情報の隠蔽
    response.headers.pop('Server', None)

    return response

# 🆕 強化されたCSRF対策


@app.context_processor
def inject_csrf_token():
    """全テンプレートにCSRFトークンを注入"""
    return dict(csrf_token=generate_csrf_token())


# 🆕 セッション管理強化


# ヘルパー関数とセキュリティ監視（リクエストコンテキスト対応版）



# 🆕 レート制限強化

rate_limit_store = {}

# 🆕 バックグラウンドメモリクリーンアップ機能

def periodic_cleanup():
    """定期的なメモリクリーンアップ"""
    while True:
        try:
            time.sleep(300)  # 5分ごと
            gc.collect()

            # 古いレート制限データを削除
            now = time.time()
            for ip in list(rate_limit_store.keys()):
                rate_limit_store[ip] = [
                    timestamp for timestamp in rate_limit_store[ip]
                    if now - timestamp < 600  # 10分以内のみ保持
                ]
                if not rate_limit_store[ip]:
                    del rate_limit_store[ip]

            # ログ出力（デバッグ時のみ）
            if ENVIRONMENT == "development":
                print(f"🧹 Memory cleanup completed - Rate limit store size: {len(rate_limit_store)}")

        except Exception as e:
            # クリーンアップ中のエラーは無視（ログのみ記録）
            if ENVIRONMENT == "development":
                print(f"⚠️ Cleanup error: {e}")

# バックグラウンドクリーンアップを開始
cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()



# 使用制限機能（既存コード + 強化）

DAILY_LIMIT_FREE = USAGE_LIMITS["free_daily_limit"]
USAGE_FILE = "usage_data.json"

def get_client_id() -> str:
    """🆕 ユーザーベースのクライアント識別子を取得（ユーザー管理システム対応）"""

    # 🆕 ログイン済みの場合はユーザー名ベースのIDを生成
    username = session.get("username")
    if username:
        salt = os.getenv("CLIENT_ID_SALT", "langpont_security_salt_2025")
        user_data = f"user_{username}_{salt}"
        client_id = hashlib.sha256(user_data.encode()).hexdigest()[:16]
        return f"user_{client_id}"

    # 🆕 未ログインの場合は従来のIPベースを使用（後方互換性）
    client_ip = get_client_ip_safe()
    user_agent = get_user_agent_safe()

    salt = os.getenv("CLIENT_ID_SALT", "langpont_security_salt_2025")
    client_data = f"{client_ip}_{user_agent}_{salt}"
    client_id = hashlib.sha256(client_data.encode()).hexdigest()[:16]

    return f"ip_{client_id}"

# 🆕 従来ユーザー設定復元ヘルパー関数
def restore_legacy_user_settings() -> None:
    """従来ユーザーの保存済み設定を復元"""
    try:
        # 🆕 一時的な言語切り替えが有効な場合はスキップ
        if session.get('temp_lang_override'):
            app_logger.info("一時的な言語切り替えが有効のため、設定復元をスキップ")
            return

        if session.get('logged_in') and not session.get('authenticated'):
            # 従来システムユーザーの場合のみ
            username = session.get('username')
            if username:
                settings_file = f"legacy_user_settings_{username}.json"
                if os.path.exists(settings_file):
                    import json
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        legacy_settings = json.load(f)
                        preferred_lang = legacy_settings.get('preferred_lang')

                        # セッションの言語設定と異なる場合は更新
                        current_lang = session.get('lang', 'jp')
                        if preferred_lang and preferred_lang != current_lang:
                            session['lang'] = preferred_lang
                            session['preferred_lang'] = preferred_lang
                            app_logger.info(f"従来ユーザー設定復元: {username} -> {preferred_lang}")
    except Exception as e:
        app_logger.warning(f"従来ユーザー設定復元エラー: {str(e)}")

# 🆕 翻訳履歴システム用ヘルパー関数
def get_current_user_id() -> Optional[int]:
    """現在ログイン中のユーザーIDを取得（翻訳履歴用）"""
    try:
        if AUTH_SYSTEM_AVAILABLE and session.get("authenticated"):
            return session.get("user_id")
        elif session.get("logged_in"):
            # 従来のシステムでのユーザーID
            username = session.get("username")
            if username:
                # ユーザー名をハッシュ化してIDとして使用
                user_hash = hashlib.sha256(username.encode()).hexdigest()[:8]
                return int(user_hash, 16) % 1000000  # 6桁のIDに変換
        return None
    except Exception as e:
        logger.error(f"ユーザーID取得エラー: {str(e)}")
        return None

def create_translation_history_entry(source_text: str, source_lang: str, target_lang: str,
                                   partner_message: str = "", context_info: str = "") -> Optional[str]:
    """翻訳履歴エントリを作成"""
    if not TRANSLATION_HISTORY_AVAILABLE:
        return None

    try:
        user_id = get_current_user_id()
        session_id = session.get("session_id") or session.get("csrf_token", "")[:16]

        request_data = TranslationRequest(
            user_id=user_id,
            session_id=session_id,
            source_text=source_text,
            source_language=source_lang,
            target_language=target_lang,
            partner_message=partner_message,
            context_info=context_info,
            ip_address=get_client_ip_safe(),
            user_agent=get_user_agent_safe(),
            request_timestamp=datetime.now().isoformat()
        )

        return translation_history_manager.create_translation_entry(request_data)
    except Exception as e:
        logger.error(f"翻訳履歴エントリ作成エラー: {str(e)}")
        return None

def save_translation_result(request_uuid: str, engine: str, translated_text: str, 
                          processing_time: float = 0.0, api_data: Dict[str, Any] = None):
    """翻訳結果を履歴に保存"""
    if not TRANSLATION_HISTORY_AVAILABLE or not request_uuid:
        return

    try:
        translation_history_manager.update_translation_result(
            request_uuid=request_uuid,
            engine=engine,
            translated_text=translated_text,
            processing_time=processing_time,
            api_call_data=api_data
        )
    except Exception as e:
        logger.error(f"翻訳結果保存エラー: {str(e)}")

def save_complete_translation_session(source_text: str, source_lang: str, target_lang: str,
                                     translations: Dict[str, str], context_data: Dict[str, Any] = None) -> Optional[str]:
    """
    完全な翻訳セッションを一括保存（Task 2.7.1 統合版）

    Args:
        source_text: 翻訳元テキスト
        source_lang: 翻訳元言語
        target_lang: 翻訳先言語  
        translations: 翻訳結果辞書 {'chatgpt': '...', 'gemini': '...', 'enhanced': '...'}
        context_data: コンテキストデータ

    Returns:
        保存された翻訳のUUID
    """
    if not TRANSLATION_HISTORY_AVAILABLE:
        return None

    try:
        user_id = get_current_user_id()
        session_id = session.get("session_id") or session.get("csrf_token", "")[:16]

        # コンテキストデータの構築
        if context_data is None:
            context_data = {}

        context_data.update({
            'partner_message': session.get('partner_message', ''),
            'context_info': session.get('context_info', ''),
            'ip_address': get_client_ip_safe(),
            'user_agent': get_user_agent_safe(),
            'processing_time': context_data.get('total_processing_time', 0.0)
        })

        # 翻訳セッションを保存
        uuid = translation_history_manager.save_complete_translation(
            user_id=user_id,
            session_id=session_id,
            source_text=source_text,
            source_language=source_lang,
            target_language=target_lang,
            translations=translations,
            context_data=context_data
        )

        if uuid:
            log_access_event(f'完全翻訳セッション保存完了: UUID={uuid}, エンジン数={len(translations)}')

        return uuid

    except Exception as e:
        logger.error(f"完全翻訳セッション保存エラー: {str(e)}")
        return None

def load_usage_data() -> Dict[str, Any]:
    """使用データをファイルから読み込み（エラーハンドリング強化）"""
    try:
        if os.path.exists(USAGE_FILE):
            with open(USAGE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                else:
                    log_security_event('DATA_CORRUPTION', 'Usage data file corrupted', 'ERROR')
                    return {}
        return {}
    except (json.JSONDecodeError, IOError) as e:
        log_security_event('FILE_ERROR', f'Error loading usage data: {str(e)}', 'ERROR')
        return {}

def save_usage_data(data: Dict[str, Any]) -> None:
    """使用データをファイルに保存（原子的書き込み）"""
    try:
        if not isinstance(data, dict):
            raise ValueError("Invalid data format")

        # 原子的書き込み
        temp_file = f"{USAGE_FILE}.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        os.replace(temp_file, USAGE_FILE)

    except Exception as e:
        log_security_event('FILE_ERROR', f'Error saving usage data: {str(e)}', 'ERROR')
        if os.path.exists(f"{USAGE_FILE}.tmp"):
            os.remove(f"{USAGE_FILE}.tmp")

def check_daily_usage(client_id: str) -> Tuple[bool, int, int]:
    """🆕 ユーザー別1日使用制限をチェック（ユーザー管理システム対応）"""
    today = datetime.now().strftime('%Y-%m-%d')
    usage_data = load_usage_data()

    # 🆕 ユーザー別制限の取得
    username = session.get("username", "unknown")
    user_role = session.get("user_role", "guest")

    # 🆕 config.pyから制限値を直接取得（セッション値より優先）
    from config import USERS
    if username in USERS:
        daily_limit = USERS[username].get("daily_limit", DAILY_LIMIT_FREE)
        log_access_event(f'Using config.py limit for {username}: {daily_limit}')
    else:
        daily_limit = session.get("daily_limit", DAILY_LIMIT_FREE)
        log_access_event(f'Using session limit for {username}: {daily_limit}')

    # 🆕 管理者の無制限チェック
    if daily_limit == -1:  # 無制限ユーザー
        log_access_event(f'Usage check: UNLIMITED for {username} ({user_role})')
        return True, 0, -1

    # 古いデータクリーンアップ（7日以上前）
    cutoff_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    cleaned_data = {}
    for key, value in usage_data.items():
        try:
            date_part = key.split('_')[-1]
            if date_part >= cutoff_date:
                cleaned_data[key] = value
        except (IndexError, ValueError):
            continue

    if cleaned_data != usage_data:
        save_usage_data(cleaned_data)
        usage_data = cleaned_data

    usage_key = f"{client_id}_{today}"
    current_usage = usage_data.get(usage_key, 0)

    # 🆕 詳細ログ記録
    log_access_event(f'Usage check: {current_usage}/{daily_limit} for {username} ({user_role})')

    return current_usage < daily_limit, current_usage, daily_limit

def increment_usage(client_id: str) -> int:
    """使用回数を増加（ログ強化 + セッション同期）"""
    today = datetime.now().strftime('%Y-%m-%d')
    usage_key = f"{client_id}_{today}"

    usage_data = load_usage_data()
    new_count = usage_data.get(usage_key, 0) + 1
    usage_data[usage_key] = new_count
    save_usage_data(usage_data)

    # 🆕 セッションにも使用回数を同期（プロフィール画面用）
    try:
        from flask import session
        session['usage_count'] = new_count
        session['last_usage_date'] = today
        log_access_event(f'Usage incremented to {new_count}, session updated')
    except (RuntimeError, ImportError):
        # セッションコンテキスト外での呼び出しの場合
        log_access_event(f'Usage incremented to {new_count} (no session context)')

    return new_count

def get_usage_status(client_id: str) -> Dict[str, Union[bool, int, str]]:
    """🆕 ユーザー別使用状況を取得（ユーザー管理システム対応）"""
    can_use, current_usage, daily_limit = check_daily_usage(client_id)

    # 🆕 ユーザー情報の取得
    username = session.get("username", "unknown")
    user_role = session.get("user_role", "guest")

    if daily_limit == -1:  # 無制限ユーザー
        return {
            "can_use": True,
            "current_usage": current_usage,
            "daily_limit": "無制限",
            "remaining": "無制限",
            "username": username,
            "user_role": user_role,
            "is_unlimited": True
        }

    remaining = max(0, daily_limit - current_usage)

    return {
        "can_use": can_use,
        "current_usage": current_usage,
        "daily_limit": daily_limit,
        "remaining": remaining,
        "username": username,
        "user_role": user_role,
        "is_unlimited": False
    }

# 🆕 Task #9 AP-1 Phase 1: TranslationService初期化（check_daily_usage定義後）
translation_service = TranslationService(
    openai_client=client,
    logger=app_logger,
    labels=labels,
    usage_checker=check_daily_usage,  # 関数参照を渡す
    translation_state_manager=translation_state_manager
)
app_logger.info("✅ Task #9 AP-1: TranslationService initialized successfully")


# 🆕 Task #9 AP-1 Phase 1: 翻訳Blueprint登録
try:
    history_functions = {
        'create_entry': create_translation_history_entry,
        'save_result': save_translation_result
    }
    translation_bp = init_translation_routes(
        translation_service, check_daily_usage, history_functions, app_logger, labels
    )
    app.register_blueprint(translation_bp)
    app_logger.info("✅ Task #9 AP-1: Translation Blueprint registered successfully")
except ImportError as e:
    app_logger.error(f"❌ Task #9 AP-1: Translation Blueprint registration failed: {e}")

# エラーハンドリング（強化版）

@app.errorhandler(400)
def bad_request_enhanced(error):
    """400エラーの詳細ハンドリング"""

    # リクエストの詳細をログに記録
    request_info = {
        'url': request.url,
        'method': request.method,
        'content_length': request.content_length,
        'user_agent': get_user_agent_safe()[:100]
    }

    log_security_event(
        'BAD_REQUEST_DETAILED',
        f'400 error details: {request_info}',
        'WARNING'
    )

    return jsonify({
        'success': False,
        'error': 'リクエストの形式が正しくありません。ページを再読み込みして再試行してください。',
        'error_code': 'BAD_REQUEST',
        'suggestion': 'ブラウザをリフレッシュしてください'
    }), 400

@app.errorhandler(403)
def forbidden(error):
    log_security_event('FORBIDDEN_ACCESS', f'403 error: {str(error)}', 'WARNING')
    return jsonify({
        'success': False,
        'error': 'アクセスが拒否されました',
        'error_code': 'FORBIDDEN'
    }), 403

@app.errorhandler(404)
def not_found(error):
    log_access_event('404 Not Found')
    return jsonify({
        'success': False,
        'error': 'ページが見つかりません',
        'error_code': 'NOT_FOUND'
    }), 404

@app.errorhandler(413)
def request_entity_too_large(error):
    log_security_event('LARGE_REQUEST', 'Request size exceeded limit', 'WARNING')
    return jsonify({
        'success': False,
        'error': 'リクエストサイズが大きすぎます',
        'error_code': 'REQUEST_TOO_LARGE'
    }), 413

@app.errorhandler(429)
def too_many_requests_enhanced(error):
    """レート制限エラーの改善ハンドリング"""

    client_ip = get_client_ip_safe()

    # レート制限情報をログに記録
    current_requests = len(rate_limit_store.get(client_ip, []))

    log_security_event(
        'RATE_LIMIT_HIT',
        f'Rate limit exceeded for IP {client_ip}: {current_requests} requests',
        'WARNING'
    )

    return jsonify({
        'success': False,
        'error': 'アクセス頻度が高すぎます。30秒待ってから再試行してください。',
        'error_code': 'RATE_LIMIT_EXCEEDED',
        'suggestion': '言語変更は通常の操作に影響しません。しばらく待ってからお試しください。',
        'retry_after': 30
    }), 429

@app.errorhandler(500)
def internal_server_error(error):
    app_logger.error(f"Internal Server Error: {error}")
    log_security_event('INTERNAL_ERROR', f'500 error: {str(error)}', 'ERROR')
    return jsonify({
        'success': False,
        'error': 'サーバー内部エラーが発生しました',
        'error_code': 'INTERNAL_SERVER_ERROR'
    }), 500

@app.errorhandler(502)
def bad_gateway(error):
    log_security_event('BAD_GATEWAY', f'502 error: {str(error)}', 'ERROR')
    return jsonify({
        'success': False,
        'error': 'サーバー接続エラーが発生しました。翻訳サービスに一時的な問題がある可能性があります。',
        'error_code': 'BAD_GATEWAY',
        'suggestion': '文章を短くして再度お試しください。問題が続く場合は、しばらく時間を置いてから再度お試しください。'
    }), 502

@app.errorhandler(504)
def gateway_timeout(error):
    log_security_event('GATEWAY_TIMEOUT', f'504 error: {str(error)}', 'ERROR')
    return jsonify({
        'success': False,
        'error': '翻訳処理がタイムアウトしました。入力テキストが長すぎる可能性があります。',
        'error_code': 'GATEWAY_TIMEOUT',
        'suggestion': '文章を短く分割して翻訳するか、複雑な表現を簡素化してお試しください。'
    }), 504

# セキュリティ監視とアクセス制御

@app.before_request
def enhanced_security_monitoring() -> None:
    """強化されたリクエスト前セキュリティ監視"""

    # セッション期限切れチェック
    if SecureSessionManager.is_session_expired():
        session.clear()
        log_security_event('SESSION_EXPIRED', 'Session expired and cleared', 'INFO')

    # 疑わしいUser-Agentチェック
    user_agent = get_user_agent_safe()
    suspicious_agents = [
        'bot', 'crawler', 'spider', 'scraper', 'scanner',
        'nikto', 'sqlmap', 'nmap', 'burp', 'curl', 'wget'
    ]

    if any(agent in user_agent.lower() for agent in suspicious_agents):
        log_security_event(
            'SUSPICIOUS_USER_AGENT',
            f'Suspicious UA detected: {user_agent[:100]}',
            'WARNING'
        )

    # 🆕 疑わしいリクエストパターンのチェック
    suspicious_paths = [
        'admin', 'wp-admin', 'phpmyadmin', 'backup', 'config',
        '.env', '.git', 'database', 'sql', 'shell'
    ]

    try:
        current_path = request.path.lower()
        if any(path in current_path for path in suspicious_paths):
            log_security_event(
                'SUSPICIOUS_PATH_ACCESS',
                f'Suspicious path accessed: {request.path}',
                'WARNING'
            )
    except RuntimeError:
        pass

    # 🆕 リクエストヘッダーの異常チェック
    try:
        if request.content_length and request.content_length > app.config.get('MAX_CONTENT_LENGTH', 16*1024*1024):
            log_security_event(
                'LARGE_REQUEST_DETECTED',
                f'Large request detected: {request.content_length} bytes',
                'WARNING'
            )
    except RuntimeError:
        pass

    # アクセスログ記録
    try:
        log_access_event(f'{request.method} {request.path}')
    except RuntimeError:
        pass

# 翻訳関数群（セキュリティ強化版）

def safe_openai_request(prompt: str, max_tokens: int = 400, temperature: float = 0.1, current_lang: str = "jp") -> str:
    """OpenAI APIの安全なリクエスト実行（翻訳用に最適化・多言語対応）"""
    from labels import labels

    try:
        # プロンプト長の計算
        prompt_length = len(prompt)

        # 動的タイムアウト設定（文章長に応じて60-120秒）
        if prompt_length >= 3000:
            timeout = 120
        elif prompt_length >= 1500:
            timeout = 90
        else:
            timeout = 60

        # より適切なmax_tokens設定
        if prompt_length > 4000:
            max_tokens = 1500  # 大幅増加
            timeout = 180  # 3分に延長
        elif prompt_length > 2000:
            max_tokens = 1000
            timeout = 120
        elif prompt_length > 1000:
            max_tokens = 600
        else:
            max_tokens = 400

        # 8000文字を超える場合の自動プロンプト短縮
        if prompt_length > 8000:
            # 前4000文字 + "...[省略]..." + 後4000文字
            shortened_prompt = prompt[:4000] + "\n\n...[Content shortened for processing]...\n\n" + prompt[-4000:]
            prompt = shortened_prompt
            log_security_event('PROMPT_SHORTENED', f'Prompt shortened from {prompt_length} to {len(prompt)} chars', 'INFO')

        if not prompt or len(prompt.strip()) < 5:
            raise ValueError(labels[current_lang]['validation_error_short'])

        # 🚀 Phase B-1: API呼び出し開始
        api_start_time = time.time()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
        api_duration = int((time.time() - api_start_time) * 1000)

        # 🚀 Phase B-1: API呼び出しログ記録
        log_api_call("openai", True, api_duration, "gpt-3.5-turbo translation")

        result = response.choices[0].message.content.strip()

        # 🆕 適切な短い翻訳警告ロジック（翻訳専用）
        # プロンプトから実際の翻訳対象テキストを推定
        lines = prompt.split('\n')
        actual_text = ""
        for line in lines:
            # 「翻訳対象」「TRANSLATE」「翻訳してください」などの後の行を翻訳対象と判定
            if any(keyword in line for keyword in ['翻訳対象', 'TRANSLATE', '翻訳してください', 'translation to', 'Translate to']):
                # この行以降を翻訳対象テキストとして抽出
                remaining_lines = lines[lines.index(line)+1:]
                actual_text = '\n'.join(remaining_lines).strip()
                break

        # 翻訳対象テキストが見つからない場合は、最後の長い行を翻訳対象と推定
        if not actual_text:
            for line in reversed(lines):
                if len(line.strip()) > 10:  # 10文字以上の行
                    actual_text = line.strip()
                    break

        # 🆕 改善された警告条件
        if actual_text and len(actual_text) >= 100 and len(result) < 10:
            log_security_event(
                'SHORT_TRANSLATION_WARNING',
                f'Translation may be incomplete: source={len(actual_text)} chars, result={len(result)} chars',
                'WARNING'
            )
            # 短い翻訳の場合は適切な警告メッセージ（多言語対応）
            warning_messages = {
                "jp": "\n\n⚠️ 翻訳が不完全な可能性があります。",
                "en": "\n\n⚠️ Translation may be incomplete.",
                "fr": "\n\n⚠️ La traduction peut être incomplète.",
                "es": "\n\n⚠️ La traducción puede estar incompleta."
            }
            result += warning_messages.get(current_lang, warning_messages["jp"])
        # 30文字未満の短い文は警告スキップ
        elif actual_text and len(actual_text) < 30:
            log_access_event(f'Short text translation completed: source={len(actual_text)}, result={len(result)}')
        # 元の文章が30-100文字の場合は通常の翻訳として扱う

        if not result or len(result.strip()) < 2:
            raise ValueError(labels[current_lang]['validation_error_short'])

        return result

    except requests.exceptions.Timeout:
        log_security_event('OPENAI_TIMEOUT', f'OpenAI API timeout after {timeout}s for prompt length {prompt_length}', 'WARNING')
        raise ValueError(f"{labels[current_lang]['api_error_timeout']}（{timeout}秒）")
    except Exception as e:
        log_security_event('OPENAI_ERROR', f'OpenAI API error: {str(e)}', 'ERROR')
        raise ValueError(labels[current_lang]['api_error_general'])

# セッション管理強化関数

def safe_session_store(key, value, max_size=1200):  # 🆕 Cookieサイズ対策：3000→1200に削減
    """セッションに安全にデータを保存"""
    if isinstance(value, str) and len(value) > max_size:
        # 長すぎる場合は要約版を保存
        truncated_value = value[:max_size//2] + "\n...[省略]...\n" + value[-max_size//2:]
        session[key] = truncated_value
        log_security_event(
            'SESSION_DATA_TRUNCATED',
            f'Session data truncated for {key}: {len(value)} -> {len(truncated_value)}',
            'INFO'
        )
    else:
        session[key] = value

def cleanup_old_session_data():
    """古いセッションデータをクリーンアップ"""
    keys_to_clean = [
        "old_translated_text", "old_reverse_translated_text",
        "old_gemini_translation", "old_better_translation"
    ]
    for key in keys_to_clean:
        session.pop(key, None)

def get_translation_state(field_name: str, default_value: Any = None) -> Any:
    """
    🆕 SL-3 Phase 1: 翻訳状態を取得（Redisキャッシュ → セッションフォールバック）
    
    Args:
        field_name: フィールド名
        default_value: デフォルト値
        
    Returns:
        Any: 取得した値
    """
    try:
        # 🔍 Debug: セッションオブジェクトの情報をログ出力
        session_id = getattr(session, 'session_id', None)
        # app_logger.debug(f"🔍 SL-3 Debug: session type={type(session)}, session_id={session_id}, field={field_name}")
        
        # TranslationStateManagerからの取得を試行
        if translation_state_manager and session_id:
            cached_value = translation_state_manager.get_translation_state(
                session_id, 
                field_name, 
                None
            )
            if cached_value is not None:
                return cached_value
        
        # フォールバック: セッションから取得
        return session.get(field_name, default_value)
        
    except Exception as e:
        app_logger.error(f"❌ SL-3 Phase 1: Failed to get translation state {field_name}: {e}")
        return session.get(field_name, default_value)

def f_translate_to_lightweight(input_text: str, source_lang: str, target_lang: str, partner_message: str = "", context_info: str = "", current_lang: str = "jp") -> str:
    """セキュリティ強化版メイン翻訳関数"""

    # 🆕 包括的な入力値検証（10000文字まで許可）
    validations = [
        (input_text, 10000, "翻訳テキスト"),
        (partner_message, 2000, "会話履歴"),
        (context_info, 2000, "背景情報")
    ]

    for text, max_len, field_name in validations:
        if text:  # 空でない場合のみ検証
            is_valid, error_msg = EnhancedInputValidator.validate_text_input(
                text, max_length=max_len, field_name=field_name, current_lang=current_lang
            )
            if not is_valid:
                raise ValueError(error_msg)

    # 言語ペア検証（多言語対応）
    is_valid_pair, pair_error = EnhancedInputValidator.validate_language_pair(f"{source_lang}-{target_lang}", current_lang)
    if not is_valid_pair:
        raise ValueError(pair_error)

    lang_map = {"ja": "Japanese", "fr": "French", "en": "English", "es": "Spanish", "de": "German", "it": "Italian"}
    target_label = lang_map.get(target_lang, target_lang.capitalize())

    if partner_message.strip() or context_info.strip():
        context_sections = []

        if partner_message.strip():
            context_sections.append(f"PREVIOUS CONVERSATION:\n{partner_message.strip()}")

        if context_info.strip():
            context_sections.append(f"BACKGROUND & RELATIONSHIP:\n{context_info.strip()}")

        context_text = "\n\n".join(context_sections)

        prompt = f"""You are a professional translator specializing in culturally appropriate {target_label} translation.

IMPORTANT CONTEXT TO CONSIDER:
{context_text}

TRANSLATION INSTRUCTIONS:
- Consider the relationship and background information carefully
- Use appropriate formality level based on the context
- Ensure cultural sensitivity and business appropriateness
- Translate naturally while respecting the contextual nuances

TRANSLATE TO {target_label.upper()}:
{input_text}

Remember: The context above is crucial for determining the appropriate tone, formality, and cultural considerations."""

    else:
        prompt = f"Professional, culturally appropriate translation to {target_label}:\n\n{input_text}"

    return safe_openai_request(prompt, current_lang=current_lang)

def f_reverse_translation(translated_text: str, target_lang: str, source_lang: str, current_lang: str = "jp") -> str:
    """セキュリティ強化版逆翻訳関数"""

    if not translated_text:
        return "(翻訳テキストが空です)"

    # 入力値検証（多言語対応）
    is_valid, error_msg = EnhancedInputValidator.validate_text_input(
        translated_text, field_name="逆翻訳テキスト", current_lang=current_lang
    )
    if not is_valid:
        raise ValueError(error_msg)

    is_valid_pair, pair_error = EnhancedInputValidator.validate_language_pair(f"{source_lang}-{target_lang}", current_lang)
    if not is_valid_pair:
        raise ValueError(pair_error)

    lang_map = {"ja": "Japanese", "fr": "French", "en": "English", "es": "Spanish", "de": "German", "it": "Italian"}
    source_label = lang_map.get(source_lang, source_lang.capitalize())

    prompt = f"""Professional translation task: Translate the following text to {source_label}.

TEXT TO TRANSLATE TO {source_label.upper()}:
{translated_text}

IMPORTANT: Respond ONLY with the {source_label} translation."""

    try:
        return safe_openai_request(prompt, max_tokens=300, current_lang=current_lang)
    except Exception as e:
        return f"逆翻訳エラー: {str(e)}"

def debug_gemini_reverse_translation(gemini_translation: str, target_lang: str, source_lang: str) -> Dict[str, Any]:
    """
    🔧 Phase A: Gemini逆翻訳デバッグ関数

    Args:
        gemini_translation: Gemini翻訳結果
        target_lang: 翻訳先言語
        source_lang: 翻訳元言語

    Returns:
        デバッグ情報辞書
    """
    debug_info = {
        "function": "debug_gemini_reverse_translation",
        "timestamp": datetime.now().isoformat(),
        "inputs": {
            "gemini_translation": gemini_translation[:100] + "..." if len(gemini_translation) > 100 else gemini_translation,
            "gemini_translation_length": len(gemini_translation),
            "target_lang": target_lang,
            "source_lang": source_lang
        },
        "validation_results": {},
        "api_call_info": {},
        "result": {}
    }

    try:
        # 1. 入力値検証テスト
        is_valid, error_msg = EnhancedInputValidator.validate_text_input(
            gemini_translation, field_name="Gemini翻訳テキスト"
        )
        debug_info["validation_results"]["text_validation"] = {
            "is_valid": is_valid,
            "error_message": error_msg
        }

        is_valid_pair, pair_error = EnhancedInputValidator.validate_language_pair(f"{source_lang}-{target_lang}")
        debug_info["validation_results"]["language_pair_validation"] = {
            "is_valid": is_valid_pair,
            "error_message": pair_error
        }

        # 2. 逆翻訳実行テスト
        if is_valid and is_valid_pair:
            start_time = time.time()
            reverse_result = f_reverse_translation(gemini_translation, target_lang, source_lang)
            processing_time = time.time() - start_time

            debug_info["api_call_info"] = {
                "processing_time_seconds": round(processing_time, 3),
                "prompt_language_direction": f"{target_lang} → {source_lang}",
                "api_provider": "OpenAI (ChatGPT)"
            }

            debug_info["result"] = {
                "reverse_translation": reverse_result[:200] + "..." if len(reverse_result) > 200 else reverse_result,
                "reverse_translation_length": len(reverse_result),
                "is_error": reverse_result.startswith("逆翻訳エラー"),
                "is_empty": len(reverse_result.strip()) == 0,
                "matches_original": reverse_result.strip() == gemini_translation.strip()
            }

            # 3. 問題検出
            problems = []
            if debug_info["result"]["is_error"]:
                problems.append("API呼び出しエラー")
            if debug_info["result"]["is_empty"]:
                problems.append("逆翻訳結果が空")
            if debug_info["result"]["matches_original"]:
                problems.append("逆翻訳結果が元翻訳と同一")
            if processing_time > 10:
                problems.append("API応答が遅い（10秒超過）")

            debug_info["problems_detected"] = problems

        else:
            debug_info["result"] = {
                "skipped": True,
                "reason": "入力値検証エラー"
            }

    except Exception as e:
        debug_info["result"] = {
            "exception": str(e),
            "exception_type": type(e).__name__
        }

    # ログ記録
    app_logger.info(f"🔧 Phase A Debug: Gemini逆翻訳デバッグ実行 - 問題: {debug_info.get('problems_detected', [])}")

    return debug_info

def f_better_translation(text_to_improve: str, source_lang: str = "fr", target_lang: str = "en", current_lang: str = "jp") -> str:
    """セキュリティ強化版改善翻訳関数"""

    # 入力値検証（多言語対応）
    is_valid, error_msg = EnhancedInputValidator.validate_text_input(
        text_to_improve, field_name="改善対象テキスト", current_lang=current_lang
    )
    if not is_valid:
        raise ValueError(error_msg)

    is_valid_pair, pair_error = EnhancedInputValidator.validate_language_pair(f"{source_lang}-{target_lang}", current_lang)
    if not is_valid_pair:
        raise ValueError(pair_error)

    lang_map = {"ja": "日本語", "fr": "フランス語", "en": "英語", "es": "スペイン語", "de": "ドイツ語", "it": "イタリア語"}
    target_label = lang_map.get(target_lang, target_lang)

    prompt = f"この{target_label}をもっと自然な{target_label}の文章に改善してください：{text_to_improve}"

    return safe_openai_request(prompt, current_lang=current_lang)

# f_translate_with_gemini() 関数は services/translation_service.py に移行されました
# Task #9 AP-1 Phase 2: Gemini翻訳Blueprint分離

# 🆕 Gemini分析関数（セキュリティ強化版）

def f_gemini_3way_analysis(translated_text: str, better_translation: str, gemini_translation: str) -> tuple:
    """3つの翻訳結果を分析する関数（セッション安全版）"""

    # 🆕 セッションから表示言語を早期取得（エラーメッセージも多言語化）
    display_lang = session.get("lang", "jp")
    analysis_lang_map = {
        "jp": "Japanese",
        "en": "English", 
        "fr": "French",
        "es": "Spanish"
    }
    analysis_language = analysis_lang_map.get(display_lang, "Japanese")

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY or len(GEMINI_API_KEY) < 10:
        if analysis_language == "English":
            return "⚠️ Gemini API key is not properly configured", ""
        elif analysis_language == "French":
            return "⚠️ La clé API Gemini n'est pas correctement configurée", ""
        elif analysis_language == "Spanish":
            return "⚠️ La clave API de Gemini no está configurada correctamente", ""
        else:
            return "⚠️ Gemini APIキーが正しく設定されていません", ""

    # 🆕 入力パラメータの検証（セッションより優先）
    if not all([translated_text, better_translation, gemini_translation]):
        if analysis_language == "English":
            return "⚠️ Translation data required for analysis is missing", ""
        elif analysis_language == "French":
            return "⚠️ Les données de traduction nécessaires à l'analyse sont manquantes", ""
        elif analysis_language == "Spanish":
            return "⚠️ Faltan los datos de traducción necesarios para el análisis", ""
        else:
            return "⚠️ 分析に必要な翻訳データが不足しています", ""

    # 🆕 現在の言語設定を直接取得（SL-3 Phase 1: キャッシュ対応）
    current_language_pair = request.form.get('language_pair') or get_translation_state("language_pair", "ja-en")

    try:
        source_lang, target_lang = current_language_pair.split("-")
        log_access_event(f'Gemini analysis - Current language pair: {current_language_pair}')
    except:
        source_lang = "ja"
        target_lang = "en"
        log_security_event('GEMINI_LANGUAGE_FALLBACK', 'Using fallback language pair ja-en', 'WARNING')

    # 🆕 現在の入力データのみ使用（セッションの古いデータを無視）
    current_input_text = request.form.get('japanese_text') or session.get("input_text", "")
    current_partner_message = request.form.get('partner_message') or ""
    current_context_info = request.form.get('context_info') or ""

    # 言語マップ
    lang_map = {
        "ja": "Japanese", "fr": "French", "en": "English",
        "es": "Spanish", "de": "German", "it": "Italian"
    }

    source_label = lang_map.get(source_lang, source_lang.capitalize())
    target_label = lang_map.get(target_lang, target_lang.capitalize())

    # 🆕 分析プロンプトの明確化
    if current_context_info.strip():
        context_section = f"""
CURRENT TRANSLATION CONTEXT:
- Language pair: {source_label} → {target_label}
- Previous conversation: {current_partner_message or "None"}
- Situation: {current_context_info.strip()}"""
    else:
        context_section = f"""
CURRENT TRANSLATION CONTEXT:
- Language pair: {source_label} → {target_label}
- Type: General conversation"""

    # 🆕 言語別の指示を強化
    if analysis_language == "English":
        lang_instruction = "IMPORTANT: Respond ENTIRELY in English. Do not use any Japanese or other languages."
        focus_points = f"""- Which {target_label} translation is most natural
- Appropriateness for the given context  
- Recommendation for this {source_label} to {target_label} translation task"""
    elif analysis_language == "French":
        lang_instruction = "IMPORTANT: Répondez ENTIÈREMENT en français. N'utilisez pas de japonais ou d'autres langues."
        focus_points = f"""- Quelle traduction {target_label} est la plus naturelle
- Adéquation au contexte donné
- Recommandation pour cette tâche de traduction {source_label} vers {target_label}"""
    elif analysis_language == "Spanish":
        lang_instruction = "IMPORTANT: Responda COMPLETAMENTE en español. No use japonés u otros idiomas."
        focus_points = f"""- Qué traducción al {target_label} es más natural
- Adecuación al contexto dado
- Recomendación para esta tarea de traducción de {source_label} a {target_label}"""
    else:
        # 🌍 現在のUIセッション言語を取得して適用
        current_ui_lang = session.get('lang', 'jp')
        lang_instructions = {
            'jp': "IMPORTANT: 日本語で回答してください。他の言語は使用しないでください。",
            'en': "IMPORTANT: Please respond in English. Do not use any other languages.",
            'fr': "IMPORTANT: Veuillez répondre en français. N'utilisez aucune autre langue.",
            'es': "IMPORTANT: Por favor responda en español. No use ningún otro idioma."
        }
        lang_instruction = lang_instructions.get(current_ui_lang, lang_instructions['jp'])

        # 🌍 フォーカスポイントも多言語対応
        focus_points_map = {
            'jp': f"""- どの{target_label}翻訳が最も自然か
- 与えられた文脈への適切性
- この{source_label}から{target_label}への翻訳タスクへの推奨""",
            'en': f"""- Which {target_label} translation is most natural
- Appropriateness to the given context
- Recommendation for this {source_label} to {target_label} translation task""",
            'fr': f"""- Quelle traduction {target_label} est la plus naturelle
- Adéquation au contexte donné
- Recommandation pour cette tâche de traduction {source_label} vers {target_label}""",
            'es': f"""- Qué traducción al {target_label} es más natural
- Adecuación al contexto dado
- Recomendación para esta tarea de traducción de {source_label} a {target_label}"""
        }
        focus_points = focus_points_map.get(current_ui_lang, focus_points_map['jp'])

    # 🆕 明確なプロンプト（言語を明示）
    prompt = f"""{lang_instruction}

Analyze these {target_label} translations of the given {source_label} text.

ORIGINAL TEXT ({source_label}): {current_input_text[:1000]}

{context_section}

TRANSLATIONS TO COMPARE:
1. ChatGPT Translation: {translated_text}
2. Enhanced Translation: {better_translation}  
3. Gemini Translation: {gemini_translation}

IMPORTANT: All translations above are in {target_label}. Analyze them as {target_label} text.

Provide analysis in {analysis_language} focusing on:
{focus_points}

Your entire response must be in {analysis_language}."""

    # 🆕 文字数チェック（セッション汚染回避）
    total_length = len(translated_text) + len(better_translation) + len(gemini_translation)
    warning = ""
    if total_length > 8000:
        warning = f"⚠️ テキストが長いため分析が制限される可能性があります（{total_length}文字）\n\n"

    # リクエスト実行
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{
                "text": prompt[:8000]  # プロンプトを8000文字に制限
            }]
        }],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1000
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=45)
        if response.status_code == 200:
            result_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            log_access_event('Gemini 3-way analysis completed successfully')
            return warning + result_text.strip(), prompt
        else:
            error_msg = f"⚠️ Gemini API error: {response.status_code}"
            log_security_event('GEMINI_API_ERROR', error_msg, 'ERROR')
            return error_msg, prompt

    except requests.exceptions.Timeout:
        # 🆕 多言語対応のタイムアウトメッセージ
        if analysis_language == "English":
            return f"⚠️ Gemini analysis timed out (45 seconds).\n\n" \
                   f"The text may be too long (total {total_length} characters).\n" \
                   f"Please try shortening the translation text and try again.", prompt
        elif analysis_language == "French":
            return f"⚠️ L'analyse Gemini a expiré (45 secondes).\n\n" \
                   f"Le texte est peut-être trop long (total {total_length} caractères).\n" \
                   f"Veuillez raccourcir le texte de traduction et réessayer.", prompt
        elif analysis_language == "Spanish":
            return f"⚠️ El análisis de Gemini agotó el tiempo de espera (45 segundos).\n\n" \
                   f"El texto puede ser demasiado largo (total {total_length} caracteres).\n" \
                   f"Por favor acorte el texto de traducción e intente de nuevo.", prompt
        else:
            return f"⚠️ Gemini分析がタイムアウトしました（45秒）。\n\n" \
                   f"テキストが長すぎる可能性があります（合計{total_length}文字）。\n" \
                   f"翻訳テキストを短縮してから再度お試しください。", prompt

    except Exception as e:
        import traceback
        # Gemini APIの詳細エラーログ
        if hasattr(e, 'response'):
            error_detail = f"Status: {e.response.status_code}, Body: {e.response.text[:500]}"
        else:
            error_detail = str(e)

        log_security_event('GEMINI_DETAILED_ERROR', error_detail, 'ERROR')
        app_logger.error(traceback.format_exc())

        # 🆕 多言語対応のエラーメッセージ
        if analysis_language == "English":
            return f"⚠️ Gemini analysis error (details logged): {str(e)[:100]}", prompt
        elif analysis_language == "French":
            return f"⚠️ Erreur d'analyse Gemini (détails enregistrés): {str(e)[:100]}", prompt
        elif analysis_language == "Spanish":
            return f"⚠️ Error de análisis de Gemini (detalles registrados): {str(e)[:100]}", prompt
        else:
            return f"⚠️ Gemini分析エラー（詳細ログに記録済み）: {str(e)[:100]}", prompt

# 🚀 Task 2.9.2 Phase B-3.5.2: 推奨判定システム（新規作成）


# 🚀 Task 2.9.2 Phase B-3.5.2: 分析エンジン管理クラス


# インタラクティブ質問処理システム（セキュリティ強化版）


# グローバルインスタンス
# グローバルインスタンス
from translation.expert_ai import LangPontTranslationExpertAI
interactive_processor = LangPontTranslationExpertAI(client)

# ルーティング（完全セキュリティ強化版）

@app.route("/login", methods=["GET", "POST"])
@csrf_protect
@require_rate_limit
def login():
    # 🚨 緊急デバッグ機能
    if request.args.get('debug') == 'emergency':
        from admin_auth import admin_auth_manager
        import json

        try:
            session_data = dict(session)
            user_info = admin_auth_manager.get_current_user_info()

            admin_routes = []
            for rule in app.url_map.iter_rules():
                if 'admin' in rule.endpoint:
                    admin_routes.append(f"{rule.endpoint}: {rule.rule}")

            debug_data = {
                "logged_in": session.get('logged_in', False),
                "user_role": session.get('user_role', 'none'),
                "username": session.get('username', 'none'),
                "has_admin_access": admin_auth_manager.has_admin_access(),
                "admin_routes_count": len(admin_routes),
                "admin_routes": admin_routes,
                "session_keys": list(session_data.keys()),
                "request_path": request.path,
                "request_method": request.method
            }

            html = f"""
            <!DOCTYPE html>
            <html><head><title>Emergency Debug</title></head>
            <body>
            <h1>🚨 Emergency Debug Information</h1>
            {f'<div style="background:green;color:white;padding:10px;margin:10px 0;">✅ Just logged in successfully!</div>' if request.args.get('just_logged_in') else ''}
            <pre>{json.dumps(debug_data, indent=2, ensure_ascii=False)}</pre>

            <h2>Quick Actions</h2>
            <p><a href="/login">Normal Login</a></p>
            <p><a href="/admin/dashboard">Admin Dashboard Test</a></p>
            <p><a href="/">Main Page</a></p>

            <h2>Test Steps</h2>
            <ol>
            <li>If not logged in: Use normal login with admin/admin_langpont_2025</li>
            <li>After login: Visit <a href="/admin/dashboard">Admin Dashboard</a></li>
            <li>If still fails: Check admin_routes above</li>
            </ol>
            </body></html>
            """
            return html

        except Exception as e:
            return f"<h1>Debug Error</h1><pre>{str(e)}</pre><p><a href='/login'>Back to Login</a></p>"

    # 🔄 通常のログイン処理に続行
    # 多言語ラベル辞書を追加（jp, en, fr, esの4言語対応）
    multilang_labels = {
        "jp": {
            "title": "LangPont ログイン",
            "password_label": "パスワード",
            "password_placeholder": "パスワードを入力してください",
            "login_button": "ログイン",
            "error_empty_password": "パスワードを入力してください",
            "error_invalid_format": "無効なパスワード形式です",
            "error_wrong_password": "パスワードが違います",
            "tagline": "心が通う翻訳を、今すぐ体験",
            "description": "LangPontは、言葉の向こうにある気持ちを大切にする翻訳サービスです。"
        },
        "en": {
            "title": "LangPont Login",
            "password_label": "Password",
            "password_placeholder": "Enter your password",
            "login_button": "Login",
            "error_empty_password": "Please enter your password",
            "error_invalid_format": "Invalid password format",
            "error_wrong_password": "Incorrect password",
            "tagline": "Experience Context-Aware Translation",
            "description": "LangPont delivers translations that capture meaning, context, and cultural nuance."
        },
        "fr": {
            "title": "Connexion LangPont",
            "password_label": "Mot de passe",
            "password_placeholder": "Entrez votre mot de passe",
            "login_button": "Se connecter",
            "error_empty_password": "Veuillez saisir votre mot de passe",
            "error_invalid_format": "Format de mot de passe invalide",
            "error_wrong_password": "Mot de passe incorrect",
            "tagline": "Découvrez la traduction contextuelle",
            "description": "LangPont propose des traductions qui capturent le sens, le contexte et les nuances culturelles."
        },
        "es": {
            "title": "Iniciar Sesión LangPont",
            "password_label": "Contraseña",
            "password_placeholder": "Ingrese su contraseña",
            "login_button": "Iniciar Sesión",
            "error_empty_password": "Por favor ingrese su contraseña",
            "error_invalid_format": "Formato de contraseña inválido",
            "error_wrong_password": "Contraseña incorrecta",
            "tagline": "Experimente la traducción contextual",
            "description": "LangPont ofrece traducciones que capturan significado, contexto y matices culturales."
        }
    }

    # current_labelsの動的取得
    lang = session.get("lang", "jp")
    if lang not in multilang_labels:
        lang = "jp"
    current_labels = multilang_labels[lang]

    error = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not password:
            error = current_labels["error_empty_password"]
        else:
            # 🆕 入力値の基本検証
            is_valid_pw, pw_error = EnhancedInputValidator.validate_text_input(
                password, max_length=100, min_length=1, field_name="パスワード"
            )
            if not is_valid_pw:
                log_security_event('INVALID_PASSWORD_INPUT', pw_error, 'WARNING')
                error = current_labels["error_invalid_format"]
            else:
                # 🆕 ユーザー認証システム
                from config import USERS, LEGACY_SETTINGS

                authenticated_user = None

                # 🆕 後方互換性：空のユーザー名で既存パスワードの場合
                if not username and password == LEGACY_SETTINGS["legacy_password"]:
                    authenticated_user = {
                        "username": LEGACY_SETTINGS["default_guest_username"],
                        "role": "guest",
                        "daily_limit": 10,
                        "auth_method": "legacy"
                    }
                    log_access_event('Legacy authentication used - migrating to guest account')

                # 🆕 新しいユーザー認証システム
                elif username in USERS:
                    user_data = USERS[username]
                    if password == user_data["password"]:
                        authenticated_user = {
                            "username": username,
                            "role": user_data["role"],
                            "daily_limit": user_data["daily_limit"],
                            "auth_method": "standard"
                        }
                    else:
                        pass

                # 🆕 空のユーザー名でguestパスワードの場合  
                elif not username and password in [user_data["password"] for user_data in USERS.values()]:
                    # パスワードからユーザーを特定
                    for user, data in USERS.items():
                        if password == data["password"] and user == "guest":
                            authenticated_user = {
                                "username": user,
                                "role": data["role"],
                                "daily_limit": data["daily_limit"],
                                "auth_method": "guest_direct"
                            }
                            break

                if authenticated_user:
                    # 🆕 セッション情報の保存
                    session["logged_in"] = True
                    session["username"] = authenticated_user["username"]
                    session["user_role"] = authenticated_user["role"]
                    session["daily_limit"] = authenticated_user["daily_limit"]
                    session.permanent = True

                    # 🆕 SL-2.1: セッションIDの生成・取得
                    if not session.get('session_id'):
                        session['session_id'] = secrets.token_hex(16)
                    
                    # 🆕 SL-2.1: Redis同期（失敗してもログイン処理は継続）
                    if session_redis_manager:
                        try:
                            session_redis_manager.sync_auth_to_redis(
                                session_id=session['session_id'],
                                auth_data={
                                    'logged_in': True,
                                    'username': authenticated_user["username"],
                                    'user_role': authenticated_user["role"],
                                    'daily_limit': authenticated_user["daily_limit"],
                                    'auth_method': authenticated_user["auth_method"]
                                }
                            )
                            app_logger.info(f"✅ SL-2.1: Auth data synced to Redis for user: {authenticated_user['username']}")
                        except Exception as e:
                            app_logger.warning(f"⚠️ SL-2.1: Redis sync failed: {e} - continuing with filesystem session")

                    # 🆕 セッションIDの再生成（セッションハイジャック対策）
                    # 🚨 TEMPORARILY DISABLED FOR DEBUG: SecureSessionManager.regenerate_session_id()
                    if USE_REDIS_SESSION and hasattr(app.session_interface, 'regenerate_session_id'):
                        try:
                            # 現在のセッションIDを保存（ログ用）
                            old_session_id = session.get('_session_id', 'unknown')
                            
                            # セッションID再生成
                            new_session_id = app.session_interface.regenerate_session_id(session)
                            
                            # ログ出力
                            app_logger.info(f"✅ SL-2.2: Session regenerated for user: {authenticated_user['username']}")
                            app_logger.info(f"✅ SL-2.2: Old session: {old_session_id[:16]}... → New session: {new_session_id[:16]}...")
                        except Exception as e:
                            app_logger.error(f"❌ SL-2.2: Session regeneration failed: {e}")

                    # 🆕 詳細ログ記録
                    log_security_event(
                        'LOGIN_SUCCESS', 
                        f'User: {authenticated_user["username"]}, Role: {authenticated_user["role"]}, Method: {authenticated_user["auth_method"]}', 
                        'INFO'
                    )
                    log_access_event(f'User logged in: {authenticated_user["username"]} ({authenticated_user["role"]})')

                    # 🆕 ログイン成功後の適切なリダイレクト
                    # 全てのユーザーをメインアプリ（翻訳画面）へリダイレクト
                    return redirect(url_for("index"))
                else:
                    # 🆕 詳細な失敗ログ
                    log_security_event(
                        'LOGIN_FAILED',
                        f'Username: "{username}", Password length: {len(password)}, IP: {get_client_ip_safe()}',
                        'WARNING'
                    )
                    error = current_labels["error_wrong_password"]

    return render_template("login.html", error=error, labels=current_labels, current_lang=lang)

# 🆕 プロフィールアクセス用リダイレクトルート
@app.route("/profile")
def profile_redirect():
    """メイン画面からのプロフィールアクセス用リダイレクト"""
    # 認証システムが利用可能かチェック
    if AUTH_SYSTEM_AVAILABLE:
        return redirect(url_for('auth.profile'))
    else:
        # 従来の認証システムの場合、適切なページにリダイレクト
        if not session.get("logged_in"):
            return redirect(url_for('login'))
        # プロフィール機能が未実装の場合は翻訳画面に戻る
        return redirect(url_for('index'))

@app.route("/debug-info", methods=["GET"])
def debug_info():
    """緊急デバッグ情報表示"""
    from admin_auth import admin_auth_manager
    import json

    try:
        session_data = dict(session)
        user_info = admin_auth_manager.get_current_user_info()

        # 管理者ルート確認
        admin_routes = []
        for rule in app.url_map.iter_rules():
            if 'admin' in rule.endpoint:
                admin_routes.append(f"{rule.endpoint}: {rule.rule}")

        debug_data = {
            "logged_in": session.get('logged_in', False),
            "user_role": session.get('user_role', 'none'),
            "username": session.get('username', 'none'),
            "has_admin_access": admin_auth_manager.has_admin_access(),
            "admin_routes_count": len(admin_routes),
            "admin_routes": admin_routes[:10],  # 最初の10個のみ
            "session_keys": list(session_data.keys())
        }

        return f"<h1>緊急デバッグ情報</h1><pre>{json.dumps(debug_data, indent=2, ensure_ascii=False)}</pre><p><a href='/login'>ログイン</a> | <a href='/admin/dashboard'>管理者ダッシュボード</a></p>"

    except Exception as e:
        return f"<h1>デバッグエラー</h1><pre>{str(e)}</pre>"

@app.route("/", methods=["GET", "POST"])
@csrf_protect
@require_rate_limit
def index():
    # 🆕 従来ユーザーの保存済み設定を復元
    restore_legacy_user_settings()

    lang = session.get("lang", "jp")
    if lang not in ['jp', 'en', 'fr', 'es']:
        lang = "jp"

    label = labels.get(lang, labels["jp"])

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    current_mode = session.get("translation_mode", "normal")
    mode_message = session.get("mode_message", "")

    language_pair = request.form.get("language_pair", "ja-fr") if request.method == "POST" else "ja-fr"

    # 🆕 言語ペア検証
    is_valid_pair, _ = EnhancedInputValidator.validate_language_pair(language_pair)
    if not is_valid_pair:
        log_security_event('INVALID_LANGUAGE_PAIR', f'Invalid pair: {language_pair}', 'WARNING')
        language_pair = "ja-fr"

    source_lang, target_lang = language_pair.split("-")

    japanese_text = ""
    translated_text = reverse_translated_text = ""
    better_translation = reverse_better_text = nuances_analysis = ""
    gemini_translation = gemini_3way_analysis = gemini_reverse_translation = ""
    nuance_question = nuance_answer = partner_message = context_info = ""

    # 🆕 データ永続化異常の完全解決：強制的な初期化処理
    if request.method == "GET":
        # 🆕 GET リクエスト（ページ初期ロード）時は完全なクリーンスレート

        # 古いチャット履歴を強制削除
        session.pop("chat_history", None)

        # Phase 3c-3: 破損した翻訳コンテキスト削除処理を除去
        # 削除済み: TranslationContext関連の処理はStateManagerに統合完了

        # 確実に空の履歴を設定
        chat_history = []

        log_access_event("Page loaded with clean slate - all old data cleared")
    else:
        # POST リクエスト時のみ既存データを保持（Phase 3c-3: translation_context参照削除）
        has_translation_data = session.get("translated_text")
        if has_translation_data:
            chat_history = session.get("chat_history", [])
        else:
            chat_history = []

    # 使用状況を取得
    client_id = get_client_id()
    usage_status = get_usage_status(client_id)

    if request.method == "POST":
        if request.form.get("reset") == "true":
            # 🆕 完全なセッションクリア
            translation_keys_to_clear = [
                # 翻訳結果
                "translated_text", "reverse_translated_text",
                "better_translation", "reverse_better_translation", 
                "gemini_translation", "gemini_reverse_translation",
                "gemini_3way_analysis",

                # 言語情報
                "source_lang", "target_lang", "language_pair",

                # 入力データ
                "input_text", "partner_message", "context_info",

                # 分析データ
                "nuance_question", "nuance_answer",

                # Phase 3c-3: "translation_context" 削除済み
                # 注意: "chat_history" はリセット時も保持（ユーザビリティ向上）
            ]

            for key in translation_keys_to_clear:
                session.pop(key, None)

            # TranslationContextの明示的クリア（StateManagerに統合 - Phase 3c-1b）
            session_id = getattr(session, 'session_id', None) or session.get("session_id") or session.get("csrf_token", "")[:16]
            if translation_state_manager and session_id:
                translation_state_manager.clear_context_data(session_id)

            log_access_event('Complete form reset executed - all translation data cleared')

            # 初期化
            japanese_text = ""
            partner_message = ""
            context_info = ""
            nuance_question = ""
        else:
            # 🆕 強化された入力値検証
            japanese_text = request.form.get("japanese_text", "").strip()
            partner_message = request.form.get("partner_message", "").strip()
            context_info = request.form.get("context_info", "").strip()
            nuance_question = request.form.get("nuance_question", "").strip()

            # 各フィールドの検証（翻訳テキストは10000文字まで許可）
            for field_name, field_value, max_len in [
                ("翻訳テキスト", japanese_text, 10000),
                ("会話履歴", partner_message, 2000),
                ("背景情報", context_info, 2000),
                ("質問", nuance_question, 1000)
            ]:
                if field_value:
                    is_valid, error_msg = EnhancedInputValidator.validate_text_input(
                        field_value, max_length=max_len, field_name=field_name
                    )
                    if not is_valid:
                        log_security_event(
                            'FORM_INPUT_VALIDATION_FAILED',
                            f'{field_name} validation failed: {error_msg}',
                            'WARNING'
                        )
                        # エラーの場合はフィールドをクリア
                        if field_name == "翻訳テキスト":
                            japanese_text = ""
                        elif field_name == "会話履歴":
                            partner_message = ""
                        elif field_name == "背景情報":
                            context_info = ""
                        elif field_name == "質問":
                            nuance_question = ""

    return render_template("index.html",
        japanese_text=japanese_text,
        translated_text=translated_text,
        reverse_translated_text=reverse_translated_text,
        better_translation=better_translation,
        reverse_better_text=reverse_better_text,
        gemini_translation=gemini_translation,
        gemini_reverse_translation=gemini_reverse_translation,
        gemini_3way_analysis=gemini_3way_analysis,
        nuance_question=nuance_question,
        nuance_answer=nuance_answer,
        chat_history=chat_history,
        partner_message=partner_message,
        context_info=context_info,
        current_mode=current_mode,
        mode_message=mode_message,
        usage_status=usage_status,
        labels=label,
        source_lang=source_lang,
        target_lang=target_lang,
        version_info=VERSION_INFO
    )

@app.route("/logout")
def logout():
    username = session.get("username", "unknown")
    
    # 🆕 SL-2.1: Redis同期（失敗してもログアウト処理は継続）
    if session_redis_manager and getattr(session, 'session_id', None):
        try:
            session_redis_manager.clear_auth_from_redis(
                session_id=session.session_id
            )
            app_logger.info(f"✅ SL-2.1: Auth data cleared from Redis for user: {username}")
        except Exception as e:
            app_logger.warning(f"⚠️ SL-2.1: Redis clear failed: {e}")
    
    log_access_event('User logged out')
    log_security_event('LOGOUT', 'User session terminated', 'INFO')
    session.clear()
    return redirect(url_for("login"))

@app.route("/set_language/<lang>")
def set_language(lang):
    try:
        # 🆕 言語パラメータの厳密な検証
        valid_languages = ["jp", "en", "fr", "es"]
        if lang not in valid_languages:
            log_security_event('INVALID_LANGUAGE', f'Invalid language: {lang}', 'WARNING')
            lang = "jp"

        # セッション保護機能：重要データの一時保存
        preserved_data = {}
        keys_to_preserve = ['logged_in', 'usage_data', 'csrf_token', 'session_created']  # Phase 3c-3: 'translation_context' 削除

        # 重要データを一時保存
        for key in keys_to_preserve:
            if key in session:
                preserved_data[key] = session[key]

        # 言語設定
        session["lang"] = lang
        # 🆕 一時的な言語切り替えフラグを設定（設定復元を無効化）
        session["temp_lang_override"] = True

        # 保存データを復元
        for key, value in preserved_data.items():
            session[key] = value

        # レート制限をリセット（言語変更は除外）
        client_ip = get_client_ip_safe()
        if client_ip in rate_limit_store:
            # 言語変更リクエストを除外
            rate_limit_store[client_ip] = [
                timestamp for timestamp in rate_limit_store[client_ip]
                if time.time() - timestamp > 5  # 5秒以内のリクエストを削除
            ]

        log_access_event(f'Language changed to {lang} with session protection')
        return redirect(url_for("index"))

    except Exception as e:
        # エラーログの追加
        log_security_event('LANGUAGE_CHANGE_ERROR', f'Error during language change: {str(e)}', 'ERROR')
        app_logger.error(f"Language change error: {str(e)}")

        # エラー時はデフォルトで日本語に設定
        session["lang"] = "jp"
        return redirect(url_for("index"))

@app.route("/reset_language")
def reset_language():
    """一時的な言語設定をリセットして、保存済み設定に戻す"""
    try:
        # 🆕 一時的な言語切り替えフラグを削除
        if 'temp_lang_override' in session:
            del session['temp_lang_override']

        # 従来ユーザーの保存済み設定を復元
        restore_legacy_user_settings()

        current_lang = session.get("lang", "jp")
        log_access_event(f'Language reset to user preference: {current_lang}')
        return redirect(url_for("index"))

    except Exception as e:
        log_security_event('LANGUAGE_RESET_ERROR', f'Error during language reset: {str(e)}', 'ERROR')
        app_logger.error(f"Language reset error: {str(e)}")
        session["lang"] = "jp"
        return redirect(url_for("index"))

# 🆕 Task #9 AP-1 Phase 1: 以下の関数はroutes/translation.pyに移行済み
# @app.route("/translate_chatgpt", methods=["POST"])
# @csrf_protect  # 🆕 Task #8 SL-4: API保護強化
# @require_rate_limit
# def translate_chatgpt_only():
    # 🚨 Task #9 AP-1 Phase 1: この関数は routes/translation.py に移行済み
    # 🚨 新しいエンドポイント: /translate_chatgpt (Blueprint経由)
    try:
        # 🔧 Phase 4b-3修正: 言語とlabels import を最初に実行
        current_lang = session.get('lang', 'jp')
        try:
            from labels import labels
        except ImportError:
            labels = {
                "jp": {
                    "usage_limit_message": "本日の利用制限に達しました。制限: {limit}回",
                    "usage_reset_time": "明日の00:00にリセット", 
                    "usage_upgrade_message": "より多くの翻訳が必要な場合はお問い合わせください",
                    "validation_error_empty": "が入力されていません"
                }
            }

        # 使用制限チェック
        client_id = get_client_id()
        can_use, current_usage, daily_limit = check_daily_usage(client_id)

        if not can_use:
            log_security_event(
                'USAGE_LIMIT_EXCEEDED',
                f'Client exceeded daily limit: {current_usage}/{daily_limit}',
                'INFO'
            )
            return jsonify({
                "success": False,
                "error": "usage_limit_exceeded",
                "message": labels[current_lang]['usage_limit_message'].format(limit=daily_limit),
                "current_usage": current_usage,
                "daily_limit": daily_limit,
                "reset_time": labels[current_lang]['usage_reset_time'],
                "upgrade_message": labels[current_lang]['usage_upgrade_message']
            })

        # リクエストデータ取得
        data = request.get_json() or {}
        input_text = data.get("japanese_text", "").strip()
        partner_message = data.get("partner_message", "")
        context_info = data.get("context_info", "")
        language_pair = data.get("language_pair", "ja-fr")  

        # 🆕 包括的な入力値検証（10000文字まで許可・多言語対応）
        validations = [
            (input_text, 10000, "翻訳テキスト"),
            (partner_message, 2000, "会話履歴"),
            (context_info, 2000, "背景情報")
        ]

        for text, max_len, field_name in validations:
            if text:  # 空でない場合のみ検証
                is_valid, error_msg = EnhancedInputValidator.validate_text_input(
                    text, max_length=max_len, field_name=field_name, current_lang=current_lang
                )
                if not is_valid:
                    log_security_event(
                        'TRANSLATION_INPUT_VALIDATION_FAILED',
                        f'{field_name} validation failed: {error_msg}',
                        'WARNING'
                    )
                    return jsonify({
                        "success": False,
                        "error": error_msg
                    })

        # 言語ペア検証（多言語対応）
        is_valid_pair, pair_error = EnhancedInputValidator.validate_language_pair(language_pair, current_lang)
        if not is_valid_pair:
            log_security_event('INVALID_TRANSLATION_LANGUAGE_PAIR', f'Pair: {language_pair}', 'WARNING')
            return jsonify({
                "success": False,
                "error": pair_error
            })

        source_lang, target_lang = language_pair.split("-")

        # セッションクリア
        critical_keys = ["translated_text", "reverse_translated_text"]
        for key in critical_keys:
            session.pop(key, None)

        # 🆕 SL-3 Phase 1: 翻訳状態をセッションに保存（キャッシュは翻訳後に実行）
        session["source_lang"] = source_lang
        session["target_lang"] = target_lang
        session["language_pair"] = language_pair
        session["input_text"] = input_text
        session["partner_message"] = partner_message
        session["context_info"] = context_info
        
        app_logger.info("📝 SL-3 Phase 1: Translation states saved to session (cache will be attempted after translation)")

        log_access_event(f'Translation started: {language_pair}, length={len(input_text)}')

        # 🚀 Phase B-3.5: 開発者監視 - 翻訳開始
        log_user_activity("translation_started", {
            "language_pair": language_pair,
            "input_length": len(input_text),
            "has_context": bool(context_info),
            "has_partner_message": bool(partner_message)
        })
        update_translation_progress("translation_init", "in_progress", 0, {
            "language_pair": language_pair,
            "input_char_count": len(input_text),
            "input_word_count": len(input_text.split())
        })

        if not input_text:
            return jsonify({
                "success": False,
                "error": f"翻訳テキスト{labels[current_lang]['validation_error_empty']}"
            })

        # 🆕 翻訳履歴エントリを作成
        translation_uuid = create_translation_history_entry(
            source_text=input_text,
            source_lang=source_lang,
            target_lang=target_lang,
            partner_message=partner_message,
            context_info=context_info
        )

        # 翻訳実行（多言語対応）
        # 🚀 Phase B-3.5: ChatGPT翻訳開始監視
        update_translation_progress("chatgpt_translation", "in_progress", 0, {"step": 1, "provider": "OpenAI"})

        start_time = time.time()
        translated = f_translate_to_lightweight(input_text, source_lang, target_lang, partner_message, context_info, current_lang)
        chatgpt_time = time.time() - start_time

        # 🚀 Phase B-3.5: ChatGPT翻訳完了監視
        update_translation_progress("chatgpt_translation", "completed", int(chatgpt_time * 1000), {
            "step": 1,
            "provider": "OpenAI",
            "output_length": len(translated),
            "success": True
        })

        # 🚀 Phase B-1: 管理者ログ記録（翻訳イベント）
        username = session.get("username", "anonymous")
        log_translation_event(username, language_pair, True, int(chatgpt_time * 1000))

        # 🚀 Phase B-2: Task 2.9.2 翻訳データ収集
        try:
            from admin_dashboard import advanced_analytics

            # セッションIDの取得
            session_id = session.get("session_id") or session.get("csrf_token", "")[:16] or f"trans_{int(time.time())}"

            # API監視データ収集
            advanced_analytics.log_api_call(
                api_provider="openai",
                endpoint="/v1/chat/completions", 
                method="POST",
                status_code=200,
                response_time_ms=int(chatgpt_time * 1000),
                success=True,
                request_size=len(input_text.encode('utf-8')),
                response_size=len(translated.encode('utf-8')),
                metadata={
                    'language_pair': language_pair,
                    'translation_type': 'chatgpt',
                    'endpoint_name': 'translate_chatgpt'
                }
            )

            app_logger.info(f"🚀 Phase B-2: Translation API monitoring data collected for session {session_id}")

        except Exception as analytics_error:
            app_logger.warning(f"🚀 Phase B-2: Analytics collection failed: {str(analytics_error)}")

        # 🆕 ChatGPT翻訳結果を履歴に保存
        save_translation_result(
            translation_uuid, "chatgpt", translated, chatgpt_time,
            {"endpoint": "openai_chat_completions", "tokens_used": len(translated.split())}
        )

        # 簡単な整合性チェック
        if translated.strip() == input_text.strip():
            translated = f"[翻訳処理でエラーが発生しました] {translated}"

        # 逆翻訳実行（多言語対応）
        # 🚀 Phase B-3.5: 逆翻訳開始監視
        update_translation_progress("reverse_translation", "in_progress", 0, {"step": 2, "provider": "OpenAI"})

        start_time = time.time()
        reverse = f_reverse_translation(translated, target_lang, source_lang, current_lang)
        reverse_time = time.time() - start_time

        # 🚀 Phase B-3.5: 逆翻訳完了監視
        update_translation_progress("reverse_translation", "completed", int(reverse_time * 1000), {
            "step": 2,
            "provider": "OpenAI",
            "output_length": len(reverse),
            "success": True
        })

        # 🆕 逆翻訳結果を履歴に保存
        save_translation_result(
            translation_uuid, "reverse", reverse, reverse_time,
            {"endpoint": "reverse_translation", "source_translation": translated}
        )

        # Gemini翻訳を取得
        # 🚀 Phase B-3.5: Gemini翻訳開始監視
        update_translation_progress("gemini_translation", "in_progress", 0, {"step": 3, "provider": "Gemini"})

        try:
            start_time = time.time()
            gemini_translation = f_translate_with_gemini(input_text, source_lang, target_lang, partner_message, context_info)
            gemini_time = time.time() - start_time

            # 🚀 Phase B-3.5: Gemini翻訳完了監視
            update_translation_progress("gemini_translation", "completed", int(gemini_time * 1000), {
                "step": 3,
                "provider": "Gemini",
                "output_length": len(gemini_translation),
                "success": True
            })

            # 🚀 Phase B-2: Gemini API監視データ収集
            try:
                from admin_dashboard import advanced_analytics
                advanced_analytics.log_api_call(
                    api_provider="gemini",
                    endpoint="/v1beta/models/gemini-1.5-pro:generateContent",
                    method="POST", 
                    status_code=200,
                    response_time_ms=int(gemini_time * 1000),
                    success=True,
                    request_size=len(input_text.encode('utf-8')),
                    response_size=len(gemini_translation.encode('utf-8')),
                    metadata={
                        'language_pair': language_pair,
                        'translation_type': 'gemini',
                        'model': 'gemini-1.5-pro-latest'
                    }
                )
            except Exception as gemini_analytics_error:
                app_logger.warning(f"🚀 Phase B-2: Gemini analytics collection failed: {str(gemini_analytics_error)}")

            # 🆕 Gemini翻訳結果を履歴に保存
            save_translation_result(
                translation_uuid, "gemini", gemini_translation, gemini_time,
                {"endpoint": "gemini_api", "model": "gemini-1.5-pro-latest"}
            )
        except Exception as gemini_error:
            gemini_translation = f"Gemini翻訳エラー: {str(gemini_error)}"

            # 🚀 Phase B-3.5: Gemini翻訳エラー監視
            update_translation_progress("gemini_translation", "failed", 0, {
                "step": 3,
                "provider": "Gemini",
                "error": str(gemini_error),
                "success": False
            })

            # 🚀 Phase B-2: Gemini API エラー監視
            try:
                from admin_dashboard import advanced_analytics
                advanced_analytics.log_api_call(
                    api_provider="gemini",
                    endpoint="/v1beta/models/gemini-1.5-pro:generateContent",
                    method="POST",
                    status_code=500,
                    response_time_ms=0,
                    success=False,
                    error_type="api_error",
                    error_message=str(gemini_error),
                    metadata={'language_pair': language_pair}
                )
            except Exception as gemini_error_analytics:
                app_logger.warning(f"🚀 Phase B-2: Gemini error analytics failed: {str(gemini_error_analytics)}")

            save_translation_result(
                translation_uuid, "gemini", gemini_translation, 0.0,
                {"endpoint": "gemini_api", "error": str(gemini_error)}
            )

        # 🆕 Phase A修正: Gemini逆翻訳実装（デバッグ機能付き）
        gemini_reverse_translation = ""
        try:
            if gemini_translation and not gemini_translation.startswith("⚠️") and not gemini_translation.startswith("Gemini翻訳エラー"):
                # 🔧 Phase A: デバッグ機能実行
                debug_result = debug_gemini_reverse_translation(gemini_translation, target_lang, source_lang)
                app_logger.info(f"🔧 Phase A Debug Result: {debug_result.get('problems_detected', [])}")

                start_time = time.time()
                gemini_reverse_translation = f_reverse_translation(gemini_translation, target_lang, source_lang, current_lang)
                gemini_reverse_time = time.time() - start_time

                # 🔧 Phase A: 詳細ログ追加
                app_logger.info(f"🔧 Phase A: Gemini逆翻訳完了")
                app_logger.info(f"  - 元翻訳: {len(gemini_translation)}文字")
                app_logger.info(f"  - 逆翻訳: {len(gemini_reverse_translation)}文字")
                app_logger.info(f"  - 処理時間: {gemini_reverse_time:.3f}秒")
                app_logger.info(f"  - 言語方向: {target_lang} → {source_lang}")
                app_logger.info(f"  - 逆翻訳結果（先頭50文字）: {gemini_reverse_translation[:50]}...")

                # Gemini逆翻訳結果を履歴に保存
                save_translation_result(
                    translation_uuid, "gemini_reverse", gemini_reverse_translation, gemini_reverse_time,
                    {"endpoint": "gemini_reverse_translation", "base_translation": gemini_translation}
                )
            else:
                app_logger.warning(f"🔧 Phase A: Gemini逆翻訳スキップ - 元翻訳が無効: {gemini_translation[:50]}...")

        except Exception as gemini_reverse_error:
            gemini_reverse_translation = f"Gemini逆翻訳エラー: {str(gemini_reverse_error)}"
            app_logger.error(f"🔧 Phase A: Gemini逆翻訳エラー: {str(gemini_reverse_error)}")
            save_translation_result(
                translation_uuid, "gemini_reverse", gemini_reverse_translation, 0.0,
                {"endpoint": "gemini_reverse_translation", "error": str(gemini_reverse_error)}
            )

        # 改善翻訳を取得（多言語対応）
        better_translation = ""
        reverse_better = ""
        try:
            start_time = time.time()
            better_translation = f_better_translation(translated, source_lang, target_lang, current_lang)
            enhanced_time = time.time() - start_time

            # 🆕 改善翻訳結果を履歴に保存
            save_translation_result(
                translation_uuid, "enhanced", better_translation, enhanced_time,
                {"endpoint": "enhanced_translation", "base_translation": translated}
            )

            if better_translation and not better_translation.startswith("改善翻訳エラー"):
                reverse_better = f_reverse_translation(better_translation, target_lang, source_lang, current_lang)

        except Exception as better_error:
            better_translation = f"改善翻訳エラー: {str(better_error)}"
            reverse_better = ""
            save_translation_result(
                translation_uuid, "enhanced", better_translation, 0.0,
                {"endpoint": "enhanced_translation", "error": str(better_error)}
            )

        # 使用回数を増加（翻訳成功時のみ）
        new_usage_count = increment_usage(client_id)
        remaining = daily_limit - new_usage_count

        # 翻訳開始時に古いセッションデータをクリーンアップ
        cleanup_old_session_data()

        # 🆕 SL-3 Phase 1: 翻訳状態をセッションに保存（キャッシュは後で実行）
        session["source_lang"] = source_lang
        session["target_lang"] = target_lang
        session["language_pair"] = language_pair
        session["input_text"] = input_text
        session["partner_message"] = partner_message
        session["context_info"] = context_info
        
        # セッション保存（安全な保存関数を使用）
        safe_session_store("translated_text", translated)
        safe_session_store("reverse_translated_text", reverse)
        safe_session_store("gemini_translation", gemini_translation)
        safe_session_store("gemini_reverse_translation", gemini_reverse_translation)
        safe_session_store("better_translation", better_translation)
        safe_session_store("reverse_better_translation", reverse_better)
        
        # 🆕 SL-3 Phase 2: Redis保存（大容量データ）
        # session.session_idプロパティから取得、またはフォールバック
        session_id = getattr(session, 'session_id', None) or session.get("session_id") or session.get("csrf_token", "")[:16] or f"trans_{int(time.time())}"
        app_logger.info(f"🔍 Debug: session_id={session_id}, session_keys={list(session.keys())[:5]}, has_session_id_attr={hasattr(session, 'session_id')}")
        if translation_state_manager and session_id:
            redis_data = {
                "translated_text": translated,
                "reverse_translated_text": reverse,
                "gemini_translation": gemini_translation,
                "gemini_reverse_translation": gemini_reverse_translation,
                "better_translation": better_translation,
                "reverse_better_translation": reverse_better
            }
            app_logger.info("🚀 Attempting Redis save...")
            translation_state_manager.save_multiple_large_data(session_id, redis_data)
        else:
            app_logger.warning(f"⚠️ Redis save skipped: session_id={session_id}, manager={translation_state_manager is not None}")

        # 🆕 軽量化：翻訳コンテキストは最小限のメタデータのみ保存（StateManagerに統合 - Phase 3c-1b）
        if translation_state_manager and session_id:
            import time
            from datetime import datetime
            # 既存データを取得し、メタデータのみ更新
            context_data = translation_state_manager.get_context_data(session_id)
            if context_data:
                # 既存データのメタデータを更新
                context_data["metadata"]["source_lang"] = source_lang
                context_data["metadata"]["target_lang"] = target_lang
            else:
                # 新規作成（最小限のメタデータのみ）
                context_data = {
                    "context_id": f"gemini_{int(time.time())}",
                    "timestamp": time.time(),
                    "created_at": datetime.now().isoformat(),
                    "input_text": "",  # 空文字（個別キーから参照）
                    "translations": {},  # 空辞書（個別キーから参照）
                    "analysis": "",
                    "metadata": {
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                        "partner_message": "",  # 空文字（個別キーから参照）
                        "context_info": ""      # 空文字（個別キーから参照）
                    }
                }
            translation_state_manager.save_context_data(session_id, context_data)

        log_access_event(f'Translation completed successfully, usage: {new_usage_count}/{daily_limit}')

        return jsonify({
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,  
            "input_text": input_text,
            "translated_text": translated,
            "reverse_translated_text": reverse,
            "gemini_translation": gemini_translation,
            "gemini_reverse_translation": gemini_reverse_translation,  # 🆕 Phase A修正
            "better_translation": better_translation,
            "reverse_better_translation": reverse_better,
            "usage_info": {
                "current_usage": new_usage_count,
                "daily_limit": daily_limit,
                "remaining": remaining,
                "can_use": remaining > 0
            }
        })

    except Exception as e:
        import traceback
        app_logger.error(f"Translation error: {str(e)}")
        app_logger.error(traceback.format_exc())
        log_security_event('TRANSLATION_ERROR', f'Error: {str(e)}', 'ERROR')

        # 🚀 Phase B-1: 管理者ログ記録（エラーイベント）
        username = session.get("username", "anonymous")
        log_error("translation_error", str(e), username, f"Exception in translate_chatgpt_only: {traceback.format_exc()[:200]}")

        return jsonify({
            "success": False,
            "error": str(e)
        })

# 🆕 Phase 1: Gemini分析保存機能実装
def save_gemini_analysis_to_db(session_id: str, analysis_result: str, recommendation: str, 
                              confidence: float, strength: str, reasons: str):
    """Gemini分析結果をデータベースに保存（デバッグ強化版）"""
    try:
        app_logger.info(f"🔍 保存開始: session_id={session_id}")
        app_logger.info(f"🔍 分析結果長: {len(analysis_result)} 文字")
        app_logger.info(f"🔍 推奨: {recommendation}, 信頼度: {confidence}, 強度: {strength}")

        import sqlite3
        conn = sqlite3.connect('langpont_translation_history.db')
        cursor = conn.cursor()

        # まず対象レコードが存在するか確認
        cursor.execute("""
            SELECT id, source_text, created_at 
            FROM translation_history 
            WHERE session_id = ?
            ORDER BY created_at DESC
        """, (session_id,))

        records = cursor.fetchall()
        app_logger.info(f"🔍 session_id={session_id} のレコード数: {len(records)}")

        if not records:
            app_logger.error(f"❌ session_id {session_id} のレコードが見つかりません")
            # デバッグ用: 最新10件のsession_idを表示
            cursor.execute("""
                SELECT session_id, created_at 
                FROM translation_history 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            recent_sessions = cursor.fetchall()
            app_logger.info("🔍 最新のセッションID一覧:")
            for sess_id, created_at in recent_sessions:
                app_logger.info(f"  - {sess_id} ({created_at})")

            conn.close()
            return False

        # 最新のレコードを選択
        record_id = records[0][0]
        source_text = records[0][1][:50] if records[0][1] else "N/A"
        created_at = records[0][2]
        app_logger.info(f"✅ 対象レコード発見: ID={record_id}, 翻訳元={source_text}..., 作成={created_at}")

        # 統合データを作成
        from datetime import datetime
        combined_analysis = f"""=== Gemini 分析結果 ===
{analysis_result}

=== 推奨翻訳 ===
推奨: {recommendation}
信頼度: {confidence}
強度: {strength}
理由: {reasons}
分析日時: {datetime.now().isoformat()}
"""

        # 更新実行（既存のgemini_analysisカラムを使用）
        cursor.execute("""
            UPDATE translation_history 
            SET gemini_analysis = ?
            WHERE id = ?
        """, (combined_analysis, record_id))

        updated_rows = cursor.rowcount
        app_logger.info(f"✅ 更新完了: {updated_rows} 行更新")

        conn.commit()
        conn.close()

        return updated_rows > 0

    except Exception as e:
        app_logger.error(f"Failed to save Gemini analysis: {str(e)}")
        app_logger.error(f"❌ 分析保存失敗 (gemini): session_id={session_id}")
        try:
            conn.close()
        except:
            pass
        return False

# =============================================================================
# 🎯 TaskH2-2(B2-3) Stage 2 Phase 7: set_analysis_engine() 責務分離
# =============================================================================
# 📅 分離日: 2025年7月20日
# 📁 分離先: routes/engine_management.py
# 📊 分離行数: 35行 (Lines 2497-2531)
#
# 🎯 分離理由: サーバー層の純粋な状態管理として独立化
# ✅ 分離された責務: 
#    - エンジン状態管理のみ
#    - セッション更新のみ
#    - バリデーションのみ
# ❌ 除外された責務:
#    - UI操作なし
#    - DOM操作なし
#
# 🆕 Task #9-3 AP-1 Phase 3: /get_nuance エンドポイントはBlueprint化されました
# 🔗 新しい場所: routes/analysis.py
# 🔗 エンドポイント: /get_nuance (同一URL維持)

@app.route("/track_translation_copy", methods=["POST"])
@require_rate_limit  
def track_translation_copy():
    """🚀 Phase B-2: Task 2.9.2 個人化データ収集 - 翻訳コピー追跡"""
    try:
        data = request.get_json() or {}
        translation_type = data.get("translation_type", "unknown")  # chatgpt, enhanced, gemini
        copy_method = data.get("copy_method", "button_click")  # button_click, keyboard_shortcut, context_menu
        text_length = data.get("text_length", 0)

        # Task 2.9.2 個人化データ収集
        try:
            from admin_dashboard import advanced_analytics

            user_id = session.get("username", "anonymous")
            language_pair = get_translation_state("language_pair", "unknown")

            # Gemini推奨との比較分析
            gemini_recommendation = session.get("gemini_recommendation", None)
            event_type = "translation_selection"
            rejection_reason = ""

            if gemini_recommendation and gemini_recommendation != translation_type:
                event_type = "rejection"
                rejection_reason = f"chose_{translation_type}_over_{gemini_recommendation}"

            # 個人化イベントログ記録
            advanced_analytics.log_personalization_event(
                user_id=user_id,
                event_type=event_type,
                gemini_recommendation=gemini_recommendation,
                user_choice=translation_type,
                language_pair=language_pair,
                context_type="copy_action",  # Phase 3c-3: translation_context → context_type
                style_attributes={
                    'copy_method': copy_method,
                    'text_length_category': 'short' if text_length < 100 else 'medium' if text_length < 500 else 'long'
                },
                confidence_score=0.0,  # Copy action は確実な選択
                rejection_reason=rejection_reason,
                metadata={
                    'copy_timestamp': time.time(),
                    'session_active_time': time.time() - session.get('session_start', time.time()),
                    'text_length': text_length
                }
            )

            app_logger.info(f"🚀 Phase B-2: Personalization data collected - {user_id} chose {translation_type} (method: {copy_method})")

        except Exception as personalization_error:
            app_logger.warning(f"🚀 Phase B-2: Personalization data collection failed: {str(personalization_error)}")

        return jsonify({"success": True, "message": "Copy event tracked"})

    except Exception as e:
        app_logger.error(f"Translation copy tracking error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# 🆕 Task #9-3 AP-1 Phase 3b: /interactive_question エンドポイントはBlueprint化されました
# 🔗 新しい場所: routes/analysis.py
# 🔗 エンドポイント: /interactive_question (同一URL維持)

# 🆕 Task #9-3 AP-1 Phase 3b: /clear_chat_history エンドポイントはBlueprint化されました
# 🔗 新しい場所: routes/analysis.py
# 🔗 エンドポイント: /clear_chat_history (同一URL維持)

@app.route("/clear_session", methods=["POST"])
@csrf_protect  # 🆕 Task #8 SL-4: API保護強化
@require_rate_limit
def clear_session():
    """🆕 セッションを完全クリアするエンドポイント（セッションキャッシュ問題対策）"""
    try:
        # 🆕 セッション全体の保護すべきキーリスト
        protected_keys = ["logged_in", "csrf_token", "lang"]

        # 🆕 現在のセッションから保護すべき値を保存
        preserved_data = {}
        for key in protected_keys:
            if key in session:
                preserved_data[key] = session[key]

        # 🆕 セッション完全クリア
        session.clear()

        # 🆕 保護すべきデータを復元
        for key, value in preserved_data.items():
            session[key] = value

        # 🆕 詳細ログ記録
        log_access_event('Session completely cleared - cache problem resolved')
        log_security_event(
            'SESSION_MANUAL_CLEAR', 
            f'User triggered session clear, preserved keys: {list(preserved_data.keys())}', 
            'INFO'
        )

        return jsonify({
            "success": True,
            "message": "セッションが完全にクリアされました",
            "preserved_keys": list(preserved_data.keys()),
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        app_logger.error(f"Session clear error: {str(e)}")
        log_security_event('SESSION_CLEAR_ERROR', str(e), 'ERROR')
        return jsonify({
            "success": False,
            "error": f"セッションクリアエラー: {str(e)}"
        })

@app.route("/reverse_better_translation", methods=["POST"])
@require_rate_limit
def reverse_better_translation():
    """改善された翻訳を逆翻訳するAPIエンドポイント（完全セキュリティ強化版）"""
    try:
        data = request.get_json() or {}
        improved_text = data.get("french_text", "")
        language_pair = data.get("language_pair", "ja-fr")

        # 🆕 包括的な入力値検証
        is_valid_text, text_error = EnhancedInputValidator.validate_text_input(
            improved_text, field_name="改善翻訳テキスト"
        )
        if not is_valid_text:
            log_security_event(
                'INVALID_REVERSE_TRANSLATION_INPUT',
                f'Text validation failed: {text_error}',
                'WARNING'
            )
            return jsonify({
                "success": False,
                "error": text_error
            })

        is_valid_pair, pair_error = EnhancedInputValidator.validate_language_pair(language_pair)
        if not is_valid_pair:
            log_security_event(
                'INVALID_REVERSE_LANGUAGE_PAIR',
                f'Language pair: {language_pair}',
                'WARNING'
            )
            return jsonify({
                "success": False,
                "error": pair_error
            })

        source_lang, target_lang = language_pair.split("-")

        if not improved_text:
            return jsonify({
                "success": False,
                "error": "逆翻訳するテキストが見つかりません"
            })

        reversed_text = f_reverse_translation(improved_text, target_lang, source_lang)

        log_access_event(f'Reverse better translation completed: {language_pair}')

        return jsonify({
            "success": True,
            "reversed_text": reversed_text
        })

    except Exception as e:
        import traceback
        app_logger.error(f"Reverse better translation error: {str(e)}")
        app_logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        })

# 🌍 安全版：日本語、英語、フランス語、スペイン語ランディングページ　　削除した（Blueprint対応）

# 🆕 Task 2.9.1: 包括的行動追跡システム - Analytics API

@app.route("/alpha/analytics", methods=["POST"])
@require_analytics_rate_limit  # 🛡️ Analytics専用レート制限適用（緩和版）
def analytics_endpoint():
    """
    包括的行動追跡システム - フロントエンド分析データ収集エンドポイント
    Task 2.9.1: 個人開発者への参入障壁構築 + ユーザー負担ゼロのデータ収集
    """
    start_time = time.time()

    try:
        # 🔒 セキュリティ検証
        client_ip = get_client_ip_safe()
        user_agent = get_user_agent_safe()

        # Content-Type検証
        if not request.is_json:
            log_security_event(
                'ANALYTICS_INVALID_CONTENT_TYPE',
                f'Non-JSON request from IP: {client_ip}',
                'WARNING'
            )
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        # JSONデータ取得と検証
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Empty JSON data'}), 400
        except Exception as e:
            log_security_event(
                'ANALYTICS_JSON_PARSE_ERROR',
                f'JSON parse error from IP: {client_ip}, Error: {str(e)}',
                'WARNING'
            )
            return jsonify({'error': 'Invalid JSON format'}), 400

        # 🆕 必須フィールド検証
        required_fields = ['event_type', 'timestamp']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            log_security_event(
                'ANALYTICS_MISSING_FIELDS',
                f'Missing fields {missing_fields} from IP: {client_ip}',
                'WARNING'
            )
            return jsonify({'error': f'Missing required fields: {missing_fields}'}), 400

        # 🆕 入力値検証と正規化
        event_type = str(data.get('event_type', '')).strip()
        if not event_type or len(event_type) > 50:
            return jsonify({'error': 'Invalid event_type'}), 400

        # 許可されたイベントタイプ（参入障壁: 予期しないデータ送信を防ぐ）
        allowed_event_types = {
            'page_view', 'cta_click', 'button_click', 'form_submit',
            'scroll_depth', 'time_on_page', 'language_switch',
            'navigation_click', 'feature_interaction', 'error_encountered',
            # 🆕 Task 2.9.1: 翻訳アプリ専用イベント
            'translation_request', 'translation_completion', 'translation_copy'
        }

        if event_type not in allowed_event_types:
            log_security_event(
                'ANALYTICS_INVALID_EVENT_TYPE',
                f'Invalid event_type: {event_type} from IP: {client_ip}',
                'WARNING'
            )
            return jsonify({'error': 'Invalid event_type'}), 400

        # 🆕 データ抽出と正規化
        analytics_data = {
            'event_type': event_type,
            'timestamp': int(data.get('timestamp', time.time() * 1000)),
            'page_url': str(data.get('page_url', request.referrer or ''))[:500],
            'action': str(data.get('action', ''))[:100],
            'language': str(data.get('language', 'unknown'))[:10],
            'session_id': session.get('session_id', session.get('csrf_token', 'anonymous')[:16]),
            'user_id': get_current_user_id(),
            'ip_address': client_ip,
            'user_agent': user_agent[:500],  # User-Agent制限
            'screen_width': int(data.get('screen_width', 0)) if str(data.get('screen_width', 0)).isdigit() else 0,
            'screen_height': int(data.get('screen_height', 0)) if str(data.get('screen_height', 0)).isdigit() else 0,
            'viewport_width': int(data.get('viewport_width', 0)) if str(data.get('viewport_width', 0)).isdigit() else 0,
            'viewport_height': int(data.get('viewport_height', 0)) if str(data.get('viewport_height', 0)).isdigit() else 0,
            'is_mobile': bool(data.get('is_mobile', False)),
            'referrer': str(data.get('referrer', request.referrer or ''))[:500],
            'utm_source': str(data.get('utm_source', ''))[:100],
            'utm_medium': str(data.get('utm_medium', ''))[:100],
            'utm_campaign': str(data.get('utm_campaign', ''))[:100],
            'custom_data': json.dumps(data.get('custom_data', {}))[:1000]  # カスタムデータをJSON文字列として保存
        }

        # 🆕 タイムスタンプ検証（現在時刻から大きく離れていないかチェック）
        current_timestamp = int(time.time() * 1000)
        timestamp_diff = abs(analytics_data['timestamp'] - current_timestamp)

        # 1日以上古い、または1時間以上未来のタイムスタンプは疑わしい
        if timestamp_diff > 24 * 60 * 60 * 1000:  # 24時間
            log_security_event(
                'ANALYTICS_SUSPICIOUS_TIMESTAMP',
                f'Suspicious timestamp difference: {timestamp_diff}ms from IP: {client_ip}',
                'WARNING'
            )
            # タイムスタンプを現在時刻に修正
            analytics_data['timestamp'] = current_timestamp

        # 🆕 データベース保存（AWS RDS移行を考慮した設計）
        try:
            if save_analytics_data(analytics_data):
                # 成功ログ
                processing_time = (time.time() - start_time) * 1000
                log_access_event(
                    f'Analytics data saved: {event_type} from {client_ip} '
                    f'(Processing: {processing_time:.2f}ms)'
                )

                # 🆕 レスポンス（ミニマル設計 - 情報漏洩防止）
                response_data = {
                    'status': 'success',
                    'event_id': analytics_data.get('event_id'),  # 保存時に生成されるID
                    'server_time': current_timestamp
                }

                return jsonify(response_data), 200
            else:
                # データベース保存失敗
                log_security_event(
                    'ANALYTICS_SAVE_FAILED',
                    f'Failed to save analytics data for event_type: {event_type} from IP: {client_ip}',
                    'ERROR'
                )
                return jsonify({'error': 'Failed to save analytics data'}), 500

        except Exception as db_error:
            log_security_event(
                'ANALYTICS_DB_ERROR',
                f'Database error while saving analytics: {str(db_error)}',
                'ERROR'
            )
            return jsonify({'error': 'Internal server error'}), 500

    except Exception as e:
        # 🚨 予期しないエラー
        log_security_event(
            'ANALYTICS_UNEXPECTED_ERROR',
            f'Unexpected error in analytics endpoint: {str(e)}',
            'CRITICAL'
        )
        return jsonify({'error': 'Internal server error'}), 500

def save_analytics_data(data: Dict[str, Any]) -> bool:
    """
    分析データをデータベースに保存
    AWS RDS移行を考慮した設計

    Returns:
        bool: 保存成功時True, 失敗時False
    """
    try:
        # 🆕 データベース接続（将来のAWS RDS対応）
        db_path = os.path.join(os.path.dirname(__file__), 'langpont_analytics.db')

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # 🆕 analytics_events テーブルの作成（存在しない場合）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analytics_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    timestamp INTEGER NOT NULL,
                    page_url TEXT,
                    action VARCHAR(100),
                    language VARCHAR(10),
                    session_id VARCHAR(50),
                    user_id INTEGER,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    screen_width INTEGER DEFAULT 0,
                    screen_height INTEGER DEFAULT 0,
                    viewport_width INTEGER DEFAULT 0,
                    viewport_height INTEGER DEFAULT 0,
                    is_mobile BOOLEAN DEFAULT 0,
                    referrer TEXT,
                    utm_source VARCHAR(100),
                    utm_medium VARCHAR(100),
                    utm_campaign VARCHAR(100),
                    custom_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT 0,

                    -- 🆕 インデックス用フィールド
                    date_only DATE GENERATED ALWAYS AS (DATE(timestamp/1000, 'unixepoch')) STORED,
                    hour_only INTEGER GENERATED ALWAYS AS (CAST(strftime('%H', timestamp/1000, 'unixepoch') AS INTEGER)) STORED
                )
            ''')

            # 🆕 インデックス作成（パフォーマンス最適化）
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics_events (timestamp)',
                'CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics_events (event_type)',
                'CREATE INDEX IF NOT EXISTS idx_analytics_session_id ON analytics_events (session_id)',
                'CREATE INDEX IF NOT EXISTS idx_analytics_user_id ON analytics_events (user_id)',
                'CREATE INDEX IF NOT EXISTS idx_analytics_ip_address ON analytics_events (ip_address)',
                'CREATE INDEX IF NOT EXISTS idx_analytics_date_only ON analytics_events (date_only)',
                'CREATE INDEX IF NOT EXISTS idx_analytics_hour_only ON analytics_events (hour_only)',
                'CREATE INDEX IF NOT EXISTS idx_analytics_processed ON analytics_events (processed)',
                # 🆕 複合インデックス（よく使われるクエリパターン用）
                'CREATE INDEX IF NOT EXISTS idx_analytics_user_date ON analytics_events (user_id, date_only)',
                'CREATE INDEX IF NOT EXISTS idx_analytics_session_time ON analytics_events (session_id, timestamp)',
                'CREATE INDEX IF NOT EXISTS idx_analytics_type_date ON analytics_events (event_type, date_only)'
            ]

            for index_sql in indexes:
                cursor.execute(index_sql)

            # 🆕 ユニークなイベントID生成
            import uuid
            event_id = str(uuid.uuid4())
            data['event_id'] = event_id

            # 🆕 データ挿入
            cursor.execute('''
                INSERT INTO analytics_events (
                    event_id, event_type, timestamp, page_url, action, language,
                    session_id, user_id, ip_address, user_agent,
                    screen_width, screen_height, viewport_width, viewport_height,
                    is_mobile, referrer, utm_source, utm_medium, utm_campaign,
                    custom_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_id, data['event_type'], data['timestamp'], data['page_url'],
                data['action'], data['language'], data['session_id'], data['user_id'],
                data['ip_address'], data['user_agent'], data['screen_width'],
                data['screen_height'], data['viewport_width'], data['viewport_height'],
                data['is_mobile'], data['referrer'], data['utm_source'],
                data['utm_medium'], data['utm_campaign'], data['custom_data']
            ))

            conn.commit()

            # 🆕 成功ログ（データサイズ付き）
            log_access_event(
                f'Analytics event saved: ID={event_id}, Type={data["event_type"]}, '
                f'User={data["user_id"]}, Session={data["session_id"][:8]}...'
            )

            return True

    except sqlite3.Error as e:
        logger.error(f"SQLite error in save_analytics_data: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in save_analytics_data: {str(e)}")
        return False

def get_current_user_id() -> Optional[int]:
    """現在のユーザーIDを取得（認証システム統合）"""
    try:
        # 🆕 認証システムが利用可能な場合
        if AUTH_SYSTEM_AVAILABLE and session.get('logged_in'):
            # 新しい認証システムのユーザーID
            return session.get('user_id')

        # 🆕 従来システムの場合
        if session.get('logged_in'):
            username = session.get('username')
            if username:
                # ユーザー名から簡易IDを生成（互換性のため）
                return hash(username) % 1000000  # 6桁のIDに変換

        return None
    except Exception:
        return None

# 🚀 Task 2.9.2 Phase B-3.5: 開発者専用リアルタイム監視API

# 開発者監視用データストア（メモリベース）
dev_monitoring_data = {
    "translation_progress": {},
    "user_activity": [],
    "system_status": {},
    "api_status": {},
    "last_actions": [],
    "current_session": {}
}

def check_developer_permission():
    """開発者・管理者権限をチェック"""
    user_role = session.get("user_role", "guest")
    return user_role in ["admin", "developer"]

def update_translation_progress(step: str, status: str, duration_ms: int = 0, data: dict = None):
    """翻訳進行状況を更新"""
    if not check_developer_permission():
        return

    session_id = session.get("session_id", "unknown")
    timestamp = datetime.now().isoformat()

    if session_id not in dev_monitoring_data["translation_progress"]:
        dev_monitoring_data["translation_progress"][session_id] = []

    progress_entry = {
        "step": step,
        "status": status,
        "timestamp": timestamp,
        "duration_ms": duration_ms,
        "data": data or {}
    }

    dev_monitoring_data["translation_progress"][session_id].append(progress_entry)

    # 最新10件のみ保持
    if len(dev_monitoring_data["translation_progress"][session_id]) > 10:
        dev_monitoring_data["translation_progress"][session_id] = dev_monitoring_data["translation_progress"][session_id][-10:]

def log_user_activity(action: str, details: dict = None):
    """ユーザー行動をログ"""
    if not check_developer_permission():
        return

    activity_entry = {
        "action": action,
        "timestamp": datetime.now().isoformat(),
        "session_id": session.get("session_id", "unknown"),
        "username": session.get("username", "unknown"),
        "details": details or {}
    }

    dev_monitoring_data["user_activity"].append(activity_entry)

    # 最新50件のみ保持
    if len(dev_monitoring_data["user_activity"]) > 50:
        dev_monitoring_data["user_activity"] = dev_monitoring_data["user_activity"][-50:]

@app.route("/get_analysis_with_recommendation", methods=["POST"])
@require_rate_limit
def get_analysis_with_recommendation():
    """選択されたエンジンで分析と推奨抽出を実行"""
    try:
        # 使用制限チェック
        usage_ok, current_usage, daily_limit = check_daily_usage()
        if not usage_ok:
            return jsonify({
                "success": False,
                "error": "daily_limit_exceeded",
                "message": "本日の利用制限に達しました。",
                "current_usage": current_usage,
                "daily_limit": daily_limit,
                "reset_time": "明日の00:00"
            }), 429

        # 分析エンジンを取得
        selected_engine = session.get('analysis_engine', 'gemini')

        # 🆕 SL-3 Phase 2: 翻訳データをRedisから取得（フォールバック付き）
        session_id = getattr(session, 'session_id', None)
        
        if translation_state_manager and session_id:
            # Redisから大容量データを取得
            translated_text = translation_state_manager.get_large_data(
                "translated_text", session_id, 
                default=session.get("translated_text", "")
            )
            better_translation = translation_state_manager.get_large_data(
                "better_translation", session_id, 
                default=session.get("better_translation", "")
            )
            gemini_translation = translation_state_manager.get_large_data(
                "gemini_translation", session_id, 
                default=session.get("gemini_translation", "")
            )
            # input_textは翻訳状態データなので既存のget_translation_state関数を使用
            input_text = get_translation_state("input_text", "")
        else:
            # フォールバック: セッションから取得
            translated_text = session.get("translated_text", "")
            better_translation = session.get("better_translation", "")
            gemini_translation = session.get("gemini_translation", "")
            input_text = session.get("input_text", "")

        if not all([translated_text, better_translation, gemini_translation, input_text]):
            return jsonify({
                "success": False,
                "error": "Insufficient translation data"
            }), 400

        # AnalysisEngineManagerを初期化
        engine_manager = AnalysisEngineManager(claude_client, app_logger, f_gemini_3way_analysis)

        # 分析を実行
        analysis_result = engine_manager.analyze_translations(
            chatgpt_trans=translated_text,
            enhanced_trans=better_translation,
            gemini_trans=gemini_translation,
            engine=selected_engine,
            context={
                "input_text": input_text,
                "source_lang": session.get('language_pair', 'ja-en').split('-')[0],
                "target_lang": session.get('language_pair', 'ja-en').split('-')[1],
                "partner_message": get_translation_state("partner_message", ""),
                "context_info": get_translation_state("context_info", "")
            }
        )

        if not analysis_result['success']:
            return jsonify({
                "success": False,
                "error": analysis_result['error']
            }), 500

        analysis_text = analysis_result.get('analysis_text', '')

        # ChatGPTで推奨を抽出
        recommendation_result = extract_recommendation_from_analysis(analysis_text, selected_engine)

        # 使用回数を更新
        increment_daily_usage()

        return jsonify({
            "success": True,
            "engine_used": selected_engine,
            "analysis": analysis_text,
            "recommendation": recommendation_result,
            "prompt_used": analysis_result.get('prompt', ''),
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        log_access_event(f'Error in analysis with recommendation: {str(e)}')
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# 🆕 Task 2.9.2 Phase B-3.5.10: 統合活動ダッシュボード API

@app.route("/admin/comprehensive_dashboard")
@require_login
def admin_comprehensive_dashboard():
    """統合活動ダッシュボード（管理者専用）"""
    # デバッグ情報
    logged_in = session.get('logged_in', False)
    user_role = session.get('user_role', 'guest')
    username = session.get('username', 'unknown')

    app_logger.info(f"Comprehensive dashboard access: logged_in={logged_in}, role={user_role}, user={username}")

    # 管理者権限チェック
    if user_role not in ['admin', 'developer']:
        app_logger.warning(f"Unauthorized comprehensive dashboard access: role={user_role}")
        return jsonify({
            "error": "アクセス権限がありません",
            "error_code": "UNAUTHORIZED",
            "success": False,
            "required_role": "admin or developer",
            "current_role": user_role
        }), 403

    try:
        # CSRFトークンを生成・セッションに保存
        import secrets
        csrf_token = secrets.token_urlsafe(32)
        session['csrf_token'] = csrf_token

        return render_template('unified_comprehensive_dashboard.html', csrf_token=csrf_token)
    except Exception as e:
        app_logger.error(f"Comprehensive dashboard template error: {str(e)}")
        return jsonify({
            "error": "テンプレートエラー",
            "error_code": "TEMPLATE_ERROR",
            "success": False,
            "details": str(e)
        }), 500

@app.route("/admin/four_stage_dashboard")
@require_login
def four_stage_dashboard():
    """4段階分析ダッシュボード（管理者専用）"""
    user_role = session.get('user_role', 'guest')
    username = session.get('username', 'unknown')

    app_logger.info(f"Four stage dashboard access: role={user_role}, user={username}")

    # 管理者権限チェック
    if user_role not in ['admin', 'developer']:
        app_logger.warning(f"Unauthorized four stage dashboard access: role={user_role}")
        return jsonify({
            "error": "アクセス権限がありません",
            "error_code": "UNAUTHORIZED",
            "success": False,
            "required_role": "admin or developer",
            "current_role": user_role
        }), 403

    try:
        # CSRFトークン生成
        import secrets
        csrf_token = secrets.token_urlsafe(32)
        session['csrf_token'] = csrf_token

        return render_template('admin/four_stage_dashboard.html', csrf_token=csrf_token)
    except Exception as e:
        app_logger.error(f"Four stage dashboard template error: {str(e)}")
        return jsonify({
            "error": "テンプレートエラー",
            "error_code": "TEMPLATE_ERROR",
            "success": False,
            "details": str(e)
        }), 500

# アプリケーション起動とセキュリティ最終設定

# ================================================================
# 🆕 SL-3 Phase 3: 翻訳状態双方向同期APIエンドポイント
# ================================================================

@app.route("/api/get_translation_state", methods=["POST"])
@csrf_protect  # 🆕 Task #8 SL-4: API保護強化
@require_rate_limit
def get_translation_state_api():
    """
    Redisから翻訳状態を取得するAPIエンドポイント
    """
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id') or getattr(session, 'session_id', None) or session.get("session_id") or session.get("csrf_token", "")[:16] or f"trans_{int(time.time())}"
        
        if not translation_state_manager:
            return jsonify({
                "success": False,
                "error": "Translation state manager not available"
            })
        
        # 全翻訳状態フィールドを取得
        fields_to_get = list(translation_state_manager.CACHE_KEYS.keys()) + list(translation_state_manager.LARGE_DATA_KEYS.keys())
        
        states = {}
        for field in fields_to_get:
            if field in translation_state_manager.CACHE_KEYS:
                value = translation_state_manager.get_translation_state(session_id, field)
            else:
                value = translation_state_manager.get_large_data(field, session_id)
            
            states[field] = value
        
        app_logger.info(f"🔄 SL-3 Phase 3: Translation states retrieved for session {session_id[:16]}...")
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "states": states
        })
        
    except Exception as e:
        app_logger.error(f"❌ SL-3 Phase 3: get_translation_state error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/set_translation_state", methods=["POST"])
@csrf_protect  # 🆕 Task #8 SL-4: API保護強化
@require_rate_limit
def set_translation_state():
    """
    翻訳状態をRedisに保存するAPIエンドポイント
    """
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id') or getattr(session, 'session_id', None) or session.get("session_id") or session.get("csrf_token", "")[:16] or f"trans_{int(time.time())}"
        field = data.get('field')
        value = data.get('value')
        
        if not translation_state_manager:
            return jsonify({
                "success": False,
                "error": "Translation state manager not available"
            })
        
        if not field or value is None:
            return jsonify({
                "success": False,
                "error": "Field and value are required"
            })
        
        # フィールドタイプに応じて適切なメソッドを呼び出し
        if field in translation_state_manager.CACHE_KEYS:
            success = translation_state_manager.set_translation_state(session_id, field, value)
        elif field in translation_state_manager.LARGE_DATA_KEYS:
            success = translation_state_manager.save_large_data(field, value, session_id)
        else:
            return jsonify({
                "success": False,
                "error": f"Unknown field: {field}"
            })
        
        if success:
            app_logger.info(f"✅ SL-3 Phase 3: Translation state saved - {field} for session {session_id[:16]}...")
            return jsonify({
                "success": True,
                "session_id": session_id,
                "field": field
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to save to Redis"
            })
        
    except Exception as e:
        app_logger.error(f"❌ SL-3 Phase 3: set_translation_state error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# 🆕 Task #9-3 AP-1 Phase 3: AnalysisEngineManager初期化
analysis_engine_manager = AnalysisEngineManager(client, app_logger, f_gemini_3way_analysis)

# 🆕 Task #9-3 AP-1 Phase 3: AnalysisService初期化
try:
    from services.analysis_service import AnalysisService
    analysis_service = AnalysisService(
        translation_state_manager=translation_state_manager,
        analysis_engine_manager=analysis_engine_manager,
        claude_client=client,
        logger=app_logger,
        labels=labels
    )
    app_logger.info("✅ Task #9-3 Phase 3: AnalysisService initialized successfully")
except ImportError as e:
    app_logger.error(f"❌ Task #9-3 Phase 3: AnalysisService import failed: {e}")
    analysis_service = None

# 🆕 Task #9-3 AP-1 Phase 3b: InteractiveService初期化
try:
    from services.interactive_service import InteractiveService
    interactive_service = InteractiveService(
        translation_state_manager=translation_state_manager,
        interactive_processor=interactive_processor,
        logger=app_logger,
        labels=labels
    )
    app_logger.info("✅ Task #9-3 Phase 3b: InteractiveService initialized successfully")
except ImportError as e:
    app_logger.error(f"❌ Task #9-3 Phase 3b: InteractiveService import failed: {e}")
    interactive_service = None

# 🆕 Task #9-3 AP-1 Phase 3: 分析Blueprint登録
try:
    from routes.analysis import init_analysis_routes
    analysis_bp = init_analysis_routes(
        analysis_service, interactive_service, app_logger, labels
    )
    app.register_blueprint(analysis_bp)
    app_logger.info("✅ Task #9-3 AP-1 Phase 3: Analysis Blueprint registered successfully")
except ImportError as e:
    app_logger.error(f"❌ Task #9-3 AP-1 Phase 3: Analysis Blueprint registration failed: {e}")

if __name__ == "__main__":
    # 🎯 Phase B1: 友人推奨のシンプル設定（8080ポート競合問題解決）
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=False,          # 友人推奨: 本番環境設定
        use_reloader=False,   # 友人推奨: 子プロセス防止
        threaded=True
    )
