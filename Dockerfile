# LangPont Production Dockerfile
FROM python:3.11-slim

# メタデータ
LABEL maintainer="LangPont Team"
LABEL description="LangPont AI Translation Platform"
LABEL version="1.0.0"

# 作業ディレクトリ設定
WORKDIR /app

# システムパッケージの更新とクリーンアップ
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 非rootユーザーの作成
RUN useradd --create-home --shell /bin/bash langpont && \
    chown -R langpont:langpont /app
USER langpont

# Python依存関係のインストール
COPY --chown=langpont:langpont requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# アプリケーションファイルのコピー
COPY --chown=langpont:langpont . .

# ログディレクトリの作成と権限設定
RUN mkdir -p logs && \
    chmod 755 logs

# ポート設定
EXPOSE 8080

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/alpha || exit 1

# 環境変数設定
ENV ENVIRONMENT=production
ENV FLASK_ENV=production
ENV PORT=8080
ENV PYTHONPATH=/app
ENV PATH="/home/langpont/.local/bin:$PATH"

# 起動コマンド
CMD ["python", "-m", "gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]