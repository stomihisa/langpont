"""
セキュリティ・アクセスログ管理モジュール
Task B2-9-Phase4で分離

このモジュールは以下の関数を提供します：
- log_security_event: セキュリティイベントログの記録
- log_access_event: アクセスログの記録
"""

import json
import logging
from datetime import datetime
from security.request_helpers import (
    get_client_ip_safe, get_user_agent_safe, 
    get_endpoint_safe, get_method_safe
)


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

    # セキュリティログの取得（アプリ側で初期化済み）
    security_logger = logging.getLogger('security')

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

    # アクセスログの取得（アプリ側で初期化済み）
    access_logger = logging.getLogger('access')
    access_logger.info(json.dumps(access_data, ensure_ascii=False))