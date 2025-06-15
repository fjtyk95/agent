# 受け入れテスト手順書

## 🎯 テスト目的
銀行取引最適化ワークフローの全機能が正常に動作することを確認する。

## 📋 前提条件

### 必要なソフトウェア
- Python 3.11+
- pip または Poetry
- JupyterLab (Notebook テスト用)

### 必要なPythonパッケージ
```bash
pip install pandas numpy pulp matplotlib ipywidgets
```

### プロジェクト構造確認
```
agent/
├── data/                    # テストデータ
│   ├── bank_master.csv
│   ├── fee_table.csv 
│   ├── balance_snapshot.csv
│   └── cashflow_history.csv
├── bankoptimize/           # CLIパッケージ
│   ├── __init__.py
│   └── cli.py
├── *.py                    # 実装モジュール
├── interactive_notebook.ipynb
└── tests/                  # 自動テスト
```

---

## 🧪 テストケース

### テスト1: データロード機能
**目的**: CSV読み込み・検証機能の確認

```bash
# 1. Pythonインタラクティブモードで実行
python3 -c "
import data_load
df = data_load.load_bank_master('data/bank_master.csv')
print(f'✅ Bank Master: {len(df)} 行読み込み')
print(df.head())
"
```

**期待結果**: 
- 12行のbank_masterデータが表示
- エラーなし

### テスト2: Safety Stock計算
**目的**: リスク計算ロジックの確認

```bash
python3 -c "
import data_load, safety
df = data_load.load_cashflow('data/cashflow_history.csv')
stocks = safety.calc_safety(df, horizon_days=30, quantile=0.95)
print('✅ Safety Stock 計算結果:')
print(stocks)
"
```

**期待結果**:
- 3銀行の安全在庫量が表示
- 全て非負の値

### テスト3: 手数料計算
**目的**: 手数料ルックアップ機能の確認

```bash
python3 -c "
import data_load, fee
df = data_load.load_fee_table('data/fee_table.csv')
calc = fee.FeeCalculator(df)
fee_small = calc.get_fee('MIZUHO', '001', 'G', 50000, 'MUFG', '001')
fee_large = calc.get_fee('MIZUHO', '001', 'G', 150000, 'MUFG', '001')
print(f'✅ 手数料: 小額={fee_small}円, 大額={fee_large}円')
"
```

**期待結果**:
- 小額: 220円
- 大額: 330円

### テスト4: MILP最適化エンジン
**目的**: 最適化の実行確認

```bash
python3 -c "
import data_load, safety, fee, optimise
from datetime import datetime, timedelta

# データ読み込み
df_bank = data_load.load_bank_master('data/bank_master.csv')
df_fee = data_load.load_fee_table('data/fee_table.csv')
df_balance = data_load.load_balance('data/balance_snapshot.csv')
df_cash = data_load.load_cashflow('data/cashflow_history.csv')

# 準備
banks = ['MIZUHO', 'MUFG', 'SMBC']
branches = {'MIZUHO': ['001', '002'], 'MUFG': ['001', '002'], 'SMBC': ['001', '002']}
days = ['2025-06-08', '2025-06-09']
services = ['G']

initial_balance = {'MIZUHO': 2500000, 'MUFG': 1800000, 'SMBC': 3200000}
safety_stocks = safety.calc_safety(df_cash, 30, 0.95)
fee_lookup = fee.build_fee_lookup(df_fee)

# 資金不足シナリオ
net_cash = {
    ('MIZUHO', '2025-06-08'): -500000,
    ('MIZUHO', '2025-06-09'): -300000,
    ('MUFG', '2025-06-08'): -400000,
    ('MUFG', '2025-06-09'): -200000,
    ('SMBC', '2025-06-08'): 200000,
    ('SMBC', '2025-06-09'): 100000,
}

# 最適化実行
result = optimise.build_model(
    banks=banks, branches=branches, days=days, services=services,
    net_cash=net_cash, initial_balance=initial_balance, 
    safety=safety_stocks.to_dict(), fee_lookup=fee_lookup
)

print(f'✅ 最適化完了: {len(result[\"transfers\"])} 件の資金移動')
"
```

