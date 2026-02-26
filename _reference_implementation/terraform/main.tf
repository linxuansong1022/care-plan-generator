# Terraform configuration for Care Plan Generator infrastructure
# AWS ECS Fargate + RDS PostgreSQL + ElastiCache Redis + S3

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment for production - use S3 backend for state
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "care-plan-generator/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-locks"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "care-plan-generator"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "care-plan-generator"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key for Claude"
  type        = string
  sensitive   = true
}

# VPC
module "vpc" {
  source = "./modules/vpc"

  app_name    = var.app_name
  environment = var.environment
  aws_region  = var.aws_region
}

# RDS PostgreSQL
module "rds" {
  source = "./modules/rds"

  app_name           = var.app_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  db_password        = var.db_password
}

# ElastiCache Redis
module "redis" {
  source = "./modules/redis"

  app_name           = var.app_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
}

# S3 Bucket
module "s3" {
  source = "./modules/s3"

  app_name    = var.app_name
  environment = var.environment
}

# ECS Cluster and Services
module "ecs" {
  source = "./modules/ecs"

  app_name           = var.app_name
  environment        = var.environment
  aws_region         = var.aws_region
  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids
  
  # Database
  database_url = "postgresql://careplan:${var.db_password}@${module.rds.endpoint}/careplan"
  
  # Redis
  redis_url = "redis://${module.redis.endpoint}:6379/0"
  
  # S3
  s3_bucket_name = module.s3.bucket_name
  
  # LLM
  anthropic_api_key = var.anthropic_api_key
}

# Outputs
output "alb_dns_name" {
  description = "ALB DNS name"
  value       = module.ecs.alb_dns_name
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.endpoint
}

output "redis_endpoint" {
  description = "Redis endpoint"
  value       = module.redis.endpoint
}

output "s3_bucket_name" {
  description = "S3 bucket name"
  value       = module.s3.bucket_name
}
