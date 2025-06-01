import os
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
import hashlib

# バージョン情報の定義
VERSION_INFO = {
    "file_name": "app.py",
    "version": "Early Access版", 
    "created_date": "2025/5/31",
    "optimization": "使用制限機能付き + Push型翻訳",
    "status": "本番準備中"
}

# .env を読み込む
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from openai import OpenAI
from textwrap import dedent
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import requests
import time
import re
from labels import labels

# APIキー
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY が環境変数に見つかりません")

# Flask
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret_key")
app.permanent_session_lifetime = timedelta(hours=1)

# OpenAI client
client = OpenAI(api_key=api_key)

# =============================================================================
# 使用制限機能
# =============================================================================

# 制限設定
DAILY_LIMIT_FREE = 10
USAGE_FILE = "usage_data.json"

def get_client_id():
    """クライアント識別子を取得（IPアドレス + User-Agent の組み合わせ）"""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    # シンプルなハッシュ化
    client_id = hashlib.md5(f"{client_ip}_{user_agent}".encode()).hexdigest()[:16]
    return client_id

def load_usage_data():
    """使用データをファイルから読み込み"""
    try:
        if os.path.exists(USAGE_FILE):
            with open(USAGE_FILE, 'r') as f:
                return json.load(f)
        return {}
    except:
        return {}

def save_usage_data(data):
    """使用データをファイルに保存"""
    try:
        with open(USAGE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"使用データ保存エラー: {e}")

