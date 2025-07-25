/**
 * =============================================================================
 * 🖥️ LangPont 開発監視パネル関連JavaScript関数群
 * =============================================================================
 * 
 * 📅 分離日: 2025年7月20日
 * 📋 Task: TaskH2-2(B2-3) Stage 2 Phase 6
 * 🎯 目的: メインファイル軽量化とコード整理
 * 
 * 📝 分離元: templates/index.html (Lines 1867-2154)
 * 📊 分離行数: 180行
 * 
 * ⚠️ 現在の状態: デッドコード（Stage 1 Phase 4でHTMLパネル削除済み）
 * 🔮 将来性: 監視パネル機能復活時の再利用可能
 * 
 * 📂 含まれる機能:
 * - システム状況監視・表示
 * - ユーザー行動監視・表示  
 * - 開発監視パネルUI改善
 * 
 * 🔧 使用方法: 
 * 監視パネル機能復活時にHTMLテンプレートでincludeして使用
 * 
 * 📋 復活に必要な要素:
 * - #devMonitorPanel (メインパネル)
 * - #systemVersion, #systemEnvironment, #systemDebugMode, #systemUptime (システム情報)
 * - #systemMemory, #memoryProgress, #systemCpu, #cpuProgress (リソース情報)
 * - #openaiStatus, #openaiStatusText, #geminiStatus, #geminiStatusText (API状況)
 * - #currentUsername, #currentLanguagePair, #translationCount (ユーザー情報)
 * - #currentInputLength, #currentWordCount (入力監視)
 * - addDevLogEntry() 関数 (ログ記録)
 * =============================================================================
 */

/**
 * システム状態表示の更新処理
 * 分離元: Lines 1867-1937 (71行)
 * 依存要素: #systemVersion, #systemEnvironment, #systemDebugMode, #systemUptime,
 *          #systemMemory, #memoryProgress, #systemCpu, #cpuProgress,
 *          #openaiStatus, #openaiStatusText, #geminiStatus, #geminiStatusText
 */
function updateSystemStatus(data) {
  // この関数は互換性のために残すが、API呼び出しは行わない
  console.log('⚠️ Legacy updateSystemStatus called - Using static display instead');
  
  try {
    // システム状況の安全な更新
    if (data.system_status) {
      const sysStatus = data.system_status;
      console.log('🔍 Debug: System status data:', sysStatus);
      
      document.getElementById('systemVersion').textContent = sysStatus.version || 'N/A';
      document.getElementById('systemEnvironment').textContent = sysStatus.environment || 'N/A';
      document.getElementById('systemDebugMode').textContent = sysStatus.debug_mode ? 'ON' : 'OFF';
      document.getElementById('systemUptime').textContent = sysStatus.uptime || 'N/A';
      
      console.log('🔍 Debug: System info updated - Version:', sysStatus.version, 'Environment:', sysStatus.environment);
      
      // メモリ使用量の安全な処理
      if (sysStatus.memory_usage && typeof sysStatus.memory_usage.percent === 'number') {
        const memPercent = sysStatus.memory_usage.percent;
        document.getElementById('systemMemory').textContent = `${memPercent.toFixed(1)}%`;
        document.getElementById('memoryProgress').style.width = `${memPercent}%`;
      } else {
        document.getElementById('systemMemory').textContent = 'N/A';
        document.getElementById('memoryProgress').style.width = '0%';
      }
      
      // CPU使用率の安全な処理
      if (typeof sysStatus.cpu_usage === 'number') {
        const cpuPercent = sysStatus.cpu_usage;
        document.getElementById('systemCpu').textContent = `${cpuPercent.toFixed(1)}%`;
        document.getElementById('cpuProgress').style.width = `${cpuPercent}%`;
      } else {
        document.getElementById('systemCpu').textContent = 'N/A';
        document.getElementById('cpuProgress').style.width = '0%';
      }
    }
    
    // API状況の安全な更新
    if (data.api_status) {
      const apiStatus = data.api_status;
      
      if (apiStatus.openai) {
        const openaiStatus = apiStatus.openai.status;
        document.getElementById('openaiStatus').className = 
          `dev-status-indicator ${openaiStatus}`;
        document.getElementById('openaiStatusText').textContent = 
          openaiStatus === 'connected' ? '接続中' : '切断';
      }
      
      if (apiStatus.gemini) {
        const geminiStatus = apiStatus.gemini.status;
        document.getElementById('geminiStatus').className = 
          `dev-status-indicator ${geminiStatus}`;
        document.getElementById('geminiStatusText').textContent = 
          geminiStatus === 'connected' ? '接続中' : '切断';
      }
    }
    
    addDevLogEntry('success', 'システム状況更新', 'データ更新完了');
    
  } catch (error) {
    console.error('System status update error:', error);
    addDevLogEntry('error', 'システム状況更新エラー', error.message);
    
    // エラー時のフォールバック表示
    document.getElementById('systemVersion').textContent = 'エラー';
    document.getElementById('systemEnvironment').textContent = 'エラー';
    document.getElementById('systemDebugMode').textContent = 'エラー';
  }
}

