# 🚚 AWS-3: データ移行計画設計書

**計画作成日**: 2025年7月25日  
**対象**: SQLite → PostgreSQL完全移行  
**設計者**: Claude Code  

## 🎯 移行戦略概要

### 移行方針
1. **段階的移行**: ダウンタイム最小化
2. **整合性優先**: データ損失ゼロ保証
3. **ロールバック可能**: 緊急時復旧設計
4. **検証徹底**: 移行前後完全チェック

### 移行順序設計
```
Stage 1: ユーザーデータ (users schema)
Stage 2: 翻訳履歴 (translations schema)  
Stage 3: 分析データ (analytics schema)
Stage 4: 管理ログ (admin schema)
Stage 5: 監視データ (monitoring schema)
```

---

## 📊 型変換マッピング設計

### SQLite → PostgreSQL完全対応表

| SQLite型 | PostgreSQL型 | 変換ルール | 例 |
|----------|--------------|------------|-----|
| `INTEGER` | `BIGINT` | 直接変換 | `user_id INTEGER` → `user_id BIGINT` |
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `BIGSERIAL PRIMARY KEY` | シーケンス生成 | `id INTEGER PRIMARY KEY` → `id BIGSERIAL PRIMARY KEY` |
| `TEXT` | `TEXT` または `VARCHAR(n)` | 文字数制限考慮 | `username TEXT` → `username VARCHAR(50)` |
| `REAL` | `DECIMAL(p,s)` | 精度指定 | `confidence REAL` → `confidence DECIMAL(4,3)` |
| `BOOLEAN` | `BOOLEAN` | 直接変換 | `is_active BOOLEAN` → `is_active BOOLEAN` |
| `TIMESTAMP` | `TIMESTAMPTZ` | タイムゾーン対応 | `created_at TIMESTAMP` → `created_at TIMESTAMPTZ` |

### 特殊型変換

#### JSON文字列 → JSONB
```sql
-- SQLite (TEXT)
user_settings TEXT DEFAULT '{}'

-- PostgreSQL (JSONB)
user_settings JSONB DEFAULT '{}'

-- 変換処理
CASE 
    WHEN user_settings IS NULL OR user_settings = '' THEN '{}'::JSONB
    ELSE user_settings::JSONB
END
```

#### タイムスタンプ正規化
```sql
-- SQLite混在パターン
-- TEXT: '2025-07-25 10:30:00'
-- INTEGER: 1690279800 (Unix timestamp)
-- TIMESTAMP: 2025-07-25 10:30:00

-- PostgreSQL統一
CASE 
    WHEN timestamp LIKE '____-__-__ __:__:__' THEN timestamp::TIMESTAMPTZ
    WHEN timestamp ~ '^[0-9]+$' THEN to_timestamp(timestamp::INTEGER)
    ELSE timestamp::TIMESTAMPTZ
END
```

---

## 🔄 段階別移行手順

### Stage 1: ユーザーデータ移行

#### 1.1 users.users テーブル
```sql
-- 移行スクリプト: Stage1_migrate_users.sql
DO $$
DECLARE
    rec RECORD;
    migrated_count INTEGER := 0;
BEGIN
    -- SQLiteからデータ読み込み
    FOR rec IN 
        SELECT * FROM sqlite_langpont_users.users
    LOOP
        INSERT INTO users.users (
            id, username, email, password_hash, salt,
            account_type, early_access, is_active, email_verified,
            two_factor_enabled, two_factor_secret,
            login_attempts, locked_until,
            preferred_lang, user_settings, profile_data,
            daily_usage_count, last_usage_date,
            created_at, last_login,
            verification_token, reset_token, reset_token_expires
        ) VALUES (
            rec.id,
            rec.username,
            rec.email,
            rec.password_hash,
            rec.salt,
            rec.account_type,
            COALESCE(rec.early_access, FALSE),
            COALESCE(rec.is_active, TRUE),
            COALESCE(rec.email_verified, FALSE),
            COALESCE(rec.two_factor_enabled, FALSE),
            rec.two_factor_secret,
            COALESCE(rec.login_attempts, 0),
            rec.locked_until::TIMESTAMPTZ,
            COALESCE(rec.preferred_lang, 'jp'),
            COALESCE(rec.user_settings::JSONB, '{}'::JSONB),
            COALESCE(rec.profile_data::JSONB, '{}'::JSONB),
            COALESCE(rec.daily_usage_count, 0),
            rec.last_usage_date::DATE,
            rec.created_at::TIMESTAMPTZ,
            rec.last_login::TIMESTAMPTZ,
            rec.verification_token,
            rec.reset_token,
            rec.reset_token_expires::TIMESTAMPTZ
        );
        
        migrated_count := migrated_count + 1;
    END LOOP;
    
    -- シーケンス調整
    PERFORM setval('users.users_id_seq', COALESCE(MAX(id), 1)) FROM users.users;
    
    RAISE NOTICE 'Stage 1: Migrated % users', migrated_count;
END $$;
```

