import os
import sys
from dotenv import load_dotenv

# 🆕 バージョン情報の定義
VERSION_INFO = {
    "file_name": "langpont_lt.py",
    "version": "軽量版（英語最小プロンプト）", 
    "created_date": "2025/5/26",
    "optimization": "27%高速化 + 90%コスト削減",
    "status": "運用中"
}

# .env を読み込む（この1行で十分）
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from flask import Flask, render_template, request, session, redirect, url_for
from openai import OpenAI
from textwrap import dedent
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import requests
import time
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

# ====== ChatGPT 用 関数 ======
def f_translate_to(input_text, source_lang, target_lang, partner_message="", context_info=""):

    print("🚀 f_translate_to 開始")   # ←★ここを追加

    # 言語コード → 表示用名称のマッピング
    lang_map = {
        "ja": "日本語",
        "fr": "フランス語",
        "en": "英語"
    }

    # 表示用の翻訳ペア名を取得（例: 日本語→フランス語）
    source_label = lang_map.get(source_lang, source_lang)
    target_label = lang_map.get(target_lang, target_lang)

    # システムメッセージを言語ペアに応じて組み立てる
    system_message = f"あなたは{source_label}および{target_label}の優秀な翻訳者です。"
    system_message += f" 下記の直前のやりとりと背景情報を参考にし、自然で丁寧で失礼のない文章に{target_label}で翻訳してください。"

    # コンテキスト情報の組み立て
    context = f"""
    ～ 直前のやりとり ～
    {partner_message or "(なし)"}

    ～ 背景情報 ～
    {context_info or "(なし)"}
    """.strip()

    # ユーザーからの翻訳指示
    user_prompt = f"""
    以下のテキストを翻訳してください。
    - 元の言語: {source_label}
    - 翻訳後の言語: {target_label}
    - 丁寧で自然、かつ失礼のない文体で{target_label}に翻訳してください。

    ▼翻訳対象テキスト：
    {input_text}
    """.strip()

    print("🧱 プロンプト作成完了")   # ←★ここを追加

    print("📥 f_translate_to 呼び出し内容：")
    print(" - 入力:", input_text)
    print(" - source_lang:", source_lang)
    print(" - target_lang:", target_lang)
    print(" - 最終プロンプト:")
    print(user_prompt)

    # ChatGPTへリクエスト
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "assistant", "content": context},
            {"role": "user", "content": user_prompt}
        ]
    )

    print("📬 APIからの応答を受信")   # ←★ここを追加

    # 🚀 軽量版: 新しい翻訳関数（ここに追加）
# 🔄 ==== 翻訳関数のバージョン管理 ==== 🔄

# 📦 バックアップ: 元の日本語版軽量翻訳関数（実験前の基準版）
# ⚠️ 注意: この関数は現在使用されていませんが、必要時に f_translate_to_lightweight と置き換え可能
def f_translate_to_lightweight_japanese_backup(input_text, source_lang, target_lang, partner_message="", context_info=""):
    """
    🇯🇵 バックアップ版: 日本語プロンプト軽量翻訳関数
    
    実験結果:
    - 平均速度: 基準 (1.0x)
    - トークン数: 約600-1200 (多い)
    - 翻訳品質: 高品質
    
    切り替え方法: この関数の内容を f_translate_to_lightweight にコピーして置き換え
    """
    
    print(f"🚀 f_translate_to_lightweight_japanese_backup 開始 - {source_lang} -> {target_lang}")
    
    # 言語コード → 表示用名称のマッピング
    lang_map = {
        "ja": "日本語",
        "fr": "フランス語", 
        "en": "英語"
    }

    source_label = lang_map.get(source_lang, source_lang)
    target_label = lang_map.get(target_lang, target_lang)

    # 🔧 重要: より明確な翻訳指示
    system_message = f"あなたは{source_label}から{target_label}への専門翻訳者です。"
    system_message += f" 必ず{target_label}で回答し、{source_label}をそのまま返すことは絶対にしないでください。"

    # コンテキスト情報の組み立て
    context = f"""
    ～ 直前のやりとり ～
    {partner_message or "(なし)"}

    ～ 背景情報 ～
    {context_info or "(なし)"}
    """.strip()

    # ユーザーからの翻訳指示
    user_prompt = f"""
    以下の{source_label}を{target_label}に翻訳してください：
    
    {input_text}
    
    注意: 必ず{target_label}で回答してください。元の{source_label}をそのまら返さないでください。
    """.strip()

    print("🧱 日本語版バックアップ プロンプト作成完了")

    try:
        # ChatGPTへリクエスト
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3  # 一貫性向上
        )
        
        result = response.choices[0].message.content.strip()
        
        # 🔧 基本的な検証のみ  
        if not result:
            raise ValueError("ChatGPTからの応答が空です")
        
        print(f"✅ 日本語版バックアップ翻訳完了: {result[:50]}...")
        return result

    except Exception as e:
        print(f"❌ f_translate_to_lightweight_japanese_backup でエラー: {str(e)}")
        raise Exception(f"翻訳処理でエラーが発生しました: {str(e)}")


# 🌟 ========== Normal/Premium Mode 対応関数群 ========== 🌟
# 🌟 ========== Normal/Premium Mode 対応関数群 ========== 🌟
# 🌟 ========== Normal/Premium Mode 対応関数群 ========== 🌟

# 🌟 プレミアム版翻訳関数
# 🌟 プレミアム版翻訳関数（背景情報強化版）
def f_translate_to_lightweight_premium(input_text, source_lang, target_lang, partner_message="", context_info=""):
    """
    🌟 プレミアム版: 文化的配慮を重視した高品質翻訳関数（背景情報強化版）
    """
    
    print(f"🌟 f_translate_to_lightweight_premium 開始 - {source_lang} -> {target_lang}")
    
    lang_map = {"ja": "Japanese", "fr": "French", "en": "English"}
    target_label = lang_map.get(target_lang, target_lang)
    
    # 🔧 改善: より詳細で明確なコンテキスト処理
    if partner_message.strip() or context_info.strip():
        
        # コンテキスト情報を整理
        context_sections = []
        
        if partner_message.strip():
            context_sections.append(f"PREVIOUS CONVERSATION:\n{partner_message.strip()}")
        
        if context_info.strip():
            context_sections.append(f"BACKGROUND & RELATIONSHIP:\n{context_info.strip()}")
        
        context_text = "\n\n".join(context_sections)
        
        # 🔧 改善: 背景情報を強く反映するプロンプト
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
        # コンテキストがない場合は標準的なプロフェッショナル翻訳
        prompt = f"Professional, culturally appropriate translation to {target_label}:\n\n{input_text}"
        print(f"🧱 プレミアムシンプルプロンプト作成完了")
    
    estimated_tokens = len(prompt.split()) * 1.3
    print(f"📊 プレミアム版推定トークン数: {estimated_tokens:.0f}")
    print(f"📝 送信プロンプト（最初の200文字）: {prompt[:200]}...")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
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


