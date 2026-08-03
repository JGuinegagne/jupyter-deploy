"""Static grammar validation for manifest command compositions.

INTENDED FOR UNIT-TEST / CI USE, NOT the runtime manifest-load path. The manifest is a
static template artifact; CI validation (test_manifest_yaml.py + this module's unit tests)
is the fail-fast guarantee — the template ships already-validated. Do NOT wire these
functions into `base_project_handler.retrieve_project_manifest`: the manifest loads on every
`jd` command, a whole-manifest walk buys nothing for a shipped template, may become
non-trivial in Python, and a typo in one command must not block unrelated operations
(e.g. `jd down`). Pydantic field validators still cover the trivially-local rules at load.

Pure functions of the parsed manifest — no project/cluster/IO — so tests call them directly.
"""

from jupyter_deploy.enum import ConditionOperator, InstructionArgumentSource
from jupyter_deploy.exceptions import InvalidCommandGrammarError
from jupyter_deploy.manifest import (
    JupyterDeployCommandV1,
    JupyterDeployConditionOperandV1,
    JupyterDeployManifestV1,
)


def _validate_operand(operand: JupyterDeployConditionOperandV1, ctx: str, violations: list[str]) -> None:
    try:
        source_type = operand.get_source_type()
    except ValueError:
        violations.append(f"{ctx}: unknown operand source '{operand.source}'")
        return

    if source_type == InstructionArgumentSource.LITERAL:
        if operand.value is None:
            violations.append(f"{ctx}: source 'literal' requires 'value'")
    else:
        if not operand.source_key:
            violations.append(f"{ctx}: source '{operand.source}' requires 'source-key'")


def collect_command_violations(command: JupyterDeployCommandV1) -> list[str]:
    """Return the list of grammar violations for a single command (empty if valid)."""
    violations: list[str] = []
    flag_names: set[str] = set()

    for flag in command.flags or []:
        if flag.name in flag_names:
            violations.append(f"command '{command.cmd}': duplicate flag name '{flag.name}'")
        flag_names.add(flag.name)
        if "!" in flag.name:
            violations.append(f"command '{command.cmd}': flag name must not contain '!': '{flag.name}'")

        for idx, condition in enumerate(flag.conditions):
            ctx = f"command '{command.cmd}' flag '{flag.name}' condition[{idx}]"
            try:
                operator = condition.get_operator()
            except ValueError:
                violations.append(f"{ctx}: unknown operator '{condition.operator}'")
                operator = None

            _validate_operand(condition.left, f"{ctx} left", violations)
            _validate_operand(condition.right, f"{ctx} right", violations)

            # `in`'s right operand must be list-typed. A literal scalar can never be a list,
            # so reject it statically. (Output list-ness is only knowable at runtime.)
            if operator == ConditionOperator.IN and condition.right.source.lower() == InstructionArgumentSource.LITERAL:
                violations.append(f"{ctx}: 'in' right operand must be list-typed, not a literal scalar")

    for idx, instruction in enumerate(command.sequence):
        when = instruction.when
        if when is None:
            continue
        ctx = f"command '{command.cmd}' sequence[{idx}]"
        stripped = when[1:] if when.startswith("!") else when
        if not stripped:
            violations.append(f"{ctx}: when: must reference a non-empty flag name")
            continue
        if "!" in stripped:
            violations.append(f"{ctx}: when: allows at most one leading '!' and no interior '!'")
            continue
        if stripped not in flag_names:
            violations.append(f"{ctx}: when: references undefined flag '{stripped}'")

    return violations


def validate_command(command: JupyterDeployCommandV1) -> None:
    """Raise InvalidCommandGrammarError if the command composition is malformed."""
    violations = collect_command_violations(command)
    if violations:
        raise InvalidCommandGrammarError(violations)


def validate_manifest(manifest: JupyterDeployManifestV1) -> None:
    """Raise InvalidCommandGrammarError listing every violation across all commands."""
    violations: list[str] = []
    for command in manifest.commands or []:
        violations.extend(collect_command_violations(command))
    if violations:
        raise InvalidCommandGrammarError(violations)
