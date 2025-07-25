"""
debug_routes.py
デバッグ機能専用Blueprint

分割されたルート:
- /debug-info
- /debug/session  
- /debug/full
- /debug/routes
- /debug/test-admin
"""

from flask import Blueprint, request, session, jsonify, render_template, current_app
import json
import os
import sys

# Blueprint作成
debug_bp = Blueprint('debug', __name__, url_prefix='/debug')

# =============================================================================
# 🔧 Phase 1で分割済みの既存ルート
# =============================================================================

@debug_bp.route('/info')
def debug_info():
    """基本的なデバッグ情報を表示"""
    debug_data = {
        'app_name': 'LangPont',
        'debug_mode': current_app.debug,
        'environment': os.environ.get('FLASK_ENV', 'production'),
        'python_version': sys.version,
        'session_data': dict(session),
        'request_method': request.method,
        'request_url': request.url,
        'user_agent': request.headers.get('User-Agent', 'Unknown')
    }
    
    return jsonify(debug_data)

# =============================================================================
# 🆕 Phase 3aで新規追加のルート
# =============================================================================

@debug_bp.route('/session')
def debug_session():
    """デバッグ用: 現在のセッション状態を表示"""
    try:
        from admin_auth import admin_auth_manager
        
        session_data = dict(session)
        user_info = admin_auth_manager.get_current_user_info()
        
        debug_info = {
            "session_data": session_data,
            "user_info": user_info,
            "has_admin_access": admin_auth_manager.has_admin_access(),
            "logged_in": session.get('logged_in', False),
            "user_role": session.get('user_role', 'none'),
            "username": session.get('username', 'none')
        }
        
        return f"<pre>{json.dumps(debug_info, indent=2, ensure_ascii=False)}</pre>"
    except Exception as e:
        return f"<pre>セッションデバッグエラー: {str(e)}</pre>"

@debug_bp.route('/full')
def debug_full():
    """完全なデバッグ情報を表示"""
    try:
        from admin_auth import admin_auth_manager
        
        # 1. ユーザー権限確認
        permission_check = {
            'logged_in': session.get('logged_in', False),
            'user_role': session.get('user_role', 'none'),
            'has_admin_access': admin_auth_manager.has_admin_access(),
            'is_admin_role': session.get('user_role', 'none') in ['admin', 'developer']
        }
        
        # 2. ルート情報
        routes = []
        for rule in current_app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'rule': rule.rule
            })
        
        admin_routes = [r for r in routes if 'admin' in r['endpoint']]
        
        # 3. Blueprint情報
        blueprints = {}
        for name, bp in current_app.blueprints.items():
            blueprints[name] = {
                'name': bp.name,
                'url_prefix': bp.url_prefix,
                'import_name': bp.import_name
            }
        
        # 4. テンプレート確認
        template_exists = {}
        template_paths = [
            'admin/dashboard.html',
            'index.html',
            'login.html'
        ]
        
        for template in template_paths:
            full_path = os.path.join('templates', template)
            template_exists[template] = os.path.exists(full_path)
        
        # 5. 完全デバッグレポート
        debug_report = {
            'permission_check': permission_check,
            'total_routes': len(routes),
            'admin_routes_count': len(admin_routes),
            'blueprints': blueprints,
            'template_exists': template_exists,
            'environment': {
                'debug_mode': current_app.debug,
                'testing': current_app.testing,
                'python_version': sys.version,
                'flask_env': os.environ.get('FLASK_ENV', 'production')
            }
        }
        
        # HTML生成
        html = f"""
        <!DOCTYPE html>
        <html><head><title>Complete Debug Report</title>
        <style>
            body {{ font-family: monospace; margin: 20px; background-color: #f8f9fa; }}
            .section {{ margin: 20px 0; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .good {{ color: #28a745; font-weight: bold; }}
            .bad {{ color: #dc3545; font-weight: bold; }}
            h1 {{ color: #333; }}
            h2 {{ color: #666; border-bottom: 2px solid #eee; padding-bottom: 5px; }}
            pre {{ background: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto; }}
            ul {{ margin: 0; padding-left: 20px; }}
            li {{ margin: 5px 0; }}
        </style></head>
        <body>
        <h1>🔍 LangPont 完全デバッグレポート</h1>
        
        <div class="section">
            <h2>🔐 ログイン状態チェック</h2>
            <p>ログイン済み: <span class="{'good' if permission_check['logged_in'] else 'bad'}">{permission_check['logged_in']}</span></p>
            <p>ユーザーロール: <span class="{'good' if permission_check['user_role'] != 'none' else 'bad'}">{permission_check['user_role']}</span></p>
            <p>管理者アクセス権: <span class="{'good' if permission_check['has_admin_access'] else 'bad'}">{permission_check['has_admin_access']}</span></p>
            <p>管理者ロール判定: <span class="{'good' if permission_check['is_admin_role'] else 'bad'}">{permission_check['is_admin_role']}</span></p>
        </div>
        
        <div class="section">
            <h2>🗺️ 管理者ルート状況</h2>
            <p>管理者ルート数: <span class="{'good' if len(admin_routes) > 0 else 'bad'}">{len(admin_routes)}</span></p>
            <ul>
        """
        
        for route in admin_routes:
            html += f"<li><strong>{route['endpoint']}</strong>: {route['rule']} {route['methods']}</li>"
        
        html += f"""
            </ul>
        </div>
        
        <div class="section">
            <h2>📄 テンプレート状況</h2>
            <ul>
        """
        
        for template, exists in template_exists.items():
            status_class = 'good' if exists else 'bad'
            status_text = '✅ 存在' if exists else '❌ 不存在'
            html += f"<li><span class='{status_class}'>{template}: {status_text}</span></li>"
        
        html += f"""
            </ul>
        </div>
        
        <div class="section">
            <h2>📦 Blueprint状況</h2>
            <ul>
        """
        
        for name, info in blueprints.items():
            html += f"<li><strong>{name}</strong>: {info['url_prefix']} ({info['import_name']})</li>"
        
        html += f"""
            </ul>
        </div>
        
        <div class="section">
            <h2>📋 完全デバッグデータ</h2>
            <pre>{json.dumps(debug_report, indent=2, ensure_ascii=False)}</pre>
        </div>
        
        </body></html>
        """
        
        return html
    except Exception as e:
        return f"<h1>デバッグエラー</h1><pre>{str(e)}</pre>"

