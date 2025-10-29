# Kubernetes マニフェスト - Classify プロジェクト

このディレクトリには、Classify プロジェクトを Kubernetes にデプロイするためのマニフェストファイルが含まれています。

## 📁 ファイル構成

```
k8s/
├── 00-namespace.yaml              # Namespace 定義
├── 01-configmap.yaml              # 環境変数設定
├── 02-secrets-template.yaml       # Secret テンプレート（要置換）
├── 03-api-gateway.yaml            # API Gateway Deployment & Service
├── 04-auth-service.yaml           # Auth Service Deployment & Service
├── 05-photos-service.yaml         # Photos Service Deployment & Service
├── 06-blur-detection-service.yaml # Blur Detection Service Deployment & Service
├── 07-blur-worker.yaml            # Blur Worker Deployment
└── 08-ingress.yaml                # Ingress (ALB)
```

ファイル名の数字プレフィックスは適用順序を示します。

---

## 🚀 デプロイ手順

### 前提条件

1. **EKS クラスタが作成済み**
2. **kubectl が設定済み**
   ```bash
   aws eks update-kubeconfig --name classify-cluster --region ap-northeast-1
   ```
3. **AWS Load Balancer Controller がインストール済み**
4. **ECR に Docker イメージがプッシュ済み**
5. **Terraform が適用済み** (RDS, ElastiCache のエンドポイント取得済み)

---

### ステップ 1: Secrets の作成

`02-secrets-template.yaml` をコピーして実際の値に置き換えます。

```bash
# テンプレートをコピー
cp 02-secrets-template.yaml 02-secrets.yaml

# 以下の値を置き換える
# - REPLACE_WITH_PASSWORD (auth/photos DB パスワード)
# - REPLACE_WITH_ENDPOINT (auth/photos DB エンドポイント)
# - REPLACE_WITH_GOOGLE_CLIENT_ID
# - REPLACE_WITH_GOOGLE_CLIENT_SECRET
# - REPLACE_WITH_NEXTAUTH_SECRET (openssl rand -base64 32 で生成)
```

**必要な値の取得方法**:

```bash
# Terraform outputs から RDS エンドポイントを取得
cd terraform
terraform output auth_db_endpoint
terraform output photos_db_endpoint

# Google OAuth 認証情報は Google Cloud Console から取得
# NextAuth Secret の生成
openssl rand -base64 32
```

---

### ステップ 2: ConfigMap の更新

`01-configmap.yaml` で ElastiCache エンドポイントを置き換えます。

```bash
# Terraform outputs から ElastiCache エンドポイントを取得
cd terraform
terraform output redis_endpoint

# 01-configmap.yaml を編集
# REDIS_HOST: "REPLACE_WITH_ELASTICACHE_ENDPOINT" を実際のエンドポイントに置き換え
```

---

### ステップ 3: Deployment マニフェストの更新

すべての Deployment で ECR レジストリを置き換えます。

```bash
# ECR レジストリ URL を取得
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="ap-northeast-1"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# すべての Deployment で置き換え
for file in k8s/03-*.yaml k8s/04-*.yaml k8s/05-*.yaml k8s/06-*.yaml k8s/07-*.yaml; do
  sed -i.bak "s|REPLACE_WITH_ECR_REGISTRY|${ECR_REGISTRY}|g" "$file"
  rm "${file}.bak"
done
```

---

### ステップ 4: マニフェストの適用

順番に適用します。

```bash
# Namespace 作成
kubectl apply -f k8s/00-namespace.yaml

# ConfigMap と Secret を作成
kubectl apply -f k8s/01-configmap.yaml
kubectl apply -f k8s/02-secrets.yaml  # 注意: 02-secrets.yaml (テンプレートではない)

# サービスをデプロイ
kubectl apply -f k8s/03-api-gateway.yaml
kubectl apply -f k8s/04-auth-service.yaml
kubectl apply -f k8s/05-photos-service.yaml
kubectl apply -f k8s/06-blur-detection-service.yaml
kubectl apply -f k8s/07-blur-worker.yaml

# Ingress を作成 (ALB が自動的に作成される)
kubectl apply -f k8s/08-ingress.yaml
```

**一括適用** (推奨):

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-configmap.yaml
kubectl apply -f k8s/02-secrets.yaml
kubectl apply -f k8s/03-api-gateway.yaml \
               -f k8s/04-auth-service.yaml \
               -f k8s/05-photos-service.yaml \
               -f k8s/06-blur-detection-service.yaml \
               -f k8s/07-blur-worker.yaml \
               -f k8s/08-ingress.yaml
```

---

## 🔍 デプロイ確認

### Pod の状態確認

```bash
kubectl get pods -n classify
```

すべての Pod が `Running` 状態になることを確認します。

### Service の確認

```bash
kubectl get svc -n classify
```

### Ingress と ALB の確認

```bash
kubectl get ingress -n classify

