# 🚀 LangPont 本番環境デプロイメントガイド

このガイドでは、LangPontを本番環境にデプロイする方法を説明します。

## 📋 目次

1. [前提条件](#前提条件)
2. [環境変数設定](#環境変数設定)
3. [デプロイメント方法](#デプロイメント方法)
4. [監視・メンテナンス](#監視メンテナンス)
5. [トラブルシューティング](#トラブルシューティング)

## 🔧 前提条件

### 必要なソフトウェア
- **Docker** (v20.10+)
- **Docker Compose** (v2.0+)
- **curl** (ヘルスチェック用)

### 必要なAPIキー
- **OpenAI API Key** (必須)
- **Gemini API Key** (オプション - 3way分析機能用)

## 🔑 環境変数設定

### 1. 環境変数ファイルの準備

```bash
# .env.exampleをコピー
cp .env.example .env

# 必要な値を設定
nano .env
```

### 2. 必須環境変数

```bash
# 🔑 必須設定
OPENAI_API_KEY=your_openai_api_key_here
FLASK_SECRET_KEY=your_super_secret_key_here_32_chars_minimum

# 🛡️ セキュリティ設定
APP_PASSWORD=your_custom_password_here

# 🌍 環境設定
ENVIRONMENT=production
PORT=8080
```

### 3. オプション設定

```bash
# Gemini API（3way分析用）
GEMINI_API_KEY=your_gemini_api_key_here

# Gunicorn設定
GUNICORN_WORKERS=4

# ログ設定
LOG_LEVEL=INFO
```

## 🚀 デプロイメント方法

### 方法1: 自動デプロイスクリプト（推奨）

```bash
# デプロイスクリプトを実行
./deploy.sh
```

このスクリプトは以下を自動実行します：
- 前提条件チェック
- 環境変数検証
- Dockerイメージビルド
- コンテナ起動
- ヘルスチェック

### 方法2: 手動デプロイ

```bash
# 1. ログディレクトリ作成
mkdir -p logs

# 2. 既存コンテナ停止
docker-compose down

# 3. イメージビルド
docker-compose build --no-cache

# 4. コンテナ起動
docker-compose up -d

# 5. 起動確認
curl -f http://localhost:8080/alpha
```

### 方法3: Nginxリバースプロキシ付き

```bash
# Nginxプロファイル付きで起動
docker-compose --profile nginx up -d
```

## 📊 デプロイ後の確認

### アクセス先
- **メインアプリ**: http://localhost:8080
- **ログイン画面**: http://localhost:8080/login
- **ランディングページ**: http://localhost:8080/alpha

### ヘルスチェック
```bash
# ヘルスチェックエンドポイント
curl -f http://localhost:8080/alpha

# コンテナ状態確認
docker-compose ps

# ログ確認
docker-compose logs langpont
```

## 🔍 監視・メンテナンス

### ログ確認

```bash
# リアルタイムログ
docker-compose logs -f langpont

# エラーログのみ
docker-compose logs langpont | grep ERROR

# アクセスログ
tail -f logs/access.log

# セキュリティログ
tail -f logs/security.log
```

### パフォーマンス監視

```bash
# リソース使用量
docker stats langpont_langpont_1

# プロセス確認
docker exec -it langpont_langpont_1 ps aux
```

### メンテナンスコマンド

```bash
# コンテナ再起動
docker-compose restart langpont

# 設定リロード
docker-compose up -d --force-recreate

# 完全再構築
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 🛡️ セキュリティ設定

### HTTPS設定（本番環境推奨）

1. SSL証明書を取得
2. `ssl/` ディレクトリに配置
3. `nginx.conf` のSSL設定を有効化

```bash
# Let's Encrypt使用例
certbot certonly --standalone -d yourdomain.com
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
```

### ファイアウォール設定

```bash
# 必要なポートのみ開放
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 22/tcp    # SSH
ufw enable
```

## 🌐 クラウドプラットフォーム別デプロイ

### Heroku

```bash
# Heroku CLIでデプロイ
heroku create your-app-name
heroku config:set OPENAI_API_KEY=your_key
heroku config:set FLASK_SECRET_KEY=your_secret
git push heroku main
```

### Render

```yaml
# render.yaml
services:
  - type: web
    name: langpont
    env: docker
    plan: starter
    envVars:
      - key: OPENAI_API_KEY
        value: your_key
      - key: ENVIRONMENT
        value: production
```

### AWS ECS

```bash
# ECRにプッシュ
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
docker build -t langpont .
docker tag langpont:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/langpont:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/langpont:latest
```

## 🔧 トラブルシューティング

### よくある問題

#### 1. コンテナが起動しない
```bash
# ログ確認
docker-compose logs langpont

# よくある原因:
# - 環境変数未設定
# - ポート競合
# - メモリ不足
```

#### 2. 502 Bad Gateway
```bash
# アプリケーション状態確認
docker-compose ps
curl -f http://localhost:8080/alpha

# Nginxログ確認（Nginx使用時）
docker-compose logs nginx
```

#### 3. API エラー
```bash
# OpenAI APIキー確認
docker exec langpont_langpont_1 printenv OPENAI_API_KEY

# ネットワーク確認
docker exec langpont_langpont_1 curl -I https://api.openai.com
```

### パフォーマンス最適化

#### メモリ使用量が多い場合
```bash
# Gunicornワーカー数を調整
echo "GUNICORN_WORKERS=2" >> .env
docker-compose restart langpont
```

#### レスポンス時間が遅い場合
```bash
# キャッシュ設定確認
# Redisなどの外部キャッシュ導入を検討
```

## 📞 サポート

問題が解決しない場合は、以下の情報と一緒にお問い合わせください：

```bash
# 環境情報収集
echo "=== システム情報 ===" > debug_info.txt
docker --version >> debug_info.txt
docker-compose --version >> debug_info.txt
echo "=== コンテナ状態 ===" >> debug_info.txt
docker-compose ps >> debug_info.txt
echo "=== ログ（最新50行） ===" >> debug_info.txt
docker-compose logs --tail=50 langpont >> debug_info.txt
```

---

**🎉 LangPont 本番環境デプロイメント完了！**

このガイドに従って、安全で効率的なLangPont環境を構築してください。