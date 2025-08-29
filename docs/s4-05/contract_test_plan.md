# Contract Test Plan: API v1 (Sessions & Translations)

**作成日**: 2025-08-29  
**対象API**: LangPont API v1  
**参照**: [OpenAPI仕様](./api_v1_openapi.yaml)

## テスト方針

### 契約テストの目的
- API仕様の正常系・異常系の動作を文書レベルで検証
- S4-06実装時の受け入れ基準を明確化
- DDL制約（UNIQUE等）とAPI仕様の整合性確認

### 制約確認
- **DDL根拠**: [S4-04a DDL v1](../s4-04a/ddl_v1.sql)
- **検証済み**: [S4-04a 開発DB適用テスト](../s4-04a/APPLY_DEV_REPORT.md)
- **UNIQUE制約**: `(session_id, engine, version)` 組み合わせ一意

---

## 正常系テスト

### TC001: 新規セッション作成
| 項目 | 値 |
|-----|---|
| **エンドポイント** | `POST /api/sessions` |
| **ヘッダー** | `Idempotency-Key: req_20250829_001` |
| **リクエストボディ** | `{}` (空) |
| **期待HTTP状態** | `201 Created` |
| **期待レスポンス** | ```json<br>{"id": "uuid", "created_at": "timestamp", "updated_at": "timestamp", "deleted_at": null, "legacy_session_key": null, "metadata": {}}``` |
| **検証ポイント** | - UUIDが生成される<br>- created_at = updated_at<br>- metadata空オブジェクト |

### TC002: メタデータ付きセッション作成
| 項目 | 値 |
|-----|---|
| **エンドポイント** | `POST /api/sessions` |
| **ヘッダー** | `Idempotency-Key: req_20250829_002` |
| **リクエストボディ** | ```json<br>{"metadata": {"source_lang": "ja", "target_lang": "en"}}``` |
| **期待HTTP状態** | `201 Created` |
| **期待レスポンス** | metadata部分に入力値が反映 |
| **検証ポイント** | - メタデータが保持される<br>- その他のフィールドは正常 |

### TC003: 翻訳結果追加（初回）
| 項目 | 値 |
|-----|---|
| **前提条件** | セッションID `session-001` が存在 |
| **エンドポイント** | `POST /api/sessions/session-001/translations` |
| **ヘッダー** | `Idempotency-Key: req_20250829_003` |
| **リクエストボディ** | ```json<br>{"engine": "openai", "version": "v1", "metadata": {"input_text": "こんにちは", "translated_text": "Hello"}}``` |
| **期待HTTP状態** | `201 Created` |
| **期待レスポンス** | ```json<br>{"id": "uuid", "session_id": "session-001", "engine": "openai", "version": "v1", "created_at": "timestamp", "metadata": {...}}``` |
| **検証ポイント** | - 翻訳IDが新規生成<br>- session_id正確に関連付け<br>- metadataが保持 |

### TC004: 異なるengineで翻訳追加
| 項目 | 値 |
|-----|---|
| **前提条件** | TC003完了後、同じセッション |
| **エンドポイント** | `POST /api/sessions/session-001/translations` |
| **ヘッダー** | `Idempotency-Key: req_20250829_004` |
| **リクエストボディ** | ```json<br>{"engine": "gemini", "version": "v1", "metadata": {"input_text": "こんにちは", "translated_text": "Hello"}}``` |
| **期待HTTP状態** | `201 Created` |
| **検証ポイント** | - 異なるengineなので成功<br>- 同じsession_idに複数翻訳が保存 |

### TC005: セッション一覧取得（既定パラメータ）
| 項目 | 値 |
|-----|---|
| **前提条件** | セッションが複数存在 |
| **エンドポイント** | `GET /api/sessions` |
| **パラメータ** | なし（既定値使用） |
| **期待HTTP状態** | `200 OK` |
| **期待レスポンス** | ```json<br>{"sessions": [...], "pagination": {"total": N, "limit": 20, "offset": 0, "next_cursor": "..."}}``` |
| **検証ポイント** | - created_at desc順（最新が先頭）<br>- limit=20既定値<br>- TC001で作成したセッションが先頭近くに表示 |

### TC006: セッション一覧取得（ページング）
| 項目 | 値 |
|-----|---|
| **エンドポイント** | `GET /api/sessions?limit=5&offset=10` |
| **期待HTTP状態** | `200 OK` |
| **検証ポイント** | - 5件取得<br>- offset=10から開始<br>- 正しいpagination情報 |

---

## 異常系テスト

### TC101: 不正なIdempotency-Key
| 項目 | 値 |
|-----|---|
| **エンドポイント** | `POST /api/sessions` |
| **ヘッダー** | `Idempotency-Key: invalid key!` |
| **期待HTTP状態** | `400 Bad Request` |
| **期待レスポンス** | ```json<br>{"error": {"code": "INVALID_IDEMPOTENCY_KEY", "message": "...", "details": {"provided_key": "invalid key!"}}}``` |
| **検証ポイント** | - 特殊文字を含むキーは拒否<br>- 明確なエラーメッセージ |

### TC102: Idempotency-Key未指定
| 項目 | 値 |
|-----|---|
| **エンドポイント** | `POST /api/sessions` |
| **ヘッダー** | Idempotency-Key なし |
| **期待HTTP状態** | `400 Bad Request` |
| **期待レスポンス** | Idempotency-Key必須エラー |
| **検証ポイント** | - ヘッダー未指定で拒否<br>- API契約の必須要件 |

