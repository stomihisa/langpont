/**
 * TaskH2-2(B2-3) Stage 3 Phase 8b: Chat Function Block Migration
 * チャット履歴管理システム統合制御クラス
 * 
 * 元の場所: templates/index.html (lines 283-395)
 * 移動理由: 機能的凝集性の保持、責任分離の実現
 */

class ChatController {
  constructor() {
    // 依存関係の確認
    if (typeof window.escapeHtml === 'undefined') {
      console.warn('escapeHtml function not available from main.js');
    }
    if (typeof window.formatChatTimestamp === 'undefined') {
      console.warn('formatChatTimestamp function not available from main.js');
    }
  }

  /**
   * チャット履歴表示機能
   * 元: displayChatHistory() (lines 283-329)
   */
  displayChatHistory(chatHistory) {
    const chatItemsContainer = document.getElementById('chat-items');
    const chatHistorySection = document.getElementById('chat-history');
    
    if (!chatItemsContainer) return;

    // 履歴をクリア
    chatItemsContainer.innerHTML = '';
    
    if (!chatHistory || chatHistory.length === 0) {
      // 履歴が空の場合はセクションを非表示
      if (chatHistorySection) {
        chatHistorySection.style.display = 'none';
      }
      return;
    }
    
    // 履歴がある場合はセクションを表示
    if (chatHistorySection) {
      chatHistorySection.style.display = 'block';
    }

    // 各チャット項目を表示
    chatHistory.forEach((item, index) => {
      if (!item || !item.question || !item.answer) return;
      
      const chatItem = document.createElement('div');
      chatItem.className = 'chat-item';
      chatItem.innerHTML = `
        <div class="chat-question">
          <div class="chat-q-header">
            <span class="chat-q-icon">❓</span>
            <span class="chat-q-text">${window.escapeHtml ? window.escapeHtml(item.question) : item.question}</span>
            <span class="chat-timestamp">${window.formatChatTimestamp ? window.formatChatTimestamp(item.timestamp) : item.timestamp}</span>
          </div>
        </div>
        <div class="chat-answer">
          <div class="chat-a-header">
            <span class="chat-a-icon">💡</span>
            <span class="chat-a-type">${this.getAnswerTypeLabel(item.type)}</span>
          </div>
          <div class="chat-a-content">${this.formatChatAnswer(item.answer)}</div>
        </div>
      `;
      chatItemsContainer.appendChild(chatItem);
    });
  }

  /**
   * チャット履歴初期化機能
   * 元: initializeChatHistory() (lines 332-359)
   */
  initializeChatHistory() {
    try {
      // ページロード時は常に空の状態から開始
      if (typeof(Storage) !== "undefined") {
        localStorage.removeItem('langpont_chat_history');
        sessionStorage.removeItem('langpont_chat_history');
      }
      
      // チャット履歴エリアを非表示
      const chatHistorySection = document.getElementById('chat-history');
      if (chatHistorySection) {
        chatHistorySection.style.display = 'none';
      }
      
      // チャット項目をクリア
      const chatItemsContainer = document.getElementById('chat-items');
      if (chatItemsContainer) {
        chatItemsContainer.innerHTML = '';
      }
      
      // 空の履歴を表示
      this.displayChatHistory([]);
      
    } catch (error) {
      console.error('Error during chat history initialization:', error);
      this.displayChatHistory([]);
    }
  }

  /**
   * 回答タイプラベル取得機能
   * 元: getAnswerTypeLabel() (lines 376-388)
   */
  getAnswerTypeLabel(type) {
    const typeLabels = {
      'translation_modification': 'Translation Edit',
      'analysis_inquiry': 'Analysis Inquiry',
      'linguistic_question': 'Linguistic Question',
      'context_variation': 'Context Change',
      'comparison_analysis': 'Comparison Analysis',
      'general_expert': 'General Question',
      'general': 'General',
      'error': 'Error'
    };
    return typeLabels[type] || window.currentLabels?.chat_answer_label || 'Answer';
  }

  /**
   * チャット回答フォーマット機能
   * 元: formatChatAnswer() (lines 390-395)
   */
  formatChatAnswer(answer) {
    if (!answer) return '';
    
    // 改行をHTMLに変換
    const escapeFunc = window.escapeHtml || ((str) => str);
    return escapeFunc(answer).replace(/\n/g, '<br>');
  }
}

// グローバルインスタンスの作成と初期化
window.ChatController = ChatController;
window.chatController = new ChatController();

// 後方互換性のためのグローバル関数エクスポート
window.displayChatHistory = function(chatHistory) {
  return window.chatController.displayChatHistory(chatHistory);
};

window.initializeChatHistory = function() {
  return window.chatController.initializeChatHistory();
};

window.getAnswerTypeLabel = function(type) {
  return window.chatController.getAnswerTypeLabel(type);
};

window.formatChatAnswer = function(answer) {
  return window.chatController.formatChatAnswer(answer);
};

// 初期化ログ
console.log('💬 ChatController initialized successfully (Phase 8b)');