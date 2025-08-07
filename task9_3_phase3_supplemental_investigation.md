# Task #9-3 AP-1 Phase 3 補足調査レポート
## Blueprint化と状態管理統合のための詳細調査

**調査日:** 2025年8月6日  
**目的:** /get_nuance, /interactive_question Blueprint化実装前の必須情報収集

---

## 🔍 調査項目 1：依存構造の明示とモジュールマッピング

### **AnalysisEngineManager**

#### **定義情報**
- **ファイル:** `translation/analysis_engine.py`
- **クラス定義:** L19-451 (433行)
- **初期化:** `__init__(self, claude_client=None, app_logger=None, f_gemini_3way_analysis=None)`

#### **主要メソッド**
| メソッド名 | 行番号 | 用途 |
|-----------|--------|------|
| `get_engine_status(engine)` | L36 | エンジン利用可能状況確認 |
| `analyze_translations(...)` | L66 | 選択エンジンで翻訳分析実行 |
| `_chatgpt_analysis(...)` | L107 | ChatGPT専用分析 |
| `_gemini_analysis(...)` | L244 | Gemini専用分析（f_gemini_3way_analysis使用） |
| `_claude_analysis(...)` | L272 | Claude専用分析 |

#### **LLMとの接続関係**
```python
# ChatGPT: 直接OpenAI API呼び出し (L213-226)
openai.chat.completions.create(model="gpt-3.5-turbo", ...)

# Gemini: 既存関数経由 (L248-249)
self.f_gemini_3way_analysis(chatgpt_trans, enhanced_trans, gemini_trans)

# Claude: claude_client経由 (L404-412)
self.claude_client.messages.create(model="claude-3-5-sonnet-20241022", ...)
```

### **LangPontTranslationExpertAI**

#### **定義情報**
- **ファイル:** `translation/expert_ai.py`
- **クラス定義:** L13-584
- **用途:** インタラクティブ質問処理・翻訳エキスパートAI

#### **主要メソッド**
| メソッド名 | 行番号 | 用途 |
|-----------|--------|------|
| `process_question(question, context)` | L569 | Flask環境用エントリーポイント |
| `process_question_safe(...)` | L533 | 依存注入版処理（実際の処理） |
| `_categorize_question(...)` | L67 | 質問タイプ分類 |
| `_handle_xxx_question(...)` | 複数 | タイプ別質問処理 |

### **interactive_processor**

#### **初期化場所**
```python
# app.py L1629-1630
from translation.expert_ai import LangPontTranslationExpertAI
interactive_processor = LangPontTranslationExpertAI(client)
```

#### **利用箇所**
- **app.py L3102:** `result = interactive_processor.process_question(question, context)`
- **グローバルインスタンス:** Claude APIクライアント（`client`）を渡して初期化

### **下請け関数群**

#### **log_analysis_activity**
- **定義ファイル:** `activity_logger.py` L587-589
- **用途:** 統合活動ログ記録
- **Blueprint移行:** ❌ 不要（グローバル関数として維持）

#### **extract_recommendation_from_analysis**
- **定義ファイル:** `analysis/recommendation.py` L18-164
- **用途:** 分析結果から推奨抽出（ChatGPT使用）
- **Blueprint移行:** ✅ 必要（分析サービスの一部として）

#### **f_gemini_3way_analysis**
- **定義場所:** `app.py` L1408
- **用途:** Gemini 3way分析実行
- **Blueprint移行:** ✅ 必要（services/analysis_service.pyへ）

#### **save_gemini_analysis_to_db**
- **定義場所:** `app.py` L2598
- **用途:** 分析結果DB保存
- **Blueprint移行:** ✅ 必要（分析サービスの一部として）

#### **log_gemini_analysis**
- **定義ファイル:** `admin_logger.py` L364
- **用途:** 管理者ログ記録
- **Blueprint移行:** ❌ 不要（admin_loggerインポートで解決）

#### **get_translation_state**
- **定義場所:** `app.py` L1167
- **用途:** 翻訳状態取得ヘルパー関数
- **Blueprint移行:** ✅ 必要（状態管理ユーティリティとして）

---

## 🔍 調査項目 2：TranslationContext → TranslationStateManager 移行戦略

### **interactive_questionでのTranslationContext使用状況**

