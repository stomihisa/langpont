/**
 * 🎯 Task#9-4 AP-1 Ph4 Step4（再挑戦）- 監視レイヤー（OL-0＋Level1）
 * クライアント側データフロー監視
 * 作成日: 2025-08-15
 */

class ClientDebugLogger {
    constructor() {
        this.requestId = null;
        this.logs = [];
        this.enabled = true; // 本番では false に設定
        this.debugEndpoint = '/api/debug_log';
        
        // サーバーからのRequest-IDを取得試行
        this.syncRequestIdFromServer();
    }
    
    syncRequestIdFromServer() {
        // Meta タグまたは window.__boot からRequest-IDを取得
        const metaRequestId = document.querySelector('meta[name="request-id"]');
        if (metaRequestId) {
            this.requestId = metaRequestId.getAttribute('content');
            return;
        }
        
        // window.__boot からの取得を試行
        if (window.__boot && window.__boot.request_id) {
            this.requestId = window.__boot.request_id;
            return;
        }
        
        // フォールバック: クライアント生成
        this.requestId = this.generateRequestId();
    }
    
    generateRequestId() {
        return Math.random().toString(36).substr(2, 8);
    }
    
    log(location, operation, data = null, options = {}) {
        if (!this.enabled) return;
        
        const timestamp = new Date().toISOString().substr(11, 12);
        const dataPreview = data ? JSON.stringify(data).substr(0, 100) : 'N/A';
        
        const logEntry = {
            reqId: this.requestId,
            time: timestamp,
            location: location,
            operation: operation,
            dataPreview: dataPreview,
            dataSize: data ? JSON.stringify(data).length : 0,
            ...options
        };
        
        // コンソール出力
        console.log(`🔍 [${this.requestId}] ${location}:${operation} ->`, dataPreview);
        
        // ログ配列に保存
        this.logs.push(logEntry);
        
        // サーバーへの非同期送信
        this.sendLogToServer(logEntry);
        
        return logEntry;
    }
    
    async sendLogToServer(logEntry) {
        if (!this.enabled) return;
        
        try {
            const response = await fetch(this.debugEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(logEntry)
            });
            
            if (!response.ok) {
                console.warn('Debug log送信失敗:', response.status);
            }
        } catch (error) {
            // ログ送信エラーは無視（サイレント失敗）
        }
    }
    
    // 復元シーケンス専用ログ
    logRestore(phase, data = null, options = {}) {
        return this.log('JS-RESTORE', phase, data, {
            category: 'restoration',
            ...options
        });
    }
    
    // 描画完了専用ログ  
    logRender(component, data = null, options = {}) {
        return this.log('JS-RENDER', component, data, {
            category: 'ui_rendering',
            ...options
        });
    }
    
    // API呼び出し専用ログ
    logApi(endpoint, phase, data = null, options = {}) {
        return this.log('JS-API', `${endpoint}_${phase}`, data, {
            category: 'api_call',
            ...options
        });
    }
    
    // エラー専用ログ
    logError(location, error, context = null) {
        return this.log(location, 'ERROR', {
            message: error.message || error,
            stack: error.stack,
            context: context
        }, {
            category: 'error',
            level: 'error'
        });
    }
    
    // ログのサマリーを取得
    getSummary() {
        const categoryCounts = {};
        this.logs.forEach(log => {
            const category = log.category || 'other';
            categoryCounts[category] = (categoryCounts[category] || 0) + 1;
        });
        
        return {
            totalLogs: this.logs.length,
            requestId: this.requestId,
            categories: categoryCounts,
            lastLog: this.logs[this.logs.length - 1] || null
        };
    }
    
    // デバッグ情報をコンソールに出力
    dumpLogs() {
        console.group(`🔍 Debug Logs Summary [${this.requestId}]`);
        console.log('Summary:', this.getSummary());
        console.log('All Logs:', this.logs);
        console.groupEnd();
    }
    
    // ログクリア
    clear() {
        this.logs = [];
        console.log(`🔍 Debug logs cleared for request ${this.requestId}`);
    }
}

// グローバルインスタンス
window.debugLog = new ClientDebugLogger();

// エラーハンドリング統合
window.addEventListener('error', (event) => {
    window.debugLog.logError('GLOBAL', event.error || event.message, {
        filename: event.filename,
        line: event.lineno,
        column: event.colno
    });
});

window.addEventListener('unhandledrejection', (event) => {
    window.debugLog.logError('PROMISE', event.reason, {
        type: 'unhandledrejection'
    });
});

// 初期化完了ログ
window.debugLog.log('JS-INIT', 'CLIENT_LOGGER_READY', {
    enabled: window.debugLog.enabled,
    requestId: window.debugLog.requestId
});