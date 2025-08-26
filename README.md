# LangPont

LangPont は多言語翻訳・ニュアンス分析を行う Flask ベースのアプリケーションです。  
ChatGPT / Gemini / Claude など複数のLLMを統合し、ユーザーに最適な翻訳を提供します。

---

## Architecture Specification

本プロジェクトの唯一の参照点（Single Source of Truth for Spec）は以下の設計書に固定されています：

- [docs/ARCHITECTURE_SAVE_v3.0.md](docs/ARCHITECTURE_SAVE_v3.0.md)

以降の実装・レビュー・Pull Request は必ず本設計に準拠して進めてください。  
タグ `v3.0-docs` で設計が固定されています。

---

## 開発ルール

- PR は必ず設計準拠テンプレートを使用し、`spec-v3.0` ラベルを付与してください。
- 以下は禁止事項です：
  - `python app.py &` での実行
  - `flask run --reload &` での実行
  - 本番環境でのデバッグモード使用
- 本番環境は `gunicorn + systemd` で運用してください。

---

## Getting Started

```bash
git clone <your-repo>
cd langpont
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .env ファイルを編集してAPIキーを設定

# 開発環境での起動
gunicorn --config gunicorn.conf.py wsgi:application
```

詳細な開発環境セットアップは [Readme_dev.md](Readme_dev.md) を参照してください。

---

## Deployment

本番環境へのデプロイメント手順は以下を参照してください：

- [README-DEPLOYMENT.md](README-DEPLOYMENT.md)

Docker、環境変数、監視設定など本番運用に必要な全ての情報が記載されています。

---

## Project Structure

```
langpont/
├── app.py                    # Flask アプリケーション エントリーポイント
├── config.py                 # 設定管理
├── labels.py                 # 多言語ラベル管理
├── services/                 # ビジネスロジック層
│   ├── translation_service.py
│   ├── translation_state_manager.py
│   └── session_redis_manager.py
├── routes/                   # Flask Blueprint ルーティング
│   ├── translation.py
│   └── analysis.py
├── security/                 # セキュリティ関連
├── templates/                # Jinja2 テンプレート
├── static/                   # 静的ファイル
├── docs/                     # 設計書・ドキュメント
└── test_suite/               # 自動テストスイート
```

---

## Documentation

### 設計・開発ドキュメント
- [docs/ARCHITECTURE_SAVE_v3.0.md](docs/ARCHITECTURE_SAVE_v3.0.md) - **メイン設計書（必読）**
- [Readme_dev.md](Readme_dev.md) - 開発環境ガイド
- [README-DEPLOYMENT.md](README-DEPLOYMENT.md) - 本番デプロイメントガイド

### 技術仕様
- **Frontend**: HTML/CSS/JavaScript (Vanilla)
- **Backend**: Python Flask
- **AI Engine**: OpenAI ChatGPT + Google Gemini + Anthropic Claude
- **State Management**: Redis + PostgreSQL (移行予定)
- **Security**: CSRF Protection, Rate Limiting, Input Validation

---

## Testing

```bash
# 自動テストスイート実行
cd test_suite
./full_test.sh

# API テスト単体実行
python api_test.py

# UI テスト単体実行  
python selenium_test.py
```

---

## Contributing

1. [docs/ARCHITECTURE_SAVE_v3.0.md](docs/ARCHITECTURE_SAVE_v3.0.md) を必ず確認
2. 設計に準拠した実装を行う
3. PR作成時は `spec-v3.0` ラベルを付与
4. コードレビューで設計準拠を確認

---

## License

このプロジェクトは MIT License の下で公開されています。

---

## Support

- 設計に関する質問: [docs/ARCHITECTURE_SAVE_v3.0.md](docs/ARCHITECTURE_SAVE_v3.0.md) を参照
- 開発環境の問題: [Readme_dev.md](Readme_dev.md) を参照  
- デプロイメントの問題: [README-DEPLOYMENT.md](README-DEPLOYMENT.md) を参照