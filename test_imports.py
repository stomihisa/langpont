#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangPont インポートテストスクリプト
必要なモジュールとライブラリの動作確認
"""

import sys
import traceback

def test_imports():
    """必要なモジュールのインポートテスト"""
    print("=== LangPont インポートテスト ===")
    
    # 基本ライブラリ
    try:
        import flask
        print("✅ Flask: OK")
    except ImportError as e:
        print(f"❌ Flask: {e}")
    
    # bcrypt
    try:
        import bcrypt
        print("✅ bcrypt: OK")
    except ImportError as e:
        print(f"❌ bcrypt: {e}")
        print("   → pip install bcrypt を実行してください")
    
    # LangPontモジュール
    try:
        from config import VERSION, ENVIRONMENT
        print("✅ config.py: OK")
    except Exception as e:
        print(f"❌ config.py: {e}")
    
    try:
        from labels import labels
        print("✅ labels.py: OK")
    except Exception as e:
        print(f"❌ labels.py: {e}")
    
    try:
        from user_auth import UserAuthSystem
        print("✅ user_auth.py: OK")
    except Exception as e:
        print(f"❌ user_auth.py: {e}")
        traceback.print_exc()
    
    try:
        from user_profile import UserProfileManager
        print("✅ user_profile.py: OK")
    except Exception as e:
        print(f"❌ user_profile.py: {e}")
        traceback.print_exc()
    
    try:
        from translation_history import TranslationHistoryManager
        print("✅ translation_history.py: OK")
    except Exception as e:
        print(f"❌ translation_history.py: {e}")
        traceback.print_exc()
    
    try:
        from auth_routes import init_auth_routes
        print("✅ auth_routes.py: OK")
    except Exception as e:
        print(f"❌ auth_routes.py: {e}")
        traceback.print_exc()

def test_database_creation():
    """データベース作成テスト"""
    print("\n=== データベース作成テスト ===")
    
    try:
        from user_auth import UserAuthSystem
        auth_system = UserAuthSystem()
        print("✅ 認証システムデータベース: OK")
    except Exception as e:
        print(f"❌ 認証システムデータベース: {e}")
        traceback.print_exc()
    
    try:
        from user_profile import UserProfileManager
        profile_manager = UserProfileManager()
        print("✅ プロファイル管理データベース: OK")
    except Exception as e:
        print(f"❌ プロファイル管理データベース: {e}")
        traceback.print_exc()
    
    try:
        from translation_history import TranslationHistoryManager
        history_manager = TranslationHistoryManager()
        print("✅ 翻訳履歴データベース: OK")
    except Exception as e:
        print(f"❌ 翻訳履歴データベース: {e}")
        traceback.print_exc()

def test_app_startup():
    """app.py起動テスト"""
    print("\n=== app.py 起動テスト ===")
    
    try:
        import app
        print("✅ app.py インポート: OK")
        
        # Flaskアプリケーションが作成されているか確認
        if hasattr(app, 'app') and app.app:
            print("✅ Flaskアプリケーション作成: OK")
        else:
            print("❌ Flaskアプリケーション作成: NG")
        
    except Exception as e:
        print(f"❌ app.py インポート: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_imports()
    test_database_creation()
    test_app_startup()
    print("\n=== テスト完了 ===")