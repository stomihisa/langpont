# 📊 SL-1: セッション分類レポート

**分析日**: 2025年7月25日  
**対象**: LangPont セッション使用87箇所の詳細分類  
**分析者**: Claude Code  

## 🎯 分析概要

### セッション使用統計（再確認）
- **総使用箇所**: 87箇所（AWS-2で特定）
- **参照箇所**: 50+箇所（session.get()）
- **セッション項目数**: 25項目
- **関連ファイル数**: 12ファイル

---

## 📋 1. Category A: 認証関連状態（Critical Priority）

### 1.1 基本認証情報
| セッションキー | 設定箇所 | 参照箇所 | ライフサイクル | Redis優先度 |
|----------------|----------|----------|----------------|-------------|
| `logged_in` | app.py:1714<br>auth_routes.py:359<br>admin_auth.py:282 | 全画面の認証判定 | ログイン〜ログアウト | **Critical** |
| `username` | app.py:1715<br>auth_routes.py:360,399<br>admin_auth.py:283 | ヘッダー表示・ログ記録 | ログイン〜ログアウト | **Critical** |
| `user_role` | app.py:1716<br>auth_routes.py:361<br>admin_auth.py:284 | 権限制御・機能制限 | ログイン〜ログアウト | **Critical** |

### 1.2 詳細認証情報
| セッションキー | 設定箇所 | 参照箇所 | ライフサイクル | Redis優先度 |
|----------------|----------|----------|----------------|-------------|
| `user_id` | auth_routes.py:398 | DB関連付け・統計 | 認証〜ログアウト | **Critical** |
| `daily_limit` | app.py:1717<br>auth_routes.py:362 | 使用制限管理 | ログイン〜ログアウト | **High** |
| `authenticated` | auth_routes.py:397 | 高度認証判定 | 認証〜ログアウト | **Critical** |
| `session_token` | auth_routes.py:400 | セッション識別 | 認証〜期限切れ | **Critical** |
| `session_id` | auth_routes.py:401 | セッション追跡 | 認証〜期限切れ | **High** |
| `account_type` | auth_routes.py:402 | アカウント種別制御 | ログイン〜ログアウト | **High** |
| `early_access` | auth_routes.py:403 | Early Access権限 | ログイン〜ログアウト | **Medium** |

### 1.3 依存関係と影響範囲

#### 認証チェーン依存
```
logged_in → username + user_role → daily_limit
    ↓           ↓          ↓           ↓
  認証状態   個人化表示   権限制御   使用制限
```

#### 影響範囲
- **Critical影響**: `logged_in`, `username`, `user_role`, `authenticated` 失効 → 全機能停止
- **High影響**: `daily_limit`, `account_type` 失効 → 制限機能影響
- **Medium影響**: `early_access` 失効 → 特別機能のみ影響

### 1.4 Redis移行時の注意点

#### データ一貫性要件
- **原子性**: 認証情報は一括更新必須
- **整合性**: `user_role` と `account_type` の矛盾防止
- **持続性**: 認証状態の確実な永続化

#### セキュリティ要件
- **暗号化**: `session_token` の Redis内暗号化
- **TTL管理**: 認証情報の適切な期限管理
- **アクセス制御**: Redis認証情報への厳格なアクセス制御

---

## 📋 2. Category B: 翻訳状態（High Priority）

### 2.1 翻訳処理データ
| セッションキー | 設定箇所 | 参照箇所 | データサイズ | 更新頻度 |
|----------------|----------|----------|--------------|----------|
| `source_lang` | app.py:2109 | 言語設定・翻訳処理 | 3-5バイト | 翻訳毎 |
| `target_lang` | app.py:2110 | 言語設定・翻訳処理 | 3-5バイト | 翻訳毎 |
| `language_pair` | app.py:2111 | 翻訳エンジン選択 | 6-10バイト | 翻訳毎 |
| `input_text` | app.py:2112 | 翻訳対象テキスト | 100-2000バイト | 入力毎 |
| `partner_message` | app.py:2113 | コンテキスト情報 | 50-500バイト | 翻訳毎 |
| `context_info` | app.py:2114 | 詳細コンテキスト | 100-1000バイト | 翻訳毎 |

### 2.2 分析・エンジン関連
| セッションキー | 設定箇所 | 参照箇所 | データサイズ | 更新頻度 |
|----------------|----------|----------|--------------|----------|
| `analysis_engine` | app.py:2552<br>engine_management.py:72 | エンジン選択・処理 | 10-20バイト | 設定変更時 |
| `gemini_3way_analysis` | app.py:2588,2590 | 分析結果表示 | 1000-5000バイト | 分析実行時 |
| `translation_context` | context_manager.py:42 | 翻訳コンテキスト | 200-800バイト | コンテキスト設定時 |

### 2.3 データサイズと最適化ポイント

#### サイズ分析
```
小容量（< 50バイト）: source_lang, target_lang, language_pair, analysis_engine
中容量（50-500バイト）: partner_message, translation_context  
大容量（> 500バイト）: input_text, context_info, gemini_3way_analysis
```

#### 最適化戦略
- **圧縮**: 大容量データ（`gemini_3way_analysis`）のgzip圧縮
- **分割**: 分析結果の段階的読み込み
- **キャッシュ**: 頻繁にアクセスされる翻訳設定のローカルキャッシュ

### 2.4 StateManager連携設計

#### フロントエンド状態との統合
```javascript
// 翻訳状態のRedis同期
stateManager.states.translation = {
  sourceLanguage: Redis['session:translation:source_lang'],
  targetLanguage: Redis['session:translation:target_lang'],
  inputText: Redis['session:translation:input_text'],
  analysisEngine: Redis['session:translation:analysis_engine']
};
```