#### **現在の実装**
```python
# app.py L3089
context = TranslationContext.get_context()

# 取得される構造（context_manager.py L69-90）
{
    "context_id": "uuid",
    "timestamp": 1234567890,
    "created_at": "2025-08-06T...",
    "input_text": session.get("input_text", ""),
    "translations": {
        "chatgpt": session.get("translated_text", ""),
        "enhanced": session.get("better_translation", ""),
        "gemini": session.get("gemini_translation", ""),
        "chatgpt_reverse": session.get("reverse_translated_text", ""),
        "enhanced_reverse": session.get("reverse_better_translation", ""),
        "gemini_reverse": session.get("gemini_reverse_translation", "")
    },
    "analysis": session.get("gemini_3way_analysis", ""),
    "metadata": {
        "source_lang": context.get("source_lang", ""),
        "target_lang": context.get("target_lang", ""),
        "partner_message": session.get("partner_message", ""),
        "context_info": session.get("context_info", "")
    }
}
```

### **TranslationStateManager対応構造**

#### **既存のキー体系**
```python
# translation_state_manager.py
CACHE_KEYS = {
    'language_pair', 'source_lang', 'target_lang',  # 状態系
    'input_text', 'partner_message', 'context_info'  # 入力系
}

LARGE_DATA_KEYS = {
    'translated_text', 'reverse_translated_text',
    'better_translation', 'reverse_better_translation',
    'gemini_translation', 'gemini_reverse_translation',
    'gemini_3way_analysis'  # 分析結果
}
```

### **移行実装案**

#### **新メソッド追加案**
```python
# TranslationStateManagerに追加
def get_full_context(self, session_id: str) -> Dict[str, Any]:
    """TranslationContext.get_context()互換メソッド"""
    # 全データを一括取得してcontext構造を再構築
    
def save_full_context(self, session_id: str, context: Dict[str, Any]) -> bool:
    """コンテキスト全体を保存"""
```

#### **データ互換性**
| TranslationContext | TranslationStateManager | 対応状況 |
|-------------------|------------------------|----------|
| session保存 | Redis保存 | ✅ 移行可能 |
| Cookie 4KB制限 | Redis制限なし | ✅ 改善 |
| context_id/timestamp | メタデータとして保存可能 | ✅ 対応可能 |
| 階層構造 | フラット構造 | ⚠️ 変換必要 |

---

## 🔍 調査項目 3：API仕様・レスポンス形式の確認

### **/get_nuance レスポンス形式**

#### **現行レスポンス構造**
```json
{
  "nuance": "分析結果テキスト（最大3000文字）",
  "analysis_engine": "gemini|chatgpt|claude",
  "recommendation": {
    "result": "ChatGPT|Enhanced|Gemini|none",
    "confidence": 0.85,
    "method": "extraction_method",
    "source": "server_side_gemini_extraction",
    "engine": "gemini"
  },
  "chatgpt_prompt": "使用されたプロンプト（オプション）"
}
```

#### **フロントエンド依存箇所**
- **templates/index.html L1080:** `fetch("/get_nuance", ...)`
- **nuance_analysis_internal.js L61:** `el.textContent = analysisText`
- **nuance_analysis_internal.js L75:** `const recommendation = data.recommendation`
- **nuance_analysis_internal.js L70:** `data.analysis_engine`

### **/interactive_question レスポンス形式**

#### **現行レスポンス構造**
```json
{
  "success": true,
  "result": {
    "result": "AI回答テキスト",
    "type": "translation_modification|analysis_inquiry|linguistic_question|..."
  },
  "current_chat": {
    "question": "質問テキスト",
    "answer": "回答テキスト",
    "type": "general",
    "timestamp": 1691234567
  }
}
```

#### **フロントエンド依存箇所**
- **question_handler.js L86:** `fetch('/interactive_question', ...)`
- **question_handler.js L106-122:** Cookie最適化対応処理
- **question_handler.js L119-121:** 新形式current_chat対応

### **Blueprint化後の互換性**

**✅ 完全互換可能**
- レスポンス形式を変更せずにBlueprint化可能
- エンドポイントURLも維持（Blueprint prefix設定で対応）
- フロントエンド修正不要

---

## 🔍 調査項目 4：責務分離と関数再配置の推奨設計

### **推奨ファイル構造**

