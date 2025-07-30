/**
 * TaskH2-2(B2-3) Stage 3 Phase 9a: StateManager Implementation
 * 状態管理システムの中央集権化 - Loading Control
 * 
 * 元の場所: templates/index.html showLoading(), hideLoading()
 * 移動理由: 状態管理の一元化、将来的な拡張性確保
 */

// Phase C: Error handling constants
const ERROR_TYPES = {
  NETWORK_ERROR: 'network_error',
  PARSE_ERROR: 'parse_error', 
  TIMEOUT_ERROR: 'timeout_error',
  ABORT_ERROR: 'abort_error',
  API_ERROR: 'api_error',
  UNKNOWN_ERROR: 'unknown_error'
};

/**
 * StateManager Class
 * DOM状態、セッション状態、API状態の統合管理
 * Phase 9aではLoading状態管理から開始
 */
class StateManager {
  constructor() {
    // Loading要素の参照を保持
    this.loadingElement = null;
    this.initialized = false;
    
    // 状態フラグ (Phase 9b拡張)
    this.states = {
      loading: false,                    // ✅ Phase 9a完了済み
      
      // 🆕 Phase 9b追加分
      translationInProgress: false,      // 翻訳実行状態
      resultCards: {                     // 結果カード表示状態
        chatgpt: false,
        gemini: false,
        better: false,
        interactive: false,
        nuance: false
      },
      uiElements: {                      // UI要素表示状態
        analysisEngineTrigger: false,
        geminiNuanceCard: false,
        improvedPanel: false
      },
      
      // 🆕 Phase 9c追加分
      apiCalling: {                      // API呼び出し状態管理
        translateChatGPT: false,
        interactiveQuestion: false,
        nuanceAnalysis: false
      },
      
      // 🆕 Phase C: エラー状態管理追加
      error: false,
      lastError: null,
      errorHistory: [],
      
      // 🆕 Phase 9d: フォーム状態管理追加
      form: {
        isDirty: false,
        fields: {
          japanese_text: { value: '', isDirty: false, originalValue: '' },
          context_info: { value: '', isDirty: false, originalValue: '' },
          partner_message: { value: '', isDirty: false, originalValue: '' },
          language_pair: { value: 'ja-en', isDirty: false, originalValue: 'ja-en' },
          analysis_engine: { value: '', isDirty: false, originalValue: '' }
        },
        lastSaved: null,
        validationErrors: {}
      },
      
      // 🆕 SL-3 Phase 3: 翻訳状態キャッシュ管理
      translation: {
        cache: {},
        syncStatus: {},
        lastSync: null,
        // フィールドマッピング（UI → Redis）
        fieldMapping: {
          'inputText': 'input_text',
          'translatedText': 'translated_text',
          'reverseTranslatedText': 'reverse_translated_text',
          'betterTranslation': 'better_translation',
          'reverseBetterTranslation': 'reverse_better_translation',
          'geminiTranslation': 'gemini_translation',
          'geminiReverseTranslation': 'gemini_reverse_translation',
          'gemini3wayAnalysis': 'gemini_3way_analysis',
          'contextInfo': 'context_info',
          'languagePair': 'language_pair',
          'partnerMessage': 'partner_message'
        }
      }
    };
    
    // 初期化
    this.init();
  }

