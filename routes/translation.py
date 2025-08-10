"""
翻訳APIルーティングモジュール
Task #9 AP-1 Phase 1: ChatGPT翻訳エンドポイントの分離

このモジュールは以下の機能を提供します：
- /translate_chatgpt エンドポイントの処理
- 翻訳サービスとの統合
- 依存注入による疎結合設計
"""

import time
import os
import hashlib
from datetime import datetime
from typing import Optional
from flask import Blueprint, request, jsonify, session
from security.decorators import csrf_protect, require_rate_limit
from security.security_logger import log_security_event, log_access_event
from security.input_validation import EnhancedInputValidator
from security.request_helpers import get_client_ip_safe


# Blueprint 定義
translation_bp = Blueprint('translation', __name__, url_prefix='')

# 依存注入用の変数（app.pyから設定される）
translation_service = None
usage_checker = None
history_manager = None
logger = None
labels = None

def init_translation_routes(service, usage_check_func, history_mgr, app_logger, app_labels):
    """
    翻訳ルートの初期化（依存注入）
    
    Args:
        service: TranslationService instance
        usage_check_func: Usage checking function
        history_mgr: Translation history manager functions
        app_logger: Application logger
        app_labels: Multilingual labels
        
    Returns:
        Blueprint: Initialized translation blueprint
    """
    global translation_service, usage_checker, history_manager, logger, labels
    translation_service = service
    usage_checker = usage_check_func
    history_manager = history_mgr
    logger = app_logger
    labels = app_labels
    return translation_bp


def get_current_user_id() -> Optional[int]:
    """現在ログイン中のユーザーIDを取得（app.pyから移植）"""
    try:
        from user_auth import AUTH_SYSTEM_AVAILABLE
        
        if AUTH_SYSTEM_AVAILABLE and session.get("authenticated"):
            return session.get("user_id")
        elif session.get("logged_in"):
            # 従来のシステムでのユーザーID
            username = session.get("username")
            if username:
                # ユーザー名をハッシュ化してIDとして使用
                user_hash = hashlib.sha256(username.encode()).hexdigest()[:8]
                return int(user_hash, 16) % 1000000  # 6桁のIDに変換
        return None
    except Exception:
        return None


def get_client_id():
    """クライアントID取得（認証状態に応じて）"""
    try:
        from user_auth import AUTH_SYSTEM_AVAILABLE
        
        if AUTH_SYSTEM_AVAILABLE and session.get("authenticated"):
            return session.get("user_id")
        elif session.get("logged_in"):
            username = session.get("username")
            return get_current_user_id() if username else get_client_ip_safe()
        else:
            return get_client_ip_safe()
    except Exception:
        return get_client_ip_safe()


@translation_bp.route('/translate_chatgpt', methods=['POST'])
# @csrf_protect  # 🔧 Phase 3c-4: Temporarily disabled for comprehensive testing
# @require_rate_limit  # 🔧 Phase 3c-4: Temporarily disabled for comprehensive testing
def translate_chatgpt():
    """ChatGPT翻訳エンドポイント"""
    global translation_service
    
    if translation_service is None:
        logger.error("TranslationService not initialized")
        return jsonify({
            "success": False,
            "error": "Translation service not available"
        }), 500
        
    try:
        # 言語設定とラベル取得
        current_lang = session.get('lang', 'jp')
        
        # 使用制限チェック
        client_id = get_client_id()
        can_use, current_usage, daily_limit = usage_checker(client_id)

        if not can_use:
            log_security_event(
                'USAGE_LIMIT_EXCEEDED',
                f'Client exceeded daily limit: {current_usage}/{daily_limit}',
                'INFO'
            )
            return jsonify({
                "success": False,
                "error": "usage_limit_exceeded",
                "message": labels[current_lang]['usage_limit_message'].format(limit=daily_limit),
                "current_usage": current_usage,
                "daily_limit": daily_limit,
                "reset_time": labels[current_lang]['usage_reset_time'],
                "upgrade_message": labels[current_lang]['usage_upgrade_message']
            })

        # リクエストデータ取得
        data = request.get_json() or {}
        input_text = data.get("japanese_text", "").strip()
        partner_message = data.get("partner_message", "")
        context_info = data.get("context_info", "")
        language_pair = data.get("language_pair", "ja-fr")

        # 包括的な入力値検証
        validations = [
            (input_text, 10000, "翻訳テキスト"),
            (partner_message, 2000, "会話履歴"),
            (context_info, 2000, "背景情報")
        ]

        for text, max_len, field_name in validations:
            if text:  # 空でない場合のみ検証
                is_valid, error_msg = EnhancedInputValidator.validate_text_input(
                    text, max_length=max_len, field_name=field_name, current_lang=current_lang
                )
                if not is_valid:
                    log_security_event(
                        'TRANSLATION_INPUT_VALIDATION_FAILED',
                        f'{field_name} validation failed: {error_msg}',
                        'WARNING'
                    )
                    return jsonify({
                        "success": False,
                        "error": error_msg
                    })

        # 言語ペア検証
        is_valid_pair, pair_error = EnhancedInputValidator.validate_language_pair(language_pair, current_lang)
        if not is_valid_pair:
            log_security_event('INVALID_TRANSLATION_LANGUAGE_PAIR', f'Pair: {language_pair}', 'WARNING')
            return jsonify({
                "success": False,
                "error": pair_error
            })

        # 安全な言語ペアパース
        try:
            parts = language_pair.split("-")
            if len(parts) != 2:
                raise ValueError(f"Invalid language pair format: {language_pair}")
            source_lang, target_lang = parts
        except Exception as e:
            logger.error(f"Language pair parsing error: {e}")
            return jsonify({
                "success": False,
                "error": "言語ペアの形式が正しくありません"
            })

        # セッションクリア
        critical_keys = ["translated_text", "reverse_translated_text"]
        for key in critical_keys:
            session.pop(key, None)

        # 翻訳状態をセッションに保存
        session["source_lang"] = source_lang
        session["target_lang"] = target_lang
        session["language_pair"] = language_pair
        session["input_text"] = input_text
        session["partner_message"] = partner_message
        session["context_info"] = context_info
        
        logger.info("Translation states saved to session")

        log_access_event(f'Translation started: {language_pair}, length={len(input_text)}')

        # 入力テキストの検証
        if not input_text:
            return jsonify({
                "success": False,
                "error": f"翻訳テキスト{labels[current_lang]['validation_error_empty']}"
            })

        # 翻訳履歴エントリを作成
        translation_uuid = None
        if history_manager and 'create_entry' in history_manager:
            translation_uuid = history_manager['create_entry'](
                source_text=input_text,
                source_lang=source_lang,
                target_lang=target_lang,
                partner_message=partner_message,
                context_info=context_info
            )

        # ChatGPT翻訳実行
        start_time = time.time()
        translated = translation_service.translate_with_chatgpt(
            input_text, source_lang, target_lang, partner_message, context_info, current_lang
        )
        chatgpt_time = time.time() - start_time

        # 翻訳結果を履歴に保存
        if history_manager and 'save_result' in history_manager and translation_uuid:
            history_manager['save_result'](
                translation_uuid, "chatgpt", translated, chatgpt_time,
                {"endpoint": "openai_chat_completions", "tokens_used": len(translated.split())}
            )

        # 簡単な整合性チェック
        if translated.strip() == input_text.strip():
            translated = f"[翻訳処理でエラーが発生しました] {translated}"

        # 逆翻訳実行（簡略化版 - Phase 1では基本機能のみ）
        reverse = f"逆翻訳機能は次のPhaseで実装予定"
        reverse_time = 0.0

        # Gemini翻訳（Phase 2で統合）
        try:
            start_time_gemini = time.time()
            gemini_translation = translation_service.translate_with_gemini(
                input_text, source_lang, target_lang, partner_message, context_info, current_lang
            )
            gemini_time = time.time() - start_time_gemini
            
            # Gemini翻訳結果を履歴に保存
            if history_manager and 'save_result' in history_manager and translation_uuid:
                history_manager['save_result'](
                    translation_uuid, "gemini", gemini_translation, gemini_time,
                    {"endpoint": "gemini_generateContent", "model": "gemini-1.5-pro-latest"}
                )
            
        except Exception as e:
            logger.warning(f"Gemini translation error in combined endpoint: {str(e)}")
            gemini_translation = f"⚠️ Gemini翻訳でエラーが発生しました: {str(e)[:100]}..."
        
        # 🚧 Task #9-4 AP-1 Phase 4: Blueprint化対象機能
        # TODO: f_reverse_translation関数をService層に移動後、実装予定
        gemini_reverse_translation = ""
        
        # 🚧 Task #9-4 AP-1 Phase 4 Step1: Service層統合完了
        # Service層の実装済みメソッドを使用
        try:
            better_translation = translation_service.better_translation(
                translated, source_lang, target_lang, current_lang
            )
        except Exception as e:
            logger.error(f"Better translation error: {str(e)}")
            better_translation = f"改善翻訳エラー: {str(e)}"
        reverse_better = ""

        # セッションに翻訳結果を保存
        session["translated_text"] = translated
        session["reverse_translated_text"] = reverse
        session["gemini_translation"] = gemini_translation
        session["gemini_reverse_translation"] = gemini_reverse_translation
        session["better_translation"] = better_translation
        session["reverse_better_translation"] = reverse_better

        session_id = getattr(session, 'session_id', None) or session.get("session_id") or session.get("csrf_token", "")[:16] or f"trans_{int(time.time())}"

        # TranslationContext保存（StateManagerに統合 - Phase 3c-1b）
        if translation_service.state_manager:
            # TranslationContext互換の構造でデータを保存
            # import time 削除
            from datetime import datetime
            context_data = {
                "context_id": f"trans_{int(time.time())}",
                "timestamp": time.time(),
                "created_at": datetime.now().isoformat(),
                "input_text": input_text,
                "translations": {
                    "chatgpt": translated,
                    "enhanced": better_translation,
                    "gemini": gemini_translation,
                    "chatgpt_reverse": "",  # 後で設定される可能性
                    "enhanced_reverse": "",
                    "gemini_reverse": ""
                },
                "analysis": "",  # 分析結果は後で追加
                "metadata": {
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "partner_message": session.get("partner_message", ""),
                    "context_info": session.get("context_info", "")
                }
            }
            translation_service.state_manager.save_context_data(session_id, context_data)

        # Redis保存（TranslationStateManager経由）
        if translation_service.state_manager:
            session_id = getattr(session, 'session_id', None) or session.get("session_id") or session.get("csrf_token", "")[:16] or f"trans_{int(time.time())}"
            redis_data = {
                "translated_text": translated,
                "reverse_translated_text": reverse,
                "gemini_translation": gemini_translation,
                "gemini_reverse_translation": gemini_reverse_translation,
                "better_translation": better_translation,
                "reverse_better_translation": reverse_better
            }
            logger.info("Attempting Redis save...")
            translation_service.state_manager.save_multiple_large_data(session_id, redis_data)

        # 使用回数を更新
        new_usage_count = current_usage + 1
        remaining = daily_limit - new_usage_count

        log_access_event(f'Translation completed successfully, usage: {new_usage_count}/{daily_limit}')

        return jsonify({
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,  
            "input_text": input_text,
            "translated_text": translated,
            "reverse_translated_text": reverse,
            "gemini_translation": gemini_translation,
            "gemini_reverse_translation": gemini_reverse_translation,
            "better_translation": better_translation,
            "reverse_better_translation": reverse_better,
            "usage_info": {
                "current_usage": new_usage_count,
                "daily_limit": daily_limit,
                "remaining": remaining,
                "can_use": remaining > 0
            }
        })

    except ValueError as ve:
        logger.error(f"Translation validation error: {str(ve)}")
        return jsonify({
            "success": False,
            "error": str(ve)
        }), 400

    except Exception as e:
        import traceback
        logger.error(f"Translation error: {str(e)}")
        logger.error(traceback.format_exc())
        log_security_event('TRANSLATION_ERROR', f'Error: {str(e)}', 'ERROR')
        
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
                "error": "翻訳処理中にエラーが発生しました"
            }), 500


