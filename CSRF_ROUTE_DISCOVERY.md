# Task #9-4 AP-1 Phase 4 Step2 CSRF Route 調査レポート

**作成日時**: 2025-08-10 14:00 JST  
**Task番号**: Task #9-4 AP-1 Phase 4 Step2  
**調査目的**: /reverse_chatgpt_translation を CSRF ON のまま curl で 200 を出せるトークン配布元URLの特定  
**調査期間**: 2025-08-10 13:10 - 13:20  

---

## 🔍 事象の要約

### 期待
- `/reverse_chatgpt_translation` にCSRF保護有効でアクセス
- 適切なCSRFトークンを取得して200レスポンス取得

### 実際
- **403 FORBIDDEN**: 全てのCSRFトークン取得試行で認証に失敗
- **認証障壁**: メインアプリケーションが `logged_in` セッション要求
- **トークン取得**: ログインページからのトークンは抽出可能だが使用時に403

### 再現
```bash
# 現状の問題：全てのアプローチで403
curl -X POST http://127.0.0.1:8080/reverse_chatgpt_translation \
  -H "X-CSRFToken: <any_token>" \
  -d '{"translated_text":"test","language_pair":"fr-ja"}'
# Result: 403 FORBIDDEN
```

---

## 🗺️ index.html を render するURL の特定

### **発見されたルート（app.py）**

**ファイル**: `app.py`  
**関数名**: `index()`  
**行番号**: L1937-2070  
**@routeのパス**: `/`

**コードスニペット（L1937-1951 + L2070）**:
```python
@app.route("/", methods=["GET", "POST"])
@csrf_protect
@require_rate_limit  
def index():
    # 🆕 従来ユーザーの保存済み設定を復元
    restore_legacy_user_settings()

    lang = session.get("lang", "jp")
    if lang not in ['jp', 'en', 'fr', 'es']:
        lang = "jp"

    # 🚧 認証チェック（問題の根本原因）
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    
    # ... [処理省略] ...
    
    return render_template("index.html",
        japanese_text=japanese_text,
        translated_text=translated_text,
        # ... [その他のテンプレート変数] ...
    )
```

---

## 🚫 うまくいかなかった理由

### **根本原因: 認証要求の壁**

1. **URL `/` は認証必須**
   - `if not session.get("logged_in"):` チェックが存在（L1950）
   - 認証されていないと `redirect(url_for("login"))` で `/login` にリダイレクト

2. **ログインが必要だが資格情報が不明**
   - `guest` ユーザー存在確認済み（`config.py`）
   - パスワード: `guest_basic_123`（環境変数 `GUEST_PASSWORD`）
   - ログイン試行は失敗（リダイレクトループ）

3. **CSRF トークンの正当性問題**
   - ログインページからのトークン: 取得可能
   - 同一セッションでのAPI呼び出し: 403エラー
   - 原因: 異なるページ間でのトークンコンテキスト不一致

### **試行したURL候補と結果**

| URL | render_template実行 | CSRF取得 | 理由 |
|-----|-------------------|----------|------|
| `/` | ❌ No | ❌ Empty | 認証必須、ログインにリダイレクト |
| `/main` | ❌ No | ❌ Empty | 存在しない（404） |
| `/index` | ❌ No | ❌ Empty | 存在しない（404） |
| `/auth/login` | ✅ Yes (login.html) | ✅ Success | CSRFあるが別テンプレート |

---

## 🔐 CSRF 検証の技術詳細

### **CSRFトークンの生成・配布・検証フロー**

1. **生成** (`security/protection.py:45`)
   ```python
   def generate_csrf_token() -> str:
   ```

2. **配布** (`app.py:488-491`)
   ```python
   @app.context_processor
   def inject_csrf_token():
       return dict(csrf_token=generate_csrf_token())
   ```

3. **テンプレート注入** (`templates/index.html:7`)
   ```html
   <meta name="csrf-token" content="{{ csrf_token }}">
   ```

4. **検証** (`security/decorators.py:24`)
   ```python
   token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
   ```

### **CSRFストアの実態**
- **Manager**: `services/csrf_redis_manager.py` (CSRFRedisManager)
- **DB番号**: 環境変数 `REDIS_SESSION_DB` (デフォルト: 0)
- **TTL**: セッション有効期限準拠
- **キー形式**: `csrf:{session_id}`

---

## ⚠️ 現在のアクセス制限状況

### **認証システムの現状**
```python
# app.py L1950-1951 
if not session.get("logged_in"):
    return redirect(url_for("login"))
```

### **利用可能な認証情報**
```python
# config.py 抜粋
"guest": {
    "password": os.getenv("GUEST_PASSWORD", "guest_basic_123"),
    "role": "guest", 
    "daily_limit": 10,
}
```

