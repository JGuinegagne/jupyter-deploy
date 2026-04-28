import unittest
from unittest.mock import Mock, patch

from jupyter_deploy.provider.k8s.k8s_client_factory import K8sClientFactory


class TestK8sClientFactory(unittest.TestCase):
    @patch("jupyter_deploy.provider.k8s.k8s_client_factory.config")
    def test_from_kubeconfig_with_path(self, mock_config: Mock) -> None:
        mock_api_client: Mock = Mock()
        mock_config.new_client_from_config.return_value = mock_api_client

        result = K8sClientFactory.from_kubeconfig(kubeconfig_path="/home/user/.kube/config")

        self.assertEqual(result, mock_api_client)
        mock_config.new_client_from_config.assert_called_once_with(config_file="/home/user/.kube/config")

    @patch("jupyter_deploy.provider.k8s.k8s_client_factory.config")
    def test_from_kubeconfig_without_path_uses_default(self, mock_config: Mock) -> None:
        mock_api_client: Mock = Mock()
        mock_config.new_client_from_config.return_value = mock_api_client

        result = K8sClientFactory.from_kubeconfig()

        self.assertEqual(result, mock_api_client)
        mock_config.new_client_from_config.assert_called_once_with(config_file=None)
