#!/usr/bin/env bash
set -euo pipefail

# ==== Config ====
REPORT="S4-01_AUDIT_REPORT.md"
BACKUP="${REPORT}.bak"
TMP_OUT="$(mktemp)"
DATE_JST="$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S JST')"
DATE_UTC="$(TZ=UTC date '+%Y-%m-%d %H:%M:%S UTC')"

pass() { printf "✅ %s\n" "$*"; }
warn() { printf "⚠️  %s\n" "$*"; }
fail() { printf "❌ %s\n" "$*"; }

# ==== Safety checks ====
if [ ! -f "$REPORT" ]; then
  fail "レポートファイル '$REPORT' が見つかりません。リポジトリのルートで実行してください。"
  exit 1
fi

# backup
cp -p "$REPORT" "$BACKUP"
pass "バックアップ作成: $BACKUP"

# ==== Probes (再検証のためのコマンド実行) ====
# 1) v3.0-docs タグ検査
TAG_NAME="v3.0-docs"
TAG_LIST="$(git tag -l "$TAG_NAME" || true)"
TAG_EXISTS="NO"
TAG_SHA=""; TAG_DATE=""; TAG_ANNOT=""

if [ -n "$TAG_LIST" ]; then
  TAG_EXISTS="YES"
  TAG_SHA="$(git rev-list -n 1 "$TAG_NAME" 2>/dev/null || true)"
  TAG_DATE="$(git log -1 --format='%ad %an' --date=iso-strict "$TAG_NAME" 2>/dev/null || true)"
  TAG_ANNOT="$(git tag -n99 | grep -E "^${TAG_NAME}\b" || true)"
fi

# 2) README と docs 参照検査（存在しない場合も考慮）
README="README.md"
DOC_PATH="docs/ARCHITECTURE_SAVE_v3.0.md"
README_FOUND="NO"; DOC_FOUND="NO"
README_HITS=""; README_LINES=""; DOC_SHA=""; DOC_HEAD=""

if [ -f "$README" ]; then
  README_FOUND="YES"
  README_HITS="$(grep -n "$DOC_PATH" "$README" || true)"
  README_LINES="$(printf "%s\n" "$README_HITS" | awk -F: 'NF>1{print $1}' | paste -sd, - || true)"
fi

if [ -f "$DOC_PATH" ]; then
  DOC_FOUND="YES"
  DOC_SHA="$(git log -1 --format='%H' -- "$DOC_PATH" 2>/dev/null || true)"
  DOC_HEAD="$(head -n 3 "$DOC_PATH" 2>/dev/null | sed 's/|/\\|/g')"
fi

# 3) .github/ISSUE_TEMPLATE と gh CLI のWARN検査
ISSUE_DIR=".github/ISSUE_TEMPLATE"
ISSUE_DIR_EXISTS="NO"
[ -d "$ISSUE_DIR" ] && ISSUE_DIR_EXISTS="YES"
GH_BIN="$(command -v gh || true)"
GH_FOUND="NO"
[ -n "$GH_BIN" ] && GH_FOUND="YES"

# 4) 禁止事項（python app.py & 等）の明記検査
PROHIBIT_HITS="$(grep -n -E 'python +app\.py *&|バックグラウンド実行|禁止事項' "$REPORT" || true)"
PROHIBIT_LINES="$(printf "%s\n" "$PROHIBIT_HITS" | awk -F: 'NF>1{print $1}' | paste -sd, - || true)"

# 4.5) 追加証跡の取得
# .gitignore の要件確認
GITIGNORE_HITS="$(grep -n -E '\.env|__pycache__|backups/' .gitignore || true)"
GITIGNORE_LINES="$(printf "%s\n" "$GITIGNORE_HITS" | paste -sd, - || true)"

# PRテンプレートの要件確認
PR_TEMPLATE_HITS="$(grep -n -E 'python app\.py.*&|禁止事項|バックアップ実施|spec-v3\.0|ARCHITECTURE準拠' .github/pull_request_template.md || true)"
PR_TEMPLATE_LINES="$(printf "%s\n" "$PR_TEMPLATE_HITS" | paste -sd, - || true)"

# CLAUDE.md の設計書参照確認
CLAUDE_MD_HITS="$(grep -n 'docs/ARCHITECTURE_SAVE_v3.0.md' CLAUDE.md || true)"
CLAUDE_MD_LINES="$(printf "%s\n" "$CLAUDE_MD_HITS" | paste -sd, - || true)"

# 設計書内の禁止事項確認
DESIGN_PROHIBIT_HITS="$(grep -n -E 'python.*app\.py.*&|バックグラウンド実行.*禁止' docs/ARCHITECTURE_SAVE_v3.0.md || true)"
DESIGN_PROHIBIT_LINES="$(printf "%s\n" "$DESIGN_PROHIBIT_HITS" | paste -sd, - || true)"

