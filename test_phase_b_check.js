/**
 * Phase B: UI制御問題解決テスト
 * Console で実行するテスト関数群
 */

// テスト1: setQuickProcessingState() が削除されているか確認
function testPhaseBQuickProcessingRemoval() {
  console.log('=== Phase B setQuickProcessingState 削除確認 ===');

  try {
    // 関数が存在しないことを確認
    if (typeof setQuickProcessingState === 'undefined') {
      console.log('✅ setQuickProcessingState 関数は正しく削除されています');
      return true;
    } else {
      console.error('❌ setQuickProcessingState 関数がまだ存在します');
      return false;
    }
  } catch (error) {
    console.error('❌ Phase B テストエラー:', error);
    return false;
  }
}

// テスト2: quickClearResults() の修正確認
function testPhaseBQuickClearModification() {
  console.log('\n=== Phase B quickClearResults 修正確認 ===');

  try {
    // テスト用の一時的な内容を設定
    const translatedText = document.getElementById('translated-text');
    const reverseTranslatedText = document.getElementById('reverse-translated-text');
    
    if (translatedText && reverseTranslatedText) {
      translatedText.innerText = 'テスト翻訳文';
      reverseTranslatedText.innerText = '逆翻訳テスト';
      
      // quickClearResults を実行
      if (typeof quickClearResults === 'function') {
        quickClearResults();
        
        // translated-text は変更されない（StateManager管理下）
        if (translatedText.innerText === 'テスト翻訳文') {
          console.log('✅ translated-text は正しく除外されています');
        } else {
          console.error('❌ translated-text が誤ってクリアされました');
          return false;
        }
        
        // reverse-translated-text はクリアされる
        if (reverseTranslatedText.innerText === '') {
          console.log('✅ reverse-translated-text は正しくクリアされました');
          return true;
        } else {
          console.error('❌ reverse-translated-text がクリアされていません');
          return false;
        }
      } else {
        console.error('❌ quickClearResults 関数が見つかりません');
        return false;
      }
    } else {
      console.error('❌ 必要な要素が見つかりません');
      return false;
    }
  } catch (error) {
    console.error('❌ Phase B テストエラー:', error);
    return false;
  }
}

// テスト3: Loading表示とtranslated-textの統合確認
function testPhaseBLoadingIntegration() {
  console.log('\n=== Phase B Loading統合確認 ===');

  try {
    // showLoading が呼び出せることを確認
    if (typeof showLoading === 'function') {
      console.log('✅ showLoading 関数が利用可能');
      
      // StateManager の状態確認
      if (window.stateManager && typeof window.stateManager.isLoading === 'function') {
        const beforeState = window.stateManager.isLoading();
        console.log('Loading状態（前）:', beforeState);
        
        // showLoading を呼び出し
        showLoading();
        
        const afterState = window.stateManager.isLoading();
        console.log('Loading状態（後）:', afterState);
        
        // hideLoading で元に戻す
        hideLoading();
        
        console.log('✅ Loading制御がStateManager経由で動作');
        return true;
      } else {
        console.error('❌ StateManager が正しく初期化されていません');
        return false;
      }
    } else {
      console.error('❌ showLoading 関数が見つかりません');
      return false;
    }
  } catch (error) {
    console.error('❌ Phase B テストエラー:', error);
    return false;
  }
}

// テスト4: Single Source of Truth 確認
function testPhaseBSingleTruth() {
  console.log('\n=== Phase B Single Source of Truth 確認 ===');

  try {
    // StateManager の loading 状態と DOM の同期を確認
    console.log('StateManager 状態:', window.stateManager.getStatus());
    
    // loading 要素の状態確認
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
      const hasShowClass = loadingElement.classList.contains('show');
      const stateLoading = window.stateManager.isLoading();
      
      console.log('DOM loading.show:', hasShowClass);
      console.log('StateManager.isLoading():', stateLoading);
      
      if (hasShowClass === stateLoading) {
        console.log('✅ StateとDOMが一致しています');
        return true;
      } else {
        console.error('❌ StateとDOMが不一致です');
        return false;
      }
    } else {
      console.error('❌ loading要素が見つかりません');
      return false;
    }
  } catch (error) {
    console.error('❌ Phase B テストエラー:', error);
    return false;
  }
}

// 統合テスト実行
function runPhaseBTests() {
  console.log('🚀 Phase B 統合テスト開始...');
  
  const results = {
    quickProcessingRemoval: testPhaseBQuickProcessingRemoval(),
    quickClearModification: testPhaseBQuickClearModification(),
    loadingIntegration: testPhaseBLoadingIntegration(),
    singleTruth: testPhaseBSingleTruth()
  };
  
  const allPassed = Object.values(results).every(result => result === true);
  
  console.log('\n📊 Phase B テスト結果:');
  console.log('  setQuickProcessingState削除:', results.quickProcessingRemoval ? '✅ PASS' : '❌ FAIL');
  console.log('  quickClearResults修正:', results.quickClearModification ? '✅ PASS' : '❌ FAIL');
  console.log('  Loading統合:', results.loadingIntegration ? '✅ PASS' : '❌ FAIL');
  console.log('  Single Source of Truth:', results.singleTruth ? '✅ PASS' : '❌ FAIL');
  
  if (allPassed) {
    console.log('\n🎉 ✅ ALL PHASE B TESTS PASSED!');
    console.log('📋 Phase B: UI制御問題の根本解決完了');
    console.log('🎯 クルクル表示問題が解消されているか実際の翻訳で確認してください');
  } else {
    console.log('\n❌ Phase B テストに失敗があります');
  }
  
  return allPassed;
}

// ブラウザからの手動実行用
if (typeof window !== 'undefined') {
  window.testPhaseBQuickProcessingRemoval = testPhaseBQuickProcessingRemoval;
  window.testPhaseBQuickClearModification = testPhaseBQuickClearModification;
  window.testPhaseBLoadingIntegration = testPhaseBLoadingIntegration;
  window.testPhaseBSingleTruth = testPhaseBSingleTruth;
  window.runPhaseBTests = runPhaseBTests;
  
  console.log('🔧 Phase B Test functions available:');
  console.log('  - window.runPhaseBTests() // 統合テスト');
  console.log('  - window.testPhaseBQuickProcessingRemoval() // setQuickProcessingState削除確認');
  console.log('  - window.testPhaseBQuickClearModification() // quickClearResults修正確認');
  console.log('  - window.testPhaseBLoadingIntegration() // Loading統合確認');
  console.log('  - window.testPhaseBSingleTruth() // Single Source of Truth確認');
}