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

# 🆕 Task#9-4 AP-1 Ph4 Step4（再挑戦）- 監視レイヤー（OL-0＋Level1）
from utils.debug_logger import data_flow_logger

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
    csrf_protect, require_rate_limit
)

# 追加：互換シム（decorators側は無改変）
from functools import wraps
import os
from flask import abort
import security.decorators as _secdec

# --- 管理者デコレータの互換名決定 ---
require_admin_auth = (
    getattr(_secdec, 'require_admin_auth', None) or
    getattr(_secdec, 'admin_required', None) or
    getattr(_secdec, 'require_admin', None)
)
if require_admin_auth is None:
    # 開発時は通す／本番厳格モードでは403
    def require_admin_auth(fn):
        @wraps(fn)
        def _w(*a, **k):
            if os.getenv('ADMIN_AUTH_STRICT', 'false').lower() == 'true':
                abort(403)
            return fn(*a, **k)
        return _w

# --- 開発モード用デコレータ（存在しなければ作る） ---
require_dev_mode = (
    getattr(_secdec, 'require_dev_mode', None) or
    getattr(_secdec, 'dev_only', None)
)
if require_dev_mode is None:
    def require_dev_mode(fn):
        @wraps(fn)
        def _w(*a, **k):
            dev_env = os.getenv('ENV', '').lower() in ('dev', 'development', 'local')
            explicit = os.getenv('DEBUG_CLIENT_INGEST_ENABLED', 'false').lower() == 'true'
            if not (dev_env or explicit):
                abort(403)
            return fn(*a, **k)
        return _w

# 設定情報
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
ERROR_MESSAGES = {
    "api_error": "翻訳エラー: APIリクエストに失敗しました",
    "timeout_error": "翻訳エラー: タイムアウトしました",
    "validation_error": "入力検証エラー",
}

# Rate limiting settings
RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW = 60  # seconds

# Flaskとその拡張
from flask import (
    Flask, render_template, request, redirect, url_for, 
    jsonify, session, g, send_from_directory, Response
)
from flask_cors import CORS

# 標準ライブラリ
import sqlite3
import uuid

# Task 2.9.2 Phase B-4-Ext: Anthropic Claude統合
try:
    from anthropic import Anthropic
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    print("⚠️ Anthropic library not available. Claude features will be disabled.")
    ANTHROPIC_AVAILABLE = False

# OpenAI and other external services
import openai
from openai import OpenAI

# 環境変数の読み込み
load_dotenv()

# ユーザー認証システム
try:
    from user_auth import (
        init_auth_system, check_password, get_current_user_id, 
        log_user_activity, update_session_activity
    )
    from user_profile import init_user_profile_system
    print("認証システム正常にインポートされました")
except ImportError as e:
    print(f"認証システムのインポートエラー: {e}")
    # フォールバック関数の定義
    def init_auth_system():
        return False
    def check_password(password):
        return password == os.getenv("APP_PASSWORD", "default_password")
    def get_current_user_id():
        return session.get("user_id", "anonymous")
    def log_user_activity(action, details=""):
        pass
    def update_session_activity():
        pass
    def init_user_profile_system():
        pass

# 翻訳履歴システム
try:
    from translation_history import (
        init_translation_history_db, save_translation_history,
        get_user_translation_history, get_translation_statistics,
        cleanup_old_history, export_user_history
    )
    print("翻訳履歴システム正常にインポートされました")
except ImportError as e:
    print(f"翻訳履歴システムのインポートエラー: {e}")
    # フォールバック関数
    def init_translation_history_db():
        pass
    def save_translation_history(*args, **kwargs):
        pass
    def get_user_translation_history(*args, **kwargs):
        return []
    def get_translation_statistics(*args, **kwargs):
        return {}
    def cleanup_old_history(*args, **kwargs):
        pass
    def export_user_history(*args, **kwargs):
        return None

# 多言語対応ラベル
from labels import labels

# Gemini API
import google.generativeai as genai

# データベース設定
DATABASE = 'langpont.db'

# OpenAI APIキー
client = None
CLAUDE_API_KEY = None
claude_client = None  # グローバル変数として定義

# Version information
VERSION_INFO = {
    "version": VERSION,
    "environment": ENVIRONMENT,
    "deployment": DEPLOYMENT["platform"],
    "features": FEATURES
}

# 🆕 管理者システムのインポート
from admin.admin_auth import AdminAuthManager
from admin.admin_logger import AdminLogger

# レート制限用ストア
rate_limit_store = {}

# 🆕 Phase 8b-0: 統合初期化関数
def setup_enhanced_logging():
    """統合ログシステムの初期化"""
    # Security logger
    security_logger = logging.getLogger('security')
    security_handler = RotatingFileHandler('logs/security.log', maxBytes=10485760, backupCount=5)
    security_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s'
    ))
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.INFO)
    
    # Application logger  
    app_logger = logging.getLogger('app')
    app_handler = RotatingFileHandler('logs/app.log', maxBytes=10485760, backupCount=5)
    app_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s'
    ))
    app_logger.addHandler(app_handler)
    app_logger.setLevel(logging.INFO)
    
    # Access logger
    access_logger = logging.getLogger('access')
    access_handler = RotatingFileHandler('logs/access.log', maxBytes=10485760, backupCount=5)
    access_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(message)s'
    ))
    access_logger.addHandler(access_handler)
    access_logger.setLevel(logging.INFO)
    
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

# 🆕 Task#9-4 AP-1 Ph4 Step4（再挑戦）- 監視レイヤー初期化
data_flow_logger.init_app(app)

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
    app_logger.error(f"❌ SL-3 Phase 1: TranslationStateManager initialization failed: {e}")
    translation_state_manager = None
    app.translation_state_manager = None

