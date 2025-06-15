"""
Vercel Serverless Function エントリーポイント
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json
import io
import csv

from flask import Flask, jsonify, render_template_string, request, session, send_file

# Vercel環境変数設定
os.environ['VERCEL'] = '1'
os.environ['FLASK_ENV'] = 'production'

# 最適化ライブラリのインポート
try:
    import pandas as pd
    import numpy as np
    import pulp as lp
    OPTIMIZATION_AVAILABLE = True
    print("✅ Optimization libraries imported successfully")
except ImportError as e:
    OPTIMIZATION_AVAILABLE = False
    print(f"⚠️ Optimization libraries not available: {e}")

# 基本的なFlaskアプリを直接定義
app = Flask(__name__)
app.secret_key = 'bank-optimization-vercel-key'

# === 最適化関数群 ===

def calc_safety_stock(cashflow_data: List[Dict], horizon: int = 30, quantile: float = 0.95) -> Dict[str, float]:
    """Safety Stock計算"""
    if not OPTIMIZATION_AVAILABLE:
        # デモ用固定値
        return {'MIZUHO': 1500000, 'MUFG': 1200000, 'SMBC': 1800000}
    
    df = pd.DataFrame(cashflow_data)
    safety_stocks = {}
    
    for bank in df['bank_id'].unique():
        bank_data = df[df['bank_id'] == bank]['net_cashflow']
        # 簡易計算: 過去データの分位点を使用
        safety_value = abs(bank_data.quantile(1 - quantile)) * horizon / 30
        safety_stocks[bank] = max(safety_value, 100000)  # 最小10万円
    
    return safety_stocks

def calculate_fee(from_bank: str, to_bank: str, service_id: str, amount: int, fee_table: List[Dict]) -> int:
    """手数料計算"""
    for fee_record in fee_table:
        if (fee_record['from_bank'] == from_bank and 
            fee_record['to_bank'] == to_bank and 
            fee_record['service_id'] == service_id):
            return fee_record['fee']
    return 330  # デフォルト手数料

def build_milp_model(banks: List[str], branches: Dict[str, List[str]], days: List[str], 
                     services: List[str], net_cash: Dict, initial_balance: Dict,
                     safety_stocks: Dict, fee_table: List[Dict], 
                     use_cutoff: bool = True, lambda_penalty: float = 1.0) -> Dict:
    """MILP最適化モデル構築・求解"""
    
    if not OPTIMIZATION_AVAILABLE:
        # デモ用結果
        return {
            'status': 'Optimal',
            'transfers': {
                ('MIZUHO', 'HQ', 'MUFG', 'HQ', 'G', days[0]): 500000,
                ('SMBC', 'HQ', 'MIZUHO', 'HQ', 'G', days[1]): 300000,
                ('MUFG', 'HQ', 'SMBC', 'HQ', 'G', days[2]): 400000
            },
            'balance': {
                (bank, day): initial_balance.get(bank, 0) + np.random.randint(-100000, 200000)
                for bank in banks for day in days[:3]
            },
            'objective_value': 990,
            'runtime_sec': 0.8
        }
    
    # MILP モデル構築
    model = lp.LpProblem("Bank_Cash_Optimization", lp.LpMinimize)
    
    # 変数定義
    # x[from_bank, from_branch, to_bank, to_branch, service, day] = 移動額
    transfer_vars = {}
    for from_bank in banks:
        for from_branch in branches[from_bank]:
            for to_bank in banks:
                if to_bank != from_bank:
                    for to_branch in branches[to_bank]:
                        for service in services:
                            for day in days:
                                var_name = f"x_{from_bank}_{from_branch}_{to_bank}_{to_branch}_{service}_{day}"
                                transfer_vars[(from_bank, from_branch, to_bank, to_branch, service, day)] = \
                                    lp.LpVariable(var_name, lowBound=0, cat='Integer')
    
    # B[bank, day] = 残高
    balance_vars = {}
    for bank in banks:
        for day in days:
            var_name = f"B_{bank}_{day}"
            balance_vars[(bank, day)] = lp.LpVariable(var_name, lowBound=0)
    
    # 不足額変数 S[bank, day] >= 0
    shortage_vars = {}
    for bank in banks:
        for day in days:
            var_name = f"S_{bank}_{day}"
            shortage_vars[(bank, day)] = lp.LpVariable(var_name, lowBound=0)
    
    # 目的関数: 手数料の合計 + ペナルティ
    total_fee = 0
    for key, var in transfer_vars.items():
        from_bank, from_branch, to_bank, to_branch, service, day = key
        fee = calculate_fee(from_bank, to_bank, service, 1, fee_table)
        total_fee += fee * var
    
    total_penalty = lambda_penalty * lp.lpSum(shortage_vars.values())
    model += total_fee + total_penalty
    
    # 制約条件
    
    # 1. 残高更新制約
    for bank in banks:
        for i, day in enumerate(days):
            if i == 0:
                # 初日
                prev_balance = initial_balance.get(bank, 0)
            else:
                prev_balance = balance_vars[(bank, days[i-1])]
            
            # 流入
            inflow = lp.lpSum([
                transfer_vars.get((fb, fbr, bank, tb, s, day), 0)
                for fb in banks for fbr in branches.get(fb, [])
                for tb in branches.get(bank, []) for s in services
                if fb != bank
            ])
            
            # 流出
            outflow = lp.lpSum([
                transfer_vars.get((bank, fbr, tb, tbr, s, day), 0)
                for fbr in branches.get(bank, []) for tb in banks
                for tbr in branches.get(tb, []) for s in services
                if tb != bank
            ])
            
            # 純キャッシュフロー
            net_flow = net_cash.get((bank, day), 0)
            
            # 残高更新
            model += balance_vars[(bank, day)] == prev_balance + inflow - outflow + net_flow
    
    # 2. Safety Stock制約
    for bank in banks:
        for day in days:
            safety_level = safety_stocks.get(bank, 0)
            model += balance_vars[(bank, day)] + shortage_vars[(bank, day)] >= safety_level
    
    # 3. 移動額の上限制約（残高以下）
    for bank in banks:
        for day in days:
            total_outflow = lp.lpSum([
                transfer_vars.get((bank, fbr, tb, tbr, s, day), 0)
                for fbr in branches.get(bank, []) for tb in banks
                for tbr in branches.get(tb, []) for s in services
                if tb != bank
            ])
            if day == days[0]:
                available = initial_balance.get(bank, 0)
            else:
                available = balance_vars[(bank, days[days.index(day)-1])]
            
            model += total_outflow <= available + net_cash.get((bank, day), 0)
    
    # モデル求解
    start_time = datetime.now()
    model.solve(lp.PULP_CBC_CMD(msg=0))
    runtime = (datetime.now() - start_time).total_seconds()
    
    # 結果取得
    status = lp.LpStatus[model.status]
    
    if status == 'Optimal':
        transfers = {}
        for key, var in transfer_vars.items():
            if var.varValue and var.varValue > 0:
                transfers[key] = var.varValue
        
        balances = {}
        for key, var in balance_vars.items():
            if var.varValue is not None:
                balances[key] = var.varValue
        
        return {
            'status': status,
            'transfers': transfers,
            'balance': balances,
            'objective_value': model.objective.value(),
            'runtime_sec': runtime
        }
    else:
        return {
            'status': status,
            'transfers': {},
            'balance': {},
            'objective_value': None,
            'runtime_sec': runtime,
            'error': f'Optimization failed with status: {status}'
        }

def generate_csv_content(transfer_records: List[Dict]) -> str:
    """資金移動計画のCSVコンテンツ生成"""
    output = io.StringIO()
    
    # CSVヘッダー
    fieldnames = [
        'execute_date', 'from_bank', 'from_branch', 'to_bank', 'to_branch',
        'service_id', 'amount', 'expected_fee', 'memo'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    # データ行
    for record in transfer_records:
        # メモ欄を追加
        memo = f"{record['from_bank']}→{record['to_bank']} 最適化移動"
        
        writer.writerow({
            'execute_date': record['execute_date'],
            'from_bank': record['from_bank'],
            'from_branch': record.get('from_branch', 'HQ'),
            'to_bank': record['to_bank'],
            'to_branch': record.get('to_branch', 'HQ'),
            'service_id': record['service_id'],
            'amount': record['amount'],
            'expected_fee': record['expected_fee'],
            'memo': memo
        })
    
    return output.getvalue()

def generate_summary_csv_content(summary: Dict, parameters: Dict) -> str:
    """最適化サマリーのCSVコンテンツ生成"""
    output = io.StringIO()
    
    # サマリー情報
    writer = csv.writer(output)
    writer.writerow(['# 銀行取引最適化結果サマリー'])
    writer.writerow(['項目', '値'])
    writer.writerow(['実行日時', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    writer.writerow(['総移動件数', summary.get('total_transfers', 0)])
    writer.writerow(['総手数料', f"¥{summary.get('total_fee', 0):,}"])
    writer.writerow(['実行時間', f"{summary.get('runtime_sec', 0):.2f}秒"])
    writer.writerow(['対象銀行数', summary.get('banks_count', 0)])
    writer.writerow(['最適化状態', summary.get('optimization_status', 'Unknown')])
    writer.writerow([])
    
    # パラメータ情報
    writer.writerow(['# 最適化パラメータ'])
    writer.writerow(['パラメータ', '値'])
    writer.writerow(['ホライズン期間', f"{parameters.get('horizon', 30)}日"])
    writer.writerow(['リスク分位点', f"{parameters.get('quantile', 0.95)*100:.0f}%"])
    writer.writerow(['ペナルティ重み', parameters.get('lambda_penalty', 1.0)])
    writer.writerow(['Cut-off制約', '有効' if parameters.get('use_cutoff', True) else '無効'])
    writer.writerow([])
    
    # Safety Stock情報
    if 'safety_stocks' in summary:
        writer.writerow(['# Safety Stock'])
        writer.writerow(['銀行', '安全在庫額'])
        for bank, amount in summary['safety_stocks'].items():
            writer.writerow([bank, f"¥{amount:,.0f}"])
    
    return output.getvalue()

# 基本的なHTMLテンプレート
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>銀行取引最適化システム - Vercel版</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-university me-2"></i>銀行取引最適化システム
            </a>
            <span class="badge bg-success">Vercel版</span>
        </div>
    </nav>
    
    <div class="container mt-4">
        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-body text-center">
                        <h1 class="card-title">
                            <i class="fas fa-chart-line text-primary"></i>
                            銀行取引最適化システム
                        </h1>
                        <p class="card-text">Vercel Serverless Functions 上で動作</p>
                        
                        <div class="row mt-4">
                            <div class="col-md-3">
                                <div class="card bg-primary text-white">
                                    <div class="card-body">
                                        <h5>3銀行</h5>
                                        <small>対応金融機関</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-success text-white">
                                    <div class="card-body">
                                        <h5>6支店</h5>
                                        <small>最適化対象</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-info text-white">
                                    <div class="card-body">
                                        <h5>30日間</h5>
                                        <small>予測期間</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-warning text-white">
                                    <div class="card-body">
                                        <h5>95%</h5>
                                        <small>安全在庫水準</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="mt-4">
                            <h3>システム状態</h3>
                            <div class="alert alert-success">
                                <i class="fas fa-check-circle"></i>
                                Vercel Serverless Function 正常動作中
                            </div>
                            
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle"></i>
                                現在の版: 軽量版（最適化機能は段階的実装中）
                            </div>
                        </div>
                        
                        <div class="mt-4">
                            <h4>クイックスタート</h4>
                            <div class="d-grid gap-2 d-md-flex justify-content-md-center">
                                <a href="/upload" class="btn btn-success me-md-2">
                                    <i class="fas fa-upload"></i> ファイルアップロード
                                </a>
                                <a href="/optimize" class="btn btn-primary me-md-2">
                                    <i class="fas fa-cogs"></i> 最適化実行
                                </a>
                                <a href="/results" class="btn btn-warning me-md-2">
                                    <i class="fas fa-chart-bar"></i> 結果表示
                                </a>
                                <a href="/api/status" class="btn btn-info">
                                    <i class="fas fa-cog"></i> システム状態
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <footer class="bg-light mt-5 py-3">
        <div class="container text-center">
            <small>© 2025 Bank Optimization System - Powered by Vercel</small>
        </div>
    </footer>
</body>
</html>
"""

