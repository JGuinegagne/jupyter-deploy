# ── Workspace Bedrock access (EKS Pod Identity) ───────────────────────────────
# Claude Code and Codex ship in the workspace image; this grants them Bedrock.
# Both call bedrock-runtime in the deployment region through cross-region
# inference profiles, so one IAM policy covers both.
# Every workspace namespace holds a labeled "workspace" ServiceAccount, which the
# operator webhook assigns to each Workspace created without one. The SA exists
# whether or not the namespace has Bedrock: the webhook only assigns it at
# creation, so a later opt-in reaches new workspaces, and an opt-out never leaves
# a workspace pointing at a deleted SA. Only the Pod Identity association, to a
# per-namespace role, is gated.
locals {
  workspace_service_account = "workspace"

  workspace_bedrock_namespaces = var.workspace_bedrock_enabled ? [
    for ns in local.workspace_ns_names : ns
    if lookup(lookup(local.workspace_ns_entries, ns, [{}])[0], "bedrock", "true") == "true"
  ] : []

  # The cross-region inference profile prefix of the deployment region's geography,
  # as Claude Code derives it from AWS_REGION. Pinned on both clients
  # (ANTHROPIC_BEDROCK_REGION_PREFIX, the Codex model) so they and the IAM grants
  # cannot diverge.
  workspace_bedrock_geo_prefix = (
    startswith(var.region, "us-gov-") ? "us-gov" :
    startswith(var.region, "us-") ? "us" :
    startswith(var.region, "eu-") ? "eu" :
    startswith(var.region, "ap-") ? "apac" : ""
  )
  workspace_bedrock_profile_prefix = var.workspace_bedrock_inference_scope == "global" ? "global" : local.workspace_bedrock_geo_prefix

  # IAM caps role names at 64 characters; a long namespace is cut and suffixed
  # with a hash of its name, so distinct namespaces keep distinct roles.
  workspace_bedrock_role_names = {
    for ns in local.workspace_bedrock_namespaces : ns => (
      length("${local.resource_name_prefix}-ws-bedrock-${ns}") <= 64
      ? "${local.resource_name_prefix}-ws-bedrock-${ns}"
      : "${substr("${local.resource_name_prefix}-ws-bedrock-${ns}", 0, 55)}-${substr(sha1(ns), 0, 8)}"
    )
  }

  workspace_bedrock_env = [
    { name = "AWS_REGION", value = var.region },
    { name = "ANTHROPIC_BEDROCK_REGION_PREFIX", value = local.workspace_bedrock_profile_prefix },
  ]

  workspace_bedrock_profile_arns = [
    for p in var.workspace_bedrock_model_patterns :
    "arn:${data.aws_partition.current.partition}:bedrock:${var.region}:${data.aws_caller_identity.current.account_id}:inference-profile/${local.workspace_bedrock_profile_prefix}.${p}"
  ]
}

data "aws_iam_policy_document" "workspace_bedrock" {
  # Claude Code and Codex call the inference profile in the deployment region...
  statement {
    sid       = "InvokeInferenceProfile"
    actions   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    resources = local.workspace_bedrock_profile_arns
  }

  # Codex's OpenAI-compatible calls are also authorized against the account's
  # default Bedrock project; the model is still gated by the profile grant above.
  statement {
    sid       = "InvokeDefaultProject"
    actions   = ["bedrock:InvokeModel"]
    resources = ["arn:${data.aws_partition.current.partition}:bedrock:${var.region}:${data.aws_caller_identity.current.account_id}:project/default"]
  }

  # ...which routes to the foundation model in any region of its scope; allowed
  # only through that profile, never as a direct call. Global profiles route to
  # the region-less foundation model ARN.
  statement {
    sid     = "InvokeFoundationModelViaProfile"
    actions = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    resources = flatten([
      for p in var.workspace_bedrock_model_patterns : [
        "arn:${data.aws_partition.current.partition}:bedrock:*::foundation-model/${p}",
        "arn:${data.aws_partition.current.partition}:bedrock:::foundation-model/${p}",
      ]
    ])
    condition {
      test     = "StringLike"
      variable = "bedrock:InferenceProfileArn"
      values   = local.workspace_bedrock_profile_arns
    }
  }

  # Model discovery (Claude Code's /model).
  statement {
    sid = "DiscoverModels"
    actions = [
      "bedrock:ListFoundationModels",
      "bedrock:GetFoundationModel",
      "bedrock:ListInferenceProfiles",
      "bedrock:GetInferenceProfile",
    ]
    resources = ["*"]
  }
}

# One role per namespace: each team is its own CloudTrail principal.
module "workspace_bedrock_role" {
  source   = "./modules/iam_role"
  for_each = toset(local.workspace_bedrock_namespaces)

  role_name          = local.workspace_bedrock_role_names[each.key]
  assume_role_policy = data.aws_iam_policy_document.pod_identity_trust.json
  combined_tags      = merge(local.combined_tags, { "jupyter-deploy/workspace-namespace" = each.key })
}

resource "aws_iam_role_policy" "workspace_bedrock" {
  for_each = toset(local.workspace_bedrock_namespaces)

  name   = local.workspace_bedrock_role_names[each.key]
  role   = module.workspace_bedrock_role[each.key].role_name
  policy = data.aws_iam_policy_document.workspace_bedrock.json
}

resource "kubernetes_service_account_v1" "workspace" {
  for_each = toset(local.workspace_ns_names)

  metadata {
    name      = local.workspace_service_account
    namespace = each.key
    labels = {
      "app.kubernetes.io/managed-by"                  = "jupyter-deploy"
      "workspace.jupyter.org/default-service-account" = "true"
    }
  }

  lifecycle {
    precondition {
      condition     = !var.workspace_bedrock_enabled || local.workspace_bedrock_profile_prefix != ""
      error_message = "${var.region} has no geographic Bedrock inference profiles: set workspace_bedrock_inference_scope to \"global\", or disable workspace_bedrock_enabled."
    }
  }

  depends_on = [kubernetes_namespace_v1.workspaces, kubernetes_labels.default_namespace]
}

resource "aws_eks_pod_identity_association" "workspace_bedrock" {
  for_each = toset(local.workspace_bedrock_namespaces)

  cluster_name    = module.eks_cluster.cluster_name
  namespace       = each.key
  service_account = kubernetes_service_account_v1.workspace[each.key].metadata[0].name
  role_arn        = module.workspace_bedrock_role[each.key].role_arn

  depends_on = [aws_eks_addon.pod_identity_agent, aws_iam_role_policy.workspace_bedrock]
}

# Bedrock offers the OpenAI models through US and global inference profiles only.
check "workspace_bedrock_codex_profile" {
  assert {
    condition     = !var.workspace_bedrock_enabled || contains(["us", "global"], local.workspace_bedrock_profile_prefix)
    error_message = "Bedrock has no ${local.workspace_bedrock_profile_prefix}.openai.* inference profiles, so Codex cannot reach its model from ${var.region}; set workspace_bedrock_inference_scope to \"global\" to use Codex. Claude Code is unaffected."
  }
}