  /**
   * 初期化処理
   */
  init() {
    // DOM読み込み完了後に要素を取得
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.initElements());
    } else {
      this.initElements();
    }
  }

  /**
   * DOM要素の初期化 (Phase 9b拡張)
   */
  initElements() {
    // Phase 9a: Loading要素
    this.loadingElement = document.getElementById('loading');
    
    // Phase 9b: 結果カード要素
    this.resultCardElements = {
      chatgpt: document.getElementById('chatgpt-result-card'),
      gemini: document.getElementById('gemini-result-card'), 
      better: document.getElementById('better-translation-card'),
      interactive: document.getElementById('interactive-section'),
      nuance: document.getElementById('gemini-nuance-card')
    };
    
    // Phase 9b: UI要素
    this.uiElements = {
      analysisEngineTrigger: document.getElementById('analysis-engine-trigger'),
      geminiNuanceCard: document.getElementById('gemini-nuance-card'),
      improvedPanel: document.getElementById('gemini-improved-result')
    };
    
    // Phase 9d: フォーム要素
    this.formElements = {
      japanese_text: document.getElementById('japanese_text'),
      context_info: document.querySelector('[name="context_info"]'),
      partner_message: document.querySelector('[name="partner_message"]'),
      language_pair: document.getElementById('language_pair'),
      analysis_engine: document.getElementById('analysis_engine')
    };
    
    // Phase 9d: フォームイベントリスナーの設定
    this.initFormEventListeners();
    
    // Phase 9d: ページ離脱時の警告設定
    this.initBeforeUnloadHandler();
    
    // Phase 9d: ページ読み込み時のセッション復元
    this.loadFormFromSession();
    
    this.initialized = !!this.loadingElement;
    
    if (this.initialized) {
      // 初期化完了後にステータス表示
      setTimeout(() => {
      }, 0);
    } else {
      console.warn('⚠️ StateManager: Loading element not found - fallback mode');
    }
  }

  /**
   * Phase 9d: フォームイベントリスナーの初期化
   */
  initFormEventListeners() {
    Object.keys(this.formElements).forEach(fieldName => {
      const element = this.formElements[fieldName];
      if (element) {
        // 初期値を設定
        const initialValue = element.value || '';
        this.setFormFieldValue(fieldName, initialValue, true);
        
        // inputイベントリスナーを追加
        element.addEventListener('input', (e) => {
          this.setFormFieldValue(fieldName, e.target.value);
        });
        
        // changeイベントリスナーも追加（select要素等）
        element.addEventListener('change', (e) => {
          this.setFormFieldValue(fieldName, e.target.value);
        });
      }
    });
    
  }
  
  /**
   * Phase 9d: ページ離脱時の警告ハンドラー初期化
   */
  initBeforeUnloadHandler() {
    window.addEventListener('beforeunload', (e) => {
      const warning = this.beforeUnloadWarning();
      if (warning) {
        e.preventDefault();
        e.returnValue = warning; // 標準仕様
        return warning; // レガシー対応
      }
    });
    
  }
  
  /**
   * Loading状態を表示
   * 元: showLoading() (index.html lines 665-668)
   */
  showLoading() {
    if (!this.loadingElement) {
      this.loadingElement = document.getElementById('loading');
    }
    
    if (this.loadingElement) {
      this.loadingElement.classList.add('show');
      this.states.loading = true;
      console.log('🔄 Loading state: ON');
    } else {
      console.warn('StateManager: Cannot show loading - element not found');
    }
  }

  /**
   * Loading状態を非表示
   * 元: hideLoading() (index.html lines 670-673)
   */
  hideLoading() {
    if (!this.loadingElement) {
      this.loadingElement = document.getElementById('loading');
    }
    
    if (this.loadingElement) {
      this.loadingElement.classList.remove('show');
      this.states.loading = false;
      console.log('✅ Loading state: OFF');
    } else {
      console.warn('StateManager: Cannot hide loading - element not found');
    }
  }

  /**
   * 現在のLoading状態を取得
   */
  isLoading() {
    return this.states.loading;
  }

  /**
   * 状態の強制リセット（エラー回復用）
   */
  resetLoadingState() {
    this.hideLoading();
    console.log('🔄 Loading state forcefully reset');
  }

  // ================================================================
  // Phase 9b: 翻訳状態制御メソッド
  // ================================================================

  /**
   * 翻訳処理開始
   */
  startTranslation() {
    this.states.translationInProgress = true;
    console.log('🚀 Translation state: STARTED');
  }

  /**
   * 翻訳処理完了
   */
  completeTranslation() {
    this.states.translationInProgress = false;
    console.log('✅ Translation state: COMPLETED');
  }

  /**
   * 翻訳実行中状態の取得
   */
  isTranslationInProgress() {
    return this.states.translationInProgress;
  }

  // ================================================================
  // Phase 9b: 結果カード状態制御メソッド
  // ================================================================

  /**
   * 結果カードを表示
   * @param {string} cardName - カード名 (chatgpt, gemini, better, interactive, nuance)
   */
  showResultCard(cardName) {
    const element = this.resultCardElements[cardName];
    if (element) {
      element.classList.add('show');
      this.states.resultCards[cardName] = true;
      console.log(`🎯 Result card shown: ${cardName}`);
    } else {
      console.warn(`⚠️ StateManager: Result card element not found: ${cardName}`);
    }
  }

  /**
   * 結果カードを非表示
   * @param {string} cardName - カード名 (chatgpt, gemini, better, interactive, nuance)
   */
  hideResultCard(cardName) {
    const element = this.resultCardElements[cardName];
    if (element) {
      element.classList.remove('show');
      this.states.resultCards[cardName] = false;
      console.log(`🔄 Result card hidden: ${cardName}`);
    } else {
      console.warn(`⚠️ StateManager: Result card element not found: ${cardName}`);
    }
  }

  /**
   * 全結果カードをリセット
   */
  resetAllResultCards() {
    Object.keys(this.states.resultCards).forEach(cardName => {
      this.hideResultCard(cardName);
    });
    console.log('🧹 All result cards reset');
  }

  /**
   * 結果カード状態の取得
   */
  getResultCardStates() {
    return { ...this.states.resultCards };
  }

  // ================================================================
  // Phase 9c: API呼び出し状態制御メソッド
  // ================================================================

  /**
   * API呼び出し開始（二重実行防止の核心機能）
   * @param {string} apiName - API名 (translateChatGPT, interactiveQuestion, nuanceAnalysis)
   * @returns {boolean} - 実行可能かどうか
   */
  startApiCall(apiName) {
    // 🔒 Critical Security: 二重実行防止チェック
    if (this.states.apiCalling[apiName]) {
      console.warn(`⚠️ API call already in progress: ${apiName} - preventing double execution`);
      return false;
    }
    
    this.states.apiCalling[apiName] = true;
    console.log(`🚀 API call started: ${apiName}`);
    return true;
  }

  /**
   * API呼び出し完了
   * @param {string} apiName - API名
   */
  completeApiCall(apiName) {
    this.states.apiCalling[apiName] = false;
    console.log(`✅ API call completed: ${apiName}`);
  }

  /**
   * API呼び出し中かどうかを確認
   * @param {string} apiName - API名
   * @returns {boolean}
   */
  isApiCalling(apiName) {
    return this.states.apiCalling[apiName];
  }

  /**
   * 全てのAPI呼び出し状態をリセット（エラー回復用）
   */
  resetAllApiCalls() {
    Object.keys(this.states.apiCalling).forEach(apiName => {
      this.states.apiCalling[apiName] = false;
    });
    console.log('🧹 All API calls reset');
  }

  // ================================================================
  // Phase 9b: UI要素状態制御メソッド
  // ================================================================

  /**
   * UI要素を表示
   * @param {string} elementName - 要素名 (analysisEngineTrigger, geminiNuanceCard, improvedPanel)
   */
  showUIElement(elementName) {
    const element = this.uiElements[elementName];
    if (element) {
      if (elementName === 'analysisEngineTrigger') {
        element.style.display = 'flex';
        element.style.justifyContent = 'center';
      } else {
        element.style.display = 'block';
      }
      this.states.uiElements[elementName] = true;
      console.log(`🎯 UI element shown: ${elementName}`);
    } else {
      console.warn(`⚠️ StateManager: UI element not found: ${elementName}`);
    }
  }

  /**
   * UI要素を非表示
   * @param {string} elementName - 要素名 (analysisEngineTrigger, geminiNuanceCard, improvedPanel)
   */
  hideUIElement(elementName) {
    const element = this.uiElements[elementName];
    if (element) {
      element.style.display = 'none';
      this.states.uiElements[elementName] = false;
      console.log(`🔄 UI element hidden: ${elementName}`);
    } else {
      console.warn(`⚠️ StateManager: UI element not found: ${elementName}`);
    }
  }

  /**
   * 全UI要素をリセット
   */
  resetAllUIElements() {
    Object.keys(this.states.uiElements).forEach(elementName => {
      this.hideUIElement(elementName);
    });
    console.log('🧹 All UI elements reset');
  }

  /**
   * StateManagerの現在状態を取得（開発・デバッグ用）
   * @returns {Object} 状態情報オブジェクト
   */
  getStatus() {
    return {
      initialized: this.initialized,
      loadingElement: !!this.loadingElement,
      currentLoadingState: this.loadingElement?.classList.contains('show') || false,
      elementId: this.loadingElement?.id || 'not found',
      
      // Phase 9b: 新しい状態情報
      translationInProgress: this.states.translationInProgress,
      resultCards: { ...this.states.resultCards },
      uiElements: { ...this.states.uiElements },
      
      // Phase 9c: API状態情報
      apiCalling: { ...this.states.apiCalling },
      
      timestamp: new Date().toISOString(),
      phase: '9c - API State Management Integrated'
    };
  }

  /**
   * StateManager動作テスト（開発用）
   */
  testStateManager() {
    
    // Phase 9a テスト
    this.showLoading();
    setTimeout(() => {
      this.hideLoading();
      
      // Phase 9b テスト開始
      
      // 翻訳状態テスト
      this.startTranslation();
      setTimeout(() => {
        this.completeTranslation();
        
        // 結果カードテスト
        this.showResultCard('chatgpt');
        setTimeout(() => {
          this.hideResultCard('chatgpt');
          
          // UI要素テスト
          this.showUIElement('analysisEngineTrigger');
          setTimeout(() => {
            this.hideUIElement('analysisEngineTrigger');
            
            
            // Phase 9c テスト開始
            
            // API状態テスト
            
            const canStart = this.startApiCall('translateChatGPT');
            
            const canStartDouble = this.startApiCall('translateChatGPT');
            
            this.completeApiCall('translateChatGPT');
            
          }, 200);
        }, 200);
      }, 200);
    }, 1000);
    
    return 'Phase 9c test initiated - check console for results';
  }

  /**
   * Phase C: API エラーの統一処理
   * @param {Error} error - エラーオブジェクト
   * @param {Object} context - エラーコンテキスト情報
   */
  handleApiError(error, context = {}) {
    try {
      // エラー情報の構築
      const errorInfo = {
        timestamp: new Date().toISOString(),
        message: error.message || 'Unknown error',
        stack: error.stack,
        context: context,
        errorType: context.errorType || ERROR_TYPES.UNKNOWN_ERROR
      };
      
      // エラー状態の更新
      this.states.error = true;
      this.states.lastError = errorInfo;
      this.states.errorHistory.push(errorInfo);
      
      // エラー履歴のサイズ制限（最新20件のみ保持）
      if (this.states.errorHistory.length > 20) {
        this.states.errorHistory = this.states.errorHistory.slice(-20);
      }
      
      // コンソールログ出力（統一フォーマット）
      console.error('🔧 StateManager: API Error Processed', {
        function: context.function || 'unknown',
        apiType: context.apiType || 'unknown',
        location: context.location || 'unknown',
        errorType: errorInfo.errorType,
        message: errorInfo.message,
        timestamp: errorInfo.timestamp
      });
      
      // UI通知（showToast使用）
      if (typeof showToast === 'function') {
        const userMessage = this.formatErrorMessage(errorInfo);
        showToast(userMessage, 'error');
      }
      
      // Loading状態のクリア（エラー時は確実にLoading解除）
      if (this.states.loading) {
        this.hideLoading();
      }
      
      return errorInfo;
      
    } catch (handlingError) {
      console.error('🚨 StateManager: Error in handleApiError:', handlingError);
      return null;
    }
  }

  /**
   * エラーメッセージのユーザー向けフォーマット
   * @param {Object} errorInfo - エラー情報
   * @returns {string} - ユーザー向けメッセージ
   */
  formatErrorMessage(errorInfo) {
    const { errorType, context } = errorInfo;
    
    switch (errorType) {
      case ERROR_TYPES.NETWORK_ERROR:
        return 'ネットワークエラーが発生しました。接続を確認してください。';
      case ERROR_TYPES.TIMEOUT_ERROR:
        return 'タイムアウトが発生しました。しばらく待ってから再試行してください。';
      case ERROR_TYPES.PARSE_ERROR:
        return 'データの処理中にエラーが発生しました。';
      case ERROR_TYPES.API_ERROR:
        return `${context.apiType || 'API'}でエラーが発生しました。`;
      default:
        return 'エラーが発生しました。しばらく待ってから再試行してください。';
    }
  }

  /**
   * エラー状態のクリア
   * @param {string} source - エラーソース（オプション）
   */
  clearError(source = null) {
    this.states.error = false;
    this.states.lastError = null;
    
  }

  /**
   * 現在のエラー状態取得
   * @param {string} source - エラーソース（オプション）
   * @returns {Object} - エラー状態情報
   */
  getErrorState(source = null) {
    return {
      hasError: this.states.error,
      lastError: this.states.lastError,
      errorCount: this.states.errorHistory.length,
      source: source
    };
  }

  /**
   * Phase 9d: フォーム状態管理メソッド群
   */
  
  /**
   * フォーム状態の取得
   * @returns {Object} - フォーム状態全体
   */
  getFormState() {
    return {
      isDirty: this.states.form.isDirty,
      fields: { ...this.states.form.fields },
      lastSaved: this.states.form.lastSaved,
      validationErrors: { ...this.states.form.validationErrors }
    };
  }
  
  /**
   * フォームフィールドの値を設定
   * @param {string} fieldName - フィールド名
   * @param {string} value - 設定する値
   * @param {boolean} updateOriginal - 元の値も更新するか
   */
  setFormFieldValue(fieldName, value, updateOriginal = false) {
    if (!this.states.form.fields[fieldName]) {
      console.warn(`🔧 StateManager: Unknown form field: ${fieldName}`);
      return;
    }
    
    const field = this.states.form.fields[fieldName];
    field.value = value;
    
    // 元の値と比較してdirty状態を更新
    field.isDirty = value !== field.originalValue;
    
    if (updateOriginal) {
      field.originalValue = value;
      field.isDirty = false;
    }
    
    // フォーム全体のdirty状態を更新
    this.updateFormDirtyState();
    
  }
  
  /**
   * フォームデータ一括取得
   * @returns {Object} - フォームフィールドの値のみ
   */
  getFormData() {
    const data = {};
    Object.keys(this.states.form.fields).forEach(fieldName => {
      data[fieldName] = this.states.form.fields[fieldName].value;
    });
    return data;
  }
  
  /**
   * フォームデータ一括設定
   * @param {Object} data - 設定するフォームデータ
   * @param {boolean} updateOriginal - 元の値も更新するか
   */
  setFormData(data, updateOriginal = false) {
    Object.keys(data).forEach(fieldName => {
      if (this.states.form.fields[fieldName]) {
        this.setFormFieldValue(fieldName, data[fieldName], updateOriginal);
      }
    });
    
    if (updateOriginal) {
      this.states.form.lastSaved = new Date().toISOString();
    }
  }
  
  /**
   * フォーム状態のリセット
   * @param {boolean} clearValues - 値もクリアするか
   */
  resetFormState(clearValues = true) {
    Object.keys(this.states.form.fields).forEach(fieldName => {
      const field = this.states.form.fields[fieldName];
      if (clearValues) {
        field.value = '';
        field.originalValue = '';
      } else {
        // 値はそのままで、dirty状態だけリセット
        field.originalValue = field.value;
      }
      field.isDirty = false;
    });
    
    this.states.form.isDirty = false;
    this.states.form.validationErrors = {};
    
  }
  
  /**
   * フォーム全体のdirty状態を更新
   * @private
   */
  updateFormDirtyState() {
    this.states.form.isDirty = Object.values(this.states.form.fields)
      .some(field => field.isDirty);
  }
  
  /**
   * フォームフィールドの値を取得
   * @param {string} fieldName - フィールド名
   * @returns {string|null} - フィールドの値
   */
  getFormFieldValue(fieldName) {
    if (!this.states.form.fields[fieldName]) {
      console.warn(`🔧 StateManager: Unknown form field: ${fieldName}`);
      return null;
    }
    return this.states.form.fields[fieldName].value;
  }
  
  /**
   * フォームのdirty状態を取得
   * @returns {boolean} - フォームが変更されているか
   */
  isFormDirty() {
    return this.states.form.isDirty;
  }
  
  /**
   * Phase 9d: セッション連携メソッド群
   */
  
  /**
   * フォーム状態をローカルストレージに保存
   * @param {string} key - 保存キー（オプション）
   */
  saveFormToSession(key = 'langpont_form_state') {
    try {
      const formData = this.getFormData();
      localStorage.setItem(key, JSON.stringify({
        data: formData,
        timestamp: new Date().toISOString(),
        isDirty: this.states.form.isDirty
      }));
      
    } catch (error) {
      console.error('🚨 StateManager: Failed to save form to session:', error);
    }
  }
  
  /**
   * ローカルストレージからフォーム状態を復元
   * @param {string} key - 復元キー（オプション）
   * @returns {boolean} - 復元に成功したか
   */
  loadFormFromSession(key = 'langpont_form_state') {
    try {
      const saved = localStorage.getItem(key);
      if (!saved) return false;
      
      const { data, timestamp, isDirty } = JSON.parse(saved);
      
      // セッションデータをフォームに復元
      this.setFormData(data, true); // 復元時はoriginalValueも更新
      
      
      return true;
    } catch (error) {
      console.error('🚨 StateManager: Failed to load form from session:', error);
      return false;
    }
  }
  
  /**
   * セッション状態をクリア
   * @param {string} key - クリアキー（オプション）
   */
  clearFormSession(key = 'langpont_form_state') {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error('🚨 StateManager: Failed to clear form session:', error);
    }
  }
  
  /**
   * ページ離脱時の確認
   * @returns {string|undefined} - 確認メッセージまたはundefined
   */
  beforeUnloadWarning() {
    if (this.states.form.isDirty) {
      const message = '未保存の変更があります。ページを離れますか？';
      // 自動保存
      this.saveFormToSession();
      return message;
    }
    return undefined;
  }
  
  // ================================================================
  // 🆕 SL-3 Phase 3: 翻訳状態双方向同期メソッド
  // ================================================================
  
  /**
   * UI側フィールド名をRedisキー名に変換
   * @param {string} uiField - UI側フィールド名
   * @returns {string} - Redisキー名
   */
  getRedisKey(uiField) {
    return this.states.translation.fieldMapping[uiField] || uiField;
  }
  
  /**
   * Redisキー名をUI側フィールド名に変換
   * @param {string} redisKey - Redisキー名
   * @returns {string} - UI側フィールド名
   */
  getUIKey(redisKey) {
    for (const [uiField, mappedRedisKey] of Object.entries(this.states.translation.fieldMapping)) {
      if (mappedRedisKey === redisKey) {
        return uiField;
      }
    }
    return redisKey;
  }
  
  /**
   * Redisから翻訳状態を取得してキャッシュに同期
   * @param {string} sessionId - セッションID（オプション）
   * @returns {Promise<boolean>} - 同期成功フラグ
   */
  async syncFromRedis(sessionId = null) {
    try {
      const response = await fetch('/api/get_translation_state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      });
      
      if (!response.ok) {
        console.warn('🔧 SL-3 Phase 3: Redis sync failed - server error');
        return false;
      }
      
      const data = await response.json();
      
      if (data.success) {
        // Redis形式からUI形式に変換してキャッシュ更新
        for (const [redisKey, value] of Object.entries(data.states || {})) {
          const uiField = this.getUIKey(redisKey);
          
          if (value === null) {
            // TTL期限切れ
            this.states.translation.syncStatus[uiField] = 'expired';
            console.log(`[SyncFromRedis] TTL expired: ${uiField} ← ${redisKey}`);
          } else {
            this.states.translation.cache[uiField] = value;
            this.states.translation.syncStatus[uiField] = 'synced';
            console.log(`[SyncFromRedis] Loaded: ${uiField} ← ${redisKey} | Value: ${String(value).substring(0, 50)}...`);
          }
        }
        
        this.states.translation.lastSync = new Date().toISOString();
        return true;
      }
      
      return false;
      
    } catch (error) {
      console.error('🚨 SL-3 Phase 3: syncFromRedis failed:', error);
      return false;
    }
  }
  
  /**
   * UI状態をRedisに同期保存
   * @param {string} field - UI側フィールド名
   * @param {string} value - 保存する値
   * @param {string} sessionId - セッションID（オプション）
   * @returns {Promise<boolean>} - 保存成功フラグ
   */
  async syncToRedis(field, value, sessionId = null) {
    try {
      // 差分検出: 同じ値では保存しない
      if (this.states.translation.cache[field] === value) {
        console.log(`[SyncToRedis] Skipped (same value): ${field} → ${this.getRedisKey(field)}`);
        return true;
      }
      
      const redisKey = this.getRedisKey(field);
      
      const response = await fetch('/api/set_translation_state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          field: redisKey,
          value: value
        })
      });
      
      if (!response.ok) {
        console.error(`[SyncToRedis] Server error: ${field} → ${redisKey} | Status: FAILED`);
        return false;
      }
      
      const data = await response.json();
      
      if (data.success) {
        // 成功時: キャッシュ更新
        this.states.translation.cache[field] = value;
        this.states.translation.syncStatus[field] = 'synced';
        console.log(`[SyncToRedis] Saving: ${field} → ${redisKey} | Status: SUCCESS`);
        return true;
      } else {
        console.error(`[SyncToRedis] Failed: ${field} → ${redisKey} | Status: FAILED | Error: ${data.error || 'unknown'}`);
        return false;
      }
      
    } catch (error) {
      console.error(`[SyncToRedis] Exception: ${field} → ${this.getRedisKey(field)}`, error);
      return false;
    }
  }
  
  /**
   * 翻訳完了後の同期実行
   * @param {Object} translationData - 翻訳データ
   * @param {string} sessionId - セッションID
   */
  async syncTranslationAfterCompletion(translationData, sessionId = null) {
    try {
      const syncPromises = [];
      
      for (const [field, value] of Object.entries(translationData)) {
        if (value && typeof value === 'string') {
          syncPromises.push(this.syncToRedis(field, value, sessionId));
        }
      }
      
      await Promise.all(syncPromises);
      console.log('🔄 SL-3 Phase 3: Translation sync completed');
      
    } catch (error) {
      console.error('🚨 SL-3 Phase 3: Translation sync failed:', error);
    }
  }
  
  /**
   * 翻訳キャッシュの取得
   * @param {string} field - UI側フィールド名
   * @returns {string|null} - キャッシュされた値またはnull
   */
  getTranslationCache(field) {
    return this.states.translation.cache[field] || null;
  }
  
  /**
   * 翻訳キャッシュの設定
   * @param {string} field - UI側フィールド名
   * @param {string} value - 設定する値
   */
  setTranslationCache(field, value) {
    this.states.translation.cache[field] = value;
    this.states.translation.syncStatus[field] = 'local';
  }

  /**
   * 将来の拡張用メソッド（Phase 9b以降）
   */
  // setTranslatingState(state) { ... }
  // getState(key) { ... }
  // setState(key, value) { ... }
}

