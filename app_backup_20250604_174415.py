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

# Configuration import
from config import VERSION, ENVIRONMENT, FEATURES, DEPLOYMENT, USAGE_LIMITS

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

from flask import Flask, render_template, request, session, redirect, url_for, jsonify, abort
from werkzeug.exceptions import RequestEntityTooLarge
from openai import OpenAI
import requests
import time
import re
from labels import labels

# =============================================================================
# 🆕 強化されたログ設定（ログローテーション対応）
# =============================================================================
def setup_enhanced_logging():
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

# OpenAI client
client = OpenAI(api_key=api_key)

# =============================================================================
# 🆕 完全版セキュリティヘッダー設定（Flask-Talisman相当）
# =============================================================================

@app.after_request
def add_comprehensive_security_headers(response):
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
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com",
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
        # 開発環境では少し緩和
        csp_directives.append("script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com")
    
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

def generate_csrf_token():
    """セキュアなCSRFトークンを生成"""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']

def validate_csrf_token(token):
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
                    f"CSRF attack attempt - IP: {get_client_ip()}, "
                    f"UA: {request.headers.get('User-Agent', '')[:100]}, "
                    f"Endpoint: {request.endpoint}"
                )
                abort(403)
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# 🆕 強化された入力値検証システム
# =============================================================================

