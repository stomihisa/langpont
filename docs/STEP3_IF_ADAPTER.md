# Task #9-4 AP-1 Phase 4 Step3 - 正規化アダプタ設計

## レスポンス正規化と後方互換性アダプタ設計

### 内部正規化方針

**Controller層での統一処理**:
```python
# Service層から取得（内部正規化キー）
reverse_text = translation_service.reverse_translation(text, target_lang, source_lang, current_lang)

# レスポンス構築（後方互換キー併記）
response_data = {
    # 内部正規化キー（将来のメイン）
    "reverse_text": reverse_text,
    
    # 後方互換キー（既存UI保護）
    "reverse_translated_text": reverse_text,      # ChatGPT逆翻訳
    "gemini_reverse_translation": reverse_text,    # Gemini逆翻訳  
    "reverse_better_translation": reverse_text,    # Better逆翻訳
    "reversed_text": reverse_text                   # reverse_better_translationエンドポイント
}
```

### エラー時の返却構造

**HTTPステータス別レスポンス**:
```python
# 成功時 (200)
{"success": True, "reverse_text": string, "reverse_translated_text": string, ...}

# バリデーションエラー (400)
{"success": False, "error": "入力値が不正です"}

# CSRF未送信 (403)
{"success": False, "error": "CSRF token missing"}

# レート制限超過 (429)
{"success": False, "error": "Too many requests"}

# 内部エラー (500)
{"success": False, "error": "Internal server error"}
```

### UIアクセス方針

**既存DOM/JSは変更なし**:
- UI側は既存の後方互換キーのみ参照
- `data.reverse_translated_text`、`data.gemini_reverse_translation` 等
- DOM要素ID（`reverse-translated-text`、`gemini-reverse-translation`）は保持

### セキュリティ統一

**必須デコレータ（全エンドポイント統一）**:
```python
@csrf_protect      # ⚠️ reverse_better_translationに不足 → 追加必須
@require_rate_limit
def reverse_better_translation():
```

### 実装順序

1. **Service層統合**: 5箇所 → `translation_service.reverse_translation()`
2. **レスポンス正規化**: 内部キー + 後方互換キー併記
3. **セキュリティ統一**: `@csrf_protect` 追加
4. **既存UI保護**: DOM/JS変更なしで動作確認