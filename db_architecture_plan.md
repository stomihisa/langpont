# LangPont AWS対応データベースアーキテクチャ設計書

## 🎯 設計目標
1. Single Source of Truth の確立
2. ダッシュボード間のデータ不整合解消
3. AWS移行時の最適パフォーマンス
4. セキュリティ・スケーラビリティの確保

## 📊 現在の問題分析
- 複数DBファイルによるデータ分散
- ダッシュボード毎の異なるデータ数
- データソースの不透明性

## 🏗️ 新アーキテクチャ

### Phase 1: データ統合（ローカル環境）
```
langpont_master.db (Single Source of Truth)
├── core_activity_log        # メインの活動ログ（既存）
├── users_management         # ユーザー管理
├── system_analytics         # システム分析用
└── translation_cache        # 翻訳キャッシュ
```

### Phase 2: AWS移行時構成
```
Amazon RDS (PostgreSQL)
├── langpont_production      # 本番データ
│   ├── activity_logs        # パーティション対応
│   ├── users               # 暗号化対応
│   ├── analytics           # インデックス最適化
│   └── system_metrics      # 監視用
│
Redis Cluster (ElastiCache)
├── session_store           # セッション管理
├── translation_cache       # 翻訳結果キャッシュ
└── real_time_metrics      # リアルタイム統計
```

## 🔧 実装計画

### Step 1: データ統合サービス作成
- 全DBからのデータを統一APIで提供
- キャッシュ層の実装
- データ整合性の保証

### Step 2: ダッシュボード統一
- 全ダッシュボードが同じAPIを使用
- データソースの透明化
- リアルタイム同期

### Step 3: AWS移行準備
- PostgreSQL互換のSQL作成
- パーティショニング戦略
- セキュリティ強化

## 📈 期待効果
1. データ不整合の完全解消
2. パフォーマンス向上（30-50%）
3. AWS移行の円滑化
4. 運用保守性の向上