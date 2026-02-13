"""
Secure HTTP client for FDMS with retry logic and strict TLS.
Never uses verify=False.
"""

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("fiscal")

RETRY_STATUS_CODES = {500, 502}
NO_RETRY_STATUS_CODES = {400, 401, 422}


def requests_session_with_retry(
    retries: int = 3,
    backoff_factor: float = 2.0,
    status_forcelist: tuple = (500, 502),
) -> requests.Session:
    """Create session with retry on 500/502. Exponential backoff: 2s, 4s, 8s."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fdms_request(
    method: str,
    url: str,
    *,
    json: dict | None = None,
    headers: dict | None = None,
    cert: tuple[str, str] | None = None,
    timeout: int = 30,
) -> requests.Response:
    """
    Make FDMS request with retry on 500/502. Never disables SSL verification.
    """
    session = requests_session_with_retry(
        retries=3,
        backoff_factor=2.0,
        status_forcelist=(500, 502),
    )
    return session.request(
        method=method,
        url=url,
        json=json,
        headers=headers,
        cert=cert,
        timeout=timeout,
        verify=True,  # Always verify TLS
    )
