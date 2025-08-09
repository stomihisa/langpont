# Task #9-4 AP-1 Phase 4 - Service層メソッド設計仕様書

## 📋 Service層拡張設計

### TranslationService クラス拡張

#### 現状のTranslationService
```python
# services/translation_service.py
class TranslationService:
    def __init__(self, openai_client, logger, labels, usage_checker, translation_state_manager)
    def translate_with_chatgpt(self, ...) -> str
```

#### Phase 4で追加するメソッド

---

## 🔄 reverse_translation メソッド

### 基本仕様
```python
def reverse_translation(self, translated_text: str, target_lang: str, source_lang: str, 
                       current_lang: str = "jp") -> str:
    """
    翻訳結果を逆方向に翻訳する（逆翻訳）
    
    Args:
        translated_text (str): 逆翻訳対象のテキスト（必須）
        target_lang (str): 元の翻訳先言語（逆翻訳では翻訳元になる）
        source_lang (str): 元の翻訳元言語（逆翻訳では翻訳先になる）
        current_lang (str): UI表示言語（デフォルト: "jp"）
    
    Returns:
        str: 逆翻訳された結果テキスト
        
    Raises:
        ValueError: 入力値検証エラー（空テキスト、無効言語ペア）
        Exception: OpenAI APIエラー、ネットワークエラー等
    """
```

### 内部処理フロー
1. **入力値検証**
   - `EnhancedInputValidator.validate_text_input()`: テキスト妥当性確認
   - `EnhancedInputValidator.validate_language_pair()`: 言語ペア妥当性確認
   
2. **翻訳実行**
   - `safe_openai_request()`: セキュリティ強化版OpenAI API呼び出し
   - プロンプト: 「Professional translation task: Translate to {source_label}」
   - 最大トークン: 300

3. **エラーハンドリング**
   - API呼び出し失敗 → "逆翻訳エラー: {error_message}"
   - 空結果 → "(翻訳テキストが空です)"

### 使用例
```python
# サービス経由での呼び出し
result = translation_service.reverse_translation(
    "Hello world", "en", "ja", "jp"
)
# 期待結果: "こんにちは世界"
```

---

## ✨ better_translation メソッド

### 基本仕様
```python
def better_translation(self, text_to_improve: str, source_lang: str = "fr", 
                      target_lang: str = "en", current_lang: str = "jp") -> str:
    """
    翻訳結果をより自然な表現に改善する
    
    Args:
        text_to_improve (str): 改善対象のテキスト（必須）
        source_lang (str): 翻訳元言語（デフォルト: "fr"）
        target_lang (str): 翻訳先言語（デフォルト: "en"）
        current_lang (str): UI表示言語（デフォルト: "jp"）
    
    Returns:
        str: 改善された翻訳テキスト
        
    Raises:
        ValueError: 入力値検証エラー（空テキスト、無効言語ペア）
        Exception: OpenAI APIエラー、ネットワークエラー等
    """
```

### 内部処理フロー
1. **入力値検証**
   - `EnhancedInputValidator.validate_text_input()`: テキスト妥当性確認
   - `EnhancedInputValidator.validate_language_pair()`: 言語ペア妥当性確認

2. **翻訳改善実行**
   - 言語マッピング: {"ja": "日本語", "fr": "フランス語", "en": "英語", ...}
   - プロンプト: 「この{target_label}をもっと自然な{target_label}の文章に改善してください：{text}」
   - `safe_openai_request()`: セキュリティ強化版API呼び出し

3. **結果返却**
   - 改善されたテキストを直接返却

### 使用例
```python
# サービス経由での呼び出し
result = translation_service.better_translation(
    "This is good translation", "en", "en", "jp"
)
# 期待結果: "これは良い翻訳です" → より自然な表現に改善
```

---

## 🏗️ 実装時の技術要件

### 依存関係
```python
# 必要なインポート（既存のTranslationServiceに追加）
from security.input_validation import EnhancedInputValidator
# safe_openai_request() は既存のapp.pyから移動または参照
```

### セキュリティ考慮事項
1. **入力値検証**: `EnhancedInputValidator` を使用した厳密なバリデーション
2. **安全なAPI呼び出し**: `safe_openai_request()` による統一されたOpenAI API呼び出し
3. **エラー情報の制限**: 機密情報の漏洩防止

### パフォーマンス考慮事項
1. **API呼び出し最適化**: 不要な呼び出しの防止
2. **エラー時の高速フォールバック**: 例外発生時の即座なエラーレスポンス
3. **ログ記録**: デバッグ用の適切なログ出力

---

## 🔌 Blueprint統合設計

### 新規エンドポイントの実装

#### /better_translation エンドポイント
```python
# routes/translation.py に追加
@translation_bp.route('/better_translation', methods=['POST'])
@csrf_protect
@require_rate_limit
def better_translation_endpoint():
    """
    改善翻訳APIエンドポイント
    """
    # リクエストデータ取得
    data = request.get_json() or {}
    text_to_improve = data.get("text", "")
    source_lang = data.get("source_lang", "fr") 
    target_lang = data.get("target_lang", "en")
    current_lang = session.get("lang", "jp")
    
    # Service層呼び出し
    result = translation_service.better_translation(
        text_to_improve, source_lang, target_lang, current_lang
    )
    
    return jsonify({
        "success": True,
        "improved_text": result
    })
```

#### /reverse_chatgpt_translation エンドポイント
```python
# routes/translation.py に追加
@translation_bp.route('/reverse_chatgpt_translation', methods=['POST'])
@csrf_protect  
@require_rate_limit
def reverse_chatgpt_translation():
    """
    ChatGPT翻訳逆翻訳APIエンドポイント
    """
    # リクエストデータ取得
    data = request.get_json() or {}
    translated_text = data.get("translated_text", "")
    language_pair = data.get("language_pair", "ja-en")
    target_lang, source_lang = language_pair.split("-")
    current_lang = session.get("lang", "jp")
    
    # Service層呼び出し
    result = translation_service.reverse_translation(
        translated_text, target_lang, source_lang, current_lang
    )
    
    return jsonify({
        "success": True,
        "reversed_text": result
    })
```

---

## 📊 移行計画

### Step 1: Service層メソッド実装
1. `services/translation_service.py` に2メソッド追加
2. app.pyから`safe_openai_request`関数の参照追加
3. 単体テスト実行

### Step 2: Blueprint エンドポイント追加  
1. `routes/translation.py` に2エンドポイント追加
2. 依存注入の設定（app.pyでのService初期化）
3. エンドポイントテスト実行

### Step 3: 既存コードの段階的移行
1. app.py内の呼び出しをService経由に変更
2. 既存の`/reverse_better_translation`をBlueprintに移動
3. 統合テスト実行

### Step 4: クリーンアップ
1. app.py内の不要な関数定義削除（必要に応じて）
2. import文の整理
3. 最終テスト実行

---

## ⚠️ 実装時の注意事項

### 破壊的変更の防止
- app.py内の既存関数は段階的に移行
- 必要に応じてwrapper関数を残し、後方互換性を確保

### エラーハンドリングの統一
- 全エンドポイントで一貫したエラーレスポンス形式
- 適切なHTTPステータスコード（400, 500等）の返却

### セキュリティの維持
- 全新規エンドポイントに`@csrf_protect`, `@require_rate_limit`適用
- 入力値検証の厳密な実行

---

**設計日**: 2025年8月9日  
**Task**: Task #9-4 AP-1 Phase 4  
**目的**: Better Translation・Reverse TranslationのService層Blueprint化設計