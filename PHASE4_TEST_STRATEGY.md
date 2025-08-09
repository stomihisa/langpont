# Task #9-4 AP-1 Phase 4 - テスト戦略・自動化計画

## 📊 現状のテスト環境評価

### 既存テストスイートの構成
```
test_suite/
├── full_test.sh        ✅ 統合テストスクリプト（90倍高速化済み）
├── api_test.py         ✅ API自動テスト（基本翻訳API）
├── selenium_test.py    ✅ UI自動テスト（ブラウザ操作）
├── app_control.py      ✅ Flask制御自動化
└── lpbasic.py, lptest.py ✅ 基本機能テスト
```

### 現状のテストカバレッジ分析

#### ✅ カバーされている領域
1. **基本翻訳機能**: ChatGPT翻訳API `/translate_chatgpt`
2. **UI基本動作**: ページロード、基本的なUI操作  
3. **フレームワーク**: Flask起動・停止の自動制御
4. **統合テスト**: エンドツーエンドの基本フロー

#### ❌ カバーされていない領域
1. **高度翻訳機能**: `f_better_translation`, `f_reverse_translation`
2. **Blueprint分離後のエンドポイント**: 新規エンドポイントの未テスト
3. **Service層の単体テスト**: TranslationService メソッドの個別テスト
4. **エラーハンドリング**: 異常系の網羅的なテスト
5. **セキュリティテスト**: CSRF、レート制限等の保護機能

---

## 🧪 Phase 4 対応テスト計画

### 1. 単体テスト (Unit Tests)

#### TranslationService テスト
```python
# 新規作成: test_suite/unit/test_translation_service.py
import pytest
from services.translation_service import TranslationService

class TestTranslationService:
    
    def test_reverse_translation_success(self):
        """逆翻訳正常系テスト"""
        # Service初期化
        service = TranslationService(mock_client, mock_logger, mock_labels, mock_usage_checker, mock_state_manager)
        
        # テスト実行
        result = service.reverse_translation("Hello", "en", "ja", "jp")
        
        # 検証
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_reverse_translation_empty_input(self):
        """逆翻訳異常系テスト（空入力）"""
        service = TranslationService(...)
        
        with pytest.raises(ValueError):
            service.reverse_translation("", "en", "ja", "jp")
    
    def test_better_translation_success(self):
        """改善翻訳正常系テスト"""
        service = TranslationService(...)
        
        result = service.better_translation("This is good", "en", "en", "jp")
        
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_better_translation_invalid_language_pair(self):
        """改善翻訳異常系テスト（無効言語ペア）"""
        service = TranslationService(...)
        
        with pytest.raises(ValueError):
            service.better_translation("test", "invalid", "invalid", "jp")
```

#### 関数レベル単体テスト
```python
# 新規作成: test_suite/unit/test_translation_functions.py
import pytest
from unittest.mock import patch, MagicMock

def test_f_reverse_translation_valid_input():
    """f_reverse_translation関数の正常系テスト"""
    with patch('app.safe_openai_request') as mock_api:
        mock_api.return_value = "こんにちは"
        
        from app import f_reverse_translation
        result = f_reverse_translation("Hello", "en", "ja", "jp")
        
        assert result == "こんにちは"
        mock_api.assert_called_once()

def test_f_better_translation_valid_input():
    """f_better_translation関数の正常系テスト"""
    with patch('app.safe_openai_request') as mock_api:
        mock_api.return_value = "This is an excellent translation"
        
        from app import f_better_translation
        result = f_better_translation("This is good translation", "en", "en", "jp")
        
        assert "excellent" in result
        mock_api.assert_called_once()
```

### 2. APIテスト (Integration Tests)

