# Name: Hemang | Enrollment number: 24bcs10209
variable "aws_region" {
  type    = string
  default = "ap-south-1"
}
variable "project" {
  type    = string
  default = "s19-mini"
}
variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}
variable "public_subnet_cidr" {
  type    = string
  default = "10.20.1.0/24"
}
variable "common_tags" {
  type = map(string)
  default = {
    Owner      = "Hemang"
    Enrollment = "24bcs10209"
    ManagedBy  = "Terraform"
  }
}
