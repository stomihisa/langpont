# LangPont Configuration File
# 機能の有効/無効を簡単に切り替えできます

VERSION = "2.0.0"
ENVIRONMENT = "development"  # development, staging, production

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
