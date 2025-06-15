#!/usr/bin/env python3
"""
サーバー再起動スクリプト
"""
import os
import subprocess
import sys
import signal
import psutil

def kill_existing_servers():
    """既存のFlaskサーバーを停止"""
    print("🔧 既存のFlaskサーバーを確認中...")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python3' and 'app.py' in ' '.join(proc.info['cmdline']):
                print(f"🔴 既存サーバーを停止: PID {proc.info['pid']}")
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

def start_flask_server():
    """Flaskサーバーを起動"""
    print("🚀 Flaskサーバーを起動中...")
    
    # webディレクトリに移動
    web_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(web_dir)
    print(f"📂 作業ディレクトリ: {os.getcwd()}")
    
    # 依存関係確認
    try:
        import flask
        import werkzeug
        print("✅ Flask/Werkzeug available")
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        return False
    
    # サーバー起動
    try:
        print("🌐 Starting Flask server on http://localhost:5001")
        print("📝 ダッシュボード: http://localhost:5001")
        print("📁 ファイルアップロード: http://localhost:5001/upload")
        print("⚙️ 最適化実行: http://localhost:5001/optimize")
        print("📊 結果表示: http://localhost:5001/results")
        print("📈 KPI: http://localhost:5001/kpi")
        print("\n💡 Ctrl+C で停止")
        
        # app.pyを実行
        subprocess.run([sys.executable, 'app.py'])
        
    except KeyboardInterrupt:
        print("\n🛑 サーバーを停止中...")
    except Exception as e:
        print(f"❌ サーバー起動エラー: {e}")
        return False
    
    return True

if __name__ == "__main__":
    kill_existing_servers()
    start_flask_server()