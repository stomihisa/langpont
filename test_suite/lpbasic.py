#!/usr/bin/env python3
"""
LangPont 超高速基本テスト (30秒以内完了)
目標: 最低限の動作確認 + 問題箇所の特定

テスト内容:
1. ログイン確認 (admin認証)
2. ChatGPT翻訳1回テスト
3. 基本UI確認
"""

import requests
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup

# 基本設定
BASE_URL = "http://127.0.0.1:8080"
TEST_TIMEOUT = 10  # 短縮
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# 基本テストデータ（1個のみ）
TEST_DATA = {
    "name": "基本テスト",
    "text": "おはようございます。",
    "language_pair": "ja-en",
    "context": "greeting"
}

def quick_login(session):
    """超高速ログイン（admin優先）"""
    print("🔐 ログイン中...")
    start_time = time.time()
    
    try:
        # ログインページアクセス
        login_page_response = session.get(f"{BASE_URL}/login", timeout=TEST_TIMEOUT)
        if login_page_response.status_code != 200:
            print(f"❌ ログインページアクセス失敗: HTTP {login_page_response.status_code}")
            print(f"   URL: {BASE_URL}/login")
            return False
            
        # CSRFトークン取得
        soup = BeautifulSoup(login_page_response.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrf_token'})
        csrf_token = csrf_input['value'] if csrf_input else None
        
        if not csrf_token:
            print("❌ CSRFトークン取得失敗")
            print(f"   HTML内容（先頭200文字）: {login_page_response.text[:200]}")
            return False
        
        # admin認証
        login_data = {
            "username": "admin",
            "password": "admin_langpont_2025",
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
        
        elapsed = time.time() - start_time
        
        # ログイン成功判定
        if response.status_code == 200 and ("翻訳" in response.text or "LangPont" in response.text):
            print(f"✅ ログイン成功: admin ({elapsed:.1f}秒)")
            return True
        else:
            print(f"❌ ログイン失敗: HTTP {response.status_code}")
            print(f"   リダイレクト先: {response.url}")
            print(f"   レスポンス長: {len(response.text)}文字")
            print(f"   内容チェック: 翻訳={'翻訳' in response.text}, LangPont={'LangPont' in response.text}")
            return False
            
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ ログインエラー ({elapsed:.1f}秒): {e}")
        print(f"   例外タイプ: {type(e).__name__}")
        return False

def get_csrf_token(session):
    """CSRFトークン高速取得"""
    try:
        response = session.get(BASE_URL, timeout=TEST_TIMEOUT)
        
        if "/login" in response.url:
            print("❌ 認証切れ - ログインページにリダイレクト")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_meta = soup.find('meta', {'name': 'csrf-token'})
        if csrf_meta:
            return csrf_meta.get('content')
        
        print("❌ CSRFトークンがHTMLに見つかりません")
        print(f"   レスポンス長: {len(response.text)}文字")
        return None
        
    except Exception as e:
        print(f"❌ CSRFトークン取得エラー: {e}")
        return None

def quick_chatgpt_test(session, csrf_token):
    """ChatGPT翻訳超高速テスト"""
    print("\n🔍 ChatGPT翻訳テスト中...")
    start_time = time.time()
    
    try:
        payload = {
            "japanese_text": TEST_DATA["text"],
            "language_pair": TEST_DATA["language_pair"],
            "context_info": TEST_DATA["context"]
        }
        
        headers = HEADERS.copy()
        headers["X-CSRFToken"] = csrf_token
        
        print(f"   📤 リクエスト: {BASE_URL}/translate_chatgpt")
        print(f"   📝 テキスト: {TEST_DATA['text']}")
        print(f"   🌐 言語ペア: {TEST_DATA['language_pair']}")
        
        response = session.post(
            f"{BASE_URL}/translate_chatgpt",
            json=payload,
            headers=headers,
            timeout=TEST_TIMEOUT
        )
        
        elapsed = time.time() - start_time
        
        # 詳細エラー解析
        if response.status_code == 429:
            print(f"❌ ChatGPT翻訳失敗 ({elapsed:.1f}秒): HTTP 429 - レート制限エラー")
            print(f"   詳細: アクセス頻度が高すぎます")
            print(f"   ヘッダー情報: {dict(response.headers)}")
            return False
            
        elif response.status_code == 403:
            print(f"❌ ChatGPT翻訳失敗 ({elapsed:.1f}秒): HTTP 403 - 認証エラー")
            print(f"   詳細: CSRFトークンまたは権限に問題があります")
            print(f"   CSRFトークン: {csrf_token[:20] if csrf_token else 'None'}...")
            return False
            
        elif response.status_code != 200:
            print(f"❌ ChatGPT翻訳失敗 ({elapsed:.1f}秒): HTTP {response.status_code}")
            print(f"   レスポンス: {response.text[:200]}")
            return False
        
        # JSON解析
        try:
            result = response.json()
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失敗 ({elapsed:.1f}秒): {e}")
            print(f"   レスポンス内容: {response.text[:200]}")
            return False
        
        # 成功判定
        if result.get("success") and result.get("translated_text"):
            translation = result['translated_text']
            print(f"✅ ChatGPT翻訳成功 ({elapsed:.1f}秒)")
            print(f"   翻訳結果: {translation}")
            return True
        else:
            error_msg = result.get('error', '不明なエラー')
            print(f"❌ ChatGPT翻訳失敗 ({elapsed:.1f}秒): {error_msg}")
            print(f"   レスポンス構造: {list(result.keys())}")
            return False
            
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"❌ ChatGPT翻訳タイムアウト ({elapsed:.1f}秒): {TEST_TIMEOUT}秒以内に応答なし")
        return False
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ ChatGPT翻訳エラー ({elapsed:.1f}秒): {e}")
        print(f"   例外タイプ: {type(e).__name__}")
        return False

def quick_ui_check(session):
    """基本UI超高速確認"""
    print("\n🎨 基本UI確認中...")
    start_time = time.time()
    
    try:
        response = session.get(BASE_URL, timeout=TEST_TIMEOUT)
        elapsed = time.time() - start_time
        
        if response.status_code != 200:
            print(f"❌ UI確認失敗 ({elapsed:.1f}秒): HTTP {response.status_code}")
            return False
        
        # 基本要素チェック
        content = response.text
        checks = {
            "LangPont": "LangPont" in content,
            "翻訳入力": "japanese_text" in content or "翻訳" in content,
            "翻訳ボタン": "translate" in content.lower(),
            "管理者ボタン": "管理者" in content or "admin" in content.lower()
        }
        
        success_count = sum(checks.values())
        total_count = len(checks)
        
        print(f"✅ UI確認完了 ({elapsed:.1f}秒)")
        print(f"   要素チェック: {success_count}/{total_count}")
        for item, found in checks.items():
            status = "✅" if found else "❌"
            print(f"   {status} {item}")
        
        return success_count >= 3  # 4つ中3つ以上あればOK
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ UI確認エラー ({elapsed:.1f}秒): {e}")
        return False

def run_basic_test():
    """超高速基本テスト実行"""
    print("=" * 50)
    print("🚀 LangPont 超高速基本テスト開始")
    print(f"📅 実行時刻: {datetime.now().strftime('%H:%M:%S')}")
    print(f"🎯 目標: 30秒以内完了")
    print("=" * 50)
    
    test_start = time.time()
    session = requests.Session()
    
    results = {
        "login": False,
        "chatgpt": False,
        "ui": False
    }
    
    # 1. ログインテスト
    results["login"] = quick_login(session)
    
    if results["login"]:
        # 2. CSRFトークン取得
        print("\n📌 CSRFトークン取得中...")
        csrf_token = get_csrf_token(session)
        
        if csrf_token:
            print("✅ CSRFトークン取得成功")
            
            # 3. ChatGPT翻訳テスト
            results["chatgpt"] = quick_chatgpt_test(session, csrf_token)
        else:
            print("❌ CSRFトークン取得失敗 - ChatGPT翻訳スキップ")
    else:
        print("❌ ログイン失敗 - 後続テストスキップ")
    
    # 4. UI確認（ログイン状態に関係なく実行）
    results["ui"] = quick_ui_check(session)
    
    # 結果サマリー
    total_elapsed = time.time() - test_start
    success_count = sum(results.values())
    total_tests = len(results)
    success_rate = (success_count / total_tests) * 100
    
    print("\n" + "=" * 50)
    print("📊 テスト結果")
    print("=" * 50)
    
    status_map = {
        "login": "ログイン",
        "chatgpt": "ChatGPT翻訳", 
        "ui": "UI確認"
    }
    
    for key, name in status_map.items():
        status = "✅" if results[key] else "❌"
        print(f"{status} {name}")
    
    print(f"\n🎯 総合結果: {success_count}/{total_tests} 成功 ({success_rate:.0f}%)")
    print(f"⏱️  実行時間: {total_elapsed:.1f}秒")
    
    # 判定
    if success_count == total_tests:
        print("🎉 全テスト成功！開発環境は正常です。")
    elif success_count >= 2:
        print("⚠️  部分的成功 - 開発可能レベル")
    else:
        print("🚨 重大な問題 - 基本機能に不具合あり")
    
    if total_elapsed <= 30:
        print(f"✅ 時間目標達成！（30秒以内）")
    else:
        print(f"⚠️  時間超過（目標30秒 vs 実際{total_elapsed:.1f}秒）")
    
    print("=" * 50)

if __name__ == "__main__":
    run_basic_test()