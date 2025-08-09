/**
 * ファイル名: static/js/interactive/question_handler.js
 * 役割: インタラクティブ質問処理の統合制御
 * 依存関係: 
 *   - window.currentLabels (多言語対応)
 *   - showToast() (通知機能)
 *   - fetch API (サーバー通信)
 * 公開インターフェース:
 *   - askInteractiveQuestion(): メイン質問処理
 *   - setupQuestionInputEvents(): イベント初期化
 * 重複関数対応: askInteractiveQuestion()の詳細ログ版を採用
 * 最終更新: H2-2(B2-3) Stage 1 Phase 1
 * 戦略コンテキスト: 1000行削減戦略 Stage 1 Phase 1
 * 品質保証: Stage 1基準（通常実装・高品質維持）
 */

// =============================================================================
// 🧠 インタラクティブQ&A質問処理システム (詳細ログ強化版)
// =============================================================================

/**
 * インタラクティブ質問を送信する関数（詳細ログ強化版）
 * 調査で確認された2つの重複関数のうち、より完成度の高い詳細ログ版を採用
 */
async function askInteractiveQuestion() {
  // 🔒 Phase 9c: Critical Security - 二重実行防止
  if (!startApiCall('interactiveQuestion')) {
    console.warn('⚠️ Interactive question already in progress - preventing double execution');
    return;
  }
  
  console.log('📤 [QUESTION] Function called');
  console.log('📤 [QUESTION] Timestamp:', new Date().toISOString());
  
  const questionInput = document.getElementById('question-input');
  const questionBtn = document.getElementById('question-btn');
  
  // 基本要素チェック
  console.log('📤 [QUESTION] DOM element checks:');
  console.log('  - questionInput found:', !!questionInput);
  console.log('  - questionBtn found:', !!questionBtn);
  
  if (!questionInput || !questionBtn) {
    console.error('❌ [QUESTION] Question input or button not found');
    return;
  }

  const question = questionInput.value.trim();
  console.log('📤 [QUESTION] Question details:');
  console.log('  - Question length:', question.length);
  console.log('  - Question content:', question.substring(0, 100) + (question.length > 100 ? '...' : ''));
  
  if (!question) {
    console.warn('⚠️ [QUESTION] Empty question submitted');
    alert(window.currentLabels.enter_question || 'Please enter a question');
    return;
  }

  if (question.length < 5) {
    console.warn('⚠️ [QUESTION] Question too short:', question.length);
    alert(window.currentLabels.question_min_length || 'Please enter a question with at least 5 characters');
    return;
  }

  // Cookie サイズ事前チェック
  const initialCookieSize = document.cookie.length;
  console.log('🍪 [QUESTION] Cookie size before request:', initialCookieSize, 'bytes');
  console.log('🍪 [QUESTION] Cookie content sample:', document.cookie.substring(0, 200) + '...');

  // UIを無効化
  questionBtn.disabled = true;
  questionBtn.textContent = window.currentLabels.processing_text || 'Processing...';
  console.log('🔒 [QUESTION] UI disabled for processing');
  
  try {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    console.log('🔐 [QUESTION] CSRF token found:', !!csrfToken);
    
    const requestData = { question: question };
    const requestBody = JSON.stringify(requestData);
    console.log('📤 [QUESTION] Request preparation:');
    console.log('  - Request data:', requestData);
    console.log('  - Request body size:', requestBody.length, 'bytes');
    
    console.log('📤 [QUESTION] Starting fetch request...');
    const response = await fetch('/interactive_question', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken || ''
      },
      body: requestBody
    });

    console.log('📥 [RESPONSE] Response received:');
    console.log('  - Status:', response.status);
    console.log('  - Status text:', response.statusText);
    console.log('  - Headers:', Object.fromEntries(response.headers.entries()));
    
    // Cookie サイズ事後チェック
    const finalCookieSize = document.cookie.length;
    console.log('🍪 [RESPONSE] Cookie size after response:', finalCookieSize, 'bytes');
    console.log('🍪 [RESPONSE] Cookie size change:', finalCookieSize - initialCookieSize, 'bytes');
    
    if (response.ok) {
      const data = await response.json();
      console.log('📥 [RESPONSE] Data received successfully:');
      console.log('  - Data structure keys:', Object.keys(data));
      console.log('  - Data.success:', data.success);
      console.log('  - Data.result exists:', !!data.result);
      console.log('  - Data.chat_history exists:', !!data.chat_history);
      console.log('  - Data.current_chat exists:', !!data.current_chat);
      console.log('  - Data.interactive_current_chat exists:', !!data.interactive_current_chat);
      
      // 🔧 Phase 3c-1b: StateManager統合対応 - interactive_current_chat優先、current_chatフォールバック
      let chatHistory = [];
      if (data.chat_history) {
        // 旧形式対応
        chatHistory = data.chat_history;
      } else if (data.interactive_current_chat) {
        // Phase 3c-1b: StateManager新形式対応
        chatHistory = [data.interactive_current_chat];
      } else if (data.current_chat) {
        // フォールバック: 既存形式対応
        chatHistory = [data.current_chat];
      }

      if (chatHistory.length > 0) {
        console.log('📥 [RESPONSE] Chat history details:');
        console.log('  - Chat history length:', chatHistory.length);
        console.log('  - Using format:', data.chat_history ? 'legacy' : (data.interactive_current_chat ? 'state_manager' : 'current_chat'));
        console.log('  - First item sample:', chatHistory[0] ? {
          question: chatHistory[0].question?.substring(0, 50) + '...',
          answer: chatHistory[0].answer?.substring(0, 50) + '...',
          type: chatHistory[0].type,
          timestamp: chatHistory[0].timestamp
        } : 'No items');
      }
      
      if (data.success) {
        console.log('🔄 [PROCESSING] Starting successful response processing...');
        
        // 入力をクリア
        questionInput.value = '';
        console.log('🧹 [PROCESSING] Input field cleared');
        
        // 🆕 確実な表示処理：DOM更新を待ってから表示
        console.log('🖥️ [DISPLAY] Starting display process with 50ms delay...');
        setTimeout(() => {
          console.log('🖥️ [DISPLAY] Calling updateChatHistory...');
          updateChatHistory(chatHistory);
          
          // 🆕 表示状態の強制確認
          const chatHistorySection = document.getElementById('chat-history');
          console.log('🖥️ [DISPLAY] Post-display checks:');
          console.log('  - Chat history section found:', !!chatHistorySection);
          
          if (chatHistorySection && chatHistory && chatHistory.length > 0) {
            chatHistorySection.style.display = 'block';
            console.log('✅ [DISPLAY] Chat history section shown');
            console.log('🖥️ [DISPLAY] Section visibility:', getComputedStyle(chatHistorySection).display);
          }
        }, 50);
        
        // 成功メッセージ
        showToast(window.currentLabels.question_generated || 'Response generated successfully', 'success');
        console.log('✅ [QUESTION] Question processed successfully');
        
      } else {
        console.error('❌ [RESPONSE] Server returned success: false');
        console.error('❌ [RESPONSE] Error details:', data.error);
        showToast(data.error || window.currentLabels.error_occurred || 'An error occurred during question processing', 'error');
      }
    } else {
      console.error('❌ [RESPONSE] HTTP request failed:');
      console.error('  - Status:', response.status);
      console.error('  - Status text:', response.statusText);
      showToast(window.currentLabels.api_error_general || 'Server error occurred', 'error');
    }
  } catch (error) {
    // 🆕 Phase C: StateManager統合
    if (window.integrateErrorWithStateManager) {
      window.integrateErrorWithStateManager(error, {
        function: 'askInteractiveQuestion',
        apiType: 'interactiveQuestion',
        location: 'question_handler.js'
      });
    }
    
    // 既存のエラー処理継続
    console.error('❌ [QUESTION] Fetch error occurred:');
    console.error('  - Error message:', error.message);
    console.error('  - Error stack:', error.stack);
    showToast(window.currentLabels.api_error_network || 'Error occurred while sending question', 'error');
  } finally {
    // UIを復元
    questionBtn.disabled = false;
    questionBtn.textContent = window.currentLabels.interactive_button || 'Ask Question';
    console.log('🔓 [QUESTION] UI restored to normal state');
    
    // 🔒 Phase 9c: API状態をクリア
    completeApiCall('interactiveQuestion');
  }
}