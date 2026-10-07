# Name: Hemang | Enrollment number: 24bcs10209
output "artifacts_bucket" {
  description = "Bucket holding build artifacts"
  value       = aws_s3_bucket.artifacts.id
}
