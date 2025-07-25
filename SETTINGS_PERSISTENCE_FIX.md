# 🔧 LangPont 設定永続化問題の修正

## 問題の概要
従来の認証システムを使用しているユーザーの設定（言語設定等）が、ログアウト後に元に戻ってしまう問題を修正しました。

## 実装した修正

### 1. 設定保存の永続化 (auth_routes.py)

#### 修正内容：
- `update_profile()` 関数で、従来ユーザーの設定をセッションだけでなく、JSONファイルにも保存
- `session.permanent = True` でセッションの永続化も強化

#### 修正箇所：
```python
# 🆕 従来ユーザー用の設定永続化ファイルに保存
username = session.get('username', 'guest')
legacy_settings_file = f"legacy_user_settings_{username}.json"
try:
    import json
    legacy_settings = {
        'username': username,
        'preferred_lang': preferred_lang,
        'last_updated': datetime.now().isoformat()
    }
    with open(legacy_settings_file, 'w', encoding='utf-8') as f:
        json.dump(legacy_settings, f, ensure_ascii=False, indent=2)
    logger.info(f"従来ユーザー設定をファイルに保存: {legacy_settings_file}")
except Exception as e:
    logger.warning(f"従来ユーザー設定ファイル保存エラー: {str(e)}")
```

### 2. ログイン時の設定復元 (auth_routes.py)

#### 修正内容：
- `login()` 関数で、ログイン成功時に保存済み設定を復元
- JSONファイルから設定を読み込んでセッションに設定

#### 修正箇所：
```python
# 🆕 従来ユーザーの保存済み設定を復元
username = user_info['username']
legacy_settings_file = f"legacy_user_settings_{username}.json"
try:
    import json
    if os.path.exists(legacy_settings_file):
        with open(legacy_settings_file, 'r', encoding='utf-8') as f:
            legacy_settings = json.load(f)
            preferred_lang = legacy_settings.get('preferred_lang', 'jp')
            session['preferred_lang'] = preferred_lang
            session['lang'] = preferred_lang
            logger.info(f"従来ユーザー設定復元: {username} -> 言語: {preferred_lang}")
except Exception as e:
    logger.warning(f"従来ユーザー設定復元エラー: {str(e)}")
```

### 3. プロフィール表示時の設定読み込み (auth_routes.py)

#### 修正内容：
- `profile()` 関数で、プロフィール表示時にもJSONファイルから設定を確認・同期
- セッションとファイルの設定が異なる場合は、ファイルの設定を優先

#### 修正箇所：
```python
# 🆕 従来ユーザー設定ファイルから言語設定を復元
legacy_settings_file = f"legacy_user_settings_{username}.json"
try:
    import json
    if os.path.exists(legacy_settings_file):
        with open(legacy_settings_file, 'r', encoding='utf-8') as f:
            legacy_settings = json.load(f)
            file_lang = legacy_settings.get('preferred_lang', saved_lang)
            if file_lang != saved_lang:
                # ファイルの設定が異なる場合は更新
                saved_lang = file_lang
                session['preferred_lang'] = file_lang
                session['lang'] = file_lang
                logger.info(f"従来ユーザー設定をファイルから復元: {username} -> {file_lang}")
except Exception as e:
    logger.warning(f"従来ユーザー設定ファイル読み込みエラー: {str(e)}")
```

### 4. メインアプリでの設定復元 (app.py)

#### 修正内容：
- `restore_legacy_user_settings()` ヘルパー関数を追加
- `index()` ルートで毎回設定をチェック・復元

#### 修正箇所：
```python
# 🆕 従来ユーザー設定復元ヘルパー関数
def restore_legacy_user_settings() -> None:
    """従来ユーザーの保存済み設定を復元"""
    try:
        if session.get('logged_in') and not session.get('authenticated'):
            # 従来システムユーザーの場合のみ
            username = session.get('username')
            if username:
                settings_file = f"legacy_user_settings_{username}.json"
                if os.path.exists(settings_file):
                    import json
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        legacy_settings = json.load(f)
                        preferred_lang = legacy_settings.get('preferred_lang')
                        
                        # セッションの言語設定と異なる場合は更新
                        current_lang = session.get('lang', 'jp')
                        if preferred_lang and preferred_lang != current_lang:
                            session['lang'] = preferred_lang
                            session['preferred_lang'] = preferred_lang
                            logger.info(f"従来ユーザー設定復元: {username} -> {preferred_lang}")
    except Exception as e:
        logger.warning(f"従来ユーザー設定復元エラー: {str(e)}")

@app.route("/", methods=["GET", "POST"])
@csrf_protect
@require_rate_limit
def index():
    # 🆕 従来ユーザーの保存済み設定を復元
    restore_legacy_user_settings()
    
    lang = session.get("lang", "jp")
    # ... 以下続く
```

## ファイル形式

### 設定ファイル名
`legacy_user_settings_{username}.json`

例：
- `legacy_user_settings_admin.json`
- `legacy_user_settings_developer.json`
- `legacy_user_settings_guest.json`

### 設定ファイル内容
```json
{
  "username": "admin",
  "preferred_lang": "en",
  "last_updated": "2025-06-13T13:10:00.000000"
}
```

## 修正効果

### ✅ 修正前の問題
- 設定保存: セッションのみ → ログアウト時に消失
- 設定復元: なし → 再ログイン時にデフォルトに戻る

### ✅ 修正後の改善
- **設定保存**: セッション + JSONファイル → 永続保存
- **設定復元**: ログイン時・プロフィール表示時・メインページアクセス時 → 確実な復元
- **多重保護**: セッション、ファイル、複数箇所での復元チェック

## テスト結果

✅ **基本テスト**: 設定保存・復元機能が正常に動作  
✅ **複数ユーザーテスト**: ユーザー別設定が独立して管理  
✅ **永続化テスト**: ログアウト→再ログイン後も設定が保持

## 使用方法

1. **設定変更**: プロフィール画面で言語設定を変更
2. **自動保存**: セッション + JSONファイルに自動保存
3. **自動復元**: ログイン時・ページアクセス時に自動復元

## ログ確認

設定保存・復元時のログで動作確認可能：

```
従来ユーザー設定をファイルに保存: legacy_user_settings_admin.json
従来ユーザー設定復元: admin -> 言語: en
従来ユーザー設定をファイルから復元: admin -> en
```

## 注意事項

- 新認証システムユーザーには影響なし（データベース保存継続）
- 従来ユーザーのみがJSONファイル方式を使用
- エラー処理により、ファイル操作失敗時もアプリは正常動作

---

**📅 修正完了**: 2025年6月13日  
**🎯 問題解決**: 設定の永続化が完全に動作し、ログアウト→再ログイン後も設定が保持される
