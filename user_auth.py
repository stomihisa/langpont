#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangPont ユーザー認証システム基盤
Task 2.6.1 - ユーザー認証システム基盤構築

セキュアなユーザー認証、登録、セッション管理を提供
"""

import sqlite3
import hashlib
import secrets
import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, Any
import bcrypt
from werkzeug.security import generate_password_hash, check_password_hash

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserAuthSystem:
    """ユーザー認証システムクラス"""
    
    def __init__(self, db_path: str = "langpont_users.db"):
        """
        ユーザー認証システムを初期化
        
        Args:
            db_path: SQLiteデータベースファイルのパス
        """
        self.db_path = db_path
        self.init_database()
        
    def init_database(self) -> None:
        """データベースとテーブルを初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # usersテーブル作成
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP NULL,
                        is_active BOOLEAN DEFAULT 1,
                        account_type VARCHAR(20) DEFAULT 'basic',
                        early_access BOOLEAN DEFAULT 0,
                        preferred_lang VARCHAR(5) DEFAULT 'jp',
                        daily_usage_count INTEGER DEFAULT 0,
                        last_usage_date DATE NULL,
                        email_verified BOOLEAN DEFAULT 0,
                        verification_token TEXT NULL,
                        reset_token TEXT NULL,
                        reset_token_expires TIMESTAMP NULL,
                        two_factor_enabled BOOLEAN DEFAULT 0,
                        two_factor_secret TEXT NULL,
                        login_attempts INTEGER DEFAULT 0,
                        locked_until TIMESTAMP NULL,
                        user_settings TEXT DEFAULT '{}',
                        profile_data TEXT DEFAULT '{}'
                    )
                ''')
                
                # user_sessionsテーブル作成
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        session_token TEXT UNIQUE NOT NULL,
                        csrf_token TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        ip_address TEXT NULL,
                        user_agent TEXT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # login_historyテーブル作成（セキュリティ追跡用）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS login_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NULL,
                        username VARCHAR(50) NULL,
                        ip_address TEXT NULL,
                        user_agent TEXT NULL,
                        login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN NOT NULL,
                        failure_reason TEXT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
                    )
                ''')
                
                # インデックス作成（パフォーマンス向上）
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions (session_token)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions (user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_login_history_user_id ON login_history (user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_login_history_ip ON login_history (ip_address)')
                
                conn.commit()
                logger.info("ユーザー認証データベースが正常に初期化されました")
                
        except Exception as e:
            logger.error(f"データベース初期化エラー: {str(e)}")
            raise
    
    def _generate_salt(self) -> str:
        """セキュアなソルトを生成"""
        return secrets.token_hex(32)
    
    def _hash_password(self, password: str, salt: str) -> str:
        """
        パスワードをソルト付きでハッシュ化
        
        Args:
            password: プレーンテキストパスワード
            salt: ソルト
            
        Returns:
            ハッシュ化されたパスワード
        """
        # bcrypt + 追加のソルトでセキュリティ強化
        password_bytes = (password + salt).encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12))
        return hashed.decode('utf-8')
    
    def _verify_password(self, password: str, salt: str, hashed: str) -> bool:
        """
        パスワードを検証
        
        Args:
            password: プレーンテキストパスワード
            salt: ソルト
            hashed: ハッシュ化されたパスワード
            
        Returns:
            パスワードが正しい場合True
        """
        try:
            password_bytes = (password + salt).encode('utf-8')
            hashed_bytes = hashed.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception as e:
            logger.error(f"パスワード検証エラー: {str(e)}")
            return False
    
    def _generate_session_token(self) -> str:
        """セッショントークンを生成"""
        return secrets.token_urlsafe(64)
    
    def _generate_csrf_token(self) -> str:
        """CSRFトークンを生成"""
        return secrets.token_urlsafe(32)
    
    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """
        パスワード強度を検証
        
        Args:
            password: 検証するパスワード
            
        Returns:
            (成功/失敗, エラーメッセージ)
        """
        if len(password) < 8:
            return False, "パスワードは8文字以上である必要があります"
        
        if len(password) > 128:
            return False, "パスワードが長すぎます（最大128文字）"
        
        if not any(c.isupper() for c in password):
            return False, "パスワードには大文字を含む必要があります"
        
        if not any(c.islower() for c in password):
            return False, "パスワードには小文字を含む必要があります"
        
        if not any(c.isdigit() for c in password):
            return False, "パスワードには数字を含む必要があります"
        
        # 特殊文字チェック
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, "パスワードには特殊文字を含む必要があります"
        
        return True, ""
    
    def validate_email(self, email: str) -> Tuple[bool, str]:
        """
        メールアドレスを検証
        
        Args:
            email: 検証するメールアドレス
            
        Returns:
            (成功/失敗, エラーメッセージ)
        """
        import re
        
        if not email:
            return False, "メールアドレスが入力されていません"
        
        if len(email) > 100:
            return False, "メールアドレスが長すぎます"
        
        # 基本的なメールアドレス形式チェック
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "無効なメールアドレス形式です"
        
        return True, ""
    
    def validate_username(self, username: str) -> Tuple[bool, str]:
        """
        ユーザー名を検証
        
        Args:
            username: 検証するユーザー名
            
        Returns:
            (成功/失敗, エラーメッセージ)
        """
        if not username:
            return False, "ユーザー名が入力されていません"
        
        if len(username) < 3:
            return False, "ユーザー名は3文字以上である必要があります"
        
        if len(username) > 50:
            return False, "ユーザー名が長すぎます（最大50文字）"
        
        # 英数字とアンダースコアのみ許可
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "ユーザー名には英数字とアンダースコアのみ使用できます"
        
        return True, ""
    
    def register_user(self, username: str, email: str, password: str, 
                     account_type: str = 'basic', early_access: bool = False) -> Tuple[bool, str, Optional[int]]:
        """
        新しいユーザーを登録
        
        Args:
            username: ユーザー名
            email: メールアドレス
            password: パスワード
            account_type: アカウントタイプ（basic, premium, unlimited）
            early_access: Early Accessアカウント
            
        Returns:
            (成功/失敗, メッセージ, ユーザーID)
        """
        try:
            # 入力値検証
            valid_username, username_error = self.validate_username(username)
            if not valid_username:
                return False, username_error, None
            
            valid_email, email_error = self.validate_email(email)
            if not valid_email:
                return False, email_error, None
            
            valid_password, password_error = self.validate_password_strength(password)
            if not valid_password:
                return False, password_error, None
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 既存ユーザーチェック
                cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
                existing_user = cursor.fetchone()
                if existing_user:
                    return False, "ユーザー名またはメールアドレスが既に使用されています", None
                
                # パスワードハッシュ化
                salt = self._generate_salt()
                password_hash = self._hash_password(password, salt)
                
                # ユーザー登録
                cursor.execute('''
                    INSERT INTO users (
                        username, email, password_hash, salt, account_type, early_access,
                        verification_token, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    username, email, password_hash, salt, account_type, early_access,
                    self._generate_session_token(), datetime.now()
                ))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"新しいユーザーが登録されました: {username} (ID: {user_id})")
                return True, "ユーザー登録が完了しました", user_id
                
        except Exception as e:
            logger.error(f"ユーザー登録エラー: {str(e)}")
            return False, "登録処理中にエラーが発生しました", None
    
    def authenticate_user(self, login_identifier: str, password: str, 
                         ip_address: str = None, user_agent: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        ユーザー認証を実行
        
        Args:
            login_identifier: ユーザー名またはメールアドレス
            password: パスワード
            ip_address: IPアドレス
            user_agent: ユーザーエージェント
            
        Returns:
            (成功/失敗, メッセージ, ユーザー情報)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # ユーザー情報取得
                cursor.execute('''
                    SELECT id, username, email, password_hash, salt, is_active, 
                           login_attempts, locked_until, account_type, early_access
                    FROM users 
                    WHERE (username = ? OR email = ?) AND is_active = 1
                ''', (login_identifier, login_identifier))
                
                user = cursor.fetchone()
                
                # ログイン履歴記録（成功/失敗問わず）
                def log_attempt(success: bool, failure_reason: str = None):
                    cursor.execute('''
                        INSERT INTO login_history (
                            user_id, username, ip_address, user_agent, success, failure_reason
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        user[0] if user else None,
                        login_identifier,
                        ip_address,
                        user_agent,
                        success,
                        failure_reason
                    ))
                
                if not user:
                    log_attempt(False, "ユーザーが見つかりません")
                    conn.commit()
                    return False, "ユーザー名またはパスワードが間違っています", None
                
                user_id, username, email, password_hash, salt, is_active, login_attempts, locked_until, account_type, early_access = user
                
                # アカウントロックチェック
                if locked_until and datetime.fromisoformat(locked_until) > datetime.now():
                    log_attempt(False, "アカウントがロックされています")
                    conn.commit()
                    return False, "アカウントがロックされています。しばらく待ってから再試行してください", None
                
                # パスワード検証
                if not self._verify_password(password, salt, password_hash):
                    # ログイン試行回数増加
                    new_attempts = login_attempts + 1
                    lock_time = None
                    
                    if new_attempts >= 5:
                        # 5回失敗でアカウントロック（30分）
                        lock_time = datetime.now() + timedelta(minutes=30)
                        cursor.execute(
                            'UPDATE users SET login_attempts = ?, locked_until = ? WHERE id = ?',
                            (new_attempts, lock_time, user_id)
                        )
                        log_attempt(False, "パスワードが間違っています（アカウントロック）")
                        conn.commit()
                        return False, "パスワードが間違っています。アカウントがロックされました", None
                    else:
                        cursor.execute(
                            'UPDATE users SET login_attempts = ? WHERE id = ?',
                            (new_attempts, user_id)
                        )
                        log_attempt(False, "パスワードが間違っています")
                        conn.commit()
                        return False, f"パスワードが間違っています。残り{5-new_attempts}回試行できます", None
                
                # 認証成功 - ログイン試行回数リセット、最終ログイン時刻更新
                cursor.execute('''
                    UPDATE users 
                    SET login_attempts = 0, locked_until = NULL, last_login = ? 
                    WHERE id = ?
                ''', (datetime.now(), user_id))
                
                log_attempt(True)
                conn.commit()
                
                user_info = {
                    'id': user_id,
                    'username': username,
                    'email': email,
                    'account_type': account_type,
                    'early_access': bool(early_access),
                    'is_active': bool(is_active)
                }
                
                logger.info(f"ユーザー認証成功: {username} (ID: {user_id})")
                return True, "認証に成功しました", user_info
                
        except Exception as e:
            logger.error(f"ユーザー認証エラー: {str(e)}")
            return False, "認証処理中にエラーが発生しました", None
    
    def create_session(self, user_id: int, ip_address: str = None, 
                      user_agent: str = None, expires_hours: int = 24) -> Tuple[bool, str, Optional[Dict]]:
        """
        ユーザーセッションを作成
        
        Args:
            user_id: ユーザーID
            ip_address: IPアドレス
            user_agent: ユーザーエージェント
            expires_hours: セッション有効期限（時間）
            
        Returns:
            (成功/失敗, メッセージ, セッション情報)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 既存のアクティブセッションを無効化
                cursor.execute(
                    'UPDATE user_sessions SET is_active = 0 WHERE user_id = ? AND is_active = 1',
                    (user_id,)
                )
                
                # 新しいセッション作成
                session_token = self._generate_session_token()
                csrf_token = self._generate_csrf_token()
                expires_at = datetime.now() + timedelta(hours=expires_hours)
                
                cursor.execute('''
                    INSERT INTO user_sessions (
                        user_id, session_token, csrf_token, expires_at, 
                        ip_address, user_agent, created_at, last_activity
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, session_token, csrf_token, expires_at,
                    ip_address, user_agent, datetime.now(), datetime.now()
                ))
                
                session_id = cursor.lastrowid
                conn.commit()
                
                session_info = {
                    'session_id': session_id,
                    'session_token': session_token,
                    'csrf_token': csrf_token,
                    'expires_at': expires_at.isoformat(),
                    'user_id': user_id
                }
                
                logger.info(f"新しいセッションが作成されました: User {user_id}, Session {session_id}")
                return True, "セッションが作成されました", session_info
                
        except Exception as e:
            logger.error(f"セッション作成エラー: {str(e)}")
            return False, "セッション作成中にエラーが発生しました", None
    
    def validate_session(self, session_token: str) -> Tuple[bool, Optional[Dict]]:
        """
        セッションを検証
        
        Args:
            session_token: セッショントークン
            
        Returns:
            (有効/無効, ユーザー情報)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT s.user_id, s.csrf_token, s.expires_at, 
                           u.username, u.email, u.account_type, u.early_access, u.is_active
                    FROM user_sessions s
                    JOIN users u ON s.user_id = u.id
                    WHERE s.session_token = ? AND s.is_active = 1 AND u.is_active = 1
                ''', (session_token,))
                
                result = cursor.fetchone()
                if not result:
                    return False, None
                
                user_id, csrf_token, expires_at, username, email, account_type, early_access, is_active = result
                
                # 有効期限チェック
                if datetime.fromisoformat(expires_at) <= datetime.now():
                    # 期限切れセッションを無効化
                    cursor.execute(
                        'UPDATE user_sessions SET is_active = 0 WHERE session_token = ?',
                        (session_token,)
                    )
                    conn.commit()
                    return False, None
                
                # 最終アクティビティ時刻更新
                cursor.execute(
                    'UPDATE user_sessions SET last_activity = ? WHERE session_token = ?',
                    (datetime.now(), session_token)
                )
                conn.commit()
                
                user_info = {
                    'id': user_id,
                    'username': username,
                    'email': email,
                    'account_type': account_type,
                    'early_access': bool(early_access),
                    'is_active': bool(is_active),
                    'csrf_token': csrf_token
                }
                
                return True, user_info
                
        except Exception as e:
            logger.error(f"セッション検証エラー: {str(e)}")
            return False, None
    
    def logout_user(self, session_token: str) -> bool:
        """
        ユーザーをログアウト
        
        Args:
            session_token: セッショントークン
            
        Returns:
            成功/失敗
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    'UPDATE user_sessions SET is_active = 0 WHERE session_token = ?',
                    (session_token,)
                )
                
                affected_rows = cursor.rowcount
                conn.commit()
                
                if affected_rows > 0:
                    logger.info(f"ユーザーがログアウトしました: Session {session_token[:16]}...")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"ログアウトエラー: {str(e)}")
            return False
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """
        ユーザーIDからユーザー情報を取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            ユーザー情報またはNone
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, username, email, created_at, last_login, account_type, 
                           early_access, preferred_lang, daily_usage_count, last_usage_date,
                           email_verified, user_settings, profile_data
                    FROM users 
                    WHERE id = ? AND is_active = 1
                ''', (user_id,))
                
                result = cursor.fetchone()
                if not result:
                    return None
                
                (id, username, email, created_at, last_login, account_type, 
                 early_access, preferred_lang, daily_usage_count, last_usage_date,
                 email_verified, user_settings, profile_data) = result
                
                return {
                    'id': id,
                    'username': username,
                    'email': email,
                    'created_at': created_at,
                    'last_login': last_login,
                    'account_type': account_type,
                    'early_access': bool(early_access),
                    'preferred_lang': preferred_lang,
                    'daily_usage_count': daily_usage_count,
                    'last_usage_date': last_usage_date,
                    'email_verified': bool(email_verified),
                    'user_settings': json.loads(user_settings) if user_settings else {},
                    'profile_data': json.loads(profile_data) if profile_data else {}
                }
                
        except Exception as e:
            logger.error(f"ユーザー情報取得エラー: {str(e)}")
            return None
    
    def update_user_usage(self, user_id: int) -> bool:
        """
        ユーザーの使用回数を更新
        
        Args:
            user_id: ユーザーID
            
        Returns:
            成功/失敗
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                today = datetime.now().date()
                
                # 前回の使用日をチェック
                cursor.execute(
                    'SELECT daily_usage_count, last_usage_date FROM users WHERE id = ?',
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    current_count, last_date = result
                    
                    # 日付が変わっていればカウントリセット
                    if not last_date or last_date != str(today):
                        new_count = 1
                    else:
                        new_count = current_count + 1
                    
                    cursor.execute('''
                        UPDATE users 
                        SET daily_usage_count = ?, last_usage_date = ? 
                        WHERE id = ?
                    ''', (new_count, today, user_id))
                    
                    conn.commit()
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"使用回数更新エラー: {str(e)}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        期限切れセッションをクリーンアップ
        
        Returns:
            削除されたセッション数
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    'DELETE FROM user_sessions WHERE expires_at <= ? OR is_active = 0',
                    (datetime.now(),)
                )
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"期限切れセッション {deleted_count} 件を削除しました")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"セッションクリーンアップエラー: {str(e)}")
            return 0


# 使用例とテスト関数
if __name__ == "__main__":
    # テスト用実行
    auth_system = UserAuthSystem("test_users.db")
    
    # テストユーザー登録
    success, message, user_id = auth_system.register_user(
        "testuser", "test@example.com", "SecurePass123!", "premium", True
    )
    print(f"登録結果: {success}, {message}, ユーザーID: {user_id}")
    
    if success:
        # テスト認証
        auth_success, auth_message, user_info = auth_system.authenticate_user(
            "testuser", "SecurePass123!", "127.0.0.1", "Test Browser"
        )
        print(f"認証結果: {auth_success}, {auth_message}")
        
        if auth_success:
            # テストセッション作成
            session_success, session_message, session_info = auth_system.create_session(
                user_info['id'], "127.0.0.1", "Test Browser"
            )
            print(f"セッション作成: {session_success}, {session_message}")