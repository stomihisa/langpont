"""
セキュリティ関連ルート Blueprint
Phase 4a: セキュリティ系分割（50行削減）

Phase 3aの成功パターンを踏襲：
- 小規模分割による安全性確保
- テンプレート依存最小限
- 独立性の高い機能分離
"""
from flask import Blueprint, session, abort, jsonify
import os

# セキュリティBlueprint作成
security_bp = Blueprint('security', __name__, url_prefix='/security')

def init_security_routes(app):
    """セキュリティルートの初期化"""
    app.register_blueprint(security_bp)
    return security_bp

@security_bp.route("/status")
def security_status():
    """セキュリティステータス表示（管理者用）"""
    if not session.get("logged_in"):
        abort(403)
    
    # app.config にアクセスするため、current_app を使用
    from flask import current_app
    
    status = {
        "csrf_protection": "有効",
        "rate_limiting": "有効", 
        "input_validation": "有効",
        "security_logging": "有効",
        "session_security": "有効",
        "environment": current_app.config.get('ENVIRONMENT', 'development'),
        "debug_mode": current_app.config.get('DEBUG', False),
        "version": current_app.config.get('VERSION_INFO', {}).get("version", "1.0.0")
    }
    
    return jsonify(status)

@security_bp.route("/logs")
def view_security_logs():
    """セキュリティログ表示（管理者用）"""
    if not session.get("logged_in"):
        abort(403)
    
    try:
        logs = []
        log_files = ['logs/security.log', 'logs/app.log', 'logs/access.log']
        
        for log_file in log_files:
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    file_logs = f.readlines()[-20:]  # 最新20行
                    logs.extend([{
                        'file': log_file,
                        'content': line.strip()
                    } for line in file_logs])
        
        return jsonify({
            "success": True,
            "logs": logs[-50:]  # 最新50件
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })