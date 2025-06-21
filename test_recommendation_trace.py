#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Task 2.9.2 Phase B-3.5.7: 推奨抽出システム完全トレース
"""

import os
import sys
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# app.pyをインポート
sys.path.append('/Users/shintaro_imac_2/langpont')

try:
    from app import extract_recommendation_from_analysis
    print('✅ extract_recommendation_from_analysis インポート成功')
except Exception as e:
    print(f'❌ インポートエラー: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# テスト用のClaude分析結果（Enhanced推奨）
test_claude_analysis = '''
私はClaude AIとして、この3つの翻訳を慎重に分析いたします。

**ChatGPT Translation:** "I would like to meet at 3 PM tomorrow."
**Enhanced Translation:** "I would appreciate the opportunity to meet at 3 PM tomorrow."
**Gemini Translation:** "I would like to arrange a meeting at 3 PM tomorrow."

## 分析結果

1. **ChatGPT Translation**は基本的な翻訳として適切ですが、やや直接的な表現です。

2. **Enhanced Translation**は最も丁寧で適切な表現です。"I would appreciate the opportunity"という表現により、相手への敬意と謙虚さが表現され、ビジネスシーンにおいて最も適切な選択肢です。

3. **Gemini Translation**は"arrange a meeting"という表現で会議の設定を示していますが、Enhanced Translationほど丁寧ではありません。

## 推奨結果
文脈を考慮すると、**2. Enhanced Translation**が最も適切です。相手への敬意を示しながら、自然で丁寧な英語表現となっています。
'''

print('\n=== Task 2.9.2 Phase B-3.5.7: 推奨抽出システム完全トレース ===\n')

# 1. プロンプト生成のテスト
print('1. **ChatGPTへのプロンプト全文**')
print('送信プロンプト：')

# 日本語プロンプトを表示（session.get('lang', 'jp')なのでjpがデフォルト）
engine_name = 'Claude'
prompt = f"""以下は{engine_name}AIによる3つの翻訳の分析結果です：

{test_claude_analysis}

この分析文章を読んで、{engine_name}AIが推奨している翻訳を特定してください。
選択肢: ChatGPT / Enhanced / Gemini
推奨されている翻訳名のみを回答してください。"""

print(f'[{prompt}]\n')

# 2. 推奨抽出実行
print('2. **推奨抽出実行**')
print('実行中...')

result = extract_recommendation_from_analysis(test_claude_analysis, 'Claude')

print('3. **ChatGPTからの生レスポンス**')
if 'raw_response' in result:
    raw_response = result['raw_response']
    print(f'ChatGPT生レスポンス: "{raw_response}"')
    
    # 3. 正規化処理の詳細表示
    print('\n3. **正規化処理の詳細**')
    print(f'正規化前：\'{raw_response}\'')
    
    # 実際の正規化処理をトレース
    recommendation_lower = raw_response.lower()
    print(f'lower()後：\'{recommendation_lower}\'')
    
    # if文の判定を順番に表示
    if "enhanced" in recommendation_lower:
        print('キーワード判定：「enhanced」にマッチ')
        final_recommendation = "Enhanced"
    elif "chatgpt" in recommendation_lower or "chat" in recommendation_lower:
        print('キーワード判定：「chatgpt」または「chat」にマッチ')
        final_recommendation = "ChatGPT"
    elif "gemini" in recommendation_lower:
        print('キーワード判定：「gemini」にマッチ')
        final_recommendation = "Gemini"
    else:
        print('キーワード判定：いずれにもマッチせず')
        final_recommendation = "none"
    
    print(f'正規化後：\'{final_recommendation}\'')
    
else:
    print(f'❌ 生レスポンスが取得できませんでした: {result}')

print('\n4. **最終推奨結果**')
print(f'最終推奨：{result.get("recommendation", "不明")}')
print(f'信頼度：{result.get("confidence", "不明")}')
print(f'方法：{result.get("method", "不明")}')

# 期待値との比較
expected = 'Enhanced'
actual = result.get('recommendation', '不明')

if actual == expected:
    print('✅ 正しい推奨抽出')
else:
    print(f'❌ 誤った推奨抽出 - {expected}期待, {actual}取得')
    
    # 詳細な問題分析
    if 'raw_response' in result:
        raw = result['raw_response']
        print(f'\n🔍 詳細分析:')
        print(f'- ChatGPT生レスポンス: "{raw}"')
        print(f'- enhanced含有: {"enhanced" in raw.lower()}')
        print(f'- chatgpt含有: {"chatgpt" in raw.lower()}')
        print(f'- gemini含有: {"gemini" in raw.lower()}')

print('\n=== トレース完了 ===')