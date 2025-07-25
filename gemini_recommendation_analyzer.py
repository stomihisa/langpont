#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎯 Task 2.9.1.5: Gemini推奨抽出・分析システム
=====================================================
目的: Gemini分析結果から推奨翻訳を自動抽出し、
     ユーザーの実選択との乖離を分析することで、
     真の個人化パターンを発見する

【重要】循環分析回避のため、推奨抽出は
       Gemini分析テキストから直接行う
"""

import re
import json
import logging
import os
import openai
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from collections import Counter, defaultdict

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiRecommendationAnalyzer:
    """Gemini分析結果から推奨翻訳を自動抽出・分析"""
    
    def __init__(self):
        """初期化"""
        # 🆕 修正: 推奨パターンマッチング用正規表現（包括的改善版 + マークダウン対応）
        self.recommendation_patterns = [
            # 🆕 マークダウン記法対応パターン
            r"\*\*(ChatGPT|Enhanced|Gemini)(?:の|)翻訳\*\*",
            r"最も.*?適切.*?翻訳.*?は.*?\*\*(ChatGPT|Enhanced|Gemini)(?:の|)翻訳\*\*",
            r"\*\*(ChatGPT|Enhanced|Gemini)(?:の|)翻訳\*\*.*?(?:が|は).*?(?:最も|最良|ベスト)",
            r"(ChatGPT|Enhanced|Gemini)(?:の|)翻訳.*?(?:が|は).*?(?:最も|最良|ベスト|一番).*?(?:適切|自然|良い|優秀)",
            r"(?:最も|最良|ベスト|一番).*?(?:適切|自然|良い|優秀).*?(?:は|が).*?(ChatGPT|Enhanced|Gemini)(?:の|)翻訳",
            r"推奨.*?(?:は|が).*?(ChatGPT|Enhanced|Gemini)(?:の|)翻訳",
            r"(ChatGPT|Enhanced|Gemini)(?:の|)翻訳.*?推奨",
            r"(ChatGPT|Enhanced|Gemini)(?:の|)翻訳.*?(?:を|が).*?(?:最も|最良|ベスト)",
            
            # 日本語パターン（大幅強化）
            r'([A-Za-z]+)(?:翻訳|訳)(?:が|は|を)?(?:最も|もっとも|一番|特に)?(?:適切|自然|良い|優秀|推奨|おすすめ|最適|最良|最善|ベスト)',
            r'([A-Za-z]+)(?:翻訳|訳)(?:が|は|を)?(?:最適|最も適切|もっとも適切|一番適切|最良|最善|ベスト)(?:な|の)?(?:選択|選択肢|オプション|方法|翻訳)?',
            r'(?:最も|もっとも|一番|特に|最も適切|最適|最良|最善|ベスト)(?:な|の)?(?:翻訳|訳|選択肢|選択|オプション)?(?:は|：|:)?\s*([A-Za-z]+)',
            r'([A-Za-z]+)(?:を|が)(?:推奨|おすすめ|選択|選ぶべき|選択すべき)',
            r'(?:推奨|おすすめ|ベスト|最適|最良|最善)(?:翻訳|訳|選択|の選択肢)?(?:は|：|:)?\s*([A-Za-z]+)',
            r'([A-Za-z]+)(?:が|の翻訳が|翻訳は)(?:より|もっと|最も)(?:適している|適切|自然|良い)',
            r'([A-Za-z]+)(?:翻訳|訳)(?:の方が|の翻訳の方が)(?:適切|自然|良い|優秀)',
            
            # 🆕 英語パターン（多言語対応強化版）
            r"(?:most|best).*?(?:appropriate|suitable|natural).*?translation.*?(?:is|would be).*?(chatgpt|enhanced|gemini)",
            r"(?:recommend|suggest).*?(chatgpt|enhanced|gemini).*?translation",
            r"(chatgpt|enhanced|gemini).*?translation.*?(?:is|would be).*?(?:most|best).*?(?:appropriate|suitable|natural)",
            r"\*\*(ChatGPT|Enhanced|Gemini).*?translation\*\*",
            r"the.*?(chatgpt|enhanced|gemini).*?translation.*?(?:is|would be).*?(?:recommended|preferred)",
            r"I.*?(?:recommend|suggest).*?the.*?(chatgpt|enhanced|gemini).*?translation",
            r'(?:recommend|suggest|prefer|choose|select)\s+(?:the\s+)?([A-Za-z]+)(?:\s+translation)?',
            r'([A-Za-z]+)(?:\s+translation)?\s+(?:is|would be|will be)\s+(?:the\s+)?(?:most\s+)?(?:recommended|best|appropriate|preferred|suitable|optimal)',
            r'(?:best|most appropriate|preferred|optimal|most suitable)\s+(?:translation|choice|option)?\s*(?:is|would be|:)?\s*(?:the\s+)?([A-Za-z]+)',
            r'(?:I would|I\'d|should|you should)\s+(?:recommend|suggest|choose|select|prefer)\s+(?:the\s+)?([A-Za-z]+)',
            r'([A-Za-z]+)(?:\s+translation)?\s+(?:is|would be)\s+(?:more|most)\s+(?:suitable|appropriate|accurate|natural)',
            r'(?:the\s+)?([A-Za-z]+)(?:\s+translation)?\s+(?:performs|works)\s+(?:better|best)',
            r'(?:go with|use|choose)\s+(?:the\s+)?([A-Za-z]+)(?:\s+translation)?',
            
            # 🆕 フランス語パターン
            r"(?:la plus|le plus).*?(?:appropriée|approprié|naturelle|naturel).*?traduction.*?(?:est|serait).*?(chatgpt|enhanced|gemini)",
            r"(?:recommande|suggère).*?traduction.*?(chatgpt|enhanced|gemini)",
            r"traduction.*?(chatgpt|enhanced|gemini).*?(?:est|serait).*?(?:la plus|le plus).*?(?:appropriée|approprié|naturelle|naturel)",
            r"la traduction.*?(chatgpt|enhanced|gemini).*?(?:est|serait).*?(?:recommandée|préférée)",
            
            # 🆕 スペイン語パターン
            r"(?:la más|el más).*?(?:apropiada|apropiado|natural).*?traducción.*?(?:es|sería).*?(chatgpt|enhanced|gemini)",
            r"(?:recomiendo|sugiero).*?traducción.*?(chatgpt|enhanced|gemini)",
            r"traducción.*?(chatgpt|enhanced|gemini).*?(?:es|sería).*?(?:la más|el más).*?(?:apropiada|apropiado|natural)",
            r"la traducción.*?(chatgpt|enhanced|gemini).*?(?:es|sería).*?(?:recomendada|preferida)",
            
            # スコアベースの推奨
            r'([A-Za-z]+)[：:]\s*(?:★|☆|◎|○|◯|✓|✔|👍|🌟|⭐)+\s*(?:\(|（)?(?:最|推奨|best)',
            # 順位ベースの推奨
            r'(?:1位|第1位|1st|first)(?:は|：|:)?\s*[「『]?([A-Za-z]+)',
        ]
        
        # 翻訳エンジン名のマッピング
        self.engine_mappings = {
            'chatgpt': ['chatgpt', 'gpt', 'openai', 'チャットジーピーティー'],
            'enhanced': ['enhanced', 'better', '強化', '改良', 'エンハンスド'],
            'gemini': ['gemini', 'google', 'ジェミニ', 'グーグル'],
            'original': ['original', 'source', '原文', 'オリジナル']
        }
        
        # 分析履歴保存
        self.analysis_history = []
        
        logger.info("Gemini推奨分析システム初期化完了")
    
    def extract_gemini_recommendation(self, gemini_analysis_text: str, language: str = 'ja') -> Optional[str]:
        """
        🚀 Phase A-7: extract_gemini_recommendation を LLM完全移行版に置き換え
        （パターンマッチング完全削除）
        
        Args:
            gemini_analysis_text: Gemini分析の生テキスト
            language: 分析言語 ('ja', 'en', 'fr', 'es')
            
        Returns:
            推奨されたエンジン名 (chatgpt/enhanced/gemini) または None
        """
        logger.info(f"🚀 Phase A-7: extract_gemini_recommendation LLM移行版呼び出し")
        
        # enhanced_recommendation_extraction を直接呼び出し
        recommendation, confidence, method = self.enhanced_recommendation_extraction(
            analysis_text=gemini_analysis_text,
            analysis_language=self._map_language_code(language)
        )
        
        logger.info(f"🚀 Phase A-7: LLM判定結果 - 推奨: {recommendation}, 信頼度: {confidence}, 手法: {method}")
        
        return recommendation
    
    def _map_language_code(self, language_code: str) -> str:
        """
        言語コードをanalysis_languageにマッピング
        
        Args:
            language_code: 言語コード ('ja', 'en', 'fr', 'es')
            
        Returns:
            分析言語名 ('Japanese', 'English', 'French', 'Spanish')
        """
        language_map = {
            'ja': 'Japanese',
            'en': 'English',
            'fr': 'French',
            'es': 'Spanish'
        }
        return language_map.get(language_code, 'Japanese')
    
    def get_analysis_tail(self, text: str, lines: int = 10) -> str:
        """
        🤖 Phase A-4: 分析結果の最後N行を抽出（コスト効率化）
        
        Args:
            text: Gemini分析テキスト
            lines: 抽出する行数（デフォルト: 10行）
            
        Returns:
            最後N行のテキスト
        """
        if not text:
            return ""
        
        # 改行で分割して最後のN行を取得
        text_lines = text.strip().split('\n')
        tail_lines = text_lines[-lines:] if len(text_lines) > lines else text_lines
        
        result = '\n'.join(tail_lines)
        
        logger.info(f"🤖 Phase A-4: テキスト最適化完了 - 元: {len(text_lines)}行 → 抽出: {len(tail_lines)}行")
        logger.debug(f"🤖 抽出されたテキスト: {result[:100]}...")
        
        return result
    
    def extract_recommendation_with_chatgpt(self, analysis_tail: str, analysis_language: str = "Japanese") -> Tuple[Optional[str], float, str]:
        """
        🚀 Phase A-6: ChatGPT推奨判定システム（プロンプト最適化版）
        
        Args:
            analysis_tail: Gemini分析の最後の部分
            analysis_language: 分析言語 ("Japanese", "English", "French", "Spanish")
            
        Returns:
            (recommendation, confidence, method) のタプル
        """
        logger.info(f"🚀 Phase A-6: ChatGPT推奨判定開始 (言語: {analysis_language})")
        
        # 🚀 Phase A-9.2: 言語別文脈クリーニング
        analysis_tail_clean = self._clean_negative_context(analysis_tail, analysis_language)
        logger.info(f"🚀 Phase A-9.2: {analysis_language}文脈クリーニング完了")
        
        # 🚀 Phase A-6: 改良された超精密プロンプト
        prompts = {
            "Japanese": f"""【翻訳推奨分析タスク】