def check_daily_usage(client_id):
    """1日の使用制限をチェック"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 使用データを読み込み
    usage_data = load_usage_data()
    
    # 古いデータをクリーンアップ（3日以上前のデータを削除）
    cutoff_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
    cleaned_data = {}
    for key, value in usage_data.items():
        if key.endswith(f"_{cutoff_date}") or key.split('_')[-1] > cutoff_date:
            cleaned_data[key] = value
    
    if cleaned_data != usage_data:
        save_usage_data(cleaned_data)
        usage_data = cleaned_data
    
    # 今日の使用回数をチェック
    usage_key = f"{client_id}_{today}"
    current_usage = usage_data.get(usage_key, 0)
    
    if current_usage >= DAILY_LIMIT_FREE:
        return False, current_usage, DAILY_LIMIT_FREE
    
    return True, current_usage, DAILY_LIMIT_FREE

def increment_usage(client_id):
    """使用回数を増加"""
    today = datetime.now().strftime('%Y-%m-%d')
    usage_key = f"{client_id}_{today}"
    
    usage_data = load_usage_data()
    usage_data[usage_key] = usage_data.get(usage_key, 0) + 1
    save_usage_data(usage_data)
    
    return usage_data[usage_key]

def get_usage_status(client_id):
    """使用状況を取得"""
    can_use, current_usage, daily_limit = check_daily_usage(client_id)
    remaining = max(0, daily_limit - current_usage)
    
    return {
        "can_use": can_use,
        "current_usage": current_usage,
        "daily_limit": daily_limit,
        "remaining": remaining
    }

# =============================================================================
# インタラクティブ質問処理システム（既存のコード）
# =============================================================================

class TranslationContext:
    """翻訳コンテキストを管理するクラス"""
    
    @staticmethod
    def save_context(input_text, translations, analysis, metadata):
        """翻訳コンテキストをセッションに保存"""
        session["translation_context"] = {
            "input_text": input_text,
            "translations": translations,
            "analysis": analysis,
            "metadata": metadata,
            "timestamp": time.time()
        }
        
    @staticmethod
    def get_context():
        """保存された翻訳コンテキストを取得"""
        return session.get("translation_context", {})
    
    @staticmethod
    def clear_context():
        """翻訳コンテキストをクリア"""
        session.pop("translation_context", None)

class QuestionAnalyzer:
    """質問の種類を分析し、適切な処理を決定するクラス"""
    
    # 質問パターンの定義
    PATTERNS = {
        "style_adjustment": [
            r"(親近感|親しみ|フレンドリー|カジュアル).*表現",
            r"(フォーマル|丁寧|敬語).*表現",
            r"もっと.*な.*表現",
            r"(優しく|厳しく|強く).*表現",
            r"(口調|文体|トーン).*変",
        ],
        "term_explanation": [
            r".*の.*意味",
            r".*とは.*何",  
            r".*について.*説明",
            r".*の.*定義",
            r"\d+番目.*意味",
        ],
        "custom_translation": [
            r".*組み合わせ",
            r".*混ぜ",
            r".*参考.*新しい",
            r".*要素.*取り入れ",
            r".*ベース.*調整",
        ],
        "comparison": [
            r"違い.*何",
            r"どちら.*良い",
            r"比較.*して",
            r".*と.*どう違う",
        ],
        "contextual_adjustment": [
            r".*場面.*適切",
            r".*状況.*使う",
            r".*相手.*応じ",
            r"ビジネス.*場面",
            r"プライベート.*場面",
        ]
    }
    
    @classmethod
    def analyze_question(cls, question):
        """質問を分析して処理タイプを決定"""
        question_lower = question.lower()
        
        for question_type, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    return question_type
        
        return "general_question"
    
    @classmethod
    def extract_reference_number(cls, question):
        """質問から翻訳番号を抽出（「1番目の」「2つ目の」など）"""
        number_patterns = [
            r"(\d+)番目",
            r"(\d+)つ目",
            r"(\d+)個目",
            r"第(\d+)",
        ]
        
        for pattern in number_patterns:
            match = re.search(pattern, question)
            if match:
                return int(match.group(1))
        
        return None

class InteractiveTranslationProcessor:
    """インタラクティブな翻訳処理を行うクラス"""
    
    def __init__(self, client):
        self.client = client
    
    def process_question(self, question, context):
        """質問を処理してレスポンスを生成"""
        
        question_type = QuestionAnalyzer.analyze_question(question)
        reference_number = QuestionAnalyzer.extract_reference_number(question)
        
        print(f"🧠 質問タイプ: {question_type}")
        print(f"🔢 参照番号: {reference_number}")
        
        # 処理タイプに応じて適切なメソッドを呼び出し
        if question_type == "style_adjustment":
            return self._handle_style_adjustment(question, context)
        elif question_type == "term_explanation":
            return self._handle_term_explanation(question, context, reference_number)
        elif question_type == "custom_translation":
            return self._handle_custom_translation(question, context)
        elif question_type == "comparison":
            return self._handle_comparison(question, context)
        elif question_type == "contextual_adjustment":
            return self._handle_contextual_adjustment(question, context)
        else:
            return self._handle_general_question(question, context)
    
    def _handle_style_adjustment(self, question, context):
        """文体調整リクエストを処理"""
        
        translations = context.get("translations", {})
        input_text = context.get("input_text", "")
        metadata = context.get("metadata", {})
        
        # 調整要求を分析
        style_keywords = {
            "親近感": "親しみやすく親近感のある",
            "親しみ": "親しみやすく親近感のある", 
            "フレンドリー": "フレンドリーでカジュアルな",
            "カジュアル": "カジュアルでリラックスした",
            "フォーマル": "フォーマルで丁寧な",
            "丁寧": "丁寧で敬意のこもった",
            "敬語": "敬語を使った非常に丁寧な",
            "優しく": "優しく親切な",
            "厳しく": "厳格で強い",
            "強く": "強く断定的な",
            "ビジネス": "ビジネスシーンに適した"
        }
        
        detected_style = "より自然で適切な"
        for keyword, style_desc in style_keywords.items():
            if keyword in question:
                detected_style = style_desc
                break
        
        # 新しい翻訳を生成
        source_lang = metadata.get("source_lang", "ja")
        target_lang = metadata.get("target_lang", "fr")
        
        lang_map = {"ja": "日本語", "fr": "フランス語", "en": "英語"}
        source_label = lang_map.get(source_lang, source_lang)
        target_label = lang_map.get(target_lang, target_lang)
        
        prompt = f"""以下の{source_label}の文章を、{detected_style}スタイルで{target_label}に翻訳してください。

元の文: {input_text}

参考となる既存の翻訳:
1. ChatGPT版: {translations.get('chatgpt', '')}
2. 改善版: {translations.get('enhanced', '')}
3. Gemini版: {translations.get('gemini', '')}

ユーザーのリクエスト: {question}

