#!/usr/bin/env python3
"""
SL-3 Phase 2 パフォーマンステスト
Cookieサイズ測定とエラー耐性テスト

使用方法:
python sl3_phase2_performance_test.py
"""

import requests
import json
import sys
import time
from typing import Dict, Any

def measure_cookie_size(response):
    """レスポンスのCookieサイズを測定"""
    if 'Set-Cookie' in response.headers:
        cookie_data = response.headers['Set-Cookie']
        return len(cookie_data.encode('utf-8'))
    return 0

def test_translation_performance():
    """翻訳パフォーマンステスト（Cookieサイズ測定）"""
    print("🚀 SL-3 Phase 2 パフォーマンステスト開始")
    
    # テストデータ
    test_data = {
        "japanese_text": "これは大容量データのRedis外部化テストです。" * 10,  # 長文テスト
        "partner_message": "パフォーマンステスト用のパートナーメッセージ" * 5,
        "context_info": "パフォーマンステスト用のコンテキスト情報" * 3,
        "language_pair": "ja-en"
    }
    
    print(f"📝 テストデータサイズ:")
    print(f"  japanese_text: {len(test_data['japanese_text'])} chars")
    print(f"  partner_message: {len(test_data['partner_message'])} chars")
    print(f"  context_info: {len(test_data['context_info'])} chars")
    
    try:
        # 翻訳実行
        print("\n🔄 翻訳実行中...")
        response = requests.post(
            "http://127.0.0.1:8080/translate_chatgpt",
            headers={"Content-Type": "application/json"},
            json=test_data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ 翻訳成功")
                
                # Cookieサイズ測定
                cookie_size = measure_cookie_size(response)
                print(f"🍪 Cookieサイズ: {cookie_size} bytes")
                
                # レスポンスサイズ測定
                response_size = len(response.content)
                print(f"📦 レスポンスサイズ: {response_size} bytes")
                
                # 翻訳結果の確認
                translations = {
                    'translated_text': len(result.get('translated_text', '')),
                    'better_translation': len(result.get('better_translation', '')),
                    'gemini_translation': len(result.get('gemini_translation', ''))
                }
                print(f"📊 翻訳結果サイズ:")
                for key, size in translations.items():
                    print(f"  {key}: {size} chars")
                
                return {
                    'success': True,
                    'cookie_size': cookie_size,
                    'response_size': response_size,
                    'translations': translations
                }
            else:
                print(f"❌ 翻訳失敗: {result.get('error', 'Unknown error')}")
                return {'success': False, 'error': result.get('error')}
        else:
            print(f"❌ HTTP エラー: {response.status_code}")
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
    except requests.exceptions.RequestException as e:
        print(f"❌ リクエストエラー: {e}")
        return {'success': False, 'error': str(e)}

def test_redis_key_verification():
    """Redisキーの作成確認テスト"""
    print("\n🔍 Redisキー確認テスト")
    
    import subprocess
    try:
        # 大容量データキーの確認
        result = subprocess.run(
            ['redis-cli', 'KEYS', 'langpont:dev:translation_state:*:translated_text'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            keys = result.stdout.strip().split('\n') if result.stdout.strip() else []
            print(f"📋 translated_textキー数: {len(keys)}")
            
            # 最新のキーのTTL確認
            if keys:
                latest_key = keys[-1]
                ttl_result = subprocess.run(
                    ['redis-cli', 'TTL', latest_key],
                    capture_output=True, text=True, timeout=5
                )
                if ttl_result.returncode == 0:
                    ttl = ttl_result.stdout.strip()
                    print(f"🕒 最新キーTTL: {ttl}秒")
                    
        # 分析データキーの確認
        result = subprocess.run(
            ['redis-cli', 'KEYS', 'langpont:dev:translation_state:*:gemini_3way_analysis'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            keys = result.stdout.strip().split('\n') if result.stdout.strip() else []
            print(f"📋 gemini_3way_analysisキー数: {len(keys)}")
            
        return True
        
    except subprocess.TimeoutExpired:
        print("⏰ Redis確認タイムアウト")
        return False
    except Exception as e:
        print(f"❌ Redis確認エラー: {e}")
        return False

def main():
    """メイン実行関数"""
    print("=" * 60)
    print("SL-3 Phase 2 パフォーマンステスト")
    print("大容量データRedis外部化の効果測定")
    print("=" * 60)
    
    # 翻訳パフォーマンステスト
    result = test_translation_performance()
    
    if result['success']:
        # Redisキー確認
        test_redis_key_verification()
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print("📊 テスト結果サマリー")
        print("=" * 60)
        print(f"✅ 翻訳実行: 成功")
        print(f"🍪 Cookieサイズ: {result['cookie_size']} bytes")
        print(f"📦 レスポンスサイズ: {result['response_size']} bytes")
        
        # Cookie削減効果の推定
        estimated_original_size = sum(result['translations'].values()) * 2  # 推定元サイズ
        reduction_ratio = (estimated_original_size - result['cookie_size']) / estimated_original_size * 100
        print(f"📉 推定Cookie削減効果: {reduction_ratio:.1f}%")
        
        if result['cookie_size'] < 2000:  # 目標: 2KB以下
            print("🎯 目標達成: Cookieサイズが2KB以下")
        else:
            print("⚠️ 改善余地: Cookieサイズがまだ大きい")
            
        print("\n✅ SL-3 Phase 2 パフォーマンステスト完了")
        
    else:
        print(f"\n❌ テスト失敗: {result.get('error', 'Unknown error')}")
        print("アプリケーションが正常に動作していることを確認してください")
        sys.exit(1)

if __name__ == "__main__":
    main()