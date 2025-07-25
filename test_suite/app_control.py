"""
LangPont アプリ制御システム
Task AUTO-TEST-1: Flask自動起動・停止制御
"""

import subprocess
import time
import requests
import signal
import os
import psutil

class FlaskAppController:
    def __init__(self):
        self.process = None
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    def kill_existing_processes(self):
        """既存のFlaskプロセスを停止"""
        print("🔍 既存Flaskプロセス確認中...")
        killed = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline'] and any('python' in arg and 'app.py' in ' '.join(proc.info['cmdline']) for arg in proc.info['cmdline']):
                    print(f"🗑️ 既存プロセス停止: PID {proc.info['pid']}")
                    proc.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        if killed > 0:
            print(f"✅ {killed}個の既存プロセスを停止")
            time.sleep(2)  # プロセス停止待機
        else:
            print("✅ 既存プロセスなし")
        
    def start_app(self):
        """Flaskアプリ起動"""
        print("🚀 Flask App起動中...")
        
        # 既存プロセス停止
        self.kill_existing_processes()
        
        # 環境変数設定
        env = os.environ.copy()
        env['FLASK_ENV'] = 'development'
        env['FLASK_DEBUG'] = '0'  # デバッグ無効（シングルプロセス）
        
        # Flaskアプリ起動
        self.process = subprocess.Popen(
            ["python", "app.py"],
            cwd=self.base_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        
        # 起動確認（最大30秒待機）
        print("⏳ Flask起動確認中（最大30秒）...")
        for i in range(30):
            try:
                response = requests.get("http://localhost:8080", timeout=2)
                if response.status_code == 200:
                    print(f"✅ Flask App起動成功 (PID: {self.process.pid})")
                    return True
            except requests.exceptions.RequestException:
                time.sleep(1)
                print(f"⏳ 起動待機中... ({i+1}/30)")
                
        print("❌ Flask App起動失敗（30秒タイムアウト）")
        
        # エラー出力確認
        if self.process:
            stdout, stderr = self.process.communicate(timeout=5)
            if stderr:
                print(f"🚨 エラー出力: {stderr.decode()[:200]}...")
        
        return False
    
    def stop_app(self):
        """Flaskアプリ停止"""
        print("🛑 Flask App停止中...")
        
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                print("✅ Flask App正常停止")
            except subprocess.TimeoutExpired:
                self.process.kill()
                print("✅ Flask App強制停止")
        
        # 残存プロセス確認・停止
        self.kill_existing_processes()
        
    def is_running(self):
        """Flask稼働状況確認"""
        try:
            response = requests.get("http://localhost:8080", timeout=2)
            return response.status_code == 200
        except:
            return False

if __name__ == "__main__":
    print("🧪 Flask制御システム単体テスト")
    
    controller = FlaskAppController()
    
    try:
        # 起動テスト
        if controller.start_app():
            print("✅ 起動テスト成功")
            
            # 稼働確認
            if controller.is_running():
                print("✅ 稼働確認成功")
            else:
                print("❌ 稼働確認失敗")
        else:
            print("❌ 起動テスト失敗")
            
    finally:
        controller.stop_app()
        print("🎉 Flask制御システムテスト完了")