分析対象テキスト:
{analysis_tail_clean}

【判定指示】
上記のGemini分析から「最も推奨されている翻訳エンジン」を1つ特定してください。

【重要ルール】
✅ 「推奨」「最適」「ベスト」「最も適切」等の肯定的表現を重視
✅ ChatGPT、Enhanced、Geminiの中から1つ選択
✅ 明確な推奨がない場合は「none」
❌ 否定的コメントは無視
❌ 解説不要、推奨エンジン名のみ回答

【回答形式】
chatgpt / enhanced / gemini / none のいずれか1語のみ

回答:""",

            "English": f"""【Translation Recommendation Analysis Task】

Analysis Text:
{analysis_tail_clean}

【Detection Instructions】
Identify the ONE most recommended translation engine from the above Gemini analysis.

【Critical Rules】
✅ Focus on positive expressions: "recommended", "best", "most appropriate", "optimal"
✅ Choose ONE from: ChatGPT, Enhanced, Gemini
✅ If no clear recommendation exists, answer "none"
❌ Ignore negative comments
❌ No explanation needed, engine name only

【Response Format】
Only one word: chatgpt / enhanced / gemini / none

Answer:""",

            "French": f"""【Tâche d'Analyse de Recommandation de Traduction】

Texte d'Analyse:
{analysis_tail_clean}

【Instructions de Détection】
Identifiez le moteur de traduction LE PLUS recommandé dans l'analyse Gemini ci-dessus.