{detected_style}表現で新しい{target_label}翻訳を作成してください。翻訳文のみを回答してください。"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400
            )
            
            new_translation = response.choices[0].message.content.strip()
            
            return {
                "type": "style_adjustment",
                "result": new_translation,
                "explanation": f"「{detected_style}」のスタイルで新しい翻訳を作成しました。"
            }
            
        except Exception as e:
            return {
                "type": "error",
                "result": f"文体調整中にエラーが発生しました: {str(e)}"
            }
    
    def _handle_general_question(self, question, context):
        """一般的な質問を処理（動的言語対応版）"""
        
        translations = context.get("translations", {})
        input_text = context.get("input_text", "")
        analysis = context.get("analysis", "")
        metadata = context.get("metadata", {})
        
        # セッションから表示言語を取得
        display_lang = session.get("lang", "jp")
        response_lang_map = {
            "jp": "Japanese",
            "en": "English", 
            "fr": "French"
        }
        response_language = response_lang_map.get(display_lang, "Japanese")
        
        # 状況変更や新しい翻訳が必要かを判定
        situation_change_keywords = [
            "上司", "部会", "指示", "シチュエーション", "場合", "状況",
            "もっと", "より", "適切", "新しい", "別の", "他の",
            "boss", "supervisor", "situation", "context", "case", "more", "better", "new", "different",
            "patron", "superviseur", "situation", "contexte", "cas", "plus", "mieux", "nouveau", "différent"
        ]
        
        needs_new_translation = any(keyword in question.lower() for keyword in situation_change_keywords)
        
        if needs_new_translation:
            # 新しい翻訳を生成
            source_lang = metadata.get("source_lang", "ja")
            target_lang = metadata.get("target_lang", "fr")
            
            lang_map = {"ja": "Japanese", "fr": "French", "en": "English"}
            source_label = lang_map.get(source_lang, source_lang)
            target_label = lang_map.get(target_lang, target_lang)
            
            prompt = f"""Based on the user's question, create a new {target_label} translation suitable for the new situation/context.

IMPORTANT: Respond entirely in {response_language}.

Original {source_label} text: {input_text}

Existing translations:
1. ChatGPT version: {translations.get('chatgpt', '')}
2. Enhanced version: {translations.get('enhanced', '')}
3. Gemini version: {translations.get('gemini', '')}

User's question: {question}

Based on the question content, create a {target_label} translation suitable for the new situation/context.

Response format (in {response_language}):
1. New {target_label} translation for the situation: [translation]
2. Reason for selection: [explanation of why this translation is appropriate]

Always provide a new {target_label} translation and respond entirely in {response_language}."""

            try:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=600
                )
                
                answer = response.choices[0].message.content.strip()
                
                return {
                    "type": "contextual_adjustment",
                    "result": answer
                }
                
            except Exception as e:
                error_messages = {
                    "jp": f"新しい翻訳生成中にエラーが発生しました: {str(e)}",
                    "en": f"Error occurred while generating new translation: {str(e)}",
                    "fr": f"Erreur lors de la génération d'une nouvelle traduction: {str(e)}"
                }
                return {
                    "type": "error",
                    "result": error_messages.get(display_lang, error_messages["jp"])
                }
        
        else:
            # 従来の一般質問処理（動的言語対応）
            prompt = f"""Answer the user's question about these translations.

IMPORTANT: Respond entirely in {response_language}.

Original text: {input_text}

Translation results:
1. ChatGPT: {translations.get('chatgpt', '')}
2. Enhanced: {translations.get('enhanced', '')}
3. Gemini: {translations.get('gemini', '')}

Previous analysis: {analysis}

User's question: {question}

Provide a helpful answer in {response_language}."""

            try:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=500
                )
                
                answer = response.choices[0].message.content.strip()
                
                return {
                    "type": "general_question",
                    "result": answer
                }
                
            except Exception as e:
                error_messages = {
                    "jp": f"質問処理中にエラーが発生しました: {str(e)}",
                    "en": f"Error occurred while processing question: {str(e)}",
                    "fr": f"Erreur lors du traitement de la question: {str(e)}"
                }
                return {
                    "type": "error",
                    "result": error_messages.get(display_lang, error_messages["jp"])
                }

# グローバルインスタンス
interactive_processor = InteractiveTranslationProcessor(client)

# =============================================================================
# 翻訳関数群（既存のコード）
# =============================================================================

def f_translate_to_lightweight_premium(input_text, source_lang, target_lang, partner_message="", context_info=""):
    """プレミアム版: 文化的配慮を重視した高品質翻訳関数"""
    
    print(f"🌟 f_translate_to_lightweight_premium 開始 - {source_lang} -> {target_lang}")
    
    lang_map = {"ja": "Japanese", "fr": "French", "en": "English"}
    target_label = lang_map.get(target_lang, target_lang)
    
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
{input_text}

