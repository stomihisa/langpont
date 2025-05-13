from flask import Flask, render_template, request, session, redirect, url_for
from openai import OpenAI
from textwrap import dedent
from concurrent.futures import ThreadPoolExecutor
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from datetime import timedelta
import requests
import time
from labels import labels

# .env 読み込み
load_dotenv()

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

def f_reverse_translation(french_text):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "日本語、フランス語に優れた翻訳者です"},
            {"role": "user", "content": f"このフランス語を日本語に翻訳して下さい：{french_text}"}
        ]
    )
    return response.choices[0].message.content.strip()

def f_better_translation(french_text):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "フランス語の翻訳をより自然に改善する専門家です。"},
            {"role": "user", "content": f"このフランス語をもっと自然なフランス語の文章に改善してください：{french_text}"}
        ]
    )
    return response.choices[0].message.content.strip()

def f_reverse_better_translation(french_text):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "フランス語から日本語に翻訳する専門家です。"},
            {"role": "user", "content": f"このフランス語を日本語に訳してください：{french_text}"}
        ]
    )
    return response.choices[0].message.content.strip()

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

def f_translate_with_gemini(japanese_text, partner_message="", context_info=""):
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        return "⚠️ Gemini APIキーがありません"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""
    あなたは優秀な日本語からフランス語へ翻訳する翻訳者です。以下の情報をもとに日本語をフランス語に翻訳してください。**フランス語の翻訳文のみ**を返してください。解説や選択肢は不要です。：

    --- 直前のやりとり ---
    {partner_message or "(なし)"}

    --- 背景情報 ---
    {context_info or "(なし)"}

    --- 翻訳対象 ---
    {japanese_text}
    """
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return f"Gemini API error: {response.status_code} - {response.text}"

def f_gemini_3way_analysis(translated_text, better_translation, gemini_translation):
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        return "⚠️ Gemini APIキーがありません"

    # 入力長すぎチェック（2000文字以上なら注意表示 ※解析は実行）
    total_input = translated_text + better_translation + gemini_translation
    if len(total_input) > 2000:
        warning = "⚠️ 入力が長いため、分析結果は要約されています。\n\n"
    else:
        warning = ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""
以下の3つのフランス語の文について、それぞれの表現のニュアンスの違いを日本語で比較して説明してください。
あなたは翻訳表現の専門家です。
比較は「丁寧さ」「口調」「トーン」「文構造」「ニュアンスの違い」を簡潔に言語化してください。
出力は日本語で簡潔にまとめてください。重要なニュアンスや文体の違いが十分に伝わるようにしてください。必要なら500文字を超えても構いません。

【ChatGPTによる翻訳】
{translated_text}

【より良い翻訳提案（ChatGPT）】
{better_translation}

【Geminiによる翻訳】
{gemini_translation}
""".strip()

    # print("【Geminiに送信するプロンプト】")
    # print(prompt)

    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            return warning + result_text.strip()
        else:
            return f"⚠️ Gemini API error: {response.status_code} - {response.text}"
    except requests.exceptions.Timeout:
        return "⚠️ Gemini APIがタイムアウトしました（30秒以内に応答がありませんでした）"

