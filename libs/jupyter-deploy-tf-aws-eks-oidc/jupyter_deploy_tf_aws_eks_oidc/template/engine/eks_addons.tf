resource "time_sleep" "wait_for_nodes" {
  create_duration = "30s"
  depends_on      = [module.eks_cluster]
}

locals {
  # Pin add-on CONTROLLER Deployments to the platform node group, alongside the
  # operator and router (helm.tf). This template has no node taints, so scheduling is
  # by nodeSelector on the jupyter-deploy/role label — unlike inference-clusters, which
  # tolerates a system-NG taint. DaemonSet parts of an addon (vpc-cni, kube-proxy, the
  # ebs-csi node plugin) are NOT pinned: they must run on every node, workspaces included.
  components_node_selector = {
    "jupyter-deploy/role" = "platform"
  }
}

# --- Addon ordering aggregators ---
#
# These two null_resources are single-source-of-truth barriers that let node
# groups and Helm releases order themselves against the addons WITHOUT each one
# re-deriving (and eventually getting wrong) the per-resource addon matrix.
# No addon depends on a node group or a Helm release, so these introduce no cycle.

# DaemonSet addons a node needs to be functional: vpc-cni (pod IPs) and kube-proxy
# (Service/ClusterIP routing). The node group depends_on this, so on create the
# CNI is in place before nodes join, and on destroy the nodes drain BEFORE these
# are removed. Only DaemonSets belong here: they report healthy with zero nodes,
# so requiring them before the node group never deadlocks. Deployment addons
# (coredns, ebs-csi, ...) must NOT be here — they need a schedulable node, so
# gating the node group on them would be a create-time cycle.
resource "null_resource" "core_node_addons" {
  depends_on = [
    aws_eks_addon.vpc_cni,
    aws_eks_addon.kube_proxy,
  ]
}

# Every cluster addon. The Helm releases (helm.tf) depend_on this, so on create
# all addons are up before any chart installs, and on destroy every chart
# uninstalls BEFORE any addon is removed — i.e. the addons a chart relies on
# (ebs-csi for PVC/PV teardown, coredns for in-cluster DNS, cert-manager,
# external-dns, ...) stay alive for the entire uninstall. Add a new addon here
# once and all charts inherit the ordering. external_dns is count-gated; the
# splat reference resolves to an empty list when disabled.
resource "null_resource" "cluster_addons" {
  depends_on = [
    aws_eks_addon.vpc_cni,
    aws_eks_addon.kube_proxy,
    aws_eks_addon.coredns,
    aws_eks_addon.pod_identity_agent,
    aws_eks_addon.ebs_csi_driver,
    aws_eks_addon.cert_manager,
    aws_eks_addon.external_dns,
  ]
}

resource "aws_eks_addon" "vpc_cni" {
  cluster_name = module.eks_cluster.cluster_name
  addon_name   = "vpc-cni"
  tags         = local.combined_tags

  # Enable Kubernetes NetworkPolicy enforcement. The VPC CNI ships with the
  # network-policy agent DISABLED by default, which silently makes every
  # NetworkPolicy inert (nothing is blocked). The workspace-ingress policy
  # (charts/workspace-defaults) and the router chart's component policies rely
  # on this being on.
  configuration_values = jsonencode({
    enableNetworkPolicy = "true"
  })
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name = module.eks_cluster.cluster_name
  addon_name   = "kube-proxy"
  tags         = local.combined_tags
}

resource "aws_eks_addon" "coredns" {
  cluster_name = module.eks_cluster.cluster_name
  addon_name   = "coredns"
  tags         = local.combined_tags

  # coredns is a Deployment — pin it to the platform node group.
  configuration_values = jsonencode({
    nodeSelector = local.components_node_selector
  })

  depends_on = [time_sleep.wait_for_nodes]
}

resource "aws_eks_addon" "pod_identity_agent" {
  cluster_name = module.eks_cluster.cluster_name
  addon_name   = "eks-pod-identity-agent"
  tags         = local.combined_tags
}

resource "aws_eks_addon" "ebs_csi_driver" {
  cluster_name = module.eks_cluster.cluster_name
  addon_name   = "aws-ebs-csi-driver"
  tags         = local.combined_tags

  # Pin the controller Deployment to the platform node group. The node plugin is a
  # DaemonSet and is deliberately left to run on every node (workspaces included) —
  # it must be present wherever a workspace EBS volume is mounted.
  # extraVolumeTags: stamps every volume the driver provisions, whatever its StorageClass,
  # so null_resource.reap_csi_volumes and the DeploymentId tag sweep find them.
  configuration_values = jsonencode({
    controller = {
      nodeSelector    = local.components_node_selector
      extraVolumeTags = local.combined_tags
    }
  })

  pod_identity_association {
    role_arn        = module.ebs_csi_role.role_arn
    service_account = "ebs-csi-controller-sa"
  }

  depends_on = [aws_eks_addon.pod_identity_agent]
}

