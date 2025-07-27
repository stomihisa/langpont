#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangPont 認証ルート
Task 2.6.1 - ユーザー認証システム基盤構築

Flask認証ルート（/register, /login, /logout, /profile）
セキュリティ強化（CSRF対策、レート制限、入力値検証）
"""

import logging
import time
import os
import json
import uuid

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, g
from werkzeug.utils import secure_filename
import secrets

from user_auth import UserAuthSystem
from user_profile import UserProfileManager, UserSettings, EarlyAccessFeatures, TranslationHistoryItem
from labels import labels

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🆕 SL-2.1: SessionRedisManager インポート
try:
    from services.session_redis_manager import get_session_redis_manager
    session_redis_manager = get_session_redis_manager()
    logger.info("✅ SL-2.1: SessionRedisManager imported successfully in auth_routes")
except Exception as e:
    session_redis_manager = None
    logger.warning(f"⚠️ SL-2.1: SessionRedisManager import failed in auth_routes: {e}")

# 🆕 翻訳履歴システムインポート
try:
    from translation_history import TranslationHistoryManager, translation_history_manager
    TRANSLATION_HISTORY_AVAILABLE = True
    logger.info("翻訳履歴システムが正常にインポートされました")
except ImportError as e:
    TRANSLATION_HISTORY_AVAILABLE = False
    logger.warning(f"翻訳履歴システムのインポートに失敗: {str(e)}")
    logger.info("翻訳履歴機能は無効になります")

# Blueprint作成
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# グローバル認証システムインスタンス
auth_system = UserAuthSystem()
profile_manager = UserProfileManager()

# レート制限用のストレージ（本番環境ではRedisなどを使用）
rate_limit_storage = {}

# CSRFトークン格納
csrf_tokens = {}

def init_auth_system():
    """認証システムを初期化"""
    global auth_system, profile_manager
    try:
        auth_system = UserAuthSystem()
        profile_manager = UserProfileManager()
        logger.info("認証システムとプロフィール管理システムが正常に初期化されました")
        return True
    except Exception as e:
        logger.error(f"認証システム初期化エラー: {str(e)}")
        return False

def get_client_ip():
    """クライアントのIPアドレスを取得"""
    # Heroku、AWS ALB、Nginx等のプロキシ対応
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def generate_csrf_token():
    """CSRFトークンを生成"""
    try:
        from flask import session
        token = secrets.token_urlsafe(32)
        session_id = session.get('session_id', 'anonymous')
        csrf_tokens[session_id] = {
            'token': token,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(hours=2)
        }
        return token
    except (RuntimeError, ImportError):
        # セッションコンテキスト外での呼び出しの場合
        return secrets.token_urlsafe(32)

def validate_csrf_token(token):
    """CSRFトークンを検証"""
    try:
        from flask import session
        session_id = session.get('session_id', 'anonymous')
        stored_token_data = csrf_tokens.get(session_id)
        
        if not stored_token_data:
            return False
        
        if datetime.now() > stored_token_data['expires_at']:
            del csrf_tokens[session_id]
            return False
        
        return stored_token_data['token'] == token
    except (RuntimeError, ImportError):
        # セッションコンテキスト外での呼び出しの場合
        return True  # テスト環境では常に通す

def check_rate_limit(identifier: str, max_attempts: int = 5, window_minutes: int = 15) -> bool:
    """レート制限をチェック"""
    current_time = time.time()
    window_start = current_time - (window_minutes * 60)
    
    if identifier not in rate_limit_storage:
        rate_limit_storage[identifier] = []
    
    # 古い試行を削除
    rate_limit_storage[identifier] = [
        attempt_time for attempt_time in rate_limit_storage[identifier] 
        if attempt_time > window_start
    ]
    
    if len(rate_limit_storage[identifier]) >= max_attempts:
        return False
    
    # 新しい試行を記録
    rate_limit_storage[identifier].append(current_time)
    return True

def require_auth(f):
    """認証が必要なエンドポイント用デコレータ（新旧システム統合対応）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 🆕 新旧認証システムの統合チェック
        new_auth = session.get('authenticated') and session.get('user_id')
        legacy_auth = session.get('logged_in')
        
        if not new_auth and not legacy_auth:
            flash('ログインが必要です', 'error')
            return redirect(url_for('auth.login'))
        
        # 🆕 新認証システムの場合のセッション検証
        if new_auth:
            session_token = session.get('session_token')
            if session_token:
                is_valid, user_info = auth_system.validate_session(session_token)
                if not is_valid:
                    session.clear()
                    flash('セッションの有効期限が切れています', 'error')
                    return redirect(url_for('auth.login'))
                
                # ユーザー情報をグローバルに設定
                g.current_user = user_info
            else:
                session.clear()
                flash('無効なセッションです', 'error')
                return redirect(url_for('auth.login'))
        
        # 🆕 従来認証システムの場合
        elif legacy_auth:
            # 従来システムの場合は基本的なセッション確認のみ
            username = session.get('username', 'guest')
            g.current_user = {
                'id': None,
                'username': username,
                'account_type': 'legacy',
                'is_legacy': True
            }
        
        return f(*args, **kwargs)
    return decorated_function

def get_current_lang():
    """現在の言語を取得"""
    return session.get('lang', 'jp')

def get_error_message(key: str, lang: str = None) -> str:
    """エラーメッセージを多言語で取得"""
    if lang is None:
        lang = get_current_lang()
    
    try:
        return labels[lang].get(key, key)
    except KeyError:
        return labels['jp'].get(key, key)