# ALB の DNS 名を取得
kubectl get ingress classify-ingress -n classify -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### ログ確認

```bash
# 特定の Pod のログ
kubectl logs -n classify <pod-name>

# API Gateway のログ
kubectl logs -n classify -l app=api-gateway --tail=100

# 継続的にログを監視
kubectl logs -n classify -l app=api-gateway -f
```

---

## 🛠 トラブルシューティング

### Pod が起動しない場合

```bash
# Pod の詳細を確認
kubectl describe pod -n classify <pod-name>

# イベントを確認
kubectl get events -n classify --sort-by='.lastTimestamp'

# ImagePullBackOff の場合、ECR へのアクセス権限を確認
```

### データベース接続エラー

```bash
# Secret が正しく設定されているか確認
kubectl get secret classify-secrets -n classify -o yaml

# RDS セキュリティグループで EKS ノードからのアクセスを許可しているか確認
```

### Redis 接続エラー

```bash
# ConfigMap が正しく設定されているか確認
kubectl get configmap classify-config -n classify -o yaml

# ElastiCache セキュリティグループで EKS ノードからのアクセスを許可しているか確認
```

---

## 🔄 更新とロールバック

### イメージの更新

```bash
# 新しいイメージをビルドして ECR にプッシュ後
kubectl rollout restart deployment/api-gateway -n classify
kubectl rollout restart deployment/auth-service -n classify
kubectl rollout restart deployment/photos-service -n classify
kubectl rollout restart deployment/blur-detection-service -n classify
kubectl rollout restart deployment/blur-worker -n classify
```

### ロールアウト状態の確認

```bash
kubectl rollout status deployment/api-gateway -n classify
```

### ロールバック

```bash
kubectl rollout undo deployment/api-gateway -n classify
```

---

## 📊 リソース構成

### Replicas

| サービス | Replicas | 理由 |
|---------|---------|------|
| api-gateway | 2 | 高可用性 |
| auth-service | 2 | 高可用性 |
| photos-service | 2 | 高可用性 |
| blur-detection-service | 2 | 高可用性 |
| blur-worker | 1 | バックグラウンドジョブ処理 |

### リソース制限

| サービス | Request (CPU/Memory) | Limit (CPU/Memory) |
|---------|---------------------|-------------------|
| api-gateway | 100m / 256Mi | 500m / 512Mi |
| auth-service | 100m / 256Mi | 500m / 512Mi |
| photos-service | 100m / 256Mi | 500m / 512Mi |
| blur-detection-service | 200m / 512Mi | 1000m / 1Gi |
| blur-worker | 200m / 512Mi | 1000m / 1Gi |

---

## 🔐 セキュリティ

### Secret の管理

- **本番環境では** AWS Secrets Manager または AWS Systems Manager Parameter Store を使用することを推奨
- **Git にコミットしない**: `02-secrets.yaml` は `.gitignore` に追加

```bash
echo "k8s/02-secrets.yaml" >> .gitignore
```

### RBAC (Role-Based Access Control)

現在の構成では RBAC は設定していません。本番環境では以下を追加することを推奨:

- ServiceAccount の作成
- Role/RoleBinding の設定
- Pod Security Standards の適用

---

## 📈 スケーリング

### 手動スケーリング

```bash
# Replicas を増やす
kubectl scale deployment/api-gateway -n classify --replicas=3
```

### Horizontal Pod Autoscaler (HPA)

将来的に HPA を設定する場合:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
  namespace: classify
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## 🗑 クリーンアップ

すべてのリソースを削除:

```bash
kubectl delete namespace classify
```

個別に削除:

```bash
kubectl delete -f k8s/08-ingress.yaml
kubectl delete -f k8s/07-blur-worker.yaml
kubectl delete -f k8s/06-blur-detection-service.yaml
kubectl delete -f k8s/05-photos-service.yaml
kubectl delete -f k8s/04-auth-service.yaml
kubectl delete -f k8s/03-api-gateway.yaml
kubectl delete -f k8s/01-configmap.yaml
kubectl delete -f k8s/02-secrets.yaml
kubectl delete -f k8s/00-namespace.yaml
```

---

## 📝 注意事項

1. **Database Migration**: 初回デプロイ時は、RDS にテーブルを作成する必要があります
   - `backend/auth-service/init.sql`
   - `backend/photos-service/init.sql`

2. **Environment Variables**: 各サービスで必要な環境変数がすべて設定されているか確認してください

3. **Health Checks**: すべてのサービスが `/health` エンドポイントを実装している必要があります

4. **Load Balancer**: AWS Load Balancer Controller が正しくインストールされていることを確認してください

---

## 🔗 関連リンク

- [Kubernetes 公式ドキュメント](https://kubernetes.io/ja/docs/home/)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [Amazon EKS ユーザーガイド](https://docs.aws.amazon.com/ja_jp/eks/latest/userguide/)
