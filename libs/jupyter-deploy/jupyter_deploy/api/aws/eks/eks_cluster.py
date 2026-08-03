from mypy_boto3_eks.client import EKSClient
from mypy_boto3_eks.type_defs import ClusterTypeDef


def describe_cluster(client: EKSClient, cluster_name: str) -> ClusterTypeDef:
    """Call EKS:DescribeCluster and return the cluster details."""
    response = client.describe_cluster(name=cluster_name)
    return response["cluster"]
