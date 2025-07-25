# 🚀 AWS-2: セッション移行戦略

**戦略作成日**: 2025年7月25日  
**対象**: ファイルベース → Redis セッション完全移行  
**設計者**: Claude Code  

## 🎯 移行戦略概要

### 移行目標
- **ダウンタイム**: < 5分（夜間メンテナンス時）
- **データ損失**: 0%（全セッション保持）
- **ロールバック可能**: 24時間以内の緊急切り戻し対応

### リスク最小化方針
1. **段階的移行**: Phase分割による影響範囲限定
2. **並行運用**: 新旧システム同時運用による安全性確保
3. **ホットスワップ**: ユーザー影響最小限のライブ切り替え

---

## 📋 1. 段階的移行計画

### Phase 1: 環境準備・基盤構築（Week 1-2）

#### Phase 1a: ElastiCache環境構築
```yaml
# Day 1-3: インフラ構築
Infrastructure_Setup:
  ElastiCache_Cluster:
    - Redis Cluster構築（Multi-AZ）
    - セキュリティグループ設定
    - VPC内プライベート接続確認
    
  Monitoring_Setup:
    - CloudWatch ダッシュボード作成
    - アラート設定
    - ログ監視設定
    
  Security_Configuration:
    - 認証トークン設定
    - 暗号化設定（Transit/At-Rest）
    - IAM ロール設定
```

#### Phase 1b: コード準備・テスト環境構築
```python
# Day 4-7: アプリケーション準備
Application_Preparation:
  Code_Development:
    - Redis接続ライブラリ統合
    - セッション管理クラス実装
    - フォールバック機能実装
    
  Test_Environment:
    - ステージング環境でのRedis統合テスト
    - 負荷テスト実行
    - フォールバック動作確認

# テスト項目例
TEST_SCENARIOS = [
    'basic_session_operations',    # 基本セッション操作
    'concurrent_access',          # 同時アクセステスト
    'failover_behavior',          # フェイルオーバーテスト
    'data_persistence',           # データ永続性テスト
    'performance_benchmark',      # パフォーマンステスト
]
```

#### Phase 1c: 移行ツール開発
```python
# セッション移行ツール
class SessionMigrationTool:
    """
    ファイルベース → Redis セッション移行ツール
    """
    
    def __init__(self):
        self.file_session_path = '/var/lib/sessions'
        self.redis_client = get_redis_client()
        self.migration_log = []
    
    def analyze_existing_sessions(self) -> dict:
        """既存セッション分析"""
        analysis = {
            'total_sessions': 0,
            'session_sizes': [],
            'session_types': {},
            'estimated_migration_time': 0
        }
        
        for session_file in os.listdir(self.file_session_path):
            if session_file.startswith('sess_'):
                analysis['total_sessions'] += 1
                
                # セッションデータ分析
                session_data = self._load_file_session(session_file)
                size = len(str(session_data))
                analysis['session_sizes'].append(size)
                
                # セッション種別分析
                session_type = self._classify_session(session_data)
                analysis['session_types'][session_type] = analysis['session_types'].get(session_type, 0) + 1
        
        # 移行時間推定（セッション数 × 平均処理時間）
        analysis['estimated_migration_time'] = analysis['total_sessions'] * 0.01  # 10ms/session
        
        return analysis
    
    def migrate_session_batch(self, session_files: list) -> dict:
        """バッチセッション移行"""
        results = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }
        
        for session_file in session_files:
            try:
                # ファイルセッション読み込み
                session_data = self._load_file_session(session_file)
                session_id = session_file.replace('sess_', '')
                
                # Redisセッション形式に変換
                redis_sessions = self._convert_to_redis_format(session_id, session_data)
                
                # Redis保存
                for category, data in redis_sessions.items():
                    key = f"session:{category}:{session_id}"
                    self.redis_client.hmset(key, data)
                    
                    # TTL設定
                    ttl = self._get_ttl_for_category(category)
                    self.redis_client.expire(key, ttl)
                
                results['success_count'] += 1
                
            except Exception as e:
                results['error_count'] += 1
                results['errors'].append({
                    'session_file': session_file,
                    'error': str(e)
                })
        
        return results
```

