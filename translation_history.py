#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangPont 翻訳履歴データベース管理システム
Task 2.7.1 - 翻訳履歴データベース構築

翻訳内容・結果の詳細保存、ユーザー別履歴管理、翻訳品質データ収集
検索・フィルタリング機能、データ分析基盤
"""

import sqlite3
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import uuid

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🆕 Task 2.9.1: 満足度推定エンジンのインポート
try:
    from satisfaction_estimator import SatisfactionEstimator
    SATISFACTION_ESTIMATOR_AVAILABLE = True
    logger.info("満足度推定エンジンをインポートしました")
except ImportError:
    SATISFACTION_ESTIMATOR_AVAILABLE = False
    logger.warning("満足度推定エンジンが利用できません")

class TranslationEngine(Enum):
    """翻訳エンジンタイプ"""
    CHATGPT = "chatgpt"
    GEMINI = "gemini"
    ENHANCED = "enhanced"
    REVERSE = "reverse"

class TranslationQuality(Enum):
    """翻訳品質レベル"""
    EXCELLENT = 5
    GOOD = 4
    AVERAGE = 3
    POOR = 2
    VERY_POOR = 1

@dataclass
class TranslationRequest:
    """翻訳リクエストデータ"""
    user_id: Optional[int] = None
    session_id: str = ""
    source_text: str = ""
    source_language: str = ""
    target_language: str = ""
    partner_message: str = ""
    context_info: str = ""
    ip_address: str = ""
    user_agent: str = ""
    request_timestamp: str = ""

@dataclass
class TranslationResult:
    """翻訳結果データ"""
    request_id: str = ""
    engine: str = ""
    translated_text: str = ""
    processing_time: float = 0.0
    confidence_score: Optional[float] = None
    error_message: str = ""
    api_response_time: float = 0.0
    result_timestamp: str = ""

@dataclass
class QualityMetrics:
    """翻訳品質メトリクス"""
    accuracy_score: Optional[float] = None
    fluency_score: Optional[float] = None
    adequacy_score: Optional[float] = None
    user_rating: Optional[int] = None
    user_feedback: str = ""
    auto_quality_score: Optional[float] = None
    evaluation_timestamp: str = ""

@dataclass
class TranslationHistoryEntry:
    """翻訳履歴エントリ（完全データ）"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    session_id: str = ""
    request_uuid: str = ""
    
    # 入力データ
    source_text: str = ""
    source_language: str = ""
    target_language: str = ""
    partner_message: str = ""
    context_info: str = ""
    
    # 翻訳結果
    chatgpt_translation: str = ""
    gemini_translation: str = ""
    enhanced_translation: str = ""
    reverse_translation: str = ""
    
    # 🆕 Gemini分析結果（Phase 1 実装）
    gemini_analysis: str = ""
    gemini_3way_comparison: str = ""
    # 🆕 Phase 1: Gemini分析結果保存用フィールド
    gemini_analysis_result: str = ""
    gemini_recommendation_extracted: str = ""
    gemini_recommendation_confidence: Optional[float] = None
    gemini_recommendation_reasons: str = ""
    gemini_recommendation_strength: str = ""
    analysis_timestamp: str = ""
    
    # メタデータ
    ip_address: str = ""
    user_agent: str = ""
    processing_time: float = 0.0
    created_at: str = ""
    
    # 品質データ
    user_rating: Optional[int] = None
    user_feedback: str = ""
    bookmarked: bool = False
    
    # 分析データ
    character_count: int = 0
    word_count: int = 0
    complexity_score: Optional[float] = None
    
    # フラグ
    is_archived: bool = False
    is_exported: bool = False

