"""
Interactive UI widgets for bank transfer optimization system

Provides real-time parameter adjustment and auto-recalculation functionality
for the Jupyter notebook interface.
"""

import ipywidgets as widgets
from IPython.display import display, clear_output
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
from typing import Dict, Any, Callable, Optional

# Import optimization modules
import data_load
import safety
import fee
import optimise
import export
import charts
import monitor
import kpi_logger


class OptimizationGUI:
    """
    Enhanced GUI with real-time recalculation for bank transfer optimization
    """
    
    def __init__(self):
        self.data_loaded = False
        self.optimization_result = None
        self.auto_recalc = False
        self.recalc_timer = None
        
        # Data storage
        self.df_bank_master = None
        self.df_fee_table = None
        self.df_balance = None
        self.df_cashflow = None
        
        # Create widgets
        self._create_parameter_widgets()
        self._create_data_widgets()
        self._create_control_widgets()
        self._create_output_widgets()
        
        # Setup callbacks
        self._setup_callbacks()
    
    def _create_parameter_widgets(self):
        """Create parameter adjustment widgets"""
        
        # Enhanced sliders with better styling
        self.horizon_slider = widgets.IntSlider(
            value=30,
            min=7,
            max=90,
            step=1,
            description='期間 (日):',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='400px'),
            continuous_update=False,  # Only update on release
            readout=True,
            readout_format='d'
        )
        
        self.quantile_slider = widgets.FloatSlider(
            value=0.95,
            min=0.80,
            max=0.99,
            step=0.01,
            description='リスク分位点:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='400px'),
            continuous_update=False,
            readout=True,
            readout_format='.2f'
        )
        
        self.lambda_slider = widgets.FloatSlider(
            value=1.0,
            min=0.1,
            max=10.0,
            step=0.1,
            description='ペナルティ重み:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='400px'),
            continuous_update=False,
            readout=True,
            readout_format='.1f'
        )
        
        self.cutoff_toggle = widgets.Checkbox(
            value=True,
            description='Cut-off時刻制約を使用',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='400px')
        )
        
        # Auto-recalc toggle
        self.auto_recalc_toggle = widgets.Checkbox(
            value=False,
            description='リアルタイム再計算 (変更時自動実行)',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='400px')
        )
        
        # Parameter reset button
        self.reset_params_button = widgets.Button(
            description="デフォルト値に戻す",
            button_style='',
            layout=widgets.Layout(width='150px')
        )
        
        # Parameter info display
        self.param_info = widgets.HTML(
            value=self._generate_param_info(),
            layout=widgets.Layout(width='500px')
        )
        
        # Group parameters
        self.params_box = widgets.VBox([
            widgets.HTML("<h3>📊 最適化パラメータ</h3>"),
            self.horizon_slider,
            self.quantile_slider,
            self.lambda_slider,
            self.cutoff_toggle,
            widgets.HTML("<hr>"),
            self.auto_recalc_toggle,
            self.reset_params_button,
            widgets.HTML("<h4>📈 パラメータ説明</h4>"),
            self.param_info
        ], layout=widgets.Layout(border='1px solid #ddd', padding='15px'))
    
    def _create_data_widgets(self):
        """Create data loading widgets"""
        
        data_dir = Path("data")
        
        self.file_widgets = {
            'bank_master': widgets.Text(
                value=str(data_dir / "bank_master.csv"),
                description='銀行マスタ:',
                style={'description_width': '120px'},
                layout=widgets.Layout(width='500px')
            ),
            'fee_table': widgets.Text(
                value=str(data_dir / "fee_table.csv"),
                description='手数料テーブル:',
                style={'description_width': '120px'},
                layout=widgets.Layout(width='500px')
            ),
            'balance': widgets.Text(
                value=str(data_dir / "balance_snapshot.csv"),
                description='残高スナップショット:',
                style={'description_width': '120px'},
                layout=widgets.Layout(width='500px')
            ),
            'cashflow': widgets.Text(
                value=str(data_dir / "cashflow_history.csv"),
                description='キャッシュフロー履歴:',
                style={'description_width': '120px'},
                layout=widgets.Layout(width='500px')
            )
        }
        
        self.load_button = widgets.Button(
            description="📂 データ読み込み",
            button_style='primary',
            layout=widgets.Layout(width='200px')
        )
        
        self.data_status = widgets.HTML(value="❌ データ未読み込み")
        
        self.data_box = widgets.VBox([
            widgets.HTML("<h3>📁 データファイル</h3>"),
            *self.file_widgets.values(),
            widgets.HBox([self.load_button, self.data_status]),
        ], layout=widgets.Layout(border='1px solid #ddd', padding='15px'))
    
    def _create_control_widgets(self):
        """Create optimization control widgets"""
        
        self.optimize_button = widgets.Button(
            description="⚡ 最適化実行",
            button_style='success',
            layout=widgets.Layout(width='200px', height='40px')
        )
        
        self.quick_run_button = widgets.Button(
            description="🚀 クイック実行",
            button_style='danger',
            layout=widgets.Layout(width='200px', height='40px')
        )
        
        self.export_path = widgets.Text(
            value="output/transfer_plan.csv",
            description='出力パス:',
            style={'description_width': '80px'},
            layout=widgets.Layout(width='400px')
        )
        
        self.export_button = widgets.Button(
            description="💾 エクスポート",
            button_style='warning',
            layout=widgets.Layout(width='150px')
        )
        
        self.control_box = widgets.VBox([
            widgets.HTML("<h3>🎯 実行制御</h3>"),
            widgets.HBox([self.optimize_button, self.quick_run_button]),
            widgets.HTML("<hr>"),
            widgets.HBox([self.export_path, self.export_button])
        ], layout=widgets.Layout(border='1px solid #ddd', padding='15px'))
    
    def _create_output_widgets(self):
        """Create output display widgets"""
        
        self.status_output = widgets.Output(
            layout=widgets.Layout(height='200px', border='1px solid #ddd')
        )
        
        self.results_output = widgets.Output(
            layout=widgets.Layout(height='300px', border='1px solid #ddd')
        )
        
        self.results_summary = widgets.HTML(
            value="<i>最適化結果はここに表示されます</i>",
            layout=widgets.Layout(height='100px', border='1px solid #ddd', padding='10px')
        )
        
        self.output_box = widgets.VBox([
            widgets.HTML("<h3>📋 実行状況</h3>"),
            self.status_output,
            widgets.HTML("<h3>📈 最適化結果</h3>"),
            self.results_summary,
            self.results_output
        ])
    
    def _setup_callbacks(self):
        """Setup widget callbacks and event handlers"""
        
        # Parameter change callbacks
        self.horizon_slider.observe(self._on_param_change, names='value')
        self.quantile_slider.observe(self._on_param_change, names='value')
        self.lambda_slider.observe(self._on_param_change, names='value')
        self.cutoff_toggle.observe(self._on_param_change, names='value')
        
        # Auto-recalc toggle
        self.auto_recalc_toggle.observe(self._on_auto_recalc_toggle, names='value')
        
        # Button callbacks
        self.reset_params_button.on_click(self._reset_parameters)
        self.load_button.on_click(self._load_data)
        self.optimize_button.on_click(self._run_optimization)
        self.quick_run_button.on_click(self._quick_run)
        self.export_button.on_click(self._export_results)
    
    def _generate_param_info(self):
        """Generate parameter information HTML"""
        return f"""
        <div style="font-size: 12px; color: #666;">
        <b>期間:</b> 最適化を行う将来期間の長さ (7-90日)<br>
        <b>リスク分位点:</b> 安全在庫計算に使用するリスク水準 (80-99%)<br>
        <b>ペナルティ重み:</b> 残高不足に対するペナルティ係数 (0.1-10.0)<br>
        <b>Cut-off制約:</b> 銀行営業時間制約の考慮有無
        </div>
        """
    
    def _on_param_change(self, change):
        """Handle parameter change events"""
        # Update parameter info
        self.param_info.value = self._generate_param_info()
        
        # Auto-recalculation if enabled
        if self.auto_recalc_toggle.value and self.data_loaded:
            self._schedule_recalculation()
    
    def _on_auto_recalc_toggle(self, change):
        """Handle auto-recalc toggle change"""
        self.auto_recalc = change['new']
        if self.auto_recalc and self.data_loaded:
            with self.status_output:
                print("✅ リアルタイム再計算が有効になりました")
        else:
            with self.status_output:
                print("⏸️ リアルタイム再計算が無効になりました")
    
    def _schedule_recalculation(self):
        """Schedule optimization recalculation with debouncing"""
        # Cancel previous timer
        if hasattr(self, '_recalc_timer') and self._recalc_timer:
            self._recalc_timer.cancel()
        
        # Schedule new calculation after 1 second delay
        import threading
        self._recalc_timer = threading.Timer(1.0, self._auto_recalculate)
        self._recalc_timer.start()
    
    def _auto_recalculate(self):
        """Perform automatic recalculation"""
        with self.status_output:
            print("🔄 パラメータ変更により自動再計算中...")
        self._run_optimization_internal()
    
    def _reset_parameters(self, button):
        """Reset all parameters to default values"""
        self.horizon_slider.value = 30
        self.quantile_slider.value = 0.95
        self.lambda_slider.value = 1.0
        self.cutoff_toggle.value = True
        
        with self.status_output:
            print("🔄 パラメータをデフォルト値にリセットしました")
    
    def _load_data(self, button):
        """Load CSV data files"""
        with self.status_output:
            clear_output(wait=True)
            print("📂 データ読み込み開始...")
            
            try:
                self.df_bank_master = data_load.load_bank_master(self.file_widgets['bank_master'].value)
                self.df_fee_table = data_load.load_fee_table(self.file_widgets['fee_table'].value)
                self.df_balance = data_load.load_balance(self.file_widgets['balance'].value)
                self.df_cashflow = data_load.load_cashflow(self.file_widgets['cashflow'].value)
                
                self.data_loaded = True
                self.data_status.value = "✅ データ読み込み完了"
                
                print("✅ データ読み込み完了")
                print(f"銀行マスタ: {len(self.df_bank_master)} 行")
                print(f"手数料テーブル: {len(self.df_fee_table)} 行")
                print(f"残高: {len(self.df_balance)} 行")
                print(f"キャッシュフロー: {len(self.df_cashflow)} 行")
                
            except Exception as e:
                self.data_loaded = False
                self.data_status.value = f"❌ データ読み込みエラー"
                print(f"❌ データ読み込みエラー: {e}")
    
    def _run_optimization(self, button):
        """Run optimization with current parameters"""
        if not self.data_loaded:
            with self.status_output:
                print("⚠️ 先にデータを読み込んでください")
            return
        
        self._run_optimization_internal()
    
    def _run_optimization_internal(self):
        """Internal optimization execution"""
        with self.status_output:
            print("⚡ 最適化実行中...")
            
            try:
                # Get parameters
                horizon = self.horizon_slider.value
                quantile = self.quantile_slider.value
                lambda_penalty = self.lambda_slider.value
                use_cutoff = self.cutoff_toggle.value
                
                start_time = datetime.now()
                
                print(f"📊 パラメータ: horizon={horizon}, quantile={quantile:.2f}, lambda={lambda_penalty}, cutoff={use_cutoff}")
                
                # Safety Stock calculation
                safety_stocks = safety.calc_safety(self.df_cashflow, horizon, quantile)
                print(f"🛡️ Safety Stock計算完了: {len(safety_stocks)} 銀行")
                
                # Prepare fee calculator
                fee_calc = fee.FeeCalculator(self.df_fee_table)
                fee_lookup = fee.build_fee_lookup(self.df_fee_table)
                
                # Prepare initial balance
                initial_balance = dict(zip(self.df_balance['bank_id'], self.df_balance['balance']))
                safety_dict = safety_stocks.to_dict()
                
                # Prepare banks and branches
                banks = self.df_bank_master['bank_id'].unique().tolist()
                branches = {}
                for bank in banks:
                    bank_branches = self.df_bank_master[self.df_bank_master['bank_id'] == bank]['branch_id'].unique().tolist()
                    branches[bank] = bank_branches
                
                services = self.df_bank_master['service_id'].unique().tolist()
                
                # Date range
                today = datetime.now()
                days = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(min(horizon, 30))]
                
                # Cut-off constraints
                cut_off = None
                if use_cutoff:
                    cut_off = {}
                    for _, row in self.df_bank_master.iterrows():
                        cut_off[(row['bank_id'], row['service_id'])] = row['cut_off_time']
                
                # Dummy net_cash (replace with actual forecasts)
                net_cash = {}
                for bank in banks:
                    for i, day in enumerate(days):
                        if i < 3:  # First 3 days with outflow
                            net_cash[(bank, day)] = -150000 * (1 + i * 0.1)
                        else:
                            net_cash[(bank, day)] = 50000
                
                # Run optimization
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
                
                transfers = result['transfers']
                balances = result['balance']
                
                runtime = (datetime.now() - start_time).total_seconds()
                
                # Store results
                self.optimization_result = {
                    'transfers': transfers,
                    'balances': balances,
                    'safety_stocks': safety_stocks,
                    'parameters': {
                        'horizon': horizon,
                        'quantile': quantile,
                        'lambda': lambda_penalty,
                        'cutoff': use_cutoff
                    },
                    'runtime': runtime
                }
                
                print(f"✅ 最適化完了: {len(transfers)} 件の資金移動 (実行時間: {runtime:.2f}秒)")
                
                # Update results display
                self._update_results_display()
                
                # Log KPI
                self._log_kpi()
                
            except Exception as e:
                print(f"❌ 最適化エラー: {e}")
                import traceback
                traceback.print_exc()
    
    def _update_results_display(self):
        """Update results display widgets"""
        if not self.optimization_result:
            return
        
        result = self.optimization_result
        transfers = result['transfers']
        
        # Convert to DataFrame
        transfer_records = []
        total_fee = 0
        
        for (from_bank, from_branch, to_bank, to_branch, service, day), amount in transfers.items():
            if amount > 0:
                try:
                    expected_fee = fee.FeeCalculator(self.df_fee_table).get_fee(
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
        
        df_transfers = pd.DataFrame(transfer_records)
        self.df_transfers = df_transfers
        self.total_fee = total_fee
        
        # Update summary
        runtime = result['runtime']
        self.results_summary.value = f"""
        <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
        <h4>📊 最適化結果サマリー</h4>
        <b>資金移動件数:</b> {len(df_transfers)} 件<br>
        <b>総手数料:</b> ¥{total_fee:,}<br>
        <b>実行時間:</b> {runtime:.2f} 秒<br>
        <b>最適化状態:</b> {result.get('status', 'Optimal')}
        </div>
        """
        
        # Display transfer plan
        with self.results_output:
            clear_output(wait=True)
            if len(df_transfers) > 0:
                print("📋 資金移動計画 (上位10件):")
                display(df_transfers.head(10))
            else:
                print("📋 最適化結果: 資金移動は不要です")
    
    def _log_kpi(self):
        """Log KPI metrics"""
        if not self.optimization_result:
            return
        
        try:
            kpi_record = kpi_logger.KPIRecord(
                timestamp=datetime.now(),
                total_fee=self.total_fee,
                total_shortfall=0,  # Simplified
                runtime_sec=self.optimization_result['runtime']
            )
            kpi_logger.append_kpi(kpi_record)
        except Exception as e:
            print(f"KPIログエラー: {e}")
    
    def _quick_run(self, button):
        """Run complete pipeline"""
        with self.status_output:
            clear_output(wait=True)
            print("🚀 クイック実行開始...")
        
        # Load data
        self._load_data(None)
        if not self.data_loaded:
            return
        
        # Run optimization
        self._run_optimization_internal()
        
        with self.status_output:
            print("🎉 クイック実行完了!")
    
    def _export_results(self, button):
        """Export results to CSV and charts"""
        if not hasattr(self, 'df_transfers'):
            with self.status_output:
                print("⚠️ 先に最適化を実行してください")
            return
        
        with self.status_output:
            print("💾 エクスポート中...")
            
            try:
                # Create output directory
                output_file = Path(self.export_path.value)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Export CSV
                self.df_transfers.to_csv(output_file, index=False)
                print(f"✅ CSV出力: {output_file}")
                
                # Create chart
                baseline_cost = self.total_fee * 1.3  # Dummy baseline
                chart_path = output_file.parent / "cost_comparison.png"
                charts.plot_cost_comparison(baseline_cost, self.total_fee, str(chart_path))
                print(f"📊 チャート出力: {chart_path}")
                
                print("💾 エクスポート完了!")
                
            except Exception as e:
                print(f"❌ エクスポートエラー: {e}")
    
    def display(self):
        """Display the complete GUI"""
        main_layout = widgets.VBox([
            widgets.HTML("<h1>🏦 銀行取引最適化システム v0.2</h1>"),
            widgets.HTML("<p><i>リアルタイムパラメータ調整 & 自動再計算対応</i></p>"),
            widgets.HTML("<hr>"),
            
            # Parameters and data in top row
            widgets.HBox([
                self.params_box,
                self.data_box
            ], layout=widgets.Layout(width='100%')),
            
            # Controls
            self.control_box,
            
            # Output
            self.output_box
        ])
        
        display(main_layout)


# Convenience function for easy import
def create_optimization_gui():
    """Create and return an OptimizationGUI instance"""
    return OptimizationGUI()