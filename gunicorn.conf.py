# -*- coding: utf-8 -*-
"""
Gunicorn Configuration for LangPont
本番環境用Gunicorn設定ファイル

使用方法:
  gunicorn -c gunicorn.conf.py wsgi:app
"""

import os
import multiprocessing

# サーバー設定
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
backlog = 2048

# ワーカー設定
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
worker_connections = 1000
timeout = 120  # OpenAI APIの長いタイムアウトに対応
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

# プロセス管理
preload_app = True
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# ログ設定
loglevel = os.getenv('LOG_LEVEL', 'info')
accesslog = os.getenv('ACCESS_LOG', '-')  # stdout
errorlog = os.getenv('ERROR_LOG', '-')   # stderr
access_log_format = '%h %l %u %t "%r" %s %b "%{Referer}i" "%{User-Agent}i" %D'

# セキュリティ設定
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# パフォーマンス設定
preload_app = True
worker_tmp_dir = "/dev/shm"  # メモリファイルシステムを使用（利用可能な場合）

# 環境変数設定
def when_ready(server):
    server.log.info("🚀 LangPont Gunicorn サーバー起動完了")
    server.log.info(f"🌍 バインド: {bind}")
    server.log.info(f"👥 ワーカー数: {workers}")
    server.log.info(f"⏱️ タイムアウト: {timeout}秒")

def worker_int(worker):
    worker.log.info("👋 ワーカーが停止シグナルを受信しました")

def on_exit(server):
    server.log.info("🛑 LangPont Gunicorn サーバー停止")

# 本番環境での追加設定
if os.getenv('ENVIRONMENT') == 'production':
    # 本番環境では少し厳しめの設定
    timeout = 180
    keepalive = 2
    max_requests = 500
    worker_connections = 500
    
    # セキュリティ強化
    limit_request_line = 2048
    limit_request_fields = 50