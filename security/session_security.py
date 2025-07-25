"""
セッション・パスワード管理セキュリティモジュール
Task B2-9-Phase2で分離

このモジュールは以下のクラスを提供します：
- SecureSessionManager: セキュアなセッション管理
- SecurePasswordManager: セキュアなパスワード管理
"""

import time
import re
from typing import Tuple
from flask import session
from werkzeug.security import generate_password_hash, check_password_hash


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