"""
分析APIルーティングモジュール
Task #9-3 AP-1 Phase 3: 分析機能のBlueprint分離

このモジュールは以下の機能を提供します：
- /get_nuance エンドポイントの処理
- /interactive_question エンドポイントの処理  
- 分析サービスとの統合
- 依存注入による疎結合設計
"""

import time
import os
from datetime import datetime
from typing import Optional
from flask import Blueprint, request, jsonify, session
from security.decorators import csrf_protect, require_rate_limit
from security.security_logger import log_security_event, log_access_event
from security.input_validation import EnhancedInputValidator
from security.request_helpers import get_client_ip_safe

# Blueprint 定義
analysis_bp = Blueprint('analysis', __name__, url_prefix='')

# 依存注入用の変数（app.pyから設定される）
analysis_service = None
interactive_service = None
logger = None
labels = None

def init_analysis_routes(analysis_svc, interactive_svc, app_logger, app_labels):
    """
    分析ルートの初期化（依存注入）
    
    Args:
        analysis_svc: AnalysisService instance
        interactive_svc: InteractiveService instance
        app_logger: Application logger
        app_labels: Multilingual labels
        
    Returns:
        Blueprint: Initialized analysis blueprint
    """
    global analysis_service, interactive_service, logger, labels
    analysis_service = analysis_svc
    interactive_service = interactive_svc
    logger = app_logger
    labels = app_labels
    return analysis_bp


@analysis_bp.route('/get_nuance', methods=['POST'])
@csrf_protect
@require_rate_limit
def get_nuance():
    """ニュアンス分析エンドポイント（app.pyから移動）"""
    global analysis_service
    
    if analysis_service is None:
        logger.error("AnalysisService not initialized")
        return jsonify({
            "success": False,
            "error": "Analysis service not available"
        }), 500
        
    try:
        # 言語設定取得
        current_lang = session.get('lang', 'jp')
        
        # リクエストデータ取得
        data = request.get_json() or {}
        selected_engine = data.get("engine", data.get("analysis_engine", "gemini"))
        # 🔧 Phase 3c-4 FIX: language_pairパラメータを抽出
        language_pair = data.get("language_pair", session.get("language_pair", "ja-en"))
        
        # デバッグログ（本番環境では削除可能）
        if logger and hasattr(logger, 'debug'):
            logger.debug(f"Analysis request - Engine: {selected_engine}, Language pair: {language_pair}")
        
        # セッションIDを優先、フォールバックでCSRFトークンまたは生成
        session_id = (getattr(session, 'session_id', None) or 
                     session.get("session_id") or 
                     session.get("csrf_token", "")[:16] or 
                     f"analysis_{int(time.time())}")
        
        log_access_event(f'Nuance analysis started: engine={selected_engine}, session={session_id[:16]}...')
        
        # エンジン選択の検証
        valid_engines = ['gemini', 'chatgpt', 'claude']
        if selected_engine not in valid_engines:
            log_security_event('INVALID_ANALYSIS_ENGINE', f'Engine: {selected_engine}', 'WARNING')
            return jsonify({
                "success": False,
                "error": f"無効な分析エンジンです: {selected_engine}"
            })
        
        # 分析実行
        analysis_result = analysis_service.perform_nuance_analysis(
            session_id=session_id,
            selected_engine=selected_engine,
            language_pair=language_pair
        )
        
        # エラーハンドリング
        if "error" in analysis_result:
            log_security_event('ANALYSIS_DATA_ERROR', analysis_result["error"], 'WARNING')
            return jsonify({
                "success": False,
                "error": analysis_result["error"]
            })
        
        # 分析結果をRedisに保存
        analysis_saved = analysis_service.save_analysis_results(session_id, analysis_result)
        
        if not analysis_saved:
            logger.warning("Failed to save analysis to Redis - using session fallback")
            # セッションフォールバック
            session["gemini_3way_analysis"] = analysis_result.get("analysis_text", "")
        
        log_access_event(f'Nuance analysis completed successfully: engine={selected_engine}')
        
        return jsonify({
            "success": True,
            "analysis_text": analysis_result.get("analysis_text", ""),
            "engine_used": analysis_result.get("engine", selected_engine),
            "prompt_used": analysis_result.get("prompt_used", ""),
            "cached": analysis_saved,
            "session_id": session_id[:16] + "..." if len(session_id) > 16 else session_id
        })
        
    except ValueError as ve:
        logger.error(f"Analysis validation error: {str(ve)}")
        return jsonify({
            "success": False,
            "error": str(ve)
        }), 400
        
    except Exception as e:
        import traceback
        logger.error(f"Analysis error: {str(e)}")
        logger.error(traceback.format_exc())
        log_security_event('ANALYSIS_ERROR', f'Error: {str(e)}', 'ERROR')
        
        if os.getenv('ENVIRONMENT', 'development') == 'development':
            return jsonify({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }), 500
        else:
            return jsonify({
                "success": False,
                "error": "分析処理中にエラーが発生しました"
            }), 500


@analysis_bp.route('/interactive_question', methods=['POST'])
@csrf_protect
@require_rate_limit
def interactive_question():
    """インタラクティブ質問エンドポイント（app.pyから移動）"""
    global interactive_service
    
    if interactive_service is None:
        logger.error("InteractiveService not initialized")
        return jsonify({
            "success": False,
            "error": "Interactive service not available"
        }), 500
        
    try:
        # リクエストデータ取得
        data = request.get_json() or {}
        question = data.get("question", "").strip()
        
        # セッションから表示言語を取得
        display_lang = session.get("lang", "jp")
        
        # セッションIDを優先、フォールバックでCSRFトークンまたは生成
        session_id = (getattr(session, 'session_id', None) or 
                     session.get("session_id") or 
                     session.get("csrf_token", "")[:16] or 
                     f"interactive_{int(time.time())}")
        
        log_access_event(f'Interactive question started: session={session_id[:16]}...')
        
        # インタラクティブ質問処理実行
        result = interactive_service.process_interactive_question(
            session_id=session_id,
            question=question,
            display_lang=display_lang
        )
        
        # エラーレスポンスの場合
        if not result.get("success", False):
            return jsonify(result)
        
        # 成功レスポンス
        return jsonify({
            "success": True,
            "result": result["result"],
            "current_chat": result["current_chat"]
        })
        
    except ValueError as ve:
        logger.error(f"Interactive question validation error: {str(ve)}")
        return jsonify({
            "success": False,
            "error": str(ve)
        }), 400
        
    except Exception as e:
        import traceback
        logger.error(f"Interactive question error: {str(e)}")
        logger.error(traceback.format_exc())
        log_security_event('INTERACTIVE_QUESTION_ERROR', f'Error: {str(e)}', 'ERROR')
        
        if os.getenv('ENVIRONMENT', 'development') == 'development':
            return jsonify({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }), 500
        else:
            return jsonify({
                "success": False,
                "error": "質問処理中にエラーが発生しました"
            }), 500


@analysis_bp.route('/clear_chat_history', methods=['POST'])
@require_rate_limit
def clear_chat_history():
    """チャット履歴をクリアするエンドポイント（app.pyから移動）"""
    global interactive_service
    
    if interactive_service is None:
        logger.error("InteractiveService not initialized")
        return jsonify({
            "success": False,
            "error": "Interactive service not available"
        }), 500
        
    try:
        # セッションID取得
        session_id = (getattr(session, 'session_id', None) or 
                     session.get("session_id") or 
                     session.get("csrf_token", "")[:16])
        
        # チャット履歴クリア実行
        result = interactive_service.clear_chat_history(session_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Chat history clear error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500