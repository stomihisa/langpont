"""
翻訳コンテキスト管理モジュール
Task B2-10-Phase1aで分離 - TranslationContextクラス

このモジュールは以下の機能を提供します：
- save_context: 翻訳コンテキストのセッション保存（入力値検証付き）
- get_context: 翻訳コンテキストの取得（期限チェック付き）
- clear_context: 翻訳コンテキストのクリア
"""

import time
import uuid
from datetime import datetime
from typing import Dict, Any
from flask import session
from security.input_validation import EnhancedInputValidator
from security.security_logger import log_access_event


class TranslationContext:
    """翻訳コンテキストを管理するクラス（セキュリティ強化版）"""

    @staticmethod
    def save_context(input_text: str, translations: Dict[str, str], analysis: str, metadata: Dict[str, Any]) -> None:
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

        # 🆕 ユニークIDとタイムスタンプを追加
        context_id = str(uuid.uuid4())[:8]  # 短縮ユニークID
        current_timestamp = time.time()

        # 🆕 Cookieサイズ制限対策：大容量データを軽量化
        session["translation_context"] = {
            "context_id": context_id,
            "timestamp": current_timestamp,
            "created_at": datetime.now().isoformat(),
            "source_lang": metadata.get("source_lang", ""),
            "target_lang": metadata.get("target_lang", ""),
            # 大容量データは個別のセッションキーから参照（重複排除）
            "has_data": True
        }

        log_access_event(f'Translation context saved: ID={context_id}, timestamp={current_timestamp}')

    @staticmethod
    def get_context() -> Dict[str, Any]:
        """保存された翻訳コンテキストを取得（期限チェック付き・Cookieサイズ対策版）"""
        context = session.get("translation_context", {})

        if context and context.get("has_data"):
            context_id = context.get("context_id", "unknown")

            # 古いコンテキストは削除（1時間以上前）
            if time.time() - context.get("timestamp", 0) > 3600:
                log_access_event(f'Translation context expired: ID={context_id}')
                TranslationContext.clear_context()
                return {}

            # 🆕 大容量データを個別セッションキーから再構築（重複排除・逆翻訳含む）
            full_context = {
                "context_id": context_id,
                "timestamp": context.get("timestamp"),
                "created_at": context.get("created_at"),
                "input_text": session.get("input_text", ""),
                "translations": {
                    "chatgpt": session.get("translated_text", ""),
                    "enhanced": session.get("better_translation", ""),
                    "gemini": session.get("gemini_translation", ""),
                    # 🆕 逆翻訳データを追加（KeyError対策）
                    "chatgpt_reverse": session.get("reverse_translated_text", ""),
                    "enhanced_reverse": session.get("reverse_better_translation", ""),
                    "gemini_reverse": session.get("gemini_reverse_translation", "")
                },
                "analysis": session.get("gemini_3way_analysis", ""),
                "metadata": {
                    "source_lang": context.get("source_lang", ""),
                    "target_lang": context.get("target_lang", ""),
                    "partner_message": session.get("partner_message", ""),
                    "context_info": session.get("context_info", "")
                }
            }

            log_access_event(f'Translation context retrieved: ID={context_id}')
            return full_context

        return {}

    @staticmethod
    def clear_context() -> None:
        """翻訳コンテキストをクリア"""
        context = session.get("translation_context", {})
        if context:
            context_id = context.get("context_id", "unknown")
            log_access_event(f'Translation context cleared: ID={context_id}')
        session.pop("translation_context", None)