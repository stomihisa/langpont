"""
分析サービスモジュール
Task #9-3 AP-1 Phase 3: 分析機能のBlueprint分離

このモジュールは以下の機能を提供します：
- 分析エンジンによる翻訳分析実行
- 分析結果の保存・管理
- 統一されたエラーハンドリング
- 依存注入による疎結合設計
"""

import os
import time
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from flask import session, request
from security.security_logger import log_security_event, log_access_event


class AnalysisService:
    """分析サービスの統合クラス"""
    
    def __init__(self, translation_state_manager, analysis_engine_manager, 
                 claude_client, logger, labels):
        """
        依存注入によるコンストラクタ
        
        Args:
            translation_state_manager: TranslationStateManager instance
            analysis_engine_manager: AnalysisEngineManager instance
            claude_client: Claude API client
            logger: Application logger
            labels: Multilingual labels
        """
        self.state_manager = translation_state_manager
        self.engine_manager = analysis_engine_manager
        self.claude_client = claude_client
        self.logger = logger
        self.labels = labels
    
    def perform_nuance_analysis(self, session_id: str, selected_engine: str = "gemini") -> Dict[str, Any]:
        """
        ニュアンス分析を実行
        
        Args:
            session_id: セッションID
            selected_engine: 分析エンジン名
            
        Returns:
            Dict[str, Any]: 分析結果
        """
        try:
            # 翻訳データ取得（Redis + Session フォールバック）
            if self.state_manager and session_id:
                translated_text = self.state_manager.get_large_data(
                    "translated_text", session_id, 
                    default=session.get("translated_text", "")
                )
                better_translation = self.state_manager.get_large_data(
                    "better_translation", session_id, 
                    default=session.get("better_translation", "")
                )
                gemini_translation = self.state_manager.get_large_data(
                    "gemini_translation", session_id, 
                    default=session.get("gemini_translation", "")
                )
            else:
                # フォールバック: セッションから取得
                translated_text = session.get("translated_text", "")
                better_translation = session.get("better_translation", "")
                gemini_translation = session.get("gemini_translation", "")

            # データ存在確認
            if not (len(translated_text.strip()) > 0 and
                    len(better_translation.strip()) > 0 and
                    len(gemini_translation.strip()) > 0):
                return {"error": "必要な翻訳データが不足しています"}

            # エンジン別分析実行
            if selected_engine == 'gemini':
                # 従来のGemini分析
                result, chatgpt_prompt = self._gemini_3way_analysis(
                    translated_text, better_translation, gemini_translation
                )
                return {
                    "success": True,
                    "analysis_text": result,
                    "prompt_used": chatgpt_prompt,
                    "engine": selected_engine
                }
            else:
                # マルチエンジンシステムを使用
                input_text = session.get("input_text", "")
                
                analysis_result = self.engine_manager.analyze_translations(
                    chatgpt_trans=translated_text,
                    enhanced_trans=better_translation,
                    gemini_trans=gemini_translation,
                    engine=selected_engine,
                    context={
                        "input_text": input_text,
                        "source_lang": self._get_translation_state("language_pair", "ja-en").split("-")[0],
                        "target_lang": self._get_translation_state("language_pair", "ja-en").split("-")[1],
                        "partner_message": self._get_translation_state("partner_message", ""),
                        "context_info": self._get_translation_state("context_info", "")
                    }
                )

                if not analysis_result['success']:
                    return {
                        "error": f"分析エンジン({selected_engine})でエラーが発生しました: {analysis_result['error']}"
                    }

                return {
                    "success": True,
                    "analysis_text": analysis_result.get('analysis_text', ''),
                    "prompt_used": analysis_result.get('prompt_used', ''),
                    "engine": selected_engine
                }

        except Exception as e:
            self.logger.error(f"Analysis service error: {str(e)}")
            return {"error": str(e)}
    
    def save_analysis_results(self, session_id: str, analysis_data: Dict[str, Any]) -> bool:
        """
        分析結果をRedisに保存
        
        Args:
            session_id: セッションID
            analysis_data: 保存する分析データ
            
        Returns:
            bool: 保存成功フラグ
        """
        try:
            if not self.state_manager or not session_id:
                return False
                
            # 分析結果をRedisに保存
            analysis_saved = self.state_manager.save_large_data(
                "gemini_3way_analysis", analysis_data.get("analysis_text", ""), session_id
            )
            
            if analysis_saved:
                self.logger.info(f"✅ Analysis result cached successfully - {len(analysis_data.get('analysis_text', ''))} chars for session {session_id[:16]}...")
                # セッションクリーンアップ
                session.pop("gemini_3way_analysis", None)
                return True
            else:
                self.logger.warning("⚠️ Failed to cache analysis result - using session fallback")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to save analysis results: {e}")
            return False

    def save_analysis_to_db(self, session_id: str, analysis_result: str, recommendation: str,
                           confidence: float, strength: str, reasons: str) -> bool:
        """
        分析結果をデータベースに保存（app.pyから移動）
        
        Args:
            session_id: セッションID
            analysis_result: 分析結果テキスト
            recommendation: 推奨翻訳
            confidence: 信頼度
            strength: 強度
            reasons: 理由
            
        Returns:
            bool: 保存成功フラグ
        """
        try:
            self.logger.info(f"🔍 保存開始: session_id={session_id}")
            self.logger.info(f"🔍 分析結果長: {len(analysis_result)} 文字")
            self.logger.info(f"🔍 推奨: {recommendation}, 信頼度: {confidence}, 強度: {strength}")

            import sqlite3
            conn = sqlite3.connect('langpont_translation_history.db')
            cursor = conn.cursor()

            # まず対象レコードが存在するか確認
            cursor.execute("""
                SELECT id, source_text, created_at 
                FROM translation_history 
                WHERE session_id = ?
                ORDER BY created_at DESC
            """, (session_id,))

            records = cursor.fetchall()
            self.logger.info(f"🔍 session_id={session_id} のレコード数: {len(records)}")

            if not records:
                self.logger.error(f"❌ session_id {session_id} のレコードが見つかりません")
                # デバッグ用: 最新10件のsession_idを表示
                cursor.execute("""
                    SELECT session_id, created_at 
                    FROM translation_history 
                    ORDER BY created_at DESC 
                    LIMIT 10
                """)
                recent_sessions = cursor.fetchall()
                self.logger.info("🔍 最新のセッションID一覧:")
                for sess_id, created_at in recent_sessions:
                    self.logger.info(f"  - {sess_id} ({created_at})")

                conn.close()
                return False

            # 最新のレコードを選択
            record_id = records[0][0]
            source_text = records[0][1][:50] if records[0][1] else "N/A"
            created_at = records[0][2]
            self.logger.info(f"✅ 対象レコード発見: ID={record_id}, 翻訳元={source_text}..., 作成={created_at}")

            # 統合データを作成
            combined_analysis = f"""=== Gemini 分析結果 ===
{analysis_result}

=== 推奨翻訳 ===
推奨: {recommendation}
信頼度: {confidence}
強度: {strength}
理由: {reasons}
分析日時: {datetime.now().isoformat()}
"""

            # 更新実行（既存のgemini_analysisカラムを使用）
            cursor.execute("""
                UPDATE translation_history 
                SET gemini_analysis = ?
                WHERE id = ?
            """, (combined_analysis, record_id))

            updated_rows = cursor.rowcount
            self.logger.info(f"✅ 更新完了: {updated_rows} 行更新")

            conn.commit()
            conn.close()

            return updated_rows > 0

        except Exception as e:
            self.logger.error(f"Failed to save analysis to DB: {str(e)}")
            self.logger.error(f"❌ 分析保存失敗: session_id={session_id}")
            try:
                conn.close()
            except:
                pass
            return False

    def _gemini_3way_analysis(self, translated_text: str, better_translation: str, gemini_translation: str) -> tuple:
        """
        3つの翻訳結果を分析する関数（app.pyから移動）
        
        Args:
            translated_text: ChatGPT翻訳
            better_translation: Enhanced翻訳
            gemini_translation: Gemini翻訳
            
        Returns:
            tuple: (分析結果, プロンプト)
        """
        # セッションから表示言語を早期取得（エラーメッセージも多言語化）
        display_lang = session.get("lang", "jp")
        analysis_lang_map = {
            "jp": "Japanese",
            "en": "English", 
            "fr": "French",
            "es": "Spanish"
        }
        analysis_language = analysis_lang_map.get(display_lang, "Japanese")

        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY or len(GEMINI_API_KEY) < 10:
            if analysis_language == "English":
                return "⚠️ Gemini API key is not properly configured", ""
            elif analysis_language == "French":
                return "⚠️ La clé API Gemini n'est pas correctement configurée", ""
            elif analysis_language == "Spanish":
                return "⚠️ La clave API de Gemini no está configurada correctamente", ""
            else:
                return "⚠️ Gemini APIキーが正しく設定されていません", ""

        # 入力パラメータの検証
        if not all([translated_text, better_translation, gemini_translation]):
            if analysis_language == "English":
                return "⚠️ Translation data required for analysis is missing", ""
            elif analysis_language == "French":
                return "⚠️ Les données de traduction nécessaires à l'analyse sont manquantes", ""
            elif analysis_language == "Spanish":
                return "⚠️ Faltan los datos de traducción necesarios para el análisis", ""
            else:
                return "⚠️ 分析に必要な翻訳データが不足しています", ""

        # 現在の言語設定を直接取得
        current_language_pair = request.form.get('language_pair') or self._get_translation_state("language_pair", "ja-en")

        try:
            source_lang, target_lang = current_language_pair.split("-")
            log_access_event(f'Gemini analysis - Current language pair: {current_language_pair}')
        except:
            source_lang = "ja"
            target_lang = "en"
            log_security_event('GEMINI_LANGUAGE_FALLBACK', 'Using fallback language pair ja-en', 'WARNING')

        # 現在の入力データのみ使用
        current_input_text = request.form.get('japanese_text') or session.get("input_text", "")
        current_partner_message = request.form.get('partner_message') or ""
        current_context_info = request.form.get('context_info') or ""

        # 言語マップ
        lang_map = {
            "ja": "Japanese", "fr": "French", "en": "English",
            "es": "Spanish", "de": "German", "it": "Italian"
        }

        source_label = lang_map.get(source_lang, source_lang.capitalize())
        target_label = lang_map.get(target_lang, target_lang.capitalize())

        # 分析プロンプトの構築
        if current_context_info.strip():
            context_section = f"""
CURRENT TRANSLATION CONTEXT:
- Language pair: {source_label} → {target_label}
- Previous conversation: {current_partner_message or "None"}
- Situation: {current_context_info.strip()}"""
        else:
            context_section = f"""
CURRENT TRANSLATION CONTEXT:
- Language pair: {source_label} → {target_label}
- Type: General conversation"""

        # 言語別の指示を構築
        current_ui_lang = session.get('lang', 'jp')
        lang_instructions = {
            'jp': "IMPORTANT: 日本語で回答してください。他の言語は使用しないでください。",
            'en': "IMPORTANT: Please respond in English. Do not use any other languages.",
            'fr': "IMPORTANT: Veuillez répondre en français. N'utilisez aucune autre langue.",
            'es': "IMPORTANT: Por favor responda en español. No use ningún otro idioma."
        }
        lang_instruction = lang_instructions.get(current_ui_lang, lang_instructions['jp'])

        # フォーカスポイント
        focus_points_map = {
            'jp': f"""- どの{target_label}翻訳が最も自然か
- 与えられた文脈への適切性
- この{source_label}から{target_label}への翻訳タスクへの推奨""",
            'en': f"""- Which {target_label} translation is most natural
- Appropriateness to the given context
- Recommendation for this {source_label} to {target_label} translation task""",
            'fr': f"""- Quelle traduction {target_label} est la plus naturelle
- Adéquation au contexte donné
- Recommandation pour cette tâche de traduction {source_label} vers {target_label}""",
            'es': f"""- Qué traducción al {target_label} es más natural
- Adecuación al contexto dado
- Recomendación para esta tarea de traducción de {source_lang} a {target_lang}"""
        }
        focus_points = focus_points_map.get(current_ui_lang, focus_points_map['jp'])

        # 明確なプロンプト
        prompt = f"""{lang_instruction}

Analyze these {target_label} translations of the given {source_label} text.

ORIGINAL TEXT ({source_label}): {current_input_text[:1000]}

{context_section}

TRANSLATIONS TO COMPARE:
1. ChatGPT Translation: {translated_text}
2. Enhanced Translation: {better_translation}  
3. Gemini Translation: {gemini_translation}

IMPORTANT: All translations above are in {target_label}. Analyze them as {target_label} text.

Provide analysis in {analysis_language} focusing on:
{focus_points}

Your entire response must be in {analysis_language}."""

        # 文字数チェック
        total_length = len(translated_text) + len(better_translation) + len(gemini_translation)
        warning = ""
        if total_length > 8000:
            warning = f"⚠️ テキストが長いため分析が制限される可能性があります（{total_length}文字）\n\n"

        # リクエスト実行
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt[:8000]  # プロンプトを8000文字に制限
                }]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1000
            }
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=45)
            if response.status_code == 200:
                result_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                log_access_event('Gemini 3-way analysis completed successfully')
                return warning + result_text.strip(), prompt
            else:
                error_msg = f"⚠️ Gemini API error: {response.status_code}"
                log_security_event('GEMINI_API_ERROR', error_msg, 'ERROR')
                return error_msg, prompt

        except requests.exceptions.Timeout:
            # 多言語対応のタイムアウトメッセージ
            if analysis_language == "English":
                return f"⚠️ Gemini analysis timed out (45 seconds).\n\n" \
                       f"The text may be too long (total {total_length} characters).\n" \
                       f"Please try shortening the translation text and try again.", prompt
            elif analysis_language == "French":
                return f"⚠️ L'analyse Gemini a expiré (45 secondes).\n\n" \
                       f"Le texte est peut-être trop long (total {total_length} caractères).\n" \
                       f"Veuillez raccourcir le texte de traduction et réessayer.", prompt
            elif analysis_language == "Spanish":
                return f"⚠️ El análisis de Gemini agotó el tiempo de espera (45 segundes).\n\n" \
                       f"El texto puede ser demasiado largo (total {total_length} caractères).\n" \
                       f"Por favor acorte el texto de traducción e intente de nuevo.", prompt
            else:
                return f"⚠️ Gemini分析がタイムアウトしました（45秒）。\n\n" \
                       f"テキストが長すぎる可能性があります（合計{total_length}文字）。\n" \
                       f"翻訳テキストを短縮してから再度お試しください。", prompt

        except Exception as e:
            import traceback
            # Gemini APIの詳細エラーログ
            if hasattr(e, 'response'):
                error_detail = f"Status: {e.response.status_code}, Body: {e.response.text[:500]}"
            else:
                error_detail = str(e)

            log_security_event('GEMINI_DETAILED_ERROR', error_detail, 'ERROR')
            self.logger.error(traceback.format_exc())

            # 多言語対応のエラーメッセージ
            if analysis_language == "English":
                return f"⚠️ Gemini analysis error (details logged): {str(e)[:100]}", prompt
            elif analysis_language == "French":
                return f"⚠️ Erreur d'analyse Gemini (détails enregistrés): {str(e)[:100]}", prompt
            elif analysis_language == "Spanish":
                return f"⚠️ Error de análisis de Gemini (detalles registrados): {str(e)[:100]}", prompt
            else:
                return f"⚠️ Gemini分析エラー（詳細ログに記録済み）: {str(e)[:100]}", prompt

    def _get_translation_state(self, field_name: str, default_value: str = "") -> str:
        """
        翻訳状態取得ヘルパー関数（app.pyから移動）
        
        Args:
            field_name: 取得するフィールド名
            default_value: デフォルト値
            
        Returns:
            str: 取得した値
        """
        session_id = getattr(session, 'session_id', None)
        
        if self.state_manager and session_id:
            cached_value = self.state_manager.get_translation_state(
                session_id, field_name, default_value
            )
            if cached_value is not None:
                return cached_value
        
        return session.get(field_name, default_value)