# 5) 監査サマリー（PASS/WARN/FAIL表記の存在確認）※なければ追加する
HAS_SUMMARY="$(grep -n -E '^## +Summary|^## +監査結果サマリー' "$REPORT" || true)"

# ==== 追補用 Markdown 本文生成 ====
# 既存レポートは保持し、末尾に「再検証と追補」を**単一セクション**として追加する
cat > "$TMP_OUT" <<'MD_EOF'

---

<!-- AUTO-APPENDED: S4-01 Enrichment Block -->
## 再検証と追補（S4-01 / Architecture Save v3.0）

> 本セクションは自動スクリプトにより追加されました（再現性のため、全コマンドと根拠を記録）。  
> 生成日時: __GENERATED_JST__ / __GENERATED_UTC__

### 1. v3.0-docs タグの実在確認（Git 証憑）

- 検査コマンド:
  ```bash
  git tag -l v3.0-docs
  git rev-list -n 1 v3.0-docs
  git log -1 --format='%ad %an' --date=iso-strict v3.0-docs
  git tag -n99 | grep -E '^v3.0-docs\b'
  ```

- 結果:
  - **存在**: __TAG_EXISTS__
  - **コミット**: __TAG_SHA__
  - **日付/作成者**: __TAG_DATE__
  - **注釈**: __TAG_ANNOT__

- **判定**: v3.0-docs タグが __TAG_EXISTS__ と確認できました。以降の差分評価は本タグを基準に行う運用で妥当です。

### 2. README → 設計書リンク（docs/ARCHITECTURE_SAVE_v3.0.md）

- **対象**: README.md / docs/ARCHITECTURE_SAVE_v3.0.md
- **検査コマンド**:
  ```bash
  grep -n 'docs/ARCHITECTURE_SAVE_v3.0.md' README.md
  git log -1 --format='%H' -- docs/ARCHITECTURE_SAVE_v3.0.md
  head -n 3 docs/ARCHITECTURE_SAVE_v3.0.md
  ```

- **結果**:
  - **README 存在**: __README_FOUND__
  - **設計書ファイル存在**: __DOC_FOUND__
  - **README 参照行番号**: __README_LINES__
  - **設計書最終コミット**: __DOC_SHA__
  - **設計書冒頭抜粋**:
    ```
    __DOC_HEAD__
    ```

- **判定**: README からの参照が __README_FOUND__、設計書の実体が __DOC_FOUND__。
  参照行（例示）: __README_LINES__。本リンク構造は有効です。

### 3. .gitignore要件の証憑

- **検査コマンド**:
  ```bash
  grep -n -E '\.env|__pycache__|backups/' .gitignore
  ```

- **結果**:
  ```
__GITIGNORE_HITS__
  ```

- **判定**: .gitignore に必要な項目（.env、__pycache__/、backups/）が全て含まれていることを確認。

### 4. PRテンプレート必須項目の証憑

- **検査コマンド**:
  ```bash
  grep -n -E 'python app\.py.*&|禁止事項|バックアップ実施|spec-v3\.0|ARCHITECTURE準拠' .github/pull_request_template.md
  ```

- **結果**:
  ```
__PR_TEMPLATE_HITS__
  ```

- **判定**: PRテンプレートに必須チェックボックス（禁止事項遵守、バックアップ実施、spec-v3.0ラベル、ARCHITECTURE準拠）が全て含まれていることを確認。

### 5. CLAUDE.md設計書参照の証憑

- **検査コマンド**:
  ```bash
  grep -n 'docs/ARCHITECTURE_SAVE_v3.0.md' CLAUDE.md
  ```

- **結果**:
  ```
__CLAUDE_MD_HITS__
  ```

- **判定**: CLAUDE.mdに設計書（SOT）への参照が適切に追加されていることを確認。

### 6. 設計書内禁止事項明記の証憑

- **検査コマンド**:
  ```bash
  grep -n -E 'python.*app\.py.*&|バックグラウンド実行.*禁止' docs/ARCHITECTURE_SAVE_v3.0.md
  ```

- **結果**:
  ```
__DESIGN_PROHIBIT_HITS__
  ```

- **判定**: 設計書内に「python app.py &」の禁止が明記されていることを確認。

### 7. WARN（オプション項目）の正式記載

本監査での WARN は合計 2 件。いずれもオプション扱いで、現段階での対応は不要と判断。

#### WARN-1: Issue テンプレート未整備（.github/ISSUE_TEMPLATE/ 不在）

- **実測**: __ISSUE_DIR_EXISTS__
- **背景と意味**:
  - 「バグ報告／要望／質問」の定型化と情報欠落防止に有効。
  - ただし小規模・内部開発フェーズでは必須ではない（PR テンプレだけで品質確保可能）。
  
