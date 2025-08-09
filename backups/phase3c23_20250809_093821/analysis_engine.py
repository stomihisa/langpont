"""
分析エンジン管理モジュール
Task B2-10-Phase1bで分離 - AnalysisEngineManagerクラス

このモジュールは以下の機能を提供します：
- get_engine_status: 分析エンジンの利用可能状況確認
- analyze_translations: 選択されたエンジンで翻訳分析実行
- _chatgpt_analysis: ChatGPTによる論理的分析
- _gemini_analysis: Geminiによる詳細分析
- _claude_analysis: Claudeによる深いニュアンス分析
"""

import os
from typing import Dict, Any
from flask import session
import openai


class AnalysisEngineManager:
    """分析エンジン管理クラス"""

    def __init__(self, claude_client=None, app_logger=None, f_gemini_3way_analysis=None):
        """依存注入設計によるコンストラクタ
        
        Args:
            claude_client: Claude API client (グローバル変数から注入)
            app_logger: アプリケーションログ (グローバル変数から注入)
            f_gemini_3way_analysis: Gemini分析関数 (既存関数から注入)
        """
        self.supported_engines = ["chatgpt", "gemini", "claude"]
        self.default_engine = "gemini"
        self.claude_client = claude_client
        self.app_logger = app_logger
        self.f_gemini_3way_analysis = f_gemini_3way_analysis

    def get_engine_status(self, engine: str) -> Dict[str, Any]:
        """エンジンの利用可能状況を確認"""
        if engine == "chatgpt":
            api_key = os.getenv("OPENAI_API_KEY")
            return {
                "available": bool(api_key),
                "status": "ready" if api_key else "api_key_missing",
                "description": "論理的分析"
            }
        elif engine == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            return {
                "available": bool(api_key),
                "status": "ready" if api_key else "api_key_missing",
                "description": "丁寧な説明"
            }
        elif engine == "claude":
            # 🆕 Claude client の実際の可用性をチェック
            return {
                "available": bool(self.claude_client),
                "status": "ready" if self.claude_client else "api_key_missing",
                "description": "深いニュアンス" if self.claude_client else "API設定必要"
            }
        else:
            return {
                "available": False,
                "status": "unsupported",
                "description": "未対応"
            }

    def analyze_translations(self, chatgpt_trans: str, enhanced_trans: str, gemini_trans: str, 
                           engine: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """選択されたエンジンで翻訳分析を実行"""

        if not engine:
            engine = self.default_engine

        engine_status = self.get_engine_status(engine)
        if not engine_status["available"]:
            return {
                "success": False,
                "error": f"{engine}エンジンが利用できません",
                "status": engine_status["status"],
                "engine": engine
            }

        try:
            if engine == "chatgpt":
                return self._chatgpt_analysis(chatgpt_trans, enhanced_trans, gemini_trans, context)
            elif engine == "gemini":
                return self._gemini_analysis(chatgpt_trans, enhanced_trans, gemini_trans, context)
            elif engine == "claude":
                return self._claude_analysis(chatgpt_trans, enhanced_trans, gemini_trans, context)
            else:
                return {
                    "success": False,
                    "error": f"未対応のエンジン: {engine}",
                    "engine": engine
                }

        except Exception as e:
            if self.app_logger:
                self.app_logger.error(f"分析エンジンエラー ({engine}): {str(e)}")
            else:
                print(f"分析エンジンエラー ({engine}): {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "engine": engine
            }

    def _chatgpt_analysis(self, chatgpt_trans: str, enhanced_trans: str, gemini_trans: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """ChatGPTによる分析"""

        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if not OPENAI_API_KEY:
            return {"success": False, "error": "OpenAI APIキーが設定されていません", "engine": "chatgpt"}

        # 言語設定取得
        display_lang = session.get("lang", "jp")
        source_lang = context.get("source_lang", "ja") if context else "ja"
        target_lang = context.get("target_lang", "en") if context else "en"
        input_text = context.get("input_text", "") if context else ""

        # ChatGPT特化プロンプト（論理的分析）
        if display_lang == "en":
            prompt = f"""Analyze these three English translations of the Japanese text logically and systematically.

Original Japanese: {input_text}

Translations to analyze:
1. ChatGPT Translation: {chatgpt_trans}
2. Enhanced Translation: {enhanced_trans}  
3. Gemini Translation: {gemini_trans}

Provide a logical analysis focusing on:
- Accuracy and precision
- Grammatical correctness
- Clarity and coherence
- Professional appropriateness

Which translation do you recommend and why? Respond in English."""
        else:
            # 🌍 多言語対応: 現在のUI言語を取得
            current_ui_lang = session.get('lang', 'jp')

            # 多言語プロンプトテンプレート
            prompt_templates = {
                'jp': f"""以下の3つの英語翻訳を論理的かつ体系的に分析してください。

元の日本語: {input_text}

分析対象の翻訳:
1. ChatGPT翻訳: {chatgpt_trans}
2. Enhanced翻訳: {enhanced_trans}  
3. Gemini翻訳: {gemini_trans}

以下の観点から論理的な分析を提供してください:
- 正確性と精度
- 文法の正しさ
- 明確性と一貫性
- 専門的な適切性

どの翻訳を推奨し、その理由は何ですか？日本語で回答してください。""",
                'en': f"""Please analyze the following three English translations logically and systematically.

Original Japanese: {input_text}

Translations to analyze:
1. ChatGPT Translation: {chatgpt_trans}
2. Enhanced Translation: {enhanced_trans}  
3. Gemini Translation: {gemini_trans}

Please provide logical analysis from the following perspectives:
- Accuracy and precision
- Grammatical correctness
- Clarity and coherence
- Professional appropriateness

Which translation do you recommend and why? Please respond in English.""",
                'fr': f"""Veuillez analyser logiquement et systématiquement les trois traductions anglaises suivantes.

Japonais original: {input_text}

Traductions à analyser:
1. Traduction ChatGPT: {chatgpt_trans}
2. Traduction améliorée: {enhanced_trans}  
3. Traduction Gemini: {gemini_trans}

Veuillez fournir une analyse logique selon les perspectives suivantes:
- Précision et exactitude
- Correction grammaticale
- Clarté et cohérence
- Pertinence professionnelle

Quelle traduction recommandez-vous et pourquoi? Veuillez répondre en français.""",
                'es': f"""Por favor analice lógica y sistemáticamente las siguientes tres traducciones al inglés.

Japonés original: {input_text}

Traducciones a analizar:
1. Traducción ChatGPT: {chatgpt_trans}
2. Traducción mejorada: {enhanced_trans}  
3. Traducción Gemini: {gemini_trans}

Por favor proporcione un análisis lógico desde las siguientes perspectivas:
- Precisión y exactitud
- Corrección gramatical
- Claridad y coherencia
- Adecuación profesional

¿Qué traducción recomienda y por qué? Por favor responda en español."""
            }

            prompt = prompt_templates.get(current_ui_lang, prompt_templates['jp'])

        try:
            openai.api_key = OPENAI_API_KEY

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "You are an expert translation analyst. Provide logical and systematic analysis."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                max_tokens=1000,
                temperature=0.3
            )

            analysis_text = response.choices[0].message.content.strip()

            return {
                "success": True,
                "analysis_text": analysis_text,
                "engine": "chatgpt",
                "status": "completed"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"ChatGPT分析エラー: {str(e)}",
                "engine": "chatgpt"
            }

    def _gemini_analysis(self, chatgpt_trans: str, enhanced_trans: str, gemini_trans: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Geminiによる分析（既存のf_gemini_3way_analysis関数を利用）"""

        try:
            if self.f_gemini_3way_analysis:
                analysis_text, prompt = self.f_gemini_3way_analysis(chatgpt_trans, enhanced_trans, gemini_trans)
            else:
                return {
                    "success": False,
                    "error": "Gemini分析関数が利用できません",
                    "engine": "gemini"
                }

            return {
                "success": True,
                "analysis_text": analysis_text,
                "engine": "gemini",
                "status": "completed",
                "prompt_used": prompt
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Gemini分析エラー: {str(e)}",
                "engine": "gemini"
            }

    def _claude_analysis(self, chatgpt_trans: str, enhanced_trans: str, gemini_trans: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """🆕 Claude API による分析実装 (Task 2.9.2 Phase B-3.5.7)"""

        # 🔍 Claude API設定チェック（Task 2.9.2 Phase B-3.5.7 Final Integration）
        if self.app_logger:
            self.app_logger.info(f"🎭 Claude analysis requested - Client available: {bool(self.claude_client)}")

        if not self.claude_client:
            # APIキー未設定時の代替メッセージ
            display_lang = session.get("lang", "jp")
            if display_lang == "en":
                message = "🚧 Claude analysis unavailable. Please check API key configuration."
            elif display_lang == "fr":
                message = "🚧 Analyse Claude indisponible. Veuillez vérifier la configuration de la clé API."
            elif display_lang == "es":
                message = "🚧 Análisis Claude no disponible. Por favor verifique la configuración de la clave API."
            else:
                message = "🚧 Claude分析が利用できません。APIキー設定を確認してください。"

            if self.app_logger:
                self.app_logger.error(f"❌ Claude client not available - returning error message")
            return {
                "success": False,
                "analysis_text": message,
                "engine": "claude",
                "status": "api_key_missing"
            }

        try:
            # 言語設定取得
            display_lang = session.get("lang", "jp")
            source_lang = context.get("source_lang", "ja") if context else "ja"
            target_lang = context.get("target_lang", "en") if context else "en"
            input_text = context.get("input_text", "") if context else ""

            # 言語ラベルマッピング
            lang_labels = {
                "ja": "Japanese", "en": "English", 
                "fr": "French", "es": "Spanish"
            }
            source_label = lang_labels.get(source_lang, source_lang)
            target_label = lang_labels.get(target_lang, target_lang)

            # Claude特化プロンプト（深いニュアンス分析とコンテキスト理解）
            if display_lang == "en":
                prompt = f"""As Claude, provide a thoughtful and nuanced analysis of these three {target_label} translations of the given {source_label} text.

ORIGINAL TEXT ({source_label}): {input_text[:1000]}

LANGUAGE PAIR: {source_label} → {target_label}

TRANSLATIONS TO COMPARE:
1. ChatGPT Translation: {chatgpt_trans}
2. Enhanced Translation: {enhanced_trans}  
3. Gemini Translation: {gemini_trans}

Please provide a comprehensive analysis focusing on:
- Cultural nuances and appropriateness
- Emotional tone and subtle implications
- Contextual accuracy and natural flow
- Which translation best captures the speaker's intent
- Detailed reasoning for your recommendation

Respond in English with thoughtful insights."""

            elif display_lang == "fr":
                prompt = f"""En tant que Claude, fournissez une analyse réfléchie et nuancée de ces trois traductions {target_label} du texte {source_label} donné.

TEXTE ORIGINAL ({source_label}): {input_text[:1000]}

PAIRE LINGUISTIQUE: {source_label} → {target_label}

TRADUCTIONS À COMPARER:
1. Traduction ChatGPT: {chatgpt_trans}
2. Traduction Améliorée: {enhanced_trans}  
3. Traduction Gemini: {gemini_trans}

Veuillez fournir une analyse complète en vous concentrant sur:
- Les nuances culturelles et l'appropriation
- Le ton émotionnel et les implications subtiles
- La précision contextuelle et le flux naturel
- Quelle traduction capture le mieux l'intention du locuteur
- Raisonnement détaillé pour votre recommandation

Répondez en français avec des insights réfléchis."""

            elif display_lang == "es":
                prompt = f"""Como Claude, proporcione un análisis reflexivo y matizado de estas tres traducciones al {target_label} del texto {source_label} dado.

TEXTO ORIGINAL ({source_label}): {input_text[:1000]}

PAR LINGÜÍSTICO: {source_label} → {target_label}

TRADUCCIONES A COMPARAR:
1. Traducción ChatGPT: {chatgpt_trans}
2. Traducción Mejorada: {enhanced_trans}  
3. Traducción Gemini: {gemini_trans}

Por favor proporcione un análisis completo enfocándose en:
- Matices culturales y apropiación
- Tono emocional e implicaciones sutiles
- Precisión contextual y flujo natural
- Qué traducción captura mejor la intención del hablante
- Razonamiento detallado para su recomendación

Responda en español con insights reflexivos."""

            else:  # Japanese
                prompt = f"""Claudeとして、与えられた{source_label}テキストの以下3つの{target_label}翻訳について、思慮深く、ニュアンスに富んだ分析を提供してください。

元のテキスト（{source_label}）: {input_text[:1000]}

言語ペア: {source_label} → {target_label}

比較する翻訳:
1. ChatGPT翻訳: {chatgpt_trans}
2. 改善翻訳: {enhanced_trans}  
3. Gemini翻訳: {gemini_trans}

以下に焦点を当てた包括的な分析を提供してください:
- 文化的ニュアンスと適切性
- 感情的なトーンと微妙な含意
- 文脈の正確性と自然な流れ
- どの翻訳が話者の意図を最もよく捉えているか
- 推奨事項の詳細な理由づけ

思慮深い洞察とともに日本語で回答してください。"""

            # 🎭 Claude API リクエスト（Task 2.9.2 Phase B-3.5.7 Final Integration）
            if self.app_logger:
                self.app_logger.info(f"🎭 Calling Claude API with prompt length: {len(prompt)} chars")

            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            analysis_text = response.content[0].text.strip()

            # 成功ログ
            if self.app_logger:
                self.app_logger.info(f"✅ Claude分析成功: 言語={display_lang}, 文字数={len(analysis_text)}")
                self.app_logger.info(f"🎭 Claude analysis preview: {analysis_text[:200]}...")

            return {
                "success": True,
                "analysis_text": analysis_text,
                "engine": "claude",
                "model": "claude-3-5-sonnet-20241022",
                "status": "completed",
                "prompt_used": prompt[:500] + "..." if len(prompt) > 500 else prompt
            }

        except Exception as e:
            error_msg = str(e)
            if self.app_logger:
                self.app_logger.error(f"Claude分析エラー: {error_msg}")

            # エラーメッセージの多言語対応
            display_lang = session.get("lang", "jp")
            if display_lang == "en":
                error_response = f"⚠️ Claude analysis failed: {error_msg[:100]}..."
            elif display_lang == "fr":
                error_response = f"⚠️ Échec de l'analyse Claude: {error_msg[:100]}..."
            elif display_lang == "es":
                error_response = f"⚠️ Falló el análisis de Claude: {error_msg[:100]}..."
            else:
                error_response = f"⚠️ Claude分析に失敗しました: {error_msg[:100]}..."

            return {
                "success": False,
                "analysis_text": error_response,
                "error": error_msg,
                "engine": "claude"
            }