#!/bin/bash
echo "🔍 Python プロセス確認"
ps aux | grep -E "python|flask" | grep -v grep
echo ""
echo "🔍 ポート8080使用状況"
lsof -i :8080 2>/dev/null || echo "ポート8080は空いています"
echo ""
echo "🔍 現在のディレクトリ"
pwd
