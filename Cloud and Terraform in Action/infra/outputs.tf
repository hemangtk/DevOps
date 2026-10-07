# Name: Hemang | Enrollment number: 24bcs10209
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_id" {
  description = "Public subnet ID"
  value       = aws_subnet.public.id
}

output "private_subnet_id" {
  description = "Private subnet ID"
  value       = aws_subnet.private.id
}

output "web_security_group_id" {
  description = "Web tier security group"
  value       = aws_security_group.web.id
}

output "app_security_group_id" {
  description = "App tier security group"
  value       = aws_security_group.app.id
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.web.id
}

output "instance_private_ip" {
  description = "Private IP of the instance"
  value       = aws_instance.web.private_ip
}

output "assets_bucket" {
  description = "S3 bucket for assets"
  value       = aws_s3_bucket.assets.id
}
