#!/usr/bin/env python3
"""
Translation Comprehensive Test
LangPont翻訳機能の包括的テスト

テスト対象：
- ChatGPT翻訳 (/translate_chatgpt)
- Enhanced翻訳 (/reverse_better_translation)
- Gemini分析 (/get_nuance?engine=gemini)
- Claude分析 (/get_nuance?engine=claude)
- ChatGPT分析 (/get_nuance?engine=chatgpt)
- 分析エンジン設定 (/set_analysis_engine)
"""

import requests
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup

# 基本設定
BASE_URL = "http://127.0.0.1:8080"
TEST_TIMEOUT = 30
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# ログイン認証情報
LOGIN_CREDENTIALS = [
    {"username": "admin", "password": "admin_langpont_2025"},
    {"username": "guest", "password": "guest_basic_123"},
    {"username": "", "password": "linguru2025"}  # 後方互換性
]

# テストデータ
TEST_TRANSLATIONS = [
    {
        "name": "ビジネス挨拶",
        "text": "お忙しいところ恐れ入りますが、会議の時間を変更していただけますでしょうか。",
        "language_pair": "ja-en",
        "context": "business email"
    },
    {
        "name": "技術説明",
        "text": "このAPIは非同期処理をサポートしており、高速なレスポンスを実現します。",
        "language_pair": "ja-en",
        "context": "technical documentation"
    },
    {
        "name": "カジュアル会話",
        "text": "今日はとても良い天気ですね。散歩でもしませんか？",
        "language_pair": "ja-en",
        "context": "casual conversation"
    }
]