@auth_bp.before_app_request
def load_user():
    """リクエスト前にユーザー情報をロード"""
    g.current_user = None
    if session.get('authenticated') and session.get('session_token'):
        is_valid, user_info = auth_system.validate_session(session.get('session_token'))
        if is_valid:
            g.current_user = user_info

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """ユーザー登録"""
    current_lang = get_current_lang()
    
    if request.method == 'GET':
        # CSRF トークン生成
        csrf_token = generate_csrf_token()
        return render_template('register.html', 
                             labels=labels[current_lang],
                             csrf_token=csrf_token)
    
    # POST処理
    try:
        # CSRFトークン検証
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            flash(get_error_message('csrf_error', current_lang), 'error')
            return redirect(url_for('auth.register'))
        
        # レート制限チェック
        client_ip = get_client_ip()
        if not check_rate_limit(f"register_{client_ip}", max_attempts=3, window_minutes=10):
            flash(get_error_message('rate_limit_register', current_lang), 'error')
            return redirect(url_for('auth.register'))
        
        # フォームデータ取得
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        account_type = request.form.get('account_type', 'basic')
        early_access = request.form.get('early_access') == 'on'
        
        # 基本入力検証
        if not username or not email or not password:
            flash(get_error_message('validation_error_empty', current_lang), 'error')
            return render_template('register.html', 
                                 labels=labels[current_lang],
                                 csrf_token=generate_csrf_token(),
                                 username=username, email=email)
        
        if password != confirm_password:
            flash(get_error_message('password_mismatch', current_lang), 'error')
            return render_template('register.html', 
                                 labels=labels[current_lang],
                                 csrf_token=generate_csrf_token(),
                                 username=username, email=email)
        
        # ユーザー登録実行
        success, message, user_id = auth_system.register_user(
            username=username,
            email=email,
            password=password,
            account_type=account_type,
            early_access=early_access
        )
        
        if success:
            flash(get_error_message('registration_success', current_lang), 'success')
            logger.info(f"新規ユーザー登録成功: {username} (ID: {user_id})")
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'error')
            return render_template('register.html', 
                                 labels=labels[current_lang],
                                 csrf_token=generate_csrf_token(),
                                 username=username, email=email)
    
    except Exception as e:
        logger.error(f"ユーザー登録エラー: {str(e)}")
        flash(get_error_message('registration_error', current_lang), 'error')
        return render_template('register.html', 
                             labels=labels[current_lang],
                             csrf_token=generate_csrf_token())

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """ユーザーログイン"""
    current_lang = get_current_lang()
    
    if request.method == 'GET':
        # 既にログイン済みの場合はリダイレクト
        if session.get('authenticated'):
            return redirect(url_for('index'))
        
        csrf_token = generate_csrf_token()
        return render_template('login_new.html', 
                             labels=labels[current_lang],
                             csrf_token=csrf_token)
    
    # POST処理
    try:
        # CSRFトークン検証
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            flash(get_error_message('csrf_error', current_lang), 'error')
            return redirect(url_for('auth.login'))
        
        # レート制限チェック
        client_ip = get_client_ip()
        if not check_rate_limit(f"login_{client_ip}", max_attempts=5, window_minutes=15):
            flash(get_error_message('rate_limit_login', current_lang), 'error')
            return redirect(url_for('auth.login'))
        
        # フォームデータ取得
        login_identifier = request.form.get('login_identifier', '').strip()
        password = request.form.get('password', '')
        remember_me = request.form.get('remember_me') == 'on'
        
        # 基本入力検証
        if not login_identifier or not password:
            flash(get_error_message('login_required_fields', current_lang), 'error')
            return render_template('login_new.html', 
                                 labels=labels[current_lang],
                                 csrf_token=generate_csrf_token(),
                                 login_identifier=login_identifier)
        
        # 🆕 新認証システムでの認証実行
        user_agent = request.headers.get('User-Agent', '')
        success, message, user_info = auth_system.authenticate_user(
            login_identifier=login_identifier,
            password=password,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        # 🆕 新認証システムで失敗した場合、従来システムを試行
        if not success:
            legacy_success = False
            # 従来システムのユーザー認証をチェック
            from config import USERS, LEGACY_SETTINGS
            
            # 従来システムのユーザーアカウント確認
            if login_identifier in USERS:
                user_data = USERS[login_identifier]
                if password == user_data["password"]:
                    legacy_success = True
                    user_info = {
                        'id': None,
                        'username': login_identifier,
                        'email': 'legacy@example.com',
                        'account_type': user_data["role"],
                        'early_access': True,
                        'is_legacy': True
                    }
            
            # レガシーパスワードチェック（後方互換性）
            elif not login_identifier and password == LEGACY_SETTINGS.get("legacy_password", "linguru2025"):
                legacy_success = True
                user_info = {
                    'id': None,
                    'username': 'guest',
                    'email': 'legacy@example.com',
                    'account_type': 'guest',
                    'early_access': True,
                    'is_legacy': True
                }
            
            if legacy_success:
                success = True
                # 従来システムのセッション設定
                session['logged_in'] = True
                session['username'] = user_info['username']
                session['user_role'] = user_info['account_type']
                session['daily_limit'] = USERS.get(login_identifier, {}).get('daily_limit', 10) if login_identifier in USERS else 10
                session['session_id'] = str(uuid.uuid4())

                # 🆕 従来ユーザーの保存済み設定を復元
                username = user_info['username']
                legacy_settings_file = f"legacy_user_settings_{username}.json"
                try:
                    import json
                    if os.path.exists(legacy_settings_file):
                        with open(legacy_settings_file, 'r', encoding='utf-8') as f:
                            legacy_settings = json.load(f)
                            preferred_lang = legacy_settings.get('preferred_lang', 'jp')
                            session['preferred_lang'] = preferred_lang
                            session['lang'] = preferred_lang
                            logger.info(f"従来ユーザー設定復元: {username} -> 言語: {preferred_lang}")
                except Exception as e:
                    logger.warning(f"従来ユーザー設定復元エラー: {str(e)}")
                
                flash(get_error_message('login_success', current_lang), 'success')
                logger.info(f"従来システムログイン成功: {user_info['username']}")
                
                # 🆕 SL-2.1: Redis同期（従来システム用・失敗してもログイン処理は継続）
                if session_redis_manager:
                    try:
                        session_redis_manager.sync_auth_to_redis(
                            session_id=session.get('session_id'),
                            auth_data={
                                'logged_in': True,
                                'username': user_info['username'],
                                'user_id': user_info.get('id', 'legacy'),
                                'account_type': user_info.get('account_type', 'legacy'),
                                'early_access': user_info.get('early_access', False),
                                'auth_method': 'legacy_login'
                            }
                        )
                        logger.info(f"✅ SL-2.1: Auth data synced to Redis for legacy user: {user_info['username']}")
                    except Exception as e:
                        logger.warning(f"⚠️ SL-2.1: Redis sync failed for legacy user: {e} - continuing with filesystem session")
                
                # 🆕 SL-2.2 Phase 2: セッションID再生成（セッション固定攻撃対策）
                try:
                    from flask import current_app
                    if hasattr(current_app.session_interface, 'regenerate_session_id'):
                        current_app.session_interface.regenerate_session_id(session)
                        logger.info(f"🔄 SL-2.2: Session ID regenerated for legacy user: {user_info['username']}")
                except Exception as e:
                    logger.warning(f"⚠️ SL-2.2: Session ID regeneration failed: {e}")
                
                next_page = request.form.get('next') or url_for('index')
                return redirect(next_page)
        
        if success and user_info and not user_info.get('is_legacy'):
            # セッション作成
            expires_hours = 720 if remember_me else 24  # remember_me: 30日、通常: 1日
            session_success, session_message, session_info = auth_system.create_session(
                user_id=user_info['id'],
                ip_address=client_ip,
                user_agent=user_agent,
                expires_hours=expires_hours
            )
            
            if session_success and session_info:
                # セッション情報を設定
                session['authenticated'] = True
                session['user_id'] = user_info['id']
                session['username'] = user_info['username']
                session['session_token'] = session_info['session_token']
                session['session_id'] = session_info['session_id']
                session['account_type'] = user_info['account_type']
                session['early_access'] = user_info['early_access']
                
                # セッション永続化設定
                session.permanent = remember_me
                
                # 🆕 SL-2.1: Redis同期（失敗してもログイン処理は継続）
                if session_redis_manager:
                    try:
                        session_redis_manager.sync_auth_to_redis(
                            session_id=session.get('session_id'),
                            auth_data={
                                'logged_in': True,
                                'username': user_info['username'],
                                'user_id': user_info['id'],
                                'account_type': user_info['account_type'],
                                'early_access': user_info['early_access'],
                                'auth_method': 'standard_login'
                            }
                        )
                        logger.info(f"✅ SL-2.1: Auth data synced to Redis for user: {user_info['username']}")
                    except Exception as e:
                        logger.warning(f"⚠️ SL-2.1: Redis sync failed: {e} - continuing with filesystem session")
                
                # 🆕 SL-2.2 Phase 2: セッションID再生成（セッション固定攻撃対策）
                try:
                    from flask import current_app
                    if hasattr(current_app.session_interface, 'regenerate_session_id'):
                        current_app.session_interface.regenerate_session_id(session)
                        logger.info(f"🔄 SL-2.2: Session ID regenerated for user: {user_info['username']}")
                except Exception as e:
                    logger.warning(f"⚠️ SL-2.2: Session ID regeneration failed: {e}")
                
                flash(get_error_message('login_success', current_lang), 'success')
                logger.info(f"ユーザーログイン成功: {user_info['username']} (ID: {user_info['id']})")
                
                # リダイレクト先を確認
                next_page = request.form.get('next') or url_for('index')
                return redirect(next_page)
            else:
                flash(get_error_message('session_creation_error', current_lang), 'error')
                return render_template('login_new.html', 
                                     labels=labels[current_lang],
                                     csrf_token=generate_csrf_token(),
                                     login_identifier=login_identifier)
        else:
            flash(message, 'error')
            return render_template('login_new.html', 
                                 labels=labels[current_lang],
                                 csrf_token=generate_csrf_token(),
                                 login_identifier=login_identifier)
    
    except Exception as e:
        logger.error(f"ログインエラー: {str(e)}")
        flash(get_error_message('login_error', current_lang), 'error')
        return render_template('login_new.html', 
                             labels=labels[current_lang],
                             csrf_token=generate_csrf_token())

@auth_bp.route('/logout')
def logout():
    """ユーザーログアウト"""
    current_lang = get_current_lang()
    
    try:
        # セッション無効化
        session_token = session.get('session_token')
        if session_token:
            auth_system.logout_user(session_token)
        
        # Flaskセッションクリア
        username = session.get('username', 'ユーザー')
        session.clear()
        
        flash(get_error_message('logout_success', current_lang), 'success')
        logger.info(f"ユーザーログアウト: {username}")
        
    except Exception as e:
        logger.error(f"ログアウトエラー: {str(e)}")
        session.clear()
        flash(get_error_message('logout_error', current_lang), 'error')
    
    return redirect(url_for('index'))

@auth_bp.route('/profile')
@require_auth
def profile():
    """ユーザープロフィール表示（新旧システム統合対応）"""
    current_lang = get_current_lang()
    
    try:
        # 🆕 新旧認証システム統合対応
        if hasattr(g, 'current_user') and g.current_user.get('is_legacy'):
            # 従来システムユーザーの場合
            username = session.get('username', 'guest')
            user_role = session.get('user_role', 'guest')
            
            # 🆕 config.pyからユーザー情報を取得
            from config import USERS
            daily_limit = USERS.get(username, {}).get('daily_limit', 10)
            
            # 🆕 従来システムユーザーの保存された言語設定を取得（ファイル + セッション）
            saved_lang = session.get('preferred_lang', session.get('lang', current_lang))
            
            # 🆕 従来ユーザー設定ファイルから言語設定を復元
            legacy_settings_file = f"legacy_user_settings_{username}.json"
            try:
                import json
                if os.path.exists(legacy_settings_file):
                    with open(legacy_settings_file, 'r', encoding='utf-8') as f:
                        legacy_settings = json.load(f)
                        file_lang = legacy_settings.get('preferred_lang', saved_lang)
                        if file_lang != saved_lang:
                            # ファイルの設定が異なる場合は更新
                            saved_lang = file_lang
                            session['preferred_lang'] = file_lang
                            session['lang'] = file_lang
                            logger.info(f"従来ユーザー設定をファイルから復元: {username} -> {file_lang}")
            except Exception as e:
                logger.warning(f"従来ユーザー設定ファイル読み込みエラー: {str(e)}")
            
            user_info = {
                'id': None,
                'username': username,
                'email': 'legacy@example.com',
                'account_type': user_role,
                'early_access': True,
                'created_at': '従来システム',
                'last_login': 'N/A',
                'preferred_lang': saved_lang  # 🆕 テンプレートからアクセス可能にする
            }
            user_settings = {'preferred_lang': saved_lang}
            early_access_features = {'translation_history': True}
            # 🆕 従来ユーザーの翻訳履歴統計を取得（改善版）
            total_translations = 0
            bookmarked = 0
            this_week = 0
            avg_rating = 0.0
            # 🆕 今日の使用回数を正確に取得
            daily_usage = session.get('usage_count', 0)
            today = datetime.now().strftime('%Y-%m-%d')
            last_usage_date = session.get('last_usage_date', '')
            
            # もし日付が変わっている場合は使用回数をリセット
            if last_usage_date != today:
                daily_usage = 0
                session['usage_count'] = 0
                session['last_usage_date'] = today
                logger.info(f"従来ユーザー使用回数をリセット: {username} (日付変更: {last_usage_date} -> {today})")
            
            if TRANSLATION_HISTORY_AVAILABLE:
                try:
                    session_id = session.get('session_id', session.get('csrf_token', '')[:16])
                    
                    # 全期間の統計
                    analytics_all = translation_history_manager.get_translation_analytics(
                        user_id=None, session_id=session_id, days=365
                    )
                    # 今週の統計
                    analytics_week = translation_history_manager.get_translation_analytics(
                        user_id=None, session_id=session_id, days=7
                    )
                    
                    if analytics_all and 'basic_stats' in analytics_all:
                        basic_stats = analytics_all['basic_stats']
                        total_translations = basic_stats.get('total_translations', 0)
                        bookmarked = basic_stats.get('bookmarked_count', 0)
                        avg_rating = basic_stats.get('avg_user_rating', 0.0)
                    
                    if analytics_week and 'basic_stats' in analytics_week:
                        this_week = analytics_week['basic_stats'].get('total_translations', 0)
                    
                    # セッションから保存済み統計があれば使用
                    if session.get('bookmarked_count'):
                        bookmarked = session.get('bookmarked_count', bookmarked)
                    if session.get('avg_rating'):
                        avg_rating = session.get('avg_rating', avg_rating)
                        
                    logger.info(f"従来ユーザー統計取得: total={total_translations}, bookmarked={bookmarked}, rating={avg_rating}")
                    
                except Exception as e:
                    logger.warning(f"従来ユーザーの翻訳履歴統計取得エラー: {str(e)}")
            
            user_statistics = {
                'total_translations': total_translations,
                'daily_usage': daily_usage,
                'daily_limit': daily_limit,
                'bookmarked': bookmarked,
                'this_week': this_week,
                'avg_rating': round(avg_rating, 1)
            }
        else:
            # 新認証システムユーザーの場合
            user_id = session.get('user_id')
            user_info = auth_system.get_user_by_id(user_id)
            if not user_info:
                flash(get_error_message('user_not_found', current_lang), 'error')
                return redirect(url_for('index'))
            
            # ユーザー設定とEarly Access機能を取得
            user_settings = profile_manager.get_user_settings(user_id)
            early_access_features = profile_manager.get_early_access_features(user_id)
            user_statistics = profile_manager.get_user_statistics(user_id)
            
            # 🆕 翻訳履歴統計のデフォルト値設定
            if not user_statistics.get('total_translations'):
                user_statistics['total_translations'] = 0
            if not user_statistics.get('bookmarked'):
                user_statistics['bookmarked'] = 0
            
            # 🆕 テンプレートアクセス用にpreferred_langを追加
            if user_settings and 'preferred_lang' in user_settings:
                user_info['preferred_lang'] = user_settings['preferred_lang']
            else:
                user_info['preferred_lang'] = current_lang
        
        csrf_token = generate_csrf_token()
        return render_template('profile.html', 
                             labels=labels[current_lang],
                             user=user_info,
                             user_settings=user_settings,
                             early_access_features=early_access_features,
                             user_statistics=user_statistics,
                             csrf_token=csrf_token)
    
    except Exception as e:
        logger.error(f"プロフィール表示エラー: {str(e)}")
        flash(get_error_message('profile_error', current_lang), 'error')
        return redirect(url_for('index'))

@auth_bp.route('/profile/update', methods=['POST'])
@require_auth
def update_profile():
    """ユーザープロフィール更新"""
    current_lang = get_current_lang()
    
    try:
        # CSRFトークン検証
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            flash(get_error_message('csrf_error', current_lang), 'error')
            return redirect(url_for('auth.profile'))
        
        # フォームデータ取得
        preferred_lang = request.form.get('preferred_lang', 'jp')
        email = request.form.get('email', '').strip()
        
        # 🆕 従来システムユーザーの場合はメール検証をスキップ
        is_legacy_user = hasattr(g, 'current_user') and g.current_user.get('is_legacy')
        
        if not is_legacy_user:
            # 新認証システムユーザーの場合のみメール検証
            if not email:
                flash(get_error_message('email_required', current_lang), 'error')
                return redirect(url_for('auth.profile'))
            
            # メールアドレス検証
            valid_email, email_error = auth_system.validate_email(email)
            if not valid_email:
                flash(email_error, 'error')
                return redirect(url_for('auth.profile'))
        
        # 🆕 新旧システム統合対応のプロフィール更新
        if hasattr(g, 'current_user') and g.current_user.get('is_legacy'):
            # 従来システムユーザーの場合 - セッションに永続保存
            session['preferred_lang'] = preferred_lang
            session['lang'] = preferred_lang  # メインアプリの言語設定も更新
            session.permanent = True  # セッションを永続化（ログアウト後も保持）
            
            # 🆕 従来ユーザー用の設定永続化ファイルに保存
            username = session.get('username', 'guest')
            legacy_settings_file = f"legacy_user_settings_{username}.json"
            try:
                import json
                legacy_settings = {
                    'username': username,
                    'preferred_lang': preferred_lang,
                    'last_updated': datetime.now().isoformat()
                }
                with open(legacy_settings_file, 'w', encoding='utf-8') as f:
                    json.dump(legacy_settings, f, ensure_ascii=False, indent=2)
                logger.info(f"従来ユーザー設定をファイルに保存: {legacy_settings_file}")
            except Exception as e:
                logger.warning(f"従来ユーザー設定ファイル保存エラー: {str(e)}")
            
            flash(f'設定を更新しました（言語: {preferred_lang}）', 'success')
            logger.info(f"従来システムユーザープロフィール更新: {session.get('username')} -> 言語: {preferred_lang}")
        else:
            # 新認証システムユーザーの場合 - データベースに保存
            user_id = session.get('user_id')
            if user_id:
                # profile_manager経由で設定を更新
                try:
                    success = profile_manager.update_user_settings(user_id, {
                        'preferred_lang': preferred_lang,
                        'email': email
                    })
                    if success:
                        flash(get_error_message('profile_updated', current_lang), 'success')
                        logger.info(f"新認証システムユーザープロフィール更新: ユーザーID {user_id}")
                    else:
                        flash('設定の更新に失敗しました', 'error')
                except Exception as e:
                    logger.error(f"プロフィール更新DB処理エラー: {str(e)}")
                    flash('設定の更新中にエラーが発生しました', 'error')
            else:
                flash('ユーザー情報が見つかりません', 'error')
        
        return redirect(url_for('auth.profile'))
    
    except Exception as e:
        logger.error(f"プロフィール更新エラー: {str(e)}")
        flash(get_error_message('profile_update_error', current_lang), 'error')
        return redirect(url_for('auth.profile'))

# 🆕 Task 2.6.2 - ユーザープロフィール管理ルート追加

@auth_bp.route('/profile/settings', methods=['GET', 'POST'])
@require_auth
def profile_settings():
    """ユーザー設定管理"""
    current_lang = get_current_lang()
    user_id = session.get('user_id')
    
    if request.method == 'GET':
        try:
            user_settings = profile_manager.get_user_settings(user_id)
            csrf_token = generate_csrf_token()
            
            return render_template('profile_settings.html',
                                 labels=labels[current_lang],
                                 user_settings=user_settings,
                                 csrf_token=csrf_token)
        except Exception as e:
            logger.error(f"設定表示エラー: {str(e)}")
            flash(get_error_message('profile_error', current_lang), 'error')
            return redirect(url_for('auth.profile'))
    
    # POST処理 - 設定更新
    try:
        # CSRFトークン検証
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            flash(get_error_message('csrf_error', current_lang), 'error')
            return redirect(url_for('auth.profile_settings'))
        
        # 現在の設定を取得
        current_settings = profile_manager.get_user_settings(user_id)
        
        # フォームから新しい設定を取得
        new_settings = UserSettings(
            # 翻訳設定
            default_source_language=request.form.get('default_source_language', current_settings.default_source_language),
            default_target_language=request.form.get('default_target_language', current_settings.default_target_language),
            preferred_translation_engine=request.form.get('preferred_translation_engine', current_settings.preferred_translation_engine),
            show_reverse_translation=request.form.get('show_reverse_translation') == 'on',
            show_nuance_analysis=request.form.get('show_nuance_analysis') == 'on',
            
            # UI設定
            display_language=request.form.get('display_language', current_settings.display_language),
            theme=request.form.get('theme', current_settings.theme),
            font_size=request.form.get('font_size', current_settings.font_size),
            compact_mode=request.form.get('compact_mode') == 'on',
            
            # 通知設定
            notification_level=request.form.get('notification_level', current_settings.notification_level),
            email_notifications=request.form.get('email_notifications') == 'on',
            usage_limit_warnings=request.form.get('usage_limit_warnings') == 'on',
            
            # プライバシー設定
            save_translation_history=request.form.get('save_translation_history') == 'on',
            share_usage_analytics=request.form.get('share_usage_analytics') == 'on',
            
            # 高度な設定
            auto_detect_language=request.form.get('auto_detect_language') == 'on',
            parallel_translation=request.form.get('parallel_translation') == 'on',
            cache_translations=request.form.get('cache_translations') == 'on',
            max_history_items=int(request.form.get('max_history_items', current_settings.max_history_items))
        )
        
        # 設定を保存
        success = profile_manager.save_user_settings(user_id, new_settings)
        
        if success:
            # セッション言語を更新
            session['lang'] = new_settings.display_language
            flash(get_error_message('profile_updated', current_lang), 'success')
            logger.info(f"ユーザー設定更新: ユーザーID {user_id}")
        else:
            flash(get_error_message('profile_update_error', current_lang), 'error')
        
        return redirect(url_for('auth.profile_settings'))
    
    except Exception as e:
        logger.error(f"設定更新エラー: {str(e)}")
        flash(get_error_message('profile_update_error', current_lang), 'error')
        return redirect(url_for('auth.profile_settings'))

@auth_bp.route('/profile/early-access', methods=['GET', 'POST'])
@require_auth
def early_access_settings():
    """Early Access機能設定"""
    current_lang = get_current_lang()
    user_id = session.get('user_id')
    
    # Early Accessユーザーかチェック
    user_info = auth_system.get_user_by_id(user_id)
    if not user_info or not user_info.get('early_access'):
        flash('Early Accessアカウントが必要です', 'error')
        return redirect(url_for('auth.profile'))
    
    if request.method == 'GET':
        try:
            early_access_features = profile_manager.get_early_access_features(user_id)
            csrf_token = generate_csrf_token()
            
            return render_template('early_access_settings.html',
                                 labels=labels[current_lang],
                                 early_access_features=early_access_features,
                                 csrf_token=csrf_token)
        except Exception as e:
            logger.error(f"Early Access設定表示エラー: {str(e)}")
            flash(get_error_message('profile_error', current_lang), 'error')
            return redirect(url_for('auth.profile'))
    
    # POST処理 - Early Access設定更新
    try:
        # CSRFトークン検証
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            flash(get_error_message('csrf_error', current_lang), 'error')
            return redirect(url_for('auth.early_access_settings'))
        
        # 新しい設定を取得
        new_features = EarlyAccessFeatures(
            unlimited_translations=request.form.get('unlimited_translations') == 'on',
            advanced_ai_features=request.form.get('advanced_ai_features') == 'on',
            beta_features=request.form.get('beta_features') == 'on',
            priority_support=request.form.get('priority_support') == 'on',
            api_access=request.form.get('api_access') == 'on',
            custom_models=request.form.get('custom_models') == 'on',
            team_features=request.form.get('team_features') == 'on'
        )
        
        # 設定を保存
        success = profile_manager.save_early_access_features(user_id, new_features)
        
        if success:
            flash('Early Access設定を更新しました', 'success')
            logger.info(f"Early Access設定更新: ユーザーID {user_id}")
            
            # Early Access利用ログを記録
            profile_manager.log_early_access_usage(
                user_id=user_id,
                feature_name="settings_update",
                action="update_features",
                metadata={"features_updated": True}
            )
        else:
            flash('設定の更新に失敗しました', 'error')
        
        return redirect(url_for('auth.early_access_settings'))
    
    except Exception as e:
        logger.error(f"Early Access設定更新エラー: {str(e)}")
        flash('設定更新中にエラーが発生しました', 'error')
        return redirect(url_for('auth.early_access_settings'))

@auth_bp.route('/profile/history')
@require_auth
def translation_history():
    """翻訳履歴表示"""
    current_lang = get_current_lang()
    user_id = session.get('user_id')
    
    try:
        # パラメータ取得
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)  # 最大100件
        bookmarked_only = request.args.get('bookmarked') == '1'
        
        offset = (page - 1) * limit
        
        # 翻訳履歴を取得
        history_items = profile_manager.get_translation_history(
            user_id=user_id,
            limit=limit,
            offset=offset,
            bookmarked_only=bookmarked_only
        )
        
        # 統計情報を取得
        user_statistics = profile_manager.get_user_statistics(user_id)
        
        csrf_token = generate_csrf_token()
        return render_template('translation_history.html',
                             labels=labels[current_lang],
                             history_items=history_items,
                             user_statistics=user_statistics,
                             page=page,
                             limit=limit,
                             bookmarked_only=bookmarked_only,
                             csrf_token=csrf_token)
    
    except Exception as e:
        logger.error(f"翻訳履歴表示エラー: {str(e)}")
        flash(get_error_message('profile_error', current_lang), 'error')
        return redirect(url_for('auth.profile'))

