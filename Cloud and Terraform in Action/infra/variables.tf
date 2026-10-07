# Name: Hemang | Enrollment number: 24bcs10209
variable "aws_region" {
  type        = string
  default     = "ap-south-1"
  description = "Region for all resources"
}

variable "project" {
  type        = string
  default     = "devops-s19"
  description = "Name prefix for every resource"
}

variable "vpc_cidr" {
  type        = string
  default     = "10.0.0.0/16"
  description = "CIDR block for the VPC"
}

variable "public_subnet_cidr" {
  type        = string
  default     = "10.0.1.0/24"
  description = "CIDR for the public subnet"
}

variable "private_subnet_cidr" {
  type        = string
  default     = "10.0.11.0/24"
  description = "CIDR for the private subnet"
}

variable "instance_type" {
  type        = string
  default     = "t3.micro"
  description = "EC2 instance size"
}

variable "common_tags" {
  type = map(string)
  default = {
    Owner      = "Hemang"
    Enrollment = "24bcs10209"
    ManagedBy  = "Terraform"
  }
}
