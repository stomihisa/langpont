#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡単なFlaskルート確認スクリプト
"""

import sys
import os

# 現在のディレクトリをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from flask import Flask
    print("✅ Flask import successful")
    
    # Mock環境変数を設定
    os.environ['OPENAI_API_KEY'] = 'test-key'
    os.environ['FLASK_SECRET_KEY'] = 'test-secret'
    
    # app.pyから必要な部分をインポート
    from app import app
    print("✅ app.py import successful")
    
    # ルート一覧を取得
    print("\n📋 登録されているルート:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.methods} {rule.rule}")
        
    # auth関連のルートを確認
    auth_routes = [rule for rule in app.url_map.iter_rules() if '/auth/' in rule.rule]
    print(f"\n🔐 認証関連ルート数: {len(auth_routes)}")
    for route in auth_routes:
        print(f"  {route.methods} {route.rule}")
    
    # プロフィールルートが存在するかチェック
    profile_routes = [rule for rule in app.url_map.iter_rules() if 'profile' in rule.rule]
    print(f"\n👤 プロフィール関連ルート数: {len(profile_routes)}")
    for route in profile_routes:
        print(f"  {route.methods} {route.rule}")
    
    # 実際に/auth/profileにアクセステスト
    with app.test_client() as client:
        response = client.get('/auth/profile', follow_redirects=False)
        print(f"\n🧪 /auth/profile テスト結果:")
        print(f"  ステータス: {response.status_code}")
        print(f"  レスポンスヘッダー: {dict(response.headers)}")
        
        if response.status_code == 302:
            print(f"  リダイレクト先: {response.headers.get('Location', 'N/A')}")
            print("  ✅ 未ログイン時の正常なリダイレクト")
        elif response.status_code == 404:
            print("  ❌ 404エラー - ルートが見つかりません")
        else:
            print(f"  ⚠️ 予期しないレスポンス: {response.status_code}")

except ImportError as e:
    print(f"❌ インポートエラー: {e}")
except Exception as e:
    print(f"❌ 実行エラー: {e}")
    import traceback
    traceback.print_exc()