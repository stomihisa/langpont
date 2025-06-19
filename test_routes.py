#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangPont ルート確認スクリプト
利用可能な全ルートの動作確認
"""

import sys
import traceback
import requests
from urllib.parse import urljoin

def test_routes():
    """利用可能なルートのテスト"""
    print("=== LangPont ルート確認テスト ===")
    
    base_url = "http://127.0.0.1:8080"
    
    # テスト対象ルート
    routes_to_test = [
        # メインアプリケーション
        {"path": "/", "method": "GET", "description": "メインページ", "auth_required": False},
        {"path": "/set_language/jp", "method": "GET", "description": "言語設定（日本語）", "auth_required": False},
        
        # 認証関連
        {"path": "/auth/login", "method": "GET", "description": "ログインページ", "auth_required": False},
        {"path": "/auth/register", "method": "GET", "description": "登録ページ", "auth_required": False},
        {"path": "/auth/profile", "method": "GET", "description": "プロフィールページ", "auth_required": True},
        {"path": "/auth/logout", "method": "GET", "description": "ログアウト", "auth_required": True},
        
        # プロフィール管理
        {"path": "/auth/profile/settings", "method": "GET", "description": "プロフィール設定", "auth_required": True},
        {"path": "/auth/profile/history", "method": "GET", "description": "翻訳履歴", "auth_required": True},
        {"path": "/auth/profile/early-access", "method": "GET", "description": "Early Access設定", "auth_required": True},
        
        # 翻訳履歴（詳細）
        {"path": "/auth/history/detailed", "method": "GET", "description": "詳細翻訳履歴", "auth_required": True},
        {"path": "/auth/history/analytics", "method": "GET", "description": "翻訳分析", "auth_required": True},
        
        # API エンドポイント
        {"path": "/translate_chatgpt", "method": "POST", "description": "ChatGPT翻訳API", "auth_required": False},
        {"path": "/translate_gemini", "method": "POST", "description": "Gemini翻訳API", "auth_required": False},
    ]
    
    success_count = 0
    fail_count = 0
    
    session = requests.Session()
    
    for route in routes_to_test:
        try:
            url = urljoin(base_url, route["path"])
            
            if route["method"] == "GET":
                response = session.get(url, timeout=5, allow_redirects=True)
            elif route["method"] == "POST":
                # POSTリクエストは基本的なテストデータで試行
                test_data = {"test": "data"}
                response = session.post(url, data=test_data, timeout=5, allow_redirects=True)
            
            status_code = response.status_code
            
            # 期待される結果の判定
            if route["auth_required"]:
                # 認証が必要なページは302（リダイレクト）または200（ログイン済み）が期待される
                expected_codes = [200, 302, 401, 403]
            else:
                # 認証不要なページは200が期待される
                expected_codes = [200, 302]
            
            if status_code in expected_codes:
                print(f"✅ {route['description']}: {status_code} ({route['path']})")
                success_count += 1
            else:
                print(f"❌ {route['description']}: {status_code} ({route['path']})")
                fail_count += 1
                
                # エラーレスポンスの内容を表示（短縮版）
                if len(response.text) < 200:
                    print(f"   応答: {response.text}")
                    
        except requests.exceptions.ConnectionError:
            print(f"❌ {route['description']}: 接続エラー - アプリケーションが起動していません ({route['path']})")
            fail_count += 1
        except requests.exceptions.Timeout:
            print(f"⏰ {route['description']}: タイムアウト ({route['path']})")
            fail_count += 1
        except Exception as e:
            print(f"❌ {route['description']}: エラー - {str(e)} ({route['path']})")
            fail_count += 1
    
    print(f"\n=== 結果 ===")
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失敗: {fail_count}")
    print(f"📊 成功率: {success_count/(success_count+fail_count)*100:.1f}%")
    
    if fail_count == 0:
        print("🎉 すべてのルートが正常に応答しています！")
    else:
        print("⚠️ 一部のルートに問題があります。アプリケーションが起動しているか確認してください。")

def test_specific_profile_route():
    """プロフィールルートの詳細テスト"""
    print("\n=== プロフィールルート詳細テスト ===")
    
    base_url = "http://127.0.0.1:8080"
    
    try:
        # まず / にアクセスしてセッションを開始
        session = requests.Session()
        main_response = session.get(base_url)
        print(f"メインページ: {main_response.status_code}")
        
        # /auth/profile にアクセス
        profile_url = urljoin(base_url, "/auth/profile")
        profile_response = session.get(profile_url, allow_redirects=False)
        
        print(f"プロフィールページ（未ログイン）: {profile_response.status_code}")
        
        if profile_response.status_code == 302:
            redirect_location = profile_response.headers.get('Location', '')
            print(f"リダイレクト先: {redirect_location}")
            
            if '/auth/login' in redirect_location:
                print("✅ 正常: 未ログイン時はログインページにリダイレクトされています")
            else:
                print(f"⚠️ 予期しないリダイレクト先: {redirect_location}")
        elif profile_response.status_code == 404:
            print("❌ エラー: プロフィールページが見つかりません（ルーティング問題）")
        elif profile_response.status_code == 200:
            print("⚠️ 注意: 未ログイン状態でプロフィールページにアクセスできています")
        else:
            print(f"❌ 予期しないステータス: {profile_response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 接続エラー: アプリケーションが起動していません")
    except Exception as e:
        print(f"❌ エラー: {str(e)}")

if __name__ == "__main__":
    test_routes()
    test_specific_profile_route()
    
    print(f"\n📝 使用方法:")
    print(f"1. アプリケーションを起動: python3 app.py")
    print(f"2. ブラウザで確認: http://127.0.0.1:8080")
    print(f"3. プロフィールボタンをクリックしてアクセステスト")
    print(f"4. ログイン後にプロフィールページへアクセス")