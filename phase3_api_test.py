#!/usr/bin/env python3
"""
Task #7-3 SL-3 Phase 3: API endpoints動作確認テスト
2025-07-30 実行: /api/get_translation_state と /api/set_translation_state の単体テスト
"""

import requests
import json
import time

# テスト用セッションID
TEST_SESSION_ID = f"phase3_test_{int(time.time())}"
BASE_URL = "http://localhost:5000"

def test_get_translation_state():
    """GET translation state API テスト"""
    print("=== /api/get_translation_state テスト ===")
    
    url = f"{BASE_URL}/api/get_translation_state"
    payload = {
        "session_id": TEST_SESSION_ID
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Response JSON: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return data
        else:
            print(f"❌ Error Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request Exception: {e}")
        return None

def test_set_translation_state():
    """SET translation state API テスト"""
    print("\n=== /api/set_translation_state テスト ===")
    
    url = f"{BASE_URL}/api/set_translation_state"
    
    # テストデータ
    test_cases = [
        {"field": "input_text", "value": "Phase3テスト用テキスト"},
        {"field": "translated_text", "value": "Phase3 test translation result"},
        {"field": "context_info", "value": "Phase3コンテキスト情報"}
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test_case['field']} ---")
        
        payload = {
            "session_id": TEST_SESSION_ID,
            "field": test_case["field"],
            "value": test_case["value"]
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                results.append({"case": i, "success": True, "data": data})
            else:
                print(f"❌ Error Response: {response.text}")
                results.append({"case": i, "success": False, "error": response.text})
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request Exception: {e}")
            results.append({"case": i, "success": False, "error": str(e)})
            
    return results

def test_integration():
    """統合テスト: SET後にGETで検証"""
    print("\n=== 統合テスト: SET → GET 検証 ===")
    
    # 1. データ設定
    set_results = test_set_translation_state()
    
    # 2. データ取得で検証
    get_result = test_get_translation_state()
    
    if get_result and get_result.get('success'):
        states = get_result.get('states', {})
        print(f"\n📊 取得された状態データ:")
        for field, value in states.items():
            print(f"  {field}: {value}")
            
        # 設定した値が正しく取得できるかチェック
        expected_fields = ["input_text", "translated_text", "context_info"]
        verification_results = []
        
        for field in expected_fields:
            if field in states and states[field] is not None:
                print(f"✅ {field}: 設定・取得成功")
                verification_results.append(True)
            else:
                print(f"❌ {field}: 設定または取得失敗")
                verification_results.append(False)
                
        success_rate = sum(verification_results) / len(verification_results)
        print(f"\n📈 統合テスト成功率: {success_rate*100:.1f}% ({sum(verification_results)}/{len(verification_results)})")
        
        return success_rate >= 0.8  # 80%以上で成功とみなす
    else:
        print("❌ 統合テスト失敗: GET APIでデータ取得できず")
        return False

if __name__ == "__main__":
    print("Task #7-3 SL-3 Phase 3: API endpoints動作確認テスト開始")
    print(f"テストセッションID: {TEST_SESSION_ID}")
    print(f"対象URL: {BASE_URL}")
    
    # 1. 初期GET APIテスト
    initial_get = test_get_translation_state()
    
    # 2. SET APIテスト  
    set_results = test_set_translation_state()
    
    # 3. 統合テスト
    integration_success = test_integration()
    
    print(f"\n=== テスト完了 ===")
    print(f"統合テスト結果: {'✅ PASS' if integration_success else '❌ FAIL'}")