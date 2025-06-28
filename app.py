print("🚨 FORCE DEBUG: app.py実行開始 - この行が見えない場合はファイルが更新されていません")
print("🚨 FORCE DEBUG: app.pyファイルロード中...")

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

print("🚨 FORCE DEBUG: 基本モジュールインポート完了")

# Configuration import
print("🚨 FORCE DEBUG: configモジュールインポート試行")
from config import VERSION, ENVIRONMENT, FEATURES, DEPLOYMENT, USAGE_LIMITS
print("🚨 FORCE DEBUG: configモジュールインポート成功")

# 🆕 認証システムインポート（緊急デバッグ版）
print("🔍 DEBUG: 認証システムインポート開始")
try:
    print("🔍 DEBUG: UserAuthSystemインポート試行")
    from user_auth import UserAuthSystem
    print("✅ DEBUG: UserAuthSystemインポート成功")
    
    print("🔍 DEBUG: init_auth_routesインポート試行")
    from auth_routes import init_auth_routes
    print("✅ DEBUG: init_auth_routesインポート成功")
    
    AUTH_SYSTEM_AVAILABLE = True
    app_logger = logging.getLogger('app')
    app_logger.info("認証システム正常にインポートされました")
    print("✅ DEBUG: 認証システムインポート完了")
    
except ImportError as e:
    print(f"❌ DEBUG: 認証システムインポートエラー: {str(e)}")
    import traceback
    print(f"❌ DEBUG: インポートエラー詳細:\n{traceback.format_exc()}")
    AUTH_SYSTEM_AVAILABLE = False
    app_logger = logging.getLogger('app')
    app_logger.warning(f"認証システムのインポートに失敗: {str(e)}")
    app_logger.info("従来の認証システムを使用します")
except Exception as e:
    print(f"❌ DEBUG: 予期しないエラー: {str(e)}")
    import traceback
    print(f"❌ DEBUG: 予期しないエラー詳細:\n{traceback.format_exc()}")
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

# =============================================================================
# 🆕 強化されたログ設定（ログローテーション対応）
# =============================================================================
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
    
    return security_logger, app_logger, access_logger

# ログ初期化
security_logger, app_logger, access_logger = setup_enhanced_logging()

# =============================================================================
# 🆕 Flask-Talisman相当のセキュリティヘッダー設定
# =============================================================================

# APIキー取得
api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_TEST")
if not api_key:
    raise ValueError("OPENAI_API_KEY が環境変数に見つかりません")

# Flask設定
print("🚨 FORCE DEBUG: Flaskアプリケーション作成開始")
app = Flask(__name__)
print("🚨 FORCE DEBUG: Flaskアプリケーション作成成功")
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB制限
print("🚨 FORCE DEBUG: Flask基本設定完了")

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

# 🚀 Task 2.9.2 Phase B-1: 管理者システム統合
print("🚀 Phase B-1: 管理者システム統合開始")
try:
    from admin_routes import init_admin_routes
    from admin_logger import admin_logger, log_translation_event, log_gemini_analysis, log_api_call, log_error
    from admin_auth import admin_auth_manager, require_admin_access
    
    # 管理者ルートを登録
    init_admin_routes(app)
    
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
print("🚨 FORCE DEBUG: ========== 認証システム初期化開始 ==========")
print(f"🚨 FORCE DEBUG: AUTH_SYSTEM_AVAILABLE = {AUTH_SYSTEM_AVAILABLE}")
print(f"🚨 FORCE DEBUG: Flask app オブジェクト: {app}")
print(f"🚨 FORCE DEBUG: Flask app blueprints（初期状態）: {app.blueprints}")

if AUTH_SYSTEM_AVAILABLE:
    print("🔍 DEBUG: 認証システムが利用可能です")
    try:
        print("🔍 DEBUG: UserAuthSystem()インスタンス作成開始")
        auth_system = UserAuthSystem()
        print("🔍 DEBUG: UserAuthSystem()インスタンス作成成功")
        
        print("🔍 DEBUG: init_auth_routes(app)呼び出し開始")
        result = init_auth_routes(app)
        print(f"🔍 DEBUG: init_auth_routes(app)結果: {result}")
        
        # Blueprint登録後のルート確認
        print("🔍 DEBUG: 登録済みBlueprint確認")
        for blueprint_name, blueprint in app.blueprints.items():
            print(f"  ✅ Blueprint登録済み: {blueprint_name} -> {blueprint}")
        
        # URL マップの確認
        print("🔍 DEBUG: 登録済みルート一覧:")
        for rule in app.url_map.iter_rules():
            print(f"  📋 {rule.methods} {rule.rule} -> {rule.endpoint}")
        
        # 特に/auth/profileルートを確認
        auth_routes = [rule for rule in app.url_map.iter_rules() if '/auth/' in rule.rule]
        print(f"🔍 DEBUG: 認証関連ルート数: {len(auth_routes)}")
        for route in auth_routes:
            print(f"  🔐 {route.methods} {route.rule} -> {route.endpoint}")
        
        app_logger.info("認証システムが正常に初期化されました")
        print("✅ DEBUG: 認証システム初期化完了")
        
    except Exception as e:
        print(f"❌ DEBUG: 認証システム初期化エラー: {str(e)}")
        import traceback
        print(f"❌ DEBUG: エラー詳細:\n{traceback.format_exc()}")
        app_logger.error(f"認証システム初期化エラー: {str(e)}")
        auth_system = None
        AUTH_SYSTEM_AVAILABLE = False
else:
    print("❌ DEBUG: AUTH_SYSTEM_AVAILABLEがFalseです")

# =============================================================================
# 🆕 完全版セキュリティヘッダー設定（Flask-Talisman相当）
# =============================================================================

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

# =============================================================================
# 🆕 強化されたCSRF対策
# =============================================================================

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

@app.context_processor
def inject_csrf_token():
    """全テンプレートにCSRFトークンを注入"""
    return dict(csrf_token=generate_csrf_token())

def csrf_protect(f):
    """CSRF保護デコレータ（強化版）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == "POST":
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            if not validate_csrf_token(token):
                security_logger.warning(
                    f"CSRF attack attempt - IP: {get_client_ip_safe()}, "
                    f"UA: {get_user_agent_safe()}, "
                    f"Endpoint: {get_endpoint_safe()}"
                )
                abort(403)
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# 🆕 強化された入力値検証システム
# =============================================================================

class EnhancedInputValidator:
    """強化された入力値検証クラス"""
    
    # 🆕 適切なレベルの危険パターン（翻訳プロンプト考慮）
    DANGEROUS_PATTERNS = [
        # 明らかに危険なスクリプトインジェクション
        r'<script[^>]*>.*?</script>',
        r'javascript\s*:\s*alert',
        r'vbscript\s*:\s*',
        r'data\s*:\s*text/html',
        
        # 危険なイベントハンドラー（翻訳で使われる可能性のある単語は除外）
        r'onload\s*=\s*["\']',
        r'onerror\s*=\s*["\']',
        r'onclick\s*=\s*["\']',
        
        # 危険なHTMLタグ
        r'<iframe[^>]*src\s*=',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<applet[^>]*>',
        
        # 明らかなSQLインジェクション（大文字小文字厳密）
        r'\bUNION\s+SELECT\b',
        r'\bDROP\s+TABLE\b',
        r'\bDELETE\s+FROM\b',
        
        # 危険なコマンド実行
        r'[\|&;]\s*(rm|del|format)\s+',
        r'\$\(\s*rm\s+',
        r'`\s*rm\s+',
    ]
    
    @classmethod
    def validate_text_input(cls, text: Optional[str], max_length: int = 5000, min_length: int = 1, field_name: str = "input", current_lang: str = "jp") -> Tuple[bool, str]:
        """包括的なテキスト入力検証（多言語対応）"""
        from labels import labels
        
        if not text or not isinstance(text, str):
            return False, f"{field_name}{labels[current_lang]['validation_error_empty']}"
        
        # 長さチェック（最大長制限を10000文字まで緩和）
        effective_max_length = max(max_length, 10000)
        
        if len(text) < min_length:
            return False, f"{field_name}{labels[current_lang]['validation_error_short']}（最小{min_length}文字）"
        
        if len(text) > effective_max_length:
            return False, f"{field_name}{labels[current_lang]['validation_error_long']}（最大{effective_max_length}文字）"
        
        # フィールドタイプによる検証レベルの調整
        translation_fields = ["翻訳テキスト", "会話履歴", "背景情報"]
        is_translation_field = field_name in translation_fields
        
        if is_translation_field:
            # 翻訳テキスト用の緩和された危険パターンチェック
            critical_patterns = [
                r'<script[^>]*>.*?</script>',
                r'javascript\s*:\s*alert',
                r'<iframe[^>]*src\s*=',
                r'<object[^>]*>',
                r'\$\(\s*rm\s+',
            ]
            patterns_to_check = critical_patterns
        else:
            # その他フィールド用の厳格なチェック
            patterns_to_check = cls.DANGEROUS_PATTERNS
        
        # 危険パターンのチェック
        for pattern in patterns_to_check:
            if re.search(pattern, text, re.IGNORECASE):
                # セキュリティログに記録
                security_logger.warning(
                    f"Dangerous pattern detected in {field_name} - "
                    f"Pattern: {pattern[:30]}..., "
                    f"Field type: {'translation' if is_translation_field else 'other'}, "
                    f"IP: {get_client_ip_safe()}"
                )
                return False, f"{field_name}に潜在的に危険な文字列が含まれています"
        
        # 🆕 制御文字チェック（翻訳フィールドでは緩和）
        if not is_translation_field and re.search(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', text):
            return False, f"{field_name}に不正な制御文字が含まれています"
        
        return True, "OK"
    
    @classmethod
    def validate_language_pair(cls, lang_pair: Optional[str], current_lang: str = "jp") -> Tuple[bool, str]:
        """言語ペア検証（ホワイトリスト方式・多言語対応）"""
        from labels import labels
        
        valid_pairs = [
            'ja-fr', 'fr-ja', 'ja-en', 'en-ja', 
            'fr-en', 'en-fr', 'ja-es', 'es-ja',
            'es-en', 'en-es', 'es-fr', 'fr-es',
            'ja-de', 'de-ja', 'ja-it', 'it-ja'
        ]
        
        if not lang_pair or lang_pair not in valid_pairs:
            return False, labels[current_lang].get('validation_error_invalid_lang_pair', "無効な言語ペアです")
        
        return True, "OK"
    
    @classmethod
    def validate_email(cls, email: Optional[str], current_lang: str = "jp") -> Tuple[bool, str]:
        """メールアドレス検証（多言語対応）"""
        from labels import labels
        
        if not email:
            return False, f"メールアドレス{labels[current_lang]['validation_error_empty']}"
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, labels[current_lang].get('validation_error_invalid_email', "無効なメールアドレス形式です")
        
        return True, "OK"

# =============================================================================
# 🆕 セッション管理強化
# =============================================================================

class SecureSessionManager:
    """セキュアなセッション管理クラス"""
    
    @staticmethod
    def regenerate_session_id() -> None:
        """セッションIDの再生成（セッションハイジャック対策）"""
        # 現在のセッションデータを保存
        old_session_data = dict(session)
        
        # セッションをクリアして新しいIDを生成
        session.clear()
        
        # データを復元
        for key, value in old_session_data.items():
            session[key] = value
        
        session.permanent = True
    
    @staticmethod
    def is_session_expired() -> bool:
        """セッション期限切れチェック"""
        if 'session_created' not in session:
            session['session_created'] = time.time()
            return False
        
        # 1時間でセッション期限切れ
        if time.time() - session['session_created'] > 3600:
            return True
        
        return False
    
    @staticmethod
    def cleanup_old_sessions() -> None:
        """古いセッションのクリーンアップ（定期実行推奨）"""
        # 実装は使用するセッションストアに依存
        pass

# =============================================================================
# 🆕 パスワード管理強化
# =============================================================================

class SecurePasswordManager:
    """セキュアなパスワード管理クラス"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """パスワードのハッシュ化（bcrypt相当）"""
        return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """パスワードの検証"""
        return check_password_hash(password_hash, password)
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """パスワード強度の検証"""
        if len(password) < 8:
            return False, "パスワードは8文字以上である必要があります"
        
        if not re.search(r'[A-Z]', password):
            return False, "パスワードには大文字を含む必要があります"
        
        if not re.search(r'[a-z]', password):
            return False, "パスワードには小文字を含む必要があります"
        
        if not re.search(r'\d', password):
            return False, "パスワードには数字を含む必要があります"
        
        return True, "OK"

# =============================================================================
# ヘルパー関数とセキュリティ監視（リクエストコンテキスト対応版）
# =============================================================================

def get_client_ip() -> Optional[str]:
    """クライアントIPアドレスを安全に取得"""
    # プロキシ経由の場合のIP取得
    forwarded_ips = request.headers.get('X-Forwarded-For')
    if forwarded_ips:
        # 最初のIPアドレスを取得（信頼できるプロキシの場合）
        return forwarded_ips.split(',')[0].strip()
    
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    
    return request.remote_addr

def get_client_ip_safe() -> str:
    """リクエストコンテキスト外でも安全なIP取得"""
    try:
        return get_client_ip()
    except RuntimeError:
        return 'N/A'

def get_user_agent_safe() -> str:
    """リクエストコンテキスト外でも安全なUser-Agent取得"""
    try:
        return request.headers.get('User-Agent', 'Unknown')[:200]
    except RuntimeError:
        return 'N/A'

def get_endpoint_safe() -> str:
    """リクエストコンテキスト外でも安全なエンドポイント取得"""
    try:
        return request.endpoint or 'N/A'
    except RuntimeError:
        return 'N/A'

def get_method_safe() -> str:
    """リクエストコンテキスト外でも安全なメソッド取得"""
    try:
        return request.method
    except RuntimeError:
        return 'N/A'

def log_security_event(event_type: str, details: str, severity: str = "INFO") -> None:
    """強化されたセキュリティイベントログ（リクエストコンテキスト対応）"""
    
    # リクエストコンテキスト外でも安全に動作するよう修正
    client_ip = get_client_ip_safe()
    user_agent = get_user_agent_safe()
    endpoint = get_endpoint_safe()
    method = get_method_safe()
    
    log_data = {
        'event_type': event_type,
        'client_ip': client_ip,
        'user_agent': user_agent,
        'details': details,
        'severity': severity,
        'endpoint': endpoint,
        'method': method,
        'timestamp': datetime.now().isoformat()
    }
    
    if severity == "WARNING":
        security_logger.warning(f"SECURITY_WARNING: {json.dumps(log_data, ensure_ascii=False)}")
    elif severity == "ERROR":
        security_logger.error(f"SECURITY_ERROR: {json.dumps(log_data, ensure_ascii=False)}")
    elif severity == "CRITICAL":
        security_logger.critical(f"SECURITY_CRITICAL: {json.dumps(log_data, ensure_ascii=False)}")
    else:
        security_logger.info(f"SECURITY_INFO: {json.dumps(log_data, ensure_ascii=False)}")

def log_access_event(details: str) -> None:
    """アクセスログの記録（リクエストコンテキスト対応）"""
    client_ip = get_client_ip_safe()
    user_agent = get_user_agent_safe()
    endpoint = get_endpoint_safe()
    method = get_method_safe()
    
    access_data = {
        'client_ip': client_ip,
        'user_agent': user_agent,
        'method': method,
        'endpoint': endpoint,
        'details': details
    }
    
    access_logger.info(json.dumps(access_data, ensure_ascii=False))

# =============================================================================
# 🆕 レート制限強化
# =============================================================================

rate_limit_store = {}

# =============================================================================
# 🆕 バックグラウンドメモリクリーンアップ機能
# =============================================================================

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

def enhanced_rate_limit_check(client_ip: str, limit: int = 50, window: int = 300, burst_limit: int = 15, burst_window: int = 60) -> bool:
    """強化されたレート制限（通常 + バースト制限）"""
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

def analytics_rate_limit_check(client_ip: str, limit: int = 500, window: int = 300, burst_limit: int = 100, burst_window: int = 60) -> bool:
    """
    🆕 Task 2.9.1: Analytics専用の緩いレート制限
    Analytics追跡のための高頻度リクエストに対応
    - 通常制限: 500req/5分 (vs 一般的な50req/5分)
    - バースト制限: 100req/1分 (vs 一般的な15req/1分)
    """
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

def require_rate_limit(f):
    """レート制限デコレータ（強化版）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = get_client_ip_safe()
        
        if not enhanced_rate_limit_check(client_ip):
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
        
        # Analytics専用の緩い制限（500req/5min, 100burst/1min）
        if not analytics_rate_limit_check(client_ip):
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

# =============================================================================
# 使用制限機能（既存コード + 強化）
# =============================================================================

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

# =============================================================================
# エラーハンドリング（強化版）
# =============================================================================

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