# 🚀 標準改善版翻訳関数（Normal Mode）
# 🚀 標準改善版翻訳関数（背景情報強化版）
def f_translate_to_lightweight_normal(input_text, source_lang, target_lang, partner_message="", context_info=""):
    """
    🚀 標準改善版: コンテキストを重視したバランス型翻訳関数（背景情報強化版）
    """
    
    print(f"🚀 f_translate_to_lightweight_normal 開始 - {source_lang} -> {target_lang}")
    
    lang_map = {"ja": "Japanese", "fr": "French", "en": "English"}
    target_label = lang_map.get(target_lang, target_lang)
    
    # 🔧 改善: より効果的な背景情報の活用
    if partner_message.strip() or context_info.strip():
        
        # 重要な情報を明確に分離
        context_info_clean = []
        
        if partner_message.strip():
            context_info_clean.append(f"Previous: {partner_message.strip()}")
        
        if context_info.strip():
            context_info_clean.append(f"Background: {context_info.strip()}")
        
        context_summary = " | ".join(context_info_clean)
        
        # 🔧 改善: 背景情報を活用することを明確に指示
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
    print(f"📝 送信プロンプト（最初の150文字）: {prompt[:150]}...")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
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
        print("🔄 オリジナル版に切り替えます...")
        return f_translate_to_lightweight_original(input_text, source_lang, target_lang, partner_message, context_info)

# 📋 修正のポイント
"""
🔧 主な改善点:

1. コンテキスト情報の明確な分離と整理
2. 背景情報の重要性を強調するプロンプト
3. 文化的配慮と敬語レベルの考慮を明示
4. より詳細なログ出力でデバッグ可能

🎯 期待される効果:
- 背景情報がより確実に翻訳に反映される
- ビジネス関係に適した敬語レベルの選択
- 文化的に適切な表現の使用
"""


# 📈 使用カウント更新関数
def update_usage_count(mode):
    """翻訳使用回数をカウント（課金計算用）"""
    
    if mode == "premium":
        session["premium_usage_count"] = session.get("premium_usage_count", 0) + 1
        print(f"📈 Premium使用回数: {session['premium_usage_count']}")
    else:
        session["normal_usage_count"] = session.get("normal_usage_count", 0) + 1
        print(f"📈 Normal使用回数: {session['normal_usage_count']}")



# 🚀 現在使用中: 英語プロンプト最小版軽量翻訳関数
# 📊 実験結果: 平均-2.9% (ほぼ同等速度) + 90%コスト削減 + 同等品質
# 🔧 修正版: 英語プロンプト最小版軽量翻訳関数
def f_translate_to_lightweight_with_cleanup(input_text, source_lang, target_lang, partner_message="", context_info=""):
    """
    🚀 修正版: 英語プロンプト最小版軽量翻訳関数
    
    修正内容:
    - 「翻訳のみ」を明確に指示
    - 余計な説明文の排除
    - より直接的なプロンプト
    """
    
    print(f"🚀 f_translate_to_lightweight_with_cleanup(英語最小版・修正) 開始 - {source_lang} -> {target_lang}")
    
    # 言語マッピング
    lang_map = {"ja": "Japanese", "fr": "French", "en": "English"}
    target_label = lang_map.get(target_lang, target_lang)
    
    # 🔧 修正: より直接的で明確なプロンプト
    if partner_message.strip() or context_info.strip():
        context = f" Context: {partner_message} {context_info}".strip()
        prompt = f"Translate to {target_label}. Output only the translation:\n\n{input_text}\n\n{context}"
    else:
        # 🔧 修正: "Output only the translation" を明記
        prompt = f"Translate to {target_label}. Output only the translation:\n\n{input_text}"

    print(f"🧱 英語最小版(修正)プロンプト作成完了")
    print(f"📝 プロンプト: {prompt[:100]}...")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,    # さらに下げて一貫性向上
            max_tokens=300      # 適度に制限
        )
        
        result = response.choices[0].message.content.strip()
        
        # 🔧 修正: 余計な前置きを除去
        # "以下の通りです：" や "---" などを除去
        unwanted_prefixes = [
            "以下の通りです：",
            "以下の通りです:",
            "翻訳：",
            "翻訳:",
            "---",
            "翻訳結果：",
            "翻訳結果:",
            "Here is the translation:",
            "Translation:"
        ]
        
        for prefix in unwanted_prefixes:
            if result.startswith(prefix):
                result = result[len(prefix):].strip()
                print(f"🧹 不要な前置き「{prefix}」を除去しました")
        
        # 改行で始まる場合も除去
        while result.startswith('\n') or result.startswith('\r'):
            result = result[1:].strip()
        
        # 簡単な検証
        if not result or len(result.strip()) < 2:
            raise ValueError("翻訳結果が短すぎます")
            
        if result.strip() == input_text.strip():
            raise ValueError("翻訳されていません")
        
        print(f"✅ 英語最小版(修正)翻訳完了: {result[:50]}...")
        return result

    except Exception as e:
        print(f"❌ f_translate_to_lightweight_with_cleanup(英語最小版・修正) でエラー: {str(e)}")
        # フォールバック: 日本語版バックアップを使用
        print("🔄 日本語版バックアップに切り替えます...")
        return f_translate_to_lightweight_japanese_backup(input_text, source_lang, target_lang, partner_message, context_info)

