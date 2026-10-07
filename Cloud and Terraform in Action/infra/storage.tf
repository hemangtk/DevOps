# S3 bucket for application assets.
# Name: Hemang | Enrollment number: 24bcs10209

resource "aws_s3_bucket" "assets" {
  bucket = "${var.project}-assets-24bcs10209"
  tags   = merge(var.common_tags, { Name = "${var.project}-assets" })
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket                  = aws_s3_bucket.assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# An object whose content references the instance - this creates an IMPLICIT
# dependency on aws_instance.web, which is what builds the graph edge.
resource "aws_s3_object" "manifest" {
  bucket       = aws_s3_bucket.assets.id
  key          = "manifest.txt"
  content      = <<-EOT
    Deployed by Terraform
    Name:       Hemang
    Enrollment: 24bcs10209
    VPC:        ${aws_vpc.main.id}
    Instance:   ${aws_instance.web.id}
    Private IP: ${aws_instance.web.private_ip}
  EOT
  content_type = "text/plain"
  tags         = var.common_tags
}
