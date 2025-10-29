# Terraform - Classify Project

Terraform configuration to manage AWS infrastructure for the Classify project.

## 📁 File Structure

```
terraform/
├── main.tf              # VPC, EKS, Security Groups, ECR
├── data-stores.tf       # RDS PostgreSQL, ElastiCache Redis
├── variables.tf         # Variable definitions
├── outputs.tf           # Output values (endpoints, passwords, etc.)
├── terraform.tfvars     # Variable values (for development environment)
├── .gitignore          # Excludes terraform.tfstate
└── README.md           # This file
```

---

## 🏗 Resources Created

### Network
- **VPC**: 10.0.0.0/16
- **Public Subnets**: 2 subnets (10.0.101.0/24, 10.0.102.0/24)
- **Private Subnets**: 2 subnets (10.0.1.0/24, 10.0.2.0/24)
- **NAT Gateway**: 1 gateway (single_nat_gateway = true)
- **Internet Gateway**: 1 gateway

### Compute
- **EKS Cluster**: Kubernetes 1.28
- **EKS Node Group**: t3.small × 2-4 nodes

### Data Stores
- **RDS PostgreSQL (auth-service)**: db.t3.micro, 20GB
- **RDS PostgreSQL (photos-service)**: db.t3.micro, 20GB
- **ElastiCache Redis**: cache.t3.micro × 1

### Container Registry
- **ECR**: 5 repositories
  - classify-api-gateway
  - classify-auth-service
  - classify-photos-service
  - classify-blur-detection-service
  - classify-blur-worker

### Security
- **Security Groups**: For RDS and Redis
- **IAM Roles**: For EKS nodes and IRSA

---

## 🚀 Usage

### Prerequisites

1. **AWS CLI is installed**
   ```bash
   aws --version
   ```

2. **AWS credentials are configured**
   ```bash
   aws configure
   ```

3. **Terraform is installed** (>= 1.5)
   ```bash
   terraform version
   ```

---

### Step 1: Initialize

```bash
cd terraform
terraform init
```

This will download the required providers (AWS, Random).

---

### Step 2: Review the Plan

```bash
terraform plan
```

Review the resources to be created. Approximately 20-30 resources will be created.

---

### Step 3: Apply

```bash
terraform apply
```

Enter `yes` at the confirmation prompt.

**Estimated Time**: 20-30 minutes
- VPC/Subnets: 2-3 minutes
- RDS: 10-15 minutes
- EKS: 10-15 minutes
- ElastiCache: 5-10 minutes

---

### Step 4: View Outputs

```bash
# Show all outputs
terraform output

# Show specific output
terraform output eks_cluster_name
terraform output redis_endpoint

# Show sensitive outputs
terraform output -raw auth_db_password
terraform output -raw auth_db_connection_string
```

---

## 📊 Key Outputs

### EKS Related
```bash
# kubectl configuration command
terraform output -raw configure_kubectl

# Example execution
$(terraform output -raw configure_kubectl)
kubectl get nodes
```

### RDS Related
```bash
# Auth DB connection info
terraform output auth_db_endpoint
terraform output -raw auth_db_password
terraform output -raw auth_db_connection_string

# Photos DB connection info
terraform output photos_db_endpoint
terraform output -raw photos_db_password
terraform output -raw photos_db_connection_string
```

### ElastiCache Related
```bash
terraform output redis_endpoint
terraform output redis_url
```

### ECR Related
```bash
# ECR registry URL
terraform output ecr_registry

# All ECR repository URLs
terraform output ecr_repository_urls
```

---

## 🔐 Creating Kubernetes Secrets

Create Kubernetes Secrets from Terraform outputs.

### Method 1: Manual Creation