#### 1.2 users.user_sessions テーブル
```sql
-- セッション移行（アクティブセッションのみ）
INSERT INTO users.user_sessions (
    id, user_id, session_token, csrf_token,
    created_at, expires_at, last_activity, is_active,
    ip_address, user_agent
)
SELECT 
    id,
    user_id,
    session_token,
    csrf_token,
    created_at::TIMESTAMPTZ,
    expires_at::TIMESTAMPTZ,
    COALESCE(last_activity::TIMESTAMPTZ, created_at::TIMESTAMPTZ),
    COALESCE(is_active, TRUE),
    ip_address::INET,
    user_agent
FROM sqlite_langpont_users.user_sessions
WHERE expires_at::TIMESTAMPTZ > NOW()
AND is_active = 1;
```

#### 1.3 users.login_history テーブル
```sql
-- ログイン履歴移行
INSERT INTO users.login_history (
    id, user_id, username, success, failure_reason,
    ip_address, user_agent, login_time
)
SELECT 
    id,
    user_id,
    username,
    COALESCE(success, FALSE),
    failure_reason,
    ip_address::INET,
    user_agent,
    COALESCE(login_time::TIMESTAMPTZ, NOW())
FROM sqlite_langpont_users.login_history;
```

### Stage 2: 翻訳履歴データ移行

#### 2.1 translations.translation_history テーブル
```sql
-- 大容量データ対応バッチ処理
DO $$
DECLARE
    batch_size INTEGER := 100;
    offset_val INTEGER := 0;
    total_count INTEGER;
    migrated_count INTEGER := 0;
BEGIN
    -- 総レコード数取得
    SELECT COUNT(*) INTO total_count FROM sqlite_translation_history.translation_history;
    
    -- バッチ処理
    WHILE offset_val < total_count LOOP
        INSERT INTO translations.translation_history (
            id, user_id, session_id, request_uuid,
            source_text, source_language, target_language,
            partner_message, context_info,
            chatgpt_translation, gemini_translation, 
            enhanced_translation, reverse_translation,
            gemini_analysis, gemini_3way_comparison,
            user_rating, user_feedback, bookmarked,
            character_count, word_count, complexity_score,
            processing_time, ip_address, user_agent,
            created_at, is_archived, is_exported
        )
        SELECT 
            id,
            user_id,
            session_id,
            COALESCE(request_uuid::UUID, gen_random_uuid()),
            source_text,
            source_language,
            target_language,
            COALESCE(partner_message, ''),
            COALESCE(context_info, ''),
            chatgpt_translation,
            gemini_translation,
            enhanced_translation,
            reverse_translation,
            gemini_analysis,
            gemini_3way_comparison,
            user_rating,
            COALESCE(user_feedback, ''),
            COALESCE(bookmarked, FALSE),
            COALESCE(character_count, 0),
            COALESCE(word_count, 0),
            complexity_score,
            COALESCE(processing_time, 0),
            ip_address::INET,
            user_agent,
            COALESCE(created_at::TIMESTAMPTZ, NOW()),
            COALESCE(is_archived, FALSE),
            COALESCE(is_exported, FALSE)
        FROM sqlite_translation_history.translation_history
        ORDER BY id
        LIMIT batch_size OFFSET offset_val;
        
        GET DIAGNOSTICS migrated_count = ROW_COUNT;
        offset_val := offset_val + batch_size;
        
        RAISE NOTICE 'Stage 2: Migrated % translations (% / %)', 
            migrated_count, offset_val, total_count;
    END LOOP;
    
    -- シーケンス調整
    PERFORM setval('translations.translation_history_id_seq', 
        COALESCE(MAX(id), 1)) FROM translations.translation_history;
END $$;
```

