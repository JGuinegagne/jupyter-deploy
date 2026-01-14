import unittest
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from jupyter_deploy.cli.servers_app import servers_app
from jupyter_deploy.manifest import InvalidServiceError


class TestServersApp(unittest.TestCase):
    def test_help_command(self) -> None:
        self.assertTrue(len(servers_app.info.help or "") > 0, "help should not be empty")

        runner = CliRunner()
        result = runner.invoke(servers_app, ["--help"])

        self.assertEqual(result.exit_code, 0)
        for cmd in ["status", "start", "stop", "restart"]:
            self.assertTrue(result.stdout.index(cmd) > 0, f"missing command: {cmd}")

    def test_no_arg_defaults_to_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(servers_app, [])

        self.assertEqual(result.exit_code, 0)
        self.assertTrue(len(result.stdout) > 0)


class TestServerStatusCmd(unittest.TestCase):
    def get_mock_server_handler(self) -> tuple[Mock, dict[str, Mock]]:
        """Return a mock server handler."""
        mock_get_server_status = Mock()
        mock_get_console = Mock()
        mock_server_handler = Mock()

        mock_server_handler.get_server_status = mock_get_server_status
        mock_server_handler.get_console = mock_get_console

        mock_get_server_status.return_value = "IN_SERVICE"
        mock_get_console.return_value = Mock()

        return mock_server_handler, {
            "get_server_status": mock_get_server_status,
            "get_console": mock_get_console,
        }

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_instantiates_server_handler_and_call_status(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["status"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_server_handler_class.assert_called_once()
        mock_handler_fns["get_server_status"].assert_called_once()
        mock_handler_fns["get_console"].assert_called_once()

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_uses_handler_console_to_print_status_response(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler

        mock_console = Mock()
        mock_handler_fns["get_console"].return_value = mock_console
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["status"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_console.print.assert_called_once()
        mock_call = mock_console.print.mock_calls[0]
        self.assertTrue("IN_SERVICE" in mock_call[1][0])

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_switches_dir_when_passed_a_project(self, mock_project_dir: Mock, mock_server_handler_class: Mock) -> None:
        # Setup
        mock_server_handler, _ = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["status", "--path", "/test/project/path"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_project_dir.assert_called_once_with("/test/project/path")

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_raises_when_server_handler_get_server_status_raises(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_handler_fns["get_server_status"].side_effect = Exception("Test error")
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["status"])

        # Assert
        self.assertNotEqual(result.exit_code, 0)


class TestServerStartCmd(unittest.TestCase):
    def get_mock_server_handler(self) -> tuple[Mock, dict[str, Mock]]:
        """Return a mock server handler."""
        mock_start_server = Mock()
        mock_get_console = Mock()
        mock_server_handler = Mock()

        mock_server_handler.start_server = mock_start_server
        mock_server_handler.get_console = mock_get_console

        mock_get_console.return_value = Mock()

        return mock_server_handler, {
            "start_server": mock_start_server,
            "get_console": mock_get_console,
        }

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_instantiates_server_handler_and_calls_start(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["start"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_server_handler_class.assert_called_once()
        mock_handler_fns["start_server"].assert_called_once_with("all")
        mock_handler_fns["get_console"].assert_called_once()

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_print_the_valid_services_when_passed_an_invalid_service(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        mock_handler_fns["start_server"].side_effect = InvalidServiceError(
            "Invalid service, use one of ['jupyter', 'traefik']"
        )

        # Set up the console mock
        mock_console = Mock()
        mock_handler_fns["get_console"].return_value = mock_console

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["start", "--service", "invalid_service"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_console.print.assert_called_once()
        mock_call = mock_console.print.mock_calls[0]
        self.assertTrue("Invalid service" in mock_call[1][0])
        self.assertTrue("red" in mock_call[2]["style"])

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_switches_dir_when_passed_a_project(self, mock_project_dir: Mock, mock_server_handler_class: Mock) -> None:
        # Setup
        mock_server_handler, _ = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["start", "--path", "/test/project/path"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_project_dir.assert_called_once_with("/test/project/path")

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_raises_when_start_raises(self, mock_project_dir: Mock, mock_server_handler_class: Mock) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_handler_fns["start_server"].side_effect = Exception("Test error")
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["start"])

        # Assert
        self.assertNotEqual(result.exit_code, 0)

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_service_parameter_passes_service_name_for_start(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["start", "--service", "jupyter"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_handler_fns["start_server"].assert_called_once_with("jupyter")


class TestServerStopCmd(unittest.TestCase):
    def get_mock_server_handler(self) -> tuple[Mock, dict[str, Mock]]:
        """Return a mock server handler."""
        mock_stop_server = Mock()
        mock_get_console = Mock()
        mock_server_handler = Mock()

        mock_server_handler.stop_server = mock_stop_server
        mock_server_handler.get_console = mock_get_console

        mock_get_console.return_value = Mock()

        return mock_server_handler, {
            "stop_server": mock_stop_server,
            "get_console": mock_get_console,
        }

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_instantiates_server_handler_and_calls_stop(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["stop"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_server_handler_class.assert_called_once()
        mock_handler_fns["stop_server"].assert_called_once_with("all")
        mock_handler_fns["get_console"].assert_called_once()

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_print_the_valid_services_when_passed_an_invalid_service(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        mock_handler_fns["stop_server"].side_effect = InvalidServiceError(
            "Invalid service, use one of ['jupyter', 'traefik']"
        )

        # Set up the console mock
        mock_console = Mock()
        mock_handler_fns["get_console"].return_value = mock_console

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["stop", "--service", "invalid_service"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_console.print.assert_called_once()
        mock_call = mock_console.print.mock_calls[0]
        self.assertTrue("Invalid service" in mock_call[1][0])
        self.assertTrue("red" in mock_call[2]["style"])

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_switches_dir_when_passed_a_project(self, mock_project_dir: Mock, mock_server_handler_class: Mock) -> None:
        # Setup
        mock_server_handler, _ = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["stop", "--path", "/test/project/path"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_project_dir.assert_called_once_with("/test/project/path")

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_raises_when_stop_raises(self, mock_project_dir: Mock, mock_server_handler_class: Mock) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_handler_fns["stop_server"].side_effect = Exception("Test error")
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["stop"])

        # Assert
        self.assertNotEqual(result.exit_code, 0)

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_service_parameter_passes_service_name_for_stop(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["stop", "--service", "jupyter"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_handler_fns["stop_server"].assert_called_once_with("jupyter")


class TestServerRestartCmd(unittest.TestCase):
    def get_mock_server_handler(self) -> tuple[Mock, dict[str, Mock]]:
        """Return a mock server handler."""
        mock_restart_server = Mock()
        mock_get_console = Mock()
        mock_server_handler = Mock()

        mock_server_handler.restart_server = mock_restart_server
        mock_server_handler.get_console = mock_get_console

        mock_get_console.return_value = Mock()

        return mock_server_handler, {
            "restart_server": mock_restart_server,
            "get_console": mock_get_console,
        }

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_instantiates_server_handler_and_calls_restart(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["restart"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_server_handler_class.assert_called_once()
        mock_handler_fns["restart_server"].assert_called_once_with("all")
        mock_handler_fns["get_console"].assert_called_once()

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_print_the_valid_services_when_passed_an_invalid_service(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        mock_handler_fns["restart_server"].side_effect = InvalidServiceError(
            "Invalid service, use one of ['jupyter', 'traefik']"
        )

        # Set up the console mock
        mock_console = Mock()
        mock_handler_fns["get_console"].return_value = mock_console

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["restart", "--service", "invalid_service"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_console.print.assert_called_once()
        mock_call = mock_console.print.mock_calls[0]
        self.assertTrue("Invalid service" in mock_call[1][0])
        self.assertTrue("red" in mock_call[2]["style"])

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_switches_dir_when_passed_a_project(self, mock_project_dir: Mock, mock_server_handler_class: Mock) -> None:
        # Setup
        mock_server_handler, _ = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["restart", "--path", "/test/project/path"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_project_dir.assert_called_once_with("/test/project/path")

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_raises_when_restart_raises(self, mock_project_dir: Mock, mock_server_handler_class: Mock) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_handler_fns["restart_server"].side_effect = Exception("Test error")
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["restart"])

        # Assert
        self.assertNotEqual(result.exit_code, 0)

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_service_parameter_passes_service_name_for_restart(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["restart", "--service", "jupyter"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_handler_fns["restart_server"].assert_called_once_with("jupyter")


class TestServerLogsCmd(unittest.TestCase):
    def get_mock_server_handler(self) -> tuple[Mock, dict[str, Mock]]:
        """Return a mock server handler."""
        mock_get_server_logs = Mock()
        mock_get_console = Mock()
        mock_server_handler = Mock()

        mock_server_handler.get_server_logs = mock_get_server_logs
        mock_server_handler.get_console = mock_get_console

        mock_get_server_logs.return_value = "Sample log output"
        mock_get_console.return_value = Mock()

        return mock_server_handler, {
            "get_server_logs": mock_get_server_logs,
            "get_console": mock_get_console,
        }

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_instantiates_server_handler_and_calls_get_logs_and_print_results(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        mock_console = Mock()
        mock_handler_fns["get_console"].return_value = mock_console
        mock_handler_fns["get_server_logs"].return_value = "some-logs", "some-errors"

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["logs"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_server_handler_class.assert_called_once()
        mock_handler_fns["get_server_logs"].assert_called_once_with(service="default", extra=[])
        mock_handler_fns["get_console"].assert_called()
        mock_console.print.assert_called()
        mock_console.rule.assert_called()

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_print_the_valid_services_when_passed_an_invalid_service(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        mock_handler_fns["get_server_logs"].side_effect = InvalidServiceError(
            "Invalid service, use one of ['jupyter', 'traefik']"
        )

        # Set up the console mock
        mock_console = Mock()
        mock_handler_fns["get_console"].return_value = mock_console

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["logs", "--service", "invalid_service"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_console.print.assert_called_once()
        mock_call = mock_console.print.mock_calls[0]
        self.assertTrue("Invalid service" in mock_call[1][0])
        self.assertTrue("red" in mock_call[2]["style"])

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_prints_placeholder_when_no_logs_are_returned(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        # Set up the logs to be empty
        mock_handler_fns["get_server_logs"].return_value = ""

        # Set up the console mock
        mock_console = Mock()
        mock_handler_fns["get_console"].return_value = mock_console
        mock_handler_fns["get_server_logs"].return_value = "", ""

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["logs"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_console.print.assert_called_once()
        mock_call = mock_console.print.mock_calls[0]
        self.assertTrue("no logs were retrieved" in mock_call[1][0])
        self.assertTrue("yellow" in mock_call[2]["style"])

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_instantiates_raises_when_server_handler_raises(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_handler_fns["get_server_logs"].side_effect = Exception("Test error")
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["logs"])

        # Assert
        self.assertNotEqual(result.exit_code, 0)


class TestServerExecCmd(unittest.TestCase):
    def get_mock_server_handler(self) -> tuple[Mock, dict[str, Mock]]:
        """Return a mock server handler."""
        mock_exec_command = Mock()
        mock_get_console = Mock()
        mock_server_handler = Mock()

        mock_server_handler.exec_command = mock_exec_command
        mock_server_handler.get_console = mock_get_console

        mock_exec_command.return_value = ("stdout output", "stderr output")
        mock_get_console.return_value = Mock()

        return mock_server_handler, {
            "exec_command": mock_exec_command,
            "get_console": mock_get_console,
        }

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_help_includes_exec_command(self, mock_project_dir: Mock, mock_server_handler_class: Mock) -> None:
        runner = CliRunner()
        result = runner.invoke(servers_app, ["--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertTrue("exec" in result.stdout, "exec command should appear in help")

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_instantiates_handler_and_calls_exec_command(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        mock_console = Mock()
        mock_handler_fns["get_console"].return_value = mock_console

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["exec", "-s", "jupyter", "--", "pwd"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_server_handler_class.assert_called_once()
        mock_handler_fns["exec_command"].assert_called_once_with(service="jupyter", command_args=["pwd"])
        mock_handler_fns["get_console"].assert_called_once()

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_passes_command_args_to_handler(self, mock_project_dir: Mock, mock_server_handler_class: Mock) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["exec", "-s", "jupyter", "--", "ls", "-la"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_handler_fns["exec_command"].assert_called_once_with(service="jupyter", command_args=["ls", "-la"])

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_prints_stdout_and_stderr(self, mock_project_dir: Mock, mock_server_handler_class: Mock) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler

        mock_console = Mock()
        mock_handler_fns["get_console"].return_value = mock_console
        mock_handler_fns["exec_command"].return_value = ("test stdout", "test stderr")
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["exec", "-s", "jupyter", "--", "whoami"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_console.print.assert_called()
        print_calls = [str(call) for call in mock_console.print.mock_calls]
        self.assertTrue(any("test stdout" in call for call in print_calls))
        self.assertTrue(any("test stderr" in call for call in print_calls))

    @patch("jupyter_deploy.cli.servers_app.Console")
    def test_fails_when_no_command_provided(self, mock_console_class: Mock) -> None:
        # Setup
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["exec", "-s", "jupyter"])

        # Assert
        self.assertEqual(result.exit_code, 1)
        mock_console_class.assert_called_once()
        mock_console.print.assert_called()

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_prints_error_when_invalid_service(self, mock_project_dir: Mock, mock_server_handler_class: Mock) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        mock_handler_fns["exec_command"].side_effect = InvalidServiceError(
            "Invalid service, use one of ['jupyter', 'traefik']"
        )

        mock_console = Mock()
        mock_handler_fns["get_console"].return_value = mock_console

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["exec", "-s", "invalid_service", "--", "pwd"])

        # Assert
        self.assertEqual(result.exit_code, 1)
        mock_console.print.assert_called_once()
        mock_call = mock_console.print.mock_calls[0]
        self.assertTrue("Invalid service" in mock_call[1][0])
        self.assertTrue("red" in mock_call[2]["style"])

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_raises_when_handler_exec_command_raises(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_handler_fns["exec_command"].side_effect = Exception("Test error")
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["exec", "-s", "jupyter", "--", "whoami"])

        # Assert
        self.assertNotEqual(result.exit_code, 0)


class TestServerConnectCmd(unittest.TestCase):
    def get_mock_server_handler(self) -> tuple[Mock, dict[str, Mock]]:
        """Return a mock server handler."""
        mock_connect = Mock()
        mock_get_console = Mock()
        mock_server_handler = Mock()

        mock_server_handler.connect = mock_connect
        mock_server_handler.get_console = mock_get_console

        mock_connect.return_value = None
        mock_get_console.return_value = Mock()

        return mock_server_handler, {
            "connect": mock_connect,
            "get_console": mock_get_console,
        }

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_help_includes_connect_command(self, mock_project_dir: Mock, mock_server_handler_class: Mock) -> None:
        runner = CliRunner()
        result = runner.invoke(servers_app, ["--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertTrue("connect" in result.stdout, "connect command should appear in help")

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_instantiates_handler_and_calls_connect(
        self, mock_project_dir: Mock, mock_server_handler_class: Mock
    ) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        mock_console = Mock()
        mock_handler_fns["get_console"].return_value = mock_console

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["connect", "-s", "jupyter"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_server_handler_class.assert_called_once()
        mock_handler_fns["connect"].assert_called_once_with(service="jupyter")
        mock_handler_fns["get_console"].assert_called_once()

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_defaults_to_default_service(self, mock_project_dir: Mock, mock_server_handler_class: Mock) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["connect"])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_handler_fns["connect"].assert_called_once_with(service="default")

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_prints_error_when_invalid_service(self, mock_project_dir: Mock, mock_server_handler_class: Mock) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_project_dir.return_value.__enter__.return_value = None

        mock_handler_fns["connect"].side_effect = InvalidServiceError(
            "Invalid service, use one of ['jupyter', 'traefik']"
        )

        mock_console = Mock()
        mock_handler_fns["get_console"].return_value = mock_console

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["connect", "-s", "invalid_service"])

        # Assert
        self.assertEqual(result.exit_code, 1)
        mock_console.print.assert_called_once()
        mock_call = mock_console.print.mock_calls[0]
        self.assertTrue("Invalid service" in mock_call[1][0])
        self.assertTrue("red" in mock_call[2]["style"])

    @patch("jupyter_deploy.handlers.resource.server_handler.ServerHandler")
    @patch("jupyter_deploy.cmd_utils.project_dir")
    def test_raises_when_handler_connect_raises(self, mock_project_dir: Mock, mock_server_handler_class: Mock) -> None:
        # Setup
        mock_server_handler, mock_handler_fns = self.get_mock_server_handler()
        mock_server_handler_class.return_value = mock_server_handler
        mock_handler_fns["connect"].side_effect = Exception("Test error")
        mock_project_dir.return_value.__enter__.return_value = None

        # Execute
        runner = CliRunner()
        result = runner.invoke(servers_app, ["connect", "-s", "jupyter"])

        # Assert
        self.assertNotEqual(result.exit_code, 0)
