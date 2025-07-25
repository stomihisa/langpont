#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🚀 Task 2.9.2 Phase B-1: 管理者権限チェック強化システム
================================================================
目的: admin/developer権限のみアクセス可能な管理者専用機能を提供
機能: 権限チェックデコレータ、ユーザー権限管理、セキュリティ強化
"""

import logging
from functools import wraps
from flask import session, request, redirect, url_for, flash, abort
from typing import Dict, Any, Optional, List
import time
from datetime import datetime

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdminAuthManager:
    """管理者権限管理システム"""
    
    def __init__(self):
        """初期化"""
        # 管理者権限レベル定義
        self.admin_roles = {
            'admin': {
                'level': 100,
                'permissions': ['dashboard', 'user_management', 'system_config', 'logs', 'analytics'],
                'description': '最高管理者'
            },
            'developer': {
                'level': 80,
                'permissions': ['dashboard', 'logs', 'analytics', 'system_monitoring'],
                'description': '開発者'
            },
            'guest': {
                'level': 10,
                'permissions': ['basic_translation'],
                'description': 'ゲストユーザー'
            }
        }
        
        # アクセス制限機能
        self.failed_attempts = {}
        self.locked_ips = {}
        
        logger.info("🔐 AdminAuthManager初期化完了")
    
    def get_current_user_role(self) -> Optional[str]:
        """現在のユーザーの権限を取得"""
        if not session.get('logged_in'):
            return None
        
        user_role = session.get('user_role', 'guest')
        return user_role if user_role in self.admin_roles else 'guest'
    
    def get_current_user_info(self) -> Dict[str, Any]:
        """現在のユーザー情報を取得"""
        if not session.get('logged_in'):
            return {
                'logged_in': False,
                'username': None,
                'role': None,
                'permissions': [],
                'level': 0
            }
        
        username = session.get('username', 'unknown')
        role = self.get_current_user_role()
        role_info = self.admin_roles.get(role, self.admin_roles['guest'])
        
        return {
            'logged_in': True,
            'username': username,
            'role': role,
            'permissions': role_info['permissions'],
            'level': role_info['level'],
            'description': role_info['description'],
            'daily_limit': session.get('daily_limit', 0),
            'login_time': session.get('login_time', 'unknown')
        }
    
    def has_permission(self, required_permission: str) -> bool:
        """指定された権限を持っているかチェック"""
        user_info = self.get_current_user_info()
        
        if not user_info['logged_in']:
            return False
        
        return required_permission in user_info['permissions']
    
    def has_admin_access(self) -> bool:
        """管理者アクセス権限を持っているかチェック"""
        user_info = self.get_current_user_info()
        
        if not user_info['logged_in']:
            return False
        
        # admin または developer のみ管理者アクセス可能
        return user_info['role'] in ['admin', 'developer']
    
    def require_minimum_level(self, min_level: int) -> bool:
        """最小権限レベルを満たしているかチェック"""
        user_info = self.get_current_user_info()
        
        if not user_info['logged_in']:
            return False
        
        return user_info['level'] >= min_level
    
    def log_admin_access(self, action: str, details: str = "", success: bool = True):
        """管理者アクセスログを記録"""
        user_info = self.get_current_user_info()
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'username': user_info.get('username', 'anonymous'),
            'role': user_info.get('role', 'unknown'),
            'action': action,
            'details': details,
            'success': success,
            'ip_address': client_ip,
            'user_agent': request.headers.get('User-Agent', 'unknown')
        }
        
        if success:
            logger.info(f"🔐 Admin access: {user_info.get('username')} ({user_info.get('role')}) - {action}")
        else:
            logger.warning(f"🚨 Admin access denied: {user_info.get('username')} - {action} - {details}")
        
        # 実際のログ保存（将来的にデータベースに保存）
        return log_entry
    
    def check_brute_force_protection(self, client_ip: str) -> bool:
        """ブルートフォース攻撃保護"""
        current_time = time.time()
        
        # IPロック確認
        if client_ip in self.locked_ips:
            lock_time, lock_duration = self.locked_ips[client_ip]
            if current_time - lock_time < lock_duration:
                return False  # まだロック中
            else:
                # ロック期間終了
                del self.locked_ips[client_ip]
                if client_ip in self.failed_attempts:
                    del self.failed_attempts[client_ip]
        
        return True
    
    def record_failed_attempt(self, client_ip: str):
        """失敗した認証試行を記録"""
        current_time = time.time()
        
        if client_ip not in self.failed_attempts:
            self.failed_attempts[client_ip] = []
        
        # 1時間以内の失敗試行のみ保持
        self.failed_attempts[client_ip] = [
            timestamp for timestamp in self.failed_attempts[client_ip]
            if current_time - timestamp < 3600
        ]
        
        self.failed_attempts[client_ip].append(current_time)
        
        # 10回失敗で1時間ロック
        if len(self.failed_attempts[client_ip]) >= 10:
            self.locked_ips[client_ip] = (current_time, 3600)  # 1時間ロック
            logger.warning(f"🚨 IP {client_ip} locked for 1 hour due to too many failed admin access attempts")


# グローバルインスタンス
admin_auth_manager = AdminAuthManager()


def require_admin_access(f):
    """管理者アクセス必須デコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        
        # ブルートフォース保護確認
        if not admin_auth_manager.check_brute_force_protection(client_ip):
            admin_auth_manager.log_admin_access(
                action="admin_access_blocked",
                details=f"IP {client_ip} blocked due to too many failed attempts",
                success=False
            )
            abort(429)  # Too Many Requests
        
        # 管理者権限確認
        if not admin_auth_manager.has_admin_access():
            admin_auth_manager.record_failed_attempt(client_ip)
            admin_auth_manager.log_admin_access(
                action="unauthorized_admin_access",
                details=f"Attempted access to {request.endpoint}",
                success=False
            )
            
            if not session.get('logged_in'):
                flash('管理者権限が必要です。ログインしてください。', 'error')
                return redirect(url_for('login'))
            else:
                flash('管理者権限が不足しています。', 'error')
                return redirect(url_for('index'))
        
        # 成功ログ
        admin_auth_manager.log_admin_access(
            action=f"admin_access_granted",
            details=f"Accessed {request.endpoint}",
            success=True
        )
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_permission(required_permission: str):
    """特定権限必須デコレータ"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not admin_auth_manager.has_permission(required_permission):
                admin_auth_manager.log_admin_access(
                    action="permission_denied",
                    details=f"Required permission: {required_permission}",
                    success=False
                )
                
                flash(f'権限が不足しています: {required_permission}', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_minimum_level(min_level: int):
    """最小権限レベル必須デコレータ"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not admin_auth_manager.require_minimum_level(min_level):
                admin_auth_manager.log_admin_access(
                    action="insufficient_level",
                    details=f"Required level: {min_level}",
                    success=False
                )
                
                flash(f'権限レベルが不足しています (必要: {min_level})', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# テスト関数
def test_admin_auth_system():
    """管理者権限システムのテスト"""
    print("🧪 管理者権限システムテスト開始")
    print("=" * 60)
    
    # テスト用セッション設定
    test_users = [
        {'username': 'admin', 'role': 'admin', 'logged_in': True},
        {'username': 'developer', 'role': 'developer', 'logged_in': True},
        {'username': 'guest', 'role': 'guest', 'logged_in': True},
        {'username': None, 'role': None, 'logged_in': False}
    ]
    
    for test_user in test_users:
        print(f"\n📝 テストユーザー: {test_user['username']} ({test_user['role']})")
        
        # セッション模擬
        if test_user['logged_in']:
            session['logged_in'] = True
            session['username'] = test_user['username']
            session['user_role'] = test_user['role']
        else:
            session.clear()
        
        # 権限テスト
        user_info = admin_auth_manager.get_current_user_info()
        print(f"   ユーザー情報: {user_info}")
        print(f"   管理者アクセス: {admin_auth_manager.has_admin_access()}")
        print(f"   ダッシュボード権限: {admin_auth_manager.has_permission('dashboard')}")
        print(f"   ユーザー管理権限: {admin_auth_manager.has_permission('user_management')}")
    
    print("\n✅ 管理者権限システムテスト完了")


if __name__ == "__main__":
    test_admin_auth_system()