# Architecture Document - Bank Transfer Optimization v0.2

## システム概要

銀行間振込最適化システムは、線形計画法(MILP)を用いて振込手数料とリスクを最小化する資金移動計画を自動生成するPythonツールキットです。

## アーキテクチャ図

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Input    │    │  Core Engine     │    │    Output       │
│                 │    │                  │    │                 │
│ • CSV Files     │───▶│ • MILP Optimizer │───▶│ • Transfer Plan │
│ • Bank Master   │    │ • Safety Stock   │    │ • Cost Charts   │
│ • Fee Table     │    │ • Fee Calculator │    │ • KPI Logs      │
│ • Cashflow      │    │ • Monitor        │    │                 │
│ • Balance       │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                        │                        │
        │              ┌────────────────────┐              │
        │              │   User Interface   │              │
        │              │                    │              │
        └──────────────│ • CLI Tool         │──────────────┘
                       │ • Jupyter Notebook │
                       │ • iPyWidgets       │
                       └────────────────────┘
```

## コンポーネント設計

### 1. データレイヤー (Data Layer)

#### `data_load.py`
- **責務**: CSV読み込み、データ検証、型変換
- **主要関数**:
  - `load_bank_master()`: 銀行・支店・サービス情報
  - `load_fee_table()`: 手数料テーブル
  - `load_balance()`: 残高スナップショット
  - `load_cashflow()`: キャッシュフロー履歴

#### `schemas.py`
- **責務**: データモデル定義
- **主要クラス**: `BankMaster`, `FeeTable`, `BalanceSnapshot`, `CashflowHistory`

### 2. ビジネスロジックレイヤー (Business Logic Layer)

#### `safety.py`
- **責務**: Safety Stock計算
- **アルゴリズム**: 過去データの分位数に基づくリスク推定
- **主要関数**: `calc_safety(horizon_days, quantile)`

#### `fee.py`
- **責務**: 振込手数料計算
- **主要クラス**: `FeeCalculator`
- **機能**: 金額帯・経路別の手数料検索

#### `optimise.py`
- **責務**: MILP最適化エンジン
- **使用ライブラリ**: PuLP (CBC Solver)
- **制約条件**:
  - 残高継続性
  - Safety Stock要件
  - Cut-off時刻制約
  - 非負制約

### 3. 制御・監視レイヤー (Control & Monitoring Layer)

#### `monitor.py`
- **責務**: 実行時間計測
- **主要クラス**: `Timer` (context manager)
- **主要関数**: `timed_run()`

#### `kpi_logger.py`
- **責務**: KPI永続化
- **出力形式**: JSONL (logs/kpi.jsonl)
- **記録項目**: timestamp, total_fee, total_shortfall, runtime_sec

### 4. 出力レイヤー (Output Layer)

#### `export.py`
- **責務**: 結果のCSV出力
- **フォーマット**: transfer_plan_YYYYMMDD_HHMMSS.csv

#### `charts.py`
- **責務**: 可視化
- **出力**: コスト比較棒グラフ (PNG)

### 5. ユーザーインターフェースレイヤー (UI Layer)

#### `bankoptimize/cli.py`
- **責務**: コマンドライン実行
- **機能**: 引数解析、パイプライン実行、エラーハンドリング

#### `interactive_notebook.ipynb`
- **責務**: インタラクティブGUI
- **技術**: ipywidgets, IPython display
- **機能**: リアルタイムパラメータ調整

## データフロー

### 1. 入力フェーズ
```
CSV Files → data_load → DataFrames → Validation → Typed Objects
```

### 2. 前処理フェーズ
```
Cashflow History → safety.calc_safety() → Safety Stock Dictionary
Fee Table → fee.build_fee_lookup() → Fee Lookup Dictionary
```

### 3. 最適化フェーズ
```
Inputs → optimise.build_model() → PuLP MILP → CBC Solver → Solution
```

### 4. 後処理フェーズ
```
Solution → export.to_csv() → Transfer Plan CSV
Solution → charts.plot_cost_comparison() → Cost Chart PNG
Metrics → kpi_logger.append_kpi() → KPI Log JSONL
```

## v0.2の技術的改善点

### 1. Cut-off時刻制約の実装

**課題**: 銀行営業時間による当日処理不可の考慮

**解決策**: バイナリ変数による日付制約
```python
effect_day[(bank, service, day)] = day if allow_same_day else next_day
```

### 2. パフォーマンス監視機能

**課題**: 大規模データでの実行時間把握

**解決策**: Context manager による自動計測
```python
with monitor.Timer("MILP Optimization"):
    result = optimise.build_model(**inputs)
```

### 3. インタラクティブGUI

**課題**: パラメータ調整の試行錯誤効率化

**解決策**: ipywidgets による即座フィードバック
```python
@widgets.interact
def update_optimization(horizon=30, quantile=0.95):
    # リアルタイム最適化実行
```

## セキュリティ考慮事項

### 1. データ保護
- 機密財務データの暗号化保存
- アクセスログ記録
- 個人情報匿名化

### 2. 実行環境
- サンドボックス実行推奨
- 依存関係の定期更新
- 入力データ検証強化

## スケーラビリティ

### 現在の制限
- 銀行数: ~100
- 日数: ~90日
- ソルバー: CBC (オープンソース)

### 将来の拡張
- 商用ソルバー対応 (Gurobi, CPLEX)
- 分散処理対応
- クラウドネイティブ実行

## テスト戦略

### 1. 単体テスト
- 各モジュールの個別機能テスト
- エッジケース検証
- モック使用によるI/O分離

### 2. 統合テスト
- モジュール間連携テスト
- サンプルデータでのエンドツーエンド
- パフォーマンステスト

### 3. 回帰テスト
- 既知解との比較
- 過去実績データでの検証
- CI/CDパイプライン組み込み

## 運用監視

### 1. KPIダッシュボード
- 実行頻度
- 平均実行時間
- 最適化効果 (コスト削減率)
- エラー発生率

### 2. アラート設定
- 実行時間異常
- 最適解発見失敗
- Safety Stock違反

### 3. ログ分析
- パフォーマンストレンド
- 使用パターン分析
- 改善ポイント特定

---

*© 2025 Mizuho Digital Planning Team*