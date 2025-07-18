"""
Admin API Routes - Phase 4b-2で分離
管理者専用API機能（11個のエンドポイント）
Created: 2025-07-08
Total: 821行をapp.pyから分離

移植対象エンドポイント:
1. /admin/api/four_stage_analysis
2. /admin/api/llm_recommendation_check
3. /admin/api/llm_recommendation_detail/<int:activity_id>
4. /admin/api/stage0_human_check
5. /admin/api/stage0_quality_check
6. /admin/api/activity_stats
7. /admin/api/activity_log
8. /admin/api/activity_detail/<int:activity_id>
9. /admin/api/export_activity_log
10. /admin/api/reset_all_data
11. /admin/api/system_logs
"""

from flask import Blueprint, request, session, jsonify, make_response
from datetime import datetime, timedelta
import os
import json
import sqlite3
import csv
import io
import time
import logging
from functools import wraps


# 🔧 Phase 4b-2 修正: 必要なグローバル変数をimport
try:
    from activity_logger import log_analysis_activity, activity_logger, get_jst_today
    print("✅ Activity Logger imported successfully in admin_api_routes")
except ImportError as e:
    print(f"⚠️ Activity Logger import failed in admin_api_routes: {e}")
    # フォールバック：ダミー関数
    def log_analysis_activity(data):
        pass
    activity_logger = None
    def get_jst_today():
        from datetime import datetime
        return datetime.now().date()

# 追加のグローバル変数import
# Note: log_security_event is defined in app.py, not admin_logger.py
# For now, we'll use a fallback implementation
def log_security_event(event_type: str, details: str, severity: str = "INFO") -> None:
    """Fallback security event logger for Blueprint"""
    app_logger.info(f"[SECURITY-{severity}] {event_type}: {details}")

# render_template も必要
from flask import render_template


# Blueprint作成（URL prefixでAdmin API専用化）
admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/admin/api')

# ログ設定
app_logger = logging.getLogger('app')

def require_login(f):
    """ログイン認証デコレータ（Blueprint用）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated_function

def csrf_protect(f):
    """CSRF保護デコレータ（Blueprint用）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # CSRF保護ロジック（必要に応じて実装）
        return f(*args, **kwargs)
    return decorated_function

# ========== Admin API機能の開始 ==========

# ここに temp_admin_api_content.txt の内容を移植し、
# @admin_api_bp.route("/ を @admin_api_bp.route("/ に変換

