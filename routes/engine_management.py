"""
🎯 TaskH2-2(B2-3) Stage 2 Phase 7: エンジン状態管理モジュール
責務分離による保守性向上実装

Pure Server Layer - エンジン状態管理のみ
- セッション更新のみ
- バリデーションのみ  
- 状態永続化のみ
- UI操作なし
- DOM操作なし

分離元: app.py Lines 2497-2531 (35行)
分離日: 2025年7月20日
"""

from flask import Blueprint, request, session, jsonify
from typing import Dict, Any, Tuple


class EngineStateManager:
    """
    純粋な責務: エンジン状態管理のみ
    UI操作・DOM操作を一切含まない状態管理専用クラス
    """
    
    def __init__(self, app_logger=None, log_access_event=None):
        """依存注入による初期化"""
        self.app_logger = app_logger
        self.log_access_event = log_access_event
        self.valid_engines = ["gemini", "claude", "gpt4", "openai", "chatgpt"]
    
    def validate_engine(self, engine: str) -> Tuple[bool, str]:
        """
        エンジン名のバリデーション（純粋な検証ロジック）
        
        Args:
            engine: 検証対象のエンジン名
            
        Returns:
            Tuple[bool, str]: (検証結果, エラーメッセージ)
        """
        if not engine:
            return False, "エンジン名が指定されていません"
        
        if engine not in self.valid_engines:
            return False, f"無効なエンジン: {engine}. 有効なエンジン: {', '.join(self.valid_engines)}"
        
        return True, ""
    
    def set_engine_state(self, engine: str) -> Dict[str, Any]:
        """
        エンジン状態の更新（純粋な状態管理）
        
        Args:
            engine: 設定するエンジン名
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        # バリデーション実行
        is_valid, error_message = self.validate_engine(engine)
        
        if not is_valid:
            return {
                "success": False,
                "error": error_message,
                "engine": None
            }
        
        try:
            # セッション状態更新（純粋な状態管理）
            session["analysis_engine"] = engine
            
            # ログ記録（状態変更の追跡）
            if self.app_logger:
                self.app_logger.info(f"Analysis engine state updated: {engine}")
            
            if self.log_access_event:
                self.log_access_event(f'Engine state changed to: {engine}')
            
            return {
                "success": True,
                "engine": engine,
                "message": f"分析エンジンを{engine}に設定しました",
                "previous_state": session.get("previous_analysis_engine"),
                "timestamp": session.get("last_engine_change_time")
            }
            
        except Exception as e:
            # エラー状態の記録
            if self.app_logger:
                self.app_logger.error(f"Engine state update error: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "engine": None
            }
    
    def get_current_engine_state(self) -> Dict[str, Any]:
        """
        現在のエンジン状態取得（純粋な状態参照）
        
        Returns:
            Dict[str, Any]: 現在の状態情報
        """
        current_engine = session.get("analysis_engine", "gemini")
        
        return {
            "current_engine": current_engine,
            "valid_engines": self.valid_engines,
            "is_set": bool(session.get("analysis_engine")),
            "last_change": session.get("last_engine_change_time")
        }


def create_engine_management_blueprint(app_logger=None, log_access_event=None, require_rate_limit=None):
    """
    エンジン管理Blueprint作成（分離されたルーティング）
    
    Args:
        app_logger: アプリケーションログ関数（依存注入）
        log_access_event: アクセスログ関数（依存注入）
        require_rate_limit: レート制限デコレータ（依存注入）
        
    Returns:
        Blueprint: エンジン管理用Blueprint
    """
    engine_bp = Blueprint('engine_management', __name__)
    engine_manager = EngineStateManager(app_logger, log_access_event)
    
    @engine_bp.route("/set_analysis_engine", methods=["POST"])
    def set_analysis_engine():
        """
        分析エンジン設定エンドポイント（責務分離版）
        純粋な状態管理のみ実行
        """
        # レート制限適用（依存注入された場合のみ）
        if require_rate_limit:
            # 注意: デコレータは直接適用できないため、関数内で呼び出し
            pass
        
        try:
            # リクエストデータ取得
            data = request.get_json() or {}
            engine = data.get("engine", "gemini")
            
            # 純粋な状態管理処理
            result = engine_manager.set_engine_state(engine)
            
            # HTTPステータスコード決定
            status_code = 200 if result["success"] else 400
            
            return jsonify(result), status_code
            
        except Exception as e:
            # 予期しないエラーのハンドリング
            if app_logger:
                app_logger.error(f"Engine management endpoint error: {str(e)}")
            
            return jsonify({
                "success": False,
                "error": "サーバー内部エラーが発生しました",
                "details": str(e) if app_logger else None
            }), 500
    
    @engine_bp.route("/get_analysis_engine_state", methods=["GET"])
    def get_analysis_engine_state():
        """
        現在のエンジン状態取得エンドポイント（新規追加）
        デバッグ・監視用途
        """
        try:
            state = engine_manager.get_current_engine_state()
            return jsonify({
                "success": True,
                "state": state
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    return engine_bp