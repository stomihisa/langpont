
# 🛡️ 安全性スクリプト使用ガイド

## 📋 作成されたスクリプト一覧

### 1. `check_processes.sh` - 状況確認スクリプト
### 2. `emergency_stop.sh` - 緊急停止スクリプト

---

## 🔍 check_processes.sh - 状況確認スクリプト

### 🎯 目的
現在のPythonプロセスとポート8080の使用状況を安全に確認する

### 📋 機能
- Pythonプロセスの一覧表示
- ポート8080の使用状況確認
- 現在のディレクトリ確認
- VS Code Python拡張の動作状況確認

### 🕐 使用タイミング

#### **必須の使用タイミング**
1. **作業開始前** - 毎回必須
2. **アプリ起動前** - Flask起動前の安全確認
3. **問題発生時** - エラー原因の特定
4. **作業終了後** - プロセス残留確認

#### **推奨の使用タイミング**
- Claude Code実行前後
- ポート8080エラーが発生した時
- 予期しないエラーが発生した時
- 長時間作業した後

### 💻 実行方法
```bash
./check_processes.sh
```

### 📊 出力例と判断基準

#### ✅ **正常な出力例**
```
🔍 Python プロセス確認
shintaro_imac_2  19679  ... Code Helper (Plugin) ... ms-python.vscode-pylance
shintaro_imac_2  19665  ... python-env-tools/bin/pet server

🔍 ポート8080使用状況
ポート8080は空いています

🔍 現在のディレクトリ
/Users/shintaro_imac_2/langpont
```
**判断**: VS Code Python拡張のみ動作、安全に作業可能

#### ⚠️ **注意が必要な出力例**
```
🔍 Python プロセス確認
shintaro_imac_2  12345  ... python app.py
shintaro_imac_2  19679  ... Code Helper (Plugin) ... ms-python.vscode-pylance

🔍 ポート8080使用状況
COMMAND  PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
python  12345 shintaro_imac_2    5u  IPv4  0x1234      0t0  TCP *:http-alt (LISTEN)
```
**判断**: Flaskアプリが動作中、停止が必要

#### 🚨 **緊急対応が必要な出力例**
```
🔍 Python プロセス確認
shintaro_imac_2  12345  ... python app.py
shintaro_imac_2  12346  ... python app.py
shintaro_imac_2  12347  ... python app.py

🔍 ポート8080使用状況
python  12345 shintaro_imac_2    5u  IPv4  0x1234      0t0  TCP *:http-alt (LISTEN)
```
**判断**: 複数のFlaskプロセスが動作、即座に `emergency_stop.sh` 実行

---

## 🚨 emergency_stop.sh - 緊急停止スクリプト

### 🎯 目的
問題のあるPythonプロセスを安全に停止し、ポート8080を解放する

### 📋 機能
- すべての `python app.py` プロセスを停止
- ポート8080を使用するプロセスを強制終了
- 停止後の状況を自動確認
- 安全な初期状態への復旧

### 🕐 使用タイミング

#### **緊急使用タイミング**
1. **ポート8080エラー発生時**
   ```
   Address already in use
   Port 8080 is in use by another program
   ```

2. **複数のPythonプロセス発見時**
   - `check_processes.sh` で複数の `python app.py` 確認

3. **アプリが応答しない時**
   - Ctrl+Cで停止できない
   - VS Codeターミナルが反応しない

4. **Claude Code実行エラー時**
   - 予期しないプロセス残留
   - 起動に失敗が続く場合

#### **予防的使用タイミング**
- 長時間作業後の環境リセット
- 重要な作業開始前のクリーンアップ
- VS Codeを再起動する前

### 💻 実行方法
```bash
./emergency_stop.sh
```

### 📊 出力例と結果確認

#### ✅ **正常な停止例**
```
🚨 緊急停止処理を開始します...
✅ Python app.py プロセスを停止しました
✅ ポート8080を解放しました

🔍 停止後の状況確認：
🔍 Python プロセス確認
shintaro_imac_2  19679  ... Code Helper (Plugin) ... ms-python.vscode-pylance
shintaro_imac_2  19665  ... python-env-tools/bin/pet server

🔍 ポート8080使用状況
ポート8080は空いています

🔍 現在のディレクトリ
/Users/shintaro_imac_2/langpont
```
**結果**: 正常にクリーンアップ完了、作業再開可能

#### ⚠️ **部分的停止例**
```
🚨 緊急停止処理を開始します...
✅ ポート8080を解放しました

🔍 停止後の状況確認：
🔍 Python プロセス確認
shintaro_imac_2  19679  ... Code Helper (Plugin) ... ms-python.vscode-pylance
```
**結果**: 一部停止、再実行または手動対応が必要

---

## 📋 実践的な使用フロー

### 🔄 **日常作業フロー**
```bash
# 1. 作業開始前
./check_processes.sh

# 2. 問題なければ作業開始
# 問題があれば緊急停止
./emergency_stop.sh

# 3. 作業中に問題発生
./emergency_stop.sh
./check_processes.sh

# 4. 作業終了後
./check_processes.sh
```

### 🚨 **トラブル対応フロー**
```bash
# ポート8080エラー発生時
./emergency_stop.sh
sleep 3
./check_processes.sh

# まだ問題がある場合
./emergency_stop.sh
# VS Codeターミナル再起動
./check_processes.sh
```

### 🔧 **Claude Code作業フロー**
```bash
# Claude Code実行前
./check_processes.sh

# Claude Code実行
# (VS CodeでClaude Code起動)

# 問題発生時
./emergency_stop.sh

# Claude Code完了後
./check_processes.sh
```

---

## ⚠️ 重要な注意事項

### 🚫 **禁止事項**
- スクリプトファイルの直接編集（破損の恐れ）
- 複数回連続実行（システム負荷）
- 他のプロジェクトでの使用（パス依存）

### ✅ **推奨事項**
- 定期的な使用習慣化
- 出力内容の理解
- 問題発生時の迅速な対応
- バックアップスクリプトとしての活用

### 🔧 **メンテナンス**
- スクリプトファイルの実行権限確認
- VS Code環境変更時の動作確認
- プロジェクト移動時の再作成

---

## 📞 トラブルシューティング

### **Q: スクリプトが実行できない**
```bash
# 実行権限確認・付与
ls -la *.sh
chmod +x check_processes.sh emergency_stop.sh
```

### **Q: ポート8080が解放されない**
```bash
# 手動での強制停止
sudo lsof -ti:8080 | xargs sudo kill -9
./check_processes.sh
```

### **Q: VS Code Python拡張も停止してしまった**
```bash
# VS Code再起動後
./check_processes.sh
# Python拡張が自動復旧することを確認
```

### **Q: 複数のプロセスが残り続ける**
```bash
# より強力な停止
sudo pkill -f python
sleep 5
./check_processes.sh
```

---

## 🎯 まとめ

これらのスクリプトは、**VS CodeでのClaude Code作業を安全に行うための必須ツール**です。

- **`check_processes.sh`**: 状況把握の目
- **`emergency_stop.sh`**: 問題解決の手

定期的な使用により、8080ポート問題や複数プロセス問題を予防し、安全な開発環境を維持できます。


