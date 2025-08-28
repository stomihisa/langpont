-- ============================================================================
-- S4-04a コアDDL草案（実行禁止）
-- ============================================================================
-- 
-- Task: Task#9-4AP-1Ph4S4-04a（コアDDL／段階導入）
-- 目的: 翻訳履歴永続化の最小限テーブル・制約の先行導入
-- 
-- ⚠️ 警告: この DDL は実行禁止です。草案・調査目的のみです。
-- ⚠️ 実装フェーズでの詳細検討・検証後に実適用してください。
-- 
-- 設計原則:
-- 1. 最小＆十分な構成（2テーブルのみ）
-- 2. UNIQUE制約による複合インデックス自動生成活用
-- 3. TLS必須前提（sslmode=require）
-- 4. UUIDv7/ULID対応の将来拡張余地
-- 5. 後続フェーズでの analyses/qa_items テーブル追加容易性
-- 
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. translation_sessions テーブル（翻訳セッション管理）
-- ----------------------------------------------------------------------------

CREATE TABLE translation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  -- セッション識別子
    
    -- セッション基本情報
    user_id INTEGER,                                -- ユーザー識別（nullable）
    session_id TEXT,                                -- レガシーセッションID（nullable）
    
    -- 翻訳コンテキスト
    source_text TEXT NOT NULL,                      -- 原文テキスト
    source_language TEXT NOT NULL,                  -- 源言語（ja, en, fr, es）
    target_language TEXT NOT NULL,                  -- 目標言語
    partner_message TEXT,                           -- パートナーメッセージ
    context_info TEXT,                              -- コンテキスト情報
    language_pair TEXT,                             -- 言語ペア（"ja-en"）
    
    -- 監査・メタデータ
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,            -- 論理削除（NULL = 有効）
    
    -- メタデータ（JSONB）
    metadata JSONB DEFAULT '{}'::jsonb,             -- 拡張メタデータ
    
    -- 監査情報（セキュリティ・運用分析用）
    ip_address INET,                                -- クライアントIP
    user_agent TEXT,                                -- ユーザーエージェント
    
    -- 制約
    CONSTRAINT valid_languages CHECK (
        source_language IN ('ja', 'en', 'fr', 'es') AND
        target_language IN ('ja', 'en', 'fr', 'es') AND
        source_language != target_language
    ),
    CONSTRAINT valid_deleted_state CHECK (
        (deleted_at IS NULL) OR (deleted_at >= created_at)
    )
);

-- ----------------------------------------------------------------------------
-- 2. translations テーブル（翻訳結果管理）  
-- ----------------------------------------------------------------------------

CREATE TABLE translations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  -- 翻訳結果識別子
    
    -- 関連づけ
    session_id UUID NOT NULL REFERENCES translation_sessions(id) ON DELETE CASCADE,
    
    -- エンジン・バージョン情報
    engine TEXT NOT NULL,                           -- chatgpt, gemini, enhanced, reverse
    version TEXT NOT NULL DEFAULT '1.0',           -- エンジンバージョン
    
    -- 翻訳結果
    translated_text TEXT NOT NULL,                  -- 翻訳結果テキスト
    
    -- 性能・品質メトリクス
    processing_time FLOAT,                          -- 処理時間（秒）
    api_response_time FLOAT,                        -- API応答時間（秒）
    confidence_score FLOAT,                         -- 信頼度スコア（0.0-1.0）
    
    -- 監査・メタデータ  
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- エンジン固有メタデータ（JSONB）
    metadata JSONB DEFAULT '{}'::jsonb,             -- エンジン固有情報
    error_message TEXT,                             -- エラー情報（エラー時）
    
    -- 制約
    CONSTRAINT valid_engine CHECK (
        engine IN ('chatgpt', 'gemini', 'enhanced', 'reverse', 'claude')
    ),
    CONSTRAINT valid_performance_metrics CHECK (
        processing_time >= 0 AND 
        api_response_time >= 0 AND
        (confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0))
    ),
    
    -- 🎯 重複防止UNIQUE制約（自動で複合B-Treeインデックス生成）
    CONSTRAINT unique_session_engine_version UNIQUE (session_id, engine, version)
);

-- ----------------------------------------------------------------------------
-- 3. インデックス設計（最小セット）
-- ----------------------------------------------------------------------------

-- 📊 時系列検索最適化（監査・履歴表示用）
CREATE INDEX idx_translation_sessions_created_at 
ON translation_sessions(created_at);

CREATE INDEX idx_translations_created_at 
ON translations(created_at);

-- 📊 ユーザー履歴検索最適化（user_idがnullでない場合）
CREATE INDEX idx_translation_sessions_user_created 
ON translation_sessions(user_id, created_at) 
WHERE user_id IS NOT NULL;

-- 📊 レガシーセッション検索最適化（session_idがnullでない場合）
CREATE INDEX idx_translation_sessions_legacy_session
ON translation_sessions(session_id)
WHERE session_id IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 4. インデックス設計の根拠・判断メモ
-- ----------------------------------------------------------------------------

