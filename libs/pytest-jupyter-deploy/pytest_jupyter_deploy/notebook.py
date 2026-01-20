"""Jupyter notebook utilities for E2E testing."""

import base64
import json
import logging
import time
from pathlib import Path

from playwright.sync_api import Page

from pytest_jupyter_deploy.deployment import EndToEndDeployment

logger = logging.getLogger(__name__)


def upload_notebook(deployment: EndToEndDeployment, src_path: str | Path, target_path: str) -> None:
    """Upload a notebook to the Jupyter server.

    Args:
        deployment: The deployment instance
        src_path: Path to the local notebook file, relative to the jupyterlab home
        target_path: Target path on the server (relative to /home/jovyan, e.g., "work/test.ipynb")

    Raises:
        FileNotFoundError: If the source notebook doesn't exist
        RuntimeError: If the upload fails
    """
    src_path = Path(src_path)
    if not src_path.exists() or not src_path.is_file():
        raise FileNotFoundError(f"Notebook not found: {src_path}")

    # Read and parse the notebook JSON
    with open(src_path) as f:
        notebook_content = json.load(f)

    # Convert to JSON string and base64 encode for safe transmission
    notebook_json = json.dumps(notebook_content)
    encoded_notebook = base64.b64encode(notebook_json.encode()).decode()

    # Upload notebook using jd server exec with python to decode and write
    # Use python to avoid shell escaping issues with complex JSON content
    python_cmd = (
        f'python3 -c "import base64, os; '
        f"os.makedirs(os.path.dirname('/home/jovyan/{target_path}'), exist_ok=True); "
        f"data=base64.b64decode('{encoded_notebook}'); "
        f"open('/home/jovyan/{target_path}', 'wb').write(data)\""
    )

    deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", python_cmd])


def _extract_cell_outputs(page: Page) -> list[dict[str, str]]:
    """Extract cell execution information from the current notebook.

    Args:
        page: Playwright Page instance with an open notebook

    Returns:
        List of dictionaries containing cell information with keys:
        - cell_number: Execution count (e.g., "[1]", "[2]")
        - has_error: Boolean indicating if cell has error output
        - error_output: Error traceback text if present, empty string otherwise
    """
    cells_info: list[dict[str, str]] = []

    # Find all code cells in the notebook
    code_cells = page.locator(".jp-CodeCell").all()

    for i, cell in enumerate(code_cells):
        cell_info: dict[str, str] = {
            "cell_index": str(i),
            "cell_number": "",
            "has_error": "False",
            "error_output": "",
        }

        # Get execution count from input prompt
        try:
            input_prompt = cell.locator(".jp-InputArea-prompt").first
            prompt_text = input_prompt.inner_text(timeout=1000)
            cell_info["cell_number"] = prompt_text.strip()
        except Exception as e:
            logger.debug(f"Could not extract cell number for cell {i}: {e}")
            cell_info["cell_number"] = "[not executed]"

        # Check for error outputs
        try:
            # JupyterLab displays errors in output area with specific classes
            output_area = cell.locator(".jp-OutputArea-output")
            if output_area.count() > 0:
                # Get all output text and check if it contains error indicators
                all_output_text = output_area.first.inner_text(timeout=1000)
                logger.debug(f"Cell {i} output text (first 200 chars): {all_output_text[:200]}")

                # Check for common error patterns
                if any(pattern in all_output_text for pattern in ["Traceback", "Error:", "Exception:", "error:"]):
                    cell_info["has_error"] = "True"
                    cell_info["error_output"] = all_output_text[:500]  # Limit to first 500 chars
                    logger.debug(f"Cell {i} has error: {cell_info['error_output'][:100]}")
        except Exception as e:
            logger.debug(f"Could not extract error output for cell {i}: {e}")

        cells_info.append(cell_info)

    return cells_info