// グローバルインスタンスの作成
window.StateManager = StateManager;
window.stateManager = new StateManager();

// Phase 9a: Wrap戦略の実装
// 既存のshowLoading/hideLoading関数を保存
const originalShowLoading = window.showLoading;
const originalHideLoading = window.hideLoading;

// 新しい実装で上書き（後方互換性維持）
window.showLoading = function() {
  window.stateManager.showLoading();
};

window.hideLoading = function() {
  window.stateManager.hideLoading();
};

// Phase 9b: グローバル関数のwrap化（後方互換性維持）

// 結果カード制御のwrap関数
window.showResultCard = function(cardName) {
  window.stateManager.showResultCard(cardName);
};

window.hideResultCard = function(cardName) {
  window.stateManager.hideResultCard(cardName);
};

// 翻訳状態制御のwrap関数
window.startTranslation = function() {
  window.stateManager.startTranslation();
};

window.completeTranslation = function() {
  window.stateManager.completeTranslation();
};

window.isTranslationInProgress = function() {
  return window.stateManager.isTranslationInProgress();
};

// UI要素制御のwrap関数
window.showUIElement = function(elementName) {
  window.stateManager.showUIElement(elementName);
};

window.hideUIElement = function(elementName) {
  window.stateManager.hideUIElement(elementName);
};

