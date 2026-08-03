import unittest
from unittest.mock import Mock, patch

from jupyter_deploy.engine.outdefs import ListStrTemplateOutputDefinition, TemplateOutputDefinition
from jupyter_deploy.engine.supervised_execution import NullDisplay
from jupyter_deploy.exceptions import OutputNotFoundError
from jupyter_deploy.manifest import JupyterDeployCommandV1
from jupyter_deploy.provider.core.core_runner import CoreInstructionRunner
from jupyter_deploy.provider.manifest_command_runner import ManifestCommandRunner
from jupyter_deploy.provider.resolved_clidefs import ResolvedCliParameter, StrResolvedCliParameter
from jupyter_deploy.provider.resolved_resultdefs import StrResolvedInstructionResult

_FACTORY = "jupyter_deploy.provider.manifest_command_runner.InstructionRunnerFactory.get_provider_instruction_runner"


def _branch_cmd() -> JupyterDeployCommandV1:
    """A pool.status-style command: is-mng flag, two when-gated branches, a coalesce."""
    return JupyterDeployCommandV1.model_validate(
        {
            "cmd": "pool.status",
            "flags": [
                {
                    "name": "is-mng",
                    "conditions": [
                        {
                            "left": {"source": "cli", "source-key": "name"},
                            "operator": "in",
                            "right": {"source": "output", "source-key": "platform_mng_names"},
                        }
                    ],
                }
            ],
            "sequence": [
                {
                    "api-name": "k8s.custom.get-cluster",
                    "when": "!is-mng",
                    "arguments": [{"api-attribute": "name", "source": "cli", "source-key": "name"}],
                },
                {
                    "api-name": "aws.eks.describe-nodegroup",
                    "when": "is-mng",
                    "arguments": [{"api-attribute": "nodegroup_name", "source": "cli", "source-key": "name"}],
                },
                {
                    "api-name": "core.coalesce-str",
                    "arguments": [
                        {"api-attribute": "value_1", "source": "result", "source-key": "[0].Resource"},
                        {"api-attribute": "value_2", "source": "result", "source-key": "[1].Resource"},
                    ],
                },
            ],
            "results": [{"result-name": "pool.status.resource", "source": "result", "source-key": "[2].Value"}],
        }
    )


def _outputs(names: list[str]) -> dict[str, TemplateOutputDefinition]:
    return {"platform_mng_names": ListStrTemplateOutputDefinition(output_name="platform_mng_names", value=names)}


def _cli(name: str) -> dict[str, ResolvedCliParameter]:
    return {"name": StrResolvedCliParameter(parameter_name="name", value=name)}


class TestFlagAndWhenSkip(unittest.TestCase):
    def _run(self, cmd: JupyterDeployCommandV1, outputs: dict, cli: dict) -> tuple[Mock, ManifestCommandRunner, dict]:
        """Run the command with real Core dispatch but mocked provider runners."""
        output_handler_mock = Mock()
        output_handler_mock.get_full_project_outputs.return_value = outputs

        # k8s.custom.get-cluster and aws.eks.describe-nodegroup are mocked; core.* uses the real runner.
        k8s_runner = Mock()
        k8s_runner.execute_instruction.return_value = {
            "Resource": StrResolvedInstructionResult(result_name="Resource", value='{"kind":"NodePool"}'),
            "Name": StrResolvedInstructionResult(result_name="Name", value="kp-1"),
        }
        aws_runner = Mock()
        aws_runner.execute_instruction.return_value = {
            "Resource": StrResolvedInstructionResult(result_name="Resource", value='{"status":"ACTIVE"}'),
            "NodegroupName": StrResolvedInstructionResult(result_name="NodegroupName", value="ng-a"),
        }

        core_runner = CoreInstructionRunner(NullDisplay())

        def fake_factory(api_name: str, *_args: object, **_kwargs: object) -> Mock:
            if api_name.startswith("k8s."):
                return k8s_runner
            if api_name.startswith("aws."):
                return aws_runner
            if api_name.startswith("core."):
                return core_runner  # type: ignore[return-value]
            raise AssertionError(f"unexpected api_name: {api_name}")

        with patch(_FACTORY, side_effect=fake_factory):
            runner = ManifestCommandRunner(
                display_manager=Mock(), output_handler=output_handler_mock, variable_handler=Mock()
            )
            _, results = runner.run_command_sequence(cmd, cli)

        return output_handler_mock, runner, results

    def test_is_mng_true_runs_mng_branch_only(self) -> None:
        cmd = _branch_cmd()
        _, runner, results = self._run(cmd, _outputs(["ng-a"]), _cli("ng-a"))

        # Karpenter branch [0] skipped → no [0].* results; MNG branch [1] ran.
        self.assertNotIn("[0].Resource", results)
        self.assertIn("[1].Resource", results)
        # coalesce picked the MNG resource
        self.assertEqual(runner.get_result_value(cmd, "pool.status.resource", str), '{"status":"ACTIVE"}')

    def test_is_mng_false_runs_karpenter_branch_only(self) -> None:
        cmd = _branch_cmd()
        _, runner, results = self._run(cmd, _outputs(["ng-a"]), _cli("kp-1"))

        # MNG branch [1] skipped → no [1].* results; Karpenter branch [0] ran.
        self.assertIn("[0].Resource", results)
        self.assertNotIn("[1].Resource", results)
        self.assertEqual(runner.get_result_value(cmd, "pool.status.resource", str), '{"kind":"NodePool"}')

    def test_index_numbering_stable_across_skipped_step(self) -> None:
        # The coalesce is at index [2] regardless of which branch skipped; its result is [2].Value.
        cmd = _branch_cmd()
        _, _, results = self._run(cmd, _outputs(["ng-a"]), _cli("ng-a"))
        self.assertIn("[2].Value", results)

    def test_missing_output_operand_raises_output_not_found(self) -> None:
        cmd = _branch_cmd()
        with self.assertRaises(OutputNotFoundError):
            self._run(cmd, {}, _cli("ng-a"))
