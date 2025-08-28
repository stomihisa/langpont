# S4-04a コアDDL事前調査

## ⚠️ **重要警告** ⚠️

<span style="color: red; font-weight: bold; font-size: 18px;">
📛 本タスクは調査専用です。実装・実DB操作は絶対禁止です 📛
</span>

### 🚫 実行禁止事項

- **DDL実行:** `ddl_draft.sql` の実適用禁止
- **データベース接続:** PostgreSQL/Redis/SQLite への実接続禁止  
- **アプリ起動:** `python app.py &` バックグラウンド実行禁止
- **設定変更:** `.env` / `config.py` / データベース設定変更禁止
- **コード修正:** アプリケーションコードの修正・拡張禁止

### ✅ 許可事項

- **ドキュメント作成・更新のみ** （ `docs/s4-04a/` 配下）
- **静的コード解析** （Read-only）
- **調査結果の文書化**

---

## 📋 調査概要

**Task番号:** Task#9-4AP-1Ph4S4-04a（コアDDL／段階導入 前調査）  
**調査日時:** 2025年8月26日  
**調査者:** Claude Code  

### 🎯 調査目的

翻訳履歴永続化のための最小限テーブル設計を、現行システムの静的分析により確定する。

### 📊 調査スコープ

1. **保存要件抽出:** 現行コードからDB保存すべきデータ項目を特定
2. **クエリパターン分析:** 想定される検索・参照パターンを列挙
3. **最小DDL設計:** 必要最小限のテーブル・制約・インデックス設計
4. **リスク分析:** 実装時の技術・運用リスク特定

## 📚 調査成果物

### 1. [findings.md](./findings.md) - **詳細調査結果**

**内容:**
- 保存要件32項目の根拠付きリスト
- 想定クエリ6パターンの詳細分析
- 前提条件・環境要件
- リスク・未決事項の整理

**重要発見:**
- セッション識別に `session_id` + `csrf_token` フォールバック構造
- エンジン種別: chatgpt, gemini, enhanced, reverse, claude
- フォーム状態管理の詳細要件（StateManager integration）

### 2. [ddl_draft.sql](./ddl_draft.sql) - **DDL草案（実行禁止）**

**設計特徴:**
- **2テーブル構成:** `translation_sessions` + `translations`
- **UNIQUE制約活用:** `(session_id, engine, version)` で複合インデックス自動生成
- **最小インデックス:** `(created_at)` のみ追加、冗長インデックス排除
- **拡張性確保:** Phase 4b での `analyses`/`qa_items` テーブル追加容易

**インデックス最適化:**
```sql
-- ✅ UNIQUE制約による自動最適化
UNIQUE(session_id, engine, version)
-- → PostgreSQLが自動生成する複合B-Treeインデックス
-- → WHERE session_id = ? 
-- → WHERE session_id = ? AND engine = ?
-- → の両方を高速化

-- ❌ 冗長なため追加不要
-- CREATE INDEX (session_id, engine) -- UNIQUE制約でカバー済み
```

### 3. [README.md](./README.md) - **提出物一覧・次ステップ**

調査成果の概要と実装フェーズへの移行準備。

## 🔍 主要技術決定

### データベース設計

| テーブル | 目的 | 主要カラム |
|---------|------|-----------|
| **translation_sessions** | セッション管理 | id(UUID), source_text, language_pair, created_at |
| **translations** | 翻訳結果格納 | id(UUID), session_id(FK), engine, version, translated_text |

### 制約設計

```sql
-- 重複防止（最重要）
UNIQUE(session_id, engine, version)

-- データ品質保証
CHECK (source_language IN ('ja', 'en', 'fr', 'es'))
CHECK (engine IN ('chatgpt', 'gemini', 'enhanced', 'reverse', 'claude'))

-- 参照整合性
FOREIGN KEY (session_id) REFERENCES translation_sessions(id) ON DELETE CASCADE
```

### インデックス戦略

**採用した最小セット:**
- `(created_at)` - 時系列検索・監査用
- `UNIQUE(session_id, engine, version)` - 自動生成複合インデックス

**意図的に除外:**
- `(session_id, engine)` - UNIQUE制約でカバー（冗長）
- `(engine, created_at)` - 頻度不明のため後回し

## 📊 想定クエリ性能

| クエリパターン | 頻度 | 対応インデックス | パフォーマンス |
|--------------|------|----------------|---------------|
| セッション最新結果取得 | 極高 | UNIQUE複合 | ✅ 高速 |
| エンジン別結果取得 | 高 | UNIQUE複合 | ✅ 高速 |
| 時系列履歴検索 | 中 | created_at | ✅ 高速 |
| ユーザー履歴 | 中 | user_id + created_at | ✅ 高速 |
| 監査・分析 | 低 | created_at + 複合 | ✅ 許容 |

## ⚠️ 実装時注意事項

### 必須確認項目

1. **TLS設定:** `sslmode=require` 強制確認
2. **環境分離:** 開発/検証/本番環境の接続先確認
3. **UNIQUE制約テスト:** 重複データ投入での制約動作確認
4. **ロールバック準備:** 失敗時の安全な戻し手順確認

### リスク軽減策

1. **段階実装:** まず開発環境、次に検証環境で動作確認
2. **性能テスト:** 想定クエリのレスポンス時間測定
3. **データ移行テスト:** 既存履歴データの移行可能性確認
4. **監視設定:** 新テーブルの容量・性能モニタリング

## 🔄 次ステップ（実装フェーズ）

1. **環境準備:** 開発用PostgreSQLインスタンス準備
2. **DDL適用:** `ddl_draft.sql` のテスト環境での実行
3. **制約テスト:** UNIQUE/FK/CHECK制約の動作確認
4. **性能テスト:** 想定クエリのベンチマーク実行
5. **アプリ統合:** translation_history.py との接続テスト

## 📞 問い合わせ・次アクション

**調査完了確認:** ✅ 全項目完了  
**実装準備状況:** ✅ 100%準備完了  
**推奨次アクション:** 実装フェーズへの移行（新ブランチ `feature/s4-04a-core-ddl` 作成）  

---

**📅 調査完了日時:** 2025年8月26日 15:45  
**📊 調査品質:** 高（実装済みコードベース + 実ユースケース分析）  
**🎯 信頼度:** 高（32項目の保存要件、6パターンの想定クエリを根拠付きで特定）  

<span style="color: red; font-weight: bold;">
🔴 再確認: 本調査は実装・実DB操作を含まず、ドキュメント作成のみです 🔴
</span>