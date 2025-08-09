/**
 * 🎯 TaskH2-2(B2-3) Stage 2 Phase 7: エンジンAPI通信モジュール
 * 責務分離による保守性向上実装
 * 
 * Pure Communication Layer - 層間通信のみ
 * - AJAX通信のみ
 * - エラーハンドリングのみ
 * - UI操作なし
 * - DOM操作なし
 * 
 * 分離元: index.html Lines initializeAnalysisEngine + AJAX通信部分
 * 分離日: 2025年7月20日
 */

class EngineApiClient {
    /**
     * 純粋な責務: エンジンAPI通信のみ
     * UI操作・DOM操作を一切含まない通信専用クラス
     */
    
    constructor() {
        this.baseUrl = '';  // 相対パス使用
        this.defaultTimeout = 10000;  // 10秒タイムアウト
    }
    
    /**
     * CSRFトークン取得（純粋な通信支援機能）
     * 
     * @returns {string} - CSRFトークン
     */
    getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }
    
    /**
     * サーバーエンジン状態更新（純粋な通信処理）
     * 
     * @param {string} engine - 設定するエンジン名
     * @returns {Promise<Object>} - API応答
     */
    async updateServerEngineState(engine) {
        try {
            const response = await fetch('/set_analysis_engine', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    engine: engine
                }),
                signal: AbortSignal.timeout(this.defaultTimeout)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            console.log(`🔗 Server engine state updated: ${engine}`);
            console.log(`📡 API response:`, data);
            
            return {
                success: true,
                data: data,
                engine: engine
            };
            
        } catch (error) {
            console.error(`❌ Server engine state update failed: ${engine}`, error);
            
            return {
                success: false,
                error: error.message,
                engine: engine
            };
        }
    }
    
    /**
     * サーバーエンジン状態取得（純粋な通信処理）
     * 
     * @returns {Promise<Object>} - 現在のエンジン状態
     */
    async getCurrentEngineState() {
        try {
            const response = await fetch('/get_analysis_engine_state', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                signal: AbortSignal.timeout(this.defaultTimeout)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            console.log('🔗 Current engine state retrieved:', data);
            
            return {
                success: true,
                state: data.state
            };
            
        } catch (error) {
            console.error('❌ Engine state retrieval failed:', error);
            
            return {
                success: false,
                error: error.message
            };
        }
    }
    
    /**
     * エンジン状態同期（純粋な通信調整）
     * 
     * @param {string} engine - 同期するエンジン名
     * @param {Function} onSuccess - 成功時コールバック
     * @param {Function} onError - エラー時コールバック
     */
    async syncEngineState(engine, onSuccess = null, onError = null) {
        try {
            const result = await this.updateServerEngineState(engine);
            
            if (result.success) {
                console.log(`✅ Engine state sync successful: ${engine}`);
                
                if (onSuccess && typeof onSuccess === 'function') {
                    onSuccess(result.data, engine);
                }
                
                return result;
            } else {
                console.error(`❌ Engine state sync failed: ${engine}`, result.error);
                
                if (onError && typeof onError === 'function') {
                    onError(result.error, engine);
                }
                
                return result;
            }
            
        } catch (error) {
            console.error(`❌ Engine state sync error: ${engine}`, error);
            
            if (onError && typeof onError === 'function') {
                onError(error.message, engine);
            }
            
            return {
                success: false,
                error: error.message,
                engine: engine
            };
        }
    }
    
    /**
     * バッチエンジン状態取得（純粋な通信最適化）
     * 
     * @param {Array<string>} engines - 取得対象エンジンリスト
     * @returns {Promise<Object>} - バッチ結果
     */
    async getBatchEngineStatus(engines) {
        try {
            // 現在のAPIは単一状態取得のみサポート
            // 将来の拡張に備えた設計
            const currentState = await this.getCurrentEngineState();
            
            if (currentState.success) {
                return {
                    success: true,
                    engines: engines.reduce((acc, engine) => {
                        acc[engine] = {
                            available: true,
                            current: currentState.state.current_engine === engine
                        };
                        return acc;
                    }, {})
                };
            } else {
                return currentState;
            }
            
        } catch (error) {
            console.error('❌ Batch engine status failed:', error);
            
            return {
                success: false,
                error: error.message
            };
        }
    }
}

// グローバルインスタンス作成（既存コードとの互換性）
const engineApiClient = new EngineApiClient();

/**
 * 後方互換性のための関数エイリアス
 * 既存のコードから呼び出し可能
 */

/**
 * サーバーエンジン状態更新（後方互換性）
 * 
 * @param {string} engine - エンジン名
 * @param {Function} onSuccess - 成功コールバック
 * @param {Function} onError - エラーコールバック
 */
async function updateServerEngineState(engine, onSuccess = null, onError = null) {
    return await engineApiClient.syncEngineState(engine, onSuccess, onError);
}

/**
 * 現在のエンジン状態取得（後方互換性）
 * 
 * @returns {Promise<Object>} - エンジン状態
 */
async function getCurrentEngineState() {
    return await engineApiClient.getCurrentEngineState();
}