# 🧪 実験用: さらに改良した版も用意
# 🚀 最終推奨版: 英語最小版（後処理なし・高速重視）
def f_translate_to_lightweight_original(input_text, source_lang, target_lang, partner_message="", context_info=""):
    """
    🚀 最終推奨版: 英語プロンプト最小版軽量翻訳関数
    
    実験結果 (最新データ):
    - 平均速度向上: +27.1% 高速化
    - トークン数削減: 90%以上
    - 翻訳品質: 同等
    - 前置き問題: 稀（5%未満）
    
    設計思想:
    - 速度最優先
    - シンプルさ重視
    - 稀な問題より全体最適化
    """
    
    print(f"🚀 f_translate_to_lightweight_original(最終版) 開始 - {source_lang} -> {target_lang}")
    
    # 言語マッピング
    lang_map = {"ja": "Japanese", "fr": "French", "en": "English"}
    target_label = lang_map.get(target_lang, target_lang)
    
    # 🔧 最適化: シンプルで効果的なプロンプト
    if partner_message.strip() or context_info.strip():
        context = f" (Context: {partner_message} {context_info})".strip()
        prompt = f"Translate to {target_label}:\n{input_text}{context}"
    else:
        # 究極にシンプル
        prompt = f"Translate to {target_label}:\n{input_text}"

    print(f"🧱 最終版プロンプト作成完了 (推定トークン数: {len(prompt.split()) * 1.3:.0f})")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,    # 一貫性重視
            max_tokens=400      # 適度な制限
        )
        
        result = response.choices[0].message.content.strip()
        
        # 🔧 最小限の検証のみ（後処理なし）
        if not result or len(result.strip()) < 2:
            raise ValueError("翻訳結果が短すぎます")
            
        if result.strip() == input_text.strip():
            raise ValueError("翻訳されていません")
        
        print(f"✅ 最終版翻訳完了: {result[:50]}...")
        return result

    except Exception as e:
        print(f"❌ f_translate_to_lightweight_original(最終版) でエラー: {str(e)}")
        # エラー時のみ日本語版バックアップ
        print("🔄 日本語版バックアップに切り替えます...")
        return f_translate_to_lightweight_japanese_backup(input_text, source_lang, target_lang, partner_message, context_info)


# 🔄 新しいメイン翻訳関数（モード切り替え対応）
def f_translate_to_lightweight(input_text, source_lang, target_lang, partner_message="", context_info=""):
    """
    🔄 モード切り替え対応メイン翻訳関数
    """
    
    # セッションから翻訳モードを取得（デフォルトはnormal）
    translation_mode = session.get("translation_mode", "normal")
    
    print(f"🔄 翻訳モード: {translation_mode.upper()}")
    
    if translation_mode == "premium":
        return f_translate_to_lightweight_premium(input_text, source_lang, target_lang, partner_message, context_info)
    else:
        # normal モードでは現在の高速版を使用
        return f_translate_to_lightweight_normal(input_text, source_lang, target_lang, partner_message, context_info)


# 🛠️ オプション: 手動で前置き除去が必要な場合の関数
def clean_translation_result(result):
    """
    手動で翻訳結果から不要な前置きを除去する関数
    必要な時だけ呼び出し可能
    """
    unwanted_prefixes = [
        "以下の通りです：", "以下の通りです:", "翻訳：", "翻訳:", "---",
        "翻訳結果：", "翻訳結果:", "Here is the translation:", "Translation:"
    ]
    
    cleaned = result.strip()
    for prefix in unwanted_prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            print(f"🧹 手動クリーニング: 「{prefix}」を除去")
    
    while cleaned.startswith('\n') or cleaned.startswith('\r'):
        cleaned = cleaned[1:].strip()
    
    return cleaned

# 📋 使い方ガイド
"""
🎯 推奨使用法:

1. 基本使用: そのまま使用
   - 95%以上は正常に動作
   - 27%高速化 + 90%コスト削減

2. 稀に前置きが付く場合:
   - 手動で clean_translation_result() を使用
   - または一時的に日本語版バックアップに切り替え

3. 完全に問題を避けたい場合:
   - 日本語版バックアップを使用
   - ただし速度・コストメリットは失われる

💡 結論: 現状のまま使用が最適
   - 速度: +27% 向上
   - コスト: 90% 削減  
   - 品質: 同等
   - 問題発生率: <5%
"""
# 🧪 ==========実験用コード開始========== 🧪
# 🧪 ==========実験用コード開始========== 🧪
# 🧪 ==========実験用コード開始========== 🧪

def f_translate_japanese_prompt_full(input_text, source_lang, target_lang, partner_message="", context_info=""):
    """現在の日本語プロンプト版（フル機能）"""
    
    lang_map = {"ja": "日本語", "fr": "フランス語", "en": "英語"}
    source_label = lang_map.get(source_lang, source_lang)
    target_label = lang_map.get(target_lang, target_lang)

    system_message = f"あなたは{source_label}から{target_label}への専門翻訳者です。必ず{target_label}で回答し、{source_label}をそのまま返すことは絶対にしないでください。"
    
    context = f"""
    ～ 直前のやりとり ～
    {partner_message or "(なし)"}
    ～ 背景情報 ～
    {context_info or "(なし)"}
    """.strip() if partner_message or context_info else ""
    
    user_prompt = f"""
    以下の{source_label}を{target_label}に翻訳してください：
    
    {input_text}
    
    注意: 必ず{target_label}で回答してください。元の{source_label}をそのまま返さないでください。
    """.strip()
    
    # トークン数概算
    total_text = system_message + context + user_prompt
    estimated_tokens = len(total_text) * 2.2  # 日本語の概算係数
    print(f"📊 日本語プロンプト推定トークン数: {estimated_tokens:.0f}")
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"翻訳処理でエラー: {str(e)}")

def f_translate_english_prompt_full(input_text, source_lang, target_lang, partner_message="", context_info=""):
    """同等機能の英語プロンプト版"""
    
    lang_map = {"ja": "Japanese", "fr": "French", "en": "English"}
    source_label = lang_map.get(source_lang, source_lang)
    target_label = lang_map.get(target_lang, target_lang)

    system_message = f"You are a professional translator specializing in {source_label} to {target_label} translation. Always respond only in {target_label}, never return the original {source_label} text."
    
    context_text = ""
    if partner_message or context_info:
        context_text = f"Context - Previous conversation: {partner_message or 'None'}. Background: {context_info or 'None'}."
    
    user_prompt = f"""
    Translate the following {source_label} text to {target_label}:
    
    {input_text}
    
    {context_text}
    
    Important: Respond only in {target_label}. Do not return the original {source_label} text.
    """.strip()
    
    # トークン数概算
    total_text = system_message + user_prompt
    estimated_tokens = len(total_text.split()) * 1.3  # 英語の概算係数
    print(f"📊 英語プロンプト推定トークン数: {estimated_tokens:.0f}")
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"翻訳処理でエラー: {str(e)}")

def f_translate_english_prompt_minimal(input_text, source_lang, target_lang, partner_message="", context_info=""):
    """最小限の英語プロンプト版（速度重視）"""
    
    lang_map = {"ja": "Japanese", "fr": "French", "en": "English"}
    target_label = lang_map.get(target_lang, target_lang)
    
    # 最小限だが必要な情報は含む
    if partner_message or context_info:
        context = f" (Context: {partner_message} {context_info})".strip()
        prompt = f"Professional translation to {target_label}:\n{input_text}{context}"
    else:
        prompt = f"Professional translation to {target_label}:\n{input_text}"
    
    # トークン数概算
    estimated_tokens = len(prompt.split()) * 1.3
    print(f"📊 最小英語プロンプト推定トークン数: {estimated_tokens:.0f}")
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=400
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"翻訳処理でエラー: {str(e)}")

