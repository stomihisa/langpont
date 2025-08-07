# Task #9-3 AP-1 Phase 3 調査レポート
## /get_nuance, /interactive_question Blueprint統合 & StateManager調査

**調査日:** 2025年8月6日  
**調査対象:** 分析系2API (/get_nuance, /interactive_question) のBlueprint化前提調査  
**目的:** TranslationStateManager統合による状態保持一元化の検討

---

## (A) /get_nuance の調査結果

### **実装場所**
- **場所:** `app.py` L2701-L2976 (約276行)
- **ルート:** `@app.route("/get_nuance", methods=["POST"])`
- **現状:** **app.py内の直接実装** (Blueprint化なし)

### **使用API・LLMエンジン**
- **マルチエンジン対応:** ChatGPT、Gemini、Claude
- **デフォルトエンジン:** Gemini
- **エンジン選択方法:**
  - POST body: `data.get('engine', session.get('analysis_engine', 'gemini'))`
  - セッション保存: `session['analysis_engine'] = selected_engine`
- **API統合:**
  - **Gemini:** `f_gemini_3way_analysis()` 関数 (L2746)
  - **ChatGPT/Claude:** `AnalysisEngineManager.analyze_translations()` (L2749-2764)

### **入力と出力フォーマット**

#### **入力データ取得**
```python
# SL-3 Phase 2: Redis + Session フォールバック
if translation_state_manager and session_id:
    translated_text = translation_state_manager.get_large_data("translated_text", session_id, 
                                                             default=session.get("translated_text", ""))
    better_translation = translation_state_manager.get_large_data("better_translation", session_id, 
                                                                default=session.get("better_translation", ""))
    gemini_translation = translation_state_manager.get_large_data("gemini_translation", session_id, 
                                                                default=session.get("gemini_translation", ""))
else:
    # フォールバック: セッションから取得
    translated_text = session.get("translated_text", "")
    # ...
```

#### **出力JSON形式**
```json
{
  "nuance": "分析結果テキスト",
  "analysis_engine": "選択されたエンジン名",
  "recommendation": {
    "result": "推奨結果",
    "confidence": 0.85,
    "method": "extraction_method",
    "source": "server_side_engine_extraction",
    "engine": "エンジン名"
  },
  "chatgpt_prompt": "使用されたプロンプト（オプション）"
}
```

### **内部処理と連携サービス**
- **AnalysisEngineManager:** Claude/ChatGPT分析実行
- **TranslationStateManager:** Redis大容量データ取得・保存
- **TranslationContext:** コンテキスト保存 (`TranslationContext.save_context()`)
- **推奨抽出:** `extract_recommendation_from_analysis()`
- **活動ログ:** `log_analysis_activity()`, `log_gemini_analysis()`
- **Task 2.9.2分析:** `advanced_analytics.log_task292_extraction()`

### **現行のセキュリティレベル**
- ✅ **CSRF保護:** `@csrf_protect`
- ✅ **レート制限:** `@require_rate_limit`
- ✅ **入力検証:** 翻訳データの存在確認
- ✅ **セキュリティログ:** `log_access_event`, `log_security_event`

### **状態管理フロー**
1. **データ取得:** TranslationStateManager → Session (フォールバック)
2. **分析実行:** エンジン別API呼び出し
3. **結果保存:** Redis大容量データ保存 (`save_large_data()`)
4. **コンテキスト保存:** TranslationContext統合

---

## (B) /interactive_question の調査結果

### **実装場所**
- **場所:** `app.py` L3036-L3151 (約116行)
- **ルート:** `@app.route("/interactive_question", methods=["POST"])`
- **現状:** **app.py内の直接実装** (Blueprint化なし)

### **使用LLM**
- **Claude専用:** `interactive_processor = LangPontTranslationExpertAI(client)`
- **グローバルインスタンス:** app.py L1630で初期化
- **処理メソッド:** `interactive_processor.process_question(question, context)`

### **入力の保持元**
- **コンテキスト取得:** `context = TranslationContext.get_context()`
- **セッション表示言語:** `display_lang = session.get("lang", "jp")`
- **入力データ:** `data = request.get_json()` → `question = data.get("question")`