def login(session):
    """ログイン処理を実行"""
    print("\n🔐 ログイン処理を開始...")
    
    # まずログインページでCSRFトークンを取得
    try:
        login_page_response = session.get(f"{BASE_URL}/login", timeout=TEST_TIMEOUT)
        soup = BeautifulSoup(login_page_response.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrf_token'})
        csrf_token = csrf_input['value'] if csrf_input else None
        
        if not csrf_token:
            print("❌ ログインページからCSRFトークンを取得できませんでした")
            return False
            
    except Exception as e:
        print(f"❌ ログインページアクセスエラー: {e}")
        return False
    
    # 各認証情報でログインを試行
    for cred in LOGIN_CREDENTIALS:
        try:
            login_data = {
                "username": cred["username"],
                "password": cred["password"],
                "csrf_token": csrf_token
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            response = session.post(
                f"{BASE_URL}/login",
                data=login_data,
                headers=headers,
                timeout=TEST_TIMEOUT,
                allow_redirects=True
            )
            
            # ログイン成功の判定（リダイレクト先がメインページ）
            if response.status_code == 200 and ("翻訳" in response.text or "LangPont" in response.text):
                username_display = cred["username"] if cred["username"] else "guest(後方互換)"
                print(f"✅ ログイン成功: {username_display}")
                return True
            
        except Exception as e:
            print(f"⚠️  ログイン試行失敗 ({cred['username']}): {e}")
            continue
    
    print("❌ すべてのログイン試行が失敗しました")
    return False

def get_csrf_token(session):
    """CSRFトークンを取得（ログイン後）"""
    try:
        response = session.get(BASE_URL, timeout=TEST_TIMEOUT)
        
        # ログインページにリダイレクトされた場合
        if "/login" in response.url:
            print("❌ 認証が必要です。ログインしてください。")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_meta = soup.find('meta', {'name': 'csrf-token'})
        if csrf_meta:
            return csrf_meta.get('content')
        return None
    except Exception as e:
        print(f"❌ CSRFトークン取得エラー: {e}")
        return None

def test_chatgpt_translation(session, csrf_token, test_data):
    """ChatGPT翻訳テスト"""
    print(f"\n🔍 ChatGPT翻訳テスト: {test_data['name']}")
    
    max_retries = 2
    for attempt in range(max_retries):
        try:
            payload = {
                "japanese_text": test_data["text"],
                "language_pair": test_data["language_pair"],
                "context_info": test_data["context"]
            }
            
            headers = HEADERS.copy()
            headers["X-CSRFToken"] = csrf_token
            
            response = session.post(
                f"{BASE_URL}/translate_chatgpt",
                json=payload,
                headers=headers,
                timeout=TEST_TIMEOUT
            )
            
            # レート制限チェック
            if response.status_code == 429:
                print(f"⚠️  レート制限検出 (429)。30秒待機してリトライ... (試行 {attempt + 1}/{max_retries})")
                time.sleep(30)
                continue
            
            # ステータスコード確認
            if response.status_code != 200:
                print(f"❌ ChatGPT翻訳失敗: HTTP {response.status_code}")
                print(f"   レスポンス: {response.text[:200]}")
                return False
            
            # JSONレスポンス解析
            result = response.json()
            
            # 成功判定
            if result.get("success") and result.get("translated_text"):
                print(f"✅ ChatGPT翻訳成功")
                print(f"   原文: {test_data['text'][:50]}...")
                print(f"   翻訳: {result['translated_text'][:100]}...")
                return True
            else:
                print(f"❌ ChatGPT翻訳失敗: {result.get('error', '不明なエラー')}")
                return False
                
        except Exception as e:
            print(f"❌ ChatGPT翻訳エラー: {e}")
            if attempt < max_retries - 1:
                print(f"⚠️  30秒待機してリトライ... (試行 {attempt + 1}/{max_retries})")
                time.sleep(30)
            else:
                return False
    
    return False

def test_enhanced_translation(session, csrf_token, test_data):
    """Enhanced翻訳テスト（reverse_better_translation）"""
    print(f"\n🔍 Enhanced翻訳テスト: {test_data['name']}")
    
    max_retries = 2
    for attempt in range(max_retries):
        try:
            # まずChatGPT翻訳を実行（Enhanced翻訳の前提）
            payload = {
                "japanese_text": test_data["text"],
                "language_pair": test_data["language_pair"],
                "context_info": test_data["context"]
            }
            
            headers = HEADERS.copy()
            headers["X-CSRFToken"] = csrf_token
            
            # ChatGPT翻訳を実行
            chat_response = session.post(
                f"{BASE_URL}/translate_chatgpt",
                json=payload,
                headers=headers,
                timeout=TEST_TIMEOUT
            )
            
            if chat_response.status_code == 429:
                print(f"⚠️  レート制限検出 (429)。30秒待機してリトライ... (試行 {attempt + 1}/{max_retries})")
                time.sleep(30)
                continue
                
            if chat_response.status_code != 200:
                print(f"❌ 前提のChatGPT翻訳失敗: HTTP {chat_response.status_code}")
                return False
            
            # Enhanced翻訳を実行
            response = session.post(
                f"{BASE_URL}/reverse_better_translation",
                json=payload,
                headers=headers,
                timeout=TEST_TIMEOUT
            )
            
            # レート制限チェック
            if response.status_code == 429:
                print(f"⚠️  レート制限検出 (429)。30秒待機してリトライ... (試行 {attempt + 1}/{max_retries})")
                time.sleep(30)
                continue
            
            # ステータスコード確認
            if response.status_code != 200:
                print(f"❌ Enhanced翻訳失敗: HTTP {response.status_code}")
                print(f"   レスポンス: {response.text[:200]}")
                return False
            
            # JSONレスポンス解析
            result = response.json()
            
            # 成功判定
            if result.get("success") and result.get("better_translation"):
                print(f"✅ Enhanced翻訳成功")
                print(f"   翻訳: {result['better_translation'][:100]}...")
                return True
            else:
                print(f"❌ Enhanced翻訳失敗: {result.get('error', '不明なエラー')}")
                return False
                
        except Exception as e:
            print(f"❌ Enhanced翻訳エラー: {e}")
            if attempt < max_retries - 1:
                print(f"⚠️  30秒待機してリトライ... (試行 {attempt + 1}/{max_retries})")
                time.sleep(30)
            else:
                return False
    
    return False

def test_nuance_analysis(session, csrf_token, engine, test_data):
    """ニュアンス分析テスト（Gemini/Claude/ChatGPT）"""
    print(f"\n🔍 {engine}分析テスト: {test_data['name']}")
    
    max_retries = 2
    for attempt in range(max_retries):
        try:
            # まず必要な翻訳を実行
            payload = {
                "japanese_text": test_data["text"],
                "language_pair": test_data["language_pair"],
                "context_info": test_data["context"]
            }
            
            headers = HEADERS.copy()
            headers["X-CSRFToken"] = csrf_token
            
            # ChatGPT翻訳
            chat_response = session.post(
                f"{BASE_URL}/translate_chatgpt",
                json=payload,
                headers=headers,
                timeout=TEST_TIMEOUT
            )
            
            if chat_response.status_code == 429:
                print(f"⚠️  レート制限検出 (429)。30秒待機してリトライ... (試行 {attempt + 1}/{max_retries})")
                time.sleep(30)
                continue
                
            if chat_response.status_code != 200:
                print(f"❌ 前提のChatGPT翻訳失敗")
                return False
            
            # Enhanced翻訳
            enhanced_response = session.post(
                f"{BASE_URL}/reverse_better_translation",
                json=payload,
                headers=headers,
                timeout=TEST_TIMEOUT
            )
            
            if enhanced_response.status_code == 429:
                print(f"⚠️  レート制限検出 (429)。30秒待機してリトライ... (試行 {attempt + 1}/{max_retries})")
                time.sleep(30)
                continue
                
            if enhanced_response.status_code != 200:
                print(f"❌ 前提のEnhanced翻訳失敗")
                return False
            
            # 分析エンジン設定
            engine_payload = {"engine": engine}
            engine_response = session.post(
                f"{BASE_URL}/set_analysis_engine",
                json=engine_payload,
                headers=headers,
                timeout=TEST_TIMEOUT
            )
            
            if engine_response.status_code != 200:
                print(f"❌ 分析エンジン設定失敗")
                return False
            
            # ニュアンス分析を実行（POSTメソッドに変更）
            analysis_payload = {
                "engine": engine,
                "japanese_text": test_data["text"],
                "language_pair": test_data["language_pair"]
            }
            response = session.post(
                f"{BASE_URL}/get_nuance",
                json=analysis_payload,
                headers=headers,
                timeout=TEST_TIMEOUT
            )
            
            # レート制限チェック
            if response.status_code == 429:
                print(f"⚠️  レート制限検出 (429)。30秒待機してリトライ... (試行 {attempt + 1}/{max_retries})")
                time.sleep(30)
                continue
            
            # メソッド不許可の場合はGETで再試行
            if response.status_code == 405:
                print(f"⚠️  POSTメソッド不許可。GETで再試行...")
                analysis_params = {"engine": engine}
                response = session.get(
                    f"{BASE_URL}/get_nuance",
                    params=analysis_params,
                    headers=headers,
                    timeout=TEST_TIMEOUT
                )
            
            # ステータスコード確認
            if response.status_code != 200:
                print(f"❌ {engine}分析失敗: HTTP {response.status_code}")
                print(f"   レスポンス: {response.text[:200]}")
                return False
            
            # JSONレスポンス解析
            result = response.json()
            
            # 成功判定
            if result.get("success") and result.get("analysis"):
                print(f"✅ {engine}分析成功")
                analysis_text = result['analysis']
                print(f"   分析結果: {analysis_text[:150]}...")
                return True
            else:
                print(f"❌ {engine}分析失敗: {result.get('error', '不明なエラー')}")
                return False
                
        except Exception as e:
            print(f"❌ {engine}分析エラー: {e}")
            if attempt < max_retries - 1:
                print(f"⚠️  30秒待機してリトライ... (試行 {attempt + 1}/{max_retries})")
                time.sleep(30)
            else:
                return False
    
    return False

def test_analysis_engine_setting(session, csrf_token):
    """分析エンジン設定テスト"""
    print(f"\n🔍 分析エンジン設定テスト")
    
    engines = ["gemini", "claude", "chatgpt"]
    success_count = 0
    
    for engine in engines:
        try:
            payload = {"engine": engine}
            headers = HEADERS.copy()
            headers["X-CSRFToken"] = csrf_token
            
            response = session.post(
                f"{BASE_URL}/set_analysis_engine",
                json=payload,
                headers=headers,
                timeout=TEST_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"✅ {engine}エンジン設定成功")
                    success_count += 1
                else:
                    print(f"❌ {engine}エンジン設定失敗: {result.get('error')}")
            else:
                print(f"❌ {engine}エンジン設定失敗: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {engine}エンジン設定エラー: {e}")
    
    return success_count == len(engines)

def run_comprehensive_tests():
    """包括的テストを実行"""
    print("="*60)
    print("🧪 LangPont翻訳機能包括的テスト開始")
    print(f"📅 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 対象URL: {BASE_URL}")
    print("="*60)
    
    # セッション作成
    session = requests.Session()
    
    # ログイン処理
    if not login(session):
        print("❌ ログインに失敗しました。テストを中断します。")
        return
    
    # CSRFトークン取得
    print("\n📌 CSRFトークン取得中...")
    csrf_token = get_csrf_token(session)
    if not csrf_token:
        print("❌ CSRFトークン取得失敗。テストを中断します。")
        return
    print("✅ CSRFトークン取得成功")
    
    # テスト結果集計
    results = {
        "chatgpt_translation": 0,
        "enhanced_translation": 0,
        "gemini_analysis": 0,
        "claude_analysis": 0,
        "chatgpt_analysis": 0,
        "engine_setting": 0
    }
    
    # 各テストデータで翻訳テストを実行
    for test_data in TEST_TRANSLATIONS:
        # ChatGPT翻訳テスト
        if test_chatgpt_translation(session, csrf_token, test_data):
            results["chatgpt_translation"] += 1
        time.sleep(3)  # レート制限対策: 3秒待機
        
        # Enhanced翻訳テスト
        if test_enhanced_translation(session, csrf_token, test_data):
            results["enhanced_translation"] += 1
        time.sleep(3)  # レート制限対策: 3秒待機
        
        # 各分析エンジンテスト
        for engine in ["gemini", "claude", "chatgpt"]:
            if test_nuance_analysis(session, csrf_token, engine, test_data):
                results[f"{engine}_analysis"] += 1
            time.sleep(3)  # レート制限対策: 3秒待機
    
    # 分析エンジン設定テスト
    if test_analysis_engine_setting(session, csrf_token):
        results["engine_setting"] = 1
    
    # 結果サマリー
    print("\n" + "="*60)
    print("📊 テスト結果サマリー")
    print("="*60)
    
    total_tests = len(TEST_TRANSLATIONS)
    print(f"\n✅ ChatGPT翻訳: {results['chatgpt_translation']}/{total_tests} 成功")
    print(f"✅ Enhanced翻訳: {results['enhanced_translation']}/{total_tests} 成功")
    print(f"✅ Gemini分析: {results['gemini_analysis']}/{total_tests} 成功")
    print(f"✅ Claude分析: {results['claude_analysis']}/{total_tests} 成功")
    print(f"✅ ChatGPT分析: {results['chatgpt_analysis']}/{total_tests} 成功")
    print(f"✅ エンジン設定: {'成功' if results['engine_setting'] else '失敗'}")
    
    # 総合判定
    total_passed = sum(results.values())
    total_expected = (len(results) - 1) * total_tests + 1  # engine_settingは1回のみ
    
    print(f"\n🎯 総合結果: {total_passed}/{total_expected} テスト成功")
    
    if total_passed == total_expected:
        print("🎉 全テスト成功！LangPont翻訳機能は正常に動作しています。")
    else:
        print("⚠️  一部のテストが失敗しました。詳細を確認してください。")
    
    print(f"\n⏱️  実行時間: 約{len(TEST_TRANSLATIONS) * 6 + 1}秒")
    print("="*60)

if __name__ == "__main__":
    run_comprehensive_tests()