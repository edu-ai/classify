# Terraform - Classify プロジェクト

Classify プロジェクトの AWS インフラを管理する Terraform 構成です。

## 📁 ファイル構成

```
terraform/
├── main.tf              # VPC, EKS, セキュリティグループ, ECR
├── data-stores.tf       # RDS PostgreSQL, ElastiCache Redis
├── variables.tf         # 変数定義
├── outputs.tf           # 出力値（エンドポイント、パスワード等）
├── terraform.tfvars     # 変数の値（開発環境用）
├── .gitignore          # terraform.tfstate を除外
└── README.md           # このファイル
```

---

## 🏗 作成されるリソース

### ネットワーク
- **VPC**: 10.0.0.0/16
- **Public Subnets**: 2つ (10.0.101.0/24, 10.0.102.0/24)
- **Private Subnets**: 2つ (10.0.1.0/24, 10.0.2.0/24)
- **NAT Gateway**: 1つ (single_nat_gateway = true)
- **Internet Gateway**: 1つ

### コンピュート
- **EKS Cluster**: Kubernetes 1.28
- **EKS Node Group**: t3.small × 2-4台

### データストア
- **RDS PostgreSQL (auth-service)**: db.t3.micro, 20GB
- **RDS PostgreSQL (photos-service)**: db.t3.micro, 20GB
- **ElastiCache Redis**: cache.t3.micro × 1

### コンテナレジストリ
- **ECR**: 5つのリポジトリ
  - classify-api-gateway
  - classify-auth-service
  - classify-photos-service
  - classify-blur-detection-service
  - classify-blur-worker

### セキュリティ
- **Security Groups**: RDS用、Redis用
- **IAM Roles**: EKS ノード用、IRSA用

---

## 🚀 使用方法

### 前提条件

1. **AWS CLI がインストール済み**
   ```bash
   aws --version
   ```

2. **AWS 認証情報が設定済み**
   ```bash
   aws configure
   ```

3. **Terraform がインストール済み** (>= 1.5)
   ```bash
   terraform version
   ```

---

### ステップ 1: 初期化

```bash
cd terraform
terraform init
```

これにより、必要なプロバイダ（AWS, Random）がダウンロードされます。

---

### ステップ 2: プランの確認

```bash
terraform plan
```

作成されるリソースを確認します。約 20-30個のリソースが作成されます。

---

### ステップ 3: 適用

```bash
terraform apply
```

確認プロンプトで `yes` を入力します。

**所要時間**: 20-30分
- VPC/サブネット: 2-3分
- RDS: 10-15分
- EKS: 10-15分
- ElastiCache: 5-10分

---

### ステップ 4: 出力値の確認

```bash
# すべての出力を表示
terraform output

# 特定の出力のみ表示
terraform output eks_cluster_name
terraform output redis_endpoint

# Sensitive な出力を表示
terraform output -raw auth_db_password
terraform output -raw auth_db_connection_string
```

---

## 📊 主要な出力値

### EKS 関連
```bash
# kubectl 設定コマンド
terraform output -raw configure_kubectl

# 実行例
$(terraform output -raw configure_kubectl)
kubectl get nodes
```

### RDS 関連
```bash
# Auth DB 接続情報
terraform output auth_db_endpoint
terraform output -raw auth_db_password
terraform output -raw auth_db_connection_string

# Photos DB 接続情報
terraform output photos_db_endpoint
terraform output -raw photos_db_password
terraform output -raw photos_db_connection_string
```

### ElastiCache 関連
```bash
terraform output redis_endpoint
terraform output redis_url
```

### ECR 関連
```bash
# ECR レジストリ URL
terraform output ecr_registry

# すべての ECR リポジトリ URL
terraform output ecr_repository_urls
```

---

## 🔐 Kubernetes Secrets の作成

Terraform outputs から Kubernetes Secrets を作成します。

### 方法 1: 手動で作成

