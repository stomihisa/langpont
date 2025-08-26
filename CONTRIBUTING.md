# Contributing to LangPont

LangPont への貢献をお考えいただき、ありがとうございます！

## 📋 必須事項

### 設計書準拠

**最重要**: 全ての貢献は [docs/ARCHITECTURE_SAVE_v3.0.md](docs/ARCHITECTURE_SAVE_v3.0.md) の設計仕様に準拠する必要があります。

- 実装前に必ず設計書を確認してください
- 設計を逸脱する変更は受け入れられません
- 疑問がある場合は Issue で相談してください

### 禁止事項

以下は **絶対に禁止** です：

- `python app.py &` での起動
- `flask run --reload &` での起動
- 本番環境でのデバッグモード使用
- 本設計にない「仮実装」「一時的な保存処理」

## 🚀 開発環境セットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd langpont
```

### 2. 仮想環境の作成

```bash
python -m venv myenv
source myenv/bin/activate  # Linux/Mac
# または
myenv\Scripts\activate  # Windows
```

### 3. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定

```bash
cp .env.example .env
# .env ファイルを編集してAPIキーを設定
```

### 5. 開発サーバーの起動

```bash
# 正しい起動方法
gunicorn --config gunicorn.conf.py wsgi:application

# 禁止されている起動方法
# python app.py &  ← これは禁止
```

## 🔧 開発フロー

### 1. Issue の作成

新機能や修正を行う前に、Issue を作成して議論してください。

### 2. ブランチの作成

```bash
git checkout -b feature/your-feature-name
# または
git checkout -b fix/your-fix-name
```

### 3. 実装

- [docs/ARCHITECTURE_SAVE_v3.0.md](docs/ARCHITECTURE_SAVE_v3.0.md) に準拠した実装
- 適切なコメント・ドキュメントの追加
- テストの作成・実行

### 4. テスト

```bash
# 自動テストスイート
cd test_suite
./full_test.sh

# 個別テスト
python api_test.py
python selenium_test.py
```

### 5. Pull Request の作成

- PR テンプレートの全項目を確認
- `spec-v3.0` ラベルを付与
- レビューを依頼

## 📝 コード規約

### Python コード

- PEP 8 に準拠
- 関数・クラスに適切な docstring
- 型ヒントの使用を推奨

```python
def example_function(param: str) -> Dict[str, Any]:
    """
    関数の説明
    
    Args:
        param: パラメータの説明
        
    Returns:
        戻り値の説明
    """
    return {"result": param}
```

### JavaScript コード

- 一貫したインデント（スペース2個）
- 適切なコメント
- ES6+ の機能を積極的に使用

```javascript
function exampleFunction(param) {
    // 処理の説明
    return {
        result: param
    };
}
```

### HTML/CSS

- セマンティックなHTML
- レスポンシブデザイン
- アクセシビリティの考慮

## 🧪 テストガイドライン

### 必須テスト

- 新機能の単体テスト
- 既存機能への影響確認
- ブラウザでの動作確認
- API エンドポイントの動作確認

### テストファイルの場所

```
test_suite/
├── full_test.sh         # メイン実行スクリプト
├── api_test.py         # API テスト
├── selenium_test.py    # UI テスト
└── test_*.py          # 個別テスト
```

## 🔒 セキュリティ

### 機密情報の扱い

- API キー・パスワードをコードに含めない
- 環境変数を使用
- `.env` ファイルをコミットしない

### セキュリティ課題の報告

セキュリティに関する問題を発見した場合：

1. 公開 Issue は作成しない
2. メンテナーに直接連絡
3. 修正まで詳細を公開しない

## 📋 Pull Request チェックリスト

PR 作成前に以下を確認してください：

- [ ] [docs/ARCHITECTURE_SAVE_v3.0.md](docs/ARCHITECTURE_SAVE_v3.0.md) に準拠
- [ ] テストが全て通る
- [ ] 禁止事項に該当しない
- [ ] 機密情報が含まれていない
- [ ] ドキュメントが更新されている（必要に応じて）
- [ ] `spec-v3.0` ラベルが付与されている

## 🏷️ Issue・PR ラベル

### 必須ラベル

- `spec-v3.0`: 設計書v3.0準拠
- `ARCHITECTURE準拠`: アーキテクチャ準拠確認済み

### カテゴリラベル

- `enhancement`: 新機能
- `bug`: バグ修正
- `documentation`: ドキュメント更新
- `security`: セキュリティ関連
- `performance`: パフォーマンス改善

### 優先度ラベル

- `priority-high`: 高優先度
- `priority-medium`: 中優先度
- `priority-low`: 低優先度

## 📚 参考資料

### 必読ドキュメント

- [docs/ARCHITECTURE_SAVE_v3.0.md](docs/ARCHITECTURE_SAVE_v3.0.md) - **メイン設計書（必読）**
- [README.md](README.md) - プロジェクト概要
- [Readme_dev.md](Readme_dev.md) - 開発環境ガイド
- [README-DEPLOYMENT.md](README-DEPLOYMENT.md) - デプロイメントガイド

### 技術スタック

- **Frontend**: HTML/CSS/JavaScript (Vanilla)
- **Backend**: Python Flask
- **AI Engine**: OpenAI ChatGPT + Google Gemini + Anthropic Claude
- **Database**: PostgreSQL (移行予定) + Redis + SQLite (移行期間中)
- **Deployment**: AWS + Heroku対応

## ❓ サポート

### 質問・相談

- GitHub Issues で質問
- 設計に関する疑問は [docs/ARCHITECTURE_SAVE_v3.0.md](docs/ARCHITECTURE_SAVE_v3.0.md) を参照
- 開発環境の問題は [Readme_dev.md](Readme_dev.md) を参照

### コミュニティ

- Issues での議論を歓迎
- コード品質向上の提案
- ドキュメント改善の提案

---

**重要**: 全ての貢献は [docs/ARCHITECTURE_SAVE_v3.0.md](docs/ARCHITECTURE_SAVE_v3.0.md) の設計仕様に準拠する必要があります。設計書に疑問がある場合は、実装前に Issue で相談してください。

皆様の貢献により、LangPont がより良いプロダクトになることを願っています！