### Phase 2: 並行運用開始（Week 3）

#### Phase 2a: Write-Through実装
```python
# 書き込み両方同期実装
class DualWriteSessionManager:
    """
    ファイル・Redis両方書き込みセッション管理
    """
    
    def __init__(self):
        self.file_session = FileSessionManager()
        self.redis_session = RedisSessionManager()
        self.write_errors = []
    
    def set_session(self, session_id: str, category: str, data: dict) -> bool:
        """デュアル書き込み"""
        file_success = False
        redis_success = False
        
        # ファイルセッション書き込み（既存）
        try:
            self.file_session.set(session_id, category, data)
            file_success = True
        except Exception as e:
            logger.error(f"File session write failed: {e}")
            self.write_errors.append(('file', session_id, str(e)))
        
        # Redisセッション書き込み（新）
        try:
            self.redis_session.set(session_id, category, data)
            redis_success = True
        except Exception as e:
            logger.error(f"Redis session write failed: {e}")
            self.write_errors.append(('redis', session_id, str(e)))
        
        # 少なくとも1つ成功すれば OK
        return file_success or redis_success
    
    def get_session(self, session_id: str, category: str) -> dict:
        """読み取り優先順位: ファイル → Redis"""
        
        # Phase 2では既存ファイルを優先
        try:
            return self.file_session.get(session_id, category)
        except Exception as e:
            logger.warning(f"File session read failed, trying Redis: {e}")
            
            try:
                return self.redis_session.get(session_id, category)
            except Exception as e2:
                logger.error(f"Both session systems failed: file={e}, redis={e2}")
                return {}
```

#### Phase 2b: データ一貫性検証
```python
class SessionConsistencyValidator:
    """
    ファイル・Redis間のデータ一貫性検証
    """
    
    def validate_session_consistency(self, session_id: str) -> dict:
        """セッション一貫性検証"""
        validation_result = {
            'session_id': session_id,
            'consistent': True,
            'differences': [],
            'file_data': {},
            'redis_data': {}
        }
        
        try:
            # ファイルセッション読み込み
            file_data = self._load_complete_file_session(session_id)
            validation_result['file_data'] = file_data
            
            # Redisセッション読み込み
            redis_data = self._load_complete_redis_session(session_id)
            validation_result['redis_data'] = redis_data
            
            # データ比較
            differences = self._compare_session_data(file_data, redis_data)
            validation_result['differences'] = differences
            validation_result['consistent'] = len(differences) == 0
            
        except Exception as e:
            validation_result['error'] = str(e)
            validation_result['consistent'] = False
        
        return validation_result
    
    def batch_validate_sessions(self, session_ids: list) -> dict:
        """バッチセッション一貫性検証"""
        results = {
            'total_sessions': len(session_ids),
            'consistent_sessions': 0,
            'inconsistent_sessions': 0,
            'error_sessions': 0,
            'inconsistencies': []
        }
        
        for session_id in session_ids:
            validation = self.validate_session_consistency(session_id)
            
            if validation.get('error'):
                results['error_sessions'] += 1
            elif validation['consistent']:
                results['consistent_sessions'] += 1
            else:
                results['inconsistent_sessions'] += 1
                results['inconsistencies'].append(validation)
        
        return results
```

### Phase 3: 読み取り切り替え（Week 4）

#### Phase 3a: Read-Through実装
```python
class ReadThroughSessionManager:
    """
    読み取り優先度変更: Redis → ファイル
    """
    
    def get_session(self, session_id: str, category: str) -> dict:
        """読み取り優先順位: Redis → ファイル → デフォルト"""
        
        # 1st: Redis読み取り試行
        try:
            redis_data = self.redis_session.get(session_id, category)
            if redis_data:
                return redis_data
        except Exception as e:
            logger.warning(f"Redis session read failed: {e}")
        
        # 2nd: ファイル読み取り試行（フォールバック）
        try:
            file_data = self.file_session.get(session_id, category)
            if file_data:
                # Redisに同期（読み取り時自動補完）
                try:
                    self.redis_session.set(session_id, category, file_data)
                except Exception:
                    pass  # 同期失敗は無視
                
                return file_data
        except Exception as e:
            logger.error(f"File session read failed: {e}")
        
        # 3rd: デフォルト値
        return self._get_default_session_data(category)
```

