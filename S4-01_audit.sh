#!/usr/bin/env bash
# S4-01 自動監査スクリプト（Bash版）
# 用途: リポジトリのルートで実行し、事前調査チェックリストを自動点検
# 注意: バックグラウンド実行は禁止（python app.py & など）
set -u

REPO_ROOT="$(pwd)"
REPORT="$REPO_ROOT/S4-01_AUDIT_REPORT.md"
PASS_ICON="✅"
FAIL_ICON="❌"
WARN_ICON="⚠️"

# 収集用
PASS=()
FAIL=()
WARN=()

add_pass(){ PASS+=("$1"); }
add_fail(){ FAIL+=("$1"); }
add_warn(){ WARN+=("$1"); }

exists_file(){ [ -f "$1" ]; }
exists_dir(){ [ -d "$1" ]; }

line() { printf -- "--------------------------------------------------------------------------------\n"; }

start_time="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"

# --------------------------------------------------------------------------------
# 0) 前提: git 管理配下かの確認
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "This folder is not a Git repository. Abort."
  exit 2
fi

# --------------------------------------------------------------------------------
# 1) リポジトリ構造の確認
DOCS_DIR="docs"
ARCH_MD="$DOCS_DIR/ARCHITECTURE_SAVE_v3.0.md"
README="README.md"
CONTRIB="CONTRIBUTING.md"
CHANGELOG="CHANGELOG.md"

if exists_dir "$DOCS_DIR"; then
  add_pass "[docs/] exists"
else
  add_fail "[docs/] NOT found"
fi

if exists_file "$ARCH_MD"; then
  add_pass "[$ARCH_MD] exists"
else
  add_fail "[$ARCH_MD] NOT found"
fi

if exists_file "$README"; then
  # Architecture章・リンク存在チェック
  if grep -qiE 'architecture|アーキテクチャ' "$README"; then
    if grep -q "docs/ARCHITECTURE_SAVE_v3.0.md" "$README"; then
      add_pass "[README.md] has link to $ARCH_MD"
    else
      add_warn "[README.md] exists but NO link to $ARCH_MD"
    fi
  else
    add_warn "[README.md] exists but NO 'Architecture' section keyword"
  fi
else
  add_warn "[README.md] NOT found"
fi

[ -f "$CONTRIB" ] && add_pass "[$CONTRIB] exists" || add_warn "[$CONTRIB] NOT found"
[ -f "$CHANGELOG" ] && add_pass "[$CHANGELOG] exists" || add_warn "[$CHANGELOG] NOT found"

# --------------------------------------------------------------------------------
# 2) Git 管理状況の確認
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'UNKNOWN')"
BR_LIST="$(git branch --format='%(refname:short)' 2>/dev/null | sed 's/^/* /')"
TAGS="$(git tag --list | sed 's/^/* /')"
GITIGNORE=".gitignore"

[ -n "$CURRENT_BRANCH" ] && add_pass "Current branch: $CURRENT_BRANCH" || add_warn "Cannot detect current branch"
[ -n "$BR_LIST" ] && add_pass "Branch list collected" || add_warn "No branches?"

if [ -n "$TAGS" ]; then
  if echo "$TAGS" | grep -q '\* v3\.0-docs'; then
    add_pass "Tag v3.0-docs exists"
  else
    add_warn "Tag v3.0-docs NOT found"
  fi
else
  add_warn "No tags found"
fi

if exists_file "$GITIGNORE"; then
  GI_MISS=()
  for pat in ".env" "__pycache__/" "backups/"; do
    if ! grep -qxF "$pat" "$GITIGNORE" && ! grep -qE "^${pat//\//\\/}(\$|/)" "$GITIGNORE"; then
      GI_MISS+=("$pat")
    fi
  done
  if [ "${#GI_MISS[@]}" -eq 0 ]; then
    add_pass "[.gitignore] has required entries (.env, __pycache__/, backups/)"
  else
    add_warn "[.gitignore] missing: ${GI_MISS[*]}"
  fi
else
  add_warn "[.gitignore] NOT found"
fi

# --------------------------------------------------------------------------------
# 3) PR/Issue 管理の確認
PR_TPL=".github/pull_request_template.md"
ISSUE_DIR=".github/ISSUE_TEMPLATE"

if exists_file "$PR_TPL"; then
  # 必須チェック項目が入っているか
  reqs=("ARCHITECTURE_SAVE_v3.0.md" "spec-v3.0" "バックアップ" "python app.py &")
  missing=()
  for r in "${reqs[@]}"; do
    grep -qi "$r" "$PR_TPL" || missing+=("$r")
  done
  if [ "${#missing[@]}" -eq 0 ]; then
    add_pass "PR template has required checkboxes/keywords"
  else
    add_warn "PR template missing: ${missing[*]}"
  fi
