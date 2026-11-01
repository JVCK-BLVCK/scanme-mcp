# ScanMe MCP

ScanMe MCP is a [Model Context Protocol](https://modelcontextprotocol.io/) server for running and reviewing Nuclei vulnerability scans. It provides six tools over the standard input/output transport and stores scan history in local JSONL files.

## Features

- Start scans asynchronously and check their status and findings.
- Review recent scan history for a target.
- Enrich CVE findings with CVSS and EPSS data from NVD and FIRST.org.
- Generate remediation reports and compare completed scans.
- Reject targets that use unsupported URL schemes or resolve to private or reserved addresses.

Only scan systems you own or are explicitly authorized to assess.

## Requirements

- Python 3.10 or newer
- [Nuclei](https://github.com/projectdiscovery/nuclei) installed and available on `PATH`

## Install

From the repository directory, create and activate a virtual environment, then install the package:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

Confirm Nuclei is available with `nuclei -version`. Scan records are written to `data/scans/` by default. Set `SCANME_MCP_SCAN_DIR` to use another directory. `NVD_API_KEY` is optional and raises the NVD API rate limit for finding enrichment. Example environment variables are listed in `.env.example`; configure them in the MCP client's environment because the server does not load `.env` files itself.

## Run

Start the server directly:

```sh
python -m scanme_mcp.server
```

Or, after installation:

```sh
scanme-mcp
```

The server communicates over standard input/output. Logs go to standard error so they do not interfere with the MCP connection.

## Configure an MCP client

Add a server entry to the client's MCP configuration. Use the absolute path to the Python executable in this repository's virtual environment:

```json
{
  "mcpServers": {
    "scanme": {
      "command": "C:\\path\\to\\scanme-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "scanme_mcp.server"],
      "env": {
        "SCANME_MCP_SCAN_DIR": "C:\\path\\to\\scanme-mcp\\data\\scans",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

On macOS or Linux, use the virtual environment's `bin/python` executable and an absolute scan-data path for that platform.

## Tools

| Tool | Purpose |
| --- | --- |
| `scan_target` | Start a Nuclei scan and return its scan ID. |
| `get_scan_status` | Read a scan's status and findings. |
| `get_scan_history` | List recent scans for a target. |
| `analyse_findings` | Enrich CVE findings with NVD and EPSS data. |
| `generate_report` | Create a structured report with severity and remediation priorities. |
| `compare_scans` | Compare completed scans of the same target. |

Typical workflow: call `scan_target`, poll `get_scan_status`, then use `analyse_findings`, `generate_report`, or `compare_scans` as needed.

## Current limitations

- The `timeout_seconds` argument is not yet passed to Nuclei; the scanner retains a fixed 600-second deadline.
- The shutdown helper is not registered with the MCP server lifecycle, so an interrupted scan may remain marked `in_progress`.
- JSONL storage coordinates threads within one server process; multiple processes should not share the same scan directory.
- Standard input/output is the only supported transport. Remote HTTP deployment and authentication are not included.
- Concurrent scan limits are not currently enforced.
