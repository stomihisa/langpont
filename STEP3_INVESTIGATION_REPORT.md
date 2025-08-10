# Task #9-4 AP-1 Phase 4 Step3 事前調査レポート

## 調査実施日時
2025年8月10日 17:30 JST

## A. コード/API調査結果

### A1. 既存5呼び出し点の詳細

#### 1. debug_gemini_reverse_translation (app.py:L1346)
- **正確な行番号**: L1346
- **関数シグネチャ**: `debug_gemini_reverse_translation(gemini_translation: str, target_lang: str, source_lang: str) -> Dict[str, Any]`
- **呼び出し時の引数**: 
  - `gemini_translation`: Gemini翻訳結果文字列
  - `target_lang`: 翻訳先言語コード
  - `source_lang`: 翻訳元言語コード
- **戻り値の使用箇所**: `debug_result.get('problems_detected', [])`をログ出力
- **エラーハンドリング**: try-except構造でデバッグ情報をDictで返却

#### 2. runFastTranslation - ChatGPT逆翻訳 (app.py:L2378)
- **正確な行番号**: L2378
- **呼び出しコンテキスト**: `reverse = f_reverse_translation(translated, target_lang, source_lang, current_lang)`
- **前後の処理フロー**:
  - L2375: `update_translation_progress("reverse_translation", "in_progress")`
  - L2377: `start_time = time.time()`
  - L2379: `reverse_time = time.time() - start_time`
  - L2382: `update_translation_progress("reverse_translation", "completed")`
- **結果の格納先変数名**: `reverse`
- **DOM更新箇所**: `data.reverse_translated_text`として返却

#### 3. runFastTranslation - Gemini逆翻訳 (app.py:L2480)
- **正確な行番号**: L2480
- **呼び出しコンテキスト**: `gemini_reverse_translation = f_reverse_translation(gemini_translation, target_lang, source_lang, current_lang)`
- **条件分岐の内容**: `if gemini_translation and not gemini_translation.startswith("⚠️") and not gemini_translation.startswith("Gemini翻訳エラー")`
- **結果の格納先変数名**: `gemini_reverse_translation`
- **DOM更新箇所**: `data.gemini_reverse_translation`として返却

#### 4. runFastTranslation - Better逆翻訳 (app.py:L2522)
- **正確な行番号**: L2522
- **呼び出しコンテキスト**: `reverse_better = f_reverse_translation(better_translation, target_lang, source_lang, current_lang)`
- **非同期処理の有無**: 同期処理（try-except内で実行）
- **結果の格納先変数名**: `reverse_better`
- **DOM更新箇所**: `data.reverse_better_translation`として返却

#### 5. reverse_better_translation (app.py:L2902)
- **正確な行番号**: L2902
- **エンドポイントパス**: `/reverse_better_translation`
- **リクエスト/レスポンスの完全な構造**:
  - **リクエスト**: `{"french_text": string, "language_pair": string}`
  - **レスポンス**: `{"success": bool, "reversed_text": string}` または `{"success": bool, "error": string}`
- **既存のデコレータリスト**: `@require_rate_limit` のみ（@csrf_protectが不足）

### A2. f_reverse_translation関数の完全仕様

#### 関数定義の詳細
- **行番号**: L1258-L1299
- **引数**:
  - `translated_text: str` - 逆翻訳対象テキスト
  - `target_lang: str` - 翻訳先言語（逆翻訳では元言語）
  - `source_lang: str` - 翻訳元言語（逆翻訳では先言語）
  - `current_lang: str = "jp"` - UI言語（デフォルト値）

#### 内部で使用している全関数/変数
- `EnhancedInputValidator.validate_text_input()`
- `EnhancedInputValidator.validate_language_pair()`
- `safe_openai_request(prompt, max_tokens=300, current_lang=current_lang)`
- `lang_map`: 言語コードマッピング辞書

#### 例外処理のパターン
```python
try:
    return safe_openai_request(prompt, max_tokens=300, current_lang=current_lang)
except Exception as e:
    return f"逆翻訳エラー: {str(e)}"
```