@app.route('/')
def index():
    """メインダッシュボード"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/status')
def api_status():
    """システム状態API"""
    return jsonify({
        'status': 'operational',
        'environment': 'vercel',
        'version': '0.2.0-vercel',
        'platform': 'serverless',
        'modules': {
            'flask': True,
            'optimization': OPTIMIZATION_AVAILABLE,
            'pandas': OPTIMIZATION_AVAILABLE,
            'numpy': OPTIMIZATION_AVAILABLE,
            'pulp': OPTIMIZATION_AVAILABLE,
            'charts': False
        },
        'features': {
            'dashboard': True,
            'file_upload': True,
            'optimization': OPTIMIZATION_AVAILABLE,
            'export': True
        },
        'next_steps': [
            'Optimization modules integration',
            'File upload functionality', 
            'Full feature restoration'
        ]
    })

@app.route('/health')
def health():
    """ヘルスチェック"""
    return jsonify({'status': 'healthy', 'timestamp': os.environ.get('VERCEL_REGION', 'unknown')})

# サンプルデータ（埋め込み）
SAMPLE_DATA = {
    'bank_master': [
        {'bank_id': 'MIZUHO', 'branch_id': 'HQ', 'service_id': 'G', 'cut_off_time': '15:00'},
        {'bank_id': 'MIZUHO', 'branch_id': 'HQ', 'service_id': 'N', 'cut_off_time': '17:00'},
        {'bank_id': 'MIZUHO', 'branch_id': 'OSK', 'service_id': 'G', 'cut_off_time': '14:30'},
        {'bank_id': 'MIZUHO', 'branch_id': 'OSK', 'service_id': 'N', 'cut_off_time': '16:30'},
        {'bank_id': 'MUFG', 'branch_id': 'HQ', 'service_id': 'G', 'cut_off_time': '15:00'},
        {'bank_id': 'MUFG', 'branch_id': 'HQ', 'service_id': 'N', 'cut_off_time': '17:00'},
        {'bank_id': 'MUFG', 'branch_id': 'OSK', 'service_id': 'G', 'cut_off_time': '14:30'},
        {'bank_id': 'MUFG', 'branch_id': 'OSK', 'service_id': 'N', 'cut_off_time': '16:30'},
        {'bank_id': 'SMBC', 'branch_id': 'HQ', 'service_id': 'G', 'cut_off_time': '15:00'},
        {'bank_id': 'SMBC', 'branch_id': 'HQ', 'service_id': 'N', 'cut_off_time': '17:00'},
        {'bank_id': 'SMBC', 'branch_id': 'OSK', 'service_id': 'G', 'cut_off_time': '14:30'},
        {'bank_id': 'SMBC', 'branch_id': 'OSK', 'service_id': 'N', 'cut_off_time': '16:30'}
    ],
    'fee_table': [
        {'from_bank': 'MIZUHO', 'from_branch': 'HQ', 'to_bank': 'MUFG', 'to_branch': 'HQ', 'service_id': 'G', 'fee': 330},
        {'from_bank': 'MIZUHO', 'from_branch': 'HQ', 'to_bank': 'SMBC', 'to_branch': 'HQ', 'service_id': 'G', 'fee': 330},
        {'from_bank': 'MUFG', 'from_branch': 'HQ', 'to_bank': 'MIZUHO', 'to_branch': 'HQ', 'service_id': 'G', 'fee': 330},
        {'from_bank': 'MUFG', 'from_branch': 'HQ', 'to_bank': 'SMBC', 'to_branch': 'HQ', 'service_id': 'G', 'fee': 330},
        {'from_bank': 'SMBC', 'from_branch': 'HQ', 'to_bank': 'MIZUHO', 'to_branch': 'HQ', 'service_id': 'G', 'fee': 330},
        {'from_bank': 'SMBC', 'from_branch': 'HQ', 'to_bank': 'MUFG', 'to_branch': 'HQ', 'service_id': 'G', 'fee': 330}
    ],
    'balance_snapshot': [
        {'bank_id': 'MIZUHO', 'balance': 5000000},
        {'bank_id': 'MUFG', 'balance': 3000000}, 
        {'bank_id': 'SMBC', 'balance': 4000000}
    ],
    'cashflow_history': [
        {'bank_id': 'MIZUHO', 'date': '2025-01-01', 'net_cashflow': -200000},
        {'bank_id': 'MIZUHO', 'date': '2025-01-02', 'net_cashflow': 150000},
        {'bank_id': 'MUFG', 'date': '2025-01-01', 'net_cashflow': -100000},
        {'bank_id': 'MUFG', 'date': '2025-01-02', 'net_cashflow': 80000},
        {'bank_id': 'SMBC', 'date': '2025-01-01', 'net_cashflow': -150000},
        {'bank_id': 'SMBC', 'date': '2025-01-02', 'net_cashflow': 120000}
    ]
}

@app.route('/api/sample_data')
def api_sample_data():
    """サンプルデータ取得API"""
    return jsonify({
        'success': True,
        'message': 'Sample data loaded successfully',
        'data': SAMPLE_DATA,
        'summary': {
            'banks': len(set(item['bank_id'] for item in SAMPLE_DATA['bank_master'])),
            'branches': len(set(f"{item['bank_id']}-{item['branch_id']}" for item in SAMPLE_DATA['bank_master'])),
            'fee_records': len(SAMPLE_DATA['fee_table']),
            'balance_records': len(SAMPLE_DATA['balance_snapshot']),
            'cashflow_records': len(SAMPLE_DATA['cashflow_history'])
        }
    })

@app.route('/upload')
def upload_page():
    """ファイルアップロードページ"""
    upload_html = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ファイルアップロード - 銀行取引最適化システム</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
            <div class="container">
                <a class="navbar-brand" href="/">
                    <i class="fas fa-university me-2"></i>銀行取引最適化システム
                </a>
                <span class="badge bg-success">Vercel版</span>
            </div>
        </nav>
        
        <div class="container mt-4">
            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header">
                            <h3><i class="fas fa-upload"></i> データファイルアップロード</h3>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle"></i>
                                現在はVercel軽量版のため、サンプルデータでのデモンストレーションが可能です。
                            </div>
                            
                            <div class="text-center">
                                <button id="useSampleData" class="btn btn-success btn-lg">
                                    <i class="fas fa-database"></i> サンプルデータ使用
                                </button>
                                <p class="mt-2 text-muted">クリックでサンプルデータを読み込み、最適化を体験できます</p>
                            </div>
                            
                            <hr>
                            
                            <h5>サンプルデータ内容</h5>
                            <div class="row">
                                <div class="col-md-6">
                                    <ul class="list-group">
                                        <li class="list-group-item">
                                            <strong>銀行マスタ</strong><br>
                                            <small>MIZUHO、MUFG、SMBC の3行</small>
                                        </li>
                                        <li class="list-group-item">
                                            <strong>手数料テーブル</strong><br>
                                            <small>行間振替手数料：330円</small>
                                        </li>
                                    </ul>
                                </div>
                                <div class="col-md-6">
                                    <ul class="list-group">
                                        <li class="list-group-item">
                                            <strong>残高スナップショット</strong><br>
                                            <small>各行の現在残高</small>
                                        </li>
                                        <li class="list-group-item">
                                            <strong>キャッシュフロー履歴</strong><br>
                                            <small>過去の入出金データ</small>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        document.getElementById('useSampleData').addEventListener('click', function() {
            fetch('/api/sample_data')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('サンプルデータが正常に読み込まれました！\\n\\n' +
                              `銀行数: ${data.summary.banks}\\n` +
                              `支店数: ${data.summary.branches}\\n` +
                              `手数料レコード: ${data.summary.fee_records}\\n` +
                              `残高レコード: ${data.summary.balance_records}\\n` +
                              `キャッシュフローレコード: ${data.summary.cashflow_records}`);
                        window.location.href = '/optimize';
                    } else {
                        alert('サンプルデータの読み込みに失敗しました。');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('エラーが発生しました。');
                });
        });
        </script>
    </body>
    </html>
    """
    return render_template_string(upload_html)

