#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI Entry Point for LangPont
本番環境用WSGIサーバー設定ファイル

使用方法:
  gunicorn --bind 0.0.0.0:8080 wsgi:app
  uwsgi --http 0.0.0.0:8080 --module wsgi:app
"""

import os
import sys
import logging
from pathlib import Path

# アプリケーションのルートディレクトリをPythonパスに追加
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# 本番環境設定の強制適用
os.environ.setdefault('ENVIRONMENT', 'production')
os.environ.setdefault('FLASK_ENV', 'production')

# 必要な環境変数のチェック
required_env_vars = ['OPENAI_API_KEY']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]

if missing_vars:
    error_msg = f"必須環境変数が設定されていません: {', '.join(missing_vars)}"
    print(f"❌ {error_msg}", file=sys.stderr)
    raise EnvironmentError(error_msg)

try:
    # アプリケーションをインポート
    from app import app
    
    # WSGIアプリケーションオブジェクト
    application = app
    
    # 本番環境での最終設定
    app.config.update({
        'DEBUG': False,
        'TESTING': False,
        'ENV': 'production'
    })
    
    # ログ設定の調整
    if not app.logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
    
    print("✅ LangPont WSGI アプリケーション初期化完了")
    print(f"🌍 本番環境モード: {app.config.get('ENV')}")
    print(f"🔒 デバッグモード: {app.config.get('DEBUG')}")
    
except ImportError as e:
    print(f"❌ アプリケーションのインポートに失敗: {e}", file=sys.stderr)
    raise
except Exception as e:
    print(f"❌ WSGI初期化エラー: {e}", file=sys.stderr)
    raise

if __name__ == "__main__":
    # 開発時の直接実行用
    print("⚠️ 開発時の直接実行です。本番環境ではWSGIサーバーを使用してください。")
    app.run(host='0.0.0.0', port=8080, debug=False)