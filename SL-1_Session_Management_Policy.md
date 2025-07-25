# 📋 SL-1: セッション管理統一ポリシー

**ポリシー策定日**: 2025年7月25日  
**対象**: LangPont セッション管理の統一規則  
**策定者**: Claude Code  

## 🎯 ポリシー目的

### 統一化目標
- **命名規則**: セッションキーの統一された命名体系
- **データ型規則**: 型安全性と一貫性の確保
- **エラーハンドリング**: 統一的な例外処理パターン
- **監視・運用**: 包括的なメトリクス・ログ体系

### 保守性向上
- **可読性**: 明確で理解しやすいセッション構造
- **拡張性**: 新機能追加時の影響範囲限定
- **デバッグ性**: 問題特定・解決の効率化

---

## 📛 1. 命名規則（Naming Convention）

### 1.1 セッションキー命名規則

#### 基本パターン
```
session:{category}:{session_id}:{sub_category}
```

#### カテゴリ分類
```python
SESSION_CATEGORIES = {
    'auth': '認証・権限情報',
    'security': 'CSRF・セキュリティ情報',
    'translation': '翻訳処理データ', 
    'ui': 'UI設定・言語設定',
    'stats': '使用量・統計データ',
    'temp': '一時的・動的データ'
}
```

#### 具体的命名例
```python
NAMING_EXAMPLES = {
    # 認証カテゴリ
    'session:auth:abc123:logged_in': 'ログイン状態',
    'session:auth:abc123:username': 'ユーザー名',
    'session:auth:abc123:user_role': 'ユーザー権限',
    'session:auth:abc123:user_id': 'ユーザーID',
    'session:auth:abc123:daily_limit': '日次制限',
    
    # セキュリティカテゴリ
    'session:security:abc123:csrf_token': 'CSRFトークン',
    'session:security:abc123:session_created': 'セッション作成時刻',
    'session:security:abc123:last_activity': '最終アクティビティ',
    
    # 翻訳カテゴリ
    'session:translation:abc123:source_lang': '翻訳元言語',
    'session:translation:abc123:target_lang': '翻訳先言語',
    'session:translation:abc123:input_text': '入力テキスト',
    'session:translation:abc123:analysis_engine': '分析エンジン',
    
    # UIカテゴリ
    'session:ui:abc123:lang': '表示言語',
    'session:ui:abc123:preferred_lang': '優先言語',
    'session:ui:abc123:theme': 'テーマ設定',
    
    # 統計カテゴリ
    'session:stats:abc123:usage_count': '使用回数',
    'session:stats:abc123:last_usage_date': '最終使用日',
    'session:stats:abc123:avg_rating': '平均評価',
    
    # 一時カテゴリ
    'session:temp:abc123:temp_lang_override': '一時言語切り替え',
    'session:temp:abc123:analysis_result': '分析結果（一時）',
}
```

### 1.2 名前空間設計

#### 階層構造
```
langpont/
├── session:auth:*         # 認証情報（Critical）
├── session:security:*     # セキュリティ情報（Critical）
├── session:translation:*  # 翻訳情報（High）
├── session:ui:*          # UI設定（Medium）
├── session:stats:*       # 統計情報（Medium）
└── session:temp:*        # 一時情報（Low）
```

#### プレフィックス管理
```python
SESSION_PREFIXES = {
    'production': 'langpont:prod:session',
    'staging': 'langpont:stage:session',
    'development': 'langpont:dev:session',
    'testing': 'langpont:test:session'
}

def get_session_key(environment: str, category: str, session_id: str, field: str) -> str:
    """統一セッションキー生成"""
    prefix = SESSION_PREFIXES.get(environment, SESSION_PREFIXES['development'])
    return f"{prefix}:{category}:{session_id}:{field}"
```

### 1.3 フィールド命名規則

#### 命名パターン
```python
FIELD_NAMING_RULES = {
    # 状態フラグ: is_, has_, can_
    'is_logged_in': 'boolean',
    'has_permission': 'boolean', 
    'can_access': 'boolean',
    
    # 識別子: _id, _key, _token
    'user_id': 'string',
    'session_key': 'string',
    'csrf_token': 'string',
    
    # 時刻: _at, _time, _date
    'created_at': 'timestamp',
    'last_access_time': 'timestamp',
    'usage_date': 'date',
    
    # カウンター: _count, _number
    'usage_count': 'integer',
    'login_attempts': 'integer',
    
    # 設定: _config, _setting, _preference
    'language_setting': 'string',
    'theme_preference': 'string'
}
```

