# 🚀 Vercel デプロイガイド

## 📋 事前準備

### 1. Vercel アカウント準備
```bash
# Vercel CLI インストール
npm install -g vercel

# Vercelにログイン
vercel login
```

### 2. GitHubリポジトリの準備
```bash
# 変更をコミット
git add .
git commit -m "Add Vercel deployment configuration

🚀 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# リポジトリにプッシュ
git push origin main
```

## 🌐 Vercelデプロイ手順

### 方法1: CLI からデプロイ
```bash
# プロジェクトルートで実行
vercel

# 初回設定質問への回答:
# ? Set up and deploy "agent"? [Y/n] y
# ? Which scope do you want to deploy to? [自分のアカウント選択]
# ? Link to existing project? [N/y] n
# ? What's your project's name? bank-optimization
# ? In which directory is your code located? ./
```

### 方法2: Vercel Dashboard からデプロイ
1. https://vercel.com/dashboard にアクセス
2. "New Project" をクリック
3. GitHubリポジトリを選択
4. プロジェクト設定:
   - **Framework Preset**: Other
   - **Root Directory**: `./`
   - **Build Command**: (空のまま)
   - **Output Directory**: (空のまま)
   - **Install Command**: `pip install -r requirements.txt`

## ⚙️ 設定済みファイル

### 📄 vercel.json
```json
{
  "version": 2,
  "builds": [
    {
      "src": "web/api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "web/api/index.py"
    },
    {
      "src": "/(.*)",
      "dest": "web/api/index.py"
    }
  ],
  "env": {
    "PYTHONPATH": "."
  },
  "functions": {
    "web/api/index.py": {
      "maxDuration": 60
    }
  }
}
```

### 🐍 web/api/index.py (Vercelエントリーポイント)
- Flask アプリケーションのVercel用ラッパー
- 環境変数 `VERCEL=1` を自動設定
- パス解決をVercel環境に対応

### 📦 requirements.txt (Vercel最適化済み)
- 不要な依存関係を除去
- Vercelでサポートされているパッケージのみ

## 🔧 Vercel環境での変更点

### 1. ファイルシステム
```python
# ローカル環境
UPLOAD_FOLDER = Path('uploads')
OUTPUT_FOLDER = Path('../output')

# Vercel環境  
UPLOAD_FOLDER = Path('/tmp/uploads')
OUTPUT_FOLDER = Path('/tmp/output')
```

### 2. モジュールパス
```python
# ローカル環境
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Vercel環境
parent_dir = '/var/task'
```

### 3. データファイルパス
```python
# Vercel環境では /var/task/data/ からサンプルデータを読み込み
base_dir = '/var/task'
```

## 🎯 デプロイ後の確認

### 1. 基本動作確認
```bash
# デプロイ完了後のURL例
https://bank-optimization-abc123.vercel.app

# エンドポイント確認
curl https://bank-optimization-abc123.vercel.app/api/status
```

### 2. 機能テスト
1. **ダッシュボード**: `/` - 基本UI表示
2. **ファイルアップロード**: `/upload` - サンプルデータ設定
3. **最適化実行**: `/optimize` - パラメータ設定→実行
4. **結果表示**: `/results` - 結果確認
5. **KPI**: `/kpi` - 監視ダッシュボード

## ⚠️ Vercel制限事項

### 1. 実行時間制限
- **Free Plan**: 10秒
- **Pro Plan**: 60秒 (設定済み)
- 最適化計算が10秒を超える場合はPro Planが必要

### 2. ファイルシステム
- 書き込み可能: `/tmp` のみ
- 読み込み専用: プロジェクトファイル
- セッション間でファイル永続化不可

### 3. メモリ制限
- **Free Plan**: 1GB
- **Pro Plan**: 3GB
- 大きなデータセットは制限内で処理

## 🐛 トラブルシューティング

### よくあるエラー

**1. モジュールインポートエラー**
```
ModuleNotFoundError: No module named 'data_load'
```
→ `PYTHONPATH` 設定確認、`sys.path` 調整

**2. ファイル書き込みエラー**
```
OSError: [Errno 30] Read-only file system
```
→ `/tmp` ディレクトリ使用確認

**3. 実行時間超過**
```
Task timed out after 10.00 seconds
```
→ Pro Plan にアップグレード、または処理の最適化

### デバッグ方法
```bash
# Vercelログ確認
vercel logs [deployment-url]

# 関数ログ確認
vercel logs --follow
```

## 🔄 継続的デプロイ

### GitHub Integration
1. Vercel Dashboard でGitHub連携設定
2. `main` ブランチへのプッシュで自動デプロイ
3. プルリクエストでプレビューデプロイ

### 環境変数設定
```bash
# Vercel環境変数設定
vercel env add SECRET_KEY production
vercel env add DATABASE_URL production
```

## 📊 パフォーマンス最適化

### 1. 冷起動時間短縮
- 不要なインポートを削除
- 遅延インポートの活用
- 軽量ライブラリの選択

### 2. メモリ使用量削減
- データフレーム処理の最適化
- 不要な変数の削除
- ガベージコレクション

### 3. 計算時間短縮
- 問題サイズの制限
- アルゴリズムの最適化
- 並列処理の活用

---

## ✅ デプロイチェックリスト

- [ ] Vercel CLI インストール・ログイン
- [ ] GitHubリポジトリ準備
- [ ] vercel.json 設定確認
- [ ] requirements.txt 更新
- [ ] Vercel環境対応コード修正
- [ ] デプロイ実行
- [ ] 基本機能テスト
- [ ] パフォーマンステスト
- [ ] エラーハンドリング確認

---

**🎉 Vercelデプロイ準備完了！**

次のコマンドでデプロイを実行してください：

```bash
vercel
```

© 2025 Bank Optimization System - Powered by Vercel