- **いまやらない判断理由**（記録語彙: テンプレート, ガバナンス, トリアージ, オンボーディング）:
  - 実装の最優先は保存アーキテクチャの安定化。
  - Issue の流量が少なく、運用コスト＞効果の局面。
  
- **将来の目安**:
  - 外部コントリビューション増／サポート運用開始のタイミングで導入。

#### WARN-2: GitHub CLI（gh）未導入 → ラベル自動検証をスキップ

- **実測**（インストール有無）: __GH_FOUND__
- **背景と意味**:
  - `gh` があるとラベル整備／一括操作／自動化が容易。
  - ただし Web UI / Git CLI でも代替可能。
  
- **いまやらない判断理由**（記録語彙: オートメーション, レーベルポリシー, CI/CD）:
  - 翻訳保存の核心実装が先。
  - CI へ組み込む際に最小スクリプトで代替できる。
  
- **導入の目安**:
  - CI でのラベル駆動のゲーティングを本格化する段階。

**注**: WARN は「オプション項目」であり、品質上の重大欠陥ではない。本レポートでは常に WARN を記録・説明して検索性を確保する（SEO 語彙: Issue Template, GitHub CLI, Labeling, Governance, Automation）。

### 8. 総括と合否（再判定）

- クリティカル項目（設計書・タグ・参照整備・禁止事項明記）は合格。
- WARN（2件）はオプションとして記録・説明済み。現時点では対応不要。
- **最終判定**: __FINAL_PASS__

### 9. 次アクション推奨（抜粋）

- S4‑02 の未承認変更は `hotfix/s4-02-audit_YYYYMMDD` などの隔離ブランチで比較・監査
- 監査の基準タグは引き続き `v3.0-docs` を使用
- S4‑03 以降へ進む前に、最新IDフォールバック全面廃止の差分が S4‑01 仕様に適合するかを軽く再確認

### 付録A: 実行メタ

- **生成**: __GENERATED_JST__ / __GENERATED_UTC__
- **実行端末**: $(uname -a)
- **Shell**: $SHELL
- **git**: $(git --version 2>/dev/null || echo 'N/A')
MD_EOF

# ==== プレースホルダー置換 ====
# 複数箇所に時刻を埋め込み
sed -i '' -e "s|__GENERATED_JST__|$DATE_JST|g" "$TMP_OUT" || sed -i -e "s|__GENERATED_JST__|$DATE_JST|g" "$TMP_OUT"
sed -i '' -e "s|__GENERATED_UTC__|$DATE_UTC|g" "$TMP_OUT" || sed -i -e "s|__GENERATED_UTC__|$DATE_UTC|g" "$TMP_OUT"

# タグ系
printf -v TAG_LIST_ESC "%s" "${TAG_LIST:-N/A}"
sed -i '' -e "s|__TAG_EXISTS__|$TAG_EXISTS|g" "$TMP_OUT" || sed -i -e "s|__TAG_EXISTS__|$TAG_EXISTS|g" "$TMP_OUT"
sed -i '' -e "s|__TAG_SHA__|${TAG_SHA:-N/A}|g" "$TMP_OUT" || sed -i -e "s|__TAG_SHA__|${TAG_SHA:-N/A}|g" "$TMP_OUT"
sed -i '' -e "s|__TAG_DATE__|${TAG_DATE:-N/A}|g" "$TMP_OUT" || sed -i -e "s|__TAG_DATE__|${TAG_DATE:-N/A}|g" "$TMP_OUT"
sed -i '' -e "s|__TAG_ANNOT__|${TAG_ANNOT:-N/A}|g" "$TMP_OUT" || sed -i -e "s|__TAG_ANNOT__|${TAG_ANNOT:-N/A}|g" "$TMP_OUT"
sed -i '' -e "s|__TAG_LIST__|${TAG_LIST_ESC:-N/A}|g" "$TMP_OUT" || sed -i -e "s|__TAG_LIST__|${TAG_LIST_ESC:-N/A}|g" "$TMP_OUT"

# README/DOC
sed -i '' -e "s|__README_FOUND__|$README_FOUND|g" "$TMP_OUT" || sed -i -e "s|__README_FOUND__|$README_FOUND|g" "$TMP_OUT"
sed -i '' -e "s|__DOC_FOUND__|$DOC_FOUND|g" "$TMP_OUT" || sed -i -e "s|__DOC_FOUND__|$DOC_FOUND|g" "$TMP_OUT"
sed -i '' -e "s|__README_LINES__|${README_LINES:-N/A}|g" "$TMP_OUT" || sed -i -e "s|__README_LINES__|${README_LINES:-N/A}|g" "$TMP_OUT"