@debug_bp.route('/routes')
def debug_routes():
    """🗺️ 全ルート一覧"""
    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': sorted(list(rule.methods - {'HEAD', 'OPTIONS'})),
            'rule': rule.rule
        })
    
    routes.sort(key=lambda x: x['rule'])
    
    html = """
    <!DOCTYPE html>
    <html><head><title>LangPont Routes</title>
    <style>
        body { font-family: monospace; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .admin-route { background-color: #fff3cd; }
        .auth-route { background-color: #d1ecf1; }
    </style></head>
    <body>
    <h1>🗺️ LangPont 全ルート一覧</h1>
    <table>
    <tr><th>エンドポイント</th><th>メソッド</th><th>パス</th></tr>
    """
    
    for route in routes:
        row_class = ""
        if 'admin' in route['endpoint']:
            row_class = "admin-route"
        elif 'auth' in route['endpoint']:
            row_class = "auth-route"
        
        html += f"""
        <tr class="{row_class}">
            <td>{route['endpoint']}</td>
            <td>{', '.join(route['methods'])}</td>
            <td>{route['rule']}</td>
        </tr>
        """
    
    html += "</table></body></html>"
    return html

@debug_bp.route('/test-admin')
def debug_test_admin():
    """🧪 管理者アクセステスト"""
    try:
        from admin_auth import admin_auth_manager
        
        # ステップバイステップのテスト
        test_results = []
        
        # Step 1: セッション確認
        logged_in = session.get('logged_in', False)
        test_results.append(f"✅ Step 1: ログイン状態 = {logged_in}" if logged_in else f"❌ Step 1: ログイン状態 = {logged_in}")
        
        # Step 2: ユーザーロール確認
        user_role = session.get('user_role', 'none')
        is_admin_role = user_role in ['admin', 'developer']
        test_results.append(f"✅ Step 2: ユーザーロール = {user_role}" if is_admin_role else f"❌ Step 2: ユーザーロール = {user_role}")
        
        # Step 3: AdminAuthManager確認
        try:
            has_admin_access = admin_auth_manager.has_admin_access()
            test_results.append(f"✅ Step 3: has_admin_access() = {has_admin_access}" if has_admin_access else f"❌ Step 3: has_admin_access() = {has_admin_access}")
        except Exception as e:
            test_results.append(f"❌ Step 3: AdminAuthManager エラー = {str(e)}")
        
        # Step 4: ルート存在確認
        admin_dashboard_exists = any(rule.endpoint == 'admin.dashboard' for rule in current_app.url_map.iter_rules())
        test_results.append(f"✅ Step 4: admin.dashboard ルート存在 = {admin_dashboard_exists}" if admin_dashboard_exists else f"❌ Step 4: admin.dashboard ルート存在 = {admin_dashboard_exists}")
        
        # Step 5: テンプレート存在確認
        template_exists = os.path.exists('templates/admin/dashboard.html')
        test_results.append(f"✅ Step 5: dashboard.html テンプレート存在 = {template_exists}" if template_exists else f"❌ Step 5: dashboard.html テンプレート存在 = {template_exists}")
        
        # Step 6: リダイレクトテスト
        redirect_test = "pending"
        try:
            # 簡単なリダイレクトテスト
            redirect_test = "success"
        except Exception as e:
            test_results.append(f"❌ Step 6: テストエラー = {str(e)}")
            redirect_test = "error"
        
        html = f"""
        <!DOCTYPE html>
        <html><head><title>Admin Access Test</title>
        <style>
            body {{ font-family: monospace; margin: 20px; }}
            .success {{ color: #28a745; }}
            .error {{ color: #dc3545; }}
            .test-item {{ padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 4px; }}
            .actions {{ margin: 20px 0; }}
            .actions a {{ display: inline-block; margin: 5px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
        </style></head>
        <body>
        <h1>🧪 管理者アクセステスト結果</h1>
        
        <div class="actions">
            <a href="/debug/full">完全デバッグ</a>
            <a href="/debug/session">セッション情報</a>
            <a href="/debug/routes">ルート一覧</a>
        </div>
        
        <h2>📋 テスト結果:</h2>
        """
        
        for result in test_results:
            result_class = "success" if "✅" in result else "error"
            html += f'<div class="test-item {result_class}">{result}</div>'
        
        html += """
        </body></html>
        """
        
        return html
    except Exception as e:
        return f"<h1>テストエラー</h1><pre>{str(e)}</pre>"

# =============================================================================
# 🔧 Blueprint初期化関数
# =============================================================================

def init_debug_routes(app):
    """デバッグルートをアプリケーションに登録"""
    app.register_blueprint(debug_bp)
    return debug_bp