"""
翻訳APIルーティングモジュール
Task #9 AP-1 Phase 1: ChatGPT翻訳エンドポイントの分離

このモジュールは以下の機能を提供します：
- /translate_chatgpt エンドポイントの処理
- 翻訳サービスとの統合
- 依存注入による疎結合設計
"""

import time
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


def get_client_id():
    """クライアントID取得（認証状態に応じて）"""
    from user_auth import get_user_id, AUTH_SYSTEM_AVAILABLE
    
    if AUTH_SYSTEM_AVAILABLE and session.get("authenticated"):
        return session.get("user_id")
    elif session.get("logged_in"):
        from user_auth import get_user_id_by_username
        username = session.get("username")
        return get_user_id_by_username(username) if username else get_client_ip_safe()
    else:
        return get_client_ip_safe()


@translation_bp.route('/translate_chatgpt', methods=['POST'])
@csrf_protect
@require_rate_limit
def translate_chatgpt():
    """ChatGPT翻訳エンドポイント"""
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

        source_lang, target_lang = language_pair.split("-")

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

        # Gemini翻訳（簡略化版 - Phase 1では基本機能のみ）
        gemini_translation = f"Gemini翻訳機能は次のPhaseで実装予定"
        gemini_reverse_translation = ""
        
        # 改善翻訳（簡略化版 - Phase 1では基本機能のみ）
        better_translation = f"改善翻訳機能は次のPhaseで実装予定"
        reverse_better = ""

        # セッションに翻訳結果を保存
        session["translated_text"] = translated
        session["reverse_translated_text"] = reverse
        session["gemini_translation"] = gemini_translation
        session["gemini_reverse_translation"] = gemini_reverse_translation
        session["better_translation"] = better_translation
        session["reverse_better_translation"] = reverse_better

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
        logger.error(f"Translation error: {str(e)}")
        log_security_event('TRANSLATION_ERROR', f'Error: {str(e)}', 'ERROR')
        return jsonify({
            "success": False,
            "error": "翻訳処理中にエラーが発生しました"
        }), 500