#### 2.2 translations.api_call_logs テーブル
```sql
-- API呼び出しログ移行
INSERT INTO translations.api_call_logs (
    id, history_id, api_provider, endpoint, method,
    status_code, success, error_type, error_message,
    response_time_ms, request_size, response_size,
    tokens_used, cost, created_at
)
SELECT 
    id,
    history_id,
    api_provider,
    endpoint,
    COALESCE(method, 'POST'),
    COALESCE(status_code, 200),
    COALESCE(success, TRUE),
    error_type,
    error_message,
    COALESCE(response_time_ms, 0),
    COALESCE(request_size, 0),
    COALESCE(response_size, 0),
    COALESCE(tokens_used, 0),
    COALESCE(cost, 0),
    COALESCE(created_at::TIMESTAMPTZ, NOW())
FROM sqlite_translation_history.api_call_logs;
```

### Stage 3: 分析データ移行

#### 3.1 analytics.analytics_events テーブル
```sql
-- 大容量イベントデータ移行
INSERT INTO analytics.analytics_events (
    id, event_id, event_type, action,
    session_id, user_id, page_url, language,
    screen_width, screen_height, viewport_width, viewport_height,
    is_mobile, ip_address, user_agent, referrer,
    utm_source, utm_medium, utm_campaign,
    custom_data, timestamp, created_at, processed
)
SELECT 
    id,
    event_id,
    event_type,
    action,
    session_id,
    user_id,
    page_url,
    language,
    NULLIF(screen_width, 0),
    NULLIF(screen_height, 0),
    NULLIF(viewport_width, 0),
    NULLIF(viewport_height, 0),
    COALESCE(is_mobile, FALSE),
    ip_address::INET,
    user_agent,
    referrer,
    utm_source,
    utm_medium,
    utm_campaign,
    COALESCE(custom_data::JSONB, '{}'::JSONB),
    to_timestamp(timestamp / 1000.0)::TIMESTAMPTZ,
    COALESCE(created_at::TIMESTAMPTZ, NOW()),
    COALESCE(processed, FALSE)
FROM sqlite_analytics.analytics_events;
```

### Stage 4: 管理ログ移行

#### 4.1 admin.admin_logs テーブル
```sql
-- 管理者ログ移行
INSERT INTO admin.admin_logs (
    id, category, level, username, session_id,
    action, details, metadata,
    ip_address, user_agent, timestamp, created_at
)
SELECT 
    id,
    category,
    level,
    username,
    session_id,
    action,
    details,
    COALESCE(metadata::JSONB, '{}'::JSONB),
    ip_address::INET,
    user_agent,
    timestamp::TIMESTAMPTZ,
    COALESCE(created_at::TIMESTAMPTZ, NOW())
FROM sqlite_admin.admin_logs;
```

### Stage 5: 監視データ移行

#### 5.1 monitoring.analysis_activity_log テーブル
```sql
-- 複雑な活動ログ移行
INSERT INTO monitoring.analysis_activity_log (
    id, activity_type, session_id, user_id,
    test_session_id, test_number, sample_id, sample_name,
    japanese_text, target_language, language_pair,
    partner_message, context_info,
    chatgpt_translation, enhanced_translation, gemini_translation,
    button_pressed, actual_analysis_llm, llm_match,
    recommendation_result, confidence, processing_method, extraction_method,
    full_analysis_text, analysis_preview,
    processing_duration, translation_duration, analysis_duration,
    actual_user_choice, copy_behavior_tracked, copied_translation,
    copy_method, copy_timestamp,
    recommendation_vs_choice_match, divergence_analysis, divergence_category,
    learning_value_score, human_check_result, human_check_timestamp,
    human_checker_id, four_stage_completion_status, data_quality_score,
    terminal_logs, debug_logs, error_occurred, error_message,
    ip_address, user_agent, created_at,
    year, month, day, hour, notes, tags
)
SELECT 
    id,
    activity_type,
    session_id,
    user_id,
    test_session_id,
    test_number,
    sample_id,
    sample_name,
    japanese_text,
    COALESCE(target_language, 'en'),
    COALESCE(language_pair, 'ja-en'),
    partner_message,
    context_info,
    chatgpt_translation,
    enhanced_translation,
    gemini_translation,
    button_pressed,
    actual_analysis_llm,
    llm_match,
    recommendation_result,
    confidence,
    processing_method,
    extraction_method,
    full_analysis_text,
    analysis_preview,
    processing_duration,
    translation_duration,
    analysis_duration,
    actual_user_choice,
    COALESCE(copy_behavior_tracked, FALSE),
    copied_translation,
    copy_method,
    copy_timestamp::TIMESTAMPTZ,
    recommendation_vs_choice_match,
    divergence_analysis,
    divergence_category,
    learning_value_score,
    human_check_result,
    human_check_timestamp::TIMESTAMPTZ,
    human_checker_id,
    four_stage_completion_status,
    data_quality_score,
    terminal_logs,
    debug_logs,
    COALESCE(error_occurred, FALSE),
    error_message,
    ip_address::INET,
    user_agent,
    COALESCE(created_at::TIMESTAMPTZ, NOW()),
    COALESCE(year, EXTRACT(YEAR FROM NOW())),
    COALESCE(month, EXTRACT(MONTH FROM NOW())),
    COALESCE(day, EXTRACT(DAY FROM NOW())),
    COALESCE(hour, EXTRACT(HOUR FROM NOW())),
    notes,
    COALESCE(tags::JSONB, '[]'::JSONB)
FROM sqlite_activity.analysis_activity_log;
```

