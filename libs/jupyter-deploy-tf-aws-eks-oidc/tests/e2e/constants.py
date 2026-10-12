"""Shared constants for the EKS OIDC e2e suite."""

# Ordered mutating GPU cases (test_workspace_gpu) run as one
# enable_default_gpu_pool on->off window; the ordinal keeps them contiguous.
ORDER_GPU = 10
# Ordered mutating workspace-namespace cases: the single -> multi migration module
# first, then test_workspace_namespaces, which applies one mapping for all its cases.
ORDER_NAMESPACES = 20

GPU_POOL_FLAG = "enable_default_gpu_pool"
# The Karpenter NodePool the flag synthesizes.
GPU_NODEPOOL = "workspace-gpu"
GPU_WORKSPACE = "e2e-gpu-workspace"
GPU_TEMPLATE_NAME = "jupyterlab-gpu"
# Display name of the default GPU WorkspaceTemplate the flag synthesizes
# (engine/platform_karpenter.tf), rendered as a card on the create page.
GPU_TEMPLATE_DISPLAY_NAME = "JupyterLab GPU"
GPU_ROLE = "workspaces-gpu"
GPU_ROLE_SELECTOR = f"jupyter-deploy/role={GPU_ROLE}"
# The karpenter-nodepools chart names each pool's EC2NodeClass after the pool.
GPU_EC2NODECLASS = GPU_NODEPOOL

# Workspace-namespace cases (test_workspace_namespaces, test_workspace_single_to_multi_namespace).
NS_A = "e2e-ns-a"
NS_B = "e2e-ns-b"
NS_SMALL_TEMPLATE = "e2e-cpu-small"
NS_SMALL_TEMPLATE_CONFIG = {"name": NS_SMALL_TEMPLATE, "cpu": "1", "memory": "2Gi", "display_name": "E2E CPU Small"}
# Synthetic teams of JD_E2E_ORG: RBAC subjects only, they need not exist on GitHub.
NS_ONLY_A_TEAM = "e2e-ns-only-a"
NS_ONLY_B_TEAM = "e2e-ns-only-b"
NS_REQUIRED_VARS = ["JD_E2E_USER", "JD_E2E_ORG", "JD_E2E_RBAC_TEAM"]
NS_RUNNING_TIMEOUT_S = 600
# Namespace of the router chart (workspace_router_namespace preset).
ROUTER_NAMESPACE = "jupyter-k8s-router"
WORKSPACE_STOP_PATCH = '{"spec":{"desiredStatus":"Stopped"}}'
WORKSPACE_START_PATCH = '{"spec":{"desiredStatus":"Running"}}'
