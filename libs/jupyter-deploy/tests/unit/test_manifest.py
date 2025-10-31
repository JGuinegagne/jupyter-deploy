import unittest
from pathlib import Path
from typing import Any

import yaml

from jupyter_deploy.engine.enum import EngineType
from jupyter_deploy.manifest import InvalidServiceError, JupyterDeployManifestV1


class TestJupyterDeployManifestV1(unittest.TestCase):
    manifest_v1_content: str
    manifest_v1_parsed_content: Any

    @classmethod
    def setUpClass(cls) -> None:
        mock_manifest_path = Path(__file__).parent / "mock_manifest.yaml"
        with open(mock_manifest_path) as f:
            cls.manifest_v1_content = f.read()
        cls.manifest_v1_parsed_content = yaml.safe_load(cls.manifest_v1_content)

    def test_can_parse_manifest_v1(self) -> None:
        JupyterDeployManifestV1(
            **self.manifest_v1_parsed_content  # type: ignore
        )

    def test_manifest_v1_get_engine(self) -> None:
        manifest = JupyterDeployManifestV1(
            **self.manifest_v1_parsed_content  # type: ignore
        )
        self.assertEqual(manifest.get_engine(), EngineType.TERRAFORM)

    def test_manifest_v1_get_declared_value_happy_path(self) -> None:
        manifest = JupyterDeployManifestV1(
            **self.manifest_v1_parsed_content  # type: ignore
        )
        self.assertEqual(
            manifest.get_declared_value("aws_region"),
            manifest.values[1],  # type: ignore
        )

    def test_manifest_v1_get_declared_value_raises_not_implement_error(self) -> None:
        manifest = JupyterDeployManifestV1(
            **self.manifest_v1_parsed_content  # type: ignore
        )
        with self.assertRaises(NotImplementedError):
            manifest.get_declared_value("i_am_not_declared")

    def test_manifest_v1_get_command_happy_path(self) -> None:
        manifest = JupyterDeployManifestV1(
            **self.manifest_v1_parsed_content  # type: ignore
        )
        manifest.get_command("server.status")  # should not raise

    def test_manifest_v1_not_found_command_raises_not_implemented_error(self) -> None:
        manifest = JupyterDeployManifestV1(
            **self.manifest_v1_parsed_content  # type: ignore
        )
        with self.assertRaises(NotImplementedError):
            manifest.get_command("cmd_does_not_exist")

    def test_manifest_v1_has_command_found(self) -> None:
        manifest = JupyterDeployManifestV1(
            **self.manifest_v1_parsed_content  # type: ignore
        )
        self.assertTrue(manifest.has_command("host.status"))

    def test_manifest_v1_has_command_not_found(self) -> None:
        manifest = JupyterDeployManifestV1(
            **self.manifest_v1_parsed_content  # type: ignore
        )
        self.assertFalse(manifest.has_command("i.do.not.exist"))

    def test_manifest_v1_get_services(self) -> None:
        manifest = JupyterDeployManifestV1(
            **self.manifest_v1_parsed_content  # type: ignore
        )
        self.assertListEqual(manifest.get_services(), ["jupyter", "traefik", "oauth"])

    def test_manifest_v1_get_validated_service(self) -> None:
        manifest = JupyterDeployManifestV1(
            **self.manifest_v1_parsed_content  # type: ignore
        )
        for svc in ["jupyter", "traefik", "oauth"]:
            self.assertEqual(manifest.get_validated_service(svc), svc)

    def test_manifest_v1_get_validated_service_default_return_first_value(self) -> None:
        manifest = JupyterDeployManifestV1(
            **self.manifest_v1_parsed_content  # type: ignore
        )
        self.assertEqual(manifest.get_validated_service("default"), "jupyter")

    def test_manifest_v1_get_validated_service_all_allowed(self) -> None:
        manifest = JupyterDeployManifestV1(
            **self.manifest_v1_parsed_content  # type: ignore
        )
        self.assertEqual(manifest.get_validated_service("all", allow_all=True), "all")

    def test_manifest_v1_get_validated_service_all_disallowed(self) -> None:
        manifest = JupyterDeployManifestV1(
            **self.manifest_v1_parsed_content  # type: ignore
        )
        with self.assertRaises(InvalidServiceError):
            manifest.get_validated_service("all", allow_all=False)