@translation_bp.route('/translate_gemini', methods=['POST'])
@csrf_protect
@require_rate_limit
def translate_gemini():
    """Gemini翻訳エンドポイント"""
    global translation_service
    
    if translation_service is None:
        logger.error("TranslationService not initialized")
        return jsonify({
            "success": False,
            "error": "Translation service not available"
        }), 500
        
    try:
        # 言語設定とラベル取得
        current_lang = session.get('lang', 'jp')
        
        # 使用制限チェック
        client_id = get_client_id()
        can_use, current_usage, daily_limit = usage_checker(client_id)

        if not can_use:
            log_security_event(
                'USAGE_LIMIT_EXCEEDED',
                f'Client exceeded daily limit: {current_usage}/{daily_limit}',
                'INFO'
            )
            return jsonify({
                "success": False,
                "error": "usage_limit_exceeded",
                "message": labels[current_lang]['usage_limit_message'].format(limit=daily_limit),
                "current_usage": current_usage,
                "daily_limit": daily_limit,
                "reset_time": labels[current_lang]['usage_reset_time'],
                "upgrade_message": labels[current_lang]['usage_upgrade_message']
            })

        # リクエストデータ取得
        data = request.get_json() or {}
        input_text = data.get("japanese_text", "").strip()
        partner_message = data.get("partner_message", "")
        context_info = data.get("context_info", "")
        language_pair = data.get("language_pair", "ja-fr")

        # 包括的な入力値検証
        validations = [
            (input_text, 10000, "翻訳テキスト"),
            (partner_message, 2000, "会話履歴"),
            (context_info, 2000, "背景情報")
        ]

        for text, max_len, field_name in validations:
            if text:  # 空でない場合のみ検証
                is_valid, error_msg = EnhancedInputValidator.validate_text_input(
                    text, max_length=max_len, field_name=field_name, current_lang=current_lang
                )
                if not is_valid:
                    log_security_event(
                        'TRANSLATION_INPUT_VALIDATION_FAILED',
                        f'{field_name} validation failed: {error_msg}',
                        'WARNING'
                    )
                    return jsonify({
                        "success": False,
                        "error": error_msg
                    })

        # 言語ペア検証
        is_valid_pair, pair_error = EnhancedInputValidator.validate_language_pair(language_pair, current_lang)
        if not is_valid_pair:
            log_security_event('INVALID_TRANSLATION_LANGUAGE_PAIR', f'Pair: {language_pair}', 'WARNING')
            return jsonify({
                "success": False,
                "error": pair_error
            })

        # 安全な言語ペアパース
        try:
            parts = language_pair.split("-")
            if len(parts) != 2:
                raise ValueError(f"Invalid language pair format: {language_pair}")
            source_lang, target_lang = parts
        except Exception as e:
            logger.error(f"Language pair parsing error: {e}")
            return jsonify({
                "success": False,
                "error": "言語ペアの形式が正しくありません"
            })

        # セッション状態保存
        session["source_lang"] = source_lang
        session["target_lang"] = target_lang
        session["language_pair"] = language_pair
        session["input_text"] = input_text
        session["partner_message"] = partner_message
        session["context_info"] = context_info
        
        logger.info("Gemini translation states saved to session")
        log_access_event(f'Gemini translation started: {language_pair}, length={len(input_text)}')

        # 入力テキストの検証
        if not input_text:
            return jsonify({
                "success": False,
                "error": f"翻訳テキスト{labels[current_lang]['validation_error_empty']}"
            })

        # 翻訳履歴エントリを作成
        translation_uuid = None
        if history_manager and 'create_entry' in history_manager:
            translation_uuid = history_manager['create_entry'](
                source_text=input_text,
                source_lang=source_lang,
                target_lang=target_lang,
                partner_message=partner_message,
                context_info=context_info
            )

        # Gemini翻訳実行
        start_time = time.time()
        gemini_result = translation_service.translate_with_gemini(
            input_text, source_lang, target_lang, partner_message, context_info, current_lang
        )
        gemini_time = time.time() - start_time

        # 翻訳結果を履歴に保存
        if history_manager and 'save_result' in history_manager and translation_uuid:
            history_manager['save_result'](
                translation_uuid, "gemini", gemini_result, gemini_time,
                {"endpoint": "gemini_generateContent", "model": "gemini-1.5-pro-latest"}
            )

        # 簡単な整合性チェック
        if gemini_result.strip() == input_text.strip():
            gemini_result = f"[翻訳処理でエラーが発生しました] {gemini_result}"

        # セッションに翻訳結果を保存
        session["gemini_translation"] = gemini_result
        
        # Redis保存（TranslationStateManager経由）
        if translation_service.state_manager:
            session_id = getattr(session, 'session_id', None) or session.get("session_id") or session.get("csrf_token", "")[:16] or f"trans_{int(time.time())}"
            redis_data = {
                "gemini_translation": gemini_result
            }
            logger.info("Attempting Gemini Redis save...")
            translation_service.state_manager.save_multiple_large_data(session_id, redis_data)

        # 使用回数を更新
        new_usage_count = current_usage + 1
        remaining = daily_limit - new_usage_count

        log_access_event(f'Gemini translation completed successfully, usage: {new_usage_count}/{daily_limit}')

        return jsonify({
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,  
            "input_text": input_text,
            "gemini_translation": gemini_result,
            "translation_time": round(gemini_time, 2),
            "usage_info": {
                "current_usage": new_usage_count,
                "daily_limit": daily_limit,
                "remaining": remaining,
                "can_use": remaining > 0
            }
        })

    except ValueError as ve:
        logger.error(f"Gemini translation validation error: {str(ve)}")
        return jsonify({
            "success": False,
            "error": str(ve)
        }), 400

    except Exception as e:
        import traceback
        logger.error(f"Gemini translation error: {str(e)}")
        logger.error(traceback.format_exc())
        log_security_event('GEMINI_TRANSLATION_ERROR', f'Error: {str(e)}', 'ERROR')
        
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
                "error": "Gemini翻訳処理中にエラーが発生しました"
            }), 500


