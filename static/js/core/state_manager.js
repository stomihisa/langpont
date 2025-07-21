/**
 * TaskH2-2(B2-3) Stage 3 Phase 9a: StateManager Implementation
 * 状態管理システムの中央集権化 - Loading Control
 * 
 * 元の場所: templates/index.html showLoading(), hideLoading()
 * 移動理由: 状態管理の一元化、将来的な拡張性確保
 */

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
    
    this.initialized = !!this.loadingElement;
    
    if (this.initialized) {
      console.log('📊 StateManager initialized successfully (Phase 9b) - Complete state management integrated');
      // 初期化完了後にステータス表示
      setTimeout(() => {
        console.log('📊 StateManager Status:', this.getStatus());
      }, 0);
    } else {
      console.warn('⚠️ StateManager: Loading element not found - fallback mode');
    }
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
    console.log('🧪 StateManager Phase 9b Test Methods Available:');
    console.log('- getStatus():', this.getStatus());
    console.log('🧪 Testing Phase 9a (Loading control)...');
    
    // Phase 9a テスト
    this.showLoading();
    setTimeout(() => {
      this.hideLoading();
      console.log('✅ Phase 9a test completed');
      
      // Phase 9b テスト開始
      console.log('🧪 Testing Phase 9b (Complete state management)...');
      
      // 翻訳状態テスト
      this.startTranslation();
      setTimeout(() => {
        console.log('Translation in progress:', this.isTranslationInProgress());
        this.completeTranslation();
        
        // 結果カードテスト
        this.showResultCard('chatgpt');
        setTimeout(() => {
          this.hideResultCard('chatgpt');
          
          // UI要素テスト
          this.showUIElement('analysisEngineTrigger');
          setTimeout(() => {
            this.hideUIElement('analysisEngineTrigger');
            
            console.log('🧪 StateManager Phase 9b test cycle completed');
            
            // Phase 9c テスト開始
            console.log('🧪 Testing Phase 9c (API State Management)...');
            
            // API状態テスト
            console.log('API State Before:', this.states.apiCalling);
            
            const canStart = this.startApiCall('translateChatGPT');
            console.log('First API call allowed:', canStart);
            
            const canStartDouble = this.startApiCall('translateChatGPT');
            console.log('Double API call prevented:', !canStartDouble);
            
            this.completeApiCall('translateChatGPT');
            console.log('API State After Complete:', this.states.apiCalling);
            
            console.log('🧪 StateManager Phase 9c test cycle completed');
            console.log('📊 Final status:', this.getStatus());
          }, 200);
        }, 200);
      }, 200);
    }, 1000);
    
    return 'Phase 9c test initiated - check console for results';
  }

  /**
   * 将来の拡張用メソッド（Phase 9b以降）
   */
  // setTranslatingState(state) { ... }
  // setFormDirtyState(state) { ... }
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
  console.log('showLoading() called - redirecting to StateManager');
  window.stateManager.showLoading();
};

window.hideLoading = function() {
  console.log('hideLoading() called - redirecting to StateManager');
  window.stateManager.hideLoading();
};

// Phase 9b: グローバル関数のwrap化（後方互換性維持）

// 結果カード制御のwrap関数
window.showResultCard = function(cardName) {
  console.log(`showResultCard(${cardName}) called - redirecting to StateManager`);
  window.stateManager.showResultCard(cardName);
};

window.hideResultCard = function(cardName) {
  console.log(`hideResultCard(${cardName}) called - redirecting to StateManager`);
  window.stateManager.hideResultCard(cardName);
};

// 翻訳状態制御のwrap関数
window.startTranslation = function() {
  console.log('startTranslation() called - redirecting to StateManager');
  window.stateManager.startTranslation();
};

window.completeTranslation = function() {
  console.log('completeTranslation() called - redirecting to StateManager');
  window.stateManager.completeTranslation();
};

window.isTranslationInProgress = function() {
  return window.stateManager.isTranslationInProgress();
};

// UI要素制御のwrap関数
window.showUIElement = function(elementName) {
  console.log(`showUIElement(${elementName}) called - redirecting to StateManager`);
  window.stateManager.showUIElement(elementName);
};

window.hideUIElement = function(elementName) {
  console.log(`hideUIElement(${elementName}) called - redirecting to StateManager`);
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

console.log('🎯 StateManager Phase 9c API State Management ready');