Remember: The context above is crucial for determining the appropriate tone, formality, and cultural considerations."""
        
        print(f"🧱 プレミアム背景強化版プロンプト作成完了")
        print(f"📝 コンテキスト詳細: {context_text[:100]}...")
        
    else:
        prompt = f"Professional, culturally appropriate translation to {target_label}:\n\n{input_text}"
        print(f"🧱 プレミアムシンプルプロンプト作成完了")
    
    estimated_tokens = len(prompt.split()) * 1.3
    print(f"📊 プレミアム版推定トークン数: {estimated_tokens:.0f}")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=400
        )
        
        result = response.choices[0].message.content.strip()
        
        if not result or len(result.strip()) < 2:
            raise ValueError("翻訳結果が短すぎます")
            
        if result.strip() == input_text.strip():
            raise ValueError("翻訳されていません")
        
        print(f"✅ プレミアム翻訳完了: {result[:50]}...")
        return result

    except Exception as e:
        print(f"❌ プレミアム版エラー: {str(e)}")
        print("🔄 標準改善版に切り替えます...")
        return f_translate_to_lightweight_normal(input_text, source_lang, target_lang, partner_message, context_info)

def f_translate_to_lightweight_normal(input_text, source_lang, target_lang, partner_message="", context_info=""):
    """標準改善版: コンテキストを重視したバランス型翻訳関数"""
    
    print(f"🚀 f_translate_to_lightweight_normal 開始 - {source_lang} -> {target_lang}")
    
    lang_map = {"ja": "Japanese", "fr": "French", "en": "English"}
    target_label = lang_map.get(target_lang, target_lang)
    
    if partner_message.strip() or context_info.strip():
        context_info_clean = []
        
        if partner_message.strip():
            context_info_clean.append(f"Previous: {partner_message.strip()}")
        
        if context_info.strip():
            context_info_clean.append(f"Background: {context_info.strip()}")
        
        context_summary = " | ".join(context_info_clean)
        
        prompt = f"""Translate to {target_label}, carefully considering this context for appropriate tone and formality:

CONTEXT: {context_summary}

Based on the context above, translate this text with appropriate cultural sensitivity:

{input_text}"""
        
        print(f"🧱 標準背景強化版プロンプト作成完了")
        print(f"📝 背景要約: {context_summary}")
        
    else:
        prompt = f"Translate to {target_label}:\n{input_text}"
        print(f"🧱 標準シンプルプロンプト作成完了")
    
    estimated_tokens = len(prompt.split()) * 1.3
    print(f"📊 標準版推定トークン数: {estimated_tokens:.0f}")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=400
        )
        
        result = response.choices[0].message.content.strip()
        
        if not result or len(result.strip()) < 2:
            raise ValueError("翻訳結果が短すぎます")
            
        if result.strip() == input_text.strip():
            raise ValueError("翻訳されていません")
        
        print(f"✅ 標準翻訳完了: {result[:50]}...")
        return result

    except Exception as e:
        print(f"❌ 標準版エラー: {str(e)}")
        raise

def update_usage_count(mode):
    """翻訳使用回数をカウント（課金計算用）"""
    
    if mode == "premium":
        session["premium_usage_count"] = session.get("premium_usage_count", 0) + 1
        print(f"📈 Premium使用回数: {session['premium_usage_count']}")
    else:
        session["normal_usage_count"] = session.get("normal_usage_count", 0) + 1
        print(f"📈 Normal使用回数: {session['normal_usage_count']}")

def f_translate_to_lightweight(input_text, source_lang, target_lang, partner_message="", context_info=""):
    """モード切り替え対応メイン翻訳関数"""
    
    translation_mode = session.get("translation_mode", "normal")
    
    print(f"🔄 翻訳モード: {translation_mode.upper()}")
    
    if translation_mode == "premium":
        return f_translate_to_lightweight_premium(input_text, source_lang, target_lang, partner_message, context_info)
    else:
        return f_translate_to_lightweight_normal(input_text, source_lang, target_lang, partner_message, context_info)

def f_reverse_translation(translated_text, target_lang, source_lang):
    """軽量版逆翻訳関数"""
    if not translated_text:
        print("⚠️ f_reverse_translation(軽量版): 空のテキストが渡されました")
        return "(翻訳テキストが空です)"

    print(f"🔄 f_reverse_translation(軽量版) 実行:")
    print(f" - translated_text: {translated_text}")
    print(f" - source_lang: {source_lang}")
    print(f" - target_lang: {target_lang}")

    lang_map = {"ja": "Japanese", "fr": "French", "en": "English"}
    source_label = lang_map.get(source_lang, source_lang)
    
    prompt = f"Translate to {source_label}:\n{translated_text}"

    estimated_tokens = len(prompt.split()) * 1.3
    print(f"🧱 軽量版逆翻訳プロンプト作成完了 (推定トークン数: {estimated_tokens:.0f})")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300
        )
        
        result = response.choices[0].message.content.strip()
        
        if not result or len(result.strip()) < 2:
            raise ValueError("逆翻訳結果が短すぎます")
        
        print("📥 軽量版逆翻訳結果:", result)
        return result

    except Exception as e:
        print("❌ f_reverse_translation(軽量版) エラー:", str(e))
        return f"逆翻訳エラー: {str(e)}"

def f_better_translation(text_to_improve, source_lang="fr", target_lang="en"):
    """翻訳テキストをより自然に改善する関数"""
    lang_map = {"ja": "日本語", "fr": "フランス語", "en": "英語"}

    source_label = lang_map.get(source_lang, source_lang)
    target_label = lang_map.get(target_lang, target_lang)

    print(f"✨ f_better_translation 開始:")
    print(f" - text_to_improve: {text_to_improve}")
    print(f" - source_lang: {source_lang} ({source_label})")
    print(f" - target_lang: {target_lang} ({target_label})")

    system_message = f"{target_label}の翻訳をより自然に改善する専門家です。"
    user_prompt = f"この{target_label}をもっと自然な{target_label}の文章に改善してください：{text_to_improve}"

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt}
        ]
    )

    result = response.choices[0].message.content.strip()
    print(f"✅ 改善結果: {result}")
    return result

def f_translate_with_gemini(text, source_lang, target_lang, partner_message="", context_info=""):
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        return "⚠️ Gemini APIキーがありません"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""
あなたは優秀な{source_lang}→{target_lang}の翻訳者です。
以下の情報（直前のやりとり、背景）を参考に、
**{target_lang}の翻訳文のみ**を返してください（解説や注釈は不要です）。

--- 直前のやりとり ---
{partner_message or "(なし)"}

--- 背景情報 ---
{context_info or "(なし)"}

--- 翻訳対象 ---
{text}
    """.strip()

    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return f"Gemini API error: {response.status_code} - {response.text}"

