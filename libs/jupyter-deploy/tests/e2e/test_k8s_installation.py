"""K8s install track tests — validate the CLI works with the [k8s] extra.

These tests run in the ``aws`` install track where ``jupyter-deploy[aws,k8s]``
is installed alongside the base template.
"""

import unittest


class TestK8sInstallation(unittest.TestCase):
    def test_kubernetes_importable(self) -> None:
        import kubernetes  # noqa: F401

    def test_k8s_provider_importable(self) -> None:
        from jupyter_deploy.provider.k8s import k8s_runner  # noqa: F401
