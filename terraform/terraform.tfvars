# Project Configuration
project_name = "classify"
environment  = "dev"
aws_region   = "ap-northeast-1"

# VPC Configuration
vpc_cidr             = "10.0.0.0/16"
availability_zones   = ["ap-northeast-1a", "ap-northeast-1c"]
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24"]

# Cost Optimization: Single NAT Gateway (for development environment)
single_nat_gateway = true

# EKS Configuration
kubernetes_version = "1.28"

# EKS Node Group (minimal configuration)
node_group_min_size     = 2
node_group_max_size     = 4
node_group_desired_size = 2
node_instance_types     = ["t3.small"]

# RDS Configuration (minimal configuration)
rds_instance_class          = "db.t3.micro"
rds_allocated_storage       = 20
rds_multi_az                = false  # Disabled for development environment
rds_backup_retention_period = 7

# ElastiCache Configuration (minimal configuration)
redis_node_type        = "cache.t3.micro"
redis_num_cache_nodes  = 1
redis_engine_version   = "7.0"
