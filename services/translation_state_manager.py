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
from typing import Dict, Any, Optional, Union
from datetime import datetime
from services.session_redis_manager import get_session_redis_manager

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


def get_translation_state_manager() -> TranslationStateManager:
    """
    TranslationStateManagerのファクトリ関数
    
    Returns:
        TranslationStateManager: インスタンス
    """
    return TranslationStateManager()