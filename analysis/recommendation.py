"""
LangPont 推奨抽出システム
Task B2-8: extract_recommendation_from_analysis関数分離
"""

import os
import re
from typing import Dict, Any
import logging

# Flask session import for language detection
from flask import session

# Logger setup - import from main app logger
import logging
logger = logging.getLogger('app')  # Use same logger as main app

def extract_recommendation_from_analysis(analysis_text: str, engine_name: str = "gemini") -> Dict[str, Any]:
    """
    分析結果から推奨を抽出する関数（Task 2.9.2 Phase B-3.5.2 対応）

    重要: ChatGPTに「分析結果から推奨を抽出」させる正しいプロンプトを実装

    間違ったアプローチ: ChatGPTに独立した翻訳判定をさせる
    正しいアプローチ: ChatGPTに「この分析文章からLLMの推奨を特定」させる
    """

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        return {
            "recommendation": "none",
            "confidence": 0.0,
            "method": "openai_key_missing",
            "error": "OpenAI APIキーが設定されていません"
        }

    # セッションから言語設定を取得
    display_lang = session.get("lang", "jp")

    # 正しいプロンプト: 分析結果から推奨抽出
    if display_lang == "en":
        prompt = f"""The following is an analysis of three translations by {engine_name} AI:

{analysis_text}

Read this analysis text and identify which translation {engine_name} AI recommends.
Choose from: ChatGPT / Enhanced / Gemini

Only respond with the name of the recommended translation."""
    elif display_lang == "fr":
        prompt = f"""Voici une analyse de trois traductions par {engine_name} IA:

{analysis_text}

Lisez ce texte d'analyse et identifiez quelle traduction {engine_name} IA recommande.
Choisissez parmi: ChatGPT / Enhanced / Gemini

Répondez uniquement avec le nom de la traduction recommandée."""
    elif display_lang == "es":
        prompt = f"""El siguiente es un análisis de tres traducciones por {engine_name} IA:

{analysis_text}

Lea este texto de análisis e identifique qué traducción recomienda {engine_name} IA.
Elija entre: ChatGPT / Enhanced / Gemini

Responda solo con el nombre de la traducción recomendada."""
    else:
        prompt = f"""以下は{engine_name}AIによる3つの翻訳の分析結果です：

{analysis_text}

この分析文章を読んで、{engine_name}AIが推奨している翻訳を特定してください。
選択肢: ChatGPT / Enhanced / Gemini
推奨されている翻訳名のみを回答してください。"""

    try:
        import openai
        openai.api_key = OPENAI_API_KEY

        # ChatGPTで推奨を抽出
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": "You are an expert at analyzing LLM recommendations. Extract the recommendation from the given analysis text."
            }, {
                "role": "user", 
                "content": prompt
            }],
            max_tokens=50,
            temperature=0.1
        )

        recommendation_text = response.choices[0].message.content.strip()

        # 🆕 デバッグログ追加（Task 2.9.2 Phase B-3.5.7 Final Integration）
        logger.info(f"🔍 DEBUG - Raw response: '{recommendation_text}'")
        logger.info(f"🔍 DEBUG - Engine analyzed: '{engine_name}'")

        # 推奨結果の正規化（簡素化・安定化）
        recommendation_lower = recommendation_text.strip().lower()
        logger.info(f"🔍 DEBUG - Cleaned: '{recommendation_lower}'")

        # 🆕 単語境界を考慮した判定ロジック（安定化）

        # 完全一致を最優先
        if recommendation_lower == 'enhanced':
            recommendation = "Enhanced"
            confidence = 0.95
            method = "exact_match"
        elif recommendation_lower == 'chatgpt':
            recommendation = "ChatGPT"
            confidence = 0.95
            method = "exact_match"
        elif recommendation_lower == 'gemini':
            recommendation = "Gemini"
            confidence = 0.95
            method = "exact_match"
        # 単語境界での部分マッチ
        elif re.search(r'\benhanced\b', recommendation_lower):
            recommendation = "Enhanced"
            confidence = 0.9
            method = "word_boundary_match"
        elif re.search(r'\bchatgpt\b', recommendation_lower):
            recommendation = "ChatGPT"
            confidence = 0.9
            method = "word_boundary_match"
        elif re.search(r'\bgemini\b', recommendation_lower):
            recommendation = "Gemini"
            confidence = 0.9
            method = "word_boundary_match"
        # フォールバック：含有チェック
        elif "enhanced" in recommendation_lower:
            recommendation = "Enhanced"
            confidence = 0.8
            method = "substring_match"
        elif "chatgpt" in recommendation_lower or "chat" in recommendation_lower:
            recommendation = "ChatGPT"
            confidence = 0.8
            method = "substring_match"
        elif "gemini" in recommendation_lower:
            recommendation = "Gemini"
            confidence = 0.8
            method = "substring_match"
        else:
            recommendation = "none"
            confidence = 0.0
            method = "no_match"

        logger.info(f"🔍 DEBUG - Final result: '{recommendation}' (method: {method})")
        logger.info(f"🎯 推奨抽出成功: {engine_name} → {recommendation} (信頼度: {confidence})")

        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "method": f"chatgpt_extraction_from_{engine_name}_{method}",
            "raw_response": recommendation_text,
            "engine_analyzed": engine_name,
            "extraction_method": method
        }

    except Exception as e:
        logger.error(f"推奨抽出エラー: {str(e)}")
        return {
            "recommendation": "error",
            "confidence": 0.0,
            "method": "extraction_failed",
            "error": str(e)
        }