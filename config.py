# LangPont Configuration File
# 機能の有効/無効を簡単に切り替えできます

import os

VERSION = "2.0.0"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # development, staging, production

# 🆕 SL-2.2: Redis Session Configuration
USE_REDIS_SESSION = os.getenv('USE_REDIS_SESSION', 'False').lower() == 'true'
SESSION_TTL_SECONDS = int(os.getenv('SESSION_TTL_SECONDS', '3600'))
SESSION_COOKIE_NAME = os.getenv('SESSION_COOKIE_NAME', 'langpont_session')

# Security settings
SESSION_COOKIE_SECURE = ENVIRONMENT == "production"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# 📱 機能フラグ（True/Falseで機能のON/OFF）
FEATURES = {
    "early_access_mode": True,      # Early Access制限機能
    "usage_limits": True,           # 1日の使用制限
    "premium_translation": False,   # Premium翻訳モード
    "experimental_ui": False,       # 実験的UI
    "debug_mode": True,            # デバッグ情報表示
    "gemini_analysis": True,       # Gemini分析機能
    "interactive_qa": True         # インタラクティブ質問機能
}

# 🌍 デプロイ環境設定
DEPLOYMENT = {
    "development": {
        "aws_instance": "langpont-dev",
        "domain": "dev.langpont.com",
        "debug": True
    },
    "production": {
        "aws_instance": "langpont-prod", 
        "domain": "langpont.com",
        "debug": False
    }
}

# 📊 使用制限設定
USAGE_LIMITS = {
    "free_daily_limit": 10,
    "premium_daily_limit": 100
}

# 👥 ユーザー管理システム（暫定版）
USERS = {
    "admin": {
        "password": os.getenv("ADMIN_PASSWORD", "admin_langpont_2025"),
        "role": "admin",
        "daily_limit": -1,  # -1 = 無制限
        "description": "管理者アカウント"
    },
    "developer": {
        "password": os.getenv("DEVELOPER_PASSWORD", "dev_langpont_456"),
        "role": "developer", 
        "daily_limit": 1000,
        "description": "開発者アカウント"
    },
    "guest": {
        "password": os.getenv("GUEST_PASSWORD", "guest_basic_123"),
        "role": "guest",
        "daily_limit": 10,
        "description": "ゲストアカウント"
    }
}

# 🔒 後方互換性設定
LEGACY_SETTINGS = {
    "legacy_password": os.getenv("LEGACY_PASSWORD", "linguru2025"),  # 既存パスワード
    "default_guest_username": "guest"  # 空ユーザー名時のデフォルト
}

# 🗄️ Phase 3c-2: Redis TTL設計
REDIS_TTL = {
    'translation_state': 86400,      # 24時間 - 通常の翻訳データ
    'large_data': 604800,           # 7日間 - 大容量データ（翻訳結果など）
    'context_full': 2592000,        # 30日間 - context_full_data
    'user_history': None            # 無期限 - ユーザー履歴インデックス
}
