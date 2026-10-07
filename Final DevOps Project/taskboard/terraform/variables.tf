# Name: Hemang | Enrollment number: 24bcs10209
variable "aws_region" {
  description = "Region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "project" {
  description = "Name prefix for every resource"
  type        = string
  default     = "taskboard"
}

variable "use_localstack" {
  description = "Target LocalStack instead of real AWS. Set false for real AWS."
  type        = bool
  default     = true
}

variable "vpc_cidr" {
  description = "CIDR for the VPC"
  type        = string
  default     = "10.30.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDRs for the public subnets - at least two, in different AZs"
  type        = list(string)
  default     = ["10.30.1.0/24", "10.30.2.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) >= 2
    error_message = "EKS requires subnets in at least two availability zones."
  }
}

variable "cluster_version" {
  description = "Kubernetes version for the EKS control plane"
  type        = string
  default     = "1.31"
}

variable "node_instance_type" {
  description = "Instance type for the EKS worker node group"
  type        = string
  default     = "t3.medium"
}

variable "node_desired_size" {
  description = "Desired worker node count"
  type        = number
  default     = 2
}

variable "common_tags" {
  type = map(string)
  default = {
    Project    = "taskboard"
    Owner      = "Hemang"
    Enrollment = "24bcs10209"
    ManagedBy  = "Terraform"
  }
}