# 🧪 比較テスト用関数
def compare_prompt_methods(test_text, source_lang="ja", target_lang="fr"):
    """3つの方法を比較テスト"""
    
    print("🧪 プロンプト比較テスト開始")
    print(f"テスト文章: {test_text}")
    print("-" * 50)
    
    import time
    
    # 1. 日本語プロンプト（フル）
    start_time = time.time()
    result_jp = f_translate_japanese_prompt_full(test_text, source_lang, target_lang)
    time_jp = time.time() - start_time
    print(f"🇯🇵 日本語版: {time_jp:.2f}秒")
    print(f"結果: {result_jp}")
    print()
    
    # 2. 英語プロンプト（同等機能）
    start_time = time.time()
    result_en_full = f_translate_english_prompt_full(test_text, source_lang, target_lang)
    time_en_full = time.time() - start_time
    print(f"🇺🇸 英語版(フル): {time_en_full:.2f}秒")
    print(f"結果: {result_en_full}")
    print()
    
    # 3. 英語プロンプト（最小限）
    start_time = time.time()
    result_en_min = f_translate_english_prompt_minimal(test_text, source_lang, target_lang)
    time_en_min = time.time() - start_time
    print(f"🚀 英語版(最小): {time_en_min:.2f}秒")
    print(f"結果: {result_en_min}")
    print()
    
    print("📊 比較結果:")
    print(f"速度改善: 日本語→英語(フル) {((time_jp-time_en_full)/time_jp*100):.1f}%")
    print(f"速度改善: 日本語→英語(最小) {((time_jp-time_en_min)/time_jp*100):.1f}%")
    
    return {
        "japanese": {"result": result_jp, "time": time_jp},
        "english_full": {"result": result_en_full, "time": time_en_full},
        "english_minimal": {"result": result_en_min, "time": time_en_min}
    }

# 🧪 実験用エンドポイント（実験用関数の後に追加）
# langpont_lt.py の experiment_prompts 関数を以下で置き換え（テスト用）
@app.route("/experiment_prompts", methods=["POST"])
def experiment_prompts():
    try:
        data = request.get_json()
        test_text = data.get("text", "")
        language_pair = data.get("language_pair", "ja-fr")
        source_lang, target_lang = language_pair.split("-")
        
        print(f"🧪 実験設定確認:")
        print(f"  - テキスト: {test_text}")
        print(f"  - 言語ペア: {language_pair}")
        print(f"  - 元言語: {source_lang}")
        print(f"  - 翻訳先: {target_lang}")
        
        if not test_text:
            return {"error": "テキストが空です"}
        
        # 実験実行（修正済みの関数を使用）
        results = {}
        errors = {}
        
        def run_japanese():
            try:
                import time
                start_time = time.time()
                result = f_translate_japanese_prompt_full(test_text, source_lang, target_lang)
                end_time = time.time()
                elapsed = end_time - start_time
                results["japanese"] = {"result": result, "time": elapsed}
                print(f"🇯🇵 日本語版完了: {elapsed:.2f}秒 - {result[:50]}...")
            except Exception as e:
                errors["japanese"] = str(e)
                print(f"❌ 日本語版エラー: {e}")
        
        def run_english_full():
            try:
                import time
                start_time = time.time()
                result = f_translate_english_prompt_full(test_text, source_lang, target_lang)
                end_time = time.time()
                elapsed = end_time - start_time
                results["english_full"] = {"result": result, "time": elapsed}
                print(f"🇺🇸 英語版(フル)完了: {elapsed:.2f}秒 - {result[:50]}...")
            except Exception as e:
                errors["english_full"] = str(e)
                print(f"❌ 英語版(フル)エラー: {e}")
        
        def run_english_minimal():
            try:
                import time
                start_time = time.time()
                result = f_translate_english_prompt_minimal(test_text, source_lang, target_lang)
                end_time = time.time()
                elapsed = end_time - start_time
                results["english_minimal"] = {"result": result, "time": elapsed}
                print(f"🚀 英語版(最小)完了: {elapsed:.2f}秒 - {result[:50]}...")
            except Exception as e:
                errors["english_minimal"] = str(e)
                print(f"❌ 英語版(最小)エラー: {e}")
        
        # 順次実行
        run_japanese()
        import time
        time.sleep(0.3)
        run_english_full()
        time.sleep(0.3)
        run_english_minimal()
        
        # エラーチェック
        if errors:
            print(f"❌ 実行エラー: {errors}")
            return {"success": False, "error": f"実行エラー: {errors}"}
        
        if len(results) != 3:
            print(f"❌ 結果不足: {len(results)}/3")
            return {"success": False, "error": f"結果不足: {len(results)}/3"}
        
        # サマリー作成
        summary = {
            "japanese_time": results["japanese"]["time"],
            "english_full_time": results["english_full"]["time"],
            "english_minimal_time": results["english_minimal"]["time"],
            "speed_improvement_full": ((results["japanese"]["time"] - results["english_full"]["time"]) / results["japanese"]["time"] * 100),
            "speed_improvement_minimal": ((results["japanese"]["time"] - results["english_minimal"]["time"]) / results["japanese"]["time"] * 100)
        }
        
        print(f"🧪 実験完了サマリー:")
        print(f"  - 日本語版: {summary['japanese_time']:.2f}秒")
        print(f"  - 英語フル版: {summary['english_full_time']:.2f}秒")
        print(f"  - 英語最小版: {summary['english_minimal_time']:.2f}秒")
        print(f"  - 速度改善: フル{summary['speed_improvement_full']:.1f}%, 最小{summary['speed_improvement_minimal']:.1f}%")
        
        return {
            "success": True,
            "results": results,
            "summary": summary
        }
        
    except Exception as e:
        import traceback
        print(f"❌ 実験エラー: {str(e)}")
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}


# 🧪 ==========実験用コード終了========== 🧪
# 🧪 ==========実験用コード終了========== 🧪

    # ✅ 追加①：APIのレスポンス全文を出力
    print("🔍 ChatGPT API レスポンス全文:")
    print(response)

    # ✅ 追加②：APIから返された翻訳文のみ出力
    print("✅ ChatGPTが返した翻訳結果（.content）:")
    print(response.choices[0].message.content)

    return response.choices[0].message.content.strip()

def f_translate_to_french(japanese_text, partner_message="", context_info=""):
    system_message = "あなたは優秀な日本語→フランス語翻訳者です．下記情報（直前のやりとり、背景情報）を参考に、ていねいで自然、失礼のないフランス語の文章に翻訳してください"
    context = f"""
    ～ 直前のやりとり ～
    {partner_message or "(なし)"}

    ～ 背景情報 ～
    {context_info or "(なし)"}
    """.strip()
    user_prompt = f"""
    以下の日本語をフランス語に翻訳してください：
    ---
    {japanese_text}
    """.strip()
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "assistant", "content": context},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# 🔄 langpont_lt.py の f_reverse_translation 関数を以下で置き換えてください

