#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Route Registration Test
"""

def test_routes():
    print("=== Route Registration Test ===")
    
    try:
        from app import app
        
        # 登録されているルートを確認
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'rule': str(rule)
            })
        
        # 管理者関連のルートをフィルタ
        admin_routes = [r for r in routes if 'admin' in r['rule']]
        
        print("📋 管理者関連ルート:")
        for route in admin_routes:
            print(f"  {route['rule']} -> {route['endpoint']} ({', '.join(route['methods'])})")
        
        # comprehensive_dashboard の存在確認
        comprehensive_routes = [r for r in routes if 'comprehensive_dashboard' in r['rule']]
        
        if comprehensive_routes:
            print("\n✅ comprehensive_dashboard ルート発見:")
            for route in comprehensive_routes:
                print(f"  {route['rule']} -> {route['endpoint']}")
        else:
            print("\n❌ comprehensive_dashboard ルートが見つかりません")
            
        # 全ルート数
        print(f"\n📊 総ルート数: {len(routes)}")
        
        return len(comprehensive_routes) > 0
        
    except Exception as e:
        print(f"❌ ルートテストエラー: {e}")
        return False

if __name__ == "__main__":
    success = test_routes()
    if success:
        print("\n✅ comprehensive_dashboard ルートが正常に登録されています")
        print("🔄 アプリを再起動してアクセスしてください")
    else:
        print("\n❌ comprehensive_dashboard ルートが登録されていません")
        print("🔧 app.py の修正が必要です")