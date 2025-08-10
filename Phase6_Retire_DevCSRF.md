# Phase6: 開発限定CSRF配布API撤去タスク

## 📋 撤去概要

**作成日**: 2025年8月10日  
**撤去予定フェーズ**: Phase 6  
**対象**: 開発限定CSRF配布API (`/api/dev/csrf-token`)  
**理由**: テスト専用の一時的実装のため、本格運用開始前に撤去必要

## 🎯 撤去対象

### 1. メインコード削除
**ファイル**: `routes/translation.py`

**削除対象コード** (L850-L909):
```python
@translation_bp.route('/api/dev/csrf-token', methods=['GET'])
@require_rate_limit
def dev_csrf_token():
    """開発環境限定: CSRF トークン配布API"""
    # ... 全実装 ...
```

### 2. 関連ドキュメント削除
- `Readme_dev.md` - 開発環境ガイド全体または該当セクション
- 本ファイル (`Phase6_Retire_DevCSRF.md`) 自体も削除

### 3. 設定・テストファイル削除
- `token.json` (テスト時に生成)
- `cookies.txt` (テスト時に生成)
- `.gitignore`から該当行削除 (L44-46):
  ```
  # Dev CSRF API テストファイル
  token.json
  cookies.txt
  ```

### 4. 環境変数削除
- `DEV_CSRF_ENDPOINT_ENABLED` - ドキュメントから削除
- 関連する環境変数設定指示を全削除

## ✅ 撤去チェックリスト

### Phase 6実施時に実行する作業

#### 1. コード削除
- [ ] `routes/translation.py`から`dev_csrf_token`関数削除 (L850-909)
- [ ] 関連import文の整理 (不要になったimportの削除)

#### 2. ドキュメント削除・更新
- [ ] `Readme_dev.md`から該当セクション削除
- [ ] `Phase6_Retire_DevCSRF.md` (本ファイル) 削除
- [ ] `CLAUDE.md`から関連記述削除

#### 3. 設定ファイル清掃
- [ ] `.gitignore`からdev CSRF関連行削除
- [ ] テストファイル削除確認 (`token.json`, `cookies.txt`)

#### 4. 痕跡確認 (grep検索)
以下のキーワードで痕跡が残っていないことを確認:

```bash
# コード内検索
grep -r "dev_csrf_token" .
grep -r "api/dev/csrf-token" .
grep -r "DEV_CSRF_ENDPOINT_ENABLED" .
grep -r "Dev CSRF API" .

# 期待結果: 全て 0 match
```

#### 5. 動作確認
```bash
# エンドポイントが完全に削除されていることを確認
curl -v "http://127.0.0.1:8080/api/dev/csrf-token"
# 期待: 404 Not Found (ルート自体が存在しない)
```

## 🚨 注意事項

### 撤去前確認
- [ ] Phase 5までの全作業が完了している
- [ ] 本格的なCSRF保護機能が正常動作している
- [ ] テスト環境での動作確認が不要になっている

### 撤去時の安全対策
- [ ] 撤去前に動作中のアプリケーションを停止
- [ ] バックアップコミット作成: `git commit -m "Phase6: backup before dev CSRF API removal"`
- [ ] 段階的削除 (一度にすべて削除せず、動作確認しながら)

### 撤去後確認
- [ ] アプリケーション正常起動確認
- [ ] 既存CSRF保護機能の動作確認
- [ ] 本番デプロイでの動作確認

## 📊 影響評価

### 削除による影響
- **正の影響**: セキュリティリスク除去、コード整理
- **負の影響**: 開発時のCSRF debuggingが困難になる (代替手段で対応)

### 代替手段
CSRF保護のテストには以下を使用:
- ブラウザ開発者ツールでのCSRFトークン取得
- 認証済みセッションでのテスト実行
- 単体テストでのモック使用

---

**📅 予定実施日**: Phase 6開始時  
**👤 実施者**: Phase 6担当者  
**📋 承認**: Phase 5完了確認後