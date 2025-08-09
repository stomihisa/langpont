/**
 * 🎯 Task H2-2(B2-3) Stage 2 Phase 5: JavaScript関数群基本分離
 * 分離された安全なユーティリティ関数群
 * 分離日: 2025/07/20
 * 削減効果: 14関数・約387行
 */

/**
 * 使用状況の表示更新
 */
function updateUsageStatus(usageInfo) {
  const usageElement = document.querySelector('.usage-count');
  if (!usageElement || !usageInfo) return;
  
  const { current_usage, daily_limit, is_unlimited, username, user_role } = usageInfo;
  
  let statusHTML;
  if (is_unlimited) {
    statusHTML = `🔰 ${username} (${user_role}): 無制限利用可能 ✨`;
  } else {
    const percentage = Math.round((current_usage / daily_limit) * 100);
    const usageClass = percentage >= 80 ? 'usage-high' : percentage >= 60 ? 'usage-medium' : 'usage-low';
    statusHTML = `📊 ${username} (${user_role}): <span class="${usageClass}">${current_usage}/${daily_limit}</span> 回`;
  }
  
  usageElement.innerHTML = statusHTML;
  
  // アップグレードボタンの表示制御
  const upgradeButton = document.querySelector('.upgrade-button');
  if (upgradeButton) {
    upgradeButton.style.display = is_unlimited ? 'none' : 'inline-block';
  }
  
  // Premium表示の制御
  const premiumMessage = document.querySelector('.premium-message');
  if (premiumMessage) {
    premiumMessage.style.display = is_unlimited ? 'block' : 'none';
  }
}

/**
 * 使用制限エラーの表示
 */
function showUsageLimitError(errorData) {
  const errorDiv = document.createElement('div');
  errorDiv.className = 'usage-limit-error';
  errorDiv.style.cssText = `
    background: #ff4757;
    color: white;
    padding: 15px;
    border-radius: 8px;
    margin: 10px 0;
    font-weight: 500;
    box-shadow: 0 2px 10px rgba(255, 71, 87, 0.3);
  `;
  
  const { current_usage, daily_limit, reset_time } = errorData;
  
  errorDiv.innerHTML = `
    <h4 style="margin: 0 0 8px 0;">🚫 利用制限に達しました</h4>
    <p style="margin: 0 0 8px 0;">今日の利用回数: ${current_usage}/${daily_limit}</p>
    <p style="margin: 0; font-size: 14px; opacity: 0.9;">
      リセット時刻: ${reset_time || '午前0時'}
    </p>
  `;
  
  const translationArea = document.querySelector('.translation-area') || document.body;
  translationArea.insertBefore(errorDiv, translationArea.firstChild);
  
  setTimeout(() => {
    if (errorDiv.parentNode) {
      errorDiv.parentNode.removeChild(errorDiv);
    }
  }, 8000);
}

/**
 * 一度だけログ出力する関数（重複ログ防止）
 */
function logOnce(key, message, level = 'log') {
  if (!window.loggedMessages) window.loggedMessages = new Set();
  if (!window.loggedMessages.has(key)) {
    console[level](message);
    window.loggedMessages.add(key);
  }
}

/**
 * IME関連ログの節度ある出力（重複ログ解決）
 */
let lastIMELog = 0;
function logIME(message, level = 'log') {
  const now = Date.now();
  if (now - lastIMELog > 2000) { // 2秒間隔でのみログ出力
    console[level](message);
    lastIMELog = now;
  }
}

/**
 * 回答テキストをフォーマット（改行、インデント、タイプ別フォーマットを適切に処理）
 */
function formatAnswerText(text, type = 'general_question') {
  if (!text) return '';
  
  // HTMLエスケープ
  const escapeHtml = (unsafe) => {
    return unsafe
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  };
  
  let escaped = escapeHtml(text);
  
  // 改行の処理
  escaped = escaped.replace(/\n/g, '<br>');
  
  // タイプ別の特別フォーマット
  switch(type) {
    case 'translation_modification':
      escaped = `<div class="translation-mod">${escaped}</div>`;
      break;
    case 'analysis_inquiry':
      escaped = `<div class="analysis-inquiry">${escaped}</div>`;
      break;
    case 'linguistic_question':
      escaped = `<div class="linguistic-q">${escaped}</div>`;
      break;
    default:
      break;
  }
  
  return escaped;
}

/**
 * チャット回答の表示/非表示切り替え
 */
function toggleChatAnswer(chatItemId) {
  const chatItem = document.getElementById(chatItemId);
  if (!chatItem) return;
  
  const answerDiv = chatItem.querySelector('.chat-answer');
  const toggleBtn = chatItem.querySelector('.toggle-answer-btn');
  
  if (!answerDiv || !toggleBtn) return;
  
  const isVisible = answerDiv.style.display !== 'none';
  
  if (isVisible) {
    answerDiv.style.display = 'none';
    toggleBtn.textContent = '▶ 回答を表示';
    toggleBtn.style.background = '#007AFF';
  } else {
    answerDiv.style.display = 'block';
    toggleBtn.textContent = '▼ 回答を非表示';
    toggleBtn.style.background = '#34C759';
  }
  
  logOnce(`toggle_answer_${chatItemId}`, `チャット回答表示切り替え: ${isVisible ? '非表示' : '表示'}`);
}