#### 新規エンドポイントテスト
```python
# 拡張: test_suite/api_test.py に追加
def test_better_translation_endpoint():
    """改善翻訳エンドポイントテスト"""
    print("🔍 API Test: /better_translation エンドポイント確認...")
    
    payload = {
        "text": "This is good translation",
        "source_lang": "en",
        "target_lang": "en"
    }
    
    # CSRF トークン取得
    csrf_token = get_csrf_token()
    
    response = requests.post(
        "http://localhost:8080/better_translation",
        json=payload,
        headers={"X-CSRFToken": csrf_token},
        timeout=30
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert "improved_text" in result
    print(f"✅ 改善翻訳成功: {result['improved_text'][:50]}...")

def test_reverse_chatgpt_translation_endpoint():
    """逆翻訳エンドポイントテスト"""
    print("🔍 API Test: /reverse_chatgpt_translation エンドポイント確認...")
    
    payload = {
        "translated_text": "Bonjour le monde",
        "language_pair": "ja-fr"
    }
    
    csrf_token = get_csrf_token()
    
    response = requests.post(
        "http://localhost:8080/reverse_chatgpt_translation",
        json=payload,
        headers={"X-CSRFToken": csrf_token},
        timeout=30
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert "reversed_text" in result
    print(f"✅ 逆翻訳成功: {result['reversed_text'][:50]}...")

def test_blueprint_endpoints_availability():
    """Blueprint化後のエンドポイント可用性確認"""
    endpoints_to_test = [
        "/better_translation",
        "/reverse_chatgpt_translation", 
        "/reverse_better_translation"  # 既存（移動後）
    ]
    
    for endpoint in endpoints_to_test:
        response = requests.options(f"http://localhost:8080{endpoint}")
        assert response.status_code in [200, 405]  # OPTIONSまたはMethodNotAllowed
        print(f"✅ エンドポイント利用可能: {endpoint}")
```

### 3. エラーハンドリングテスト

#### セキュリティテスト
```python
# 新規作成: test_suite/security_test.py
def test_csrf_protection():
    """CSRF保護機能テスト"""
    payload = {"text": "test"}
    
    # CSRFトークンなしでのアクセス
    response = requests.post("http://localhost:8080/better_translation", json=payload)
    assert response.status_code == 403
    print("✅ CSRF保護が正常に機能")

def test_rate_limiting():
    """レート制限テスト"""
    payload = {"text": "test"}
    csrf_token = get_csrf_token()
    
    # 連続リクエストでレート制限確認
    for i in range(20):  # 制限値を超える回数
        response = requests.post(
            "http://localhost:8080/better_translation",
            json=payload,
            headers={"X-CSRFToken": csrf_token}
        )
        if response.status_code == 429:  # Too Many Requests
            print("✅ レート制限が正常に機能")
            break
    else:
        print("⚠️ レート制限が設定されていない可能性があります")

def test_input_validation():
    """入力値検証テスト"""
    test_cases = [
        {"text": "", "expected": 400},           # 空文字
        {"text": "x" * 10000, "expected": 400}, # 長すぎる文字
        {"source_lang": "invalid", "expected": 400},  # 無効言語
    ]
    
    csrf_token = get_csrf_token()
    
    for case in test_cases:
        response = requests.post(
            "http://localhost:8080/better_translation",
            json=case,
            headers={"X-CSRFToken": csrf_token}
        )
        assert response.status_code == case["expected"]
        print(f"✅ 入力値検証: {case}")
```

### 4. UIテスト (End-to-End Tests)

#### Seleniumテスト拡張
```python
# 拡張: test_suite/selenium_test.py に追加
def test_better_translation_ui_flow():
    """改善翻訳UI操作テスト"""
    driver = webdriver.Chrome()
    
    try:
        # ページアクセス
        driver.get("http://localhost:8080")
        
        # 翻訳実行
        text_area = driver.find_element(By.ID, "japanese_text")
        text_area.send_keys("こんにちは")
        
        translate_button = driver.find_element(By.ID, "translate_button")
        translate_button.click()
        
        # 改善翻訳ボタンをクリック
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "better_translation_button"))
        )
        better_button = driver.find_element(By.ID, "better_translation_button")
        better_button.click()
        
        # 結果確認
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "better_translation_result"))
        )
        result_element = driver.find_element(By.ID, "better_translation_result")
        assert len(result_element.text) > 0
        print("✅ UI改善翻訳フロー正常")
        
    finally:
        driver.quit()
```

