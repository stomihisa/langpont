"""Translation module initialization
Task B2-10-Phase1a: TranslationContext分離モジュール (Phase 3c-1b: StateManagerに統合完了)
Task B2-10-Phase1c: LangPontTranslationExpertAI安全部分分離
Task B2-10-Phase1d-Step1: 抽象化アダプター追加
"""
# Phase 3c-1b: TranslationContext削除 - StateManagerに統合完了
from .expert_ai import LangPontTranslationExpertAI
from .adapters import SessionContextAdapter, SafeLoggerAdapter

__all__ = [
    # Phase 3c-1b: TranslationContext削除
    'LangPontTranslationExpertAI',
    # 継続使用
    'SessionContextAdapter',
    'SafeLoggerAdapter'
]