【Règles Critiques】
✅ Concentrez-vous sur les expressions positives: "recommandé", "meilleur", "plus approprié", "optimal"
✅ Choisissez UN parmi: ChatGPT, Enhanced, Gemini
✅ Si aucune recommandation claire, répondez "none"
❌ Ignorez les commentaires négatifs
❌ Pas d'explication, nom du moteur uniquement

【Format de Réponse】
Un seul mot: chatgpt / enhanced / gemini / none

Réponse:""",

            "Spanish": f"""【Tarea de Análisis de Recomendación de Traducción】

Texto de Análisis:
{analysis_tail_clean}

【Instrucciones de Detección】
Identifique el motor de traducción MÁS recomendado en el análisis Gemini anterior.

【Reglas Críticas】
✅ Enfóquese en expresiones positivas: "recomendado", "mejor", "más apropiado", "óptimo"
✅ Elija UNO de: ChatGPT, Enhanced, Gemini
✅ Si no hay recomendación clara, responda "none"
❌ Ignore comentarios negativos
❌ Sin explicación, solo nombre del motor

【Formato de Respuesta】
Una sola palabra: chatgpt / enhanced / gemini / none

Respuesta:"""
        }
        
        prompt = prompts.get(analysis_language, prompts["Japanese"])
        
        logger.info(f"🚀 Phase A-6: === ChatGPT API呼び出し開始 ===")
        
        try:
            # 🚀 Phase A-6: 環境変数確認
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.error("🚀 Phase A-6: OPENAI_API_KEY が設定されていません")
                return None, 0.0, "api_key_missing"
            
            logger.info(f"🚀 Phase A-6: APIキー確認完了 (長さ: {len(api_key)}文字)")
            
            # 🚀 Phase A-8: OpenAI v1.x 対応のクライアント設定
            client = openai.OpenAI(api_key=api_key)
            
            # 🚀 Phase A-8: 最適化されたAPI呼び出しパラメータ
            api_params = {
                "model": "gpt-3.5-turbo",
                "max_tokens": 5,  # 🚀 さらに短縮（1語のみ）
                "temperature": 0.0,  # 🚀 完全決定論的
                "top_p": 1.0,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            }
            logger.info(f"🚀 Phase A-8: API呼び出しパラメータ: {api_params}")
            
            # 🚀 Phase A-8: 改良されたシステムプロンプト
            system_prompt = "You are a precise translation recommendation detector. Analyze the text and respond with exactly one word: chatgpt, enhanced, gemini, or none. No explanation, no punctuation, just the single word."
            
            logger.info(f"🚀 Phase A-8: ChatGPT API呼び出し実行...")
            
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                **api_params
            )
            
            logger.info(f"🚀 Phase A-6: API呼び出し成功")
            
            # 🚀 Phase A-8: レスポンス解析
            if response and hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    raw_answer = choice.message.content.strip().lower()
                    logger.info(f"🚀 Phase A-8: ChatGPT生回答: '{raw_answer}'")
                    
                    # 🚀 Phase A-8: 厳密な回答検証
                    normalized_answer = self._normalize_chatgpt_response(raw_answer)
                    logger.info(f"🚀 Phase A-8: 正規化後: '{normalized_answer}'")
                    
                    if normalized_answer in ['chatgpt', 'enhanced', 'gemini']:
                        confidence = 0.98  # 🚀 Phase A-8 高信頼度
                        logger.info(f"✅ Phase A-8: ChatGPT判定成功 - 推奨: {normalized_answer} (信頼度: {confidence})")
                        return normalized_answer, confidence, "llm_chatgpt_a8"
                    elif normalized_answer == 'none':
                        logger.info(f"🚀 Phase A-8: ChatGPT判定 - 明確な推奨なし")
                        return None, 0.7, "llm_chatgpt_none_a8"
                    else:
                        logger.warning(f"🚀 Phase A-8: ChatGPT回答が予期しない形式: '{raw_answer}' → '{normalized_answer}'")
                        return None, 0.0, "llm_chatgpt_invalid_a8"
                else:
                    logger.error("🚀 Phase A-8: レスポンス構造エラー")
                    return None, 0.0, "llm_response_malformed_a8"
            else:
                logger.error("🚀 Phase A-8: 空のレスポンス")
                return None, 0.0, "llm_response_empty_a8"
                
        except openai.RateLimitError as e:
            logger.error(f"🚀 Phase A-8: OpenAI レート制限エラー: {str(e)}")
            return None, 0.0, "llm_rate_limit_a8"
        except openai.AuthenticationError as e:
            logger.error(f"🚀 Phase A-8: OpenAI 認証エラー: {str(e)}")
            return None, 0.0, "llm_auth_error_a8"
        except openai.APIError as e:
            logger.error(f"🚀 Phase A-8: OpenAI APIエラー: {str(e)}")
            return None, 0.0, "llm_api_error_a8"
        except Exception as e:
            logger.error(f"🚀 Phase A-8: 予期しないエラー: {str(e)}")
            import traceback
            logger.error(f"🚀 Phase A-8: スタックトレース: {traceback.format_exc()}")
            return None, 0.0, "llm_unexpected_error_a8"
        
        finally:
            logger.info(f"🚀 Phase A-8: === ChatGPT API呼び出し終了 ===")
    
    def _clean_negative_context(self, text: str, analysis_language: str = "Japanese") -> str:
        """
        🚀 Phase A-9.2: 否定的文脈の除去（完全多言語対応版）
        
        Args:
            text: 元のGemini分析テキスト
            analysis_language: 分析言語 ("Japanese", "English", "French", "Spanish")
            
        Returns:
            否定的文脈を除去したテキスト（言語別推奨文保護）
        """
        if not text:
            return text
        
        logger.info(f"🚀 Phase A-9.2: 完全多言語対応クリーニング開始 (言語: {analysis_language})")
        
        # 🚀 Phase A-9.2: 言語別推奨文保護キーワード
        recommendation_keywords = {
            "Japanese": ['最も自然で適切', '最も適切', '最も自然', '推奨', 'おすすめ', 'ベスト', '最良', '最善', 
                        '一番良い', '一番適切', '最適', '優れている', '素晴らしい'],
            "English": ['most natural', 'most appropriate', 'most suitable', 'recommend', 'best choice', 'optimal', 
                       'preferred', 'ideal', 'I recommend', 'I suggest', 'should choose', 'should use', 'excellent'],
            "French": ['le plus naturel', 'le plus approprié', 'recommande', 'meilleur choix', 'optimal', 'idéal', 
                      'préféré', 'je recommande', 'je suggère', 'devrait choisir', 'excellent'],
            "Spanish": ['más natural', 'más apropiado', 'recomiendo', 'mejor opción', 'óptimo', 'ideal', 
                       'preferido', 'sugiero', 'debería elegir', 'excelente']
        }
        
        # 🚀 Phase A-9.2: 言語別否定的パターン
        negative_patterns_by_language = {
            "Japanese": [
                r'.*(?:ChatGPT|Enhanced|Gemini).*(?:は|が).*?(?:劣る|不足|弱い|足りない|問題がある|適切ではない).*',
                r'.*(?:ChatGPT|Enhanced|Gemini).*(?:では|だと).*?(?:不適切|不自然|違和感がある|おかしい).*',
                r'.*(?:批判|否定|欠点|弱点|問題点|課題).*?(?:ChatGPT|Enhanced|Gemini).*',
                r'.*(?:しかし|ただし|一方で|ただ).*?(?:ChatGPT|Enhanced|Gemini).*?(?:欠点|問題|課題|不十分).*',
                r'.*(?:ChatGPT|Enhanced|Gemini).*?(?:フォーマルな印象|堅い印象|硬い印象|冷たい印象).*',
            ],
            "English": [
                r'.*(?:ChatGPT|Enhanced|Gemini).*(?:is|are|has|have).*?(?:poor|inadequate|weak|problematic|unsuitable|inferior).*',
                r'.*(?:ChatGPT|Enhanced|Gemini).*(?:translation|version).*?(?:is|are).*?(?:unnatural|awkward|strange|odd).*',
                r'.*(?:criticism|critique|weakness|flaw|problem|issue).*?(?:ChatGPT|Enhanced|Gemini).*',
                r'.*(?:however|but|although|though).*?(?:ChatGPT|Enhanced|Gemini).*?(?:lacks|fails|problems|issues).*',
                r'.*(?:ChatGPT|Enhanced|Gemini).*?(?:formal tone|stiff impression|cold feeling).*',
            ],
            "French": [
                r'.*(?:ChatGPT|Enhanced|Gemini).*(?:est|sont|a|ont).*?(?:pauvre|inadéquat|faible|problématique|inapproprié).*',
                r'.*(?:ChatGPT|Enhanced|Gemini).*(?:traduction|version).*?(?:est|sont).*?(?:peu naturel|maladroit|étrange|bizarre).*',
                r'.*(?:critique|faiblesse|défaut|problème).*?(?:ChatGPT|Enhanced|Gemini).*',
                r'.*(?:cependant|mais|bien que|quoique).*?(?:ChatGPT|Enhanced|Gemini).*?(?:manque|échoue|problèmes).*',
            ],
            "Spanish": [
                r'.*(?:ChatGPT|Enhanced|Gemini).*(?:es|son|tiene|tienen).*?(?:pobre|inadecuado|débil|problemático|inapropiado).*',
                r'.*(?:ChatGPT|Enhanced|Gemini).*(?:traducción|versión).*?(?:es|son).*?(?:poco natural|torpe|extraño|raro).*',
                r'.*(?:crítica|debilidad|defecto|problema).*?(?:ChatGPT|Enhanced|Gemini).*',
                r'.*(?:sin embargo|pero|aunque).*?(?:ChatGPT|Enhanced|Gemini).*?(?:carece|falla|problemas).*',
            ]
        }
        
        # 🚀 Phase A-9.2: 現在の言語に対応するキーワードとパターンを取得
        current_keywords = recommendation_keywords.get(analysis_language, recommendation_keywords["Japanese"])
        negative_patterns = negative_patterns_by_language.get(analysis_language, negative_patterns_by_language["Japanese"])
        
        lines = text.split('\n')
        filtered_lines = []
        
        for line in lines:
            is_negative = False
            
            # 🚀 Phase A-9.2: 言語別推奨文保護
            is_recommendation = any(keyword.lower() in line.lower() for keyword in current_keywords)
            
            if is_recommendation:
                # 推奨文は保護（削除しない）
                logger.info(f"🚀 Phase A-9.2: {analysis_language}推奨文保護: {line[:50]}...")
                filtered_lines.append(line)
                continue
            
            # 推奨文以外で言語別否定的パターンをチェック
            for pattern in negative_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    logger.info(f"🚀 Phase A-9.2: {analysis_language}否定的文除去: {line[:50]}...")
                    is_negative = True
                    break
            
            if not is_negative:
                filtered_lines.append(line)
        
        result = '\n'.join(filtered_lines)
        
        logger.info(f"🚀 Phase A-9.2: {analysis_language}クリーニング完了 - 元: {len(lines)}行 → 後: {len(filtered_lines)}行")
        
        return result
    
    def _normalize_chatgpt_response(self, raw_response: str) -> str:
        """ChatGPTレスポンスの正規化"""
        # 小文字化、空白除去
        clean_response = raw_response.strip().lower()
        
        # 余分な文字や句読点を除去
        clean_response = re.sub(r'[^\w]', '', clean_response)
        
        # 部分マッチング
        if 'chatgpt' in clean_response:
            return 'chatgpt'
        elif 'enhanced' in clean_response:
            return 'enhanced'
        elif 'gemini' in clean_response:
            return 'gemini'
        elif 'none' in clean_response or 'なし' in clean_response or 'unclear' in clean_response:
            return 'none'
        else:
            return 'unknown'
    
    def validate_openai_api_key(self) -> Dict[str, Any]:
        """
        🚨 Phase A-8: OpenAI APIキー検証システム（v1.x対応版）
        
        Returns:
            APIキー検証結果の詳細辞書
        """
        logger.info("🚨 Phase A-8: OpenAI APIキー検証開始（v1.x対応）")
        
        validation_result = {
            "is_valid": False,
            "api_key_exists": False,
            "api_key_format_valid": False,
            "api_connection_test": False,
            "error_details": [],
            "recommendations": []
        }
        
        try:
            # 1. 環境変数の存在確認
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                validation_result["error_details"].append("OPENAI_API_KEY環境変数が設定されていません")
                validation_result["recommendations"].append("環境変数 OPENAI_API_KEY を設定してください")
                return validation_result
            
            validation_result["api_key_exists"] = True
            logger.info(f"🚨 Phase A-8: APIキー存在確認 - OK (長さ: {len(api_key)}文字)")
            
            # 2. APIキー形式の検証
            if not api_key.startswith("sk-"):
                validation_result["error_details"].append("APIキーが 'sk-' で始まっていません")
                validation_result["recommendations"].append("正しいOpenAI APIキーを設定してください")
                return validation_result
            
            if len(api_key) < 40:
                validation_result["error_details"].append(f"APIキーが短すぎます (長さ: {len(api_key)})")
                validation_result["recommendations"].append("完全なAPIキーを設定してください")
                return validation_result
            
            validation_result["api_key_format_valid"] = True
            logger.info("🚨 Phase A-8: APIキー形式検証 - OK")
            
            # 3. 🚀 Phase A-8: OpenAI v1.x 対応のAPI接続テスト
            import openai
            
            # 🚀 Phase A-8: 新しいクライアント初期化方式
            client = openai.OpenAI(api_key=api_key)
            
            # 非常に簡単なテストリクエスト
            test_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
                temperature=0
            )
            
            if test_response and hasattr(test_response, 'choices') and test_response.choices:
                validation_result["api_connection_test"] = True
                validation_result["is_valid"] = True
                logger.info("🚨 Phase A-8: API接続テスト - OK (v1.x)")
                validation_result["recommendations"].append("APIキーは正常に動作しています（v1.x対応）")
            else:
                validation_result["error_details"].append("APIレスポンスが予期しない形式です")
                
        except openai.AuthenticationError as e:
            validation_result["error_details"].append(f"認証エラー: {str(e)}")
            validation_result["recommendations"].append("APIキーが無効です。正しいキーを設定してください")
            logger.error(f"🚨 Phase A-8: 認証エラー - {str(e)}")
            
        except openai.RateLimitError as e:
            validation_result["api_connection_test"] = True  # レート制限=キーは有効
            validation_result["is_valid"] = True
            validation_result["error_details"].append(f"レート制限: {str(e)}")
            validation_result["recommendations"].append("APIキーは有効ですが、レート制限に達しています")
            logger.warning(f"🚨 Phase A-8: レート制限 - {str(e)}")
            
        except openai.APIError as e:
            validation_result["error_details"].append(f"OpenAI APIエラー: {str(e)}")
            validation_result["recommendations"].append("OpenAI APIサービスに問題がある可能性があります")
            logger.error(f"🚨 Phase A-8: APIエラー - {str(e)}")
            
        except Exception as e:
            validation_result["error_details"].append(f"予期しないエラー: {str(e)}")
            validation_result["recommendations"].append("システム設定を確認してください")
            logger.error(f"🚨 Phase A-8: 予期しないエラー - {str(e)}")
        
        logger.info(f"🚨 Phase A-8: APIキー検証完了 - 有効: {validation_result['is_valid']}")
        return validation_result
    
    def enhanced_recommendation_extraction(self, analysis_text: str, analysis_language: str = "Japanese") -> Tuple[Optional[str], float, str]:
        """
        🚀 Phase A-6: LLM完全移行システム（パターンマッチング完全廃止）
        
        Args:
            analysis_text: Gemini分析テキスト全文
            analysis_language: 分析言語
            
        Returns:
            (recommendation, confidence, method) のタプル
        """
        logger.info(f"🚀 Phase A-6: LLM完全移行システム開始 - パターンマッチング廃止")
        
        try:
            # 🚀 Phase A-6: APIキー検証を実行（失敗時は即座に終了）
            api_validation = self.validate_openai_api_key()
            if not api_validation["is_valid"]:
                logger.error("🚨 Phase A-6: OpenAI APIキーが無効 - 処理を中断")
                for error in api_validation["error_details"]:
                    logger.error(f"🚨 Phase A-6: {error}")
                for rec in api_validation["recommendations"]:
                    logger.info(f"🚨 Phase A-6: 推奨事項: {rec}")
                
                # 🚀 パターンマッチング完全廃止 - API失敗時は素直に失敗
                logger.warning("🚀 Phase A-6: APIキー無効のため処理終了（フォールバック廃止）")
                return None, 0.0, "api_key_invalid_no_fallback"
            
            logger.info("✅ Phase A-6: OpenAI APIキー検証成功 - LLM判定のみ実行")
            
            # 1. テキスト最適化（最後10行抽出）
            analysis_tail = self.get_analysis_tail(analysis_text, 10)
            
            if not analysis_tail:
                logger.warning("🚀 Phase A-6: 分析テキストが空です")
                return None, 0.0, "empty_text"
            
            # 2. ChatGPT判定のみ実行（Phase A-6完全移行版）
            recommendation, confidence, method = self.extract_recommendation_with_chatgpt(analysis_tail, analysis_language)
            
            # 🚀 Phase A-6: 結果をそのまま返す（フォールバック一切なし）
            if recommendation and method.startswith("llm_chatgpt"):
                logger.info(f"✅ Phase A-6: ChatGPT判定成功 - 推奨: {recommendation}, 信頼度: {confidence}")
                return recommendation, confidence, method
            elif method.startswith("llm_chatgpt_none"):
                logger.info(f"✅ Phase A-6: ChatGPT判定完了 - 明確な推奨なし")
                return None, 0.5, method
            else:
                logger.warning(f"❌ Phase A-6: ChatGPT判定失敗 - 理由: {method}")
                return None, 0.0, method
                
        except Exception as e:
            logger.error(f"❌ Phase A-6: LLM完全移行システムエラー: {str(e)}")
            # 🚀 Phase A-6: 緊急時もフォールバック廃止
            return None, 0.0, "llm_system_error"
    
    def _normalize_engine_name(self, raw_name: str) -> Optional[str]:
        """エンジン名を正規化"""
        raw_lower = raw_name.lower().strip()
        
        for engine, aliases in self.engine_mappings.items():
            for alias in aliases:
                if alias in raw_lower or raw_lower in alias:
                    return engine
        
        return None
    
    def _extract_by_score_analysis(self, text: str) -> Optional[str]:
        """スコアや評価表現から推奨を推定"""
        # スコアパターン（例: "ChatGPT: 8/10", "Enhanced: ★★★★☆"）
        score_patterns = [
            r'(\w+)[：:]\s*(\d+)\s*[/／]\s*\d+',  # 数値スコア
            r'(\w+)[：:]\s*(★+|☆+|◎+|○+|◯+)',  # 記号スコア
        ]
        
        scores = {}
        for pattern in score_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                engine_raw = match.group(1)
                engine = self._normalize_engine_name(engine_raw)
                if engine:
                    # スコアの簡易評価
                    score_text = match.group(2)
                    if score_text.isdigit():
                        scores[engine] = int(score_text)
                    else:
                        # 記号の数をスコアとして使用
                        scores[engine] = len(score_text)
        
        # 最高スコアのエンジンを返す
        if scores:
            return max(scores, key=scores.get)
        
        return None
    
    def analyze_recommendation_vs_choice(self, 
                                       recommended: str, 
                                       actual_choice: str,
                                       session_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        推奨vs実選択の乖離分析
        
        Args:
            recommended: Gemini推奨のエンジン
            actual_choice: ユーザーの実際の選択
            session_context: セッションコンテキスト（オプション）
            
        Returns:
            乖離分析結果
        """
        analysis = {
            'recommended': recommended,
            'actual_choice': actual_choice,
            'followed_recommendation': recommended == actual_choice,
            'divergence_type': None,
            'potential_reasons': [],
            'confidence': 0.0,
            'timestamp': datetime.now().isoformat()
        }
        
        if recommended == actual_choice:
            analysis['divergence_type'] = 'aligned'
            analysis['confidence'] = 1.0
        else:
            analysis['divergence_type'] = 'diverged'
            
            # 乖離理由の推定
            if session_context:
                # コンテキストベースの理由推定
                if session_context.get('text_length', 0) > 500:
                    analysis['potential_reasons'].append('long_text_preference')
                    
                if session_context.get('has_technical_terms'):
                    analysis['potential_reasons'].append('technical_accuracy_priority')
                    
                if session_context.get('previous_choices', {}).get(actual_choice, 0) > 2:
                    analysis['potential_reasons'].append('engine_familiarity')
            
            # 一般的な乖離パターン
            if recommended == 'gemini' and actual_choice == 'chatgpt':
                analysis['potential_reasons'].append('prefer_traditional_style')
            elif recommended == 'chatgpt' and actual_choice == 'gemini':
                analysis['potential_reasons'].append('prefer_modern_style')
            elif actual_choice == 'enhanced':
                analysis['potential_reasons'].append('prefer_contextual_enhancement')
        
        # 分析履歴に追加
        self.analysis_history.append(analysis)
        
        return analysis
    
    def detect_preference_patterns(self, user_data: List[Dict]) -> Dict[str, Any]:
        """
        個人化パターンの検出（循環分析を回避）
        
        Args:
            user_data: ユーザーの選択履歴データ
            
        Returns:
            検出された選好パターン
        """
        patterns = {
            'engine_preferences': Counter(),
            'divergence_patterns': Counter(),
            'context_based_choices': defaultdict(Counter),
            'temporal_trends': [],
            'personalization_insights': []
        }
        
        # エンジン選好の集計
        for data in user_data:
            choice = data.get('actual_choice')
            if choice:
                patterns['engine_preferences'][choice] += 1
            
            # 乖離パターンの集計
            if data.get('followed_recommendation') is False:
                reasons = data.get('potential_reasons', [])
                for reason in reasons:
                    patterns['divergence_patterns'][reason] += 1
            
            # コンテキスト別選択の集計
            context = data.get('context_type', 'general')
            if choice:
                patterns['context_based_choices'][context][choice] += 1
        
        # 個人化インサイトの生成
        total_choices = sum(patterns['engine_preferences'].values())
        if total_choices > 0:
            # 最頻使用エンジン
            top_engine = patterns['engine_preferences'].most_common(1)[0]
            preference_rate = (top_engine[1] / total_choices) * 100
            
            if preference_rate > 60:
                patterns['personalization_insights'].append(
                    f"Strong preference for {top_engine[0]} ({preference_rate:.1f}%)"
                )
            
            # 推奨への従順度
            aligned_count = sum(1 for d in user_data if d.get('followed_recommendation'))
            alignment_rate = (aligned_count / len(user_data)) * 100 if user_data else 0
            
            if alignment_rate < 40:
                patterns['personalization_insights'].append(
                    f"Independent decision maker (follows recommendations only {alignment_rate:.1f}%)"
                )
            elif alignment_rate > 80:
                patterns['personalization_insights'].append(
                    f"Trusts AI recommendations ({alignment_rate:.1f}% alignment)"
                )
        
        # 時系列トレンドの検出
        if len(user_data) >= 5:
            recent_choices = [d.get('actual_choice') for d in user_data[-5:]]
            recent_counter = Counter(recent_choices)
            if len(recent_counter) == 1:
                patterns['temporal_trends'].append(
                    f"Recent consistency: exclusively using {recent_choices[0]}"
                )
        
        return patterns
    
    def generate_personalization_report(self, user_id: str) -> Dict[str, Any]:
        """
        ユーザー別個人化レポートの生成
        
        Args:
            user_id: ユーザーID
            
        Returns:
            個人化分析レポート
        """
        # 分析履歴からユーザーデータを抽出
        user_analyses = [a for a in self.analysis_history if a.get('user_id') == user_id]
        
        if not user_analyses:
            return {'error': 'No data available for user'}
        
        # パターン検出
        patterns = self.detect_preference_patterns(user_analyses)
        
        report = {
            'user_id': user_id,
            'total_translations': len(user_analyses),
            'preference_patterns': patterns,
            'recommendation_alignment': {
                'followed': sum(1 for a in user_analyses if a.get('followed_recommendation')),
                'diverged': sum(1 for a in user_analyses if not a.get('followed_recommendation'))
            },
            'personalization_ready': len(user_analyses) >= 10,  # 10回以上で個人化可能
            'generated_at': datetime.now().isoformat()
        }
        
        return report


