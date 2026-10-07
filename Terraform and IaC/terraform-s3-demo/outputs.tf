# Outputs.
# Name: Hemang | Enrollment number: 24bcs10209
output "bucket_name" {
  description = "Name of the created bucket"
  value       = aws_s3_bucket.coursework.id
}

output "bucket_arn" {
  description = "ARN of the created bucket"
  value       = aws_s3_bucket.coursework.arn
}

output "bucket_region" {
  description = "Region the bucket lives in"
  value       = aws_s3_bucket.coursework.region
}

output "versioning_status" {
  description = "Whether object versioning is enabled"
  value       = aws_s3_bucket_versioning.coursework.versioning_configuration[0].status
}

output "uploaded_object_key" {
  description = "Key of the object Terraform uploaded"
  value       = aws_s3_object.readme.key
}