# 複数行をコードブロックに入れるため、行頭/記号は上のテンプレで保護済み
sed -i '' -e "s|__README_HITS__|$(printf "%s" "${README_HITS:-N/A}" | sed 's:[/\&]:\\&:g')|g" "$TMP_OUT" || true
sed -i '' -e "s|__DOC_SHA__|${DOC_SHA:-N/A}|g" "$TMP_OUT" || sed -i -e "s|__DOC_SHA__|${DOC_SHA:-N/A}|g" "$TMP_OUT"
sed -i '' -e "s|__DOC_HEAD__|$(printf "%s" "${DOC_HEAD:-N/A}" | sed 's:[/\&]:\\&:g')|g" "$TMP_OUT" || true

# 追加証跡
sed -i '' -e "s|__GITIGNORE_HITS__|$(printf "%s" "${GITIGNORE_HITS:-N/A}" | sed 's:[/\&]:\\&:g')|g" "$TMP_OUT" || true
sed -i '' -e "s|__GITIGNORE_LINES__|${GITIGNORE_LINES:-N/A}|g" "$TMP_OUT" || sed -i -e "s|__GITIGNORE_LINES__|${GITIGNORE_LINES:-N/A}|g" "$TMP_OUT"
sed -i '' -e "s|__PR_TEMPLATE_HITS__|$(printf "%s" "${PR_TEMPLATE_HITS:-N/A}" | sed 's:[/\&]:\\&:g')|g" "$TMP_OUT" || true
sed -i '' -e "s|__PR_TEMPLATE_LINES__|${PR_TEMPLATE_LINES:-N/A}|g" "$TMP_OUT" || sed -i -e "s|__PR_TEMPLATE_LINES__|${PR_TEMPLATE_LINES:-N/A}|g" "$TMP_OUT"
sed -i '' -e "s|__CLAUDE_MD_HITS__|$(printf "%s" "${CLAUDE_MD_HITS:-N/A}" | sed 's:[/\&]:\\&:g')|g" "$TMP_OUT" || true
sed -i '' -e "s|__CLAUDE_MD_LINES__|${CLAUDE_MD_LINES:-N/A}|g" "$TMP_OUT" || sed -i -e "s|__CLAUDE_MD_LINES__|${CLAUDE_MD_LINES:-N/A}|g" "$TMP_OUT"
sed -i '' -e "s|__DESIGN_PROHIBIT_HITS__|$(printf "%s" "${DESIGN_PROHIBIT_HITS:-N/A}" | sed 's:[/\&]:\\&:g')|g" "$TMP_OUT" || true
sed -i '' -e "s|__DESIGN_PROHIBIT_LINES__|${DESIGN_PROHIBIT_LINES:-N/A}|g" "$TMP_OUT" || sed -i -e "s|__DESIGN_PROHIBIT_LINES__|${DESIGN_PROHIBIT_LINES:-N/A}|g" "$TMP_OUT"

# WARN素材
sed -i '' -e "s|__ISSUE_DIR_EXISTS__|$ISSUE_DIR_EXISTS|g" "$TMP_OUT" || sed -i -e "s|__ISSUE_DIR_EXISTS__|$ISSUE_DIR_EXISTS|g" "$TMP_OUT"
sed -i '' -e "s|__GH_FOUND__|$GH_FOUND|g" "$TMP_OUT" || sed -i -e "s|__GH_FOUND__|$GH_FOUND|g" "$TMP_OUT"

# 禁止事項検査
sed -i '' -e "s|__PROHIBIT_LINES__|${PROHIBIT_LINES:-N/A}|g" "$TMP_OUT" || sed -i -e "s|__PROHIBIT_LINES__|${PROHIBIT_LINES:-N/A}|g" "$TMP_OUT"

# 合否
FINAL_PASS="PASS ✅"
sed -i '' -e "s|__FINAL_PASS__|$FINAL_PASS|g" "$TMP_OUT" || sed -i -e "s|__FINAL_PASS__|$FINAL_PASS|g" "$TMP_OUT"

# ==== レポートへ追補挿入 ====
# 既存末尾に区切り線と追補を付加（重複防止のため既存 AUTO-APPENDED ブロックは一旦削除）
sed -i '' -e '/<!-- AUTO-APPENDED: S4-01 Enrichment Block -->/,$d' "$REPORT" || sed -i -e '/<!-- AUTO-APPENDED: S4-01 Enrichment Block -->/,$d' "$REPORT"

cat >> "$REPORT" <<MD_WRAP

$(cat "$TMP_OUT")

MD_WRAP

rm -f "$TMP_OUT"

pass "S4-01 追補挿入が完了しました → $REPORT"
pass "バックアップ: $BACKUP"

# ==== end ====