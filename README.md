# Agent Repository

このリポジトリは **inter-bank transfer optimisation** を行う小さなツールキットです。  
CSV から取引データを読み込み、各銀行の Safety Stock を推定し、線形計画法で振込手数料を最小化する送金計画を作成します。チャート表示とエクスポート機能で結果を可視化・保存できます。

## v0.2 新機能

- 🎛️ **インタラクティブGUI**: Jupyter Notebook でパラメータをリアルタイム調整
- ⏱️ **パフォーマンス監視**: 実行時間とKPIの自動ロギング機能
- 🕐 **Cut-off時刻制約**: 銀行営業時間を考慮した最適化
- 🛠️ **CLI コマンド**: `python -m agent.bankoptimize.cli run` で簡単実行
- 🧪 **充実したテスト**: 単体・統合・エンドツーエンドテストを完備

---

## モジュール一覧

| ファイル                 | 役割 |
|--------------------------|------|
| `schemas.py`             | CSV 行を表す dataclass 群 |
| `data_load.py`           | CSV 読み込み（dtype & カラム検証） |
| `fee.py`                 | `FeeCalculator` — 振込手数料の検索 |
| `safety.py`              | `calc_safety` — Safety Stock 計算 |
| `optimise.py`            | PuLP で MILP を構築・解く |
| `export.py`              | 送金計画 CSV 出力 |
| `charts.py`              | `plot_cost_comparison` 棒グラフ生成 |
| `monitor.py`             | 実行時間の計測 (`Timer`, `timed_run`) |
| `kpi_logger.py`          | KPI を JSONL に永続化 |
| `interactive_notebook.ipynb` | 最適化ワークフローのデモ |
| `bankoptimize/cli.py`        | コマンドライン実行インターフェース |

---

## 🚀 クイックスタート

### CLI実行

```bash
# データファイルを用意
mkdir -p data output

# 最適化実行
python -m agent.bankoptimize.cli run \
  --balance data/balance_snapshot.csv \
  --cash data/cashflow_history.csv \
  --out output/transfer_plan.csv \
  --horizon 30 \
  --quantile 0.95
```

### Jupyter Notebook実行

```bash
# Jupyter Notebook起動
jupyter lab agent/interactive_notebook.ipynb

# GUI操作でパラメータ調整 → 最適化実行 → 結果確認
```

---

## 📊 出力ファイル

- `output/transfer_plan_YYYYMMDD_HHMMSS.csv`: 送金計画
- `output/cost_comparison.png`: コスト比較チャート
- `logs/kpi.jsonl`: KPIログ（実行時間、総コスト、shortfall件数）

---

## 🧪 テスト実行

```bash
# 全テスト実行
pytest agent/tests/ -v

# 最適化特化テスト
pytest agent/tests/test_optimise.py -v

# 統合テスト
pytest agent/tests/test_integration.py -v
```

---

## Dataclass schema 例

```python
@dataclass
class BankMaster:
    bank_id: str
    branch_id: str
    service_id: str
    cut_off_time: str  # HH:MM
