"""
Task #7 SL-3 Phase 1: 翻訳状態キャッシュ管理モジュール

このモジュールは翻訳状態データのRedisキャッシュ化を提供します：
- language_pair, source_lang, target_lang の管理
- input_text, partner_message, context_info の揮発性キャッシュ管理
- SessionRedisManagerとの統合によるキャッシュ操作
- エラー時のフォールバック機能

設計方針：
- SL-2.2で実装したRedis基盤を最大限活用
- context_manager.pyとの機能分離（contextは履歴系、こちらは状態系）
- 将来のStateManager統合に向けた準備
"""

import logging
import json
import time
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from services.session_redis_manager import get_session_redis_manager
from config import REDIS_TTL  # Phase 3c-2: TTL設定外部化

# 🆕 Task#9-4 AP-1 Ph4 Step4（再挑戦）- Level1: StateManager監視
from utils.debug_logger import watch_io

logger = logging.getLogger(__name__)


class TranslationStateManager:
    """
    翻訳状態専用Redisキャッシュ管理クラス
    
    責務:
    - 翻訳状態（言語・入力・ペア・コンテキスト）のCRUDを提供
    - TTL管理: 翻訳状態は3600秒（1時間）、入力データは1800秒（30分）
    - エラーハンドリングとフォールバック機能
    """
    
    # TTL設定
    STATE_TTL = 3600  # 翻訳状態（言語設定等）: 1時間
    INPUT_TTL = 1800  # 入力データ（テキスト等）: 30分
    
    # キャッシュキー定義
    CACHE_KEYS = {
        # 翻訳状態系（長期保持）
        'language_pair': {'ttl': STATE_TTL, 'type': 'state'},
        'source_lang': {'ttl': STATE_TTL, 'type': 'state'}, 
        'target_lang': {'ttl': STATE_TTL, 'type': 'state'},
        
        # 入力データ系（短期保持）
        'input_text': {'ttl': INPUT_TTL, 'type': 'input'},
        'partner_message': {'ttl': INPUT_TTL, 'type': 'input'},
        'context_info': {'ttl': INPUT_TTL, 'type': 'input'},
    }
    
    # 🆕 SL-3 Phase 2: 大容量データ用キー定義
    LARGE_DATA_KEYS = {
        # 翻訳結果系（30分保持）
        'translated_text': {'ttl': INPUT_TTL, 'type': 'translation'},
        'reverse_translated_text': {'ttl': INPUT_TTL, 'type': 'translation'},
        'better_translation': {'ttl': INPUT_TTL, 'type': 'translation'},
        'reverse_better_translation': {'ttl': INPUT_TTL, 'type': 'translation'},
        'gemini_translation': {'ttl': INPUT_TTL, 'type': 'translation'},
        'gemini_reverse_translation': {'ttl': INPUT_TTL, 'type': 'translation'},
        
        # 分析結果系（30分保持）
        'gemini_3way_analysis': {'ttl': INPUT_TTL, 'type': 'analysis'},
        
        # 🆕 Phase 3c-1b: TranslationContext統合用キー
        'context_full_data': {'ttl': STATE_TTL, 'type': 'context'},
        'interactive_current_chat': {'ttl': INPUT_TTL, 'type': 'interactive'},
        'interactive_chat_history': {'ttl': INPUT_TTL, 'type': 'interactive'},
        'context_metadata': {'ttl': STATE_TTL, 'type': 'context'},
    }
    
    def __init__(self):
        """初期化"""
        self.redis_manager = get_session_redis_manager()
        logger.info("✅ SL-3 Phase 1: TranslationStateManager initialized")
        
    def _get_cache_key(self, session_id: str, field_name: str) -> str:
        """
        キャッシュキーを生成
        
        Args:
            session_id: セッションID
            field_name: フィールド名
            
        Returns:
            str: Redis用キャッシュキー
        """
        import os
        environment = os.getenv('ENVIRONMENT', 'development')
        if environment == 'production':
            prefix = 'langpont:prod:translation_state'
        elif environment == 'staging':
            prefix = 'langpont:stage:translation_state'
        else:
            prefix = 'langpont:dev:translation_state'
            
        return f"{prefix}:{session_id}:{field_name}"
    
    def set_translation_state(self, session_id: str, field_name: str, value: Union[str, dict], ttl: Optional[int] = None) -> bool:
        """
        翻訳状態をRedisに設定
        
        Args:
            session_id: セッションID
            field_name: フィールド名
            value: 設定値
            ttl: TTL（指定なしの場合は設定による自動判定）
            
        Returns:
            bool: 設定成功フラグ
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("⚠️ SL-3 Phase 1: Redis not available for translation state set")
                return False
                
            # TTLの決定
            if ttl is None:
                ttl = self.CACHE_KEYS.get(field_name, {}).get('ttl', self.STATE_TTL)
            
            cache_key = self._get_cache_key(session_id, field_name)
            
            # 値の準備（JSON化が必要な場合）
            cache_value = json.dumps(value) if isinstance(value, dict) else str(value)
            
            # Redis設定
            self.redis_manager.redis_client.set(cache_key, cache_value, ex=ttl)
            
            field_type = self.CACHE_KEYS.get(field_name, {}).get('type', 'unknown')
            logger.debug(f"✅ SL-3 Phase 1: Translation state set - {field_name}({field_type}) for session {session_id[:16]}... TTL={ttl}s")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ SL-3 Phase 1: Failed to set translation state {field_name}: {e}")
            return False
    
    @watch_io("STATE_MANAGER", "_REDIS_GET")
    def get_translation_state(self, session_id: str, field_name: str, default_value: Any = None) -> Any:
        """
        翻訳状態をRedisから取得
        
        Args:
            session_id: セッションID
            field_name: フィールド名
            default_value: デフォルト値
            
        Returns:
            Any: 取得値またはデフォルト値
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("⚠️ SL-3 Phase 1: Redis not available for translation state get")
                return default_value
                
            cache_key = self._get_cache_key(session_id, field_name)
            
            # Redis取得
            cached_value = self.redis_manager.redis_client.get(cache_key)
            
            if cached_value is None:
                logger.debug(f"📭 SL-3 Phase 1: No cached value for {field_name} in session {session_id[:16]}...")
                return default_value
            
            # 値のデコード
            try:
                # JSON形式の場合はパース
                decoded_value = json.loads(cached_value.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # 通常の文字列の場合
                decoded_value = cached_value.decode('utf-8')
            
            field_type = self.CACHE_KEYS.get(field_name, {}).get('type', 'unknown')
            logger.debug(f"📦 SL-3 Phase 1: Translation state retrieved - {field_name}({field_type}) for session {session_id[:16]}...")
            
            return decoded_value
            
        except Exception as e:
            logger.error(f"❌ SL-3 Phase 1: Failed to get translation state {field_name}: {e}")
            return default_value
    
    def set_multiple_states(self, session_id: str, states: Dict[str, Any]) -> Dict[str, bool]:
        """
        複数の翻訳状態を一括設定
        
        Args:
            session_id: セッションID
            states: 状態データの辞書
            
        Returns:
            Dict[str, bool]: 各フィールドの設定成功フラグ
        """
        results = {}
        
        for field_name, value in states.items():
            if field_name in self.CACHE_KEYS:
                results[field_name] = self.set_translation_state(session_id, field_name, value)
            else:
                logger.warning(f"⚠️ SL-3 Phase 1: Unknown field name for caching: {field_name}")
                results[field_name] = False
                
        successful_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        logger.info(f"📊 SL-3 Phase 1: Bulk state update - {successful_count}/{total_count} successful for session {session_id[:16]}...")
        
        return results
    
    def save_translation_state(self, session_id: str, states: Dict[str, Any]) -> Dict[str, bool]:
        """
        翻訳状態を一括保存（Redis TTL対応）
        Task #9-3 AP-1 Phase 3c-2: config.pyのTTL設定適用
        
        Args:
            session_id: セッションID
            states: 状態データの辞書
            
        Returns:
            Dict[str, bool]: 各フィールドの設定成功フラグ
        """
        results = {}
        
        for field_name, value in states.items():
            if field_name in self.CACHE_KEYS:
                # config.pyからTTL値を取得
                ttl_value = REDIS_TTL['translation_state']
                results[field_name] = self.set_translation_state(session_id, field_name, value, ttl=ttl_value)
            else:
                logger.warning(f"⚠️ Phase 3c-2: Unknown field name for caching: {field_name}")
                results[field_name] = False
                
        successful_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        logger.info(f"📊 Phase 3c-2: Bulk state update - {successful_count}/{total_count} successful for session {session_id[:16]}...")
        
        return results
    
    def get_multiple_states(self, session_id: str, field_names: list, default_values: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        複数の翻訳状態を一括取得
        
        Args:
            session_id: セッションID
            field_names: フィールド名のリスト
            default_values: デフォルト値の辞書
            
        Returns:
            Dict[str, Any]: 取得した状態データ
        """
        if default_values is None:
            default_values = {}
            
        results = {}
        
        for field_name in field_names:
            default_val = default_values.get(field_name, None)
            results[field_name] = self.get_translation_state(session_id, field_name, default_val)
            
        logger.debug(f"📊 SL-3 Phase 1: Bulk state retrieval - {len(results)} fields for session {session_id[:16]}...")
        
        return results
    
    def clear_translation_states(self, session_id: str, field_names: Optional[list] = None) -> int:
        """
        翻訳状態をクリア
        
        Args:
            session_id: セッションID
            field_names: クリアするフィールド名（指定なしの場合は全て）
            
        Returns:
            int: クリアされたフィールド数
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("⚠️ SL-3 Phase 1: Redis not available for translation state clear")
                return 0
                
            if field_names is None:
                field_names = list(self.CACHE_KEYS.keys())
            
            cleared_count = 0
            for field_name in field_names:
                cache_key = self._get_cache_key(session_id, field_name)
                if self.redis_manager.redis_client.delete(cache_key):
                    cleared_count += 1
            
            logger.info(f"🧹 SL-3 Phase 1: Translation states cleared - {cleared_count} fields for session {session_id[:16]}...")
            
            return cleared_count
            
        except Exception as e:
            logger.error(f"❌ SL-3 Phase 1: Failed to clear translation states: {e}")
            return 0
    
    def get_cache_info(self, session_id: str) -> Dict[str, Any]:
        """
        キャッシュ情報を取得（デバッグ用）
        
        Args:
            session_id: セッションID
            
        Returns:
            Dict[str, Any]: キャッシュ情報
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                return {"error": "Redis not available"}
                
            cache_info = {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "fields": {}
            }
            
            for field_name in self.CACHE_KEYS.keys():
                cache_key = self._get_cache_key(session_id, field_name)
                
                # 存在チェック
                exists = self.redis_manager.redis_client.exists(cache_key)
                ttl = self.redis_manager.redis_client.ttl(cache_key) if exists else -2
                
                cache_info["fields"][field_name] = {
                    "exists": bool(exists),
                    "ttl": ttl,
                    "key": cache_key
                }
            
            return cache_info
            
        except Exception as e:
            logger.error(f"❌ SL-3 Phase 1: Failed to get cache info: {e}")
            return {"error": str(e)}
    
    # 🆕 SL-3 Phase 2: 大容量データ管理メソッド
    
    def save_large_data(self, key: str, value: str, session_id: str, ttl: int = None) -> bool:
        """
        大容量データをRedisに保存（Phase 3c-2: TTL設定外部化対応）
        
        Args:
            key: データキー名
            value: 保存する値
            session_id: セッションID
            ttl: TTL（指定なしの場合はconfig.pyから取得）
            
        Returns:
            bool: 保存成功フラグ
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning(f"⚠️ Phase 3c-2: Redis not available for large data save - key: {key}")
                return False
                
            if key not in self.LARGE_DATA_KEYS:
                logger.warning(f"⚠️ Phase 3c-2: Unknown large data key: {key}")
                return False
                
            # Phase 3c-2: config.pyからTTL値を取得
            if ttl is None:
                ttl = REDIS_TTL['large_data']
            
            cache_key = self._get_cache_key(session_id, key)
            
            # 値のサイズログ出力（デバッグ用）
            value_size = len(value.encode('utf-8')) if value else 0
            
            # Redis保存
            self.redis_manager.redis_client.set(cache_key, value, ex=ttl)
            
            data_type = self.LARGE_DATA_KEYS[key]['type']
            logger.info(f"✅ Phase 3c-2: Large data saved - {key}({data_type}) for session {session_id[:16]}... Size={value_size}bytes TTL={ttl}s")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Phase 3c-2: Failed to save large data {key}: {e}")
            return False
    
    def get_large_data(self, key: str, session_id: str, default: str = None) -> str:
        """
        大容量データをRedisから取得
        
        Args:
            key: データキー名
            session_id: セッションID
            default: デフォルト値
            
        Returns:
            str: 取得値またはデフォルト値
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning(f"⚠️ SL-3 Phase 2: Redis not available for large data get - key: {key}")
                return default or ""
                
            if key not in self.LARGE_DATA_KEYS:
                logger.warning(f"⚠️ SL-3 Phase 2: Unknown large data key: {key}")
                return default or ""
            
            cache_key = self._get_cache_key(session_id, key)
            
            # Redis取得
            cached_value = self.redis_manager.redis_client.get(cache_key)
            
            if cached_value is None:
                logger.debug(f"📭 SL-3 Phase 2: No cached large data for {key} in session {session_id[:16]}...")
                return default or ""
            
            # 値のデコード
            try:
                decoded_value = cached_value.decode('utf-8')
            except UnicodeDecodeError as e:
                logger.error(f"❌ SL-3 Phase 2: Unicode decode error for {key}: {e}")
                return default or ""
            
            data_type = self.LARGE_DATA_KEYS[key]['type']
            value_size = len(decoded_value.encode('utf-8'))
            logger.debug(f"📦 SL-3 Phase 2: Large data retrieved - {key}({data_type}) for session {session_id[:16]}... Size={value_size}bytes")
            
            return decoded_value
            
        except Exception as e:
            logger.error(f"❌ SL-3 Phase 2: Failed to get large data {key}: {e}")
            return default or ""
    
    def delete_large_data(self, key: str, session_id: str) -> bool:
        """
        大容量データをRedisから削除
        
        Args:
            key: データキー名
            session_id: セッションID
            
        Returns:
            bool: 削除成功フラグ
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning(f"⚠️ SL-3 Phase 2: Redis not available for large data delete - key: {key}")
                return False
                
            if key not in self.LARGE_DATA_KEYS:
                logger.warning(f"⚠️ SL-3 Phase 2: Unknown large data key: {key}")
                return False
            
            cache_key = self._get_cache_key(session_id, key)
            
            # Redis削除
            result = self.redis_manager.redis_client.delete(cache_key)
            
            if result:
                data_type = self.LARGE_DATA_KEYS[key]['type']
                logger.info(f"🗑️ SL-3 Phase 2: Large data deleted - {key}({data_type}) for session {session_id[:16]}...")
                return True
            else:
                logger.debug(f"📭 SL-3 Phase 2: Large data not found for deletion - {key} in session {session_id[:16]}...")
                return False
            
        except Exception as e:
            logger.error(f"❌ SL-3 Phase 2: Failed to delete large data {key}: {e}")
            return False
    
    @watch_io("STATE_MANAGER", "_REDIS_SAVE")
    def save_multiple_large_data(self, session_id: str, data_dict: Dict[str, str]) -> Dict[str, bool]:
        """
        複数の大容量データを一括保存
        
        Args:
            session_id: セッションID
            data_dict: データの辞書 {key: value}
            
        Returns:
            Dict[str, bool]: 各キーの保存成功フラグ
        """
        results = {}
        
        for key, value in data_dict.items():
            if key in self.LARGE_DATA_KEYS:
                results[key] = self.save_large_data(key, value, session_id)
                if results[key]:
                    logger.info(f"✅ Saved to Redis: {key} = {str(value)[:50]}...")
            else:
                logger.warning(f"⚠️ SL-3 Phase 2: Unknown large data key for bulk save: {key}")
                results[key] = False
                
        successful_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        logger.info(f"📊 SL-3 Phase 2: Bulk large data save - {successful_count}/{total_count} successful for session {session_id[:16]}...")
        
        return results
    
    def save_context_data(self, session_id: str, context_data: Dict[str, Any]) -> bool:
        """
        翻訳コンテキスト全体をRedisに保存
        Task #9-3 AP-1 Phase 3c-2: TTL設定外部化対応
        
        Args:
            session_id: セッションID
            context_data: 保存するコンテキストデータ
            
        Returns:
            bool: 保存成功フラグ
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("❌ Phase 3c-2: Redis not connected for context save")
                return False
            
            # コンテキストデータをJSON文字列に変換
            context_json = json.dumps(context_data, ensure_ascii=False)
            
            # Phase 3c-2: context_full_dataに専用TTLを適用
            cache_key = self._get_cache_key(session_id, 'context_full_data')
            ttl_value = REDIS_TTL['context_full']
            
            # Redis保存
            self.redis_manager.redis_client.set(cache_key, context_json, ex=ttl_value)
            
            logger.info(f"✅ Phase 3c-2: Context data saved - {len(context_json)} chars for session {session_id[:16]}... TTL={ttl_value}s")
            return True
            
        except Exception as e:
            logger.error(f"❌ Phase 3c-2: Failed to save context data: {e}")
            return False
    
    def get_context_data(self, session_id: str) -> Dict[str, Any]:
        """
        翻訳コンテキスト全体をRedisから取得（TranslationContext.get_context()互換）
        Task #9-3 AP-1 Phase 3c-1b: TranslationContext統合
        
        Args:
            session_id: セッションID
            
        Returns:
            Dict[str, Any]: コンテキストデータ（TranslationContext互換形式）
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("❌ Phase 3c-1b: Redis not connected for context retrieval")
                return {}
            
            # context_full_dataから取得
            context_json = self.get_large_data('context_full_data', session_id, default='{}')
            
            if context_json == '{}':
                # コンテキストが存在しない場合、個別データから再構築を試みる
                from flask import session
                full_context = {
                    "context_id": f"rebuilt_{session_id[:8]}",
                    "timestamp": time.time(),
                    "created_at": datetime.now().isoformat(),
                    "input_text": self.get_translation_state(session_id, "input_text", "") or session.get("input_text", ""),
                    "translations": {
                        "chatgpt": self.get_large_data("translated_text", session_id, "") or session.get("translated_text", ""),
                        "enhanced": self.get_large_data("better_translation", session_id, "") or session.get("better_translation", ""),
                        "gemini": self.get_large_data("gemini_translation", session_id, "") or session.get("gemini_translation", ""),
                        "chatgpt_reverse": self.get_large_data("reverse_translated_text", session_id, "") or session.get("reverse_translated_text", ""),
                        "enhanced_reverse": self.get_large_data("reverse_better_translation", session_id, "") or session.get("reverse_better_translation", ""),
                        "gemini_reverse": self.get_large_data("gemini_reverse_translation", session_id, "") or session.get("gemini_reverse_translation", "")
                    },
                    "analysis": self.get_large_data("gemini_3way_analysis", session_id, "") or session.get("gemini_3way_analysis", ""),
                    "metadata": {
                        "source_lang": self.get_translation_state(session_id, "source_lang", "") or session.get("source_lang", ""),
                        "target_lang": self.get_translation_state(session_id, "target_lang", "") or session.get("target_lang", ""),
                        "partner_message": self.get_translation_state(session_id, "partner_message", "") or session.get("partner_message", ""),
                        "context_info": self.get_translation_state(session_id, "context_info", "") or session.get("context_info", "")
                    }
                }
                
                # データが存在する場合のみ返す
                if full_context["input_text"] or any(full_context["translations"].values()):
                    logger.info(f"📦 Phase 3c-1b: Context rebuilt from individual keys for session {session_id[:16]}...")
                    return full_context
                else:
                    return {}
            
            # JSON文字列をパース
            context_data = json.loads(context_json)
            logger.info(f"📦 Phase 3c-1b: Context retrieved - {len(context_json)} chars for session {session_id[:16]}...")
            
            return context_data
            
        except Exception as e:
            logger.error(f"❌ Phase 3c-1b: Failed to get context data: {e}")
            return {}
    
    def clear_context_data(self, session_id: str) -> bool:
        """
        翻訳コンテキスト全体をクリア
        Task #9-3 AP-1 Phase 3c-1b: TranslationContext統合
        
        Args:
            session_id: セッションID
            
        Returns:
            bool: クリア成功フラグ
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("❌ Phase 3c-1b: Redis not connected for context clear")
                return False
            
            # コンテキスト関連の全キーをクリア
            keys_to_clear = [
                'context_full_data',
                'context_metadata',
                'input_text',
                'partner_message', 
                'context_info',
                'translated_text',
                'better_translation',
                'gemini_translation',
                'reverse_translated_text',
                'reverse_better_translation',
                'gemini_reverse_translation',
                'gemini_3way_analysis'
            ]
            
            cleared_count = 0
            for key in keys_to_clear:
                cache_key = self._get_cache_key(session_id, key)
                try:
                    if self.redis_manager.redis_client.delete(cache_key):
                        cleared_count += 1
                except:
                    pass
            
            logger.info(f"🧹 Phase 3c-1b: Context cleared - {cleared_count} keys deleted for session {session_id[:16]}...")
            return cleared_count > 0
            
        except Exception as e:
            logger.error(f"❌ Phase 3c-1b: Failed to clear context data: {e}")
            return False
    
    def save_interactive_chat(self, session_id: str, chat_data: Dict[str, Any]) -> bool:
        """
        current_chatデータを保存
        Task #9-3 AP-1 Phase 3c-2: TTL設定外部化対応
        
        Args:
            session_id: セッションID
            chat_data: チャットデータ
            
        Returns:
            bool: 保存成功フラグ
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("❌ Phase 3c-2: Redis not connected for chat save")
                return False
            
            # チャットデータをJSON文字列に変換
            chat_json = json.dumps(chat_data, ensure_ascii=False)
            
            # Phase 3c-2: TTL設定外部化対応
            saved = self.save_large_data('interactive_current_chat', chat_json, session_id)
            
            if saved:
                logger.info(f"💬 Phase 3c-2: Interactive chat saved - {len(chat_json)} chars for session {session_id[:16]}...")
            
            return saved
            
        except Exception as e:
            logger.error(f"❌ Phase 3c-2: Failed to save interactive chat: {e}")
            return False
    
    def get_interactive_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        インタラクティブ履歴を取得
        Task #9-3 AP-1 Phase 3c-2: TTL設定外部化対応
        
        Args:
            session_id: セッションID
            limit: 取得する履歴の上限数
            
        Returns:
            List[Dict[str, Any]]: チャット履歴リスト
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("❌ Phase 3c-2: Redis not connected for history retrieval")
                return []
            
            # interactive_chat_historyから取得
            history_json = self.get_large_data('interactive_chat_history', session_id, default='[]')
            
            # JSON文字列をパース
            history_list = json.loads(history_json)
            
            # limitに従って最新のものから取得
            if len(history_list) > limit:
                history_list = history_list[-limit:]
            
            logger.info(f"📜 Phase 3c-2: Interactive history retrieved - {len(history_list)} items for session {session_id[:16]}...")
            
            return history_list
            
        except Exception as e:
            logger.error(f"❌ Phase 3c-2: Failed to get interactive history: {e}")
            return []
    
    def save_user_history_index(self, user_id: str, history_data: Dict[str, Any]) -> bool:
        """
        ユーザー履歴インデックスを保存
        Task #9-3 AP-1 Phase 3c-2: 無期限保存対応
        
        Args:
            user_id: ユーザーID
            history_data: 履歴インデックスデータ
            
        Returns:
            bool: 保存成功フラグ
        """
        try:
            if not self.redis_manager or not self.redis_manager.is_connected:
                logger.warning("❌ Phase 3c-2: Redis not connected for user history save")
                return False
            
            # ユーザー履歴用のキー生成
            cache_key = self._get_cache_key(user_id, 'user_history_index')
            
            # 履歴データをJSON文字列に変換
            history_json = json.dumps(history_data, ensure_ascii=False)
            
            # TTLがNone（無期限）の場合はpersist()を使用
            ttl_value = REDIS_TTL['user_history']
            
            if ttl_value is None:
                # 無期限保存：TTLなしでset後、persist()で期限解除
                self.redis_manager.redis_client.set(cache_key, history_json)
                self.redis_manager.redis_client.persist(cache_key)
                logger.info(f"✅ Phase 3c-2: User history saved (persistent) - user {user_id[:8]}... Size={len(history_json)}bytes")
            else:
                # TTL指定保存
                self.redis_manager.redis_client.set(cache_key, history_json, ex=ttl_value)
                logger.info(f"✅ Phase 3c-2: User history saved - user {user_id[:8]}... Size={len(history_json)}bytes TTL={ttl_value}s")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Phase 3c-2: Failed to save user history: {e}")
            return False


def get_translation_state_manager() -> TranslationStateManager:
    """
    TranslationStateManagerのファクトリ関数
    
    Returns:
        TranslationStateManager: インスタンス
    """
    return TranslationStateManager()