# スピードアップ用改修
@app.route("/translate_chatgpt", methods=["POST"])
def translate_chatgpt_only():
    data = request.get_json()
    japanese_text = data.get("japanese_text", "")
    partner_message = data.get("partner_message", "")
    context_info = data.get("context_info", "")

    try:
        translated = f_translate_to_french(japanese_text, partner_message, context_info)
        reverse = f_reverse_translation(translated)

        # ✅ 翻訳結果ログ表示
        print("🔵 翻訳対象（日本語）:", japanese_text)
        print("🔵 翻訳結果（仏語）:", translated)
        print("🟢 和訳:", reverse)

        # ✅ Gemini翻訳をここで取得・保存
        gemini = f_translate_with_gemini(japanese_text)
        session["translated_text"] = translated
        session["gemini_translation"] = gemini

        return {
            "success": True,
            "translated_text": translated,
            "reverse_translated_text": reverse,
            "gemini_translation": gemini
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.route("/reverse_translate_chatgpt", methods=["POST"])
def reverse_translate_chatgpt():
    data = request.get_json()
    french_text = data.get("french_text", "")

    try:
        reversed_text = f_reverse_translation(french_text)
        print("🔁 再翻訳対象（仏語）:", french_text)
        print("🟢 再翻訳結果（和訳）:", reversed_text)  # ←✅ これを追加
        return {
            "success": True,
            "reversed_text": reversed_text
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.route("/improve_translation", methods=["POST"])
def improve_translation():
    data = request.get_json()
    french_text = data.get("french_text", "")

    try:
        improved = f_better_translation(french_text)
        print("✨ 改善対象（仏語）:", french_text)
        print("✨ 改善翻訳結果:", improved)

        # ✅ Gemini翻訳を仏語から取得（簡易的に直接使う）
        gemini_translation = f_translate_with_gemini(french_text)
        print("🔷 Gemini翻訳:", gemini_translation)

        # ✅ セッションに保存（必要！）
        session["better_translation"] = improved
        # session["gemini_translation"] = gemini_translation  # ✅ ←これがないと /get_nuance が動かない

        return {
            "success": True,
            "improved_text": improved
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.route("/reverse_better_translation", methods=["POST"])
def reverse_better_translation():
    data = request.get_json()
    french_text = data.get("french_text", "")

    try:
        reversed_text = f_reverse_better_translation(french_text)
        print("🔁 改善翻訳の和訳対象:", french_text)
        print("🟢 改善翻訳の和訳結果:", reversed_text)
        return {
            "success": True,
            "reversed_text": reversed_text
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.route("/reverse_gemini_translation", methods=["POST"])
def reverse_gemini_translation():
    gemini_text = session.get("gemini_translation", "")
    reversed_text = f_reverse_translation(gemini_text)
    print("🔁 Gemini翻訳の和訳対象:", gemini_text)
    print("🟢 Gemini翻訳の和訳結果:", reversed_text)
    return {
        "success": True,
        "reversed_text": reversed_text
    }

# ====== ルーティング ======

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        password = request.form.get("password", "")
        correct_pw = os.getenv("APP_PASSWORD", "linguru2025")  # .envに設定してもOK
        if password == correct_pw:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            error = "パスワードが違います"

    return render_template("login.html", error=error)


@app.route("/get_nuance", methods=["POST"])
def get_nuance():
    translated_text = session.get("translated_text", "")
    better_translation = session.get("better_translation", "")
    gemini_translation = session.get("gemini_translation", "")

    print("🧠 /get_nuance にアクセスが来ました")
    print("🧾 セッション情報:", {
        "translated_text": translated_text,
        "better_translation": better_translation,
        "gemini_translation": gemini_translation
    })

    # ✅ ② 文字数で空かチェック（.strip()含む）
    if not (
        len(translated_text.strip()) > 0 and
        len(better_translation.strip()) > 0 and
        len(gemini_translation.strip()) > 0
    ):
        return {"error": "必要な翻訳データが不足しています"}, 400

    result = f_gemini_3way_analysis(translated_text, better_translation, gemini_translation)

#    print("✅ Gemini分析結果:", result)

    session["gemini_3way_analysis"] = result
    return {"nuance": result}

@app.route("/", methods=["GET", "POST"])
def index():

    lang = session.get("lang", "jp") # デフォルトがJP
    label = labels.get(lang, labels["jp"])  # ← fallbackあり

    if not session.get("logged_in"):
        return redirect(url_for("login"))

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
             with ThreadPoolExecutor() as executor:
                 # 翻訳処理を並列実行
                 future_translated = executor.submit(f_translate_to_french, japanese_text, partner_message, context_info)
                 future_gemini_translation = executor.submit(f_translate_with_gemini, japanese_text, partner_message, context_info)

                 # 翻訳結果を取得
                 translated_text = future_translated.result()
                 gemini_translation = future_gemini_translation.result()

             with ThreadPoolExecutor() as executor:
                 future_reverse_translated = executor.submit(f_reverse_translation, translated_text)
                 future_better_translation = executor.submit(f_better_translation, translated_text)
                 future_gemini_reverse_translation = executor.submit(f_reverse_translation, gemini_translation)

                 reverse_translated_text = future_reverse_translated.result()
                 better_translation = future_better_translation.result()
                 gemini_reverse_translation = future_gemini_reverse_translation.result()
                 
                 future_reverse_better_translation = executor.submit(f_reverse_better_translation, better_translation)
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
        labels=label
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