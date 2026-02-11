from enum import Enum

import boto3
from mypy_boto3_ec2.client import EC2Client

from jupyter_deploy.api.aws.ec2 import ec2_instance
from jupyter_deploy.engine.supervised_execution import TerminalHandler
from jupyter_deploy.exceptions import IncompatibleHostStateError, InstructionNotFoundError
from jupyter_deploy.provider.instruction_runner import InstructionRunner
from jupyter_deploy.provider.resolved_argdefs import (
    ResolvedInstructionArgument,
    StrResolvedInstructionArgument,
    require_arg,
)
from jupyter_deploy.provider.resolved_resultdefs import ResolvedInstructionResult, StrResolvedInstructionResult


class AwsEc2Instruction(str, Enum):
    """AWS EC2 instructions accessible from manifest.commands[].sequence[].api-name."""

    DESCRIBE_INSTANCE_STATUS = "describe-instance-status"
    START_INSTANCE = "start-instance"
    STOP_INSTANCE = "stop-instance"
    REBOOT_INSTANCE = "reboot-instance"
    WAIT_FOR_RUNNING = "wait-for-running"
    WAIT_FOR_STOPPED = "wait-for-stopped"


class AwsEc2Runner(InstructionRunner):
    """Runner class for AWS EC2 service API instructions."""

    client: EC2Client

    def __init__(self, region_name: str | None) -> None:
        """Instantiates the EC2 boto3 client."""
        self.client: EC2Client = boto3.client("ec2", region_name=region_name)

    def _describe_instance_status(
        self,
        resolved_arguments: dict[str, ResolvedInstructionArgument],
        terminal_handler: TerminalHandler | None = None,
    ) -> dict[str, ResolvedInstructionResult]:
        # retrieve required parameters
        instance_id_arg = require_arg(resolved_arguments, "instance_id", StrResolvedInstructionArgument)
        instance_id = instance_id_arg.value

        if terminal_handler:
            terminal_handler.info(f"Retrieving status of instance: {instance_id}")

        instance_status = ec2_instance.describe_instance_status(
            self.client,
            instance_id=instance_id,
        )

        if terminal_handler:
            terminal_handler.info(f"Successfully retrieved status of instance: {instance_id}")

        return {
            "InstanceStateName": StrResolvedInstructionResult(
                result_name="InstanceStateName",
                value=instance_status.get("InstanceState", {}).get("Name", "unknown"),
            )
        }

    def _start_instance(
        self,
        resolved_arguments: dict[str, ResolvedInstructionArgument],
        terminal_handler: TerminalHandler | None = None,
    ) -> dict[str, ResolvedInstructionResult]:
        # retrieve required parameters
        instance_id_arg = require_arg(resolved_arguments, "instance_id", StrResolvedInstructionArgument)
        instance_id = instance_id_arg.value

        instance_status = ec2_instance.describe_instance_status(self.client, instance_id=instance_id)
        state = ec2_instance.Ec2InstanceState.from_state_response(instance_status.get("InstanceState", {}))

        if state == ec2_instance.Ec2InstanceState.PENDING:
            raise IncompatibleHostStateError(
                f"Instance '{instance_id}' is already starting",
                hint="Wait for the instance to come online",
            )
        elif state == ec2_instance.Ec2InstanceState.RUNNING:
            raise IncompatibleHostStateError(
                f"Instance '{instance_id}' is already running",
            )
        elif state == ec2_instance.Ec2InstanceState.SHUTTING_DOWN:
            raise IncompatibleHostStateError(
                f"Cannot start instance '{instance_id}', it is being terminated",
            )
        elif state == ec2_instance.Ec2InstanceState.TERMINATED:
            raise IncompatibleHostStateError(
                f"Cannot start terminated instance '{instance_id}'",
            )
        elif state == ec2_instance.Ec2InstanceState.STOPPING:
            raise IncompatibleHostStateError(
                f"Instance '{instance_id}' is stopping",
                hint="Wait for the instance to fully stop",
            )
        elif not state.is_startable():
            raise IncompatibleHostStateError(
                f"Cannot start instance '{instance_id}' in state '{state.value}'",
            )

        ec2_instance.start_instance(
            self.client,
            instance_id=instance_id_arg.value,
        )

        if terminal_handler:
            terminal_handler.success(f"Starting instance {instance_id}...")

        return {}

    def _stop_instance(
        self,
        resolved_arguments: dict[str, ResolvedInstructionArgument],
        terminal_handler: TerminalHandler | None = None,
    ) -> dict[str, ResolvedInstructionResult]:
        # retrieve required parameters
        instance_id_arg = require_arg(resolved_arguments, "instance_id", StrResolvedInstructionArgument)
        instance_id = instance_id_arg.value

        instance_status = ec2_instance.describe_instance_status(self.client, instance_id=instance_id)
        state = ec2_instance.Ec2InstanceState.from_state_response(instance_status.get("InstanceState", {}))

        if state == ec2_instance.Ec2InstanceState.PENDING:
            raise IncompatibleHostStateError(
                f"Instance '{instance_id}' is starting",
                hint="Wait for the instance to come online",
            )
        elif state == ec2_instance.Ec2InstanceState.SHUTTING_DOWN:
            raise IncompatibleHostStateError(
                f"Cannot stop instance '{instance_id}', it is being terminated",
            )
        elif state == ec2_instance.Ec2InstanceState.TERMINATED:
            raise IncompatibleHostStateError(
                f"Cannot stop terminated instance '{instance_id}'",
            )
        elif state == ec2_instance.Ec2InstanceState.STOPPING:
            raise IncompatibleHostStateError(
                f"Instance '{instance_id}' is already stopping",
                hint="Wait for the instance to fully stop",
            )
        elif state == ec2_instance.Ec2InstanceState.STOPPED:
            raise IncompatibleHostStateError(
                f"Instance '{instance_id}' is already stopped",
            )
        elif not state.is_stoppable():
            raise IncompatibleHostStateError(
                f"Cannot stop instance '{instance_id}' in state '{state.value}'",
            )

        ec2_instance.stop_instance(
            self.client,
            instance_id=instance_id,
        )

        if terminal_handler:
            terminal_handler.success(f"Instance {instance_id} is stopping...")

        return {}

    def _reboot_instance(
        self,
        resolved_arguments: dict[str, ResolvedInstructionArgument],
        terminal_handler: TerminalHandler | None = None,
    ) -> dict[str, ResolvedInstructionResult]:
        # retrieve required parameters
        instance_id_arg = require_arg(resolved_arguments, "instance_id", StrResolvedInstructionArgument)
        instance_id = instance_id_arg.value

        instance_status = ec2_instance.describe_instance_status(self.client, instance_id=instance_id)
        state = ec2_instance.Ec2InstanceState.from_state_response(instance_status.get("InstanceState", {}))

        if state == ec2_instance.Ec2InstanceState.PENDING:
            raise IncompatibleHostStateError(
                f"Instance '{instance_id}' is starting",
                hint="Wait for the instance to come online",
            )
        elif state == ec2_instance.Ec2InstanceState.SHUTTING_DOWN:
            raise IncompatibleHostStateError(
                f"Cannot reboot instance '{instance_id}', it is being terminated",
            )
        elif state == ec2_instance.Ec2InstanceState.TERMINATED:
            raise IncompatibleHostStateError(
                f"Cannot reboot terminated instance '{instance_id}'",
            )
        elif state == ec2_instance.Ec2InstanceState.STOPPING:
            raise IncompatibleHostStateError(
                f"Instance '{instance_id}' is stopping",
                hint="Wait for the instance to fully stop, then run 'jd host start'",
            )
        elif state == ec2_instance.Ec2InstanceState.STOPPED:
            raise IncompatibleHostStateError(
                f"Cannot reboot stopped instance '{instance_id}'",
                hint="Run 'jd host start' instead",
            )
        elif not state.is_stoppable():
            raise IncompatibleHostStateError(
                f"Cannot reboot instance '{instance_id}' in state '{state.value}'",
            )

        ec2_instance.restart_instance(
            self.client,
            instance_id=instance_id,
        )

        if terminal_handler:
            terminal_handler.success(f"Instance {instance_id} is rebooting...")

        return {}

    def _wait_for_state(
        self,
        resolved_arguments: dict[str, ResolvedInstructionArgument],
        terminal_handler: TerminalHandler | None,
        desired_state: ec2_instance.Ec2InstanceState,
        timeout_seconds: int = 60,
    ) -> dict[str, ResolvedInstructionResult]:
        instance_id_arg = require_arg(resolved_arguments, "instance_id", StrResolvedInstructionArgument)
        instance_id = instance_id_arg.value
        instance_status = ec2_instance.poll_for_instance_status(
            self.client,
            instance_id=instance_id,
            desired_state=desired_state,
            terminal_handler=terminal_handler,
            timeout_seconds=timeout_seconds,
        )
        return {
            "InstanceStateName": StrResolvedInstructionResult(
                result_name="InstanceStateName",
                value=instance_status.get("InstanceState", {}).get("Name", "unknown"),
            )
        }

    def execute_instruction(
        self,
        instruction_name: str,
        resolved_arguments: dict[str, ResolvedInstructionArgument],
        terminal_handler: TerminalHandler | None = None,
    ) -> dict[str, ResolvedInstructionResult]:
        if instruction_name == AwsEc2Instruction.DESCRIBE_INSTANCE_STATUS:
            return self._describe_instance_status(
                resolved_arguments=resolved_arguments,
                terminal_handler=terminal_handler,
            )
        elif instruction_name == AwsEc2Instruction.START_INSTANCE:
            return self._start_instance(
                resolved_arguments=resolved_arguments,
                terminal_handler=terminal_handler,
            )
        elif instruction_name == AwsEc2Instruction.STOP_INSTANCE:
            return self._stop_instance(
                resolved_arguments=resolved_arguments,
                terminal_handler=terminal_handler,
            )
        elif instruction_name == AwsEc2Instruction.REBOOT_INSTANCE:
            return self._reboot_instance(
                resolved_arguments=resolved_arguments,
                terminal_handler=terminal_handler,
            )
        elif instruction_name == AwsEc2Instruction.WAIT_FOR_RUNNING:
            return self._wait_for_state(
                resolved_arguments=resolved_arguments,
                terminal_handler=terminal_handler,
                desired_state=ec2_instance.Ec2InstanceState.RUNNING,
                timeout_seconds=60,  # EC2:StartInstances is generally fast
            )
        elif instruction_name == AwsEc2Instruction.WAIT_FOR_STOPPED:
            return self._wait_for_state(
                resolved_arguments=resolved_arguments,
                terminal_handler=terminal_handler,
                desired_state=ec2_instance.Ec2InstanceState.STOPPED,
                timeout_seconds=600,  # GPU instances take a while to stop
            )

        raise InstructionNotFoundError(f"No execution implementation for command: 'aws.ec2.{instruction_name}'")