/**
 * ユーザー活動状況の更新処理
 * 分離元: Lines 1940-1975 (36行)
 * 依存要素: #currentUsername, #currentLanguagePair, #translationCount,
 *          #currentInputLength, #currentWordCount, #japanese_text
 */
function updateUserActivity(data) {
  try {
    if (data.current_session) {
      const session = data.current_session;
      document.getElementById('currentUsername').textContent = session.username || 'N/A';
      document.getElementById('currentLanguagePair').textContent = session.language_pair || 'N/A';
      document.getElementById('translationCount').textContent = session.translations_count || 0;
    }
    
    // 現在の入力を監視
    const inputField = document.getElementById('japanese_text');
    if (inputField) {
      const inputText = inputField.value || '';
      document.getElementById('currentInputLength').textContent = inputText.length;
      document.getElementById('currentWordCount').textContent = inputText.split(/\s+/).filter(w => w.length > 0).length;
    } else {
      document.getElementById('currentInputLength').textContent = '0';
      document.getElementById('currentWordCount').textContent = '0';
    }
    
    // 最新のアクティビティをログに追加
    if (data.recent_activity && Array.isArray(data.recent_activity) && data.recent_activity.length > 0) {
      const latestActivity = data.recent_activity[data.recent_activity.length - 1];
      if (latestActivity && latestActivity.timestamp !== window.lastActivityTimestamp) {
        const details = latestActivity.details ? JSON.stringify(latestActivity.details) : '';
        addDevLogEntry('info', latestActivity.action || 'unknown', details);
        window.lastActivityTimestamp = latestActivity.timestamp;
      }
    }
  } catch (error) {
    console.error('User activity update error:', error);
    addDevLogEntry('error', 'ユーザー行動更新エラー', error.message);
  }
}

/**
 * 開発監視パネルのUI改善処理
 * 分離元: Lines 2082-2154 (73行)
 * 依存要素: #devMonitorPanel, .reasoning-text, #recommendationReasoning,
 *          .dev-section-title, .dev-metric-label, .dev-metric-value, .dev-log-entry
 */
function applyDevMonitorUIImprovements() {
  // ログ出力を大幅削減（2%の確率でのみ）
  if (Math.random() < 0.02) {
    logOnce('ui_improvements_applied', "🎨 UI improvements applied");
  }
  
  // 判定根拠テキストの強制改善
  const reasoningTexts = document.querySelectorAll('.reasoning-text');
  reasoningTexts.forEach(element => {
    element.style.color = '#E5E7EB';
    element.style.fontSize = '13px';
    element.style.lineHeight = '1.6';
    element.style.fontWeight = '400';
  });
  
  // 判定根拠セクションの改善
  const reasoningElement = document.getElementById('recommendationReasoning');
  if (reasoningElement) {
    reasoningElement.style.backgroundColor = '#1F2937';
    reasoningElement.style.padding = '12px';
    reasoningElement.style.borderRadius = '6px';
    
    const text = reasoningElement.querySelector('.reasoning-text');
    if (text) {
      text.style.color = '#F3F4F6';
      text.style.fontSize = '13px';
      text.style.lineHeight = '1.6';
    }
  }
  
  // 全体の文字サイズ強制適用
  const devMonitorPanel = document.getElementById('devMonitorPanel');
  if (devMonitorPanel) {
    devMonitorPanel.style.fontSize = '14px';
    devMonitorPanel.style.lineHeight = '1.5';
    
    // セクションタイトル
    const titles = devMonitorPanel.querySelectorAll('h3, h4, .dev-section-title');
    titles.forEach(title => {
      title.style.fontSize = '16px';
      title.style.fontWeight = '600';
    });
    
    // メトリクスラベル
    const labels = devMonitorPanel.querySelectorAll('.dev-metric-label');
    labels.forEach(label => {
      label.style.fontSize = '12px';
      label.style.fontWeight = '500';
      label.style.color = '#9CA3AF';
    });
    
    // メトリクス値
    const values = devMonitorPanel.querySelectorAll('.dev-metric-value');
    values.forEach(value => {
      if (!value.classList.contains('recommendation-highlight') && 
          !value.classList.contains('confidence-highlight')) {
        value.style.fontSize = '13px';
        value.style.color = '#E5E7EB';
      }
    });
    
    // ログエントリ
    const logEntries = devMonitorPanel.querySelectorAll('.dev-log-entry, .dev-log-timestamp, .dev-log-message');
    logEntries.forEach(entry => {
      entry.style.fontSize = '12px';
    });
  }
  
  // 完了ログも削減
  if (Math.random() < 0.02) {
    logOnce('ui_improvements_complete', "✅ UI improvements complete");
  }
}

/**
 * 監視パネル関連関数の参照呼び出し（互換性保持）
 * これらの呼び出しも復活時に必要となる可能性があります
 */

// applyDevMonitorUIImprovements() の定期実行設定
// 元の場所: Lines 2192, 2195
// 復活時のコード例:
// applyDevMonitorUIImprovements();
// setInterval(applyDevMonitorUIImprovements, 30000);