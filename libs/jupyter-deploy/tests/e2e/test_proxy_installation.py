"""AWS+proxy install track tests — validate the CLI works with the [aws,proxy] extra.

These tests run in the ``aws-proxy`` install track where ``jupyter-deploy[aws,proxy]`` is
installed (the client proxy resolves from prod PyPI). They guard the install contract that
``jd open`` / ``jd proxy`` rely on: the separate client-proxy package is present, and its
console script resolves the way :func:`resolve_console_script` looks for it (next to the
interpreter, then PATH). The positive counterpart to ``test_bare_installation`` — which
asserts the proxy is ABSENT without the extra.
"""

import shutil
import subprocess
import unittest
from pathlib import Path


class TestProxyInstallation(unittest.TestCase):
    def test_client_proxy_package_installed(self) -> None:
        # The [proxy] extra ships the separate client-proxy package. `jd` never imports it (it
        # shells out to the console script), but the package must be present for that script to exist.
        import jupyter_deploy_client_proxy  # noqa: F401

    def test_proxy_console_script_on_path(self) -> None:
        self.assertIsNotNone(shutil.which("jupyter-deploy-client-proxy"))

    def test_resolve_console_script_finds_proxy(self) -> None:
        # Mirror the exact resolution `jd` uses to launch the proxy: next to sys.executable, then
        # PATH. If it can't find the script, `jd open` fails at proxy launch — so assert we get a
        # real absolute path, not the bare-name last-resort fallback.
        from jupyter_deploy.proxy.proxy_manager import resolve_console_script

        resolved = resolve_console_script("jupyter-deploy-client-proxy")
        self.assertTrue(Path(resolved).is_absolute())
        self.assertTrue(Path(resolved).exists())

    def test_proxy_console_script_runs(self) -> None:
        # The entry point actually imports and runs — catches a broken module path in the
        # client-proxy [project.scripts] that a mere PATH check would miss.
        result = subprocess.run(
            ["jupyter-deploy-client-proxy", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