// Phase 9c: API状態管理のwrap関数

// API状態制御のwrap関数
window.startApiCall = function(apiName) {
  return window.stateManager.startApiCall(apiName);
};

window.completeApiCall = function(apiName) {
  window.stateManager.completeApiCall(apiName);
};

window.isApiCalling = function(apiName) {
  return window.stateManager.isApiCalling(apiName);
};

window.resetAllApiCalls = function() {
  window.stateManager.resetAllApiCalls();
};

// デバッグ用: 元の関数も保持
window._originalShowLoading = originalShowLoading;
window._originalHideLoading = originalHideLoading;

// 🆕 Phase C: エラー処理統合
window.integrateErrorWithStateManager = function(error, context) {
  if (window.stateManager && typeof window.stateManager.handleApiError === 'function') {
    return window.stateManager.handleApiError(error, context);
  } else {
    console.error('🚨 StateManager not available for error handling:', error);
    return null;
  }
};

// 🆕 Phase 9d: フォーム管理のwrap関数
window.getFormData = function() {
  return window.stateManager.getFormData();
};

window.setFormData = function(data, updateOriginal = false) {
  return window.stateManager.setFormData(data, updateOriginal);
};

window.getFormFieldValue = function(fieldName) {
  return window.stateManager.getFormFieldValue(fieldName);
};

