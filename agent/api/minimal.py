"""
Vercel用の最小限Flask アプリケーション
"""
import os
import sys
from pathlib import Path
from flask import Flask, jsonify

# 最小限のFlask アプリ
app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        'status': 'running',
        'message': 'Bank Optimization System - Minimal Version',
        'version': '0.2.0-minimal',
        'environment': 'vercel'
    })

@app.route('/api/status')
def api_status():
    return jsonify({
        'system': 'operational',
        'version': '0.2.0-minimal',
        'environment': 'vercel',
        'modules': {
            'flask': True,
            'optimization': False
        }
    })

# Vercel用エクスポート
application = app

if __name__ == '__main__':
    app.run(debug=True)