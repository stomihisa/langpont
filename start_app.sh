#\!/bin/bash

echo "🚀 LangPont アプリケーション起動スクリプト"
echo "=================================="

# ポート8080をクリーンアップ  
echo "🔧 ポートクリーンアップ中..."
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
pkill -f "python.*app.py" 2>/dev/null || true

# 2秒待機
sleep 2

# ポート状況確認
if lsof -i:8080 2>/dev/null | grep -q LISTEN; then
    echo "❌ ポート8080がまだ使用中です。手動で確認してください："
    lsof -i:8080
    exit 1
else
    echo "✅ ポート8080は解放されました"
fi

echo ""
echo "🎉 LangPont アプリケーションを起動します..."
echo "📍 URL: http://localhost:8080"
echo "🔐 管理者ログイン: admin / admin_langpont_2025"
echo ""

# アプリケーション起動
python app.py