# Destroy-time: delete the EBS volumes the CSI driver provisioned for this deployment.
# Their StorageClasses reclaim on PVC deletion, but a PVC whose deletion is skipped or
# races the cluster going away leaves an unattached volume that bills forever. Matches
# the DeploymentId tag (extraVolumeTags above) AND the driver's own CSIVolumeName tag,
# so only driver-provisioned volumes qualify. Tags apply at creation: volumes created
# before extraVolumeTags was set carry no DeploymentId and are not reaped.
#
# Runs once nothing can hold a volume attached: aws_eks_node_group.platform and
# null_resource.wait_for_lb_cleanup (which terminates Karpenter instances) depend on it,
# so on destroy they are torn down first.
#
# NOT best-effort, like the EC2 templates' reap_volume_backups: a volume still attached
# or a failed delete fails the destroy; an already-deleted volume counts as success, so
# re-running `jd down` converges.
resource "null_resource" "reap_csi_volumes" {
  triggers = {
    deployment_id = random_id.postfix.hex
    region        = var.region
  }

  provisioner "local-exec" {
    when        = destroy
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      region="${self.triggers.region}"
      filters=("Name=tag:DeploymentId,Values=${self.triggers.deployment_id}" "Name=tag-key,Values=CSIVolumeName")
      list_volumes() {
        aws ec2 describe-volumes --region "$region" --filters "$${filters[@]}" "Name=status,Values=$1" \
          --query 'Volumes[].VolumeId' --output text
      }

      echo "Reaping EBS CSI volumes of deployment ${self.triggers.deployment_id}..."
      deadline=$((SECONDS + 600))
      # Plain assignments, not a while condition or a for word list, where a failed
      # describe-volumes would read as "no volumes" instead of failing the destroy.
      while :; do
        attached=$(list_volumes in-use,creating)
        [ -z "$attached" ] && break
        if [ "$SECONDS" -ge "$deadline" ]; then
          echo "ERROR: EBS CSI volumes still attached after 600s: $attached" >&2
          exit 1
        fi
        echo "  Waiting for volumes to detach: $attached"
        sleep 15
      done

      available=$(list_volumes available)
      for vol in $available; do
        if out=$(aws ec2 delete-volume --region "$region" --volume-id "$vol" 2>&1); then
          echo "  Deleted volume: $vol"
        elif grep -q "InvalidVolume.NotFound" <<<"$out"; then
          echo "  Already deleted: $vol"
        else
          echo "ERROR: failed to delete volume $vol: $out" >&2
          exit 1
        fi
      done
      echo "  EBS CSI volume reaping complete."
    EOT
  }
}

resource "aws_eks_addon" "cert_manager" {
  cluster_name = module.eks_cluster.cluster_name
  addon_name   = "cert-manager"
  tags         = local.combined_tags

  # cert-manager ships three Deployments (controller + webhook + cainjector), each with
  # its own nodeSelector — pin all of them to the platform node group.
  configuration_values = jsonencode({
    nodeSelector = local.components_node_selector
    webhook = {
      nodeSelector = local.components_node_selector
    }
    cainjector = {
      nodeSelector = local.components_node_selector
    }
  })

  depends_on = [aws_eks_addon.pod_identity_agent, time_sleep.wait_for_nodes]
}

resource "aws_eks_addon" "external_dns" {
  count        = local.enable_external_dns ? 1 : 0
  cluster_name = module.eks_cluster.cluster_name
  addon_name   = "external-dns"
  tags         = local.combined_tags

  # Stable owner ID tied to the subdomain — a new deployment on the same subdomain
  # takes ownership of existing DNS records instead of conflicting with them.
  # external-dns is a Deployment — pin it to the platform node group.
  configuration_values = jsonencode({
    txtOwnerId    = local.full_domain
    domainFilters = [var.domain]
    nodeSelector  = local.components_node_selector
  })

  pod_identity_association {
    role_arn        = module.external_dns_role[0].role_arn
    service_account = "external-dns"
  }

  depends_on = [aws_eks_addon.pod_identity_agent, time_sleep.wait_for_nodes]
}
