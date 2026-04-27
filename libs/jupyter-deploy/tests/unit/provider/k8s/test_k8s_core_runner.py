import unittest
from unittest.mock import Mock, patch

from jupyter_deploy.api.k8s.core import NodeConditionStatus, NodeInfo, PodInfo, PodPhase
from jupyter_deploy.engine.supervised_execution import NullDisplay
from jupyter_deploy.exceptions import InstructionNotFoundError
from jupyter_deploy.provider.k8s.k8s_core_runner import K8sCoreRunner
from jupyter_deploy.provider.resolved_argdefs import StrResolvedInstructionArgument


class TestK8sCoreRunner(unittest.TestCase):
    def _make_runner(self) -> tuple[K8sCoreRunner, Mock]:
        mock_api_client: Mock = Mock()
        with patch("jupyter_deploy.provider.k8s.k8s_core_runner.client") as mock_client_mod:
            mock_client_mod.CoreV1Api.return_value = Mock()
            runner = K8sCoreRunner(NullDisplay(), api_client=mock_api_client)
        return runner, runner.core_api

    @patch("jupyter_deploy.provider.k8s.k8s_core_runner.k8s_core")
    def test_list_nodes_returns_names_and_count(self, mock_k8s_core: Mock) -> None:
        runner, _ = self._make_runner()
        mock_k8s_core.list_nodes.return_value = (
            [
                NodeInfo(name="node-1", status=NodeConditionStatus.READY),
                NodeInfo(name="node-2", status=NodeConditionStatus.READY),
            ],
            None,
        )

        result = runner.execute_instruction(instruction_name="list-nodes", resolved_arguments={})

        self.assertEqual(result["NodeNames"].value, "node-1,node-2")
        self.assertEqual(result["NextToken"].value, "")
        mock_k8s_core.list_nodes.assert_called_once_with(
            runner.core_api, label_selector=None, limit=None, _continue=None
        )

    @patch("jupyter_deploy.provider.k8s.k8s_core_runner.k8s_core")
    def test_list_nodes_with_label_selector(self, mock_k8s_core: Mock) -> None:
        runner, _ = self._make_runner()
        mock_k8s_core.list_nodes.return_value = ([], None)

        runner.execute_instruction(
            instruction_name="list-nodes",
            resolved_arguments={
                "query": StrResolvedInstructionArgument(argument_name="query", value="role=worker"),
            },
        )

        mock_k8s_core.list_nodes.assert_called_once_with(
            runner.core_api, label_selector="role=worker", limit=None, _continue=None
        )

    @patch("jupyter_deploy.provider.k8s.k8s_core_runner.k8s_core")
    def test_list_nodes_with_pagination(self, mock_k8s_core: Mock) -> None:
        runner, _ = self._make_runner()
        mock_k8s_core.list_nodes.return_value = (
            [NodeInfo(name="node-1", status=NodeConditionStatus.READY)],
            "abc123",
        )

        result = runner.execute_instruction(
            instruction_name="list-nodes",
            resolved_arguments={
                "page_size": StrResolvedInstructionArgument(argument_name="page_size", value="1"),
            },
        )

        self.assertEqual(result["NextToken"].value, "abc123")
        mock_k8s_core.list_nodes.assert_called_once_with(runner.core_api, label_selector=None, limit=1, _continue=None)

    @patch("jupyter_deploy.provider.k8s.k8s_core_runner.k8s_core")
    def test_list_nodes_with_pagination_token(self, mock_k8s_core: Mock) -> None:
        runner, _ = self._make_runner()
        mock_k8s_core.list_nodes.return_value = ([], None)

        runner.execute_instruction(
            instruction_name="list-nodes",
            resolved_arguments={
                "pagination_token": StrResolvedInstructionArgument(argument_name="pagination_token", value="abc123"),
            },
        )

        mock_k8s_core.list_nodes.assert_called_once_with(
            runner.core_api, label_selector=None, limit=None, _continue="abc123"
        )

    @patch("jupyter_deploy.provider.k8s.k8s_core_runner.k8s_core")
    def test_get_node_ready(self, mock_k8s_core: Mock) -> None:
        runner, _ = self._make_runner()
        mock_k8s_core.get_node.return_value = NodeInfo(name="node-1", status=NodeConditionStatus.READY)

        result = runner.execute_instruction(
            instruction_name="get-node",
            resolved_arguments={
                "name": StrResolvedInstructionArgument(argument_name="name", value="node-1"),
            },
        )

        self.assertEqual(result["Name"].value, "node-1")
        self.assertEqual(result["Status"].value, "Ready")

    @patch("jupyter_deploy.provider.k8s.k8s_core_runner.k8s_core")
    def test_get_node_not_ready(self, mock_k8s_core: Mock) -> None:
        runner, _ = self._make_runner()
        mock_k8s_core.get_node.return_value = NodeInfo(name="node-1", status=NodeConditionStatus.NOT_READY)

        result = runner.execute_instruction(
            instruction_name="get-node",
            resolved_arguments={
                "name": StrResolvedInstructionArgument(argument_name="name", value="node-1"),
            },
        )

        self.assertEqual(result["Status"].value, "NotReady")

    @patch("jupyter_deploy.provider.k8s.k8s_core_runner.k8s_core")
    def test_list_pods_returns_names_and_count(self, mock_k8s_core: Mock) -> None:
        runner, _ = self._make_runner()
        mock_k8s_core.list_pods.return_value = (
            [
                PodInfo(name="pod-1", phase=PodPhase.RUNNING),
                PodInfo(name="pod-2", phase=PodPhase.RUNNING),
            ],
            None,
        )

        result = runner.execute_instruction(
            instruction_name="list-pods",
            resolved_arguments={
                "scope": StrResolvedInstructionArgument(argument_name="scope", value="default"),
            },
        )

        self.assertEqual(result["PodNames"].value, "pod-1,pod-2")
        self.assertEqual(result["NextToken"].value, "")
        mock_k8s_core.list_pods.assert_called_once_with(
            runner.core_api, namespace="default", label_selector=None, limit=None, _continue=None
        )

    @patch("jupyter_deploy.provider.k8s.k8s_core_runner.k8s_core")
    def test_list_pods_with_pagination(self, mock_k8s_core: Mock) -> None:
        runner, _ = self._make_runner()
        mock_k8s_core.list_pods.return_value = (
            [PodInfo(name="pod-1", phase=PodPhase.RUNNING)],
            "xyz789",
        )

        result = runner.execute_instruction(
            instruction_name="list-pods",
            resolved_arguments={
                "scope": StrResolvedInstructionArgument(argument_name="scope", value="default"),
                "page_size": StrResolvedInstructionArgument(argument_name="page_size", value="1"),
            },
        )

        self.assertEqual(result["NextToken"].value, "xyz789")
        mock_k8s_core.list_pods.assert_called_once_with(
            runner.core_api, namespace="default", label_selector=None, limit=1, _continue=None
        )

    @patch("jupyter_deploy.provider.k8s.k8s_core_runner.k8s_core")
    def test_list_pods_with_pagination_token(self, mock_k8s_core: Mock) -> None:
        runner, _ = self._make_runner()
        mock_k8s_core.list_pods.return_value = ([], None)

        runner.execute_instruction(
            instruction_name="list-pods",
            resolved_arguments={
                "scope": StrResolvedInstructionArgument(argument_name="scope", value="default"),
                "pagination_token": StrResolvedInstructionArgument(argument_name="pagination_token", value="xyz789"),
            },
        )

        mock_k8s_core.list_pods.assert_called_once_with(
            runner.core_api, namespace="default", label_selector=None, limit=None, _continue="xyz789"
        )

    @patch("jupyter_deploy.provider.k8s.k8s_core_runner.k8s_core")
    def test_get_pod_running(self, mock_k8s_core: Mock) -> None:
        runner, _ = self._make_runner()
        mock_k8s_core.get_pod.return_value = PodInfo(name="pod-1", phase=PodPhase.RUNNING)

        result = runner.execute_instruction(
            instruction_name="get-pod",
            resolved_arguments={
                "name": StrResolvedInstructionArgument(argument_name="name", value="pod-1"),
                "scope": StrResolvedInstructionArgument(argument_name="scope", value="default"),
            },
        )

        self.assertEqual(result["Name"].value, "pod-1")
        self.assertEqual(result["Phase"].value, "Running")

    def test_unknown_instruction_raises_error(self) -> None:
        runner, _ = self._make_runner()

        with self.assertRaises(InstructionNotFoundError):
            runner.execute_instruction(instruction_name="unknown", resolved_arguments={})
