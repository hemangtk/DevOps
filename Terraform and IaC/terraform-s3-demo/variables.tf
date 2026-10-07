# Input variables.
# Name: Hemang | Enrollment number: 24bcs10209
variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "bucket_name" {
  description = "Globally unique name for the S3 bucket"
  type        = string
  default     = "devops-coursework-24bcs10209"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "Bucket names must be lowercase, 3-63 chars, and start/end alphanumeric."
  }
}

variable "environment" {
  description = "Environment tag applied to every resource"
  type        = string
  default     = "coursework"
}

variable "enable_versioning" {
  description = "Keep previous versions of objects"
  type        = bool
  default     = true
}

variable "common_tags" {
  description = "Tags merged onto every resource"
  type        = map(string)
  default = {
    Owner      = "Hemang"
    Enrollment = "24bcs10209"
    ManagedBy  = "Terraform"
  }
}
