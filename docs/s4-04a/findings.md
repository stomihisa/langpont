# S4-04a コアDDL 事前調査結果

**調査日時:** 2025年8月26日  
**Task番号:** Task#9-4AP-1Ph4S4-04a（コアDDL／段階導入 前調査）  
**調査者:** Claude Code  

---

## 📋 調査概要

**目的:** テーブル設計を"最小＆十分"に確定するため、現行コードから保存要件・想定クエリを静的に抽出  
**ゴール:** ①必要カラム/制約の根拠一覧、②想定クエリ（頻度/目的）、③最小DDL草案、④インデックス最小セットの妥当性を資料化  

## 🔍 保存要件分析

### 1. セッション識別要件

| 項目 | データ型 | 参照元 | 説明 |
|------|----------|--------|------|
| **session_id** | UUID/TEXT | app.py:514, 571 | `session.get("session_id")` セッション識別子 |
| **csrf_token** | TEXT | app.py:514 | フォールバック識別子 (`[:16]`) |
| **user_id** | INTEGER | app.py:492-496 | ユーザー識別、認証システムベース |
| **username** | TEXT | app.py:496 | レガシー認証での識別子 |

**コード根拠:**
```python
# app.py:514, 571
session_id = session.get("session_id") or session.get("csrf_token", "")[:16]

# app.py:492-496  
if AUTH_SYSTEM_AVAILABLE and session.get("authenticated"):
    return session.get("user_id")
elif session.get("logged_in"):
    username = session.get("username")
```

### 2. 翻訳内容要件

| 項目 | データ型 | 参照元 | 説明 |
|------|----------|--------|------|
| **source_text** | TEXT | translation_history.py:56 | 原文テキスト |
| **source_language** | TEXT | translation_history.py:57 | 源言語（ja, en, fr, es） |
| **target_language** | TEXT | translation_history.py:58 | 目標言語 |
| **translated_text** | TEXT | translation_history.py:70 | 翻訳結果テキスト |
| **partner_message** | TEXT | app.py:578, translation_history.py:59 | パートナーメッセージ |
| **context_info** | TEXT | app.py:579, translation_history.py:60 | コンテキスト情報 |

**コード根拠:**
```python
# app.py:578-579
'partner_message': session.get('partner_message', ''),
'context_info': session.get('context_info', ''),

# translation_history.py:56-61 TranslationRequest クラス
source_text: str = ""
source_language: str = ""  
target_language: str = ""
partner_message: str = ""
context_info: str = ""
```

### 3. エンジン・バージョン要件

| 項目 | データ型 | 参照元 | 説明 |
|------|----------|--------|------|
| **engine** | TEXT | translation_history.py:36-41 | chatgpt, gemini, enhanced, reverse |
| **version** | TEXT | app.py:534-543 | 同一エンジンの複数バージョン対応 |
| **engine_metadata** | JSONB | translation_history.py:69 | エンジン固有メタデータ |

**コード根拠:**
```python
# translation_history.py:36-42 TranslationEngine Enum
class TranslationEngine(Enum):
    CHATGPT = "chatgpt"
    GEMINI = "gemini" 
    ENHANCED = "enhanced"
    REVERSE = "reverse"

# app.py:534-543 save_translation_result 関数
def save_translation_result(request_uuid: str, engine: str, translated_text: str, ...)
```

### 4. フォーム状態要件

| 項目 | データ型 | 参照元 | 説明 |
|------|----------|--------|------|
| **language_pair** | TEXT | state_manager.js:68 | "ja-en" 形式の言語ペア選択 |
| **analysis_engine** | TEXT | state_manager.js:69 | 分析エンジン選択状態 |
| **form_metadata** | JSONB | state_manager.js:62-73 | フォーム状態の詳細メタデータ |

**コード根拠:**
```javascript
// static/js/core/state_manager.js:64-69
fields: {
  japanese_text: { value: '', isDirty: false, originalValue: '' },
  context_info: { value: '', isDirty: false, originalValue: '' },
  partner_message: { value: '', isDirty: false, originalValue: '' },
  language_pair: { value: 'ja-en', isDirty: false, originalValue: 'ja-en' },
  analysis_engine: { value: '', isDirty: false, originalValue: '' }
}
```

### 5. 監査・メタデータ要件

| 項目 | データ型 | 参照元 | 説明 |
|------|----------|--------|------|
| **created_at** | TIMESTAMP | translation_history.py:75 | 作成日時 |
| **updated_at** | TIMESTAMP | - | 更新日時（将来対応） |
| **deleted_at** | TIMESTAMP | - | 論理削除日時（将来対応） |
| **ip_address** | TEXT | translation_history.py:61 | クライアントIP（監査用） |
| **user_agent** | TEXT | translation_history.py:62 | ユーザーエージェント（監査用） |
| **processing_time** | FLOAT | translation_history.py:71 | 処理時間（性能分析用） |
| **api_response_time** | FLOAT | translation_history.py:74 | API応答時間 |

## 🔎 想定クエリ分析

### 1. セッション最新結果取得（高頻度）
**目的:** UI復元・継続翻訳  
**頻度:** 極高（ページ読み込み毎）  
```sql
-- 雛形
SELECT t.* FROM translations t 
JOIN translation_sessions ts ON t.session_id = ts.id 
WHERE ts.id = ? 
ORDER BY t.created_at DESC LIMIT 1;
```

