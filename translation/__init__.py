"""Translation module initialization
Task B2-10-Phase1a: TranslationContext分離モジュール
Task B2-10-Phase1c: LangPontTranslationExpertAI安全部分分離
Task B2-10-Phase1d-Step1: 抽象化アダプター追加
"""
from .context_manager import TranslationContext
from .expert_ai import LangPontTranslationExpertAI
from .adapters import SessionContextAdapter, SafeLoggerAdapter

__all__ = [
    # 既存のエクスポート（保持）
    'TranslationContext',
    'LangPontTranslationExpertAI',
    # 新規追加
    'SessionContextAdapter',
    'SafeLoggerAdapter'
]