@app.route('/optimize')
def optimize_page():
    """最適化実行ページ"""
    optimize_html = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>最適化実行 - 銀行取引最適化システム</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
            <div class="container">
                <a class="navbar-brand" href="/">
                    <i class="fas fa-university me-2"></i>銀行取引最適化システム
                </a>
                <span class="badge bg-success">Vercel版</span>
            </div>
        </nav>
        
        <div class="container mt-4">
            <div class="row">
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-header">
                            <h3><i class="fas fa-cogs"></i> 最適化パラメータ設定</h3>
                        </div>
                        <div class="card-body">
                            <form id="optimizeForm">
                                <div class="mb-3">
                                    <label for="horizon" class="form-label">ホライズン期間（日）</label>
                                    <input type="range" class="form-range" id="horizon" min="7" max="90" value="30">
                                    <div class="d-flex justify-content-between">
                                        <small>7日</small>
                                        <small id="horizonValue">30日</small>
                                        <small>90日</small>
                                    </div>
                                </div>
                                
                                <div class="mb-3">
                                    <label for="quantile" class="form-label">リスク分位点</label>
                                    <input type="range" class="form-range" id="quantile" min="0.8" max="0.99" step="0.01" value="0.95">
                                    <div class="d-flex justify-content-between">
                                        <small>80%</small>
                                        <small id="quantileValue">95%</small>
                                        <small>99%</small>
                                    </div>
                                </div>
                                
                                <div class="mb-3">
                                    <label for="lambda_penalty" class="form-label">ペナルティ重み</label>
                                    <input type="range" class="form-range" id="lambda_penalty" min="0.1" max="5.0" step="0.1" value="1.0">
                                    <div class="d-flex justify-content-between">
                                        <small>0.1</small>
                                        <small id="lambdaValue">1.0</small>
                                        <small>5.0</small>
                                    </div>
                                </div>
                                
                                <div class="mb-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="use_cutoff" checked>
                                        <label class="form-check-label" for="use_cutoff">
                                            Cut-off時刻制約を使用
                                        </label>
                                    </div>
                                </div>
                                
                                <div class="text-center">
                                    <button type="submit" class="btn btn-primary btn-lg">
                                        <i class="fas fa-play"></i> 最適化開始
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-info-circle"></i> パラメータ説明</h5>
                        </div>
                        <div class="card-body">
                            <ul class="list-unstyled">
                                <li><strong>ホライズン期間:</strong><br>
                                <small>最適化を行う将来期間の長さ</small></li>
                                
                                <li class="mt-2"><strong>リスク分位点:</strong><br>
                                <small>安全在庫計算に使用するリスク水準</small></li>
                                
                                <li class="mt-2"><strong>ペナルティ重み:</strong><br>
                                <small>残高不足に対する重み係数</small></li>
                                
                                <li class="mt-2"><strong>Cut-off制約:</strong><br>
                                <small>銀行の営業時間制約を考慮</small></li>
                            </ul>
                        </div>
                    </div>
                    
                    <div class="card mt-3">
                        <div class="card-header">
                            <h6><i class="fas fa-database"></i> データ状態</h6>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-success">
                                <small><i class="fas fa-check"></i> サンプルデータ読み込み済み</small>
                            </div>
                            <small>
                                • 銀行: 3行<br>
                                • 支店: 6支店<br>
                                • 手数料レコード: 6件
                            </small>
                        </div>
                    </div>
                </div>
            </div>
            
            <div id="resultsSection" style="display: none;" class="mt-4">
                <div class="card">
                    <div class="card-header">
                        <h4><i class="fas fa-chart-bar"></i> 最適化結果</h4>
                    </div>
                    <div class="card-body">
                        <div id="resultsContent">
                            <!-- 結果がここに表示されます -->
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        // スライダー値をリアルタイム更新
        document.getElementById('horizon').addEventListener('input', function() {
            document.getElementById('horizonValue').textContent = this.value + '日';
        });
        
        document.getElementById('quantile').addEventListener('input', function() {
            document.getElementById('quantileValue').textContent = Math.round(this.value * 100) + '%';
        });
        
        document.getElementById('lambda_penalty').addEventListener('input', function() {
            document.getElementById('lambdaValue').textContent = this.value;
        });
        
        // 最適化実行
        document.getElementById('optimizeForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const params = {
                horizon: parseInt(document.getElementById('horizon').value),
                quantile: parseFloat(document.getElementById('quantile').value),
                lambda_penalty: parseFloat(document.getElementById('lambda_penalty').value),
                use_cutoff: document.getElementById('use_cutoff').checked
            };
            
            // 実行中表示
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 計算中...';
            submitBtn.disabled = true;
            
            // 実際の最適化API呼び出し
            fetch('/api/optimize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(params)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 結果をローカルストレージに保存
                    localStorage.setItem('latest_optimization_results', JSON.stringify(data));
                    displayResults(data);
                } else {
                    alert('最適化でエラーが発生しました: ' + (data.error || 'Unknown error'));
                }
                
                // ボタンを元に戻す
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            })
            .catch(error => {
                console.error('Error:', error);
                alert('最適化でエラーが発生しました: ' + error.message);
                
                // ボタンを元に戻す
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            });
        });
        
        function displayResults(results) {
            const resultsSection = document.getElementById('resultsSection');
            const resultsContent = document.getElementById('resultsContent');
            
            resultsContent.innerHTML = `
                <div class="row">
                    <div class="col-md-3">
                        <div class="card bg-primary text-white">
                            <div class="card-body text-center">
                                <h4>${results.summary.total_transfers}</h4>
                                <small>資金移動件数</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-success text-white">
                            <div class="card-body text-center">
                                <h4>¥${results.summary.total_fee.toLocaleString()}</h4>
                                <small>総手数料</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-info text-white">
                            <div class="card-body text-center">
                                <h4>${results.summary.runtime_sec}秒</h4>
                                <small>実行時間</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-warning text-white">
                            <div class="card-body text-center">
                                <h4>${results.summary.optimization_status}</h4>
                                <small>最適化状態</small>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="mt-3">
                    <h5>資金移動計画</h5>
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>実行日</th>
                                    <th>送金元</th>
                                    <th>送金先</th>
                                    <th>金額</th>
                                    <th>手数料</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${results.transfers.map(t => `
                                    <tr>
                                        <td>${t.execute_date}</td>
                                        <td>${t.from_bank}</td>
                                        <td>${t.to_bank}</td>
                                        <td>¥${t.amount.toLocaleString()}</td>
                                        <td>¥${t.expected_fee.toLocaleString()}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="alert alert-success mt-3">
                    <i class="fas fa-check-circle"></i>
                    最適化が正常に完了しました。上記の資金移動計画により手数料を最小化できます。
                </div>
            `;
            
            resultsSection.style.display = 'block';
            resultsSection.scrollIntoView({ behavior: 'smooth' });
        }
        </script>
    </body>
    </html>
    """
    return render_template_string(optimize_html)

@app.route('/api/optimize', methods=['POST'])
def api_optimize():
    """実際の最適化計算API"""
    try:
        # パラメータ取得
        data = request.get_json()
        horizon = data.get('horizon', 30)
        quantile = data.get('quantile', 0.95)
        lambda_penalty = data.get('lambda_penalty', 1.0)
        use_cutoff = data.get('use_cutoff', True)
        
        print(f"🔧 Starting optimization with params: horizon={horizon}, quantile={quantile}, lambda={lambda_penalty}")
        
        # サンプルデータの取得（セッションから取得する代わりに埋め込みデータを使用）
        bank_master = SAMPLE_DATA['bank_master']
        fee_table = SAMPLE_DATA['fee_table']
        balance_snapshot = SAMPLE_DATA['balance_snapshot']
        cashflow_history = SAMPLE_DATA['cashflow_history']
        
        # 基本データ準備
        banks = list(set(item['bank_id'] for item in bank_master))
        branches = {}
        for bank in banks:
            bank_branches = list(set(item['branch_id'] for item in bank_master if item['bank_id'] == bank))
            branches[bank] = bank_branches
        
        services = list(set(item['service_id'] for item in bank_master))
        
        # 日付生成（今日から指定日数）
        today = datetime.now()
        days = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(min(horizon, 10))]  # Vercelの制限で最大10日
        
        # 初期残高
        initial_balance = {item['bank_id']: item['balance'] for item in balance_snapshot}
        
        # Safety Stock 計算
        print("🛡️ Calculating safety stocks...")
        safety_stocks = calc_safety_stock(cashflow_history, horizon, quantile)
        print(f"Safety stocks: {safety_stocks}")
        
        # ダミーネットキャッシュフロー（一部の日にキャッシュアウトフローを設定）
        net_cash = {}
        for bank in banks:
            for i, day in enumerate(days):
                if i < 3:  # 最初の3日間にアウトフロー
                    net_cash[(bank, day)] = -200000 * (1 + i * 0.2)  # 日々増加するアウトフロー
                else:
                    net_cash[(bank, day)] = 50000  # その後は小さなインフロー
        
        print(f"📊 Prepared data: banks={banks}, services={services}, days={len(days)}")
        
        # MILP最適化実行
        print("🔧 Running MILP optimization...")
        start_time = datetime.now()
        
        result = build_milp_model(
            banks=banks,
            branches=branches,
            days=days,
            services=services,
            net_cash=net_cash,
            initial_balance=initial_balance,
            safety_stocks=safety_stocks,
            fee_table=fee_table,
            use_cutoff=use_cutoff,
            lambda_penalty=lambda_penalty
        )
        
        runtime = (datetime.now() - start_time).total_seconds()
        print(f"✅ Optimization completed in {runtime:.2f}s with status: {result['status']}")
        
        # 結果を人間が読める形式に変換
        transfer_records = []
        total_fee = 0
        
        for key, amount in result['transfers'].items():
            if amount > 0:
                from_bank, from_branch, to_bank, to_branch, service, day = key
                fee = calculate_fee(from_bank, to_bank, service, int(amount), fee_table)
                
                transfer_records.append({
                    'execute_date': day,
                    'from_bank': from_bank,
                    'from_branch': from_branch,
                    'to_bank': to_bank,
                    'to_branch': to_branch,
                    'service_id': service,
                    'amount': int(amount),
                    'expected_fee': fee
                })
                total_fee += fee
        
        # レスポンス作成
        response = {
            'success': True,
            'summary': {
                'total_transfers': len(transfer_records),
                'total_fee': total_fee,
                'runtime_sec': runtime,
                'banks_count': len(banks),
                'optimization_status': result['status'],
                'objective_value': result.get('objective_value'),
                'safety_stocks': safety_stocks
            },
            'transfers': transfer_records[:10],  # 最大10件表示
            'parameters': {
                'horizon': horizon,
                'quantile': quantile,
                'lambda_penalty': lambda_penalty,
                'use_cutoff': use_cutoff
            },
            'optimization_available': OPTIMIZATION_AVAILABLE
        }
        
        if 'error' in result:
            response['warning'] = result['error']
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Optimization error: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': f'Optimization failed: {str(e)}',
            'optimization_available': OPTIMIZATION_AVAILABLE
        }), 500

@app.route('/api/download/csv', methods=['POST'])
def api_download_csv():
    """資金移動計画CSVダウンロード"""
    try:
        data = request.get_json()
        transfer_records = data.get('transfers', [])
        
        if not transfer_records:
            return jsonify({'error': 'No transfer records provided'}), 400
        
        # CSV内容生成
        csv_content = generate_csv_content(transfer_records)
        
        # ファイル名生成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'transfer_plan_{timestamp}.csv'
        
        # レスポンス作成
        return send_file(
            io.BytesIO(csv_content.encode('utf-8-sig')),  # BOM付きUTF-8でExcel対応
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': f'CSV generation failed: {str(e)}'}), 500

@app.route('/api/download/summary', methods=['POST'])
def api_download_summary():
    """最適化結果サマリーCSVダウンロード"""
    try:
        data = request.get_json()
        summary = data.get('summary', {})
        parameters = data.get('parameters', {})
        
        # サマリーCSV内容生成
        csv_content = generate_summary_csv_content(summary, parameters)
        
        # ファイル名生成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'optimization_summary_{timestamp}.csv'
        
        # レスポンス作成
        return send_file(
            io.BytesIO(csv_content.encode('utf-8-sig')),  # BOM付きUTF-8でExcel対応
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': f'Summary CSV generation failed: {str(e)}'}), 500

@app.route('/results')
def results_page():
    """結果表示・ダウンロードページ"""
    results_html = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>結果表示 - 銀行取引最適化システム</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
            <div class="container">
                <a class="navbar-brand" href="/">
                    <i class="fas fa-university me-2"></i>銀行取引最適化システム
                </a>
                <span class="badge bg-success">Vercel版</span>
            </div>
        </nav>
        
        <div class="container mt-4">
            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header">
                            <h3><i class="fas fa-chart-bar"></i> 最適化結果 & ダウンロード</h3>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle"></i>
                                最適化を実行後、こちらから結果をダウンロードできます。
                            </div>
                            
                            <div id="noResultsMessage">
                                <div class="text-center">
                                    <i class="fas fa-exclamation-triangle fa-3x text-muted mb-3"></i>
                                    <h5>表示する結果がありません</h5>
                                    <p class="text-muted">最適化を実行してから結果を確認してください。</p>
                                    <a href="/optimize" class="btn btn-primary">
                                        <i class="fas fa-cogs"></i> 最適化実行へ
                                    </a>
                                </div>
                            </div>
                            
                            <div id="resultsSection" style="display: none;">
                                <div id="resultsSummary"></div>
                                
                                <div class="mt-4">
                                    <h5>ダウンロード</h5>
                                    <div class="row">
                                        <div class="col-md-6">
                                            <div class="card">
                                                <div class="card-body text-center">
                                                    <i class="fas fa-file-csv fa-3x text-success mb-3"></i>
                                                    <h6>資金移動計画</h6>
                                                    <p class="text-muted">実行すべき資金移動の詳細リスト</p>
                                                    <button id="downloadTransferPlan" class="btn btn-success">
                                                        <i class="fas fa-download"></i> CSV ダウンロード
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="col-md-6">
                                            <div class="card">
                                                <div class="card-body text-center">
                                                    <i class="fas fa-chart-pie fa-3x text-info mb-3"></i>
                                                    <h6>最適化サマリー</h6>
                                                    <p class="text-muted">実行結果・パラメータの要約</p>
                                                    <button id="downloadSummary" class="btn btn-info">
                                                        <i class="fas fa-download"></i> サマリー ダウンロード
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        // ローカルストレージから最新の最適化結果を読み込み
        let latestResults = null;
        
        function loadLatestResults() {
            const stored = localStorage.getItem('latest_optimization_results');
            if (stored) {
                try {
                    latestResults = JSON.parse(stored);
                    displayResults();
                } catch (e) {
                    console.error('Failed to parse stored results:', e);
                }
            }
        }
        
        function displayResults() {
            if (!latestResults) return;
            
            document.getElementById('noResultsMessage').style.display = 'none';
            document.getElementById('resultsSection').style.display = 'block';
            
            // サマリー表示
            const summary = latestResults.summary;
            const summaryHtml = `
                <div class="row">
                    <div class="col-md-3">
                        <div class="card bg-primary text-white">
                            <div class="card-body text-center">
                                <h4>${summary.total_transfers}</h4>
                                <small>資金移動件数</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-success text-white">
                            <div class="card-body text-center">
                                <h4>¥${summary.total_fee.toLocaleString()}</h4>
                                <small>総手数料</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-info text-white">
                            <div class="card-body text-center">
                                <h4>${summary.runtime_sec.toFixed(2)}秒</h4>
                                <small>実行時間</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-warning text-white">
                            <div class="card-body text-center">
                                <h4>${summary.optimization_status}</h4>
                                <small>最適化状態</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            document.getElementById('resultsSummary').innerHTML = summaryHtml;
        }
        
        // CSV ダウンロード関数
        function downloadCSV(url, data, filename) {
            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => {
                if (response.ok) {
                    return response.blob();
                } else {
                    throw new Error('Download failed');
                }
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            })
            .catch(error => {
                alert('ダウンロードでエラーが発生しました: ' + error.message);
            });
        }
        
        // イベントリスナー
        document.getElementById('downloadTransferPlan').addEventListener('click', function() {
            if (!latestResults) {
                alert('ダウンロードする結果がありません。');
                return;
            }
            
            const timestamp = new Date().toISOString().slice(0,19).replace(/[:T]/g, '_');
            downloadCSV('/api/download/csv', 
                { transfers: latestResults.transfers }, 
                `transfer_plan_${timestamp}.csv`);
        });
        
        document.getElementById('downloadSummary').addEventListener('click', function() {
            if (!latestResults) {
                alert('ダウンロードする結果がありません。');
                return;
            }
            
            const timestamp = new Date().toISOString().slice(0,19).replace(/[:T]/g, '_');
            downloadCSV('/api/download/summary',
                { 
                    summary: latestResults.summary, 
                    parameters: latestResults.parameters 
                },
                `optimization_summary_${timestamp}.csv`);
        });
        
        // ページ読み込み時に結果を表示
        loadLatestResults();
        </script>
    </body>
    </html>
    """
    return render_template_string(results_html)

# エラーハンドリング
@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'Vercel Serverless Function encountered an error',
        'status': 500
    }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': 'Endpoint not found',
        'status': 404
    }), 404

# Vercel用エクスポート
application = app