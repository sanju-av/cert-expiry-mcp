"""MCP server exposing a certificate expiry check tool."""

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from cert_checker import CertificateCheckError, get_certificate_expiry

mcp = MCPServer("cert-expiry-checker", version="0.1.0")


@mcp.tool()
def check_certificate_expiry(domain: str) -> dict:
    """Check the TLS certificate of a domain on port 443.

    Returns the expiry date, the number of days remaining, and a warning
    flag that is true when fewer than 30 days remain.
    """
    try:
        return get_certificate_expiry(domain)
    except CertificateCheckError as exc:
        raise ToolError(str(exc)) from exc


if __name__ == "__main__":
    mcp.run(transport="stdio")