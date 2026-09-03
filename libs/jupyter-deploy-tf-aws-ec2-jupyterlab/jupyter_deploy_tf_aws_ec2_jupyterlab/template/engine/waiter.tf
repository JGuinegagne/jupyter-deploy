locals {
  # For wait_for_instance_ready
  await_server_file = templatefile("${path.module}/local-await-server.sh.tftpl", {
    instance_id                = module.ec2_instance.id
    association_id             = aws_ssm_association.instance_startup.association_id
    status_check_document_name = aws_ssm_document.instance_status_check.name
    region                     = data.aws_region.current.id
  })
  await_indent_str      = join("", [for i in range(6) : " "])
  await_server_indented = join("\n${local.await_indent_str}", compact(split("\n", local.await_server_file)))
}

resource "null_resource" "wait_for_instance_ready" {
  triggers = {
    # Instance parameters:
    instance_id = module.ec2_instance.id
    # the instance ID might be preserved even on VM swap.
    # NOTE: deliberately no public IP trigger — without an EIP the IP changes on every
    # stop/start, and the await script never uses it (it keys on instance/association/document
    # ids); triggering on it would needlessly replace this resource and re-run the multi-minute
    # SSM/status wait after a plain `jd host stop` + `jd up`.
    ami            = module.ec2_instance.ami
    instance_type  = module.ec2_instance.instance_type
    root_volume_id = module.ec2_instance.root_block_device_id
    # Cloudinit parameters:
    association_id = aws_ssm_association.instance_startup.id
    # the association ID should capture. the startup instructions doc name and versions
    # consider removing after further testing
    startup_doc_name    = aws_ssm_document.instance_startup.name
    startup_doc_version = aws_ssm_document.instance_startup.default_version
    # Inner status check parameters:
    status_doc_name    = aws_ssm_document.instance_status_check.name
    status_doc_version = aws_ssm_document.instance_status_check.default_version
  }
  provisioner "local-exec" {
    quiet   = true
    command = <<DOC
      ${local.await_server_indented}
    DOC
  }

  depends_on = [
    aws_ssm_association.instance_startup,
    aws_ssm_document.instance_status_check,
    aws_ssm_document.instance_startup,
    module.ec2_instance,
    module.network,
    module.volumes,
  ]
}