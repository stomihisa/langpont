# S4-04a APPLY_DEV_REPORT（開発DB）

## 環境
- DATABASE_URL: (伏字) … db=langpont_dev / sslmode=prefer
- 実行日時: 2025-08-29T12:08:00Z

## 実施結果（要約）
- ドライラン：成功（ROLLBACK適用）
- 本適用：成功（translation_sessions / translations 作成）
- UNIQUE重複テスト：**エラー発生を確認**（期待どおり）
- ロールバック：成功（両テーブル削除）
- 再適用：成功

## 抜粋ログ
### \d+ translation_sessions / translations

```
                                               テーブル"public.translation_sessions"
         列         |          タイプ          | 照合順序 | Null 値を許容 |    デフォルト     | ストレージ | 圧縮 | 統計目標 | 説明 
--------------------+--------------------------+----------+---------------+-------------------+------------+------+----------+------
 id                 | uuid                     |          | not null      | gen_random_uuid() | plain      |      |          | 
 created_at         | timestamp with time zone |          | not null      | now()             | plain      |      |          | 
 updated_at         | timestamp with time zone |          | not null      | now()             | plain      |      |          | 
 deleted_at         | timestamp with time zone |          |               |                   | plain      |      |          | 
 legacy_session_key | text                     |          |               |                   | extended   |      |          | 
 metadata           | jsonb                    |          | not null      | '{}'::jsonb       | extended   |      |          | 
インデックス:
    "translation_sessions_pkey" PRIMARY KEY, btree (id)
    "idx_ts_legacy_session_key" btree (legacy_session_key) WHERE legacy_session_key IS NOT NULL
参照元:
    TABLE "translations" CONSTRAINT "translations_session_id_fkey" FOREIGN KEY (session_id) REFERENCES translation_sessions(id) ON DELETE CASCADE
アクセスメソッド: heap

                                               テーブル"public.translations"
     列     |          タイプ          | 照合順序 | Null 値を許容 |    デフォルト     | ストレージ | 圧縮 | 統計目標 | 説明 
------------+--------------------------+----------+---------------+-------------------+------------+------+----------+------
 id         | uuid                     |          | not null      | gen_random_uuid() | plain      |      |          | 
 session_id | uuid                     |          | not null      |                   | plain      |      |          | 
 engine     | text                     |          | not null      |                   | extended   |      |          | 
 version    | text                     |          | not null      |                   | extended   |      |          | 
 created_at | timestamp with time zone |          | not null      | now()             | plain      |      |          | 
 metadata   | jsonb                    |          | not null      | '{}'::jsonb       | extended   |      |          | 
インデックス:
    "translations_pkey" PRIMARY KEY, btree (id)
    "idx_translations_created_at" btree (created_at)
    "uq_translations_session_engine_version" UNIQUE CONSTRAINT, btree (session_id, engine, version)
外部キー制約:
    "translations_session_id_fkey" FOREIGN KEY (session_id) REFERENCES translation_sessions(id) ON DELETE CASCADE
アクセスメソッド: heap
```

### UNIQUE重複テスト（エラーが正）

```
BEGIN
                  id                  
--------------------------------------
 afeea5ec-5aae-4006-b0ea-d8815cab868f
(1 行)

INSERT 0 1
ERROR:  duplicate key value violates unique constraint "uq_translations_session_engine_version"
DETAIL:  Key (session_id, engine, version)=(afeea5ec-5aae-4006-b0ea-d8815cab868f, openai, v1) already exists.
ROLLBACK
```

## 気づき・未決
- pgcrypto拡張は既存環境にインストール済み（スキップ処理）
- UNIQUE制約が正しく機能することを確認
- インデックスとFK制約も正常に作成
