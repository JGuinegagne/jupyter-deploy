data "aws_iam_policy_document" "codebuild_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["codebuild.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "codebuild" {
  name               = "${var.project_name}-codebuild"
  assume_role_policy = data.aws_iam_policy_document.codebuild_trust.json
  tags               = var.combined_tags
}

data "aws_iam_policy_document" "codebuild_permissions" {
  statement {
    sid = "ECRPush"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:CompleteLayerUpload",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [var.ecr_repository_arn]
  }

  statement {
    sid       = "ECRAuth"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid = "S3Source"
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
    ]
    resources = ["${var.source_s3_bucket_arn}/*"]
  }

  statement {
    sid       = "S3BucketList"
    actions   = ["s3:ListBucket"]
    resources = [var.source_s3_bucket_arn]
  }

  # Scoped to the declared build group (below): CodeBuild needs no CreateLogGroup.
  statement {
    sid       = "CloudWatchLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.build.arn}:*"]
  }
}

resource "aws_iam_role_policy" "codebuild" {
  name   = "${var.project_name}-permissions"
  role   = aws_iam_role.codebuild.id
  policy = data.aws_iam_policy_document.codebuild_permissions.json
}

# Declared rather than left to CodeBuild, whose default /aws/codebuild/<project> group
# never expires and outlives `jd down`. A name of our own, not CodeBuild's default, so
# that deployments where CodeBuild already created the default group need no import.
resource "aws_cloudwatch_log_group" "build" {
  name              = var.log_group_name
  retention_in_days = var.log_retention_days
  tags              = var.combined_tags
}

resource "aws_codebuild_project" "this" {
  name         = var.project_name
  service_role = aws_iam_role.codebuild.arn

  source {
    type      = "S3"
    location  = var.source_s3_location
    buildspec = var.buildspec
  }

  artifacts {
    type = "NO_ARTIFACTS"
  }

  logs_config {
    cloudwatch_logs {
      group_name = aws_cloudwatch_log_group.build.name
    }
  }

  environment {
    compute_type    = "BUILD_GENERAL1_SMALL"
    image           = "aws/codebuild/standard:7.0"
    type            = "LINUX_CONTAINER"
    privileged_mode = true

    environment_variable {
      name  = "ECR_REPO_URL"
      value = var.ecr_repository_url
    }

    environment_variable {
      name  = "IMAGE_TAG"
      value = var.image_tag
    }
  }

  tags = var.combined_tags
}