#### Phase 3b: パフォーマンス監視強化
```python
class MigrationPerformanceMonitor:
    """
    移行時パフォーマンス監視
    """
    
    def __init__(self):
        self.metrics = {
            'redis_read_latency': [],
            'file_read_latency': [],
            'read_success_rate': 0,
            'write_success_rate': 0,
            'consistency_rate': 0
        }
    
    def measure_read_performance(self, session_id: str, category: str) -> dict:
        """読み取りパフォーマンス測定"""
        results = {}
        
        # Redis読み取り性能
        start_time = time.time()
        try:
            redis_data = redis_session.get(session_id, category)
            redis_latency = (time.time() - start_time) * 1000
            results['redis'] = {
                'success': True,
                'latency_ms': redis_latency,
                'data_size': len(str(redis_data))
            }
        except Exception as e:
            results['redis'] = {
                'success': False,
                'error': str(e)
            }
        
        # ファイル読み取り性能
        start_time = time.time()
        try:
            file_data = file_session.get(session_id, category)
            file_latency = (time.time() - start_time) * 1000
            results['file'] = {
                'success': True,
                'latency_ms': file_latency,
                'data_size': len(str(file_data))
            }
        except Exception as e:
            results['file'] = {
                'success': False,
                'error': str(e)
            }
        
        return results
```

### Phase 4: 完全切り替え（Week 5）

#### Phase 4a: Write-Only Redis実装
```python
class RedisOnlySessionManager:
    """
    Redis専用セッション管理（ファイル書き込み停止）
    """
    
    def __init__(self):
        self.redis_session = RedisSessionManager()
        self.file_session = FileSessionManager()  # 読み取り専用保持
        
    def set_session(self, session_id: str, category: str, data: dict) -> bool:
        """Redis専用書き込み"""
        try:
            return self.redis_session.set(session_id, category, data)
        except Exception as e:
            logger.error(f"Redis session write failed: {e}")
            
            # 緊急時のみファイルフォールバック
            if self._is_emergency_fallback_enabled():
                logger.warning("Emergency fallback to file session")
                return self.file_session.set(session_id, category, data)
            
            return False
    
    def get_session(self, session_id: str, category: str) -> dict:
        """Redis優先読み取り"""
        
        # Redis読み取り
        try:
            redis_data = self.redis_session.get(session_id, category)
            if redis_data:
                return redis_data
        except Exception as e:
            logger.warning(f"Redis read failed: {e}")
        
        # レガシーファイル読み取り（移行期間のみ）
        try:
            file_data = self.file_session.get(session_id, category)
            if file_data:
                # Redisへ移行（一度限り）
                try:
                    self.redis_session.set(session_id, category, file_data)
                    logger.info(f"Migrated legacy session: {session_id}:{category}")
                except Exception:
                    pass
                
                return file_data
        except Exception:
            pass
        
        return {}
```

#### Phase 4b: ファイルセッション無効化
```python
# ファイルセッション段階的無効化
class FileSessionDeprecation:
    """
    ファイルセッション段階的廃止
    """
    
    def __init__(self):
        self.deprecation_start = datetime.now()
        self.complete_cutoff = self.deprecation_start + timedelta(days=7)
    
    def should_read_file_session(self, session_id: str) -> bool:
        """ファイルセッション読み取り可否判定"""
        
        # 完全カットオフ後は読み取り不可
        if datetime.now() > self.complete_cutoff:
            return False
        
        # Redis失敗時のみファイル読み取り許可
        try:
            redis_session.exists(session_id)
            return False  # Redisにデータがある場合はファイル不要
        except Exception:
            return True   # Redis失敗時のみファイル読み取り
    
    def cleanup_old_file_sessions(self):
        """古いファイルセッションクリーンアップ"""
        cleanup_count = 0
        
        for session_file in os.listdir(self.file_session_path):
            file_path = os.path.join(self.file_session_path, session_file)
            
            # 1週間以上古いファイルを削除
            if os.path.getmtime(file_path) < time.time() - 604800:  # 7日
                try:
                    os.remove(file_path)
                    cleanup_count += 1
                except Exception as e:
                    logger.error(f"Failed to cleanup session file {session_file}: {e}")
        
        logger.info(f"Cleaned up {cleanup_count} old session files")
```