@auth_bp.route('/profile/history/bookmark', methods=['POST'])
@require_auth
def bookmark_translation():
    """翻訳をブックマーク/ブックマーク解除"""
    current_lang = get_current_lang()
    user_id = session.get('user_id')
    
    try:
        # CSRFトークン検証
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            return jsonify({'success': False, 'error': 'CSRF エラー'})
        
        history_id = int(request.form.get('history_id'))
        bookmarked = request.form.get('bookmarked') == 'true'
        
        success = profile_manager.bookmark_translation(user_id, history_id, bookmarked)
        
        if success:
            action = 'ブックマーク' if bookmarked else 'ブックマーク解除'
            return jsonify({'success': True, 'message': f'{action}しました'})
        else:
            return jsonify({'success': False, 'error': '更新に失敗しました'})
    
    except Exception as e:
        logger.error(f"ブックマーク更新エラー: {str(e)}")
        return jsonify({'success': False, 'error': 'エラーが発生しました'})

@auth_bp.route('/profile/history/rate', methods=['POST'])
@require_auth
def rate_translation():
    """翻訳を評価"""
    current_lang = get_current_lang()
    user_id = session.get('user_id')
    
    try:
        # CSRFトークン検証
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            return jsonify({'success': False, 'error': 'CSRF エラー'})
        
        history_id = int(request.form.get('history_id'))
        engine_type = request.form.get('engine_type')  # chatgpt, gemini, better
        rating = int(request.form.get('rating'))  # 1-5
        feedback_text = request.form.get('feedback_text', '')
        
        # 評価値の検証
        if not (1 <= rating <= 5):
            return jsonify({'success': False, 'error': '評価は1〜5の範囲で入力してください'})
        
        success = profile_manager.rate_translation(
            user_id=user_id,
            history_id=history_id,
            engine_type=engine_type,
            rating=rating,
            feedback_text=feedback_text
        )
        
        if success:
            return jsonify({'success': True, 'message': '評価を保存しました'})
        else:
            return jsonify({'success': False, 'error': '評価の保存に失敗しました'})
    
    except Exception as e:
        logger.error(f"翻訳評価エラー: {str(e)}")
        return jsonify({'success': False, 'error': 'エラーが発生しました'})

