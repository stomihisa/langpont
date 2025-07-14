"""
LangPont翻訳エキスパートAI - 安全部分のみ
Task B2-10-Phase1c: 段階的移行アプローチ

このモジュールはLangPontTranslationExpertAIクラスの安全な部分のみを含みます。
Flask session依存やapp_logger依存のメソッドは含まれていません。
"""

import re
from typing import Dict, Any


class LangPontTranslationExpertAI:
    """🎯 LangPont多言語翻訳エキスパートAI - 安全部分移行版"""

    def __init__(self, client: Any) -> None:
        self.client = client
        self.supported_languages = {
            'ja': {'name': 'Japanese', '日本語': True},
            'en': {'name': 'English', 'English': True}, 
            'fr': {'name': 'French', 'Français': True},
            'es': {'name': 'Spanish', 'Español': True}
        }

        # 🌍 多言語対応: レスポンス言語マップ
        self.response_lang_map = {
            "jp": "Japanese",
            "en": "English", 
            "fr": "French",
            "es": "Spanish"  # ← スペイン語を追加
        }

        # 🌍 多言語対応: エラーメッセージ
        self.error_messages = {
            "jp": {
                "question_processing": "質問処理中にエラーが発生しました: {}",
                "translation_modification": "翻訳修正中にエラーが発生しました: {}",
                "analysis_inquiry": "分析解説中にエラーが発生しました: {}",
                "linguistic_question": "言語学的質問処理中にエラーが発生しました: {}",
                "context_variation": "コンテキスト変更処理中にエラーが発生しました: {}",
                "comparison_analysis": "比較分析中にエラーが発生しました: {}"
            },
            "en": {
                "question_processing": "Error occurred while processing question: {}",
                "translation_modification": "Error occurred during translation modification: {}",
                "analysis_inquiry": "Error occurred during analysis inquiry: {}",
                "linguistic_question": "Error occurred while processing linguistic question: {}",
                "context_variation": "Error occurred during context variation: {}",
                "comparison_analysis": "Error occurred during comparison analysis: {}"
            },
            "fr": {
                "question_processing": "Erreur lors du traitement de la question: {}",
                "translation_modification": "Erreur lors de la modification de traduction: {}",
                "analysis_inquiry": "Erreur lors de l'analyse d'enquête: {}",
                "linguistic_question": "Erreur lors du traitement de la question linguistique: {}",
                "context_variation": "Erreur lors de la variation de contexte: {}",
                "comparison_analysis": "Erreur lors de l'analyse comparative: {}"
            },
            "es": {
                "question_processing": "Error al procesar la pregunta: {}",
                "translation_modification": "Error durante la modificación de traducción: {}",
                "analysis_inquiry": "Error durante la consulta de análisis: {}",
                "linguistic_question": "Error al procesar la pregunta lingüística: {}",
                "context_variation": "Error durante la variación de contexto: {}",
                "comparison_analysis": "Error durante el análisis comparativo: {}"
            }
        }

    def _get_error_message(self, context: Dict[str, Any], error_type: str, error_details: str) -> str:
        """🌍 多言語対応エラーメッセージを取得"""
        display_lang = context.get('display_language', 'jp')
        lang_errors = self.error_messages.get(display_lang, self.error_messages["jp"])
        error_template = lang_errors.get(error_type, lang_errors["question_processing"])
        return error_template.format(error_details)

    def _analyze_question_intent(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """🎯 質問の意図を詳細に分析"""

        question_lower = question.lower()

        # 翻訳修正要求の検出
        modification_patterns = [
            r'(\d+)番目.*?((口語|カジュアル|フォーマル|丁寧|親しみ|ビジネス).*?(に|で|風に))',
            r'(\d+).*?(もっと|より).*?(口語|カジュアル|フォーマル|丁寧|親しみ|ビジネス)',
            r'(\d+).*?(変更|修正|直し|調整).*?(して|してください)',
            r'(フランス語|英語|スペイン語).*?(口語|カジュアル|フォーマル).*?(に|で)'
        ]

        for pattern in modification_patterns:
            match = re.search(pattern, question)
            if match:
                # 番号抽出
                number_match = re.search(r'(\d+)番目', question)
                target_number = int(number_match.group(1)) if number_match else None

                # スタイル抽出
                style_match = re.search(r'(口語|カジュアル|フォーマル|丁寧|親しみ|ビジネス)', question)
                target_style = style_match.group(1) if style_match else None

                return {
                    'type': 'translation_modification',
                    'target_number': target_number,
                    'target_style': target_style,
                    'target_language': context['target_lang'],
                    'confidence': 0.9
                }

        # 分析内容への質問
        if any(word in question_lower for word in ['分析', 'なぜ', '理由', '推奨', 'gemini', 'chatgpt']):
            return {
                'type': 'analysis_inquiry',
                'confidence': 0.8
            }

        # 言語学的質問
        if any(word in question_lower for word in ['活用', '文法', '構造', '意味', '違い', '類義語']):
            return {
                'type': 'linguistic_question', 
                'confidence': 0.8
            }

        # コンテキスト変更要求
        if any(word in question_lower for word in ['怒っ', '友達', 'ビジネス', '場合', 'だったら']):
            return {
                'type': 'context_variation',
                'confidence': 0.7
            }

        # 比較質問
        if any(word in question_lower for word in ['比較', '違い', 'どちら', '1番目', '2番目', '3番目']):
            return {
                'type': 'comparison_analysis',
                'confidence': 0.8
            }

        return {
            'type': 'general_expert',
            'confidence': 0.5
        }

    def _handle_translation_modification(self, question: str, context: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """🔧 翻訳修正要求を処理"""

        target_number = analysis.get('target_number')
        target_style = analysis.get('target_style') 
        target_lang = context['target_lang']

        # 対象翻訳を特定
        translations = context['translations']
        translation_map = {
            1: ('ChatGPT', translations['chatgpt']),
            2: ('Enhanced', translations['enhanced']), 
            3: ('Gemini', translations['gemini'])
        }

        if target_number and target_number in translation_map:
            engine_name, original_translation = translation_map[target_number]
        else:
            # 番号が指定されていない場合、最新の分析で推奨された翻訳を使用
            engine_name = "Enhanced"
            original_translation = translations['enhanced']

        # 言語別のスタイル定義
        style_instructions = {
            'fr': {
                '口語': 'très familier et oral, utilise des contractions et expressions quotidiennes',
                'カジュアル': 'détendu et amical, style conversationnel sans formalité excessive',
                'フォーマル': 'très formel et professionnel, style soutenu et respectueux',
                'ビジネス': 'style commercial professionnel, adapté aux communications d\'entreprise',
                '丁寧': 'poli et courtois, utilise les formules de politesse appropriées'
            },
            'en': {
                '口語': 'very casual and colloquial, use contractions and everyday expressions',
                'カジュアル': 'relaxed and friendly, conversational style without excessive formality',
                'フォーマル': 'very formal and professional, elevated and respectful style',
                'ビジネス': 'professional business style, suitable for corporate communications',
                '丁寧': 'polite and courteous, use appropriate politeness formulas'
            },
            'es': {
                '口語': 'muy familiar y coloquial, usa contracciones y expresiones cotidianas',
                'カジュアル': 'relajado y amistoso, estilo conversacional sin formalidad excesiva',
                'フォーマル': 'muy formal y profesional, estilo elevado y respetuoso',
                'ビジネス': 'estilo comercial profesional, adecuado para comunicaciones empresariales',
                '丁寧': 'cortés y educado, usa las fórmulas de cortesía apropiadas'
            }
        }

        style_instruction = style_instructions.get(target_lang, {}).get(target_style, f'{target_style}的なスタイル')

        # 専門的な修正プロンプト
        prompt = f"""【LangPont翻訳エキスパートAI】
あなたは多言語翻訳の専門家です。以下の翻訳を指定されたスタイルに修正してください。

【元の文章（日本語）】
{context['original_text']}

【現在の{engine_name}翻訳（{target_lang.upper()}）】
{original_translation}

【修正指示】
この翻訳を「{target_style}」なスタイルに変更してください。
言語: {target_lang.upper()}
スタイル要件: {style_instruction}

【修正版翻訳を提供してください】
- 元の意味は完全に保持
- {target_style}なスタイルに完全に適応
- 文化的に自然な表現を使用
- 修正のポイントも説明

修正版:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",  # より高品質な翻訳のためGPT-4を使用
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800
            )

            result = response.choices[0].message.content.strip()

            return {
                "type": "translation_modification",
                "result": result,
                "original_engine": engine_name,
                "target_style": target_style,
                "target_language": target_lang
            }

        except Exception as e:
            error_msg = self._get_error_message(context, "translation_modification", str(e))
            return {
                "type": "error",
                "result": error_msg
            }

    def _handle_analysis_inquiry(self, question: str, context: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """🧠 分析内容への質問を処理"""

        nuance_analysis = context.get('nuance_analysis', '')
        selected_engine = context.get('selected_engine', 'gemini')

        prompt = f"""【LangPont翻訳エキスパートAI - 分析解説】
あなたは翻訳品質分析の専門家です。以下の分析結果について質問に答えてください。

【元の文章】
{context['original_text']}

【3つの翻訳】
1. ChatGPT: {context['translations']['chatgpt']}
2. Enhanced: {context['translations']['enhanced']}
3. Gemini: {context['translations']['gemini']}

【{selected_engine.upper()}による分析結果】
{nuance_analysis}

【ユーザーの質問】
{question}

【回答要件】
- 分析内容を詳しく解説
- 翻訳の品質評価基準を説明
- 推奨理由の言語学的根拠を提示
- 具体例を用いて説明

回答:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=700
            )

            result = response.choices[0].message.content.strip()

            return {
                "type": "analysis_inquiry",
                "result": result,
                "analyzed_engine": selected_engine
            }

        except Exception as e:
            error_msg = self._get_error_message(context, "analysis_inquiry", str(e))
            return {
                "type": "error", 
                "result": error_msg
            }

    def _handle_linguistic_question(self, question: str, context: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """📚 言語学的質問を処理"""

        prompt = f"""【LangPont翻訳エキスパートAI - 言語学習支援】
あなたは多言語の言語学専門家です。以下の翻訳に関する言語学的質問に答えてください。

【翻訳セッション情報】
元の文章: {context['original_text']}
言語ペア: {context['source_lang']} → {context['target_lang']}

【3つの翻訳結果】
1. ChatGPT: {context['translations']['chatgpt']}
2. Enhanced: {context['translations']['enhanced']}
3. Gemini: {context['translations']['gemini']}

【ユーザーの質問】
{question}

【回答要件】
- 言語学的に正確な説明
- 文法構造の詳細解説
- 語彙の使い分けの説明
- 実用的な学習アドバイス
- 具体例を用いた説明

回答:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=700
            )

            result = response.choices[0].message.content.strip()

            return {
                "type": "linguistic_question",
                "result": result
            }

        except Exception as e:
            error_msg = self._get_error_message(context, "linguistic_question", str(e))
            return {
                "type": "error",
                "result": error_msg
            }

    def _handle_context_variation(self, question: str, context: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """🎭 コンテキスト変更要求を処理"""

        # 推奨翻訳を基準とする
        base_translation = context['translations']['enhanced']

        prompt = f"""【LangPont翻訳エキスパートAI - コンテキスト適応】
あなたは多言語翻訳の専門家です。異なるコンテキストでの翻訳バリエーションを提供してください。

【元の文章】
{context['original_text']}

【現在の翻訳（{context['target_lang'].upper()}）】
{base_translation}

【コンテキスト変更要求】
{question}

【提供してください】
- 新しいコンテキストに適した翻訳
- 変更のポイントと理由
- 文化的配慮事項
- 使用場面の説明

回答:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=700
            )

            result = response.choices[0].message.content.strip()

            return {
                "type": "context_variation",
                "result": result
            }

        except Exception as e:
            error_msg = self._get_error_message(context, "context_variation", str(e))
            return {
                "type": "error",
                "result": error_msg
            }

    def handle_comparison_analysis_safe(self, question: str, context: Dict[str, Any], 
                                      analysis: Dict[str, Any], logger_adapter) -> Dict[str, Any]:
        """⚖️ 比較分析を処理（安全版 - app_logger依存なし）"""
        
        translations = context['translations']

        # 🆕 デバッグ：利用可能な翻訳キーを確認（SafeLoggerAdapter使用）
        logger_adapter.info(f"🔍 Available translation keys: {list(translations.keys())}")

        # 🆕 必要なキーの存在確認
        required_keys = ['chatgpt', 'enhanced', 'gemini', 'chatgpt_reverse', 'enhanced_reverse', 'gemini_reverse']
        missing_keys = [key for key in required_keys if key not in translations]
        if missing_keys:
            logger_adapter.warning(f"⚠️ Missing translation keys: {missing_keys}")
            return {
                "type": "error",
                "result": f"翻訳データが不完全です。不足キー: {missing_keys}"
            }

        # 📝 既存のロジックを完全移行
        prompt = f"""【LangPont翻訳エキスパートAI - 比較分析】
あなたは翻訳品質分析の専門家です。以下の翻訳を詳細に比較分析してください。

【元の文章】
{context['original_text']}

【比較対象の翻訳】
1. ChatGPT: {translations['chatgpt']}
2. Enhanced: {translations['enhanced']}
3. Gemini: {translations['gemini']}

【逆翻訳も参考情報として】
1. ChatGPT逆翻訳: {translations['chatgpt_reverse']}
2. Enhanced逆翻訳: {translations['enhanced_reverse']}
3. Gemini逆翻訳: {translations['gemini_reverse']}

【ユーザーの質問】
{question}

【分析観点】
- 正確性（元の意味の保持度）
- 自然さ（目標言語としての流暢さ）
- 文化的適切性
- 語彙選択の妥当性
- 文体の一貫性

回答:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800
            )

            result = response.choices[0].message.content.strip()

            return {
                "type": "comparison_analysis",
                "result": result
            }

        except Exception as e:
            error_msg = self._get_error_message(context, "comparison_analysis", str(e))
            return {
                "type": "error",
                "result": error_msg
            }

    def handle_general_expert_question_safe(self, question: str, context: Dict[str, Any], 
                                          analysis: Dict[str, Any], logger_adapter) -> Dict[str, Any]:
        """🎓 一般的な翻訳エキスパート質問を処理（安全版 - app_logger依存なし）"""

        display_lang = context.get('display_language', 'jp')
        response_language = self.response_lang_map.get(display_lang, "Japanese")

        # 🆕 デバッグ用ログ追加（SafeLoggerAdapter使用）
        logger_adapter.info(f"Interactive question language: display_lang={display_lang}, response_language={response_language}")

        prompt = f"""【LangPont Translation Expert AI】
You are a multilingual translation expert. Please answer the following question about the translation session.

【Translation Session Information】
Original text: {context['original_text']}
Language pair: {context['source_lang']} → {context['target_lang']}
Context information: {context.get('context_info', 'None')}
Message to partner: {context.get('partner_message', 'None')}

【Three Translation Results】
1. ChatGPT: {context['translations']['chatgpt']}
2. Enhanced: {context['translations']['enhanced']}
3. Gemini: {context['translations']['gemini']}

【Analysis Results】
{context.get('nuance_analysis', 'Analysis not performed')}

【User's Question】
{question}

【Response Requirements】
- Comprehensive answer as a translation expert
- Practical and constructive advice
- Information helpful for language learning
- Explanations including cultural considerations

IMPORTANT: Please provide your response in {response_language}.

Response:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=700
            )

            result = response.choices[0].message.content.strip()

            return {
                "type": "general_expert",
                "result": result
            }

        except Exception as e:
            error_msg = self._get_error_message(context, "question_processing", str(e))
            return {
                "type": "error",
                "result": error_msg
            }

    def get_complete_translation_context_safe(self, context: Dict[str, Any], 
                                            session_adapter) -> Dict[str, Any]:
        """🔍 セッションから完全な翻訳コンテキストを取得（安全版 - Flask依存なし）"""
        
        # SessionContextAdapterから翻訳コンテキストを取得
        session_data = session_adapter.get_translation_context()
        
        # 基本コンテキストと統合
        session_data.update(context)
        
        return session_data

    def process_question_safe(self, question: str, context: Dict[str, Any], 
                             input_validator, security_logger, session_adapter, logger_adapter) -> Dict[str, Any]:
        """🧠 翻訳エキスパートとして質問を包括的に処理（統合安全版）"""
        
        # 入力値検証（依存注入）
        is_valid, error_msg = input_validator.validate_text_input(
            question, max_length=1000, min_length=5, field_name="質問"
        )
        if not is_valid:
            security_logger(
                'INVALID_QUESTION_INPUT',
                f'Question validation failed: {error_msg}',
                'WARNING'
            )
            raise ValueError(error_msg)

        # セッション情報取得（既存safe版使用）
        full_context = self.get_complete_translation_context_safe(context, session_adapter)

        # 質問意図分析（既存安全メソッド使用）
        question_analysis = self._analyze_question_intent(question, full_context)

        # 質問タイプに応じた処理（全て既存安全メソッド使用）
        if question_analysis['type'] == 'translation_modification':
            return self._handle_translation_modification(question, full_context, question_analysis)
        elif question_analysis['type'] == 'analysis_inquiry':
            return self._handle_analysis_inquiry(question, full_context, question_analysis)
        elif question_analysis['type'] == 'linguistic_question':
            return self._handle_linguistic_question(question, full_context, question_analysis)
        elif question_analysis['type'] == 'context_variation':
            return self._handle_context_variation(question, full_context, question_analysis)
        elif question_analysis['type'] == 'comparison_analysis':
            return self.handle_comparison_analysis_safe(question, full_context, question_analysis, logger_adapter)
        else:
            return self.handle_general_expert_question_safe(question, full_context, question_analysis, logger_adapter)

    def process_question(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """🧠 翻訳エキスパートとして質問を包括的に処理（統合版 - Flask対応）"""
        # 必要な依存モジュールをimport
        from security.input_validation import EnhancedInputValidator
        from security.security_logger import log_security_event
        from translation.adapters import SessionContextAdapter, SafeLoggerAdapter
        
        # アダプターを初期化
        session_adapter = SessionContextAdapter()
        logger_adapter = SafeLoggerAdapter()
        
        # 統合安全版を呼び出し
        return self.process_question_safe(
            question, context, EnhancedInputValidator, log_security_event,
            session_adapter, logger_adapter
        )