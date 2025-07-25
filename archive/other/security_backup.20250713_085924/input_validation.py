"""
LangPont Input Validation System
Task B2-9-Phase1: セキュリティ強化版入力値検証システム
"""

import re
from typing import Tuple, Optional

# セキュリティログとクライアントIP取得の参照（app.pyから）
try:
    import logging
    security_logger = logging.getLogger('security')
except ImportError:
    import logging
    security_logger = logging.getLogger(__name__)

def get_client_ip_safe():
    """安全なクライアントIP取得（app.pyの関数への参照回避）"""
    try:
        from flask import request
        return request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    except (ImportError, RuntimeError):
        return 'unknown'

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