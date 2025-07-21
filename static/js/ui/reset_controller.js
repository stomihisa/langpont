/**
 * TaskH2-2(B2-3) Stage 3 Phase 8a: Reset Function Block Migration
 * リセット機能の統合制御クラス
 * 
 * 元の場所: templates/index.html (lines 1105-1223)
 * 移動理由: 機能的凝集性の保持、責任分離の実現
 */

class ResetController {
  constructor() {
    // 依存関係の確認
    if (typeof logOnce === 'undefined') {
      console.warn('logOnce function not available, using console.log fallback');
      window.logOnce = (id, message, level = 'info') => {
        console.log(`[${level.toUpperCase()}] ${id}: ${message}`);
      };
    }
  }

  /**
   * メインリセット機能 - 全てのリセット処理を統括
   * 元: resetForm() (lines 1105-1113)
   */
  resetForm() {
    logOnce('reset_form_called', 'resetForm() called');
    
    // 🆕 完全なリセット処理
    this.resetNuanceAnalysisArea();
    this.resetTranslationResults();
    this.resetFormInputs();
    this.resetInteractiveSections();
  }

  /**
   * ニュアンス分析エリアのリセット
   * 元: resetNuanceAnalysisArea() (lines 1115-1137)
   */
  resetNuanceAnalysisArea() {
    // ニュアンス分析カードを完全に非表示
    const nuanceCard = document.getElementById('gemini-nuance-card');
    if (nuanceCard) {
      nuanceCard.style.display = 'none';
      nuanceCard.classList.remove('show');
    }
    
    // 分析テキストをクリア
    const analysisText = document.getElementById('gemini-3way-analysis');
    if (analysisText) {
      analysisText.textContent = '';
      analysisText.innerHTML = '';
    }
    
    // エンジン選択ボタンエリアを非表示
    const engineTrigger = document.getElementById("analysis-engine-trigger");
    if (engineTrigger) {
      engineTrigger.style.display = "none";
    }

    logOnce('nuance_area_reset', '🧹 ニュアンス分析エリアをリセット');
  }

  /**
   * 翻訳結果エリアのリセット
   * 元: resetTranslationResults() (lines 1139-1165)
   */
  resetTranslationResults() {
    // 全ての翻訳結果カードを非表示
    const resultCards = document.querySelectorAll(".result-card");
    resultCards.forEach(card => {
      card.classList.remove("show");
      if (card.id === 'gemini-nuance-card') {
        card.style.display = 'none';
      }
    });
    
    // テキスト内容もクリア
    const textElements = [
      'translated-text', 'reverse-translated-text',
      'better-translation', 'reverse-better-translation',
      'gemini-translation', 'gemini-reverse-translation'
    ];
    
    textElements.forEach(id => {
      const element = document.getElementById(id);
      if (element) {
        element.textContent = '';
        element.innerHTML = '';
      }
    });
    
    logOnce('translation_area_reset', '🧹 翻訳結果エリアをリセット');
  }

  /**
   * フォーム入力フィールドのリセット
   * 元: resetFormInputs() (lines 1167-1178)
   */
  resetFormInputs() {
    // フォーム入力フィールドをクリア
    const inputField = document.getElementById("japanese_text");
    const partnerField = document.querySelector("[name='partner_message']");
    const contextField = document.querySelector("[name='context_info']");
    
    if (inputField) inputField.value = "";
    if (partnerField) partnerField.value = "";
    if (contextField) contextField.value = "";
    
    logOnce('input_field_reset', '🧹 入力フィールドをリセット');
  }

  /**
   * インタラクティブセクションのリセット
   * 元: resetInteractiveSections() (lines 1180-1192)
   */
  resetInteractiveSections() {
    // インタラクティブセクションも非表示に
    const interactiveSection = document.getElementById("interactive-section");
    if (interactiveSection) interactiveSection.classList.remove("show");
    
    const chatHistory = document.getElementById("chat-history");
    if (chatHistory) chatHistory.classList.remove("show");

    logOnce('interactive_section_reset', '🧹 インタラクティブセクションをリセット');
    
    // 🆕 サーバー側リセットを実行
    this.performServerReset();
  }

  /**
   * サーバー側リセット処理
   * 元: performServerReset() (lines 1194-1223)
   */
  performServerReset() {
    try {
      const form = document.querySelector("form");
      if (!form) {
        logOnce('form_not_found', 'Form not found', 'error');
        return;
      }
      
      // 既存のreset inputがあれば削除
      const existingReset = form.querySelector('input[name="reset"]');
      if (existingReset) {
        existingReset.remove();
      }
      
      // 新しいreset inputを追加
      const resetInput = document.createElement("input");
      resetInput.type = "hidden";
      resetInput.name = "reset";
      resetInput.value = "true";
      form.appendChild(resetInput);
      
      logOnce('reset_form_submit', 'Submitting reset form');
      form.submit();
      
    } catch (error) {
      logOnce('reset_form_error', `Reset form submission failed: ${error.message}`, 'error');
      // フォールバック：ページをリロード
      window.location.reload();
    }
  }
}

// グローバルインスタンスの作成と初期化
window.resetController = new ResetController();

// 後方互換性のためのグローバル関数エクスポート
window.resetForm = () => window.resetController.resetForm();
window.resetNuanceAnalysisArea = () => window.resetController.resetNuanceAnalysisArea();
window.resetTranslationResults = () => window.resetController.resetTranslationResults();
window.resetFormInputs = () => window.resetController.resetFormInputs();
window.resetInteractiveSections = () => window.resetController.resetInteractiveSections();
window.performServerReset = () => window.resetController.performServerReset();

// 初期化ログ
console.log('🔄 ResetController initialized successfully (Phase 8a)');