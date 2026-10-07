# S3 bucket and its configuration.
# Name: Hemang | Enrollment number: 24bcs10209

resource "aws_s3_bucket" "coursework" {
  bucket = var.bucket_name

  tags = merge(var.common_tags, {
    Name        = var.bucket_name
    Environment = var.environment
  })
}

# Versioning - keeps old object versions so an overwrite is recoverable.
resource "aws_s3_bucket_versioning" "coursework" {
  bucket = aws_s3_bucket.coursework.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Suspended"
  }
}

# Server-side encryption at rest.
resource "aws_s3_bucket_server_side_encryption_configuration" "coursework" {
  bucket = aws_s3_bucket.coursework.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block ALL public access - the single most important S3 setting.
resource "aws_s3_bucket_public_access_block" "coursework" {
  bucket                  = aws_s3_bucket.coursework.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle: expire old versions so storage costs do not grow forever.
resource "aws_s3_bucket_lifecycle_configuration" "coursework" {
  bucket     = aws_s3_bucket.coursework.id
  depends_on = [aws_s3_bucket_versioning.coursework]

  rule {
    id     = "expire-noncurrent-versions"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# An object, to prove the bucket is usable.
resource "aws_s3_object" "readme" {
  bucket       = aws_s3_bucket.coursework.id
  key          = "hello/README.txt"
  content      = "Created by Terraform.\nName: Hemang\nEnrollment: 24bcs10209\n"
  content_type = "text/plain"
  tags         = var.common_tags
}