### **処理内容**
- **入力検証:** `EnhancedInputValidator.validate_text_input()` (max_length=1000, min_length=5)
- **多言語エラー:** 4言語対応エラーメッセージ (jp/en/fr/es)
- **プロセッサー:** `LangPontTranslationExpertAI.process_question()`
- **回答最適化:** Cookie最適化による文字数制限 (max_answer_length=2500)

### **出力JSON形式**
```json
{
  "success": true,
  "result": {
    "result": "AI回答テキスト",
    "type": "質問タイプ"
  },
  "current_chat": {
    "question": "質問テキスト",
    "answer": "回答テキスト",
    "type": "general",
    "timestamp": 1691234567
  }
}
```

### **Claude連携詳細**
- **実装クラス:** `translation.expert_ai.LangPontTranslationExpertAI`
- **メソッド:** `process_question()` → `process_question_safe()`
- **依存注入設計:** EnhancedInputValidator, log_security_event, adapters使用
- **アダプター:** `SessionContextAdapter`, `SafeLoggerAdapter`

### **ログ/エラー処理**
- ✅ **セキュリティログ:** `log_security_event('INVALID_INTERACTIVE_QUESTION')`
- ✅ **アクセスログ:** `log_access_event('Interactive question processed')`
- ✅ **エラー処理:** try-catch with traceback logging
- ✅ **処理時間計測:** `processing_time = time.time() - start_time`

### **現行のセキュリティレベル**
- ✅ **CSRF保護:** `@csrf_protect`
- ✅ **レート制限:** `@require_rate_limit`
- ✅ **入力検証:** EnhancedInputValidator (質問長・文字検証)
- ✅ **多言語対応:** エラーメッセージ4言語対応

---

## (C) TranslationStateManager の調査結果

### **実装場所**
- **ファイル:** `services/translation_state_manager.py`
- **クラス:** `TranslationStateManager`
- **初期化:** app.py L243-250で条件付き初期化

### **現在の機能**

#### **基本状態管理**
```python
# 基本メソッド
def set_translation_state(session_id, field_name, value, ttl=None) -> bool
def get_translation_state(session_id, field_name, default_value=None) -> Any
def clear_translation_state(session_id, field_name) -> bool
def get_multiple_states(session_id, field_names, default_values=None) -> Dict
```

#### **大容量データ管理 (SL-3 Phase 2)**
```python
# 大容量データ用メソッド
def save_large_data(field_name, data, session_id, ttl=None) -> bool
def get_large_data(field_name, session_id, default=None) -> str
def save_multiple_large_data(session_id, data_dict) -> bool
```

#### **TTL設定**
- **STATE_TTL:** 3600秒（1時間）- 言語設定等
- **INPUT_TTL:** 1800秒（30分）- 入力データ・翻訳結果

#### **キャッシュキー管理**
```python
CACHE_KEYS = {
    # 翻訳状態系（長期保持）
    'language_pair': {'ttl': STATE_TTL, 'type': 'state'},
    'source_lang': {'ttl': STATE_TTL, 'type': 'state'}, 
    'target_lang': {'ttl': STATE_TTL, 'type': 'state'},
    # 入力データ系（短期保持）
    'input_text': {'ttl': INPUT_TTL, 'type': 'input'},
    'partner_message': {'ttl': INPUT_TTL, 'type': 'input'},
    'context_info': {'ttl': INPUT_TTL, 'type': 'input'},
}

LARGE_DATA_KEYS = {
    # 翻訳結果系
    'translated_text': {'ttl': INPUT_TTL, 'type': 'translation'},
    'better_translation': {'ttl': INPUT_TTL, 'type': 'translation'},
    'gemini_translation': {'ttl': INPUT_TTL, 'type': 'translation'},
    # 分析結果系
    'gemini_3way_analysis': {'ttl': INPUT_TTL, 'type': 'analysis'},
}
```

### **現行の使用元**

#### **エンドポイント別使用状況**
| エンドポイント | 使用状況 | 詳細 |
|---------------|----------|------|
| **/translate_chatgpt** | ✅ **使用中** | routes/translation.py L268-279でRedis保存 |
| **/get_nuance** | ✅ **使用中** | 大容量データ取得・保存 (L2709-2786) |
| **/interactive_question** | ❌ **未使用** | TranslationContextのみ使用 |
| **/translate_gemini** | ✅ **使用中** | routes/translation.py L474-480でRedis保存 |