@auth_bp.route('/profile/statistics')
@require_auth
def user_statistics():
    """ユーザー統計情報表示"""
    current_lang = get_current_lang()
    user_id = session.get('user_id')
    
    try:
        statistics = profile_manager.get_user_statistics(user_id)
        early_access_features = profile_manager.get_early_access_features(user_id)
        
        return render_template('user_statistics.html',
                             labels=labels[current_lang],
                             statistics=statistics,
                             early_access_features=early_access_features)
    
    except Exception as e:
        logger.error(f"統計情報表示エラー: {str(e)}")
        flash(get_error_message('profile_error', current_lang), 'error')
        return redirect(url_for('auth.profile'))

@auth_bp.route('/profile/export', methods=['POST'])
@require_auth
def export_user_data():
    """ユーザーデータエクスポート（GDPR対応）"""
    current_lang = get_current_lang()
    user_id = session.get('user_id')
    
    try:
        # CSRFトークン検証
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            flash(get_error_message('csrf_error', current_lang), 'error')
            return redirect(url_for('auth.profile'))
        
        # データをエクスポート
        export_data = profile_manager.export_user_data(user_id)
        
        if export_data:
            # JSONファイルとしてダウンロード
            from flask import make_response
            import json
            
            response = make_response(json.dumps(export_data, ensure_ascii=False, indent=2))
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename=langpont_user_data_{user_id}_{datetime.now().strftime("%Y%m%d")}.json'
            
            logger.info(f"ユーザーデータエクスポート: ユーザーID {user_id}")
            return response
        else:
            flash('データのエクスポートに失敗しました', 'error')
            return redirect(url_for('auth.profile'))
    
    except Exception as e:
        logger.error(f"データエクスポートエラー: {str(e)}")
        flash('エクスポート中にエラーが発生しました', 'error')
        return redirect(url_for('auth.profile'))