window.setFormFieldValue = function(fieldName, value, updateOriginal = false) {
  return window.stateManager.setFormFieldValue(fieldName, value, updateOriginal);
};

window.resetFormState = function(clearValues = true) {
  return window.stateManager.resetFormState(clearValues);
};

window.isFormDirty = function() {
  return window.stateManager.isFormDirty();
};

window.saveFormToSession = function(key) {
  return window.stateManager.saveFormToSession(key);
};

window.loadFormFromSession = function(key) {
  return window.stateManager.loadFormFromSession(key);
};

window.clearFormSession = function(key) {
  return window.stateManager.clearFormSession(key);
};

// 🆕 SL-3 Phase 3: 翻訳状態同期のwrap関数
window.syncFromRedis = function(sessionId) {
  return window.stateManager.syncFromRedis(sessionId);
};

window.syncToRedis = function(field, value, sessionId) {
  return window.stateManager.syncToRedis(field, value, sessionId);
};

window.getTranslationCache = function(field) {
  return window.stateManager.getTranslationCache(field);
};

window.setTranslationCache = function(field, value) {
  return window.stateManager.setTranslationCache(field, value);
};

window.syncTranslationAfterCompletion = function(translationData, sessionId) {
  return window.stateManager.syncTranslationAfterCompletion(translationData, sessionId);
};

