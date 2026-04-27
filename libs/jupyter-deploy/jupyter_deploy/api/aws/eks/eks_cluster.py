from mypy_boto3_eks.client import EKSClient
from mypy_boto3_eks.type_defs import ClusterTypeDef, DescribeNodegroupResponseTypeDef, NodegroupTypeDef


def describe_cluster(client: EKSClient, cluster_name: str) -> ClusterTypeDef:
    """Call EKS:DescribeCluster and return the cluster details."""
    response = client.describe_cluster(name=cluster_name)
    return response["cluster"]


def list_nodegroups(
    client: EKSClient, cluster_name: str, starting_token: str | None = None
) -> tuple[list[str], str | None]:
    """Call EKS:ListNodegroups and return nodegroup names with optional next token."""
    kwargs: dict[str, str] = {"clusterName": cluster_name}
    if starting_token:
        kwargs["nextToken"] = starting_token

    response = client.list_nodegroups(**kwargs)
    next_token = response.get("nextToken")
    return response["nodegroups"], next_token


def describe_nodegroup(client: EKSClient, cluster_name: str, nodegroup_name: str) -> NodegroupTypeDef:
    """Call EKS:DescribeNodegroup and return the nodegroup details."""
    response: DescribeNodegroupResponseTypeDef = client.describe_nodegroup(
        clusterName=cluster_name, nodegroupName=nodegroup_name
    )
    return response["nodegroup"]
