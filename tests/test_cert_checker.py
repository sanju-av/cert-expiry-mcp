"""Unit tests for cert_checker. The network is mocked, so no internet is needed."""

import socket
from datetime import datetime, timedelta, timezone

import pytest

import cert_checker
from cert_checker import CertificateCheckError, get_certificate_expiry


def make_cert(days_from_now: int) -> dict:
    """Build a fake certificate dict that expires in days_from_now days (+1 hour)."""
    expires = datetime.now(timezone.utc) + timedelta(days=days_from_now, hours=1)
    return {"notAfter": expires.strftime("%b %d %H:%M:%S %Y GMT")}


def fake_fetch(monkeypatch, cert: dict) -> None:
    """Replace the network function so it returns our fake certificate."""
    monkeypatch.setattr(
        cert_checker, "_fetch_certificate", lambda domain, port, timeout: cert
    )


def test_valid_certificate_has_no_warning(monkeypatch):
    fake_fetch(monkeypatch, make_cert(60))
    result = get_certificate_expiry("example.com")
    assert result["domain"] == "example.com"
    assert result["days_remaining"] == 60
    assert result["warning"] is False


def test_warning_when_fewer_than_30_days(monkeypatch):
    fake_fetch(monkeypatch, make_cert(29))
    result = get_certificate_expiry("example.com")
    assert result["days_remaining"] == 29
    assert result["warning"] is True


def test_exactly_30_days_is_not_a_warning(monkeypatch):
    fake_fetch(monkeypatch, make_cert(30))
    assert get_certificate_expiry("example.com")["warning"] is False


def test_empty_domain_is_rejected():
    with pytest.raises(CertificateCheckError, match="must not be empty"):
        get_certificate_expiry("   ")


def test_missing_certificate_is_an_error(monkeypatch):
    fake_fetch(monkeypatch, {})
    with pytest.raises(CertificateCheckError, match="No certificate"):
        get_certificate_expiry("example.com")


def test_dns_failure_gives_friendly_error(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.gaierror("name not known")

    monkeypatch.setattr(cert_checker.socket, "create_connection", fail)
    with pytest.raises(CertificateCheckError, match="Could not resolve"):
        get_certificate_expiry("bad.invalid")


def test_timeout_gives_friendly_error(monkeypatch):
    def fail(*args, **kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(cert_checker.socket, "create_connection", fail)
    with pytest.raises(CertificateCheckError, match="Timed out"):
        get_certificate_expiry("slow.example.com")