#### **実際の状態フロー**
```python
# 1. 翻訳エンドポイントでの保存
redis_data = {
    "translated_text": translated,
    "better_translation": better_translation,
    "gemini_translation": gemini_translation
}
translation_state_manager.save_multiple_large_data(session_id, redis_data)

# 2. get_nuanceでの取得
translated_text = translation_state_manager.get_large_data("translated_text", session_id, 
                                                         default=session.get("translated_text", ""))
```

### **SessionRedisManager統合**
- **Redis基盤:** `services.session_redis_manager.get_session_redis_manager()`
- **接続管理:** `self.redis_manager.is_connected`
- **フォールバック:** Redis接続失敗時は自動的にFalse返却

### **TranslationContextとの違い**

| 項目 | TranslationStateManager | TranslationContext |
|------|------------------------|-------------------|
| **保存先** | Redis (TTL管理) | Session (Cookie) |
| **データ種別** | 翻訳結果・状態データ | コンテキスト・メタデータ |
| **TTL** | 30分-1時間 | セッション持続 |
| **容量制限** | Redis制限 | Cookie 4KB制限 |
| **用途** | 大容量翻訳データ | 軽量コンテキスト |

---

## 📋 Blueprint化の課題推定

### **実装上の課題**

#### **1. /get_nuance Blueprint化課題**
- **巨大関数:** 276行の複雑な処理を適切に分割
- **グローバル依存:** 複数のグローバル変数・サービス依存
- **状態管理複雑:** Redis + Session フォールバック機構
- **ログ処理統合:** 複数のログシステム統合

#### **2. /interactive_question Blueprint化課題**
- **Claude専用:** `interactive_processor`グローバルインスタンス
- **TranslationContext依存:** context_managerとの連携
- **多言語処理:** エラーメッセージ・レスポンス多言語化

#### **3. TranslationStateManager統合課題**
- **使用格差:** get_nuanceは全面使用、interactive_questionは未使用
- **状態フロー統一:** TranslationContextとの役割分担
- **セッションID管理:** 一貫したセッション識別子取得

### **Blueprint化実装方針**

#### **推奨アプローチ**
1. **段階的分離:**
   - Phase 3a: /get_nuance Blueprint分離 + StateManager統合
   - Phase 3b: /interactive_question Blueprint分離 + StateManager統合

2. **依存注入設計:**
   ```python
   # services/analysis_service.py (新規作成)
   class AnalysisService:
       def __init__(self, translation_state_manager, analysis_engine_manager, 
                    interactive_processor, logger):
   
   # routes/analysis.py (新規作成)  
   analysis_bp = Blueprint('analysis', __name__)
   ```

3. **StateManager統合:**
   - 分析結果の統一保存: `analysis_results`キー
   - インタラクティブ履歴: `interactive_history`キー
   - コンテキスト統合: TranslationContextからStateManagerへの移行

#### **状態管理統一化**
```python
# 統合後の理想的な状態フロー
StateManager.save_analysis_data(session_id, {
    'nuance_analysis': analysis_result,
    'recommendation': recommendation_data,
    'interactive_qa': qa_history,
    'context_metadata': context_info
})
```

---

## 🎯 結論

### **重要な発見**
1. **両エンドポイントとも app.py内直接実装** (Blueprint化なし)
2. **TranslationStateManager部分使用** (get_nuanceのみ、interactive_questionは未使用)
3. **状態管理が分散** (StateManager + TranslationContext + Session)
4. **依存関係が複雑** (グローバル変数・サービス・ログシステム)

### **Blueprint化の効果予測**
- **コード削減:** app.pyから約392行削減 (get_nuance 276行 + interactive_question 116行)
- **保守性向上:** 分析機能の責務分離・テスト容易性
- **状態管理統一:** TranslationStateManagerによる一元管理
- **拡張性確保:** 新しい分析機能追加の標準パターン

### **次フェーズ実装準備**
Task #9-3 AP-1 Phase 3の実装に向けて、全ての前提情報が整いました。段階的なBlueprint化により、LangPontの分析機能アーキテクチャを大幅に改善できる見込みです。

---

**📅 調査完了日:** 2025年8月6日  
**📊 対象行数:** get_nuance (276行) + interactive_question (116行) = 392行  
**🎯 Blueprint化準備:** 完了  
**🔄 次段階:** Phase 3実装開始可能