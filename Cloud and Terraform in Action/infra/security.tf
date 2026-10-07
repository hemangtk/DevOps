# Security groups, chained so each tier only accepts the tier above it.
# Name: Hemang | Enrollment number: 24bcs10209

# Web tier: open to the world on 80/443 only.
resource "aws_security_group" "web" {
  name        = "${var.project}-web-sg"
  description = "Allow HTTP/HTTPS from anywhere"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, { Name = "${var.project}-web-sg" })
}

# App tier: reachable ONLY from the web security group, by reference.
# No IP addresses are hardcoded - this is the clean way to express tiering.
resource "aws_security_group" "app" {
  name        = "${var.project}-app-sg"
  description = "Allow 8080 only from the web tier"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "App port from web tier only"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.web.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, { Name = "${var.project}-app-sg" })
}