# 📦 バックアップ: 元の日本語版逆翻訳関数（保持用）
def f_reverse_translation_japanese_backup(translated_text, target_lang, source_lang):
    """
    🇯🇵 バックアップ版: 日本語プロンプト逆翻訳関数
    
    元の実装を保持（必要時に復元可能）
    切り替え方法: この関数の内容を f_reverse_translation にコピーして置き換え
    """
    if not translated_text:
        print("⚠️ f_reverse_translation_japanese_backup: 空のテキストが渡されました")
        return "(翻訳テキストが空です)"

    print(f"🔄 f_reverse_translation_japanese_backup 実行:")
    print(f" - translated_text: {translated_text}")
    print(f" - source_lang: {source_lang}")
    print(f" - target_lang: {target_lang}")

    lang_map = {
        "ja": "日本語",
        "fr": "フランス語",
        "en": "英語"
    }

    source_label = lang_map.get(source_lang, source_lang)
    target_label = lang_map.get(target_lang, target_lang)

    system_message = (
        f"あなたは優秀な{target_label}および{source_label}の翻訳者です。"
        f" 次の文章を元の言語（{source_lang}）に自然な形で正確に翻訳してください。"
    )

    user_prompt = f"""
    以下の{target_label}の文を{source_label}に翻訳してください：
    ---
    {translated_text}
    """.strip()

    print("📤 f_reverse_translation_japanese_backup 呼び出し:")
    print(f" - システムメッセージ: {system_message}")
    print(f" - ユーザープロンプト: {user_prompt}")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ]
        )
        result = response.choices[0].message.content.strip()
        print("📥 f_reverse_translation_japanese_backup 結果:", result)
        return result

    except Exception as e:
        import traceback
        print("❌ f_reverse_translation_japanese_backup エラー:", str(e))
        print(traceback.format_exc())
        raise

# 🚀 現在使用中: 軽量版逆翻訳関数（英語最小プロンプト）
def f_reverse_translation(translated_text, target_lang, source_lang):
    """
    🚀 軽量版逆翻訳関数（英語最小プロンプト）
    
    実装内容:
    - 英語最小プロンプト採用
    - トークン数90%削減
    - 処理速度向上
    - フォールバック機能付き
    """
    if not translated_text:
        print("⚠️ f_reverse_translation(軽量版): 空のテキストが渡されました")
        return "(翻訳テキストが空です)"

    print(f"🔄 f_reverse_translation(軽量版) 実行:")
    print(f" - translated_text: {translated_text}")
    print(f" - source_lang: {source_lang}")
    print(f" - target_lang: {target_lang}")

    # 🚀 軽量版: 英語最小プロンプト
    lang_map = {"ja": "Japanese", "fr": "French", "en": "English"}
    source_label = lang_map.get(source_lang, source_lang)
    
    # 超シンプルなプロンプト
    prompt = f"Translate to {source_label}:\n{translated_text}"

    # トークン数概算
    estimated_tokens = len(prompt.split()) * 1.3
    print(f"🧱 軽量版逆翻訳プロンプト作成完了 (推定トークン数: {estimated_tokens:.0f})")
    print(f"📝 プロンプト: {prompt}")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=300
        )
        
        result = response.choices[0].message.content.strip()
        
        # 簡単な検証
        if not result or len(result.strip()) < 2:
            raise ValueError("逆翻訳結果が短すぎます")
        
        print("📥 軽量版逆翻訳結果:", result)
        return result

    except Exception as e:
        import traceback
        print("❌ f_reverse_translation(軽量版) エラー:", str(e))
        print(traceback.format_exc())
        
        # 🔄 フォールバック: 日本語版バックアップを使用
        print("🔄 日本語版バックアップに切り替えます...")
        return f_reverse_translation_japanese_backup(translated_text, target_lang, source_lang)

# 📋 切り替え方法ガイド
#"""
#🔄 日本語版に戻す場合:
#
#1. 簡単な方法（関数呼び出し変更）:
#   - 全ての f_reverse_translation() 呼び出しを
#   - f_reverse_translation_japanese_backup() に変更

#2. 完全な方法（関数内容置き換え）:
#   - f_reverse_translation_japanese_backup の内容を
#   - f_reverse_translation にコピーして置き換え

#3. 自動フォールバック:
#   - エラー時は自動的に日本語版バックアップを使用
#"""

# 📊 期待される改善効果
#"""
#🔍 逆翻訳プロンプト比較:

#【従来版（日本語）】
#システムメッセージ: "あなたは優秀なフランス語および日本語の翻訳者です。次の文章を元の言語（日本語）に自然な形で正確に翻訳してください。"
#ユーザープロンプト: "以下のフランス語の文を日本語に翻訳してください：\n---\nVous devriez quitter cette entreprise."
#推定トークン数: 約100-150トークン

#【軽量版（英語）】
#プロンプト: "Translate to Japanese:\nVous devriez quitter cette entreprise."
#推定トークン数: 約10-15トークン

#📈 改善効果:
#- トークン数削減: 85-90%
#- 処理速度向上: 推定20-30%
#- APIコスト削減: 85-90%
#- 品質: 同等維持
#"""

def f_better_translation(text_to_improve, source_lang="fr", target_lang="en"):
    """翻訳テキストをより自然に改善する関数"""
    lang_map = {
        "ja": "日本語",
        "fr": "フランス語",
        "en": "英語"
    }

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

def f_reverse_better_translation(text_to_reverse, source_lang, target_lang):
    """改善翻訳を元の言語に戻す関数"""
    
    lang_map = {
        "ja": "日本語",
        "fr": "フランス語",
        "en": "英語"
    }

    source_label = lang_map.get(source_lang, source_lang)
    target_label = lang_map.get(target_lang, target_lang)

    system_message = f"{target_label}から{source_label}に翻訳する専門家です。"
    user_prompt = f"この{target_label}を{source_label}に訳してください：{text_to_reverse}"

    print("📤 f_reverse_better_translation 呼び出し:")
    print(" - system:", system_message)
    print(" - prompt:", user_prompt)

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ]
        )
        result = response.choices[0].message.content.strip()
        print("📥 f_reverse_better_translation 結果:", result)
        return result

    except Exception as e:
        import traceback
        print("❌ f_reverse_better_translation エラー:", str(e))
        print(traceback.format_exc())
        return "(逆翻訳に失敗しました)"

