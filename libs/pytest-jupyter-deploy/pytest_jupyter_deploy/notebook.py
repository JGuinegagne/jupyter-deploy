"""Jupyter notebook utilities for E2E testing."""

import base64
import json
import logging
import time
from pathlib import Path

from playwright.sync_api import Page

from pytest_jupyter_deploy.cli import JDCliError
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


def _extract_cell_outputs(page: Page, execution_idx: int = 0) -> list[dict[str, str]]:
    """Extract cell execution information from the current notebook.

    Note: this method swallows exceptions to ensure we gather as much cell
    information as possible.

    Args:
        page: Playwright Page instance
        execution_idx: Poll iteration number for logging (0 = first check)

    Returns:
        List of dictionaries containing cell information with keys:
        - cell_number: Execution count (e.g., "[1]", "[2]") or "[-1]" when not-executed
        - has_error: Boolean indicating if cell has error output
        - error_output: Error traceback text if present, empty string otherwise
    """
    cells_info: list[dict[str, str]] = []

    # Find all code cells in the notebook
    code_cells = page.locator(".jp-CodeCell").all()
    logger.info(f"[Poll {execution_idx}] Found {len(code_cells)} code cells")

    for i, cell in enumerate(code_cells):
        cell_info: dict[str, str] = {
            "cell_index": str(i),
            "cell_number": "[-1]",
            "has_error": "False",
            "error_output": "",
        }

        # Get execution count from input prompt
        try:
            input_prompt = cell.locator(".jp-InputArea-prompt").first
            prompt_text = input_prompt.inner_text(timeout=1000)
            cell_info["cell_number"] = prompt_text.strip()
            logger.info(f"[Poll {execution_idx}] Cell {i} execution count: {cell_info['cell_number']}")
        except Exception as e:
            logger.warning(f"[Poll {execution_idx}] Could not extract cell number for cell {i}: {e}")
            cell_info["cell_number"] = "[-1]"
            # do NOT raise here, keep gathering cell information

        # Check for error outputs
        try:
            # JupyterLab displays errors in output area with specific classes
            output_area = cell.locator(".jp-OutputArea-output")
            if output_area.count() > 0:
                # Get all output text and check if it contains error indicators
                all_output_text = output_area.first.inner_text(timeout=1000)
                logger.info(f"[Poll {execution_idx}] Cell {i} output text (first 200 chars): {all_output_text[:200]}")

                # Check for common error patterns
                if any(pattern in all_output_text for pattern in ["Traceback", "Error:", "Exception:", "error:"]):
                    cell_info["has_error"] = "True"
                    cell_info["error_output"] = all_output_text[:500]  # Limit to first 500 chars
                    logger.warning(f"[Poll {execution_idx}] Cell {i} has error: {cell_info['error_output'][:100]}")
        except Exception as e:
            logger.error(f"[Poll {execution_idx}] Could not extract error output for cell {i}: {e}")
            cell_info["has_error"] = "Possibly"
            cell_info["error_output"] = "Failed to retrieve cell output"
            # do NOT raise here, keep gathering cell information

        cells_info.append(cell_info)

    return cells_info


