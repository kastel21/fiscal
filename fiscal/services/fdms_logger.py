"""
FDMS API call logging utility.
Stores request/response payloads, status codes, and errors for audit and debugging.
"""

import json
import logging

from fiscal.models import FDMSApiLog
from fiscal.utils import mask_sensitive_fields

logger = logging.getLogger("fiscal")


def _safe_json(value):
    """Convert value to JSON-serializable dict, or return as-is for JSONField."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if hasattr(value, "json") and callable(getattr(value, "json")):
        try:
            return value.json()
        except Exception:
            pass
    if hasattr(value, "text"):
        try:
            return json.loads(value.text) if value.text else {}
        except (json.JSONDecodeError, TypeError):
            return {"raw": str(value.text)[:10000]}
    return value


def log_fdms_call(
    endpoint: str,
    method: str,
    request_payload: dict | None = None,
    response=None,
    error: str | Exception | None = None,
) -> FDMSApiLog:
    """
    Log an FDMS API call to the database for audit and debugging.

    Args:
        endpoint: API endpoint path (e.g. "/Device/v1/123/GetConfig").
        method: HTTP method (e.g. "GET", "POST").
        request_payload: Request body as dict, or None.
        response: requests.Response or dict with 'status_code' and optional 'json'/body.
        error: Error message string or Exception to log.

    Returns:
        FDMSApiLog: The created log record.
    """
    request_json = _safe_json(request_payload) if request_payload is not None else {}
    if not isinstance(request_json, dict):
        request_json = {"payload": request_json}
    request_json = mask_sensitive_fields(request_json)

    status_code = None
    response_json = None

    if response is not None:
        if hasattr(response, "status_code"):
            status_code = response.status_code
        elif isinstance(response, dict):
            status_code = response.get("status_code")
        response_json = _safe_json(response)
        if isinstance(response_json, dict):
            response_json = mask_sensitive_fields(response_json)

    error_message = None
    if error is not None:
        error_message = str(error) if not isinstance(error, str) else error

    log_entry = FDMSApiLog.objects.create(
        endpoint=endpoint,
        method=method.upper(),
        request_payload=request_json,
        response_payload=response_json,
        status_code=status_code,
        error_message=error_message,
    )

    logger.info(
        "FDMS call logged: %s %s -> %s",
        method,
        endpoint,
        status_code or error_message or "unknown",
    )
    return log_entry
