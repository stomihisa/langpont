#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
App Startup Test
app.py の構文エラーチェック
"""

import subprocess
import sys

def test_app_startup():
    print("=== App Startup Test ===")
    
    # 1. 構文チェック
    print("1. Python構文チェック...")
    try:
        result = subprocess.run([
            sys.executable, '-m', 'py_compile', 'app.py'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ app.py 構文OK")
        else:
            print(f"❌ app.py 構文エラー:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ 構文チェック失敗: {e}")
        return False
    
    # 2. インポートテスト
    print("\n2. モジュールインポートテスト...")
    try:
        result = subprocess.run([
            sys.executable, '-c', 
            'import app; print("✅ app.py import successful")'
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print("✅ app.py インポートOK")
            print("STDOUT:", result.stdout)
        else:
            print(f"❌ app.py インポートエラー:")
            print("STDERR:", result.stderr)
            return False
    except Exception as e:
        print(f"❌ インポートテスト失敗: {e}")
        return False
    
    # 3. ルート登録テスト
    print("\n3. comprehensive_dashboard ルート登録テスト...")
    try:
        result = subprocess.run([
            sys.executable, '-c', 
            '''
from app import app
routes = [str(rule) for rule in app.url_map.iter_rules()]
comprehensive_routes = [r for r in routes if "comprehensive_dashboard" in r]
if comprehensive_routes:
    print("✅ comprehensive_dashboard ルート登録済み:", comprehensive_routes[0])
else:
    print("❌ comprehensive_dashboard ルート未登録")
    print("Available admin routes:")
    admin_routes = [r for r in routes if "admin" in r]
    for route in admin_routes[:10]:
        print("  -", route)
'''
        ], capture_output=True, text=True, timeout=15)
        
        print("ルートテスト結果:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        if "✅ comprehensive_dashboard ルート登録済み" in result.stdout:
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ ルートテスト失敗: {e}")
        return False

if __name__ == "__main__":
    success = test_app_startup()
    if success:
        print("\n🚀 app.py は正常に起動できます")
        print("💡 次の手順: python app.py")
    else:
        print("\n❌ app.py に問題があります")
        print("🔧 エラーを修正してから再試行してください")