```
services/
├── analysis_service.py      # 分析ビジネスロジック
└── interactive_service.py   # インタラクティブ質問ロジック

routes/
└── analysis.py             # /get_nuance, /interactive_question ルーティング

utils/
├── analysis_utils.py       # 分析関連ユーティリティ
└── state_helpers.py        # 状態管理ヘルパー関数
```

### **services/analysis_service.py への移動対象**

| 関数/クラス | 現在の場所 | 移動理由 |
|------------|-----------|----------|
| `f_gemini_3way_analysis` | app.py L1408 | Gemini分析ロジック |
| `save_gemini_analysis_to_db` | app.py L2598 | DB保存ロジック |
| `AnalysisEngineManager` | translation/analysis_engine.py | そのまま依存注入 |
| `extract_recommendation_from_analysis` | analysis/recommendation.py | そのまま依存注入 |

#### **AnalysisServiceクラス設計**
```python
class AnalysisService:
    def __init__(self, translation_state_manager, analysis_engine_manager, 
                 claude_client, logger, labels):
        self.state_manager = translation_state_manager
        self.engine_manager = analysis_engine_manager
        self.claude_client = claude_client
        self.logger = logger
        self.labels = labels
    
    def perform_nuance_analysis(self, session_id, selected_engine):
        # get_nuanceのビジネスロジック
    
    def save_analysis_results(self, session_id, analysis_data):
        # 分析結果の保存処理
```

### **services/interactive_service.py への移動対象**

| 関数/クラス | 現在の場所 | 移動理由 |
|------------|-----------|----------|
| `interactive_processor` | app.py L1630 (グローバル) | インスタンス管理 |
| TranslationContext統合ロジック | - | 新規実装 |

#### **InteractiveServiceクラス設計**
```python
class InteractiveService:
    def __init__(self, translation_state_manager, interactive_processor, logger):
        self.state_manager = translation_state_manager
        self.processor = interactive_processor
        self.logger = logger
    
    def process_interactive_question(self, session_id, question, display_lang):
        # interactive_questionのビジネスロジック
```

### **routes/analysis.py への移動対象**

| エンドポイント | 現在の行番号 | 責務 |
|--------------|------------|------|
| `/get_nuance` | app.py L2701-2976 | ルーティング・リクエスト処理 |
| `/interactive_question` | app.py L3036-3151 | ルーティング・リクエスト処理 |

#### **Blueprint実装案**
```python
analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/get_nuance', methods=['POST'])
@csrf_protect
@require_rate_limit
def get_nuance():
    # セッションID取得、サービス呼び出し、レスポンス返却のみ

@analysis_bp.route('/interactive_question', methods=['POST'])
@csrf_protect
@require_rate_limit
def interactive_question():
    # 入力検証、サービス呼び出し、レスポンス返却のみ
```

### **utils/ への移動対象**

#### **utils/state_helpers.py**
- `get_translation_state()` (app.py L1167) - 状態取得ヘルパー

#### **utils/analysis_utils.py**
- 分析結果の切り詰め処理
- エラーメッセージの多言語対応辞書

### **app.pyに残すもの**
- グローバル変数定義（client, claude_client等）
- 初期化処理
- Blueprint登録

---

## 📊 移行影響分析

### **削減行数予測**
- **app.py削減:** 約450行（get_nuance 276行 + interactive_question 116行 + 関連関数）
- **新規追加:** 約350行（サービス層 + ルーティング層）
- **実質削減:** 約100行（重複コード削除効果）

### **リスク評価**
| リスク項目 | 影響度 | 対策 |
|-----------|--------|------|
| セッションID取得ロジックの統一 | 中 | 共通関数化 |
| グローバル変数依存 | 低 | 依存注入で解決済み |
| フロントエンド互換性 | 低 | レスポンス形式維持 |
| Redis接続エラー | 中 | フォールバック実装済み |

### **実装優先順位**
1. **Phase 3a:** /get_nuance Blueprint化（複雑度高）
2. **Phase 3b:** /interactive_question Blueprint化（依存少）
3. **Phase 3c:** TranslationStateManager完全統合

---

**📅 調査完了日:** 2025年8月6日  
**🎯 Blueprint化準備:** 詳細設計完了  
**📊 影響範囲:** 明確化完了  
**🔄 実装開始:** 可能