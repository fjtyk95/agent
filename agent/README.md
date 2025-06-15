# Agent Repository

このリポジトリは **inter-bank transfer optimisation** を行う小さなツールキットです。  
CSV から取引データを読み込み、各銀行の Safety Stock を推定し、線形計画法で振込手数料を最小化する送金計画を作成します。チャート表示とエクスポート機能で結果を可視化・保存できます。

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

---

## Dataclass schema 例

```python
@dataclass
class BankMaster:
    bank_id: str
    branch_id: str
    service_id: str
    cut_off_time: str  # HH:MM