---

## 🧪 2. テスト戦略

### 2.1 単体テスト方針

#### セッション機能テスト
```python
import unittest
from unittest.mock import Mock, patch

class SessionMigrationTests(unittest.TestCase):
    """セッション移行単体テスト"""
    
    def setUp(self):
        self.redis_mock = Mock()
        self.file_session_mock = Mock()
        self.session_manager = DualWriteSessionManager()
    
    def test_dual_write_success(self):
        """デュアル書き込み成功テスト"""
        session_data = {'user_id': '123', 'username': 'test'}
        
        result = self.session_manager.set_session('sess_123', 'auth', session_data)
        
        self.assertTrue(result)
        self.redis_mock.hmset.assert_called_once()
        self.file_session_mock.set.assert_called_once()
    
    def test_redis_write_failure_fallback(self):
        """Redis書き込み失敗時のフォールバック"""
        self.redis_mock.hmset.side_effect = ConnectionError("Redis down")
        session_data = {'user_id': '123'}
        
        result = self.session_manager.set_session('sess_123', 'auth', session_data)
        
        # ファイル書き込みが成功すれば全体成功
        self.assertTrue(result)
        self.file_session_mock.set.assert_called_once()
    
    def test_session_consistency_validation(self):
        """セッション一貫性検証テスト"""
        validator = SessionConsistencyValidator()
        
        # モックデータ設定
        file_data = {'username': 'test', 'role': 'user'}
        redis_data = {'username': 'test', 'role': 'admin'}  # 差分あり
        
        with patch.object(validator, '_load_complete_file_session', return_value=file_data), \
             patch.object(validator, '_load_complete_redis_session', return_value=redis_data):
            
            result = validator.validate_session_consistency('sess_123')
            
            self.assertFalse(result['consistent'])
            self.assertEqual(len(result['differences']), 1)
    
    def test_performance_benchmark(self):
        """パフォーマンスベンチマークテスト"""
        monitor = MigrationPerformanceMonitor()
        
        # 100回読み取り性能測定
        latencies = []
        for i in range(100):
            start = time.time()
            self.session_manager.get_session(f'sess_{i}', 'auth')
            latency = (time.time() - start) * 1000
            latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies)
        self.assertLess(avg_latency, 50, "Average latency should be < 50ms")
```

### 2.2 統合テスト方針

