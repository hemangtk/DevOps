# Name: Hemang | Enrollment number: 24bcs10209
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # LocalStack settings. To target REAL AWS, delete this whole block and the
  # two access keys below, then supply credentials normally.
  access_key                  = var.use_localstack ? "test" : null
  secret_key                  = var.use_localstack ? "test" : null
  s3_use_path_style           = var.use_localstack
  skip_credentials_validation = var.use_localstack
  skip_metadata_api_check     = var.use_localstack
  skip_requesting_account_id  = var.use_localstack

  dynamic "endpoints" {
    for_each = var.use_localstack ? [1] : []
    content {
      ec2 = "http://localhost:4566"
      iam = "http://localhost:4566"
      sts = "http://localhost:4566"
      eks = "http://localhost:4566"
      s3  = "http://localhost:4566"
    }
  }
}