---

## 🚀 テスト自動化戦略

### 1. テスト実行スクリプト拡張

#### full_test.sh 拡張版
```bash
# 既存のfull_test.sh に追加
echo "🧪 Phase 4 高度翻訳機能テスト開始..."

# 単体テスト実行
echo "🔬 単体テスト実行中..."
python3 -m pytest test_suite/unit/ -v

# 新規APIテスト実行
echo "🌐 新規APIテスト実行中..."
python3 -c "
from api_test import test_better_translation_endpoint, test_reverse_chatgpt_translation_endpoint
test_better_translation_endpoint()
test_reverse_chatgpt_translation_endpoint()
"

# セキュリティテスト実行
echo "🔒 セキュリティテスト実行中..."
python3 security_test.py

echo "✅ Phase 4テストスイート完了"
```

### 2. CI/CD統合対応

#### GitHub Actions ワークフロー
```yaml
# 新規作成: .github/workflows/phase4_test.yml
name: Phase 4 Translation Tests

on:
  push:
    branches: [ feature/phase4-blueprint ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest requests selenium
    
    - name: Run Phase 4 Tests
      run: |
        chmod +x test_suite/full_test.sh
        ./test_suite/full_test.sh
    
    - name: Upload test results
      uses: actions/upload-artifact@v2
      with:
        name: test-results
        path: test-results/
```

### 3. テストデータ管理

#### テスト用データセット
```python
# 新規作成: test_suite/data/test_data.py
TRANSLATION_TEST_CASES = [
    {
        "input": "こんにちは、世界",
        "source_lang": "ja",
        "target_lang": "en",
        "expected_contains": ["hello", "world"]
    },
    {
        "input": "Bonjour le monde", 
        "source_lang": "fr",
        "target_lang": "ja",
        "expected_contains": ["こんにちは", "世界"]
    },
    # ... 多言語テストケース
]

REVERSE_TRANSLATION_TEST_CASES = [
    {
        "input": "Hello world",
        "target_lang": "en",
        "source_lang": "ja", 
        "expected_contains": ["こんにちは"]
    },
    # ... 逆翻訳テストケース
]

BETTER_TRANSLATION_TEST_CASES = [
    {
        "input": "This translation is good",
        "source_lang": "en",
        "target_lang": "en",
        "min_length": 10
    },
    # ... 改善翻訳テストケース
]
```

---

## 📈 テストカバレッジ目標

### カバレッジ目標値
- **Unit Tests**: 90%以上
- **Integration Tests**: 85%以上  
- **E2E Tests**: 主要フロー100%
- **Error Handling**: 80%以上

### 測定ツール
```bash
# カバレッジ測定
pip install coverage
coverage run -m pytest test_suite/
coverage report -m
coverage html
```

### 継続的品質改善
1. **定期実行**: 毎日午前2:00にフルテスト実行
2. **レポート自動生成**: テスト結果の自動レポート作成
3. **パフォーマンス監視**: APIレスポンス時間の監視
4. **失敗通知**: テスト失敗時のSlack/Email通知

---

## ⚠️ 実装時の注意事項

### テスト環境の整備
1. **独立環境**: 本番環境から完全分離されたテスト環境
2. **データ分離**: テストデータの本番データへの影響防止  
3. **リソース管理**: テスト実行時のメモリ・CPU使用量管理

### テストの保守性
1. **モジュール化**: 再利用可能なテスト関数の作成
2. **設定管理**: テスト設定の外部化（config.json等）
3. **ドキュメント化**: テストケースの詳細ドキュメント作成

---

**策定日**: 2025年8月9日  
**Task**: Task #9-4 AP-1 Phase 4  
**目的**: Better Translation・Reverse Translation機能の包括的テスト戦略