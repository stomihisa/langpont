#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangPont ユーザープロファイル管理システム
Task 2.6.2 - ユーザープロファイル管理の実装

個人設定保存・管理、Early Accessフラグ管理、翻訳履歴管理を提供
"""

import sqlite3
import json
import logging
import os
import time
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThemeType(Enum):
    """テーマタイプ"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"

class NotificationLevel(Enum):
    """通知レベル"""
    ALL = "all"
    IMPORTANT = "important"
    NONE = "none"

@dataclass
class UserSettings:
    """ユーザー設定データクラス"""
    # 翻訳設定
    default_source_language: str = "ja"
    default_target_language: str = "en"
    preferred_translation_engine: str = "auto"  # auto, chatgpt, gemini
    show_reverse_translation: bool = True
    show_nuance_analysis: bool = True
    
    # UI設定
    display_language: str = "jp"
    theme: str = ThemeType.LIGHT.value
    font_size: str = "medium"  # small, medium, large
    compact_mode: bool = False
    
    # 通知設定
    notification_level: str = NotificationLevel.IMPORTANT.value
    email_notifications: bool = False
    usage_limit_warnings: bool = True
    
    # プライバシー設定
    save_translation_history: bool = True
    share_usage_analytics: bool = False
    
    # 高度な設定
    auto_detect_language: bool = True
    parallel_translation: bool = True
    cache_translations: bool = True
    max_history_items: int = 100

@dataclass
class EarlyAccessFeatures:
    """Early Access機能設定"""
    unlimited_translations: bool = True
    advanced_ai_features: bool = True
    beta_features: bool = True
    priority_support: bool = True
    api_access: bool = False
    custom_models: bool = False
    team_features: bool = False

@dataclass
class TranslationHistoryItem:
    """翻訳履歴アイテム"""
    id: Optional[int] = None
    user_id: int = 0
    source_text: str = ""
    source_language: str = ""
    target_language: str = ""
    chatgpt_translation: str = ""
    gemini_translation: str = ""
    better_translation: str = ""
    nuance_analysis: str = ""
    context_info: str = ""
    partner_message: str = ""
    created_at: str = ""
    session_id: str = ""
    rating: Optional[int] = None  # 1-5 stars
    bookmarked: bool = False

