# LangPont 開発環境ガイド

## 🔧 開発限定CSRF配布API

### 概要
Task #9-4で実装したCSRF保護エンドポイントのテスト用に、開発環境限定でCSRFトークンを配布するAPIを提供しています。

**⚠️ 重要**: このAPIは開発環境でのテスト専用です。Phase6で撤去予定。

### エンドポイント
```
GET /api/dev/csrf-token
```

### 安全ガード
- **環境制限**: `ENVIRONMENT='development'` のときのみ有効
- **フィーチャーフラグ**: `DEV_CSRF_ENDPOINT_ENABLED='true'` のときのみ有効 (既定: true)
- **IPアドレス制限**: localhost (127.0.0.1, ::1) のみ許可
- **レート制限**: 標準レート制限適用
- **ログマスク**: CSRFトークン値は先頭8文字のみログ出力

### テスト確認コマンド

#### 1. 開発環境での正常動作確認 (200期待)
```bash
# CSRFトークン取得
curl -s -c cookies.txt "http://127.0.0.1:8080/api/dev/csrf-token" -o token.json && cat token.json

# 取得したトークンで逆翻訳API呼び出し
TOKEN=$(jq -r '.csrf_token' token.json)
curl -iS --fail-with-body -X POST "http://127.0.0.1:8080/reverse_chatgpt_translation" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: ${TOKEN}" \
  -b cookies.txt \
  -d '{"translated_text":"Hello World","language_pair":"en-ja"}'
```

#### 2. 本番環境想定での無効化確認 (404期待)
```bash
# アプリを本番環境設定で再起動
ENVIRONMENT=production python app.py &
sleep 5

# 404が返されることを確認
curl -v "http://127.0.0.1:8080/api/dev/csrf-token"
```

#### 3. フィーチャーフラグでの無効化確認 (404期待)
```bash
# フラグを無効化してアプリ再起動
DEV_CSRF_ENDPOINT_ENABLED=false python app.py &
sleep 5

# 404が返されることを確認
curl -v "http://127.0.0.1:8080/api/dev/csrf-token"
```

### 期待結果

#### 開発環境 (有効時)
```json
{
  "success": true,
  "csrf_token": "6IQEzLTMRgvT6jvpshiPzbxKkaFUkbYDJffeCcLLwDI"
}
```

#### 本番環境 / フラグ無効時
```
HTTP/1.1 404 NOT FOUND
```

## 📁 関連ファイル

- **実装**: `routes/translation.py` - `/api/dev/csrf-token`エンドポイント
- **テストファイル**: `token.json`, `cookies.txt` (.gitignoreに追加済み)
- **撤去計画**: `Phase6_Retire_DevCSRF.md` (予定)

## 🚨 セキュリティ注意事項

- このAPIは開発・テスト専用です
- CSRFトークンをログやコミットに含めないよう注意してください
- Phase6で必ず撤去する予定です

---

**更新日**: 2025年8月10日  
**Task**: #9-4 AP-1 Phase 4 Step2  
**撤去予定**: Phase6