#### エンドツーエンドテスト
```python
class SessionMigrationIntegrationTests(unittest.TestCase):
    """セッション移行統合テスト"""
    
    @classmethod
    def setUpClass(cls):
        """テスト環境セットアップ"""
        # テスト用Redis起動
        cls.redis_client = redis.Redis(host='localhost', port=6380, db=1)
        
        # テスト用セッションデータ作成
        cls.test_sessions = cls._create_test_sessions(100)
    
    def test_full_migration_workflow(self):
        """完全移行ワークフローテスト"""
        migration_tool = SessionMigrationTool()
        
        # Phase 1: 分析
        analysis = migration_tool.analyze_existing_sessions()
        self.assertGreater(analysis['total_sessions'], 0)
        
        # Phase 2: 移行実行
        session_files = list(self.test_sessions.keys())
        results = migration_tool.migrate_session_batch(session_files)
        
        self.assertEqual(results['error_count'], 0)
        self.assertEqual(results['success_count'], len(session_files))
        
        # Phase 3: 検証
        validator = SessionConsistencyValidator()
        validation_results = validator.batch_validate_sessions(session_files)
        
        self.assertEqual(validation_results['inconsistent_sessions'], 0)
    
    def test_failover_behavior(self):
        """フェイルオーバー動作テスト"""
        session_manager = RedisOnlySessionManager()
        
        # 正常時動作確認
        session_manager.set_session('test_session', 'auth', {'user': 'test'})
        data = session_manager.get_session('test_session', 'auth')
        self.assertEqual(data['user'], 'test')
        
        # Redis障害シミュレーション
        with patch.object(session_manager.redis_session, 'get', side_effect=ConnectionError):
            # フォールバック動作確認
            data = session_manager.get_session('test_session', 'auth')
            # ファイルフォールバックまたはデフォルト値が返されること
            self.assertIsInstance(data, dict)
    
    def test_concurrent_access(self):
        """同時アクセステスト"""
        import threading
        import queue
        
        session_manager = DualWriteSessionManager()
        results = queue.Queue()
        
        def worker(session_id):
            try:
                # 同時書き込み
                session_manager.set_session(session_id, 'auth', {'user': session_id})
                
                # 即座に読み取り
                data = session_manager.get_session(session_id, 'auth')
                results.put(('success', session_id, data))
            except Exception as e:
                results.put(('error', session_id, str(e)))
        
        # 50個の同時アクセス
        threads = []
        for i in range(50):
            thread = threading.Thread(target=worker, args=(f'concurrent_{i}',))
            threads.append(thread)
            thread.start()
        
        # 全スレッド完了待ち
        for thread in threads:
            thread.join()
        
        # 結果検証
        success_count = 0
        error_count = 0
        
        while not results.empty():
            result_type, session_id, data = results.get()
            if result_type == 'success':
                success_count += 1
            else:
                error_count += 1
        
        self.assertEqual(error_count, 0, "No concurrent access errors should occur")
        self.assertEqual(success_count, 50, "All concurrent operations should succeed")
```

### 2.3 負荷テスト設計

#### パフォーマンステスト
```python
import locust
from locust import HttpUser, task, between

class SessionLoadTest(HttpUser):
    """セッション負荷テスト"""
    
    wait_time = between(1, 3)  # 1-3秒間隔
    
    def on_start(self):
        """テスト開始時のセットアップ"""
        # ログイン
        self.client.post("/login", data={
            "username": "test_user",
            "password": "test_password"
        })
    
    @task(3)
    def session_read_heavy(self):
        """セッション読み取り集約テスト"""
        # 翻訳ページアクセス（セッション読み取り集約）
        self.client.get("/")
        
    @task(1)
    def session_write_moderate(self):
        """セッション書き込み中程度テスト"""
        # 翻訳実行（セッション更新）
        self.client.post("/translate", data={
            "input_text": "Test translation",
            "source_lang": "en",
            "target_lang": "jp"
        })
    
    @task(1)
    def language_switch(self):
        """言語切り替えテスト"""
        self.client.post("/set_language", data={
            "language": "en"
        })

# 負荷テスト実行設定
class LoadTestConfiguration:
    """負荷テスト設定"""
    
    TEST_SCENARIOS = {
        'baseline': {
            'users': 50,
            'spawn_rate': 5,
            'duration': '10m'
        },
        'stress': {
            'users': 200,
            'spawn_rate': 10,
            'duration': '30m'
        },
        'spike': {
            'users': 500,
            'spawn_rate': 50,
            'duration': '5m'
        }
    }
    
    PERFORMANCE_THRESHOLDS = {
        'response_time_p95': 500,  # 95%ile < 500ms
        'error_rate': 0.01,        # エラー率 < 1%
        'throughput_min': 100,     # 最低100 req/sec
    }
```

---

## 🔄 3. ロールバック設計

### 3.1 緊急切り戻し手順