#### 言語マッピングの完全な内容
```python
lang_map = {
    "ja": "Japanese", 
    "fr": "French", 
    "en": "English", 
    "es": "Spanish", 
    "de": "German", 
    "it": "Italian"
}
```

#### プロンプトテンプレートの正確な文字列
```python
prompt = f"""Professional translation task: Translate the following text to {source_label}.

TEXT TO TRANSLATE TO {source_label.upper()}:
{translated_text}

IMPORTANT: Respond ONLY with the {source_label} translation."""
```

### A3. レスポンス仕様の詳細

#### 各呼び出し点でのレスポンスキー名の差異
- **ChatGPT逆翻訳**: `reverse_translated_text`
- **Gemini逆翻訳**: `gemini_reverse_translation`
- **Better逆翻訳**: `reverse_better_translation`
- **reverse_better_translationエンドポイント**: `reversed_text`

#### テキスト整形規則
- **改行コードの扱い**: そのまま保持
- **空白文字の正規化**: なし
- **HTMLエスケープの有無**: なし（JSON返却時に自動エスケープ）
- **文字数制限の有無**: OpenAIの`max_tokens=300`制限

### A4. エラーハンドリング仕様

#### 空入力時の挙動
- 空文字列の場合: `"(翻訳テキストが空です)"`を返却

#### API呼び出し失敗時の動作
- Exception発生時: `f"逆翻訳エラー: {str(e)}"`を返却
- タイムアウト: safe_openai_request内で処理

#### HTTPステータスコードのマッピング
- 成功: 200 (JSON)
- バリデーションエラー: 400 (JSON with error)
- レート制限超過: 429
- 内部エラー: 500

#### エラーメッセージの多言語対応
- 現在は日本語のみ（current_langパラメータはあるが、エラーメッセージ自体は固定）

### A5. デコレータと認証

#### 現在適用されているデコレータの完全リスト
- `/reverse_better_translation`: `@require_rate_limit` のみ
- 他の呼び出し点: デコレータなし（関数内呼び出し）

#### CSRF実装状況
- **reverse_better_translationエンドポイント**: @csrf_protectが欠如（要追加）
- **実装要求**: Step3で@csrf_protectデコレータ追加が必要

#### レート制限の詳細
- `@require_rate_limit`: security.decoratorsで実装
- 制限値: app.pyで使用、具体的な閾値は調査対象外

## B. UI/フロント調査結果

### B1. DOM構造の完全把握

#### 逆翻訳結果表示に使用される全DOM要素
- **ChatGPT逆翻訳**: `id="reverse-translated-text"` (result-text class)
- **Gemini逆翻訳**: `id="gemini-reverse-translation"` (result-text class)
- **Better逆翻訳**: 専用DOM要素なし（別エンドポイント経由）

#### 表示/非表示の制御方法
- テキスト内容の更新によるもの（display制御なし）
- 空文字列またはエラーメッセージ表示

### B2. イベントハンドラ調査

#### コピーボタンのイベントハンドラ
- **関数名**: `copyContent(id, toastId, buttonElement)`
- **実装箇所**: `static/js/main.js:72`
- **クリップボードAPI**: `navigator.clipboard.writeText(text)`

#### 削除/クリア機能
- **機能**: クリアボタンで全結果をリセット
- **実装箇所**: templates/index.html内のcriticalElements配列

### B3. CSRFトークンフロー

#### トークン生成箇所
- **テンプレート内**: `<meta name="csrf-token" content="{{ csrf_token }}">`

#### JavaScriptでの取得・付与方法
```javascript
'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
```

#### トークン欠落時のエラーハンドリング
- 403エラーでAPI呼び出し失敗
- UI側でエラーメッセージ表示

### B4. エラー表示とトースト

#### エラーメッセージの表示
- APIエラー時のアラート表示
- コンソールログ出力

#### トースト通知の実装
- **関数**: `showToastNearButton(toastId, buttonElement)`
- **実装箇所**: static/js/main.js:87

## C. 運用/テスト調査結果

