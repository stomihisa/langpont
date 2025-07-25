#!/bin/bash
# -*- coding: utf-8 -*-
"""
LangPont 本番環境デプロイメントスクリプト
自動化されたデプロイメントプロセス
"""

set -e  # エラー時に停止

# 色付きメッセージ関数
print_info() {
    echo -e "\033[34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[32m[SUCCESS]\033[0m $1"
}

print_warning() {
    echo -e "\033[33m[WARNING]\033[0m $1"
}

print_error() {
    echo -e "\033[31m[ERROR]\033[0m $1"
}

# スクリプト開始
print_info "🚀 LangPont 本番環境デプロイメント開始"

# 前提条件チェック
print_info "📋 前提条件をチェック中..."

# Docker チェック
if ! command -v docker &> /dev/null; then
    print_error "Dockerがインストールされていません"
    exit 1
fi

# Docker Compose チェック
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Composeがインストールされていません"
    exit 1
fi

# .env ファイルチェック
if [ ! -f ".env" ]; then
    print_warning ".envファイルが見つかりません"
    print_info ".env.exampleをコピーして.envを作成してください"
    cp .env.example .env
    print_warning "⚠️ .envファイルに必要な値を設定してからデプロイを再実行してください"
    exit 1
fi

# 必須環境変数チェック
source .env
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
    print_error "OPENAI_API_KEYが設定されていません"
    exit 1
fi

print_success "✅ 前提条件チェック完了"

# ログディレクトリ作成
print_info "📁 ログディレクトリを作成中..."
mkdir -p logs
chmod 755 logs
print_success "✅ ログディレクトリ作成完了"

# 既存コンテナの停止と削除
print_info "🛑 既存コンテナを停止中..."
docker-compose down || true
print_success "✅ 既存コンテナ停止完了"

# イメージの構築
print_info "🔨 Dockerイメージを構築中..."
docker-compose build --no-cache
print_success "✅ Dockerイメージ構築完了"

# コンテナの起動
print_info "🚀 コンテナを起動中..."
docker-compose up -d

# 起動確認
print_info "⏳ サービス起動を確認中..."
sleep 10

# ヘルスチェック
print_info "🏥 ヘルスチェック実行中..."
max_attempts=12
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f -s http://localhost:8080/alpha > /dev/null 2>&1; then
        print_success "✅ ヘルスチェック成功"
        break
    else
        print_warning "⏳ 起動確認中... ($attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    fi
done

if [ $attempt -gt $max_attempts ]; then
    print_error "❌ ヘルスチェックが失敗しました"
    print_info "📜 ログを確認してください:"
    docker-compose logs langpont
    exit 1
fi

# デプロイメント情報表示
print_success "🎉 LangPont デプロイメント完了！"
echo ""
print_info "📊 デプロイメント情報:"
echo "  🌐 アプリケーション: http://localhost:8080"
echo "  🔐 ログイン画面: http://localhost:8080/login"
echo "  🌍 ランディングページ: http://localhost:8080/alpha"
echo ""
print_info "🔧 管理コマンド:"
echo "  ログ確認: docker-compose logs langpont"
echo "  停止: docker-compose down"
echo "  再起動: docker-compose restart"
echo "  コンテナ情報: docker-compose ps"
echo ""
print_info "📋 環境設定:"
echo "  環境: $(grep ENVIRONMENT .env | cut -d'=' -f2)"
echo "  ポート: $(grep PORT .env | cut -d'=' -f2 || echo '8080')"
echo ""

# オプション: Nginxプロファイルの案内
print_info "💡 Nginxリバースプロキシを使用する場合:"
echo "  docker-compose --profile nginx up -d"

print_success "🚀 デプロイメント完了！LangPontが正常に起動しました。"