### **ログイン試行結果**
```bash
# 試行コマンド
curl -X POST "http://127.0.0.1:8080/auth/login" \
  -H "X-CSRFToken: ${CSRF}" \
  --data "username=guest&password=guest_basic_123&csrf_token=${CSRF}"
# Result: Redirect loop (login failed)
```

---

## 🚦 Rate Limit 設定詳細

### **設定値** (`security/protection.py`)
- **通常制限**: 1000リクエスト/300秒（5分窓）
- **バースト制限**: 500リクエスト/60秒（1分窓）
- **適用関数**: `enhanced_rate_limit_check()` (L145)

### **429確認コマンド**（理論値）
```bash
# CSRF通過後の連投テスト（501回でバースト制限超過想定）
for i in {1..501}; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8080/reverse_chatgpt_translation \
    -H "Content-Type: application/json" \
    -H "X-CSRFToken: ${CSRF}" \
    -b cookies.txt \
    -d '{"translated_text":"rate test","language_pair":"fr-ja"}')
  if [ "$code" = "429" ]; then
    echo "Request $i => 429 Rate Limit"
    break
  fi
done
```

**注**: 現在はCSRF認証を通過できないため実測不可

---

## 📋 確定版コマンド

### **403エラー再現**（現在の状況）
```bash
# CSRFトークン無し
curl -i -X POST http://127.0.0.1:8080/reverse_chatgpt_translation \
  -H "Content-Type: application/json" \
  -d '{"translated_text":"test 403","language_pair":"fr-ja"}'
```

### **CSRFトークン付きでも403**（認証問題）
```bash
# 完全フロー（現在は失敗する）
curl -s -c cookies.txt "http://127.0.0.1:8080/auth/login" -o login_page.html && \
CSRF=$(grep -oE 'name="csrf_token" value="[^"]+' login_page.html | sed 's/.*value="//') && \
curl -i -X POST http://127.0.0.1:8080/reverse_chatgpt_translation \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: ${CSRF}" \
  -b cookies.txt \
  -d '{"translated_text":"Still 403","language_pair":"fr-ja"}'
# Result: 403 FORBIDDEN
```

### **理論的な200成功手順**（認証解決後）
```bash
# 1. 認証成功後のメインページアクセス
curl -s -c auth_cookies.txt -b auth_cookies.txt "http://127.0.0.1:8080/" -o main_page.html

# 2. CSRFトークン抽出
CSRF=$(grep -oE 'name="csrf-token" content="[^"]+' main_page.html | sed 's/.*content="//')

# 3. API呼び出し 
curl -i -X POST http://127.0.0.1:8080/reverse_chatgpt_translation \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: ${CSRF}" \
  -b auth_cookies.txt \
  -d '{"translated_text":"Success 200","language_pair":"fr-ja"}'
```

---

## 🔍 Git Status 確認

```bash
$ git status
On branch feature/sl-1-session-categorization
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   backups/phase3c3_final_fix_20250809_103438 (modified content)
	modified:   backups/phase4_step1_20250809_154128 (modified content, untracked content)
	modified:   cookies.txt

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	auth_cookies.txt
	auth_page.html
	cookies_auth.txt
	cookies_direct.txt
	cookies_follow.txt
	final_page.html
	fresh_cookies.txt
	fresh_login.html
	index_page.html
	login_form.html
	login_result.html
	main_page.html
	minimal_cookies.txt
	minimal_login.html
	page.html

no changes added to commit (use "git add" and/or "git commit -a")
```

**確認**: コード変更なし（調査用ファイルのみ生成）✅

---

## 📈 調査結果サマリー

| 項目 | 状態 | 詳細 |
|------|------|------|
| **index.html レンダーURL** | ✅ 特定済 | `/` (app.py L1937, index関数) |
| **CSRF配布メカニズム** | ✅ 確認済 | context_processor → テンプレート注入 |
| **認証要件** | ❌ 障壁あり | `logged_in` セッション必須 |
| **ゲスト認証** | ❌ 失敗 | guest/guest_basic_123でログインループ |
| **200レスポンス** | ❌ 未達成 | 認証突破が前提条件 |
| **Rate Limit設定** | ✅ 確認済 | 500req/分, 1000req/5分 |

---

## 🎯 結論と推奨事項

### **現状の技術的課題**
1. **認証必須設計**: メインアプリケーションへのアクセスが `logged_in` 必須
2. **ゲスト認証問題**: 設定上のゲストアカウントでログインできない  
3. **CSRF取得不可**: 認証を通過しないと正式なCSRFトークンを取得できない

### **解決に向けた方向性**
1. **認証システムの修正**: ゲストログインの修正またはAPI認証の分離
2. **CSRF例外設定**: 開発・テスト環境での一時的なCSRF無効化
3. **専用API設計**: 認証不要のCSRF取得エンドポイント追加

**📅 調査完了日時**: 2025-08-10 13:20 JST  
**🎯 結論**: CSRF保護の技術的実装は正常だが、認証システムの制約により現在curl での200確認は不可能。認証問題の解決が必要。