# VPC Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}

# EKS Outputs
output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_certificate_authority_data" {
  description = "EKS cluster certificate authority data"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "eks_node_security_group_id" {
  description = "EKS node security group ID"
  value       = module.eks.node_security_group_id
}

output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.aws_region}"
}

# RDS Outputs
output "auth_db_endpoint" {
  description = "Auth database endpoint"
  value       = aws_db_instance.auth.endpoint
}

output "auth_db_name" {
  description = "Auth database name"
  value       = aws_db_instance.auth.db_name
}

output "auth_db_username" {
  description = "Auth database username"
  value       = aws_db_instance.auth.username
}

output "auth_db_password" {
  description = "Auth database password"
  value       = random_password.auth_db.result
  sensitive   = true
}

output "auth_db_connection_string" {
  description = "Auth database connection string"
  value       = "postgresql://${aws_db_instance.auth.username}:${random_password.auth_db.result}@${aws_db_instance.auth.endpoint}/${aws_db_instance.auth.db_name}"
  sensitive   = true
}

output "photos_db_endpoint" {
  description = "Photos database endpoint"
  value       = aws_db_instance.photos.endpoint
}

output "photos_db_name" {
  description = "Photos database name"
  value       = aws_db_instance.photos.db_name
}

output "photos_db_username" {
  description = "Photos database username"
  value       = aws_db_instance.photos.username
}

output "photos_db_password" {
  description = "Photos database password"
  value       = random_password.photos_db.result
  sensitive   = true
}

output "photos_db_connection_string" {
  description = "Photos database connection string"
  value       = "postgresql://${aws_db_instance.photos.username}:${random_password.photos_db.result}@${aws_db_instance.photos.endpoint}/${aws_db_instance.photos.db_name}"
  sensitive   = true
}

# ElastiCache Outputs
output "redis_endpoint" {
  description = "Redis endpoint"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_cluster.redis.port
}

output "redis_url" {
  description = "Redis URL"
  value       = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:${aws_elasticache_cluster.redis.port}"
}

# ECR Outputs
output "ecr_repository_urls" {
  description = "ECR repository URLs"
  value = {
    for name, repo in aws_ecr_repository.services :
    name => repo.repository_url
  }
}

output "ecr_registry" {
  description = "ECR registry URL"
  value       = split("/", aws_ecr_repository.services["classify-api-gateway"].repository_url)[0]
}

# Output for Kubernetes Secrets
output "kubernetes_secrets_yaml" {
  description = "Kubernetes Secrets YAML (use with caution)"
  value = <<-EOT
  apiVersion: v1
  kind: Secret
  metadata:
    name: classify-secrets
    namespace: classify
  type: Opaque
  stringData:
    AUTH_DB_URL: "${aws_db_instance.auth.username}:${random_password.auth_db.result}@${aws_db_instance.auth.endpoint}/${aws_db_instance.auth.db_name}"
    PHOTOS_DB_URL: "${aws_db_instance.photos.username}:${random_password.photos_db.result}@${aws_db_instance.photos.endpoint}/${aws_db_instance.photos.db_name}"
  EOT
  sensitive   = true
}
