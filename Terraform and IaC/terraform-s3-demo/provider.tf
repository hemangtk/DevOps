# Provider configuration.
# Name: Hemang | Enrollment number: 24bcs10209
#
# NOTE: this points at LocalStack, an AWS emulator running in Docker, rather
# than at real AWS. Every API call below is genuine - LocalStack implements the
# S3 API - but nothing is billable and no real account is involved. Removing the
# `endpoints` block and the fake credentials is all that is needed to target
# real AWS.
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
  region     = var.aws_region
  access_key = "test" # LocalStack accepts any credentials
  secret_key = "test"

  # these four lines are the only LocalStack-specific part
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3       = "http://localhost:4566"
    iam      = "http://localhost:4566"
    ec2      = "http://localhost:4566"
    dynamodb = "http://localhost:4566"
    sts      = "http://localhost:4566"
  }
}
