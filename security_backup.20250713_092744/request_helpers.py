"""
リクエスト関連ヘルパー関数モジュール
Task B2-9-Phase3で分離

このモジュールは以下の関数を提供します：
- get_client_ip: クライアントIPアドレスを安全に取得
- get_client_ip_safe: リクエストコンテキスト外でも安全なIP取得
- get_user_agent_safe: リクエストコンテキスト外でも安全なUser-Agent取得
- get_endpoint_safe: リクエストコンテキスト外でも安全なエンドポイント取得
- get_method_safe: リクエストコンテキスト外でも安全なメソッド取得
"""

from typing import Optional
from flask import request


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