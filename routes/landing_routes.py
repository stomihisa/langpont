"""
Landing Page Routes - Phase 4b-3で分離
ランディングページ機能（5個のルート）
Created: 2025-07-08
Total: 約150行をapp.pyから分離

分離対象ルート:
1. /alpha - メインランディング
2. /alpha/jp - 日本語ランディング
3. /alpha/en - 英語ランディング
4. /alpha/fr - フランス語ランディング  
5. /alpha/es - スペイン語ランディング
"""

from flask import Blueprint, render_template, url_for, session, redirect

# 🔧 修正: labels import の改善
labels = {}  # デフォルト値を先に設定
try:
    from labels import labels as imported_labels
    labels = imported_labels
    print("✅ Labels imported successfully in landing_routes")
except ImportError as e:
    print(f"⚠️ Labels import failed in landing_routes: {e}")
    labels = {
        "jp": {"validation_error_empty": "が入力されていません"},
        "en": {"validation_error_empty": " is required"},
        "fr": {"validation_error_empty": " est requis"},
        "es": {"validation_error_empty": " es requerido"}
    }

# Blueprint作成（URL prefixなし - 既存URLを維持）
landing_bp = Blueprint('landing', __name__)

# 必要なグローバル変数import
try:
    from labels import labels
except ImportError:
    labels = {"jp": {}, "en": {}, "fr": {}, "es": {}}

# グローバル変数として確実に定義
if 'labels' not in globals():
    labels = {"jp": {}, "en": {}, "fr": {}, "es": {}}

# VERSION_INFO import
try:
    from config import VERSION
    VERSION_INFO = {
        "version": VERSION,
        "status": "ランディングページ専用"
    }
except ImportError:
    VERSION_INFO = {"version": "unknown", "status": "fallback"}

# 🆕 必要なヘルパー関数import
try:
    from admin_logger import log_access_event
    print("✅ log_access_event imported successfully")
except ImportError:
    print("⚠️ log_access_event import failed - using fallback")
    def log_access_event(message):
        print(f"LOG: {message}")

# =============================================================================
# ランディングページルート群
# =============================================================================

@landing_bp.route("/alpha")
def alpha_landing():
    """使用制限時のEarly Access案内 - ユーザー言語に応じてリダイレクト"""
    from flask import session, redirect
    lang = session.get('lang', 'jp')
    log_access_event(f'Usage limit redirect to Early Access: {lang}')
    return redirect(f"/alpha/{lang}")

@landing_bp.route("/alpha/jp")
def alpha_jp_safe():
    """日本語専用ランディングページ（安全版）"""
    
    # 既存のlabelsから日本語ラベルを取得
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

@landing_bp.route("/alpha/en")
def alpha_en_safe():
    """英語専用ランディングページ（安全版）"""
    
    # 既存のlabelsから英語ラベルを取得
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

@landing_bp.route("/alpha/fr")
def alpha_fr_safe():
    """フランス語専用ランディングページ（安全版）"""
    
    # 既存のlabelsからフランス語ラベルを取得
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

@landing_bp.route("/alpha/es")
def alpha_es_safe():
    """スペイン語専用ランディングページ（安全版）"""
    
    # 既存のlabelsからスペイン語ラベルを取得
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
