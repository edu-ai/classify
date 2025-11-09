# Kubernetes Manifests - Classify Project

This directory contains Kubernetes manifest files for deploying the Classify project.

## File Structure

```
k8s/
├── 00-namespace.yaml              # Namespace definition
├── 01-configmap.yaml              # Environment variable configuration
├── 02-secrets-template.yaml       # Secret template (requires replacement)
├── 03-api-gateway.yaml            # API Gateway Deployment & Service
├── 04-auth-service.yaml           # Auth Service Deployment & Service
├── 05-photos-service.yaml         # Photos Service Deployment & Service
├── 06-blur-detection-service.yaml # Blur Detection Service Deployment & Service
├── 07-blur-worker.yaml            # Blur Worker Deployment
└── 08-ingress.yaml                # Ingress (ALB)
```

The numeric prefixes in filenames indicate the application order.

---

## Deployment Steps

### Prerequisites

1. **EKS cluster is already created**
2. **kubectl is configured**
   ```bash
   aws eks update-kubeconfig --name classify-cluster --region ap-northeast-1
   ```
3. **AWS Load Balancer Controller is installed**
4. **Docker images are pushed to ECR**
5. **Terraform is applied** (RDS and ElastiCache endpoints obtained)

---

### Step 1: Create Secrets

Copy `02-secrets-template.yaml` and replace with actual values.

```bash
# Copy the template
cp 02-secrets-template.yaml 02-secrets.yaml

# Replace the following values:
# - REPLACE_WITH_PASSWORD (auth/photos DB password)
# - REPLACE_WITH_ENDPOINT (auth/photos DB endpoint)
# - REPLACE_WITH_GOOGLE_CLIENT_ID
# - REPLACE_WITH_GOOGLE_CLIENT_SECRET
# - REPLACE_WITH_NEXTAUTH_SECRET (generate with: openssl rand -base64 32)
```

**How to obtain required values**:

```bash
# Get RDS endpoints from Terraform outputs
cd terraform
terraform output auth_db_endpoint
terraform output photos_db_endpoint

# Get Google OAuth credentials from Google Cloud Console
# Generate NextAuth Secret
openssl rand -base64 32
```

---

### Step 2: Update ConfigMap

Replace the ElastiCache endpoint in `01-configmap.yaml`.

```bash
# Get ElastiCache endpoint from Terraform outputs
cd terraform
terraform output redis_endpoint

# Edit 01-configmap.yaml
# Replace REDIS_HOST: "REPLACE_WITH_ELASTICACHE_ENDPOINT" with the actual endpoint
```

---

### Step 3: Update Deployment Manifests

Replace the ECR registry in all Deployments.

```bash
# Get ECR registry URL
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="ap-northeast-1"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Replace in all Deployments
for file in k8s/03-*.yaml k8s/04-*.yaml k8s/05-*.yaml k8s/06-*.yaml k8s/07-*.yaml; do
  sed -i.bak "s|REPLACE_WITH_ECR_REGISTRY|${ECR_REGISTRY}|g" "$file"
  rm "${file}.bak"
done
```

---

### Step 4: Apply Manifests

Apply in order.

```bash
# Create Namespace
kubectl apply -f k8s/00-namespace.yaml

# Create ConfigMap and Secret
kubectl apply -f k8s/01-configmap.yaml
kubectl apply -f k8s/02-secrets.yaml  # Note: 02-secrets.yaml (not the template)

# Deploy services
kubectl apply -f k8s/03-api-gateway.yaml
kubectl apply -f k8s/04-auth-service.yaml
kubectl apply -f k8s/05-photos-service.yaml
kubectl apply -f k8s/06-blur-detection-service.yaml
kubectl apply -f k8s/07-blur-worker.yaml

# Create Ingress (ALB will be automatically created)
kubectl apply -f k8s/08-ingress.yaml
```

**Batch apply** (recommended):

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

## Deployment Verification

### Check Pod Status

