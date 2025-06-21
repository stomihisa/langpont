#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CSV Export Test
CSV出力機能のテスト
"""

import requests
import json

def test_csv_export():
    print("=== CSV Export Test ===")
    
    base_url = "http://127.0.0.1:8080"
    
    # 1. 統計API テスト（認証なし）
    print("1. 統計API テスト")
    try:
        response = requests.get(f"{base_url}/admin/api/activity_stats", timeout=10)
        print(f"統計API ステータス: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  総活動数: {data['basic']['total_activities']}")
        elif response.status_code == 403:
            print("  ⚠️ 認証が必要（正常）")
        else:
            print(f"  レスポンス: {response.text[:200]}")
    except Exception as e:
        print(f"❌ 統計API エラー: {e}")
    
    # 2. CSV出力API テスト（認証なし）
    print("\n2. CSV出力API テスト")
    try:
        response = requests.get(f"{base_url}/admin/api/export_activity_log?type=all", timeout=10)
        print(f"CSV API ステータス: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'なし')}")
        
        if response.status_code == 200:
            content = response.text
            if content.startswith('{'):
                # JSONエラーレスポンス
                try:
                    error_data = json.loads(content)
                    print(f"❌ JSONエラー: {error_data}")
                except:
                    print(f"❌ 不明なレスポンス: {content[:200]}")
            else:
                # CSVデータ
                lines = content.split('\n')
                print(f"✅ CSV出力成功: {len(lines)} 行")
                if lines:
                    print(f"  ヘッダー: {lines[0][:100]}...")
        elif response.status_code == 403:
            print("  ⚠️ 認証が必要（正常）")
        else:
            print(f"  エラーレスポンス: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ CSV API エラー: {e}")
    
    # 3. make_response インポートテスト
    print("\n3. make_response インポートテスト")
    try:
        from flask import make_response
        print("✅ make_response インポート成功")
        
        # テスト用レスポンス作成
        test_response = make_response("test")
        print(f"✅ make_response 動作確認: {type(test_response)}")
        
    except Exception as e:
        print(f"❌ make_response インポート失敗: {e}")
    
    # 4. app.py インポートテスト
    print("\n4. app.py インポートテスト")
    try:
        import sys
        if 'app' in sys.modules:
            del sys.modules['app']
        
        from app import app
        print("✅ app.py インポート成功")
        
        # ルート確認
        with app.app_context():
            rules = [str(rule) for rule in app.url_map.iter_rules()]
            export_routes = [r for r in rules if 'export_activity_log' in r]
            if export_routes:
                print(f"✅ CSV出力ルート存在: {export_routes[0]}")
            else:
                print("❌ CSV出力ルート未発見")
                
    except Exception as e:
        print(f"❌ app.py インポート失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_csv_export()
    print("\n💡 解決策:")
    print("1. アプリを再起動: python app.py")
    print("2. admin/developerでログイン")
    print("3. CSV出力を再試行")