"""
LangPont API自動テスト
Task AUTO-TEST-1: 翻訳API基本動作テスト
"""

import requests
import time
import json

def test_translation_api():
    """翻訳API基本動作テスト"""
    print("🔍 API Test: 翻訳API動作確認開始...")
    
    payload = {
        "japanese_text": "こんにちは、世界",
        "language_pair": "ja-fr",
        "partner_message": "",
        "context_info": ""
    }
    
    try:
        # API呼び出し
        print("📡 ChatGPT翻訳API呼び出し中...")
        response = requests.post(
            "http://localhost:8080/translate_chatgpt", 
            json=payload,
            timeout=30
        )
        
        # 結果検証
        assert response.status_code == 200, f"Status code: {response.status_code}"
        data = response.json()
        assert data.get("success") == True, f"API Success flag: {data.get('success')}"
        assert len(data.get("translated_text", "")) > 0, "Empty translation result"
        
        translated_text = data.get("translated_text", "")
        print(f"✅ API Test: 翻訳成功 - '{translated_text[:50]}...'")
        return True
        
    except requests.exceptions.Timeout:
        print("❌ API Test: タイムアウト（30秒）")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ API Test: 接続エラー (Flask未起動?)")
        return False
    except AssertionError as e:
        print(f"❌ API Test: アサーションエラー - {e}")
        return False
    except Exception as e:
        print(f"❌ API Test: 予期しないエラー - {e}")
        return False

def test_index_page():
    """メインページアクセステスト"""
    print("🔍 Page Test: メインページアクセス確認...")
    
    try:
        response = requests.get("http://localhost:8080", timeout=10)
        assert response.status_code == 200, f"Status code: {response.status_code}"
        assert "LangPont" in response.text, "LangPont not found in page"
        
        print("✅ Page Test: メインページアクセス成功")
        return True
        
    except Exception as e:
        print(f"❌ Page Test: エラー - {e}")
        return False

if __name__ == "__main__":
    print("🚀 API自動テスト単体実行")
    success = test_index_page() and test_translation_api()
    if success:
        print("🎉 全APIテスト成功")
    else:
        print("💥 APIテスト失敗")
        exit(1)