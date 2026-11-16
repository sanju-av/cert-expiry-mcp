"""Certificate expiry checking logic. Standard library only."""

import socket
import ssl
import sys
from datetime import datetime, timezone

WARNING_THRESHOLD_DAYS = 30


class CertificateCheckError(Exception):
    """Raised when we cannot get a usable certificate for a domain."""


def _fetch_certificate(domain: str, port: int, timeout: float) -> dict:
    """Open a TLS connection and return the server's certificate as a dict."""
    context = ssl.create_default_context()
    try:
        with socket.create_connection((domain, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as tls_sock:
                return tls_sock.getpeercert()
    except socket.gaierror as exc:
        raise CertificateCheckError(
            f"Could not resolve '{domain}'. Check the domain name."
        ) from exc
    except TimeoutError as exc:
        raise CertificateCheckError(
            f"Timed out after {timeout} seconds connecting to {domain}:{port}."
        ) from exc
    except ssl.SSLCertVerificationError as exc:
        raise CertificateCheckError(
            f"Certificate for '{domain}' failed verification: {exc.verify_message}"
        ) from exc
    except ssl.SSLError as exc:
        raise CertificateCheckError(f"TLS error talking to '{domain}': {exc}") from exc
    except OSError as exc:
        raise CertificateCheckError(
            f"Could not connect to {domain}:{port}: {exc}"
        ) from exc


def get_certificate_expiry(domain: str, port: int = 443, timeout: float = 5.0) -> dict:
    """Return expiry date, days remaining and a warning flag for a domain."""
    domain = domain.strip()
    if not domain:
        raise CertificateCheckError("Domain must not be empty.")

    cert = _fetch_certificate(domain, port, timeout)
    if not cert or "notAfter" not in cert:
        raise CertificateCheckError(f"No certificate returned by {domain}.")

    expiry_timestamp = ssl.cert_time_to_seconds(cert["notAfter"])
    expires_at = datetime.fromtimestamp(expiry_timestamp, tz=timezone.utc)
    days_remaining = (expires_at - datetime.now(timezone.utc)).days

    return {
        "domain": domain,
        "expires_on": expires_at.isoformat(),
        "days_remaining": days_remaining,
        "warning": days_remaining < WARNING_THRESHOLD_DAYS,
    }


if __name__ == "__main__":
    # Quick manual test: python cert_checker.py example.com
    if len(sys.argv) != 2:
        print("Usage: python cert_checker.py <domain>", file=sys.stderr)
        sys.exit(1)
    try:
        print(get_certificate_expiry(sys.argv[1]))
    except CertificateCheckError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)