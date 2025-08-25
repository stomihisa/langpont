# ARCHITECTURE_SAVE_v3.0

## 1. 目的

本書は LangPont アプリの **保存・履歴・状態管理アーキテクチャ** を確定させる最終版設計書である。
以降の開発・レビューは本設計に準拠する。
このファイルを唯一の参照点（SOT: Source of Truth）とし、揺れや多重解釈を排除する。

## 2. 基本方針

### 設計の固定化
- 以降の実装は本書に完全準拠。PR には準拠ラベルを必須化する。

### 責任分離
- `translation_service.py`: 翻訳API呼び出し
- `translation_state_manager.py`: 状態統合（翻訳結果・UI同期）
- `session_redis_manager.py`: Redisセッションの低レイヤー管理
- `langpont_redis_session.py`: 高レイヤーの Redis セッション制御
- `app.py`: Flaskエントリポイント（ルーティング）
- `index.html`: UI

### 禁止事項
- `python app.py &` での起動は禁止。必ず `gunicorn` + `systemd` を使用。
- 本設計にない「仮実装」「一時的な保存処理」は禁止。

### データベース接続設定方針（Task #9-4 S4-02）
- **DSN形式優先**: `DATABASE_URL`・`REDIS_URL` を第一優先で使用
- **TLS強制**: PostgreSQL `sslmode=require`・Redis `rediss://` を本番・検証環境で必須
- **SQLite絶対パス**: 相対パス完全撤廃、絶対パス指定必須
- **Secrets管理**: 本番環境では AWS Secrets Manager/SSM 経由で機密情報取得

## 3. 状態管理アーキテクチャ

### 3.1 構造
```
ユーザー入力
   ↓
translation_service.py      ← 各翻訳APIを呼び出し
   ↓
translation_state_manager.py ← 状態を統合、保存リクエストを生成
   ↓
langpont_redis_session.py   ← 高レベルのセッション制御
   ↓
session_redis_manager.py    ← Redis操作（低レベル）
   ↓
Redis DB                    ← 永続化された状態データ
```

### 3.2 保存ルール
- **空保存は禁止**：テキストが空の場合は保存処理を skip
- **セッションキー**: `session_id` に基づき Redis に保存
- **UI同期**: `index.html` から呼び出す履歴復元は必ず `translation_state_manager.py` を経由

## 4. 履歴復元フロー

1. UI（履歴ボタン押下）
2. `/load_history` API 呼び出し
3. `translation_state_manager` が Redis からデータ取得
4. 復元データを UI に返却
5. 多言語混在でも正しく復元できることを保証

## 5. テスト要件

- **初期ロード時**: 履歴が存在する場合に正しく一覧表示されること
- **履歴アイテムクリック**: 選択セッションが完全に復元されること
- **復元データ完全性**: UI表示と保存済みデータが一致すること
- **多言語履歴**: 言語混在時でも破綻しないこと
- **大量履歴負荷**: 50件以上でもモーダル表示・復元が正しく動作

## 6. 運用ルール

### リポジトリ反映
- 本設計書を `docs/ARCHITECTURE_SAVE_v3.0.md` に保存
- `README.md` からリンクを設置（Architecture 章）

### タグ付け
- Git タグ `v3.0-docs` を付与

### レビュー運用
- PR には「ARCHITECTURE_v3.0 準拠」ラベルを必須
- 本書を逸脱する変更はレビューで拒否

## 7. 今後の拡張指針

- DB移行（Redis → PostgreSQL など）時も、本書の責任分離構造を維持
- API増加時は `translation_service.py` に追加し、`translation_state_manager` を通じて統合する
- UI改修時も、必ず State Manager 層との責務境界を維持する

---

✅ **本書を唯一の参照点とし、以降の全ての開発はこの仕様に従う。**