---

## 🏷️ 2. データ型規則（Data Type Standards）

### 2.1 型統一ルール

#### 基本データ型
```python
SESSION_DATA_TYPES = {
    # 文字列型（最も一般的）
    'string': {
        'examples': ['username', 'language', 'analysis_engine'],
        'validation': 'str, max_length=255',
        'redis_type': 'string',
        'encoding': 'utf-8'
    },
    
    # 整数型（カウンター・ID）
    'integer': {
        'examples': ['user_id', 'usage_count', 'daily_limit'],
        'validation': 'int, min_value=0',
        'redis_type': 'string',  # Redisでは文字列として保存
        'conversion': 'str(value) / int(value)'
    },
    
    # 真偽値型（フラグ・状態）
    'boolean': {
        'examples': ['logged_in', 'early_access', 'is_admin'],
        'validation': 'bool',
        'redis_type': 'string',
        'values': ['true', 'false'],  # Redisでは文字列
        'conversion': 'str(value).lower() / value.lower() == "true"'
    },
    
    # タイムスタンプ型（時刻情報）
    'timestamp': {
        'examples': ['session_created', 'last_activity'],
        'validation': 'datetime',
        'redis_type': 'string',
        'format': 'ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)',
        'conversion': 'datetime.isoformat() / datetime.fromisoformat()'
    },
    
    # 日付型（日付のみ）
    'date': {
        'examples': ['last_usage_date', 'registration_date'],
        'validation': 'date',
        'redis_type': 'string',
        'format': 'YYYY-MM-DD',
        'conversion': 'date.isoformat() / date.fromisoformat()'
    },
    
    # JSON型（複雑なデータ）
    'json': {
        'examples': ['analysis_result', 'user_preferences'],
        'validation': 'dict',
        'redis_type': 'string',
        'encoding': 'json.dumps() / json.loads()',
        'compression': 'gzip for large data'
    }
}
```

### 2.2 型変換ユーティリティ

#### SessionDataConverter
```python
import json
import gzip
from datetime import datetime, date
from typing import Any, Union

class SessionDataConverter:
    """セッションデータの型変換統一ユーティリティ"""
    
    @staticmethod
    def to_redis_value(value: Any, data_type: str) -> str:
        """Python値をRedis保存用文字列に変換"""
        if value is None:
            return ""
        
        if data_type == 'string':
            return str(value)
        elif data_type == 'integer':
            return str(int(value))
        elif data_type == 'boolean':
            return str(bool(value)).lower()
        elif data_type == 'timestamp':
            if isinstance(value, datetime):
                return value.isoformat()
            return str(value)
        elif data_type == 'date':
            if isinstance(value, date):
                return value.isoformat()
            return str(value)
        elif data_type == 'json':
            json_str = json.dumps(value, ensure_ascii=False)
            # 大容量データは圧縮
            if len(json_str) > 1024:  # 1KB超過時
                return gzip.compress(json_str.encode()).decode('latin1')
            return json_str
        else:
            return str(value)
    
    @staticmethod
    def from_redis_value(value: str, data_type: str) -> Any:
        """Redis文字列をPython値に変換"""
        if not value:
            return None
        
        try:
            if data_type == 'string':
                return value
            elif data_type == 'integer':
                return int(value)
            elif data_type == 'boolean':
                return value.lower() == 'true'
            elif data_type == 'timestamp':
                return datetime.fromisoformat(value)
            elif data_type == 'date':
                return date.fromisoformat(value)
            elif data_type == 'json':
                # 圧縮データかチェック
                try:
                    # gzip圧縮データの復元試行
                    decompressed = gzip.decompress(value.encode('latin1')).decode()
                    return json.loads(decompressed)
                except:
                    # 通常のJSON文字列
                    return json.loads(value)
            else:
                return value
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            # 変換失敗時はログ記録して元の値を返す
            logging.warning(f"Type conversion failed: {data_type}, value: {value}, error: {e}")
            return value
```

