// Task #7-3 SL-3 Phase 3: StateManager翻訳セクション動作テスト
// 2025-07-30 実行: StateManagerの翻訳同期機能テスト（同期テスト）

console.log("=== Task #7-3 SL-3 Phase 3: StateManager翻訳セクション動作テスト ===");

// 1. StateManagerインスタンス確認
if (typeof window.StateManager === 'undefined') {
    console.error("❌ StateManager not found in window");
} else {
    console.log("✅ StateManager found");
    
    // 2. translation sectionの構造確認
    const translation = window.StateManager.states.translation;
    if (!translation) {
        console.error("❌ states.translation not found");
    } else {
        console.log("✅ states.translation structure:", translation);
        
        // 3. fieldMapping確認
        console.log("📋 fieldMapping:");
        Object.entries(translation.fieldMapping).forEach(([ui, redis]) => {
            console.log(`  ${ui} → ${redis}`);
        });
        
        // 4. getRedisKey()テスト
        console.log("\n🔧 getRedisKey() Test:");
        const testFields = ['inputText', 'translatedText', 'contextInfo'];
        testFields.forEach(field => {
            const redisKey = window.StateManager.getRedisKey(field);
            console.log(`  ${field} → ${redisKey}`);
        });
        
        // 5. getUIKey()テスト
        console.log("\n🔧 getUIKey() Test:");
        const testRedisKeys = ['input_text', 'translated_text', 'context_info'];
        testRedisKeys.forEach(redisKey => {
            const uiKey = window.StateManager.getUIKey(redisKey);
            console.log(`  ${redisKey} → ${uiKey}`);
        });
        
        // 6. syncStatus初期状態確認
        console.log("\n📊 syncStatus initial state:", translation.syncStatus);
        
        // 7. cache初期状態確認
        console.log("📊 cache initial state:", translation.cache);
        
        // 8. lastSync初期状態確認
        console.log("📊 lastSync initial state:", translation.lastSync);
    }
}

console.log("\n=== StateManager翻訳セクション動作テスト完了 ===");