/**
 * チャット履歴の表示更新
 */
function updateChatHistory(chatHistory) {
  const chatItemsContainer = document.getElementById('chat-items');
  const chatHistorySection = document.getElementById('chat-history');
  
  if (!chatItemsContainer || !chatHistorySection) {
    logOnce('chat_history_elements_missing', '❌ チャット履歴要素が見つかりません', 'error');
    return;
  }
  
  if (!chatHistory || chatHistory.length === 0) {
    chatHistorySection.style.display = 'none';
    logOnce('empty_chat_history', '📭 チャット履歴は空です');
    return;
  }
  
  chatItemsContainer.innerHTML = '';
  
  chatHistory.forEach((item, index) => {
    const chatItemDiv = document.createElement('div');
    chatItemDiv.className = 'chat-item';
    chatItemDiv.id = `chat-item-${item.id || index}`;
    
    const questionDiv = document.createElement('div');
    questionDiv.className = 'chat-question';
    questionDiv.innerHTML = `
      <span class="chat-timestamp">${formatChatTimestamp(item.timestamp)}</span>
      <span class="question-text">${escapeHtml(item.question)}</span>
    `;
    
    const answerDiv = document.createElement('div');
    answerDiv.className = 'chat-answer';
    answerDiv.style.display = 'none';
    answerDiv.innerHTML = formatAnswerText(item.answer, item.type);
    
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'toggle-answer-btn';
    toggleBtn.textContent = '▶ 回答を表示';
    toggleBtn.onclick = () => toggleChatAnswer(`chat-item-${item.id || index}`);
    
    chatItemDiv.appendChild(questionDiv);
    chatItemDiv.appendChild(toggleBtn);
    chatItemDiv.appendChild(answerDiv);
    chatItemsContainer.appendChild(chatItemDiv);
  });
  
  chatHistorySection.style.display = 'block';
  logOnce('chat_history_updated', `✅ チャット履歴更新完了: ${chatHistory.length}件`);
}

/**
 * 質問タイプ名の取得
 */
function getTypeName(type) {
  const typeNames = {
    'general_question': '一般質問',
    'translation_modification': '翻訳修正',
    'analysis_inquiry': '分析解説',
    'linguistic_question': '言語学的質問',
    'context_variation': 'コンテキスト変更',
    'comparison_analysis': '比較分析'
  };
  return typeNames[type] || '質問';
}

/**
 * チャット履歴の強制表示
 */
function forceChatHistoryDisplay() {
  const chatHistorySection = document.getElementById('chat-history');
  if (chatHistorySection) {
    chatHistorySection.style.display = 'block';
    chatHistorySection.style.visibility = 'visible';
    logOnce('force_chat_display', '🔧 チャット履歴を強制表示しました');
  }
}

/**
 * チャット履歴表示の診断
 */
function diagnoseChatHistoryDisplay() {
  const section = document.getElementById('chat-history');
  const container = document.getElementById('chat-items');
  
  if (!section || !container) {
    console.error('🚫 チャット履歴要素が見つかりません');
    return;
  }
  
  const diagnosis = {
    section_display: section.style.display,
    section_visibility: section.style.visibility,
    container_children: container.children.length,
    section_classes: section.className
  };
  
  console.log('🔍 チャット履歴診断:', diagnosis);
  logOnce('chat_history_diagnosis', `チャット履歴診断完了: ${JSON.stringify(diagnosis)}`);
}

/**
 * 質問入力イベントの設定
 */
function setupQuestionInputEvents() {
  const questionInput = document.getElementById('question-input');
  if (!questionInput) return;
  
  questionInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const submitBtn = document.getElementById('submit-question-btn');
      if (submitBtn) submitBtn.click();
    }
  });
  
  // IME入力中はEnterキー送信を無効化
  let isComposing = false;
  questionInput.addEventListener('compositionstart', () => isComposing = true);
  questionInput.addEventListener('compositionend', () => isComposing = false);
  
  questionInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      const submitBtn = document.getElementById('submit-question-btn');
      if (submitBtn) submitBtn.click();
    }
  });
  
  logOnce('question_input_events', '📝 質問入力イベント設定完了');
}

/**
 * トースト通知の表示
 */
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = 'toast-notification';
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 12px 20px;
    background: ${type === 'success' ? '#34C759' : '#007AFF'};
    color: white;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    z-index: 9999;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    transition: opacity 0.3s ease, transform 0.3s ease;
  `;
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    setTimeout(() => {
      document.body.removeChild(toast);
    }, 300);
  }, 3000);
}

// ヘルパー関数
function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatChatTimestamp(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('ja-JP', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: false 
  });
}