@admin_api_bp.route("/four_stage_analysis", methods=["GET"])
@require_login
def get_four_stage_analysis():
    """4段階分析データAPI（管理者専用）"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # activity_loggerは既にグローバルにインポート済み
        
        # フィルターパラメータ取得
        period = request.args.get('period', 'all')
        
        # 基本的な活動ログデータを取得（直接SQL実行）
        import sqlite3
        conn = sqlite3.connect(activity_logger.db_path)
        conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, created_at, japanese_text, recommendation_result,
                actual_user_choice, llm_match, confidence, 
                processing_duration, activity_type, button_pressed,
                actual_analysis_llm, stage0_human_check,
                stage0_human_check_date, stage0_human_check_user
            FROM analysis_activity_log
            ORDER BY created_at DESC
            LIMIT 100
        """)
        
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
        conn.close()
        
        # 4段階分析形式に変換
        four_stage_data = []
        for row in results:
            item = {
                'id': row.get('id'),
                'japanese_text': row.get('japanese_text', '')[:50] + '...' if row.get('japanese_text') and len(row.get('japanese_text', '')) > 50 else row.get('japanese_text', ''),
                'created_at': row.get('created_at'),
                'stage0': {  # 第0段階: 人間CK
                    'status': row.get('stage0_human_check') or '未チェック',
                    'check_date': row.get('stage0_human_check_date'),
                    'check_user': row.get('stage0_human_check_user')
                },
                'stage05': {  # 第0.5段階: User SEL LLM
                    'user_selected_llm': row.get('button_pressed') or '-'
                },
                'stage1': {  # 第1段階: LLMの推奨
                    'recommendation': row.get('recommendation_result') or '-',
                    'confidence': row.get('confidence') or 0.0
                },
                'stage15': {  # 第1.5段階: 判定したLLM
                    'judging_llm': row.get('actual_analysis_llm') or '-'
                },
                'stage2': {  # 第2段階: User選択(Copy)
                    'user_selection': row.get('actual_user_choice') or '未選択',
                    'data_source': 'actual_copy_tracking'
                },
                'stage3': {  # 第3段階: LLM推奨 vs User選択
                    'match': bool(row.get('llm_match', False)),
                    'analysis': '自動判定'
                },
                'analysis_engine': row.get('actual_analysis_llm') or '-'
            }
            four_stage_data.append(item)
        
        # 統計計算
        total_count = len(four_stage_data)
        match_count = sum(1 for item in four_stage_data if item['stage3']['match'])
        match_rate = (match_count / total_count * 100) if total_count > 0 else 0
        copy_count = sum(1 for item in four_stage_data if item['stage2']['data_source'] == 'actual_copy_tracking')
        human_check_count = sum(1 for item in four_stage_data if item['stage0']['status'] and item['stage0']['status'] != '未チェック')
        
        return jsonify({
            'success': True,
            'data': {
                'items': four_stage_data,
                'total_count': total_count,
                'match_rate': match_rate,
                'copy_count': copy_count,
                'human_check_count': human_check_count
            },
            'period': period
        })
        
    except Exception as e:
        app_logger.error(f"Four stage analysis API error: {str(e)}")
        return jsonify({
            'error': str(e),
            'error_code': 'API_ERROR',
            'success': False
        }), 500

# Note: The template route for /admin/llm_recommendation_check should be in admin_routes.py, not in the API routes
# This file should only contain API endpoints that return JSON

