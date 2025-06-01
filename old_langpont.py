import os
import sys
from dotenv import load_dotenv

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

def f_reverse_translation(translated_text, target_lang, source_lang):
    """翻訳されたテキストを元の言語に戻す関数"""
    if not translated_text:
        print("⚠️ f_reverse_translation: 空のテキストが渡されました")
        return "(翻訳テキストが空です)"

    print(f"🔄 f_reverse_translation 実行:")
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
        f" 次の文章を元の言語（{source_label}）に自然な形で正確に翻訳してください。"
    )

    user_prompt = f"""
    以下の{target_label}の文を{source_label}に翻訳してください：
    ---
    {translated_text}
    """.strip()

    print("📤 f_reverse_translation 呼び出し:")
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
        print("📥 f_reverse_translation 結果:", result)
        return result

    except Exception as e:
        import traceback
        print("❌ f_reverse_translation エラー:", str(e))
        print(traceback.format_exc())
        raise

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

def f_gemini_3way_analysis(translated_text, better_translation, gemini_translation):
    """3つの翻訳結果を比較分析する関数"""

    # APIキー確認
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        return "⚠️ Gemini APIキーがありません"

    # 文字数チェック
    total_input = translated_text + better_translation + gemini_translation
    warning = "⚠️ 入力が長いため、分析結果は要約されています。\n\n" if len(total_input) > 2000 else ""

    # セッションから言語取得（デフォルトはja-fr）
    source_lang = session.get("source_lang", "ja")
    target_lang = session.get("target_lang", "fr")

    lang_map = {
        "ja": "日本語",
        "fr": "フランス語",
        "en": "英語"
    }

    source_label = lang_map.get(source_lang, source_lang)
    target_label = lang_map.get(target_lang, target_lang)

    # Geminiへのプロンプト
    prompt = f"""
以下の3つの{target_label}の文について、それぞれの表現のニュアンスの違いを{source_label}で比較して説明してください。
あなたは翻訳表現の専門家です。
比較は「丁寧さ」「口調」「トーン」「文構造」「ニュアンスの違い」を簡潔に言語化してください。
出力は{source_label}で簡潔にまとめてください。重要なニュアンスや文体の違いが十分に伝わるようにしてください。
必要なら500文字を超えても構いません。

【ChatGPTによる翻訳】
{translated_text}

【より良い翻訳提案（ChatGPT）】
{better_translation}

【Geminiによる翻訳】
{gemini_translation}
""".strip()

    print("📤 Gemini 3way分析リクエスト:")
    print(f" - prompt: {prompt[:300]}...")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            print("📥 Gemini 3way分析結果:", result_text[:100] + "...")
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

# スピードアップ用改修
@app.route("/translate_chatgpt", methods=["POST"])
def translate_chatgpt_only():
    try:
        data = request.get_json() or {}
        input_text = data.get("japanese_text", "")
        partner_message = data.get("partner_message", "")
        context_info = data.get("context_info", "")
        language_pair = data.get("language_pair", "ja-fr")  
        source_lang, target_lang = language_pair.split("-")  

        # セッションに保存
        session["source_lang"] = source_lang
        session["target_lang"] = target_lang
        session["language_pair"] = language_pair

        print("🟦 [/translate_chatgpt] API呼び出し")
        print("🔵 翻訳対象：", input_text)
        print(" - source_lang:", source_lang)
        print(" - target_lang:", target_lang)
        print(" - partner_message:", partner_message)
        print(" - context_info:", context_info)

        if not input_text:
            return {
                "success": False,
                "error": "翻訳するテキストが空です"
            }

        # ★★★ ここが重要：source_lang → target_lang の方向で翻訳 ★★★
        # 元の言語 → 翻訳先言語の方向で翻訳
        translated = f_translate_to(input_text, source_lang, target_lang, partner_message, context_info)
        print("🔵 翻訳結果translated：", translated)
        
        # ★★★ ここが重要：target_lang → source_lang の方向で逆翻訳 ★★★
        # 翻訳した言語 → 元の言語の方向で逆翻訳
        reverse = f_reverse_translation(translated, target_lang, source_lang)
        print("🟢 逆翻訳reverse：", reverse)

        # Gemini翻訳を取得
        try:
            gemini_translation = f_translate_with_gemini(input_text, source_lang, target_lang, partner_message, context_info)
            print("🔷 Gemini翻訳結果：", gemini_translation)
        except Exception as gemini_error:
            print("⚠️ Gemini翻訳エラー:", str(gemini_error))
            gemini_translation = f"Gemini翻訳エラー: {str(gemini_error)}"

        # セッションに保存
        session["input_text"] = input_text  # 元のテキストも保存
        session["translated_text"] = translated
        session["gemini_translation"] = gemini_translation

        # レスポンスを返す
        return {
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "input_text": input_text,  # 元のテキストも返す
            "translated_text": translated,
            "reverse_translated_text": reverse,
            "gemini_translation": gemini_translation
        }
    
    except Exception as e:
        import traceback
        print("❌ translate_chatgpt_only エラー:", str(e))
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
        labels=label,
        source_lang=source_lang,
        target_lang=target_lang
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/set_language/<lang>")
def set_language(lang):
    session["lang"] = lang
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)