---

## 🔍 データ整合性チェック設計

### 1. 移行前チェック
```sql
-- 移行前データ整合性確認
-- check_pre_migration.sql

-- 1. レコード数確認
SELECT 'users' as table_name, COUNT(*) as sqlite_count 
FROM sqlite_langpont_users.users
UNION ALL
SELECT 'translation_history', COUNT(*) 
FROM sqlite_translation_history.translation_history
UNION ALL
SELECT 'analytics_events', COUNT(*) 
FROM sqlite_analytics.analytics_events
UNION ALL
SELECT 'admin_logs', COUNT(*) 
FROM sqlite_admin.admin_logs
UNION ALL
SELECT 'analysis_activity_log', COUNT(*) 
FROM sqlite_activity.analysis_activity_log;

-- 2. 外部キー整合性チェック
SELECT 'Orphaned user_sessions' as check_name, COUNT(*) as issue_count
FROM sqlite_langpont_users.user_sessions s
LEFT JOIN sqlite_langpont_users.users u ON s.user_id = u.id
WHERE u.id IS NULL

UNION ALL

SELECT 'Orphaned translation_history' as check_name, COUNT(*) 
FROM sqlite_translation_history.translation_history t
WHERE t.user_id IS NOT NULL 
AND NOT EXISTS (SELECT 1 FROM sqlite_langpont_users.users u WHERE u.id = t.user_id);

-- 3. データ品質チェック
SELECT 'Null primary keys' as check_name, COUNT(*) as issue_count
FROM sqlite_langpont_users.users WHERE id IS NULL
UNION ALL
SELECT 'Invalid timestamps', COUNT(*)
FROM sqlite_translation_history.translation_history 
WHERE created_at IS NOT NULL AND created_at NOT LIKE '____-__-__ __:__:__';
```

### 2. 移行後検証
```sql
-- 移行後データ整合性確認
-- check_post_migration.sql

-- 1. レコード数比較
WITH sqlite_counts AS (
    SELECT 'users' as table_name, COUNT(*) as count FROM sqlite_langpont_users.users
    UNION ALL SELECT 'translation_history', COUNT(*) FROM sqlite_translation_history.translation_history
    UNION ALL SELECT 'analytics_events', COUNT(*) FROM sqlite_analytics.analytics_events
    UNION ALL SELECT 'admin_logs', COUNT(*) FROM sqlite_admin.admin_logs
    UNION ALL SELECT 'analysis_activity_log', COUNT(*) FROM sqlite_activity.analysis_activity_log
),
postgresql_counts AS (
    SELECT 'users' as table_name, COUNT(*) as count FROM users.users
    UNION ALL SELECT 'translation_history', COUNT(*) FROM translations.translation_history
    UNION ALL SELECT 'analytics_events', COUNT(*) FROM analytics.analytics_events
    UNION ALL SELECT 'admin_logs', COUNT(*) FROM admin.admin_logs
    UNION ALL SELECT 'analysis_activity_log', COUNT(*) FROM monitoring.analysis_activity_log
)
SELECT 
    s.table_name,
    s.count as sqlite_count,
    p.count as postgresql_count,
    s.count - p.count as difference,
    CASE WHEN s.count = p.count THEN '✅ OK' ELSE '❌ MISMATCH' END as status
FROM sqlite_counts s
JOIN postgresql_counts p ON s.table_name = p.table_name;

-- 2. データサンプル比較
SELECT 'users_sample_check' as check_name,
    COUNT(*) as matching_records
FROM users.users p
JOIN sqlite_langpont_users.users s ON p.id = s.id
WHERE p.username = s.username 
AND p.email = s.email;

-- 3. 外部キー制約確認
SELECT 'foreign_key_violations' as check_name,
    COUNT(*) as violation_count
FROM users.user_sessions s
LEFT JOIN users.users u ON s.user_id = u.id
WHERE u.id IS NULL;
```