def f_gemini_3way_analysis(translated_text, better_translation, gemini_translation):
    """3つの翻訳結果を背景情報の内容に応じて動的に分析する関数"""

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        return "⚠️ Gemini APIキーがありません"

    display_lang = session.get("lang", "jp")
    
    print(f"🌐 Gemini分析表示言語: {display_lang}")
    
    analysis_lang_map = {
        "jp": "Japanese",
        "en": "English", 
        "fr": "French"
    }
    
    analysis_language = analysis_lang_map.get(display_lang, "Japanese")
    
    language_pair = session.get("language_pair", "ja-fr")
    
    try:
        source_lang, target_lang = language_pair.split("-")
        print(f"🔍 翻訳言語ペア: {source_lang} -> {target_lang}")
    except:
        source_lang = session.get("source_lang", "ja")
        target_lang = session.get("target_lang", "fr") 
        print(f"⚠️ language_pair分割失敗、個別取得: {source_lang} -> {target_lang}")

    # 文字数チェック
    total_input = translated_text + better_translation + gemini_translation
    warning = "⚠️ 入力が長いため、分析結果は要約されています。\n\n" if len(total_input) > 2000 else ""

    # 背景情報を取得
    input_text = session.get("input_text", "")
    partner_message = session.get("partner_message", "")
    context_info = session.get("context_info", "")

    # 翻訳言語のマッピング（内容分析用）
    lang_map = {
        "ja": "Japanese", "fr": "French", "en": "English",
        "es": "Spanish", "de": "German", "it": "Italian",
        "pt": "Portuguese", "ru": "Russian", "ko": "Korean", "zh": "Chinese"
    }

    # 翻訳対象言語ラベル取得
    source_label = lang_map.get(source_lang, source_lang.capitalize())
    target_label = lang_map.get(target_lang, target_lang.capitalize())
    
    print(f"🌐 翻訳対象: {source_label} -> {target_label}")
    print(f"📝 分析表示言語: {analysis_language}")

    # 背景情報の内容に応じたプロンプト構築
    if context_info.strip():
        context_section = f"""
CONTEXT PROVIDED:
- Previous conversation: {partner_message or "None"}
- Situation/Background: {context_info.strip()}

Based on this specific context, analyze which translation is most appropriate."""
        
        analysis_instruction = "Analyze: formality, tone, and appropriateness for the given situation/relationship."
        
    else:
        context_section = f"""
CONTEXT: General conversation (no specific context provided)
- Previous conversation: {partner_message or "None"}

Analyze as general daily conversation."""
        
        analysis_instruction = "Analyze: formality, tone, and general conversational appropriateness."

    prompt = f"""Compare these 3 {target_label} translations considering the specific context. 

IMPORTANT: Respond in {analysis_language} with clear, readable format using bullet points and clear sections.

ORIGINAL TEXT ({source_label}): {input_text}

{context_section}

TRANSLATIONS:
1. ChatGPT: {translated_text}
2. ChatGPT Enhanced: {better_translation}  
3. Gemini: {gemini_translation}

{analysis_instruction}

CONCLUSION: Which translation best fits this specific situation and why? 

REMEMBER: Your entire response must be in {analysis_language}."""

    print("📤 Gemini 言語対応分析:")
    print(f" - 翻訳言語ペア: {source_lang} -> {target_lang}")
    print(f" - 分析表示言語: {analysis_language}")
    print(f" - 推定トークン数: {len(prompt.split()) * 1.3:.0f}")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            print(f"📥 Gemini 言語対応分析結果: {result_text[:100]}...")
            return warning + result_text.strip()
        else:
            error_msg = f"⚠️ Gemini API error: {response.status_code} - {response.text}"
            print("❌", error_msg)
            return error_msg

    except requests.exceptions.Timeout:
        return "⚠️ Gemini APIがタイムアウトしました（30秒以内に応答がありませんでした）"

    except Exception as e:
        import traceback
        error_msg = f"⚠️ Gemini API呼び出しエラー: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return error_msg

