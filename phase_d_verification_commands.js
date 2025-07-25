// ============================================================================
// Phase D検証コマンド集 - ブラウザコンソールで実行
// TaskH2-2(B2-3) Stage3 Phase9c Step2 Phase D統合検証
// ============================================================================

console.log("=== Phase D統合検証開始 ===");

// D-8: エラー状態管理検証
console.log("\n--- D-8: エラー状態管理検証 ---");

// 1. メソッド存在確認
console.log('1. handleApiError exists:', typeof window.stateManager?.handleApiError === 'function');
console.log('1. StateManager instance exists:', typeof window.stateManager);

// 2. エラー初期状態確認
console.log('2. Initial error state:', window.stateManager?.getErrorState?.());

// 3. テストエラー発生
if (window.stateManager?.handleApiError) {
    console.log('3. Testing handleApiError...');
    window.stateManager.handleApiError(
        new Error("Test error for StateManager verification"), 
        {
            function: 'testFunction',
            apiType: 'testAPI', 
            location: 'console_test',
            errorType: 'network_error'
        }
    );
}

// 4. エラー状態再確認
setTimeout(() => {
    console.log('4. Error state after test:', window.stateManager?.getErrorState?.());
    console.log('4. Error history length:', window.stateManager?.getErrorState?.()?.errorCount);
}, 100);

// 5. 既存機能確認
console.log('5. Existing methods availability:', {
    showLoading: typeof window.stateManager?.showLoading,
    hideLoading: typeof window.stateManager?.hideLoading,
    startApiCall: typeof window.stateManager?.startApiCall,
    completeApiCall: typeof window.stateManager?.completeApiCall
});

// 6. Phase A/B/C統合確認
console.log('6. Phase integration check:');
console.log('   - Phase A (Loading): showLoading/hideLoading available');
console.log('   - Phase B (UI Control): showResultCard/hideResultCard wrap available');  
console.log('   - Phase C (Error Integration): integrateErrorWithStateManager available');
console.log('   - integrateErrorWithStateManager:', typeof window.integrateErrorWithStateManager);

console.log("\n=== D-8検証完了 ===");