```bash
# Auth DB パスワードを取得
AUTH_DB_PASSWORD=$(terraform output -raw auth_db_password)
AUTH_DB_ENDPOINT=$(terraform output -raw auth_db_endpoint | sed 's/:5432//')

# Photos DB パスワードを取得
PHOTOS_DB_PASSWORD=$(terraform output -raw photos_db_password)
PHOTOS_DB_ENDPOINT=$(terraform output -raw photos_db_endpoint | sed 's/:5432//')

# Redis エンドポイントを取得
REDIS_HOST=$(terraform output -raw redis_endpoint)

# k8s/02-secrets.yaml を編集
cd ../k8s
cp 02-secrets-template.yaml 02-secrets.yaml

# 置換 (macOS)
sed -i '' "s|REPLACE_WITH_PASSWORD|${AUTH_DB_PASSWORD}|g" 02-secrets.yaml
sed -i '' "s|REPLACE_WITH_ENDPOINT|${AUTH_DB_ENDPOINT}|g" 02-secrets.yaml
# ... 以下同様
```

### 方法 2: スクリプトで自動作成

```bash
cd terraform
./scripts/update-k8s-manifests.sh
```

（注: スクリプトは別途作成が必要）

---

## 🔄 更新とメンテナンス

### リソースの変更

```bash
# terraform.tfvars を編集
vim terraform.tfvars

# 変更内容を確認
terraform plan

# 適用
terraform apply
```

### ノード数のスケーリング

```bash
# terraform.tfvars で変更
node_group_desired_size = 3

# 適用
terraform apply
```

または kubectl で直接：

```bash
kubectl scale deployment/api-gateway -n classify --replicas=3
```

---

## 🗑 クリーンアップ

### すべてのリソースを削除

```bash
terraform destroy
```

確認プロンプトで `yes` を入力します。

**注意**:
- RDS のスナップショットは保持されません（`skip_final_snapshot = true`）
- 削除前に必要なデータをバックアップしてください

---

## 💰 コスト見積もり

### 月額コスト（ap-northeast-1, 2024年10月時点）

| リソース | 仕様 | 月額 (USD) |
|---------|------|-----------|
| EKS クラスター | 1つ | $73 |
| EKS ノード (t3.small) | 2台 × 24h | ~$30 |
| RDS (db.t3.micro) | 2台 × 20GB | ~$30 |
| ElastiCache (cache.t3.micro) | 1台 | ~$12 |
| NAT Gateway | 1つ + データ転送 | ~$35 |
| ALB | 1つ + データ転送 | ~$20 |
| **合計** | | **~$200** |

**コスト削減のヒント**:
- NAT Gateway: single_nat_gateway = true (すでに設定済み)
- RDS: Multi-AZ を無効 (すでに設定済み)
- EKS ノード: t3.small → t3.micro (ただし推奨しない)
- 使わない時は `terraform destroy`

---

## 🛠 トラブルシューティング

### terraform init エラー

```bash
# プロバイダのキャッシュをクリア
rm -rf .terraform .terraform.lock.hcl
terraform init
```

### terraform apply タイムアウト

RDS や EKS の作成には時間がかかります。最大30分待ちます。

### EKS クラスターに接続できない

```bash
# kubectl 設定を更新
aws eks update-kubeconfig --name classify-cluster --region ap-northeast-1

# 認証情報を確認
kubectl get nodes
```

### RDS に接続できない

- セキュリティグループが正しく設定されているか確認
- EKS ノードから RDS への接続が許可されているか確認

```bash
# セキュリティグループ ID を取得
terraform output | grep security_group
```

---

## 📝 本番環境への移行

開発環境（dev）から本番環境（prod）に移行する場合：

1. **terraform.tfvars を複製**
   ```bash
   cp terraform.tfvars prod.tfvars
   ```

2. **prod.tfvars を編集**
   ```hcl
   environment = "prod"

   # 本番環境設定
   single_nat_gateway = false        # NAT Gateway を冗長化
   rds_multi_az = true                # RDS を Multi-AZ に
   node_group_min_size = 3            # ノード数を増やす
   node_instance_types = ["t3.medium"] # インスタンスサイズ up
   ```

3. **workspace を使用（推奨）**
   ```bash
   terraform workspace new prod
   terraform workspace select prod
   terraform apply -var-file="prod.tfvars"
   ```

---

## 🔗 関連リンク

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform VPC Module](https://registry.terraform.io/modules/terraform-aws-modules/vpc/aws/latest)
- [Terraform EKS Module](https://registry.terraform.io/modules/terraform-aws-modules/eks/aws/latest)
- [AWS EKS ベストプラクティス](https://aws.github.io/aws-eks-best-practices/)