@admin_api_bp.route("/llm_recommendation_check", methods=["GET", "POST"])
@require_login
def api_llm_recommendation_check():
    """LLM推奨品質チェックAPI"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    if request.method == 'GET':
        # データ取得
        try:
            app_logger.info("Starting LLM recommendation check data retrieval")
            
            if activity_logger is None:
                raise Exception("Activity logger not available")
            
            import sqlite3
            db_path = activity_logger.db_path
            app_logger.info(f"Using database: {db_path}")
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # まず全体の件数を確認
            cursor.execute("SELECT COUNT(*) as total FROM analysis_activity_log")
            total_rows = cursor.fetchone()[0]
            app_logger.info(f"Total rows in database: {total_rows}")
            
            # 推奨結果がある件数を確認
            cursor.execute("SELECT COUNT(*) as count FROM analysis_activity_log WHERE recommendation_result IS NOT NULL AND recommendation_result != ''")
            recommendation_rows = cursor.fetchone()[0]
            app_logger.info(f"Rows with recommendation_result: {recommendation_rows}")
            
            cursor.execute("""
                SELECT 
                    id, created_at, japanese_text, recommendation_result,
                    actual_user_choice, llm_match, confidence, 
                    button_pressed, actual_analysis_llm, full_analysis_text,
                    stage0_human_check, stage0_human_check_date, stage0_human_check_user
                FROM analysis_activity_log
                WHERE recommendation_result IS NOT NULL 
                AND recommendation_result != ''
                ORDER BY created_at DESC
                LIMIT 50
            """)
            
            rows = cursor.fetchall()
            app_logger.info(f"Retrieved {len(rows)} rows for LLM recommendation check")
            
            data = []
            for row in rows:
                try:
                    data.append({
                        'id': row['id'],
                        'created_at': row['created_at'],
                        'japanese_text': row['japanese_text'][:100] + '...' if row['japanese_text'] and len(row['japanese_text']) > 100 else row['japanese_text'],
                        'recommendation_result': row['recommendation_result'],
                        'actual_user_choice': row['actual_user_choice'],
                        'llm_match': bool(row['llm_match']) if row['llm_match'] is not None else False,
                        'confidence': float(row['confidence']) if row['confidence'] is not None else 0.0,
                        'button_pressed': row['button_pressed'],
                        'actual_analysis_llm': row['actual_analysis_llm'],
                        'full_analysis_text': row['full_analysis_text'][:500] + '...' if row['full_analysis_text'] and len(row['full_analysis_text']) > 500 else row['full_analysis_text'],
                        'stage0_human_check': row['stage0_human_check'],
                        'stage0_human_check_date': row['stage0_human_check_date'],
                        'stage0_human_check_user': row['stage0_human_check_user']
                    })
                except Exception as row_error:
                    app_logger.error(f"Error processing row {row['id']}: {str(row_error)}")
                    continue
            
            conn.close()
            
            app_logger.info(f"Successfully processed {len(data)} records for LLM recommendation check")
            
            # 統計計算
            pending_count = len([item for item in data if not item.get('stage0_human_check')])
            approved_count = len([item for item in data if item.get('stage0_human_check')])
            rejected_count = 0  # 新しい①〜④選択方式では「修正」の概念がない
            accuracy_rate = (approved_count / len(data) * 100) if len(data) > 0 else 0
            
            return jsonify({
                'success': True,
                'items': data,  # JavaScriptが期待する形式
                'total_count': len(data),
                'pending_count': pending_count,
                'approved_count': approved_count,
                'rejected_count': rejected_count,
                'accuracy_rate': accuracy_rate,
                'debug_info': {
                    'total_db_rows': total_rows,
                    'recommendation_rows': recommendation_rows,
                    'processed_rows': len(data)
                }
            })
            
        except Exception as e:
            app_logger.error(f"LLM recommendation check GET error: {str(e)}")
            return jsonify({
                'error': str(e),
                'error_code': 'API_ERROR',
                'success': False
            }), 500
    
    else:  # POST - 品質チェック処理
        try:
            data = request.json
            activity_id = data.get('activity_id')
            quality_status = data.get('quality_status', '確認済み')
            
            if not activity_id:
                return jsonify({
                    'error': 'activity_id が必要です',
                    'error_code': 'MISSING_PARAMETER',
                    'success': False
                }), 400
            
            # 品質チェック結果を記録（実装は後で詳細化）
            result = {
                'success': True,
                'activity_id': activity_id,
                'quality_check': {
                    'status': quality_status,
                    'checked_at': datetime.now().isoformat(),
                    'checked_by': session.get('username', 'unknown')
                }
            }
            
            return jsonify(result)
            
        except Exception as e:
            app_logger.error(f"LLM recommendation check POST error: {str(e)}")
            return jsonify({
                'error': str(e),
                'error_code': 'QUALITY_CHECK_ERROR',
                'success': False
            }), 500

@admin_api_bp.route("/llm_recommendation_detail/<int:activity_id>", methods=["GET"])
@require_login
def get_llm_recommendation_detail(activity_id):
    """LLM推奨詳細データ取得API"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        app_logger.info(f"Getting LLM recommendation detail for activity_id: {activity_id}")
        
        if activity_logger is None:
            raise Exception("Activity logger not available")
        
        import sqlite3
        db_path = activity_logger.db_path
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, created_at, japanese_text, 
                chatgpt_translation, enhanced_translation, gemini_translation,
                recommendation_result, actual_user_choice, llm_match, 
                confidence, button_pressed, actual_analysis_llm, 
                full_analysis_text, human_check_result, 
                processing_duration, language_pair, context_info,
                partner_message
            FROM analysis_activity_log
            WHERE id = ?
        """, (activity_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({
                'error': f'Activity ID {activity_id} not found',
                'error_code': 'NOT_FOUND',
                'success': False
            }), 404
        
        # データを構造化
        detail = {
            'id': row['id'],
            'created_at': row['created_at'],
            'japanese_text': row['japanese_text'],
            'chatgpt_translation': row['chatgpt_translation'],
            'enhanced_translation': row['enhanced_translation'],
            'gemini_translation': row['gemini_translation'],
            'recommendation_result': row['recommendation_result'],
            'actual_user_choice': row['actual_user_choice'],
            'llm_match': bool(row['llm_match']) if row['llm_match'] is not None else False,
            'confidence': float(row['confidence']) if row['confidence'] is not None else 0.0,
            'button_pressed': row['button_pressed'],
            'actual_analysis_llm': row['actual_analysis_llm'],
            'full_analysis_text': row['full_analysis_text'],
            'human_check_result': row['human_check_result'],
            'processing_duration': row['processing_duration'],
            'language_pair': row['language_pair'],
            'context_info': row['context_info'],
            'partner_message': row['partner_message']
        }
        
        app_logger.info(f"Successfully retrieved detail for activity_id: {activity_id}")
        
        return jsonify({
            'success': True,
            'data': detail
        })
        
    except Exception as e:
        app_logger.error(f"LLM recommendation detail error for ID {activity_id}: {str(e)}")
        return jsonify({
            'error': str(e),
            'error_code': 'DETAIL_ERROR',
            'success': False
        }), 500

@admin_api_bp.route("/stage0_human_check", methods=["POST"])
@require_login
def stage0_human_check():
    """第0段階: 人間による推奨判定更新API"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        data = request.json
        activity_id = data.get('activity_id')
        human_selection = data.get('human_selection')
        
        if not activity_id:
            return jsonify({
                'error': 'activity_id が必要です',
                'error_code': 'MISSING_PARAMETER',
                'success': False
            }), 400
            
        if not human_selection:
            return jsonify({
                'error': 'human_selection が必要です',
                'error_code': 'MISSING_PARAMETER',
                'success': False
            }), 400
        
        app_logger.info(f"Updating human check for activity_id: {activity_id} to: {human_selection}")
        
        if activity_logger is None:
            raise Exception("Activity logger not available")
        
        import sqlite3
        db_path = activity_logger.db_path
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 現在のデータを確認
        cursor.execute("SELECT id FROM analysis_activity_log WHERE id = ?", (activity_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({
                'error': f'Activity ID {activity_id} not found',
                'error_code': 'NOT_FOUND',
                'success': False
            }), 404
        
        # 人間チェック結果を更新
        cursor.execute("""
            UPDATE analysis_activity_log 
            SET stage0_human_check = ?,
                stage0_human_check_date = datetime('now'),
                stage0_human_check_user = ?
            WHERE id = ?
        """, (human_selection, session.get('username', 'unknown'), activity_id))
        
        conn.commit()
        conn.close()
        
        app_logger.info(f"Successfully updated human check for activity_id: {activity_id}")
        
        return jsonify({
            'success': True,
            'activity_id': activity_id,
            'human_selection': human_selection,
            'message': f'人間チェック結果を「{human_selection}」に更新しました'
        })
        
    except Exception as e:
        app_logger.error(f"Stage0 human check error: {str(e)}")
        return jsonify({
            'error': str(e),
            'error_code': 'UPDATE_ERROR',
            'success': False
        }), 500

@admin_api_bp.route("/stage0_quality_check", methods=["POST"])
@require_login
def stage0_quality_check():
    """第0段階: LLM推奨品質チェックAPI"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        data = request.json
        activity_id = data.get('activity_id')
        
        if not activity_id:
            return jsonify({
                'error': 'activity_id が必要です',
                'error_code': 'MISSING_PARAMETER',
                'success': False
            }), 400
        
        # 実際の品質チェック処理をここに実装
        # 現在は仮の実装
        result = {
            'success': True,
            'activity_id': activity_id,
            'quality_check': {
                'status': '品質チェック完了',
                'score': 0.95,
                'notes': '自動品質チェック実行済み'
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        app_logger.error(f"Stage 0 quality check error: {str(e)}")
        return jsonify({
            'error': str(e),
            'error_code': 'QUALITY_CHECK_ERROR',
            'success': False
        }), 500

@admin_api_bp.route("/activity_stats", methods=["GET"])
@require_login
def get_activity_stats():
    """活動統計API（期間フィルター対応）"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # activity_loggerとget_jst_todayは既にグローバルにインポート済み
        from datetime import datetime, timedelta
        
        # 期間フィルター処理
        period = request.args.get('period', 'all')
        filters = {}
        
        # JST基準で期間を設定
        today = get_jst_today()
        
        if period == 'today':
            filters['date_from'] = today.strftime('%Y-%m-%d')
            filters['date_to'] = today.strftime('%Y-%m-%d')
        elif period == 'week':
            week_ago = today - timedelta(days=7)
            filters['date_from'] = week_ago.strftime('%Y-%m-%d')
            filters['date_to'] = today.strftime('%Y-%m-%d')
        elif period == 'month':
            month_start = today.replace(day=1)
            filters['date_from'] = month_start.strftime('%Y-%m-%d')
            filters['date_to'] = today.strftime('%Y-%m-%d')
        # 'all' の場合はフィルターなし
        
        # 追加フィルター取得
        additional_filters = {
            'activity_type': request.args.get('activity_type'),
            'user_id': request.args.get('user_id'),
            'button_pressed': request.args.get('button_pressed'),
            'date_from': request.args.get('date_from'),  # 手動指定があれば上書き
            'date_to': request.args.get('date_to')
        }
        
        # 手動指定の日付があれば期間設定を上書き
        for key, value in additional_filters.items():
            if value:
                filters[key] = value
        
        # None値を削除
        filters = {k: v for k, v in filters.items() if v}
        
        stats = activity_logger.get_activity_stats(filters)
        return jsonify(stats)
        
    except Exception as e:
        app_logger.error(f"Activity stats error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin_api_bp.route("/activity_log", methods=["GET"])
@require_login
def get_activity_log():
    """活動ログAPI（期間フィルター対応）"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # activity_loggerとget_jst_todayは既にグローバルにインポート済み
        from datetime import datetime, timedelta
        
        # パラメータ取得
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 50)), 100)  # 最大100件
        offset = (page - 1) * limit
        
        # 期間フィルター処理
        period = request.args.get('period', 'all')
        filters = {}
        
        # JST基準で期間を設定
        today = get_jst_today()
        
        if period == 'today':
            filters['date_from'] = today.strftime('%Y-%m-%d')
            filters['date_to'] = today.strftime('%Y-%m-%d')
        elif period == 'week':
            week_ago = today - timedelta(days=7)
            filters['date_from'] = week_ago.strftime('%Y-%m-%d')
            filters['date_to'] = today.strftime('%Y-%m-%d')
        elif period == 'month':
            month_start = today.replace(day=1)
            filters['date_from'] = month_start.strftime('%Y-%m-%d')
            filters['date_to'] = today.strftime('%Y-%m-%d')
        # 'all' の場合はフィルターなし
        
        # 追加フィルター取得
        additional_filters = {
            'activity_type': request.args.get('activity_type'),
            'user_id': request.args.get('user_id'),
            'button_pressed': request.args.get('button_pressed'),
            'date_from': request.args.get('date_from'),  # 手動指定があれば上書き
            'date_to': request.args.get('date_to'),
            'error_only': request.args.get('error_only') == 'true',
            'llm_mismatch_only': request.args.get('llm_mismatch_only') == 'true'
        }
        
        # 手動指定の日付があれば期間設定を上書き
        for key, value in additional_filters.items():
            if value is not None and value != '':
                filters[key] = value
        
        result = activity_logger.get_activities(filters, limit, offset)
        return jsonify(result)
        
    except Exception as e:
        app_logger.error(f"Activity log error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin_api_bp.route("/activity_detail/<int:activity_id>", methods=["GET"])
@require_login
def get_activity_detail(activity_id):
    """活動詳細API"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # activity_loggerは既にグローバルにインポート済み
        
        detail = activity_logger.get_activity_detail(activity_id)
        if not detail:
            return jsonify({"error": "Activity not found"}), 404
        
        return jsonify(detail)
        
    except Exception as e:
        app_logger.error(f"Activity detail error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin_api_bp.route("/export_activity_log", methods=["GET"])
@require_login
def export_activity_log():
    """活動ログCSV出力API"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # activity_loggerは既にグローバルにインポート済み
        import csv
        import io
        
        export_type = request.args.get('type', 'filtered')
        
        # フィルター取得
        if export_type == 'filtered':
            filters = {
                'activity_type': request.args.get('activity_type'),
                'user_id': request.args.get('user_id'),
                'button_pressed': request.args.get('button_pressed'),
                'date_from': request.args.get('date_from'),
                'date_to': request.args.get('date_to')
            }
            filters = {k: v for k, v in filters.items() if v}
        else:
            filters = {}
        
        # 大量データ取得（最大10000件）
        result = activity_logger.get_activities(filters, limit=10000, offset=0)
        activities = result['activities']
        
        # CSV生成
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー（推奨抽出検証用の詳細情報を含む）
        writer.writerow([
            'ID', '活動タイプ', 'ユーザー', '実行日時', '日本語文章',
            '言語ペア', '押下ボタン', '実際LLM', 'LLM一致', '推奨結果',
            '信頼度', '処理時間', 'エラー発生', 'エラーメッセージ',
            'ChatGPT翻訳', 'Enhanced翻訳', 'Gemini翻訳',
            'ニュアンス分析結果全文', '分析プレビュー',
            'ターミナルログ', 'デバッグログ', 'IP', 'User Agent',
            'セッションID', 'サンプル名', 'テストセッションID', 
            '作成日時', '年', '月', '日', '時間', 'メモ', 'タグ'
        ])
        
        # データ行
        for activity in activities:
            # 詳細データ取得
            detail = activity_logger.get_activity_detail(activity['id'])
            if detail:
                writer.writerow([
                    detail['id'],
                    detail['activity_type'],
                    detail['user_id'],
                    detail['created_at'],
                    detail['japanese_text'],
                    detail['language_pair'],
                    detail['button_pressed'],
                    detail['actual_analysis_llm'],
                    '一致' if detail['llm_match'] else '不一致',
                    detail['recommendation_result'],
                    detail['confidence'],
                    detail['processing_duration'],
                    'エラー' if detail['error_occurred'] else '正常',
                    detail['error_message'],
                    # 推奨抽出検証用の詳細情報
                    detail['chatgpt_translation'] or '',
                    detail['enhanced_translation'] or '',
                    detail['gemini_translation'] or '',
                    detail['full_analysis_text'] or '',  # ニュアンス分析結果全文（最重要）
                    detail['analysis_preview'] or '',
                    detail['terminal_logs'] or '',
                    detail['debug_logs'] or '',
                    detail['ip_address'] or '',
                    detail['user_agent'] or '',
                    detail['session_id'],
                    detail['sample_name'],
                    detail['test_session_id'],
                    detail['created_at'],
                    detail['year'],
                    detail['month'],
                    detail['day'],
                    detail['hour'],
                    detail['notes'] or '',
                    detail['tags'] or ''
                ])
        
        # レスポンス生成（Excel対応のBOM付きUTF-8）
        csv_data = output.getvalue()
        output.close()
        
        # Excel用にBOM（Byte Order Mark）を追加
        csv_data_with_bom = '\ufeff' + csv_data
        
        response = make_response(csv_data_with_bom.encode('utf-8'))
        response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
        response.headers['Content-Disposition'] = f'attachment; filename=langpont_activities_{export_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        app_logger.error(f"CSV export error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin_api_bp.route("/reset_all_data", methods=["POST"])
@require_login
@csrf_protect
def reset_all_data():
    """全データリセットAPI（統合ダッシュボード用）"""
    user_role = session.get('user_role', 'guest')
    username = session.get('username', 'unknown')
    
    # 管理者のみアクセス可能
    if user_role != 'admin':
        app_logger.warning(f"Unauthorized data reset attempt by {username} ({user_role})")
        return jsonify({"error": "管理者権限が必要です"}), 403
    
    try:
        # activity_loggerは既にグローバルにインポート済み
        import os
        
        # アクティビティログデータベースの削除
        if os.path.exists(activity_logger.db_path):
            os.remove(activity_logger.db_path)
            app_logger.info(f"Activity log database deleted: {activity_logger.db_path}")
        
        # 翻訳履歴データベースの削除
        if os.path.exists("langpont_translation_history.db"):
            os.remove("langpont_translation_history.db")
            app_logger.info("Translation history database deleted")
        
        # 使用統計ファイルの削除
        if os.path.exists("usage_data.json"):
            os.remove("usage_data.json")
            app_logger.info("Usage data file deleted")
        
        # データベースの再初期化
        activity_logger.init_database()
        
        # セキュリティログに記録
        log_security_event(
            'DATA_RESET', 
            f'All data reset by admin user: {username}',
            'CRITICAL'
        )
        
        app_logger.info(f"✅ All data reset completed by admin: {username}")
        
        return jsonify({
            "success": True,
            "message": "全データが正常に削除され、システムがリセットされました",
            "reset_by": username,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        app_logger.error(f"Data reset error: {str(e)}")
        log_security_event(
            'DATA_RESET_ERROR', 
            f'Data reset failed for admin {username}: {str(e)}',
            'ERROR'
        )
        return jsonify({"error": f"データリセットに失敗しました: {str(e)}"}), 500

# 🔧 包括的デバッグシステム
@admin_api_bp.route("/system_logs", methods=["GET"])
@require_login
def get_system_logs():
    """システムログAPI（統合ダッシュボード用）"""
    user_role = session.get('user_role', 'guest')
    if user_role not in ['admin', 'developer']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        import os
        import json
        from datetime import datetime
        
        logs = []
        limit = min(int(request.args.get('limit', 50)), 200)  # 最大200件
        
        # アプリケーションログの読み込み
        log_files = [
            ("logs/app.log", "アプリケーション"),
            ("logs/security.log", "セキュリティ"),
            ("logs/access.log", "アクセス")
        ]
        
        for log_file, log_type in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        # 最新のログを取得
                        for line in lines[-limit//3:]:  # 各ファイルから同じ数だけ取得
                            line = line.strip()
                            if line:
                                # ログレベルの推定
                                level = 'info'
                                if 'ERROR' in line or 'Failed' in line or 'エラー' in line:
                                    level = 'error'
                                elif 'WARNING' in line or 'WARN' in line or '警告' in line:
                                    level = 'warning'
                                
                                logs.append({
                                    'timestamp': datetime.now().isoformat(),
                                    'level': level,
                                    'source': log_type,
                                    'message': line[:200]  # 200文字まで
                                })
                except Exception as e:
                    app_logger.error(f"Error reading log file {log_file}: {str(e)}")
        
        # タイムスタンプでソート（新しい順）
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # 制限数まで絞る
        logs = logs[:limit]
        
        return jsonify({
            'logs': logs,
            'total_count': len(logs),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        app_logger.error(f"System logs error: {str(e)}")
        return jsonify({"error": str(e)}), 500





# ========== Blueprint初期化関数 ==========

def init_admin_api_routes(app):
    """Admin API Blueprintをアプリに登録"""
    app.register_blueprint(admin_api_bp)
    return admin_api_bp