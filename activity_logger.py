#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Task 2.9.2 Phase B-3.5.10: Comprehensive Activity Logging System
LangPont 統合活動履歴管理システム

全ての分析活動（通常利用・手動テスト・自動テスト）を統一的に記録・管理
"""

import sqlite3
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import os
import logging

# 🗾 JSTタイムゾーン定義
JST = timezone(timedelta(hours=9))

def get_jst_now():
    """日本時間で現在時刻を取得"""
    return datetime.now(JST)

def get_jst_today():
    """日本時間で今日の日付を取得"""
    return get_jst_now().date()

class ActivityLogger:
    """LangPont統合活動ログシステム"""
    
    def __init__(self, db_path: str = "langpont_activity_log.db"):
        self.db_path = db_path
        
        # ログ設定を最初に行う（init_database前に必要）
        self.setup_logger()
        
        # データベース初期化
        self.init_database()
    
    def setup_logger(self):
        """ロガーのセットアップ"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def init_database(self):
        """データベース初期化・テーブル作成"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 統合活動ログテーブル
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- 活動分類
                activity_type TEXT NOT NULL,              -- 'normal_use' | 'manual_test' | 'automated_test'
                session_id TEXT,                          -- セッションID
                user_id TEXT,                             -- ユーザーID（admin/developer/guest等）
                
                -- テスト関連（自動テストの場合）
                test_session_id TEXT,                     -- バッチテストセッションID
                test_number INTEGER,                      -- テスト番号
                sample_id INTEGER,                        -- サンプルID
                sample_name TEXT,                         -- サンプル名
                
                -- 入力データ
                japanese_text TEXT,                       -- 日本語原文
                target_language TEXT DEFAULT 'en',       -- 対象言語（en/fr/es）
                language_pair TEXT DEFAULT 'ja-en',      -- 言語ペア
                partner_message TEXT,                     -- パートナーメッセージ
                context_info TEXT,                        -- コンテキスト情報
                
                -- 翻訳結果
                chatgpt_translation TEXT,                 -- ChatGPT翻訳
                enhanced_translation TEXT,                -- Enhanced翻訳（改善ChatGPT）
                gemini_translation TEXT,                  -- Gemini翻訳
                
                -- 分析実行データ
                button_pressed TEXT,                      -- 押下ボタン（ChatGPT/Gemini/Claude）
                actual_analysis_llm TEXT,                 -- 実際分析LLM
                llm_match BOOLEAN,                        -- ボタンとLLMの一致フラグ
                
                -- 分析結果
                recommendation_result TEXT,               -- 推奨結果（Enhanced/ChatGPT/Gemini）
                confidence REAL,                          -- 信頼度（0.0-1.0）
                processing_method TEXT,                   -- 推奨抽出方法
                extraction_method TEXT,                   -- 抽出詳細方法
                
                -- 分析内容
                full_analysis_text TEXT,                  -- ニュアンス分析結果全文
                analysis_preview TEXT,                    -- 分析プレビュー（最初200文字）
                
                -- 実行ログ
                terminal_logs TEXT,                       -- 関連ターミナルログ
                debug_logs TEXT,                          -- デバッグログ
                error_occurred BOOLEAN DEFAULT 0,        -- エラー発生フラグ
                error_message TEXT,                       -- エラーメッセージ
                
                -- パフォーマンス
                processing_duration REAL,                -- 処理時間（秒）
                translation_duration REAL,               -- 翻訳処理時間
                analysis_duration REAL,                  -- 分析処理時間
                
                -- メタデータ
                ip_address TEXT,                          -- IPアドレス
                user_agent TEXT,                          -- ユーザーエージェント
                request_headers TEXT,                     -- リクエストヘッダー（JSON）
                
                -- タイムスタンプ
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                year INTEGER,                             -- 年（インデックス用）
                month INTEGER,                            -- 月（インデックス用）
                day INTEGER,                              -- 日（インデックス用）
                hour INTEGER,                             -- 時（インデックス用）
                
                -- 第0段階: 人間チェック
                stage0_human_check TEXT,                  -- 人間による推奨判定 (ChatGPT/Enhanced/Gemini/None)
                stage0_human_check_date TIMESTAMP,        -- 人間チェック日時
                stage0_human_check_user TEXT,             -- チェック実施者
                
                -- 追加メモ
                notes TEXT,                               -- 手動メモ
                tags TEXT                                 -- タグ（JSON配列）
            )
        """)
            
            # 既存テーブルに新カラムを追加（安全に）
            try:
                cursor.execute("ALTER TABLE analysis_activity_log ADD COLUMN stage0_human_check TEXT")
                self.logger.info("Added stage0_human_check column")
            except sqlite3.OperationalError:
                pass  # カラムが既に存在する場合
                
            try:
                cursor.execute("ALTER TABLE analysis_activity_log ADD COLUMN stage0_human_check_date TIMESTAMP")
                self.logger.info("Added stage0_human_check_date column")
            except sqlite3.OperationalError:
                pass  # カラムが既に存在する場合
                
            try:
                cursor.execute("ALTER TABLE analysis_activity_log ADD COLUMN stage0_human_check_user TEXT")
                self.logger.info("Added stage0_human_check_user column")
            except sqlite3.OperationalError:
                pass  # カラムが既に存在する場合
            
            # インデックス作成（パフォーマンス最適化）
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_type ON analysis_activity_log(activity_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON analysis_activity_log(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON analysis_activity_log(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_year_month ON analysis_activity_log(year, month)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_button_pressed ON analysis_activity_log(button_pressed)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_actual_llm ON analysis_activity_log(actual_analysis_llm)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_occurred ON analysis_activity_log(error_occurred)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stage0_human_check ON analysis_activity_log(stage0_human_check)")
            
            # テストサンプル管理テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_name TEXT NOT NULL,
                    japanese_text TEXT NOT NULL,
                    category TEXT DEFAULT 'general',          -- 'technical', 'business', 'casual'
                    description TEXT,
                    expected_result TEXT,                      -- 期待される結果
                    difficulty_level INTEGER DEFAULT 1,       -- 難易度 1-5
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # 🎯 4段階分析システム用のカラムを追加（既存テーブルの拡張）
            self._add_four_stage_analysis_columns(cursor)
        
            conn.commit()
            conn.close()
            
            if hasattr(self, 'logger'):
                self.logger.info(f"✅ Activity Logger database initialized: {self.db_path}")
            else:
                print(f"✅ Activity Logger database initialized: {self.db_path}")
                
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"❌ Failed to initialize database: {str(e)}")
            else:
                print(f"❌ Failed to initialize database: {str(e)}")
            raise
    
    def _add_four_stage_analysis_columns(self, cursor):
        """🎯 4段階分析システム用のカラムを追加"""
        try:
            # 既存のカラムリストを取得
            cursor.execute("PRAGMA table_info(analysis_activity_log)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            # 4段階分析用の新しいカラムを定義
            four_stage_columns = [
                # 第0段階: 人間によるLLM推奨チェック
                ("human_check_result", "TEXT"),          # 'approved' | 'rejected' | 'pending'
                ("human_check_timestamp", "TIMESTAMP"),  # 人間チェック実行時刻
                ("human_checker_id", "TEXT"),            # チェック実行者ID
                ("human_check_notes", "TEXT"),           # 人間チェックメモ
                
                # 第1段階: LLM推奨抽出・分析（改良版）
                ("stage1_extraction_method", "TEXT"),    # 推奨抽出手法詳細
                ("stage1_confidence_score", "REAL"),     # 第1段階の信頼度
                ("stage1_processing_time", "REAL"),      # 第1段階処理時間
                ("stage1_metadata", "TEXT"),             # 第1段階メタデータ（JSON）
                
                # 第1.5段階: 補完分析
                ("stage15_supplementary_analysis", "TEXT"),    # 補完分析内容
                ("stage15_context_evaluation", "TEXT"),        # コンテキスト評価
                ("stage15_linguistic_notes", "TEXT"),          # 言語学的ノート
                
                # 第2段階: ユーザー実選択・行動分析（強化版）
                ("actual_user_choice", "TEXT"),          # 実際のユーザー選択（追跡済み）
                ("copy_behavior_tracked", "BOOLEAN"),    # コピー行動追跡済みフラグ
                ("copied_translation", "TEXT"),          # コピーされた翻訳内容
                ("copy_method", "TEXT"),                 # コピー方法（button|keyboard|other）
                ("copy_timestamp", "TIMESTAMP"),         # コピー実行時刻
                ("selection_reasoning", "TEXT"),         # 選択理由（推定・アンケート）
                ("user_confidence_level", "REAL"),       # ユーザーの確信度
                
                # 第3段階: 推奨vs実選択の一致分析（詳細版）
                ("recommendation_vs_choice_match", "BOOLEAN"),    # 推奨と実選択の一致フラグ
                ("divergence_analysis", "TEXT"),                 # 乖離分析結果
                ("divergence_category", "TEXT"),                 # 乖離カテゴリ分類
                ("learning_value_score", "REAL"),                # 学習価値スコア（0-1）
                ("feedback_loop_data", "TEXT"),                  # フィードバックループデータ（JSON）
                
                # 統合メタデータ
                ("four_stage_completion_status", "TEXT"),        # 4段階完了状況
                ("data_quality_score", "REAL"),                  # データ品質スコア
                ("analysis_revision_count", "INTEGER")           # 分析修正回数
            ]
            
            # 存在しないカラムのみ追加
            for column_name, column_type in four_stage_columns:
                if column_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE analysis_activity_log ADD COLUMN {column_name} {column_type}")
                        print(f"✅ Added column: {column_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" not in str(e):
                            print(f"⚠️ Failed to add column {column_name}: {e}")
            
            # 4段階分析用のインデックスを追加
            four_stage_indexes = [
                ("idx_human_check_result", "human_check_result"),
                ("idx_actual_user_choice", "actual_user_choice"),
                ("idx_copy_behavior_tracked", "copy_behavior_tracked"),
                ("idx_recommendation_match", "recommendation_vs_choice_match"),
                ("idx_four_stage_completion", "four_stage_completion_status")
            ]
            
            for index_name, column_name in four_stage_indexes:
                try:
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON analysis_activity_log({column_name})")
                except sqlite3.OperationalError:
                    pass  # インデックスが既に存在する場合は無視
            
            print("🎯 4段階分析用データベーススキーマ拡張完了")
            
        except Exception as e:
            print(f"❌ 4段階分析カラム追加エラー: {str(e)}")
    
    def log_activity(self, activity_data: Dict[str, Any]) -> int:
        """活動ログを記録"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # JST基準の現在時刻の詳細情報
            now = get_jst_now()
            
            # デフォルト値の設定
            activity_data.setdefault('activity_type', 'normal_use')
            activity_data.setdefault('user_id', 'anonymous')
            activity_data.setdefault('error_occurred', False)
            
            # LLM一致判定
            button_pressed = activity_data.get('button_pressed', '').lower()
            actual_llm = activity_data.get('actual_analysis_llm', '').lower()
            llm_match = button_pressed == actual_llm if button_pressed and actual_llm else None
            
            # 分析プレビュー生成
            full_analysis = activity_data.get('full_analysis_text', '')
            analysis_preview = full_analysis[:200] + '...' if len(full_analysis) > 200 else full_analysis
            
            # SQLクエリ実行
            cursor.execute("""
                INSERT INTO analysis_activity_log (
                    activity_type, session_id, user_id,
                    test_session_id, test_number, sample_id, sample_name,
                    japanese_text, target_language, language_pair, partner_message, context_info,
                    chatgpt_translation, enhanced_translation, gemini_translation,
                    button_pressed, actual_analysis_llm, llm_match,
                    recommendation_result, confidence, processing_method, extraction_method,
                    full_analysis_text, analysis_preview,
                    terminal_logs, debug_logs, error_occurred, error_message,
                    processing_duration, translation_duration, analysis_duration,
                    ip_address, user_agent, request_headers,
                    year, month, day, hour,
                    notes, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                activity_data.get('activity_type'),
                activity_data.get('session_id'),
                activity_data.get('user_id'),
                activity_data.get('test_session_id'),
                activity_data.get('test_number'),
                activity_data.get('sample_id'),
                activity_data.get('sample_name'),
                activity_data.get('japanese_text'),
                activity_data.get('target_language', 'en'),
                activity_data.get('language_pair', 'ja-en'),
                activity_data.get('partner_message'),
                activity_data.get('context_info'),
                activity_data.get('chatgpt_translation'),
                activity_data.get('enhanced_translation'),
                activity_data.get('gemini_translation'),
                activity_data.get('button_pressed'),
                activity_data.get('actual_analysis_llm'),
                llm_match,
                activity_data.get('recommendation_result'),
                activity_data.get('confidence'),
                activity_data.get('processing_method'),
                activity_data.get('extraction_method'),
                activity_data.get('full_analysis_text'),
                analysis_preview,
                activity_data.get('terminal_logs'),
                activity_data.get('debug_logs'),
                activity_data.get('error_occurred', False),
                activity_data.get('error_message'),
                activity_data.get('processing_duration'),
                activity_data.get('translation_duration'),
                activity_data.get('analysis_duration'),
                activity_data.get('ip_address'),
                activity_data.get('user_agent'),
                json.dumps(activity_data.get('request_headers', {})),
                now.year,
                now.month,
                now.day,
                now.hour,
                activity_data.get('notes'),
                json.dumps(activity_data.get('tags', []))
            ))
            
            log_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            self.logger.info(f"✅ Activity logged: ID={log_id}, Type={activity_data.get('activity_type')}")
            return log_id
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"❌ Failed to log activity: {str(e)}")
            else:
                print(f"❌ Failed to log activity: {str(e)}")
            return -1
    
    def get_activity_stats(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """活動統計を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # フィルター条件構築
        where_clause, params = self._build_where_clause(filters or {})
        
        # JST基準の基本統計
        today_jst = get_jst_today().strftime('%Y-%m-%d')
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total_activities,
                COUNT(CASE WHEN DATE(created_at, '+9 hours') = ? THEN 1 END) as today_activities,
                COUNT(CASE WHEN error_occurred = 1 THEN 1 END) as error_count,
                AVG(processing_duration) as avg_processing_time,
                COUNT(CASE WHEN llm_match = 1 THEN 1 END) as llm_match_count,
                COUNT(CASE WHEN llm_match = 0 THEN 1 END) as llm_mismatch_count
            FROM analysis_activity_log
            {where_clause}
        """, [today_jst] + params)
        
        basic_stats = cursor.fetchone()
        
        # エンジン別統計
        cursor.execute(f"""
            SELECT 
                button_pressed,
                COUNT(*) as count,
                AVG(confidence) as avg_confidence,
                AVG(processing_duration) as avg_duration
            FROM analysis_activity_log
            {where_clause}
            GROUP BY button_pressed
            ORDER BY count DESC
        """, params)
        
        engine_stats = cursor.fetchall()
        
        # 推奨結果統計
        cursor.execute(f"""
            SELECT 
                recommendation_result,
                COUNT(*) as count
            FROM analysis_activity_log
            {where_clause}
            GROUP BY recommendation_result
            ORDER BY count DESC
        """, params)
        
        recommendation_stats = cursor.fetchall()
        
        conn.close()
        
        # 統計データの構造化
        stats = {
            'basic': {
                'total_activities': basic_stats[0] or 0,
                'today_activities': basic_stats[1] or 0,
                'today_translations': basic_stats[1] or 0,  # 翻訳数として表示
                'error_count': basic_stats[2] or 0,
                'error_rate': round((basic_stats[2] or 0) / max(basic_stats[0] or 1, 1) * 100, 2),
                'avg_processing_time': round(basic_stats[3] or 0, 2),
                'llm_match_count': basic_stats[4] or 0,
                'llm_mismatch_count': basic_stats[5] or 0,
                'llm_match_rate': round((basic_stats[4] or 0) / max((basic_stats[4] or 0) + (basic_stats[5] or 0), 1) * 100, 2)
            },
            'engines': [
                {
                    'engine': row[0] or 'unknown',
                    'count': row[1],
                    'avg_confidence': round(row[2] or 0, 2),
                    'avg_duration': round(row[3] or 0, 2)
                }
                for row in engine_stats
            ],
            'recommendations': [
                {
                    'result': row[0] or 'unknown',
                    'count': row[1]
                }
                for row in recommendation_stats
            ]
        }
        
        return stats
    
    def get_activities(self, filters: Dict[str, Any] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """活動ログを取得（ページング対応）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # フィルター条件構築
        where_clause, params = self._build_where_clause(filters or {})
        
        # データ取得
        cursor.execute(f"""
            SELECT 
                id, activity_type, user_id, created_at,
                japanese_text, button_pressed, actual_analysis_llm, llm_match,
                recommendation_result, confidence, processing_duration,
                error_occurred, error_message,
                test_session_id, sample_name
            FROM analysis_activity_log
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        
        rows = cursor.fetchall()
        
        # 総件数取得
        cursor.execute(f"""
            SELECT COUNT(*) FROM analysis_activity_log {where_clause}
        """, params)
        
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        # データ構造化
        activities = []
        for row in rows:
            activities.append({
                'id': row[0],
                'activity_type': row[1],
                'user_id': row[2],
                'created_at': row[3],
                'japanese_text': row[4][:50] + '...' if row[4] and len(row[4]) > 50 else row[4],
                'button_pressed': row[5],
                'actual_analysis_llm': row[6],
                'llm_match': row[7],
                'recommendation_result': row[8],
                'confidence': row[9],
                'processing_duration': row[10],
                'error_occurred': row[11],
                'error_message': row[12],
                'test_session_id': row[13],
                'sample_name': row[14]
            })
        
        return {
            'activities': activities,
            'total_count': total_count,
            'page_count': (total_count + limit - 1) // limit,
            'current_page': offset // limit + 1
        }
    
    def get_activity_detail(self, activity_id: int) -> Optional[Dict[str, Any]]:
        """活動詳細を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM analysis_activity_log WHERE id = ?
        """, (activity_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # カラム名取得
        columns = [description[0] for description in cursor.description]
        
        # 詳細データ構造化
        detail = dict(zip(columns, row))
        
        # JSON フィールドのパース
        try:
            detail['request_headers'] = json.loads(detail['request_headers'] or '{}')
            detail['tags'] = json.loads(detail['tags'] or '[]')
        except:
            detail['request_headers'] = {}
            detail['tags'] = []
        
        return detail
    
    def _build_where_clause(self, filters: Dict[str, Any]) -> tuple:
        """フィルター条件からWHERE句を構築"""
        conditions = []
        params = []
        
        if filters.get('activity_type'):
            conditions.append("activity_type = ?")
            params.append(filters['activity_type'])
        
        if filters.get('user_id'):
            conditions.append("user_id = ?")
            params.append(filters['user_id'])
        
        if filters.get('button_pressed'):
            conditions.append("button_pressed = ?")
            params.append(filters['button_pressed'])
        
        if filters.get('date_from'):
            conditions.append("DATE(created_at) >= ?")
            params.append(filters['date_from'])
        
        if filters.get('date_to'):
            conditions.append("DATE(created_at) <= ?")
            params.append(filters['date_to'])
        
        if filters.get('error_only'):
            conditions.append("error_occurred = 1")
        
        if filters.get('llm_mismatch_only'):
            conditions.append("llm_match = 0")
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        return where_clause, params

# グローバルインスタンス
activity_logger = ActivityLogger()

def log_analysis_activity(activity_data: Dict[str, Any]) -> int:
    """グローバル関数：分析活動をログに記録"""
    return activity_logger.log_activity(activity_data)

# テスト用メイン関数
if __name__ == "__main__":
    # テストデータ
    test_activity = {
        'activity_type': 'normal_use',
        'user_id': 'test_user',
        'japanese_text': 'テスト用の日本語文章です。',
        'button_pressed': 'Claude',
        'actual_analysis_llm': 'Claude',
        'recommendation_result': 'Enhanced',
        'confidence': 0.85,
        'full_analysis_text': 'これはテスト用の分析結果です。非常に詳細な分析内容が含まれています。',
        'processing_duration': 2.5
    }
    
    # ログ記録テスト
    log_id = activity_logger.log_activity(test_activity)
    print(f"✅ Test activity logged: ID={log_id}")
    
    # 統計取得テスト
    stats = activity_logger.get_activity_stats()
    print(f"📊 Stats: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    # 活動一覧取得テスト
    activities = activity_logger.get_activities(limit=5)
    print(f"📋 Activities: {len(activities['activities'])} items")
    
    print("✅ Activity Logger test completed")


# =============================================================================
# 🎯 4段階分析システム専用機能
# =============================================================================

class FourStageAnalysisManager:
    """4段階統合分析システムの管理クラス"""
    
    def __init__(self, activity_logger: ActivityLogger):
        self.activity_logger = activity_logger
        self.db_path = activity_logger.db_path
    
    def update_stage0_human_check(self, activity_id: int, check_result: str, checker_id: str, notes: str = "") -> bool:
        """第0段階: 人間によるLLM推奨チェック結果を更新"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = get_jst_now()
            
            cursor.execute("""
                UPDATE analysis_activity_log 
                SET human_check_result = ?, 
                    human_check_timestamp = ?, 
                    human_checker_id = ?, 
                    human_check_notes = ?
                WHERE id = ?
            """, (check_result, now.isoformat(), checker_id, notes, activity_id))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Stage 0 updated: Activity {activity_id} - {check_result} by {checker_id}")
            return True
            
        except Exception as e:
            print(f"❌ Stage 0 update failed: {str(e)}")
            return False
    
    def update_stage1_analysis(self, activity_id: int, extraction_method: str, confidence: float, processing_time: float, metadata: Dict[str, Any] = None) -> bool:
        """第1段階: LLM推奨抽出・分析データを更新"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute("""
                UPDATE analysis_activity_log 
                SET stage1_extraction_method = ?, 
                    stage1_confidence_score = ?, 
                    stage1_processing_time = ?, 
                    stage1_metadata = ?
                WHERE id = ?
            """, (extraction_method, confidence, processing_time, metadata_json, activity_id))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Stage 1 updated: Activity {activity_id} - {extraction_method} (confidence: {confidence})")
            return True
            
        except Exception as e:
            print(f"❌ Stage 1 update failed: {str(e)}")
            return False
    
    def update_stage15_supplementary(self, activity_id: int, supplementary_analysis: str, context_evaluation: str, linguistic_notes: str = "") -> bool:
        """第1.5段階: 補完分析データを更新"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE analysis_activity_log 
                SET stage15_supplementary_analysis = ?, 
                    stage15_context_evaluation = ?, 
                    stage15_linguistic_notes = ?
                WHERE id = ?
            """, (supplementary_analysis, context_evaluation, linguistic_notes, activity_id))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Stage 1.5 updated: Activity {activity_id} - supplementary analysis added")
            return True
            
        except Exception as e:
            print(f"❌ Stage 1.5 update failed: {str(e)}")
            return False
    
    def update_stage2_user_behavior(self, activity_id: int, user_choice: str, copied_text: str, copy_method: str, reasoning: str = "", confidence: float = None) -> bool:
        """第2段階: ユーザー実選択・行動データを更新"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = get_jst_now()
            
            cursor.execute("""
                UPDATE analysis_activity_log 
                SET actual_user_choice = ?, 
                    copy_behavior_tracked = 1, 
                    copied_translation = ?, 
                    copy_method = ?, 
                    copy_timestamp = ?, 
                    selection_reasoning = ?, 
                    user_confidence_level = ?
                WHERE id = ?
            """, (user_choice, copied_text, copy_method, now.isoformat(), reasoning, confidence, activity_id))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Stage 2 updated: Activity {activity_id} - User chose {user_choice}")
            return True
            
        except Exception as e:
            print(f"❌ Stage 2 update failed: {str(e)}")
            return False
    
    def update_stage3_divergence_analysis(self, activity_id: int) -> bool:
        """第3段階: 推奨vs実選択の一致分析を実行・更新"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 現在のデータを取得
            cursor.execute("""
                SELECT recommendation_result, actual_user_choice, 
                       chatgpt_translation, enhanced_translation, gemini_translation,
                       copied_translation, japanese_text
                FROM analysis_activity_log 
                WHERE id = ?
            """, (activity_id,))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            recommendation, user_choice, chatgpt, enhanced, gemini, copied_text, original = row
            
            # 一致判定
            match = False
            divergence_category = "unknown"
            learning_value = 0.0
            
            if recommendation and user_choice:
                match = recommendation.lower() == user_choice.lower()
                
                if not match:
                    # 乖離カテゴリ分析
                    if "enhanced" in recommendation.lower() and "chatgpt" in user_choice.lower():
                        divergence_category = "enhanced_to_original"
                    elif "chatgpt" in recommendation.lower() and "gemini" in user_choice.lower():
                        divergence_category = "chatgpt_to_gemini"
                    elif "gemini" in recommendation.lower() and "enhanced" in user_choice.lower():
                        divergence_category = "gemini_to_enhanced"
                    else:
                        divergence_category = "other_divergence"
                    
                    # 学習価値スコア（乖離の場合は高い価値）
                    learning_value = 0.8
                else:
                    divergence_category = "perfect_match"
                    learning_value = 0.3
            
            # 乖離分析結果
            divergence_analysis = f"Recommendation: {recommendation}, User Choice: {user_choice}, Match: {match}, Category: {divergence_category}"
            
            # フィードバックループデータ
            feedback_data = {
                "match": match,
                "divergence_category": divergence_category,
                "learning_value": learning_value,
                "analysis_timestamp": get_jst_now().isoformat(),
                "text_length": len(original) if original else 0
            }
            
            cursor.execute("""
                UPDATE analysis_activity_log 
                SET recommendation_vs_choice_match = ?, 
                    divergence_analysis = ?, 
                    divergence_category = ?, 
                    learning_value_score = ?, 
                    feedback_loop_data = ?
                WHERE id = ?
            """, (match, divergence_analysis, divergence_category, learning_value, json.dumps(feedback_data), activity_id))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Stage 3 updated: Activity {activity_id} - Match: {match}, Category: {divergence_category}")
            return True
            
        except Exception as e:
            print(f"❌ Stage 3 update failed: {str(e)}")
            return False
    
    def get_four_stage_analysis_data(self, period: str = "all", engine: str = "") -> Dict[str, Any]:
        """4段階分析統合データを取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # フィルター条件構築
            where_conditions = []
            params = []
            
            if period == 'today':
                where_conditions.append("DATE(created_at, '+9 hours') = DATE('now', '+9 hours')")
            elif period == 'week':
                where_conditions.append("created_at >= datetime('now', '-7 days')")
            elif period == 'month':
                where_conditions.append("created_at >= datetime('now', '-30 days')")
            
            if engine:
                where_conditions.append("actual_analysis_llm = ?")
                params.append(engine)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # 統計データ取得
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_cases,
                    COUNT(human_check_result) as stage0_completed,
                    COUNT(CASE WHEN recommendation_result IS NOT NULL THEN 1 END) as stage1_completed,
                    COUNT(CASE WHEN actual_user_choice IS NOT NULL THEN 1 END) as stage2_completed,
                    COUNT(CASE WHEN recommendation_vs_choice_match IS NOT NULL THEN 1 END) as stage3_completed,
                    COUNT(CASE WHEN copy_behavior_tracked = 1 THEN 1 END) as copy_tracked,
                    COUNT(CASE WHEN recommendation_vs_choice_match = 1 THEN 1 END) as stage3_matches,
                    COUNT(CASE WHEN recommendation_vs_choice_match = 0 THEN 1 END) as stage3_divergent
                FROM analysis_activity_log
                {where_clause}
            """, params)
            
            summary = cursor.fetchone()
            
            # 詳細データ取得
            cursor.execute(f"""
                SELECT 
                    id, created_at, japanese_text, actual_analysis_llm,
                    recommendation_result, actual_user_choice, 
                    human_check_result, human_check_timestamp,
                    copy_behavior_tracked, copied_translation, copy_method,
                    recommendation_vs_choice_match, divergence_category,
                    stage1_confidence_score, learning_value_score
                FROM analysis_activity_log
                {where_clause}
                ORDER BY created_at DESC
                LIMIT 100
            """, params)
            
            rows = cursor.fetchall()
            conn.close()
            
            # データ構造化
            items = []
            for row in rows:
                item = {
                    'id': row[0],
                    'created_at': row[1],
                    'japanese_text': row[2],
                    'analysis_engine': row[3],
                    'stage0': {
                        'status': row[6] or 'pending',
                        'timestamp': row[7]
                    } if row[6] else None,
                    'stage1': {
                        'recommendation': row[4],
                        'confidence': row[12]
                    } if row[4] else None,
                    'stage15': {
                        'status': 'completed' if row[4] else 'pending'
                    },
                    'stage2': {
                        'user_selection': row[5],
                        'copy_tracked': bool(row[8]),
                        'copy_method': row[10],
                        'data_source': 'actual_copy_tracking' if row[8] else 'button_tracking'
                    } if row[5] else None,
                    'stage3': {
                        'match': row[11] if row[11] is not None else None,
                        'category': row[12],
                        'learning_value': row[13]
                    } if row[11] is not None else None
                }
                items.append(item)
            
            return {
                'total_count': summary[0] if summary else 0,
                'stage0_completed': summary[1] if summary else 0,
                'stage1_completed': summary[2] if summary else 0,
                'stage2_completed': summary[3] if summary else 0,
                'stage3_completed': summary[4] if summary else 0,
                'copy_count': summary[5] if summary else 0,
                'match_rate': (summary[6] / summary[7] * 100) if summary and summary[7] > 0 else 0,
                'human_check_count': summary[1] if summary else 0,
                'items': items
            }
            
        except Exception as e:
            print(f"❌ 4段階分析データ取得エラー: {str(e)}")
            return {'total_count': 0, 'items': []}
    
    def get_human_check_queue(self) -> List[Dict[str, Any]]:
        """第0段階: 人間チェック待ちのデータを取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    id, created_at, japanese_text, recommendation_result, 
                    confidence, actual_analysis_llm, full_analysis_text
                FROM analysis_activity_log 
                WHERE human_check_result IS NULL 
                   OR human_check_result = 'pending'
                ORDER BY created_at DESC 
                LIMIT 50
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            items = []
            for row in rows:
                items.append({
                    'id': row[0],
                    'created_at': row[1],
                    'japanese_text': row[2],
                    'recommendation_result': row[3],
                    'confidence': row[4],
                    'actual_analysis_llm': row[5],
                    'full_analysis_text': row[6]
                })
            
            return items
            
        except Exception as e:
            print(f"❌ 人間チェック待ちデータ取得エラー: {str(e)}")
            return []


# グローバルインスタンス作成用関数
def create_four_stage_manager() -> FourStageAnalysisManager:
    """4段階分析マネージャーのインスタンスを作成"""
    activity_logger = ActivityLogger()
    return FourStageAnalysisManager(activity_logger)