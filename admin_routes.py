#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🚀 Task 2.9.2 Phase B-1: 管理者専用ルート構築
================================================================
目的: admin/developer権限のみアクセス可能な管理者専用ダッシュボード
機能: システム監視、ユーザー管理、ログ表示、データ分析
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

# 管理者権限システム
from admin_auth import require_admin_access, require_permission, admin_auth_manager
from admin_logger import admin_logger, log_translation_event, log_gemini_analysis, log_api_call, log_error

# ユーザー認証システム（既存）
try:
    from user_auth import UserAuthSystem
    user_auth_system = UserAuthSystem()
except ImportError:
    user_auth_system = None

# Blueprintの作成
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@require_admin_access
def dashboard():
    """管理者ダッシュボードメイン画面"""
    try:
        # 現在のユーザー情報取得
        user_info = admin_auth_manager.get_current_user_info()
        
        # システム統計取得
        system_stats = admin_logger.get_system_stats()
        
        # 最新ログ取得
        recent_logs = admin_logger.get_recent_logs(20)
        
        # エラーサマリー取得
        error_summary = admin_logger.get_error_summary(24)
        
        # 翻訳分析データ取得
        translation_analytics = admin_logger.get_translation_analytics(7)
        
        # ダッシュボードアクセスをログ
        admin_auth_manager.log_admin_access(
            action="dashboard_accessed",
            details=f"User: {user_info['username']} ({user_info['role']})"
        )
        
        dashboard_data = {
            'user_info': user_info,
            'system_stats': system_stats,
            'recent_logs': recent_logs,
            'error_summary': error_summary,
            'translation_analytics': translation_analytics,
            'page_title': 'LangPont 管理者ダッシュボード',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return render_template('admin/dashboard.html', **dashboard_data)
        
    except Exception as e:
        log_error("dashboard_error", str(e), user_info.get('username'))
        flash(f'ダッシュボード読み込みエラー: {str(e)}', 'error')
        return redirect(url_for('index'))


@admin_bp.route('/api/system_stats')
@require_admin_access
def api_system_stats():
    """システム統計API（リアルタイム更新用）"""
    try:
        stats = admin_logger.get_system_stats()
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/recent_logs')
@require_admin_access
def api_recent_logs():
    """最新ログAPI"""
    try:
        limit = request.args.get('limit', 50, type=int)
        category = request.args.get('category', None)
        
        logs = admin_logger.get_recent_logs(limit, category)
        
        return jsonify({
            'success': True,
            'data': logs,
            'count': len(logs),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/error_summary')
@require_admin_access
def api_error_summary():
    """エラーサマリーAPI"""
    try:
        hours = request.args.get('hours', 24, type=int)
        error_summary = admin_logger.get_error_summary(hours)
        
        return jsonify({
            'success': True,
            'data': error_summary,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/users')
@require_permission('user_management')
def users():
    """ユーザー管理画面"""
    try:
        user_info = admin_auth_manager.get_current_user_info()
        
        # ユーザー一覧取得（UserAuthSystemを使用）
        users_data = []
        if user_auth_system:
            users_data = user_auth_system.get_all_users()
        
        # 管理者用設定から既存ユーザー情報も取得
        from config import USERS
        existing_users = []
        for username, user_data in USERS.items():
            existing_users.append({
                'username': username,
                'role': user_data['role'],
                'daily_limit': user_data['daily_limit'],
                'description': user_data['description'],
                'source': 'config'
            })
        
        # ユーザー管理アクセスをログ
        admin_auth_manager.log_admin_access(
            action="user_management_accessed",
            details=f"User: {user_info['username']}"
        )
        
        return render_template('admin/users.html',
                             user_info=user_info,
                             users_data=users_data,
                             existing_users=existing_users,
                             page_title='ユーザー管理')
        
    except Exception as e:
        log_error("user_management_error", str(e), user_info.get('username'))
        flash(f'ユーザー管理画面エラー: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/logs')
@require_admin_access
def logs():
    """ログ表示画面"""
    try:
        user_info = admin_auth_manager.get_current_user_info()
        
        # フィルタパラメータ取得
        category = request.args.get('category', 'all')
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        # ログ取得
        if category == 'all':
            logs = admin_logger.get_recent_logs(limit)
        else:
            logs = admin_logger.get_recent_logs(limit, category)
        
        # カテゴリ統計
        category_stats = {}
        for log in logs:
            cat = log['category']
            category_stats[cat] = category_stats.get(cat, 0) + 1
        
        # ログアクセスをログ
        admin_auth_manager.log_admin_access(
            action="logs_accessed",
            details=f"Category: {category}, Hours: {hours}, Limit: {limit}"
        )
        
        return render_template('admin/logs.html',
                             user_info=user_info,
                             logs=logs,
                             category=category,
                             hours=hours,
                             limit=limit,
                             category_stats=category_stats,
                             page_title='システムログ')
        
    except Exception as e:
        log_error("logs_view_error", str(e), user_info.get('username'))
        flash(f'ログ表示エラー: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/analytics')
@require_admin_access
def analytics():
    """データ分析画面"""
    try:
        user_info = admin_auth_manager.get_current_user_info()
        
        # 分析期間取得
        days = request.args.get('days', 7, type=int)
        
        # 翻訳分析データ取得
        translation_analytics = admin_logger.get_translation_analytics(days)
        
        # システム統計取得
        system_stats = admin_logger.get_system_stats()
        
        # パフォーマンス統計
        performance_data = {
            'avg_response_time': system_stats.get('avg_response_time', 0),
            'total_api_calls': system_stats.get('total_api_calls', 0),
            'success_rate': calculate_success_rate(),
            'gemini_recommendations': system_stats.get('gemini_recommendations', {})
        }
        
        # 分析アクセスをログ
        admin_auth_manager.log_admin_access(
            action="analytics_accessed",
            details=f"Analysis period: {days} days"
        )
        
        return render_template('admin/analytics.html',
                             user_info=user_info,
                             translation_analytics=translation_analytics,
                             system_stats=system_stats,
                             performance_data=performance_data,
                             days=days,
                             page_title='データ分析')
        
    except Exception as e:
        log_error("analytics_error", str(e), user_info.get('username'))
        flash(f'分析画面エラー: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/task292-monitor')
@require_admin_access
def task292_monitor():
    """🚀 Phase B-2: Task 2.9.2 専用監視ダッシュボード"""
    try:
        user_info = admin_auth_manager.get_current_user_info()
        
        # 高度な分析システムからデータ取得
        from admin_dashboard import advanced_analytics
        
        # Task 2.9.2 メトリクス取得
        task292_metrics = advanced_analytics.get_task292_metrics()
        
        # API統計取得
        api_stats = advanced_analytics.get_api_statistics()
        
        # アクティブアラート取得
        active_alerts = advanced_analytics.get_active_alerts()
        
        # 抽出履歴取得
        extraction_history = advanced_analytics.get_extraction_history(hours=6, limit=20)
        
        # アクセスログ記録
        admin_auth_manager.log_admin_access(
            action="task292_monitor_accessed",
            details=f"User: {user_info['username']} ({user_info['role']})"
        )
        
        dashboard_data = {
            'user_info': user_info,
            'task292_metrics': task292_metrics,
            'api_stats': api_stats,
            'active_alerts': active_alerts,
            'extraction_history': extraction_history,
            'page_title': 'Task 2.9.2 専用監視',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return render_template('admin/task292_monitor.html', **dashboard_data)
        
    except Exception as e:
        log_error("task292_monitor_error", str(e), user_info.get('username'))
        flash(f'Task 2.9.2 監視画面エラー: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/api/task292_metrics')
@require_admin_access
def api_task292_metrics():
    """Task 2.9.2 メトリクスAPI（リアルタイム更新用）"""
    try:
        from admin_dashboard import advanced_analytics
        
        metrics = advanced_analytics.get_task292_metrics()
        api_stats = advanced_analytics.get_api_statistics()
        alerts = advanced_analytics.get_active_alerts()
        
        return jsonify({
            'success': True,
            'data': {
                'task292_metrics': metrics,
                'api_stats': api_stats,
                'active_alerts': alerts,
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/task292_extraction_log')
@require_admin_access
def api_task292_extraction_log():
    """Task 2.9.2 抽出ログAPI"""
    try:
        from admin_dashboard import advanced_analytics
        
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 100, type=int)
        format_type = request.args.get('format', 'json')
        
        logs = advanced_analytics.get_extraction_history(hours, limit)
        
        if format_type == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=['timestamp', 'user_id', 'analysis_language', 
                                                       'extraction_method', 'recommendation', 
                                                       'confidence', 'processing_time_ms', 'success'])
            writer.writeheader()
            writer.writerows(logs)
            
            response = output.getvalue()
            output.close()
            
            return response, 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename=task292_extraction_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        
        return jsonify({
            'success': True,
            'data': logs,
            'count': len(logs),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/task292_diagnostics', methods=['POST'])
@require_admin_access
def api_task292_diagnostics():
    """Task 2.9.2 システム診断API"""
    try:
        from admin_dashboard import advanced_analytics
        
        # 診断実行
        diagnostics = []
        
        # 1. メトリクス整合性チェック
        metrics = advanced_analytics.get_task292_metrics()
        if metrics['total_extractions'] > 0:
            success_rate = metrics['success_rate']
            if success_rate < 70:
                diagnostics.append(f"⚠️ 成功率が低下: {success_rate:.1f}%")
            else:
                diagnostics.append(f"✅ 成功率正常: {success_rate:.1f}%")
        
        # 2. API応答時間チェック
        api_stats = advanced_analytics.get_api_statistics()
        for provider, stats in api_stats.items():
            avg_time = stats.get('average_response_time', 0)
            if avg_time > 3000:
                diagnostics.append(f"⚠️ {provider} API応答時間遅延: {avg_time:.0f}ms")
            else:
                diagnostics.append(f"✅ {provider} API応答時間正常: {avg_time:.0f}ms")
        
        # 3. アラート状況チェック
        alerts = advanced_analytics.get_active_alerts()
        critical_alerts = [a for a in alerts if a['severity'] == 'CRITICAL']
        if critical_alerts:
            diagnostics.append(f"🚨 重要アラート {len(critical_alerts)} 件")
        else:
            diagnostics.append("✅ 重要アラートなし")
        
        # 4. データベース整合性チェック
        try:
            extraction_logs = advanced_analytics.get_extraction_history(hours=1, limit=10)
            diagnostics.append(f"✅ データベース接続正常: 直近1時間で {len(extraction_logs)} 件のログ")
        except Exception as db_error:
            diagnostics.append(f"❌ データベース接続エラー: {str(db_error)}")
        
        # アクセスログ記録
        user_info = admin_auth_manager.get_current_user_info()
        admin_auth_manager.log_admin_access(
            action="task292_diagnostics_run",
            details=f"Diagnostics executed by {user_info['username']}"
        )
        
        return jsonify({
            'success': True,
            'message': f'診断完了: {len(diagnostics)} 項目をチェック',
            'details': diagnostics,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/test_log', methods=['POST'])
@require_admin_access
def api_test_log():
    """テストログ生成API（開発・デバッグ用）"""
    try:
        user_info = admin_auth_manager.get_current_user_info()
        
        # テストログ生成
        log_translation_event("test_user", "ja-en", True, 1200)
        log_gemini_analysis("test_user", "chatgpt", 0.92, "llm_chatgpt_a9")
        log_api_call("openai", True, 850, "Test API call")
        
        # 🚀 Phase B-2: Task 2.9.2 テストデータ生成
        from admin_dashboard import advanced_analytics
        
        # Task 2.9.2 抽出テストログ
        advanced_analytics.log_task292_extraction(
            session_id="test_session",
            user_id=user_info['username'],
            input_text="これはテスト用の推奨抽出です。",
            analysis_language="Japanese",
            method="llm_chatgpt_a8",
            recommendation="enhanced",
            confidence=0.95,
            processing_time_ms=1200,
            success=True,
            metadata={'test': True, 'generated_by': 'admin_test'}
        )
        
        # API監視テストログ
        advanced_analytics.log_api_call(
            api_provider="openai",
            endpoint="/v1/chat/completions",
            method="POST",
            status_code=200,
            response_time_ms=850,
            success=True,
            metadata={'test': True}
        )
        
        admin_auth_manager.log_admin_access(
            action="test_logs_generated",
            details="Generated test logs for debugging including Task 2.9.2 data"
        )
        
        return jsonify({
            'success': True,
            'message': 'テストログを生成しました（Task 2.9.2 データ含む）',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def calculate_success_rate() -> float:
    """成功率を計算"""
    try:
        stats = admin_logger.get_system_stats()
        total_operations = stats.get('total_translations', 0) + stats.get('total_api_calls', 0)
        errors = stats.get('error_count', 0)
        
        if total_operations == 0:
            return 100.0
        
        success_rate = ((total_operations - errors) / total_operations) * 100
        return round(success_rate, 2)
        
    except:
        return 0.0


def init_admin_routes(app):
    """管理者ルートをFlaskアプリに登録"""
    try:
        app.register_blueprint(admin_bp)
        
        # 管理者ダッシュボードへのリダイレクト
        @app.route('/admin')
        @require_admin_access
        def admin_redirect():
            return redirect(url_for('admin.dashboard'))
        
        # ナビゲーション用ヘルパー
        @app.context_processor
        def inject_admin_helpers():
            def is_admin_user():
                return admin_auth_manager.has_admin_access()
            
            def has_permission(permission):
                return admin_auth_manager.has_permission(permission)
            
            return dict(
                is_admin_user=is_admin_user,
                has_permission=has_permission,
                admin_user_info=admin_auth_manager.get_current_user_info
            )
        
        print("✅ 管理者ルート登録完了")
        
    except Exception as e:
        print(f"❌ 管理者ルート登録エラー: {str(e)}")


# テスト関数
def test_admin_routes():
    """管理者ルートのテスト"""
    print("🧪 管理者ルートテスト開始")
    print("=" * 60)
    
    # Blueprintテスト
    print(f"📝 Admin Blueprint: {admin_bp.name}")
    print(f"📝 URL Prefix: {admin_bp.url_prefix}")
    
    # ルート一覧
    print("📝 登録ルート:")
    for rule in admin_bp.url_map.iter_rules():
        print(f"   {rule.rule} [{', '.join(rule.methods)}]")
    
    print("\n✅ 管理者ルートテスト完了")


if __name__ == "__main__":
    test_admin_routes()