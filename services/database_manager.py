# DATABASE_MANAGER_v3.0
# 
# 目的: 全てのDB/Redis接続を統一管理し、相対パス・機密情報ハードコードを根絶
# 適用範囲: PostgreSQL/RDS, Redis, SQLite(移行期間中の互換性維持)
# セキュリティ: AWS Secrets Manager/SSM統合、sslmode=require強制

import os
import json
import logging
from typing import Dict, Any, Optional, Union
from urllib.parse import urlparse
import sqlite3
from pathlib import Path

# 条件付きインポート（本番環境でのみ必須）
try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    
try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    DATABASE_MANAGER_v3.0準拠のデータベース接続統一管理
    
    設計原則:
    1. 全接続文字列の環境変数化（相対パス撤廃）
    2. AWS Secrets Manager/SSM統合
    3. sslmode=require強制
    4. 本番/検証/開発環境での誤接続防止
    5. 機密情報のコード/ログ流出防止
    """
    
    def __init__(self, environment: str = None):
        """
        初期化
        
        Args:
            environment: 環境識別子 (development/staging/production)
        """
        self.environment = environment or os.getenv('ENVIRONMENT', 'development')
        self.logger = logging.getLogger(f"{__name__}.{self.environment}")
        
        # 接続プール管理
        self._postgres_pool = None
        self._redis_pool = None
        self._secrets_cache = {}
        
        # AWS Secrets Manager クライアント（本番環境のみ）
        self._secrets_client = None
        self._ssm_client = None
        
        if self.environment in ['staging', 'production']:
            if not BOTO3_AVAILABLE:
                raise ImportError("boto3 is required for staging/production environments")
                
            try:
                self._secrets_client = boto3.client('secretsmanager')
                self._ssm_client = boto3.client('ssm')
                self.logger.info("✅ AWS Secrets Manager/SSM clients initialized")
            except Exception as e:
                self.logger.error(f"❌ AWS clients initialization failed: {e}")
                raise
        else:
            # 開発環境では AWS クライアント不要
            if not BOTO3_AVAILABLE:
                self.logger.info("ℹ️ boto3 not available - OK for development environment")
                
        self.logger.info(f"🔧 DatabaseManager initialized for environment: {self.environment}")
    
    def get_secret(self, secret_name: str, default: str = None) -> str:
        """
        AWS Secrets Manager/SSM から機密情報を安全取得
        
        Args:
            secret_name: シークレット名（環境プレフィックス自動付与）
            default: フォールバック値（開発環境用）
            
        Returns:
            str: 取得した機密情報
            
        Raises:
            ValueError: 本番環境でシークレット取得失敗時
        """
        # キャッシュ確認
        cache_key = f"{self.environment}:{secret_name}"
        if cache_key in self._secrets_cache:
            return self._secrets_cache[cache_key]
            
        # 環境別シークレット名
        env_secret_name = f"langpont/{self.environment}/{secret_name}"
        
        try:
            if self.environment == 'development':
                # 開発環境: 環境変数またはデフォルト値
                value = os.getenv(secret_name.upper(), default)
                if not value:
                    raise ValueError(f"Development secret not found: {secret_name}")
                    
            elif self.environment in ['staging', 'production']:
                # 本番環境: AWS Secrets Manager優先、SSMフォールバック
                try:
                    response = self._secrets_client.get_secret_value(SecretId=env_secret_name)
                    secret_data = json.loads(response['SecretString'])
                    value = secret_data.get(secret_name)
                    
                    if not value:
                        raise KeyError(f"Key {secret_name} not found in secret")
                        
                except Exception as secrets_error:
                    self.logger.warning(f"Secrets Manager failed, trying SSM: {secrets_error}")
                    
                    # SSM Parameter Store フォールバック
                    response = self._ssm_client.get_parameter(
                        Name=env_secret_name,
                        WithDecryption=True
                    )
                    value = response['Parameter']['Value']
                    
            else:
                raise ValueError(f"Unsupported environment: {self.environment}")
                
            # キャッシュに保存（ログには絶対に出力しない）
            self._secrets_cache[cache_key] = value
            self.logger.info(f"✅ Secret retrieved: {secret_name} (length: {len(value) if value else 0})")
            
            return value
            
        except Exception as e:
            error_msg = f"❌ Failed to retrieve secret '{secret_name}' for environment '{self.environment}': {e}"
            self.logger.error(error_msg)
            
            if self.environment in ['staging', 'production']:
                # 本番環境では必須
                raise ValueError(error_msg)
            elif default:
                # 開発環境ではデフォルト値で継続
                self.logger.warning(f"⚠️ Using default value for {secret_name}")
                return default
            else:
                raise ValueError(error_msg)
    
    def get_postgres_dsn(self) -> str:
        """
        PostgreSQL/RDS接続文字列を環境別に取得
        優先順: DATABASE_URL → POSTGRES_* 個別パラメータ（後方互換）
        
        Returns:
            str: PostgreSQL DSN (sslmode=require強制)
            
        Raises:
            RuntimeError: sslmode=require が本番環境で無い場合
        """
        try:
            # 第一優先: DATABASE_URL
            dsn = os.getenv('DATABASE_URL')
            
            if dsn:
                # DATABASE_URL が提供済みの場合、sslmode=require を検証
                parsed = urlparse(dsn)
                if self.environment in ['staging', 'production']:
                    if 'sslmode=require' not in dsn:
                        raise RuntimeError(f"DATABASE_URL must include sslmode=require in {self.environment}")
                
                # ログには機密情報を含めない
                safe_dsn = dsn.replace(f':{parsed.password}@', ':***@') if parsed.password else dsn
                self.logger.info(f"✅ PostgreSQL DSN from DATABASE_URL: {safe_dsn}")
                return dsn
            
            # 第二優先: 後方互換として個別パラメータから DSN 構築
            self.logger.info("ℹ️ DATABASE_URL not found, using POSTGRES_* (backward compatibility)")
            
            if self.environment == 'development':
                # 開発環境: 環境変数またはローカルPostgreSQL
                host = os.getenv('POSTGRES_HOST', 'localhost')
                port = os.getenv('POSTGRES_PORT', '5432')
                database = os.getenv('POSTGRES_DB', 'langpont_dev')
                username = os.getenv('POSTGRES_USER', 'langpont_dev')
                password = os.getenv('POSTGRES_PASSWORD', 'dev_password_123')
                
            else:
                # 本番環境: AWS Secrets Manager から取得
                host = self.get_secret('postgres_host')
                port = self.get_secret('postgres_port', 'localhost')
                database = self.get_secret('postgres_database', 'langpont')
                username = self.get_secret('postgres_username') 
                password = self.get_secret('postgres_password')
                
            # sslmode=require を強制（セキュリティ要件）
            if self.environment in ['staging', 'production']:
                sslmode = 'require'
            else:
                sslmode = 'prefer'
            
            dsn = f"postgresql://{username}:{password}@{host}:{port}/{database}?sslmode={sslmode}"
            
            # ログには機密情報を含めない
            safe_dsn = f"postgresql://***@{host}:{port}/{database}?sslmode={sslmode}"
            self.logger.info(f"✅ PostgreSQL DSN constructed from POSTGRES_*: {safe_dsn}")
            
            return dsn
            
        except Exception as e:
            self.logger.error(f"❌ PostgreSQL DSN construction failed: {e}")
            raise
    
    def get_redis_dsn(self) -> str:
        """
        Redis接続文字列を環境別に取得
        優先順: REDIS_URL → REDIS_* 個別パラメータ（後方互換）
        
        Returns:
            str: Redis DSN (rediss:// 強制)
            
        Raises:
            RuntimeError: rediss:// 以外のスキーム使用時（Fail Fast）
        """
        try:
            # 第一優先: REDIS_URL
            dsn = os.getenv('REDIS_URL')
            
            if dsn:
                # REDIS_URL が提供済みの場合、rediss:// を強制
                if not dsn.startswith('rediss://'):
                    raise RuntimeError(f"REDIS_URL must use rediss:// scheme (TLS required), got: {dsn.split('://')[0] if '://' in dsn else 'invalid'}")
                
                # ログには機密情報を含めない
                parsed = urlparse(dsn)
                safe_dsn = dsn.replace(f':{parsed.password}@', ':***@') if parsed.password else dsn
                self.logger.info(f"✅ Redis DSN from REDIS_URL: {safe_dsn}")
                return dsn
            
            # 第二優先: 後方互換として個別パラメータから DSN 構築（rediss:// 強制）
            self.logger.info("ℹ️ REDIS_URL not found, using REDIS_* (backward compatibility)")
            
            if self.environment == 'development':
                # 開発環境でも rediss:// 強制（セキュリティ要件）
                self.logger.warning("⚠️ Development environment: using rediss:// (TLS required)")
                scheme = 'rediss'
                host = os.getenv('REDIS_HOST', 'localhost')
                port = os.getenv('REDIS_PORT', '6379')
                password = os.getenv('REDIS_PASSWORD', '')
                db = os.getenv('REDIS_DB', '0')
                
            else:
                # 本番環境: AWS Secrets Manager から取得
                scheme = 'rediss'  # TLS必須
                host = self.get_secret('redis_host')
                port = self.get_secret('redis_port', '6379') 
                password = self.get_secret('redis_password', '')
                db = self.get_secret('redis_db', '0')
                
            # rediss:// DSN 構築
            if password:
                dsn = f"{scheme}://:{password}@{host}:{port}/{db}"
                safe_dsn = f"{scheme}://:***@{host}:{port}/{db}"
            else:
                dsn = f"{scheme}://{host}:{port}/{db}"
                safe_dsn = dsn
                
            self.logger.info(f"✅ Redis DSN constructed from REDIS_* (TLS enforced): {safe_dsn}")
            return dsn
            
        except Exception as e:
            self.logger.error(f"❌ Redis DSN construction failed: {e}")
            raise
    
    def get_postgres_connection(self):
        """
        PostgreSQL接続を取得（接続プール対応）
        
        Returns:
            psycopg2.connection: PostgreSQL接続
        """
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("psycopg2 is required for PostgreSQL connections")
            
        try:
            dsn = self.get_postgres_dsn()
            
            # 接続テスト付きで接続作成
            conn = psycopg2.connect(dsn)
            conn.autocommit = False
            
            # 接続確認
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                
            self.logger.info("✅ PostgreSQL connection established")
            return conn
            
        except Exception as e:
            self.logger.error(f"❌ PostgreSQL connection failed: {e}")
            raise
    
    def get_redis_connection(self):
        """
        Redis接続を取得（接続プール対応）
        
        Returns:
            redis.Redis: Redis接続
        """
        if not REDIS_AVAILABLE:
            raise ImportError("redis is required for Redis connections")
            
        try:
            dsn = self.get_redis_dsn()
            
            # Redis接続作成
            redis_client = redis.from_url(dsn, decode_responses=True)
            
            # 接続確認
            redis_client.ping()
            
            self.logger.info("✅ Redis connection established")
            return redis_client
            
        except Exception as e:
            self.logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    def get_sqlite_path(self, db_name: str) -> str:
        """
        SQLite データベースファイルパスを取得（移行期間中の互換性維持）
        
        Args:
            db_name: データベース名 (例: 'users', 'history', 'analytics')
            
        Returns:
            str: 絶対パス
            
        Note:
            相対パス撤廃 - 環境変数SQLITE_BASE_PATHで基準ディレクトリ指定
        """
        try:
            # 基準ディレクトリを環境変数から取得
            base_path = os.getenv('SQLITE_BASE_PATH')
            
            if not base_path:
                if self.environment == 'development':
                    # 開発環境: プロジェクトルート/data
                    base_path = os.path.join(os.path.dirname(__file__), '..', 'data')
                else:
                    # 本番環境: 専用ディレクトリ
                    base_path = '/opt/langpont/data'
                    
            # ディレクトリ作成
            Path(base_path).mkdir(parents=True, exist_ok=True)
            
            # データベースファイル名マッピング
            db_mapping = {
                'users': 'langpont_users.db',
                'history': 'langpont_translation_history.db', 
                'analytics': 'langpont_analytics.db',
                'activity': 'langpont_activity_log.db'
            }
            
            filename = db_mapping.get(db_name, f'langpont_{db_name}.db')
            full_path = os.path.join(base_path, filename)
            
            self.logger.info(f"✅ SQLite path resolved: {db_name} -> {full_path}")
            return full_path
            
        except Exception as e:
            self.logger.error(f"❌ SQLite path resolution failed for {db_name}: {e}")
            raise
    
    def get_sqlite_connection(self, db_name: str):
        """
        SQLite接続を取得（移行期間中の互換性維持）
        
        Args:
            db_name: データベース名
            
        Returns:
            sqlite3.Connection: SQLite接続
        """
        try:
            db_path = self.get_sqlite_path(db_name)
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # 辞書形式での結果取得
            
            self.logger.info(f"✅ SQLite connection established: {db_name}")
            return conn
            
        except Exception as e:
            self.logger.error(f"❌ SQLite connection failed for {db_name}: {e}")
            raise
    
    def validate_connections(self) -> Dict[str, Any]:
        """
        全接続の検証テスト
        
        Returns:
            Dict[str, Any]: 検証結果レポート
        """
        results = {
            'environment': self.environment,
            'timestamp': logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None)),
            'tests': {}
        }
        
        # PostgreSQL接続テスト
        if PSYCOPG2_AVAILABLE:
            try:
                conn = self.get_postgres_connection()
                conn.close()
                results['tests']['postgresql'] = {'status': 'SUCCESS', 'error': None}
            except Exception as e:
                results['tests']['postgresql'] = {'status': 'FAILED', 'error': str(e)}
        else:
            results['tests']['postgresql'] = {'status': 'SKIPPED', 'error': 'psycopg2 not available'}
        
        # Redis接続テスト
        if REDIS_AVAILABLE:
            try:
                client = self.get_redis_connection()
                client.close()
                results['tests']['redis'] = {'status': 'SUCCESS', 'error': None}
            except Exception as e:
                results['tests']['redis'] = {'status': 'FAILED', 'error': str(e)}
        else:
            results['tests']['redis'] = {'status': 'SKIPPED', 'error': 'redis not available'}
        
        # SQLite接続テスト（開発環境のみ）
        if self.environment == 'development':
            for db_name in ['users', 'history', 'analytics']:
                try:
                    conn = self.get_sqlite_connection(db_name)
                    conn.close()
                    results['tests'][f'sqlite_{db_name}'] = {'status': 'SUCCESS', 'error': None}
                except Exception as e:
                    results['tests'][f'sqlite_{db_name}'] = {'status': 'FAILED', 'error': str(e)}
        
        # 全体成功率計算
        total_tests = len(results['tests'])
        successful_tests = sum(1 for test in results['tests'].values() if test['status'] == 'SUCCESS')
        results['success_rate'] = successful_tests / total_tests if total_tests > 0 else 0
        
        self.logger.info(f"🔍 Connection validation completed: {successful_tests}/{total_tests} successful")
        return results
    
    def close_all_connections(self):
        """
        全接続プールのクリーンアップ
        """
        try:
            if self._postgres_pool:
                self._postgres_pool.closeall()
                self.logger.info("✅ PostgreSQL pool closed")
                
            if self._redis_pool:
                self._redis_pool.disconnect()
                self.logger.info("✅ Redis pool closed")
                
        except Exception as e:
            self.logger.error(f"❌ Connection cleanup failed: {e}")


# 環境別インスタンス作成関数
def create_database_manager(environment: str = None) -> DatabaseManager:
    """
    環境別DatabaseManagerインスタンス作成
    
    Args:
        environment: 環境識別子
        
    Returns:
        DatabaseManager: 設定済みインスタンス
    """
    return DatabaseManager(environment)


# グローバルインスタンス（後方互換性）
db_manager = None

def get_database_manager() -> DatabaseManager:
    """
    グローバルDatabaseManagerインスタンス取得
    
    Returns:
        DatabaseManager: シングルトンインスタンス
    """
    global db_manager
    if db_manager is None:
        db_manager = create_database_manager()
    return db_manager