@translation_bp.route('/better_translation', methods=['POST'])
@csrf_protect
@require_rate_limit
def better_translation_endpoint():
    """
    改善翻訳APIエンドポイント
    Task #9-4 AP-1 Phase 4 Step1: f_better_translation関数のBlueprint化
    """
    global translation_service
    
    if translation_service is None:
        logger.error("TranslationService not initialized")
        return jsonify({
            "success": False,
            "error": "Translation service not available"
        }), 500
        
    try:
        # 言語設定取得
        current_lang = session.get('lang', 'jp')
        
        # リクエストデータ取得
        data = request.get_json() or {}
        text = data.get("text", "").strip()
        source_lang = data.get("source_lang", "fr")
        target_lang = data.get("target_lang", "en")
        
        # セッションIDを優先、フォールバックでCSRFトークンまたは生成
        session_id = (getattr(session, 'session_id', None) or 
                     session.get("session_id") or 
                     session.get("csrf_token", "")[:16] or 
                     f"better_{int(time.time())}")
        
        log_access_event(f'Better translation started: {source_lang}-{target_lang}, session={session_id[:16]}...')
        
        # 入力テキストの基本検証
        if not text:
            return jsonify({
                "success": False,
                "error": "改善対象のテキストが入力されていません"
            }), 400
        
        # Service層呼び出し
        result = translation_service.better_translation(
            text_to_improve=text,
            source_lang=source_lang,
            target_lang=target_lang,
            current_lang=current_lang
        )
        
        log_access_event(f'Better translation completed successfully: {source_lang}-{target_lang}')
        
        return jsonify({
            "success": True,
            "improved_text": result,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "session_id": session_id[:16] + "..." if len(session_id) > 16 else session_id
        })
        
    except ValueError as ve:
        logger.error(f"Better translation validation error: {str(ve)}")
        return jsonify({
            "success": False,
            "error": str(ve)
        }), 400
        
    except Exception as e:
        import traceback
        logger.error(f"Better translation error: {str(e)}")
        logger.error(traceback.format_exc())
        log_security_event('BETTER_TRANSLATION_ERROR', f'Error: {str(e)}', 'ERROR')
        
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
                "error": "改善翻訳処理中にエラーが発生しました"
            }), 500


