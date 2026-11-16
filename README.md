# cert-expiry-mcp

![Tests](https://github.com/sanju-av/cert-expiry-mcp/actions/workflows/tests.yml/badge.svg)

A small [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server written in Python. It exposes one tool, `check_certificate_expiry(domain)`, which connects to a domain on port 443, reads its TLS certificate, and reports when it expires. The certificate check uses only the Python standard library (`ssl` and `socket`).

## What the tool returns

```python
{
    "domain": "example.com",
    "expires_on": "2026-12-25T22:56:35+00:00",  # ISO 8601, UTC
    "days_remaining": 39,
    "warning": False,  # True when fewer than 30 days remain
}
```

If something goes wrong, the tool reports a clear error message instead of crashing:

- the domain cannot be resolved
- the connection times out (5 seconds)
- the certificate fails verification (for example, it has expired)
- the server returns no certificate

## Project layout

| File                           | What it does                                                                                                                                                     |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cert_checker.py`              | The certificate logic. `_fetch_certificate` does the network call; `get_certificate_expiry` parses the date, counts days and sets the warning flag. No MCP code. |
| `server.py`                    | The MCP server. Registers `check_certificate_expiry` as a tool and turns checker errors into tool errors.                                                        |
| `tests/test_cert_checker.py`   | Unit tests (pytest). The network is mocked, so no internet is needed.                                                                                            |
| `pytest.ini`                   | Tells pytest where the tests are and makes the project root importable.                                                                                          |
| `requirements.txt`             | Runtime dependency: the `mcp` SDK (2.x).                                                                                                                         |
| `requirements-dev.txt`         | Runtime dependencies plus `pytest`.                                                                                                                              |
| `Dockerfile` / `.dockerignore` | Builds a container image that runs the server.                                                                                                                   |
| `.vscode/mcp.json`             | Registers the server with VS Code so GitHub Copilot can use it.                                                                                                  |
| `.github/workflows/tests.yml`  | GitHub Actions workflow that installs dependencies and runs the tests on every push.                                                                             |

## Setup

Requires Python 3.10 or newer.

```bash
git clone https://github.com/sanju-av/cert-expiry-mcp.git
cd cert-expiry-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Try the checker on its own

```bash
python cert_checker.py example.com
```

## Run the server

```bash
python server.py
```

The server speaks MCP over standard input and output (stdio), so it prints nothing and waits for a client. Stop it with `Ctrl+C`. Because stdout carries the protocol messages, the server code must never `print()` to stdout.

## Connect it to VS Code (GitHub Copilot)

1. Complete the setup above so `.venv` exists in the project folder.
2. Open the project folder in VS Code. The repository already contains `.vscode/mcp.json`:

   ```json
   {
     "servers": {
       "cert-expiry": {
         "type": "stdio",
         "command": "${workspaceFolder}/.venv/bin/python",
         "args": ["${workspaceFolder}/server.py"]
       }
     }
   }
   ```

   This path assumes macOS or Linux. On Windows the interpreter is `.venv\Scripts\python.exe`.

3. Open `.vscode/mcp.json` and click **Start** above `cert-expiry` (or run **MCP: List Servers** from the Command Palette). Trust the server when prompted. The MCP output should show `Discovered 1 tools`.
4. Open Copilot Chat, switch to **Agent** mode, and ask, for example: _Check the certificate expiry for example.com_. Approve the tool call when asked.

## Run the tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

## Docker

```bash
docker build -t cert-expiry-mcp .

# Run the checker inside the container
docker run --rm cert-expiry-mcp python cert_checker.py example.com

# Run the MCP server (the -i flag keeps stdin open, which a stdio server needs)
docker run -i --rm cert-expiry-mcp
```

## Continuous integration

The workflow in `.github/workflows/tests.yml` runs on every push. It checks out the code, installs `requirements-dev.txt` and runs `pytest -v` on a fresh Ubuntu runner.

## Design notes

- **I/O is separated from logic.** The network call lives in one small function, so the date maths and warning logic can be tested without a network.
- **Certificates are verified.** An expired or untrusted certificate fails the TLS handshake, so the tool reports a verification error instead of a negative number of days.
- **Only port 443 is checked** through the tool, with a 5-second