# 🆕 SL-2.2: セッション管理メソッド（Flask標準セッション使用）
app_logger.info("📝 SL-2.2: Using Flask standard session (filesystem)")

# OpenAI API client initialization
try:
    client = OpenAI(api_key=api_key)
    app_logger.info("OpenAI client initialized successfully")
except Exception as e:
    app_logger.error(f"Failed to initialize OpenAI client: {e}")
    client = None

# 🆕 Task 2.9.2 Phase B-4-Ext: Claude API初期化
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
if CLAUDE_API_KEY and ANTHROPIC_AVAILABLE:
    try:
        claude_client = Anthropic(api_key=CLAUDE_API_KEY)
        app_logger.info("Claude API client initialized successfully")
    except Exception as e:
        app_logger.error(f"Failed to initialize Claude client: {e}")
        claude_client = None
else:
    claude_client = None
    if not CLAUDE_API_KEY:
        app_logger.warning("Claude API key not found in environment variables")
    if not ANTHROPIC_AVAILABLE:
        app_logger.warning("Anthropic library not available")

# CORS設定 - 必要に応じて有効化
# CORS(app)

# データベース初期化
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # ユーザーテーブル（既存）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 使用履歴テーブル（既存）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # インデックスの作成
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_usage_history_user_id 
            ON usage_history(user_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_usage_history_timestamp 
            ON usage_history(timestamp)
        ''')
        
        conn.commit()
        app_logger.info("Database initialized successfully")

# Initialize database on startup
init_db()

# 管理者システムの初期化
admin_auth = AdminAuthManager(app)
admin_logger = AdminLogger()

# 認証システムの初期化
auth_initialized = init_auth_system()
if auth_initialized:
    app_logger.info("認証システムが正常に初期化されました")
else:
    app_logger.warning("認証システムの初期化に失敗しました - 基本認証モードで動作します")

# プロフィールシステムの初期化
init_user_profile_system()

# 翻訳履歴データベースの初期化
init_translation_history_db()

# 🆕 Phase B-1: 管理者システム統合
print("🚀 Phase B-1: 管理者システム統合開始")

# Import admin routes AFTER all systems are initialized
from admin_routes import admin_bp
app.register_blueprint(admin_bp)

# Import debug routes
from debug_routes import debug_bp
app.register_blueprint(debug_bp)

# Import security routes
from security_routes import security_bp
app.register_blueprint(security_bp)

# Import developer API routes
from dev_api_routes import dev_api_bp
app.register_blueprint(dev_api_bp)

# 🆕 Phase B-1.5: 管理者API統合
from admin_api_routes import admin_api_bp
app.register_blueprint(admin_api_bp)

# 🆕 Task H2-4.3c-Phase4b-3: ランディングページルート登録
from landing_routes import landing_bp
app.register_blueprint(landing_bp)

# 🆕 Phase 7: エンジン管理Blueprint登録
from routes.engine_management import init_engine_routes
engine_bp = init_engine_routes(session, app_logger)
app.register_blueprint(engine_bp)

print("✅ Phase B-1: 管理者システム統合完了")

# 🆕 認証ルートの登録
from auth_routes import init_auth_routes
auth_bp = init_auth_routes(
    auth_check_func=check_password,
    get_user_func=get_current_user_id,
    log_activity_func=log_user_activity,
    update_session_func=update_session_activity,
    history_funcs={
        'save': save_translation_history,
        'get': get_user_translation_history,
        'stats': get_translation_statistics,
        'cleanup': cleanup_old_history,
        'export': export_user_history
    },
    session_redis_manager=session_redis_manager,
    logger=app_logger
)
if auth_bp:
    app.register_blueprint(auth_bp)
    app_logger.info("認証システムが正常に初期化されました")

# セッション設定
@app.before_request
def before_request():
    # セキュリティヘッダーの設定
    g.start_time = time.time()
    
    # セッションの初期化
    if 'session_created' not in session:
        session['session_created'] = datetime.now().isoformat()
        session.permanent = True
        
        # 🆕 SL-2.1: セッションIDの生成（Flask標準セッションと同期）
        if not getattr(session, 'session_id', None):
            session.session_id = str(uuid.uuid4())
        
        # Redis同期（利用可能な場合）
        if session_redis_manager:
            try:
                session_redis_manager.sync_to_redis(
                    session_id=session.session_id,
                    session_data=dict(session)
                )
            except Exception as e:
                app_logger.warning(f"⚠️ Redis sync failed: {e}")
    
    # ユーザーアクティビティの更新
    update_session_activity()

@app.after_request
def after_request(response):
    # セキュリティヘッダーの追加
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # レスポンスタイムの記録
    if hasattr(g, 'start_time'):
        elapsed = time.time() - g.start_time
        response.headers['X-Response-Time'] = str(elapsed)
    
    return response

# エラーハンドラー
@app.errorhandler(404)
def not_found(error):
    log_security_event('404_ERROR', f'Page not found: {request.url}', 'WARNING')
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    log_security_event('500_ERROR', f'Internal server error: {str(error)}', 'ERROR')
    return render_template('500.html'), 500

@app.errorhandler(403)
def forbidden(error):
    log_security_event('403_ERROR', f'Forbidden access attempt: {request.url}', 'WARNING')
    return jsonify({"error": "Forbidden"}), 403

# 🆕 セキュリティ強化: CSRFトークン例外処理
@app.errorhandler(400)
def bad_request(error):
    if 'CSRF' in str(error):
        log_security_event('CSRF_ERROR', f'CSRF validation failed', 'WARNING')
        return jsonify({"error": "CSRF validation failed"}), 400
    return jsonify({"error": "Bad request"}), 400

# Gemini API キーの設定
gemini_api_key = os.getenv("GEMINI_API_KEY")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)

# データベース接続関数
def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

# ユーザー情報の取得
def get_user_info():
    """現在のユーザー情報を取得"""
    return {
        'username': session.get('username', 'unknown'),
        'user_id': get_current_user_id(),
        'user_role': session.get('user_role', 'user'),
        'logged_in': session.get('logged_in', False)
    }

# 使用回数管理関数
def check_daily_usage(client_id):
    """
    デイリー使用制限をチェック
    Returns: (can_use: bool, current_usage: int, daily_limit: int)
    """
    # ユーザーロールに基づく制限
    user_role = session.get('user_role', 'guest')
    user_info = get_user_info()
    
    # 無制限ユーザーのチェック
    if user_role in ['admin', 'developer', 'premium']:
        return True, 0, -1  # -1 は無制限を示す
    
    # 通常ユーザーの制限
    daily_limit = USAGE_LIMITS.get(user_role, USAGE_LIMITS['guest'])
    
    # 今日の使用回数を取得
    today = datetime.now().strftime('%Y-%m-%d')
    usage_key = f'usage:{client_id}:{today}'
    
    # Redisから取得を試行
    current_usage = 0
    if session_redis_manager:
        try:
            usage_data = session_redis_manager.redis_client.get(usage_key)
            if usage_data:
                current_usage = int(usage_data)
        except Exception as e:
            app_logger.warning(f"Redis usage check failed: {e}")
            # フォールバック: セッションから取得
            current_usage = session.get(f'usage_{today}', 0)
    else:
        # Redisが利用できない場合はセッションを使用
        current_usage = session.get(f'usage_{today}', 0)
    
    can_use = current_usage < daily_limit
    
    # 使用した場合はカウントを増やす
    if can_use:
        new_count = current_usage + 1
        if session_redis_manager:
            try:
                session_redis_manager.redis_client.set(
                    usage_key, 
                    new_count,
                    ex=86400  # 24時間で自動削除
                )
            except Exception as e:
                app_logger.warning(f"Redis usage update failed: {e}")
                session[f'usage_{today}'] = new_count
        else:
            session[f'usage_{today}'] = new_count
    
    return can_use, current_usage, daily_limit

# クライアントID取得関数
def get_client_id():
    """クライアントIDを取得または生成"""
    if 'client_id' not in session:
        # ユーザーIDベースのクライアントID生成
        user_id = get_current_user_id()
        client_ip = get_client_ip_safe()
        
        # より安全なクライアントID生成
        client_data = f"{user_id}:{client_ip}:{datetime.now().date()}"
        client_id = hashlib.sha256(client_data.encode()).hexdigest()[:16]
        session['client_id'] = client_id
        
        # Redisにも保存
        if session_redis_manager and getattr(session, 'session_id', None):
            try:
                session_redis_manager.sync_to_redis(
                    session_id=session.session_id,
                    session_data={'client_id': client_id}
                )
            except Exception as e:
                app_logger.warning(f"Redis client_id sync failed: {e}")
    
    return session['client_id']

# 使用状況取得関数
def get_usage_status(client_id):
    """使用状況の詳細を取得"""
    user_info = get_user_info()
    user_role = session.get('user_role', 'guest')
    
    # 使用制限チェック
    can_use, current_usage, daily_limit = check_daily_usage(client_id)
    
    # 無制限ユーザーの判定
    is_unlimited = daily_limit == -1
    
    return {
        'username': user_info['username'],
        'user_role': user_role,
        'current_usage': current_usage if not is_unlimited else 0,
        'daily_limit': daily_limit if not is_unlimited else 0,
        'remaining': (daily_limit - current_usage) if not is_unlimited else 999,
        'can_use': can_use,
        'is_unlimited': is_unlimited,
        'reset_time': '午前0時（日本時間）'
    }

# 🆕 既存コード互換性のための翻訳履歴システムヘルパー（translationhistoryを前提）
def save_translation(source_text, source_lang, target_lang, translated_text, 
                    engine="chatgpt", quality_score=None, user_feedback=None):
    """翻訳履歴を保存（後方互換性）"""
    try:
        user_id = get_current_user_id()
        save_translation_history(
            user_id=user_id,
            source_text=source_text,
            source_lang=source_lang,
            target_lang=target_lang,
            translated_text=translated_text,
            engine=engine,
            quality_score=quality_score,
            user_feedback=user_feedback
        )
    except Exception as e:
        app_logger.error(f"Failed to save translation history: {e}")

# 利用履歴記録関数
def record_usage(client_id, action, details=""):
    """利用履歴を記録"""
    try:
        log_user_activity(action, details)
    except Exception as e:
        app_logger.error(f"Usage recording error: {e}")

# 🆕 Phase B-2: 強化セキュリティミドルウェア
@app.before_request
def security_checks():
    """リクエスト前のセキュリティチェック"""
    # IPアドレスベースのレート制限
    client_ip = get_client_ip_safe()
    endpoint = get_endpoint_safe()
    
    # 特定エンドポイントの保護
    protected_endpoints = ['/admin', '/api/admin', '/debug']
    if any(endpoint.startswith(ep) for ep in protected_endpoints):
        if not session.get('is_admin'):
            log_security_event('UNAUTHORIZED_ACCESS_ATTEMPT', 
                             f'Attempted to access {endpoint}', 'WARNING')
            # 管理者エンドポイントへのアクセスは個別にチェックされるため、ここでは記録のみ

# 🆕 TranslationContext統合クラス（簡易版）
class TranslationContext:
    """翻訳コンテキスト管理クラス（後方互換性のため残存）"""
    
    @staticmethod
    def save_context(data, is_large=False):
        """
        翻訳コンテキストを保存
        Phase 3c-3: StateManagerに処理を委譲
        """
        if not translation_state_manager:
            return False
            
        session_id = getattr(session, 'session_id', None) or session.get("session_id")
        if not session_id:
            return False
            
        try:
            if is_large:
                # 大容量データはRedisに保存
                for key, value in data.items():
                    translation_state_manager.save_large_data(key, value, session_id)
            else:
                # 通常データはキャッシュに保存
                for key, value in data.items():
                    translation_state_manager.set_translation_state(session_id, key, value)
            return True
        except Exception as e:
            app_logger.error(f"Context save error (delegated to StateManager): {e}")
            return False
    
    @staticmethod
    def get_context():
        """
        翻訳コンテキストを取得
        Phase 3c-3: StateManagerから取得
        """
        if not translation_state_manager:
            return {}
            
        session_id = getattr(session, 'session_id', None) or session.get("session_id")
        if not session_id:
            return {}
            
        try:
            # 基本フィールドを取得
            context = {}
            fields = ['input_text', 'partner_message', 'context_info', 
                     'language_pair', 'source_lang', 'target_lang']
            
            for field in fields:
                value = translation_state_manager.get_translation_state(session_id, field)
                if value:
                    context[field] = value
                    
            # 大容量データも取得
            large_fields = ['translated_text', 'reverse_translated_text', 
                          'better_translation', 'gemini_translation']
            for field in large_fields:
                value = translation_state_manager.get_large_data(field, session_id)
                if value:
                    context[field] = value
                    
            return context
        except Exception as e:
            app_logger.error(f"Context get error (delegated from StateManager): {e}")
            return {}
    
    @staticmethod
    def clear_context():
        """
        翻訳コンテキストをクリア
        Phase 3c-3: StateManagerのクリア処理を呼び出し
        """
        if not translation_state_manager:
            return
            
        session_id = getattr(session, 'session_id', None) or session.get("session_id")
        if not session_id:
            return
            
        try:
            translation_state_manager.clear_context_data(session_id)
        except Exception as e:
            app_logger.error(f"Context clear error (delegated to StateManager): {e}")

# 🆕 Task B2-9-Phase3: システム間統合
from translation.translation_adapters import TranslationEngineAdapter
from translation.context_manager import ContextManager
# from translation.analysis_engine import AnalysisEngineManager  # Phase B-4で分離済み

# システム統合の初期化
translation_adapter = TranslationEngineAdapter(client, app_logger)
context_manager = ContextManager()
# AnalysisEngineManagerは後で初期化（claude_client必要）

# ヘルパー関数群

def extract_language_name(lang_code):
    """言語コードから言語名を抽出"""
    lang_names = {
        'ja': '日本語', 'en': '英語', 'zh': '中国語', 'ko': '韓国語',
        'es': 'スペイン語', 'fr': 'フランス語', 'de': 'ドイツ語',
        'it': 'イタリア語', 'pt': 'ポルトガル語', 'ru': 'ロシア語',
        'ar': 'アラビア語', 'hi': 'ヒンディー語', 'th': 'タイ語',
        'vi': 'ベトナム語', 'id': 'インドネシア語', 'ms': 'マレー語',
        'tl': 'タガログ語', 'nl': 'オランダ語', 'sv': 'スウェーデン語',
        'no': 'ノルウェー語', 'da': 'デンマーク語', 'fi': 'フィンランド語',
        'pl': 'ポーランド語', 'cs': 'チェコ語', 'sk': 'スロバキア語',
        'hu': 'ハンガリー語', 'ro': 'ルーマニア語', 'bg': 'ブルガリア語',
        'hr': 'クロアチア語', 'sr': 'セルビア語', 'sl': 'スロベニア語',
        'lt': 'リトアニア語', 'lv': 'ラトビア語', 'et': 'エストニア語',
        'tr': 'トルコ語', 'el': 'ギリシャ語', 'he': 'ヘブライ語',
        'fa': 'ペルシャ語', 'ur': 'ウルドゥー語', 'bn': 'ベンガル語',
        'ta': 'タミル語', 'te': 'テルグ語', 'mr': 'マラーティー語',
        'gu': 'グジャラート語', 'kn': 'カンナダ語', 'ml': 'マラヤーラム語',
        'pa': 'パンジャブ語', 'ne': 'ネパール語', 'si': 'シンハラ語',
        'my': 'ミャンマー語', 'km': 'クメール語', 'lo': 'ラオ語',
        'ka': 'ジョージア語', 'am': 'アムハラ語', 'sw': 'スワヒリ語'
    }
    return lang_names.get(lang_code, lang_code)

# 💡 Task #9-4 AP-1 Phase 4 Step1: better_translation関数
def f_better_translation(translated_text, source_lang="ja", target_lang="en", display_lang="jp"):
    """
    翻訳結果を改善・洗練させる（Phase 4で分離予定）
    """
    if not translated_text:
        return translated_text
    
    try:
        # 言語ラベル取得
        source_label = extract_language_name(source_lang)
        target_label = extract_language_name(target_lang)
        
        # 改善用プロンプト
        if display_lang == "jp":
            prompt = f"""
            以下の{source_label}から{target_label}への翻訳を、より自然で洗練された表現に改善してください。
            
            現在の翻訳: {translated_text}
            
            改善のポイント:
            1. より自然な{target_label}の表現に
            2. 文脈に応じた適切な語彙選択
            3. 流暢で読みやすい文章構造
            
            改善された翻訳のみを出力してください。
            """
        else:
            prompt = f"""
            Please improve the following {source_lang} to {target_lang} translation to make it more natural and refined.
            
            Current translation: {translated_text}
            
            Improvement points:
            1. More natural {target_lang} expression
            2. Appropriate vocabulary based on context
            3. Fluent and readable sentence structure
            
            Output only the improved translation.
            """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a professional translator specializing in {source_lang} to {target_lang} translation."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.3
        )
        
        improved = response.choices[0].message.content.strip()
        
        # ログ記録
        app_logger.info(f"Translation improved: {len(translated_text)} -> {len(improved)} chars")
        
        return improved
        
    except Exception as e:
        app_logger.error(f"Better translation error: {str(e)}")
        # エラー時は元の翻訳を返す
        return translated_text

# 💡 Task #9-4 AP-1 Phase 4 Step2: reverse_translation関数
def f_reverse_translation(text, source_lang="en", target_lang="ja", display_lang="jp"):
    """
    逆翻訳を実行（Phase 4で分離予定）
    """
    if not text:
        return ""
    
    try:
        # 言語ラベル取得
        source_label = extract_language_name(source_lang)
        target_label = extract_language_name(target_lang)
        
        # 逆翻訳プロンプト
        if display_lang == "jp":
            prompt = f"""
            以下の{source_label}のテキストを{target_label}に正確に翻訳してください。
            元の意味を保ちながら、自然な{target_label}にしてください。
            
            テキスト: {text}
            
            翻訳のみを出力してください。
            """
        else:
            prompt = f"""
            Please accurately translate the following {source_lang} text to {target_lang}.
            Maintain the original meaning while making it natural {target_lang}.
            
            Text: {text}
            
            Output only the translation.
            """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a professional translator specializing in {source_lang} to {target_lang} translation."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.1
        )
        
        reverse_text = response.choices[0].message.content.strip()
        
        # ログ記録
        app_logger.info(f"Reverse translation completed: {source_lang} -> {target_lang}")
        
        return reverse_text
        
    except Exception as e:
        app_logger.error(f"Reverse translation error: {str(e)}")
        return ""

# 🆕 Phase B-4-Ext: 分析エンジン管理
from translation.analysis_engine import AnalysisEngineManager

# 🆕 Phase B-2.1-SubPhase3: エキスパートAI完全統合版
from translation.expert_ai import LangPontTranslationExpertAI

# 🆕 Task 2.8.3b: 一時的な逆翻訳生成関数（将来削除予定）
def generate_reverse_translations(translated_text, better_translation, gemini_translation,
                                 source_lang="ja", target_lang="en"):
    """3つの翻訳結果に対する逆翻訳を生成"""
    results = {}
    
    # ChatGPT逆翻訳
    if translated_text:
        results['reverse_translated_text'] = f_reverse_translation(
            translated_text, source_lang=target_lang, target_lang=source_lang
        )
    
    # Better逆翻訳
    if better_translation:
        results['reverse_better_translation'] = f_reverse_translation(
            better_translation, source_lang=target_lang, target_lang=source_lang
        )
    
    # Gemini逆翻訳
    if gemini_translation:
        results['gemini_reverse_translation'] = f_reverse_translation(
            gemini_translation, source_lang=target_lang, target_lang=source_lang
        )
    
    return results

# 🆕 Phase C-2: 従来ユーザー設定復元機能
def restore_legacy_user_settings():
    """従来ユーザーの保存済み設定を復元"""
    # 言語設定の復元（セッションに保存済みの場合）
    if 'saved_language' in session and 'temp_lang_override' not in session:
        session['lang'] = session['saved_language']
    
    # 一時的な言語切り替えフラグをクリア
    session.pop('temp_lang_override', None)
    
    # ユーザープリファレンスの復元（データベースから）
    user_id = get_current_user_id()
    if user_id and user_id != 'anonymous':
        try:
            # ここでユーザー設定をデータベースから読み込む処理を追加可能
            pass
        except Exception as e:
            app_logger.error(f"Failed to restore user settings: {e}")

# 🆕 Phase 2.8.5: Gemini 3-way comparison analysis with recommendation focus
def f_gemini_3way_analysis(translated_text, better_translation, gemini_translation):
    """
    Gemini APIを使用した3つの翻訳の比較分析（Phase 3で分離予定）
    """
    if not gemini_api_key:
        return "Gemini APIが設定されていません"
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 分析プロンプト
        prompt = f"""
        以下の3つの翻訳を分析し、それぞれの特徴を簡潔に説明してください。
        
        1. ChatGPT翻訳: {translated_text}
        2. Enhanced翻訳: {better_translation}
        3. Gemini翻訳: {gemini_translation}
        
        分析項目（各50文字以内）:
        - 自然さ: 最も自然な翻訳はどれか
        - 正確性: 意味の正確さの比較
        - 流暢さ: 読みやすさの評価
        - 推奨: どの翻訳が最適か、理由と共に
        
        簡潔に、ビジネス向けの分析として出力してください。
        """
        
        response = model.generate_content(prompt)
        analysis_text = response.text.strip()
        
        # 🔧 Phase B-2.9: 推奨結果の抽出と保存
        try:
            # extract_recommendation_from_analysis を使用
            recommendation_data = extract_recommendation_from_analysis(analysis_text)
            
            # recommendation_dataの構造:
            # {
            #   'recommended_engine': 'chatgpt' | 'enhanced' | 'gemini',
            #   'confidence': 85,
            #   'strength': 'strong' | 'moderate' | 'weak',
            #   'reasons': ['理由1', '理由2']
            # }
            
            # Flaskセッションへの保存（認証ユーザーのみ）
            if session.get('logged_in'):
                session['last_recommendation'] = recommendation_data
                
                # 🆕 Task 2.9.2 Phase B-3.5.10: 活動ログに推奨エンジンを記録
                if activity_logger:
                    try:
                        log_analysis_activity({
                            'analysis_type': 'gemini_3way',
                            'recommended_engine': recommendation_data.get('recommended_engine', 'unknown'),
                            'confidence': recommendation_data.get('confidence', 0),
                            'strength': recommendation_data.get('strength', 'unknown'),
                            'reasons': recommendation_data.get('reasons', [])
                        })
                    except Exception as log_error:
                        app_logger.error(f"Activity logging failed: {log_error}")
                
            # デバッグ用ログ
            app_logger.info(f"Recommendation extracted: {recommendation_data.get('recommended_engine', 'none')} "
                          f"(confidence: {recommendation_data.get('confidence', 0)}%)")
                          
        except Exception as extraction_error:
            app_logger.error(f"Recommendation extraction failed: {extraction_error}")
            # エラーが発生しても分析テキストは返す
        
        return analysis_text
        
    except Exception as e:
        app_logger.error(f"Gemini 3-way analysis error: {str(e)}")
        
        # Geminiエラー時のフォールバック分析
        try:
            # 簡易的な比較ロジック
            analysis = "【自動分析】\n"
            
            # 長さ比較
            lengths = {
                'ChatGPT': len(translated_text or ''),
                'Enhanced': len(better_translation or ''),
                'Gemini': len(gemini_translation or '')
            }
            
            # 最も短い翻訳を簡潔として評価
            shortest = min(lengths.items(), key=lambda x: x[1] if x[1] > 0 else float('inf'))
            analysis += f"• 簡潔性: {shortest[0]}が最も簡潔\n"
            
            # デフォルト推奨
            analysis += "• 推奨: Enhanced翻訳（バランスが良い）\n"
            analysis += "\n※ Gemini APIエラーのため簡易分析を表示"
            
            return analysis
            
        except:
            return "翻訳の比較分析中にエラーが発生しました"

# LangPontTranslationExpertAI_Remaining: 旧app.py残存メソッドのみ
class LangPontTranslationExpertAI_Remaining:
    """
    Phase 3c-2の残りメソッド（将来的に移行予定）
    注: メインのLangPontTranslationExpertAIはtranslation/expert_ai.pyに移行済み
    """
    
    def __init__(self, claude_client):
        self.claude_client = claude_client
        self.expert_ai = LangPontTranslationExpertAI(claude_client)
    
    def process_question(self, question, context):
        """質問処理の委譲"""
        return self.expert_ai.process_question(question, context)
    
    def _get_complete_translation_context(self, additional_context=None):
        """
        翻訳コンテキストの完全な取得（Flask sessionへの依存削除）
        Step3: SessionContextAdapterを使用
        """
        from translation.adapters import SessionContextAdapter
        
        try:
            # SessionContextAdapterを使用してコンテキスト取得
            adapter = SessionContextAdapter()
            context = adapter.get_translation_context()
            
            # 追加コンテキストのマージ
            if additional_context:
                context.update(additional_context)
            
            return context
            
        except Exception as e:
            app_logger.error(f"Failed to get translation context: {e}")
            return {}

# エキスパートAIのインスタンス化
interactive_processor = LangPontTranslationExpertAI_Remaining(claude_client)

# ルーティング

@app.route("/login", methods=["GET", "POST"])
def login():
    lang = request.args.get("lang", session.get("lang", "jp"))
    if lang not in ["jp", "en", "fr", "es"]:
        lang = "jp"
    session["lang"] = lang
    label = labels.get(lang, labels["jp"])

    if request.method == "POST":
        password = request.form.get("password", "")
        
        # 認証システムを使用した検証
        auth_result = check_password(password)
        
        if auth_result:
            # 認証成功
            session["logged_in"] = True
            session["login_time"] = datetime.now().isoformat()
            
            # ユーザー情報の設定
            user_info = get_user_info()
            session["username"] = user_info.get('username', 'user')
            session["user_role"] = user_info.get('user_role', 'user')
            
            # 🆕 SL-2.1: Redis同期（利用可能な場合）
            if session_redis_manager and getattr(session, 'session_id', None):
                try:
                    session_redis_manager.sync_auth_to_redis(
                        session_id=session.session_id,
                        auth_data={
                            'logged_in': True,
                            'username': session["username"],
                            'user_role': session["user_role"],
                            'login_time': session["login_time"]
                        }
                    )
                    app_logger.info(f"✅ SL-2.1: Auth data synced to Redis for user: {session['username']}")
                except Exception as e:
                    app_logger.warning(f"⚠️ SL-2.1: Redis auth sync failed: {e}")
            
            # 管理者権限チェック
            if session["user_role"] in ["admin", "developer"]:
                session["is_admin"] = True
            
            # アクティビティログ
            log_user_activity("login", f"User {session['username']} logged in")
            log_access_event(f"User {session['username']} logged in successfully")
            log_security_event('LOGIN_SUCCESS', f'User: {session["username"]}', 'INFO')
            
            # Task #9-4 AP-1 Phase 4 Step3: ui_state設定
            session['ui_state'] = 'clean'  # ログイン直後はクリーンな状態
            
            return redirect(url_for("index"))
        else:
            # 認証失敗
            log_security_event('LOGIN_FAILED', 'Invalid password attempt', 'WARNING')
            error_message = label.get("login_error", "パスワードが正しくありません")
            return render_template("login.html", 
                                 error=error_message, 
                                 labels=label,
                                 version_info=VERSION_INFO)

    return render_template("login.html", 
                         labels=label,
                         version_info=VERSION_INFO)

@app.route("/test")
def test():
    try:
        # テスト用のレスポンス
        test_data = {
            "status": "OK",
            "timestamp": datetime.now().isoformat(),
            "environment": ENVIRONMENT,
            "features": FEATURES,
            "session_active": session.get("logged_in", False),
            "user": session.get("username", "anonymous")
        }
        
        # テスト用ログ
        app_logger.info("Test endpoint accessed")
        
        return jsonify(test_data)

    except Exception as e:
        return f"<h1>デバッグエラー</h1><pre>{str(e)}</pre>"

@app.route("/", methods=["GET", "POST"])
@csrf_protect
@require_rate_limit
def index():
    # 🆕 Task#9-4 AP-1 Ph4 Step4（再挑戦）- OL-0: GET /ルート監視開始
    data_flow_logger.log_data_flow(
        "ROUTE",
        "INDEX_START",
        {
            "method": request.method,
            "logged_in": session.get("logged_in", False),
            "session_keys": list(session.keys()),
            "lang": session.get("lang", "jp")
        }
    )

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
    else:
        # POSTリクエスト時のみ既存の履歴を取得
        chat_history = session.get("chat_history", [])

    # 使用状況を取得
    client_id = get_client_id()
    usage_status = get_usage_status(client_id)

    if request.method == "POST":
        # 🆕 P1修正: reset処理は削除（/api/resetに統一）
        # if request.form.get("reset") == "true": の処理を削除
        
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
                        f'Field: {field_name}, Error: {error_msg}',
                        'WARNING'
                    )
                    # エラーメッセージを設定してレンダリング
                    return render_template(
                        "index.html",
                        error_message=error_msg,
                        japanese_text=japanese_text,
                        partner_message=partner_message,
                        context_info=context_info,
                        language_pair=language_pair,
                        labels=label,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        version_info=VERSION_INFO
                    )

    # テンプレートレンダリング用にチャット履歴を再取得（削除済みも考慮）
    chat_history = session.get("chat_history", [])

    # 🆕 Task#9-4 AP-1 Ph4 Step4（再挑戦）- OL-0: GET /ルート監視終了
    data_flow_logger.log_data_flow(
        "ROUTE",
        "INDEX_END",
        {
            "method": request.method,
            "language_pair": language_pair,
            "has_translation": bool(translated_text),
            "ui_state": "clean" if request.method == "GET" else "working",
            "response_size": len(str(japanese_text) + str(translated_text))
        }
    )

    return render_template(
        "index.html",
        japanese_text=japanese_text,
        translated_text=translated_text,
        reverse_translated_text=reverse_translated_text,
        better_translation=better_translation,
        reverse_better_translation=reverse_better_text,
        language_pair=language_pair,
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

# 🆕 P1: 専用リセットエンドポイント
@app.route("/api/reset", methods=["POST"])
@csrf_protect
@require_rate_limit
def api_reset():
    """翻訳データの完全リセット"""
    # 🆕 Task#9-4 AP-1 Ph4 Step4（再挑戦）- OL-0: POST /api/reset 監視開始
    data_flow_logger.log_data_flow(
        "ROUTE",
        "API_RESET_START",
        {
            "session_keys_before": list(session.keys()),
            "session_id": session.get("session_id", "unknown")[:16] if session.get("session_id") else "unknown"
        }
    )
    
    # 完全なセッションクリア
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
    ]
    
    for key in translation_keys_to_clear:
        session.pop(key, None)
    
    # TranslationStateManagerのクリア
    session_id = getattr(session, 'session_id', None) or session.get("session_id") or session.get("csrf_token", "")[:16]
    if translation_state_manager and session_id:
        translation_state_manager.clear_context_data(session_id)
    
    log_access_event('API reset executed - all translation data cleared')
    
    # 🆕 Task#9-4 AP-1 Ph4 Step4（再挑戦）- OL-0: POST /api/reset 監視終了
    data_flow_logger.log_data_flow(
        "ROUTE",
        "API_RESET_COMPLETE",
        {
            "keys_cleared": len(translation_keys_to_clear),
            "session_keys_after": list(session.keys()),
            "state_manager_cleared": translation_state_manager is not None,
            "ui_state": "clean"
        }
    )
    
    # ui_stateをcleanに設定
    session['ui_state'] = 'clean'
    
    return jsonify({
        "success": True,
        "message": "Translation data cleared successfully"
    })

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
    # 言語設定をデフォルトに戻す
    session["lang"] = "jp"
    # 保存済み言語設定もクリア
    session.pop('saved_language', None)
    session.pop('temp_lang_override', None)
    
    log_access_event('Language reset to default')
    return redirect(url_for("index"))

# 🆕 SL-3 Phase 3: API経由での翻訳状態取得エンドポイント
@app.route("/api/get_translation_state", methods=["GET"])
# @csrf_protect  # 🔧 Phase 3c-4: Temporarily disabled for comprehensive testing
# @require_rate_limit  # 🔧 Phase 3c-4: Temporarily disabled for comprehensive testing
def get_translation_state_api():
    """
    翻訳状態をAPIで取得（クライアントサイド用）
    注: セッションから値を返す場合と、StateManagerから値を返す場合がある
    """
    try:
        field_name = request.args.get('field')
        default_value = request.args.get('default', '')
        
        # まずセッションから取得を試行
        if field_name:
            value = session.get(field_name, None)
            if value is not None:
                return jsonify({
                    "success": True,
                    "field": field_name,
                    "value": value,
                    "source": "session"
                })
        
        # StateManagerが利用可能な場合はRedisから取得
        if not translation_state_manager:
            return jsonify({
                "success": False,
                "error": "Translation state manager not available"
            })
        
        session_id = getattr(session, 'session_id', None) or session.get("session_id") or session.get("csrf_token", "")[:16] or f"trans_{int(time.time())}"
        
        if field_name:
            # 特定のフィールドを取得
            if field_name in translation_state_manager.CACHE_KEYS:
                value = translation_state_manager.get_translation_state(session_id, field_name, default_value)
            else:
                value = translation_state_manager.get_large_data(field_name, session_id) or default_value
            
            return jsonify({
                "success": True,
                "field": field_name,
                "value": value,
                "source": "redis"
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
        
        # フィールドタイプに応じた保存
        if field in translation_state_manager.CACHE_KEYS:
            success = translation_state_manager.set_translation_state(session_id, field, value)
        else:
            success = translation_state_manager.save_large_data(field, value, session_id)
        
        if success:
            app_logger.info(f"✅ SL-3 Phase 3: State saved - field: {field}, session: {session_id[:16]}...")
            return jsonify({
                "success": True,
                "field": field,
                "session_id": session_id
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to save state"
            })
            
    except Exception as e:
        app_logger.error(f"❌ SL-3 Phase 3: set_translation_state error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# 🆕 Phase C-1: 統合分析関数（Geminiの3-way分析とClaudeの深層分析を統合）
# Phase B-4で分離済み（AnalysisEngineManagerに移行）
# ここではanalysis_engine_managerのインスタンス化のみ

# 🆕 Task #9-3 AP-1 Phase 3: AnalysisEngineManager初期化
analysis_engine_manager = AnalysisEngineManager(claude_client, app_logger, f_gemini_3way_analysis)  # 🔧 修正: client → claude_client

# 🆕 Task #9-3 AP-1 Phase 3: AnalysisService初期化
try:
    from services.analysis_service import AnalysisService
    analysis_service = AnalysisService(
        translation_state_manager=translation_state_manager,
        analysis_engine_manager=analysis_engine_manager,
        claude_client=claude_client,  # 🔧 修正: client → claude_client
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

# 🆕 P2修正: /api/debug_log エンドポイントの防御強化
@app.route("/api/debug_log", methods=["POST"])
# CSRFはスキップ（クライアントサイドログ用）
@require_rate_limit  # レート制限適用
def receive_debug_log():
    """クライアントからのデバッグログを受信"""
    
    # P2: 開発環境限定
    if ENVIRONMENT == "production":
        return jsonify({"success": False, "message": "Not available in production"}), 403
    
    try:
        log_data = request.get_json() or {}
        
        # P2: サイズ制限（app.configで16MB設定済み）
        # P2: 再マスキング（念のため）
        if 'dataPreview' in log_data:
            log_data['dataPreview'] = data_flow_logger.mask_sensitive_data(
                str(log_data['dataPreview'])[:100]
            )
        
        # ログをサーバー側に記録（デフォルトOFFのため、enabled時のみ動作）
        data_flow_logger.log_data_flow(
            "CLIENT_LOG",
            log_data.get('operation', 'UNKNOWN'),
            log_data,
            client_req_id=log_data.get('reqId', 'unknown')
        )
        
        return jsonify({"success": True})
        
    except Exception as e:
        app_logger.error(f"❌ Debug log reception failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# 🆕 Task #9 AP-1: TranslationService初期化と翻訳Blueprint登録
try:
    from services.translation_service import TranslationService
    
    # 翻訳履歴管理関数の定義
    def save_to_history(data):
        """翻訳履歴保存ヘルパー"""
        try:
            save_translation_history(
                user_id=get_current_user_id(),
                source_text=data.get('source_text', ''),
                source_lang=data.get('source_lang', ''),
                target_lang=data.get('target_lang', ''),
                translated_text=data.get('translated_text', ''),
                engine=data.get('engine', 'chatgpt')
            )
        except Exception as e:
            app_logger.error(f"History save error: {e}")
    
    # TranslationService初期化
    translation_service = TranslationService(
        openai_client=client,
        logger=app_logger,
        labels=labels,
        usage_checker=check_daily_usage,
        translation_state_manager=translation_state_manager
    )
    
    app_logger.info("✅ Task #9 AP-1: TranslationService initialized successfully")
    
    # Translation Blueprint登録
    from routes.translation import init_translation_routes
    
    history_manager = {
        'save': save_to_history,
        'context_save': lambda data: TranslationContext.save_context(data),
        'context_get': lambda: TranslationContext.get_context()
    }
    
    translation_bp = init_translation_routes(
        service=translation_service,
        usage_check_func=check_daily_usage,
        history_mgr=history_manager,
        app_logger=app_logger,
        app_labels=labels
    )
    
    app.register_blueprint(translation_bp)
    app_logger.info("✅ Task #9 AP-1: Translation Blueprint registered successfully")
    
except ImportError as e:
    app_logger.error(f"❌ Task #9 AP-1: TranslationService import failed: {e}")
    translation_service = None

if __name__ == "__main__":
    # 🎯 Phase B1: 友人推奨のシンプル設定（8080ポート競合問題解決）
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=False,          # 友人推奨: 本番環境設定
        use_reloader=False,   # 友人推奨: 子プロセス防止
        threaded=True
    )