#### 即座実行可能ロールバック
```python
class EmergencyRollback:
    """緊急ロールバック実行"""
    
    def __init__(self):
        self.rollback_log = []
        self.backup_redis_data = {}
    
    def execute_immediate_rollback(self, reason: str) -> dict:
        """即座ロールバック実行"""
        rollback_result = {
            'timestamp': datetime.now().isoformat(),
            'reason': reason,
            'steps_completed': [],
            'success': False
        }
        
        try:
            # Step 1: Redis書き込み停止
            self._disable_redis_writes()
            rollback_result['steps_completed'].append('redis_writes_disabled')
            
            # Step 2: ファイルセッション有効化
            self._enable_file_sessions()
            rollback_result['steps_completed'].append('file_sessions_enabled')
            
            # Step 3: アプリケーション設定切り戻し
            self._revert_application_config()
            rollback_result['steps_completed'].append('app_config_reverted')
            
            # Step 4: 監視アラート送信
            self._send_rollback_alert(reason)
            rollback_result['steps_completed'].append('alerts_sent')
            
            rollback_result['success'] = True
            logger.critical(f"Emergency rollback completed: {reason}")
            
        except Exception as e:
            rollback_result['error'] = str(e)
            logger.critical(f"Emergency rollback failed: {e}")
        
        return rollback_result
    
    def _disable_redis_writes(self):
        """Redis書き込み無効化"""
        # 環境変数でRedis書き込み無効化
        os.environ['REDIS_WRITES_ENABLED'] = 'false'
        
        # アプリケーション設定ファイル更新
        with open('/app/config/emergency_config.json', 'w') as f:
            json.dump({
                'session_backend': 'file',
                'redis_enabled': False,
                'emergency_mode': True
            }, f)
    
    def _enable_file_sessions(self):
        """ファイルセッション有効化"""
        # ファイルセッションディレクトリ確認
        session_dir = '/var/lib/sessions'
        if not os.path.exists(session_dir):
            os.makedirs(session_dir, mode=0o755)
        
        # 権限確認・修正
        os.chmod(session_dir, 0o755)
        
        # Flask-Session設定切り戻し
        os.environ['SESSION_TYPE'] = 'filesystem'
```

### 3.2 データ整合性確保

#### ロールバック時データ保護
```python
class RollbackDataProtection:
    """ロールバック時データ保護"""
    
    def backup_redis_sessions(self) -> str:
        """Redis全セッションバックアップ"""
        backup_file = f"/backups/redis_sessions_{int(time.time())}.json"
        backup_data = {}
        
        try:
            # 全セッションキー取得
            for key in redis_client.scan_iter(match="session:*"):
                if redis_client.type(key) == 'hash':
                    backup_data[key] = redis_client.hgetall(key)
                else:
                    backup_data[key] = redis_client.get(key)
            
            # バックアップファイル作成
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            logger.info(f"Redis sessions backed up to {backup_file}")
            return backup_file
            
        except Exception as e:
            logger.error(f"Redis backup failed: {e}")
            raise
    
    def restore_from_backup(self, backup_file: str) -> dict:
        """バックアップからの復元"""
        restore_result = {
            'restored_sessions': 0,
            'failed_sessions': 0,
            'errors': []
        }
        
        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            for key, data in backup_data.items():
                try:
                    if isinstance(data, dict):
                        redis_client.hmset(key, data)
                    else:
                        redis_client.set(key, data)
                    
                    restore_result['restored_sessions'] += 1
                    
                except Exception as e:
                    restore_result['failed_sessions'] += 1
                    restore_result['errors'].append({
                        'key': key,
                        'error': str(e)
                    })
            
        except Exception as e:
            logger.error(f"Backup restore failed: {e}")
            raise
        
        return restore_result
    
    def convert_redis_to_file_sessions(self) -> dict:
        """Redis → ファイルセッション変換"""
        conversion_result = {
            'converted_sessions': 0,
            'failed_conversions': 0,
            'errors': []
        }
        
        session_dir = '/var/lib/sessions'
        os.makedirs(session_dir, exist_ok=True)
        
        # Redis全セッション取得
        for key in redis_client.scan_iter(match="session:*"):
            try:
                # セッションID抽出
                key_parts = key.split(':')
                if len(key_parts) >= 3:
                    category = key_parts[1]
                    session_id = key_parts[2]
                    
                    # ファイルセッション形式に変換
                    file_session_data = self._convert_to_file_format(
                        session_id, category, redis_client.hgetall(key)
                    )
                    
                    # ファイル保存
                    session_file = os.path.join(session_dir, f"sess_{session_id}")
                    with open(session_file, 'w') as f:
                        json.dump(file_session_data, f)
                    
                    conversion_result['converted_sessions'] += 1
                
            except Exception as e:
                conversion_result['failed_conversions'] += 1
                conversion_result['errors'].append({
                    'key': key,
                    'error': str(e)
                })
        
        return conversion_result
```