def run_notebook_in_jupyterlab(page: Page, notebook_path: str, timeout_ms: int = 120000) -> None:
    """Run a notebook in JupyterLab and wait for completion.

    NOTE: To avoid "Document session error" dialogs, restart the Jupyter server
    and re-authenticate BEFORE calling this function.

    Args:
        page: Playwright Page instance with JupyterLab already loaded
        notebook_path: Path to the notebook relative to /home/jovyan (e.g., "work/test.ipynb")
        timeout: Maximum time to wait for notebook execution in milliseconds (default: 120000)

    Raises:
        RuntimeError: If notebook execution fails or times out, includes cell execution details
    """
    # Refresh page to establish fresh kernel connections (especially important after server restarts)
    page.reload()
    page.wait_for_load_state("networkidle")

    # Close all open notebook tabs to avoid strict mode violations when multiple notebooks are open
    # This can happen if previous tests left tabs open due to errors
    # Strategy: Use Command Palette to execute "application:close-all"
    try:
        # Close any open dialogs first
        page.keyboard.press("Escape")
        time.sleep(0.2)

        # Open Command Palette with Ctrl+Shift+C
        page.keyboard.press("Control+Shift+c")
        time.sleep(0.5)

        # Type "close all tabs" to filter commands
        page.keyboard.type("close all tabs")
        time.sleep(0.3)

        # Press Enter to execute the "application:close-all" command
        page.keyboard.press("Enter")
        time.sleep(0.5)
    except Exception as e:
        # If closing tabs fails, continue anyway
        logger.warning(f"Could not close all tabs: {e}")

    # Open the notebook directly via URL to bypass file browser caching issues
    # JupyterLab uses URLs like /lab/tree/path/to/notebook.ipynb
    current_url = page.url
    base_url = current_url.split("/lab")[0] if "/lab" in current_url else current_url.rstrip("/")
    notebook_url = f"{base_url}/lab/tree/{notebook_path}"

    logger.info(f"Opening notebook at: {notebook_url}")
    page.goto(notebook_url)
    time.sleep(2)  # Give JupyterLab time to load the notebook

    # Wait for the notebook to load - check for the notebook toolbar
    # Use .first to handle cases where multiple notebooks may be open
    notebook_toolbar = page.locator(".jp-NotebookPanel-toolbar").first
    notebook_toolbar.wait_for(state="visible", timeout=10000)

    # Wait a bit for the notebook to fully initialize
    time.sleep(1)

    # Click "Run" menu
    run_menu = page.get_by_role("menuitem", name="Run")
    run_menu.click()

    # Click "Run All Cells" from the dropdown
    run_all_item = page.get_by_text("Run All Cells", exact=True)
    run_all_item.click()

    # Wait for execution to complete
    # Look for the kernel idle indicator or execution count updates
    # JupyterLab shows a filled circle when kernel is busy, empty when idle
    # We'll wait for the kernel status to become idle

    # Strategy: Wait for the busy indicator to appear and then disappear
    start_time = time.time()
    max_wait = timeout_ms / 1000  # Convert to seconds
    connection_error_recovered = False  # Track if we've already recovered from connection error once

    # First, wait for execution to start (busy indicator appears)
    # The kernel status is in the status bar
    busy_started = False
    while time.time() - start_time < max_wait:
        # Check for connection error dialog first
        connection_error = page.get_by_text("Server Connection Error")
        if connection_error.is_visible(timeout=500):
            if connection_error_recovered:
                # Already tried to recover once, fail now
                raise RuntimeError(
                    f"Server connection error detected while executing {notebook_path}. "
                    "The Jupyter server may not be fully ready or may have crashed during notebook execution."
                )
            # First connection error, attempt recovery
            logger.warning("Connection error detected, waiting 2s and refreshing page...")
            time.sleep(2)
            page.reload()
            page.wait_for_load_state("networkidle")
            connection_error_recovered = True
            # Continue checking after refresh
            time.sleep(0.5)
            continue

        # Check if kernel is busy by looking for the filled circle icon
        # JupyterLab uses jp-FilledCircleIcon for busy state
        busy_indicator = page.locator(".jp-Kernel-statusCircle.jp-FilledCircleIcon")
        try:
            if busy_indicator.is_visible(timeout=1000):
                busy_started = True
                break
        except Exception as e:
            logger.debug(f"Could not check busy indicator visibility: {e}")
        time.sleep(0.5)

    if not busy_started:
        # Kernel might have executed too fast, or execution didn't start
        # Check if there are any execution counts to verify it ran
        execution_count = page.locator(".jp-InputArea-prompt:has-text('[')").first
        try:
            execution_count.wait_for(state="visible", timeout=5000)
            # If we see execution counts, check for errors before returning
            cells_info = _extract_cell_outputs(page)
            _check_for_errors(cells_info, notebook_path)
            return
        except Exception:
            raise RuntimeError("Notebook execution did not start") from None

    # Now wait for kernel to become idle (busy indicator disappears)
    while time.time() - start_time < max_wait:
        # Check for connection error dialog
        connection_error = page.get_by_text("Server Connection Error")
        if connection_error.is_visible(timeout=500):
            if connection_error_recovered:
                # Already tried to recover once, fail now
                raise RuntimeError(
                    f"Server connection error detected while executing {notebook_path}. "
                    "The Jupyter server may not be fully ready or may have crashed during notebook execution."
                )
            # First connection error, attempt recovery
            logger.warning("Connection error detected, waiting 2s and refreshing page...")
            time.sleep(2)
            page.reload()
            page.wait_for_load_state("networkidle")
            connection_error_recovered = True
            # Continue checking after refresh
            time.sleep(0.5)
            continue

        busy_indicator = page.locator(".jp-Kernel-statusCircle.jp-FilledCircleIcon")
        try:
            # Check if busy indicator is no longer visible
            if not busy_indicator.is_visible(timeout=1000):
                # Kernel is idle, execution complete
                # Wait a bit more for UI to stabilize
                time.sleep(1)
                # Check for errors in cell outputs
                cells_info = _extract_cell_outputs(page)
                _check_for_errors(cells_info, notebook_path)
                return
        except Exception as e:
            # Busy indicator not visible, execution likely complete
            logger.debug(f"Exception while checking busy indicator: {e}")
            time.sleep(1)
            # Check for errors before returning
            cells_info = _extract_cell_outputs(page)
            _check_for_errors(cells_info, notebook_path)
            return

        time.sleep(0.5)

    # Timeout - extract cell info for diagnostics
    cells_info = _extract_cell_outputs(page)
    error_msg = f"Notebook execution timed out after {timeout_ms}ms\n"
    error_msg += _format_cell_diagnostics(cells_info)
    raise RuntimeError(error_msg)