# =============================================================================
# ルーティング
# =============================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        password = request.form.get("password", "").strip()

        if not password:
            error = "パスワードを入力してください"
        else:
            correct_pw = os.getenv("APP_PASSWORD", "linguru2025")
            if password == correct_pw:
                session["logged_in"] = True
                return redirect(url_for("index"))
            else:
                error = "パスワードが違います"

    return render_template("login.html", error=error)

@app.route("/", methods=["GET", "POST"])
def index():
    lang = session.get("lang", "jp")
    label = labels.get(lang, labels["jp"])

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    # モード情報を最初に定義
    current_mode = session.get("translation_mode", "normal")
    mode_message = session.get("mode_message", "")

    language_pair = request.form.get("language_pair", "ja-fr") if request.method == "POST" else "ja-fr"
    source_lang, target_lang = language_pair.split("-")
        
    japanese_text = ""
    translated_text = reverse_translated_text = ""
    better_translation = reverse_better_text = nuances_analysis = ""
    gemini_translation = gemini_3way_analysis = gemini_reverse_translation = ""
    nuance_question = nuance_answer = partner_message = context_info = ""
    chat_history = session.get("chat_history", [])

    # 使用状況を取得
    client_id = get_client_id()
    usage_status = get_usage_status(client_id)

    if request.method == "POST":
        if request.form.get("reset") == "true":
            # 完全リセット
            keys_to_clear = [
                "chat_history", "translated_text", "better_translation", "gemini_translation",
                "partner_message", "context_info", "gemini_3way_analysis",
                "nuance_question", "nuance_answer", "reverse_better_translation"
            ]
            for key in keys_to_clear:
                session.pop(key, None)
            
            TranslationContext.clear_context()

            japanese_text = ""
            partner_message = ""
            context_info = ""
            nuance_question = ""
        else:
            japanese_text = request.form.get("japanese_text", "").strip()
            partner_message = request.form.get("partner_message", "").strip()
            context_info = request.form.get("context_info", "").strip()
            nuance_question = request.form.get("nuance_question", "").strip()

    return render_template("index.html",
        japanese_text=japanese_text,
        translated_text=translated_text,
        reverse_translated_text=reverse_translated_text,
        better_translation=better_translation,
        reverse_better_text=reverse_better_text,
        gemini_translation=gemini_translation,
        gemini_reverse_translation=gemini_reverse_translation,
        gemini_3way_analysis=gemini_3way_analysis,
        nuance_question=nuance_question,
        nuance_answer=nuance_answer,
        chat_history=chat_history,
        partner_message=partner_message,
        context_info=context_info,
        current_mode=current_mode,
        mode_message=mode_message,
        usage_status=usage_status,  # 使用状況を追加
        labels=label,
        source_lang=source_lang,
        target_lang=target_lang,
        version_info=VERSION_INFO
    )

@app.route("/alpha")
def alpha_landing():
    """Early Access用ランディングページ"""
    return render_template("landing.html", version_info=VERSION_INFO)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/set_language/<lang>")
def set_language(lang):
    session["lang"] = lang
    return redirect(url_for("index"))

@app.route("/set_translation_mode/<mode>")
def set_translation_mode(mode):
    """翻訳モード切り替えエンドポイント"""
    
    if mode in ["normal", "premium"]:
        session["translation_mode"] = mode
        print(f"🎛️ 翻訳モードを {mode.upper()} に変更しました")
        
        if mode == "premium":
            session["mode_message"] = "Premium Mode に切り替えました。より高品質な翻訳をお楽しみください。"
        else:
            session["mode_message"] = "Normal Mode に切り替えました。"
    else:
        session["mode_message"] = "無効なモードです。"
    
    return redirect(url_for("index"))

