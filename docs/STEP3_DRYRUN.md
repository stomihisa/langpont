# Task #9-4 AP-1 Phase 4 Step3 - Dry-Run (文章での差し替え通し)

## 5呼び出し点ごとのBefore/After

### 1. debug_gemini_reverse_translation (app.py:L1346)

#### Before (現在)
```python
reverse_result = f_reverse_translation(gemini_translation, target_lang, source_lang)
```

#### After (Step3後)
```python
# デバッグ関数はそのまま保持（UI更新なし）
reverse_result = f_reverse_translation(gemini_translation, target_lang, source_lang)
```

**引数・戻り値・例外パターン**:
- 引数: `gemini_translation: str`, `target_lang: str`, `source_lang: str`
- 戻り値: `str` (逆翻訳結果)
- 空入力: `"(翻訳テキストが空です)"`
- timeout/失敗: `"逆翻訳エラー: {error}"`

**UIでの表示**:
- 変更なし（デバッグ関数のためUI更新なし）

---

### 2. runFastTranslation - ChatGPT逆翻訳 (app.py:L2378)

#### Before (現在)
```python
reverse = f_reverse_translation(translated, target_lang, source_lang, current_lang)
```

#### After (Step3後)
```python
reverse = translation_service.reverse_translation(translated, target_lang, source_lang, current_lang)
```

**引数・戻り値・例外パターン**:
- 引数: `translated: str`, `target_lang: str`, `source_lang: str`, `current_lang: str`
- 戻り値: `str` (逆翻訳結果)
- 空入力: `"(翻訳テキストが空です)"`
- timeout/失敗: `"逆翻訳エラー: {error}"`

**UIでの表示・トーストの挙動**:
- DOM更新: `document.getElementById("reverse-translated-text").innerText = data.reverse_translated_text`
- コピー: `copyContent('reverse-translated-text', 'toast-translated', button)`
- トースト: `showToastNearButton('toast-translated', button)` - 文言変更なし

---

### 3. runFastTranslation - Gemini逆翻訳 (app.py:L2480)

#### Before (現在)
```python
gemini_reverse_translation = f_reverse_translation(gemini_translation, target_lang, source_lang, current_lang)
```

#### After (Step3後)
```python
gemini_reverse_translation = translation_service.reverse_translation(gemini_translation, target_lang, source_lang, current_lang)
```

**引数・戻り値・例外パターン**:
- 引数: `gemini_translation: str`, `target_lang: str`, `source_lang: str`, `current_lang: str`
- 戻り値: `str` (逆翻訳結果)
- 空入力: `"(翻訳テキストが空です)"`
- timeout/失敗: `"逆翻訳エラー: {error}"`
- 条件チェック: エラー文字列で始まる場合は実行スキップ

**UIでの表示・トーストの挙動**:
- DOM更新: `document.getElementById("gemini-reverse-translation").innerText = data.gemini_reverse_translation`
- フォールバック: `window.currentLabels.no_reverse_result` または `"(逆翻訳結果なし)"`
- コピー: 既存のコピー機能 - 文言変更なし

---

### 4. runFastTranslation - Better逆翻訳 (app.py:L2522)

#### Before (現在)
```python
reverse_better = f_reverse_translation(better_translation, target_lang, source_lang, current_lang)
```

#### After (Step3後)
```python
reverse_better = translation_service.reverse_translation(better_translation, target_lang, source_lang, current_lang)
```

**引数・戻り値・例外パターン**:
- 引数: `better_translation: str`, `target_lang: str`, `source_lang: str`, `current_lang: str`
- 戻り値: `str` (逆翻訳結果)
- 空入力: `"(翻訳テキストが空です)"`
- timeout/失敗: 空文字列 `""` (例外でキャッチされる)
- 条件チェック: エラー文字列で始まる場合は実行スキップ

**UIでの表示・トーストの挙動**:
- DOM更新: `data.reverse_better_translation` でレスポンス内包含
- 表示: 別のエンドポイント経由またはrunFastTranslationレスポンス - 文言変更なし

---

### 5. reverse_better_translation エンドポイント (app.py:L2902)

#### Before (現在)
```python
@app.route("/reverse_better_translation", methods=["POST"])
@require_rate_limit  # ⚠️ @csrf_protectが不足
def reverse_better_translation():
    # ...
    reversed_text = f_reverse_translation(improved_text, target_lang, source_lang)
    # ...
    return jsonify({"success": True, "reversed_text": reversed_text})
```

#### After (Step3後)
```python
@app.route("/reverse_better_translation", methods=["POST"])
@csrf_protect        # ✅ 追加必須
@require_rate_limit
def reverse_better_translation():
    # ...
    reversed_text = translation_service.reverse_translation(improved_text, target_lang, source_lang)
    # ...
    # レスポンス正規化アダプタ適用
    return jsonify({
        "success": True,
        "reverse_text": reversed_text,           # 内部正規化キー
        "reversed_text": reversed_text,          # 後方互換キー
        "reverse_translated_text": reversed_text  # 統一後方互換
    })
```

**引数・戻り値・例外パターン**:
- リクエスト: `{"french_text": str, "language_pair": str}`
- 成功レスポンス: `{"success": true, "reverse_text": str, "reversed_text": str, ...}`
- エラーレスポンス: `{"success": false, "error": str}`
- 空入力: `{"success": false, "error": "逆翻訳するテキストが見つかりません"}`
- CSRF未送信: HTTP 403 + `{"success": false, "error": "CSRF token missing"}`
- レート制限: HTTP 429 + `{"success": false, "error": "Too many requests"}`

**UIでの表示・トーストの挙動**:
- AJAX呼び出し: `fetch("/reverse_better_translation", {...})`
- DOM更新: `reverseBetterElement.innerText = reverseBetterData.reversed_text || "(逆翻訳結果なし)"`
- エラー表示: アラートまたはコンソールログ - 文言変更なし

## @csrf_protect付与の明文化

### 必須対応
- **reverse_better_translationエンドポイント**: `@csrf_protect` デコレータを追加
- **セキュリティ統一**: 他のPOSTエンドポイントと同等の保護レベル確保
- **互換性維持**: CSRFトークン送信は既存UIで実装済み

## 想定外の深掘り課題

### なし (実装開始可能)

現在の調査とDry-Runの結果、想定外の複雑化要因は検出されませんでした。以下が確認済み：

✅ **依存関係**: Service層のメソッドは既に実装済み
✅ **エラーハンドリング**: 既存パターンを踏襲可能
✅ **UI影響**: DOM/JavaScript変更不要
✅ **セキュリティ**: CSRFトークン送信機構は実装済み
✅ **後方互換性**: 4つのレスポンスキー併記で保護可能

**実装リスク評価**: 低 - 標準的なService層統合とレスポンス正規化