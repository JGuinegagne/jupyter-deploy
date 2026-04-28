import unittest
from unittest.mock import Mock

from botocore.exceptions import ClientError
from mypy_boto3_eks.client import EKSClient
from mypy_boto3_eks.type_defs import ClusterTypeDef, NodegroupTypeDef

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


class TestListNodegroups(unittest.TestCase):
    def test_returns_nodegroup_names_and_no_next_token(self) -> None:
        mock_client: Mock = Mock(spec=EKSClient)
        mock_client.list_nodegroups.return_value = {"nodegroups": ["ng-1", "ng-2"]}

        nodegroups, next_token = eks_cluster.list_nodegroups(mock_client, cluster_name="my-cluster")

        self.assertEqual(nodegroups, ["ng-1", "ng-2"])
        self.assertIsNone(next_token)
        mock_client.list_nodegroups.assert_called_once_with(clusterName="my-cluster")

    def test_returns_next_token_when_present(self) -> None:
        mock_client: Mock = Mock(spec=EKSClient)
        mock_client.list_nodegroups.return_value = {"nodegroups": ["ng-1"], "nextToken": "token-abc"}

        nodegroups, next_token = eks_cluster.list_nodegroups(mock_client, cluster_name="my-cluster")

        self.assertEqual(nodegroups, ["ng-1"])
        self.assertEqual(next_token, "token-abc")

    def test_passes_starting_token(self) -> None:
        mock_client: Mock = Mock(spec=EKSClient)
        mock_client.list_nodegroups.return_value = {"nodegroups": ["ng-2"]}

        nodegroups, next_token = eks_cluster.list_nodegroups(
            mock_client, cluster_name="my-cluster", starting_token="token-abc"
        )

        self.assertEqual(nodegroups, ["ng-2"])
        self.assertIsNone(next_token)
        mock_client.list_nodegroups.assert_called_once_with(clusterName="my-cluster", nextToken="token-abc")

    def test_raises_on_client_error(self) -> None:
        mock_client: Mock = Mock(spec=EKSClient)
        mock_client.list_nodegroups.side_effect = _not_found_error()

        with self.assertRaises(ClientError):
            eks_cluster.list_nodegroups(mock_client, cluster_name="nonexistent")


class TestDescribeNodegroup(unittest.TestCase):
    def test_returns_nodegroup_details(self) -> None:
        mock_client: Mock = Mock(spec=EKSClient)
        nodegroup: NodegroupTypeDef = {
            "nodegroupName": "ng-1",
            "status": "ACTIVE",
        }
        mock_client.describe_nodegroup.return_value = {"nodegroup": nodegroup}

        result = eks_cluster.describe_nodegroup(mock_client, cluster_name="my-cluster", nodegroup_name="ng-1")

        self.assertEqual(result["nodegroupName"], "ng-1")
        self.assertEqual(result["status"], "ACTIVE")
        mock_client.describe_nodegroup.assert_called_once_with(clusterName="my-cluster", nodegroupName="ng-1")

    def test_raises_on_client_error(self) -> None:
        mock_client: Mock = Mock(spec=EKSClient)
        mock_client.describe_nodegroup.side_effect = _not_found_error()

        with self.assertRaises(ClientError):
            eks_cluster.describe_nodegroup(mock_client, cluster_name="my-cluster", nodegroup_name="nonexistent")
