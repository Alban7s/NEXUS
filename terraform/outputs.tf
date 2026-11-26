output "nexus_instance_id" {
  value = data.aws_instance.nexus.id
}

output "nexus_instance_type" {
  value = data.aws_instance.nexus.instance_type
}

output "nexus_private_ip" {
  value = data.aws_instance.nexus.private_ip
}

output "nexus_public_ip" {
  value = data.aws_instance.nexus.public_ip
}
