#!/bin/bash
echo "🚨 緊急停止処理を開始します..."

# Pythonプロセス停止
pkill -f "python app.py" 2>/dev/null && echo "✅ Python app.py プロセスを停止しました"

# ポート8080解放
lsof -ti:8080 | xargs kill -9 2>/dev/null && echo "✅ ポート8080を解放しました"

# 結果確認
sleep 2
echo ""
echo "🔍 停止後の状況確認："
./check_processes.sh
