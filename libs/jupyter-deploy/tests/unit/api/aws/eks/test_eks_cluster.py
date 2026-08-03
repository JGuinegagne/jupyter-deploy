import unittest
from unittest.mock import Mock

from botocore.exceptions import ClientError
from mypy_boto3_eks.client import EKSClient
from mypy_boto3_eks.type_defs import ClusterTypeDef

from jupyter_deploy.api.aws.eks import eks_cluster


def _not_found_error() -> ClientError:
    return ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "Cluster not found"}},
        "DescribeCluster",
    )


class TestDescribeCluster(unittest.TestCase):
    def test_returns_cluster_details(self) -> None:
        mock_client: Mock = Mock(spec=EKSClient)
        cluster: ClusterTypeDef = {
            "name": "my-cluster",
            "status": "ACTIVE",
            "endpoint": "https://abc.eks.amazonaws.com",
            "version": "1.31",
        }
        mock_client.describe_cluster.return_value = {"cluster": cluster}

        result = eks_cluster.describe_cluster(mock_client, cluster_name="my-cluster")

        self.assertEqual(result["name"], "my-cluster")
        self.assertEqual(result["status"], "ACTIVE")
        mock_client.describe_cluster.assert_called_once_with(name="my-cluster")

    def test_raises_on_client_error(self) -> None:
        mock_client: Mock = Mock(spec=EKSClient)
        mock_client.describe_cluster.side_effect = _not_found_error()

        with self.assertRaises(ClientError):
            eks_cluster.describe_cluster(mock_client, cluster_name="nonexistent")
