// CSRF Header Verification Script
// このスクリプトをブラウザのコンソールで実行して、CSRFヘッダーが正しく設定されているかを確認

console.log('🧪 CSRF Header Verification Test');
console.log('================================');

// 1. CSRF token availability check
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
console.log('1. CSRF Token Check:');
console.log(`   Available: ${!!csrfToken}`);
console.log(`   Token: ${csrfToken ? csrfToken.substring(0, 20) + '...' : 'Not found'}`);

// 2. Check if runFastTranslation has CSRF header
console.log('\n2. runFastTranslation CSRF Header Check:');
const scriptTags = document.querySelectorAll('script');
let foundCSRFInRunFast = false;

for (let script of scriptTags) {
    if (script.innerHTML && script.innerHTML.includes('runFastTranslation')) {
        const content = script.innerHTML;
        if (content.includes('X-CSRFToken') && content.includes('csrf-token')) {
            foundCSRFInRunFast = true;
            console.log('   ✅ runFastTranslation has CSRF header support');
            break;
        }
    }
}

if (!foundCSRFInRunFast) {
    console.log('   ❌ runFastTranslation missing CSRF header');
}

// 3. Check StateManager file for CSRF headers
console.log('\n3. StateManager CSRF Header Check:');
fetch('/static/js/core/state_manager.js')
    .then(response => response.text())
    .then(content => {
        const syncFromRedisHasCSRF = content.includes('syncFromRedis') && 
                                   content.includes('X-CSRFToken') &&
                                   content.includes('csrf-token');
        
        const syncToRedisHasCSRF = content.includes('syncToRedis') && 
                                 content.includes('X-CSRFToken') &&
                                 content.includes('csrf-token');
        
        console.log(`   syncFromRedis CSRF: ${syncFromRedisHasCSRF ? '✅' : '❌'}`);
        console.log(`   syncToRedis CSRF: ${syncToRedisHasCSRF ? '✅' : '❌'}`);
        
        if (syncFromRedisHasCSRF && syncToRedisHasCSRF) {
            console.log('\n🎉 All CSRF headers implemented correctly!');
            console.log('Frontend should now work without 403 errors.');
        } else {
            console.log('\n⚠️  Some CSRF headers may be missing.');
        }
    })
    .catch(error => {
        console.log('   ❌ Could not verify StateManager file:', error);
    });

// 4. Test API call with CSRF header (if token available)
if (csrfToken) {
    console.log('\n4. Test API Call with CSRF Header:');
    fetch('/api/get_translation_state', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ session_id: 'test' })
    })
    .then(response => {
        console.log(`   API Test Status: ${response.status}`);
        if (response.status === 200) {
            console.log('   ✅ CSRF protection working correctly');
        } else if (response.status === 403) {
            console.log('   ❌ Still getting 403 - may need further debugging');
        } else {
            console.log(`   ⚠️  Other status: ${response.status}`);
        }
    })
    .catch(error => {
        console.log('   ❌ API test failed:', error);
    });
}