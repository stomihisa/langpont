#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
緊急デバッグテスト
app.pyが正しく更新されているかテスト
"""

print("🚨 FORCE DEBUG: debug_test.py実行開始")

# 環境変数設定
import os
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['FLASK_SECRET_KEY'] = 'test-secret'

print("🚨 FORCE DEBUG: 環境変数設定完了")

try:
    print("🚨 FORCE DEBUG: app.py インポート試行")
    
    # app.pyをインポート（これでデバッグ情報が出力されるはず）
    import app
    
    print("🚨 FORCE DEBUG: app.py インポート成功")
    print(f"🚨 FORCE DEBUG: Flask app オブジェクト: {app.app}")
    print(f"🚨 FORCE DEBUG: Blueprint数: {len(app.app.blueprints)}")
    
    for name, bp in app.app.blueprints.items():
        print(f"  📋 Blueprint: {name}")
    
    # ルート確認
    auth_routes = [rule for rule in app.app.url_map.iter_rules() if '/auth/' in rule.rule]
    print(f"🚨 FORCE DEBUG: 認証ルート数: {len(auth_routes)}")
    
    for route in auth_routes:
        print(f"  🔐 {route.methods} {route.rule} -> {route.endpoint}")
    
    # プロフィールルートの存在確認
    profile_route_exists = any('/auth/profile' in rule.rule for rule in app.app.url_map.iter_rules())
    profile_redirect_exists = any(rule.rule == '/profile' for rule in app.app.url_map.iter_rules())
    print(f"🚨 FORCE DEBUG: /auth/profileルート存在: {profile_route_exists}")
    print(f"🚨 FORCE DEBUG: /profileリダイレクトルート存在: {profile_redirect_exists}")
    
except Exception as e:
    print(f"❌ FORCE DEBUG: エラー発生: {str(e)}")
    import traceback
    print(f"❌ FORCE DEBUG: エラー詳細:\n{traceback.format_exc()}")

print("🚨 FORCE DEBUG: debug_test.py実行完了")