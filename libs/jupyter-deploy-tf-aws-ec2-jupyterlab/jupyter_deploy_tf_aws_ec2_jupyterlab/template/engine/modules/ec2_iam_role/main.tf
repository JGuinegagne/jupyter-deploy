data "aws_partition" "current" {}

# Define the IAM role for the instance and add policies
data "aws_iam_policy_document" "server_assume_role_policy" {
  statement {
    sid     = "EC2AssumeRole"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.${data.aws_partition.current.dns_suffix}"]
    }
  }
}

resource "aws_iam_role" "execution_role" {
  name_prefix = "${var.iam_role_prefix}-${var.postfix}-"
  description = "Execution role for the JupyterServer instance, with access to SSM."

  assume_role_policy    = data.aws_iam_policy_document.server_assume_role_policy.json
  force_detach_policies = true
  tags                  = var.combined_tags
}

data "aws_iam_policy" "ssm_managed_policy" {
  arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "execution_role_ssm_policy_attachment" {
  role       = aws_iam_role.execution_role.name
  policy_arn = data.aws_iam_policy.ssm_managed_policy.arn
}

# Add required policies for EFS IAM auth and EC2 instance to describe resources
data "aws_iam_policy" "efs_managed_policy" {
  count = var.has_efs_filesystems ? 1 : 0
  arn   = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonElasticFileSystemClientReadWriteAccess"
}

data "aws_iam_policy" "ec2_describe_policy" {
  count = var.has_efs_filesystems ? 1 : 0
  arn   = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEC2ReadOnlyAccess"
}

resource "aws_iam_role_policy_attachment" "efs_client_read_write" {
  count      = var.has_efs_filesystems ? 1 : 0
  role       = aws_iam_role.execution_role.name
  policy_arn = data.aws_iam_policy.efs_managed_policy[0].arn
}

resource "aws_iam_role_policy_attachment" "ec2_describe" {
  count      = var.has_efs_filesystems ? 1 : 0
  role       = aws_iam_role.execution_role.name
  policy_arn = data.aws_iam_policy.ec2_describe_policy[0].arn
}

# Define the instance profile to associate the IAM role with the EC2 instance
resource "aws_iam_instance_profile" "server_instance_profile" {
  role        = aws_iam_role.execution_role.name
  name_prefix = "${var.iam_role_prefix}-${var.postfix}-"
  lifecycle {
    create_before_destroy = true
  }
  tags = var.combined_tags
}

# IAM is eventually consistent: a freshly-created instance profile is not always visible
# to EC2's RunInstances yet, which fails with a misleading "Invalid IAM Instance Profile
# name" (InvalidParameterValue) that the AWS provider does NOT retry. Gate the profile
# name through this delay so the instance can't launch until the profile has propagated.
# The profile name flows out of the trigger (below), making consumers wait on the value.
resource "time_sleep" "instance_profile_propagation" {
  create_duration = "20s"
  triggers = {
    instance_profile_name = aws_iam_instance_profile.server_instance_profile.name
  }
}