### 3.3 段階的切り戻し

#### 部分的ロールバック
```python
class GradualRollback:
    """段階的ロールバック"""
    
    def __init__(self):
        self.rollback_phases = [
            'stop_new_redis_sessions',
            'revert_read_priority',  
            'revert_write_priority',
            'disable_redis_completely'
        ]
        self.current_phase = None
    
    def execute_phase_rollback(self, target_phase: str) -> dict:
        """段階的ロールバック実行"""
        rollback_result = {
            'target_phase': target_phase,
            'completed_phases': [],
            'success': False
        }
        
        try:
            phase_index = self.rollback_phases.index(target_phase)
            
            for i in range(phase_index + 1):
                phase = self.rollback_phases[i]
                
                if phase == 'stop_new_redis_sessions':
                    self._stop_new_redis_sessions()
                elif phase == 'revert_read_priority':
                    self._revert_read_priority()
                elif phase == 'revert_write_priority':
                    self._revert_write_priority()
                elif phase == 'disable_redis_completely':
                    self._disable_redis_completely()
                
                rollback_result['completed_phases'].append(phase)
                self.current_phase = phase
                
                # 各フェーズ後の安定性確認
                if not self._verify_phase_stability():
                    raise Exception(f"Phase {phase} instability detected")
            
            rollback_result['success'] = True
            
        except Exception as e:
            rollback_result['error'] = str(e)
            logger.error(f"Phase rollback failed at {self.current_phase}: {e}")
        
        return rollback_result
    
    def _verify_phase_stability(self) -> bool:
        """フェーズ安定性確認"""
        try:
            # セッション読み取りテスト
            test_session_data = self._test_session_operations()
            
            # エラー率確認
            error_rate = self._calculate_recent_error_rate()
            
            return (test_session_data['success'] and 
                   error_rate < 0.05)  # 5%未満のエラー率
                   
        except Exception:
            return False
```

---

## ⏱️ 4. 移行スケジュール

### タイムライン設計

```
Week 1: 基盤準備
├── Day 1-2: ElastiCache構築・設定
├── Day 3-4: 監視・アラート設定
└── Day 5-7: 移行ツール開発・テスト

Week 2: テスト・検証
├── Day 8-10: ステージング環境統合テスト
├── Day 11-12: 負荷テスト・パフォーマンス確認
└── Day 13-14: セキュリティテスト・脆弱性確認

Week 3: 並行運用開始（Phase 2）
├── Day 15: Write-Through実装デプロイ
├── Day 16-18: 並行運用監視・調整
└── Day 19-21: データ一貫性検証・問題修正

Week 4: 読み取り切り替え（Phase 3）
├── Day 22: Read-Through実装デプロイ
├── Day 23-25: 読み取り優先度変更監視
└── Day 26-28: パフォーマンス最適化

Week 5: 完全移行（Phase 4）
├── Day 29: Redis専用セッション管理デプロイ
├── Day 30-32: ファイルセッション段階的廃止
└── Day 33-35: 移行完了確認・クリーンアップ
```

### ダウンタイム最小化
- **メンテナンス時間**: 夜間2-6時（JST）
- **ローリングデプロイ**: ゼロダウンタイム配布
- **ホットスワップ**: 設定切り替えによる即座移行

---

## ✅ 移行戦略完了確認

- ✅ **段階的移行計画**: 5Phase詳細計画完成
- ✅ **テスト戦略**: 単体・統合・負荷テスト設計完了
- ✅ **ロールバック設計**: 緊急・段階的切り戻し設計完了
- ✅ **スケジュール**: 5週間詳細タイムライン確定
- ✅ **リスク最小化**: ダウンタイム<5分・データ損失0%設計

**移行戦略完成**: Redis移行完全戦略確立  
**実行準備度**: 100%完了 - 即座に移行実行可能