def run_notebook_in_jupyterlab(
    page: Page, notebook_path: str, timeout_ms: int = 120000, poll_interval_ms: int = 2000
) -> None:
    """Run a notebook in JupyterLab and wait for completion.

    NOTE: To avoid "Document session error" dialogs, restart the Jupyter server
    and re-authenticate BEFORE calling this function.

    Args:
        page: Playwright Page instance with JupyterLab already loaded
        notebook_path: Path to the notebook relative to /home/jovyan (e.g., "work/test.ipynb")
        timeout_ms: Maximum time to wait for notebook execution in milliseconds (default: 120000)
        poll_interval_ms: Interval between cell execution checks in milliseconds (default: 2000)

    Raises:
        RuntimeError: If notebook execution fails or times out, includes cell execution details
    """
    # Refresh page to establish fresh kernel connections (especially important after server restarts)
    page.reload()
    page.wait_for_load_state("networkidle")

    # Check for server connection errors after page load
    _reload_on_server_connection_error(page)

    # Close all open notebook tabs to avoid strict mode violations when multiple notebooks are open
    # This can happen if previous tests left tabs open due to errors
    # Strategy: Use Command Palette to execute "application:close-all"
    try:
        logger.info("Attempting to close all other tabs...")

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

        logger.info("Successfully executed close-all command...")
    except Exception as e:
        # If closing tabs fails, continue anyway
        logger.warning(f"Could not close all tabs: {e}")

    # Open the notebook directly via URL to bypass file browser caching issues
    # JupyterLab uses URLs like /lab/tree/path/to/notebook.ipynb
    current_url = page.url
    base_url = current_url.split("/lab")[0] if "/lab" in current_url else current_url.rstrip("/")
    notebook_url = f"{base_url}/lab/tree/{notebook_path}"

    logger.info(f"Opening notebook at: {notebook_url}...")
    page.goto(notebook_url)
    time.sleep(2)  # Give JupyterLab time to load the notebook

    # Wait for the notebook to load - check for the notebook toolbar
    # Use .first to handle cases where multiple notebooks may be open
    logger.info("Looking for notebook toolbar...")
    notebook_toolbar = page.locator(".jp-NotebookPanel-toolbar").first
    notebook_toolbar.wait_for(state="visible", timeout=10000)

    # Wait for the kernel to be ready before executing cells
    # The kernel status is shown in the status bar (e.g., "Python 3 (ipykernel) | Idle")
    logger.info("Waiting for kernel to be ready...")
    try:
        # Target the visible status bar element specifically to avoid strict mode violation
        kernel_status_idle = page.locator(".jp-StatusBar-TextItem").filter(has_text="Idle")
        kernel_status_idle.wait_for(state="visible", timeout=30000)
        logger.info("Kernel is idle and ready")
    except Exception as e:
        logger.warning(f"Could not detect idle kernel status, proceeding anyway: {e}")

    # Click "Run" option in JupyterLab top menu and then "Run All Cells" option
    logger.info("Clicking 'Run' option in JupyterLab top menu...")
    run_menu = page.get_by_role("menuitem", name="Run")
    run_menu.click()

    logger.info("Clicking 'Run All Cells' option...")
    run_all_item = page.get_by_text("Run All Cells", exact=True)
    run_all_item.click()
    logger.info("Clicked 'Run All Cells'")

    # Wait for execution to complete by polling cell execution counts
    # This is more reliable than watching kernel status indicators, which can be affected by WebSocket issues
    start_time = time.time()
    max_wait = timeout_ms / 1000  # Convert to seconds
    poll_interval = poll_interval_ms / 1000  # Convert to seconds
    connection_error_recovered = False  # Track if we've already recovered from connection error once
    poll_iteration = 0  # Track poll iteration for logging

    logger.info(f"Waiting for notebook execution to complete (timeout: {timeout_ms}ms)...")
    while time.time() - start_time < max_wait:
        poll_iteration += 1
        logger.info(f"[Poll {poll_iteration}] Checking cell execution states...")

        # Check for server connection errors
        if _reload_on_server_connection_error(page):
            if connection_error_recovered:
                # Already tried to recover once, fail now
                raise RuntimeError(
                    f"Server connection error detected while executing {notebook_path}. "
                    "The Jupyter server may not be fully ready or may have crashed during notebook execution."
                )
            connection_error_recovered = True
            # Continue checking after refresh
            time.sleep(0.5)
            continue

        # Extract current cell execution states
        cells_info = _extract_cell_outputs(page, execution_idx=poll_iteration)

        if not cells_info:
            # No cells found yet, notebook may still be loading
            logger.warning(f"[Poll {poll_iteration}] No cells found, waiting for notebook to load...")
            time.sleep(poll_interval)
            continue

        # Count how many cells have executed
        executed_count = len([cell for cell in cells_info if _is_cell_executed(cell["cell_number"])])
        total_count = len(cells_info)

        logger.info(f"[Poll {poll_iteration}] Execution progress: {executed_count}/{total_count} cells completed")

        # Check if all cells have executed
        if executed_count == total_count:
            # All cells executed - verify no errors
            _verify_executed_and_no_cell_error(cells_info, notebook_path)
            logger.info(f"Notebook execution completed successfully: all {total_count} cells executed without errors")
            return

        # Not done yet, wait and check again
        time.sleep(poll_interval)

    # Timeout - perform final check to see if cells actually completed
    poll_iteration += 1
    logger.warning(f"[Poll {poll_iteration}] Timeout reached, performing final cell extraction...")
    cells_info = _extract_cell_outputs(page, execution_idx=poll_iteration)
    executed_count = len([cell for cell in cells_info if _is_cell_executed(cell["cell_number"])])
    total_count = len(cells_info)

    # Check if all cells actually executed (might have finished just after timeout)
    if executed_count == total_count and total_count > 0:
        # All cells executed - verify no errors
        _verify_executed_and_no_cell_error(cells_info, notebook_path)
        logger.info(
            f"Notebook execution completed successfully (caught on final check after timeout): "
            f"all {total_count} cells executed without errors"
        )
        return

    # Cells did not complete execution
    logger.error(f"Notebook execution timed out: {executed_count}/{total_count} cells executed")
    raise RuntimeError(
        f"Notebook execution timed out after {timeout_ms}ms. "
        f"Only {executed_count} out of {total_count} cells completed execution."
    )