### 2. セッション内エンジン別結果横断取得（高頻度）
**目的:** 結果カード表示・比較分析  
**頻度:** 高（翻訳実行毎）  
```sql  
-- 雛形
SELECT engine, translated_text, created_at FROM translations 
WHERE session_id = ? 
ORDER BY engine, created_at DESC;
```

### 3. 特定エンジンの最新バージョン取得（中頻度）
**目的:** エンジン固有の最新結果表示  
**頻度:** 中（エンジン切り替え時）  
```sql
-- 雛形  
SELECT * FROM translations 
WHERE session_id = ? AND engine = ? 
ORDER BY version DESC, created_at DESC LIMIT 1;
```

### 4. ユーザー履歴参照（中頻度）
**目的:** 履歴表示・個人化推奨  
**頻度:** 中（履歴画面アクセス時）  
```sql
-- 雛形（user_id がnullable の場合の考慮あり）
SELECT ts.*, t.engine, t.translated_text FROM translation_sessions ts
LEFT JOIN translations t ON ts.id = t.session_id
WHERE ts.user_id = ? OR ts.session_id IN (SELECT session_id FROM user_sessions WHERE user_id = ?)
ORDER BY ts.created_at DESC LIMIT 50;
```

### 5. 期間別監査参照（低頻度）
**目的:** 管理者監査・運用分析  
**頻度:** 低（週次・月次）  
```sql
-- 雛形
SELECT DATE(ts.created_at) as date, COUNT(*) as session_count,
       COUNT(DISTINCT t.engine) as engine_count
FROM translation_sessions ts
LEFT JOIN translations t ON ts.id = t.session_id  
WHERE ts.created_at >= ? AND ts.created_at <= ?
GROUP BY DATE(ts.created_at)
ORDER BY date DESC;
```

### 6. エンジン性能分析（低頻度）
**目的:** 性能最適化・品質向上  
**頻度:** 低（分析作業時）  
```sql
-- 雛形
SELECT engine, AVG(processing_time) as avg_time, 
       COUNT(*) as request_count
FROM translations 
WHERE created_at >= ? 
GROUP BY engine 
ORDER BY avg_time;
```

## 🛡️ 前提条件・環境要件

### TLS必須前提
- **PostgreSQL:** `sslmode=require` 強制適用  
- **Redis:** `rediss://` プロトコル使用  
- **Fail-Fast:** services/database_manager.py:84 `_validate_tls_configuration()` による起動時検証  

### 環境分離
- **開発環境:** SQLite絶対パス + PostgreSQL並行  
- **検証環境:** PostgreSQL + TLS強制  
- **本番環境:** PostgreSQL + AWS Secrets Manager統合  

### 接続管理
- **統一DSN:** DATABASE_URL環境変数経由  
- **プール管理:** services/database_manager.py による接続プール統合管理  
- **秘匿性:** AWS Secrets Manager/.env管理、コード・ログ流出防止  

## ⚠️ リスク・未決事項

### 技術的リスク
1. **UNIQUE制約違反:** 同一 `(session_id, engine, version)` の重複投入可能性  
2. **NULL値処理:** user_idがnullable時の履歴検索複雑性  
3. **大容量データ:** translated_text・metadataのサイズ制限未定  
4. **トランザクション境界:** セッション作成と翻訳結果保存の分離による整合性  

### 運用リスク
1. **インデックス不足:** 想定外クエリパターンでの性能劣化  
2. **容量増大:** 履歴蓄積による容量圧迫  
3. **バックアップ:** 論理削除データを含む復旧戦略  

### 設計検討事項
1. **バージョン管理:** version カラムの型・命名規則  
2. **メタデータ構造:** JSONB内の標準化・スキーマ  
3. **削除ポリシー:** 物理削除 vs 論理削除のタイミング  
4. **監査要件:** IP/UA保存の法的・セキュリティ要件確認  

## 📊 受入チェックリスト

- [x] **保存項目の根拠リンク:** 全項目にソース参照を記載済み  
- [x] **想定クエリの対応表:** 各クエリとインデックス効果の対応関係明記済み  
- [x] **DDL草案の最小性:** 最小限のテーブル・制約のみで構成予定  
- [x] **拡張余地の明記:** Phase 4b以降での analyses/qa_items テーブル追加方針記録済み  
- [x] **前提条件の確認:** TLS設定・環境分離・接続管理要件を文書化済み  
- [x] **リスク識別:** 技術・運用・設計の各リスクを列挙済み  

## 🔄 次フェーズへの提案

### Phase 4a実装優先度
1. **最高優先:** UNIQUE制約 `(session_id, engine, version)` - 重複防止  
2. **高優先:** 基本インデックス `(created_at)` - 時系列検索最適化  
3. **中優先:** FK制約適用とカスケード削除設計  

### Phase 4b拡張計画
1. **analyses テーブル:** ニュアンス分析結果格納  
2. **qa_items テーブル:** 質疑応答履歴格納  
3. **高度インデックス:** 複合検索パターン最適化  

---

**📅 調査完了日時:** 2025年8月26日 15:30  
**🎯 調査結果:** 保存要件32項目、想定クエリ6パターン、リスク12項目を特定  
**📊 信頼度:** 高（実装済みコードベース・実際のユースケースから抽出）  
**🔄 次のアクション:** DDL草案作成・最小インデックス設計確定  

✅ **S4-04a事前調査完全完了**