"""Unit tests for the kubernetes.services helpers."""

import unittest
from unittest.mock import Mock, patch

from pytest_jupyter_deploy.kubernetes.services import get_service_port


class TestGetServicePort(unittest.TestCase):
    @patch("pytest_jupyter_deploy.kubernetes.services.run_kubectl")
    def test_single_port(self, mock_run: Mock) -> None:
        mock_run.return_value = Mock(stdout="8443")
        self.assertEqual(get_service_port("web-app", "router"), 8443)
        mock_run.assert_called_once_with(
            "get", "service", "web-app", "-n", "router", "-o", "jsonpath={.spec.ports[*].port}", check=True
        )

    @patch("pytest_jupyter_deploy.kubernetes.services.run_kubectl")
    def test_several_ports_raise(self, mock_run: Mock) -> None:
        mock_run.return_value = Mock(stdout="8090 8443")
        with self.assertRaises(ValueError):
            get_service_port("web-app", "router")

    @patch("pytest_jupyter_deploy.kubernetes.services.run_kubectl")
    def test_no_port_raises(self, mock_run: Mock) -> None:
        mock_run.return_value = Mock(stdout="")
        with self.assertRaises(ValueError):
            get_service_port("web-app", "router")
