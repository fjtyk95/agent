# 銀行取引最適化ワークフロー 要件定義書 v0.1

## 1. 要件定義書

### 1.1 背景・目的

振込不能をゼロにしつつ、振込⼿数料と社内資金移動コストを最小化する運用フローを構築する。財務企画・決済チームの作業を自動化/省力化し、意思決定をデータドリブン化する。

### 1.2 スコープ

| 項目     | 内容                           |
| ------ | ---------------------------- |
| 対象銀行   | みずほ・三菱UFJ・SMBC（各2支店）         |
| 取扱サービス | 総合振込(G) / ネット振込(N) / 給与振込(P) |
| 口座種別   | 円普通預金のみ                      |
| 入出金データ | 過去6 ヶ月実績 + モンテカルロ1,000本      |
| 最適化範囲  | 30営業日ローリングホライズン              |

### 1.3 利用者

* **財務企画担当**: CSV 入力・結果確認
* **決済チーム**: 振込 CSV のアップロード

### 1.4 用語定義

| 用語           | 説明                                             |
| ------------ | ---------------------------------------------- |
| Safety Stock | 次のリバランスまでの純流出 95% 分位額                          |
| MILP         | Mixed‑Integer Linear Programming（PuLP/CBC で解く） |

### 1.5 機能要件

| ID    | 要件                               | 優先度 |
| ----- | -------------------------------- | --- |
| FR‑01 | 現残高 CSV (balance\_snapshot) 取込   | ★★★ |
| FR‑02 | 入出金履歴 CSV (cashflow\_history) 読込 | ★★★ |
| FR‑03 | 手数料テーブル CSV (fee\_table) 読込      | ★★★ |
| FR‑04 | Safety Stock 自動計算 & グラフ表示        | ★★☆ |
| FR‑05 | MILP による資金移動最適化                  | ★★★ |
| FR‑06 | 振込 / 資金移動計画 CSV 出力               | ★★★ |
| FR‑07 | 実コスト vs 過去実績の比較チャート              | ★★☆ |
| FR‑08 | パラメータ (H, p, λ) GUI 入力           | ★★☆ |

### 1.6 非機能要件

| 区分     | 要件                                        |
| ------ | ----------------------------------------- |
| 性能     | CSV 1,000 行規模で 30 秒以内に解が返る                |
| 可用性    | Notebook がローカル PC 1 台で完結                  |
| 保守性    | Python 3.11 + Poetry で依存管理、型ヒント必須         |
| セキュリティ | 機密データはテスト用ダミーのみ、GitHub Enterprise 私有リポジトリ |

### 1.7 成功指標 (KPI)

1. 振込不能件数: **0 / 月**
2. コスト削減率: **‑10% 以上**（手数料 + 余剰資金コスト）
3. 実行時間: **≤30 s**

## 2. システム設計書

### 2.1 全体アーキテクチャ

```
Jupyter Notebook
├─ 01_data_load.py
├─ 02_safety_stock.py
├─ 03_optimise_milp.py
└─ 04_export_report.py
```

周辺 CSV は `/data/` フォルダ。成果物 (transfer\_plan.csv, charts/) は `/output/`。

### 2.2 データモデル

| ファイル                  | 主キー                                                        | 主要カラム          |
| --------------------- | ---------------------------------------------------------- | -------------- |
| bank\_master.csv      | bank\_id, branch\_id, service\_id                          | cut\_off\_time |
| fee\_table.csv        | from\_bank, service\_id, amount\_bin, to\_bank, to\_branch | fee            |
| balance\_snapshot.csv | bank\_id                                                   | balance        |
| cashflow\_history.csv | date, bank\_id, direction                                  | amount         |

### 2.3 アルゴリズム詳細

1. **Safety Stock**

   ```python
   def calc_safety(df_hist, horizon=30, q=0.95):
       # 各銀行×シナリオで純流出を計算し q 分位を返す
   ```
2. **MILP**

   * 変数:  x(i,j,s,d)=移動額,  B(i,d)=残高
   * 目的:  Σfee + λ × Σ残高不足ペナルティ
   * 制約:  残高更新式, B(i,d)≥0, 金額≧0

### 2.4 日次処理フロー

1. 09:00  balance\_snapshot.csv 更新
2. Notebook 実行: Load → Safety → MILP → Export
3. `transfer_plan.csv` を決済チームに共有
4. 実績 vs 計画を翌営業日差分検証

---

© 2025 Mizuho Digital Planning Team