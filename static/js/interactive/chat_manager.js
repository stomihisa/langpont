/**
 * ファイル名: static/js/interactive/chat_manager.js
 * 役割: チャット履歴管理とクイック質問制御
 * 依存関係: 
 *   - window.currentLabels (多言語対応)
 *   - showToast() (通知機能)
 *   - escapeHtml(), formatChatTimestamp() (ユーティリティ関数)
 * 公開インターフェース:
 *   - updateChatHistory(): チャット履歴表示更新
 *   - clearChatHistory(): チャット履歴クリア
 *   - setQuickQuestion(): クイック質問設定
 * 最終更新: H2-2(B2-3) Stage 1 Phase 1
 * 戦略コンテキスト: 1000行削減戦略 Stage 1 Phase 1
 * 品質保証: Stage 1基準（通常実装・高品質維持）
 */

// =============================================================================
// 🧠 チャット履歴管理システム
// =============================================================================

/**
 * チャット履歴をクリアする関数（クライアントサイド版）
 */
function clearChatHistory() {
  if (!confirm(window.currentLabels.confirm_clear_history || 'Are you sure you want to clear chat history?')) {
    return;
  }

  try {
    // クライアントサイドチャット履歴をクリア
    window.clientChatHistory = [];
    
    // UI更新
    updateChatHistory([]);
    
    // ローカルストレージからも削除（存在する場合）
    if (typeof(Storage) !== "undefined") {
      localStorage.removeItem('langpont_chat_history');
      sessionStorage.removeItem('langpont_chat_history');
    }
    
    // チャット履歴セクションを非表示
    const chatHistorySection = document.getElementById('chat-history');
    if (chatHistorySection) {
      chatHistorySection.style.display = 'none';
    }
    
    console.log('🧹 Chat history cleared (client-side)');
    showToast(window.currentLabels.history_cleared_success || 'Chat history cleared', 'success');
    
  } catch (error) {
    console.error('Error clearing chat history:', error);
    showToast(window.currentLabels.history_clear_error || 'Error occurred while clearing chat history', 'error');
  }
}

/**
 * クイック質問を設定する関数
 */
function setQuickQuestion(questionText) {
  const questionInput = document.getElementById('question-input');
  if (questionInput) {
    questionInput.value = questionText;
    questionInput.focus();
  }
}

// =============================================================================
// 🛠️ ユーティリティ関数 (index.htmlから移動)
// =============================================================================

/**
 * チャット履歴表示を強制する関数
 */
function forceChatHistoryDisplay() {
  const chatHistorySection = document.getElementById('chat-history');
  if (!chatHistorySection) return false;
  
  // 強制表示（!importantを使用）
  chatHistorySection.style.cssText = `
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    height: auto !important;
    max-height: none !important;
    position: static !important;
    z-index: 1 !important;
  `;
  
  // showクラスも追加
  chatHistorySection.classList.add('show');
  
  return true;
}

/**
 * 回答タイプのラベルを取得する関数
 */
function getTypeName(type) {
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
 * 回答テキストをフォーマットする関数
 */
function formatAnswerText(text, type = 'general_question') {
  if (!text) return '';
  
  // HTML エスケープを行い、改行を適切に処理
  let formatted = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
  
  // 改行をHTMLに変換
  formatted = formatted.replace(/\n/g, '<br>');
  
  return formatted;
}

/**
 * チャット回答の展開/折りたたみ機能
 */
function toggleChatAnswer(chatItemId) {
  const chatItem = document.getElementById(chatItemId);
  if (!chatItem) return;
  
  const answerDiv = chatItem.querySelector('.chat-answer');
  const expandBtn = chatItem.querySelector('.chat-expand-btn');
  
  if (!answerDiv || !expandBtn) return;
  
  if (answerDiv.classList.contains('collapsed')) {
    answerDiv.classList.remove('collapsed');
    expandBtn.textContent = window.currentLabels?.collapse_text || '▲ Collapse';
  } else {
    answerDiv.classList.add('collapsed');
    expandBtn.textContent = window.currentLabels?.expand_full_text || '▼ Show full text';
  }
}

/**
 * チャット履歴表示更新関数
 */
function updateChatHistory(chatHistory) {
  const chatHistorySection = document.getElementById('chat-history');
  const chatItemsContainer = document.getElementById('chat-items');
  
  if (!chatHistory || chatHistory.length === 0) {
    if (chatHistorySection) {
      chatHistorySection.classList.remove('show');
    }
    return;
  }
  
  // チャット履歴を表示
  if (chatHistorySection) {
    chatHistorySection.classList.add('show');
    
    // 表示問題の自動修正
    setTimeout(() => {
      const computedStyle = window.getComputedStyle(chatHistorySection);
      if (computedStyle.display === 'none') {
        forceChatHistoryDisplay();
      }
    }, 100);
  }
  
  // 最新の5件のみ表示
  const recentChats = chatHistory.slice(-5);
  
  if (!chatItemsContainer) return;
  
  chatItemsContainer.innerHTML = '';
  
  recentChats.forEach((chat, index) => {
    const chatItem = document.createElement('div');
    chatItem.className = 'chat-item';
    const chatItemId = `chat-item-${Date.now()}-${index}`;
    chatItem.id = chatItemId;
    
    const typeClass = chat.type || 'general_question';
    const typeName = getTypeName(typeClass);
    
    // 🔧 デバッグログ追加で問題表示を確認
    console.log('🔧 Chat item data:', {
      question: chat.question,
      answer: chat.answer?.substring(0, 100),
      type: chat.type
    });
    
    // 🔧 質問はシンプルなエスケープのみ、回答はフルフォーマット
    const formattedAnswer = formatAnswerText(chat.answer || '', typeClass);
    const formattedQuestion = (chat.question || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
    const isLongAnswer = (chat.answer || '').length > 1500; /* 🎯 300 → 1500 展開ボタン闾値調整 */
    
    // 🎯 UI最終調整: 質問・回答タイトル、フォントサイズ統一、高さ自動調整
    // 🌍 多言語対応: 動的ラベルを取得
    const questionLabel = window.currentLabels?.chat_question_label || "Question";
    const answerLabel = window.currentLabels?.chat_answer_label || "Answer";
    const expandLabel = window.currentLabels?.expand_full_text || "▼ Show full text";
    
    chatItem.innerHTML = `
      <div class="chat-question">
        <div class="chat-type-badge ${typeClass}">💡 ${questionLabel}: ${formattedQuestion}</div>
      </div>
      <div class="chat-answer${isLongAnswer ? ' collapsed' : ''}">
        <div class="chat-answer-title">💬 ${answerLabel}:</div>
        <div class="chat-a-content">${formattedAnswer}</div>
        ${isLongAnswer ? `<button class="chat-expand-btn" onclick="toggleChatAnswer('${chatItemId}')">${expandLabel}</button>` : ''}
      </div>
    `;
    
    chatItemsContainer.appendChild(chatItem);
  });
  
  // 🆕 チャット履歴を一番下にスクロール（新しいメッセージを表示）
  setTimeout(() => {
    if (chatItemsContainer && chatItemsContainer.scrollHeight > chatItemsContainer.clientHeight) {
      chatItemsContainer.scrollTop = chatItemsContainer.scrollHeight;
    }
  }, 100);
}