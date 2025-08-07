"""
翻訳サービスモジュール
Task #9 AP-1 Phase 1: ChatGPT翻訳機能の分離

このモジュールは以下の機能を提供します：
- ChatGPT翻訳の実行
- OpenAI APIの安全なリクエスト処理
- 統一されたエラーハンドリング
- 依存注入による疎結合設計
"""

import time
import os
import requests
from typing import Optional, Callable, Dict, Any
from security.input_validation import EnhancedInputValidator
from security.security_logger import log_security_event, log_access_event


class TranslationService:
    """翻訳サービスの統合クラス"""
    
    def __init__(self, openai_client, logger, labels, 
                 usage_checker: Callable, translation_state_manager):
        """
        依存注入によるコンストラクタ
        
        Args:
            openai_client: OpenAI client instance
            logger: Application logger
            labels: Multilingual labels
            usage_checker: Usage checking function
            translation_state_manager: State manager for Redis
        """
        self.client = openai_client
        self.logger = logger
        self.labels = labels
        self.usage_checker = usage_checker
        self.state_manager = translation_state_manager
    
    def translate_with_chatgpt(self, text: str, source_lang: str, target_lang: str, 
                              partner_message: str = "", context_info: str = "", 
                              current_lang: str = "jp") -> str:
        """
        ChatGPT翻訳の実行
        
        Args:
            text: 翻訳対象テキスト
            source_lang: ソース言語
            target_lang: ターゲット言語
            partner_message: 会話履歴
            context_info: 背景情報
            current_lang: UI言語
            
        Returns:
            str: 翻訳結果
            
        Raises:
            ValueError: 入力検証エラー
        """
        # 包括的な入力値検証（10000文字まで許可）
        validations = [
            (text, 10000, "翻訳テキスト"),
            (partner_message, 2000, "会話履歴"),
            (context_info, 2000, "背景情報")
        ]

        for input_text, max_len, field_name in validations:
            if input_text:  # 空でない場合のみ検証
                is_valid, error_msg = EnhancedInputValidator.validate_text_input(
                    input_text, max_length=max_len, field_name=field_name, current_lang=current_lang
                )
                if not is_valid:
                    self.logger.error(f"Translation validation error: {error_msg}")
                    raise ValueError(error_msg)

        # 言語ペア検証（多言語対応）
        is_valid_pair, pair_error = EnhancedInputValidator.validate_language_pair(
            f"{source_lang}-{target_lang}", current_lang
        )
        if not is_valid_pair:
            self.logger.error(f"Language pair validation error: {pair_error}")
            raise ValueError(pair_error)

        lang_map = {
            "ja": "Japanese", "fr": "French", "en": "English", 
            "es": "Spanish", "de": "German", "it": "Italian"
        }
        target_label = lang_map.get(target_lang, target_lang.capitalize())

        if partner_message.strip() or context_info.strip():
            context_sections = []

            if partner_message.strip():
                context_sections.append(f"PREVIOUS CONVERSATION:\n{partner_message.strip()}")

            if context_info.strip():
                context_sections.append(f"BACKGROUND & RELATIONSHIP:\n{context_info.strip()}")

            context_text = "\n\n".join(context_sections)

            prompt = f"""You are a professional translator specializing in culturally appropriate {target_label} translation.

IMPORTANT CONTEXT TO CONSIDER:
{context_text}

TRANSLATION INSTRUCTIONS:
- Consider the relationship and background information carefully
- Use appropriate formality level based on the context
- Ensure cultural sensitivity and business appropriateness
- Translate naturally while respecting the contextual nuances

TRANSLATE TO {target_label.upper()}:
{text}

Remember: The context above is crucial for determining the appropriate tone, formality, and cultural considerations."""

        else:
            prompt = f"Professional, culturally appropriate translation to {target_label}:\n\n{text}"

        return self.safe_openai_request(prompt, current_lang=current_lang)
    
    def safe_openai_request(self, prompt: str, max_tokens: int = 400, 
                           temperature: float = 0.1, current_lang: str = "jp") -> str:
        """
        OpenAI APIの安全なリクエスト実行（翻訳用に最適化・多言語対応）
        
        Args:
            prompt: API送信プロンプト
            max_tokens: 最大トークン数
            temperature: 温度パラメータ
            current_lang: UI言語
            
        Returns:
            str: API応答結果
            
        Raises:
            ValueError: API エラーまたは検証エラー
        """
        try:
            # プロンプト長の計算
            prompt_length = len(prompt)

            # 動的タイムアウト設定（文章長に応じて60-120秒）
            if prompt_length >= 3000:
                timeout = 120
            elif prompt_length >= 1500:
                timeout = 90
            else:
                timeout = 60

            # より適切なmax_tokens設定
            if prompt_length > 4000:
                max_tokens = 1500  # 大幅増加
                timeout = 180  # 3分に延長
            elif prompt_length > 2000:
                max_tokens = 1000
                timeout = 120
            elif prompt_length > 1000:
                max_tokens = 600
            else:
                max_tokens = 400

            # 8000文字を超える場合の自動プロンプト短縮
            if prompt_length > 8000:
                # 前4000文字 + "...[省略]..." + 後4000文字
                shortened_prompt = prompt[:4000] + "\n\n...[Content shortened for processing]...\n\n" + prompt[-4000:]
                prompt = shortened_prompt
                log_security_event('PROMPT_SHORTENED', 
                                 f'Prompt shortened from {prompt_length} to {len(prompt)} chars', 'INFO')

            if not prompt or len(prompt.strip()) < 5:
                raise ValueError(self.labels[current_lang]['validation_error_short'])

            # API呼び出し開始
            api_start_time = time.time()
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
            api_duration = int((time.time() - api_start_time) * 1000)

            # API呼び出しログ記録
            try:
                from admin_logger import log_api_call
                log_api_call("openai", True, api_duration, "gpt-3.5-turbo translation")
            except ImportError:
                # フォールバック: 基本ログ出力
                self.logger.info(f"OpenAI API call completed: {api_duration}ms")

            result = response.choices[0].message.content.strip()

            # 適切な短い翻訳警告ロジック（翻訳専用）
            # プロンプトから実際の翻訳対象テキストを推定
            lines = prompt.split('\n')
            actual_text = ""
            for line in lines:
                # 「翻訳対象」「TRANSLATE」「翻訳してください」などの後の行を翻訳対象と判定
                if any(keyword in line for keyword in ['翻訳対象', 'TRANSLATE', '翻訳してください', 'translation to', 'Translate to']):
                    # この行以降を翻訳対象テキストとして抽出
                    remaining_lines = lines[lines.index(line)+1:]
                    actual_text = '\n'.join(remaining_lines).strip()
                    break

            # 翻訳対象テキストが見つからない場合は、最後の長い行を翻訳対象と推定
            if not actual_text:
                for line in reversed(lines):
                    if len(line.strip()) > 10:  # 10文字以上の行
                        actual_text = line.strip()
                        break

            # 改善された警告条件
            if actual_text and len(actual_text) >= 100 and len(result) < 10:
                log_security_event(
                    'SHORT_TRANSLATION_WARNING',
                    f'Translation may be incomplete: source={len(actual_text)} chars, result={len(result)} chars',
                    'WARNING'
                )
                # 短い翻訳の場合は適切な警告メッセージ（多言語対応）
                warning_messages = {
                    "jp": "\n\n⚠️ 翻訳が不完全な可能性があります。",
                    "en": "\n\n⚠️ Translation may be incomplete.",
                    "fr": "\n\n⚠️ La traduction peut être incomplète.",
                    "es": "\n\n⚠️ La traducción puede estar incompleta."
                }
                result += warning_messages.get(current_lang, warning_messages["jp"])
            # 30文字未満の短い文は警告スキップ
            elif actual_text and len(actual_text) < 30:
                log_access_event(f'Short text translation completed: source={len(actual_text)}, result={len(result)}')

            if not result or len(result.strip()) < 2:
                raise ValueError(self.labels[current_lang]['validation_error_short'])

            return result

        except requests.exceptions.Timeout:
            log_security_event('OPENAI_TIMEOUT', 
                             f'OpenAI API timeout after {timeout}s for prompt length {prompt_length}', 'WARNING')
            self.logger.error(f"OpenAI API timeout: {timeout}s")
            raise ValueError(f"{self.labels[current_lang]['api_error_timeout']}（{timeout}秒）")
        except Exception as e:
            log_security_event('OPENAI_ERROR', f'OpenAI API error: {str(e)}', 'ERROR')
            self.logger.error(f"OpenAI API error: {str(e)}")
            raise ValueError(self.labels[current_lang]['api_error_general'])
    
    def translate_with_gemini(self, text: str, source_lang: str, target_lang: str, 
                             partner_message: str = "", context_info: str = "", 
                             current_lang: str = "jp") -> str:
        """
        Gemini翻訳の実行
        
        Args:
            text: 翻訳対象テキスト
            source_lang: ソース言語
            target_lang: ターゲット言語
            partner_message: 会話履歴
            context_info: 背景情報
            current_lang: UI言語
            
        Returns:
            str: 翻訳結果
            
        Raises:
            ValueError: 入力検証エラーまたはAPI エラー
        """
        # Gemini APIキー確認
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            error_messages = {
                "jp": "⚠️ Gemini APIキーがありません",
                "en": "⚠️ Gemini API key not found",
                "fr": "⚠️ Clé API Gemini introuvable",
                "es": "⚠️ Clave API de Gemini no encontrada"
            }
            raise ValueError(error_messages.get(current_lang, error_messages["jp"]))

        # 包括的な入力値検証（10000文字まで許可）
        validations = [
            (text, 10000, "翻訳テキスト"),
            (partner_message, 2000, "会話履歴"),
            (context_info, 2000, "背景情報")
        ]

        for input_text, max_len, field_name in validations:
            if input_text:  # 空でない場合のみ検証
                is_valid, error_msg = EnhancedInputValidator.validate_text_input(
                    input_text, max_length=max_len, field_name=field_name, current_lang=current_lang
                )
                if not is_valid:
                    self.logger.error(f"Gemini validation error: {error_msg}")
                    raise ValueError(error_msg)

        # 言語ペア検証
        is_valid_pair, pair_error = EnhancedInputValidator.validate_language_pair(
            f"{source_lang}-{target_lang}", current_lang
        )
        if not is_valid_pair:
            self.logger.error(f"Language pair validation error: {pair_error}")
            raise ValueError(pair_error)

        # 言語マップ
        lang_map = {
            "ja": "Japanese", "fr": "French", "en": "English",
            "es": "Spanish", "de": "German", "it": "Italian"
        }

        source_label = lang_map.get(source_lang, source_lang.capitalize())
        target_label = lang_map.get(target_lang, target_lang.capitalize())

        # Gemini用プロンプト構築
        prompt = f"""
You are a professional {source_label} to {target_label} translator.
Using the context below, provide ONLY the {target_label} translation (no explanations or notes).

LANGUAGE PAIR: {source_label} → {target_label}

--- Previous conversation ---
{partner_message or "(None)"}

--- Background context ---
{context_info or "(None)"}

--- TEXT TO TRANSLATE TO {target_label.upper()} ---
{text}

IMPORTANT: Respond ONLY with the {target_label} translation.
        """.strip()

        return self.safe_gemini_request(prompt, current_lang=current_lang)
    
    def safe_gemini_request(self, prompt: str, current_lang: str = "jp") -> str:
        """
        Gemini APIの安全なリクエスト実行
        
        Args:
            prompt: API送信プロンプト
            current_lang: UI言語
            
        Returns:
            str: API応答結果
            
        Raises:
            ValueError: API エラーまたは検証エラー
        """
        try:
            GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
            if not GEMINI_API_KEY:
                raise ValueError("Gemini API key not available")

            # プロンプト検証
            if not prompt or len(prompt.strip()) < 5:
                raise ValueError(self.labels[current_lang]['validation_error_short'])

            # API リクエスト設定
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            data = {"contents": [{"parts": [{"text": prompt}]}]}

            # API呼び出し開始
            api_start_time = time.time()
            response = requests.post(url, headers=headers, json=data, timeout=30)
            api_duration = int((time.time() - api_start_time) * 1000)

            # API呼び出しログ記録
            try:
                from admin_logger import log_api_call
                log_api_call("gemini", response.status_code == 200, api_duration, "gemini-1.5-pro translation")
            except ImportError:
                # フォールバック: 基本ログ出力
                self.logger.info(f"Gemini API call completed: {api_duration}ms, status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                
                # 結果検証
                if not result or len(result.strip()) < 2:
                    raise ValueError(self.labels[current_lang]['validation_error_short'])
                
                return result.strip()
            else:
                log_security_event(
                    'GEMINI_API_ERROR',
                    f'Gemini API error: {response.status_code}',
                    'ERROR'
                )
                error_messages = {
                    "jp": f"Gemini API エラー: {response.status_code}",
                    "en": f"Gemini API error: {response.status_code}",
                    "fr": f"Erreur API Gemini: {response.status_code}",
                    "es": f"Error API Gemini: {response.status_code}"
                }
                raise ValueError(error_messages.get(current_lang, error_messages["jp"]))

        except requests.exceptions.Timeout:
            log_security_event('GEMINI_TIMEOUT', 'Gemini API timeout after 30s', 'WARNING')
            self.logger.error("Gemini API timeout: 30s")
            timeout_messages = {
                "jp": "⚠️ Gemini APIがタイムアウトしました（30秒）",
                "en": "⚠️ Gemini API timeout (30 seconds)",
                "fr": "⚠️ Timeout de l'API Gemini (30 secondes)",
                "es": "⚠️ Tiempo de espera de API Gemini (30 segundos)"
            }
            raise ValueError(timeout_messages.get(current_lang, timeout_messages["jp"]))
        except Exception as e:
            log_security_event('GEMINI_REQUEST_ERROR', f'Gemini request error: {str(e)}', 'ERROR')
            self.logger.error(f"Gemini API error: {str(e)}")
            error_messages = {
                "jp": f"Gemini API エラー: {str(e)}",
                "en": f"Gemini API error: {str(e)}",
                "fr": f"Erreur API Gemini: {str(e)}",
                "es": f"Error API Gemini: {str(e)}"
            }
            raise ValueError(error_messages.get(current_lang, error_messages["jp"]))