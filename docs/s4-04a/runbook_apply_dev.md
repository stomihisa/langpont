# S4-04a Runbook（開発DB向け）— DDL適用手順 *DO NOT APPLY IN THIS PR*

> ⚠️ このPR段階では **実行禁止**。手順書としてのドキュメントです。  
> ⚠️ `python app.py &`（バックグラウンド起動）**絶対禁止**。  
> 前提：PostgreSQL は TLS（`sslmode=require`）で接続。対象は **開発DBのみ**。

## 0. 事前確認
- 環境変数 `DATABASE_URL` が開発DB（TLS必須）を指していること  
- スキーマに `translation_sessions` / `translations` が未作成であること（検証用に既存DBなら別DB/別スキーマ）

## 1. 適用（手順のみ・ここでは実行しない）
```sh
psql "$DATABASE_URL" -f docs/s4-04a/ddl_v1.sql

2. 検証SQL（存在確認・制約動作）
-- テーブル・制約・インデックス確認
\d+ translation_sessions
\d+ translations

-- UNIQUE の重複挿入が失敗することを確認（同一 session_id, engine, version）
BEGIN;
  WITH s AS (
    INSERT INTO translation_sessions (metadata) VALUES ('{}') RETURNING id
  )
  INSERT INTO translations (session_id, engine, version, metadata)
  SELECT id, 'openai', 'v1', '{}' FROM s;

  INSERT INTO translations (session_id, engine, version, metadata)
  SELECT id, 'openai', 'v1', '{}' FROM s;  -- ← ここで UNIQUE 違反になるのが正しい
ROLLBACK;

-- 代表クエリの実行計画（Index Scan が選ばれることを確認）
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM translations WHERE session_id = $1 AND engine = $2;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM translations WHERE session_id = $1;

3. ロールバック（DROP 順序）
-- 1) 子テーブル → 2) 親の部分インデックス → 3) 親テーブル
DROP TABLE IF EXISTS translations CASCADE;
DROP INDEX IF EXISTS idx_ts_legacy_session_key;
DROP TABLE IF EXISTS translation_sessions CASCADE;

4. 補足

ddl_v1.sql は pgcrypto 前提（gen_random_uuid()）。先頭に CREATE EXTENSION IF NOT EXISTS pgcrypto; を宣言済み。

(session_id, engine) 単独インデックスは現時点では追加しない（UNIQUE(session_id, engine, version) に包含）。実クエリを見て後続フェーズで評価。
