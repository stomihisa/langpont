"""
インタラクティブサービスモジュール
Task #9-3 AP-1 Phase 3b: インタラクティブ機能のBlueprint分離

このモジュールは以下の機能を提供します：
- インタラクティブ質問処理
- 翻訳コンテキスト管理との連携
- TranslationStateManager統合
- 依存注入による疎結合設計
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional
from flask import session
from security.input_validation import EnhancedInputValidator
from security.security_logger import log_security_event, log_access_event
# Phase 3c-1b: TranslationContext統合 - import削除


class InteractiveService:
    """インタラクティブサービスの統合クラス"""
    
    def __init__(self, translation_state_manager, interactive_processor, logger, labels):
        """
        依存注入によるコンストラクタ
        
        Args:
            translation_state_manager: TranslationStateManager instance
            interactive_processor: LangPontTranslationExpertAI instance
            logger: Application logger
            labels: Multilingual labels
        """
        self.state_manager = translation_state_manager
        self.processor = interactive_processor
        self.logger = logger
        self.labels = labels
    
    def process_interactive_question(self, session_id: str, question: str, display_lang: str) -> Dict[str, Any]:
        """
        インタラクティブ質問を処理（app.pyから移動）
        
        Args:
            session_id: セッションID
            question: ユーザーからの質問
            display_lang: 表示言語
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        try:
            start_time = time.time()
            
            # 多言語対応エラーメッセージ
            error_messages = self._get_error_messages()
            
            # 入力値検証
            validation_result = self._validate_question_input(question, display_lang, error_messages)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"]
                }
            
            # 翻訳コンテキスト取得（StateManagerから - Phase 3c-1b統合）
            context = self.state_manager.get_context_data(session_id) if self.state_manager else {}
            if not context:
                error_message = error_messages["no_context"].get(
                    display_lang, error_messages["no_context"]["jp"]
                )
                return {
                    "success": False,
                    "error": error_message
                }
            
            # コンテキストに表示言語追加
            context['display_language'] = display_lang
            
            # Phase 3c実装時: TranslationStateManagerとの統合
            # if self.state_manager and session_id:
            #     # コンテキストをRedisからも取得・更新
            #     pass
            
            # 質問処理実行
            result = self.processor.process_question(question, context)
            
            # 回答最適化処理
            optimized_result = self._optimize_response(question, result)
            
            # 処理時間計測
            processing_time = time.time() - start_time
            log_access_event(
                f'Interactive question processed: type={result.get("type")}, time={processing_time:.2f}s'
            )
            
            # Phase 3c実装時: 質問履歴をStateManagerに保存
            # if self.state_manager and session_id:
            #     self._save_question_history(session_id, optimized_result)
            
            return {
                "success": True,
                "result": result,
                "current_chat": optimized_result["current_chat"]
            }
            
        except Exception as e:
            import traceback
            self.logger.error(f"Interactive question processing error: {str(e)}")
            self.logger.error(traceback.format_exc())
            log_security_event('INTERACTIVE_PROCESSING_ERROR', f'Error: {str(e)}', 'ERROR')
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def clear_chat_history(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        チャット履歴をクリア（Cookie最適化版）
        
        Args:
            session_id: セッションID（Phase 3c で使用予定）
            
        Returns:
            Dict[str, Any]: クリア結果
        """
        try:
            # Phase 3c実装時: RedisからもQA履歴をクリア
            # if self.state_manager and session_id:
            #     self.state_manager.clear_translation_state(session_id, "interactive_history")
            
            log_access_event('Chat history clear requested (client-side management)')
            
            return {
                "success": True,
                "message": "チャット履歴をクリアしました（クライアント側で管理）"
            }
            
        except Exception as e:
            self.logger.error(f"Chat history clear error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_error_messages(self) -> Dict[str, Dict[str, str]]:
        """多言語対応エラーメッセージ取得"""
        return {
            "no_question": {
                "jp": "質問が入力されていません",
                "en": "No question has been entered",
                "fr": "Aucune question n'a été saisie",
                "es": "No se ha ingresado ninguna pregunta"
            },
            "no_context": {
                "jp": "翻訳コンテキストが見つかりません。まず翻訳を実行してください。",
                "en": "Translation context not found. Please perform a translation first.",
                "fr": "Contexte de traduction non trouvé. Veuillez d'abord effectuer une traduction.",
                "es": "Contexto de traducción no encontrado. Por favor, realice una traducción primero."
            }
        }
    
    def _validate_question_input(self, question: str, display_lang: str, error_messages: Dict) -> Dict[str, Any]:
        """
        質問入力の検証
        
        Args:
            question: 質問テキスト
            display_lang: 表示言語
            error_messages: エラーメッセージ辞書
            
        Returns:
            Dict[str, Any]: 検証結果
        """
        if not question:
            error_message = error_messages["no_question"].get(
                display_lang, error_messages["no_question"]["jp"]
            )
            return {
                "valid": False,
                "error": error_message
            }
        
        # 厳密な入力値検証
        is_valid, error_msg = EnhancedInputValidator.validate_text_input(
            question, max_length=1000, min_length=5, field_name="質問"
        )
        
        if not is_valid:
            log_security_event(
                'INVALID_INTERACTIVE_QUESTION',
                f'Question validation failed: {error_msg}',
                'WARNING'
            )
            return {
                "valid": False,
                "error": error_msg
            }
        
        return {"valid": True}
    
    def _optimize_response(self, question: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        回答最適化処理（Cookie最適化対応）
        
        Args:
            question: 元の質問
            result: AI処理結果
            
        Returns:
            Dict[str, Any]: 最適化された結果
        """
        answer_text = result.get("result", "")
        max_answer_length = 2500
        max_question_length = 1000
        
        # 回答の長さ最適化
        if len(answer_text) > max_answer_length:
            # 回答の最後が文の途中で切れないよう、句読点で切断
            truncated = answer_text[:max_answer_length]
            last_punct = max(
                truncated.rfind('。'), truncated.rfind('！'), 
                truncated.rfind('？'), truncated.rfind('.')
            )
            
            if last_punct > max_answer_length - 200:  # 句読点が近くにある場合
                answer_text = answer_text[:last_punct + 1] + "\n\n[回答が長いため省略されました]"
            else:
                answer_text = answer_text[:max_answer_length] + "...\n\n[回答が長いため省略されました]"
        
        # 質問も同様に適切に切断
        question_text = question
        if len(question_text) > max_question_length:
            question_text = question_text[:max_question_length] + "..."
        
        # 現在の質問と回答のみを含むレスポンスを作成
        current_chat_item = {
            "question": question_text,
            "answer": answer_text,
            "type": result.get("type", "general"),
            "timestamp": time.time()
        }
        
        return {
            "current_chat": current_chat_item,
            "original_result": result
        }
    
    def _save_question_history(self, session_id: str, optimized_result: Dict[str, Any]) -> bool:
        """
        質問履歴をTranslationStateManagerに保存（Phase 3c実装予定）
        
        Args:
            session_id: セッションID
            optimized_result: 最適化された結果
            
        Returns:
            bool: 保存成功フラグ
        """
        try:
            if not self.state_manager:
                return False
            
            # Phase 3c で実装予定
            # qa_history = {
            #     "question": optimized_result["current_chat"]["question"],
            #     "answer": optimized_result["current_chat"]["answer"],
            #     "type": optimized_result["current_chat"]["type"],
            #     "timestamp": optimized_result["current_chat"]["timestamp"]
            # }
            # 
            # return self.state_manager.save_large_data(
            #     "interactive_history", json.dumps(qa_history), session_id
            # )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save question history: {e}")
            return False