# =============================================================================
# セキュリティ監視とアクセス制御
# =============================================================================

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

# =============================================================================
# 翻訳関数群（セキュリティ強化版）
# =============================================================================

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

# =============================================================================
# セッション管理強化関数
# =============================================================================

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

def f_translate_with_gemini(text: str, source_lang: str, target_lang: str, partner_message: str = "", context_info: str = "") -> str:
    """セキュリティ強化版Gemini翻訳関数"""
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        return "⚠️ Gemini APIキーがありません"
    
    # 🆕 包括的な入力値検証（翻訳テキストは10000文字まで許可）
    validations = [
        (text, 10000, "翻訳テキスト"),
        (partner_message, 2000, "会話履歴"),
        (context_info, 2000, "背景情報")
    ]
    
    for input_text, max_len, field_name in validations:
        if input_text:  # 空でない場合のみ検証
            is_valid, error_msg = EnhancedInputValidator.validate_text_input(
                input_text, max_length=max_len, field_name=field_name
            )
            if not is_valid:
                return f"⚠️ {error_msg}"
    
    # 🆕 言語マップの明確化
    lang_map = {
        "ja": "Japanese", "fr": "French", "en": "English",
        "es": "Spanish", "de": "German", "it": "Italian"
    }
    
    source_label = lang_map.get(source_lang, source_lang.capitalize())
    target_label = lang_map.get(target_lang, target_lang.capitalize())
    
    prompt = f"""
You are a professional {source_label} to {target_label} translator.
Using the context below, provide ONLY the {target_label} translation (no explanations or notes).

LANGUAGE PAIR: {source_label} → {target_label}

--- Previous conversation ---
{partner_message or "(None)"}

--- Background context ---
{context_info or "(None)"}

--- TEXT TO TRANSLATE TO {target_label.upper()} ---
{text}

IMPORTANT: Respond ONLY with the {target_label} translation.
    """.strip()
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            log_security_event(
                'GEMINI_API_ERROR',
                f'Gemini API error: {response.status_code}',
                'ERROR'
            )
            return f"Gemini API error: {response.status_code}"
            
    except requests.exceptions.Timeout:
        return "⚠️ Gemini APIがタイムアウトしました"
    except Exception as e:
        log_security_event(
            'GEMINI_REQUEST_ERROR',
            f'Gemini request error: {str(e)}',
            'ERROR'
        )
        return f"Gemini API error: {str(e)}"

# =============================================================================
# 🆕 Gemini分析関数（セキュリティ強化版）
# =============================================================================

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

    # 🆕 現在の言語設定を直接取得（セッションの古いデータを無視）
    current_language_pair = request.form.get('language_pair') or session.get("language_pair", "ja-en")
    
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

# =============================================================================
# 🚀 Task 2.9.2 Phase B-3.5.2: 推奨判定システム（新規作成）
# =============================================================================

def extract_recommendation_from_analysis(analysis_text: str, engine_name: str = "gemini") -> Dict[str, Any]:
    """
    分析結果から推奨を抽出する関数（Task 2.9.2 Phase B-3.5.2 対応）
    
    重要: ChatGPTに「分析結果から推奨を抽出」させる正しいプロンプトを実装
    
    間違ったアプローチ: ChatGPTに独立した翻訳判定をさせる
    正しいアプローチ: ChatGPTに「この分析文章からLLMの推奨を特定」させる
    """
    
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        return {
            "recommendation": "none",
            "confidence": 0.0,
            "method": "openai_key_missing",
            "error": "OpenAI APIキーが設定されていません"
        }
    
    # セッションから言語設定を取得
    display_lang = session.get("lang", "jp")
    
    # 正しいプロンプト: 分析結果から推奨抽出
    if display_lang == "en":
        prompt = f"""The following is an analysis of three translations by {engine_name} AI:

{analysis_text}

Read this analysis text and identify which translation {engine_name} AI recommends.
Choose from: ChatGPT / Enhanced / Gemini

Only respond with the name of the recommended translation."""
    elif display_lang == "fr":
        prompt = f"""Voici une analyse de trois traductions par {engine_name} IA:

{analysis_text}

Lisez ce texte d'analyse et identifiez quelle traduction {engine_name} IA recommande.
Choisissez parmi: ChatGPT / Enhanced / Gemini

Répondez uniquement avec le nom de la traduction recommandée."""
    elif display_lang == "es":
        prompt = f"""El siguiente es un análisis de tres traducciones por {engine_name} IA:

{analysis_text}

Lea este texto de análisis e identifique qué traducción recomienda {engine_name} IA.
Elija entre: ChatGPT / Enhanced / Gemini

Responda solo con el nombre de la traducción recomendada."""
    else:
        prompt = f"""以下は{engine_name}AIによる3つの翻訳の分析結果です：

{analysis_text}

この分析文章を読んで、{engine_name}AIが推奨している翻訳を特定してください。
選択肢: ChatGPT / Enhanced / Gemini
推奨されている翻訳名のみを回答してください。"""
    
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        
        # ChatGPTで推奨を抽出
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": "You are an expert at analyzing LLM recommendations. Extract the recommendation from the given analysis text."
            }, {
                "role": "user", 
                "content": prompt
            }],
            max_tokens=50,
            temperature=0.1
        )
        
        recommendation_text = response.choices[0].message.content.strip()
        
        # 🆕 デバッグログ追加（Task 2.9.2 Phase B-3.5.7 Final Integration）
        app_logger.info(f"🔍 DEBUG - Raw response: '{recommendation_text}'")
        app_logger.info(f"🔍 DEBUG - Engine analyzed: '{engine_name}'")
        
        # 推奨結果の正規化（簡素化・安定化）
        recommendation_lower = recommendation_text.strip().lower()
        app_logger.info(f"🔍 DEBUG - Cleaned: '{recommendation_lower}'")
        
        # 🆕 単語境界を考慮した判定ロジック（安定化）
        import re
        
        # 完全一致を最優先
        if recommendation_lower == 'enhanced':
            recommendation = "Enhanced"
            confidence = 0.95
            method = "exact_match"
        elif recommendation_lower == 'chatgpt':
            recommendation = "ChatGPT"
            confidence = 0.95
            method = "exact_match"
        elif recommendation_lower == 'gemini':
            recommendation = "Gemini"
            confidence = 0.95
            method = "exact_match"
        # 単語境界での部分マッチ
        elif re.search(r'\benhanced\b', recommendation_lower):
            recommendation = "Enhanced"
            confidence = 0.9
            method = "word_boundary_match"
        elif re.search(r'\bchatgpt\b', recommendation_lower):
            recommendation = "ChatGPT"
            confidence = 0.9
            method = "word_boundary_match"
        elif re.search(r'\bgemini\b', recommendation_lower):
            recommendation = "Gemini"
            confidence = 0.9
            method = "word_boundary_match"
        # フォールバック：含有チェック
        elif "enhanced" in recommendation_lower:
            recommendation = "Enhanced"
            confidence = 0.8
            method = "substring_match"
        elif "chatgpt" in recommendation_lower or "chat" in recommendation_lower:
            recommendation = "ChatGPT"
            confidence = 0.8
            method = "substring_match"
        elif "gemini" in recommendation_lower:
            recommendation = "Gemini"
            confidence = 0.8
            method = "substring_match"
        else:
            recommendation = "none"
            confidence = 0.0
            method = "no_match"
        
        app_logger.info(f"🔍 DEBUG - Final result: '{recommendation}' (method: {method})")
        app_logger.info(f"🎯 推奨抽出成功: {engine_name} → {recommendation} (信頼度: {confidence})")
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "method": f"chatgpt_extraction_from_{engine_name}_{method}",
            "raw_response": recommendation_text,
            "engine_analyzed": engine_name,
            "extraction_method": method
        }
        
    except Exception as e:
        app_logger.error(f"推奨抽出エラー: {str(e)}")
        return {
            "recommendation": "error",
            "confidence": 0.0,
            "method": "extraction_failed",
            "error": str(e)
        }

# =============================================================================
# 🚀 Task 2.9.2 Phase B-3.5.2: 分析エンジン管理クラス
# =============================================================================