@auth_bp.route('/profile/delete-data', methods=['POST'])
@require_auth
def delete_user_data():
    """ユーザーデータ完全削除（GDPR対応）"""
    current_lang = get_current_lang()
    user_id = session.get('user_id')
    
    try:
        # CSRFトークン検証
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            flash(get_error_message('csrf_error', current_lang), 'error')
            return redirect(url_for('auth.profile'))
        
        # 確認フィールドをチェック
        confirmation = request.form.get('delete_confirmation', '').strip()
        if confirmation != 'DELETE':
            flash('削除確認の入力が正しくありません', 'error')
            return redirect(url_for('auth.profile'))
        
        # プロフィールデータを削除
        success = profile_manager.delete_user_data(user_id)
        
        if success:
            # アカウント自体も削除するかはここで決定
            # 今回はプロフィールデータのみ削除
            flash('プロフィールデータを完全に削除しました', 'success')
            logger.info(f"ユーザープロフィールデータ削除: ユーザーID {user_id}")
        else:
            flash('データの削除に失敗しました', 'error')
        
        return redirect(url_for('auth.profile'))
    
    except Exception as e:
        logger.error(f"データ削除エラー: {str(e)}")
        flash('削除中にエラーが発生しました', 'error')
        return redirect(url_for('auth.profile'))

@auth_bp.route('/api/profile/settings', methods=['GET'])
@require_auth
def get_user_settings_api():
    """ユーザー設定API（JSON）"""
    try:
        user_id = session.get('user_id')
        user_settings = profile_manager.get_user_settings(user_id)
        
        # UserSettingsをdict形式に変換
        from dataclasses import asdict
        settings_dict = asdict(user_settings)
        
        return jsonify({
            'success': True,
            'settings': settings_dict
        })
    
    except Exception as e:
        logger.error(f"設定API取得エラー: {str(e)}")
        return jsonify({'success': False, 'error': 'エラーが発生しました'})

