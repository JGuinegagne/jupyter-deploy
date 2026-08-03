import unittest

from jupyter_deploy import manifest_validation
from jupyter_deploy.exceptions import InvalidCommandGrammarError
from jupyter_deploy.manifest import JupyterDeployCommandV1, JupyterDeployManifestV1


def _valid_pool_status() -> JupyterDeployCommandV1:
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
                {"api-name": "k8s.custom.get-cluster", "when": "!is-mng", "arguments": []},
                {"api-name": "aws.eks.describe-nodegroup", "when": "is-mng", "arguments": []},
                {"api-name": "core.coalesce-str", "arguments": []},
            ],
        }
    )


class TestValidCommands(unittest.TestCase):
    def test_valid_pool_status_passes(self) -> None:
        manifest_validation.validate_command(_valid_pool_status())  # no raise

    def test_command_without_flags_passes(self) -> None:
        cmd = JupyterDeployCommandV1.model_validate(
            {"cmd": "pool.list", "sequence": [{"api-name": "k8s.custom.list-cluster", "arguments": []}]}
        )
        manifest_validation.validate_command(cmd)  # no raise


class TestRejections(unittest.TestCase):
    def _assert_violation(self, cmd_dict: dict, needle: str) -> None:
        cmd = JupyterDeployCommandV1.model_validate(cmd_dict)
        with self.assertRaises(InvalidCommandGrammarError) as ctx:
            manifest_validation.validate_command(cmd)
        self.assertTrue(
            any(needle in v for v in ctx.exception.violations),
            f"expected a violation containing {needle!r}, got {ctx.exception.violations}",
        )

    def test_when_references_undefined_flag(self) -> None:
        self._assert_violation(
            {
                "cmd": "c",
                "flags": [
                    {
                        "name": "is-mng",
                        "conditions": [
                            {
                                "left": {"source": "cli", "source-key": "name"},
                                "operator": "in",
                                "right": {"source": "output", "source-key": "mng"},
                            }
                        ],
                    }
                ],
                "sequence": [{"api-name": "k8s.custom.get-cluster", "when": "not-a-flag", "arguments": []}],
            },
            "undefined flag",
        )

    def test_duplicate_flag_name(self) -> None:
        cond = {
            "left": {"source": "cli", "source-key": "name"},
            "operator": "in",
            "right": {"source": "output", "source-key": "mng"},
        }
        self._assert_violation(
            {
                "cmd": "c",
                "flags": [
                    {"name": "dup", "conditions": [cond]},
                    {"name": "dup", "conditions": [cond]},
                ],
                "sequence": [],
            },
            "duplicate flag name",
        )

    def test_unknown_operator(self) -> None:
        self._assert_violation(
            {
                "cmd": "c",
                "flags": [
                    {
                        "name": "f",
                        "conditions": [
                            {
                                "left": {"source": "cli", "source-key": "name"},
                                "operator": "not-in",
                                "right": {"source": "output", "source-key": "mng"},
                            }
                        ],
                    }
                ],
                "sequence": [],
            },
            "unknown operator",
        )

    def test_literal_operand_missing_value(self) -> None:
        self._assert_violation(
            {
                "cmd": "c",
                "flags": [
                    {
                        "name": "f",
                        "conditions": [
                            {
                                "left": {"source": "literal"},
                                "operator": "in",
                                "right": {"source": "output", "source-key": "mng"},
                            }
                        ],
                    }
                ],
                "sequence": [],
            },
            "requires 'value'",
        )

    def test_in_with_literal_scalar_right_operand(self) -> None:
        self._assert_violation(
            {
                "cmd": "c",
                "flags": [
                    {
                        "name": "f",
                        "conditions": [
                            {
                                "left": {"source": "cli", "source-key": "name"},
                                "operator": "in",
                                "right": {"source": "literal", "value": "scalar"},
                            }
                        ],
                    }
                ],
                "sequence": [],
            },
            "must be list-typed",
        )

    def test_flag_condition_referencing_instruction_result(self) -> None:
        # Flags are computed before the sequence runs, so a `source: result` operand would
        # always resolve against an empty result set. Reject it statically.
        self._assert_violation(
            {
                "cmd": "c",
                "flags": [
                    {
                        "name": "f",
                        "conditions": [
                            {
                                "left": {"source": "result", "source-key": "[0].Name"},
                                "operator": "in",
                                "right": {"source": "output", "source-key": "mng"},
                            }
                        ],
                    }
                ],
                "sequence": [],
            },
            "must not depend on instruction results",
        )

    def test_validate_manifest_aggregates_across_commands(self) -> None:
        manifest = JupyterDeployManifestV1.model_validate(
            {
                "schema_version": 1,
                "template": {"name": "t", "engine": "terraform", "version": "1"},
                "commands": [
                    {
                        "cmd": "bad",
                        "sequence": [{"api-name": "k8s.custom.get-cluster", "when": "ghost", "arguments": []}],
                    }
                ],
            }
        )
        with self.assertRaises(InvalidCommandGrammarError):
            manifest_validation.validate_manifest(manifest)