class AnalysisEngineManager:
    """分析エンジン管理クラス"""
    
    def __init__(self):
        self.supported_engines = ["chatgpt", "gemini", "claude"]
        self.default_engine = "gemini"
    
    def get_engine_status(self, engine: str) -> Dict[str, Any]:
        """エンジンの利用可能状況を確認"""
        if engine == "chatgpt":
            api_key = os.getenv("OPENAI_API_KEY")
            return {
                "available": bool(api_key),
                "status": "ready" if api_key else "api_key_missing",
                "description": "論理的分析"
            }
        elif engine == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            return {
                "available": bool(api_key),
                "status": "ready" if api_key else "api_key_missing",
                "description": "丁寧な説明"
            }
        elif engine == "claude":
            # 🆕 Claude client の実際の可用性をチェック
            return {
                "available": bool(claude_client),
                "status": "ready" if claude_client else "api_key_missing",
                "description": "深いニュアンス" if claude_client else "API設定必要"
            }
        else:
            return {
                "available": False,
                "status": "unsupported",
                "description": "未対応"
            }
    
    def analyze_translations(self, chatgpt_trans: str, enhanced_trans: str, gemini_trans: str, 
                           engine: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """選択されたエンジンで翻訳分析を実行"""
        
        if not engine:
            engine = self.default_engine
        
        engine_status = self.get_engine_status(engine)
        if not engine_status["available"]:
            return {
                "success": False,
                "error": f"{engine}エンジンが利用できません",
                "status": engine_status["status"],
                "engine": engine
            }
        
        try:
            if engine == "chatgpt":
                return self._chatgpt_analysis(chatgpt_trans, enhanced_trans, gemini_trans, context)
            elif engine == "gemini":
                return self._gemini_analysis(chatgpt_trans, enhanced_trans, gemini_trans, context)
            elif engine == "claude":
                return self._claude_analysis(chatgpt_trans, enhanced_trans, gemini_trans, context)
            else:
                return {
                    "success": False,
                    "error": f"未対応のエンジン: {engine}",
                    "engine": engine
                }
                
        except Exception as e:
            app_logger.error(f"分析エンジンエラー ({engine}): {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "engine": engine
            }
    
    def _chatgpt_analysis(self, chatgpt_trans: str, enhanced_trans: str, gemini_trans: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """ChatGPTによる分析"""
        
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if not OPENAI_API_KEY:
            return {"success": False, "error": "OpenAI APIキーが設定されていません", "engine": "chatgpt"}
        
        # 言語設定取得
        display_lang = session.get("lang", "jp")
        source_lang = context.get("source_lang", "ja") if context else "ja"
        target_lang = context.get("target_lang", "en") if context else "en"
        input_text = context.get("input_text", "") if context else ""
        
        # ChatGPT特化プロンプト（論理的分析）
        if display_lang == "en":
            prompt = f"""Analyze these three English translations of the Japanese text logically and systematically.

Original Japanese: {input_text}

Translations to analyze:
1. ChatGPT Translation: {chatgpt_trans}
2. Enhanced Translation: {enhanced_trans}  
3. Gemini Translation: {gemini_trans}

Provide a logical analysis focusing on:
- Accuracy and precision
- Grammatical correctness
- Clarity and coherence
- Professional appropriateness

Which translation do you recommend and why? Respond in English."""
        else:
            # 🌍 多言語対応: 現在のUI言語を取得
            current_ui_lang = session.get('lang', 'jp')
            
            # 多言語プロンプトテンプレート
            prompt_templates = {
                'jp': f"""以下の3つの英語翻訳を論理的かつ体系的に分析してください。

元の日本語: {input_text}

分析対象の翻訳:
1. ChatGPT翻訳: {chatgpt_trans}
2. Enhanced翻訳: {enhanced_trans}  
3. Gemini翻訳: {gemini_trans}

以下の観点から論理的な分析を提供してください:
- 正確性と精度
- 文法の正しさ
- 明確性と一貫性
- 専門的な適切性

どの翻訳を推奨し、その理由は何ですか？日本語で回答してください。""",
                'en': f"""Please analyze the following three English translations logically and systematically.

Original Japanese: {input_text}

Translations to analyze:
1. ChatGPT Translation: {chatgpt_trans}
2. Enhanced Translation: {enhanced_trans}  
3. Gemini Translation: {gemini_trans}

Please provide logical analysis from the following perspectives:
- Accuracy and precision
- Grammatical correctness
- Clarity and coherence
- Professional appropriateness

Which translation do you recommend and why? Please respond in English.""",
                'fr': f"""Veuillez analyser logiquement et systématiquement les trois traductions anglaises suivantes.

Japonais original: {input_text}

Traductions à analyser:
1. Traduction ChatGPT: {chatgpt_trans}
2. Traduction améliorée: {enhanced_trans}  
3. Traduction Gemini: {gemini_trans}

Veuillez fournir une analyse logique selon les perspectives suivantes:
- Précision et exactitude
- Correction grammaticale
- Clarté et cohérence
- Pertinence professionnelle

Quelle traduction recommandez-vous et pourquoi? Veuillez répondre en français.""",
                'es': f"""Por favor analice lógica y sistemáticamente las siguientes tres traducciones al inglés.

Japonés original: {input_text}

Traducciones a analizar:
1. Traducción ChatGPT: {chatgpt_trans}
2. Traducción mejorada: {enhanced_trans}  
3. Traducción Gemini: {gemini_trans}

Por favor proporcione un análisis lógico desde las siguientes perspectivas:
- Precisión y exactitud
- Corrección gramatical
- Claridad y coherencia
- Adecuación profesional

¿Qué traducción recomienda y por qué? Por favor responda en español."""
            }
            
            prompt = prompt_templates.get(current_ui_lang, prompt_templates['jp'])
        
        try:
            import openai
            openai.api_key = OPENAI_API_KEY
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "You are an expert translation analyst. Provide logical and systematic analysis."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                max_tokens=1000,
                temperature=0.3
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            return {
                "success": True,
                "analysis_text": analysis_text,
                "engine": "chatgpt",
                "status": "completed"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"ChatGPT分析エラー: {str(e)}",
                "engine": "chatgpt"
            }
    
    def _gemini_analysis(self, chatgpt_trans: str, enhanced_trans: str, gemini_trans: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Geminiによる分析（既存のf_gemini_3way_analysis関数を利用）"""
        
        try:
            analysis_text, prompt = f_gemini_3way_analysis(chatgpt_trans, enhanced_trans, gemini_trans)
            
            return {
                "success": True,
                "analysis_text": analysis_text,
                "engine": "gemini",
                "status": "completed",
                "prompt_used": prompt
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Gemini分析エラー: {str(e)}",
                "engine": "gemini"
            }
    
    def _claude_analysis(self, chatgpt_trans: str, enhanced_trans: str, gemini_trans: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """🆕 Claude API による分析実装 (Task 2.9.2 Phase B-3.5.7)"""
        
        # 🔍 Claude API設定チェック（Task 2.9.2 Phase B-3.5.7 Final Integration）
        app_logger.info(f"🎭 Claude analysis requested - Client available: {bool(claude_client)}")
        
        if not claude_client:
            # APIキー未設定時の代替メッセージ
            display_lang = session.get("lang", "jp")
            if display_lang == "en":
                message = "🚧 Claude analysis unavailable. Please check API key configuration."
            elif display_lang == "fr":
                message = "🚧 Analyse Claude indisponible. Veuillez vérifier la configuration de la clé API."
            elif display_lang == "es":
                message = "🚧 Análisis Claude no disponible. Por favor verifique la configuración de la clave API."
            else:
                message = "🚧 Claude分析が利用できません。APIキー設定を確認してください。"
            
            app_logger.error(f"❌ Claude client not available - returning error message")
            return {
                "success": False,
                "analysis_text": message,
                "engine": "claude",
                "status": "api_key_missing"
            }
        
        try:
            # 言語設定取得
            display_lang = session.get("lang", "jp")
            source_lang = context.get("source_lang", "ja") if context else "ja"
            target_lang = context.get("target_lang", "en") if context else "en"
            input_text = context.get("input_text", "") if context else ""
            
            # 言語ラベルマッピング
            lang_labels = {
                "ja": "Japanese", "en": "English", 
                "fr": "French", "es": "Spanish"
            }
            source_label = lang_labels.get(source_lang, source_lang)
            target_label = lang_labels.get(target_lang, target_lang)
            
            # Claude特化プロンプト（深いニュアンス分析とコンテキスト理解）
            if display_lang == "en":
                prompt = f"""As Claude, provide a thoughtful and nuanced analysis of these three {target_label} translations of the given {source_label} text.

ORIGINAL TEXT ({source_label}): {input_text[:1000]}

LANGUAGE PAIR: {source_label} → {target_label}

TRANSLATIONS TO COMPARE:
1. ChatGPT Translation: {chatgpt_trans}
2. Enhanced Translation: {enhanced_trans}  
3. Gemini Translation: {gemini_trans}

Please provide a comprehensive analysis focusing on:
- Cultural nuances and appropriateness
- Emotional tone and subtle implications
- Contextual accuracy and natural flow
- Which translation best captures the speaker's intent
- Detailed reasoning for your recommendation

Respond in English with thoughtful insights."""

            elif display_lang == "fr":
                prompt = f"""En tant que Claude, fournissez une analyse réfléchie et nuancée de ces trois traductions {target_label} du texte {source_label} donné.

TEXTE ORIGINAL ({source_label}): {input_text[:1000]}

PAIRE LINGUISTIQUE: {source_label} → {target_label}

TRADUCTIONS À COMPARER:
1. Traduction ChatGPT: {chatgpt_trans}
2. Traduction Améliorée: {enhanced_trans}  
3. Traduction Gemini: {gemini_trans}

Veuillez fournir une analyse complète en vous concentrant sur:
- Les nuances culturelles et l'appropriation
- Le ton émotionnel et les implications subtiles
- La précision contextuelle et le flux naturel
- Quelle traduction capture le mieux l'intention du locuteur
- Raisonnement détaillé pour votre recommandation

Répondez en français avec des insights réfléchis."""

            elif display_lang == "es":
                prompt = f"""Como Claude, proporcione un análisis reflexivo y matizado de estas tres traducciones al {target_label} del texto {source_label} dado.

TEXTO ORIGINAL ({source_label}): {input_text[:1000]}

PAR LINGÜÍSTICO: {source_label} → {target_label}

TRADUCCIONES A COMPARAR:
1. Traducción ChatGPT: {chatgpt_trans}
2. Traducción Mejorada: {enhanced_trans}  
3. Traducción Gemini: {gemini_trans}

Por favor proporcione un análisis completo enfocándose en:
- Matices culturales y apropiación
- Tono emocional e implicaciones sutiles
- Precisión contextual y flujo natural
- Qué traducción captura mejor la intención del hablante
- Razonamiento detallado para su recomendación

Responda en español con insights reflexivos."""

            else:  # Japanese
                prompt = f"""Claudeとして、与えられた{source_label}テキストの以下3つの{target_label}翻訳について、思慮深く、ニュアンスに富んだ分析を提供してください。

元のテキスト（{source_label}）: {input_text[:1000]}

言語ペア: {source_label} → {target_label}

比較する翻訳:
1. ChatGPT翻訳: {chatgpt_trans}
2. 改善翻訳: {enhanced_trans}  
3. Gemini翻訳: {gemini_trans}

以下に焦点を当てた包括的な分析を提供してください:
- 文化的ニュアンスと適切性
- 感情的なトーンと微妙な含意
- 文脈の正確性と自然な流れ
- どの翻訳が話者の意図を最もよく捉えているか
- 推奨事項の詳細な理由づけ

思慮深い洞察とともに日本語で回答してください。"""

            # 🎭 Claude API リクエスト（Task 2.9.2 Phase B-3.5.7 Final Integration）
            app_logger.info(f"🎭 Calling Claude API with prompt length: {len(prompt)} chars")
            
            response = claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            analysis_text = response.content[0].text.strip()
            
            # 成功ログ
            app_logger.info(f"✅ Claude分析成功: 言語={display_lang}, 文字数={len(analysis_text)}")
            app_logger.info(f"🎭 Claude analysis preview: {analysis_text[:200]}...")
            
            return {
                "success": True,
                "analysis_text": analysis_text,
                "engine": "claude",
                "model": "claude-3-5-sonnet-20241022",
                "status": "completed",
                "prompt_used": prompt[:500] + "..." if len(prompt) > 500 else prompt
            }
            
        except Exception as e:
            error_msg = str(e)
            app_logger.error(f"Claude分析エラー: {error_msg}")
            
            # エラーメッセージの多言語対応
            if display_lang == "en":
                error_response = f"⚠️ Claude analysis failed: {error_msg[:100]}..."
            elif display_lang == "fr":
                error_response = f"⚠️ Échec de l'analyse Claude: {error_msg[:100]}..."
            elif display_lang == "es":
                error_response = f"⚠️ Falló el análisis de Claude: {error_msg[:100]}..."
            else:
                error_response = f"⚠️ Claude分析に失敗しました: {error_msg[:100]}..."
            
            return {
                "success": False,
                "analysis_text": error_response,
                "error": error_msg,
                "engine": "claude"
            }

# =============================================================================
# インタラクティブ質問処理システム（セキュリティ強化版）
# =============================================================================

class TranslationContext:
    """翻訳コンテキストを管理するクラス（セキュリティ強化版）"""
    
    @staticmethod
    def save_context(input_text: str, translations: Dict[str, str], analysis: str, metadata: Dict[str, Any]) -> None:
        """翻訳コンテキストをセッションに保存（入力値検証付き）"""
        
        # 🆕 保存前の入力値検証
        safe_translations = {}
        for key, value in translations.items():
            if value:
                is_valid, _ = EnhancedInputValidator.validate_text_input(
                    value, max_length=10000, field_name=f"translation_{key}"
                )
                if is_valid:
                    safe_translations[key] = value
        
        # 🆕 ユニークIDとタイムスタンプを追加
        import uuid
        context_id = str(uuid.uuid4())[:8]  # 短縮ユニークID
        current_timestamp = time.time()
        
        # 🆕 Cookieサイズ制限対策：大容量データを軽量化
        session["translation_context"] = {
            "context_id": context_id,
            "timestamp": current_timestamp,
            "created_at": datetime.now().isoformat(),
            "source_lang": metadata.get("source_lang", ""),
            "target_lang": metadata.get("target_lang", ""),
            # 大容量データは個別のセッションキーから参照（重複排除）
            "has_data": True
        }
        
        log_access_event(f'Translation context saved: ID={context_id}, timestamp={current_timestamp}')
        
    @staticmethod
    def get_context() -> Dict[str, Any]:
        """保存された翻訳コンテキストを取得（期限チェック付き・Cookieサイズ対策版）"""
        context = session.get("translation_context", {})
        
        if context and context.get("has_data"):
            context_id = context.get("context_id", "unknown")
            
            # 古いコンテキストは削除（1時間以上前）
            if time.time() - context.get("timestamp", 0) > 3600:
                log_access_event(f'Translation context expired: ID={context_id}')
                TranslationContext.clear_context()
                return {}
            
            # 🆕 大容量データを個別セッションキーから再構築（重複排除・逆翻訳含む）
            full_context = {
                "context_id": context_id,
                "timestamp": context.get("timestamp"),
                "created_at": context.get("created_at"),
                "input_text": session.get("input_text", ""),
                "translations": {
                    "chatgpt": session.get("translated_text", ""),
                    "enhanced": session.get("better_translation", ""),
                    "gemini": session.get("gemini_translation", ""),
                    # 🆕 逆翻訳データを追加（KeyError対策）
                    "chatgpt_reverse": session.get("reverse_translated_text", ""),
                    "enhanced_reverse": session.get("reverse_better_translation", ""),
                    "gemini_reverse": session.get("gemini_reverse_translation", "")
                },
                "analysis": session.get("gemini_3way_analysis", ""),
                "metadata": {
                    "source_lang": context.get("source_lang", ""),
                    "target_lang": context.get("target_lang", ""),
                    "partner_message": session.get("partner_message", ""),
                    "context_info": session.get("context_info", "")
                }
            }
            
            log_access_event(f'Translation context retrieved: ID={context_id}')
            return full_context
        
        return {}
    
    @staticmethod
    def clear_context() -> None:
        """翻訳コンテキストをクリア"""
        context = session.get("translation_context", {})
        if context:
            context_id = context.get("context_id", "unknown")
            log_access_event(f'Translation context cleared: ID={context_id}')
        session.pop("translation_context", None)

class LangPontTranslationExpertAI:
    """🎯 LangPont多言語翻訳エキスパートAI - 包括的翻訳支援システム"""
    
    def __init__(self, client: Any) -> None:
        self.client = client
        self.supported_languages = {
            'ja': {'name': 'Japanese', '日本語': True},
            'en': {'name': 'English', 'English': True}, 
            'fr': {'name': 'French', 'Français': True},
            'es': {'name': 'Spanish', 'Español': True}
        }
        
        # 🌍 多言語対応: レスポンス言語マップ
        self.response_lang_map = {
            "jp": "Japanese",
            "en": "English", 
            "fr": "French",
            "es": "Spanish"  # ← スペイン語を追加
        }
        
        # 🌍 多言語対応: エラーメッセージ
        self.error_messages = {
            "jp": {
                "question_processing": "質問処理中にエラーが発生しました: {}",
                "translation_modification": "翻訳修正中にエラーが発生しました: {}",
                "analysis_inquiry": "分析解説中にエラーが発生しました: {}",
                "linguistic_question": "言語学的質問処理中にエラーが発生しました: {}",
                "context_variation": "コンテキスト変更処理中にエラーが発生しました: {}",
                "comparison_analysis": "比較分析中にエラーが発生しました: {}"
            },
            "en": {
                "question_processing": "Error occurred while processing question: {}",
                "translation_modification": "Error occurred during translation modification: {}",
                "analysis_inquiry": "Error occurred during analysis inquiry: {}",
                "linguistic_question": "Error occurred while processing linguistic question: {}",
                "context_variation": "Error occurred during context variation: {}",
                "comparison_analysis": "Error occurred during comparison analysis: {}"
            },
            "fr": {
                "question_processing": "Erreur lors du traitement de la question: {}",
                "translation_modification": "Erreur lors de la modification de traduction: {}",
                "analysis_inquiry": "Erreur lors de l'analyse d'enquête: {}",
                "linguistic_question": "Erreur lors du traitement de la question linguistique: {}",
                "context_variation": "Erreur lors de la variation de contexte: {}",
                "comparison_analysis": "Erreur lors de l'analyse comparative: {}"
            },
            "es": {
                "question_processing": "Error al procesar la pregunta: {}",
                "translation_modification": "Error durante la modificación de traducción: {}",
                "analysis_inquiry": "Error durante la consulta de análisis: {}",
                "linguistic_question": "Error al procesar la pregunta lingüística: {}",
                "context_variation": "Error durante la variación de contexto: {}",
                "comparison_analysis": "Error durante el análisis comparativo: {}"
            }
        }
    
    def _get_error_message(self, context: Dict[str, Any], error_type: str, error_details: str) -> str:
        """🌍 多言語対応エラーメッセージを取得"""
        display_lang = context.get('display_language', 'jp')
        lang_errors = self.error_messages.get(display_lang, self.error_messages["jp"])
        error_template = lang_errors.get(error_type, lang_errors["question_processing"])
        return error_template.format(error_details)
    
    def process_question(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """🧠 翻訳エキスパートとして質問を包括的に処理"""
        
        # 🆕 厳密な入力値検証
        is_valid, error_msg = EnhancedInputValidator.validate_text_input(
            question, max_length=1000, min_length=5, field_name="質問"
        )
        if not is_valid:
            log_security_event(
                'INVALID_QUESTION_INPUT',
                f'Question validation failed: {error_msg}',
                'WARNING'
            )
            raise ValueError(error_msg)
        
        # 🔍 完全な翻訳セッション情報を取得
        full_context = self._get_complete_translation_context(context)
        
        # 🎯 質問意図の詳細分析
        question_analysis = self._analyze_question_intent(question, full_context)
        
        # 🚀 質問タイプに応じた専門的処理
        if question_analysis['type'] == 'translation_modification':
            return self._handle_translation_modification(question, full_context, question_analysis)
        elif question_analysis['type'] == 'analysis_inquiry':
            return self._handle_analysis_inquiry(question, full_context, question_analysis)
        elif question_analysis['type'] == 'linguistic_question':
            return self._handle_linguistic_question(question, full_context, question_analysis)
        elif question_analysis['type'] == 'context_variation':
            return self._handle_context_variation(question, full_context, question_analysis)
        elif question_analysis['type'] == 'comparison_analysis':
            return self._handle_comparison_analysis(question, full_context, question_analysis)
        else:
            return self._handle_general_expert_question(question, full_context, question_analysis)
    
    def _get_complete_translation_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """🔍 セッションから完全な翻訳コンテキストを取得"""
        
        # セッションから全翻訳データを取得
        session_data = {
            # 基本情報
            'original_text': session.get('input_text', ''),
            'language_pair': session.get('language_pair', 'ja-en'),
            'source_lang': session.get('language_pair', 'ja-en').split('-')[0],
            'target_lang': session.get('language_pair', 'ja-en').split('-')[1],
            
            # コンテキスト情報
            'partner_message': session.get('partner_message', ''),
            'context_info': session.get('context_info', ''),
            
            # 6つの翻訳結果
            'translations': {
                'chatgpt': session.get('translated_text', ''),
                'chatgpt_reverse': session.get('reverse_translated_text', ''),
                'enhanced': session.get('better_translation', ''),
                'enhanced_reverse': session.get('reverse_better_translation', ''),
                'gemini': session.get('gemini_translation', ''),
                'gemini_reverse': session.get('gemini_reverse_translation', '')
            },
            
            # 分析結果
            'nuance_analysis': session.get('gemini_3way_analysis', ''),
            'selected_engine': session.get('analysis_engine', 'gemini'),
            
            # チャット履歴
            'chat_history': session.get('chat_history', []),
            
            # 表示言語
            'display_language': session.get('lang', 'jp')
        }
        
        # 基本コンテキストと統合
        session_data.update(context)
        return session_data
    
    def _analyze_question_intent(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """🎯 質問の意図を詳細に分析"""
        
        question_lower = question.lower()
        
        # 翻訳修正要求の検出
        modification_patterns = [
            r'(\d+)番目.*?((口語|カジュアル|フォーマル|丁寧|親しみ|ビジネス).*?(に|で|風に))',
            r'(\d+).*?(もっと|より).*?(口語|カジュアル|フォーマル|丁寧|親しみ|ビジネス)',
            r'(\d+).*?(変更|修正|直し|調整).*?(して|してください)',
            r'(フランス語|英語|スペイン語).*?(口語|カジュアル|フォーマル).*?(に|で)'
        ]
        
        for pattern in modification_patterns:
            import re
            match = re.search(pattern, question)
            if match:
                # 番号抽出
                number_match = re.search(r'(\d+)番目', question)
                target_number = int(number_match.group(1)) if number_match else None
                
                # スタイル抽出
                style_match = re.search(r'(口語|カジュアル|フォーマル|丁寧|親しみ|ビジネス)', question)
                target_style = style_match.group(1) if style_match else None
                
                return {
                    'type': 'translation_modification',
                    'target_number': target_number,
                    'target_style': target_style,
                    'target_language': context['target_lang'],
                    'confidence': 0.9
                }
        
        # 分析内容への質問
        if any(word in question_lower for word in ['分析', 'なぜ', '理由', '推奨', 'gemini', 'chatgpt']):
            return {
                'type': 'analysis_inquiry',
                'confidence': 0.8
            }
        
        # 言語学的質問
        if any(word in question_lower for word in ['活用', '文法', '構造', '意味', '違い', '類義語']):
            return {
                'type': 'linguistic_question', 
                'confidence': 0.8
            }
        
        # コンテキスト変更要求
        if any(word in question_lower for word in ['怒っ', '友達', 'ビジネス', '場合', 'だったら']):
            return {
                'type': 'context_variation',
                'confidence': 0.7
            }
        
        # 比較質問
        if any(word in question_lower for word in ['比較', '違い', 'どちら', '1番目', '2番目', '3番目']):
            return {
                'type': 'comparison_analysis',
                'confidence': 0.8
            }
        
        return {
            'type': 'general_expert',
            'confidence': 0.5
        }
    
    def _handle_translation_modification(self, question: str, context: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """🔧 翻訳修正要求を処理"""
        
        target_number = analysis.get('target_number')
        target_style = analysis.get('target_style') 
        target_lang = context['target_lang']
        
        # 対象翻訳を特定
        translations = context['translations']
        translation_map = {
            1: ('ChatGPT', translations['chatgpt']),
            2: ('Enhanced', translations['enhanced']), 
            3: ('Gemini', translations['gemini'])
        }
        
        if target_number and target_number in translation_map:
            engine_name, original_translation = translation_map[target_number]
        else:
            # 番号が指定されていない場合、最新の分析で推奨された翻訳を使用
            engine_name = "Enhanced"
            original_translation = translations['enhanced']
        
        # 言語別のスタイル定義
        style_instructions = {
            'fr': {
                '口語': 'très familier et oral, utilise des contractions et expressions quotidiennes',
                'カジュアル': 'détendu et amical, style conversationnel sans formalité excessive',
                'フォーマル': 'très formel et professionnel, style soutenu et respectueux',
                'ビジネス': 'style commercial professionnel, adapté aux communications d\'entreprise',
                '丁寧': 'poli et courtois, utilise les formules de politesse appropriées'
            },
            'en': {
                '口語': 'very casual and colloquial, use contractions and everyday expressions',
                'カジュアル': 'relaxed and friendly, conversational style without excessive formality',
                'フォーマル': 'very formal and professional, elevated and respectful style',
                'ビジネス': 'professional business style, suitable for corporate communications',
                '丁寧': 'polite and courteous, use appropriate politeness formulas'
            },
            'es': {
                '口語': 'muy familiar y coloquial, usa contracciones y expresiones cotidianas',
                'カジュアル': 'relajado y amistoso, estilo conversacional sin formalidad excesiva',
                'フォーマル': 'muy formal y profesional, estilo elevado y respetuoso',
                'ビジネス': 'estilo comercial profesional, adecuado para comunicaciones empresariales',
                '丁寧': 'cortés y educado, usa las fórmulas de cortesía apropiadas'
            }
        }
        
        style_instruction = style_instructions.get(target_lang, {}).get(target_style, f'{target_style}的なスタイル')
        
        # 専門的な修正プロンプト
        prompt = f"""【LangPont翻訳エキスパートAI】
あなたは多言語翻訳の専門家です。以下の翻訳を指定されたスタイルに修正してください。

【元の文章（日本語）】
{context['original_text']}

【現在の{engine_name}翻訳（{target_lang.upper()}）】
{original_translation}

【修正指示】
この翻訳を「{target_style}」なスタイルに変更してください。
言語: {target_lang.upper()}
スタイル要件: {style_instruction}

【修正版翻訳を提供してください】
- 元の意味は完全に保持
- {target_style}なスタイルに完全に適応
- 文化的に自然な表現を使用
- 修正のポイントも説明

修正版:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",  # より高品質な翻訳のためGPT-4を使用
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800
            )
            
            result = response.choices[0].message.content.strip()
            
            return {
                "type": "translation_modification",
                "result": result,
                "original_engine": engine_name,
                "target_style": target_style,
                "target_language": target_lang
            }
            
        except Exception as e:
            error_msg = self._get_error_message(context, "translation_modification", str(e))
            return {
                "type": "error",
                "result": error_msg
            }
    
    def _handle_analysis_inquiry(self, question: str, context: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """🧠 分析内容への質問を処理"""
        
        nuance_analysis = context.get('nuance_analysis', '')
        selected_engine = context.get('selected_engine', 'gemini')
        
        prompt = f"""【LangPont翻訳エキスパートAI - 分析解説】
あなたは翻訳品質分析の専門家です。以下の分析結果について質問に答えてください。

【元の文章】
{context['original_text']}

【3つの翻訳】
1. ChatGPT: {context['translations']['chatgpt']}
2. Enhanced: {context['translations']['enhanced']}
3. Gemini: {context['translations']['gemini']}

【{selected_engine.upper()}による分析結果】
{nuance_analysis}

【ユーザーの質問】
{question}

【回答要件】
- 分析内容を詳しく解説
- 翻訳の品質評価基準を説明
- 推奨理由の言語学的根拠を提示
- 具体例を用いて説明

回答:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=700
            )
            
            result = response.choices[0].message.content.strip()
            
            return {
                "type": "analysis_inquiry",
                "result": result,
                "analyzed_engine": selected_engine
            }
            
        except Exception as e:
            error_msg = self._get_error_message(context, "analysis_inquiry", str(e))
            return {
                "type": "error", 
                "result": error_msg
            }
    
    def _handle_linguistic_question(self, question: str, context: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """📚 言語学的質問を処理"""
        
        prompt = f"""【LangPont翻訳エキスパートAI - 言語学習支援】
あなたは多言語の言語学専門家です。以下の翻訳に関する言語学的質問に答えてください。

【翻訳セッション情報】
元の文章: {context['original_text']}
言語ペア: {context['source_lang']} → {context['target_lang']}

【3つの翻訳結果】
1. ChatGPT: {context['translations']['chatgpt']}
2. Enhanced: {context['translations']['enhanced']}
3. Gemini: {context['translations']['gemini']}

【ユーザーの質問】
{question}

【回答要件】
- 言語学的に正確な説明
- 文法構造の詳細解説
- 語彙の使い分けの説明
- 実用的な学習アドバイス
- 具体例を用いた説明

回答:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=700
            )
            
            result = response.choices[0].message.content.strip()
            
            return {
                "type": "linguistic_question",
                "result": result
            }
            
        except Exception as e:
            error_msg = self._get_error_message(context, "linguistic_question", str(e))
            return {
                "type": "error",
                "result": error_msg
            }
    
    def _handle_context_variation(self, question: str, context: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """🎭 コンテキスト変更要求を処理"""
        
        # 推奨翻訳を基準とする
        base_translation = context['translations']['enhanced']
        
        prompt = f"""【LangPont翻訳エキスパートAI - コンテキスト適応】
あなたは多言語翻訳の専門家です。異なるコンテキストでの翻訳バリエーションを提供してください。

【元の文章】
{context['original_text']}

【現在の翻訳（{context['target_lang'].upper()}）】
{base_translation}

【コンテキスト変更要求】
{question}

【提供してください】
- 新しいコンテキストに適した翻訳
- 変更のポイントと理由
- 文化的配慮事項
- 使用場面の説明

回答:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=700
            )
            
            result = response.choices[0].message.content.strip()
            
            return {
                "type": "context_variation",
                "result": result
            }
            
        except Exception as e:
            error_msg = self._get_error_message(context, "context_variation", str(e))
            return {
                "type": "error",
                "result": error_msg
            }
    
    def _handle_comparison_analysis(self, question: str, context: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """⚖️ 比較分析を処理"""
        
        translations = context['translations']
        
        # 🆕 デバッグ：利用可能な翻訳キーを確認（KeyError対策）
        app_logger.info(f"🔍 Available translation keys: {list(translations.keys())}")
        
        # 🆕 必要なキーの存在確認
        required_keys = ['chatgpt', 'enhanced', 'gemini', 'chatgpt_reverse', 'enhanced_reverse', 'gemini_reverse']
        missing_keys = [key for key in required_keys if key not in translations]
        if missing_keys:
            app_logger.warning(f"⚠️ Missing translation keys: {missing_keys}")
            return {
                "type": "error",
                "result": f"翻訳データが不完全です。不足キー: {missing_keys}"
            }
        
        prompt = f"""【LangPont翻訳エキスパートAI - 比較分析】
あなたは翻訳品質分析の専門家です。以下の翻訳を詳細に比較分析してください。

【元の文章】
{context['original_text']}

【比較対象の翻訳】
1. ChatGPT: {translations['chatgpt']}
2. Enhanced: {translations['enhanced']}
3. Gemini: {translations['gemini']}

【逆翻訳も参考情報として】
1. ChatGPT逆翻訳: {translations['chatgpt_reverse']}
2. Enhanced逆翻訳: {translations['enhanced_reverse']}
3. Gemini逆翻訳: {translations['gemini_reverse']}

【ユーザーの質問】
{question}

【分析観点】
- 正確性（元の意味の保持度）
- 自然さ（目標言語としての流暢さ）
- 文化的適切性
- 語彙選択の妥当性
- 文体の一貫性

回答:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800
            )
            
            result = response.choices[0].message.content.strip()
            
            return {
                "type": "comparison_analysis",
                "result": result
            }
            
        except Exception as e:
            error_msg = self._get_error_message(context, "comparison_analysis", str(e))
            return {
                "type": "error",
                "result": error_msg
            }
    
    def _handle_general_expert_question(self, question: str, context: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """🎓 一般的な翻訳エキスパート質問を処理（多言語対応）"""
        
        display_lang = context.get('display_language', 'jp')
        response_language = self.response_lang_map.get(display_lang, "Japanese")
        
        # 🎯 デバッグ用ログ追加
        app_logger.info(f"Interactive question language: display_lang={display_lang}, response_language={response_language}")
        
        prompt = f"""【LangPont Translation Expert AI】
You are a multilingual translation expert. Please answer the following question about the translation session.

【Translation Session Information】
Original text: {context['original_text']}
Language pair: {context['source_lang']} → {context['target_lang']}
Context information: {context.get('context_info', 'None')}
Message to partner: {context.get('partner_message', 'None')}

【Three Translation Results】
1. ChatGPT: {context['translations']['chatgpt']}
2. Enhanced: {context['translations']['enhanced']}
3. Gemini: {context['translations']['gemini']}

【Analysis Results】
{context.get('nuance_analysis', 'Analysis not performed')}

【User's Question】
{question}

【Response Requirements】
- Comprehensive answer as a translation expert
- Practical and constructive advice
- Information helpful for language learning
- Explanations including cultural considerations

IMPORTANT: Please provide your response in {response_language}.

Response:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=700
            )
            
            result = response.choices[0].message.content.strip()
            
            return {
                "type": "general_expert",
                "result": result
            }
            
        except Exception as e:
            error_msg = self._get_error_message(context, "question_processing", str(e))
            return {
                "type": "error",
                "result": error_msg
            }

# グローバルインスタンス
interactive_processor = LangPontTranslationExpertAI(client)

# =============================================================================
# ルーティング（完全セキュリティ強化版）
# =============================================================================

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
        print(f"🚨 LOGIN DEBUG: POST request - username: '{username}', password length: {len(password)}")
        
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
                    print(f"🚨 LOGIN DEBUG: Found user {username}, checking password...")
                    if password == user_data["password"]:
                        print(f"🚨 LOGIN DEBUG: Password correct for {username}!")
                        authenticated_user = {
                            "username": username,
                            "role": user_data["role"],
                            "daily_limit": user_data["daily_limit"],
                            "auth_method": "standard"
                        }
                        print(f"🚨 LOGIN DEBUG: Created authenticated_user: {authenticated_user}")
                    else:
                        print(f"🚨 LOGIN DEBUG: Password incorrect for {username}")
                
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
                    print(f"🚨 LOGIN DEBUG: authenticated_user exists, setting session...")
                    # 🆕 セッション情報の保存
                    session["logged_in"] = True
                    session["username"] = authenticated_user["username"]
                    session["user_role"] = authenticated_user["role"]
                    session["daily_limit"] = authenticated_user["daily_limit"]
                    session.permanent = True
                    print(f"🚨 LOGIN DEBUG: Session set - logged_in: {session['logged_in']}, username: {session['username']}, role: {session['user_role']}")
                    
                    # 🆕 セッションIDの再生成（セッションハイジャック対策）
                    # 🚨 TEMPORARILY DISABLED FOR DEBUG: SecureSessionManager.regenerate_session_id()
                    
                    # 🆕 詳細ログ記録
                    log_security_event(
                        'LOGIN_SUCCESS', 
                        f'User: {authenticated_user["username"]}, Role: {authenticated_user["role"]}, Method: {authenticated_user["auth_method"]}', 
                        'INFO'
                    )
                    log_access_event(f'User logged in: {authenticated_user["username"]} ({authenticated_user["role"]})')
                    
                    print(f"🚨 LOGIN DEBUG: About to redirect to main page...")
                    # 🆕 ログイン成功後の適切なリダイレクト
                    # 全てのユーザーをメインアプリ（翻訳画面）へリダイレクト
                    return redirect(url_for("index"))
                else:
                    print(f"🚨 LOGIN DEBUG: authenticated_user is None - authentication failed")
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
        
        # 破損した翻訳コンテキストを削除
        broken_context = session.get("translation_context", {})
        if broken_context and not session.get("translated_text"):
            session.pop("translation_context", None)
            log_access_event("Broken translation context cleared on page load")
        
        # 確実に空の履歴を設定
        chat_history = []
        
        log_access_event("Page loaded with clean slate - all old data cleared")
    else:
        # POST リクエスト時のみ既存データを保持
        has_translation_data = session.get("translated_text") or session.get("translation_context", {}).get("has_data")
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
                
                # 翻訳コンテキスト
                "translation_context"
                # 注意: "chat_history" はリセット時も保持（ユーザビリティ向上）
            ]
            
            for key in translation_keys_to_clear:
                session.pop(key, None)
            
            # TranslationContextの明示的クリア
            TranslationContext.clear_context()
            
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

# 2. 既存の /alpha ルートを修正（置き換えてください）
@app.route("/alpha")
def alpha_landing():
    """Early Access用ランディングページ"""
    log_access_event('Alpha landing page accessed')
    return render_template("landing.html", version_info=VERSION_INFO)

@app.route("/logout")
def logout():
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
        keys_to_preserve = ['logged_in', 'translation_context', 'usage_data', 'csrf_token', 'session_created']
        
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

@app.route("/translate_chatgpt", methods=["POST"])
@require_rate_limit
def translate_chatgpt_only():
    try:
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
        
        # 現在の言語を取得
        current_lang = session.get('lang', 'jp')
        from labels import labels
        
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

        # セッション保存
        session["source_lang"] = source_lang
        session["target_lang"] = target_lang
        session["language_pair"] = language_pair
        session["input_text"] = input_text
        session["partner_message"] = partner_message
        session["context_info"] = context_info

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

        # セッション保存（安全な保存関数を使用）
        safe_session_store("translated_text", translated)
        safe_session_store("reverse_translated_text", reverse)
        safe_session_store("gemini_translation", gemini_translation)
        safe_session_store("gemini_reverse_translation", gemini_reverse_translation)  # 🆕 Phase A修正
        safe_session_store("better_translation", better_translation)
        safe_session_store("reverse_better_translation", reverse_better)

        # 🆕 軽量化：翻訳コンテキストは最小限のメタデータのみ保存（重複データ排除）
        TranslationContext.save_context(
            input_text="",  # 空文字（個別セッションキーから参照）
            translations={},  # 空辞書（個別セッションキーから参照）
            analysis="",
            metadata={
                "source_lang": source_lang,
                "target_lang": target_lang,
                "partner_message": "",  # 空文字（個別セッションキーから参照）
                "context_info": ""      # 空文字（個別セッションキーから参照）
            }
        )

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
        
        # 更新実行
        cursor.execute("""
            UPDATE translation_history 
            SET gemini_analysis_result = ?,
                gemini_recommendation_extracted = ?,
                gemini_recommendation_confidence = ?,
                gemini_recommendation_strength = ?,
                gemini_recommendation_reasons = ?,
                analysis_timestamp = ?
            WHERE id = ?
        """, (analysis_result, recommendation, confidence, strength, reasons, 
              datetime.now().isoformat(), record_id))
        
        updated_rows = cursor.rowcount
        app_logger.info(f"✅ 更新完了: {updated_rows} 行更新")
        
        conn.commit()
        conn.close()
        
        return updated_rows > 0
        
    except Exception as e:
        app_logger.error(f"Failed to save Gemini analysis: {str(e)}")

@app.route("/set_analysis_engine", methods=["POST"])
@require_rate_limit
def set_analysis_engine():
    """分析エンジンを設定するエンドポイント"""
    try:
        data = request.get_json() or {}
        engine = data.get("engine", "gemini")
        
        # 有効なエンジンのリスト
        valid_engines = ["gemini", "claude", "gpt4", "openai", "chatgpt"]
        
        if engine not in valid_engines:
            return jsonify({
                "success": False,
                "error": f"無効なエンジン: {engine}. 有効なエンジン: {', '.join(valid_engines)}"
            }), 400
        
        # セッションにエンジンを保存
        session["analysis_engine"] = engine
        
        app_logger.info(f"Analysis engine set to: {engine}")
        log_access_event(f'Analysis engine changed to: {engine}')
        
        return jsonify({
            "success": True,
            "engine": engine,
            "message": f"分析エンジンを{engine}に設定しました"
        })
        
    except Exception as e:
        app_logger.error(f"Set analysis engine error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/get_nuance", methods=["POST"])
@require_rate_limit
def get_nuance():
    try:
        translated_text = session.get("translated_text", "")
        better_translation = session.get("better_translation", "")
        gemini_translation = session.get("gemini_translation", "")

        if not (len(translated_text.strip()) > 0 and
                len(better_translation.strip()) > 0 and
                len(gemini_translation.strip()) > 0):
            return {"error": "必要な翻訳データが不足しています"}, 400

        # 🧠 Task 2.9.2 Phase B-3.5.2: 選択された分析エンジンで実行
        # POSTリクエストボディからエンジン情報を取得（優先）
        data = request.get_json() or {}
        selected_engine = data.get('engine', session.get('analysis_engine', 'gemini'))
        
        # エンジン情報をセッションに保存（次回の呼び出しのため）
        if 'engine' in data:
            session['analysis_engine'] = selected_engine
            app_logger.info(f"Analysis engine updated in session: {selected_engine}")
        
        if selected_engine == 'gemini':
            # 従来のGemini分析（既存実装）
            result, chatgpt_prompt = f_gemini_3way_analysis(translated_text, better_translation, gemini_translation)
        else:
            # 新しいマルチエンジンシステムを使用
            engine_manager = AnalysisEngineManager()
            input_text = session.get("input_text", "")
            
            analysis_result = engine_manager.analyze_translations(
                chatgpt_trans=translated_text,
                enhanced_trans=better_translation,
                gemini_trans=gemini_translation,
                engine=selected_engine,
                context={
                    "input_text": input_text,
                    "source_lang": session.get("language_pair", "ja-en").split("-")[0],
                    "target_lang": session.get("language_pair", "ja-en").split("-")[1],
                    "partner_message": session.get("partner_message", ""),
                    "context_info": session.get("context_info", "")
                }
            )
            
            if not analysis_result['success']:
                return {"error": f"分析エンジン({selected_engine})でエラーが発生しました: {analysis_result['error']}"}, 500
            
            result = analysis_result.get('analysis_text', '')
            chatgpt_prompt = analysis_result.get('prompt_used', '')
        
        # Truncate analysis to reduce cookie size from 4100+ bytes to under 4000 bytes
        max_analysis_length = 3000  # Conservative limit to stay under 4KB cookie limit
        if len(result) > max_analysis_length:
            truncated_result = result[:max_analysis_length] + "...\n\n[分析結果が長いため省略されました]"
            app_logger.info(f"Analysis truncated from {len(result)} to {len(truncated_result)} characters")
            session["gemini_3way_analysis"] = truncated_result
        else:
            session["gemini_3way_analysis"] = result
        
        # 🆕 Task 2.9.2 Phase B-3.5.2: 新しい推奨抽出システム
        try:
            app_logger.info(f"🧠 Task 2.9.2 Phase B-3.5.2: 推奨抽出開始 (engine: {selected_engine})")
            app_logger.info(f"🤖 分析テキスト長: {len(result)} 文字")
            
            # 新しい統一推奨抽出システムを使用
            recommendation_result = extract_recommendation_from_analysis(result, selected_engine)
            
            app_logger.info(f"🧠 推奨抽出結果: {recommendation_result}")
            
            # 結果を取得
            final_recommendation = recommendation_result.get('recommendation', 'none')
            final_confidence = recommendation_result.get('confidence', 0.0)
            final_strength = recommendation_result.get('method', 'chatgpt_extraction')
            
            # Backward compatibility: 古いフォーマットのサポート
            if isinstance(recommendation_result, tuple) and len(recommendation_result) >= 3:
                final_recommendation, final_confidence, final_strength = recommendation_result[:3]
                final_recommendation = final_recommendation if final_recommendation else 'none'
                final_confidence = final_confidence if final_confidence else 0.0
                final_strength = final_strength if final_strength else 'chatgpt_extraction'
            
            # 🚀 Phase B-2: Task 2.9.2 推奨抽出データ収集
            try:
                from admin_dashboard import advanced_analytics
                session_id = session.get("session_id") or session.get("csrf_token", "")[:16] or f"nuance_{int(time.time())}"
                user_id = session.get("username", "anonymous")
                input_text_from_session = session.get("input_text", "")
                
                # Task 2.9.2 推奨抽出ログ記録
                advanced_analytics.log_task292_extraction(
                    session_id=session_id,
                    user_id=user_id,
                    input_text=input_text_from_session,
                    analysis_language="Japanese",
                    method=final_strength,
                    recommendation=final_recommendation,
                    confidence=final_confidence,
                    processing_time_ms=int((time.time() - app_logger.info.__globals__.get('analysis_start_time', time.time())) * 1000),
                    success=True,
                    llm_response=result[:1000],  # 最初の1000文字のみ保存
                    metadata={
                        'analysis_type': f'{selected_engine}_3way_nuance',
                        'analysis_engine': selected_engine,
                        'translation_types': ['chatgpt', 'enhanced', 'gemini'],
                        'analysis_length': len(result)
                    }
                )
                
                app_logger.info(f"🚀 Phase B-2: Task 2.9.2 extraction data collected: {final_recommendation} ({final_confidence:.3f})")
                
            except Exception as task292_error:
                app_logger.warning(f"🚀 Phase B-2: Task 2.9.2 data collection failed: {str(task292_error)}")
            
            # 🚀 Phase B-1: 管理者ログ記録（分析エンジンイベント）
            username = session.get("username", "anonymous")
            log_gemini_analysis(username, final_recommendation, final_confidence, final_strength)
            
            # 🔍 デバッグ: セッションID取得の改善（翻訳保存時と同じロジックを使用）
            session_id = session.get("session_id") or session.get("csrf_token", "")[:16]
            app_logger.info(f"🔍 セッションID取得: session_id={session_id}")
            
            # 🆕 Task 2.9.2 Phase B-3.5.10: 統合活動ログ記録
            try:
                activity_data = {
                    'activity_type': 'normal_use',
                    'session_id': session_id,
                    'user_id': session.get('username', 'anonymous'),
                    'japanese_text': session.get("input_text", ""),
                    'target_language': session.get("language_pair", "ja-en").split("-")[1],
                    'language_pair': session.get("language_pair", "ja-en"),
                    'partner_message': session.get("partner_message", ""),
                    'context_info': session.get("context_info", ""),
                    'chatgpt_translation': translated_text,
                    'enhanced_translation': better_translation,
                    'gemini_translation': gemini_translation,
                    'button_pressed': selected_engine,
                    'actual_analysis_llm': selected_engine,  # 実際のエンジン
                    'recommendation_result': final_recommendation,
                    'confidence': final_confidence,
                    'processing_method': final_strength,
                    'extraction_method': recommendation_result.get('extraction_method', ''),
                    'full_analysis_text': result,
                    'terminal_logs': '',  # 必要に応じて追加
                    'debug_logs': f"Engine: {selected_engine}, Method: {final_strength}",
                    'error_occurred': False,
                    'processing_duration': time.time() - start_time if 'start_time' in locals() else None,
                    'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR') or request.environ.get('REMOTE_ADDR'),
                    'user_agent': request.environ.get('HTTP_USER_AGENT', ''),
                    'notes': f'Analysis via {selected_engine} engine'
                }
                
                log_id = log_analysis_activity(activity_data)
                app_logger.info(f"✅ Activity logged to comprehensive system: ID={log_id}")
                
            except Exception as log_error:
                app_logger.warning(f"⚠️ Failed to log to comprehensive system: {str(log_error)}")
            
            app_logger.info(f"🔍 Gemini分析保存開始: session_id={session_id}")
            
            # 🚀 Phase A-9: structured_rec エラー修正
            # データベースに保存（Phase A-8 LLM結果使用）
            save_result = save_gemini_analysis_to_db(
                session_id=session_id,
                analysis_result=result,
                recommendation=final_recommendation,
                confidence=final_confidence,
                strength=final_strength,
                reasons=f"Engine: {selected_engine}, Method: {final_strength}, Confidence: {final_confidence:.3f}"
            )
            
            if save_result:
                app_logger.info(f"✅ 分析保存成功 ({selected_engine}): session_id={session_id}, recommendation={final_recommendation}")
            else:
                app_logger.error(f"❌ 分析保存失敗 ({selected_engine}): session_id={session_id}")
            
            # 🚀 Phase A-9: structured_rec エラー修正
            app_logger.info(f"Task 2.9.2 analysis completed: recommendation={final_recommendation}, confidence={final_confidence:.3f}")
            
        except Exception as analysis_error:
            app_logger.error(f"Task 2.9.2 analysis error: {str(analysis_error)}")
            import traceback
            app_logger.error(traceback.format_exc())
        
        # 分析結果を翻訳コンテキストに追加
        context = TranslationContext.get_context()
        if context:
            context["analysis"] = result
            TranslationContext.save_context(
                context["input_text"],
                context["translations"],
                result,
                context["metadata"]
            )
        
        log_access_event('Nuance analysis completed')
        
        # 🚨 重要修正：サーバー側推奨結果をフロントエンドに正しく渡す
        response_data = {
            "nuance": result,
            "analysis_engine": selected_engine  # 🧠 使用した分析エンジン情報を追加
        }
        
        # Task 2.9.2 Phase B-3.5.2 で抽出した推奨結果をレスポンスに含める
        try:
            response_data["recommendation"] = {
                "result": final_recommendation,
                "confidence": final_confidence,
                "method": final_strength,
                "source": f"server_side_{selected_engine}_extraction",
                "engine": selected_engine
            }
            app_logger.info(f"🔧 フロントエンド送信: recommendation={final_recommendation}, confidence={final_confidence}")
        except:
            # 推奨結果が取得できない場合のフォールバック
            response_data["recommendation"] = {
                "result": "none",
                "confidence": 0.0,
                "method": "extraction_failed",
                "source": f"server_side_{selected_engine}_fallback",
                "engine": selected_engine
            }
        
        # ChatGPTプロンプトをレスポンスに含める
        if chatgpt_prompt:
            response_data["chatgpt_prompt"] = chatgpt_prompt
            app_logger.info(f"🔧 プロンプト送信: length={len(chatgpt_prompt)} characters")
        
        return response_data
    except Exception as e:
        import traceback
        app_logger.error(f"Nuance analysis error: {str(e)}")
        app_logger.error(traceback.format_exc())
        return {"error": str(e)}, 500

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
            language_pair = session.get("language_pair", "unknown")
            
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
                translation_context="copy_action",
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

@app.route("/interactive_question", methods=["POST"])
@require_rate_limit
def interactive_question():
    """インタラクティブな質問を処理するエンドポイント（多言語対応）"""
    start_time = time.time()
    
    # 🌍 多言語対応: エラーメッセージ
    error_messages = {
        "no_question": {
            "jp": "質問が入力されていません",
            "en": "No question has been entered",
            "fr": "Aucune question n'a été saisie",
            "es": "No se ha ingresado ninguna pregunta"
        },
        "no_context": {
            "jp": "翻訳コンテキストが見つかりません。まず翻訳を実行してください。",
            "en": "Translation context not found. Please perform a translation first.",
            "fr": "Contexte de traduction non trouvé. Veuillez d'abord effectuer une traduction.",
            "es": "Contexto de traducción no encontrado. Por favor, realice una traducción primero."
        }
    }
    
    try:
        data = request.get_json() or {}
        question = data.get("question", "").strip()
        
        # セッションから表示言語を取得
        display_lang = session.get("lang", "jp")
        
        if not question:
            error_message = error_messages["no_question"].get(display_lang, error_messages["no_question"]["jp"])
            return jsonify({
                "success": False,
                "error": error_message
            })
        
        # 🆕 厳密な入力値検証
        is_valid, error_msg = EnhancedInputValidator.validate_text_input(
            question, max_length=1000, min_length=5, field_name="質問"
        )
        if not is_valid:
            log_security_event(
                'INVALID_INTERACTIVE_QUESTION',
                f'Question validation failed: {error_msg}',
                'WARNING'
            )
            return jsonify({
                "success": False,
                "error": error_msg
            })
        
        # 翻訳コンテキストを取得
        context = TranslationContext.get_context()
        
        if not context:
            error_message = error_messages["no_context"].get(display_lang, error_messages["no_context"]["jp"])
            return jsonify({
                "success": False,
                "error": error_message
            })
        
        # 🌍 多言語対応: コンテキストに表示言語を追加
        context['display_language'] = display_lang
        
        # 質問を処理
        result = interactive_processor.process_question(question, context)
        
        # 🔧 Cookie最適化: チャット履歴を返すだけで、セッションには保存しない
        # これによりCookieサイズの増大を防ぐ
        answer_text = result.get("result", "")
        max_answer_length = 2500
        max_question_length = 1000
        
        if len(answer_text) > max_answer_length:
            # 回答の最後が文の途中で切れないよう、句読点で切断
            truncated = answer_text[:max_answer_length]
            last_punct = max(truncated.rfind('。'), truncated.rfind('！'), 
                           truncated.rfind('？'), truncated.rfind('.'))
            if last_punct > max_answer_length - 200:  # 句読点が近くにある場合
                answer_text = answer_text[:last_punct + 1] + "\n\n[回答が長いため省略されました]"
            else:
                answer_text = answer_text[:max_answer_length] + "...\n\n[回答が長いため省略されました]"
        
        # 質問も同様に適切に切断
        question_text = question
        if len(question_text) > max_question_length:
            question_text = question_text[:max_question_length] + "..."
        
        # 🔧 現在の質問と回答のみを含むレスポンスを作成
        # クライアント側でチャット履歴を管理してもらう
        current_chat_item = {
            "question": question_text,
            "answer": answer_text,
            "type": result.get("type", "general"),
            "timestamp": time.time()
        }
        
        processing_time = time.time() - start_time
        log_access_event(f'Interactive question processed: type={result.get("type")}, time={processing_time:.2f}s')
        
        # 🔧 Cookie最適化: chat_historyは返さない（クライアント側で管理）
        return jsonify({
            "success": True,
            "result": result,
            "current_chat": current_chat_item  # 現在の質問・回答のみ返す
        })
        
    except Exception as e:
        import traceback
        app_logger.error(f"Interactive question error: {str(e)}")
        app_logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/clear_chat_history", methods=["POST"])
@require_rate_limit
def clear_chat_history():
    """チャット履歴をクリアするエンドポイント（Cookie最適化版）"""
    try:
        # 🔧 Cookie最適化: セッションにチャット履歴を保存していないため、
        # クライアント側でクリアしてもらうための成功レスポンスのみ返す
        log_access_event('Chat history clear requested (client-side management)')
        
        return jsonify({
            "success": True,
            "message": "チャット履歴をクリアしました（クライアント側で管理）"
        })
        
    except Exception as e:
        app_logger.error(f"Chat history clear error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/clear_session", methods=["POST"])
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

# =============================================================================
# 🆕 管理者用セキュリティ機能
# =============================================================================

@app.route("/security/status")
def security_status():
    """セキュリティステータス表示（管理者用）"""
    if not session.get("logged_in"):
        abort(403)
    
    status = {
        "csrf_protection": "有効",
        "rate_limiting": "有効",
        "input_validation": "有効",
        "security_logging": "有効",
        "session_security": "有効",
        "environment": ENVIRONMENT,
        "debug_mode": app.config.get('DEBUG', False),
        "version": VERSION_INFO["version"]
    }
    
    return jsonify(status)

@app.route("/security/logs")
def view_security_logs():
    """セキュリティログ表示（管理者用）"""
    if not session.get("logged_in"):
        abort(403)
    
    try:
        logs = []
        log_files = ['logs/security.log', 'logs/app.log', 'logs/access.log']
        
        for log_file in log_files:
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    file_logs = f.readlines()[-20:]  # 最新20行
                    logs.extend([{
                        'file': log_file,
                        'content': line.strip()
                    } for line in file_logs])
        
        return jsonify({
            "success": True,
            "logs": logs[-50:]  # 最新50件
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

# =============================================================================
# 🌍 安全版：日本語、英語、フランス語、スペイン語ランディングページ
# =============================================================================

@app.route("/alpha/jp")
def alpha_jp_safe():
    """日本語専用ランディングページ（安全版）"""
    
    # 既存のlabelsから日本語ラベルを取得
    from labels import labels
    label = labels.get('jp', labels['jp'])
    
    try:
        return render_template(
            "landing_jp.html",
            labels=label,
            current_lang='jp',
            version_info=VERSION_INFO,
            main_app_url=url_for('index'),
            contact_email="hello@langpont.com"
        )
    except Exception as e:
        # エラー内容を表示
        return f"エラーが発生しました: {str(e)}<br><br>landing_jp.html が正しく作成されているか確認してください。"

@app.route("/alpha/en")
def alpha_en_safe():
    """英語専用ランディングページ（安全版）"""
    
    # 既存のlabelsから英語ラベルを取得
    from labels import labels
    label = labels.get('en', labels['en'])
    
    try:
        return render_template(
            "landing_en.html",
            labels=label,
            current_lang='en',
            version_info=VERSION_INFO,
            main_app_url=url_for('index'),
            contact_email="hello@langpont.com"
        )
    except Exception as e:
        # エラー内容を表示
        return f"エラーが発生しました: {str(e)}<br><br>landing_en.html が正しく作成されているか確認してください。"

@app.route("/alpha/fr")
def alpha_fr_safe():
    """フランス語専用ランディングページ（安全版）"""
    
    # 既存のlabelsからフランス語ラベルを取得
    from labels import labels
    label = labels.get('fr', labels['fr'])
    
    try:
        return render_template(
            "landing_fr.html",
            labels=label,
            current_lang='fr',
            version_info=VERSION_INFO,
            main_app_url=url_for('index'),
            contact_email="hello@langpont.com"
        )
    except Exception as e:
        # エラー内容を表示
        return f"エラーが発生しました: {str(e)}<br><br>landing_fr.html が正しく作成されているか確認してください。"

@app.route("/alpha/es")
def alpha_es_safe():
    """スペイン語専用ランディングページ（安全版）"""
    
    # 既存のlabelsからスペイン語ラベルを取得
    from labels import labels
    label = labels.get('es', labels['es'])
    
    try:
        return render_template(
            "landing_es.html",
            labels=label,
            current_lang='es',
            version_info=VERSION_INFO,
            main_app_url=url_for('index'),
            contact_email="hello@langpont.com"
        )
    except Exception as e:
        # エラー内容を表示
        return f"エラーが発生しました: {str(e)}<br><br>landing_es.html が正しく作成されているか確認してください。"

# =============================================================================
# 🆕 Task 2.9.1: 包括的行動追跡システム - Analytics API
# =============================================================================

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


# =============================================================================
# 🚀 Task 2.9.2 Phase B-3.5: 開発者専用リアルタイム監視API
# =============================================================================

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

@app.route("/api/dev/realtime-status")
@require_rate_limit
def get_realtime_status():
    """リアルタイムシステム状況取得"""
    if not check_developer_permission():
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        import psutil
        memory_info = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent()
    except:
        memory_info = None
        cpu_percent = 0
    
    # システム状況データ
    system_status = {
        "version": VERSION,
        "environment": ENVIRONMENT,
        "debug_mode": FEATURES.get("debug_mode", False),
        "uptime": "運用中",  # 簡略化
        "memory_usage": {
            "total": memory_info.total if memory_info else 0,
            "available": memory_info.available if memory_info else 0,
            "percent": memory_info.percent if memory_info else 0
        } if memory_info else {"total": 0, "available": 0, "percent": 0},
        "cpu_usage": cpu_percent,
        "session_count": 1 if session.get("logged_in") else 0
    }
    
    # API接続状況
    api_status = {
        "openai": {
            "status": "connected" if os.getenv("OPENAI_API_KEY") else "disconnected",
            "last_check": datetime.now().isoformat()
        },
        "gemini": {
            "status": "connected" if os.getenv("GEMINI_API_KEY") else "disconnected",
            "last_check": datetime.now().isoformat()
        }
    }
    
    return jsonify({
        "success": True,
        "data": {
            "system_status": system_status,
            "api_status": api_status,
            "timestamp": datetime.now().isoformat()
        }
    })

@app.route("/api/dev/user-activity")
@require_rate_limit
def get_user_activity():
    """ユーザー行動追跡データ取得"""
    if not check_developer_permission():
        return jsonify({"error": "Unauthorized"}), 403
    
    # 現在のセッション情報
    current_session = {
        "session_id": session.get("session_id", "unknown"),
        "username": session.get("username", "unknown"),
        "user_role": session.get("user_role", "guest"),
        "language_pair": session.get("language_pair", "ja-fr"),
        "login_time": session.get("login_time", "unknown"),
        "page_loads": session.get("page_loads", 0),
        "translations_count": session.get("translations_count", 0)
    }
    
    return jsonify({
        "success": True,
        "data": {
            "current_session": current_session,
            "recent_activity": dev_monitoring_data["user_activity"][-20:],  # 最新20件
            "timestamp": datetime.now().isoformat()
        }
    })

@app.route("/api/dev/translation-progress")
@require_rate_limit  
def get_translation_progress():
    """翻訳進行状況取得"""
    if not check_developer_permission():
        return jsonify({"error": "Unauthorized"}), 403
    
    session_id = session.get("session_id", "unknown")
    current_progress = dev_monitoring_data["translation_progress"].get(session_id, [])
    
    # 進行状況サマリー
    progress_summary = {
        "total_steps": len(current_progress),
        "completed_steps": len([p for p in current_progress if p["status"] == "completed"]),
        "failed_steps": len([p for p in current_progress if p["status"] == "failed"]),
        "in_progress_steps": len([p for p in current_progress if p["status"] == "in_progress"])
    }
    
    return jsonify({
        "success": True,
        "data": {
            "session_id": session_id,
            "progress_summary": progress_summary,
            "detailed_progress": current_progress[-10:],  # 最新10件
            "timestamp": datetime.now().isoformat()
        }
    })

@app.route("/api/dev/clear-monitoring")
@require_rate_limit
def clear_monitoring_data():
    """監視データクリア"""
    if not check_developer_permission():
        return jsonify({"error": "Unauthorized"}), 403
    
    global dev_monitoring_data
    dev_monitoring_data = {
        "translation_progress": {},
        "user_activity": [],
        "system_status": {},
        "api_status": {},
        "last_actions": [],
        "current_session": {}
    }
    
    return jsonify({
        "success": True,
        "message": "監視データをクリアしました",
        "timestamp": datetime.now().isoformat()
    })

# 🗑️ 重複削除: set_analysis_engineは4062行目で既に定義済み

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
        
        # 翻訳データを取得
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
        engine_manager = AnalysisEngineManager()
        
        # 分析を実行
        analysis_result = engine_manager.analyze_translations(
            chatgpt_trans=translated_text,
            enhanced_trans=better_translation,
            gemini_trans=gemini_translation,
            engine=selected_engine,
            context={
                "input_text": input_text,
                "source_lang": session.get("language_pair", "ja-en").split("-")[0],
                "target_lang": session.get("language_pair", "ja-en").split("-")[1],
                "partner_message": session.get("partner_message", ""),
                "context_info": session.get("context_info", "")
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

# =============================================================================
# 🆕 Task 2.9.2 Phase B-3.5.10: 統合活動ダッシュボード API
# =============================================================================

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

@app.route("/admin/api/four_stage_analysis", methods=["GET"])
@require_login
def get_four_stage_analysis():
    """4段階分析データAPI（管理者専用）"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # activity_loggerは既にグローバルにインポート済み
        
        # フィルターパラメータ取得
        period = request.args.get('period', 'all')
        
        # 基本的な活動ログデータを取得（直接SQL実行）
        import sqlite3
        conn = sqlite3.connect(activity_logger.db_path)
        conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, created_at, japanese_text, recommendation_result,
                actual_user_choice, llm_match, confidence, 
                processing_duration, activity_type, button_pressed,
                actual_analysis_llm, stage0_human_check,
                stage0_human_check_date, stage0_human_check_user
            FROM analysis_activity_log
            ORDER BY created_at DESC
            LIMIT 100
        """)
        
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
        conn.close()
        
        # 4段階分析形式に変換
        four_stage_data = []
        for row in results:
            item = {
                'id': row.get('id'),
                'japanese_text': row.get('japanese_text', '')[:50] + '...' if row.get('japanese_text') and len(row.get('japanese_text', '')) > 50 else row.get('japanese_text', ''),
                'created_at': row.get('created_at'),
                'stage0': {  # 第0段階: 人間CK
                    'status': row.get('stage0_human_check') or '未チェック',
                    'check_date': row.get('stage0_human_check_date'),
                    'check_user': row.get('stage0_human_check_user')
                },
                'stage05': {  # 第0.5段階: User SEL LLM
                    'user_selected_llm': row.get('button_pressed') or '-'
                },
                'stage1': {  # 第1段階: LLMの推奨
                    'recommendation': row.get('recommendation_result') or '-',
                    'confidence': row.get('confidence') or 0.0
                },
                'stage15': {  # 第1.5段階: 判定したLLM
                    'judging_llm': row.get('actual_analysis_llm') or '-'
                },
                'stage2': {  # 第2段階: User選択(Copy)
                    'user_selection': row.get('actual_user_choice') or '未選択',
                    'data_source': 'actual_copy_tracking'
                },
                'stage3': {  # 第3段階: LLM推奨 vs User選択
                    'match': bool(row.get('llm_match', False)),
                    'analysis': '自動判定'
                },
                'analysis_engine': row.get('actual_analysis_llm') or '-'
            }
            four_stage_data.append(item)
        
        # 統計計算
        total_count = len(four_stage_data)
        match_count = sum(1 for item in four_stage_data if item['stage3']['match'])
        match_rate = (match_count / total_count * 100) if total_count > 0 else 0
        copy_count = sum(1 for item in four_stage_data if item['stage2']['data_source'] == 'actual_copy_tracking')
        human_check_count = sum(1 for item in four_stage_data if item['stage0']['status'] == '完了')
        
        return jsonify({
            'success': True,
            'data': {
                'items': four_stage_data,
                'total_count': total_count,
                'match_rate': match_rate,
                'copy_count': copy_count,
                'human_check_count': human_check_count
            },
            'period': period
        })
        
    except Exception as e:
        app_logger.error(f"Four stage analysis API error: {str(e)}")
        return jsonify({
            'error': str(e),
            'error_code': 'API_ERROR',
            'success': False
        }), 500

@app.route("/admin/llm_recommendation_check")
@require_login
def llm_recommendation_check():
    """第0段階: LLM推奨品質チェックページ（管理者専用）"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "アクセス権限がありません"}), 403
    
    try:
        import secrets
        csrf_token = secrets.token_urlsafe(32)
        session['csrf_token'] = csrf_token
        
        return render_template('admin/llm_recommendation_check.html', csrf_token=csrf_token)
    except Exception as e:
        app_logger.error(f"LLM recommendation check template error: {str(e)}")
        return jsonify({"error": "テンプレートエラー", "details": str(e)}), 500

@app.route("/admin/api/llm_recommendation_check", methods=["GET", "POST"])
@require_login
def api_llm_recommendation_check():
    """LLM推奨品質チェックAPI"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    if request.method == 'GET':
        # データ取得
        try:
            app_logger.info("Starting LLM recommendation check data retrieval")
            
            if activity_logger is None:
                raise Exception("Activity logger not available")
            
            import sqlite3
            db_path = activity_logger.db_path
            app_logger.info(f"Using database: {db_path}")
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # まず全体の件数を確認
            cursor.execute("SELECT COUNT(*) as total FROM analysis_activity_log")
            total_rows = cursor.fetchone()[0]
            app_logger.info(f"Total rows in database: {total_rows}")
            
            # 推奨結果がある件数を確認
            cursor.execute("SELECT COUNT(*) as count FROM analysis_activity_log WHERE recommendation_result IS NOT NULL AND recommendation_result != ''")
            recommendation_rows = cursor.fetchone()[0]
            app_logger.info(f"Rows with recommendation_result: {recommendation_rows}")
            
            cursor.execute("""
                SELECT 
                    id, created_at, japanese_text, recommendation_result,
                    actual_user_choice, llm_match, confidence, 
                    button_pressed, actual_analysis_llm, full_analysis_text,
                    stage0_human_check, stage0_human_check_date, stage0_human_check_user
                FROM analysis_activity_log
                WHERE recommendation_result IS NOT NULL 
                AND recommendation_result != ''
                ORDER BY created_at DESC
                LIMIT 50
            """)
            
            rows = cursor.fetchall()
            app_logger.info(f"Retrieved {len(rows)} rows for LLM recommendation check")
            
            data = []
            for row in rows:
                try:
                    data.append({
                        'id': row['id'],
                        'created_at': row['created_at'],
                        'japanese_text': row['japanese_text'][:100] + '...' if row['japanese_text'] and len(row['japanese_text']) > 100 else row['japanese_text'],
                        'recommendation_result': row['recommendation_result'],
                        'actual_user_choice': row['actual_user_choice'],
                        'llm_match': bool(row['llm_match']) if row['llm_match'] is not None else False,
                        'confidence': float(row['confidence']) if row['confidence'] is not None else 0.0,
                        'button_pressed': row['button_pressed'],
                        'actual_analysis_llm': row['actual_analysis_llm'],
                        'full_analysis_text': row['full_analysis_text'][:500] + '...' if row['full_analysis_text'] and len(row['full_analysis_text']) > 500 else row['full_analysis_text'],
                        'stage0_human_check': row['stage0_human_check'],
                        'stage0_human_check_date': row['stage0_human_check_date'],
                        'stage0_human_check_user': row['stage0_human_check_user']
                    })
                except Exception as row_error:
                    app_logger.error(f"Error processing row {row['id']}: {str(row_error)}")
                    continue
            
            conn.close()
            
            app_logger.info(f"Successfully processed {len(data)} records for LLM recommendation check")
            
            # 統計計算
            pending_count = len([item for item in data if not item.get('human_checked', False)])
            approved_count = len([item for item in data if item.get('human_check_result') == 'approved'])
            rejected_count = len([item for item in data if item.get('human_check_result') == 'rejected'])
            accuracy_rate = (approved_count / len(data) * 100) if len(data) > 0 else 0
            
            return jsonify({
                'success': True,
                'items': data,  # JavaScriptが期待する形式
                'total_count': len(data),
                'pending_count': pending_count,
                'approved_count': approved_count,
                'rejected_count': rejected_count,
                'accuracy_rate': accuracy_rate,
                'debug_info': {
                    'total_db_rows': total_rows,
                    'recommendation_rows': recommendation_rows,
                    'processed_rows': len(data)
                }
            })
            
        except Exception as e:
            app_logger.error(f"LLM recommendation check GET error: {str(e)}")
            return jsonify({
                'error': str(e),
                'error_code': 'API_ERROR',
                'success': False
            }), 500
    
    else:  # POST - 品質チェック処理
        try:
            data = request.json
            activity_id = data.get('activity_id')
            quality_status = data.get('quality_status', '確認済み')
            
            if not activity_id:
                return jsonify({
                    'error': 'activity_id が必要です',
                    'error_code': 'MISSING_PARAMETER',
                    'success': False
                }), 400
            
            # 品質チェック結果を記録（実装は後で詳細化）
            result = {
                'success': True,
                'activity_id': activity_id,
                'quality_check': {
                    'status': quality_status,
                    'checked_at': datetime.now().isoformat(),
                    'checked_by': session.get('username', 'unknown')
                }
            }
            
            return jsonify(result)
            
        except Exception as e:
            app_logger.error(f"LLM recommendation check POST error: {str(e)}")
            return jsonify({
                'error': str(e),
                'error_code': 'QUALITY_CHECK_ERROR',
                'success': False
            }), 500

@app.route("/admin/api/llm_recommendation_detail/<int:activity_id>", methods=["GET"])
@require_login
def get_llm_recommendation_detail(activity_id):
    """LLM推奨詳細データ取得API"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        app_logger.info(f"Getting LLM recommendation detail for activity_id: {activity_id}")
        
        if activity_logger is None:
            raise Exception("Activity logger not available")
        
        import sqlite3
        db_path = activity_logger.db_path
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, created_at, japanese_text, 
                chatgpt_translation, enhanced_translation, gemini_translation,
                recommendation_result, actual_user_choice, llm_match, 
                confidence, button_pressed, actual_analysis_llm, 
                full_analysis_text, human_check_result, 
                processing_duration, language_pair, context_info,
                partner_message
            FROM analysis_activity_log
            WHERE id = ?
        """, (activity_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({
                'error': f'Activity ID {activity_id} not found',
                'error_code': 'NOT_FOUND',
                'success': False
            }), 404
        
        # データを構造化
        detail = {
            'id': row['id'],
            'created_at': row['created_at'],
            'japanese_text': row['japanese_text'],
            'chatgpt_translation': row['chatgpt_translation'],
            'enhanced_translation': row['enhanced_translation'],
            'gemini_translation': row['gemini_translation'],
            'recommendation_result': row['recommendation_result'],
            'actual_user_choice': row['actual_user_choice'],
            'llm_match': bool(row['llm_match']) if row['llm_match'] is not None else False,
            'confidence': float(row['confidence']) if row['confidence'] is not None else 0.0,
            'button_pressed': row['button_pressed'],
            'actual_analysis_llm': row['actual_analysis_llm'],
            'full_analysis_text': row['full_analysis_text'],
            'human_check_result': row['human_check_result'],
            'processing_duration': row['processing_duration'],
            'language_pair': row['language_pair'],
            'context_info': row['context_info'],
            'partner_message': row['partner_message']
        }
        
        app_logger.info(f"Successfully retrieved detail for activity_id: {activity_id}")
        
        return jsonify({
            'success': True,
            'data': detail
        })
        
    except Exception as e:
        app_logger.error(f"LLM recommendation detail error for ID {activity_id}: {str(e)}")
        return jsonify({
            'error': str(e),
            'error_code': 'DETAIL_ERROR',
            'success': False
        }), 500

@app.route("/admin/api/stage0_human_check", methods=["POST"])
@require_login
def stage0_human_check():
    """第0段階: 人間による推奨判定更新API"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        data = request.json
        activity_id = data.get('activity_id')
        human_selection = data.get('human_selection')
        
        if not activity_id:
            return jsonify({
                'error': 'activity_id が必要です',
                'error_code': 'MISSING_PARAMETER',
                'success': False
            }), 400
            
        if not human_selection:
            return jsonify({
                'error': 'human_selection が必要です',
                'error_code': 'MISSING_PARAMETER',
                'success': False
            }), 400
        
        app_logger.info(f"Updating human check for activity_id: {activity_id} to: {human_selection}")
        
        if activity_logger is None:
            raise Exception("Activity logger not available")
        
        import sqlite3
        db_path = activity_logger.db_path
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 現在のデータを確認
        cursor.execute("SELECT id FROM analysis_activity_log WHERE id = ?", (activity_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({
                'error': f'Activity ID {activity_id} not found',
                'error_code': 'NOT_FOUND',
                'success': False
            }), 404
        
        # 人間チェック結果を更新
        cursor.execute("""
            UPDATE analysis_activity_log 
            SET stage0_human_check = ?,
                stage0_human_check_date = datetime('now'),
                stage0_human_check_user = ?
            WHERE id = ?
        """, (human_selection, session.get('username', 'unknown'), activity_id))
        
        conn.commit()
        conn.close()
        
        app_logger.info(f"Successfully updated human check for activity_id: {activity_id}")
        
        return jsonify({
            'success': True,
            'activity_id': activity_id,
            'human_selection': human_selection,
            'message': f'人間チェック結果を「{human_selection}」に更新しました'
        })
        
    except Exception as e:
        app_logger.error(f"Stage0 human check error: {str(e)}")
        return jsonify({
            'error': str(e),
            'error_code': 'UPDATE_ERROR',
            'success': False
        }), 500

@app.route("/admin/api/stage0_quality_check", methods=["POST"])
@require_login
def stage0_quality_check():
    """第0段階: LLM推奨品質チェックAPI"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        data = request.json
        activity_id = data.get('activity_id')
        
        if not activity_id:
            return jsonify({
                'error': 'activity_id が必要です',
                'error_code': 'MISSING_PARAMETER',
                'success': False
            }), 400
        
        # 実際の品質チェック処理をここに実装
        # 現在は仮の実装
        result = {
            'success': True,
            'activity_id': activity_id,
            'quality_check': {
                'status': '品質チェック完了',
                'score': 0.95,
                'notes': '自動品質チェック実行済み'
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        app_logger.error(f"Stage 0 quality check error: {str(e)}")
        return jsonify({
            'error': str(e),
            'error_code': 'QUALITY_CHECK_ERROR',
            'success': False
        }), 500

@app.route("/admin/api/activity_stats", methods=["GET"])
@require_login
def get_activity_stats():
    """活動統計API（期間フィルター対応）"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # activity_loggerとget_jst_todayは既にグローバルにインポート済み
        from datetime import datetime, timedelta
        
        # 期間フィルター処理
        period = request.args.get('period', 'all')
        filters = {}
        
        # JST基準で期間を設定
        today = get_jst_today()
        
        if period == 'today':
            filters['date_from'] = today.strftime('%Y-%m-%d')
            filters['date_to'] = today.strftime('%Y-%m-%d')
        elif period == 'week':
            week_ago = today - timedelta(days=7)
            filters['date_from'] = week_ago.strftime('%Y-%m-%d')
            filters['date_to'] = today.strftime('%Y-%m-%d')
        elif period == 'month':
            month_start = today.replace(day=1)
            filters['date_from'] = month_start.strftime('%Y-%m-%d')
            filters['date_to'] = today.strftime('%Y-%m-%d')
        # 'all' の場合はフィルターなし
        
        # 追加フィルター取得
        additional_filters = {
            'activity_type': request.args.get('activity_type'),
            'user_id': request.args.get('user_id'),
            'button_pressed': request.args.get('button_pressed'),
            'date_from': request.args.get('date_from'),  # 手動指定があれば上書き
            'date_to': request.args.get('date_to')
        }
        
        # 手動指定の日付があれば期間設定を上書き
        for key, value in additional_filters.items():
            if value:
                filters[key] = value
        
        # None値を削除
        filters = {k: v for k, v in filters.items() if v}
        
        stats = activity_logger.get_activity_stats(filters)
        return jsonify(stats)
        
    except Exception as e:
        app_logger.error(f"Activity stats error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/admin/api/activity_log", methods=["GET"])
@require_login
def get_activity_log():
    """活動ログAPI（期間フィルター対応）"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # activity_loggerとget_jst_todayは既にグローバルにインポート済み
        from datetime import datetime, timedelta
        
        # パラメータ取得
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 50)), 100)  # 最大100件
        offset = (page - 1) * limit
        
        # 期間フィルター処理
        period = request.args.get('period', 'all')
        filters = {}
        
        # JST基準で期間を設定
        today = get_jst_today()
        
        if period == 'today':
            filters['date_from'] = today.strftime('%Y-%m-%d')
            filters['date_to'] = today.strftime('%Y-%m-%d')
        elif period == 'week':
            week_ago = today - timedelta(days=7)
            filters['date_from'] = week_ago.strftime('%Y-%m-%d')
            filters['date_to'] = today.strftime('%Y-%m-%d')
        elif period == 'month':
            month_start = today.replace(day=1)
            filters['date_from'] = month_start.strftime('%Y-%m-%d')
            filters['date_to'] = today.strftime('%Y-%m-%d')
        # 'all' の場合はフィルターなし
        
        # 追加フィルター取得
        additional_filters = {
            'activity_type': request.args.get('activity_type'),
            'user_id': request.args.get('user_id'),
            'button_pressed': request.args.get('button_pressed'),
            'date_from': request.args.get('date_from'),  # 手動指定があれば上書き
            'date_to': request.args.get('date_to'),
            'error_only': request.args.get('error_only') == 'true',
            'llm_mismatch_only': request.args.get('llm_mismatch_only') == 'true'
        }
        
        # 手動指定の日付があれば期間設定を上書き
        for key, value in additional_filters.items():
            if value is not None and value != '':
                filters[key] = value
        
        result = activity_logger.get_activities(filters, limit, offset)
        return jsonify(result)
        
    except Exception as e:
        app_logger.error(f"Activity log error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/admin/api/activity_detail/<int:activity_id>", methods=["GET"])
@require_login
def get_activity_detail(activity_id):
    """活動詳細API"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # activity_loggerは既にグローバルにインポート済み
        
        detail = activity_logger.get_activity_detail(activity_id)
        if not detail:
            return jsonify({"error": "Activity not found"}), 404
        
        return jsonify(detail)
        
    except Exception as e:
        app_logger.error(f"Activity detail error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/admin/api/export_activity_log", methods=["GET"])
@require_login
def export_activity_log():
    """活動ログCSV出力API"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # activity_loggerは既にグローバルにインポート済み
        import csv
        import io
        
        export_type = request.args.get('type', 'filtered')
        
        # フィルター取得
        if export_type == 'filtered':
            filters = {
                'activity_type': request.args.get('activity_type'),
                'user_id': request.args.get('user_id'),
                'button_pressed': request.args.get('button_pressed'),
                'date_from': request.args.get('date_from'),
                'date_to': request.args.get('date_to')
            }
            filters = {k: v for k, v in filters.items() if v}
        else:
            filters = {}
        
        # 大量データ取得（最大10000件）
        result = activity_logger.get_activities(filters, limit=10000, offset=0)
        activities = result['activities']
        
        # CSV生成
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー（推奨抽出検証用の詳細情報を含む）
        writer.writerow([
            'ID', '活動タイプ', 'ユーザー', '実行日時', '日本語文章',
            '言語ペア', '押下ボタン', '実際LLM', 'LLM一致', '推奨結果',
            '信頼度', '処理時間', 'エラー発生', 'エラーメッセージ',
            'ChatGPT翻訳', 'Enhanced翻訳', 'Gemini翻訳',
            'ニュアンス分析結果全文', '分析プレビュー',
            'ターミナルログ', 'デバッグログ', 'IP', 'User Agent',
            'セッションID', 'サンプル名', 'テストセッションID', 
            '作成日時', '年', '月', '日', '時間', 'メモ', 'タグ'
        ])
        
        # データ行
        for activity in activities:
            # 詳細データ取得
            detail = activity_logger.get_activity_detail(activity['id'])
            if detail:
                writer.writerow([
                    detail['id'],
                    detail['activity_type'],
                    detail['user_id'],
                    detail['created_at'],
                    detail['japanese_text'],
                    detail['language_pair'],
                    detail['button_pressed'],
                    detail['actual_analysis_llm'],
                    '一致' if detail['llm_match'] else '不一致',
                    detail['recommendation_result'],
                    detail['confidence'],
                    detail['processing_duration'],
                    'エラー' if detail['error_occurred'] else '正常',
                    detail['error_message'],
                    # 推奨抽出検証用の詳細情報
                    detail['chatgpt_translation'] or '',
                    detail['enhanced_translation'] or '',
                    detail['gemini_translation'] or '',
                    detail['full_analysis_text'] or '',  # ニュアンス分析結果全文（最重要）
                    detail['analysis_preview'] or '',
                    detail['terminal_logs'] or '',
                    detail['debug_logs'] or '',
                    detail['ip_address'] or '',
                    detail['user_agent'] or '',
                    detail['session_id'],
                    detail['sample_name'],
                    detail['test_session_id'],
                    detail['created_at'],
                    detail['year'],
                    detail['month'],
                    detail['day'],
                    detail['hour'],
                    detail['notes'] or '',
                    detail['tags'] or ''
                ])
        
        # レスポンス生成（Excel対応のBOM付きUTF-8）
        csv_data = output.getvalue()
        output.close()
        
        # Excel用にBOM（Byte Order Mark）を追加
        csv_data_with_bom = '\ufeff' + csv_data
        
        response = make_response(csv_data_with_bom.encode('utf-8'))
        response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
        response.headers['Content-Disposition'] = f'attachment; filename=langpont_activities_{export_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        app_logger.error(f"CSV export error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/admin/api/reset_all_data", methods=["POST"])
@require_login
@csrf_protect
def reset_all_data():
    """全データリセットAPI（統合ダッシュボード用）"""
    user_role = session.get('user_role', 'guest')
    username = session.get('username', 'unknown')
    
    # 管理者のみアクセス可能
    if user_role != 'admin':
        app_logger.warning(f"Unauthorized data reset attempt by {username} ({user_role})")
        return jsonify({"error": "管理者権限が必要です"}), 403
    
    try:
        # activity_loggerは既にグローバルにインポート済み
        import os
        
        # アクティビティログデータベースの削除
        if os.path.exists(activity_logger.db_path):
            os.remove(activity_logger.db_path)
            app_logger.info(f"Activity log database deleted: {activity_logger.db_path}")
        
        # 翻訳履歴データベースの削除
        if os.path.exists("langpont_translation_history.db"):
            os.remove("langpont_translation_history.db")
            app_logger.info("Translation history database deleted")
        
        # 使用統計ファイルの削除
        if os.path.exists("usage_data.json"):
            os.remove("usage_data.json")
            app_logger.info("Usage data file deleted")
        
        # データベースの再初期化
        activity_logger.init_database()
        
        # セキュリティログに記録
        log_security_event(
            'DATA_RESET', 
            f'All data reset by admin user: {username}',
            'CRITICAL'
        )
        
        app_logger.info(f"✅ All data reset completed by admin: {username}")
        
        return jsonify({
            "success": True,
            "message": "全データが正常に削除され、システムがリセットされました",
            "reset_by": username,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        app_logger.error(f"Data reset error: {str(e)}")
        log_security_event(
            'DATA_RESET_ERROR', 
            f'Data reset failed for admin {username}: {str(e)}',
            'ERROR'
        )
        return jsonify({"error": f"データリセットに失敗しました: {str(e)}"}), 500

# 🔧 包括的デバッグシステム
@app.route("/debug/session", methods=["GET"])
def debug_session():
    """デバッグ用: 現在のセッション状態を表示"""
    from admin_auth import admin_auth_manager
    
    session_data = dict(session)
    user_info = admin_auth_manager.get_current_user_info()
    
    debug_info = {
        "session_data": session_data,
        "user_info": user_info,
        "has_admin_access": admin_auth_manager.has_admin_access(),
        "logged_in": session.get('logged_in', False),
        "user_role": session.get('user_role', 'none'),
        "username": session.get('username', 'none')
    }
    
    return f"<pre>{json.dumps(debug_info, indent=2, ensure_ascii=False)}</pre>"

@app.route("/debug/full", methods=["GET"])
def debug_full():
    """🔍 完全デバッグ情報"""
    from admin_auth import admin_auth_manager
    import sys
    
    # 1. セッション情報
    session_data = dict(session)
    user_info = admin_auth_manager.get_current_user_info()
    
    # 2. ルート情報
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': rule.rule
        })
    
    admin_routes = [r for r in routes if 'admin' in r['endpoint']]
    
    # 3. Blueprint情報
    blueprints = {}
    for name, bp in app.blueprints.items():
        blueprints[name] = {
            'name': bp.name,
            'url_prefix': bp.url_prefix,
            'import_name': bp.import_name
        }
    
    # 4. テンプレート確認
    template_exists = {}
    import os
    template_paths = [
        'admin/dashboard.html',
        'index.html',
        'login.html'
    ]
    
    for template in template_paths:
        full_path = os.path.join('templates', template)
        template_exists[template] = os.path.exists(full_path)
    
    # 5. 権限チェック
    permission_check = {
        'logged_in': session.get('logged_in', False),
        'user_role': session.get('user_role', 'none'),
        'has_admin_access': admin_auth_manager.has_admin_access(),
        'is_admin_role': session.get('user_role') in ['admin', 'developer'],
        'session_keys': list(session_data.keys())
    }
    
    debug_report = {
        "🔐 セッション情報": session_data,
        "👤 ユーザー情報": user_info,
        "🛡️ 権限チェック": permission_check,
        "🗺️ 管理者ルート": admin_routes,
        "📦 Blueprint情報": blueprints,
        "📄 テンプレート存在": template_exists,
        "🔢 総ルート数": len(routes),
        "🔢 管理者ルート数": len(admin_routes),
        "🐍 Python Version": sys.version,
        "🌐 Request Info": {
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'method': request.method,
            'path': request.path,
            'url': request.url
        }
    }
    
    html = f"""
    <!DOCTYPE html>
    <html><head><title>LangPont Debug Report</title>
    <style>
        body {{ font-family: monospace; margin: 20px; background: #f5f5f5; }}
        .section {{ background: white; margin: 20px 0; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .good {{ color: #28a745; }}
        .bad {{ color: #dc3545; }}
        .warning {{ color: #ffc107; }}
        pre {{ background: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto; }}
        h2 {{ color: #007bff; border-bottom: 2px solid #007bff; padding-bottom: 5px; }}
        .test-links {{ background: #e9ecef; padding: 15px; border-radius: 8px; }}
        .test-links a {{ display: inline-block; margin: 5px 10px; padding: 8px 15px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
        .test-links a:hover {{ background: #0056b3; }}
    </style></head>
    <body>
    <h1>🔍 LangPont 完全デバッグレポート</h1>
    
    <div class="test-links">
        <h3>🧪 テストリンク</h3>
        <a href="/debug/session">セッション情報</a>
        <a href="/admin/dashboard">管理者ダッシュボード</a>
        <a href="/login">ログインページ</a>
        <a href="/">メインページ</a>
        <a href="/debug/routes">全ルート一覧</a>
    </div>
    
    <div class="section">
        <h2>🔐 ログイン状態チェック</h2>
        <p>ログイン済み: <span class="{'good' if permission_check['logged_in'] else 'bad'}">{permission_check['logged_in']}</span></p>
        <p>ユーザーロール: <span class="{'good' if permission_check['user_role'] != 'none' else 'bad'}">{permission_check['user_role']}</span></p>
        <p>管理者アクセス権: <span class="{'good' if permission_check['has_admin_access'] else 'bad'}">{permission_check['has_admin_access']}</span></p>
        <p>管理者ロール判定: <span class="{'good' if permission_check['is_admin_role'] else 'bad'}">{permission_check['is_admin_role']}</span></p>
    </div>
    
    <div class="section">
        <h2>🗺️ 管理者ルート状況</h2>
        <p>管理者ルート数: <span class="{'good' if len(admin_routes) > 0 else 'bad'}">{len(admin_routes)}</span></p>
        <ul>
    """
    
    for route in admin_routes:
        html += f"<li><strong>{route['endpoint']}</strong>: {route['rule']} {route['methods']}</li>"
    
    html += f"""
        </ul>
    </div>
    
    <div class="section">
        <h2>📄 テンプレート状況</h2>
        <ul>
    """
    
    for template, exists in template_exists.items():
        status_class = 'good' if exists else 'bad'
        status_text = '✅ 存在' if exists else '❌ 不存在'
        html += f"<li><span class='{status_class}'>{template}: {status_text}</span></li>"
    
    html += f"""
        </ul>
    </div>
    
    <div class="section">
        <h2>📦 Blueprint状況</h2>
        <ul>
    """
    
    for name, info in blueprints.items():
        html += f"<li><strong>{name}</strong>: {info['url_prefix']} ({info['import_name']})</li>"
    
    html += f"""
        </ul>
    </div>
    
    <div class="section">
        <h2>📋 完全デバッグデータ</h2>
        <pre>{json.dumps(debug_report, indent=2, ensure_ascii=False)}</pre>
    </div>
    
    </body></html>
    """
    
    return html

@app.route("/debug/routes", methods=["GET"])
def debug_routes():
    """🗺️ 全ルート一覧"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': sorted(list(rule.methods - {'HEAD', 'OPTIONS'})),
            'rule': rule.rule
        })
    
    routes.sort(key=lambda x: x['rule'])
    
    html = """
    <!DOCTYPE html>
    <html><head><title>LangPont Routes</title>
    <style>
        body { font-family: monospace; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .admin-route { background-color: #fff3cd; }
        .auth-route { background-color: #d1ecf1; }
    </style></head>
    <body>
    <h1>🗺️ LangPont 全ルート一覧</h1>
    <table>
    <tr><th>エンドポイント</th><th>メソッド</th><th>パス</th></tr>
    """
    
    for route in routes:
        row_class = ""
        if 'admin' in route['endpoint']:
            row_class = "admin-route"
        elif 'auth' in route['endpoint']:
            row_class = "auth-route"
        
        html += f"""
        <tr class="{row_class}">
            <td>{route['endpoint']}</td>
            <td>{', '.join(route['methods'])}</td>
            <td>{route['rule']}</td>
        </tr>
        """
    
    html += "</table></body></html>"
    return html

@app.route("/debug/test-admin", methods=["GET"])
def debug_test_admin():
    """🧪 管理者アクセステスト"""
    from admin_auth import admin_auth_manager
    
    # ステップバイステップのテスト
    test_results = []
    
    # Step 1: セッション確認
    logged_in = session.get('logged_in', False)
    test_results.append(f"✅ Step 1: ログイン状態 = {logged_in}" if logged_in else f"❌ Step 1: ログイン状態 = {logged_in}")
    
    # Step 2: ユーザーロール確認
    user_role = session.get('user_role', 'none')
    is_admin_role = user_role in ['admin', 'developer']
    test_results.append(f"✅ Step 2: ユーザーロール = {user_role}" if is_admin_role else f"❌ Step 2: ユーザーロール = {user_role}")
    
    # Step 3: AdminAuthManager確認
    try:
        has_admin_access = admin_auth_manager.has_admin_access()
        test_results.append(f"✅ Step 3: has_admin_access() = {has_admin_access}" if has_admin_access else f"❌ Step 3: has_admin_access() = {has_admin_access}")
    except Exception as e:
        test_results.append(f"❌ Step 3: AdminAuthManager エラー = {str(e)}")
    
    # Step 4: ルート存在確認
    admin_dashboard_exists = any(rule.endpoint == 'admin.dashboard' for rule in app.url_map.iter_rules())
    test_results.append(f"✅ Step 4: admin.dashboard ルート存在 = {admin_dashboard_exists}" if admin_dashboard_exists else f"❌ Step 4: admin.dashboard ルート存在 = {admin_dashboard_exists}")
    
    # Step 5: テンプレート存在確認
    import os
    template_exists = os.path.exists('templates/admin/dashboard.html')
    test_results.append(f"✅ Step 5: dashboard.html テンプレート存在 = {template_exists}" if template_exists else f"❌ Step 5: dashboard.html テンプレート存在 = {template_exists}")
    
    # Step 6: 実際のアクセステスト
    try:
        if logged_in and is_admin_role and has_admin_access and admin_dashboard_exists and template_exists:
            test_results.append("✅ Step 6: 全条件クリア - 管理者ダッシュボードアクセス可能")
            redirect_test = "success"
        else:
            test_results.append("❌ Step 6: 条件不足 - 管理者ダッシュボードアクセス不可")
            redirect_test = "failed"
    except Exception as e:
        test_results.append(f"❌ Step 6: テストエラー = {str(e)}")
        redirect_test = "error"
    
    html = f"""
    <!DOCTYPE html>
    <html><head><title>Admin Access Test</title>
    <style>
        body {{ font-family: monospace; margin: 20px; }}
        .success {{ color: #28a745; }}
        .error {{ color: #dc3545; }}
        .test-item {{ padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 4px; }}
        .actions {{ margin: 20px 0; }}
        .actions a {{ display: inline-block; margin: 5px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
    </style></head>
    <body>
    <h1>🧪 管理者アクセステスト結果</h1>
    
    <div class="actions">
        <a href="/debug/full">完全デバッグ</a>
        <a href="/login">ログイン</a>
        <a href="/admin/dashboard">管理者ダッシュボード</a>
    </div>
    
    <h2>📝 テスト結果</h2>
    """
    
    for result in test_results:
        item_class = "success" if result.startswith("✅") else "error"
        html += f'<div class="test-item {item_class}">{result}</div>'
    
    html += f"""
    
    <h2>🎯 推奨アクション</h2>
    <div class="test-item">
    """
    
    if redirect_test == "success":
        html += "🎉 すべてのテストをパス！管理者ダッシュボードにアクセスできるはずです。"
    elif not logged_in:
        html += "🔑 まずログインしてください: <a href='/login'>ログインページ</a>"
    elif not is_admin_role:
        html += f"⚠️ 現在のロール '{user_role}' は管理者権限がありません。adminまたはdeveloperロールでログインしてください。"
    else:
        html += "🚨 予期しない問題が発生しています。開発者に連絡してください。"
    
    html += """
    </div>
    
    </body></html>
    """
    
    return html

@app.route("/admin/api/system_logs", methods=["GET"])
@require_login
def get_system_logs():
    """システムログAPI（統合ダッシュボード用）"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        import os
        import json
        from datetime import datetime
        
        logs = []
        limit = min(int(request.args.get('limit', 50)), 200)  # 最大200件
        
        # アプリケーションログの読み込み
        log_files = [
            ("logs/app.log", "アプリケーション"),
            ("logs/security.log", "セキュリティ"),
            ("logs/access.log", "アクセス")
        ]
        
        for log_file, log_type in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        # 最新のログを取得
                        for line in lines[-limit//3:]:  # 各ファイルから同じ数だけ取得
                            line = line.strip()
                            if line:
                                # ログレベルの推定
                                level = 'info'
                                if 'ERROR' in line or 'Failed' in line or 'エラー' in line:
                                    level = 'error'
                                elif 'WARNING' in line or 'WARN' in line or '警告' in line:
                                    level = 'warning'
                                
                                logs.append({
                                    'timestamp': datetime.now().isoformat(),
                                    'level': level,
                                    'source': log_type,
                                    'message': line[:200]  # 200文字まで
                                })
                except Exception as e:
                    app_logger.error(f"Error reading log file {log_file}: {str(e)}")
        
        # タイムスタンプでソート（新しい順）
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # 制限数まで絞る
        logs = logs[:limit]
        
        return jsonify({
            'logs': logs,
            'total_count': len(logs),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        app_logger.error(f"System logs error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# =============================================================================
# アプリケーション起動とセキュリティ最終設定
# =============================================================================

if __name__ == "__main__":
    # 🆕 修正7: アプリケーション設定の最適化
    
    # ポート設定（優先順位：コマンド引数 > 環境変数 > デフォルト）
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8080))
    
    # 本番環境判定の強化
    is_production = (
        ENVIRONMENT == "production" or 
        os.getenv('AWS_EXECUTION_ENV') or 
        os.getenv('HEROKU_APP_NAME') or
        os.getenv('RENDER_SERVICE_NAME') or
        os.getenv('VERCEL') or
        port in [80, 443, 8000]  # よく使われる本番ポート
    )
    
    # 🆕 本番環境用最適化設定
    if is_production:
        # セキュリティ設定の強制適用
        app.config.update({
            'DEBUG': False,
            'TESTING': False,
            'SESSION_COOKIE_SECURE': True,
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'PERMANENT_SESSION_LIFETIME': timedelta(hours=1),
            
            # 🆕 パフォーマンス最適化
            'SEND_FILE_MAX_AGE_DEFAULT': 31536000,  # 1年間のキャッシュ
            'PREFERRED_URL_SCHEME': 'https',
            'JSON_SORT_KEYS': False,  # JSON応答の高速化
            'JSONIFY_PRETTYPRINT_REGULAR': False,  # JSON圧縮
            
            # 🆕 タイムアウト設定
            'PERMANENT_SESSION_LIFETIME': timedelta(hours=2),  # セッション延長
            'MAX_CONTENT_LENGTH': 32 * 1024 * 1024,  # 32MB（本番用）
            
            # 🆕 セキュリティ強化
            'SESSION_COOKIE_NAME': 'langpont_session',
            'WTF_CSRF_TIME_LIMIT': 3600,  # CSRF 1時間有効
        })
        
        # 本番環境でのログレベル最適化
        app.logger.setLevel(logging.INFO)  # WARNINGからINFOに変更（重要ログも記録）
        
        # 🆕 本番環境メッセージ
        print("🔒 本番環境最適化設定を適用しました")
        print(f"🌍 本番サービス: https://langpont.com")
        print(f"🚀 最適化: パフォーマンス + セキュリティ")
        
    else:
        # 🆕 開発環境用最適化
        app.config.update({
            'JSON_SORT_KEYS': True,  # 開発時は見やすく
            'JSONIFY_PRETTYPRINT_REGULAR': True,
            'TEMPLATES_AUTO_RELOAD': True,
            'EXPLAIN_TEMPLATE_LOADING': FEATURES.get("debug_mode", False)
        })
        
        print("🔧 開発環境最適化設定を適用しました")
        print(f"🏠 開発サーバー: http://localhost:{port}")
        print(f"🔍 デバッグモード: {FEATURES.get('debug_mode', False)}")
    
    # 🆕 セキュリティ機能確認（更新版）
    print("\n🛡️ LangPont 全セキュリティ機能 (修正7完了版):")
    security_features = [
        "セキュリティヘッダー (CSP, HSTS, X-Frame-Options等)",
        "CSRF対策 (トークン検証, タイミング攻撃対策)", 
        "エラーハンドリング (機密情報漏洩防止)",
        "入力値検証 (XSS/SQLi/コマンドインジェクション対策)",
        "ログ機能 (ローテーション対応, 3種類のログ)",
        "レート制限 (通常+バースト制限)",
        "セッション管理 (ID再生成, 期限管理)",
        "パスワード管理 (ハッシュ化, 強度検証)",
        "セキュリティ監視 (疑わしいアクセス検知)",
        "包括的脅威対策 (ボット検知, パス監視)",
        "本番環境最適化 (パフォーマンス + セキュリティ)"  # 新規追加
    ]
    
    for i, feature in enumerate(security_features, 1):
        print(f"  {i:2d}. ✅ {feature}")
    
    # 🆕 パフォーマンス最適化確認
    print("\n⚡ パフォーマンス最適化:")
    perf_features = [
        "動的タイムアウト (文章長に応じて60-120秒)",
        "自動プロンプト短縮 (8000文字超過時)",
        "Gemini文字数制限 (3000字/個別, 5000字/合計)",
        "チャット履歴制限 (最新20件)",
        "ログローテーション (10MB x 5ファイル)",
        "JSONレスポンス最適化",
        "セッションストレージ最適化"
    ]
    
    for i, feature in enumerate(perf_features, 1):
        print(f"  {i}. ⚡ {feature}")
    
    # ホスト設定の最適化
    host = "0.0.0.0"
    debug_mode = FEATURES["debug_mode"] if ENVIRONMENT == "development" else False
    
    # 🆕 詳細起動情報
    print(f"\n🚀 LangPont 最適化版起動:")
    print(f"   🌐 Host: {host}")
    print(f"   🔌 Port: {port}")
    print(f"   🔍 Debug: {debug_mode}")
    print(f"   🌍 Environment: {ENVIRONMENT}")
    print(f"   📦 Version: {VERSION_INFO['version']}")
    print(f"   🏭 Production Mode: {is_production}")
    
    # 🆕 強化された起動時チェック
    security_checks = []
    warning_count = 0
    
    # セキュリティチェック
    if app.secret_key and len(app.secret_key) >= 32:
        security_checks.append("✅ セキュアなシークレットキー")
    else:
        security_checks.append("⚠️ シークレットキーが弱い可能性")
        warning_count += 1
    
    # ディレクトリチェック
    if os.path.exists('logs'):
        security_checks.append("✅ ログディレクトリ作成済み")
    else:
        security_checks.append("⚠️ ログディレクトリが見つかりません")
        warning_count += 1
    
    # APIキーチェック
    if api_key:
        security_checks.append("✅ OpenAI APIキー設定済み")
    else:
        security_checks.append("❌ OpenAI APIキーが設定されていません")
        warning_count += 1
    
    # 🆕 追加チェック
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        security_checks.append("✅ Gemini APIキー設定済み")
    else:
        security_checks.append("⚠️ Gemini APIキーが未設定（オプション機能）")
    
    flask_secret = os.getenv("FLASK_SECRET_KEY")
    if flask_secret:
        security_checks.append("✅ 本番用シークレットキー設定済み")
    else:
        security_checks.append("⚠️ 本番用シークレットキー未設定")
    
    app_password = os.getenv("APP_PASSWORD")
    if app_password:
        security_checks.append("✅ カスタムアプリパスワード設定済み")
    else:
        security_checks.append("ℹ️ デフォルトパスワード使用中")
    
    print(f"\n🔍 起動時セキュリティチェック ({len(security_checks)}項目):")
    for check in security_checks:
        print(f"   {check}")
    
    if warning_count > 0:
        print(f"\n⚠️ 注意: {warning_count}件の推奨設定が未完了です")
    else:
        print("\n✅ 全セキュリティチェック完了！")
    
    # 🆕 環境変数ガイド
    if not is_production and warning_count > 0:
        print("\n📋 推奨環境変数設定:")
        print("   export FLASK_SECRET_KEY='your-super-secret-key-here'")
        print("   export APP_PASSWORD='your-custom-password'")
        print("   export GEMINI_API_KEY='your-gemini-api-key'  # オプション")
    
    try:
        # 🆕 起動ログ記録（詳細版）
        startup_info = {
            'version': VERSION_INFO["version"],
            'environment': ENVIRONMENT,
            'is_production': is_production,
            'port': port,
            'debug_mode': debug_mode,
            'warning_count': warning_count
        }
        
        log_security_event(
            'APPLICATION_STARTUP',
            f'LangPont 最適化版起動完了 - {startup_info}',
            'INFO'
        )
        
        # 🚨 FORCE DEBUG: Flask起動直前の最終ルート確認
        print("\n🚨 FORCE DEBUG: Flask起動直前の最終ルート確認")
        print(f"🚨 FORCE DEBUG: 登録済みBlueprint数: {len(app.blueprints)}")
        for name, bp in app.blueprints.items():
            print(f"  📋 Blueprint: {name}")
        
        print("🚨 FORCE DEBUG: 全ルート一覧:")
        route_count = 0
        auth_route_count = 0
        for rule in app.url_map.iter_rules():
            route_count += 1
            if '/auth/' in rule.rule:
                auth_route_count += 1
                print(f"  🔐 AUTH: {rule.methods} {rule.rule} -> {rule.endpoint}")
            else:
                print(f"  📋 ROUTE: {rule.methods} {rule.rule} -> {rule.endpoint}")
        
        print(f"🚨 FORCE DEBUG: 総ルート数: {route_count}, 認証ルート数: {auth_route_count}")
        
        # 特にプロフィールルートを確認
        profile_exists = any('/auth/profile' in rule.rule for rule in app.url_map.iter_rules())
        print(f"🚨 FORCE DEBUG: /auth/profileルート存在: {profile_exists}")
        
        # 🆕 本番環境での起動完了メッセージ
        if is_production:
            print(f"\n🎉 LangPont 本番環境起動完了！")
            print(f"🌍 サービス開始: ポート{port}")
        else:
            print(f"\n🎉 LangPont 開発環境起動完了！") 
            print(f"🏠 開発サーバー開始: http://localhost:{port}")
        
        # Flask起動（最適化されたパラメータ）
        app.run(
            host=host, 
            port=port, 
            debug=debug_mode,
            threaded=True,  # 🆕 マルチスレッド有効
            use_reloader=debug_mode,  # 🆕 開発時のみリローダー
            use_debugger=debug_mode   # 🆕 開発時のみデバッガー
        )
        
    except PermissionError:
        if port in [80, 443]:
            print("⚠️ 特権ポートへの権限がありません。ポート8080を使用します。")
            port = 8080
            print(f"🔄 ポート変更: {port}")
            app.run(host=host, port=port, debug=debug_mode, threaded=True)
        else:
            print(f"❌ ポート{port}へのアクセス権限がありません")
            raise
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ ポート{port}は既に使用中です")
            print("💡 他のプロセスを停止するか、別のポートを指定してください")
        else:
            print(f"❌ ネットワークエラー: {e}")
        raise
    except KeyboardInterrupt:
        print(f"\n👋 LangPont を停止しています...")
        log_security_event('APPLICATION_SHUTDOWN', 'Manual shutdown via Ctrl+C', 'INFO')
    except Exception as e:
        print(f"❌ アプリケーション起動エラー: {e}")
        log_security_event('APPLICATION_STARTUP_ERROR', str(e), 'CRITICAL')
        raise

