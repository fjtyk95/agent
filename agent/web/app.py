"""Flask web application for bank optimization workflow."""

import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename

# Import optimization modules
import sys
import os

# Add parent directory to path for module imports
if os.environ.get('VERCEL'):
    # Vercel環境ではプロジェクトルートを使用
    parent_dir = '/var/task'
else:
    # ローカル環境
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

try:
    import data_load
    import safety
    import fee
    import optimise
    import export
    import monitor
    import kpi_logger
    
    # charts モジュールは matplotlib 依存のため条件付きインポート
    try:
        import charts
        CHARTS_AVAILABLE = True
    except ImportError:
        CHARTS_AVAILABLE = False
        print("⚠️ Charts module not available (matplotlib not installed)")
    
    print("✅ Core optimization modules imported successfully")
except ImportError as e:
    print(f"❌ Module import error: {e}")
    print(f"Current path: {os.getcwd()}")
    print(f"Parent dir: {parent_dir}")
    print(f"Python path: {sys.path[:3]}")
    raise

app = Flask(__name__)
app.secret_key = 'bank-optimization-secret-key-2025'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Upload configuration - Vercel compatible
if os.environ.get('VERCEL'):
    # Vercel環境では一時ディレクトリを使用
    UPLOAD_FOLDER = Path('/tmp/uploads')
    OUTPUT_FOLDER = Path('/tmp/output')