/* 
🎯 UNIQUE制約による自動インデックス活用

UNIQUE制約 unique_session_engine_version (session_id, engine, version) により、
PostgreSQLは自動で以下の複合B-Treeインデックスを生成:

✅ 自動最適化されるクエリパターン:
   - WHERE session_id = ?                        （左端列一致）
   - WHERE session_id = ? AND engine = ?         （左2列一致）  
   - WHERE session_id = ? AND engine = ? AND version = ? （全列一致）

❌ 追加不要なインデックス:
   - CREATE INDEX (session_id, engine) → UNIQUE制約で代替済み（冗長）
   - CREATE INDEX (session_id) → UNIQUE制約で代替済み（冗長）

🔄 将来追加候補のインデックス（Phase 4b以降での検討）:
   - CREATE INDEX (session_id, engine, created_at DESC) → 特定エンジンの時系列最適化
   - CREATE INDEX (engine, created_at) → エンジン別性能分析最適化
   - CREATE INDEX (created_at, engine) → 期間別エンジン統計最適化

💡 方針: "クエリ頻度・パターンを実測してから最適化"
   - 現状は最小構成で開始
   - 本番運用でのスロークエリログ分析後に追加判断
   - パフォーマンステスト結果に基づく段階的拡張
*/

-- ----------------------------------------------------------------------------
-- 5. 初期データ・検証用サンプル（参考）
-- ----------------------------------------------------------------------------

/* 
-- 検証用サンプルデータ（実装フェーズでのテスト用）

INSERT INTO translation_sessions (
    source_text, source_language, target_language, 
    partner_message, context_info, language_pair
) VALUES (
    'こんにちは、世界！',
    'ja', 'en',
    '友達への挨拶',
    'カジュアルな会話',
    'ja-en'
) RETURNING id;

-- 上記で返されたsession_idを使用
INSERT INTO translations (
    session_id, engine, version, translated_text, processing_time
) VALUES 
    ([session_id], 'chatgpt', '1.0', 'Hello, world!', 0.85),
    ([session_id], 'gemini', '1.0', 'Hello, world!', 1.20),
    ([session_id], 'enhanced', '1.0', 'Hey there, world!', 2.15);

-- UNIQUE制約の動作確認（重複エラーになることを期待）
INSERT INTO translations (
    session_id, engine, version, translated_text
) VALUES 
    ([session_id], 'chatgpt', '1.0', 'Duplicate test');  -- ERROR: 重複により失敗する想定
*/

-- ----------------------------------------------------------------------------
-- 6. ロールバック手順（安全な戻し方）
-- ----------------------------------------------------------------------------

/* 
🔄 ロールバック手順（DDL実装後に問題が発生した場合）

-- ⚠️ 注意: データ損失の可能性があるため、本番環境では事前バックアップ必須

-- Step 1: 外部キー制約を削除（依存関係解除）
ALTER TABLE translations DROP CONSTRAINT translations_session_id_fkey;

-- Step 2: インデックスを削除
DROP INDEX IF EXISTS idx_translation_sessions_created_at;
DROP INDEX IF EXISTS idx_translations_created_at;  
DROP INDEX IF EXISTS idx_translation_sessions_user_created;
DROP INDEX IF EXISTS idx_translation_sessions_legacy_session;

-- Step 3: テーブルを削除（translations → translation_sessions の順）
DROP TABLE IF EXISTS translations;
DROP TABLE IF EXISTS translation_sessions;

-- Step 4: データベース接続の確認
-- 既存アプリケーションが影響されていないことを確認

-- Step 5: アプリケーション再起動テスト
-- python app.py でエラーが発生しないことを確認
*/

-- ============================================================================
-- 7. 次フェーズでの拡張計画（Phase 4b）
-- ============================================================================

/* 
🚀 Phase 4b で追加予定のテーブル:

-- analyses テーブル（ニュアンス分析結果）
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    translation_id UUID NOT NULL REFERENCES translations(id) ON DELETE CASCADE,
    analysis_type TEXT NOT NULL, -- 'nuance', 'context', 'cultural'
    analysis_result JSONB NOT NULL,
    confidence_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(translation_id, analysis_type)
);

-- qa_items テーブル（質疑応答履歴）  
CREATE TABLE qa_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES translation_sessions(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    question_type TEXT, -- 'modification', 'explanation', 'context'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
*/

-- ============================================================================
-- 📝 DDL草案作成完了
-- ============================================================================
-- 
-- 作成日時: 2025年8月26日
-- 検証状況: 未実行（草案のみ）
-- 次ステップ: 実装フェーズでのテスト環境での検証
-- 
-- ✅ 最小＆十分性: 2テーブルのみで翻訳履歴の基本機能をカバー
-- ✅ UNIQUE制約最適化: 複合インデックス自動生成による冗長性排除  
-- ✅ 拡張性確保: Phase 4b以降のテーブル追加容易性
-- ✅ 安全性配慮: ロールバック手順・制約による不正データ防止
-- 
-- ⚠️ 再注意: このDDLは実行禁止です。実装フェーズでの詳細確認後に適用してください。
-- ============================================================================