### 2.3 データ検証ルール

#### ValidationSchemas
```python
SESSION_VALIDATION_SCHEMAS = {
    'auth': {
        'logged_in': {'type': 'boolean', 'required': True},
        'username': {'type': 'string', 'max_length': 50, 'pattern': r'^[a-zA-Z0-9_]+$'},
        'user_role': {'type': 'string', 'choices': ['admin', 'user', 'guest']},
        'user_id': {'type': 'integer', 'min_value': 1},
        'daily_limit': {'type': 'integer', 'min_value': 0, 'max_value': 10000}
    },
    
    'security': {
        'csrf_token': {'type': 'string', 'length': 64, 'pattern': r'^[a-zA-Z0-9_-]+$'},
        'session_created': {'type': 'timestamp', 'required': True}
    },
    
    'translation': {
        'source_lang': {'type': 'string', 'choices': ['ja', 'en', 'fr', 'es', 'zh']},
        'target_lang': {'type': 'string', 'choices': ['ja', 'en', 'fr', 'es', 'zh']},
        'input_text': {'type': 'string', 'max_length': 5000},
        'analysis_engine': {'type': 'string', 'choices': ['chatgpt', 'gemini', 'claude']}
    },
    
    'ui': {
        'lang': {'type': 'string', 'choices': ['jp', 'en', 'fr', 'es']},
        'preferred_lang': {'type': 'string', 'choices': ['jp', 'en', 'fr', 'es']},
        'theme': {'type': 'string', 'choices': ['light', 'dark', 'auto']}
    }
}

def validate_session_data(category: str, data: dict) -> dict:
    """セッションデータの検証"""
    schema = SESSION_VALIDATION_SCHEMAS.get(category, {})
    errors = {}
    
    for field, value in data.items():
        if field in schema:
            field_schema = schema[field]
            validation_error = _validate_field(field, value, field_schema)
            if validation_error:
                errors[field] = validation_error
    
    return errors
```

---

## ⚠️ 3. エラーハンドリング統一規則

### 3.1 例外処理パターン

#### セッション例外階層
```python
class SessionError(Exception):
    """セッション関連エラーの基底クラス"""
    def __init__(self, message: str, category: str = None, session_id: str = None):
        super().__init__(message)
        self.category = category
        self.session_id = session_id
        self.timestamp = datetime.now().isoformat()

class SessionNotFoundError(SessionError):
    """セッションが見つからない"""
    pass

class SessionExpiredError(SessionError):
    """セッションが期限切れ"""
    pass

class SessionValidationError(SessionError):
    """セッションデータ検証エラー"""
    def __init__(self, message: str, validation_errors: dict, **kwargs):
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors

class SessionSecurityError(SessionError):
    """セッションセキュリティエラー"""
    pass

class RedisConnectionError(SessionError):
    """Redis接続エラー"""
    pass
```

#### エラーハンドリング統一パターン
```python
def handle_session_operation(operation_func):
    """セッション操作の統一エラーハンドリングデコレータ"""
    def wrapper(*args, **kwargs):
        try:
            return operation_func(*args, **kwargs)
        
        except RedisConnectionError as e:
            # Redis接続エラー → フォールバック
            logger.error(f"Redis connection failed: {e}")
            return _fallback_to_file_session(*args, **kwargs)
        
        except SessionValidationError as e:
            # 検証エラー → データクリーンアップ
            logger.warning(f"Session validation failed: {e}")
            _cleanup_invalid_session(e.session_id, e.category)
            raise
        
        except SessionExpiredError as e:
            # 期限切れ → 自動削除
            logger.info(f"Session expired: {e}")
            _remove_expired_session(e.session_id, e.category)
            raise
        
        except SessionSecurityError as e:
            # セキュリティエラー → 即座削除・ログ記録
            logger.critical(f"Session security violation: {e}")
            _emergency_session_cleanup(e.session_id)
            _log_security_incident(e)
            raise
        
        except Exception as e:
            # 未知のエラー → ログ記録・通知
            logger.error(f"Unexpected session error: {e}")
            _notify_admin_of_session_error(e)
            raise SessionError(f"Unexpected error: {str(e)}")
    
    return wrapper
```