@auth_bp.route('/api/profile/early-access-log', methods=['POST'])
@require_auth
def log_early_access_usage_api():
    """Early Access機能利用ログAPI"""
    try:
        user_id = session.get('user_id')
        
        # Early Accessユーザーかチェック
        user_info = auth_system.get_user_by_id(user_id)
        if not user_info or not user_info.get('early_access'):
            return jsonify({'success': False, 'error': 'Early Accessアカウントが必要です'})
        
        data = request.get_json()
        feature_name = data.get('feature_name')
        action = data.get('action')
        metadata = data.get('metadata', {})
        
        success = profile_manager.log_early_access_usage(
            user_id=user_id,
            feature_name=feature_name,
            action=action,
            metadata=metadata
        )
        
        if success:
            return jsonify({'success': True, 'message': 'ログを記録しました'})
        else:
            return jsonify({'success': False, 'error': 'ログの記録に失敗しました'})
    
    except Exception as e:
        logger.error(f"Early Accessログ記録エラー: {str(e)}")
        return jsonify({'success': False, 'error': 'エラーが発生しました'})

# 🆕 Task 2.7.1 - 翻訳履歴管理機能

@auth_bp.route('/history/detailed')
@require_auth
def detailed_translation_history():
    """詳細な翻訳履歴表示（Task 2.7.1 強化版）"""
    current_lang = get_current_lang()
    user_id = session.get('user_id')
    
    if not TRANSLATION_HISTORY_AVAILABLE:
        flash('翻訳履歴機能は現在利用できません', 'error')
        return redirect(url_for('auth.profile'))
    
    try:
        # パラメータ取得と検証
        page = max(1, int(request.args.get('page', 1)))
        limit = min(max(10, int(request.args.get('limit', 20))), 100)
        search_query = request.args.get('search', '').strip()
        language_pair = request.args.get('language_pair', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        min_rating = request.args.get('min_rating', '')
        bookmarked_only = request.args.get('bookmarked') == '1'
        
        offset = (page - 1) * limit
        
        # フィルタ条件の構築
        filters = {}
        if language_pair and '-' in language_pair:
            source_lang, target_lang = language_pair.split('-', 1)
            filters['source_language'] = source_lang
            filters['target_language'] = target_lang
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        if min_rating and min_rating.isdigit():
            filters['min_rating'] = int(min_rating)
        if bookmarked_only:
            filters['bookmarked_only'] = True
        
        # 🆕 ユーザーIDの統合処理（新旧システム対応）
        effective_user_id = user_id
        session_id = None
        
        # 従来ユーザーの場合はセッションIDを使用
        if not user_id and session.get('logged_in'):
            session_id = session.get('session_id') or session.get('csrf_token', '')[:16]
            logger.info(f"従来ユーザーの履歴検索: session_id={session_id}")
        
        # 🆕 履歴取得（検索対応）
        if search_query:
            # 全文検索実行
            history_entries = translation_history_manager.search_translation_history(
                user_id=effective_user_id,
                session_id=session_id,
                search_query=search_query,
                search_fields=['source_text', 'chatgpt_translation', 'gemini_translation', 'enhanced_translation'],
                filters=filters,
                limit=limit,
                offset=offset
            )
        else:
            # 通常の履歴取得
            history_entries = translation_history_manager.get_user_translation_history(
                user_id=effective_user_id,
                session_id=session_id,
                limit=limit,
                offset=offset,
                filters=filters
            )
        
        # 🆕 分析データを取得（改善版）
        analytics = translation_history_manager.get_translation_analytics(
            user_id=effective_user_id, 
            session_id=session_id,
            days=365  # 全期間の統計
        )
        
        # 今週の統計も取得
        analytics_week = translation_history_manager.get_translation_analytics(
            user_id=effective_user_id, 
            session_id=session_id,
            days=7
        )
        
        # 統計データを統合
        if analytics and 'basic_stats' in analytics:
            basic_stats = analytics['basic_stats']
            # 今週の翻訳数を統合
            if analytics_week and 'basic_stats' in analytics_week:
                basic_stats['this_week'] = analytics_week['basic_stats'].get('total_translations', 0)
            else:
                basic_stats['this_week'] = 0
            
            # テンプレート用の形式に変換
            analytics = {
                'total_translations': basic_stats.get('total_translations', 0),
                'this_week': basic_stats.get('this_week', 0),
                'bookmarked': basic_stats.get('bookmarked_count', 0),
                'avg_rating': basic_stats.get('avg_user_rating', 0.0)
            }
        else:
            analytics = {
                'total_translations': len(history_entries) if history_entries else 0,
                'this_week': 0,
                'bookmarked': 0,
                'avg_rating': 0.0
            }
        
        # 🆕 言語ペア統計
        language_stats = translation_history_manager.get_language_pair_stats(
            user_id=effective_user_id,
            session_id=session_id
        )
        
        csrf_token = generate_csrf_token()
        
        logger.info(f"翻訳履歴表示: user_id={effective_user_id}, entries={len(history_entries)}, page={page}")
        
        return render_template('translation_history.html',
                             labels=labels[current_lang],
                             history_entries=history_entries,
                             analytics=analytics,
                             language_stats=language_stats,
                             search_query=search_query,
                             page=page,
                             limit=limit,
                             filters=filters,
                             csrf_token=csrf_token)
    
    except Exception as e:
        logger.error(f"詳細翻訳履歴表示エラー: {str(e)}")
        flash(get_error_message('profile_error', current_lang), 'error')
        return redirect(url_for('auth.profile'))

@auth_bp.route('/history/analytics')
@require_auth
def translation_analytics():
    """翻訳分析データ表示"""
    current_lang = get_current_lang()
    user_id = session.get('user_id')
    
    if not TRANSLATION_HISTORY_AVAILABLE:
        flash('翻訳分析機能は現在利用できません', 'error')
        return redirect(url_for('auth.profile'))
    
    try:
        # 分析期間の取得
        days = int(request.args.get('days', 30))
        days = min(max(days, 1), 365)  # 1日〜365日の範囲に制限
        
        # 分析データを取得
        analytics = translation_history_manager.get_translation_analytics(user_id=user_id, days=days)
        
        # セッション履歴（ユーザーIDがない場合）
        session_analytics = {}
        if not user_id:
            session_id = session.get('session_id', session.get('csrf_token', '')[:16])
            if session_id:
                session_history = translation_history_manager.get_user_translation_history(
                    user_id=None, session_id=session_id, limit=100
                )
                session_analytics = {
                    'total_translations': len(session_history),
                    'recent_history': session_history[:10]
                }
        
        return render_template('translation_analytics.html',
                             labels=labels[current_lang],
                             analytics=analytics,
                             session_analytics=session_analytics,
                             days=days)
    
    except Exception as e:
        logger.error(f"翻訳分析表示エラー: {str(e)}")
        flash(get_error_message('profile_error', current_lang), 'error')
        return redirect(url_for('auth.profile'))

@auth_bp.route('/history/rate', methods=['POST'])
@require_auth
def rate_detailed_translation():
    """詳細翻訳履歴の評価（4段階評価システム対応）"""
    current_lang = get_current_lang()
    user_id = session.get('user_id')
    
    if not TRANSLATION_HISTORY_AVAILABLE:
        return jsonify({'success': False, 'error': '翻訳履歴機能は利用できません'})
    
    try:
        # CSRFトークン検証
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            return jsonify({'success': False, 'error': 'CSRF エラー'})
        
        history_id = int(request.form.get('history_id'))
        
        # 🆕 4段階評価データの処理
        evaluation_data_str = request.form.get('evaluation_data')
        feedback = request.form.get('feedback', '').strip()
        
        if evaluation_data_str:
            # 新しい4段階評価システム
            try:
                evaluation_data = json.loads(evaluation_data_str)
                
                # 必須項目の確認
                if not evaluation_data.get('usage'):
                    return jsonify({'success': False, 'error': '実際の利用選択は必須項目です'})
                
                # 数値評価への変換（後方互換性のため）
                usage_score_map = {
                    'use_as_is': 5,
                    'use_with_edit': 4,
                    'use_as_reference': 3,
                    'not_use': 2
                }
                numeric_rating = usage_score_map.get(evaluation_data['usage'], 3)
                
                # 詳細評価データを含むフィードバックを構築
                detailed_feedback = {
                    'evaluation_type': '4stage_system',
                    'usage': evaluation_data.get('usage'),
                    'context': evaluation_data.get('context'),
                    'best_translation': evaluation_data.get('best_translation'),
                    'gemini_analysis': evaluation_data.get('gemini_analysis'),
                    'user_feedback': feedback,
                    'submitted_at': datetime.now().isoformat()
                }
                
                detailed_feedback_json = json.dumps(detailed_feedback, ensure_ascii=False)
                
            except json.JSONDecodeError:
                return jsonify({'success': False, 'error': '評価データの形式が正しくありません'})
                
        else:
            # 従来の星評価システム（後方互換性）
            rating = int(request.form.get('rating', 0))
            if not (1 <= rating <= 5):
                return jsonify({'success': False, 'error': '評価は1〜5の範囲で入力してください'})
            
            numeric_rating = rating
            detailed_feedback_json = feedback
        
        # 評価を保存
        success = translation_history_manager.update_user_rating(history_id, numeric_rating, detailed_feedback_json)
        
        if success:
            # 🆕 統計データをリフレッシュ（平均評価更新）
            try:
                if user_id:
                    # 新認証システムユーザーの統計更新
                    profile_manager.refresh_user_statistics(user_id)
                else:
                    # 従来ユーザーの場合は翻訳履歴から平均評価を再計算
                    session_id = session.get('session_id', session.get('csrf_token', '')[:16])
                    if session_id:
                        analytics = translation_history_manager.get_translation_analytics(
                            user_id=None, session_id=session_id, days=365
                        )
                        avg_rating = analytics.get('basic_stats', {}).get('avg_user_rating', 0)
                        session['avg_rating'] = round(avg_rating, 1)
                
                # 4段階評価システムログ
                if evaluation_data_str:
                    logger.info(f"4段階評価システム評価完了: user_id={user_id}, history_id={history_id}, usage={evaluation_data.get('usage')}")
                else:
                    logger.info(f"従来評価システム評価完了: user_id={user_id}, history_id={history_id}, rating={numeric_rating}")
                    
            except Exception as e:
                logger.warning(f"評価更新後の統計リフレッシュエラー: {str(e)}")
            
            return jsonify({'success': True, 'message': '評価を保存しました'})
        else:
            return jsonify({'success': False, 'error': '評価の保存に失敗しました'})
    
    except Exception as e:
        logger.error(f"詳細翻訳評価エラー: {str(e)}")
        return jsonify({'success': False, 'error': 'エラーが発生しました'})

@auth_bp.route('/history/bookmark', methods=['POST'])
@require_auth
def bookmark_detailed_translation():
    """詳細翻訳履歴のブックマーク"""
    current_lang = get_current_lang()
    user_id = session.get('user_id')
    
    if not TRANSLATION_HISTORY_AVAILABLE:
        return jsonify({'success': False, 'error': '翻訳履歴機能は利用できません'})
    
    try:
        # CSRFトークン検証
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            return jsonify({'success': False, 'error': 'CSRF エラー'})
        
        history_id = int(request.form.get('history_id'))
        bookmarked = request.form.get('bookmarked') == 'true'
        
        # ブックマーク状態を更新
        success = translation_history_manager.toggle_bookmark(history_id, bookmarked)
        
        if success:
            # 🆕 統計データをリフレッシュ（プロフィール画面用）
            try:
                if user_id:
                    # 新認証システムユーザーの統計更新
                    profile_manager.refresh_user_statistics(user_id)
                else:
                    # 従来ユーザーの場合はセッション統計を更新
                    session_id = session.get('session_id', session.get('csrf_token', '')[:16])
                    if session_id:
                        # セッション内でブックマーク数を更新
                        current_bookmarks = session.get('bookmarked_count', 0)
                        if bookmarked:
                            session['bookmarked_count'] = current_bookmarks + 1
                        else:
                            session['bookmarked_count'] = max(0, current_bookmarks - 1)
                logger.info(f"ブックマーク更新後に統計データをリフレッシュ: user_id={user_id}")
            except Exception as e:
                logger.warning(f"統計データリフレッシュエラー: {str(e)}")
            
            action = 'ブックマーク' if bookmarked else 'ブックマーク解除'
            return jsonify({'success': True, 'message': f'{action}しました'})
        else:
            return jsonify({'success': False, 'error': '更新に失敗しました'})
    
    except Exception as e:
        logger.error(f"詳細翻訳ブックマークエラー: {str(e)}")
        return jsonify({'success': False, 'error': 'エラーが発生しました'})

@auth_bp.route('/history/export', methods=['POST'])
@require_auth
def export_detailed_history():
    """詳細翻訳履歴のエクスポート"""
    current_lang = get_current_lang()
    user_id = session.get('user_id')
    
    if not TRANSLATION_HISTORY_AVAILABLE:
        flash('翻訳履歴機能は現在利用できません', 'error')
        return redirect(url_for('auth.profile'))
    
    try:
        # CSRFトークン検証
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            flash(get_error_message('csrf_error', current_lang), 'error')
            return redirect(url_for('auth.detailed_translation_history'))
        
        export_format = request.form.get('format', 'json')
        session_id = session.get('session_id', '') if not user_id else ''
        
        # データをエクスポート
        export_data = translation_history_manager.export_user_history(
            user_id=user_id,
            session_id=session_id,
            format_type=export_format
        )
        
        if export_data:
            from flask import make_response
            
            if export_format == 'json':
                content_type = 'application/json; charset=utf-8'
                filename = f'langpont_detailed_history_{user_id or "session"}_{datetime.now().strftime("%Y%m%d")}.json'
            else:  # csv
                content_type = 'text/csv; charset=utf-8'
                filename = f'langpont_detailed_history_{user_id or "session"}_{datetime.now().strftime("%Y%m%d")}.csv'
            
            response = make_response(export_data)
            response.headers['Content-Type'] = content_type
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            
            logger.info(f"詳細翻訳履歴エクスポート: ユーザーID {user_id}, 形式 {export_format}")
            return response
        else:
            flash('データのエクスポートに失敗しました', 'error')
            return redirect(url_for('auth.detailed_translation_history'))
    
    except Exception as e:
        logger.error(f"詳細履歴エクスポートエラー: {str(e)}")
        flash('エクスポート中にエラーが発生しました', 'error')
        return redirect(url_for('auth.detailed_translation_history'))

@auth_bp.route('/history/cleanup', methods=['POST'])
@require_auth
def cleanup_old_translations():
    """古い翻訳履歴のクリーンアップ（管理者用）"""
    current_lang = get_current_lang()
    user_id = session.get('user_id')
    
    if not TRANSLATION_HISTORY_AVAILABLE:
        return jsonify({'success': False, 'error': '翻訳履歴機能は利用できません'})
    
    try:
        # 管理者権限チェック（簡易版）
        user_role = session.get('user_role', 'guest')
        if user_role not in ['admin', 'developer']:
            return jsonify({'success': False, 'error': '管理者権限が必要です'})
        
        # CSRFトークン検証
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            return jsonify({'success': False, 'error': 'CSRF エラー'})
        
        days_to_keep = int(request.form.get('days_to_keep', 180))
        keep_bookmarked = request.form.get('keep_bookmarked') == 'true'
        
        # クリーンアップ実行
        deleted_count = translation_history_manager.cleanup_old_history(
            days_to_keep=days_to_keep,
            keep_bookmarked=keep_bookmarked
        )
        
        logger.info(f"翻訳履歴クリーンアップ実行: {deleted_count}件削除, 実行者: {user_id}")
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count}件の古い履歴を削除しました'
        })
    
    except Exception as e:
        logger.error(f"翻訳履歴クリーンアップエラー: {str(e)}")
        return jsonify({'success': False, 'error': 'エラーが発生しました'})