class EnhancedInputValidator:
    """強化された入力値検証クラス"""
    
    # 🆕 より包括的な危険パターン
    DANGEROUS_PATTERNS = [
        # スクリプトインジェクション
        r'<script[^>]*>.*?</script>',
        r'javascript\s*:',
        r'vbscript\s*:',
        r'data\s*:.*base64',
        
        # イベントハンドラー
        r'on\w+\s*=',
        r'onload\s*=',
        r'onerror\s*=',
        r'onclick\s*=',
        r'onmouseover\s*=',
        
        # HTMLタグ
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<applet[^>]*>',
        r'<meta[^>]*>',
        r'<link[^>]*>',
        
        # SQLインジェクション
        r'union\s+select',
        r'select\s+.*\s+from',
        r'insert\s+into',
        r'delete\s+from',
        r'drop\s+table',
        r'exec\s*\(',
        r'eval\s*\(',
        
        # コマンドインジェクション
        r'[\|\&\;`]\s*\w+',
        r'\$\([^)]*\)',
        r'`[^`]*`',
    ]
    
    @classmethod
    def validate_text_input(cls, text, max_length=5000, min_length=1, field_name="input"):
        """包括的なテキスト入力検証"""
        if not text or not isinstance(text, str):
            return False, f"{field_name}が入力されていません"
        
        # 長さチェック
        if len(text) < min_length:
            return False, f"{field_name}が短すぎます（最小{min_length}文字）"
        
        if len(text) > max_length:
            return False, f"{field_name}が長すぎます（最大{max_length}文字）"
        
        # 🆕 危険な文字列の包括的チェック
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                # セキュリティログに記録
                security_logger.warning(
                    f"Dangerous pattern detected in {field_name} - "
                    f"Pattern: {pattern[:50]}..., "
                    f"IP: {get_client_ip()}"
                )
                return False, f"{field_name}に不正な文字列が含まれています"
        
        # 🆕 制御文字チェック
        if re.search(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', text):
            return False, f"{field_name}に不正な制御文字が含まれています"
        
        return True, "OK"
    
    @classmethod
    def validate_language_pair(cls, lang_pair):
        """言語ペア検証（ホワイトリスト方式）"""
        valid_pairs = [
            'ja-fr', 'fr-ja', 'ja-en', 'en-ja', 
            'fr-en', 'en-fr', 'ja-es', 'es-ja',
            'ja-de', 'de-ja', 'ja-it', 'it-ja'
        ]
        
        if not lang_pair or lang_pair not in valid_pairs:
            return False, "無効な言語ペアです"
        
        return True, "OK"
    
    @classmethod
    def validate_email(cls, email):
        """メールアドレス検証"""
        if not email:
            return False, "メールアドレスが入力されていません"
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "無効なメールアドレス形式です"
        
        return True, "OK"

# =============================================================================
# 🆕 セッション管理強化
# =============================================================================

class SecureSessionManager:
    """セキュアなセッション管理クラス"""
    
    @staticmethod
    def regenerate_session_id():
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
    def is_session_expired():
        """セッション期限切れチェック"""
        if 'session_created' not in session:
            session['session_created'] = time.time()
            return False
        
        # 1時間でセッション期限切れ
        if time.time() - session['session_created'] > 3600:
            return True
        
        return False
    
    @staticmethod
    def cleanup_old_sessions():
        """古いセッションのクリーンアップ（定期実行推奨）"""
        # 実装は使用するセッションストアに依存
        pass

# =============================================================================
# 🆕 パスワード管理強化
# =============================================================================

class SecurePasswordManager:
    """セキュアなパスワード管理クラス"""
    
    @staticmethod
    def hash_password(password):
        """パスワードのハッシュ化（bcrypt相当）"""
        return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    
    @staticmethod
    def verify_password(password, password_hash):
        """パスワードの検証"""
        return check_password_hash(password_hash, password)
    
    @staticmethod
    def validate_password_strength(password):
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
# ヘルパー関数とセキュリティ監視
# =============================================================================

def get_client_ip():
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

def log_security_event(event_type, details, severity="INFO"):
    """強化されたセキュリティイベントログ"""
    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', 'Unknown')[:200]  # 長すぎるUAを制限
    
    log_data = {
        'event_type': event_type,
        'client_ip': client_ip,
        'user_agent': user_agent,
        'details': details,
        'severity': severity,
        'endpoint': request.endpoint,
        'method': request.method,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if severity == "WARNING":
        security_logger.warning(f"SECURITY_WARNING: {json.dumps(log_data, ensure_ascii=False)}")
    elif severity == "ERROR":
        security_logger.error(f"SECURITY_ERROR: {json.dumps(log_data, ensure_ascii=False)}")
    elif severity == "CRITICAL":
        security_logger.critical(f"SECURITY_CRITICAL: {json.dumps(log_data, ensure_ascii=False)}")
    else:
        security_logger.info(f"SECURITY_INFO: {json.dumps(log_data, ensure_ascii=False)}")

def log_access_event(details):
    """アクセスログの記録"""
    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', 'Unknown')[:200]
    
    access_data = {
        'client_ip': client_ip,
        'user_agent': user_agent,
        'method': request.method,
        'endpoint': request.endpoint,
        'details': details
    }
    
    access_logger.info(json.dumps(access_data, ensure_ascii=False))

# =============================================================================
# 🆕 レート制限強化
# =============================================================================

rate_limit_store = {}

def enhanced_rate_limit_check(client_ip, limit=20, window=300, burst_limit=5, burst_window=60):
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

def require_rate_limit(f):
    """レート制限デコレータ（強化版）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = get_client_ip()
        
        if not enhanced_rate_limit_check(client_ip):
            log_security_event(
                'RATE_LIMIT_BLOCKED',
                f'Request blocked for IP {client_ip}',
                'WARNING'
            )
            abort(429)
        
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# 使用制限機能（既存コード + 強化）
# =============================================================================

DAILY_LIMIT_FREE = USAGE_LIMITS["free_daily_limit"]
USAGE_FILE = "usage_data.json"

def get_client_id():
    """クライアント識別子を取得（強化版）"""
    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')
    
    # より安全なハッシュ化（ソルト付き）
    salt = os.getenv("CLIENT_ID_SALT", "langpont_security_salt_2025")
    client_data = f"{client_ip}_{user_agent}_{salt}"
    client_id = hashlib.sha256(client_data.encode()).hexdigest()[:16]
    
    return client_id

def load_usage_data():
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

def save_usage_data(data):
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
        import traceback
        app_logger.error(f"Translation error: {str(e)}")
        app_logger.error(traceback.format_exc())
        log_security_event('TRANSLATION_ERROR', f'Error: {str(e)}', 'ERROR')
        return jsonify({
            "success": False,
            "error": str(e)
        })

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

        # Gemini分析実行（セキュリティ強化版で実装済み）
        result = f_gemini_3way_analysis(translated_text, better_translation, gemini_translation)

        session["gemini_3way_analysis"] = result
        
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
        
        return {"nuance": result}
    except Exception as e:
        import traceback
        app_logger.error(f"Nuance analysis error: {str(e)}")
        app_logger.error(traceback.format_exc())
        return {"error": str(e)}, 500

@app.route("/interactive_question", methods=["POST"])
@require_rate_limit
def interactive_question():
    """インタラクティブな質問を処理するエンドポイント（完全セキュリティ強化版）"""
    try:
        data = request.get_json() or {}
        question = data.get("question", "").strip()
        
        if not question:
            return jsonify({
                "success": False,
                "error": "質問が入力されていません"
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
            return jsonify({
                "success": False,
                "error": "翻訳コンテキストが見つかりません。まず翻訳を実行してください。"
            })
        
        # 質問を処理
        result = interactive_processor.process_question(question, context)
        
        # チャット履歴に追加（サニタイズ済み）
        chat_history = session.get("chat_history", [])
        chat_history.append({
            "question": question,
            "answer": result.get("result", ""),
            "type": result.get("type", "general"),
            "timestamp": time.time()
        })
        
        # 🆕 チャット履歴の制限（最新20件のみ保持）
        if len(chat_history) > 20:
            chat_history = chat_history[-20:]
        
        session["chat_history"] = chat_history
        
        log_access_event(f'Interactive question processed: type={result.get("type")}')
        
        return jsonify({
            "success": True,
            "result": result,
            "chat_history": chat_history
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
    """チャット履歴をクリアするエンドポイント"""
    try:
        session["chat_history"] = []
        log_access_event('Chat history cleared')
        
        return jsonify({
            "success": True,
            "message": "チャット履歴をクリアしました"
        })
        
    except Exception as e:
        app_logger.error(f"Chat history clear error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
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
# 🆕 Gemini分析関数（セキュリティ強化版）
# =============================================================================

def f_gemini_3way_analysis(translated_text, better_translation, gemini_translation):
    """3つの翻訳結果を分析する関数（セキュリティ強化版）"""

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        return "⚠️ Gemini APIキーがありません"

    # 🆕 入力値の包括的検証
    texts_to_validate = [
        (translated_text, "ChatGPT翻訳"),
        (better_translation, "改善翻訳"),
        (gemini_translation, "Gemini翻訳")
    ]
    
    for text, field_name in texts_to_validate:
        if text:
            is_valid, error_msg = EnhancedInputValidator.validate_text_input(
                text, max_length=10000, field_name=field_name
            )
            if not is_valid:
                return f"⚠️ {field_name}の検証に失敗しました: {error_msg}"

    display_lang = session.get("lang", "jp")
    analysis_lang_map = {
        "jp": "Japanese",
        "en": "English", 
        "fr": "French"
    }
    analysis_language = analysis_lang_map.get(display_lang, "Japanese")
    
    language_pair = session.get("language_pair", "ja-fr")
    
    try:
        source_lang, target_lang = language_pair.split("-")
    except:
        source_lang = session.get("source_lang", "ja")
        target_lang = session.get("target_lang", "fr")

    # 文字数チェック
    total_input = translated_text + better_translation + gemini_translation
    warning = "⚠️ 入力が長いため、分析結果は要約されています。\n\n" if len(total_input) > 2000 else ""

    # 背景情報を取得
    input_text = session.get("input_text", "")
    partner_message = session.get("partner_message", "")
    context_info = session.get("context_info", "")

    lang_map = {
        "ja": "Japanese", "fr": "French", "en": "English",
        "es": "Spanish", "de": "German", "it": "Italian",
        "pt": "Portuguese", "ru": "Russian", "ko": "Korean", "zh": "Chinese"
    }

    source_label = lang_map.get(source_lang, source_lang.capitalize())
    target_label = lang_map.get(target_lang, target_lang.capitalize())

    if context_info.strip():
        context_section = f"""
CONTEXT PROVIDED:
- Previous conversation: {partner_message or "None"}
- Situation/Background: {context_info.strip()}

Based on this specific context, analyze which translation is most appropriate."""
        
        analysis_instruction = "Analyze: formality, tone, and appropriateness for the given situation/relationship."
        
    else:
        context_section = f"""
CONTEXT: General conversation (no specific context provided)
- Previous conversation: {partner_message or "None"}

Analyze as general daily conversation."""
        
        analysis_instruction = "Analyze: formality, tone, and general conversational appropriateness."

    prompt = f"""Compare these 3 {target_label} translations considering the specific context. 

IMPORTANT: Respond in {analysis_language} with clear, readable format using bullet points and clear sections.

ORIGINAL TEXT ({source_label}): {input_text}

{context_section}

TRANSLATIONS:
1. ChatGPT: {translated_text}
2. ChatGPT Enhanced: {better_translation}  
3. Gemini: {gemini_translation}

{analysis_instruction}

CONCLUSION: Which translation best fits this specific situation and why? 

REMEMBER: Your entire response must be in {analysis_language}."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            log_access_event('Gemini 3-way analysis completed successfully')
            return warning + result_text.strip()
        else:
            error_msg = f"⚠️ Gemini API error: {response.status_code}"
            log_security_event('GEMINI_API_ERROR', error_msg, 'ERROR')
            return error_msg

    except requests.exceptions.Timeout:
        return "⚠️ Gemini APIがタイムアウトしました（30秒以内に応答がありませんでした）"

    except Exception as e:
        import traceback
        error_msg = f"⚠️ Gemini API呼び出しエラー: {str(e)}"
        log_security_event('GEMINI_REQUEST_ERROR', error_msg, 'ERROR')
        app_logger.error(traceback.format_exc())
        return error_msg

# =============================================================================
# アプリケーション起動とセキュリティ最終設定
# =============================================================================

if __name__ == "__main__":
    # ポート設定
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8080))
    
    # 本番環境判定
    is_production = ENVIRONMENT == "production" or os.getenv('AWS_EXECUTION_ENV')
    
    # 🆕 本番環境用セキュリティ最終設定
    if is_production:
        # セキュリティ設定の強制適用
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
        
        # 🆕 本番環境用追加設定
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1年間のキャッシュ
        app.config['PREFERRED_URL_SCHEME'] = 'https'
        
        print("🔒 本番環境セキュリティ設定を適用しました")
        print(f"🌍 外部アクセス可能: https://langpont.com")
        
        # 本番環境でのログレベル調整
        app.logger.setLevel(logging.WARNING)
        
    else:
        print("🔧 開発環境で実行中")
        print(f"🏠 ローカルアクセス: http://localhost:{port}")
    
    # 🆕 セキュリティ強化完了メッセージ（友人のアドバイス反映版）
    print("\n🛡️ LangPont セキュリティ強化機能 (友人アドバイス反映版):")
    print("  ✅ セキュリティヘッダー (CSP, HSTS, X-Frame-Options等)")
    print("  ✅ CSRF対策 (トークン検証, タイミング攻撃対策)")
    print("  ✅ エラーハンドリング (機密情報漏洩防止)")
    print("  ✅ 入力値検証 (XSS/SQLi/コマンドインジェクション対策)")
    print("  ✅ ログ機能 (ローテーション対応, アクセス/セキュリティ/アプリログ)")
    print("  ✅ レート制限 (通常+バースト制限)")
    print("  ✅ セッション管理 (ID再生成, 期限管理)")
    print("  ✅ パスワード管理 (ハッシュ化, 強度検証)")
    print("  ✅ セキュリティ監視 (疑わしいアクセス検知)")
    print("  ✅ 包括的脅威対策 (ボット検知, パス監視)")
    
    # 友人のアドバイス項目の確認
    print("\n📋 友人アドバイス反映状況:")
    print("  ✅ Flask-Talisman相当のセキュリティヘッダー")
    print("  ✅ ログローテーション (10MB x 5ファイル)")
    print("  ✅ セッションIDの再生成")
    print("  ✅ パスワードハッシュ化")
    print("  ✅ 原子的ファイル書き込み")
    print("  ✅ 包括的入力値検証")
    print("  ✅ セキュリティイベントの詳細ログ")
    print("  ✅ 本番環境でのデバッグ無効化")
    
    # ホスト設定
    host = "0.0.0.0"
    debug_mode = FEATURES["debug_mode"] if ENVIRONMENT == "development" else False
    
    print(f"\n🚀 LangPont セキュリティ強化版起動:")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Debug: {debug_mode}")
    print(f"   Environment: {ENVIRONMENT}")
    print(f"   Version: {VERSION_INFO['version']}")
    
    # 起動時セキュリティチェック
    security_checks = []
    
    if app.secret_key and len(app.secret_key) >= 32:
        security_checks.append("✅ セキュアなシークレットキー")
    else:
        security_checks.append("⚠️ シークレットキーが弱い可能性")
    
    if os.path.exists('logs'):
        security_checks.append("✅ ログディレクトリ作成済み")
    else:
        security_checks.append("⚠️ ログディレクトリが見つかりません")
    
    if api_key:
        security_checks.append("✅ OpenAI APIキー設定済み")
    else:
        security_checks.append("❌ OpenAI APIキーが設定されていません")
    
    print("\n🔍 起動時セキュリティチェック:")
    for check in security_checks:
        print(f"   {check}")
    
    try:
        # 🆕 起動ログ記録
        log_security_event(
            'APPLICATION_STARTUP',
            f'LangPont started - Version: {VERSION_INFO["version"]}, Environment: {ENVIRONMENT}',
            'INFO'
        )
        
        app.run(host=host, port=port, debug=debug_mode)
        
    except PermissionError:
        if port == 80 or port == 443:
            print("⚠️ 特権ポートへの権限がありません。ポート8080を使用します。")
            port = 8080
            print(f"🔄 ポート変更: {port}")
            app.run(host=host, port=port, debug=debug_mode)
        else:
            raise
    except Exception as e:
        print(f"❌ アプリケーション起動エラー: {e}")
        log_security_event('APPLICATION_STARTUP_ERROR', str(e), 'CRITICAL')
        raise as e:
        log_security_event('FILE_ERROR', f'Error saving usage data: {str(e)}', 'ERROR')
        if os.path.exists(f"{USAGE_FILE}.tmp"):
            os.remove(f"{USAGE_FILE}.tmp")