class TranslationHistoryManager:
    """翻訳履歴データベース管理クラス"""
    
    def __init__(self, db_path: str = "langpont_translation_history.db"):
        """
        翻訳履歴管理システムを初期化
        
        Args:
            db_path: SQLiteデータベースファイルのパス
        """
        self.db_path = db_path
        self.init_history_tables()
        
        # 🆕 Task 2.9.1: 満足度推定エンジンの初期化
        self.satisfaction_estimator = None
        if SATISFACTION_ESTIMATOR_AVAILABLE:
            try:
                self.satisfaction_estimator = SatisfactionEstimator()
                logger.info("満足度推定エンジンを初期化しました")
            except Exception as e:
                logger.error(f"満足度推定エンジン初期化エラー: {str(e)}")
        
    def init_history_tables(self) -> None:
        """翻訳履歴データベーステーブルを初期化"""
        try:
            # データベースファイルの存在確認
            db_exists = os.path.exists(self.db_path)
            if db_exists:
                logger.info(f"既存のデータベースファイルを使用: {self.db_path}")
            else:
                logger.info(f"新しいデータベースファイルを作成: {self.db_path}")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # SQLiteバージョン確認
                cursor.execute("SELECT sqlite_version()")
                sqlite_version = cursor.fetchone()[0]
                logger.info(f"SQLiteバージョン: {sqlite_version}")
                
                # メインの翻訳履歴テーブル（最適化版）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS translation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        session_id VARCHAR(100) NOT NULL,
                        request_uuid VARCHAR(36) UNIQUE NOT NULL,
                        
                        -- 入力データ
                        source_text TEXT NOT NULL,
                        source_language VARCHAR(10) NOT NULL,
                        target_language VARCHAR(10) NOT NULL,
                        partner_message TEXT DEFAULT '',
                        context_info TEXT DEFAULT '',
                        
                        -- 翻訳結果
                        chatgpt_translation TEXT,
                        gemini_translation TEXT,
                        enhanced_translation TEXT,
                        reverse_translation TEXT,
                        
                        -- Gemini分析結果
                        gemini_analysis TEXT,
                        gemini_3way_comparison TEXT,
                        
                        -- メタデータ
                        ip_address VARCHAR(45),
                        user_agent TEXT,
                        processing_time REAL DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        -- 品質データ
                        user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),
                        user_feedback TEXT DEFAULT '',
                        bookmarked BOOLEAN DEFAULT 0,
                        
                        -- 分析データ
                        character_count INTEGER DEFAULT 0,
                        word_count INTEGER DEFAULT 0,
                        complexity_score REAL,
                        
                        -- フラグ
                        is_archived BOOLEAN DEFAULT 0,
                        is_exported BOOLEAN DEFAULT 0,
                        
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
                    )
                ''')
                
                # 翻訳品質メトリクステーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS translation_quality_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        history_id INTEGER NOT NULL,
                        engine_type VARCHAR(20) NOT NULL,
                        accuracy_score REAL,
                        fluency_score REAL,
                        adequacy_score REAL,
                        auto_quality_score REAL,
                        evaluation_method VARCHAR(50),
                        evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (history_id) REFERENCES translation_history (id) ON DELETE CASCADE
                    )
                ''')
                
                # API呼び出し詳細ログテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS api_call_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        history_id INTEGER NOT NULL,
                        engine VARCHAR(20) NOT NULL,
                        api_endpoint VARCHAR(200),
                        request_size INTEGER,
                        response_size INTEGER,
                        response_time REAL,
                        http_status_code INTEGER,
                        error_code VARCHAR(50),
                        error_message TEXT,
                        tokens_used INTEGER,
                        cost REAL,
                        called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (history_id) REFERENCES translation_history (id) ON DELETE CASCADE
                    )
                ''')
                
                # 使用パターン分析テーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS usage_patterns (
                        user_id INTEGER,
                        date DATE NOT NULL,
                        hour INTEGER NOT NULL,
                        language_pair VARCHAR(10) NOT NULL,
                        translation_count INTEGER DEFAULT 1,
                        avg_text_length REAL,
                        total_processing_time REAL,
                        PRIMARY KEY (user_id, date, hour, language_pair),
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    ) WITHOUT ROWID
                ''')
                
                # 翻訳エンジン比較テーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS engine_comparisons (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        history_id INTEGER NOT NULL,
                        comparison_type VARCHAR(50),
                        engine_a VARCHAR(20),
                        engine_b VARCHAR(20),
                        winner VARCHAR(20),
                        confidence REAL,
                        comparison_criteria TEXT,
                        compared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (history_id) REFERENCES translation_history (id) ON DELETE CASCADE
                    )
                ''')
                
                # パフォーマンス最適化のためのインデックス
                indexes = [
                    'CREATE INDEX IF NOT EXISTS idx_translation_history_user_id ON translation_history (user_id)',
                    'CREATE INDEX IF NOT EXISTS idx_translation_history_created_at ON translation_history (created_at)',
                    'CREATE INDEX IF NOT EXISTS idx_translation_history_language_pair ON translation_history (source_language, target_language)',
                    'CREATE INDEX IF NOT EXISTS idx_translation_history_session_id ON translation_history (session_id)',
                    'CREATE INDEX IF NOT EXISTS idx_translation_history_bookmarked ON translation_history (bookmarked)',
                    'CREATE INDEX IF NOT EXISTS idx_translation_history_user_date ON translation_history (user_id, created_at)',
                    'CREATE INDEX IF NOT EXISTS idx_quality_metrics_history_id ON translation_quality_metrics (history_id)',
                    'CREATE INDEX IF NOT EXISTS idx_api_logs_history_id ON api_call_logs (history_id)',
                    'CREATE INDEX IF NOT EXISTS idx_usage_patterns_user_date ON usage_patterns (user_id, date)',
                    'CREATE INDEX IF NOT EXISTS idx_engine_comparisons_history_id ON engine_comparisons (history_id)'
                ]
                
                for index_sql in indexes:
                    try:
                        cursor.execute(index_sql)
                        logger.debug(f"インデックス作成完了: {index_sql[:50]}...")
                    except sqlite3.Error as idx_error:
                        logger.warning(f"インデックス作成スキップ: {str(idx_error)}")
                
                conn.commit()
                logger.info("翻訳履歴データベースが正常に初期化されました")
                
                # テーブル一覧を確認
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                logger.info(f"作成されたテーブル: {[table[0] for table in tables]}")
                
        except sqlite3.Error as e:
            logger.error(f"SQLiteエラー: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"翻訳履歴データベース初期化エラー: {str(e)}")
            logger.error(f"エラータイプ: {type(e).__name__}")
            raise
    
    def create_translation_entry(self, request_data: TranslationRequest) -> str:
        """
        新しい翻訳リクエストエントリを作成
        
        Args:
            request_data: 翻訳リクエストデータ
            
        Returns:
            生成された翻訳エントリのUUID
        """
        try:
            request_uuid = str(uuid.uuid4())
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 文字数・単語数を計算
                character_count = len(request_data.source_text)
                word_count = len(request_data.source_text.split())
                
                cursor.execute('''
                    INSERT INTO translation_history (
                        user_id, session_id, request_uuid, source_text, source_language, 
                        target_language, partner_message, context_info, ip_address, 
                        user_agent, character_count, word_count, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    request_data.user_id, request_data.session_id, request_uuid,
                    request_data.source_text, request_data.source_language,
                    request_data.target_language, request_data.partner_message,
                    request_data.context_info, request_data.ip_address,
                    request_data.user_agent, character_count, word_count,
                    request_data.request_timestamp or datetime.now().isoformat()
                ))
                
                conn.commit()
                logger.info(f"翻訳エントリ作成完了: UUID={request_uuid}")
                return request_uuid
                
        except Exception as e:
            logger.error(f"翻訳エントリ作成エラー: {str(e)}")
            raise
    
    def update_translation_result(self, request_uuid: str, engine: str, 
                                 translated_text: str, processing_time: float = 0.0,
                                 api_call_data: Dict[str, Any] = None) -> bool:
        """
        翻訳結果を更新
        
        Args:
            request_uuid: 翻訳リクエストUUID
            engine: 翻訳エンジン（chatgpt, gemini, enhanced, reverse）
            translated_text: 翻訳結果テキスト
            processing_time: 処理時間
            api_call_data: API呼び出し詳細データ
            
        Returns:
            成功/失敗
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # エンジンタイプに応じたカラム名を決定
                column_map = {
                    'chatgpt': 'chatgpt_translation',
                    'gemini': 'gemini_translation', 
                    'enhanced': 'enhanced_translation',
                    'reverse': 'reverse_translation',
                    'gemini_analysis': 'gemini_analysis',
                    'gemini_3way_comparison': 'gemini_3way_comparison'
                }
                
                column_name = column_map.get(engine, 'chatgpt_translation')
                
                # 翻訳結果を更新
                cursor.execute(f'''
                    UPDATE translation_history 
                    SET {column_name} = ?, processing_time = processing_time + ?
                    WHERE request_uuid = ?
                ''', (translated_text, processing_time, request_uuid))
                
                if cursor.rowcount == 0:
                    logger.warning(f"翻訳結果更新失敗: UUID {request_uuid} が見つかりません")
                    return False
                
                # 履歴IDを取得
                cursor.execute('SELECT id FROM translation_history WHERE request_uuid = ?', (request_uuid,))
                history_result = cursor.fetchone()
                
                if history_result and api_call_data:
                    history_id = history_result[0]
                    self._log_api_call(cursor, history_id, engine, api_call_data)
                
                conn.commit()
                logger.info(f"翻訳結果更新完了: UUID={request_uuid}, エンジン={engine}")
                return True
                
        except Exception as e:
            logger.error(f"翻訳結果更新エラー: {str(e)}")
            return False
    
    def _log_api_call(self, cursor: sqlite3.Cursor, history_id: int, 
                     engine: str, api_data: Dict[str, Any]) -> None:
        """API呼び出し詳細をログに記録"""
        try:
            cursor.execute('''
                INSERT INTO api_call_logs (
                    history_id, engine, api_endpoint, request_size, response_size,
                    response_time, http_status_code, error_code, error_message,
                    tokens_used, cost
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                history_id, engine, api_data.get('endpoint', ''),
                api_data.get('request_size', 0), api_data.get('response_size', 0),
                api_data.get('response_time', 0.0), api_data.get('status_code', 200),
                api_data.get('error_code', ''), api_data.get('error_message', ''),
                api_data.get('tokens_used', 0), api_data.get('cost', 0.0)
            ))
        except Exception as e:
            logger.error(f"API呼び出しログ記録エラー: {str(e)}")
    
    def get_user_translation_history(self, user_id: Optional[int], 
                                   session_id: str = "", limit: int = 50, 
                                   offset: int = 0, filters: Dict[str, Any] = None) -> List[TranslationHistoryEntry]:
        """
        ユーザーの翻訳履歴を取得
        
        Args:
            user_id: ユーザーID（Noneの場合はsession_idで検索）
            session_id: セッションID
            limit: 取得件数制限
            offset: オフセット
            filters: フィルタ条件
            
        Returns:
            翻訳履歴リスト
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # WHERE句の構築
                where_conditions = []
                params = []
                
                if user_id is not None:
                    where_conditions.append("user_id = ?")
                    params.append(user_id)
                elif session_id:
                    where_conditions.append("session_id = ?")
                    params.append(session_id)
                else:
                    return []  # ユーザーIDもセッションIDもない場合は空リストを返す
                
                # フィルタ条件の追加
                if filters:
                    if filters.get('language_pair'):
                        source_lang, target_lang = filters['language_pair'].split('-')
                        where_conditions.append("source_language = ? AND target_language = ?")
                        params.extend([source_lang, target_lang])
                    
                    if filters.get('bookmarked_only'):
                        where_conditions.append("bookmarked = 1")
                    
                    if filters.get('date_from'):
                        where_conditions.append("created_at >= ?")
                        params.append(filters['date_from'])
                    
                    if filters.get('date_to'):
                        where_conditions.append("created_at <= ?")
                        params.append(filters['date_to'])
                    
                    if filters.get('min_rating'):
                        where_conditions.append("user_rating >= ?")
                        params.append(filters['min_rating'])
                
                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                
                # 履歴を取得
                cursor.execute(f'''
                    SELECT * FROM translation_history
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                ''', params + [limit, offset])
                
                results = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                history_entries = []
                for row in results:
                    row_dict = dict(zip(columns, row))
                    entry = TranslationHistoryEntry(**row_dict)
                    history_entries.append(entry)
                
                return history_entries
                
        except Exception as e:
            logger.error(f"翻訳履歴取得エラー: {str(e)}")
            return []
    
    def search_translation_history(self, user_id: Optional[int] = None, 
                                 session_id: str = "", search_query: str = "", 
                                 search_fields: List[str] = None, 
                                 filters: Dict[str, Any] = None,
                                 limit: int = 20, offset: int = 0) -> List[TranslationHistoryEntry]:
        """
        翻訳履歴を検索
        
        Args:
            user_id: ユーザーID
            session_id: セッションID
            search_query: 検索クエリ
            search_fields: 検索対象フィールド
            filters: フィルタ条件
            limit: 取得件数制限
            offset: オフセット
            
        Returns:
            検索結果リスト
        """
        try:
            search_fields = search_fields or ['source_text', 'chatgpt_translation', 'gemini_translation', 'enhanced_translation']
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 検索条件の構築
                search_conditions = []
                params = []
                
                # ユーザー/セッション条件
                if user_id is not None:
                    search_conditions.append("user_id = ?")
                    params.append(user_id)
                elif session_id:
                    search_conditions.append("session_id = ?")
                    params.append(session_id)
                
                # テキスト検索条件
                if search_query:
                    text_conditions = []
                    for field in search_fields:
                        text_conditions.append(f"{field} LIKE ?")
                        params.append(f"%{search_query}%")
                    
                    if text_conditions:
                        search_conditions.append(f"({' OR '.join(text_conditions)})")
                
                # フィルタ条件の追加
                if filters:
                    if filters.get('source_language') and filters.get('target_language'):
                        search_conditions.append("source_language = ? AND target_language = ?")
                        params.extend([filters['source_language'], filters['target_language']])
                    
                    if filters.get('date_from'):
                        search_conditions.append("created_at >= ?")
                        params.append(filters['date_from'])
                    
                    if filters.get('date_to'):
                        search_conditions.append("created_at <= ?")
                        params.append(filters['date_to'])
                    
                    if filters.get('min_rating'):
                        search_conditions.append("user_rating >= ?")
                        params.append(filters['min_rating'])
                    
                    if filters.get('bookmarked_only'):
                        search_conditions.append("bookmarked = 1")
                
                where_clause = " AND ".join(search_conditions) if search_conditions else "1=1"
                
                cursor.execute(f'''
                    SELECT * FROM translation_history
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                ''', params + [limit, offset])
                
                results = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                history_entries = []
                for row in results:
                    row_dict = dict(zip(columns, row))
                    entry = TranslationHistoryEntry(**row_dict)
                    history_entries.append(entry)
                
                return history_entries
                
        except Exception as e:
            logger.error(f"翻訳履歴検索エラー: {str(e)}")
            return []
    
    def get_translation_analytics(self, user_id: Optional[int] = None, 
                                session_id: str = "", days: int = 30) -> Dict[str, Any]:
        """
        翻訳分析データを取得
        
        Args:
            user_id: ユーザーID（Noneの場合は全体統計）
            session_id: セッションID
            days: 分析期間（日数）
            
        Returns:
            分析データ辞書
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 期間の計算
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                analytics = {}
                
                # WHERE句の構築
                where_condition = "created_at >= ?"
                params = [start_date.isoformat()]
                
                if user_id is not None:
                    where_condition += " AND user_id = ?"
                    params.append(user_id)
                elif session_id:
                    where_condition += " AND session_id = ?"
                    params.append(session_id)
                
                # 基本統計
                cursor.execute(f'''
                    SELECT 
                        COUNT(*) as total_translations,
                        AVG(character_count) as avg_character_count,
                        AVG(processing_time) as avg_processing_time,
                        COUNT(DISTINCT source_language || '-' || target_language) as unique_language_pairs,
                        COUNT(CASE WHEN bookmarked = 1 THEN 1 END) as bookmarked_count,
                        AVG(user_rating) as avg_user_rating
                    FROM translation_history
                    WHERE {where_condition}
                ''', params)
                
                basic_stats = cursor.fetchone()
                if basic_stats:
                    analytics['basic_stats'] = {
                        'total_translations': basic_stats[0],
                        'avg_character_count': round(basic_stats[1] or 0, 2),
                        'avg_processing_time': round(basic_stats[2] or 0, 3),
                        'unique_language_pairs': basic_stats[3],
                        'bookmarked_count': basic_stats[4],
                        'avg_user_rating': round(basic_stats[5] or 0, 2)
                    }
                
                # 言語ペア統計
                cursor.execute(f'''
                    SELECT 
                        source_language || '-' || target_language as language_pair,
                        COUNT(*) as count,
                        AVG(processing_time) as avg_time
                    FROM translation_history
                    WHERE {where_condition}
                    GROUP BY language_pair
                    ORDER BY count DESC
                    LIMIT 10
                ''', params)
                
                language_pairs = cursor.fetchall()
                analytics['language_pairs'] = [
                    {'pair': pair[0], 'count': pair[1], 'avg_time': round(pair[2] or 0, 3)}
                    for pair in language_pairs
                ]
                
                # 日別統計
                cursor.execute(f'''
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as count,
                        AVG(processing_time) as avg_time
                    FROM translation_history
                    WHERE {where_condition}
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                    LIMIT 30
                ''', params)
                
                daily_stats = cursor.fetchall()
                analytics['daily_stats'] = [
                    {'date': day[0], 'count': day[1], 'avg_time': round(day[2] or 0, 3)}
                    for day in daily_stats
                ]
                
                # エンジン比較統計
                engine_stats = {}
                for engine in ['chatgpt_translation', 'gemini_translation', 'enhanced_translation']:
                    cursor.execute(f'''
                        SELECT 
                            COUNT(CASE WHEN {engine} IS NOT NULL AND {engine} != '' THEN 1 END) as count,
                            AVG(LENGTH({engine})) as avg_length
                        FROM translation_history
                        WHERE {where_condition}
                    ''', params)
                    
                    result = cursor.fetchone()
                    engine_name = engine.replace('_translation', '')
                    engine_stats[engine_name] = {
                        'count': result[0] if result else 0,
                        'avg_length': round(result[1] or 0, 2) if result else 0
                    }
                
                analytics['engine_stats'] = engine_stats
                
                return analytics
                
        except Exception as e:
            logger.error(f"翻訳分析データ取得エラー: {str(e)}")
            return {}
    
    def update_user_rating(self, history_id: int, rating: int, 
                          feedback: str = "") -> bool:
        """
        ユーザー評価を更新
        
        Args:
            history_id: 履歴ID
            rating: 評価（1-5）
            feedback: フィードバック
            
        Returns:
            成功/失敗
        """
        try:
            if not (1 <= rating <= 5):
                raise ValueError("評価は1〜5の範囲で入力してください")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE translation_history 
                    SET user_rating = ?, user_feedback = ?
                    WHERE id = ?
                ''', (rating, feedback, history_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"ユーザー評価更新完了: 履歴ID {history_id}, 評価 {rating}")
                    return True
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"ユーザー評価更新エラー: {str(e)}")
            return False
    
    def toggle_bookmark(self, history_id: int, bookmarked: bool) -> bool:
        """
        ブックマーク状態を切り替え
        
        Args:
            history_id: 履歴ID
            bookmarked: ブックマーク状態
            
        Returns:
            成功/失敗
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE translation_history 
                    SET bookmarked = ?
                    WHERE id = ?
                ''', (bookmarked, history_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    action = "ブックマーク" if bookmarked else "ブックマーク解除"
                    logger.info(f"{action}完了: 履歴ID {history_id}")
                    return True
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"ブックマーク更新エラー: {str(e)}")
            return False
    
    def cleanup_old_history(self, days_to_keep: int = 180, 
                           keep_bookmarked: bool = True) -> int:
        """
        古い翻訳履歴をクリーンアップ
        
        Args:
            days_to_keep: 保持日数
            keep_bookmarked: ブックマーク済みを保持するか
            
        Returns:
            削除件数
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                where_condition = "created_at < ?"
                params = [cutoff_date.isoformat()]
                
                if keep_bookmarked:
                    where_condition += " AND bookmarked = 0"
                
                cursor.execute(f'''
                    DELETE FROM translation_history 
                    WHERE {where_condition}
                ''', params)
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"古い翻訳履歴クリーンアップ完了: {deleted_count}件削除")
                return deleted_count
                
        except Exception as e:
            logger.error(f"翻訳履歴クリーンアップエラー: {str(e)}")
            return 0
    
    def export_user_history(self, user_id: Optional[int], 
                          session_id: str = "", format_type: str = "json") -> Optional[str]:
        """
        ユーザーの翻訳履歴をエクスポート
        
        Args:
            user_id: ユーザーID
            session_id: セッションID
            format_type: エクスポート形式（json, csv）
            
        Returns:
            エクスポートデータ（文字列）
        """
        try:
            history_entries = self.get_user_translation_history(
                user_id=user_id, 
                session_id=session_id, 
                limit=1000
            )
            
            if format_type == "json":
                export_data = {
                    'export_timestamp': datetime.now().isoformat(),
                    'user_id': user_id,
                    'session_id': session_id,
                    'total_entries': len(history_entries),
                    'history': [asdict(entry) for entry in history_entries]
                }
                return json.dumps(export_data, ensure_ascii=False, indent=2)
            
            elif format_type == "csv":
                import csv
                import io
                
                output = io.StringIO()
                if history_entries:
                    fieldnames = asdict(history_entries[0]).keys()
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    for entry in history_entries:
                        writer.writerow(asdict(entry))
                
                return output.getvalue()
            
            else:
                raise ValueError(f"サポートされていない形式: {format_type}")
                
        except Exception as e:
            logger.error(f"履歴エクスポートエラー: {str(e)}")
            return None
    
    def get_language_pair_stats(self, user_id: Optional[int] = None, 
                               session_id: str = "", days: int = 30) -> Dict[str, Any]:
        """
        言語ペア統計データを取得
        
        Args:
            user_id: ユーザーID
            session_id: セッションID
            days: 分析期間（日数）
            
        Returns:
            言語ペア統計データ
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 期間の計算
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # WHERE句の構築
                where_condition = "created_at >= ?"
                params = [start_date.isoformat()]
                
                if user_id is not None:
                    where_condition += " AND user_id = ?"
                    params.append(user_id)
                elif session_id:
                    where_condition += " AND session_id = ?"
                    params.append(session_id)
                
                # 言語ペア別統計
                cursor.execute(f'''
                    SELECT 
                        source_language,
                        target_language,
                        source_language || '-' || target_language as language_pair,
                        COUNT(*) as translation_count,
                        AVG(character_count) as avg_char_count,
                        AVG(word_count) as avg_word_count,
                        AVG(processing_time) as avg_processing_time,
                        COUNT(CASE WHEN user_rating IS NOT NULL THEN 1 END) as rated_count,
                        AVG(user_rating) as avg_rating,
                        COUNT(CASE WHEN bookmarked = 1 THEN 1 END) as bookmarked_count,
                        MAX(created_at) as last_used
                    FROM translation_history
                    WHERE {where_condition}
                    GROUP BY source_language, target_language
                    ORDER BY translation_count DESC
                ''', params)
                
                results = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                language_pairs = []
                for row in results:
                    row_dict = dict(zip(columns, row))
                    # データを整形
                    row_dict['avg_char_count'] = round(row_dict['avg_char_count'] or 0, 1)
                    row_dict['avg_word_count'] = round(row_dict['avg_word_count'] or 0, 1)
                    row_dict['avg_processing_time'] = round(row_dict['avg_processing_time'] or 0, 3)
                    row_dict['avg_rating'] = round(row_dict['avg_rating'] or 0, 1)
                    language_pairs.append(row_dict)
                
                # 全体サマリー
                cursor.execute(f'''
                    SELECT 
                        COUNT(DISTINCT source_language || '-' || target_language) as total_pairs,
                        COUNT(*) as total_translations,
                        COUNT(DISTINCT source_language) as source_languages,
                        COUNT(DISTINCT target_language) as target_languages
                    FROM translation_history
                    WHERE {where_condition}
                ''', params)
                
                summary_result = cursor.fetchone()
                summary = dict(zip([desc[0] for desc in cursor.description], summary_result)) if summary_result else {}
                
                return {
                    'language_pairs': language_pairs,
                    'summary': summary,
                    'period_days': days,
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"言語ペア統計取得エラー: {str(e)}")
            return {'language_pairs': [], 'summary': {}, 'error': str(e)}

    def save_complete_translation(self, user_id: Optional[int], session_id: str,
                                 source_text: str, source_language: str, 
                                 target_language: str, translations: Dict[str, str],
                                 context_data: Dict[str, Any] = None) -> Optional[str]:
        """
        完全な翻訳セッションを保存（app.py統合用メソッド）
        
        Args:
            user_id: ユーザーID
            session_id: セッションID
            source_text: 翻訳元テキスト
            source_language: 翻訳元言語
            target_language: 翻訳先言語
            translations: 翻訳結果辞書 {'chatgpt': '...', 'gemini': '...', 'enhanced': '...'}
            context_data: コンテキストデータ
            
        Returns:
            保存された翻訳のUUID
        """
        try:
            # リクエストデータの構築
            request_data = TranslationRequest(
                user_id=user_id,
                session_id=session_id,
                source_text=source_text,
                source_language=source_language,
                target_language=target_language,
                partner_message=context_data.get('partner_message', '') if context_data else '',
                context_info=context_data.get('context_info', '') if context_data else '',
                ip_address=context_data.get('ip_address', '') if context_data else '',
                user_agent=context_data.get('user_agent', '') if context_data else '',
                request_timestamp=datetime.now().isoformat()
            )
            
            # 翻訳エントリを作成
            request_uuid = self.create_translation_entry(request_data)
            
            # 各翻訳結果を保存
            processing_time = context_data.get('processing_time', 0.0) if context_data else 0.0
            
            for engine, translation_text in translations.items():
                if translation_text:  # 空でない翻訳結果のみ保存
                    self.update_translation_result(
                        request_uuid=request_uuid,
                        engine=engine,
                        translated_text=translation_text,
                        processing_time=processing_time / len(translations),  # 処理時間を分散
                        api_call_data=context_data.get(f'{engine}_api_data') if context_data else None
                    )
            
            logger.info(f"完全翻訳セッション保存完了: UUID={request_uuid}, エンジン数={len(translations)}")
            
            # 🆕 Task 2.9.1: 満足度推定の実行
            if self.satisfaction_estimator and session_id:
                try:
                    # 翻訳IDを取得
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT id FROM translation_history WHERE request_uuid = ?', (request_uuid,))
                        result = cursor.fetchone()
                        translation_id = result[0] if result else None
                    
                    # 満足度を計算
                    satisfaction_result = self.satisfaction_estimator.calculate_satisfaction(
                        session_id=session_id,
                        user_id=str(user_id) if user_id else None,
                        translation_id=translation_id
                    )
                    
                    if satisfaction_result and 'satisfaction_score' in satisfaction_result:
                        logger.info(f"満足度スコア計算完了: session={session_id}, score={satisfaction_result['satisfaction_score']}")
                    
                except Exception as e:
                    logger.error(f"満足度計算エラー（翻訳は正常に保存されました）: {str(e)}")
            
            return request_uuid
            
        except Exception as e:
            logger.error(f"完全翻訳セッション保存エラー: {str(e)}")
            return None
    
    def get_satisfaction_data(self, session_id: str = None, 
                            user_id: int = None, 
                            translation_id: int = None) -> Optional[Dict[str, Any]]:
        """
        🆕 Task 2.9.1: 満足度データを取得
        
        Args:
            session_id: セッションID
            user_id: ユーザーID
            translation_id: 翻訳履歴ID
            
        Returns:
            満足度データ辞書、エラー時はNone
        """
        if not self.satisfaction_estimator:
            return None
        
        try:
            # 最新の満足度データを取得
            history = self.satisfaction_estimator.get_satisfaction_history(
                user_id=str(user_id) if user_id else None,
                days=1  # 直近1日
            )
            
            if history and session_id:
                # セッションIDでフィルタ
                for entry in history:
                    if entry.get('session_id') == session_id:
                        return entry
            elif history:
                # 最新のエントリを返す
                return history[0]
            
            return None
            
        except Exception as e:
            logger.error(f"満足度データ取得エラー: {str(e)}")
            return None
    
    def get_satisfaction_analytics(self, user_id: int = None, days: int = 30) -> Dict[str, Any]:
        """
        🆕 Task 2.9.1: 満足度分析データを取得
        
        Args:
            user_id: ユーザーID（Noneの場合は全体統計）
            days: 分析期間（日数）
            
        Returns:
            満足度分析データ
        """
        if not self.satisfaction_estimator:
            return {
                'available': False,
                'message': '満足度推定エンジンが利用できません'
            }
        
        try:
            # トレンド分析を取得
            trends = self.satisfaction_estimator.analyze_satisfaction_trends()
            
            # 平均満足度を取得
            avg_satisfaction = self.satisfaction_estimator.get_average_satisfaction(
                user_id=str(user_id) if user_id else None,
                days=days
            )
            
            return {
                'available': True,
                'average_satisfaction': avg_satisfaction,
                'trends': trends,
                'period_days': days,
                'user_id': user_id
            }
            
        except Exception as e:
            logger.error(f"満足度分析データ取得エラー: {str(e)}")
            return {
                'available': False,
                'message': f'エラー: {str(e)}'
            }

# グローバルインスタンス
translation_history_manager = TranslationHistoryManager()

# 使用例とテスト関数
if __name__ == "__main__":
    # テスト用実行
    manager = TranslationHistoryManager("test_translation_history.db")
    
    # テスト用翻訳リクエスト
    test_request = TranslationRequest(
        user_id=1,
        session_id="test_session_123",
        source_text="こんにちは、元気ですか？",
        source_language="ja",
        target_language="en",
        partner_message="友人との会話",
        context_info="カジュアルな挨拶",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 Test Browser",
        request_timestamp=datetime.now().isoformat()
    )
    
    # 翻訳エントリ作成テスト
    uuid = manager.create_translation_entry(test_request)
    print(f"翻訳エントリ作成テスト: UUID = {uuid}")
    
    # 翻訳結果更新テスト
    success = manager.update_translation_result(
        uuid, "chatgpt", "Hello, how are you?", 1.5
    )
    print(f"翻訳結果更新テスト: {'成功' if success else '失敗'}")
    
    # 履歴取得テスト
    history = manager.get_user_translation_history(user_id=1, limit=5)
    print(f"履歴取得テスト: {len(history)}件取得")
    
    # 分析データ取得テスト
    analytics = manager.get_translation_analytics(user_id=1)
    print(f"分析データ取得テスト: {analytics.get('basic_stats', {})}")