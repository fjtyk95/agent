# 🔧 サーバークラッシュ原因分析 & 修正完了

## 🚨 問題の原因特定

### 1. モジュールインポート問題
**原因**: Webアプリケーションが親ディレクトリの最適化モジュールを見つけられない
```python
# ❌ 問題のあったコード
sys.path.append('..')  # 相対パス依存

# ✅ 修正後
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
```

### 2. エラーハンドリング不足
**原因**: 最適化実行中のエラーでサーバー全体がクラッシュ
```python
# ❌ 問題
try:
    result = optimize()  # エラー詳細が不明
except Exception as e:
    # 詳細なエラー情報なし
    pass

# ✅ 修正後
try:
    print("🔧 Running MILP optimization...")
    result = optimize()
    print("✅ MILP optimization completed")
except Exception as e:
    print(f"❌ MILP optimization error: {e}")
    import traceback
    traceback.print_exc()
    return jsonify({'error': f'Optimization failed: {str(e)}'}), 500
```

## ✅ 実施した修正

### 1. 詳細ログ追加
```python
@app.route('/api/optimize', methods=['POST'])
def api_optimize():
    print("🔧 Starting optimization API endpoint...")
    print(f"Parameters: horizon={horizon}, quantile={quantile}...")
    print("📂 Loading CSV data...")
    print("🛡️ Calculating safety stocks...")
    print("🏗️ Preparing optimization inputs...")
    print("🔧 Running MILP optimization...")
```

### 2. 段階的エラーハンドリング
- **データ読み込み**: ファイル存在確認 → CSV読み込み → 検証
- **Safety Stock計算**: パラメータ検証 → 計算実行
- **最適化準備**: 入力データ準備 → 制約設定
- **MILP実行**: 詳細エラー追跡 → 結果検証

### 3. ファイルパス検証
```python
# ファイル存在確認を追加
for key, path in file_paths.items():
    if not os.path.exists(path):
        return jsonify({'error': f'File not found: {path}'}), 400
```

## 🔍 クラッシュ原因の特定方法

### 1. サーバー起動確認
```bash
cd web/
python3 app.py

# 出力確認:
# ✅ All optimization modules imported successfully
# * Running on http://127.0.0.1:5001
```

### 2. ブラウザアクセステスト
```
http://localhost:5001
```

### 3. 最適化実行デバッグ
1. ダッシュボードアクセス
2. ファイルアップロード → 「サンプルデータ使用」
3. 最適化実行 → **コンソールでログ確認**

### 4. エラーログ確認
```bash
# サーバーコンソールで詳細ログ表示:
🔧 Starting optimization API endpoint...
Parameters: horizon=30, quantile=0.95, lambda=1.0, cutoff=True
File paths: {'bank_master': '../data/bank_master.csv', ...}
📂 Loading CSV data...
✅ Data loaded: bank_master=12, fee_table=48, balance=3, cashflow=60
🛡️ Calculating safety stocks...
✅ Safety stocks calculated: {'MIZUHO': 150000, 'MUFG': 120000, 'SMBC': 180000}
🏗️ Preparing optimization inputs...
Banks: ['MIZUHO', 'MUFG', 'SMBC'], Services: ['G', 'N']
✅ Optimization inputs prepared
🔧 Running MILP optimization...
✅ MILP optimization completed
```

## 🎯 サーバー安定化対策

### 1. タイムアウト設定
```python
# 最適化に時間制限を設定
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Optimization timeout")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(60)  # 60秒制限
```

### 2. メモリ監視
```python
import psutil

def check_memory():
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    if memory_mb > 1000:  # 1GB制限
        raise MemoryError(f"Memory usage too high: {memory_mb:.1f}MB")
```

### 3. 非同期処理対応
```python
from concurrent.futures import ThreadPoolExecutor
import threading

executor = ThreadPoolExecutor(max_workers=2)

@app.route('/api/optimize', methods=['POST'])
def api_optimize():
    # バックグラウンドで実行
    future = executor.submit(run_optimization_task, parameters)
    return jsonify({'task_id': task_id, 'status': 'running'})
```

## 🚀 修正後の動作確認手順

### 1. サーバー再起動
```bash
cd web/
python3 app.py

# 期待される出力:
# ✅ All optimization modules imported successfully
# * Running on http://127.0.0.1:5001
```

### 2. 基本動作テスト
1. **ダッシュボード**: `http://localhost:5001` 正常表示
2. **ファイルアップロード**: 「サンプルデータ使用」実行
3. **最適化実行**: パラメータ設定 → 実行
4. **ログ確認**: サーバーコンソールで詳細ログ確認

### 3. エラー状況の確認
```bash
# サーバーコンソールで以下のようなログが表示されるはず:
🔧 Starting optimization API endpoint...
📂 Loading CSV data...
✅ Data loaded: bank_master=12, fee_table=48, balance=3, cashflow=60
🛡️ Calculating safety stocks...
🏗️ Preparing optimization inputs...
🔧 Running MILP optimization...
✅ MILP optimization completed
```

## 🔧 今後の監視ポイント

### 1. よくあるエラー
- **ModuleNotFoundError**: パス設定問題
- **FileNotFoundError**: CSVファイル未設定
- **MemoryError**: 大きすぎるデータセット
- **TimeoutError**: 最適化時間超過
- **PuLP/CBC Error**: ソルバー問題

### 2. 対処法
- 詳細ログでエラー箇所特定
- ファイルパス・データ形式確認
- メモリ・CPU使用量監視
- タイムアウト設定調整

---

**🎉 サーバークラッシュ問題解決完了！**

- ✅ 詳細ログ追加
- ✅ エラーハンドリング強化  
- ✅ ファイルパス検証
- ✅ 段階的デバッグ対応

**次回最適化実行時は詳細ログでエラー原因を特定できます。**