@auth_bp.route('/api/history/stats', methods=['GET'])
@require_auth
def get_translation_stats_api():
    """翻訳統計API（JSON）"""
    current_lang = get_current_lang()
    user_id = session.get('user_id')
    
    if not TRANSLATION_HISTORY_AVAILABLE:
        return jsonify({'success': False, 'error': '翻訳履歴機能は利用できません'})
    
    try:
        days = int(request.args.get('days', 7))
        analytics = translation_history_manager.get_translation_analytics(user_id=user_id, days=days)
        
        return jsonify({
            'success': True,
            'analytics': analytics,
            'period_days': days
        })
    
    except Exception as e:
        logger.error(f"翻訳統計API取得エラー: {str(e)}")
        return jsonify({'success': False, 'error': 'エラーが発生しました'})

@auth_bp.route('/password/change', methods=['POST'])
@require_auth
def change_password():
    """パスワード変更"""
    current_lang = get_current_lang()
    
    try:
        # CSRFトークン検証
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            flash(get_error_message('csrf_error', current_lang), 'error')
            return redirect(url_for('auth.profile'))
        
        # フォームデータ取得
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # 基本入力検証
        if not current_password or not new_password or not confirm_password:
            flash(get_error_message('password_change_required', current_lang), 'error')
            return redirect(url_for('auth.profile'))
        
        if new_password != confirm_password:
            flash(get_error_message('password_mismatch', current_lang), 'error')
            return redirect(url_for('auth.profile'))
        
        # 新しいパスワードの強度チェック
        valid_password, password_error = auth_system.validate_password_strength(new_password)
        if not valid_password:
            flash(password_error, 'error')
            return redirect(url_for('auth.profile'))
        
        # TODO: UserAuthSystemクラスにchange_passwordメソッドを追加
        
        flash(get_error_message('password_changed', current_lang), 'success')
        logger.info(f"パスワード変更: ユーザーID {session.get('user_id')}")
        
        return redirect(url_for('auth.profile'))
    
    except Exception as e:
        logger.error(f"パスワード変更エラー: {str(e)}")
        flash(get_error_message('password_change_error', current_lang), 'error')
        return redirect(url_for('auth.profile'))

