#!/usr/bin/env python3
"""
Task #9-4 AP-1 Phase 4 Step3 - 軽量ユニットテスト
目的: APIレスポンスに内部正規化キー＋後方互換キーが全て存在することのみをassert
"""

import json
import requests
import time
import sys

# テスト設定
BASE_URL = "http://localhost:8080"
ENDPOINT = "/reverse_better_translation"
TIMEOUT = 10

def get_csrf_token():
    """開発用CSRFトークン取得"""
    try:
        response = requests.get(f"{BASE_URL}/api/dev/csrf-token", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            return data.get('csrf_token', 'dummy_token')
    except Exception as e:
        print(f"⚠️  CSRFトークン取得失敗: {e}")
    
    return 'dummy_token'

def test_response_keys():
    """Step3契約テスト: レスポンスキー存在確認"""
    print("🧪 test_response_keys: レスポンスキー存在確認")
    
    # CSRFトークン取得
    csrf_token = get_csrf_token()
    
    # テストペイロード
    payload = {
        "french_text": "Bonjour le monde",
        "language_pair": "ja-fr"
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf_token
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}{ENDPOINT}",
            json=payload,
            headers=headers,
            timeout=TIMEOUT
        )
        
        print(f"  📡 HTTPステータス: {response.status_code}")
        
        # 200以外の場合は詳細情報を表示して継続
        if response.status_code != 200:
            print(f"  ⚠️  非200レスポンス - レスポンス内容: {response.text[:200]}")
            return False
        
        # JSONパース
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"  ❌ JSONパースエラー: {e}")
            return False
        
        # 基本成功確認
        assert data.get('success') is True, f"success フィールドが True でない: {data.get('success')}"
        print("  ✅ success: True")
        
        # 必須キー存在確認（Step3契約）
        required_keys = [
            # 内部正規化キー
            "reverse_text",
            
            # 後方互換キー
            "reversed_text",                # reverse_better_translationエンドポイント
            "reverse_translated_text",      # ChatGPT逆翻訳互換
            # "gemini_reverse_translation",   # Gemini逆翻訳互換（このエンドポイントでは非対象）
            # "reverse_better_translation"    # Better逆翻訳互換（このエンドポイントでは非対象）
        ]
        
        missing_keys = []
        for key in required_keys:
            if key in data:
                print(f"  ✅ {key}: 存在")
            else:
                missing_keys.append(key)
                print(f"  ❌ {key}: 不在")
        
        # アサーション
        assert len(missing_keys) == 0, f"必須キーが不足: {missing_keys}"
        
        # 値の妥当性確認（文字列かつ非空）
        for key in required_keys:
            if key in data:
                value = data[key]
                assert isinstance(value, str), f"{key} は文字列である必要がある: {type(value)}"
                assert len(value.strip()) > 0, f"{key} は非空文字列である必要がある: '{value}'"
                print(f"  ✅ {key}: 妥当な値 (長さ: {len(value)})")
        
        print("  🎯 全ての必須キーが存在し、妥当な値を持つ")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"  ❌ リクエストエラー: {e}")
        return False
    except AssertionError as e:
        print(f"  ❌ アサーションエラー: {e}")
        return False
    except Exception as e:
        print(f"  ❌ 予期しないエラー: {e}")
        return False

def test_error_response_format():
    """エラーレスポンス形式確認"""
    print("🧪 test_error_response_format: エラーレスポンス形式確認")
    
    # 不正なペイロード（空文字列）
    payload = {
        "french_text": "",
        "language_pair": "ja-fr"
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-CSRFToken": get_csrf_token()
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}{ENDPOINT}",
            json=payload,
            headers=headers,
            timeout=TIMEOUT
        )
        
        print(f"  📡 HTTPステータス: {response.status_code}")
        
        if response.status_code == 200:
            # 空入力でも成功する場合があるので、レスポンス内容を確認
            data = response.json()
            success = data.get('success', False)
            print(f"  📋 success: {success}")
            
            if not success:
                # エラーレスポンスの場合
                assert 'error' in data, "エラー時は 'error' キーが必要"
                print(f"  ✅ エラーメッセージ: {data['error']}")
            
        return True
        
    except Exception as e:
        print(f"  ❌ エラーレスポンステストで例外: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🚀 Task #9-4 AP-1 Phase 4 Step3 - 契約テスト開始")
    print(f"対象: {BASE_URL}{ENDPOINT}")
    
    # サーバー接続確認
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"✅ サーバー接続確認: {response.status_code}")
    except Exception as e:
        print(f"❌ サーバーに接続できません: {e}")
        print("   python app.py でサーバーを起動してください")
        return False
    
    # テスト実行
    tests = [
        test_response_keys,
        test_error_response_format
    ]
    
    results = []
    for test_func in tests:
        print()
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ テスト関数 {test_func.__name__} で例外: {e}")
            results.append(False)
    
    # 結果サマリー
    print()
    print("📊 テスト結果サマリー")
    passed = sum(results)
    total = len(results)
    print(f"✅ 成功: {passed}/{total}")
    
    if passed == total:
        print("🎯 全てのテストが成功 - Step3契約を満たしています")
        return True
    else:
        print("❌ 一部テストが失敗 - 実装を確認してください")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)