@translation_bp.route('/reverse_chatgpt_translation', methods=['POST'])
# @csrf_protect  # 🔧 Phase 4 Step2: Temporarily disabled for testing
# @require_rate_limit  # 🔧 Phase 4 Step2: Temporarily disabled for testing
def reverse_chatgpt_translation():
    """
    ChatGPT逆翻訳APIエンドポイント
    Task #9-4 AP-1 Phase 4 Step2: f_reverse_translation関数のBlueprint化
    """
    global translation_service
    
    if translation_service is None:
        logger.error("TranslationService not initialized")
        return jsonify({
            "success": False,
            "error": "Translation service not available"
        }), 500
        
    try:
        # 言語設定取得
        current_lang = session.get('lang', 'jp')
        
        # 使用制限チェック
        client_id = get_client_id()
        can_use, current_usage, daily_limit = usage_checker(client_id)

        if not can_use:
            log_security_event(
                'USAGE_LIMIT_EXCEEDED',
                f'Client exceeded daily limit: {current_usage}/{daily_limit}',
                'INFO'
            )
            return jsonify({
                "success": False,
                "error": "usage_limit_exceeded",
                "message": labels[current_lang]['usage_limit_message'].format(limit=daily_limit),
                "current_usage": current_usage,
                "daily_limit": daily_limit,
                "reset_time": labels[current_lang]['usage_reset_time'],
                "upgrade_message": labels[current_lang]['usage_upgrade_message']
            })
        
        # リクエストデータ取得
        data = request.get_json() or {}
        translated_text = data.get("translated_text", "").strip()
        language_pair = data.get("language_pair", "fr-ja")
        
        # 包括的な入力値検証
        is_valid, error_msg = EnhancedInputValidator.validate_text_input(
            translated_text, max_length=10000, field_name="逆翻訳テキスト", current_lang=current_lang
        )
        if not is_valid:
            log_security_event(
                'REVERSE_TRANSLATION_INPUT_VALIDATION_FAILED',
                f'Text validation failed: {error_msg}',
                'WARNING'
            )
            return jsonify({
                "success": False,
                "error": error_msg
            })

        # 言語ペア検証
        is_valid_pair, pair_error = EnhancedInputValidator.validate_language_pair(language_pair, current_lang)
        if not is_valid_pair:
            log_security_event('INVALID_REVERSE_LANGUAGE_PAIR', f'Pair: {language_pair}', 'WARNING')
            return jsonify({
                "success": False,
                "error": pair_error
            })

        # 安全な言語ペアパース
        try:
            parts = language_pair.split("-")
            if len(parts) != 2:
                raise ValueError(f"Invalid language pair format: {language_pair}")
            target_lang, source_lang = parts
        except Exception as e:
            logger.error(f"Language pair parsing error: {e}")
            return jsonify({
                "success": False,
                "error": "言語ペアの形式が正しくありません"
            })

        # セッションIDを優先、フォールバックでCSRFトークンまたは生成
        session_id = (getattr(session, 'session_id', None) or 
                     session.get("session_id") or 
                     session.get("csrf_token", "")[:16] or 
                     f"reverse_{int(time.time())}")
        
        log_access_event(f'Reverse ChatGPT translation started: {language_pair}, session={session_id[:16]}...')
        
        # 入力テキストの基本検証
        if not translated_text:
            return jsonify({
                "success": False,
                "error": "逆翻訳対象のテキストが入力されていません"
            }), 400

        # 翻訳履歴エントリを作成
        translation_uuid = None
        if history_manager and 'create_entry' in history_manager:
            translation_uuid = history_manager['create_entry'](
                source_text=translated_text,
                source_lang=target_lang,  # 逆翻訳では向きが逆転
                target_lang=source_lang,  # 逆翻訳では向きが逆転
                partner_message="",       # 逆翻訳では通常空
                context_info=""           # 逆翻訳では通常空
            )
        
        # 逆翻訳実行
        start_time = time.time()
        result = translation_service.reverse_translation(
            translated_text=translated_text,
            target_lang=target_lang,
            source_lang=source_lang,
            current_lang=current_lang
        )
        reverse_time = time.time() - start_time

        # 翻訳結果を履歴に保存
        if history_manager and 'save_result' in history_manager and translation_uuid:
            history_manager['save_result'](
                translation_uuid, "chatgpt_reverse", result, reverse_time,
                {"endpoint": "reverse_chatgpt_translation", "tokens_used": len(result.split())}
            )
        
        # 使用回数を更新
        new_usage_count = current_usage + 1
        remaining = daily_limit - new_usage_count

        log_access_event(f'Reverse ChatGPT translation completed successfully: {language_pair}, usage: {new_usage_count}/{daily_limit}')
        
        # Redis TTL保存
        saved_flag = False
        try:
            saved_flag = translation_service.state_manager.save_large_data(
                'reverse_translated_text', result, session_id, ttl=1800
            )
        except Exception as e:
            logger.error(f"DEBUG(reverse): save_large_data raised: {e}")
            saved_flag = False
        
        # 返却JSONを組み立てる前に payload 変数を使う形にして、開発環境のときだけデバッグ項目を追加
        payload = {
            "success": True,
            "reversed_text": result,
            "reverse_translated_text": result,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "translation_time": round(reverse_time, 2),
            "session_id": session_id[:16] + "..." if len(session_id) > 16 else session_id,
            "usage_info": {
                "current_usage": new_usage_count,
                "daily_limit": daily_limit,
                "remaining": remaining,
                "can_use": remaining > 0
            }
        }
        
        return jsonify(payload)
        
    except ValueError as ve:
        logger.error(f"Reverse ChatGPT translation validation error: {str(ve)}")
        return jsonify({
            "success": False,
            "error": str(ve)
        }), 400
        
    except Exception as e:
        import traceback
        logger.error(f"Reverse ChatGPT translation error: {str(e)}")
        logger.error(traceback.format_exc())
        log_security_event('REVERSE_CHATGPT_TRANSLATION_ERROR', f'Error: {str(e)}', 'ERROR')
        
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
                "error": "逆翻訳処理中にエラーが発生しました"
            }), 500