# 🚀 Phase A-8 総合テスト関数
def test_phase_a8_openai_v1_system():
    """🚀 Phase A-8: OpenAI v1.x完全対応システムの総合テスト"""
    print("🚀 Phase A-8: OpenAI v1.x完全対応システム - 総合テスト実行")
    print("=" * 80)
    
    analyzer = GeminiRecommendationAnalyzer()
    
    # 1. APIキー検証テスト（Phase A-8版）
    print("🔍 Phase A-8: Step 1 - OpenAI APIキー検証テスト（v1.x対応）")
    print("-" * 50)
    
    api_validation = analyzer.validate_openai_api_key()
    
    print(f"   APIキー存在: {api_validation['api_key_exists']}")
    print(f"   APIキー形式: {api_validation['api_key_format_valid']}")
    print(f"   API接続テスト: {api_validation['api_connection_test']}")
    print(f"   総合判定: {api_validation['is_valid']}")
    
    if api_validation['error_details']:
        print("   🚨 エラー詳細:")
        for error in api_validation['error_details']:
            print(f"     - {error}")
    
    if api_validation['recommendations']:
        print("   💡 推奨事項:")
        for rec in api_validation['recommendations']:
            print(f"     - {rec}")
    
    # 2. OpenAI v1.x対応推奨抽出システムテスト
    print(f"\n🧪 Phase A-8: Step 2 - OpenAI v1.x対応推奨抽出システムテスト")
    print("-" * 50)
    
    test_cases = [
        {
            "name": "Enhanced Translation推奨ケース（Phase A-6最適化）",
            "text": "分析結果: Enhanced Translationが最も適切で自然な翻訳を提供しています。コンテキストを十分に考慮した優秀な翻訳です。Enhanced Translationを強く推奨します。",
            "expected": "enhanced"
        },
        {
            "name": "Gemini Translation推奨ケース",
            "text": "比較分析の結果、Gemini Translationが最も創造性に富み、自然な表現を使用しています。文脈理解度も高く、Gemini Translationを推奨します。",
            "expected": "gemini"
        },
        {
            "name": "ChatGPT Translation推奨ケース",
            "text": "総合的な評価として、ChatGPT Translationが正確性と一貫性の面で優れています。基本翻訳として最も信頼できるため、ChatGPT Translationを推奨します。",
            "expected": "chatgpt"
        },
        {
            "name": "明確な推奨なしケース",
            "text": "3つの翻訳それぞれに長所と短所があります。どの翻訳も一定の品質を満たしており、明確な優劣は判断できません。利用シーンに応じて選択してください。",
            "expected": "none"
        },
        {
            "name": "複雑混在ケース（Enhanced推奨）",
            "text": """
            【翻訳比較結果】
            
            1. ChatGPT Translation: 標準的で正確な翻訳です。
            2. Enhanced Translation: より自然で流暢な翻訳で、コンテキストをよく理解しています。
            3. Gemini Translation: 創造的だが、やや過度な表現があります。
            
            【結論】Enhanced Translationが最もバランスが取れており、推奨します。
            """,
            "expected": "enhanced"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n  {i}. {case['name']}")
        print(f"     入力: {case['text'][:100].replace(chr(10), ' ')}...")
        print(f"     期待: {case['expected']}")
        
        # 🚀 Phase A-6 LLM完全移行システムでテスト
        recommendation, confidence, method = analyzer.enhanced_recommendation_extraction(case['text'], 'Japanese')
        
        print(f"     結果: {recommendation}")
        print(f"     信頼度: {confidence}")
        print(f"     手法: {method}")
        
        # 🚀 Phase A-8 成功判定（OpenAI v1.x対応）
        if method.startswith("llm_chatgpt_a8"):
            # OpenAI v1.x成功時
            success = recommendation == case['expected']
            print(f"     評価: {'✅ 成功 (OpenAI v1.x対応)' if success else '❌ 失敗 (LLM判定ミス)'}")
        elif method.startswith("llm_chatgpt_none_a8"):
            # OpenAI v1.x noneの場合
            success = case['expected'] == 'none'
            print(f"     評価: {'✅ 成功 (OpenAI v1.x none判定)' if success else '❌ 失敗 (none判定ミス)'}")
        elif method.startswith("api_key_invalid_no_fallback"):
            # APIキー無効（フォールバック廃止）
            print(f"     評価: ⚠️ APIキー無効 (フォールバック廃止により処理終了)")
        else:
            # その他のエラー
            print(f"     評価: ❌ エラー (method: {method})")
    
    # 3. APIキー無効時の動作テスト
    print(f"\n🔐 Phase A-6: Step 3 - APIキー無効時動作テスト")
    print("-" * 50)
    
    # 一時的にAPIキーを無効化してテスト
    original_api_key = os.getenv("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "invalid_key"
    
    try:
        test_text = "Enhanced Translationを推奨します。"
        recommendation, confidence, method = analyzer.enhanced_recommendation_extraction(test_text, 'Japanese')
        
        print(f"   APIキー無効時の結果: {recommendation}")
        print(f"   信頼度: {confidence}")
        print(f"   手法: {method}")
        
        if method == "api_key_invalid_no_fallback":
            print("   評価: ✅ 正常（フォールバック廃止により適切に失敗）")
        else:
            print("   評価: ❌ 異常（予期しない動作）")
            
    finally:
        # APIキーを復元
        if original_api_key:
            os.environ["OPENAI_API_KEY"] = original_api_key
        else:
            os.environ.pop("OPENAI_API_KEY", None)
    
    # 4. パフォーマンステスト
    print(f"\n⚡ Phase A-6: Step 4 - パフォーマンステスト")
    print("-" * 50)
    
    long_analysis_text = "\n".join([
        f"Line {i}: この行は長いGemini分析テキストのサンプルです。" 
        for i in range(1, 30)
    ]) + "\n\n【最終結論】Enhanced Translationが最も優秀で、推奨します。コンテキスト理解が優れています。"
    
    original_length = len(long_analysis_text)
    tail_text = analyzer.get_analysis_tail(long_analysis_text, 10)
    optimized_length = len(tail_text)
    
    print(f"   元テキスト長: {original_length} 文字")
    print(f"   最適化後長: {optimized_length} 文字")
    print(f"   コスト削減率: {((original_length - optimized_length) / original_length * 100):.1f}%")
    
    # 最適化後のテキストで推奨抽出テスト
    import time
    start_time = time.time()
    recommendation, confidence, method = analyzer.enhanced_recommendation_extraction(long_analysis_text, 'Japanese')
    processing_time = time.time() - start_time
    
    print(f"   最適化テキストでの推奨: {recommendation}")
    print(f"   信頼度: {confidence}")
    print(f"   処理時間: {processing_time:.3f}秒")
    
    # 5. システム統計
    print(f"\n📊 Phase A-6: Step 5 - システム統計")
    print("-" * 50)
    
    print("   環境変数確認:")
    openai_key_exists = bool(os.getenv("OPENAI_API_KEY"))
    print(f"     - OPENAI_API_KEY: {'設定済み' if openai_key_exists else '未設定'}")
    
    if openai_key_exists:
        api_key = os.getenv("OPENAI_API_KEY")
        print(f"     - キー長: {len(api_key)} 文字")
        print(f"     - 形式チェック: {'OK' if api_key.startswith('sk-') else 'NG'}")
    
    print(f"\n   Phase A-8 システム特徴:")
    print(f"     - パターンマッチング: 完全廃止 ✅")
    print(f"     - LLM依存度: 100%")
    print(f"     - フォールバック: 廃止")
    print(f"     - OpenAI v1.x対応: 完全実装 ✅")
    print(f"     - APIキー検証: v1.x対応強化済み")
    print(f"     - プロンプト最適化: 実装済み")
    
    print("\n✅ Phase A-8 OpenAI v1.x完全対応テスト完了")
    print("🚀 OpenAI v1.x互換性により、システム安定性向上を期待")
    print("=" * 80)

# Phase A-4 テスト関数（互換性のため保持）
def test_phase_a4_system():
    """🤖 Phase A-4: LLMベース推奨抽出システムのテスト"""
    print("🤖 Phase A-4: LLMベース推奨抽出システム - テスト実行")
    print("=" * 60)
    
    analyzer = GeminiRecommendationAnalyzer()
    
    # テストケース: ユーザー指定のケース
    test_cases = [
        {
            "name": "Enhanced Translation推奨ケース",
            "text": "2. Enhanced Translation の「la volonté d'Apple de ne pas prendre de retard」は、Appleの戦略的な意図を的確に表現しています。Enhanced Translationが最も適切です。",
            "expected": "enhanced"
        },
        {
            "name": "Gemini Translation推奨ケース", 
            "text": "分析の結果、Gemini Translationを推奨します。自然な表現と文脈理解が優れています。",
            "expected": "gemini"
        },
        {
            "name": "ChatGPT Translation推奨ケース",
            "text": "総合的に判断すると、ChatGPT Translationが最も正確で適切な翻訳を提供しています。",
            "expected": "chatgpt"
        },
        {
            "name": "明確な推奨なしケース",
            "text": "各翻訳にはそれぞれ長所と短所があります。どれも一長一短です。",
            "expected": "none"
        }
    ]
    
    print("🧪 LLMベース推奨抽出テスト:")
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. {case['name']}")
        print(f"   入力: {case['text'][:80]}...")
        print(f"   期待: {case['expected']}")
        
        # Phase A-4 システムでテスト
        recommendation, confidence, method = analyzer.enhanced_recommendation_extraction(case['text'], 'Japanese')
        
        print(f"   結果: {recommendation} (信頼度: {confidence}, 手法: {method})")
        
        if recommendation == case['expected']:
            print("   ✅ 成功")
        else:
            print("   ❌ 失敗")
    
    # コスト効率化テスト
    print(f"\n💰 コスト効率化テスト:")
    long_text = "\n".join([f"Line {i}: この行は長いテキストのテストです。" for i in range(1, 21)])
    tail = analyzer.get_analysis_tail(long_text, 10)
    print(f"   元テキスト: {long_text.count(chr(10))}行")
    print(f"   最適化後: {tail.count(chr(10)) + 1}行") 
    print(f"   コスト削減: {((len(long_text) - len(tail)) / len(long_text) * 100):.1f}%")
    
    print("\n✅ Phase A-4 テスト完了")

# テスト用メイン関数
if __name__ == "__main__":
    # 🚀 Phase A-8: OpenAI v1.x完全対応システムテスト
    test_phase_a8_openai_v1_system()
    
    print("\n" + "=" * 80)
    print("🤖 Phase A-4: 従来システムテスト（参考）")
    print("=" * 80)
    
    # Phase A-4 システムテスト（参考用）
    test_phase_a4_system()
    
    print("\n" + "=" * 80)
    print("🎯 従来システム - 基本テスト実行")
    print("=" * 80)
    
    analyzer = GeminiRecommendationAnalyzer()
    
    # テストケース1: 推奨抽出テスト
    test_texts = [
        "3つの翻訳を比較した結果、Enhanced翻訳が最も自然で適切です。",
        "ChatGPT: ★★★☆☆\nEnhanced: ★★★★★\nGemini: ★★★★☆\n総合的にEnhancedを推奨します。",
        "翻訳の精度と自然さを考慮すると、Geminiが一番おすすめです。",
        "1st: Gemini (最も文脈に適合)\n2nd: Enhanced\n3rd: ChatGPT"
    ]
    
    print("📝 推奨抽出テスト:")
    for i, text in enumerate(test_texts, 1):
        recommendation = analyzer.extract_gemini_recommendation(text)
        print(f"{i}. 入力: {text[:50]}...")
        print(f"   推奨: {recommendation}\n")
    
    # テストケース2: 推奨vs選択分析
    print("\n🔍 推奨vs選択分析テスト:")
    test_analysis = analyzer.analyze_recommendation_vs_choice(
        recommended='enhanced',
        actual_choice='gemini',
        session_context={
            'text_length': 600,
            'has_technical_terms': True,
            'previous_choices': {'gemini': 3}
        }
    )
    print(f"分析結果: {json.dumps(test_analysis, indent=2, ensure_ascii=False)}")
    
    print("\n✅ テスト完了")