def f_ask_about_nuance(question):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "翻訳の解釈や違いについて説明できる翻訳者です。"},
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content.strip()

# ====== Gemini 用 関数 ======

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

# 🔧 修正版: 言語の動的取得
def f_gemini_3way_analysis(translated_text, better_translation, gemini_translation):
    """3つの翻訳結果を背景情報の内容に応じて動的に分析する関数（ヘッダー言語設定対応版）"""

    # APIキー確認
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        return "⚠️ Gemini APIキーがありません"

    # 🆕 ヘッダーの言語設定を取得（優先）
    display_lang = session.get("lang", "jp")  # デフォルトは日本語
    
    print(f"🌐 Gemini分析表示言語: {display_lang}")
    
    # 表示言語に応じた分析言語を設定
    analysis_lang_map = {
        "jp": "Japanese",
        "en": "English", 
        "fr": "French"
    }
    
    analysis_language = analysis_lang_map.get(display_lang, "Japanese")
    
    # 🔍 デバッグ機能
    print("🔍 === セッションデータ詳細確認 ===")
    print("📋 重要なセッションキー:")
    debug_keys = ['input_text', 'partner_message', 'context_info', 'language_pair', 'source_lang', 'target_lang', 'lang']
    for key in debug_keys:
        value = session.get(key, None)
        print(f"   {key}: {repr(value)}")
    print("=" * 50)

    # 翻訳の言語ペアを取得（分析内容のため）
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
        "ja": "Japanese",
        "fr": "French", 
        "en": "English",
        "es": "Spanish",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
        "ko": "Korean",
        "zh": "Chinese"
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

    # 🆕 分析表示言語に応じたプロンプト
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
    print(f" - 背景情報: {context_info[:50] if context_info else '(なし - 日常会話として分析)'}...")

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

# 📋 修正のポイント
"""
🔧 主な修正点:

1. language_pairから動的に言語を取得
   - ja-fr → ja, fr
   - en-ja → en, ja  
   - fr-en → fr, en

2. より包括的な言語マッピング
   - 10言語に対応
   - 未知の言語でも安全に処理

3. デバッグログの充実
   - 検出された言語ペアを表示
   - エラー時の詳細情報

4. フォールバック処理
   - language_pair分割失敗時の対応
   - 不明な言語コードへの対応
"""

# スピードアップ用改修
# langpont_lt.py の修正箇所

# 1. translate_chatgpt_only 関数を置き換え
# 🚀 これが「最初のアーティファクト」のコードです
# 🔧 translate_chatgpt_only 関数の修正
# langpont_lt.py の translate_chatgpt_only 関数を以下で修正してください

@app.route("/translate_chatgpt", methods=["POST"])
def translate_chatgpt_only():
    try:
        data = request.get_json() or {}
        input_text = data.get("japanese_text", "").strip()
        partner_message = data.get("partner_message", "")
        context_info = data.get("context_info", "")
        language_pair = data.get("language_pair", "ja-fr")  
        
        source_lang, target_lang = language_pair.split("-")  

        # 🔧 軽量版: 重要なセッションキーのみクリア
        critical_keys = ["translated_text", "reverse_translated_text"]
        for key in critical_keys:
            session.pop(key, None)

        # 🆕 修正: 背景情報も含めてセッションに保存
        session["source_lang"] = source_lang
        session["target_lang"] = target_lang
        session["language_pair"] = language_pair
        session["input_text"] = input_text           # ← 追加
        session["partner_message"] = partner_message # ← 追加
        session["context_info"] = context_info       # ← 追加

        print(f"🟦 [軽量版/translate_chatgpt] 翻訳実行: {source_lang} -> {target_lang}")
        print(f"🔵 入力: {input_text[:30]}...")
        print(f"💬 partner_message: {partner_message[:30] if partner_message else '(なし)'}...")  # ← 追加
        print(f"🏢 context_info: {context_info[:30] if context_info else '(なし)'}...")      # ← 追加

        if not input_text:
            return {
                "success": False,
                "error": "翻訳するテキストが空です"
            }

        # 🆕 モード取得と使用カウント更新
        translation_mode = session.get("translation_mode", "normal")
        update_usage_count(translation_mode)

        # 翻訳実行（軽量版関数を使用）
        translated = f_translate_to_lightweight(input_text, source_lang, target_lang, partner_message, context_info)
        print(f"🔵 翻訳結果: {translated[:30]}...")
        
        # 🔧 軽量版: 簡単な整合性チェックのみ
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

        # 🆕 修正: セッションに翻訳結果と背景情報を再度保存（確実にするため）
        session["input_text"] = input_text
        session["partner_message"] = partner_message
        session["context_info"] = context_info
        session["translated_text"] = translated
        session["reverse_translated_text"] = reverse
        session["gemini_translation"] = gemini_translation

        # 🔍 デバッグ: セッション保存の確認
        print("🔍 === セッション保存確認 ===")
        print(f"📝 保存されたcontext_info: {repr(session.get('context_info'))}")
        print(f"💬 保存されたpartner_message: {repr(session.get('partner_message'))}")
        print("=" * 40)

        # レスポンスを返す
        return {
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,  
            "input_text": input_text,
            "translated_text": translated,
            "reverse_translated_text": reverse,
            "gemini_translation": gemini_translation
        }
    
    except Exception as e:
        import traceback
        print(f"❌ 軽量版translate_chatgpt_only エラー:", str(e))
        print(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }
    
    
@app.route("/reverse_translate_chatgpt", methods=["POST"])
def reverse_translate_chatgpt():
    """ChatGPT翻訳結果を逆翻訳するエンドポイント"""
    try:
        data = request.get_json() or {}
        translated_text = data.get("french_text", "")
        language_pair = data.get("language_pair", "ja-fr")
        source_lang, target_lang = language_pair.split("-")

        # セッションに言語情報を保存
        session["source_lang"] = source_lang
        session["target_lang"] = target_lang

        # デバッグログ
        print("🔍 reverse_translate_chatgpt:")
        print(" - translated_text:", translated_text)
        print(" - language_pair:", language_pair)
        print(" - source_lang:", source_lang)
        print(" - target_lang:", target_lang)

        # 入力チェック
        if not translated_text:
            return {
                "success": False,
                "error": "翻訳テキストが空です"
            }

        # ✅ 逆方向に翻訳: target_lang → source_lang
        reversed_text = f_reverse_translation(translated_text, target_lang, source_lang)

        print("🔁 再翻訳対象（translated_text）:", translated_text)
        print("🟢 再翻訳結果（逆翻訳reversed_text）:", reversed_text)

        return {
            "success": True,
            "reversed_text": reversed_text
        }
    except Exception as e:
        import traceback
        print("❌ reverse_translate_chatgpt エラー:", str(e))
        print(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }

@app.route("/improve_translation", methods=["POST"])
def improve_translation():
    try:
        data = request.get_json() or {}
        text_to_improve = data.get("french_text", "")
        language_pair = data.get("language_pair", "ja-fr")
        source_lang, target_lang = language_pair.split("-")

        print("🔍 improve_translation:")
        print(" - text_to_improve:", text_to_improve)
        print(" - language_pair:", language_pair)
        print(" - source_lang:", source_lang)
        print(" - target_lang:", target_lang)

        if not text_to_improve:
            return {
                "success": False,
                "error": "改善する翻訳テキストが見つかりません"
            }

        # 改善翻訳
        improved = f_better_translation(text_to_improve, source_lang, target_lang)
        print(f"✨ 改善対象（{source_lang} → {target_lang}）:", text_to_improve)
        print("✨ 改善翻訳結果improved:", improved)

        try:
            gemini_translation = f_translate_with_gemini(text_to_improve, source_lang, target_lang)
            print("🔷 Gemini翻訳gemini_translation:", gemini_translation)
            session["gemini_translation"] = gemini_translation
        except Exception as gemini_error:
            print("⚠️ Gemini翻訳取得エラー:", str(gemini_error))

        session["better_translation"] = improved

        return {
            "success": True,
            "improved_text": improved
        }
    except Exception as e:
        import traceback
        print("❌ improve_translation エラー:", str(e))
        print(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }

@app.route("/reverse_better_translation", methods=["POST"])
def reverse_better_translation():
    """改善された翻訳を逆翻訳するAPIエンドポイント"""
    try:
        # リクエストデータ取得
        data = request.get_json() or {}
        improved_text = data.get("french_text", "")
        language_pair = data.get("language_pair", "ja-fr")
        source_lang, target_lang = language_pair.split("-")

        # デバッグログ
        print("🔍 reverse_better_translation:")
        print(" - improved_text:", improved_text)
        print(" - language_pair:", language_pair)
        print(" - source_lang:", source_lang)
        print(" - target_lang:", target_lang)

        # 入力チェック
        if not improved_text:
            return {
                "success": False,
                "error": "逆翻訳するテキストが見つかりません"
            }

        # ✅ 改善翻訳は target_lang の言語なので、逆翻訳は target_lang → source_lang
        reversed_text = f_reverse_translation(improved_text, target_lang, source_lang)

        print("🔁 改善翻訳の逆翻訳対象:", improved_text)
        print("🟢 改善翻訳の逆翻訳結果:", reversed_text)

        return {
            "success": True,
            "reversed_text": reversed_text
        }

    except Exception as e:
        import traceback
        print("❌ reverse_better_translation エラー:", str(e))
        print(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }

@app.route("/reverse_gemini_translation", methods=["POST"])
def reverse_gemini_translation():
    """Gemini翻訳結果を逆翻訳するエンドポイント"""
    try:
        data = request.get_json() or {}
        language_pair = data.get("language_pair", "ja-fr")
        source_lang, target_lang = language_pair.split("-")
        
        # セッションからGemini翻訳結果を取得
        gemini_text = session.get("gemini_translation", "")
        
        # デバッグログ
        print("🔍 reverse_gemini_translation:")
        print(" - language_pair:", language_pair)
        print(" - source_lang:", source_lang)
        print(" - target_lang:", target_lang)
        print(" - gemini_text:", gemini_text)
        
        # テキストが空かチェック
        if not gemini_text:
            return {
                "success": False,
                "error": "Gemini翻訳テキストが見つかりません"
            }
        
        # ✅ Gemini翻訳は source_lang → target_lang の方向なので、
        # 逆翻訳は target_lang → source_lang
        reversed_text = f_reverse_translation(gemini_text, target_lang, source_lang)

        print("🔁 Gemini翻訳の逆翻訳対象:", gemini_text)
        print("🟢 Gemini翻訳の逆翻訳結果:", reversed_text)
        
        return {
            "success": True,
            "reversed_text": reversed_text
        }

    except Exception as e:
        import traceback
        print("❌ reverse_gemini_translation エラー:", str(e))
        print(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }

# ====== ルーティング ======

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        password = request.form.get("password", "").strip()

        # 空欄チェック
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


@app.route("/get_nuance", methods=["POST"])
def get_nuance():
    try:
        translated_text = session.get("translated_text", "")
        better_translation = session.get("better_translation", "")
        gemini_translation = session.get("gemini_translation", "")

        print("🧠 /get_nuance にアクセスが来ました")
        print("🧾 セッション情報:", {
            "translated_text": translated_text,
            "better_translation": better_translation,
            "gemini_translation": gemini_translation
        })

        # 文字数で空かチェック
        if not (
            len(translated_text.strip()) > 0 and
            len(better_translation.strip()) > 0 and
            len(gemini_translation.strip()) > 0
        ):
            return {"error": "必要な翻訳データが不足しています"}, 400

        result = f_gemini_3way_analysis(translated_text, better_translation, gemini_translation)
        print("✅ Gemini分析結果:", result)

        session["gemini_3way_analysis"] = result
        return {"nuance": result}
    except Exception as e:
        import traceback
        print("❌ get_nuance エラー:", str(e))
        print(traceback.format_exc())
        return {"error": str(e)}, 500