### 3.2 ログ記録方針

#### 統一ログフォーマット
```python
SESSION_LOG_FORMAT = {
    'timestamp': 'ISO 8601 timestamp',
    'level': 'DEBUG|INFO|WARNING|ERROR|CRITICAL',
    'category': 'session category',
    'session_id': 'session identifier (masked)',
    'operation': 'operation type',
    'result': 'success|failure|partial',
    'duration_ms': 'operation duration',
    'error_code': 'error code if applicable',
    'message': 'human readable message'
}

# ログ例
{
    "timestamp": "2025-07-25T10:30:00Z",
    "level": "INFO",
    "category": "auth",
    "session_id": "abc123***",  # マスク済み
    "operation": "login",
    "result": "success",
    "duration_ms": 45,
    "message": "User login successful"
}
```

#### セキュリティログ
```python
SECURITY_LOG_EVENTS = {
    'session_created': 'INFO',
    'session_expired': 'INFO', 
    'invalid_csrf_token': 'WARNING',
    'session_hijack_attempt': 'CRITICAL',
    'multiple_login_attempts': 'WARNING',
    'session_data_corruption': 'ERROR'
}

def log_security_event(event_type: str, session_id: str, details: dict = None):
    """セキュリティイベントのログ記録"""
    level = SECURITY_LOG_EVENTS.get(event_type, 'INFO')
    
    security_logger.log(level, {
        'event_type': event_type,
        'session_id': mask_session_id(session_id),
        'timestamp': datetime.now().isoformat(),
        'details': details or {},
        'source_ip': request.remote_addr if request else 'unknown',
        'user_agent': request.headers.get('User-Agent', 'unknown') if request else 'unknown'
    })
```

---

## 📊 4. 監視・運用統一規則

### 4.1 メトリクス定義

#### セッション関連メトリクス
```python
SESSION_METRICS = {
    # パフォーマンスメトリクス
    'session_operation_duration': {
        'type': 'histogram',
        'unit': 'milliseconds',
        'labels': ['category', 'operation', 'result'],
        'description': 'セッション操作時間'
    },
    
    'session_cache_hit_rate': {
        'type': 'gauge',
        'unit': 'percentage',
        'labels': ['category', 'cache_type'],
        'description': 'セッションキャッシュヒット率'
    },
    
    # 使用量メトリクス
    'active_sessions_total': {
        'type': 'gauge',
        'unit': 'count',
        'labels': ['category', 'user_type'],
        'description': 'アクティブセッション数'
    },
    
    'session_operations_total': {
        'type': 'counter',
        'unit': 'count',
        'labels': ['category', 'operation', 'result'],
        'description': 'セッション操作回数'
    },
    
    # エラーメトリクス
    'session_errors_total': {
        'type': 'counter',
        'unit': 'count',
        'labels': ['category', 'error_type', 'severity'],
        'description': 'セッションエラー発生回数'
    },
    
    'session_security_violations_total': {
        'type': 'counter',
        'unit': 'count',
        'labels': ['violation_type', 'source_ip'],
        'description': 'セッションセキュリティ違反回数'
    }
}
```

#### メトリクス収集実装
```python
from prometheus_client import Counter, Histogram, Gauge

class SessionMetricsCollector:
    """セッションメトリクス収集器"""
    
    def __init__(self):
        # メトリクス初期化
        self.operation_duration = Histogram(
            'session_operation_duration_seconds',
            'Session operation duration',
            ['category', 'operation', 'result']
        )
        
        self.active_sessions = Gauge(
            'active_sessions_total',
            'Active sessions count',
            ['category', 'user_type']
        )
        
        self.operation_count = Counter(
            'session_operations_total',
            'Session operations count',
            ['category', 'operation', 'result']
        )
        
        self.error_count = Counter(
            'session_errors_total',
            'Session errors count',
            ['category', 'error_type', 'severity']
        )
    
    def record_operation(self, category: str, operation: str, duration: float, result: str):
        """セッション操作メトリクス記録"""
        self.operation_duration.labels(
            category=category,
            operation=operation,
            result=result
        ).observe(duration)
        
        self.operation_count.labels(
            category=category,
            operation=operation,
            result=result
        ).inc()
    
    def record_error(self, category: str, error_type: str, severity: str):
        """セッションエラーメトリクス記録"""
        self.error_count.labels(
            category=category,
            error_type=error_type,
            severity=severity
        ).inc()
```