def _reload_on_server_connection_error(page: Page, pop_up_visible_timeout_ms: int = 500) -> bool:
    """Check for server connection error and reload page if detected.

    Args:
        page: Playwright Page instance
        pop_up_visible_timeout_ms: Timeout in ms to check if connection error popup is visible

    Returns:
        True if connection error was detected and page was reloaded, False otherwise
    """
    connection_error = page.get_by_text("Server Connection Error")
    if connection_error.is_visible(timeout=pop_up_visible_timeout_ms):
        logger.warning("Connection error detected, waiting 2s and refreshing page...")
        time.sleep(2)
        page.reload()
        logger.info("Page reloaded after connection error")
        return True
    return False


def _is_cell_executed(cell_number: str) -> bool:
    """Return True if a cell has been executed based on its execution count.

    Args:
        cell_number: The execution count text from the cell prompt (e.g., "[1]", "[ ]:", "[*]", "[-1]")

    Returns:
        True if the cell has a numeric execution count (indicating it executed successfully),
        False if the cell is unexecuted or still executing
    """
    # Cell is executed if it contains a digit (e.g., "[1]", "[2]", etc.)
    # Not executed if it's "[ ]:", "[ ]", "[]", "[-1]", "[*]", or any variation without digits
    return any(char.isdigit() for char in cell_number) and "*" not in cell_number and "-" not in cell_number


def _verify_executed_and_no_cell_error(cells_info: list[dict[str, str]], notebook_path: str) -> None:
    """Check if any cells have errors and raise RuntimeError if found.

    Args:
        cells_info: List of cell information dictionaries
        notebook_path: Path to the notebook for error message

    Raises:
        RuntimeError: If any cell has an error or if no cells executed
    """
    # Verify we found at least one cell
    if not cells_info:
        raise RuntimeError(
            f"Notebook {notebook_path} validation failed: no cells found. The notebook may not have loaded properly."
        )

    # Verify all cells have execution counts (actually executed)
    unexecuted_cells = [cell for cell in cells_info if not _is_cell_executed(cell["cell_number"])]
    if unexecuted_cells:
        unexecuted_indices = [cell["cell_index"] for cell in unexecuted_cells]
        unexecuted_numbers = [cell["cell_number"] for cell in unexecuted_cells]
        raise RuntimeError(
            f"Notebook {notebook_path} validation failed.\n"
            f"{len(unexecuted_cells)} cell(s) did not execute completely.\n"
            f"Cell indices: {unexecuted_indices}\n"
            f"Cell execution states: {unexecuted_numbers}\n"
            "The notebook may have failed to execute or is still executing."
        )

    errors_found = [cell for cell in cells_info if cell["has_error"] in ["True", "Possibly"]]
    if errors_found:
        raise RuntimeError(f"Notebook {notebook_path} execution failed with errors.")


def wait_for_kernel_ready(
    deployment: EndToEndDeployment,
    timeout_seconds: int = 60,
    jupyter_port: int = 8888,
    interval_seconds: int = 5,
    settle_delay_seconds: int = 2,
) -> None:
    """Wait for Jupyter kernel manager to be ready after server restart.

    This function polls the Jupyter kernels API endpoint until it responds successfully,
    indicating the kernel manager is ready to handle notebook execution requests.

    Args:
        deployment: The deployment instance
        timeout_seconds: Maximum time to wait for kernel readiness (default: 60)
        jupyter_port: Port where Jupyter server is running (default: 8888)
        interval_seconds: Delay between polling attempts (default: 5)
        settle_delay_seconds: Additional delay after API responds to allow full initialization (default: 2)

    Raises:
        TimeoutError: If kernel manager is not ready within timeout_seconds
    """
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        try:
            result = deployment.cli.run_command(
                ["jupyter-deploy", "server", "exec", "--", "curl", "-s", f"http://localhost:{jupyter_port}/api/kernels"]
            )
            if result.stdout.strip() != "":
                # Kernel API is responding - wait a bit more for full initialization
                logger.info(f"Kernel manager ready after {time.time() - start_time:.1f}s")
                time.sleep(settle_delay_seconds)
                return
        except JDCliError:
            # Command failed, kernel not ready yet
            pass

        time.sleep(interval_seconds)

    raise TimeoutError(
        f"Kernel manager not ready after {timeout_seconds}s. "
        "The Jupyter server may not have fully initialized or the kernel manager failed to start."
    )


def delete_notebook(deployment: EndToEndDeployment, target_path: str, home_path: str = "/home/jovyan") -> None:
    """Delete a notebook from the Jupyter server.

    Args:
        deployment: The deployment instance
        target_path: Path to the notebook on the server (relative to home dir, e.g., "work/test.ipynb")
        home_path: Path to the home dir in the jupyterlab container (default: /home/jovyan)
    """
    full_cmd = f"rm -f {home_path}/{target_path}"
    deployment.cli.run_command(["jupyter-deploy", "server", "exec", "--", full_cmd])
