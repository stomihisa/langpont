#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangPont データベースリセットスクリプト
古いデータベースファイルを安全に削除し、新しいデータベースを初期化する
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime
import shutil

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# データベースファイルリスト
DATABASE_FILES = [
    "langpont_users.db",
    "langpont_translation_history.db",
    "test_profiles.db",
    "test_translation_history.db"
]

def backup_database(db_path: str) -> str:
    """データベースファイルをバックアップ"""
    if os.path.exists(db_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.backup_{timestamp}"
        try:
            shutil.copy2(db_path, backup_path)
            logger.info(f"データベースバックアップ作成: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"バックアップ作成失敗: {str(e)}")
            return ""
    return ""

def remove_database(db_path: str) -> bool:
    """データベースファイルを削除"""
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            logger.info(f"データベースファイル削除: {db_path}")
            return True
        except Exception as e:
            logger.error(f"データベースファイル削除失敗: {str(e)}")
            return False
    else:
        logger.info(f"データベースファイルが存在しません: {db_path}")
        return True

def initialize_auth_system():
    """認証システムデータベースを初期化"""
    try:
        from user_auth import UserAuthSystem
        auth_system = UserAuthSystem()
        logger.info("認証システムデータベース初期化完了")
        return True
    except Exception as e:
        logger.error(f"認証システム初期化エラー: {str(e)}")
        return False

def initialize_translation_history():
    """翻訳履歴システムデータベースを初期化"""
    try:
        from translation_history import TranslationHistoryManager
        history_manager = TranslationHistoryManager()
        logger.info("翻訳履歴システムデータベース初期化完了")
        return True
    except Exception as e:
        logger.error(f"翻訳履歴システム初期化エラー: {str(e)}")
        return False

def initialize_user_profile():
    """ユーザープロファイルシステムデータベースを初期化"""
    try:
        from user_profile import UserProfileManager
        profile_manager = UserProfileManager()
        logger.info("ユーザープロファイルシステムデータベース初期化完了")
        return True
    except Exception as e:
        logger.error(f"ユーザープロファイルシステム初期化エラー: {str(e)}")
        return False

def verify_database_structure(db_path: str) -> bool:
    """データベース構造を検証"""
    if not os.path.exists(db_path):
        logger.warning(f"データベースファイルが存在しません: {db_path}")
        return False
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # テーブル一覧を取得
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            table_names = [table[0] for table in tables]
            
            logger.info(f"データベース {db_path} のテーブル: {table_names}")
            
            # 各テーブルの構造を確認
            for table_name in table_names:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                logger.debug(f"テーブル {table_name} の構造: {[col[1] for col in columns]}")
            
            return True
            
    except Exception as e:
        logger.error(f"データベース検証エラー: {str(e)}")
        return False

def main():
    """メイン処理"""
    logger.info("=== LangPont データベースリセット開始 ===")
    
    # バックアップ作成（オプション）
    backup_option = input("データベースをバックアップしますか？ (y/n): ").lower().strip()
    backup_created = False
    
    if backup_option == 'y':
        for db_file in DATABASE_FILES:
            if backup_database(db_file):
                backup_created = True
    
    # データベースファイル削除の確認
    confirm = input("データベースファイルを削除して初期化しますか？ (y/n): ").lower().strip()
    
    if confirm != 'y':
        logger.info("処理を中止しました")
        return
    
    # データベースファイル削除
    for db_file in DATABASE_FILES:
        remove_database(db_file)
    
    # システム初期化
    logger.info("=== データベース初期化開始 ===")
    
    # 認証システム初期化
    if initialize_auth_system():
        verify_database_structure("langpont_users.db")
    
    # 翻訳履歴システム初期化
    if initialize_translation_history():
        verify_database_structure("langpont_translation_history.db")
    
    # ユーザープロファイルシステム初期化（user_authと同じDBを使用）
    if initialize_user_profile():
        logger.info("ユーザープロファイルシステム初期化完了")
    
    logger.info("=== データベースリセット完了 ===")
    
    if backup_created:
        logger.info("バックアップファイルが作成されました。不要になったら手動で削除してください。")

if __name__ == "__main__":
    main()