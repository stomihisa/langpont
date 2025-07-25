#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dashboard Access Debug Script
ダッシュボードアクセス問題のデバッグ用スクリプト
"""

import requests
import sys

print("=== Dashboard Access Debug ===")
print("")

# Test Flask app is running
base_url = "http://localhost:5000"

print("1. Flask アプリ起動確認")
try:
    response = requests.get(f"{base_url}/login", timeout=5)
    if response.status_code == 200:
        print("✅ Flask アプリ起動中")
    else:
        print(f"❌ Flask アプリ応答異常: {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Flask アプリにアクセスできません: {e}")
    print("📝 解決方法: 'python app.py' でアプリを起動してください")
    sys.exit(1)

print("\n2. ダッシュボードルート確認")
try:
    response = requests.get(f"{base_url}/admin/comprehensive_dashboard", timeout=5)
    if response.status_code == 302:
        print("✅ ダッシュボードルート存在（ログインリダイレクト）")
    elif response.status_code == 200:
        print("✅ ダッシュボードアクセス可能")
    else:
        print(f"❌ ダッシュボードアクセス異常: {response.status_code}")
except Exception as e:
    print(f"❌ ダッシュボードアクセスエラー: {e}")

print("\n3. 管理者ログインアカウント確認")
try:
    from config import USERS
    admin_accounts = []
    for username, data in USERS.items():
        if data.get('role') in ['admin', 'developer']:
            admin_accounts.append({
                'username': username,
                'password': data.get('password'),
                'role': data.get('role')
            })
    
    if admin_accounts:
        print("✅ 管理者アカウント:")
        for account in admin_accounts:
            print(f"   - ユーザー名: {account['username']}")
            print(f"     パスワード: {account['password']}")
            print(f"     ロール: {account['role']}")
            print()
    else:
        print("❌ 管理者アカウントが見つかりません")
        
except Exception as e:
    print(f"❌ アカウント情報読み込みエラー: {e}")

print("4. HTML テンプレート確認")
try:
    template_path = "/Users/shintaro_imac_2/langpont/templates/admin_comprehensive_dashboard.html"
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '📥 全データCSV' in content:
        print("✅ CSVボタンHTML存在")
    else:
        print("❌ CSVボタンHTML不存在")
        
    if 'exportAllToCsv()' in content:
        print("✅ CSV出力JavaScript関数存在")
    else:
        print("❌ CSV出力JavaScript関数不存在")
        
except Exception as e:
    print(f"❌ テンプレートファイル確認エラー: {e}")

print("\n=== ダッシュボードアクセス手順 ===")
print("1. アプリが起動していることを確認: python app.py")
print("2. ブラウザで http://localhost:5000/login にアクセス")
print("3. 上記の管理者アカウントでログイン")
print("4. ログイン後、URL欄に http://localhost:5000/admin/comprehensive_dashboard を直接入力")
print("5. 「📋 活動履歴」セクションの右上にCSVボタンがあることを確認")
print("")
print("🔍 もしCSVボタンが見えない場合:")
print("- ブラウザのF12でコンソールエラーを確認")
print("- ページの最下部までスクロール")
print("- ブラウザの拡大率を100%に設定")
print("- キャッシュをクリア（Ctrl+F5）")