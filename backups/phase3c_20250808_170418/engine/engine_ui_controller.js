/**
 * 🎯 TaskH2-2(B2-3) Stage 2 Phase 7: エンジンUI制御モジュール
 * 責務分離による保守性向上実装
 * 
 * Pure Client UI Layer - UI表示制御のみ
 * - DOM操作のみ
 * - 表示更新のみ
 * - ユーザー体験のみ
 * - サーバー通信なし
 * - 状態管理なし
 * 
 * 分離元: index.html Lines 464-515 (selectAnalysisEngine部分)
 * 分離日: 2025年7月20日
 */

class EngineUIController {
    /**
     * 純粋な責務: エンジンUI表示制御のみ
     * サーバー通信・状態管理を一切含まないUI専用クラス
     */
    
    constructor() {
        this.engineDescriptions = {
            'chatgpt': '🤖 ChatGPT が論理的で詳細な分析を提供します',
            'gemini': '💎 Gemini が翻訳の違いやニュアンスを丁寧に解説します',
            'claude': '🎭 Claude が深いニュアンスと文化的洞察を提供します'
        };
        
        this.engineDisplayNames = {
            'chatgpt': 'ChatGPT',
            'gemini': 'Gemini',
            'claude': 'Claude',
            'gpt4': 'GPT-4',
            'openai': 'OpenAI'
        };
    }
    
    /**
     * エンジン説明文の更新（純粋なUI表示制御）
     * 
     * @param {string} engine - 選択されたエンジン名
     * @returns {boolean} - 更新成功フラグ
     */
    updateEngineDescription(engine) {
        try {
            const descElement = document.getElementById('engineDescText');
            
            if (!descElement) {
                console.warn('engineDescText element not found');
                return false;
            }
            
            const description = this.engineDescriptions[engine];
            
            if (description) {
                descElement.textContent = description;
                console.log(`✅ Engine description updated for: ${engine}`);
                return true;
            } else {
                console.warn(`No description found for engine: ${engine}`);
                descElement.textContent = `${this.getDisplayName(engine)} エンジンが選択されました`;
                return false;
            }
            
        } catch (error) {
            console.error('Engine description update error:', error);
            return false;
        }
    }
    
    /**
     * エンジンの表示名取得（純粋なUI支援機能）
     * 
     * @param {string} engine - エンジン名
     * @returns {string} - 表示用エンジン名
     */
    getDisplayName(engine) {
        return this.engineDisplayNames[engine] || engine.charAt(0).toUpperCase() + engine.slice(1);
    }
    
    /**
     * エンジン選択成功時のUI更新（純粋なUI表示制御）
     * 
     * @param {string} engine - 選択されたエンジン名
     * @param {string} message - サーバーからのメッセージ
     */
    showSelectionSuccess(engine, message) {
        try {
            // 説明文を更新
            this.updateEngineDescription(engine);
            
            // 成功通知の表示（showToast関数が利用可能な場合）
            if (typeof showToast === 'function') {
                const displayName = this.getDisplayName(engine);
                showToast(`分析エンジンを ${displayName} に変更しました`, 'success');
            }
            
            console.log(`✅ Engine selection UI updated: ${engine}`);
            console.log(`📝 Server message: ${message}`);
            
        } catch (error) {
            console.error('Selection success UI update error:', error);
        }
    }
    
    /**
     * エンジン選択エラー時のUI更新（純粋なUI表示制御）
     * 
     * @param {string} engine - 選択しようとしたエンジン名
     * @param {string} errorMessage - エラーメッセージ
     */
    showSelectionError(engine, errorMessage) {
        try {
            // エラー通知の表示（showToast関数が利用可能な場合）
            if (typeof showToast === 'function') {
                showToast(`エンジン選択エラー: ${errorMessage}`, 'error');
            }
            
            console.error(`❌ Engine selection failed: ${engine}`);
            console.error(`📝 Error message: ${errorMessage}`);
            
        } catch (error) {
            console.error('Selection error UI update error:', error);
        }
    }
    
    /**
     * エンジン選択UI初期化（純粋なUI初期設定）
     */
    initializeEngineUI() {
        try {
            // 説明文要素の存在確認
            const descElement = document.getElementById('engineDescText');
            
            if (descElement && !descElement.textContent.trim()) {
                // デフォルト説明文を設定
                descElement.textContent = 'エンジンを選択してください';
            }
            
            console.log('✅ Engine UI initialized');
            
        } catch (error) {
            console.error('Engine UI initialization error:', error);
        }
    }
    
    /**
     * エンジン選択状態の視覚的表示更新（純粋なUI表示制御）
     * 
     * @param {string} selectedEngine - 選択されたエンジン名
     */
    updateSelectionVisualState(selectedEngine) {
        try {
            // 全エンジンボタンから選択状態をクリア
            const allButtons = document.querySelectorAll('.engine-btn');
            allButtons.forEach(btn => {
                btn.classList.remove('selected', 'active');
            });
            
            // 選択されたボタンに視覚的な選択状態を追加
            const selectedButton = document.querySelector(`[data-engine="${selectedEngine}"]`);
            if (selectedButton) {
                selectedButton.classList.add('selected');
                console.log(`✅ Visual selection state updated: ${selectedEngine}`);
            } else {
                console.warn(`Button not found for engine: ${selectedEngine}`);
            }
            
        } catch (error) {
            console.error('Visual state update error:', error);
        }
    }
}

// グローバルインスタンス作成（既存コードとの互換性）
const engineUIController = new EngineUIController();

/**
 * 後方互換性のための関数エイリアス
 * 既存のコードから呼び出し可能
 */

/**
 * エンジン説明文更新（後方互換性）
 * 
 * @param {string} engine - エンジン名
 */
function updateEngineDescription(engine) {
    return engineUIController.updateEngineDescription(engine);
}

/**
 * エンジン選択成功表示（後方互換性）
 * 
 * @param {string} engine - エンジン名
 * @param {string} message - メッセージ
 */
function showEngineSelectionSuccess(engine, message) {
    return engineUIController.showSelectionSuccess(engine, message);
}

/**
 * エンジン選択エラー表示（後方互換性）
 * 
 * @param {string} engine - エンジン名
 * @param {string} errorMessage - エラーメッセージ
 */
function showEngineSelectionError(engine, errorMessage) {
    return engineUIController.showSelectionError(engine, errorMessage);
}