@app.route("/translate_chatgpt", methods=["POST"])
def translate_chatgpt_only():
    try:
        # 使用制限チェック
        client_id = get_client_id()
        can_use, current_usage, daily_limit = check_daily_usage(client_id)
        
        if not can_use:
            return jsonify({
                "success": False,
                "error": "usage_limit_exceeded",
                "message": f"1日の利用制限({daily_limit}回)に達しました。",
                "current_usage": current_usage,
                "daily_limit": daily_limit,
                "reset_time": "明日の00:00(日本時間)",
                "upgrade_message": "制限なしで利用したい場合は、Early Access版をお試しください。"
            })
        
        # 既存の翻訳処理
        data = request.get_json() or {}
        input_text = data.get("japanese_text", "").strip()
        partner_message = data.get("partner_message", "")
        context_info = data.get("context_info", "")
        language_pair = data.get("language_pair", "ja-fr")  
        
        source_lang, target_lang = language_pair.split("-")  

        # セッションクリア
        critical_keys = ["translated_text", "reverse_translated_text"]
        for key in critical_keys:
            session.pop(key, None)

        # セッション保存
        session["source_lang"] = source_lang
        session["target_lang"] = target_lang
        session["language_pair"] = language_pair
        session["input_text"] = input_text
        session["partner_message"] = partner_message
        session["context_info"] = context_info

        print(f"🟦 [Early Access版/translate_chatgpt] 翻訳実行: {source_lang} -> {target_lang}")
        print(f"🔵 入力: {input_text[:30]}...")

        if not input_text:
            return jsonify({
                "success": False,
                "error": "翻訳するテキストが空です"
            })

        # モード取得と使用カウント更新
        translation_mode = session.get("translation_mode", "normal")
        update_usage_count(translation_mode)

        # 翻訳実行
        translated = f_translate_to_lightweight(input_text, source_lang, target_lang, partner_message, context_info)
        print(f"🔵 翻訳結果: {translated[:30]}...")
        
        # 簡単な整合性チェック
        if translated.strip() == input_text.strip():
            print("⚠️ 翻訳結果が入力と同じ - 表示用にマーキング")
            translated = f"[翻訳処理でエラーが発生しました] {translated}"
        
        # 逆翻訳実行
        reverse = f_reverse_translation(translated, target_lang, source_lang)
        print(f"🟢 逆翻訳: {reverse[:30]}...")

        # Gemini翻訳を取得
        try:
            gemini_translation = f_translate_with_gemini(input_text, source_lang, target_lang, partner_message, context_info)
            print(f"🔷 Gemini翻訳: {gemini_translation[:30]}...")
        except Exception as gemini_error:
            print(f"⚠️ Gemini翻訳エラー:", str(gemini_error))
            gemini_translation = f"Gemini翻訳エラー: {str(gemini_error)}"

        # 改善翻訳を取得
        better_translation = ""
        reverse_better = ""
        try:
            better_translation = f_better_translation(translated, source_lang, target_lang)
            print(f"✨ 改善翻訳: {better_translation[:30]}...")
            
            # 改善翻訳の逆翻訳も実行
            if better_translation and not better_translation.startswith("改善翻訳エラー"):
                reverse_better = f_reverse_translation(better_translation, target_lang, source_lang)
                print(f"🔄 改善翻訳の逆翻訳: {reverse_better[:30]}...")
            
        except Exception as better_error:
            print(f"⚠️ 改善翻訳エラー:", str(better_error))
            better_translation = f"改善翻訳エラー: {str(better_error)}"
            reverse_better = ""

        # 使用回数を増加（翻訳成功時のみ）
        new_usage_count = increment_usage(client_id)
        remaining = daily_limit - new_usage_count

        # セッション保存
        session["translated_text"] = translated
        session["reverse_translated_text"] = reverse
        session["gemini_translation"] = gemini_translation
        session["better_translation"] = better_translation
        session["reverse_better_translation"] = reverse_better

        # 翻訳コンテキストを保存（インタラクティブ機能用）
        TranslationContext.save_context(
            input_text=input_text,
            translations={
                "chatgpt": translated,
                "enhanced": better_translation,
                "gemini": gemini_translation
            },
            analysis="",
            metadata={
                "source_lang": source_lang,
                "target_lang": target_lang,
                "partner_message": partner_message,
                "context_info": context_info
            }
        )

        return jsonify({
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,  
            "input_text": input_text,
            "translated_text": translated,
            "reverse_translated_text": reverse,
            "gemini_translation": gemini_translation,
            "better_translation": better_translation,
            "reverse_better_translation": reverse_better,
            # 使用状況情報を追加
            "usage_info": {
                "current_usage": new_usage_count,
                "daily_limit": daily_limit,
                "remaining": remaining,
                "is_near_limit": remaining <= 2
            }
        })
    
    except Exception as e:
        import traceback
        print(f"❌ Early Access版translate_chatgpt_only エラー:", str(e))
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/get_nuance", methods=["POST"])
def get_nuance():
    try:
        translated_text = session.get("translated_text", "")
        better_translation = session.get("better_translation", "")
        gemini_translation = session.get("gemini_translation", "")

        print("🧠 /get_nuance にアクセスが来ました")

        if not (len(translated_text.strip()) > 0 and
                len(better_translation.strip()) > 0 and
                len(gemini_translation.strip()) > 0):
            return {"error": "必要な翻訳データが不足しています"}, 400

        result = f_gemini_3way_analysis(translated_text, better_translation, gemini_translation)
        print("✅ Gemini分析結果:", result)

        session["gemini_3way_analysis"] = result
        
        # 分析結果を翻訳コンテキストに追加
        context = TranslationContext.get_context()
        if context:
            context["analysis"] = result
            TranslationContext.save_context(
                context["input_text"],
                context["translations"],
                result,
                context["metadata"]
            )
        
        return {"nuance": result}
    except Exception as e:
        import traceback
        print("❌ get_nuance エラー:", str(e))
        print(traceback.format_exc())
        return {"error": str(e)}, 500