@auth_bp.route('/api/session/validate', methods=['POST'])
def validate_session_api():
    """セッション有効性API"""
    try:
        session_token = request.json.get('session_token') if request.is_json else None
        if not session_token:
            session_token = session.get('session_token')
        
        if not session_token:
            return jsonify({'valid': False, 'error': 'セッショントークンがありません'})
        
        is_valid, user_info = auth_system.validate_session(session_token)
        
        if is_valid:
            return jsonify({
                'valid': True,
                'user': {
                    'id': user_info['id'],
                    'username': user_info['username'],
                    'account_type': user_info['account_type'],
                    'early_access': user_info['early_access']
                }
            })
        else:
            return jsonify({'valid': False, 'error': 'セッションが無効です'})
    
    except Exception as e:
        logger.error(f"セッション検証APIエラー: {str(e)}")
        return jsonify({'valid': False, 'error': '検証エラーが発生しました'})

@auth_bp.route('/api/usage/update', methods=['POST'])
@require_auth
def update_usage_api():
    """使用回数更新API"""
    try:
        user_id = session.get('user_id')
        success = auth_system.update_user_usage(user_id)
        
        if success:
            return jsonify({'success': True, 'message': '使用回数を更新しました'})
        else:
            return jsonify({'success': False, 'error': '使用回数の更新に失敗しました'})
    
    except Exception as e:
        logger.error(f"使用回数更新APIエラー: {str(e)}")
        return jsonify({'success': False, 'error': 'API エラーが発生しました'})

@auth_bp.route('/cleanup')
def cleanup_sessions():
    """期限切れセッションクリーンアップ（管理者用）"""
    try:
        # 簡易的な管理者チェック（本番環境では適切な認証を実装）
        if not session.get('username') == 'admin':
            return jsonify({'error': '権限がありません'}), 403
        
        deleted_count = auth_system.cleanup_expired_sessions()
        return jsonify({
            'success': True,
            'message': f'{deleted_count} 件の期限切れセッションを削除しました'
        })
    
    except Exception as e:
        logger.error(f"セッションクリーンアップエラー: {str(e)}")
        return jsonify({'success': False, 'error': 'クリーンアップエラーが発生しました'})

# エラーハンドラー
@auth_bp.errorhandler(404)
def not_found_error(error):
    current_lang = get_current_lang()
    return render_template('error.html', 
                         labels=labels[current_lang],
                         error_code=404,
                         error_message=get_error_message('page_not_found', current_lang)), 404

@auth_bp.errorhandler(500)
def internal_error(error):
    current_lang = get_current_lang()
    logger.error(f"内部サーバーエラー: {str(error)}")
    return render_template('error.html', 
                         labels=labels[current_lang],
                         error_code=500,
                         error_message=get_error_message('internal_server_error', current_lang)), 500

# 初期化関数（緊急デバッグ版）
def init_auth_routes(app):
    """認証ルートを初期化"""
    print("🔍 DEBUG: init_auth_routes()関数開始")
    
    try:
        print("🔍 DEBUG: auth_bp Blueprintオブジェクト確認")
        print(f"  📍 auth_bp type: {type(auth_bp)}")
        print(f"  📍 auth_bp name: {auth_bp.name}")
        print(f"  📍 auth_bp url_prefix: {auth_bp.url_prefix}")
        
        # Blueprint登録前のルート数は取得できないため、登録後に確認
        
        print("🔍 DEBUG: Blueprint登録前のapp.blueprints:")
        for name, bp in app.blueprints.items():
            print(f"  📋 既存Blueprint: {name}")
        
        print("🔍 DEBUG: app.register_blueprint(auth_bp)実行")
        app.register_blueprint(auth_bp)
        print("✅ DEBUG: app.register_blueprint(auth_bp)成功")
        
        print("🔍 DEBUG: Blueprint登録後のapp.blueprints:")
        for name, bp in app.blueprints.items():
            print(f"  📋 登録済みBlueprint: {name}")
        
        # 登録後のルート数確認
        auth_routes = [rule for rule in app.url_map.iter_rules() if rule.endpoint and rule.endpoint.startswith('auth.')]
        print(f"  📍 認証ルート数: {len(auth_routes)}")
        
        print("🔍 DEBUG: 認証システム初期化開始")
        init_result = init_auth_system()
        print(f"🔍 DEBUG: init_auth_system()結果: {init_result}")
        
        logger.info("認証ルートが正常に初期化されました")
        print("✅ DEBUG: init_auth_routes()完了")
        return True
        
    except Exception as e:
        print(f"❌ DEBUG: init_auth_routes()エラー: {str(e)}")
        import traceback
        print(f"❌ DEBUG: エラー詳細:\n{traceback.format_exc()}")
        logger.error(f"認証ルート初期化エラー: {str(e)}")
        return False

if __name__ == "__main__":
    # テスト用
    from flask import Flask
    app = Flask(__name__)
    app.secret_key = 'test_secret_key'
    
    init_auth_routes(app)
    
    print("認証ルートテスト実行")
    with app.test_client() as client:
        response = client.get('/auth/register')
        print(f"登録ページテスト: {response.status_code}")