```bash
# Get Auth DB password
AUTH_DB_PASSWORD=$(terraform output -raw auth_db_password)
AUTH_DB_ENDPOINT=$(terraform output -raw auth_db_endpoint | sed 's/:5432//')

# Get Photos DB password
PHOTOS_DB_PASSWORD=$(terraform output -raw photos_db_password)
PHOTOS_DB_ENDPOINT=$(terraform output -raw photos_db_endpoint | sed 's/:5432//')

# Get Redis endpoint
REDIS_HOST=$(terraform output -raw redis_endpoint)

# Edit k8s/02-secrets.yaml
cd ../k8s
cp 02-secrets-template.yaml 02-secrets.yaml

# Replace values (macOS)
sed -i '' "s|REPLACE_WITH_PASSWORD|${AUTH_DB_PASSWORD}|g" 02-secrets.yaml
sed -i '' "s|REPLACE_WITH_ENDPOINT|${AUTH_DB_ENDPOINT}|g" 02-secrets.yaml
# ... and so on
```

### Method 2: Automated Script

```bash
cd terraform
./scripts/update-k8s-manifests.sh
```

(Note: Script needs to be created separately)

---

## 🔄 Updates and Maintenance

### Changing Resources

```bash
# Edit terraform.tfvars
vim terraform.tfvars

# Review changes
terraform plan

# Apply changes
terraform apply
```

### Scaling Node Count

```bash
# Change in terraform.tfvars
node_group_desired_size = 3

# Apply
terraform apply
```

Or directly with kubectl:

```bash
kubectl scale deployment/api-gateway -n classify --replicas=3
```

---

## 🗑 Cleanup

### Delete All Resources

```bash
terraform destroy
```

Enter `yes` at the confirmation prompt.

**Warning**:
- RDS snapshots will not be retained (`skip_final_snapshot = true`)
- Back up any necessary data before deletion

---

## 💰 Cost Estimation

### Monthly Cost (ap-northeast-1, as of October 2024)

| Resource | Specification | Monthly (USD) |
|---------|------|-----------|
| EKS Cluster | 1 cluster | $73 |
| EKS Nodes (t3.small) | 2 nodes × 24h | ~$30 |
| RDS (db.t3.micro) | 2 instances × 20GB | ~$30 |
| ElastiCache (cache.t3.micro) | 1 instance | ~$12 |
| NAT Gateway | 1 gateway + data transfer | ~$35 |
| ALB | 1 load balancer + data transfer | ~$20 |
| **Total** | | **~$200** |

**Cost Reduction Tips**:
- NAT Gateway: single_nat_gateway = true (already configured)
- RDS: Multi-AZ disabled (already configured)
- EKS Nodes: t3.small → t3.micro (not recommended)
- Run `terraform destroy` when not in use

---

## 🛠 Troubleshooting

### terraform init Error

```bash
# Clear provider cache
rm -rf .terraform .terraform.lock.hcl
terraform init
```

### terraform apply Timeout

RDS and EKS creation takes time. Wait up to 30 minutes.

### Cannot Connect to EKS Cluster

```bash
# Update kubectl configuration
aws eks update-kubeconfig --name classify-cluster --region ap-northeast-1

# Verify credentials
kubectl get nodes
```

### Cannot Connect to RDS

- Verify security group is correctly configured
- Verify EKS nodes are allowed to access RDS

```bash
# Get security group ID
terraform output | grep security_group
```

---

## 📝 Migrating to Production

When migrating from development (dev) to production (prod):

1. **Duplicate terraform.tfvars**
   ```bash
   cp terraform.tfvars prod.tfvars
   ```

2. **Edit prod.tfvars**
   ```hcl
   environment = "prod"

   # Production settings
   single_nat_gateway = false        # Redundant NAT Gateway
   rds_multi_az = true                # RDS Multi-AZ
   node_group_min_size = 3            # Increase node count
   node_instance_types = ["t3.medium"] # Larger instance size
   ```

3. **Use workspace (recommended)**
   ```bash
   terraform workspace new prod
   terraform workspace select prod
   terraform apply -var-file="prod.tfvars"
   ```

---

## 🔗 Related Links

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform VPC Module](https://registry.terraform.io/modules/terraform-aws-modules/vpc/aws/latest)
- [Terraform EKS Module](https://registry.terraform.io/modules/terraform-aws-modules/eks/aws/latest)
- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
