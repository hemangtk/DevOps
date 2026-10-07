# EC2 instance in the public subnet.
# Name: Hemang | Enrollment number: 24bcs10209

# A data source: look the AMI up rather than hardcoding an ID that differs per region.
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_instance" "web" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type

  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web.id]

  # Runs on first boot.
  user_data = <<-EOT
    #!/bin/bash
    yum install -y httpd
    systemctl enable --now httpd
    cat > /var/www/html/index.html <<'HTML'
    <h1>Provisioned by Terraform</h1>
    <p>Hemang - 24bcs10209</p>
    HTML
  EOT

  tags = merge(var.common_tags, { Name = "${var.project}-web", Tier = "web" })
}
