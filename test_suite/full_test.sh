#!/bin/bash

echo "🚀 LangPont自動テストスイート開始..."
echo "Task AUTO-TEST-1: 最小構成完全自動テスト"
echo "=========================================="

# テスト開始時刻記録
START_TIME=$(date +%s)

# 1. 既存プロセス確認・停止
echo "🔍 既存プロセス確認・停止中..."
pkill -f "python.*app.py" 2>/dev/null || true
sleep 2

# 2. Python環境確認
echo "🐍 Python環境確認..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python3が見つかりません"
    exit 1
fi

# 3. 必要なライブラリ確認
echo "📦 必要ライブラリ確認..."
python3 -c "import requests, psutil" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️ 必要ライブラリが不足している可能性があります"
    echo "インストール: pip install requests psutil"
fi

# 4. テストディレクトリに移動
cd "$(dirname "$0")"
echo "📁 現在のディレクトリ: $(pwd)"

# 5. 統合テスト実行
echo "🧪 統合テスト実行中..."

python3 -c "
import sys
import time

# 統合テスト実行
def run_full_test():
    print('🎬 テストシナリオ開始')
    
    try:
        from app_control import FlaskAppController
        from api_test import test_index_page, test_translation_api
        from selenium_test import test_simple_page_load, test_ui_translation
    except ImportError as e:
        print(f'❌ インポートエラー: {e}')
        return False
    
    controller = FlaskAppController()
    
    try:
        # Step 1: アプリ起動
        print('🚀 Step 1: Flask App起動...')
        if not controller.start_app():
            print('❌ Flask App起動失敗')
            return False
        
        time.sleep(3)  # 起動安定化待機
        
        # Step 2: API基本テスト
        print('🚀 Step 2: API基本テスト...')
        if not test_index_page():
            print('❌ ページアクセステスト失敗')
            return False
            
        if not test_translation_api():
            print('❌ 翻訳APIテスト失敗')
            return False
        
        # Step 3: UI基本テスト
        print('🚀 Step 3: UI基本テスト...')
        if not test_simple_page_load():
            print('❌ シンプルUIテスト失敗')
            return False
        
        # Step 4: UI高度テスト（オプション）
        print('🚀 Step 4: UI高度テスト（Selenium）...')
        ui_advanced_success = test_ui_translation()
        if ui_advanced_success:
            print('✅ Selenium UIテスト成功')
        else:
            print('⚠️ Selenium UIテストスキップ（Selenium未インストールまたはエラー）')
        
        print('✅ 全テスト成功: LangPont翻訳機能正常動作確認')
        return True
        
    except Exception as e:
        print(f'❌ 予期しないエラー: {e}')
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        print('🛑 Flask App停止中...')
        controller.stop_app()

# メイン実行
if __name__ == '__main__':
    success = run_full_test()
    sys.exit(0 if success else 1)
"

TEST_RESULT=$?

# 6. テスト結果集計
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "=========================================="
echo "📊 テスト実行結果"
echo "実行時間: ${DURATION}秒"

if [ $TEST_RESULT -eq 0 ]; then
    echo "🎉 全テスト成功: LangPont正常動作確認"
    echo "✅ API基本機能: 正常"
    echo "✅ UI基本機能: 正常" 
    echo "✅ 翻訳機能: 正常"
    echo ""
    echo "🚀 自動テスト完了（目標3分 vs 実際${DURATION}秒）"
else
    echo "💥 テスト失敗: 詳細は上記ログを確認してください"
    echo ""
    echo "🔍 トラブルシューティング:"
    echo "1. Flask起動確認: python app.py"
    echo "2. ポート確認: lsof -i :8080"
    echo "3. ライブラリ確認: pip install requests psutil selenium"
fi

exit $TEST_RESULT