@app.route("/interactive_question", methods=["POST"])
def interactive_question():
    """インタラクティブな質問を処理するエンドポイント"""
    try:
        data = request.get_json() or {}
        question = data.get("question", "").strip()
        
        if not question:
            return jsonify({
                "success": False,
                "error": "質問が入力されていません"
            })
        
        # 翻訳コンテキストを取得
        context = TranslationContext.get_context()
        
        if not context:
            return jsonify({
                "success": False,
                "error": "翻訳コンテキストが見つかりません。まず翻訳を実行してください。"
            })
        
        print(f"🧠 インタラクティブ質問受信: {question}")
        
        # 質問を処理
        result = interactive_processor.process_question(question, context)
        
        # チャット履歴に追加
        chat_history = session.get("chat_history", [])
        chat_history.append({
            "question": question,
            "answer": result.get("result", ""),
            "type": result.get("type", "general"),
            "timestamp": time.time()
        })
        session["chat_history"] = chat_history
        
        print(f"✅ インタラクティブ質問処理完了: {result.get('type')}")
        
        return jsonify({
            "success": True,
            "result": result,
            "chat_history": chat_history
        })
        
    except Exception as e:
        import traceback
        print(f"❌ インタラクティブ質問エラー: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/clear_chat_history", methods=["POST"])
def clear_chat_history():
    """チャット履歴をクリアするエンドポイント"""
    try:
        session["chat_history"] = []
        
        return jsonify({
            "success": True,
            "message": "チャット履歴をクリアしました"
        })
        
    except Exception as e:
        print(f"❌ チャット履歴クリアエラー: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/reverse_better_translation", methods=["POST"])
def reverse_better_translation():
    """改善された翻訳を逆翻訳するAPIエンドポイント"""
    try:
        data = request.get_json() or {}
        improved_text = data.get("french_text", "")
        language_pair = data.get("language_pair", "ja-fr")
        source_lang, target_lang = language_pair.split("-")

        print("🔍 reverse_better_translation:")
        print(" - improved_text:", improved_text)
        print(" - language_pair:", language_pair)
        print(" - source_lang:", source_lang)
        print(" - target_lang:", target_lang)

        if not improved_text:
            return jsonify({
                "success": False,
                "error": "逆翻訳するテキストが見つかりません"
            })

        reversed_text = f_reverse_translation(improved_text, target_lang, source_lang)

        print("🔁 改善翻訳の逆翻訳対象:", improved_text)
        print("🟢 改善翻訳の逆翻訳結果:", reversed_text)

        return jsonify({
            "success": True,
            "reversed_text": reversed_text
        })

    except Exception as e:
        import traceback
        print("❌ reverse_better_translation エラー:", str(e))
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/usage_status", methods=["GET"])
def get_usage_status_endpoint():
    """使用状況を取得するエンドポイント"""
    try:
        client_id = get_client_id()
        status = get_usage_status(client_id)
        
        return jsonify({
            "success": True,
            "usage_status": status,
            "message": f"本日 {status['current_usage']}/{status['daily_limit']} 回利用済み"
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/get_usage_stats")
def get_usage_stats():
    """使用状況統計を取得"""
    
    return {
        "normal_usage": session.get("normal_usage_count", 0),
        "premium_usage": session.get("premium_usage_count", 0),
        "current_mode": session.get("translation_mode", "normal")
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    
    # 本番環境判定
    is_production = os.getenv('FLASK_ENV') == 'production'
    
    # 本番環境用セキュリティ設定
    if is_production:
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    app.run(host="0.0.0.0", port=port, debug=not is_production)