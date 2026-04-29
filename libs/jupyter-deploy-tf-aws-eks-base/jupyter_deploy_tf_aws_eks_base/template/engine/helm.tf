locals {
  traefik_crds_repo             = "https://traefik.github.io/charts"
  workspace_operator_chart_repo = "oci://ghcr.io/jupyter-infra/charts"
  enable_external_dns           = true
}

resource "helm_release" "traefik_crds" {
  name             = "traefik-crds"
  repository       = local.traefik_crds_repo
  chart            = "traefik-crds"
  version          = var.traefik_crd_chart_version
  namespace        = var.workspace_router_namespace
  create_namespace = true

  depends_on = [aws_eks_addon.cert_manager]
}

resource "helm_release" "jupyter_k8s" {
  name             = "jupyter-k8s"
  repository       = local.workspace_operator_chart_repo
  chart            = "jupyter-k8s"
  version          = var.workspace_operator_chart_version
  namespace        = var.workspace_operator_namespace
  create_namespace = true

  set = [
    {
      name  = "certManager.enable"
      value = "true"
    },
    {
      name  = "crd.enable"
      value = "true"
    },
    {
      name  = "workspaceTemplates.defaultNamespace"
      value = var.workspace_operator_namespace
    },
  ]

  depends_on = [aws_eks_addon.cert_manager, helm_release.traefik_crds]
}

