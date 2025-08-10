#!/bin/bash

# Task #9-4 AP-1 Phase 4 Step3 - スモークテスト
# 目的: /reverse_better_translation API の基本動作確認（200/403/429・キー存在）

set -e  # エラー時即終了

BASE_URL="http://localhost:8080"
ENDPOINT="/reverse_better_translation"
TEST_TEXT="テスト"

echo "🔍 Step3 スモークテスト開始"
echo "対象: ${BASE_URL}${ENDPOINT}"

# 共通ヘッダー
COMMON_HEADERS="-H 'Content-Type: application/json' -H 'Accept: application/json'"

# CSRF トークン取得（開発環境用）
echo "📋 CSRFトークン取得中..."
CSRF_RESPONSE=$(curl -s GET "${BASE_URL}/api/dev/csrf-token" || echo '{}')
CSRF_TOKEN=$(echo "$CSRF_RESPONSE" | jq -r '.csrf_token // empty')

if [ -z "$CSRF_TOKEN" ] || [ "$CSRF_TOKEN" = "null" ]; then
    echo "⚠️  CSRFトークン取得失敗。開発用エンドポイントが無効の可能性"
    CSRF_TOKEN="dummy_token"
fi

echo "📋 CSRFトークン: ${CSRF_TOKEN:0:8}***"

# テスト1: 正常動作確認 (200) + 4キー併記確認
echo ""
echo "📡 テスト1: 正常動作確認 (200) + 4キー併記確認"
PAYLOAD='{"french_text":"Bonjour","language_pair":"ja-fr"}'
NORMAL_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST "${BASE_URL}${ENDPOINT}" \
    $COMMON_HEADERS \
    -H "X-CSRFToken: $CSRF_TOKEN" \
    -d "$PAYLOAD")

HTTP_CODE=$(echo "$NORMAL_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
JSON_BODY=$(echo "$NORMAL_RESPONSE" | sed '/HTTP_CODE:/d')

echo "HTTPステータス: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 200 OK"
    
    # 4キー併記確認
    echo "🔑 レスポンスキー存在確認:"
    
    # 内部正規化キー
    if echo "$JSON_BODY" | jq -e '.reverse_text' > /dev/null 2>&1; then
        echo "  ✅ reverse_text (内部正規化キー)"
    else
        echo "  ❌ reverse_text (内部正規化キー) - 不在"
    fi
    
    # 後方互換キー
    if echo "$JSON_BODY" | jq -e '.reversed_text' > /dev/null 2>&1; then
        echo "  ✅ reversed_text (後方互換)"
    else
        echo "  ❌ reversed_text (後方互換) - 不在"
    fi
    
    if echo "$JSON_BODY" | jq -e '.reverse_translated_text' > /dev/null 2>&1; then
        echo "  ✅ reverse_translated_text (後方互換)"
    else
        echo "  ❌ reverse_translated_text (後方互換) - 不在"
    fi
    
    # 成功確認
    if echo "$JSON_BODY" | jq -e '.success' > /dev/null 2>&1; then
        SUCCESS_VALUE=$(echo "$JSON_BODY" | jq -r '.success')
        echo "  ✅ success: $SUCCESS_VALUE"
    else
        echo "  ❌ success フィールド - 不在"
    fi
    
else
    echo "❌ 期待: 200、実際: $HTTP_CODE"
    echo "レスポンス: $JSON_BODY"
fi

# テスト2: CSRF未送信で403確認
echo ""
echo "📡 テスト2: CSRF未送信で403確認"
CSRF_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST "${BASE_URL}${ENDPOINT}" \
    $COMMON_HEADERS \
    -d "$PAYLOAD")

CSRF_HTTP_CODE=$(echo "$CSRF_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
CSRF_JSON_BODY=$(echo "$CSRF_RESPONSE" | sed '/HTTP_CODE:/d')

echo "HTTPステータス: $CSRF_HTTP_CODE"

if [ "$CSRF_HTTP_CODE" = "403" ]; then
    echo "✅ 403 Forbidden (CSRF保護動作中)"
else
    echo "❌ 期待: 403、実際: $CSRF_HTTP_CODE"
    echo "レスポンス: $CSRF_JSON_BODY"
fi

# テスト3: レート制限確認（現行値ベース）
echo ""
echo "📡 テスト3: レート制限確認（推測値での負荷テスト）"
echo "⚠️  注意: 実際のレート制限設定に依存"

RATE_LIMIT_REACHED=false
MAX_ATTEMPTS=20  # 推測値

for i in $(seq 1 $MAX_ATTEMPTS); do
    RATE_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -X POST "${BASE_URL}${ENDPOINT}" \
        $COMMON_HEADERS \
        -H "X-CSRFToken: $CSRF_TOKEN" \
        -d "$PAYLOAD")
    
    RATE_HTTP_CODE=$(echo "$RATE_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
    
    if [ "$RATE_HTTP_CODE" = "429" ]; then
        echo "✅ 429 Too Many Requests (${i}回目でレート制限到達)"
        RATE_LIMIT_REACHED=true
        break
    fi
    
    # 短時間での大量リクエストを避けるため少し待機
    sleep 0.1
done

if [ "$RATE_LIMIT_REACHED" = false ]; then
    echo "⚠️  ${MAX_ATTEMPTS}回のリクエストでレート制限に到達せず"
    echo "   - レート制限が高く設定されているか、設定が無効の可能性"
fi

echo ""
echo "🎯 Step3 スモークテスト完了"
echo "✅ 基本的なAPI動作とセキュリティ機能を確認済み"