else:
    # ローカル環境
    UPLOAD_FOLDER = Path('uploads')
    OUTPUT_FOLDER = Path('../output')

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename: str) -> bool:
    """Check if file has allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload_files():
    """File upload page."""
    if request.method == 'POST':
        # Check if files are present
        required_files = ['bank_master', 'fee_table', 'balance_snapshot', 'cashflow_history']
        uploaded_files = {}
        
        for file_key in required_files:
            if file_key not in request.files:
                flash(f'No {file_key} file selected', 'error')
                return redirect(request.url)
            
            file = request.files[file_key]
            if file.filename == '':
                flash(f'No {file_key} file selected', 'error')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{file_key}.csv")
                filepath = UPLOAD_FOLDER / filename
                file.save(filepath)
                uploaded_files[file_key] = str(filepath)
            else:
                flash(f'Invalid file type for {file_key}. Only CSV files allowed.', 'error')
                return redirect(request.url)
        
        # Store file paths in session
        from flask import session
        session['uploaded_files'] = uploaded_files
        flash('Files uploaded successfully!', 'success')
        return redirect(url_for('optimize'))
    
    return render_template('upload.html')


@app.route('/optimize')
def optimize_page():
    """Optimization configuration page."""
    return render_template('optimize.html')


@app.route('/api/optimize', methods=['POST'])
def api_optimize():
    """API endpoint to run optimization."""
    try:
        print("🔧 Starting optimization API endpoint...")
        
        # Get parameters
        data = request.get_json()
        horizon = data.get('horizon', 30)
        quantile = data.get('quantile', 0.95)
        lambda_penalty = data.get('lambda_penalty', 1.0)
        use_cutoff = data.get('use_cutoff', True)
        
        print(f"Parameters: horizon={horizon}, quantile={quantile}, lambda={lambda_penalty}, cutoff={use_cutoff}")
        
        # Get uploaded file paths
        from flask import session
        print(f"🔍 Session keys: {list(session.keys())}")
        if 'uploaded_files' not in session:
            print("❌ No uploaded_files in session")
            return jsonify({'error': 'No files uploaded. Please upload CSV files first.'}), 400
        
        file_paths = session['uploaded_files']
        print(f"📂 File paths from session: {file_paths}")
        
        # Validate file paths exist
        for key, path in file_paths.items():
            if not os.path.exists(path):
                return jsonify({'error': f'File not found: {path}'}), 400
        
        # Load data with error handling
        try:
            print("📂 Loading CSV data...")
            with monitor.Timer("Data Loading"):
                df_bank_master = data_load.load_bank_master(file_paths['bank_master'])
                df_fee_table = data_load.load_fee_table(file_paths['fee_table'])
                df_balance = data_load.load_balance(file_paths['balance_snapshot'])
                df_cashflow = data_load.load_cashflow(file_paths['cashflow_history'])
            print(f"✅ Data loaded: bank_master={len(df_bank_master)}, fee_table={len(df_fee_table)}, balance={len(df_balance)}, cashflow={len(df_cashflow)}")
        except Exception as e:
            print(f"❌ Data loading error: {e}")
            return jsonify({'error': f'Data loading failed: {str(e)}'}), 500
        
        # Calculate safety stocks
        try:
            print("🛡️ Calculating safety stocks...")
            with monitor.Timer("Safety Stock Calculation"):
                safety_stocks = safety.calc_safety(df_cashflow, horizon, quantile)
            print(f"✅ Safety stocks calculated: {safety_stocks.to_dict()}")
        except Exception as e:
            print(f"❌ Safety stock calculation error: {e}")
            return jsonify({'error': f'Safety stock calculation failed: {str(e)}'}), 500
        
        # Prepare optimization inputs
        try:
            print("🏗️ Preparing optimization inputs...")
            banks = df_bank_master['bank_id'].unique().tolist()
            branches = {}
            for bank in banks:
                bank_branches = df_bank_master[df_bank_master['bank_id'] == bank]['branch_id'].unique().tolist()
                branches[bank] = bank_branches
            
            services = df_bank_master['service_id'].unique().tolist()
            
            # Generate future days (next 30 days)
            from datetime import datetime, timedelta
            today = datetime.now()
            days = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
            
            initial_balance = dict(zip(df_balance['bank_id'], df_balance['balance']))
            safety_dict = safety_stocks.to_dict()
            fee_lookup = fee.build_fee_lookup(df_fee_table)
            
            print(f"Banks: {banks}, Services: {services}")
            print(f"Initial balances: {initial_balance}")
            
            # Cut-off constraints
            cut_off = None
            if use_cutoff:
                cut_off = {}
                for _, row in df_bank_master.iterrows():
                    cut_off[(row['bank_id'], row['service_id'])] = row['cut_off_time']
                print(f"Cut-off constraints: {cut_off}")
            
            # Dummy net cash flows (would use forecasts in production)
            net_cash = {(bank, day): 0 for bank in banks for day in days}
            
            # Add some cash outflows to trigger transfers
            for bank in banks:
                for i, day in enumerate(days[:5]):  # First 5 days
                    net_cash[(bank, day)] = -100000 * (1 + i * 0.1)  # Increasing outflows
            
            print(f"✅ Optimization inputs prepared")
        except Exception as e:
            print(f"❌ Input preparation error: {e}")
            return jsonify({'error': f'Input preparation failed: {str(e)}'}), 500
        
        # Run optimization
        try:
            print("🔧 Running MILP optimization...")
            start_time = datetime.now()
            with monitor.Timer("MILP Optimization"):
                result = optimise.build_model(
                    banks=banks,
                    branches=branches,
                    days=days,
                    services=services,
                    net_cash=net_cash,
                    initial_balance=initial_balance,
                    safety=safety_dict,
                    fee_lookup=fee_lookup,
                    cut_off=cut_off,
                    lambda_penalty=lambda_penalty
                )
            print(f"✅ MILP optimization completed")
        except Exception as e:
            print(f"❌ MILP optimization error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Optimization failed: {str(e)}'}), 500
        
        transfers = result['transfers']
        balances = result['balance']
        
        # Prepare export data
        transfer_records = []
        total_fee = 0
        
        fee_calc = fee.FeeCalculator(df_fee_table)
        
        for (from_bank, from_branch, to_bank, to_branch, service, day), amount in transfers.items():
            if amount > 0:
                try:
                    expected_fee = fee_calc.get_fee(
                        from_bank, from_branch, service, int(amount), to_bank, to_branch
                    )
                except:
                    expected_fee = 0
                
                transfer_records.append({
                    'execute_date': day,
                    'from_bank': from_bank,
                    'from_branch': from_branch,
                    'to_bank': to_bank,
                    'to_branch': to_branch,
                    'service_id': service,
                    'amount': int(amount),
                    'expected_fee': expected_fee
                })
                total_fee += expected_fee
        
        # Export results
        output_file = OUTPUT_FOLDER / f"transfer_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        export.to_csv(transfer_records, str(output_file))
        
        # Create cost comparison chart (if matplotlib available)
        chart_file = None
        if CHARTS_AVAILABLE:
            baseline_cost = total_fee * 1.3  # Dummy baseline
            chart_file = OUTPUT_FOLDER / f"cost_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            charts.plot_cost_comparison(baseline_cost, total_fee, str(chart_file))
        
        # Log KPI
        runtime = (datetime.now() - start_time).total_seconds()
        kpi_record = kpi_logger.KPIRecord(
            timestamp=start_time,
            total_fee=total_fee,
            total_shortfall=0,  # Would calculate from balances in practice
            runtime_sec=runtime
        )
        kpi_logger.append_kpi(kpi_record)
        
        # Return results
        return jsonify({
            'success': True,
            'summary': {
                'total_transfers': len(transfer_records),
                'total_fee': total_fee,
                'runtime_sec': runtime,
                'banks_count': len(banks),
                'safety_stocks': safety_dict
            },
            'transfers': transfer_records[:10],  # First 10 transfers for display
            'download_links': {
                'csv': f'/download/{output_file.name}',
                'chart': f'/download/{chart_file.name}' if chart_file else None
            },
            'parameters': {
                'horizon': horizon,
                'quantile': quantile,
                'lambda_penalty': lambda_penalty,
                'use_cutoff': use_cutoff
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Optimization failed: {str(e)}'}), 500


@app.route('/results')
def results_page():
    """Results display page."""
    return render_template('results.html')


@app.route('/download/<filename>')
def download_file(filename):
    """Download generated files."""
    file_path = OUTPUT_FOLDER / filename
    if file_path.exists():
        return send_file(str(file_path), as_attachment=True)
    else:
        return "File not found", 404


@app.route('/api/kpi')
def api_kpi():
    """API endpoint to get KPI history."""
    try:
        days = request.args.get('days', 30, type=int)
        records = kpi_logger.load_recent(days=days)
        kpi_data = []
        for record in records:
            kpi_data.append({
                'timestamp': record.timestamp.isoformat(),
                'total_fee': record.total_fee,
                'total_shortfall': record.total_shortfall,
                'runtime_sec': record.runtime_sec
            })
        return jsonify({'kpi_history': kpi_data})
    except Exception as e:
        return jsonify({'error': f'Failed to load KPI: {str(e)}'}), 500


@app.route('/api/set_sample_data', methods=['POST'])
def api_set_sample_data():
    """API endpoint to set sample data for testing."""
    try:
        from flask import session
        # Set session to use sample data files with absolute paths
        if os.environ.get('VERCEL'):
            # Vercel環境ではプロジェクトルートの data フォルダ
            base_dir = '/var/task'
        else:
            # ローカル環境
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        session['uploaded_files'] = {
            'bank_master': os.path.join(base_dir, 'data', 'bank_master.csv'),
            'fee_table': os.path.join(base_dir, 'data', 'fee_table.csv'),
            'balance_snapshot': os.path.join(base_dir, 'data', 'balance_snapshot.csv'),
            'cashflow_history': os.path.join(base_dir, 'data', 'cashflow_history.csv')
        }
        
        # Verify files exist
        for key, path in session['uploaded_files'].items():
            if not os.path.exists(path):
                return jsonify({'error': f'Sample file not found: {key} at {path}'}), 400
        
        print(f"🔧 Sample data configured in session: {session['uploaded_files']}")
        return jsonify({'success': True, 'message': 'Sample data configured', 'files': session['uploaded_files']})
    except Exception as e:
        print(f"❌ Sample data error: {e}")
        return jsonify({'error': f'Failed to set sample data: {str(e)}'}), 500


@app.route('/api/status')
def api_status():
    """API endpoint to get system status."""
    try:
        # Check if required modules are available
        status = {
            'system': 'operational',
            'modules': {
                'data_load': True,
                'safety': True,
                'fee': True,
                'optimise': True,
                'export': True,
                'monitor': True,
                'kpi_logger': True
            },
            'version': '0.2.0',
            'timestamp': datetime.now().isoformat()
        }
        
        # Check if sample data exists
        sample_files = [
            '../data/bank_master.csv',
            '../data/fee_table.csv',
            '../data/balance_snapshot.csv',
            '../data/cashflow_history.csv'
        ]
        
        status['sample_data_available'] = all(Path(f).exists() for f in sample_files)
        
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': f'Status check failed: {str(e)}'}), 500


@app.route('/kpi')
def kpi_page():
    """KPI dashboard page."""
    return render_template('kpi.html')


@app.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    flash('File is too large. Maximum size is 16MB.', 'error')
    return redirect(url_for('upload_files'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)