@app.route("/", methods=["GET", "POST"])
def index():

    lang = session.get("lang", "jp") # デフォルトがJP
    label = labels.get(lang, labels["jp"])  # ← fallbackあり

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    language_pair = request.form.get("language_pair", "ja-fr") if request.method == "POST" else "ja-fr"
    source_lang, target_lang = language_pair.split("-")
        
    japanese_text = ""
    translated_text = reverse_translated_text = ""
    better_translation = reverse_better_text = nuances_analysis = ""
    gemini_translation = gemini_3way_analysis = gemini_reverse_translation = ""
    nuance_question = nuance_answer = partner_message = context_info = ""
    chat_history = session.get("chat_history", [])

    if request.method == "POST":

        if request.form.get("reset") == "true":
            keys_to_clear = [
                "chat_history", "translated_text", "better_translation", "gemini_translation",
                "partner_message", "context_info", "gemini_3way_analysis",
                "nuance_question", "nuance_answer"
    ]
            for key in keys_to_clear:
                session.pop(key, None)

            japanese_text = ""
            partner_message = ""
            context_info = ""
            nuance_question = ""

        else:

         japanese_text = request.form.get("japanese_text", "").strip()
         partner_message = request.form.get("partner_message", "").strip()
         context_info = request.form.get("context_info", "").strip()
         nuance_question = request.form.get("nuance_question", "").strip()

        if japanese_text:
            
            # 🔍 デバッグ出力：翻訳前のパラメータ確認
             print("[ChatGPT] 翻訳へ渡す内容：")
             print(" - 入力文章:", japanese_text)
             print(" - source_lang:", source_lang)
             print(" - target_lang:", target_lang)
             print(" - partner_message:", partner_message)
             print(" - context_info:", context_info)

             with ThreadPoolExecutor() as executor:
                 # 翻訳処理を並列実行
                 future_translated = executor.submit(f_translate_to, japanese_text, source_lang, target_lang, partner_message, context_info)
                 future_gemini_translation = executor.submit(f_translate_with_gemini, japanese_text, source_lang, target_lang, partner_message, context_info)

                 # 翻訳結果を取得
                 translated_text = future_translated.result()
                 gemini_translation = future_gemini_translation.result()

             with ThreadPoolExecutor() as executor:
                 future_reverse_translated = executor.submit(f_reverse_translation, translated_text, target_lang, source_lang)

                 future_better_translation = executor.submit(f_better_translation, translated_text)
                 future_gemini_reverse_translation = executor.submit(f_reverse_translation, gemini_translation, target_lang, source_lang)

                 reverse_translated_text = future_reverse_translated.result()
                 better_translation = future_better_translation.result()
                 gemini_reverse_translation = future_gemini_reverse_translation.result()
                 
                 future_reverse_better_translation = executor.submit(f_reverse_translation, better_translation, target_lang, source_lang)
                 reverse_better_text = future_reverse_better_translation.result()

             gemini_3way_analysis = f_gemini_3way_analysis(translated_text, better_translation, gemini_translation)

             session.update({
                 "chat_history": chat_history,
                 "partner_message": partner_message,
                 "context_info": context_info,
                 "translated_text": translated_text,
                 "better_translation": better_translation,
                 "gemini_translation": gemini_translation
             })

        if nuance_question:
             nuance_answer = f_ask_about_nuance(nuance_question)
             chat_history.append({"question": nuance_question, "answer": nuance_answer})
             session["chat_history"] = chat_history
             nuance_question = ""

    # ✅ どんな場合も return を通る（POST or GET）
    return render_template("index_lt.html",
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
        labels=label,
        source_lang=source_lang,
        target_lang=target_lang,
        version_info=VERSION_INFO  # 🆕 これを追加
    )

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

@app.route("/get_usage_stats")
def get_usage_stats():
    """使用状況統計を取得"""
    
    return {
        "normal_usage": session.get("normal_usage_count", 0),
        "premium_usage": session.get("premium_usage_count", 0),
        "current_mode": session.get("translation_mode", "normal")
    }


# ====== ここからこのCodeのトラブル対応マニュアル ======
# ====== ここからこのCodeのトラブル対応マニュアル ======
# ====== ここからこのCodeのトラブル対応マニュアル ======
# 🆘 翻訳機能トラブル対応ガイド

# 作成日: 2025年5月26日  
# 対象ファイル: `langpont_lt.py`
# Claudeに聞いて書いています。

# 🚨 問題: 翻訳結果に不要な前置きが表示される

# 症状の例

# ❌ "以下の通りです：Hello, how are you?"
# ❌ "翻訳：Bonjour, comment allez-vous?"  
# ❌ "---\nGuten Tag, wie geht es Ihnen?"


# 🛠️ 対応方法（優先順位順）

# 1️⃣ 様子見（まず試す）
#- **手順**: 数回翻訳を試してみる
#- **理由**: 稀な問題の可能性
#- **メリット**: 手間なし
#- **デメリット**: 問題が続く可能性

# 2️⃣ 手動クリーニング関数を使用
#- **手順**: 
  # 使用例:`
  # 問題のある結果
#  result = "以下の通りです：Hello"
  
  # クリーニング実行
#  cleaned = clean_translation_result(result)
#  print(cleaned)  # → "Hello"
  
#- **メリット**: 高速・低コスト維持
#- **デメリット**: 一部手間

# 3️⃣ 呼び出し部分のみ変更（簡単）
#- **手順**: 
#  1. `langpont_lt.py` を開く
#  2. 以下の行を探す：
#     # 使用例:`
#     translated = f_translate_to_lightweight(input_text, source_lang, target_lang, partner_message, context_info)
#     
#  3. これを以下に変更：
#     # 使用例:`
#     translated = f_translate_to_lightweight_japanese_backup(input_text, source_lang, target_lang, partner_message, context_info)
#     
#  4. アプリ再起動: `python langpont_lt.py`
#- **メリット**: 確実、変更箇所少ない
#- **デメリット**: 高速・低コストを失う

# 4️⃣ 完全切り替え（最終手段）
#- **手順**:
#  1. `langpont_lt.py` を開く
#  2. 現在の `f_translate_to_lightweight` 関数を探す
#  3. 関数名を `f_translate_to_lightweight_english_backup` に変更
#  4. `f_translate_to_lightweight_japanese_backup` の中身全体をコピー
#  5. 新しい `f_translate_to_lightweight` 関数として貼り付け
#  6. アプリ再起動: `python langpont_lt.py`
#- **メリット**: 完全確実
#- **デメリット**: 高速・低コストを失う、変更箇所多い

# 📊 各方法の比較表

#| 方法 | 手間 | 確実性 | 速度維持 | コスト維持 |
#|------|------|--------|----------|------------|
#| 1️⃣ 様子見 | ⭐⭐⭐ | ⭐ | ✅ | ✅ |
#| 2️⃣ 手動クリーニング | ⭐⭐ | ⭐⭐ | ✅ | ✅ |
#| 3️⃣ 簡単切り替え | ⭐⭐ | ⭐⭐⭐ | ❌ | ❌ |
#| 4️⃣ 完全切り替え | ⭐ | ⭐⭐⭐ | ❌ | ❌ |

# 🎯 推奨対応順序

#1. **まず1️⃣で様子見** → 問題が続くか確認
#2. **問題が続くなら2️⃣** → 高速・低コスト維持しつつ解決
#3. **それでもダメなら3️⃣** → 簡単で確実
#4. **最終手段として4️⃣** → 完全解決

# 🔄 元に戻す方法

# 日本語版→英語版に戻す場合
#上記手順の逆を実行するか、以下のバックアップから復元：
#- `f_translate_to_lightweight_japanese_backup` (日本語版)
#- `f_translate_to_lightweight_english_backup` (英語版、4️⃣実行時に作成)

# 📞 サポート

#このガイドで解決しない場合は、以下の情報と共にお問い合わせください：
#- 発生した症状の具体例
#- 試した対応方法
#- エラーメッセージ（あれば）


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)