```bash
kubectl get pods -n classify
```

Verify that all Pods are in `Running` state.

### Check Services

```bash
kubectl get svc -n classify
```

### Check Ingress and ALB

```bash
kubectl get ingress -n classify

# Get ALB DNS name
kubectl get ingress classify-ingress -n classify -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### Check Logs

```bash
# Logs for a specific Pod
kubectl logs -n classify <pod-name>

# API Gateway logs
kubectl logs -n classify -l app=api-gateway --tail=100

# Monitor logs continuously
kubectl logs -n classify -l app=api-gateway -f
```

---

## Troubleshooting

### Pod Won't Start

```bash
# Check Pod details
kubectl describe pod -n classify <pod-name>

# Check events
kubectl get events -n classify --sort-by='.lastTimestamp'

# For ImagePullBackOff, check ECR access permissions
```

### Database Connection Errors

```bash
# Verify Secret is correctly set
kubectl get secret classify-secrets -n classify -o yaml

# Verify RDS security group allows access from EKS nodes
```

### Redis Connection Errors

```bash
# Verify ConfigMap is correctly set
kubectl get configmap classify-config -n classify -o yaml

# Verify ElastiCache security group allows access from EKS nodes
```

---

## Updates and Rollback

### Update Images

```bash
# After building new images and pushing to ECR
kubectl rollout restart deployment/api-gateway -n classify
kubectl rollout restart deployment/auth-service -n classify
kubectl rollout restart deployment/photos-service -n classify
kubectl rollout restart deployment/blur-detection-service -n classify
kubectl rollout restart deployment/blur-worker -n classify
```

### Check Rollout Status

```bash
kubectl rollout status deployment/api-gateway -n classify
```

### Rollback

```bash
kubectl rollout undo deployment/api-gateway -n classify
```

---

## Resource Configuration

### Replicas

| Service | Replicas | Reason |
|---------|---------|--------|
| api-gateway | 2 | High availability |
| auth-service | 2 | High availability |
| photos-service | 2 | High availability |
| blur-detection-service | 2 | High availability |
| blur-worker | 1 | Background job processing |

### Resource Limits

| Service | Request (CPU/Memory) | Limit (CPU/Memory) |
|---------|---------------------|-------------------|
| api-gateway | 100m / 256Mi | 500m / 512Mi |
| auth-service | 100m / 256Mi | 500m / 512Mi |
| photos-service | 100m / 256Mi | 500m / 512Mi |
| blur-detection-service | 200m / 512Mi | 1000m / 1Gi |
| blur-worker | 200m / 512Mi | 1000m / 1Gi |

---

## Security

### Secret Management

- **For production environments**, it is recommended to use AWS Secrets Manager or AWS Systems Manager Parameter Store
- **Do not commit to Git**: Add `02-secrets.yaml` to `.gitignore`

```bash
echo "k8s/02-secrets.yaml" >> .gitignore
```

### RBAC (Role-Based Access Control)

The current configuration does not include RBAC. For production environments, it is recommended to add:

- ServiceAccount creation
- Role/RoleBinding configuration
- Pod Security Standards application

---

## Scaling

### Manual Scaling

```bash
# Increase Replicas
kubectl scale deployment/api-gateway -n classify --replicas=3
```

### Horizontal Pod Autoscaler (HPA)

For future HPA configuration:

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

## Cleanup

Delete all resources:

```bash
kubectl delete namespace classify
```

Delete individually:

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

## Notes

1. **Database Migration**: For the initial deployment, you need to create tables in RDS
   - `backend/auth-service/init.sql`
   - `backend/photos-service/init.sql`

2. **Environment Variables**: Verify that all required environment variables are set for each service

3. **Health Checks**: All services must implement the `/health` endpoint

4. **Load Balancer**: Verify that AWS Load Balancer Controller is correctly installed

---

## Related Links

- [Kubernetes Official Documentation](https://kubernetes.io/docs/home/)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [Amazon EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/)