class UserProfileManager:
    """ユーザープロファイル管理クラス"""
    
    def __init__(self, db_path: str = "langpont_users.db"):
        """
        ユーザープロファイル管理システムを初期化
        
        Args:
            db_path: SQLiteデータベースファイルのパス
        """
        self.db_path = db_path
        self.init_profile_tables()
        
    def init_profile_tables(self) -> None:
        """プロファイル関連テーブルを初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # user_settingsテーブル（ユーザー設定）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_settings (
                        user_id INTEGER PRIMARY KEY,
                        settings_json TEXT NOT NULL DEFAULT '{}',
                        early_access_features TEXT DEFAULT '{}',
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # translation_historyテーブル（翻訳履歴）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS translation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        source_text TEXT NOT NULL,
                        source_language VARCHAR(5) NOT NULL,
                        target_language VARCHAR(5) NOT NULL,
                        chatgpt_translation TEXT,
                        gemini_translation TEXT,
                        better_translation TEXT,
                        nuance_analysis TEXT,
                        context_info TEXT,
                        partner_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        session_id VARCHAR(50),
                        rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                        bookmarked BOOLEAN DEFAULT 0,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # user_preferencesテーブル（詳細な個人設定）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        user_id INTEGER PRIMARY KEY,
                        language_pairs_used TEXT DEFAULT '[]',
                        favorite_features TEXT DEFAULT '[]',
                        custom_prompts TEXT DEFAULT '{}',
                        quick_actions TEXT DEFAULT '[]',
                        workspace_layout TEXT DEFAULT '{}',
                        keyboard_shortcuts TEXT DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # early_access_logsテーブル（Early Access利用ログ）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS early_access_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        feature_name VARCHAR(100) NOT NULL,
                        action VARCHAR(50) NOT NULL,
                        metadata TEXT DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # translation_ratingsテーブル（翻訳評価）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS translation_ratings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        translation_history_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        engine_type VARCHAR(20) NOT NULL,
                        rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                        feedback_text TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (translation_history_id) REFERENCES translation_history (id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # インデックス作成（パフォーマンス向上）
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_translation_history_user_id ON translation_history (user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_translation_history_created_at ON translation_history (created_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_translation_history_bookmarked ON translation_history (bookmarked)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_early_access_logs_user_id ON early_access_logs (user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_translation_ratings_user_id ON translation_ratings (user_id)')
                
                conn.commit()
                logger.info("ユーザープロファイル関連テーブルが正常に初期化されました")
                
        except Exception as e:
            logger.error(f"プロファイルテーブル初期化エラー: {str(e)}")
            raise
    
    def get_user_settings(self, user_id: int) -> UserSettings:
        """
        ユーザー設定を取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            ユーザー設定オブジェクト
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    'SELECT settings_json FROM user_settings WHERE user_id = ?',
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    settings_data = json.loads(result[0])
                    return UserSettings(**settings_data)
                else:
                    # デフォルト設定を作成
                    default_settings = UserSettings()
                    self.save_user_settings(user_id, default_settings)
                    return default_settings
                    
        except Exception as e:
            logger.error(f"ユーザー設定取得エラー: {str(e)}")
            return UserSettings()  # デフォルト設定を返す
    
    def save_user_settings(self, user_id: int, settings: UserSettings) -> bool:
        """
        ユーザー設定を保存
        
        Args:
            user_id: ユーザーID
            settings: ユーザー設定オブジェクト
            
        Returns:
            成功/失敗
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                settings_json = json.dumps(asdict(settings), ensure_ascii=False)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO user_settings (user_id, settings_json, updated_at)
                    VALUES (?, ?, ?)
                ''', (user_id, settings_json, datetime.now().isoformat()))
                
                conn.commit()
                logger.info(f"ユーザー設定保存完了: ユーザーID {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"ユーザー設定保存エラー: {str(e)}")
            return False
    
    def get_early_access_features(self, user_id: int) -> EarlyAccessFeatures:
        """
        Early Access機能設定を取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            Early Access機能設定
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # まずユーザーのEarly Accessステータスを確認
                cursor.execute(
                    'SELECT early_access FROM users WHERE id = ?',
                    (user_id,)
                )
                user_result = cursor.fetchone()
                
                if not user_result or not user_result[0]:
                    # Early Accessユーザーでない場合は制限付き機能
                    return EarlyAccessFeatures(
                        unlimited_translations=False,
                        advanced_ai_features=False,
                        beta_features=False,
                        priority_support=False,
                        api_access=False,
                        custom_models=False,
                        team_features=False
                    )
                
                # Early Access機能設定を取得
                cursor.execute(
                    'SELECT early_access_features FROM user_settings WHERE user_id = ?',
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if result and result[0]:
                    features_data = json.loads(result[0])
                    return EarlyAccessFeatures(**features_data)
                else:
                    # デフォルトのEarly Access機能
                    default_features = EarlyAccessFeatures()
                    self.save_early_access_features(user_id, default_features)
                    return default_features
                    
        except Exception as e:
            logger.error(f"Early Access機能取得エラー: {str(e)}")
            return EarlyAccessFeatures()
    
    def save_early_access_features(self, user_id: int, features: EarlyAccessFeatures) -> bool:
        """
        Early Access機能設定を保存
        
        Args:
            user_id: ユーザーID
            features: Early Access機能設定
            
        Returns:
            成功/失敗
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                features_json = json.dumps(asdict(features), ensure_ascii=False)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO user_settings (user_id, early_access_features, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        early_access_features = excluded.early_access_features,
                        updated_at = excluded.updated_at
                ''', (user_id, features_json, datetime.now().isoformat()))
                
                conn.commit()
                logger.info(f"Early Access機能設定保存完了: ユーザーID {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Early Access機能設定保存エラー: {str(e)}")
            return False
    
    def add_translation_history(self, history_item: TranslationHistoryItem) -> Optional[int]:
        """
        翻訳履歴を追加
        
        Args:
            history_item: 翻訳履歴アイテム
            
        Returns:
            作成された履歴ID（失敗時はNone）
        """
        try:
            # ユーザー設定で履歴保存が無効な場合はスキップ
            user_settings = self.get_user_settings(history_item.user_id)
            if not user_settings.save_translation_history:
                return None
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO translation_history (
                        user_id, source_text, source_language, target_language,
                        chatgpt_translation, gemini_translation, better_translation,
                        nuance_analysis, context_info, partner_message,
                        session_id, rating, bookmarked
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    history_item.user_id, history_item.source_text,
                    history_item.source_language, history_item.target_language,
                    history_item.chatgpt_translation, history_item.gemini_translation,
                    history_item.better_translation, history_item.nuance_analysis,
                    history_item.context_info, history_item.partner_message,
                    history_item.session_id, history_item.rating, history_item.bookmarked
                ))
                
                history_id = cursor.lastrowid
                conn.commit()
                
                # 履歴数制限チェック
                self._cleanup_old_history(history_item.user_id, user_settings.max_history_items)
                
                logger.info(f"翻訳履歴追加完了: ユーザーID {history_item.user_id}, 履歴ID {history_id}")
                return history_id
                
        except Exception as e:
            logger.error(f"翻訳履歴追加エラー: {str(e)}")
            return None
    
    def get_translation_history(self, user_id: int, limit: int = 50, offset: int = 0, 
                              bookmarked_only: bool = False) -> List[TranslationHistoryItem]:
        """
        翻訳履歴を取得
        
        Args:
            user_id: ユーザーID
            limit: 取得件数制限
            offset: オフセット
            bookmarked_only: ブックマーク済みのみ
            
        Returns:
            翻訳履歴リスト
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                where_clause = "WHERE user_id = ?"
                params = [user_id]
                
                if bookmarked_only:
                    where_clause += " AND bookmarked = 1"
                
                cursor.execute(f'''
                    SELECT * FROM translation_history
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                ''', params + [limit, offset])
                
                results = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                history_items = []
                for row in results:
                    row_dict = dict(zip(columns, row))
                    history_item = TranslationHistoryItem(**row_dict)
                    history_items.append(history_item)
                
                return history_items
                
        except Exception as e:
            logger.error(f"翻訳履歴取得エラー: {str(e)}")
            return []
    
    def bookmark_translation(self, user_id: int, history_id: int, bookmarked: bool = True) -> bool:
        """
        翻訳をブックマーク/ブックマーク解除
        
        Args:
            user_id: ユーザーID
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
                    WHERE id = ? AND user_id = ?
                ''', (bookmarked, history_id, user_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"翻訳ブックマーク更新: ユーザーID {user_id}, 履歴ID {history_id}, 状態 {bookmarked}")
                    return True
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"翻訳ブックマーク更新エラー: {str(e)}")
            return False
    
    def rate_translation(self, user_id: int, history_id: int, engine_type: str, 
                        rating: int, feedback_text: str = "") -> bool:
        """
        翻訳を評価
        
        Args:
            user_id: ユーザーID
            history_id: 履歴ID
            engine_type: エンジンタイプ（chatgpt, gemini, better）
            rating: 評価（1-5）
            feedback_text: フィードバックテキスト
            
        Returns:
            成功/失敗
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO translation_ratings 
                    (translation_history_id, user_id, engine_type, rating, feedback_text)
                    VALUES (?, ?, ?, ?, ?)
                ''', (history_id, user_id, engine_type, rating, feedback_text))
                
                conn.commit()
                logger.info(f"翻訳評価保存: ユーザーID {user_id}, 履歴ID {history_id}, エンジン {engine_type}, 評価 {rating}")
                return True
                
        except Exception as e:
            logger.error(f"翻訳評価保存エラー: {str(e)}")
            return False
    
    def log_early_access_usage(self, user_id: int, feature_name: str, action: str, 
                             metadata: Dict[str, Any] = None) -> bool:
        """
        Early Access機能の利用ログを記録
        
        Args:
            user_id: ユーザーID
            feature_name: 機能名
            action: アクション
            metadata: メタデータ
            
        Returns:
            成功/失敗
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
                
                cursor.execute('''
                    INSERT INTO early_access_logs (user_id, feature_name, action, metadata)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, feature_name, action, metadata_json))
                
                conn.commit()
                logger.info(f"Early Access利用ログ記録: ユーザーID {user_id}, 機能 {feature_name}, アクション {action}")
                return True
                
        except Exception as e:
            logger.error(f"Early Access利用ログ記録エラー: {str(e)}")
            return False
    
    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        ユーザー統計情報を取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            統計情報辞書
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # 翻訳統計
                cursor.execute('''
                    SELECT COUNT(*) as total_translations,
                           COUNT(CASE WHEN DATE(created_at) = DATE('now') THEN 1 END) as today_translations,
                           COUNT(CASE WHEN DATE(created_at) >= DATE('now', '-7 days') THEN 1 END) as week_translations,
                           COUNT(CASE WHEN bookmarked = 1 THEN 1 END) as bookmarked_translations
                    FROM translation_history WHERE user_id = ?
                ''', (user_id,))
                
                translation_stats = cursor.fetchone()
                if translation_stats:
                    stats.update({
                        'total_translations': translation_stats[0],
                        'today_translations': translation_stats[1],
                        'week_translations': translation_stats[2],
                        'bookmarked_translations': translation_stats[3]
                    })
                
                # 言語ペア統計
                cursor.execute('''
                    SELECT source_language, target_language, COUNT(*) as count
                    FROM translation_history 
                    WHERE user_id = ?
                    GROUP BY source_language, target_language
                    ORDER BY count DESC
                    LIMIT 5
                ''', (user_id,))
                
                language_pairs = cursor.fetchall()
                stats['top_language_pairs'] = [
                    {'source': pair[0], 'target': pair[1], 'count': pair[2]}
                    for pair in language_pairs
                ]
                
                # Early Access利用統計
                cursor.execute('''
                    SELECT feature_name, COUNT(*) as usage_count
                    FROM early_access_logs 
                    WHERE user_id = ?
                    GROUP BY feature_name
                    ORDER BY usage_count DESC
                ''', (user_id,))
                
                early_access_usage = cursor.fetchall()
                stats['early_access_usage'] = [
                    {'feature': usage[0], 'count': usage[1]}
                    for usage in early_access_usage
                ]
                
                # 平均評価
                cursor.execute('''
                    SELECT AVG(rating) as avg_rating, COUNT(*) as rating_count
                    FROM translation_ratings 
                    WHERE user_id = ?
                ''', (user_id,))
                
                rating_stats = cursor.fetchone()
                if rating_stats and rating_stats[0]:
                    stats.update({
                        'average_rating': round(rating_stats[0], 2),
                        'total_ratings': rating_stats[1]
                    })
                
                return stats
                
        except Exception as e:
            logger.error(f"ユーザー統計取得エラー: {str(e)}")
            return {}
    
    def _cleanup_old_history(self, user_id: int, max_items: int) -> None:
        """古い翻訳履歴をクリーンアップ"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # ブックマーク以外の古いアイテムを削除
                cursor.execute('''
                    DELETE FROM translation_history 
                    WHERE user_id = ? AND bookmarked = 0 AND id NOT IN (
                        SELECT id FROM translation_history 
                        WHERE user_id = ? AND bookmarked = 0
                        ORDER BY created_at DESC 
                        LIMIT ?
                    )
                ''', (user_id, user_id, max_items))
                
                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    conn.commit()
                    logger.info(f"古い翻訳履歴クリーンアップ: ユーザーID {user_id}, 削除件数 {deleted_count}")
                    
        except Exception as e:
            logger.error(f"翻訳履歴クリーンアップエラー: {str(e)}")
    
    def export_user_data(self, user_id: int) -> Dict[str, Any]:
        """
        ユーザーデータをエクスポート（GDPR対応）
        
        Args:
            user_id: ユーザーID
            
        Returns:
            エクスポートデータ
        """
        try:
            export_data = {
                'user_id': user_id,
                'export_timestamp': datetime.now().isoformat(),
                'settings': asdict(self.get_user_settings(user_id)),
                'early_access_features': asdict(self.get_early_access_features(user_id)),
                'translation_history': [
                    asdict(item) for item in self.get_translation_history(user_id, limit=1000)
                ],
                'statistics': self.get_user_statistics(user_id)
            }
            
            logger.info(f"ユーザーデータエクスポート完了: ユーザーID {user_id}")
            return export_data
            
        except Exception as e:
            logger.error(f"ユーザーデータエクスポートエラー: {str(e)}")
            return {}
    
    def delete_user_data(self, user_id: int) -> bool:
        """
        ユーザーデータを完全削除（GDPR対応）
        
        Args:
            user_id: ユーザーID
            
        Returns:
            成功/失敗
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 関連テーブルからデータを削除（CASCADE削除で自動処理されるが明示的に実行）
                tables = [
                    'translation_ratings',
                    'early_access_logs', 
                    'translation_history',
                    'user_preferences',
                    'user_settings'
                ]
                
                for table in tables:
                    cursor.execute(f'DELETE FROM {table} WHERE user_id = ?', (user_id,))
                
                conn.commit()
                logger.info(f"ユーザーデータ完全削除完了: ユーザーID {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"ユーザーデータ削除エラー: {str(e)}")
            return False


# 使用例とテスト関数
if __name__ == "__main__":
    # テスト用実行
    profile_manager = UserProfileManager("test_profiles.db")
    
    # テスト用ユーザー設定
    test_settings = UserSettings(
        default_source_language="ja",
        default_target_language="en",
        display_language="jp",
        theme=ThemeType.DARK.value,
        save_translation_history=True
    )
    
    # 設定保存テスト
    success = profile_manager.save_user_settings(1, test_settings)
    print(f"設定保存テスト: {'成功' if success else '失敗'}")
    
    # 設定取得テスト
    loaded_settings = profile_manager.get_user_settings(1)
    print(f"設定取得テスト: テーマ = {loaded_settings.theme}")
    
    # 翻訳履歴追加テスト
    history_item = TranslationHistoryItem(
        user_id=1,
        source_text="こんにちは",
        source_language="ja",
        target_language="en",
        chatgpt_translation="Hello",
        session_id="test_session"
    )
    
    history_id = profile_manager.add_translation_history(history_item)
    print(f"翻訳履歴追加テスト: 履歴ID = {history_id}")
    
    # 統計取得テスト
    stats = profile_manager.get_user_statistics(1)
    print(f"統計取得テスト: 総翻訳数 = {stats.get('total_translations', 0)}")