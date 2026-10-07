# Name: Hemang | Enrollment number: 24bcs10209
output "vpc_id" { value = aws_vpc.main.id }
output "vpc_cidr" { value = aws_vpc.main.cidr_block }
output "public_subnet_id" { value = aws_subnet.public.id }
output "internet_gateway_id" { value = aws_internet_gateway.main.id }
output "route_table_id" { value = aws_route_table.public.id }
output "web_security_group_id" { value = aws_security_group.web.id }
