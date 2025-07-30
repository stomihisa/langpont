#!/usr/bin/env python3
"""
Task #7-3 SL-3 Phase 3: API endpoints認証テスト
2025-07-30 実行: ログイン付きでのAPI呼び出しテスト
"""

import requests
import json
import time

# テスト用セッションID
TEST_SESSION_ID = f"phase3_test_{int(time.time())}"
BASE_URL = "http://localhost:8080"

def login_admin():
    """管理者でログイン"""
    print("=== 管理者ログイン ===")
    
    session = requests.Session()
    
    # 1. ログインページ取得（CSRF トークン取得）
    login_page = session.get(f"{BASE_URL}/login")
    print(f"Login page status: {login_page.status_code}")
    
    # 2. ログイン実行
    login_data = {
        'username': 'admin',
        'password': 'your_secure_password_here'
    }
    
    login_response = session.post(f"{BASE_URL}/login", data=login_data)
    print(f"Login response status: {login_response.status_code}")
    
    if login_response.status_code == 200 and 'Welcome' in login_response.text:
        print("✅ ログイン成功")
        return session
    else:
        print("❌ ログイン失敗")
        print(f"Response content: {login_response.text[:200]}...")
        return None

def test_api_with_auth(session):
    """認証付きでAPIテスト"""
    print("\n=== 認証付きAPIテスト ===")
    
    # 1. SET API テスト
    print("--- SET API テスト ---")
    set_url = f"{BASE_URL}/api/set_translation_state"
    set_payload = {
        "session_id": TEST_SESSION_ID,
        "field": "input_text",
        "value": "認証付きテストテキスト"
    }
    
    try:
        set_response = session.post(set_url, json=set_payload, timeout=10)
        print(f"SET API Status: {set_response.status_code}")
        
        if set_response.status_code == 200:
            set_data = set_response.json()
            print(f"✅ SET Response: {json.dumps(set_data, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ SET Error: {set_response.text}")
            
    except Exception as e:
        print(f"❌ SET Exception: {e}")
    
    # 2. GET API テスト
    print("\n--- GET API テスト ---")
    get_url = f"{BASE_URL}/api/get_translation_state"
    get_payload = {
        "session_id": TEST_SESSION_ID
    }
    
    try:
        get_response = session.post(get_url, json=get_payload, timeout=10)
        print(f"GET API Status: {get_response.status_code}")
        
        if get_response.status_code == 200:
            get_data = get_response.json()
            print(f"✅ GET Response: {json.dumps(get_data, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ GET Error: {get_response.text}")
            
    except Exception as e:
        print(f"❌ GET Exception: {e}")

if __name__ == "__main__":
    print("Task #7-3 SL-3 Phase 3: API endpoints認証テスト開始")
    
    # ログイン
    session = login_admin()
    
    if session:
        # 認証付きAPIテスト
        test_api_with_auth(session)
    else:
        print("❌ ログインに失敗したため、APIテストをスキップします")
    
    print("\n=== テスト完了 ===")