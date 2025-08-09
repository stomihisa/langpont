// 🧠 ニュアンス分析システム内部処理関数群
// Task H2-2(B2-3) Stage 1 Phase 2 により分離

// 🧠 Task 2.9.2 Phase B-3.5.2: マルチエンジン分析実行
function fetchNuanceAnalysis(engine = 'gemini') {
  // 🔒 Phase 9c: Critical Security - 二重実行防止
  if (!startApiCall('nuanceAnalysis')) {
    console.warn('⚠️ Nuance analysis already in progress - preventing double execution');
    return;
  }
  
  const el = document.getElementById("gemini-3way-analysis");
  const card = document.getElementById("gemini-nuance-card");
  if (!card || !el) {
    logOnce('analysis_elements_missing', '🚨 分析要素が見つかりません', 'error');
    // 🔒 API状態をクリア
    completeApiCall('nuanceAnalysis');
    return;
  }

  logOnce(`analysis_start_${engine}`, `🧠 ${engine}分析開始`);
  
  // 🚨 重要修正: インラインstyleのdisplay:noneを明示的に削除
  card.style.display = 'block';
  card.classList.add("show");
  el.textContent = `${window.currentLabels.analyzing_with_engine || '分析中...'} (${engine.toUpperCase()})`;

  // 🔍 Dev Monitor更新
  updateDevMonitorAnalysis(engine, '実行中');

  const startTime = performance.now();

  fetch("/get_nuance", {
    method: "POST",
    credentials: "include",
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
    },
    body: JSON.stringify({
      engine: engine,
      // 🔧 Phase 3c-4 FIX: 言語ペア情報を追加
      language_pair: document.getElementById('language_pair')?.value || 'ja-en'
    })
  })
    .then(response => {
      logOnce(`analysis_response_${engine}`, `🧠 ${engine}分析レスポンス受信: ${response.status}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      logOnce(`analysis_data_${engine}`, `🧠 ${engine}分析データ受信完了`);
      
      // 🧠 新旧レスポンス形式に対応
      const analysisText = data.nuance || data.analysis || data.analysis_text || data.result;
      
      if (analysisText) {
        logOnce(`analysis_display_${engine}`, `✅ ${engine}分析結果表示開始`);
        logOnce(`analysis_text_length_${engine}`, `📊 分析結果テキスト長: ${analysisText.length} 文字`);
        
        el.textContent = analysisText;
        
        // 強制的に確認
        logOnce(`analysis_text_set_${engine}`, `✅ テキスト設定後: ${el.textContent.length}文字`);
        
        const trigger = document.getElementById("analysis-engine-trigger");
        if (trigger) trigger.style.display = "none";

        // 🧠 分析エンジン情報を表示
        if (data.analysis_engine) {
          logOnce(`analysis_engine_${engine}`, `🧠 分析実行エンジン: ${data.analysis_engine}`);
        }

        // 🚨 重要修正：サーバー側推奨結果を優先使用
        const recommendation = data.recommendation || data.rec || data.recommended_engine;
        if (typeof processServerRecommendation === 'function' && recommendation) {
          // サーバー側で抽出された推奨結果を使用
          processServerRecommendation(recommendation, analysisText);
        } else if (typeof processGeminiRecommendation === 'function') {
          // フォールバック：従来のクライアント側推奨抽出
          logOnce('fallback_client_recommendation', '⚠️ Fallback: Using client-side recommendation extraction', 'warn');
          processGeminiRecommendation(analysisText);
        }

        logOnce(`analysis_timing_${engine}`, `⏱ ${engine}分析表示まで: ${Math.round(performance.now() - startTime)}ms`);
        
        // 🔍 Dev Monitor完了状態更新
        updateDevMonitorAnalysis(engine, '完了', recommendation);
        
        showToast(`${engine.toUpperCase()}分析が完了しました`, 'success');
        
        // 🔒 Phase 9c: API状態をクリア
        completeApiCall('nuanceAnalysis');
      } else {
        logOnce(`analysis_empty_${engine}`, `🚨 ${engine}分析結果が空です`, 'error');
        el.textContent = `分析結果を取得できませんでした (${engine}) - データ確認が必要`;
        showToast(`${engine.toUpperCase()}分析結果が空でした`, 'error');
        
        // 🔒 Phase 9c: API状態をクリア
        completeApiCall('nuanceAnalysis');
      }
    })
    .catch(error => {
      logOnce(`analysis_error_${engine}`, `${engine}分析エラー: ${error.message}`, 'error');
      el.textContent = `分析エラー: ${engine}による分析に失敗しました`;
      
      // 🔍 Dev Monitorエラー状態更新
      updateDevMonitorAnalysis(engine, 'エラー');
      
      showToast(`${engine.toUpperCase()}分析でエラーが発生しました`, 'error');
      
      // 🔒 Phase 9c: API状態をクリア
      completeApiCall('nuanceAnalysis');
    });
}

function updateDevMonitorAnalysis(engine, status, recommendation = null) {
  const engineStatusElement = document.getElementById('analysisEngineStatus');
  
  if (engineStatusElement) {
    engineStatusElement.textContent = status;
    
    if (status === 'in_progress' || status === '実行中') {
      engineStatusElement.style.color = '#FF9500';
    } else if (status === 'completed' || status === '完了') {
      engineStatusElement.style.color = '#34C759';
    } else if (status === 'error' || status === 'エラー') {
      engineStatusElement.style.color = '#FF3B30';
    }
  }
  
  if (recommendation) {
    // 既存の推奨判定表示も更新
    const geminiRecommendation = document.getElementById('geminiRecommendation');
    const confidenceScore = document.getElementById('confidenceScore');
    
    if (geminiRecommendation) {
      geminiRecommendation.textContent = recommendation.result || recommendation.recommendation || 'unknown';
    }
    
    if (confidenceScore && recommendation.confidence !== undefined) {
      confidenceScore.textContent = `${Math.round(recommendation.confidence * 100)}%`;
    }
  }
}

function processServerRecommendation(recommendationData, geminiAnalysis) {
  if (!recommendationData) {
    console.warn('⚠️ No server recommendation data provided, falling back to client-side');
    processGeminiRecommendation(geminiAnalysis);
    return;
  }
  
  try {
    const { result, confidence, method, source } = recommendationData;
    
    console.log(`🎯 SERVER RECOMMENDATION PROCESSING:
      Result: ${result}
      Confidence: ${confidence}%
      Method: ${method}
      Source: ${source}
      Original Analysis: "${geminiAnalysis.substring(0, 100)}..."`);
    
    // サーバー側の推奨結果をそのまま使用（信頼性が高い）
    let displayRecommendation = result;
    let displayReason = `サーバー側LLM分析 (${method}, 信頼度: ${confidence}%)`;
    let displayConfidence = confidence;
    
    // 表示名の正規化
    if (result.toLowerCase() === 'enhanced') {
      displayRecommendation = 'Enhanced';
    } else if (result.toLowerCase() === 'chatgpt') {
      displayRecommendation = 'ChatGPT';
    } else if (result.toLowerCase() === 'gemini') {
      displayRecommendation = 'Gemini';
    }
    
    console.log(`🎯 FINAL SERVER RECOMMENDATION:
      Display: ${displayRecommendation}
      Reason: ${displayReason}
      Confidence: ${displayConfidence}%
      
      🔍 VERIFICATION CHECK:
      - Server says: "${result}"
      - UI will show: "${displayRecommendation}"
      - Match status: ${result.toLowerCase() === displayRecommendation.toLowerCase() ? '✅ CORRECT' : '❌ MISMATCH'}`);
    
    // サーバー側推奨結果で画面更新（詳細データ付き）
    const detailData = {
      method: method,
      log_detail: `推奨=${result}, 信頼度=${confidence}%, 手法=${method}`,
      reasoning: geminiAnalysis ? geminiAnalysis.substring(0, 300) + '...' : '',
      source: source
    };
    updateGeminiRecommendation(displayRecommendation, displayReason, displayConfidence, detailData);
    
    // 開発者パネルログ
    if (window.userRole === 'admin' || window.userRole === 'developer') {
      addDevLogEntry('success', 'サーバー推奨採用', `${result} → ${displayRecommendation} (${confidence}%)`);
    }
    
  } catch (error) {
    console.error('🚨 Server recommendation processing error:', error);
    console.log('Falling back to client-side recommendation extraction');
    processGeminiRecommendation(geminiAnalysis);
  }
}

function processGeminiRecommendation(geminiAnalysis) {
  if (!geminiAnalysis) return;
  
  try {
    console.log('🧠 Gemini Analysis Raw:', geminiAnalysis);
    
    // Gemini分析から推奨を抽出（厳密なパターンマッチング）
    const analysisText = geminiAnalysis.toLowerCase();
    let recommendation = '判定中';
    let reason = 'LLM分析処理中';
    let confidence = 0;
    let improvedTranslation = null;
    
    // 🚨 重要修正：英語・日本語両対応の推奨判定（優先順位厳格化）
    
    // 1. Gemini推奨の明確な判定（最優先：英語・日本語対応）
    if ((analysisText.includes('gemini') && (analysisText.includes('recommend') || analysisText.includes('推奨'))) ||
        (analysisText.includes('i recommend the gemini') || analysisText.includes('recommend the gemini')) ||
        (analysisText.includes('gemini translation') && (analysisText.includes('best') || analysisText.includes('better') || analysisText.includes('良い'))) ||
        (analysisText.includes('gemini') && (analysisText.includes('最も') || analysisText.includes('適切') || analysisText.includes('良い')))) {
      recommendation = 'Gemini';
      reason = 'Gemini分析：Gemini翻訳を推奨';
      confidence = 90;
    }
    // 2. Enhanced推奨の明確な判定
    else if ((analysisText.includes('enhanced') && (analysisText.includes('recommend') || analysisText.includes('推奨'))) ||
             (analysisText.includes('i recommend the enhanced') || analysisText.includes('recommend the enhanced')) ||
             (analysisText.includes('enhanced') && (analysisText.includes('最も') || analysisText.includes('適切') || analysisText.includes('自然'))) ||
             (analysisText.includes('enhanced') && (analysisText.includes('best') || analysisText.includes('better') || analysisText.includes('良い')))) {
      recommendation = 'Enhanced';
      reason = 'Gemini分析：Enhanced翻訳を推奨';
      confidence = 90;
    }
    // 3. ChatGPT推奨の明確な判定
    else if ((analysisText.includes('chatgpt') && (analysisText.includes('recommend') || analysisText.includes('推奨'))) ||
             (analysisText.includes('i recommend the chatgpt') || analysisText.includes('recommend the chatgpt')) ||
             (analysisText.includes('chatgpt') && (analysisText.includes('最も') || analysisText.includes('適切') || analysisText.includes('良い'))) ||
             (analysisText.includes('chatgpt') && (analysisText.includes('best') || analysisText.includes('better')))) {
      recommendation = 'ChatGPT';
      reason = 'Gemini分析：ChatGPT翻訳を推奨';
      confidence = 85;
    }
    // 4. 改良版翻訳提案の検出
    else if (analysisText.includes('組み合わせ') || analysisText.includes('修正') || analysisText.includes('ベース')) {
      recommendation = 'Gemini改良版';
      reason = 'Gemini分析：複数翻訳の組み合わせ提案';
      confidence = 95;
      
      // 改良版翻訳文の抽出
      improvedTranslation = extractGeminiImprovedTranslation(geminiAnalysis);
    }
    // 5. デフォルト判定（複数候補がある場合）
    else {
      // より詳細な解析
      if (analysisText.includes('enhanced')) {
        recommendation = 'Enhanced';
        reason = 'Enhanced翻訳への言及あり';
        confidence = 70;
      } else if (analysisText.includes('chatgpt')) {
        recommendation = 'ChatGPT';
        reason = 'ChatGPT翻訳への言及あり';
        confidence = 65;
      } else {
        recommendation = '判定不能';
        reason = '明確な推奨が見つかりませんでした';
        confidence = 0;
      }
    }
    
    console.log(`🧠 Gemini Recommendation Analysis:
      Original: "${geminiAnalysis.substring(0, 200)}..."
      Analysis Text (lowercase): "${analysisText.substring(0, 200)}..."
      Recommendation: ${recommendation}
      Reason: ${reason}
      Confidence: ${confidence}%
      Improved Translation: ${improvedTranslation ? 'Yes' : 'No'}
      
      TEST_RESULT: 推奨判定表示テスト
      - 分析元データ: ${geminiAnalysis.includes('recommend') ? '✅ recommend含む' : '❌ recommend含まず'}
      - Gemini言及: ${analysisText.includes('gemini') ? '✅ gemini含む' : '❌ gemini含まず'}
      - Enhanced言及: ${analysisText.includes('enhanced') ? '✅ enhanced含む' : '❌ enhanced含まず'}
      - ChatGPT言及: ${analysisText.includes('chatgpt') ? '✅ chatgpt含む' : '❌ chatgpt含まず'}
      - 最終判定結果: ${recommendation}
      - 判定ロジック状況: ${recommendation === 'Gemini' ? '✅ PASS' : '❌ FAIL'}`);
    
    // クライアント側推奨判定の詳細データ
    const detailData = {
      method: 'client_side_pattern_matching',
      log_detail: `推奨=${recommendation}, 信頼度=${confidence}%, 手法=client_side`,
      reasoning: geminiAnalysis ? geminiAnalysis.substring(0, 300) + '...' : '',
      source: 'client_side_extraction'
    };
    updateGeminiRecommendation(recommendation, reason, confidence, detailData);
    
    // 4つ目翻訳があれば表示
    if (improvedTranslation) {
      showGeminiImprovedTranslation(improvedTranslation);
    }
    
  } catch (error) {
    console.error('Gemini推奨処理エラー:', error);
    const errorDetailData = {
      method: 'error',
      log_detail: 'エラー: LLM分析処理に失敗しました',
      reasoning: error.message || '不明なエラーが発生しました',
      source: 'error_handling'
    };
    updateGeminiRecommendation('エラー', 'LLM分析に失敗', 0, errorDetailData);
  }
}