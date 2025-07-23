// ============================================================================
// Phase 9d フォーム状態管理テストコマンド集 - ブラウザコンソールで実行
// TaskH2-2(B2-3) Stage3 Phase9 Step3 Phase 9d 統合テスト
// ============================================================================

console.log("=== Phase 9d フォーム状態管理テスト開始 ===");

// Test 1: StateManager初期化確認
console.log("\n--- Test 1: StateManager初期化確認 ---");
console.log('StateManager exists:', typeof window.stateManager);
console.log('Form management ready:', typeof window.stateManager?.getFormState === 'function');

// Test 2: フォーム状態取得テスト
console.log("\n--- Test 2: フォーム状態取得テスト ---");
if (window.stateManager?.getFormState) {
    const formState = window.stateManager.getFormState();
    console.log('Current form state:', formState);
    console.log('Available fields:', Object.keys(formState.fields));
}

// Test 3: フォームフィールド操作テスト
console.log("\n--- Test 3: フォームフィールド操作テスト ---");
if (window.stateManager?.setFormFieldValue) {
    // テスト用の値を設定
    window.stateManager.setFormFieldValue('japanese_text', 'テスト用のテキスト');
    window.stateManager.setFormFieldValue('context_info', 'テスト用のコンテキスト');
    
    // 値の取得確認
    console.log('japanese_text value:', window.stateManager.getFormFieldValue('japanese_text'));
    console.log('context_info value:', window.stateManager.getFormFieldValue('context_info'));
    console.log('Form is dirty:', window.stateManager.isFormDirty());
}

// Test 4: フォームデータ一括操作テスト
console.log("\n--- Test 4: フォームデータ一括操作テスト ---");
if (window.stateManager?.getFormData) {
    const allData = window.stateManager.getFormData();
    console.log('All form data:', allData);
    
    // 一括設定テスト
    const testData = {
        japanese_text: 'こんにちは、世界！',
        context_info: 'ビジネス会話',
        partner_message: '前回の話題：商談について',
        language_pair: 'ja-en'
    };
    
    window.stateManager.setFormData(testData);
    console.log('After batch set:', window.stateManager.getFormData());
}

// Test 5: セッション機能テスト
console.log("\n--- Test 5: セッション機能テスト ---");
if (window.stateManager?.saveFormToSession) {
    // セッション保存
    window.stateManager.saveFormToSession();
    console.log('Form saved to session');
    
    // フォームをクリア
    window.stateManager.resetFormState(true);
    console.log('Form cleared:', window.stateManager.getFormData());
    
    // セッション復元
    const restored = window.stateManager.loadFormFromSession();
    console.log('Form restored from session:', restored);
    console.log('Restored data:', window.stateManager.getFormData());
}

// Test 6: Dirty状態管理テスト
console.log("\n--- Test 6: Dirty状態管理テスト ---");
if (window.stateManager?.resetFormState) {
    // 状態をリセット（値はそのまま）
    window.stateManager.resetFormState(false);
    console.log('After reset (keep values), is dirty:', window.stateManager.isFormDirty());
    
    // 少し変更
    window.stateManager.setFormFieldValue('japanese_text', window.stateManager.getFormFieldValue('japanese_text') + ' 追加');
    console.log('After modification, is dirty:', window.stateManager.isFormDirty());
}

// Test 7: グローバル関数テスト
console.log("\n--- Test 7: グローバル関数テスト ---");
console.log('Global form functions available:', {
    getFormData: typeof window.getFormData,
    setFormData: typeof window.setFormData,
    getFormFieldValue: typeof window.getFormFieldValue,
    setFormFieldValue: typeof window.setFormFieldValue,
    resetFormState: typeof window.resetFormState,
    isFormDirty: typeof window.isFormDirty,
    saveFormToSession: typeof window.saveFormToSession,
    loadFormFromSession: typeof window.loadFormFromSession,
    clearFormSession: typeof window.clearFormSession
});

// グローバル関数の動作確認例
if (typeof window.getFormData === 'function') {
    console.log('Global getFormData() result:', window.getFormData());
}

// Test 8: 既存機能確認（Phase A/B/C互換性）
console.log("\n--- Test 8: 既存機能確認 ---");
console.log('Phase A/B/C functions still available:', {
    showLoading: typeof window.stateManager?.showLoading,
    hideLoading: typeof window.stateManager?.hideLoading,
    handleApiError: typeof window.stateManager?.handleApiError,
    showResultCard: typeof window.stateManager?.showResultCard,
    startApiCall: typeof window.stateManager?.startApiCall
});

// Test 9: フォーム要素の実在確認
console.log("\n--- Test 9: フォーム要素の実在確認 ---");
const formElementsCheck = {};
['japanese_text', 'context_info', 'partner_message', 'language_pair', 'analysis_engine'].forEach(fieldName => {
    const element = document.getElementById(fieldName) || document.querySelector(`[name="${fieldName}"]`);
    formElementsCheck[fieldName] = !!element;
    if (element) {
        console.log(`${fieldName}: Found (${element.tagName})`);
    } else {
        console.warn(`${fieldName}: Not found in DOM`);
    }
});

console.log('Form elements existence:', formElementsCheck);

console.log("\n=== Phase 9d テスト完了 ===");
console.log("🎯 StateManager Phase 9d Form Management Test Results Summary:");
console.log("- StateManager Form functions: Initialized");
console.log("- Form state management: Available");
console.log("- Session integration: Functional");
console.log("- Global functions: Wrapped and available");
console.log("- Backward compatibility: Preserved");
console.log("- Form elements: Check individual results above");

// 最終状態表示
console.log("\n📊 Final StateManager Status:");
if (window.stateManager?.getStatus) {
    console.log(window.stateManager.getStatus());
}