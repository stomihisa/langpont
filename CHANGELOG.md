# Changelog

All notable changes to LangPont will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Task #9-4 AP-1 Phase4 Step4-02: DSN固定とSecrets管理移行
  - DatabaseManager_v3.0による統一データベース接続管理システム
  - AWS Secrets Manager/SSM統合による機密情報安全管理
  - PostgreSQL/Redis DSN統一化とTLS強制
  - LegacyDatabaseAdapterによる既存コード完全互換性保持

### Changed
- .env.example を Task #9-4 対応版に更新
- config.py にデータベース統一設定追加
- services/session_redis_manager.py を DatabaseManager統合

### Security
- 相対パス完全撤廃によるファイルアクセス安全化
- sslmode=require強制による PostgreSQL接続セキュリティ強化
- Redis TLS強制による通信暗号化
- 機密情報コード・ログ流出防止機能追加

## [3.0.0] - 2025-08-21

### Added
- ARCHITECTURE_SAVE_v3.0.md 設計書確定・リポジトリ反映 (Task #9-4 AP-1 Phase4 Step4-01)
- docs/ ディレクトリと包括的設計ドキュメント
- README.md メイン設計書リンク
- Git タグ v3.0-docs による設計固定
- S4-01 自動監査スクリプト実装

### Changed
- README.md をプロジェクト統一ドキュメントハブに更新
- CLAUDE.md にアーキテクチャ仕様参照セクション追加

## [2.1.0] - 2025-08-17

### Added
- Task #9-4 AP-1 Phase4 Step4 / No.1 Step1: 履歴機能実装完了
  - 翻訳履歴表示・復元機能 (258行のJavaScript新機能)
  - localStorage による安全なローカル履歴管理
  - UI統合監視システム (UIMonitor) 実装
- Task #9-4 AP-1 Phase4 Step4 / No.0: 監視レイヤー事前導入
  - 軽量UI専用監視機能 (105行)
  - 必須5イベント包括記録機能

### Fixed
- No.0-Fix: sendイベント未記録・target_lang不正・関数未フック修正

## [2.0.0] - 2025-08-16

### Changed
- 監視レイヤー実装失敗により dd3ae5c へ git reset 復旧実施
- 失敗パターン学習と復旧手順確立

## [1.9.0] - 2025-08-12-13

### Added
- Task #9-4 AP-1 Phase 4 Step2-3: 逆翻訳機能実装・テスト成功
- Blueprint統合による逆翻訳Service層実装
- Redis TTL=604800s保存・全エンジン対応確認

### Security
- CSRF Redis統合完成確認
- セキュリティイベント統合ログ実装

## [1.8.0] - 2025-08-06-09

### Added
- Task #9 AP-1 Phase 2: Gemini翻訳Blueprint分離完全実装
  - TranslationService拡張 (translate_with_gemini メソッド)
  - /translate_gemini エンドポイント新設
  - 3つのAIエンジン統一アーキテクチャ確立
- Task #9-3 AP-1 Phase 3: 分析機能Blueprint分離完全実装
  - AnalysisService/InteractiveService実装
  - routes/analysis.py Blueprint実装
  - 3層責務分離アーキテクチャ構築

### Removed
- レガシー f_translate_with_gemini() 関数削除 (74行削減)
- app.py から分析エンドポイント392行削除

## [1.7.0] - 2025-08-04-05

### Added
- Task #9 AP-1 Phase 1: ChatGPT翻訳Blueprint分離完全実装
  - services/translation_service.py 新規作成
  - routes/translation.py Blueprint実装
  - 依存注入パターンによる疎結合設計

### Fixed
- 初期化順序エラー修正
- ImportError修正 (get_user_id関数)
- 関数名競合修正 (get_translation_state)
- セッション保存修正

## [1.6.0] - 2025-08-03

### Fixed
- Task #8 SL-4: CSRF状態の外部化完全解決
  - HTMLテンプレートCSRF変数参照エラー修正
  - HTTPヘッダー名1文字不一致修正
  - 403エラー完全解消

### Security
- CSRF Redis統合完成
- 5つのAPIエンドポイント保護強化

## [1.5.0] - 2025-07-23

### Added
- Phase 9d フォーム状態管理統合実装完了
  - StateManager フォーム管理機能拡張 (12メソッド)
  - 統合管理フォームフィールド (5つ)
  - 自動化機能実現

### Security
- 3層責務分離アーキテクチャ構築完了
- デバッグ効率向上「30分→5分」達成

## [1.4.0] - 2025-07-20

### Changed
- CLAUDE.md 分割実施 (61,160トークン→25MB対応)
  - CLAUDE_HISTORY_202506.md (2025年6月セッション履歴)
  - CLAUDE_HISTORY_202507.md (2025年7月セッション履歴)
  - 一切の情報削除なし、完全保存による分割

## [1.3.0] - 2025-06月

### Added
- Task 2.6.1: ユーザー認証システム基盤構築
- Task 2.9.2: Claude API統合実装
- 統合活動ログシステム完成
- 多言語対応緊急修正
- 最適ダッシュボード設計

## [1.2.0] - 2025年初期

### Added
- 基本翻訳機能実装
- ChatGPT/Gemini/Claude 3エンジン統合
- セッション管理システム
- Redis統合機能

### Security
- 基本セキュリティ機能実装
- レート制限機能
- 入力検証システム

## [1.0.0] - 2025年初期

### Added
- 初期リリース
- 基本AI翻訳機能
- Web インターフェース

---

## 変更カテゴリ説明

- **Added**: 新機能追加
- **Changed**: 既存機能変更
- **Deprecated**: 廃止予定機能
- **Removed**: 削除された機能
- **Fixed**: バグ修正
- **Security**: セキュリティ関連の変更