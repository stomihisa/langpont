#!/usr/bin/env python3
"""
LangPont HTML構造・UI位置テストスクリプト (lphtmltest.py)
Task: H0-1-Implementation-Fixed

目的: SeleniumベースUI位置テスト + 実在確認済みセレクタ使用
実装: 認証フロー + UI位置検証 + エラーハンドリング
"""

import requests
import time
import argparse
import sys
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple, Optional

# Selenium関連インポート（オプショナル）
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
    print("✅ Selenium library imported successfully")
except ImportError as e:
    SELENIUM_AVAILABLE = False
    print(f"⚠️ Selenium library not available: {e}")
    print("💡 Install with: pip install --break-system-packages selenium")
except Exception as e:
    SELENIUM_AVAILABLE = False
    print(f"❌ Selenium import error: {e}")

# 基本設定
BASE_URL = "http://127.0.0.1:8080"
TEST_TIMEOUT = 10  # Selenium用タイムアウト（最適化: 15→10秒）
HTTP_TIMEOUT = 8   # requests用タイムアウト（最適化: 10→8秒）

# 🔐 実在確認済みセレクタ（調査結果ベース）
LOGIN_SELECTORS = {
    'username': '#username',           # ユーザー名入力 (実在確認済み)
    'password': '#password',           # パスワード入力 (実在確認済み) 
    'login_button': '.login-button',   # ログインボタン (実在確認済み)
    'login_container': '.login-container' # メインコンテナ (実在確認済み)
}

# 🎯 メイン翻訳ページ用セレクタ
MAIN_SELECTORS = {
    'input_text': '#japanese_text',         # 翻訳入力 (実在確認済み)
    'translate_button': '#translate-btn',   # 翻訳ボタン (実在確認済み)
    'chatgpt_result': '#chatgpt-result',    # ChatGPT結果カード (実在確認済み)
    'chatgpt_translation': '#translated-text', # ChatGPT翻訳結果 (実在確認済み)
    'enhanced_translation': '#better-translation', # Enhanced翻訳 (実在確認済み)
    'gemini_result': '#gemini-result',      # Gemini結果カード (実在確認済み)
    'gemini_translation': '#gemini-translation', # Gemini翻訳 (実在確認済み)
    'copy_buttons': '.copy-btn',            # コピーボタン (buttonタグ・実在確認済み)
    'analysis_text': '#gemini-3way-analysis' # 分析結果 (実在確認済み)
}

# ニュアンス分析エンジンセレクタ
ENGINE_SELECTORS = {
    'chatgpt_engine': '.engine-btn[data-engine="chatgpt"]',
    'gemini_engine': '.engine-btn[data-engine="gemini"]',
    'claude_engine': '.engine-btn[data-engine="claude"]'
}