### C1. 既存テストケース

#### 逆翻訳関連の既存テスト
- **ファイル**: `test_suite/lptest.py`
- **テスト対象**: `/reverse_better_translation` エンドポイント
- **テスト関数**: `test_enhanced_translation()`

#### テストデータのパターン
- 基本的なテキスト翻訳
- エラーケース処理
- CSRF/レート制限テスト含む

### C2. ログ設定

#### ロガーの設定
- **使用ロガー**: `app_logger`
- **ログレベル**: INFO/ERROR/WARNING
- **ログフォーマット**: 標準Flask形式

#### 機密情報のマスキング
- トークン値のマスキング実装: `masked_token = csrf_token[:8] + "***"`

### C3. 環境変数とFeature Flag

#### 関連環境変数
- `ENVIRONMENT`: development/production切り替え
- `DEV_CSRF_ENDPOINT_ENABLED`: 開発用CSRF配布API制御

## D. 追加調査項目

### D1. セッション管理

#### 逆翻訳に関連するセッション変数
- `reverse_translated_text`: ChatGPT逆翻訳結果
- `gemini_reverse_translation`: Gemini逆翻訳結果  
- `reverse_better_translation`: Better逆翻訳結果

#### セッション保存方法
- **Flask session**: `safe_session_store()` 関数使用
- **Redis**: `translation_state_manager.save_multiple_large_data()`

### D2. キャッシュ戦略

#### Redis使用の詳細
- **使用有無**: translation_state_managerで使用
- **キャッシュキー**: session_id ベース
- **TTL設定**: 調査範囲では詳細不明

### D3. 国際化（i18n）

#### labels辞書の構造
- **ファイル**: labels.py
- **逆翻訳関連ラベル**: `no_reverse_result`, `toast_copied`
- **多言語対応**: jp/en/fr/es

### D4. パフォーマンス

#### 現在の設定値
- **max_tokens**: 300 (OpenAI API)
- **TEST_TIMEOUT**: テスト用タイムアウト設定
- **同時実行制御**: 調査範囲では詳細不明

### D5. 依存関係

#### 主要依存関係
- **translation_service**: Phase 4でのService層統合対象
- **EnhancedInputValidator**: 入力値検証
- **safe_openai_request**: OpenAI API呼び出し
- **translation_state_manager**: セッション/Redis管理

## 調査で発見した懸念事項

### 1. セキュリティ関連
- **@csrf_protect欠如**: `/reverse_better_translation`エンドポイントにCSRF保護なし
- **一貫性のないデコレータ適用**: 他のエンドポイントと保護レベルが異なる

### 2. レスポンスキー名の不統一
- 同じ逆翻訳機能でキー名が複数存在（reverse_translated_text, reversed_text等）
- UI/API間での命名不一致の可能性

### 3. エラーハンドリングの不統一
- 一部の呼び出し点でエラーハンドリングが不完全
- 多言語対応のエラーメッセージが未実装

### 4. 巨大関数における複雑性
- `runFastTranslation()` 関数が176行と巨大
- 複数の逆翻訳呼び出しが単一関数内に混在

## 未解決の調査項目

### 1. 具体的な制限値
- レート制限の詳細な閾値・時間窓
- セッションタイムアウトの具体的な値

### 2. パフォーマンス指標
- 現在の平均レスポンスタイム
- Redis TTLの具体的な設定値

### 3. 完全なテストカバレッジ
- 全5箇所の呼び出し点に対するテストケース
- エラーケースの網羅的なテスト

## 実装時の推奨事項

### 1. セキュリティ強化
- 全エンドポイントに@csrf_protectデコレータ追加
- デコレータ適用の標準化

### 2. レスポンス統一化
- 逆翻訳結果のキー名統一（API設計ガイドライン策定）
- エラーレスポンス形式の標準化

### 3. 段階的移行戦略
- 5箇所の呼び出し点を順次Service層に移行
- 各段階でのテスト実行による回帰防止

### 4. ロールバック準備
- 移行前のバックアップ完備
- 旧実装への即座復旧手順の文書化