**期待結果**:
- エラーなく実行完了
- 何らかの資金移動計画が生成

### テスト5: CLI インターフェース
**目的**: コマンドライン実行の確認

```bash
# ヘルプ表示
python3 -m bankoptimize.cli --help

# 最適化実行
python3 -m bankoptimize.cli run \
  --balance data/balance_snapshot.csv \
  --cash data/cashflow_history.csv \
  --out output/test_transfer_plan.csv \
  --horizon 30 \
  --quantile 0.95
```

**期待結果**:
- ヘルプが正常表示
- 最適化が30秒以内に完了
- `output/test_transfer_plan.csv` が生成
- KPIログが `logs/kpi.jsonl` に記録

### テスト6: Jupyter Notebook
**目的**: インタラクティブ UI の確認

```bash
# JupyterLab起動
jupyter lab interactive_notebook.ipynb
```

**手順**:
1. 全セルを順番に実行
2. パラメータスライダーを操作
3. 「🚀 全実行」ボタンをクリック
4. 結果表示を確認

**期待結果**:
- エラーなく全セル実行
- ウィジェットが正常動作
- 最適化結果がDataFrameで表示
- チャートが生成

### テスト7: 結果ファイル確認
**目的**: 出力ファイルの品質確認

```bash
# 生成ファイル確認
ls -la output/
cat output/test_transfer_plan.csv | head -5
cat logs/kpi.jsonl
```

**期待内容**:
- `output/test_transfer_plan.csv`: execute_date, from_bank, to_bank, service_id, amount, expected_fee
- `logs/kpi.jsonl`: timestamp, total_fee, total_shortfall, runtime_sec

### テスト8: 自動テスト実行
**目的**: 単体・統合テストの確認

```bash
# pytest実行 (要pytest)
pip install pytest
python3 -m pytest tests/ -v
```

**期待結果**:
- 全テストが PASSED
- テスト時間 < 60秒

---

## 🔍 性能・品質基準

### 性能要件
- [ ] CSV 1,000行規模で30秒以内に最適化完了
- [ ] メモリ使用量 < 1GB
- [ ] CLI実行でエラー終了なし

### 機能要件
- [ ] 振込不能ケース: 0件 (安全在庫維持)
- [ ] 手数料計算: 金額帯別に正確
- [ ] Cut-off制約: 15:00以降は翌日扱い
- [ ] 自己取引除外: 同一銀行・支店間は移動なし

### UI要件 (Notebook)
- [ ] パラメータ変更でリアルタイム反映
- [ ] 結果表示: 10行以内でサマリー
- [ ] エクスポート: CSVとチャートが同時生成

---

## 🚨 トラブルシューティング

### よくあるエラー

**ImportError: No module named 'pulp'**
```bash
pip install pulp
```

**FileNotFoundError: data/xxx.csv**
```bash
# データディレクトリの存在確認
ls -la data/
```

**MILP solver failed**
- PuLP/CBCソルバーの問題
- データの制約が満たせない場合
- λ_penaltyを大きくして再実行

**Jupyter widgets not working**
```bash
pip install ipywidgets
jupyter nbextension enable --py widgetsnbextension
```

---

## ✅ 受け入れ判定基準

### 必須 (MUST)
- [ ] 全テストケース1-8が成功
- [ ] 性能要件を満たす
- [ ] 出力ファイルが仕様通り

### 推奨 (SHOULD)  
- [ ] エラーハンドリングが適切
- [ ] ログ出力が分かりやすい
- [ ] ドキュメントが整備済み

### オプション (MAY)
- [ ] GUI要素が直感的
- [ ] 計算結果が手計算と一致
- [ ] 拡張性への配慮

---

**テスト実施者**: _______________  
**テスト実施日**: _______________  
**合否判定**: _______________

© 2025 Mizuho Digital Planning Team