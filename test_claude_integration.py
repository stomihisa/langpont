#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Claude API統合テストスクリプト
Task 2.9.2 Phase B-3.5.7
"""

import os
import sys
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

print("=== Claude API統合テスト開始 ===")

# 1. anthropicライブラリのインポート確認
try:
    from anthropic import Anthropic
    print("✅ anthropicライブラリ: インポート成功")
except ImportError as e:
    print(f"❌ anthropicライブラリ: インポート失敗 - {e}")
    sys.exit(1)

# 2. CLAUDE_API_KEYの確認
claude_api_key = os.getenv("CLAUDE_API_KEY")
if claude_api_key:
    print(f"✅ CLAUDE_API_KEY: 設定済み (長さ: {len(claude_api_key)}文字)")
    # セキュリティのため最初の10文字のみ表示
    print(f"   キーの先頭: {claude_api_key[:10]}...")
else:
    print("❌ CLAUDE_API_KEY: 未設定")
    sys.exit(1)

# 3. Claude clientの初期化テスト
try:
    claude_client = Anthropic(api_key=claude_api_key)
    print("✅ Claude client: 初期化成功")
except Exception as e:
    print(f"❌ Claude client: 初期化失敗 - {e}")
    sys.exit(1)

# 4. app.pyのインポートテスト
try:
    import app
    print("✅ app.py: インポート成功")
    
    # Claude clientが正しく初期化されているか確認
    if hasattr(app, 'claude_client'):
        if app.claude_client:
            print("✅ app.claude_client: 正常に初期化されています")
        else:
            print("⚠️  app.claude_client: None (APIキー問題の可能性)")
    else:
        print("❌ app.claude_client: 属性が見つかりません")
        
except Exception as e:
    print(f"❌ app.py: インポート失敗 - {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 5. Claude API接続テスト（オプション）
print("\n=== Claude API接続テスト ===")
test_connection = input("Claude APIへの接続テストを実行しますか？ (y/n): ").lower().strip()

if test_connection == 'y':
    try:
        response = claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            temperature=0.0,
            messages=[{
                "role": "user",
                "content": "Hello Claude! Please respond with: 'API connection successful!'"
            }]
        )
        
        result = response.content[0].text.strip()
        print(f"✅ Claude API応答: {result}")
        
    except Exception as e:
        print(f"❌ Claude API接続エラー: {e}")

print("\n=== テスト完了 ===")
print("✅ Claude API統合の基本設定は正常です")