else
  add_warn "[.github/pull_request_template.md] NOT found"
fi

if exists_dir "$ISSUE_DIR"; then
  add_pass "[.github/ISSUE_TEMPLATE/] exists"
else
  add_warn "[.github/ISSUE_TEMPLATE/] NOT found"
fi

# ラベルはローカルからは取得できないため、gh CLIがあれば参照
if command -v gh >/dev/null 2>&1; then
  if gh repo view >/dev/null 2>&1; then
    LABELS="$(gh label list 2>/dev/null | awk '{print $1}' | sed 's/^/* /')"
    if echo "$LABELS" | grep -qiE '\* (ARCHITECTURE準拠|spec-v3\.0)'; then
      add_pass "Labels include ARCHITECTURE準拠/spec-v3.0"
    else
      add_warn "Labels missing ARCHITECTURE準拠/spec-v3.0"
    fi
  else
    add_warn "gh CLI configured? (cannot fetch labels)"
  fi
else
  add_warn "gh CLI not installed; skip label check"
fi

# --------------------------------------------------------------------------------
# 4) 設計書の最終確認
if exists_file "$ARCH_MD"; then
  # 旧版参照の残骸
  if grep -qiE 'v2(\.0)?' "$ARCH_MD"; then
    add_warn "$ARCH_MD may reference old version (v2.x)"
  else
    add_pass "$ARCH_MD has no legacy version refs"
  fi
  # 禁止事項（python app.py &）の明記
  if grep -q 'python app\.py \&' "$ARCH_MD"; then
    add_pass "$ARCH_MD mentions ban: 'python app.py &'"
  else
    add_warn "$ARCH_MD does NOT mention ban: 'python app.py &'"
  fi
else
  add_fail "$ARCH_MD not found (already reported)"
fi

# --------------------------------------------------------------------------------
# 5) 依存関係・整合性の確認（CLAUDE.md など）
CLAUDE_MD="CLAUDE.md"
if exists_file "$CLAUDE_MD"; then
  # 設計参照の整合
  if grep -q "$ARCH_MD" "$CLAUDE_MD"; then
    add_pass "[CLAUDE.md] references $ARCH_MD"
  else
    add_warn "[CLAUDE.md] does NOT reference $ARCH_MD"
  fi
else
  add_warn "[CLAUDE.md] NOT found"
fi

# 他ドキュメントの参照状況（README 以外）
ARCH_REFS="$(grep -Rns "docs/ARCHITECTURE_SAVE_v3.0.md" . 2>/dev/null | grep -v '^./.git/' || true)"
[ -n "$ARCH_REFS" ] && add_pass "Other docs reference $ARCH_MD" || add_warn "No other docs reference $ARCH_MD (README除く)"

# --------------------------------------------------------------------------------
# レポート出力
{
  echo "# S4-01 Audit Report"
  echo ""
  echo "- Repo: $(basename "$REPO_ROOT")"
  echo "- Date: $start_time"
  line
  echo "## Summary"
  echo "- Pass: ${#PASS[@]}"
  echo "- Warn: ${#WARN[@]}"
  echo "- Fail: ${#FAIL[@]}"
  line
  echo "## PASS"
  for m in "${PASS[@]}"; do echo "- $PASS_ICON $m"; done
  echo ""
  echo "## WARN"
  for m in "${WARN[@]}"; do echo "- $WARN_ICON $m"; done
  echo ""
  echo "## FAIL"
  if [ ${#FAIL[@]} -gt 0 ]; then
    for m in "${FAIL[@]}"; do echo "- $FAIL_ICON $m"; done
  else
    echo "(none)"
  fi
  echo ""
  line
  echo "## Git Branches"
  echo "${BR_LIST:-'(none)'}"
  echo ""
  echo "## Git Tags"
  echo "${TAGS:-'(none)'}"
  echo ""
  echo "## Notes"
  echo "- If [README.md] is missing, create it and link to $ARCH_MD."
  echo "- Ensure PR template contains: architecture compliance, spec-v3.0 label, backup checkbox, and ban of 'python app.py &'."
} > "$REPORT"

# 端末にもサマリ表示
echo ""
line
echo "S4-01 audit finished. Report: $REPORT"

# Exit with failure if there are any FAIL items
fail_count=${#FAIL[@]}
if [ "$fail_count" -gt 0 ]; then
  echo "AUDIT FAILED: $fail_count critical issues found"
  exit 1
else
  echo "AUDIT PASSED: No critical failures"
fi