def _check_for_errors(cells_info: list[dict[str, str]], notebook_path: str) -> None:
    """Check if any cells have errors and raise RuntimeError if found.

    Args:
        cells_info: List of cell information dictionaries
        notebook_path: Path to the notebook for error message

    Raises:
        RuntimeError: If any cell has an error
    """
    # Log all cell info for debugging
    logger.info(f"Checking {len(cells_info)} cells for errors in {notebook_path}")
    for cell in cells_info:
        error_preview = cell["error_output"][:100] if cell["error_output"] else "none"
        logger.info(
            f"  Cell {cell['cell_number']} (index {cell['cell_index']}): "
            f"has_error={cell['has_error']}, error_output={error_preview}"
        )

    errors_found = [cell for cell in cells_info if cell["has_error"] == "True"]
    if errors_found:
        error_msg = f"Notebook {notebook_path} execution failed with errors:\n"
        error_msg += _format_cell_diagnostics(cells_info)
        raise RuntimeError(error_msg)


def _format_cell_diagnostics(cells_info: list[dict[str, str]]) -> str:
    """Return formatted string with cell execution details.

    Args:
        cells_info: List of cell information dictionaries
    """
    if not cells_info:
        return "No cell execution information available"

    lines: list[str] = []
    for cell in cells_info:
        status = "ERROR" if cell["has_error"] == "True" else "OK"
        lines.append(f"  Cell {cell['cell_number']} (index {cell['cell_index']}): {status}")
        if cell["has_error"] == "True" and cell["error_output"]:
            # Indent error output
            error_lines = cell["error_output"].split("\n")
            for line in error_lines[:10]:  # Limit to first 10 lines
                lines.append(f"    {line}")
            if len(error_lines) > 10:
                lines.append("    ... (error output truncated)")

    return "\n".join(lines)


def delete_notebook(deployment: EndToEndDeployment, target_path: str, home_path: str = "/home/jovyan") -> None:
    """Delete a notebook from the Jupyter server.

    Args:
        deployment: The deployment instance
        target_path: Path to the notebook on the server (relative to home dir, e.g., "work/test.ipynb")
        home_path: Path to the home dir in the jupyterlab container (default: /home/jovyan)
    """
    full_cmd = f"rm -f {home_path}/{target_path}"
    deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", full_cmd])