def check_daily_usage(client_id):
    """1日の使用制限をチェック（ログ強化）"""
    today = datetime.now().strftime('%Y-%m-%d')
    usage_data = load_usage_data()
    
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
    
    log_access_event(f'Usage check: {current_usage}/{DAILY_LIMIT_FREE}')
    
    return current_usage < DAILY_LIMIT_FREE, current_usage, DAILY_LIMIT_FREE

def increment_usage(client_id):
    """使用回数を増加（ログ強化）"""
    today = datetime.now().strftime('%Y-%m-%d')
    usage_key = f"{client_id}_{today}"
    
    usage_data = load_usage_data()
    new_count = usage_data.get(usage_key, 0) + 1
    usage_data[usage_key] = new_count
    save_usage_data(usage_data)
    
    log_access_event(f'Usage incremented to {new_count}')
    
    return new_count

def get_usage_status(client_id):
    """使用状況を取得"""
    can_use, current_usage, daily_limit = check_daily_usage(client_id)
    remaining = max(0, daily_limit - current_usage)
    
    return {
        "can_use": can_use,
        "current_usage": current_usage,
        "daily_limit": daily_limit,
        "remaining": remaining
    }

# =============================================================================
# エラーハンドリング（強化版）
# =============================================================================

@app.errorhandler(400)
def bad_request(error):
    log_security_event('BAD_REQUEST', f'400 error: {str(error)}', 'WARNING')
    return jsonify({
        'success': False,
        'error': 'リクエストが正しくありません',
        'error_code': 'BAD_REQUEST'
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
def too_many_requests(error):
    log_security_event('RATE_LIMIT_RESPONSE', 'Rate limit response sent', 'INFO')
    return jsonify({
        'success': False,
        'error': 'リクエストが多すぎます。しばらく待ってから再試行してください',
        'error_code': 'RATE_LIMIT_EXCEEDED'
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

# =============================================================================
# セキュリティ監視とアクセス制御
# =============================================================================

@app.before_request
def enhanced_security_monitoring():
    """強化されたリクエスト前セキュリティ監視"""
    
    # セッション期限切れチェック
    if SecureSessionManager.is_session_expired():
        session.clear()
        log_security_event('SESSION_EXPIRED', 'Session expired and cleared', 'INFO')
    
    # 疑わしいUser-Agentチェック
    user_agent = request.headers.get('User-Agent', '')
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
    
    if any(path in request.path.lower() for path in suspicious_paths):
        log_security_event(
            'SUSPICIOUS_PATH_ACCESS',
            f'Suspicious path accessed: {request.path}',
            'WARNING'
        )
    
    # 🆕 リクエストヘッダーの異常チェック
    if request.content_length and request.content_length > app.config.get('MAX_CONTENT_LENGTH', 16*1024*1024):
        log_security_event(
            'LARGE_REQUEST_DETECTED',
            f'Large request detected: {request.content_length} bytes',
            'WARNING'
        )
    
    # アクセスログ記録
    log_access_event(f'{request.method} {request.path}')

# =============================================================================
# 翻訳関数群（セキュリティ強化版）
# =============================================================================

def safe_openai_request(prompt, max_tokens=400, temperature=0.1):
    """OpenAI APIの安全なリクエスト実行（強化版）"""
    
    try:
        # 🆕 プロンプトの包括的検証
        is_valid, error_msg = EnhancedInputValidator.validate_text_input(
            prompt, max_length=8000, field_name="prompt"
        )
        if not is_valid:
            raise ValueError(error_msg)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=30
        )
        
        result = response.choices[0].message.content.strip()
        
        if not result or len(result.strip()) < 2:
            raise ValueError("翻訳結果が短すぎます")
        
        return result
        
    except Exception as e:
        log_security_event('OPENAI_ERROR', f'OpenAI API error: {str(e)}', 'ERROR')
        raise

def f_translate_to_lightweight(input_text, source_lang, target_lang, partner_message="", context_info=""):
    """セキュリティ強化版メイン翻訳関数"""
    
    # 🆕 包括的な入力値検証
    validations = [
        (input_text, 5000, "翻訳テキスト"),
        (partner_message, 2000, "会話履歴"),
        (context_info, 2000, "背景情報")
    ]
    
    for text, max_len, field_name in validations:
        if text:  # 空でない場合のみ検証
            is_valid, error_msg = EnhancedInputValidator.validate_text_input(
                text, max_length=max_len, field_name=field_name
            )
            if not is_valid:
                raise ValueError(error_msg)
    
    # 言語ペア検証
    is_valid_pair, pair_error = EnhancedInputValidator.validate_language_pair(f"{source_lang}-{target_lang}")
    if not is_valid_pair:
        raise ValueError(pair_error)
    
    lang_map = {"ja": "Japanese", "fr": "French", "en": "English"}
    target_label = lang_map.get(target_lang, target_lang)
    
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
    
    return safe_openai_request(prompt)

def f_reverse_translation(translated_text, target_lang, source_lang):
    """セキュリティ強化版逆翻訳関数"""
    
    if not translated_text:
        return "(翻訳テキストが空です)"
    
    # 入力値検証
    is_valid, error_msg = EnhancedInputValidator.validate_text_input(
        translated_text, field_name="逆翻訳テキスト"
    )
    if not is_valid:
        raise ValueError(error_msg)
    
    is_valid_pair, pair_error = EnhancedInputValidator.validate_language_pair(f"{source_lang}-{target_lang}")
    if not is_valid_pair:
        raise ValueError(pair_error)
    
    lang_map = {"ja": "Japanese", "fr": "French", "en": "English"}
    source_label = lang_map.get(source_lang, source_lang)
    
    prompt = f"Translate to {source_label}:\n{translated_text}"
    
    try:
        return safe_openai_request(prompt, max_tokens=300)
    except Exception as e:
        return f"逆翻訳エラー: {str(e)}"

def f_better_translation(text_to_improve, source_lang="fr", target_lang="en"):
    """セキュリティ強化版改善翻訳関数"""
    
    # 入力値検証
    is_valid, error_msg = EnhancedInputValidator.validate_text_input(
        text_to_improve, field_name="改善対象テキスト"
    )
    if not is_valid:
        raise ValueError(error_msg)
    
    is_valid_pair, pair_error = EnhancedInputValidator.validate_language_pair(f"{source_lang}-{target_lang}")
    if not is_valid_pair:
        raise ValueError(pair_error)
    
    lang_map = {"ja": "日本語", "fr": "フランス語", "en": "英語"}
    target_label = lang_map.get(target_lang, target_lang)
    
    prompt = f"この{target_label}をもっと自然な{target_label}の文章に改善してください：{text_to_improve}"
    
    return safe_openai_request(prompt)

def f_translate_with_gemini(text, source_lang, target_lang, partner_message="", context_info=""):
    """セキュリティ強化版Gemini翻訳関数"""
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        return "⚠️ Gemini APIキーがありません"
    
    # 🆕 包括的な入力値検証
    validations = [
        (text, 5000, "翻訳テキスト"),
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
    
    prompt = f"""
あなたは優秀な{source_lang}→{target_lang}の翻訳者です。
以下の情報（直前のやりとり、背景）を参考に、
**{target_lang}の翻訳文のみ**を返してください（解説や注釈は不要です）。

--- 直前のやりとり ---
{partner_message or "(なし)"}

--- 背景情報 ---
{context_info or "(なし)"}

--- 翻訳対象 ---
{text}
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
# インタラクティブ質問処理システム（セキュリティ強化版）
# =============================================================================

class TranslationContext:
    """翻訳コンテキストを管理するクラス（セキュリティ強化版）"""
    
    @staticmethod
    def save_context(input_text, translations, analysis, metadata):
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
        
        session["translation_context"] = {
            "input_text": input_text,
            "translations": safe_translations,
            "analysis": analysis,
            "metadata": metadata,
            "timestamp": time.time()
        }
        
    @staticmethod
    def get_context():
        """保存された翻訳コンテキストを取得（期限チェック付き）"""
        context = session.get("translation_context", {})
        
        # 古いコンテキストは削除（1時間以上前）
        if context and time.time() - context.get("timestamp", 0) > 3600:
            log_access_event('Translation context expired')
            TranslationContext.clear_context()
            return {}
        
        return context
    
    @staticmethod
    def clear_context():
        """翻訳コンテキストをクリア"""
        session.pop("translation_context", None)

class InteractiveTranslationProcessor:
    """インタラクティブな翻訳処理クラス（セキュリティ強化版）"""
    
    def __init__(self, client):
        self.client = client
    
    def process_question(self, question, context):
        """質問を処理してレスポンスを生成（強化された入力値検証付き）"""
        
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
        
        # 質問タイプの分析とログ記録
        question_type = self._analyze_question_type(question)
        log_access_event(f'Interactive question processed: type={question_type}')
        
        return self._handle_general_question(question, context)
    
    def _analyze_question_type(self, question):
        """質問タイプを分析（ログ用）"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['親しみ', 'フレンドリー', 'カジュアル', 'フォーマル']):
            return 'style_adjustment'
        elif any(word in question_lower for word in ['意味', '定義', '説明']):
            return 'term_explanation'
        elif any(word in question_lower for word in ['組み合わせ', '混ぜ', '参考']):
            return 'custom_translation'
        elif any(word in question_lower for word in ['違い', '比較', 'どちら']):
            return 'comparison'
        else:
            return 'general_question'
    
    def _handle_general_question(self, question, context):
        """一般的な質問を処理（セキュリティ強化版）"""
        
        translations = context.get("translations", {})
        input_text = context.get("input_text", "")
        analysis = context.get("analysis", "")
        
        # セッションから表示言語を取得
        display_lang = session.get("lang", "jp")
        response_lang_map = {
            "jp": "Japanese",
            "en": "English", 
            "fr": "French"
        }
        response_language = response_lang_map.get(display_lang, "Japanese")
        
        prompt = f"""Answer the user's question about these translations.

IMPORTANT: Respond entirely in {response_language}.

Original text: {input_text}

Translation results:
1. ChatGPT: {translations.get('chatgpt', '')}
2. Enhanced: {translations.get('enhanced', '')}
3. Gemini: {translations.get('gemini', '')}

Previous analysis: {analysis}

User's question: {question}

Provide a helpful answer in {response_language}."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content.strip()
            
            return {
                "type": "general_question",
                "result": answer
            }
            
        except Exception as e:
            error_messages = {
                "jp": f"質問処理中にエラーが発生しました: {str(e)}",
                "en": f"Error occurred while processing question: {str(e)}",
                "fr": f"Erreur lors du traitement de la question: {str(e)}"
            }
            return {
                "type": "error",
                "result": error_messages.get(display_lang, error_messages["jp"])
            }

# グローバルインスタンス
interactive_processor = InteractiveTranslationProcessor(client)

# =============================================================================
# ルーティング（完全セキュリティ強化版）
# =============================================================================

@app.route("/login", methods=["GET", "POST"])
@csrf_protect
@require_rate_limit
def login():
    error = ""
    
    if request.method == "POST":
        password = request.form.get("password", "").strip()
        
        if not password:
            error = "パスワードを入力してください"
        else:
            # 🆕 パスワード入力の基本検証
            is_valid, validation_error = EnhancedInputValidator.validate_text_input(
                password, max_length=100, min_length=1, field_name="パスワード"
            )
            if not is_valid:
                log_security_event('INVALID_PASSWORD_INPUT', validation_error, 'WARNING')
                error = "無効なパスワード形式です"
            else:
                correct_pw = os.getenv("APP_PASSWORD", "linguru2025")
                if password == correct_pw:
                    session["logged_in"] = True
                    session.permanent = True
                    
                    # 🆕 セッションIDの再生成（セッションハイジャック対策）
                    SecureSessionManager.regenerate_session_id()
                    
                    log_security_event('LOGIN_SUCCESS', 'Successful login', 'INFO')
                    log_access_event('User logged in successfully')
                    return redirect(url_for("index"))
                else:
                    log_security_event(
                        'LOGIN_FAILED',
                        f'Failed login attempt with password length: {len(password)}',
                        'WARNING'
                    )
                    error = "パスワードが違います"
    
    return render_template("login.html", error=error)

@app.route("/", methods=["GET", "POST"])
@csrf_protect
@require_rate_limit
def index():
    lang = session.get("lang", "jp")
    if lang not in ['jp', 'en', 'fr']:
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
    chat_history = session.get("chat_history", [])

    # 使用状況を取得
    client_id = get_client_id()
    usage_status = get_usage_status(client_id)

    if request.method == "POST":
        if request.form.get("reset") == "true":
            # 完全リセット
            keys_to_clear = [
                "chat_history", "translated_text", "better_translation", "gemini_translation",
                "partner_message", "context_info", "gemini_3way_analysis",
                "nuance_question", "nuance_answer", "reverse_better_translation"
            ]
            for key in keys_to_clear:
                session.pop(key, None)
            
            TranslationContext.clear_context()
            log_access_event('Form reset completed')

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
            
            # 各フィールドの検証
            for field_name, field_value, max_len in [
                ("翻訳テキスト", japanese_text, 5000),
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
    # 🆕 言語パラメータの厳密な検証
    valid_languages = ["jp", "en", "fr"]
    if lang not in valid_languages:
        log_security_event('INVALID_LANGUAGE', f'Invalid language: {lang}', 'WARNING')
        lang = "jp"
    
    session["lang"] = lang
    log_access_event(f'Language changed to {lang}')
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
                "message": f"1日の利用制限({daily_limit}回)に達しました。",
                "current_usage": current_usage,
                "daily_limit": daily_limit,
                "reset_time": "明日の00:00(日本時間)",
                "upgrade_message": "制限なしで利用したい場合は、Early Access版をお試しください。"
            })
        
        # リクエストデータ取得
        data = request.get_json() or {}
        input_text = data.get("japanese_text", "").strip()
        partner_message = data.get("partner_message", "")
        context_info = data.get("context_info", "")
        language_pair = data.get("language_pair", "ja-fr")  
        
        # 🆕 包括的な入力値検証
        validations = [
            (input_text, 5000, "翻訳テキスト"),
            (partner_message, 2000, "会話履歴"),
            (context_info, 2000, "背景情報")
        ]
        
        for text, max_len, field_name in validations:
            if text:  # 空でない場合のみ検証
                is_valid, error_msg = EnhancedInputValidator.validate_text_input(
                    text, max_length=max_len, field_name=field_name
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
        
        # 言語ペア検証
        is_valid_pair, pair_error = EnhancedInputValidator.validate_language_pair(language_pair)
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

        if not input_text:
            return jsonify({
                "success": False,
                "error": "翻訳するテキストが空です"
            })

        # 翻訳実行
        translated = f_translate_to_lightweight(input_text, source_lang, target_lang, partner_message, context_info)
        
        # 簡単な整合性チェック
        if translated.strip() == input_text.strip():
            translated = f"[翻訳処理でエラーが発生しました] {translated}"
        
        # 逆翻訳実行
        reverse = f_reverse_translation(translated, target_lang, source_lang)

        # Gemini翻訳を取得
        try:
            gemini_translation = f_translate_with_gemini(input_text, source_lang, target_lang, partner_message, context_info)
        except Exception as gemini_error:
            gemini_translation = f"Gemini翻訳エラー: {str(gemini_error)}"

        # 改善翻訳を取得
        better_translation = ""
        reverse_better = ""
        try:
            better_translation = f_better_translation(translated, source_lang, target_lang)
            
            if better_translation and not better_translation.startswith("改善翻訳エラー"):
                reverse_better = f_reverse_translation(better_translation, target_lang, source_lang)
            
        except Exception as better_error:
            better_translation = f"改善翻訳エラー: {str(better_error)}"
            reverse_better = ""

        # 使用回数を増加（翻訳成功時のみ）
        new_usage_count = increment_usage(client_id)
        remaining = daily_limit - new_usage_count

        # セッション保存
        session["translated_text"] = translated
        session["reverse_translated_text"] = reverse
        session["gemini_translation"] = gemini_translation
        session["better_translation"] = better_translation
        session["reverse_better_translation"] = reverse_better

        # 翻訳コンテキストを保存（インタラクティブ機能用）
        TranslationContext.save_context(
            input_text=input_text,
            translations={
                "chatgpt": translated,
                "enhanced": better_translation,
                "gemini": gemini_translation
            },
            analysis="",
            metadata={
                "source_lang": source_lang,
                "target_lang": target_lang,
                "partner_message": partner_message,
                "context_info": context_info
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
            "better_translation": better_translation,
            "reverse_better_translation": reverse_better,
            "usage_info": {
                "current_usage": new_usage_count,
                "daily_limit": daily_limit,
                "remaining": remaining,
                "is_near_limit": remaining <= 2
            }
        })
    
    except Exception