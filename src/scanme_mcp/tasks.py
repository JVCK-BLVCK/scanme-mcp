"""Background scan task tracking for the ScanMe MCP server.

Strong references keep tasks alive until completion, and callbacks log
unhandled errors. The shutdown helper can mark interrupted scans as failed
when connected to the MCP server's shutdown lifecycle.
"""

import asyncio
import logging
from scanme_mcp.storage import save_scan, load_scan

logger = logging.getLogger(__name__)

# Maps each running Task to the scan_id it's executing — so on shutdown
# we know exactly which scans to mark failed, not just that "something"
# was running.
_background_tasks: dict[asyncio.Task, str | None] = {}


def spawn_background_task(coro, scan_id: str | None = None) -> asyncio.Task:
    """
    Schedule a coroutine to run without blocking the caller.

    Schedule a scan coroutine while retaining it until it finishes.
 
    Args:
        coro:    The coroutine to run (e.g. asyncio.to_thread(run_nuclei, ...))
        scan_id: Optional scan_id to register for shutdown tracking.
                Pass None for background work not associated with a scan.
 
    Returns:
        The created asyncio.Task.
    
    """
    task = asyncio.create_task(coro)
    _background_tasks[task] = scan_id

    def _on_done(completed: asyncio.Task):
        _background_tasks.pop(completed, None)

        if completed.cancelled():
            return
        
        exc = completed.exception()
        if exc is not None:
            logger.error({
                "event": "background_task_failed",
                "scan_id" : scan_id,
                "error": str(exc),
                "type" : type(exc).__name__

            })

    task.add_done_callback(_on_done)
    return task


async def shutdown_pending_scans(grace_period: float = 5) -> list[str]:
    """
    Call this from the MCP server's shutdown lifecycle.
 
    Gives running scans a brief window to complete naturally (some may be
    seconds from finishing). After the grace period, cancels remaining tasks
    and marks their scans as failed in storage so polling clients receive
    a clear, honest answer rather than an eternal "in_progress" status.
 
    Args:
        grace_period: Seconds to wait before force-cancelling tasks.
                      Docker's default SIGTERM grace period is 10 seconds.
                      Scans take 1-10 minutes, so most won't finish here —
                      the value of this function is the explicit failure
                      marking, not waiting for completion.
 
    Returns:
        List of scan_ids that were interrupted.
    """
    # Local import avoids circular dependency:
    # tasks.py -> storage.py is fine
    # storage.py -> tasks.py would create a cycle

    if not _background_tasks:
        return []

    tasks = list(_background_tasks.keys())

    _, pending = await asyncio.wait(tasks, timeout=grace_period)

    interrupted: list[str] = []

    for task in pending:
        scan_id = _background_tasks.get(task)
        task.cancel()

        if scan_id:
            try:
                data = await load_scan(scan_id)
                if data and data["status"] == "in_progress":
                    await save_scan(scan_id, {
                        **data,
                        "status": "failed",
                        "error": "Service shut down before scan completed"
                    })
                interrupted.append(scan_id)
            except (IOError, Exception) as e:
                # Best-effort -log and continue even if storage fails
                logger.error({
                    "event": "shutdown_mark_failed_error",
                    "scan_id" : scan_id,
                    "error" : str(e)
                })

    return interrupted # type: ignore