### 4.2 アラート設定

#### アラート閾値
```python
ALERT_THRESHOLDS = {
    # パフォーマンスアラート
    'session_operation_slow': {
        'metric': 'session_operation_duration',
        'threshold': 0.5,  # 500ms
        'condition': 'greater_than',
        'severity': 'warning'
    },
    
    'session_cache_miss_high': {
        'metric': 'session_cache_hit_rate',
        'threshold': 0.8,  # 80%
        'condition': 'less_than',
        'severity': 'warning'
    },
    
    # セキュリティアラート
    'session_security_violation': {
        'metric': 'session_security_violations_total',
        'threshold': 1,
        'condition': 'greater_than_or_equal',
        'severity': 'critical'
    },
    
    'session_error_rate_high': {
        'metric': 'session_errors_total',
        'threshold': 10,  # 10回/分
        'condition': 'rate_greater_than',
        'timeframe': '1m',
        'severity': 'error'
    },
    
    # 容量アラート
    'active_sessions_high': {
        'metric': 'active_sessions_total',
        'threshold': 1000,
        'condition': 'greater_than',
        'severity': 'warning'
    }
}
```

### 4.3 ヘルスチェック

#### セッションシステムヘルスチェック
```python
class SessionHealthChecker:
    """セッションシステムの健全性チェック"""
    
    def __init__(self):
        self.checks = {
            'redis_connectivity': self._check_redis_connectivity,
            'session_operations': self._check_session_operations,
            'data_consistency': self._check_data_consistency,
            'security_status': self._check_security_status
        }
    
    def run_health_check(self) -> dict:
        """包括的ヘルスチェック実行"""
        results = {}
        overall_status = 'healthy'
        
        for check_name, check_func in self.checks.items():
            try:
                result = check_func()
                results[check_name] = result
                
                if result['status'] != 'healthy':
                    if result['severity'] == 'critical':
                        overall_status = 'unhealthy'
                    elif overall_status == 'healthy':
                        overall_status = 'degraded'
                        
            except Exception as e:
                results[check_name] = {
                    'status': 'error',
                    'message': str(e),
                    'severity': 'critical'
                }
                overall_status = 'unhealthy'
        
        return {
            'overall_status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'checks': results
        }
    
    def _check_redis_connectivity(self) -> dict:
        """Redis接続性チェック"""
        try:
            # Redis ping テスト
            response_time = time.time()
            redis_client.ping()
            response_time = (time.time() - response_time) * 1000
            
            if response_time > 100:  # 100ms以上
                return {
                    'status': 'degraded',
                    'message': f'Redis response slow: {response_time:.2f}ms',
                    'severity': 'warning'
                }
            
            return {
                'status': 'healthy',
                'message': f'Redis responsive: {response_time:.2f}ms',
                'severity': 'info'
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Redis connection failed: {str(e)}',
                'severity': 'critical'
            }
```

---

## ✅ セッション管理統一ポリシー完了確認

### 完了項目
- [x] **命名規則**: カテゴリ別統一命名体系策定
- [x] **データ型規則**: 6種類データ型の統一変換ルール
- [x] **エラーハンドリング**: 例外階層とハンドリングパターン設計
- [x] **ログ記録**: 統一ログフォーマットとセキュリティログ設計
- [x] **監視・運用**: メトリクス定義とアラート設定
- [x] **ヘルスチェック**: 包括的システム健全性監視設計

### 技術的成果
- **統一命名体系**: 6カテゴリの階層的命名規則
- **型安全性**: 自動型変換とバリデーション機能
- **エラー処理**: 5段階例外階層と統一ハンドリング
- **運用性**: メトリクス・ログ・アラートの完全統合

### ポリシー適用効果
- **保守性向上**: 統一規則による開発効率大幅向上
- **品質向上**: データ検証・エラーハンドリングの標準化
- **運用性向上**: 包括的監視・ログ・アラート体系
- **セキュリティ強化**: セキュリティログ・違反検知の自動化

**SL-1タスク完全完了**: 4つの成果物作成完了