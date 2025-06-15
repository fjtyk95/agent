"""
Vercel用のFlask アプリケーションエントリーポイント
"""
import os
import sys
from pathlib import Path

# Vercel環境変数設定
os.environ['VERCEL'] = '1'
os.environ['FLASK_ENV'] = 'production'

# プロジェクトルートを追加
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_dir.parent))

# Flaskアプリをインポート
try:
    sys.path.insert(0, str(current_dir.parent))
    from app import app
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current path: {sys.path}")
    raise

# Vercelではこの変数名が必要
app = app