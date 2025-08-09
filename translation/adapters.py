"""
Flask依存抽象化アダプター
Task B2-10-Phase1d-Step1で作成
"""
from typing import Dict, Any, Callable, Optional
import logging


class SessionContextAdapter:
    """Flask session依存を抽象化するアダプター"""

    def __init__(self, session_provider: Optional[Callable] = None):
        """
        Args:
            session_provider: セッションプロバイダー関数（デフォルト: Flask session）
        """
        self.session_provider = session_provider or self._default_session_provider

    def _default_session_provider(self):
        """デフォルトのFlask session provider"""
        from flask import session
        return session

    def get_translation_context(self) -> Dict[str, Any]:
        """
        翻訳コンテキストを取得（session依存を抽象化）
        Phase 3c-3: StateManager統合完了により参照のみ保持
        
        Returns:
            翻訳に必要な全コンテキストデータ
        """
        session = self.session_provider()

        # 言語ペア情報の安全な取得
        language_pair = session.get('language_pair', 'ja-en')
        try:
            source_lang, target_lang = language_pair.split('-')
        except (ValueError, AttributeError):
            source_lang, target_lang = 'ja', 'en'

        return {
            # 基本情報
            'original_text': session.get('input_text', ''),
            'language_pair': language_pair,
            'source_lang': source_lang,
            'target_lang': target_lang,

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


class SafeLoggerAdapter:
    """app_logger依存を抽象化するアダプター"""

    def __init__(self, logger_provider: Optional[Callable] = None):
        """
        Args:
            logger_provider: ロガープロバイダー関数（デフォルト: app logger）
        """
        self.logger_provider = logger_provider or self._default_logger_provider

    def _default_logger_provider(self):
        """デフォルトのapp_logger provider"""
        return logging.getLogger('app')

    def info(self, message: str):
        """情報ログを記録"""
        try:
            logger = self.logger_provider()
            logger.info(message)
        except Exception:
            # ログ記録失敗時は無視（アプリケーション継続を優先）
            pass

    def warning(self, message: str):
        """警告ログを記録"""
        try:
            logger = self.logger_provider()
            logger.warning(message)
        except Exception:
            # ログ記録失敗時は無視
            pass

    def error(self, message: str):
        """エラーログを記録"""
        try:
            logger = self.logger_provider()
            logger.error(message)
        except Exception:
            # ログ記録失敗時は無視
            pass