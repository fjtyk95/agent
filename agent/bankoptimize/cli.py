"""Command line interface for bankoptimize package."""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Import optimization modules
import data_load
import safety
import fee
import optimise
import export
import monitor
import kpi_logger


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Bank transfer optimization workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s run --balance data/balance.csv --cash data/cashflow.csv --out transfer_plan.csv
  %(prog)s run --balance data/balance.csv --cash data/cashflow.csv --horizon 45 --quantile 0.99
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run optimization command
    run_parser = subparsers.add_parser('run', help='Run optimization pipeline')
    
    # Required arguments
    run_parser.add_argument(
        '--balance', 
        required=True,
        help='Path to balance_snapshot.csv'
    )
    run_parser.add_argument(
        '--cash',
        required=True, 
        help='Path to cashflow_history.csv'
    )
    run_parser.add_argument(
        '--out',
        default='output/transfer_plan.csv',
        help='Output path for transfer plan CSV (default: output/transfer_plan.csv)'
    )
    
    # Optional data files
    run_parser.add_argument(
        '--bank-master',
        default='data/bank_master.csv',
        help='Path to bank_master.csv (default: data/bank_master.csv)'
    )
    run_parser.add_argument(
        '--fee-table',
        default='data/fee_table.csv', 
        help='Path to fee_table.csv (default: data/fee_table.csv)'
    )
    
    # Optimization parameters
    run_parser.add_argument(
        '--horizon',
        type=int,
        default=30,
        help='Safety stock horizon in days (default: 30)'
    )
    run_parser.add_argument(
        '--quantile',
        type=float,
        default=0.95,
        help='Safety stock quantile (default: 0.95)'
    )
    run_parser.add_argument(
        '--lambda-penalty',
        type=float,
        default=1.0,
        help='Shortfall penalty weight (default: 1.0)'
    )
    run_parser.add_argument(
        '--no-cutoff',
        action='store_true',
        help='Disable cut-off time constraints'
    )
    
    # Logging
    run_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser


def prepare_optimization_inputs(args) -> Dict:
    """Load data and prepare optimization inputs."""
    print("📂 Loading data files...")
    
    # Load CSV data
    df_bank_master = data_load.load_bank_master(args.bank_master)
    df_fee_table = data_load.load_fee_table(args.fee_table)
    df_balance = data_load.load_balance(args.balance)
    df_cashflow = data_load.load_cashflow(args.cash)
    
    print(f"   Bank Master: {len(df_bank_master)} rows")
    print(f"   Fee Table: {len(df_fee_table)} rows") 
    print(f"   Balance: {len(df_balance)} rows")
    print(f"   Cashflow: {len(df_cashflow)} rows")
    
    # Calculate safety stocks
    print(f"🛡️  Calculating safety stocks (horizon={args.horizon}, quantile={args.quantile})...")
    safety_stocks = safety.calc_safety(df_cashflow, args.horizon, args.quantile)
    
    # Prepare fee calculator
    fee_lookup = fee.build_fee_lookup(df_fee_table)
    
    # Prepare initial balances
    initial_balance = dict(zip(df_balance['bank_id'], df_balance['balance']))
    safety_dict = safety_stocks.to_dict()
    
    # Prepare banks and branches
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
    
    # Cut-off constraints
    cut_off = None
    if not args.no_cutoff:
        cut_off = {}
        for _, row in df_bank_master.iterrows():
            cut_off[(row['bank_id'], row['service_id'])] = row['cut_off_time']
    
    # Dummy net cash flows (in practice, would use forecasts)
    net_cash = {(bank, day): 0 for bank in banks for day in days}
    
    return {
        'banks': banks,
        'branches': branches,
        'days': days,
        'services': services,
        'net_cash': net_cash,
        'initial_balance': initial_balance,
        'safety': safety_dict,
        'fee_lookup': fee_lookup,
        'cut_off': cut_off,
        'lambda_penalty': args.lambda_penalty
    }


def run_optimization_pipeline(args) -> None:
    """Execute the full optimization pipeline."""
    start_time = datetime.now()
    
    try:
        # Prepare inputs
        with monitor.Timer("Data Loading & Preparation"):
            inputs = prepare_optimization_inputs(args)
        
        # Run optimization
        print("🔧 Running MILP optimization...")
        with monitor.Timer("MILP Optimization"):
            result = optimise.build_model(**inputs)
        
        transfers = result['transfers']
        balances = result['balance']
        
        print(f"✅ Optimization complete: {len(transfers)} transfers planned")
        
        # Prepare export data
        transfer_records = []
        total_fee = 0
        
        fee_calc = fee.FeeCalculator(data_load.load_fee_table(args.fee_table))
        
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
        print(f"💾 Exporting results to {args.out}...")
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        export.to_csv(transfer_records, args.out)
        print(f"📄 Transfer plan exported: {len(transfer_records)} transfers, total fee: ¥{total_fee:,}")
        
        # Log KPI
        runtime = (datetime.now() - start_time).total_seconds()
        kpi_record = kpi_logger.KPIRecord(
            timestamp=start_time,
            total_fee=total_fee,
            total_shortfall=0,  # Would calculate from balances in practice
            runtime_sec=runtime
        )
        kpi_logger.append_kpi(kpi_record)
        print(f"📊 KPI logged: runtime={runtime:.1f}s")
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'run':
        # Configure logging
        import logging
        level = logging.INFO if args.verbose else logging.WARNING
        logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
        
        run_optimization_pipeline(args)


if __name__ == '__main__':
    main()