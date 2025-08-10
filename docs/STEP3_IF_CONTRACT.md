# Task #9-4 AP-1 Phase 4 Step3 - IF契約固定

## API↔UI完全対応表

### 1. debug_gemini_reverse_translation (app.py:L1346)

| 項目 | 仕様 |
|-----|-----|
| **呼び出し起点** | `debug_gemini_reverse_translation(gemini_translation, target_lang, source_lang)` @ app.py:L1346 |
| **Request仕様** | - `gemini_translation: str` (必須)<br>- `target_lang: str` (必須)<br>- `source_lang: str` (必須)<br>- 空時: デバッグ情報で記録、f_reverse_translationに渡る |
| **Response仕様** | - 内部正規化キー: `reverse_text`<br>- 後方互換キー: なし（デバッグ関数）<br>- エラー時: デバッグ辞書内で記録 |
| **UI DOM** | なし（デバッグ関数のためUI更新なし） |

### 2. runFastTranslation - ChatGPT逆翻訳 (app.py:L2378)

| 項目 | 仕様 |
|-----|-----|
| **呼び出し起点** | `reverse = f_reverse_translation(translated, target_lang, source_lang, current_lang)` @ app.py:L2378 |
| **Request仕様** | - `translated: str` (必須、翻訳結果)<br>- `target_lang: str` (必須)<br>- `source_lang: str` (必須)<br>- `current_lang: str` (デフォルト"jp")<br>- 空時: "(翻訳テキストが空です)" |
| **Response仕様** | - 内部正規化キー: `reverse_text`<br>- 後方互換キー: `reverse_translated_text`<br>- エラー時: "逆翻訳エラー: {error}" |
| **UI DOM** | - ID: `reverse-translated-text`<br>- クラス: `result-text`<br>- 更新: `data.reverse_translated_text`<br>- コピー: `copyContent('reverse-translated-text', 'toast-translated', this)` |

### 3. runFastTranslation - Gemini逆翻訳 (app.py:L2480)

| 項目 | 仕様 |
|-----|-----|
| **呼び出し起点** | `gemini_reverse_translation = f_reverse_translation(gemini_translation, target_lang, source_lang, current_lang)` @ app.py:L2480 |
| **Request仕様** | - `gemini_translation: str` (必須)<br>- `target_lang: str` (必須)<br>- `source_lang: str` (必須)<br>- `current_lang: str` (デフォルト"jp")<br>- 条件: エラー文字列で始まらない場合のみ実行 |
| **Response仕様** | - 内部正規化キー: `reverse_text`<br>- 後方互換キー: `gemini_reverse_translation`<br>- エラー時: "逆翻訳エラー: {error}" |
| **UI DOM** | - ID: `gemini-reverse-translation`<br>- クラス: `result-text`<br>- 更新: `data.gemini_reverse_translation`<br>- フォールバック: `window.currentLabels.no_reverse_result` または `"(逆翻訳結果なし)"` |

### 4. runFastTranslation - Better逆翻訳 (app.py:L2522)

| 項目 | 仕様 |
|-----|-----|
| **呼び出し起点** | `reverse_better = f_reverse_translation(better_translation, target_lang, source_lang, current_lang)` @ app.py:L2522 |
| **Request仕様** | - `better_translation: str` (必須)<br>- `target_lang: str` (必須)<br>- `source_lang: str` (必須)<br>- `current_lang: str` (デフォルト"jp")<br>- 条件: エラー文字列で始まらない場合のみ実行 |
| **Response仕様** | - 内部正規化キー: `reverse_text`<br>- 後方互換キー: `reverse_better_translation`<br>- エラー時: 空文字列 `""` |
| **UI DOM** | - ID: 専用DOM要素なし（別エンドポイント経由）<br>- 更新: `data.reverse_better_translation` |

### 5. reverse_better_translation エンドポイント (app.py:L2902)

| 項目 | 仕様 |
|-----|-----|
| **呼び出し起点** | `POST /reverse_better_translation` @ app.py:L2902 |
| **Request仕様** | - `french_text: str` (必須、JSONキー)<br>- `language_pair: str` (デフォルト"ja-fr")<br>- 空時: `{"success": false, "error": "逆翻訳するテキストが見つかりません"}` |
| **Response仕様** | - 成功: `{"success": true, "reversed_text": string}`<br>- 内部正規化キー: `reverse_text`<br>- 後方互換キー: `reversed_text`<br>- エラー時: `{"success": false, "error": string}` |
| **UI DOM** | - 専用UI要素なし（APIエンドポイント）<br>- デコレータ: `@require_rate_limit` のみ<br>- **要追加**: `@csrf_protect` |

## 内部正規化キー統一方針

### 統一内部キー
- **`reverse_text`**: 全ての逆翻訳結果の内部正規化キー

### 後方互換キー（既存UI保護）
1. `reverse_translated_text` - ChatGPT逆翻訳
2. `gemini_reverse_translation` - Gemini逆翻訳
3. `reverse_better_translation` - Better逆翻訳（runFastTranslation内）
4. `reversed_text` - reverse_better_translationエンドポイント

## セキュリティ要件

### 必須デコレータ（統一化）
- `@csrf_protect` - CSRF保護（reverse_better_translationに不足）
- `@require_rate_limit` - レート制限

### エラーレスポンス統一
- HTTPステータス: 200(成功), 400(バリデーションエラー), 403(CSRF), 429(レート制限), 500(内部エラー)
- JSONフォーマット: `{"success": bool, "error": string}` または成功時の各種キー

## UI DOM参照（変更禁止）

### 既存ID（ハイフン区切り）
- `reverse-translated-text` - ChatGPT逆翻訳表示
- `gemini-reverse-translation` - Gemini逆翻訳表示

### 既存JSONキー（アンダーバー区切り）
- `reverse_translated_text` - APIレスポンス
- `gemini_reverse_translation` - APIレスポンス
- `reverse_better_translation` - APIレスポンス
- `reversed_text` - 専用エンドポイント

### イベントハンドラ（変更禁止）
- `copyContent(id, toastId, buttonElement)` - コピー機能
- `showToastNearButton(toastId, buttonElement)` - トースト表示