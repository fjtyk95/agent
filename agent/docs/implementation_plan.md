# 銀行取引最適化ワークフロー 実装計画書 v0.2

## 3. 実装計画

### 3.1 技術スタック

* Python 3.11 / JupyterLab
* NumPy / Pandas / PuLP(CBC)
* Matplotlib (可視化)
* GitHub Enterprise  + Poetry

### 3.2 タスク分解（Codex に細分化）

| #  | モジュール            | Codex 指示例                                             |
| -- | ---------------- | ----------------------------------------------------- |
| 1  | **CSV スキーマ定義**   | "Generate dataclass schemas for the four CSVs"        |
| 2  | **データロード関数**     | "Write a function to read CSVs into typed DataFrames" |
| 3  | **Safety Stock** | "Implement calc\_safety using quantile"               |
| 4  | **手数料計算ユーティリティ** | "Create FeeCalculator class with get\_fee()"          |
| 5  | **MILP モデル**     | "Build PuLP model with variables x,B and constraints" |
| 6  | **結果エクスポート**     | "Output transfer\_plan.csv with columns..."           |
| 7  | **グラフ生成**        | "Plot bar chart of cost comparison"                   |
| 8  | **パラメータ GUI**    | "Add ipywidgets sliders for horizon, q, λ"            |
| 9  | **単体テスト**        | "Create pytest for calc\_safety edge cases"           |
| 10 | **README 作成**    | "Draft README explaining setup & run"                 |

### 3.3 マイルストーン & Timeline (暫定)

| 週  | 完了目標       | Deliverable                         |
| -- | ---------- | ----------------------------------- |
| W1 | タスク #1‑#3  | calc\_safety.py, schemas.py         |
| W2 | タスク #4‑#5  | optimise\_milp.py                   |
| W3 | タスク #6‑#7  | transfer\_plan.csv, charts/         |
| W4 | タスク #8‑#10 | interactive\_notebook.ipynb, README |

### 3.4 リスク & 対応策

| リスク         | 影響              | 対応                         |
| ----------- | --------------- | -------------------------- |
| MILP 計算時間超過 | 実務で使えない         | サービス削減 / 金額帯集約 / Gurobi 評価 |
| 入出金分布の変化    | Safety Stock 過小 | 月次でモデル再学習 & アラート           |

### 3.5 移行・テスト計画

1. **バックテスト**: 過去 6 ヶ月実データで KPI 計測
2. **ユーザーテスト**: 財務担当が Notebook を操作、手動フローと比較
3. **リリース判定**: KPI 達成 & 担当者レビュー合格で本番運用へ

## 5. v0.2 追加実装計画 & GitHub 運用指針

### 5.1 目的と改善点（v0.1 → v0.2）

| 未達/改善ポイント                 | 対応方針                                                                                               |
| ------------------------- | -------------------------------------------------------------------------------------------------- |
| **GUI (ipywidgets)** が限定的 | - interactive\_notebook へ `widgets` 追加<br>- Horizon / Quantile / λ / Cut‑off ON/OFF をリアルタイム反映      |
| **実行時間 & KPI ロギング** が未実装  | - `monitor.py` で `time.perf_counter` 計測<br>- `kpi_logger.py` に JSON ログ (実行秒・総コスト・Shortfall 件数) を追記 |
| **Cut‑off 時刻制約** 未考慮      | - MILP にバイナリ変数 `is_next_day[i,j,s,d]` を導入し当日処理不可なら x=0                                             |
| **統合テスト不足**               | - `tests/test_optimise.py` でミニケースを自動検証                                                             |

### 5.2 ブランチ & PR フロー（コンフリクト回避）

1. **main**: 運用ブランチ（保護設定, squash‑merge）
2. **dev**: 日常開発統合。CI (pytest + mypy) 必須。
3. **feature/XYZ**: 個別タスク用。Codex 指示は *必ず* `feature/` ブランチ上で実行。
4. **PR 規約**:

   * `feat:` / `fix:` / `docs:` prefix
   * PR テンプレート: *目的* / *変更点* / *テスト結果*

### 5.3 タスク一覧（Codex 指示例付き）

| #  | ブランチ名                     | 新規ファイル                        | Codex 指示(抜粋)                                                 |
| -- | ------------------------- | ----------------------------- | ------------------------------------------------------------ |
| 11 | feature/gui‑widgets       | `ui_widgets.py`, ipynb        | "Add ipywidgets sliders ... write ui\_widgets.py"            |
| 12 | feature/monitoring        | `monitor.py`, `kpi_logger.py` | "Wrap main() with timing & JSON log"                         |
| 13 | feature/cutoff‑constraint | modify `optimise.py` 追加ファイル不要 | "Extend PuLP model to respect cut‑off with binaries"         |
| 14 | feature/integration‑test  | `tests/test_optimise.py`      | "Create pytest that loads mini CSV and asserts no shortfall" |
| 15 | feature/docs‑update       | `README.md`, ARCH.md          | "Update README for v0.2 features"                            |

### 5.4 リリース判定 (追加)

* GUI: 主要パラメータ変更で再計算が 3 秒以内に完了
* KPI ログ: `/logs/kpi_*.json` が毎実行生成
* Cut‑off 満たさない送金が 0 件

### 5.5 Task 15 分割案 (Conflict‑Free CLI Implementation)

| サブタスク    | ブランチ例                | 目的                                   | 典型ファイル & 差分                                    | 備考                                  |
| -------- | -------------------- | ------------------------------------ | ---------------------------------------------- | ----------------------------------- |
| **15‑a** | feature/cli‑pkg‑init | パッケージ初期化 & 依存掃除                      | `bankoptimize/__init__.py` 新規 or 更新            | 他タスクに影響無し                           |
| **15‑b** | feature/cli‑skeleton | `cli.py` 骨格 (argparse 雛形, main stub) | `bankoptimize/cli.py` **新規**                   | 実行時は pass; CI 通過可                   |
| **15‑c** | feature/cli‑wire     | パイプライン関数を呼び出す `run()` 実装             | `cli.py` 10‑15 行のみ変更                           | data\_load→optimise→export 直列呼び出し   |
| **15‑d** | feature/cli‑scripts  | Poetry script 定義                     | `pyproject.toml` `[tool.poetry.scripts]` 1 行追加 | **単独コミット推奨** (衝突しやすい)               |
| **15‑e** | feature/cli‑tests    | End‑to‑End CLI テスト追加                 | `tests/test_cli.py` **新規**                     | `subprocess.run([...])` で exit 0 確認 |
| **15‑f** | feature/cli‑docs     | README 追記                            | `README.md` の Usage セクション更新                    | Docs 専用コミット                         |

> **ブランチ運用 Tips**
>
> 1. 各サブタスク完了後、即 PR → squash merge で **dev** へ。
> 2. `pyproject.toml` は **15‑d** の 1コミットだけで変更。別タスクで依存追加がある場合は、`[[tool.poetry.group.dev.dependencies]]` など別ブロックに追記し、コンフリクトを避ける。
> 3. `feature/cli‑wire` では既存モジュールの public API のみ使用し、実装を触らない。
> 4. 最後に `release/v0.2` へまとめて PR → CI 通過 → main マージ。

これにより **新規ファイル → 既存ファイル** の順で差分を小さく保ち、`pyproject.toml` の衝突も最小限に抑えられます。

---

© 2025 Mizuho Digital Planning Team