### TC103: 存在しないセッションに翻訳追加
| 項目 | 値 |
|-----|---|
| **エンドポイント** | `POST /api/sessions/nonexistent-uuid/translations` |
| **ヘッダー** | `Idempotency-Key: req_20250829_103` |
| **リクエストボディ** | ```json<br>{"engine": "openai", "version": "v1", "metadata": {}}``` |
| **期待HTTP状態** | `404 Not Found` |
| **期待レスポンス** | ```json<br>{"error": {"code": "SESSION_NOT_FOUND", "message": "...", "details": {"session_id": "nonexistent-uuid"}}}``` |
| **検証ポイント** | - 不在session_idで404<br>- エラー詳細に該当IDを含む |

### TC104: UNIQUE制約違反（engine+version重複）
| 項目 | 値 |
|-----|---|
| **前提条件** | TC003完了（openai, v1で翻訳済み） |
| **エンドポイント** | `POST /api/sessions/session-001/translations` |
| **ヘッダー** | `Idempotency-Key: req_20250829_104` |
| **リクエストボディ** | ```json<br>{"engine": "openai", "version": "v1", "metadata": {"different": "data"}}``` |
| **期待HTTP状態** | `409 Conflict` |
| **期待レスポンス** | ```json<br>{"error": {"code": "TRANSLATION_DUPLICATE", "message": "...", "details": {"session_id": "session-001", "engine": "openai", "version": "v1", "constraint": "uq_translations_session_engine_version"}}}``` |
| **検証ポイント** | - DDL UNIQUE制約と完全一致<br>- 制約名もエラーに含む<br>- **これが最重要テスト** |

### TC105: 翻訳追加時の必須フィールド不足
| 項目 | 値 |
|-----|---|
| **エンドポイント** | `POST /api/sessions/session-001/translations` |
| **ヘッダー** | `Idempotency-Key: req_20250829_105` |
| **リクエストボディ** | ```json<br>{"version": "v1", "metadata": {}}``` |
| **期待HTTP状態** | `400 Bad Request` |
| **期待レスポンス** | ```json<br>{"error": {"code": "VALIDATION_ERROR", "message": "engine is required", "details": {"field": "engine"}}}``` |
| **検証ポイント** | - engine必須の検証<br>- 詳細にフィールド名を含む |

### TC106: セッション一覧取得（不正limit）
| 項目 | 値 |
|-----|---|
| **エンドポイント** | `GET /api/sessions?limit=1000` |
| **期待HTTP状態** | `400 Bad Request` |
| **期待レスポンス** | limit上限超過エラー（max=100） |
| **検証ポイント** | - limit上限の境界値テスト |

---

## 冪等性テスト（紙上定義）

### TC201: 同一Idempotency-Keyでの重複作成防止
| 項目 | 値 |
|-----|---|
| **シナリオ** | 1. セッション作成（`Idempotency-Key: dup-test-001`）<br>2. 同じキーで再度セッション作成 |
| **期待動作** | 2回目は新規作成されず、1回目の結果を返す |
| **実装方針** | S4-06で詳細実装、ここは契約定義のみ |
| **検証ポイント** | - レスポンスは同一<br>- DBに重複レコード作成されない<br>- HTTP 201 → 200への変更検討 |

### TC202: 翻訳追加での冪等性
| 項目 | 値 |
|-----|---|
| **シナリオ** | 同一Idempotency-Keyでの翻訳追加重複送信 |
| **期待動作** | 重複実行されない |
| **注意点** | UNIQUE制約エラー(409)との区別が必要 |

---

## 非機能テスト（紙上定義）

### NTC001: ページング制限
| 項目 | 仕様 |
|-----|---|
| **limit既定値** | 20 |
| **limit上限** | 100 |
| **offset上限** | 実装で決定（10,000件程度を想定） |
| **ソート既定** | `created_at DESC` |
| **カーソルページング** | オプション（next_cursor対応） |

### NTC002: メタデータ拡張互換ポリシー
| 項目 | ポリシー |
|-----|---|
| **未知フィールド** | 無視（破壊しない） |
| **既存フィールド削除** | v2で検討（破壊的変更） |
| **型変更** | 禁止（破壊的変更） |
| **ネストレベル** | 制限なし（JSONBの範囲内） |

---

## 実装確認チェックリスト

### S4-06実装時の受け入れ基準

- [ ] **TC001-006**: 正常系全て成功
- [ ] **TC101-106**: 異常系全て期待通りエラー
- [ ] **TC104**: DDL UNIQUE制約との完全一致確認
- [ ] **TC201-202**: 冪等性の基本動作確認
- [ ] **NTC001**: ページング制限の実装確認
- [ ] **OpenAPI仕様**: 実装と仕様の完全一致

### 最重要確認項目

1. **UNIQUE制約整合性**: TC104でのDB制約エラーとAPI応答の一致
2. **最新IDフォールバック禁止**: 仕様で明文化、実装で確実に禁止
3. **Idempotency-Key必須**: 全POST操作での強制
4. **エラー体系統一**: 400/404/409の使い分けとメッセージ形式

---

## 参考資料

- [OpenAPI v1仕様](./api_v1_openapi.yaml)
- [S4-04a DDL設計](../s4-04a/ddl_v1.sql)  
- [S4-04a 開発DB検証](../s4-04a/APPLY_DEV_REPORT.md)
- [チェックリスト](./checklist_done.md)

**最終更新**: 2025-08-29  
**次ステップ**: S4-06でのAPI実装とテスト実行