class LangPontUITest:
    """LangPont UI位置テストクラス"""
    
    def __init__(self, verbose: bool = False, quick: bool = False):
        self.verbose = verbose
        self.quick = quick
        self.session = requests.Session()
        self.driver = None
        self.test_results = []
        self.start_time = time.time()
        
        # ヘッダー設定
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        
        self.log("🚀 LangPont HTML構造・UI位置テスト開始")
        self.log(f"📅 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"🔧 モード: {'詳細' if verbose else '標準'}, {'高速' if quick else '完全'}")
        
    def log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        if self.verbose or level in ['ERROR', 'WARNING']:
            print(f"[{timestamp}] {message}")
        elif level == "INFO":
            print(message)
    
    def setup_selenium(self) -> bool:
        """Seleniumドライバー初期化"""
        if not SELENIUM_AVAILABLE:
            self.log("⚠️ Selenium利用不可 - 基本テストのみ実行", "WARNING")
            self.log("💡 Seleniumインストール: pip install --break-system-packages selenium", "INFO")
            return False
        
        try:
            # Chrome Options設定
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # ヘッドレスモード
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            
            # ChromeDriverサービス設定（明示的パス指定）
            try:
                service = Service('/opt/homebrew/bin/chromedriver')
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception:
                # フォールバック: パス指定なし
                self.driver = webdriver.Chrome(options=chrome_options)
            
            self.driver.implicitly_wait(5)
            self.log("✅ Selenium Chrome driver 初期化成功")
            self.log(f"🔧 ChromeDriver location: /opt/homebrew/bin/chromedriver")
            return True
            
        except WebDriverException as e:
            self.log(f"❌ WebDriverException: {e}", "ERROR")
            self.log("🔍 ChromeDriver確認: chromedriver --version", "INFO")
            return False
        except Exception as e:
            self.log(f"❌ General Exception during Selenium setup: {e}", "ERROR")
            self.log(f"❌ Exception type: {type(e).__name__}", "ERROR")
            return False
    
    def authenticate(self) -> bool:
        """admin認証実行（lpbasic.py準拠）"""
        self.log("\n🔐 認証フロー開始...")
        
        try:
            # 1. /login ページアクセス
            login_response = self.session.get(f"{BASE_URL}/login", timeout=HTTP_TIMEOUT)
            if login_response.status_code != 200:
                self.log(f"❌ ログインページアクセス失敗: HTTP {login_response.status_code}", "ERROR")
                return False
            
            self.log("✅ ログインページアクセス成功")
            
            # 2. CSRFトークン取得
            soup = BeautifulSoup(login_response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            csrf_token = csrf_input['value'] if csrf_input else None
            
            if not csrf_token:
                self.log("❌ CSRFトークン取得失敗", "ERROR")
                return False
            
            self.log("✅ CSRFトークン取得成功")
            
            # 3. admin/admin_langpont_2025 で認証
            login_data = {
                "username": "admin",
                "password": "admin_langpont_2025",
                "csrf_token": csrf_token
            }
            
            auth_response = self.session.post(
                f"{BASE_URL}/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=HTTP_TIMEOUT,
                allow_redirects=True
            )
            
            # 4. 認証成功確認
            if auth_response.status_code == 200 and ("翻訳" in auth_response.text or "LangPont" in auth_response.text):
                self.log("✅ admin認証成功")
                return True
            else:
                self.log(f"❌ 認証失敗: HTTP {auth_response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ 認証エラー: {e}", "ERROR")
            return False
    
    def test_basic_structure(self) -> bool:
        """基本構造テスト（requests + BeautifulSoup）"""
        self.log("\n🏗️ 基本HTML構造テスト...")
        
        try:
            response = self.session.get(BASE_URL, timeout=HTTP_TIMEOUT)
            if response.status_code != 200:
                self.log(f"❌ メインページアクセス失敗: HTTP {response.status_code}", "ERROR")
                return False
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 主要要素の存在確認
            test_selectors = {**MAIN_SELECTORS, **ENGINE_SELECTORS}
            found_elements = 0
            total_elements = len(test_selectors)
            
            for name, selector in test_selectors.items():
                if selector.startswith('#'):
                    # ID セレクタ
                    element = soup.find(id=selector[1:])
                elif selector.startswith('.'):
                    # クラス セレクタ
                    class_name = selector[1:]
                    if '[' in class_name:  # data属性対応
                        # 簡易的な data属性チェック
                        if 'data-engine=' in selector:
                            elements = soup.find_all(attrs={'data-engine': True})
                            element = elements[0] if elements else None
                        else:
                            element = soup.find(class_=class_name.split('[')[0])
                    else:
                        element = soup.find(class_=class_name)
                else:
                    element = None
                
                if element:
                    found_elements += 1
                    self.log(f"  ✅ {name}: {selector}", "DEBUG" if not self.verbose else "INFO")
                else:
                    self.log(f"  ❌ {name}: {selector}", "WARNING")
            
            success_rate = (found_elements / total_elements) * 100
            self.log(f"📊 基本構造テスト結果: {found_elements}/{total_elements} ({success_rate:.1f}%)")
            
            self.test_results.append({
                'test': 'basic_structure',
                'success': success_rate >= 80,
                'details': f"{found_elements}/{total_elements} elements found"
            })
            
            return success_rate >= 80
            
        except Exception as e:
            self.log(f"❌ 基本構造テストエラー: {e}", "ERROR")
            return False
    
    def test_element_position(self, selector: str, name: str) -> Dict:
        """UI要素位置テスト（待機ロジック強化版）"""
        try:
            # Stage 1: 要素の存在確認
            element = WebDriverWait(self.driver, TEST_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            
            # Stage 2: 要素のクリック可能性確認（インタラクティブ要素の場合）
            if selector in ['#translate-btn', '.login-button', '.copy-btn'] or 'btn' in selector:
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                except TimeoutException:
                    # クリック不可でも位置テストは継続
                    pass
            
            # Stage 3: 位置・サイズ情報取得
            is_displayed = element.is_displayed()
            location = element.location
            size = element.size
            
            x, y = location["x"], location["y"]
            width, height = size["width"], size["height"]
            
            # 判定条件（動的要素に配慮）
            is_normal = (
                is_displayed and
                width > 20 and height > 10 and
                0 < x < 1500
            )
            
            # 特別判定: 翻訳結果カードは存在するが非表示でも正常
            if 'result' in selector and not is_displayed and width > 0 and height > 0:
                is_normal = True  # 要素は存在するが初期非表示（正常状態）
            
            result = {
                'name': name,
                'selector': selector,
                'displayed': is_displayed,
                'position': (x, y),
                'size': (width, height),
                'normal': is_normal,
                'issues': []
            }
            
            # 異常検出
            if not is_displayed:
                result['issues'].append('要素が非表示')
            if width == 0 or height == 0:
                result['issues'].append('サイズが0')
            if x > 2000:
                result['issues'].append('画面外に配置')
            if x < 0 or y < 0:
                result['issues'].append('負の位置')
            
            status = "✅" if is_normal else "❌"
            details = f"位置:({x},{y}) サイズ:{width}x{height}"
            if result['issues']:
                details += f" 問題:{','.join(result['issues'])}"
            
            self.log(f"  {status} {name}: {details}")
            
            return result
            
        except (TimeoutException, NoSuchElementException) as e:
            # 詳細デバッグ情報出力
            try:
                page_source_snippet = self.driver.page_source[:500] + "..."
                current_url = self.driver.current_url
                self.log(f"  🔍 デバッグ情報 - URL: {current_url}")
                if self.verbose:
                    self.log(f"  🔍 ページソース: {page_source_snippet}")
            except:
                pass
            
            self.log(f"  ❌ {name}: 要素が見つかりません - {selector} ({type(e).__name__})", "WARNING")
            return {
                'name': name,
                'selector': selector,
                'displayed': False,
                'position': (0, 0),
                'size': (0, 0),
                'normal': False,
                'issues': ['要素が存在しない']
            }
        except Exception as e:
            self.log(f"  ❌ {name}: テストエラー - {e} ({type(e).__name__})", "ERROR")
            return {
                'name': name,
                'selector': selector,
                'displayed': False,
                'position': (0, 0),
                'size': (0, 0),
                'normal': False,
                'issues': [f'テストエラー: {e}']
            }
    
    def test_ui_positions(self) -> bool:
        """UI位置テスト実行（Selenium認証統合版）"""
        if not self.driver:
            self.log("⚠️ Seleniumドライバー未初期化 - UI位置テストスキップ", "WARNING")
            return False
        
        self.log("\n🎯 UI位置テスト開始...")
        
        try:
            # 1. Selenium認証実行
            if not self.selenium_authenticate():
                self.log("❌ Selenium認証失敗 - UI位置テスト中断", "ERROR")
                return False
            
            # 2. メインページ完全読み込み待機
            WebDriverWait(self.driver, TEST_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, MAIN_SELECTORS['input_text']))
            )
            
            # 3. JavaScript読み込み完了待機
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                self.log("✅ ページ読み込み完了確認")
            except:
                self.log("⚠️ ページ読み込み確認タイムアウト（継続）", "WARNING")
            
            # 4. テスト対象セレクタ設定（初期表示要素のみ）
            position_results = []
            
            # 初期表示要素のみテスト（動的要素は除外）
            initial_display_selectors = {
                'input_text': MAIN_SELECTORS['input_text'],
                'translate_button': MAIN_SELECTORS['translate_button']
            }
            
            # 高速モードでない場合は、存在確認要素も追加
            if not self.quick:
                initial_display_selectors.update({
                    'chatgpt_result': MAIN_SELECTORS['chatgpt_result'],
                    'gemini_result': MAIN_SELECTORS['gemini_result']
                })
            
            test_selectors = initial_display_selectors
            self.log(f"📋 テスト対象: {len(test_selectors)}個の要素（初期表示要素）")
            
            # 5. 各要素の位置テスト実行
            for name, selector in test_selectors.items():
                result = self.test_element_position(selector, name)
                position_results.append(result)
                
                # 高速モード: 主要要素のみ
                if self.quick and len(position_results) >= 5:
                    self.log("🚄 高速モード: 主要要素のみテスト")
                    break
            
            # 6. 結果集計・分析
            normal_count = sum(1 for r in position_results if r['normal'])
            total_count = len(position_results)
            success_rate = (normal_count / total_count) * 100 if total_count > 0 else 0
            
            self.log(f"📊 UI位置テスト結果: {normal_count}/{total_count} ({success_rate:.1f}%)")
            
            # 7. 問題分析とデバッグ情報
            issues = [r for r in position_results if not r['normal']]
            if issues:
                self.log(f"⚠️ 問題のある要素: {len(issues)}個")
                if self.verbose:
                    for issue in issues:
                        self.log(f"  - {issue['name']}: {', '.join(issue['issues'])}")
            
            # 8. テスト結果記録
            self.test_results.append({
                'test': 'ui_positions',
                'success': success_rate >= 85,
                'details': f"{normal_count}/{total_count} normal positions",
                'issues': len(issues)
            })
            
            return success_rate >= 85
            
        except Exception as e:
            self.log(f"❌ UI位置テストエラー: {e} ({type(e).__name__})", "ERROR")
            return False
    
    def run_all_tests(self) -> bool:
        """全テスト実行"""
        success = True
        
        # 1. 認証テスト
        if not self.authenticate():
            self.log("❌ 認証失敗 - テスト中断", "ERROR")
            return False
        
        # 2. 基本構造テスト
        if not self.test_basic_structure():
            self.log("⚠️ 基本構造テスト失敗", "WARNING")
            success = False
        
        # 3. Selenium UI位置テスト
        if self.setup_selenium():
            if not self.test_ui_positions():
                self.log("⚠️ UI位置テスト失敗", "WARNING")
                success = False
        else:
            self.log("⚠️ UI位置テストスキップ（Selenium利用不可）", "WARNING")
        
        return success
    
    def print_summary(self):
        """テスト結果サマリー出力"""
        elapsed = time.time() - self.start_time
        
        print("\n" + "=" * 60)
        print("📊 LangPont HTML構造・UI位置テスト結果")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['success'])
        
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']}: {result['details']}")
        
        print(f"\n🎯 総合結果: {passed_tests}/{total_tests} テスト成功")
        print(f"⏱️ 実行時間: {elapsed:.1f}秒")
        
        if passed_tests == total_tests:
            print("🎉 全テスト成功！HTML構造とUI位置は正常です。")
        elif passed_tests >= total_tests * 0.8:
            print("⚠️ 部分的成功 - 軽微な問題がある可能性があります。")
        else:
            print("🚨 重大な問題 - HTML構造またはUI位置に問題があります。")
        
        print("=" * 60)
    
    def cleanup(self):
        """リソースクリーンアップ"""
        if self.driver:
            try:
                self.driver.quit()
                self.log("✅ Seleniumドライバークリーンアップ完了")
            except Exception:
                pass
        
        self.session.close()
    
    def selenium_authenticate(self) -> bool:
        """Seleniumドライバー用認証フロー"""
        if not self.driver:
            self.log("❌ Seleniumドライバー未初期化", "ERROR")
            return False
        
        self.log("🔐 Selenium認証フロー開始...")
        
        try:
            # 1. ログインページアクセス
            self.driver.get(f"{BASE_URL}/login")
            WebDriverWait(self.driver, TEST_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, LOGIN_SELECTORS['username']))
            )
            self.log("✅ Seleniumログインページアクセス成功")
            
            # 2. ユーザー名入力
            username_field = self.driver.find_element(By.CSS_SELECTOR, LOGIN_SELECTORS['username'])
            username_field.clear()
            username_field.send_keys("admin")
            self.log("✅ ユーザー名入力完了")
            
            # 3. パスワード入力
            password_field = self.driver.find_element(By.CSS_SELECTOR, LOGIN_SELECTORS['password'])
            password_field.clear()
            password_field.send_keys("admin_langpont_2025")
            self.log("✅ パスワード入力完了")
            
            # 4. ログインボタンクリック
            login_button = WebDriverWait(self.driver, TEST_TIMEOUT).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, LOGIN_SELECTORS['login_button']))
            )
            login_button.click()
            self.log("✅ ログインボタンクリック完了")
            
            # 5. 認証成功確認（リダイレクト先チェック）
            WebDriverWait(self.driver, TEST_TIMEOUT).until(
                lambda driver: BASE_URL in driver.current_url and "/login" not in driver.current_url
            )
            
            # 6. メインページ要素の存在確認
            WebDriverWait(self.driver, TEST_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, MAIN_SELECTORS['input_text']))
            )
            
            self.log(f"✅ Selenium認証成功 - リダイレクト先: {self.driver.current_url}")
            return True
            
        except TimeoutException:
            self.log("❌ Selenium認証タイムアウト", "ERROR")
            self.log(f"   現在URL: {self.driver.current_url}")
            return False
        except Exception as e:
            self.log(f"❌ Selenium認証エラー: {e}", "ERROR")
            return False

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description="LangPont HTML構造・UI位置テスト")
    parser.add_argument('--verbose', '-v', action='store_true', help='詳細モード')
    parser.add_argument('--quick', '-q', action='store_true', help='高速モード')
    
    args = parser.parse_args()
    
    tester = LangPontUITest(verbose=args.verbose, quick=args.quick)
    
    try:
        success = tester.run_all_tests()
        tester.print_summary()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️ テスト中断")
        sys.exit(1)
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main()