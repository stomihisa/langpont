// LangPont Main JavaScript Functions
// 外部ファイル化されたJavaScript関数群

function showToast(message, type = 'info') {
  if (typeof window.showToast === 'function' && window.showToast !== showToast) {
    return window.showToast(message, type);
  }
  
  if (type === 'error') {
    console.error(message);
  } else if (type === 'success') {
    console.log(`✅ ${message}`);
  } else {
    console.info(`ℹ️ ${message}`);
  }
}

// HTMLエスケープ関数
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// 言語ペア取得関数
function getLanguagePair() {
  const hiddenLanguagePair = document.getElementById('language_pair');
  return hiddenLanguagePair ? hiddenLanguagePair.value : 'ja-fr';
}

// 現在の言語ペア取得関数
function getCurrentLanguagePair() {
  const sourceSelect = document.getElementById('source_language');
  const targetSelect = document.getElementById('target_language');
  
  if (sourceSelect && targetSelect) {
    return `${sourceSelect.value}-${targetSelect.value}`;
  }
  const legacySelect = document.getElementById('language_pair');
  return legacySelect ? legacySelect.value : 'ja-en';
}

// コンテンツクリア関数
function clearContent(elementId) {
  const el = document.getElementById(elementId);
  if (el) el.value = "";
}

// チャット時刻フォーマット関数
function formatChatTimestamp(timestamp) {
  if (!timestamp) return '';
  
  const date = new Date(timestamp * 1000);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} min ago`;
  if (diffHours < 24) return `${diffHours} hours ago`;
  
  return date.toLocaleDateString('ja-JP', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

// コンテンツコピー関数
function copyContent(id, toastId, buttonElement) {
  const el = document.getElementById(id);
  const text = el ? (el.value || el.innerText) : "";
  navigator.clipboard.writeText(text);
  
  trackTranslationCopy(id, 'button_click', text);
  
  if (buttonElement) {
    showToastNearButton(toastId, buttonElement);
  } else {
    showToast(toastId);
  }
}

// ボタン近くでのトースト表示
function showToastNearButton(toastId, buttonElement) {
  const toast = document.getElementById(toastId);
  if (!toast) return;
  
  if (toast.hideTimer) {
    clearTimeout(toast.hideTimer);
  }
  const buttonRect = buttonElement.getBoundingClientRect();
  
  toast.style.cssText = `
    position: fixed !important;
    top: ${buttonRect.top - 45}px !important;
    left: ${buttonRect.left + buttonRect.width/2 - 60}px !important;
    width: 120px !important;
    height: 32px !important;
    background: #34C759 !important;
    color: white !important;
    border-radius: 6px !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    z-index: 9999 !important;
    box-shadow: 0 4px 12px rgba(52, 199, 89, 0.4) !important;
    pointer-events: none !important;
    opacity: 1 !important;
    transform: translateY(0) !important;
  `;
  
  toast.hideTimer = setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    setTimeout(() => {
      toast.style.display = 'none';
    }, 300);
  }, 1200);
}

// 言語ペア更新関数
function updateLanguagePair() {
  const sourceSelect = document.getElementById('source_language');
  const targetSelect = document.getElementById('target_language');
  const hiddenLanguagePair = document.getElementById('language_pair');
  
  if (sourceSelect && targetSelect && hiddenLanguagePair) {
    const sourceLang = sourceSelect.value;
    const targetLang = targetSelect.value;
    const languagePair = `${sourceLang}-${targetLang}`;
    
    hiddenLanguagePair.value = languagePair;
    updateLanguageLabels(languagePair);
  }
}

// 言語切り替え関数
function swapLanguages() {
  const sourceSelect = document.getElementById('source_language');
  const targetSelect = document.getElementById('target_language');
  const arrowButton = document.querySelector('.swap-arrow');
  
  if (sourceSelect && targetSelect && arrowButton) {
    const currentSource = sourceSelect.value;
    const currentTarget = targetSelect.value;
    
    sourceSelect.value = currentTarget;
    targetSelect.value = currentSource;
    
    arrowButton.classList.add('arrow-flipped');
    setTimeout(() => {
      arrowButton.classList.remove('arrow-flipped');
    }, 400);
    updateLanguagePair();
  }
}

// 詳細設定エリアの表示切り替え
function toggleAdvanced() {
  const content = document.getElementById("advancedContent");
  const button = document.querySelector(".advanced-toggle");
  const icon = button.querySelector("span");
  
  if (content.classList.contains("show")) {
    content.classList.remove("show");
    icon.textContent = "▼";
    if (window.currentLabels && window.currentLabels.toggle_details_open) {
      button.innerHTML = button.innerHTML.replace(
        window.currentLabels.toggle_details_close || "Close Details", 
        window.currentLabels.toggle_details_open || "Show Details"
      );
    }
  } else {
    content.classList.add("show");
    icon.textContent = "▲";
    if (window.currentLabels && window.currentLabels.toggle_details_close) {
      button.innerHTML = button.innerHTML.replace(
        window.currentLabels.toggle_details_open || "Show Details", 
        window.currentLabels.toggle_details_close || "Close Details"
      );
    }
  }
}

// アプリケーションリセット関数
function resetApplication() {
  resetForm();
}