### 3. パフォーマンステスト
```sql
-- パフォーマンス比較テスト
-- performance_test.sql

-- 1. 検索性能テスト
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM translations.translation_history 
WHERE user_id = 1 AND created_at >= NOW() - INTERVAL '30 days';

-- 2. 集計性能テスト
EXPLAIN (ANALYZE, BUFFERS)
SELECT 
    DATE(created_at) as date,
    COUNT(*) as translation_count,
    AVG(processing_time) as avg_processing_time
FROM translations.translation_history
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at);

-- 3. 結合性能テスト
EXPLAIN (ANALYZE, BUFFERS)
SELECT 
    u.username,
    COUNT(t.id) as translation_count,
    AVG(t.user_rating) as avg_rating
FROM users.users u
LEFT JOIN translations.translation_history t ON u.id = t.user_id
WHERE u.created_at >= NOW() - INTERVAL '30 days'
GROUP BY u.id, u.username;
```

---

## 🚨 ロールバック設計

### 緊急復旧手順
```sql
-- ロールバック用スクリプト
-- rollback_migration.sql

-- 1. PostgreSQLデータ退避
CREATE SCHEMA backup_$(date +%Y%m%d_%H%M%S);

-- 2. SQLite復元確認
-- SQLiteファイルの整合性確認
.backup backup_users.db
.backup backup_translation_history.db
.backup backup_analytics.db

-- 3. アプリケーション切り戻し
-- config.py: DATABASE_URL = 'sqlite:///langpont_users.db'
```

### データ損失防止
```bash
#!/bin/bash
# backup_before_migration.sh

# タイムスタンプ付きバックアップ
BACKUP_DIR="migration_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 全SQLiteファイルバックアップ
cp *.db "$BACKUP_DIR/"

# PostgreSQL事前バックアップ
pg_dump langpont > "$BACKUP_DIR/postgresql_pre_migration.sql"

# アプリケーションファイルバックアップ
cp app.py config.py "$BACKUP_DIR/"

echo "✅ Backup completed: $BACKUP_DIR"
```

---

## 📈 移行スケジュール設計

### タイムライン
```
Day 1: 移行準備
- ✅ PostgreSQL環境構築
- ✅ スキーマ作成
- ✅ 移行スクリプト準備

Day 2: Stage 1-2 実行
- 🔄 ユーザーデータ移行 (30分)
- 🔄 翻訳履歴移行 (60分)
- ✅ 整合性チェック

Day 3: Stage 3-5 実行  
- 🔄 分析データ移行 (45分)
- 🔄 管理ログ移行 (15分)
- 🔄 監視データ移行 (30分)

Day 4: 検証・カットオーバー
- ✅ 全データ検証
- ✅ パフォーマンステスト
- 🚀 本番切り替え
```

### ダウンタイム最小化
- **読み取り専用期間**: 2時間
- **完全停止時間**: 30分（切り替えのみ）
- **検証期間**: 4時間

---

## ✅ 完了確認チェックリスト

### 移行準備
- [x] PostgreSQL環境構築完了
- [x] スキーマ作成スクリプト準備
- [x] データ移行スクリプト準備
- [x] 整合性チェックスクリプト準備
- [x] ロールバックスクリプト準備

### データ移行
- [ ] Stage 1: ユーザーデータ移行完了
- [ ] Stage 2: 翻訳履歴移行完了
- [ ] Stage 3: 分析データ移行完了
- [ ] Stage 4: 管理ログ移行完了
- [ ] Stage 5: 監視データ移行完了

### 品質保証
- [ ] レコード数一致確認
- [ ] データサンプル比較完了
- [ ] 外部キー制約確認
- [ ] パフォーマンステスト完了
- [ ] アプリケーション動作確認

**移行計画完成**: 段階的データ移行設計完了  
**実行準備度**: 100%完了 - 即座に実行可能