---

## 📋 3. Category C: セキュリティ状態（Critical Priority）

### 3.1 CSRF・セキュリティ管理
| セッションキー | 設定箇所 | 参照箇所 | セキュリティ要件 | Redis優先度 |
|----------------|----------|----------|------------------|-------------|
| `csrf_token` | protection.py:22<br>admin_routes.py:542<br>app.py:3517,3553 | 全フォーム送信 | 高セキュリティ | **Critical** |
| `session_created` | session_security.py:39 | セッション有効期限 | 改竄防止 | **High** |

### 3.2 セキュリティ要件

#### CSRF保護要件
- **一意性**: 各リクエストでの一意トークン生成
- **期限管理**: 適切なトークン有効期限
- **検証**: サーバーサイドでの厳格な検証

#### 暗号化・保護戦略
```python
# Redis内CSRFトークン暗号化
REDIS_SECURITY_CONFIG = {
    'csrf_encryption': True,
    'token_rotation': 3600,  # 1時間毎にローテーション
    'hash_algorithm': 'SHA-256'
}
```

### 3.3 セッション有効期限管理

#### 階層的期限設計
```python
SESSION_TIMEOUTS = {
    'csrf_token': 1800,      # 30分（短期）
    'session_created': 3600,  # 1時間（認証と同期）
    'security_check': 900    # 15分（セキュリティチェック）
}
```

---

## 📋 4. Category D: UI・言語設定状態（Medium Priority）

### 4.1 言語設定管理
| セッションキー | 設定箇所 | 参照箇所 | ライフサイクル | Redis優先度 |
|----------------|----------|----------|----------------|-------------|
| `lang` | app.py:482,1974,2000,2021<br>auth_routes.py:374,491,641,760 | UI表示・多言語化 | セッション中永続 | **Medium** |
| `preferred_lang` | app.py:483<br>auth_routes.py:373,490,640 | 言語設定保存 | セッション中永続 | **Medium** |
| `temp_lang_override` | app.py:1976,2009 | 一時言語切り替え | 一時的 | **Low** |

### 4.2 StateManager統合

#### UI状態のRedis同期
```javascript
// StateManagerとRedisの双方向同期
stateManager.states.ui.language = {
  current: Redis['session:ui:lang'],
  preferred: Redis['session:ui:preferred_lang'],
  temporary: Redis['session:ui:temp_lang_override']
};
```

---

## 📋 5. Category E: 使用量・統計状態（Medium Priority）

### 5.1 使用量管理
| セッションキー | 設定箇所 | 参照箇所 | 更新パターン | Redis優先度 |
|----------------|----------|----------|--------------|-------------|
| `usage_count` | app.py:698<br>auth_routes.py:521 | 使用制限判定 | 使用毎インクリメント | **Medium** |
| `last_usage_date` | app.py:699<br>auth_routes.py:522 | 使用履歴管理 | 日次更新 | **Medium** |
| `avg_rating` | auth_routes.py:1362 | 評価統計 | 評価投稿時 | **Low** |
| `bookmarked_count` | auth_routes.py:1416,1418 | ブックマーク管理 | ブックマーク操作時 | **Low** |

### 5.2 統計データ最適化

#### カウンター最適化
```python
# Redis Atomic Operations活用
pipeline = redis_client.pipeline()
pipeline.hincrby('session:stats:usage_count', session_id, 1)
pipeline.hset('session:stats:last_usage_date', session_id, today)
pipeline.execute()
```

---

## 📋 6. Category F: 動的・その他状態（Low Priority）

### 6.1 動的データ保存
| セッションキー | 設定箇所 | 用途 | データ特性 | Redis優先度 |
|----------------|----------|------|------------|-------------|
| `{動的キー}` | app.py:1018,1025,1157,1980,2981 | 汎用データ保存 | 可変・予測不能 | **Low** |

### 6.2 動的キー管理の課題

#### 現行の問題点
```python
# 予測不可能なセッション構造
session[key] = value  # keyが実行時決定
preserved_data[key] = session[key]  # 全データコピー
```

#### Redis移行時の対応策
- **命名規則**: 動的キーの統一プレフィックス
- **TTL統一**: 動的データの統一期限管理
- **サイズ制限**: 大容量データの自動制限

---

## 🔍 7. カテゴリ間依存関係マトリクス

### 7.1 強依存関係
```
認証(A) ← セキュリティ(C) ← 翻訳(B)
   ↓          ↓              ↓
 UI(D) ← 統計(E) ← 動的データ(F)
```

### 7.2 依存関係の影響度
| 上位カテゴリ | 下位カテゴリ | 影響レベル | 復旧優先度 |
|--------------|--------------|------------|------------|
| 認証(A) | 全カテゴリ | Critical | P0 |
| セキュリティ(C) | 翻訳(B), UI(D) | High | P1 |
| 翻訳(B) | 統計(E) | Medium | P2 |
| UI(D) | 統計(E) | Low | P3 |

---

## ✅ 分類完了確認

### セッション分類統計
- **Category A（認証）**: 10項目 - Critical/High優先度
- **Category B（翻訳）**: 9項目 - High/Medium優先度  
- **Category C（セキュリティ）**: 2項目 - Critical優先度
- **Category D（UI・言語）**: 3項目 - Medium/Low優先度
- **Category E（統計）**: 4項目 - Medium/Low優先度
- **Category F（動的）**: 複数項目 - Low優先度

### 完了項目
- [x] **87箇所セッション使用の完全分類**
- [x] **6カテゴリ28項目の詳細分析**
- [x] **Redis移行優先度の決定**
- [x] **StateManager連携方法の設計**
- [x] **依存関係マトリクスの作成**

**次段階**: StateManager統合計画の詳細設計へ